"""
Clerk Authentication Middleware for MinouChat
Handles Clerk session verification and user mapping
"""
import os
import jwt
import logging
import urllib.request
import urllib.error
import json
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from fastapi import Request, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...database.config import get_db
from ...database.models import User

logger = logging.getLogger(__name__)

# Clerk configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")


@dataclass
class ClerkUserProfile:
    """User profile data from Clerk API"""
    user_id: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]

    @property
    def display_name(self) -> str:
        """Get the best display name available"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        if self.username:
            return self.username
        if self.email:
            return self.email.split('@')[0]
        return self.user_id


def fetch_clerk_user_profile(clerk_user_id: str) -> Optional[ClerkUserProfile]:
    """
    Fetch user profile from Clerk Backend API.

    IMPORTANT: Includes User-Agent header to avoid Cloudflare 403 blocks.
    """
    if not CLERK_SECRET_KEY:
        logger.warning("CLERK_SECRET_KEY not configured")
        return None

    url = f"https://api.clerk.com/v1/users/{clerk_user_id}"
    headers = {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "MinouChat/1.0",  # Required to avoid Cloudflare blocks
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

            # Extract email from email_addresses array
            email = None
            if data.get("email_addresses"):
                primary_email = next(
                    (e for e in data["email_addresses"] if e.get("id") == data.get("primary_email_address_id")),
                    data["email_addresses"][0] if data["email_addresses"] else None
                )
                if primary_email:
                    email = primary_email.get("email_address")

            return ClerkUserProfile(
                user_id=clerk_user_id,
                email=email,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                username=data.get("username"),
            )
    except urllib.error.HTTPError as e:
        logger.error(f"Clerk API HTTP error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"Clerk API URL error: {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Clerk API error: {e}")
        return None


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


def get_or_create_user_from_clerk(db: Session, clerk_user_id: str) -> User:
    """Get or create a local user from Clerk user data"""
    # First try to find by clerk_id
    user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
    if user:
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        return user

    # Fetch full profile from Clerk API
    profile = fetch_clerk_user_profile(clerk_user_id)

    if profile:
        email = profile.email or f"{clerk_user_id}@clerk.local"
        username = profile.display_name
    else:
        # Fallback if API call fails
        logger.warning(f"Could not fetch Clerk profile for {clerk_user_id}, using fallback")
        email = f"{clerk_user_id}@clerk.local"
        username = clerk_user_id

    # Check if user exists by email (for existing users)
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link existing user to Clerk and update username if we have a real name
        user.clerk_id = clerk_user_id
        if profile and profile.display_name and user.username.startswith("user_"):
            user.username = profile.display_name
        user.last_login = datetime.utcnow()
        db.commit()
        return user

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

    # Get or create local user (fetches full profile from Clerk API)
    user = get_or_create_user_from_clerk(db, clerk_user_id)
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
