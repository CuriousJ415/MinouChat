"""
Google Tasks sync routes.

Endpoints for managing per-persona sync configuration:
- GET /api/google/tasks/sync-config/{character_id} - Get sync config
- PUT /api/google/tasks/sync-config/{character_id} - Enable/disable sync
- POST /api/google/tasks/sync/{character_id} - Manual sync trigger
- GET /api/google/tasks/sync-status/{character_id} - Get sync status
- GET /api/google/tasks/personas - Get all personas with sync status
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from miachat.database.config import get_db
from miachat.api.core.clerk_auth import get_current_user_from_session
from miachat.api.core.google_auth_service import google_auth_service
from miachat.api.core.google_sync_service import google_sync_service
from miachat.api.core.character_manager import character_manager
from miachat.database.models import User, PersonaGoogleSyncConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google/tasks", tags=["google-tasks"])


class SyncConfigUpdate(BaseModel):
    """Request body for updating sync configuration."""
    tasks_sync_enabled: bool = False
    calendar_sync_enabled: bool = False


@router.get("/sync-config/{character_id}")
async def get_sync_config(
    character_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Get the sync configuration for a persona.

    Returns sync settings and status for the specified persona.
    """
    # Check if Google is connected
    google_status = google_auth_service.get_connection_status(user.id, db)
    if not google_status.get('connected'):
        return {
            'google_connected': False,
            'tasks_sync_enabled': False,
            'calendar_sync_enabled': False
        }

    config = google_sync_service.get_sync_config(user.id, character_id, db)

    if not config:
        return {
            'google_connected': True,
            'tasks_sync_enabled': False,
            'calendar_sync_enabled': False,
            'google_tasklist_id': None,
            'google_tasklist_name': None,
            'last_sync_at': None,
            'last_sync_status': 'never'
        }

    return {
        'google_connected': True,
        **config.to_dict()
    }


@router.put("/sync-config/{character_id}")
async def update_sync_config(
    character_id: str,
    config: SyncConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Enable or disable sync for a persona.

    When enabling tasks sync, creates a Google Tasks list for the persona.
    """
    # Check if Google is connected
    google_status = google_auth_service.get_connection_status(user.id, db)
    if not google_status.get('connected'):
        raise HTTPException(
            status_code=400,
            detail="Google account not connected. Connect your Google account first."
        )

    try:
        if config.tasks_sync_enabled or config.calendar_sync_enabled:
            # Enable sync
            sync_config = google_sync_service.enable_sync(
                user_id=user.id,
                character_id=character_id,
                db=db,
                tasks_enabled=config.tasks_sync_enabled,
                calendar_enabled=config.calendar_sync_enabled
            )

            # Trigger initial sync if tasks enabled
            if config.tasks_sync_enabled:
                google_sync_service.full_sync(user.id, character_id, db)

            return {
                'success': True,
                'message': 'Sync enabled',
                **sync_config.to_dict()
            }
        else:
            # Disable sync
            google_sync_service.disable_sync(
                user_id=user.id,
                character_id=character_id,
                db=db,
                delete_google_list=False  # Keep the list by default
            )
            return {
                'success': True,
                'message': 'Sync disabled'
            }

    except Exception as e:
        logger.error(f"Failed to update sync config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/{character_id}")
async def trigger_sync(
    character_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Manually trigger a full sync for a persona.

    Performs two-way sync between MinouChat todos and Google Tasks.
    """
    # Check if Google is connected
    google_status = google_auth_service.get_connection_status(user.id, db)
    if not google_status.get('connected'):
        raise HTTPException(
            status_code=400,
            detail="Google account not connected"
        )

    config = google_sync_service.get_sync_config(user.id, character_id, db)
    if not config or not config.tasks_sync_enabled:
        raise HTTPException(
            status_code=400,
            detail="Sync not enabled for this persona"
        )

    try:
        result = google_sync_service.full_sync(user.id, character_id, db)
        return {
            'success': True,
            **result
        }
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-status/{character_id}")
async def get_sync_status(
    character_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Get the last sync status for a persona."""
    config = google_sync_service.get_sync_config(user.id, character_id, db)

    if not config:
        return {
            'tasks_sync_enabled': False,
            'last_sync_at': None,
            'last_sync_status': 'never'
        }

    return {
        'tasks_sync_enabled': bool(config.tasks_sync_enabled),
        'last_sync_at': config.last_sync_at.isoformat() if config.last_sync_at else None,
        'last_sync_status': config.last_sync_status,
        'last_sync_error': config.last_sync_error
    }


@router.get("/personas")
async def get_personas_with_sync_status(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Get all personas with their sync status.

    Used for the settings page to show which personas have sync enabled.
    """
    # Check if Google is connected
    google_status = google_auth_service.get_connection_status(user.id, db)

    # Get all characters
    try:
        characters = character_manager.list_characters()
    except Exception as e:
        logger.error(f"Failed to list characters: {e}")
        characters = []

    # Get all sync configs for this user
    configs = db.query(PersonaGoogleSyncConfig).filter_by(user_id=user.id).all()
    configs_by_character = {c.character_id: c for c in configs}

    personas = []
    for char in characters:
        char_id = char.get('id')
        config = configs_by_character.get(char_id)

        personas.append({
            'id': char_id,
            'name': char.get('name', 'Unknown'),
            'category': char.get('category', 'Other'),
            'avatar_url': char.get('avatar_url'),
            'tasks_sync_enabled': bool(config.tasks_sync_enabled) if config else False,
            'calendar_sync_enabled': bool(config.calendar_sync_enabled) if config else False,
            'last_sync_at': config.last_sync_at.isoformat() if config and config.last_sync_at else None,
            'last_sync_status': config.last_sync_status if config else 'never'
        })

    return {
        'google_connected': google_status.get('connected', False),
        'google_email': google_status.get('google_email'),
        'personas': personas
    }
