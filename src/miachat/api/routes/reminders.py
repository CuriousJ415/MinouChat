"""
API routes for reminder management.
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.reminder_service import reminder_service
from ..core.clerk_auth import get_current_user_from_session
from ...database.config import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Request models
class CreateReminderRequest(BaseModel):
    persona_name: str
    title: str
    description: Optional[str] = None
    reminder_time: str  # ISO format datetime string
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, monthly, yearly
    recurrence_interval: int = 1
    recurrence_days: Optional[str] = None  # For weekly: "mon,tue,wed"
    context_type: Optional[str] = None
    context_data: Optional[dict] = None

class UpdateReminderRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reminder_time: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    recurrence_interval: Optional[int] = None
    recurrence_days: Optional[str] = None
    context_type: Optional[str] = None
    context_data: Optional[dict] = None

class TimeContextRequest(BaseModel):
    persona_name: str
    timezone: str = 'UTC'
    date_format: str = '%Y-%m-%d'
    time_format: str = '%H:%M:%S'
    work_schedule: Optional[dict] = None
    important_dates: Optional[dict] = None

class ReminderResponse(BaseModel):
    id: int
    user_id: int
    persona_name: str
    title: str
    description: Optional[str]
    reminder_time: str
    is_recurring: bool
    recurrence_pattern: Optional[str]
    recurrence_interval: int
    recurrence_days: Optional[str]
    is_completed: bool
    is_active: bool
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    context_type: Optional[str]
    context_data: Optional[dict]

@router.post("/create", response_model=ReminderResponse)
async def create_reminder(
    request: CreateReminderRequest,
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """Create a new reminder."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request_obj, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Parse datetime
        try:
            reminder_time = datetime.fromisoformat(request.reminder_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format")

        # Create reminder
        reminder = reminder_service.create_reminder(
            db=db,
            user_id=current_user.id,
            persona_name=request.persona_name,
            title=request.title,
            reminder_time=reminder_time,
            description=request.description,
            is_recurring=request.is_recurring,
            recurrence_pattern=request.recurrence_pattern,
            recurrence_interval=request.recurrence_interval,
            recurrence_days=request.recurrence_days,
            context_type=request.context_type,
            context_data=request.context_data
        )

        if not reminder:
            raise HTTPException(status_code=500, detail="Failed to create reminder")

        return ReminderResponse(**reminder.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create reminder")

@router.get("/list")
async def list_reminders(
    request: Request,
    persona_name: Optional[str] = None,
    include_completed: bool = False,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """List reminders for the current user."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        reminders = reminder_service.get_reminders(
            db=db,
            user_id=current_user.id,
            persona_name=persona_name,
            include_completed=include_completed,
            include_inactive=include_inactive
        )

        return {
            "reminders": [reminder.to_dict() for reminder in reminders]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing reminders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list reminders")

@router.get("/due")
async def get_due_reminders(
    request: Request,
    persona_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get reminders that are currently due."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        reminders = reminder_service.get_due_reminders(
            db=db,
            user_id=current_user.id,
            persona_name=persona_name
        )

        return {
            "reminders": [reminder.to_dict() for reminder in reminders]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting due reminders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get due reminders")

@router.get("/upcoming")
async def get_upcoming_reminders(
    request: Request,
    persona_name: Optional[str] = None,
    hours_ahead: int = 24,
    db: Session = Depends(get_db)
):
    """Get upcoming reminders within the specified time window."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        reminders = reminder_service.get_upcoming_reminders(
            db=db,
            user_id=current_user.id,
            persona_name=persona_name,
            hours_ahead=hours_ahead
        )

        return {
            "reminders": [reminder.to_dict() for reminder in reminders]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upcoming reminders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get upcoming reminders")

@router.post("/{reminder_id}/complete")
async def complete_reminder(
    reminder_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Mark a reminder as completed."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        success = reminder_service.complete_reminder(
            db=db,
            reminder_id=reminder_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Reminder not found")

        return {"message": "Reminder completed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing reminder: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to complete reminder")

@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a reminder."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        success = reminder_service.delete_reminder(
            db=db,
            reminder_id=reminder_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Reminder not found")

        return {"message": "Reminder deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reminder: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete reminder")

@router.post("/time-context", response_model=dict)
async def create_time_context(
    request: TimeContextRequest,
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """Create or update time context for a persona."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request_obj, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        context = reminder_service.create_persona_time_context(
            db=db,
            user_id=current_user.id,
            persona_name=request.persona_name,
            timezone=request.timezone,
            date_format=request.date_format,
            time_format=request.time_format,
            work_schedule=request.work_schedule,
            important_dates=request.important_dates
        )

        if not context:
            raise HTTPException(status_code=500, detail="Failed to create time context")

        return context.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating time context: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create time context")

@router.get("/time-context/{persona_name}")
async def get_time_context(
    persona_name: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get time context for a persona."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        context = reminder_service.get_persona_time_context(
            db=db,
            user_id=current_user.id,
            persona_name=persona_name
        )

        if not context:
            raise HTTPException(status_code=404, detail="Time context not found")

        return context.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time context: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get time context")

@router.get("/time-info/{persona_name}")
async def get_current_time_info(
    persona_name: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current time information for a persona."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        time_info = reminder_service.get_current_time_info(
            db=db,
            user_id=current_user.id,
            persona_name=persona_name
        )

        return time_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get time info")

@router.get("/context/{persona_name}")
async def get_chat_context(
    persona_name: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get time-aware context for chat conversations."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        context = reminder_service.get_context_for_chat(
            db=db,
            user_id=current_user.id,
            persona_name=persona_name
        )

        return {
            "context": context,
            "has_context": bool(context.strip())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat context: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get chat context")