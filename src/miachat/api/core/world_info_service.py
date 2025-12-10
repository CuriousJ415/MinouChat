"""
World Info / Lorebook service for keyword-triggered context injection.
Inspired by KoboldCpp's World Info feature.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session

from ...database.models import WorldInfoEntry
from ...database.config import get_db
from .token_service import token_service

logger = logging.getLogger(__name__)


class WorldInfoService:
    """Service for managing World Info entries and keyword-triggered context injection."""

    def __init__(self):
        """Initialize the World Info service."""
        self._keyword_cache: Dict[int, Dict[str, Any]] = {}  # Cache compiled patterns by entry ID
        self._user_entries_cache: Dict[int, List[WorldInfoEntry]] = {}  # Cache entries by user

    def create_entry(
        self,
        user_id: int,
        entry_data: Dict[str, Any],
        db: Session
    ) -> WorldInfoEntry:
        """Create a new World Info entry.

        Args:
            user_id: User ID
            entry_data: Entry data dictionary
            db: Database session

        Returns:
            Created WorldInfoEntry
        """
        # Calculate token count for the content
        content = entry_data.get('content', '')
        token_count = token_service.count_tokens(content)

        entry = WorldInfoEntry(
            user_id=user_id,
            character_id=entry_data.get('character_id'),
            name=entry_data.get('name', 'Untitled'),
            description=entry_data.get('description'),
            category=entry_data.get('category'),
            keywords=entry_data.get('keywords', []),
            regex_pattern=entry_data.get('regex_pattern'),
            case_sensitive=1 if entry_data.get('case_sensitive', False) else 0,
            match_whole_word=1 if entry_data.get('match_whole_word', True) else 0,
            content=content,
            priority=entry_data.get('priority', 100),
            is_enabled=1 if entry_data.get('is_enabled', True) else 0,
            insertion_order=entry_data.get('insertion_order', 0),
            token_count=token_count,
            max_tokens=entry_data.get('max_tokens'),
            activation_conditions=entry_data.get('activation_conditions', {})
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)

        # Invalidate cache
        self._invalidate_user_cache(user_id)

        logger.info(f"Created World Info entry '{entry.name}' for user {user_id}")
        return entry

    def update_entry(
        self,
        entry_id: int,
        user_id: int,
        entry_data: Dict[str, Any],
        db: Session
    ) -> Optional[WorldInfoEntry]:
        """Update an existing World Info entry.

        Args:
            entry_id: Entry ID
            user_id: User ID (for ownership check)
            entry_data: Updated data
            db: Database session

        Returns:
            Updated entry or None if not found
        """
        entry = db.query(WorldInfoEntry).filter(
            WorldInfoEntry.id == entry_id,
            WorldInfoEntry.user_id == user_id
        ).first()

        if not entry:
            return None

        # Update fields
        if 'name' in entry_data:
            entry.name = entry_data['name']
        if 'description' in entry_data:
            entry.description = entry_data['description']
        if 'category' in entry_data:
            entry.category = entry_data['category']
        if 'keywords' in entry_data:
            entry.keywords = entry_data['keywords']
        if 'regex_pattern' in entry_data:
            entry.regex_pattern = entry_data['regex_pattern']
        if 'case_sensitive' in entry_data:
            entry.case_sensitive = 1 if entry_data['case_sensitive'] else 0
        if 'match_whole_word' in entry_data:
            entry.match_whole_word = 1 if entry_data['match_whole_word'] else 0
        if 'content' in entry_data:
            entry.content = entry_data['content']
            entry.token_count = token_service.count_tokens(entry_data['content'])
        if 'priority' in entry_data:
            entry.priority = entry_data['priority']
        if 'is_enabled' in entry_data:
            entry.is_enabled = 1 if entry_data['is_enabled'] else 0
        if 'insertion_order' in entry_data:
            entry.insertion_order = entry_data['insertion_order']
        if 'max_tokens' in entry_data:
            entry.max_tokens = entry_data['max_tokens']
        if 'activation_conditions' in entry_data:
            entry.activation_conditions = entry_data['activation_conditions']
        if 'character_id' in entry_data:
            entry.character_id = entry_data['character_id']

        entry.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(entry)

        # Invalidate caches
        self._invalidate_user_cache(user_id)
        self._invalidate_entry_cache(entry_id)

        logger.info(f"Updated World Info entry '{entry.name}' (ID: {entry_id})")
        return entry

    def delete_entry(
        self,
        entry_id: int,
        user_id: int,
        db: Session
    ) -> bool:
        """Delete a World Info entry.

        Args:
            entry_id: Entry ID
            user_id: User ID (for ownership check)
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        entry = db.query(WorldInfoEntry).filter(
            WorldInfoEntry.id == entry_id,
            WorldInfoEntry.user_id == user_id
        ).first()

        if not entry:
            return False

        db.delete(entry)
        db.commit()

        # Invalidate caches
        self._invalidate_user_cache(user_id)
        self._invalidate_entry_cache(entry_id)

        logger.info(f"Deleted World Info entry ID: {entry_id}")
        return True

    def get_user_entries(
        self,
        user_id: int,
        character_id: Optional[str] = None,
        category: Optional[str] = None,
        enabled_only: bool = True,
        db: Session = None
    ) -> List[WorldInfoEntry]:
        """Get all World Info entries for a user.

        Args:
            user_id: User ID
            character_id: Optional character filter
            category: Optional category filter
            enabled_only: Only return enabled entries
            db: Database session

        Returns:
            List of matching entries
        """
        if db is None:
            db = next(get_db())

        query = db.query(WorldInfoEntry).filter(WorldInfoEntry.user_id == user_id)

        if enabled_only:
            query = query.filter(WorldInfoEntry.is_enabled == 1)

        if character_id:
            # Include global entries (NULL character_id) and character-specific entries
            query = query.filter(
                (WorldInfoEntry.character_id == None) |
                (WorldInfoEntry.character_id == character_id)
            )

        if category:
            query = query.filter(WorldInfoEntry.category == category)

        entries = query.order_by(WorldInfoEntry.priority.desc()).all()
        return entries

    def find_triggered_entries(
        self,
        text: str,
        user_id: int,
        character_id: Optional[str] = None,
        token_budget: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Find all World Info entries triggered by keywords in the text.

        Args:
            text: Text to check for keyword triggers
            user_id: User ID
            character_id: Optional character ID for filtering
            token_budget: Maximum tokens to return
            context: Additional context for activation conditions
            db: Database session

        Returns:
            List of triggered entries with match info
        """
        if db is None:
            db = next(get_db())

        entries = self.get_user_entries(
            user_id=user_id,
            character_id=character_id,
            enabled_only=True,
            db=db
        )

        triggered = []
        total_tokens = 0

        for entry in entries:
            # Check if entry is triggered
            match_result = self._check_keyword_match(text, entry)

            if match_result['triggered']:
                # Check activation conditions if any
                if entry.activation_conditions and context:
                    if not self._check_activation_conditions(entry, context):
                        continue

                # Check token budget
                entry_tokens = entry.token_count or token_service.count_tokens(entry.content)

                # Apply entry-level max_tokens if set
                if entry.max_tokens and entry_tokens > entry.max_tokens:
                    entry_tokens = entry.max_tokens

                if token_budget and (total_tokens + entry_tokens) > token_budget:
                    # Try to fit partial content if possible
                    remaining_budget = token_budget - total_tokens
                    if remaining_budget > 50:  # Minimum useful content
                        truncated_content = token_service.truncate_to_budget(
                            entry.content,
                            remaining_budget,
                            preserve_end=False
                        )
                        triggered.append({
                            'id': entry.id,
                            'name': entry.name,
                            'content': truncated_content,
                            'category': entry.category,
                            'priority': entry.priority,
                            'insertion_order': entry.insertion_order,
                            'matched_keywords': match_result['matched_keywords'],
                            'token_count': remaining_budget,
                            'truncated': True
                        })
                        total_tokens = token_budget
                    break  # No more budget

                triggered.append({
                    'id': entry.id,
                    'name': entry.name,
                    'content': entry.content,
                    'category': entry.category,
                    'priority': entry.priority,
                    'insertion_order': entry.insertion_order,
                    'matched_keywords': match_result['matched_keywords'],
                    'token_count': entry_tokens,
                    'truncated': False
                })
                total_tokens += entry_tokens

        # Sort by insertion_order, then priority
        triggered.sort(key=lambda x: (x['insertion_order'], -x['priority']))

        logger.info(f"Found {len(triggered)} triggered World Info entries for user {user_id}")
        return triggered

    def build_world_info_context(
        self,
        triggered_entries: List[Dict[str, Any]],
        token_budget: Optional[int] = None,
        format_style: str = 'sections'
    ) -> str:
        """Build the World Info context string from triggered entries.

        Args:
            triggered_entries: List of triggered entry dicts
            token_budget: Maximum tokens for output
            format_style: How to format ('sections', 'inline', 'minimal')

        Returns:
            Formatted context string
        """
        if not triggered_entries:
            return ""

        parts = []

        if format_style == 'sections':
            parts.append("## World Information\n")
            for entry in triggered_entries:
                if entry.get('category'):
                    parts.append(f"### {entry['name']} ({entry['category']})")
                else:
                    parts.append(f"### {entry['name']}")
                parts.append(entry['content'])
                parts.append("")

        elif format_style == 'inline':
            for entry in triggered_entries:
                parts.append(f"[{entry['name']}]: {entry['content']}")

        else:  # minimal
            for entry in triggered_entries:
                parts.append(entry['content'])

        context = "\n".join(parts)

        # Truncate if over budget
        if token_budget:
            context = token_service.truncate_to_budget(
                context,
                token_budget,
                preserve_end=False
            )

        return context

    def test_triggers(
        self,
        text: str,
        user_id: int,
        character_id: Optional[str] = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Test which entries would be triggered by given text.

        Useful for debugging and UI previews.

        Args:
            text: Text to test
            user_id: User ID
            character_id: Optional character filter
            db: Database session

        Returns:
            List of entries with match details
        """
        if db is None:
            db = next(get_db())

        entries = self.get_user_entries(
            user_id=user_id,
            character_id=character_id,
            enabled_only=True,
            db=db
        )

        results = []
        for entry in entries:
            match_result = self._check_keyword_match(text, entry)
            results.append({
                'id': entry.id,
                'name': entry.name,
                'triggered': match_result['triggered'],
                'matched_keywords': match_result['matched_keywords'],
                'keywords': entry.keywords,
                'category': entry.category
            })

        return results

    def _check_keyword_match(self, text: str, entry: WorldInfoEntry) -> Dict[str, Any]:
        """Check if text triggers an entry's keywords.

        Args:
            text: Text to check
            entry: World Info entry

        Returns:
            Dict with 'triggered' bool and 'matched_keywords' list
        """
        result = {
            'triggered': False,
            'matched_keywords': []
        }

        # Prepare text for matching
        check_text = text if entry.case_sensitive else text.lower()

        # Check keywords
        keywords = entry.keywords if isinstance(entry.keywords, list) else []
        for keyword in keywords:
            check_keyword = keyword if entry.case_sensitive else keyword.lower()

            if entry.match_whole_word:
                # Use word boundary matching
                pattern = r'\b' + re.escape(check_keyword) + r'\b'
                if re.search(pattern, check_text):
                    result['matched_keywords'].append(keyword)
                    result['triggered'] = True
            else:
                # Simple substring match
                if check_keyword in check_text:
                    result['matched_keywords'].append(keyword)
                    result['triggered'] = True

        # Check regex pattern if defined
        if entry.regex_pattern and not result['triggered']:
            try:
                flags = 0 if entry.case_sensitive else re.IGNORECASE
                if re.search(entry.regex_pattern, text, flags):
                    result['triggered'] = True
                    result['matched_keywords'].append(f"[regex: {entry.regex_pattern}]")
            except re.error as e:
                logger.warning(f"Invalid regex pattern in entry {entry.id}: {e}")

        return result

    def _check_activation_conditions(
        self,
        entry: WorldInfoEntry,
        context: Dict[str, Any]
    ) -> bool:
        """Check if entry meets its activation conditions.

        Args:
            entry: World Info entry
            context: Context dictionary with message count, character, etc.

        Returns:
            True if conditions are met
        """
        conditions = entry.activation_conditions or {}

        # Check minimum message count
        if 'min_messages' in conditions:
            message_count = context.get('message_count', 0)
            if message_count < conditions['min_messages']:
                return False

        # Check required character
        if 'requires_character' in conditions:
            current_character = context.get('character_id')
            if current_character != conditions['requires_character']:
                return False

        # Check time range if specified
        if 'time_range' in conditions:
            time_range = conditions['time_range']
            current_hour = datetime.now().hour
            start_hour = time_range.get('start', 0)
            end_hour = time_range.get('end', 24)
            if not (start_hour <= current_hour < end_hour):
                return False

        return True

    def _invalidate_user_cache(self, user_id: int):
        """Invalidate cached entries for a user."""
        if user_id in self._user_entries_cache:
            del self._user_entries_cache[user_id]

    def _invalidate_entry_cache(self, entry_id: int):
        """Invalidate cached pattern for an entry."""
        if entry_id in self._keyword_cache:
            del self._keyword_cache[entry_id]

    def get_stats(self, user_id: Optional[int] = None, db: Session = None) -> Dict[str, Any]:
        """Get World Info statistics.

        Args:
            user_id: Optional user ID filter
            db: Database session

        Returns:
            Statistics dictionary
        """
        if db is None:
            db = next(get_db())

        query = db.query(WorldInfoEntry)
        if user_id:
            query = query.filter(WorldInfoEntry.user_id == user_id)

        entries = query.all()

        categories = {}
        total_tokens = 0
        enabled_count = 0

        for entry in entries:
            cat = entry.category or 'uncategorized'
            categories[cat] = categories.get(cat, 0) + 1
            total_tokens += entry.token_count or 0
            if entry.is_enabled:
                enabled_count += 1

        return {
            'total_entries': len(entries),
            'enabled_entries': enabled_count,
            'categories': categories,
            'total_tokens': total_tokens,
        }


# Global World Info service instance
world_info_service = WorldInfoService()
