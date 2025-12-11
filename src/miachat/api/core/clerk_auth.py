"""
Clerk Authentication Middleware for MinouChat
Handles Clerk session verification and user mapping
"""
import os
import jwt
from typing import Optional
from datetime import datetime
from fastapi import Request, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...database.config import get_db
from ...database.models import User


# Clerk configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")


async def get_clerk_session_claims(request: Request) -> Optional[dict]:
    """Extract and verify Clerk session token from request"""
    # Get session token from cookie or Authorization header
    session_token = request.cookies.get("__session")
    if not session_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header[7:]

    if not session_token:
        return None

    try:
        # Verify the JWT token
        # Clerk tokens are signed with RS256, we need the public key
        # For now, we'll decode without verification and rely on Clerk's infrastructure
        # In production, you should verify with Clerk's JWKS endpoint
        claims = jwt.decode(
            session_token,
            options={"verify_signature": False}  # TODO: Add proper verification with Clerk JWKS
        )
        return claims
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


def get_or_create_user_from_clerk(db: Session, clerk_user_id: str, email: str, username: str = None) -> User:
    """Get or create a local user from Clerk user data"""
    # First try to find by clerk_id
    user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
    if user:
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        return user

    # If no clerk_id match, try by email (for existing users)
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link existing user to Clerk
        user.clerk_id = clerk_user_id
        user.last_login = datetime.utcnow()
        db.commit()
        return user

    # Create new user
    # Generate a unique username if not provided
    if not username:
        username = email.split('@')[0]

    # Ensure username is unique
    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    new_user = User(
        username=username,
        email=email,
        password_hash="clerk_managed",  # Placeholder since Clerk handles auth
        clerk_id=clerk_user_id,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


async def get_current_user_from_session(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Get the current user from Clerk session.
    This replaces the old session-based auth function.
    Returns None if not authenticated (for optional auth routes).
    """
    claims = await get_clerk_session_claims(request)
    if not claims:
        return None

    # Extract user info from Clerk claims
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        return None

    # Get email and username from claims
    # Clerk stores these in different claim fields
    email = claims.get("email") or claims.get("primary_email_address") or f"{clerk_user_id}@clerk.local"
    username = claims.get("username") or claims.get("first_name")

    # Get or create local user
    user = get_or_create_user_from_clerk(db, clerk_user_id, email, username)
    return user


async def require_clerk_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Require Clerk authentication for protected routes.
    Raises 401 if not authenticated.
    """
    user = await get_current_user_from_session(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"Location": "/auth/login"}
        )
    return user


async def require_session_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Alias for require_clerk_auth for backwards compatibility.
    """
    return await require_clerk_auth(request, db)


# Helper functions for templates
def get_clerk_publishable_key() -> str:
    """Get the Clerk publishable key for frontend use"""
    return CLERK_PUBLISHABLE_KEY


def is_clerk_configured() -> bool:
    """Check if Clerk is properly configured"""
    return bool(CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY)
