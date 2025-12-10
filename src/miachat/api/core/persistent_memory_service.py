"""
Persistent Memory service for always-injected context.
Inspired by KoboldCpp's Memory feature.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ...database.models import PersistentMemory
from ...database.config import get_db
from .token_service import token_service

logger = logging.getLogger(__name__)


class PersistentMemoryService:
    """Service for managing user-configurable persistent memory.

    Persistent memories are always injected into the context,
    unlike World Info which is keyword-triggered.
    """

    def __init__(self):
        """Initialize the Persistent Memory service."""
        pass

    def create_memory(
        self,
        user_id: int,
        memory_data: Dict[str, Any],
        db: Session
    ) -> PersistentMemory:
        """Create a new persistent memory entry.

        Args:
            user_id: User ID
            memory_data: Memory data dictionary
            db: Database session

        Returns:
            Created PersistentMemory
        """
        content = memory_data.get('content', '')
        token_count = token_service.count_tokens(content)

        memory = PersistentMemory(
            user_id=user_id,
            character_id=memory_data.get('character_id'),
            name=memory_data.get('name', 'Untitled Memory'),
            content=content,
            is_enabled=1 if memory_data.get('is_enabled', True) else 0,
            priority=memory_data.get('priority', 100),
            insertion_position=memory_data.get('insertion_position', 'before_conversation'),
            token_count=token_count,
            max_tokens=memory_data.get('max_tokens')
        )

        db.add(memory)
        db.commit()
        db.refresh(memory)

        logger.info(f"Created persistent memory '{memory.name}' for user {user_id}")
        return memory

    def update_memory(
        self,
        memory_id: int,
        user_id: int,
        memory_data: Dict[str, Any],
        db: Session
    ) -> Optional[PersistentMemory]:
        """Update an existing persistent memory.

        Args:
            memory_id: Memory ID
            user_id: User ID (for ownership check)
            memory_data: Updated data
            db: Database session

        Returns:
            Updated memory or None if not found
        """
        memory = db.query(PersistentMemory).filter(
            PersistentMemory.id == memory_id,
            PersistentMemory.user_id == user_id
        ).first()

        if not memory:
            return None

        # Update fields
        if 'name' in memory_data:
            memory.name = memory_data['name']
        if 'content' in memory_data:
            memory.content = memory_data['content']
            memory.token_count = token_service.count_tokens(memory_data['content'])
        if 'is_enabled' in memory_data:
            memory.is_enabled = 1 if memory_data['is_enabled'] else 0
        if 'priority' in memory_data:
            memory.priority = memory_data['priority']
        if 'insertion_position' in memory_data:
            memory.insertion_position = memory_data['insertion_position']
        if 'max_tokens' in memory_data:
            memory.max_tokens = memory_data['max_tokens']
        if 'character_id' in memory_data:
            memory.character_id = memory_data['character_id']

        memory.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(memory)

        logger.info(f"Updated persistent memory '{memory.name}' (ID: {memory_id})")
        return memory

    def delete_memory(
        self,
        memory_id: int,
        user_id: int,
        db: Session
    ) -> bool:
        """Delete a persistent memory.

        Args:
            memory_id: Memory ID
            user_id: User ID (for ownership check)
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        memory = db.query(PersistentMemory).filter(
            PersistentMemory.id == memory_id,
            PersistentMemory.user_id == user_id
        ).first()

        if not memory:
            return False

        db.delete(memory)
        db.commit()

        logger.info(f"Deleted persistent memory ID: {memory_id}")
        return True

    def get_user_memories(
        self,
        user_id: int,
        character_id: Optional[str] = None,
        enabled_only: bool = True,
        insertion_position: Optional[str] = None,
        db: Session = None
    ) -> List[PersistentMemory]:
        """Get all persistent memories for a user.

        Args:
            user_id: User ID
            character_id: Optional character filter
            enabled_only: Only return enabled memories
            insertion_position: Filter by insertion position
            db: Database session

        Returns:
            List of matching memories
        """
        if db is None:
            db = next(get_db())

        query = db.query(PersistentMemory).filter(PersistentMemory.user_id == user_id)

        if enabled_only:
            query = query.filter(PersistentMemory.is_enabled == 1)

        if character_id:
            # Include global memories (NULL character_id) and character-specific
            query = query.filter(
                (PersistentMemory.character_id == None) |
                (PersistentMemory.character_id == character_id)
            )

        if insertion_position:
            query = query.filter(PersistentMemory.insertion_position == insertion_position)

        memories = query.order_by(PersistentMemory.priority.desc()).all()
        return memories

    def build_memory_context(
        self,
        user_id: int,
        character_id: Optional[str] = None,
        token_budget: Optional[int] = None,
        insertion_position: Optional[str] = None,
        format_style: str = 'sections',
        db: Session = None
    ) -> str:
        """Build persistent memory context string within budget.

        Args:
            user_id: User ID
            character_id: Optional character filter
            token_budget: Maximum tokens
            insertion_position: Filter by position (if None, returns all)
            format_style: How to format ('sections', 'inline', 'minimal')
            db: Database session

        Returns:
            Formatted memory context string
        """
        if db is None:
            db = next(get_db())

        memories = self.get_user_memories(
            user_id=user_id,
            character_id=character_id,
            enabled_only=True,
            insertion_position=insertion_position,
            db=db
        )

        if not memories:
            return ""

        parts = []
        total_tokens = 0

        if format_style == 'sections':
            parts.append("## Persistent Memory\n")

        for memory in memories:
            memory_tokens = memory.token_count or token_service.count_tokens(memory.content)

            # Apply memory-level max_tokens if set
            content = memory.content
            if memory.max_tokens and memory_tokens > memory.max_tokens:
                content = token_service.truncate_to_budget(
                    content,
                    memory.max_tokens,
                    preserve_end=False
                )
                memory_tokens = memory.max_tokens

            # Check token budget
            if token_budget and (total_tokens + memory_tokens) > token_budget:
                remaining = token_budget - total_tokens
                if remaining > 50:  # Minimum useful content
                    content = token_service.truncate_to_budget(
                        content,
                        remaining,
                        preserve_end=False
                    )
                    if format_style == 'sections':
                        parts.append(f"### {memory.name}")
                        parts.append(content)
                        parts.append("")
                    elif format_style == 'inline':
                        parts.append(f"[{memory.name}]: {content}")
                    else:
                        parts.append(content)
                break

            if format_style == 'sections':
                parts.append(f"### {memory.name}")
                parts.append(content)
                parts.append("")
            elif format_style == 'inline':
                parts.append(f"[{memory.name}]: {content}")
            else:  # minimal
                parts.append(content)

            total_tokens += memory_tokens

        return "\n".join(parts)

    def get_memories_by_position(
        self,
        user_id: int,
        character_id: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, List[PersistentMemory]]:
        """Get memories grouped by insertion position.

        Args:
            user_id: User ID
            character_id: Optional character filter
            db: Database session

        Returns:
            Dict mapping position to list of memories
        """
        if db is None:
            db = next(get_db())

        memories = self.get_user_memories(
            user_id=user_id,
            character_id=character_id,
            enabled_only=True,
            db=db
        )

        grouped = {
            'start': [],
            'after_system_prompt': [],
            'before_conversation': [],
            'before_user_message': []
        }

        for memory in memories:
            position = memory.insertion_position or 'before_conversation'
            if position in grouped:
                grouped[position].append(memory)
            else:
                grouped['before_conversation'].append(memory)

        return grouped

    def get_stats(self, user_id: Optional[int] = None, db: Session = None) -> Dict[str, Any]:
        """Get Persistent Memory statistics.

        Args:
            user_id: Optional user ID filter
            db: Database session

        Returns:
            Statistics dictionary
        """
        if db is None:
            db = next(get_db())

        query = db.query(PersistentMemory)
        if user_id:
            query = query.filter(PersistentMemory.user_id == user_id)

        memories = query.all()

        positions = {}
        total_tokens = 0
        enabled_count = 0

        for memory in memories:
            pos = memory.insertion_position or 'before_conversation'
            positions[pos] = positions.get(pos, 0) + 1
            total_tokens += memory.token_count or 0
            if memory.is_enabled:
                enabled_count += 1

        return {
            'total_memories': len(memories),
            'enabled_memories': enabled_count,
            'positions': positions,
            'total_tokens': total_tokens,
        }


# Global Persistent Memory service instance
persistent_memory_service = PersistentMemoryService()
