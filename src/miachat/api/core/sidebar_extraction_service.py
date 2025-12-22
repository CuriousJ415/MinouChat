"""
Sidebar Extraction Service for MinouChat.

Extracts todos and life area ratings from chat messages using LLM.
Integrates with todo_service and life_area_service for persistence.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from .todo_service import todo_service
from .life_area_service import life_area_service
from .llm_client import LLMClient
from ...database.models import LIFE_AREAS

logger = logging.getLogger(__name__)


class SidebarExtractionService:
    """Service for extracting sidebar document items from chat messages."""

    # Trigger phrases for todo extraction
    TODO_TRIGGERS = [
        r'\b(add|put).*(to.*(my|the).*)?(?:to.?do|task|list)\b',
        r'\bremind me to\b',
        r'\bi need to\b',
        r'\bdon\'?t (let me )?forget to\b',
        r'\bmake sure (i|to)\b',
        r'\bi should\b',
        r'\bi have to\b',
        r'\bi\'?ve got to\b',
        r'\badd\s+(this|these|that|those)\s+to\s+(my\s+)?(?:to.?do|task|list)',  # "add this to my todo"
        r'\bplease\s+add\s+(this|these|that|those|it)\b',  # "please add this/these"
        r'\bput\s+(this|these|that|those)\s+on\s+(my\s+)?(?:to.?do|task|list)',  # "put this on my list"
        r'\bcan you add\b.*(?:to.?do|task|list)',  # "can you add X to my todo"
    ]

    # Patterns that indicate reference to previous context
    CONTEXT_REFERENCE_PATTERNS = [
        r'\b(this|these|that|those|it)\b',
    ]

    # Trigger phrases for life area extraction
    LIFE_AREA_TRIGGERS = [
        r'\b(my\s+)?(career|job|work).*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?finances?.*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?health.*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?relationships?.*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?family.*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?friendships?.*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?growth.*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?(fun|recreation).*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?environment.*(?:is|at|feels?|rate).*\d',
        r'\b(my\s+)?contribution.*(?:is|at|feels?|rate).*\d',
        r'\brate\s+(my\s+)?\w+.*(?:as|at)\s*\d',
        r'\b\d+\s*(?:out\s+of\s+10|/10)\s*(?:for|on)\s+\w+',
    ]

    def __init__(self):
        self.llm_client = None

    def _get_llm_client(self) -> LLMClient:
        """Get or create LLM client."""
        if not self.llm_client:
            self.llm_client = LLMClient()
        return self.llm_client

    def should_extract_todos(self, message: str) -> bool:
        """Check if message might contain todo items."""
        message_lower = message.lower()
        for pattern in self.TODO_TRIGGERS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        return False

    def should_extract_life_areas(self, message: str) -> bool:
        """Check if message might contain life area ratings."""
        message_lower = message.lower()
        for pattern in self.LIFE_AREA_TRIGGERS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        return False

    def _references_context(self, message: str) -> bool:
        """Check if message references previous conversation context."""
        message_lower = message.lower()
        for pattern in self.CONTEXT_REFERENCE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        return False

    async def extract_todos(
        self,
        message: str,
        user_id: int,
        character_id: str,
        db: Session,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Extract todo items from a message using LLM.

        Args:
            message: User message to extract from
            user_id: User ID for saving todos
            character_id: Character ID for context
            db: Database session
            conversation_context: Recent conversation messages for context

        Returns:
            List of created todo items
        """
        if not self.should_extract_todos(message):
            return []

        try:
            llm = self._get_llm_client()

            # Check if message references previous context
            needs_context = self._references_context(message)

            # Build context string from recent messages
            context_str = ""
            if needs_context and conversation_context:
                recent_user_messages = [
                    msg['content'] for msg in conversation_context
                    if msg.get('role') == 'user' and msg.get('content') != message
                ][-3:]  # Last 3 user messages
                if recent_user_messages:
                    context_str = "\n\nPREVIOUS USER MESSAGES (extract tasks from these):\n" + "\n".join(
                        f"- \"{msg}\"" for msg in recent_user_messages
                    )

            # Build a more explicit prompt when context is needed
            if needs_context and context_str:
                extraction_prompt = f"""The user said: "{message}"

This means they want to add tasks to their todo list from their previous messages.
{context_str}

Extract the ACTUAL TASKS from the previous messages above. Do NOT extract "this", "these", "those" - extract what they actually need to do.

Return a JSON array. Example format:
[{{"text": "Buy groceries from Costco", "priority": 2}}, {{"text": "Pick up dry cleaning", "priority": 3}}]

Rules:
- Extract specific, actionable tasks from the context above
- Each task should be a clear action item
- priority: 1=urgent, 2=normal, 3=low
- If no tasks found, return []

Return ONLY the JSON array, nothing else."""
            else:
                extraction_prompt = f"""Extract todo items from this message:
"{message}"

Return a JSON array of tasks. Example: [{{"text": "Buy milk", "priority": 2}}]
priority: 1=urgent, 2=normal, 3=low

Return ONLY the JSON array, nothing else."""

            # LLMClient.generate_response is synchronous
            response_text = llm.generate_response(
                messages=[{"role": "user", "content": extraction_prompt}],
                model="llama3.1:latest",  # Use better model for context understanding
                temperature=0.1,
                max_tokens=800
            ).strip()

            # Try to extract JSON from response
            todos_data = self._parse_json_array(response_text)

            if not todos_data:
                return []

            created_todos = []
            for todo_data in todos_data:
                if not todo_data.get('text'):
                    continue

                todo = todo_service.create_todo(
                    user_id=user_id,
                    character_id=character_id,
                    text=todo_data['text'][:500],  # Limit length
                    priority=min(max(todo_data.get('priority', 2), 1), 3),
                    source_type='extracted',
                    db=db
                )
                created_todos.append(todo)
                logger.info(f"Extracted todo: {todo_data['text'][:50]}...")

            return created_todos

        except Exception as e:
            logger.error(f"Error extracting todos: {str(e)}")
            return []

    async def extract_life_areas(
        self,
        message: str,
        user_id: int,
        character_id: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Extract life area ratings from a message using LLM.

        Args:
            message: User message to extract from
            user_id: User ID for saving scores
            character_id: Character ID for context
            db: Database session

        Returns:
            List of updated life area scores
        """
        if not self.should_extract_life_areas(message):
            return []

        try:
            llm = self._get_llm_client()

            extraction_prompt = f"""Extract any life area self-ratings from this message.
Valid life areas: {', '.join(LIFE_AREAS)}

Return a JSON array of objects with:
- "area": One of the valid life areas above
- "score": Number from 1-10

Only extract explicit ratings. If no ratings found, return empty array [].

Message: "{message}"

Return only valid JSON array, nothing else."""

            # LLMClient.generate_response is synchronous
            response_text = llm.generate_response(
                messages=[{"role": "user", "content": extraction_prompt}],
                model="llama3.1:8b",  # Use fast local model
                temperature=0.1,
                max_tokens=300
            ).strip()

            # Try to extract JSON from response
            ratings_data = self._parse_json_array(response_text)

            if not ratings_data:
                return []

            updated_scores = []
            for rating in ratings_data:
                area = rating.get('area', '').lower()
                score = rating.get('score')

                # Validate area
                if area not in LIFE_AREAS:
                    continue

                # Validate score
                if not isinstance(score, (int, float)) or not 1 <= score <= 10:
                    continue

                score_data = life_area_service.update_score(
                    user_id=user_id,
                    character_id=character_id,
                    area=area,
                    score=int(score),
                    source_type='extracted',
                    db=db
                )
                updated_scores.append(score_data)
                logger.info(f"Extracted life area: {area} = {score}")

            return updated_scores

        except Exception as e:
            logger.error(f"Error extracting life areas: {str(e)}")
            return []

    def _parse_json_array(self, text: str) -> Optional[List[Dict]]:
        """Parse JSON array from text, handling markdown code blocks."""
        # Try direct parse first
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            try:
                data = json.loads(code_block_match.group(1))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Try finding array brackets
        array_match = re.search(r'\[[\s\S]*\]', text)
        if array_match:
            try:
                data = json.loads(array_match.group(0))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        return None

    async def process_message(
        self,
        message: str,
        user_id: int,
        character_id: str,
        category: str,
        db: Session,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Process a message for sidebar extractions based on character category.

        Args:
            message: User message to process
            user_id: User ID
            character_id: Character ID
            category: Character category ('Coach', 'Assistant', etc.)
            db: Database session
            conversation_context: Recent conversation messages for context

        Returns:
            Dictionary with extracted items
        """
        extractions = {
            'todos': [],
            'life_areas': []
        }

        # Extract todos for Assistant category
        if category and category.lower() == 'assistant':
            extractions['todos'] = await self.extract_todos(
                message, user_id, character_id, db, conversation_context
            )

        # Extract life areas for Coach category
        if category and category.lower() == 'coach':
            extractions['life_areas'] = await self.extract_life_areas(
                message, user_id, character_id, db
            )

        return extractions


# Global service instance
sidebar_extraction_service = SidebarExtractionService()
