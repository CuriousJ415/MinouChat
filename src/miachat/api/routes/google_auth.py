"""
Google OAuth authentication routes.

Endpoints for connecting/disconnecting Google account:
- GET /api/google/auth/url - Get OAuth consent URL
- GET /api/google/auth/callback - Handle OAuth callback
- POST /api/google/auth/disconnect - Disconnect Google account
- GET /api/google/auth/status - Check connection status
"""

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from miachat.database.config import get_db
from miachat.api.core.clerk_auth import get_current_user_from_session
from miachat.api.core.google_auth_service import google_auth_service
from miachat.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google/auth", tags=["google-auth"])


@router.get("/url")
async def get_auth_url(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Get the Google OAuth consent URL.

    Returns a URL to redirect the user to for Google authorization.
    """
    if not google_auth_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    # Store state and user_id in session
    # User ID is stored so we can identify the user in callback even if Clerk token expires
    request.session['google_oauth_state'] = state
    request.session['google_oauth_user_id'] = user.id

    try:
        auth_url = google_auth_service.get_auth_url(state=state)
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Failed to get Google auth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Handle the Google OAuth callback.

    This is called by Google after user authorizes (or denies) the app.
    Exchanges the authorization code for tokens and stores them.
    """
    # Handle denial
    if error:
        logger.warning(f"Google OAuth denied: {error}")
        return RedirectResponse(url="/settings?google_error=access_denied")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Verify state for CSRF protection
    stored_state = request.session.get('google_oauth_state')
    if state and stored_state and state != stored_state:
        logger.warning("Google OAuth state mismatch - possible CSRF")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Get user_id from session (stored when OAuth was initiated)
    # This is needed because Clerk tokens may expire during the OAuth flow
    user_id = request.session.get('google_oauth_user_id')
    if not user_id:
        logger.error("No user_id in session for Google OAuth callback")
        return RedirectResponse(url="/auth/login?return_to=/settings")

    # Clear OAuth data from session
    request.session.pop('google_oauth_state', None)
    request.session.pop('google_oauth_user_id', None)

    try:
        # Build the full callback URL for token exchange
        authorization_response = str(request.url)

        # Exchange code for tokens
        google_auth_service.handle_callback(
            authorization_response=authorization_response,
            user_id=user_id,
            db=db
        )

        logger.info(f"Google OAuth successful for user {user_id}")
        return RedirectResponse(url="/settings?google_connected=true")

    except Exception as e:
        logger.error(f"Google OAuth callback failed: {e}")
        return RedirectResponse(url=f"/settings?google_error={str(e)[:100]}")


@router.post("/disconnect")
async def disconnect_google(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Disconnect the user's Google account.

    Revokes tokens and removes credentials from database.
    """
    try:
        success = google_auth_service.disconnect(user_id=user.id, db=db)
        if success:
            return {"success": True, "message": "Google account disconnected"}
        else:
            return {"success": True, "message": "No Google account was connected"}
    except Exception as e:
        logger.error(f"Failed to disconnect Google: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_connection_status(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_session)
):
    """Get the current Google connection status for the user."""
    try:
        status = google_auth_service.get_connection_status(user_id=user.id, db=db)
        return status
    except Exception as e:
        logger.error(f"Failed to get Google status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
