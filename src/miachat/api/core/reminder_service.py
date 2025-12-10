"""
Reminder and time awareness service for personas.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pytz
from sqlalchemy.orm import Session

from ...database.models import Reminder, PersonaTimeContext, User
from ...database.config import get_db

logger = logging.getLogger(__name__)

class ReminderService:
    """Service for managing persona reminders and time awareness."""

    def __init__(self):
        pass

    def create_reminder(
        self,
        db: Session,
        user_id: int,
        persona_name: str,
        title: str,
        reminder_time: datetime,
        description: str = None,
        is_recurring: bool = False,
        recurrence_pattern: str = None,
        recurrence_interval: int = 1,
        recurrence_days: str = None,
        context_type: str = None,
        context_data: Dict[str, Any] = None
    ) -> Optional[Reminder]:
        """Create a new reminder."""
        try:
            reminder = Reminder(
                user_id=user_id,
                persona_name=persona_name,
                title=title,
                description=description,
                reminder_time=reminder_time,
                is_recurring=1 if is_recurring else 0,
                recurrence_pattern=recurrence_pattern,
                recurrence_interval=recurrence_interval,
                recurrence_days=recurrence_days,
                context_type=context_type,
                context_data=context_data or {}
            )

            db.add(reminder)
            db.commit()
            db.refresh(reminder)

            logger.info(f"Created reminder '{title}' for user {user_id} and persona {persona_name}")
            return reminder

        except Exception as e:
            logger.error(f"Error creating reminder: {str(e)}")
            db.rollback()
            return None

    def get_reminders(
        self,
        db: Session,
        user_id: int,
        persona_name: str = None,
        include_completed: bool = False,
        include_inactive: bool = False
    ) -> List[Reminder]:
        """Get reminders for a user and optionally a specific persona."""
        try:
            query = db.query(Reminder).filter(Reminder.user_id == user_id)

            if persona_name:
                query = query.filter(Reminder.persona_name == persona_name)

            if not include_completed:
                query = query.filter(Reminder.is_completed == 0)

            if not include_inactive:
                query = query.filter(Reminder.is_active == 1)

            return query.order_by(Reminder.reminder_time).all()

        except Exception as e:
            logger.error(f"Error getting reminders: {str(e)}")
            return []

    def get_due_reminders(
        self,
        db: Session,
        user_id: int,
        persona_name: str = None,
        check_time: datetime = None
    ) -> List[Reminder]:
        """Get reminders that are currently due."""
        if not check_time:
            check_time = datetime.utcnow()

        reminders = self.get_reminders(db, user_id, persona_name)
        return [r for r in reminders if r.is_due(check_time)]

    def get_upcoming_reminders(
        self,
        db: Session,
        user_id: int,
        persona_name: str = None,
        hours_ahead: int = 24
    ) -> List[Reminder]:
        """Get reminders due within the next N hours."""
        check_time = datetime.utcnow() + timedelta(hours=hours_ahead)

        try:
            query = db.query(Reminder).filter(
                Reminder.user_id == user_id,
                Reminder.reminder_time <= check_time,
                Reminder.reminder_time > datetime.utcnow(),
                Reminder.is_completed == 0,
                Reminder.is_active == 1
            )

            if persona_name:
                query = query.filter(Reminder.persona_name == persona_name)

            return query.order_by(Reminder.reminder_time).all()

        except Exception as e:
            logger.error(f"Error getting upcoming reminders: {str(e)}")
            return []

    def complete_reminder(self, db: Session, reminder_id: int, user_id: int) -> bool:
        """Mark a reminder as completed."""
        try:
            reminder = db.query(Reminder).filter(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id
            ).first()

            if not reminder:
                return False

            reminder.mark_completed()

            # If it's recurring, create the next occurrence
            if reminder.is_recurring and reminder.recurrence_pattern:
                self._create_next_recurrence(db, reminder)

            db.commit()
            return True

        except Exception as e:
            logger.error(f"Error completing reminder: {str(e)}")
            db.rollback()
            return False

    def _create_next_recurrence(self, db: Session, reminder: Reminder):
        """Create the next occurrence of a recurring reminder."""
        try:
            next_time = self._calculate_next_recurrence(
                reminder.reminder_time,
                reminder.recurrence_pattern,
                reminder.recurrence_interval,
                reminder.recurrence_days
            )

            if next_time:
                new_reminder = Reminder(
                    user_id=reminder.user_id,
                    persona_name=reminder.persona_name,
                    title=reminder.title,
                    description=reminder.description,
                    reminder_time=next_time,
                    is_recurring=reminder.is_recurring,
                    recurrence_pattern=reminder.recurrence_pattern,
                    recurrence_interval=reminder.recurrence_interval,
                    recurrence_days=reminder.recurrence_days,
                    context_type=reminder.context_type,
                    context_data=reminder.context_data
                )

                db.add(new_reminder)

        except Exception as e:
            logger.error(f"Error creating next recurrence: {str(e)}")

    def _calculate_next_recurrence(
        self,
        current_time: datetime,
        pattern: str,
        interval: int,
        days: str = None
    ) -> Optional[datetime]:
        """Calculate the next occurrence time for a recurring reminder."""
        try:
            if pattern == 'daily':
                return current_time + timedelta(days=interval)
            elif pattern == 'weekly':
                return current_time + timedelta(weeks=interval)
            elif pattern == 'monthly':
                # Simple monthly addition - may need more sophisticated logic
                month = current_time.month
                year = current_time.year
                month += interval
                while month > 12:
                    month -= 12
                    year += 1
                return current_time.replace(year=year, month=month)
            elif pattern == 'yearly':
                return current_time.replace(year=current_time.year + interval)

            return None

        except Exception as e:
            logger.error(f"Error calculating next recurrence: {str(e)}")
            return None

    def create_persona_time_context(
        self,
        db: Session,
        user_id: int,
        persona_name: str,
        timezone: str = 'UTC',
        date_format: str = '%Y-%m-%d',
        time_format: str = '%H:%M:%S',
        work_schedule: Dict[str, Any] = None,
        important_dates: Dict[str, Any] = None
    ) -> Optional[PersonaTimeContext]:
        """Create or update time context for a persona."""
        try:
            # Check if context already exists
            existing = db.query(PersonaTimeContext).filter(
                PersonaTimeContext.user_id == user_id,
                PersonaTimeContext.persona_name == persona_name
            ).first()

            if existing:
                # Update existing
                existing.timezone = timezone
                existing.date_format = date_format
                existing.time_format = time_format
                existing.work_schedule = work_schedule or {}
                existing.important_dates = important_dates or {}
                existing.updated_at = datetime.utcnow()

                db.commit()
                db.refresh(existing)
                return existing
            else:
                # Create new
                context = PersonaTimeContext(
                    user_id=user_id,
                    persona_name=persona_name,
                    timezone=timezone,
                    date_format=date_format,
                    time_format=time_format,
                    work_schedule=work_schedule or {},
                    important_dates=important_dates or {}
                )

                db.add(context)
                db.commit()
                db.refresh(context)
                return context

        except Exception as e:
            logger.error(f"Error creating persona time context: {str(e)}")
            db.rollback()
            return None

    def get_persona_time_context(
        self,
        db: Session,
        user_id: int,
        persona_name: str
    ) -> Optional[PersonaTimeContext]:
        """Get time context for a persona."""
        try:
            return db.query(PersonaTimeContext).filter(
                PersonaTimeContext.user_id == user_id,
                PersonaTimeContext.persona_name == persona_name
            ).first()

        except Exception as e:
            logger.error(f"Error getting persona time context: {str(e)}")
            return None

    def get_current_time_info(
        self,
        db: Session,
        user_id: int,
        persona_name: str
    ) -> Dict[str, Any]:
        """Get current time information formatted for the persona."""
        try:
            context = self.get_persona_time_context(db, user_id, persona_name)

            if context:
                tz = pytz.timezone(context.timezone)
                current_time = datetime.now(tz)

                return {
                    'current_time': current_time.strftime(context.time_format),
                    'current_date': current_time.strftime(context.date_format),
                    'timezone': context.timezone,
                    'day_of_week': current_time.strftime('%A'),
                    'month': current_time.strftime('%B'),
                    'year': current_time.year,
                    'is_weekend': current_time.weekday() >= 5,
                    'availability_status': context.availability_status
                }
            else:
                # Default UTC time
                current_time = datetime.utcnow()
                return {
                    'current_time': current_time.strftime('%H:%M:%S'),
                    'current_date': current_time.strftime('%Y-%m-%d'),
                    'timezone': 'UTC',
                    'day_of_week': current_time.strftime('%A'),
                    'month': current_time.strftime('%B'),
                    'year': current_time.year,
                    'is_weekend': current_time.weekday() >= 5,
                    'availability_status': 'available'
                }

        except Exception as e:
            logger.error(f"Error getting current time info: {str(e)}")
            return {}

    def get_context_for_chat(
        self,
        db: Session,
        user_id: int,
        persona_name: str
    ) -> str:
        """Get time-aware context string for chat conversations."""
        try:
            time_info = self.get_current_time_info(db, user_id, persona_name)
            due_reminders = self.get_due_reminders(db, user_id, persona_name)
            upcoming_reminders = self.get_upcoming_reminders(db, user_id, persona_name, hours_ahead=2)

            context_parts = []

            # Current time info
            if time_info:
                context_parts.append(
                    f"Current time: {time_info['current_time']} on {time_info['current_date']} "
                    f"({time_info['day_of_week']}) in {time_info['timezone']} timezone. "
                    f"Status: {time_info['availability_status']}"
                )

            # Due reminders
            if due_reminders:
                context_parts.append("URGENT REMINDERS DUE NOW:")
                for reminder in due_reminders:
                    context_parts.append(f"- {reminder.title}: {reminder.description or 'No details'}")

            # Upcoming reminders
            if upcoming_reminders:
                context_parts.append("Upcoming reminders (next 2 hours):")
                for reminder in upcoming_reminders:
                    time_str = reminder.reminder_time.strftime('%H:%M')
                    context_parts.append(f"- {time_str}: {reminder.title}")

            return "\n".join(context_parts) if context_parts else ""

        except Exception as e:
            logger.error(f"Error getting context for chat: {str(e)}")
            return ""

    def delete_reminder(self, db: Session, reminder_id: int, user_id: int) -> bool:
        """Delete a reminder."""
        try:
            reminder = db.query(Reminder).filter(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id
            ).first()

            if not reminder:
                return False

            db.delete(reminder)
            db.commit()
            return True

        except Exception as e:
            logger.error(f"Error deleting reminder: {str(e)}")
            db.rollback()
            return False

# Create a global instance
reminder_service = ReminderService()