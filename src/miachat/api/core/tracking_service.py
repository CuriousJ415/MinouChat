"""
Tracking Service for goals, todos, and habits.

This service manages per-persona tracking features including:
- Goals with progress tracking
- Todo items with completion status
- Habits with streak tracking
- Google Tasks sync integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from miachat.database.models import (
    PersonaGoal,
    GoalProgressLog,
    TodoItem,
    PersonaHabit,
    HabitCompletion,
)

logger = logging.getLogger(__name__)


def _sync_todo_to_google(todo: TodoItem, action: str, db: Session):
    """Helper to sync todo changes to Google Tasks (if enabled).

    Uses lazy import to avoid circular dependency.
    """
    try:
        from miachat.api.core.google_sync_service import google_sync_service

        if action == 'create':
            google_sync_service.sync_todo_create(todo, db)
        elif action == 'update':
            google_sync_service.sync_todo_update(todo, db)
        elif action == 'toggle':
            google_sync_service.sync_todo_toggle(todo, db)
    except Exception as e:
        # Don't fail the local operation if sync fails
        logger.warning(f"Google sync failed for todo {action}: {e}")


class TrackingService:
    """Service for managing goals, todos, and habits."""

    # ==================== GOALS ====================

    def get_goals(
        self,
        user_id: int,
        character_id: str,
        db: Session,
        status: Optional[str] = None,
        include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all goals for a user+character."""
        query = db.query(PersonaGoal).filter(
            PersonaGoal.user_id == user_id,
            PersonaGoal.character_id == character_id
        )

        if status:
            query = query.filter(PersonaGoal.status == status)
        elif not include_completed:
            query = query.filter(PersonaGoal.status != 'completed')

        goals = query.order_by(PersonaGoal.priority, PersonaGoal.created_at.desc()).all()
        return [g.to_dict() for g in goals]

    def get_goal(self, goal_id: int, user_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Get a single goal by ID."""
        goal = db.query(PersonaGoal).filter(
            PersonaGoal.id == goal_id,
            PersonaGoal.user_id == user_id
        ).first()
        return goal.to_dict() if goal else None

    def create_goal(
        self,
        user_id: int,
        character_id: str,
        title: str,
        db: Session,
        description: Optional[str] = None,
        category: Optional[str] = None,
        target_value: Optional[float] = None,
        unit: Optional[str] = None,
        target_date: Optional[datetime] = None,
        priority: int = 2
    ) -> Dict[str, Any]:
        """Create a new goal."""
        goal = PersonaGoal(
            user_id=user_id,
            character_id=character_id,
            title=title,
            description=description,
            category=category,
            target_value=target_value,
            current_value=0,
            unit=unit,
            target_date=target_date,
            priority=priority,
            status='active'
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        logger.info(f"Created goal '{title}' for user {user_id}, character {character_id}")
        return goal.to_dict()

    def update_goal(
        self,
        goal_id: int,
        user_id: int,
        db: Session,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Update a goal's properties."""
        goal = db.query(PersonaGoal).filter(
            PersonaGoal.id == goal_id,
            PersonaGoal.user_id == user_id
        ).first()

        if not goal:
            return None

        allowed_fields = ['title', 'description', 'category', 'target_value', 'unit',
                          'target_date', 'priority', 'status']
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(goal, field, value)

        # Auto-complete if status changed to completed
        if kwargs.get('status') == 'completed' and not goal.completed_at:
            goal.mark_completed()

        db.commit()
        db.refresh(goal)
        return goal.to_dict()

    def log_goal_progress(
        self,
        goal_id: int,
        user_id: int,
        value_change: float,
        db: Session,
        note: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Log progress on a goal."""
        goal = db.query(PersonaGoal).filter(
            PersonaGoal.id == goal_id,
            PersonaGoal.user_id == user_id
        ).first()

        if not goal:
            return None

        # Update current value
        new_value = goal.current_value + value_change
        goal.current_value = max(0, new_value)  # Don't go negative

        # Create log entry
        log = GoalProgressLog(
            goal_id=goal_id,
            value_change=value_change,
            new_value=goal.current_value,
            note=note
        )
        db.add(log)

        # Check if goal is now complete
        if goal.target_value and goal.current_value >= goal.target_value:
            goal.mark_completed()

        db.commit()
        db.refresh(goal)
        logger.info(f"Logged progress on goal {goal_id}: {value_change:+.2f} -> {goal.current_value}")
        return goal.to_dict()

    def get_goal_progress_history(
        self,
        goal_id: int,
        user_id: int,
        db: Session,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get progress history for a goal."""
        # Verify ownership
        goal = db.query(PersonaGoal).filter(
            PersonaGoal.id == goal_id,
            PersonaGoal.user_id == user_id
        ).first()

        if not goal:
            return []

        logs = db.query(GoalProgressLog).filter(
            GoalProgressLog.goal_id == goal_id
        ).order_by(GoalProgressLog.logged_at.desc()).limit(limit).all()

        return [log.to_dict() for log in logs]

    def delete_goal(self, goal_id: int, user_id: int, db: Session) -> bool:
        """Delete a goal and its progress logs."""
        goal = db.query(PersonaGoal).filter(
            PersonaGoal.id == goal_id,
            PersonaGoal.user_id == user_id
        ).first()

        if not goal:
            return False

        db.delete(goal)
        db.commit()
        logger.info(f"Deleted goal {goal_id}")
        return True

    # ==================== TODOS ====================

    def get_todos(
        self,
        user_id: int,
        character_id: str,
        db: Session,
        include_completed: bool = False,
        goal_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all todos for a user+character."""
        query = db.query(TodoItem).filter(
            TodoItem.user_id == user_id,
            TodoItem.character_id == character_id
        )

        if not include_completed:
            query = query.filter(TodoItem.is_completed == 0)

        if goal_id is not None:
            query = query.filter(TodoItem.parent_goal_id == goal_id)

        todos = query.order_by(TodoItem.sort_order, TodoItem.priority, TodoItem.created_at).all()
        return [t.to_dict() for t in todos]

    def create_todo(
        self,
        user_id: int,
        character_id: str,
        text: str,
        db: Session,
        priority: int = 2,
        due_date: Optional[datetime] = None,
        parent_goal_id: Optional[int] = None,
        source_type: str = 'manual'
    ) -> Dict[str, Any]:
        """Create a new todo item."""
        # Get max sort order for this character
        max_order = db.query(TodoItem).filter(
            TodoItem.user_id == user_id,
            TodoItem.character_id == character_id
        ).count()

        todo = TodoItem(
            user_id=user_id,
            character_id=character_id,
            text=text,
            priority=priority,
            due_date=due_date,
            parent_goal_id=parent_goal_id,
            source_type=source_type,
            sort_order=max_order
        )
        db.add(todo)
        db.commit()
        db.refresh(todo)
        logger.info(f"Created todo '{text[:50]}...' for user {user_id}")

        # Sync to Google Tasks (if enabled for this persona)
        _sync_todo_to_google(todo, 'create', db)

        return todo.to_dict()

    def update_todo(
        self,
        todo_id: int,
        user_id: int,
        db: Session,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Update a todo item."""
        todo = db.query(TodoItem).filter(
            TodoItem.id == todo_id,
            TodoItem.user_id == user_id
        ).first()

        if not todo:
            return None

        allowed_fields = ['text', 'priority', 'due_date', 'sort_order', 'parent_goal_id']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(todo, field, value)

        db.commit()
        db.refresh(todo)

        # Sync to Google Tasks (if enabled for this persona)
        _sync_todo_to_google(todo, 'update', db)

        return todo.to_dict()

    def toggle_todo(self, todo_id: int, user_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Toggle a todo's completion status."""
        todo = db.query(TodoItem).filter(
            TodoItem.id == todo_id,
            TodoItem.user_id == user_id
        ).first()

        if not todo:
            return None

        if todo.is_completed:
            todo.is_completed = 0
            todo.completed_at = None
        else:
            todo.is_completed = 1
            todo.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(todo)
        logger.info(f"Toggled todo {todo_id} to {'completed' if todo.is_completed else 'incomplete'}")

        # Sync to Google Tasks (if enabled for this persona)
        _sync_todo_to_google(todo, 'toggle', db)

        return todo.to_dict()

    def delete_todo(self, todo_id: int, user_id: int, db: Session) -> bool:
        """Delete a todo item."""
        todo = db.query(TodoItem).filter(
            TodoItem.id == todo_id,
            TodoItem.user_id == user_id
        ).first()

        if not todo:
            return False

        # Capture character_id for sync before deleting
        character_id = todo.character_id

        # Sync deletion to Google Tasks (if enabled for this persona)
        try:
            from miachat.api.core.google_sync_service import google_sync_service
            google_sync_service.sync_todo_delete(todo_id, user_id, character_id, db)
        except Exception as e:
            logger.warning(f"Google sync failed for todo delete: {e}")

        db.delete(todo)
        db.commit()
        logger.info(f"Deleted todo {todo_id}")
        return True

    # ==================== HABITS ====================

    def get_habits(
        self,
        user_id: int,
        character_id: str,
        db: Session,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all habits for a user+character."""
        query = db.query(PersonaHabit).filter(
            PersonaHabit.user_id == user_id,
            PersonaHabit.character_id == character_id
        )

        if active_only:
            query = query.filter(PersonaHabit.is_active == 1)

        habits = query.order_by(PersonaHabit.created_at).all()
        return [h.to_dict() for h in habits]

    def get_habit(self, habit_id: int, user_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Get a single habit by ID."""
        habit = db.query(PersonaHabit).filter(
            PersonaHabit.id == habit_id,
            PersonaHabit.user_id == user_id
        ).first()
        return habit.to_dict() if habit else None

    def create_habit(
        self,
        user_id: int,
        character_id: str,
        title: str,
        db: Session,
        description: Optional[str] = None,
        frequency: str = 'daily',
        frequency_days: Optional[List[str]] = None,
        target_per_period: int = 1
    ) -> Dict[str, Any]:
        """Create a new habit."""
        habit = PersonaHabit(
            user_id=user_id,
            character_id=character_id,
            title=title,
            description=description,
            frequency=frequency,
            frequency_days=frequency_days,
            target_per_period=target_per_period,
            current_streak=0,
            longest_streak=0,
            is_active=1
        )
        db.add(habit)
        db.commit()
        db.refresh(habit)
        logger.info(f"Created habit '{title}' for user {user_id}")
        return habit.to_dict()

    def update_habit(
        self,
        habit_id: int,
        user_id: int,
        db: Session,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Update a habit's properties."""
        habit = db.query(PersonaHabit).filter(
            PersonaHabit.id == habit_id,
            PersonaHabit.user_id == user_id
        ).first()

        if not habit:
            return None

        allowed_fields = ['title', 'description', 'frequency', 'frequency_days',
                          'target_per_period', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(habit, field, value)

        db.commit()
        db.refresh(habit)
        return habit.to_dict()

    def complete_habit(
        self,
        habit_id: int,
        user_id: int,
        db: Session,
        note: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Mark a habit as completed for today."""
        habit = db.query(PersonaHabit).filter(
            PersonaHabit.id == habit_id,
            PersonaHabit.user_id == user_id
        ).first()

        if not habit:
            return None

        now = datetime.utcnow()
        today = now.date()

        # Check if already completed today
        existing = db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit_id
        ).order_by(HabitCompletion.completed_at.desc()).first()

        if existing and existing.completed_at.date() == today:
            # Already completed today - still return success
            return habit.to_dict()

        # Create completion record
        completion = HabitCompletion(
            habit_id=habit_id,
            completed_at=now,
            note=note
        )
        db.add(completion)

        # Update streak
        if habit.last_completed_date:
            last_date = habit.last_completed_date.date()
            if last_date == today - timedelta(days=1):
                # Consecutive day - increment streak
                habit.current_streak += 1
            elif last_date != today:
                # Streak broken - reset to 1
                habit.current_streak = 1
        else:
            # First completion
            habit.current_streak = 1

        # Update longest streak
        if habit.current_streak > habit.longest_streak:
            habit.longest_streak = habit.current_streak

        habit.last_completed_date = now
        db.commit()
        db.refresh(habit)

        logger.info(f"Completed habit {habit_id}, streak: {habit.current_streak}")
        return habit.to_dict()

    def get_habit_stats(
        self,
        habit_id: int,
        user_id: int,
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get completion stats for a habit."""
        habit = db.query(PersonaHabit).filter(
            PersonaHabit.id == habit_id,
            PersonaHabit.user_id == user_id
        ).first()

        if not habit:
            return {}

        since = datetime.utcnow() - timedelta(days=days)
        completions = db.query(HabitCompletion).filter(
            HabitCompletion.habit_id == habit_id,
            HabitCompletion.completed_at >= since
        ).all()

        # Build completion dates set
        completion_dates = set(c.completed_at.date() for c in completions)

        # Calculate completion rate
        total_days = days
        completed_days = len(completion_dates)
        completion_rate = (completed_days / total_days) * 100 if total_days > 0 else 0

        return {
            'habit_id': habit_id,
            'current_streak': habit.current_streak,
            'longest_streak': habit.longest_streak,
            'days_analyzed': days,
            'completed_days': completed_days,
            'completion_rate': round(completion_rate, 1),
            'completion_dates': [d.isoformat() for d in sorted(completion_dates)]
        }

    def delete_habit(self, habit_id: int, user_id: int, db: Session) -> bool:
        """Delete a habit and its completions."""
        habit = db.query(PersonaHabit).filter(
            PersonaHabit.id == habit_id,
            PersonaHabit.user_id == user_id
        ).first()

        if not habit:
            return False

        db.delete(habit)
        db.commit()
        logger.info(f"Deleted habit {habit_id}")
        return True

    # ==================== SUMMARY ====================

    def get_tracking_summary(
        self,
        user_id: int,
        character_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Get a summary of tracking data for the sidebar badges."""
        # Count active goals
        active_goals = db.query(PersonaGoal).filter(
            PersonaGoal.user_id == user_id,
            PersonaGoal.character_id == character_id,
            PersonaGoal.status == 'active'
        ).count()

        # Count incomplete todos
        incomplete_todos = db.query(TodoItem).filter(
            TodoItem.user_id == user_id,
            TodoItem.character_id == character_id,
            TodoItem.is_completed == 0
        ).count()

        # Count active habits and how many completed today
        habits = db.query(PersonaHabit).filter(
            PersonaHabit.user_id == user_id,
            PersonaHabit.character_id == character_id,
            PersonaHabit.is_active == 1
        ).all()

        today = datetime.utcnow().date()
        habits_completed_today = sum(
            1 for h in habits
            if h.last_completed_date and h.last_completed_date.date() == today
        )

        return {
            'goals': {
                'active': active_goals
            },
            'todos': {
                'incomplete': incomplete_todos
            },
            'habits': {
                'total': len(habits),
                'completed_today': habits_completed_today
            }
        }

    def get_tracking_context(
        self,
        user_id: int,
        character_id: str,
        db: Session
    ) -> str:
        """Get tracking data formatted for LLM context injection."""
        goals = self.get_goals(user_id, character_id, db, include_completed=False)
        todos = self.get_todos(user_id, character_id, db, include_completed=False)
        habits = self.get_habits(user_id, character_id, db, active_only=True)

        if not goals and not todos and not habits:
            return ""

        context_parts = []

        if goals:
            context_parts.append("=== User's Active Goals ===")
            for g in goals[:5]:  # Limit to 5 most important
                progress = f" ({g['current_value']}/{g['target_value']} {g['unit']})" if g['target_value'] else ""
                due = f" - due {g['target_date'][:10]}" if g['target_date'] else ""
                context_parts.append(f"- {g['title']}{progress}{due}")

        if todos:
            context_parts.append("\n=== User's Active Todos ===")
            for t in todos[:8]:  # Limit to 8 items
                priority_icon = "❗" if t['priority'] == 1 else ""
                due = f" (due {t['due_date'][:10]})" if t['due_date'] else ""
                context_parts.append(f"- {priority_icon}{t['text']}{due}")

        if habits:
            context_parts.append("\n=== User's Habits ===")
            today = datetime.utcnow().date()
            for h in habits[:5]:  # Limit to 5 habits
                status = "✓" if h['completed_today'] else "○"
                streak = f" (streak: {h['current_streak']})" if h['current_streak'] > 0 else ""
                context_parts.append(f"{status} {h['title']}{streak}")

        return "\n".join(context_parts)


# Singleton instance
tracking_service = TrackingService()
