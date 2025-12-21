"""
FastAPI Authentication Routes - Clerk Integration
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional
from sqlalchemy.orm import Session

from ..core.clerk_auth import (
    get_current_user_from_session,
    require_clerk_auth,
    get_clerk_publishable_key,
    is_clerk_configured,
    get_or_create_user_from_clerk
)
from ..core.templates import render_template
from ...database.config import get_db
from ...database.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """Login page with Clerk sign-in component"""
    # Check if user is already logged in
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Pass Clerk publishable key to template
    return await render_template(
        request,
        "login",
        clerk_publishable_key=get_clerk_publishable_key(),
        clerk_configured=is_clerk_configured()
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    """Registration page - redirects to login since sign-up is invite-only via Clerk"""
    # Check if user is already logged in
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Show sign-up page (invite-only is enforced in Clerk dashboard)
    return await render_template(
        request,
        "register",
        clerk_publishable_key=get_clerk_publishable_key(),
        clerk_configured=is_clerk_configured()
    )


@router.post("/logout")
async def logout(request: Request):
    """
    Logout user - clears the __session cookie and returns success.
    Clerk handles session invalidation on the frontend.
    """
    response = JSONResponse(content={
        "success": True,
        "message": "Logout successful",
        "redirect": "/auth/login"
    })
    # Clear the __session cookie
    response.delete_cookie(key="__session", path="/")
    return response


@router.get("/logout", response_class=HTMLResponse)
async def logout_page(request: Request):
    """
    Logout page that properly clears Clerk session via JavaScript.
    """
    return await render_template(
        request,
        "logout",
        clerk_publishable_key=get_clerk_publishable_key(),
        clerk_configured=is_clerk_configured()
    )


@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """
    OAuth callback handler for Clerk.
    Clerk handles most of the OAuth flow, this is just for any post-auth processing.
    """
    # The session should already be set by Clerk
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=302)

    return RedirectResponse(url="/auth/login", status_code=302)


@router.post("/clerk-webhook")
async def clerk_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Clerk webhooks for user events.

    Events:
    - user.created: Create local user record
    - user.updated: Update local user record
    - user.deleted: Optionally remove local user data

    Security:
    - Verifies Svix webhook signature before processing
    - Rejects requests with missing or invalid signatures
    """
    import hashlib
    import hmac
    import time as time_module

    # Get webhook secret for verification
    webhook_secret = os.getenv("CLERK_WEBHOOK_SECRET", "")
    if not webhook_secret:
        return JSONResponse(
            status_code=500,
            content={"error": "Webhook secret not configured"}
        )

    # Get Svix headers for signature verification
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        return JSONResponse(
            status_code=400,
            content={"error": "Missing webhook signature headers"}
        )

    # Validate timestamp to prevent replay attacks (5 minute tolerance)
    try:
        timestamp = int(svix_timestamp)
        current_time = int(time_module.time())
        if abs(current_time - timestamp) > 300:  # 5 minutes
            return JSONResponse(
                status_code=401,
                content={"error": "Webhook timestamp expired"}
            )
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid timestamp format"}
        )

    # Get raw body for signature verification
    body = await request.body()

    # Verify signature (Svix uses whsec_ prefixed secrets)
    secret = webhook_secret
    if secret.startswith("whsec_"):
        secret = secret[6:]  # Remove whsec_ prefix

    try:
        import base64
        secret_bytes = base64.b64decode(secret)
    except Exception:
        # If not base64, use as-is (for testing)
        secret_bytes = secret.encode()

    # Construct signed payload
    signed_payload = f"{svix_id}.{svix_timestamp}.{body.decode()}"

    # Calculate expected signature
    expected_signature = hmac.new(
        secret_bytes,
        signed_payload.encode(),
        hashlib.sha256
    ).digest()
    expected_signature_b64 = base64.b64encode(expected_signature).decode()

    # Svix signature header format: "v1,<base64_signature> v1,<another_sig>"
    signatures = svix_signature.split(" ")
    signature_valid = False
    for sig in signatures:
        if sig.startswith("v1,"):
            sig_value = sig[3:]  # Remove "v1," prefix
            if hmac.compare_digest(sig_value, expected_signature_b64):
                signature_valid = True
                break

    if not signature_valid:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid webhook signature"}
        )

    try:
        payload = await request.json()
        event_type = payload.get("type")
        data = payload.get("data", {})

        if event_type == "user.created":
            clerk_user_id = data.get("id")
            # Extract fallback email from webhook data
            email = None
            email_addresses = data.get("email_addresses", [])
            for email_obj in email_addresses:
                if email_obj.get("id") == data.get("primary_email_address_id"):
                    email = email_obj.get("email_address")
                    break
            if not email and email_addresses:
                email = email_addresses[0].get("email_address")

            username = data.get("username") or data.get("first_name")

            if clerk_user_id:
                # Will fetch full profile from Clerk API, fallbacks used if unavailable
                get_or_create_user_from_clerk(
                    db,
                    clerk_user_id,
                    fallback_email=email,
                    fallback_username=username
                )

        elif event_type == "user.updated":
            clerk_user_id = data.get("id")
            user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
            if user:
                # Update email if changed
                email_addresses = data.get("email_addresses", [])
                for email_obj in email_addresses:
                    if email_obj.get("id") == data.get("primary_email_address_id"):
                        new_email = email_obj.get("email_address")
                        if new_email and new_email != user.email:
                            # Check email isn't already in use
                            existing = db.query(User).filter(User.email == new_email).first()
                            if not existing:
                                user.email = new_email
                        break

                # Update username if changed and available
                new_username = data.get("username") or data.get("first_name")
                if new_username and new_username != user.username:
                    # Sanitize and check uniqueness
                    sanitized = ''.join(c for c in new_username if c.isalnum() or c == '_')[:50]
                    if sanitized:
                        existing = db.query(User).filter(User.username == sanitized).first()
                        if not existing:
                            user.username = sanitized

                db.commit()

        elif event_type == "user.deleted":
            clerk_user_id = data.get("id")
            # Optionally delete user data
            # For now, just unlink the Clerk ID
            user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
            if user:
                user.clerk_id = None
                db.commit()

        return {"success": True}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Session sync endpoint - bridges Clerk JS session to server
@router.post("/sync")
async def sync_session(request: Request, db: Session = Depends(get_db)):
    """
    Sync Clerk session from frontend to server.

    The client sends the Clerk session token via Authorization header.
    Server verifies, creates a user session, and sets the __session cookie
    for subsequent requests.
    """
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        # Extract the token from Authorization header to set as cookie
        auth_header = request.headers.get("Authorization", "")
        session_token = None
        if auth_header.startswith("Bearer "):
            session_token = auth_header[7:]

        response = JSONResponse(content={
            "success": True,
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username
            }
        })

        # Set the __session cookie so subsequent requests are authenticated
        if session_token:
            response.set_cookie(
                key="__session",
                value=session_token,
                httponly=True,
                secure=request.url.scheme == "https",
                samesite="lax",
                max_age=60 * 60 * 24 * 7  # 7 days
            )

        return response

    return JSONResponse(
        status_code=401,
        content={"success": False, "error": "Invalid or missing session token"}
    )


# API endpoints for checking auth status
@router.get("/api/check")
async def check_auth(request: Request, db: Session = Depends(get_db)):
    """Check if user is authenticated"""
    current_user = await get_current_user_from_session(request, db)
    if current_user:
        return {
            "success": True,
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email
            }
        }
    else:
        return {
            "success": True,
            "authenticated": False
        }


@router.get("/api/me")
async def get_current_user_info(request: Request, db: Session = Depends(get_db)):
    """Get current user information"""
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login
        }
    }
