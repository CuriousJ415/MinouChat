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
from .tracking_service import tracking_service
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

    # Trigger phrases for goal extraction
    GOAL_TRIGGERS = [
        r'\blet\'?s\s+set\s+a\s+goal\b',
        r'\bi\s+want\s+to\s+(?:start|begin)\s+(?:a\s+)?goal\b',
        r'\bmy\s+goal\s+is\s+to\b',
        r'\bhelp\s+me\s+(?:set|track|create)\s+(?:a\s+)?goal\b',
        # Flexible number patterns with optional currency/units
        r'\bi\s+want\s+to\s+(?:lose|gain|save|read|run|write|exercise|earn|make|finish|complete)\s+[\$£€]?\d+',
        r'\bi\s+want\s+to\s+save\s+(?:money|up|for)\b',  # "I want to save money", "I want to save up"
        r'\bi\s+want\s+to\s+lose\s+(?:weight|some)\b',  # "I want to lose weight"
        r'\bby\s+(?:the\s+end\s+of|next)\s+(?:month|week|year)',
        r'\bi\'?m\s+going\s+to\s+achieve\b',
        r'\bset\s+(?:a\s+)?goal\s+(?:to|for)\b',
        r'\b(?:set|make|add)\s+(?:this|that|it)\s+(?:as\s+)?(?:a\s+|my\s+)?goal\b',
        r'\badd\s+(?:this|that|it)\s+to\s+(?:my\s+)?goals?\b',
        r'\b(?:create|make|set)\s+(?:a\s+)?goal\b',
        r'\btrack\s+(?:this|that|it)\s+as\s+a\s+goal\b',
        r'\b(?:every|each)\s+day\s+for\s+\d+\s+(?:days?|weeks?)\b',
        r'\bfor\s+(?:the\s+)?next\s+\d+\s+(?:days?|weeks?|months?)\b',
        r'\bgoal\s+to\s+\w+',  # "goal to write", "goal to save"
        r'\bplease\s+(?:make|create|set|add)\s+(?:a\s+)?goal\b',
        r'\bnew\s+goal\b',  # "new goal"
        r'\bgoal\s*:\s*\w+',  # "goal: save money"
        r'\bgoal\b.*\d+',  # any message with "goal" and a number
    ]

    # Trigger phrases for habit extraction
    HABIT_TRIGGERS = [
        r'\bi\s+want\s+to\s+(?:start|build|develop)\s+(?:a\s+)?habit\b',
        r'\bhelp\s+me\s+(?:track|create|start)\s+(?:a\s+)?habit\b',
        r'\bi\s+want\s+to\s+do\s+.+\s+every\s+day\b',
        r'\bdaily\s+(?:habit|practice|routine)\b',
        r'\bweekly\s+(?:habit|practice|routine)\b',
        r'\bi\s+want\s+to\s+make\s+.+\s+a\s+habit\b',
        r'\bi\s+should\s+.+\s+every\s+(?:day|morning|evening|night)\b',
        r'\btrack\s+(?:my\s+)?(?:daily|weekly)\b',
        r'\bstart\s+(?:a\s+)?(?:daily|weekly)\s+\w+\s+habit\b',
    ]

    # Trigger phrases for calendar event extraction
    # Made flexible to match natural speech (allow text between keywords)
    CALENDAR_TRIGGERS = [
        # Any mention of adding to calendar (with up to 50 chars between)
        r'\b(?:add|put|schedule|book)\b.{0,50}\b(?:to|on|in)\s+(?:my\s+)?calendar\b',
        r'\b(?:to|on)\s+(?:my\s+)?calendar\b',  # "...to my calendar"
        # Appointment/meeting/event/workout with day/time
        r'\b(?:schedule|add|put|create|set\s+up|book)\b.{0,40}\b(?:appointment|meeting|event|workout|session|call)\b',
        r'\b(?:appointment|meeting|event|workout)\b.{0,30}\b(?:on|at|for)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)\b',
        # Day + time patterns
        r'\b(?:tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+\d',
        r'\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b',
        # Block time
        r'\bblock\s+(?:off\s+)?(?:time|my\s+calendar)\b',
        # Reminder style
        r'\bremind(?:er)?\b.{0,30}\b(?:at|on|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
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

    def should_extract_goals(self, message: str) -> bool:
        """Check if message might contain goal statements."""
        message_lower = message.lower()
        for pattern in self.GOAL_TRIGGERS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                logger.info(f"Goal trigger matched: '{pattern}'")
                return True
        return False

    def should_extract_habits(self, message: str) -> bool:
        """Check if message might contain habit statements."""
        message_lower = message.lower()
        for pattern in self.HABIT_TRIGGERS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        return False

    def should_extract_calendar_events(self, message: str) -> bool:
        """Check if message requests calendar event creation."""
        message_lower = message.lower()
        for pattern in self.CALENDAR_TRIGGERS:
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

    async def extract_goals(
        self,
        message: str,
        user_id: int,
        character_id: str,
        db: Session,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Extract goal statements from a message using LLM.

        Args:
            message: User message to extract from
            user_id: User ID for saving goals
            character_id: Character ID for context
            db: Database session
            conversation_context: Recent conversation messages for context

        Returns:
            List of created goal items
        """
        if not self.should_extract_goals(message):
            return []

        try:
            llm = self._get_llm_client()

            # Check if message references previous context (this, that, it)
            needs_context = self._references_context(message)

            # Build context string from recent messages
            context_str = ""
            if needs_context and conversation_context:
                recent_messages = [
                    f"- {msg.get('role', 'user')}: \"{msg.get('content', '')}\""
                    for msg in conversation_context[-6:]
                    if msg.get('content') and msg.get('content') != message
                ]
                if recent_messages:
                    context_str = "\n\nPREVIOUS CONVERSATION (extract the goal from this context):\n" + "\n".join(recent_messages)

            if needs_context and context_str:
                extraction_prompt = f"""The user said: "{message}"

This means they want to create a goal based on something mentioned in the previous conversation.
{context_str}

Extract the ACTUAL GOAL from the context above. Do NOT extract "this", "that", "it" - extract the specific goal they discussed.

Return a JSON array of goals. Example:
[{{"title": "Write a short essay every day for 10 days", "description": "Daily writing practice", "target_value": 10, "unit": "days", "category": "personal", "priority": 2, "goal_type": "completion"}}]

Rules:
- title: Clear, actionable goal statement (required)
- description: Brief explanation (optional)
- target_value: Numeric target if mentioned (optional)
- unit: Unit of measurement (optional)
- goal_type: "completion" for daily/repeated tasks (X days, X times), "numeric" for measurable amounts ($, lbs, miles)
- category: health, career, finance, personal, education, relationships (optional)
- priority: 1=high, 2=medium, 3=low (default 2)
- If no goals found, return []

Return ONLY the JSON array, nothing else."""
            else:
                extraction_prompt = f"""Extract goal information from this message:
"{message}"

Return a JSON array of goals. Example for numeric goal:
[{{"title": "Save $5000 for vacation", "target_value": 5000, "unit": "$", "category": "finance", "goal_type": "numeric"}}]

Example for completion goal (daily tasks):
[{{"title": "Write daily for 10 days", "target_value": 10, "unit": "days", "category": "personal", "goal_type": "completion"}}]

Rules:
- title: Clear, actionable goal statement (required)
- description: Brief explanation (optional)
- target_value: Numeric target if mentioned (optional)
- unit: Unit of measurement ($, lbs, miles, days, times, etc.) (optional)
- goal_type: "completion" for daily/repeated tasks (X days, X times, every day for X), "numeric" for measurable amounts ($, lbs, miles)
- category: health, career, finance, personal, education, relationships (optional)
- priority: 1=high, 2=medium, 3=low (default 2)
- If no goals found, return []

Return ONLY the JSON array, nothing else."""

            response_text = llm.generate_response(
                messages=[{"role": "user", "content": extraction_prompt}],
                model="llama3.1:latest",
                temperature=0.1,
                max_tokens=500
            ).strip()

            goals_data = self._parse_json_array(response_text)

            if not goals_data:
                return []

            created_goals = []
            for goal_data in goals_data:
                if not goal_data.get('title'):
                    continue

                goal = tracking_service.create_goal(
                    user_id=user_id,
                    character_id=character_id,
                    title=goal_data['title'][:200],
                    description=goal_data.get('description'),
                    target_value=goal_data.get('target_value'),
                    unit=goal_data.get('unit'),
                    category=goal_data.get('category'),
                    priority=min(max(goal_data.get('priority', 2), 1), 3),
                    db=db
                )
                created_goals.append(goal)
                logger.info(f"Extracted goal: {goal_data['title'][:50]}...")

            return created_goals

        except Exception as e:
            logger.error(f"Error extracting goals: {str(e)}")
            return []

    async def extract_habits(
        self,
        message: str,
        user_id: int,
        character_id: str,
        db: Session,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Extract habit statements from a message using LLM.

        Args:
            message: User message to extract from
            user_id: User ID for saving habits
            character_id: Character ID for context
            db: Database session
            conversation_context: Recent conversation messages for context

        Returns:
            List of created habit items
        """
        if not self.should_extract_habits(message):
            return []

        try:
            llm = self._get_llm_client()

            extraction_prompt = f"""Extract habit information from this message:
"{message}"

Return a JSON array of habits. Example:
[{{"title": "Meditate for 10 minutes", "description": "Morning mindfulness practice", "frequency": "daily", "target_per_period": 1}}]

Rules:
- title: Clear, actionable habit name (required)
- description: Brief explanation (optional)
- frequency: "daily" or "weekly" (default "daily")
- frequency_days: For weekly, array like ["mon", "wed", "fri"] (optional)
- target_per_period: Times per day/week to do it (default 1)
- If no habits found, return []

Return ONLY the JSON array, nothing else."""

            response_text = llm.generate_response(
                messages=[{"role": "user", "content": extraction_prompt}],
                model="llama3.1:latest",
                temperature=0.1,
                max_tokens=500
            ).strip()

            habits_data = self._parse_json_array(response_text)

            if not habits_data:
                return []

            created_habits = []
            for habit_data in habits_data:
                if not habit_data.get('title'):
                    continue

                habit = tracking_service.create_habit(
                    user_id=user_id,
                    character_id=character_id,
                    title=habit_data['title'][:200],
                    description=habit_data.get('description'),
                    frequency=habit_data.get('frequency', 'daily'),
                    frequency_days=habit_data.get('frequency_days'),
                    target_per_period=habit_data.get('target_per_period', 1),
                    db=db
                )
                created_habits.append(habit)
                logger.info(f"Extracted habit: {habit_data['title'][:50]}...")

            return created_habits

        except Exception as e:
            logger.error(f"Error extracting habits: {str(e)}")
            return []

    async def extract_calendar_events(
        self,
        message: str,
        user_id: int,
        character_id: str,
        db: Session,
        conversation_context: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Extract and create calendar events from a message using LLM.

        Args:
            message: User message to extract from
            user_id: User ID for Google credentials
            character_id: Character ID for sync config check
            db: Database session
            conversation_context: Recent conversation messages for context

        Returns:
            List of created event info dicts
        """
        if not self.should_extract_calendar_events(message):
            logger.debug(f"No calendar trigger in message: {message[:50]}...")
            return []

        logger.info(f"Calendar trigger detected in message: {message[:100]}...")

        # Check if calendar is enabled for this persona
        from ...database.models import PersonaGoogleSyncConfig
        sync_config = db.query(PersonaGoogleSyncConfig).filter_by(
            user_id=user_id,
            character_id=character_id
        ).first()

        if not sync_config:
            logger.info(f"No sync config found for persona {character_id}")
            return []

        if not sync_config.calendar_sync_enabled:
            logger.info(f"Calendar not enabled for persona {character_id}")
            return []

        logger.info(f"Calendar enabled, proceeding with event extraction")

        try:
            from .google_calendar_service import google_calendar_service
            from .google_auth_service import google_auth_service
            from datetime import datetime, timedelta
            import dateparser

            llm = self._get_llm_client()

            # Get current date/time for context
            now = datetime.now()
            current_context = f"Today is {now.strftime('%A, %B %d, %Y')}. Current time is {now.strftime('%I:%M %p')}."

            extraction_prompt = f"""{current_context}

Extract calendar event information from this message:
"{message}"

Return a JSON object with event details. Example:
{{"title": "Meeting with John", "date": "2024-01-15", "time": "14:00", "duration_minutes": 60, "description": "Discuss project"}}

Rules:
- title: Event name (required)
- date: Date in YYYY-MM-DD format (required). Use today's date if "today", tomorrow if "tomorrow", etc.
- time: Time in 24h HH:MM format (required for timed events, omit for all-day)
- duration_minutes: Length in minutes (default 60)
- description: Brief note (optional)
- all_day: true for all-day events (optional)
- If message doesn't specify a calendar event, return {{}}

Return ONLY the JSON object, nothing else."""

            response_text = llm.generate_response(
                messages=[{"role": "user", "content": extraction_prompt}],
                model="llama3.1:latest",
                temperature=0.1,
                max_tokens=300
            ).strip()

            logger.info(f"LLM extraction response: {response_text[:200]}...")

            # Parse JSON
            event_data = self._parse_json_object(response_text)
            logger.info(f"Parsed event data: {event_data}")

            if not event_data or not event_data.get('title') or not event_data.get('date'):
                logger.info("No valid calendar event extracted from message (missing title or date)")
                return []

            logger.info(f"Extracted event: {event_data.get('title')} on {event_data.get('date')} at {event_data.get('time')}")

            # Get Google credentials
            credentials = google_auth_service.get_credentials(user_id, db)
            if not credentials:
                logger.warning("No Google credentials for user, cannot create calendar event")
                return []

            logger.info("Got Google credentials, creating event...")

            # Parse date and time
            try:
                event_date = datetime.strptime(event_data['date'], '%Y-%m-%d')
            except ValueError:
                # Try dateparser as fallback
                parsed = dateparser.parse(event_data['date'])
                if parsed:
                    event_date = parsed
                else:
                    logger.warning(f"Could not parse date: {event_data['date']}")
                    return []

            # Determine start/end times
            all_day = event_data.get('all_day', False)
            if event_data.get('time') and not all_day:
                try:
                    time_parts = event_data['time'].split(':')
                    start_time = event_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
                except (ValueError, IndexError):
                    start_time = event_date.replace(hour=12, minute=0)
            else:
                start_time = event_date
                all_day = True

            duration = event_data.get('duration_minutes', 60)
            end_time = start_time + timedelta(minutes=duration)

            # Create the event
            created_event = google_calendar_service.create_event(
                credentials=credentials,
                summary=event_data['title'],
                description=event_data.get('description'),
                start_time=start_time,
                end_time=end_time,
                all_day=all_day
            )

            logger.info(f"Created calendar event: {event_data['title']}")
            return [created_event]

        except Exception as e:
            logger.error(f"Error extracting/creating calendar event: {str(e)}")
            return []

    def _parse_json_object(self, text: str) -> Optional[Dict]:
        """Parse JSON object from text, handling markdown code blocks."""
        import json
        # Try direct parse first
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON in code blocks
        import re
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            try:
                data = json.loads(code_block_match.group(1))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        # Try to find JSON object pattern
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        return None

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
            'life_areas': [],
            'goals': [],
            'habits': [],
            'calendar_events': []
        }

        logger.info(f"Processing message for extractions. Category: {category}")

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

        # Extract goals and habits for Coach and Assistant categories
        if category and category.lower() in ('coach', 'assistant'):
            extractions['goals'] = await self.extract_goals(
                message, user_id, character_id, db, conversation_context
            )
            extractions['habits'] = await self.extract_habits(
                message, user_id, character_id, db, conversation_context
            )

        # Extract calendar events for any category if calendar is enabled for persona
        # (The extract_calendar_events method checks calendar_sync_enabled internally)
        extractions['calendar_events'] = await self.extract_calendar_events(
            message, user_id, character_id, db, conversation_context
        )

        return extractions


# Global service instance
sidebar_extraction_service = SidebarExtractionService()
