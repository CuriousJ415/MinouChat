"""
Fact Extraction Service for automatically learning facts from conversations.

Uses the LLM to extract user facts from conversation exchanges and stores
them in the database for future context enrichment.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ...database.models import ConversationFact
from .llm_client import llm_client

logger = logging.getLogger(__name__)

# Fact types and their descriptions
FACT_TYPES = {
    'name': 'User name or nickname',
    'preference': 'User preferences (likes, dislikes, favorites)',
    'relationship': 'Relationships (family, friends, partners)',
    'event': 'Important events or experiences',
    'trait': 'Personality traits or characteristics',
    'location': 'Where the user lives or works',
    'occupation': 'Job, profession, or career',
    'hobby': 'Hobbies, interests, activities',
    'goal': 'Goals, aspirations, or plans',
    'other': 'Other notable facts'
}

# Prompt for fact extraction - optimized for consistent JSON output
# Note: Double braces {{ }} are used to escape literal braces in .format() strings
FACT_EXTRACTION_PROMPT = """You are a fact extraction system. Analyze this conversation and extract personal facts about the user.

TASK: Extract 0-3 facts from the user's message. Return ONLY a JSON array, nothing else.

VALID FACT TYPES: name, preference, relationship, location, occupation, hobby, goal, trait, event, other

OUTPUT FORMAT (exact JSON, no markdown):
[{{"fact_type":"name","fact_key":"user_name","fact_value":"Jason"}}]

RULES:
- Only explicit facts directly stated by the user
- No inferences or assumptions
- Return [] if no facts found
- fact_key should be snake_case (e.g., "favorite_color", "pet_name")
- fact_value should be the actual value, not a description

USER MESSAGE: {user_message}

JSON ARRAY:"""


class FactExtractionService:
    """Extracts and manages facts learned from conversations."""

    def __init__(self):
        # Rate limiting: track last extraction time per user
        self._last_extraction = {}
        self.min_extraction_interval = 5  # seconds between extractions per user
        self.min_message_length = 20  # minimum user message length to trigger extraction

        # Caching for fact retrieval
        self._facts_cache = {}  # Key: "user_id:character_id", Value: {"facts": [...], "timestamp": datetime}
        self.cache_ttl = 60  # Cache TTL in seconds (1 minute)

    async def extract_facts_from_message(
        self,
        user_message: str,
        assistant_response: str,
        user_id: int,
        character_id: str,
        conversation_id: Optional[int],
        message_id: Optional[int],
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Use the LLM to extract facts from a conversation exchange.

        This should be called after generating a response, typically in a
        background/async context to avoid blocking the main response.

        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            user_id: User ID
            character_id: Character ID (facts can be character-specific or global)
            conversation_id: Optional conversation ID for source tracking
            message_id: Optional message ID for source tracking
            db: Database session

        Returns:
            List of extracted and saved facts
        """
        # Skip if message too short
        if len(user_message) < self.min_message_length:
            return []

        # Rate limiting
        cache_key = f"{user_id}:{character_id}"
        now = datetime.now(timezone.utc)
        last = self._last_extraction.get(cache_key)
        if last and (now - last).seconds < self.min_extraction_interval:
            logger.debug(f"Rate limited fact extraction for user {user_id}")
            return []
        self._last_extraction[cache_key] = now

        try:
            # Build extraction prompt - only use user message for cleaner extraction
            prompt = FACT_EXTRACTION_PROMPT.format(
                user_message=user_message[:500]  # Limit input size
            )

            # Use default Ollama for fact extraction (privacy: uses local model)
            messages = [{"role": "user", "content": prompt}]
            model_config = {
                'provider': 'ollama',
                'model': 'llama3.1:8b',
                'temperature': 0.0,  # Zero temp for deterministic JSON output
                'max_tokens': 300,
                'top_p': 0.1  # Very focused output
            }

            response = llm_client.generate_response_with_config(
                messages=messages,
                system_prompt="You extract facts from text and return JSON arrays only. Never add explanations.",
                model_config=model_config
            )

            logger.debug(f"Fact extraction raw response: {response[:500] if response else 'None'}")

            # Parse JSON response
            facts = self._parse_facts_response(response)
            logger.debug(f"Parsed facts: {facts}")

            # Ensure facts is a list
            if not isinstance(facts, list):
                logger.warning(f"Facts is not a list, got {type(facts)}: {facts}")
                if isinstance(facts, dict):
                    # Single fact dict returned instead of array
                    facts = [facts]
                else:
                    facts = []

            # Validate and save facts
            saved_facts = []
            for fact in facts[:3]:  # Max 3 facts per extraction
                if self._is_valid_fact(fact):
                    saved = self._save_fact(
                        user_id=user_id,
                        character_id=character_id,
                        fact=fact,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        db=db
                    )
                    if saved:
                        saved_facts.append(saved)

            if saved_facts:
                logger.info(f"Extracted {len(saved_facts)} facts for user {user_id}")

            return saved_facts

        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return []

    def get_user_facts(
        self,
        user_id: int,
        character_id: Optional[str] = None,
        db: Session = None,
        include_global: bool = True,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all known facts about the user.

        Args:
            user_id: User ID
            character_id: Optional character ID to filter by
            db: Database session
            include_global: Whether to include facts with no character_id (global facts)
            use_cache: Whether to use cached results (default True)

        Returns:
            List of fact dictionaries
        """
        # Check cache first
        cache_key = f"{user_id}:{character_id or 'all'}:{include_global}"
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for facts: {cache_key}")
                return cached

        # Query database
        query = db.query(ConversationFact).filter(
            ConversationFact.user_id == user_id,
            ConversationFact.is_active == 1
        )

        if character_id:
            if include_global:
                # Get both character-specific and global facts
                query = query.filter(
                    (ConversationFact.character_id == character_id) |
                    (ConversationFact.character_id.is_(None))
                )
            else:
                query = query.filter(ConversationFact.character_id == character_id)

        facts = query.order_by(ConversationFact.created_at.desc()).all()

        result = [
            {
                'id': f.id,
                'fact_type': f.fact_type,
                'fact_key': f.fact_key,
                'fact_value': f.fact_value,
                'character_id': f.character_id,
                'confidence': f.confidence,
                'created_at': f.created_at.isoformat() if f.created_at else None,
                'is_global': f.character_id is None
            }
            for f in facts
        ]

        # Cache the results
        if use_cache:
            self._set_cache(cache_key, result)

        return result

    def _get_from_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Get facts from cache if not expired."""
        if key not in self._facts_cache:
            return None

        cached = self._facts_cache[key]
        age = (datetime.now(timezone.utc) - cached['timestamp']).total_seconds()

        if age > self.cache_ttl:
            # Cache expired
            del self._facts_cache[key]
            return None

        return cached['facts']

    def _set_cache(self, key: str, facts: List[Dict[str, Any]]):
        """Store facts in cache."""
        self._facts_cache[key] = {
            'facts': facts,
            'timestamp': datetime.now(timezone.utc)
        }

    def invalidate_cache(self, user_id: int, character_id: Optional[str] = None):
        """
        Invalidate cache entries for a user/character.

        Called after saving or updating facts.
        """
        # Clear all cache entries for this user
        keys_to_remove = [
            k for k in self._facts_cache.keys()
            if k.startswith(f"{user_id}:")
        ]
        for key in keys_to_remove:
            del self._facts_cache[key]

        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for user {user_id}")

    def update_fact(
        self,
        fact_id: int,
        new_value: str,
        user_id: int,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Allow manual fact correction.

        Args:
            fact_id: Fact ID to update
            new_value: New fact value
            user_id: User ID (for ownership verification)
            db: Database session

        Returns:
            Updated fact dict or None if not found
        """
        fact = db.query(ConversationFact).filter(
            ConversationFact.id == fact_id,
            ConversationFact.user_id == user_id
        ).first()

        if not fact:
            return None

        fact.fact_value = new_value.strip()
        fact.confidence = 1.0  # User-corrected facts have full confidence
        fact.updated_at = datetime.now(timezone.utc)

        db.commit()

        # Invalidate cache after update
        self.invalidate_cache(user_id)

        return {
            'id': fact.id,
            'fact_type': fact.fact_type,
            'fact_key': fact.fact_key,
            'fact_value': fact.fact_value,
            'updated_at': fact.updated_at.isoformat()
        }

    def delete_fact(
        self,
        fact_id: int,
        user_id: int,
        db: Session
    ) -> bool:
        """
        Remove an incorrect fact (soft delete).

        Args:
            fact_id: Fact ID to delete
            user_id: User ID (for ownership verification)
            db: Database session

        Returns:
            True if deleted, False if not found
        """
        fact = db.query(ConversationFact).filter(
            ConversationFact.id == fact_id,
            ConversationFact.user_id == user_id
        ).first()

        if not fact:
            return False

        # Soft delete
        fact.is_active = 0
        fact.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Invalidate cache after delete
        self.invalidate_cache(user_id)

        return True

    def create_fact(
        self,
        user_id: int,
        fact_type: str,
        fact_key: str,
        fact_value: str,
        character_id: Optional[str],
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Manually create a new fact.

        Args:
            user_id: User ID
            fact_type: Type of fact (name, preference, hobby, etc.)
            fact_key: Key/label for the fact (e.g., 'favorite_color')
            fact_value: The fact value (e.g., 'blue')
            character_id: Optional character ID (None for global facts)
            db: Database session

        Returns:
            Created fact dict or None if validation failed
        """
        # Validate fact type
        if fact_type not in FACT_TYPES:
            logger.warning(f"Invalid fact_type: {fact_type}")
            return None

        # Build fact dict and validate
        fact = {
            'fact_type': fact_type,
            'fact_key': fact_key.strip().lower().replace(' ', '_'),
            'fact_value': fact_value.strip()
        }

        if not self._is_valid_fact(fact):
            return None

        # Save the fact
        saved = self._save_fact(
            user_id=user_id,
            character_id=character_id,
            fact=fact,
            conversation_id=None,
            message_id=None,
            db=db
        )

        if saved:
            # Set confidence to 1.0 for manually created facts
            db_fact = db.query(ConversationFact).filter(
                ConversationFact.id == saved['id']
            ).first()
            if db_fact:
                db_fact.confidence = 1.0
                db.commit()
                saved['confidence'] = 1.0

        return saved

    def format_facts_context(
        self,
        user_id: int,
        character_id: Optional[str],
        db: Session
    ) -> str:
        """
        Format user facts as context for system prompt.

        Args:
            user_id: User ID
            character_id: Optional character ID
            db: Database session

        Returns:
            Formatted context string
        """
        facts = self.get_user_facts(user_id, character_id, db)

        if not facts:
            return ""

        lines = ["[What you know about the user - use naturally in conversation]"]

        for fact in facts:
            # Format: "- user_name: Jason" or "- favorite_color: blue"
            lines.append(f"- {fact['fact_key']}: {fact['fact_value']}")

        return "\n".join(lines)

    def _parse_facts_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract JSON facts array with robust error handling."""
        if not response:
            return []

        try:
            # Clean up response
            response = response.strip()

            # Remove common prefixes the LLM might add
            prefixes_to_remove = [
                "Here is", "Here's", "The facts are:", "Facts:", "JSON:",
                "Output:", "Result:", "Answer:"
            ]
            for prefix in prefixes_to_remove:
                if response.lower().startswith(prefix.lower()):
                    response = response[len(prefix):].strip()

            # Handle empty array responses
            if response in ['[]', '[ ]', 'null', 'None', '']:
                return []

            # Try direct JSON parse first
            if response.startswith('['):
                # Find the matching closing bracket
                bracket_count = 0
                end_idx = 0
                for i, char in enumerate(response):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break
                if end_idx > 0:
                    json_str = response[:end_idx]
                    return json.loads(json_str)

            # Try to extract JSON from markdown code block
            code_block_patterns = [
                r'```json\s*([\s\S]*?)\s*```',
                r'```\s*([\s\S]*?)\s*```',
                r'`(\[[\s\S]*?\])`'
            ]
            for pattern in code_block_patterns:
                match = re.search(pattern, response)
                if match:
                    json_str = match.group(1).strip()
                    if json_str.startswith('['):
                        return json.loads(json_str)

            # Try to find array pattern anywhere in response
            array_pattern = r'\[\s*(?:\{[^}]*\}\s*,?\s*)*\]'
            array_match = re.search(array_pattern, response, re.DOTALL)
            if array_match:
                return json.loads(array_match.group(0))

            # Last resort: try to extract individual fact objects
            fact_pattern = r'\{\s*"fact_type"\s*:\s*"([^"]+)"\s*,\s*"fact_key"\s*:\s*"([^"]+)"\s*,\s*"fact_value"\s*:\s*"([^"]+)"\s*\}'
            matches = re.findall(fact_pattern, response)
            if matches:
                return [
                    {"fact_type": m[0], "fact_key": m[1], "fact_value": m[2]}
                    for m in matches
                ]

            logger.debug(f"No JSON facts found in response: {response[:100]}...")
            return []

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse facts JSON: {e}. Response: {response[:200]}...")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing facts: {e}")
            return []

    def _is_valid_fact(self, fact: Dict[str, Any]) -> bool:
        """Validate a fact dictionary."""
        # First check it's actually a dict
        if not isinstance(fact, dict):
            logger.warning(f"Fact is not a dict: {type(fact)} - {fact}")
            return False

        required_fields = ['fact_type', 'fact_key', 'fact_value']

        # Check required fields
        if not all(field in fact for field in required_fields):
            logger.warning(f"Fact missing required fields: {fact}")
            return False

        # Check fact_type is valid
        if fact['fact_type'] not in FACT_TYPES:
            logger.warning(f"Invalid fact_type '{fact['fact_type']}' not in {list(FACT_TYPES.keys())}")
            return False

        # Check values are non-empty strings
        if not isinstance(fact['fact_value'], str) or not fact['fact_value'].strip():
            return False

        if not isinstance(fact['fact_key'], str) or not fact['fact_key'].strip():
            return False

        # Security: Don't store anything that looks like code or commands
        value = fact['fact_value'].lower()
        danger_patterns = [
            'import ', 'eval(', 'exec(', '<script', 'javascript:',
            'rm -', 'sudo ', 'curl ', 'wget '
        ]
        if any(pattern in value for pattern in danger_patterns):
            logger.warning(f"Rejected fact with suspicious content: {fact['fact_key']}")
            return False

        return True

    def _save_fact(
        self,
        user_id: int,
        character_id: Optional[str],
        fact: Dict[str, Any],
        conversation_id: Optional[int],
        message_id: Optional[int],
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Save a validated fact to the database."""
        try:
            # Check if we already have this fact (by key)
            existing = db.query(ConversationFact).filter(
                ConversationFact.user_id == user_id,
                ConversationFact.fact_key == fact['fact_key'],
                ConversationFact.is_active == 1
            ).first()

            if existing:
                # Update existing fact if value changed
                if existing.fact_value != fact['fact_value']:
                    existing.fact_value = fact['fact_value']
                    existing.updated_at = datetime.now(timezone.utc)
                    existing.confidence = min(existing.confidence + 0.1, 1.0)  # Boost confidence
                    db.commit()
                    # Invalidate cache after update
                    self.invalidate_cache(user_id)
                    return {
                        'id': existing.id,
                        'fact_type': existing.fact_type,
                        'fact_key': existing.fact_key,
                        'fact_value': existing.fact_value,
                        'updated': True
                    }
                return None  # Same value, no update needed

            # Create new fact
            new_fact = ConversationFact(
                user_id=user_id,
                character_id=character_id,
                fact_type=fact['fact_type'],
                fact_key=fact['fact_key'],
                fact_value=fact['fact_value'],
                source_conversation_id=conversation_id,
                source_message_id=message_id,
                confidence=0.8,  # Initial confidence
                is_active=1,
                created_at=datetime.now(timezone.utc)
            )
            db.add(new_fact)
            db.commit()

            # Invalidate cache after saving new fact
            self.invalidate_cache(user_id)

            return {
                'id': new_fact.id,
                'fact_type': new_fact.fact_type,
                'fact_key': new_fact.fact_key,
                'fact_value': new_fact.fact_value,
                'updated': False
            }

        except Exception as e:
            logger.error(f"Error saving fact: {e}")
            db.rollback()
            return None


# Global instance
fact_extraction_service = FactExtractionService()
