"""
Google Calendar routes.

Endpoints for accessing Google Calendar:
- GET /api/google/calendar/events - Get upcoming events
- POST /api/google/calendar/events - Create event
- GET /api/google/calendar/calendars - List available calendars
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from miachat.database.config import get_db
from miachat.api.core.clerk_auth import get_current_user_from_session
from miachat.api.core.google_auth_service import google_auth_service
from miachat.api.core.google_calendar_service import google_calendar_service
from miachat.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google/calendar", tags=["google-calendar"])


class CreateEventRequest(BaseModel):
    """Request body for creating a calendar event."""
    summary: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: bool = False
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    calendar_id: str = 'primary'


@router.get("/calendars")
async def list_calendars(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """List all calendars the user has access to.

    Returns list of calendars with their IDs and names.
    """
    credentials = google_auth_service.get_credentials(user.id, db)
    if not credentials:
        raise HTTPException(
            status_code=400,
            detail="Google account not connected"
        )

    try:
        calendars = google_calendar_service.list_calendars(credentials)
        return {'calendars': calendars}
    except Exception as e:
        logger.error(f"Failed to list calendars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_upcoming_events(
    request: Request,
    days_ahead: int = Query(default=7, ge=1, le=30),
    max_results: int = Query(default=50, ge=1, le=100),
    calendar_id: str = Query(default='primary'),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Get upcoming calendar events.

    Args:
        days_ahead: Number of days to look ahead (1-30)
        max_results: Maximum number of events (1-100)
        calendar_id: Calendar ID ('primary' for main calendar)

    Returns:
        List of upcoming events
    """
    credentials = google_auth_service.get_credentials(user.id, db)
    if not credentials:
        raise HTTPException(
            status_code=400,
            detail="Google account not connected"
        )

    try:
        events = google_calendar_service.get_upcoming_events(
            credentials=credentials,
            calendar_id=calendar_id,
            days_ahead=days_ahead,
            max_results=max_results
        )
        return {'events': events, 'count': len(events)}
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events")
async def create_event(
    event_data: CreateEventRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Create a new calendar event.

    The persona can use this to schedule events based on conversation.
    """
    credentials = google_auth_service.get_credentials(user.id, db)
    if not credentials:
        raise HTTPException(
            status_code=400,
            detail="Google account not connected"
        )

    try:
        event = google_calendar_service.create_event(
            credentials=credentials,
            calendar_id=event_data.calendar_id,
            summary=event_data.summary,
            description=event_data.description,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            all_day=event_data.all_day,
            location=event_data.location,
            attendees=event_data.attendees
        )
        return {
            'success': True,
            'event': event
        }
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_calendar_context(
    request: Request,
    days_ahead: int = Query(default=7, ge=1, le=14),
    max_events: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Get calendar context for chat.

    Returns formatted calendar events for injection into chat context.
    """
    context = google_calendar_service.get_calendar_context(
        user_id=user.id,
        db=db,
        days_ahead=days_ahead,
        max_events=max_events
    )

    if context is None:
        return {
            'connected': False,
            'context': None
        }

    return {
        'connected': True,
        'context': context
    }
