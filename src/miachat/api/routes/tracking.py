"""
Tracking routes for goals, todos, and habits.

Provides REST API endpoints for per-persona tracking features.
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from miachat.database.config import get_db
from ..core.clerk_auth import get_current_user_from_session
from ..core.tracking_service import tracking_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


# ==================== PYDANTIC MODELS ====================

class GoalCreate(BaseModel):
    character_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    target_date: Optional[datetime] = None
    priority: int = 2


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    target_date: Optional[datetime] = None
    priority: Optional[int] = None
    status: Optional[str] = None


class GoalProgress(BaseModel):
    value_change: float
    note: Optional[str] = None


class TodoCreate(BaseModel):
    character_id: str
    text: str
    priority: int = 2
    due_date: Optional[datetime] = None
    parent_goal_id: Optional[int] = None


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None
    sort_order: Optional[int] = None
    parent_goal_id: Optional[int] = None


class HabitCreate(BaseModel):
    character_id: str
    title: str
    description: Optional[str] = None
    frequency: str = "daily"
    frequency_days: Optional[List[str]] = None
    target_per_period: int = 1


class HabitUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    frequency_days: Optional[List[str]] = None
    target_per_period: Optional[int] = None
    is_active: Optional[bool] = None


class HabitComplete(BaseModel):
    note: Optional[str] = None


# ==================== GOALS ENDPOINTS ====================

@router.get("/goals")
async def get_goals(
    character_id: str,
    status: Optional[str] = None,
    include_completed: bool = False,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get all goals for a character."""
    goals = tracking_service.get_goals(
        user_id=user.id,
        character_id=character_id,
        db=db,
        status=status,
        include_completed=include_completed
    )
    return {"goals": goals}


@router.get("/goals/{goal_id}")
async def get_goal(
    goal_id: int,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get a single goal by ID."""
    goal = tracking_service.get_goal(goal_id, user.id, db)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.post("/goals")
async def create_goal(
    data: GoalCreate,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Create a new goal."""
    goal = tracking_service.create_goal(
        user_id=user.id,
        character_id=data.character_id,
        title=data.title,
        db=db,
        description=data.description,
        category=data.category,
        target_value=data.target_value,
        unit=data.unit,
        target_date=data.target_date,
        priority=data.priority
    )
    return goal


@router.put("/goals/{goal_id}")
async def update_goal(
    goal_id: int,
    data: GoalUpdate,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Update a goal."""
    goal = tracking_service.update_goal(
        goal_id=goal_id,
        user_id=user.id,
        db=db,
        **data.model_dump(exclude_none=True)
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.post("/goals/{goal_id}/progress")
async def log_goal_progress(
    goal_id: int,
    data: GoalProgress,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Log progress on a goal."""
    goal = tracking_service.log_goal_progress(
        goal_id=goal_id,
        user_id=user.id,
        value_change=data.value_change,
        db=db,
        note=data.note
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.get("/goals/{goal_id}/history")
async def get_goal_history(
    goal_id: int,
    limit: int = 30,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get progress history for a goal."""
    history = tracking_service.get_goal_progress_history(
        goal_id=goal_id,
        user_id=user.id,
        db=db,
        limit=limit
    )
    return {"history": history}


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: int,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Delete a goal."""
    success = tracking_service.delete_goal(goal_id, user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True}


# ==================== TODOS ENDPOINTS ====================

@router.get("/todos")
async def get_todos(
    character_id: str,
    include_completed: bool = False,
    goal_id: Optional[int] = None,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get all todos for a character."""
    todos = tracking_service.get_todos(
        user_id=user.id,
        character_id=character_id,
        db=db,
        include_completed=include_completed,
        goal_id=goal_id
    )
    return {"todos": todos}


@router.post("/todos")
async def create_todo(
    data: TodoCreate,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Create a new todo."""
    todo = tracking_service.create_todo(
        user_id=user.id,
        character_id=data.character_id,
        text=data.text,
        db=db,
        priority=data.priority,
        due_date=data.due_date,
        parent_goal_id=data.parent_goal_id
    )
    return todo


@router.put("/todos/{todo_id}")
async def update_todo(
    todo_id: int,
    data: TodoUpdate,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Update a todo."""
    todo = tracking_service.update_todo(
        todo_id=todo_id,
        user_id=user.id,
        db=db,
        **data.model_dump(exclude_none=True)
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.post("/todos/{todo_id}/toggle")
async def toggle_todo(
    todo_id: int,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Toggle a todo's completion status."""
    todo = tracking_service.toggle_todo(todo_id, user.id, db)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.delete("/todos/{todo_id}")
async def delete_todo(
    todo_id: int,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Delete a todo."""
    success = tracking_service.delete_todo(todo_id, user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"success": True}


# ==================== HABITS ENDPOINTS ====================

@router.get("/habits")
async def get_habits(
    character_id: str,
    active_only: bool = True,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get all habits for a character."""
    habits = tracking_service.get_habits(
        user_id=user.id,
        character_id=character_id,
        db=db,
        active_only=active_only
    )
    return {"habits": habits}


@router.get("/habits/{habit_id}")
async def get_habit(
    habit_id: int,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get a single habit by ID."""
    habit = tracking_service.get_habit(habit_id, user.id, db)
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.post("/habits")
async def create_habit(
    data: HabitCreate,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Create a new habit."""
    habit = tracking_service.create_habit(
        user_id=user.id,
        character_id=data.character_id,
        title=data.title,
        db=db,
        description=data.description,
        frequency=data.frequency,
        frequency_days=data.frequency_days,
        target_per_period=data.target_per_period
    )
    return habit


@router.put("/habits/{habit_id}")
async def update_habit(
    habit_id: int,
    data: HabitUpdate,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Update a habit."""
    update_data = data.model_dump(exclude_none=True)
    # Convert is_active bool to int for database
    if 'is_active' in update_data:
        update_data['is_active'] = 1 if update_data['is_active'] else 0

    habit = tracking_service.update_habit(
        habit_id=habit_id,
        user_id=user.id,
        db=db,
        **update_data
    )
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.post("/habits/{habit_id}/complete")
async def complete_habit(
    habit_id: int,
    data: HabitComplete = HabitComplete(),
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Mark a habit as completed for today."""
    habit = tracking_service.complete_habit(
        habit_id=habit_id,
        user_id=user.id,
        db=db,
        note=data.note
    )
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.get("/habits/{habit_id}/stats")
async def get_habit_stats(
    habit_id: int,
    days: int = 30,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get completion stats for a habit."""
    stats = tracking_service.get_habit_stats(
        habit_id=habit_id,
        user_id=user.id,
        db=db,
        days=days
    )
    if not stats:
        raise HTTPException(status_code=404, detail="Habit not found")
    return stats


@router.delete("/habits/{habit_id}")
async def delete_habit(
    habit_id: int,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Delete a habit."""
    success = tracking_service.delete_habit(habit_id, user.id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Habit not found")
    return {"success": True}


# ==================== SUMMARY ENDPOINT ====================

@router.get("/summary")
async def get_tracking_summary(
    character_id: str,
    user: dict = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    """Get tracking summary for sidebar badges."""
    summary = tracking_service.get_tracking_summary(
        user_id=user.id,
        character_id=character_id,
        db=db
    )
    return summary
