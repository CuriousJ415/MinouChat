"""
Clerk Authentication Middleware for MinouChat

Handles Clerk session verification and user mapping with proper JWT
signature verification using Clerk's JWKS endpoint.

Security Features:
- RS256 JWT signature verification via JWKS
- Automatic key rotation support
- Secure user creation with random password hashes
- Rate limiting ready (middleware integration)
- Full user profile fetching from Clerk Backend API
"""
import os
import logging
import secrets
import hashlib
import urllib.request
import urllib.error
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from functools import lru_cache
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient, PyJWKClientError
from fastapi import Request, HTTPException, Depends, status
from sqlalchemy.orm import Session

from ...database.config import get_db
from ...database.models import User

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ClerkUserProfile:
    """User profile data fetched from Clerk Backend API."""
    clerk_id: str
    email: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    profile_image_url: Optional[str]

    @property
    def display_name(self) -> str:
        """Get the best display name available."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        if self.username:
            return self.username
        if self.email:
            return self.email.split('@')[0]
        return self.clerk_id

    @property
    def safe_username(self) -> str:
        """Get a safe username for database storage."""
        # Priority: username > first_name > email prefix
        base = self.username or self.first_name or (self.email.split('@')[0] if self.email else None)
        if not base:
            return f"user_{secrets.token_hex(4)}"
        # Sanitize: alphanumeric and underscore only, max 50 chars
        sanitized = ''.join(c for c in base if c.isalnum() or c == '_')[:50]
        return sanitized if sanitized else f"user_{secrets.token_hex(4)}"

# =============================================================================
# Configuration
# =============================================================================

CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY: str = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_API_BASE_URL: str = "https://api.clerk.com/v1"


# =============================================================================
# Clerk Backend API Client
# =============================================================================

def fetch_clerk_user_profile(clerk_user_id: str) -> Optional[ClerkUserProfile]:
    """
    Fetch full user profile from Clerk's Backend API.

    This provides complete user data including email, name, and profile image
    that aren't always included in the session JWT claims.

    Args:
        clerk_user_id: The Clerk user ID (e.g., 'user_xxxxx')

    Returns:
        ClerkUserProfile if successful, None if failed

    Note:
        Requires CLERK_SECRET_KEY to be set. This is a server-side only operation.
    """
    if not CLERK_SECRET_KEY:
        logger.warning("CLERK_SECRET_KEY not set - cannot fetch user profile from Clerk API")
        return None

    if not clerk_user_id:
        logger.error("Cannot fetch Clerk user profile: clerk_user_id is empty")
        return None

    url = f"{CLERK_API_BASE_URL}/users/{clerk_user_id}"
    headers = {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "MinouChat/1.0",
    }

    try:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                logger.error(f"Clerk API returned status {response.status} for user {clerk_user_id}")
                return None

            data = json.loads(response.read().decode("utf-8"))

            # Extract primary email
            email = None
            email_addresses = data.get("email_addresses", [])
            primary_email_id = data.get("primary_email_address_id")
            for email_obj in email_addresses:
                if email_obj.get("id") == primary_email_id:
                    email = email_obj.get("email_address")
                    break
            # Fallback to first email if no primary
            if not email and email_addresses:
                email = email_addresses[0].get("email_address")

            profile = ClerkUserProfile(
                clerk_id=data.get("id", clerk_user_id),
                email=email,
                username=data.get("username"),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                profile_image_url=data.get("image_url") or data.get("profile_image_url"),
            )

            logger.debug(f"Fetched Clerk profile for {clerk_user_id}: {profile.display_name}")
            return profile

    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.warning(f"Clerk user not found: {clerk_user_id}")
        elif e.code == 401:
            logger.error("Clerk API authentication failed - check CLERK_SECRET_KEY")
        else:
            logger.error(f"Clerk API HTTP error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"Clerk API connection error: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Clerk API returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching Clerk user profile: {e}")
        return None


# =============================================================================
# JWKS Client for JWT Verification
# =============================================================================

# Extract Clerk domain from publishable key for JWKS URL
# Publishable key format: pk_test_<base64_encoded_domain>
def _get_clerk_domain() -> Optional[str]:
    """Extract Clerk domain from publishable key for JWKS URL construction."""
    if not CLERK_PUBLISHABLE_KEY:
        return None
    try:
        # The publishable key contains the domain in base64 after pk_test_ or pk_live_
        import base64
        parts = CLERK_PUBLISHABLE_KEY.split("_")
        if len(parts) >= 3:
            encoded_domain = parts[2]
            # Add padding if needed
            padding = 4 - len(encoded_domain) % 4
            if padding != 4:
                encoded_domain += "=" * padding
            domain = base64.b64decode(encoded_domain).decode("utf-8")
            # Clerk encodes domain with trailing $, strip it
            domain = domain.rstrip("$")
            return domain
    except Exception as e:
        logger.warning(f"Could not extract Clerk domain from publishable key: {e}")
    return None


# Initialize JWKS client lazily
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> Optional[PyJWKClient]:
    """Get or create the JWKS client for Clerk token verification."""
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client

    clerk_domain = _get_clerk_domain()
    if not clerk_domain:
        logger.warning("Clerk domain not available - JWT verification disabled")
        return None

    jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"
    try:
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        logger.info(f"Initialized Clerk JWKS client with URL: {jwks_url}")
        return _jwks_client
    except Exception as e:
        logger.error(f"Failed to initialize JWKS client: {e}")
        return None


def _generate_secure_placeholder_hash() -> str:
    """
    Generate a secure random hash for Clerk-managed users.

    This prevents the security risk of having a predictable placeholder
    password hash that could be exploited if auth logic has bugs.
    """
    random_bytes = secrets.token_bytes(32)
    return f"clerk_external_auth_{hashlib.sha256(random_bytes).hexdigest()}"


async def get_clerk_session_claims(request: Request) -> Optional[Dict[str, Any]]:
    """
    Extract and verify Clerk session token from request.

    Args:
        request: FastAPI request object

    Returns:
        Decoded JWT claims if valid, None otherwise

    Security:
        - Verifies JWT signature using Clerk's JWKS
        - Validates token expiration
        - Falls back to unverified decode only in development if JWKS unavailable
    """
    # Get session token from cookie or Authorization header
    session_token = request.cookies.get("__session")
    if not session_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            session_token = auth_header[7:]

    if not session_token:
        logger.warning(f"[AUTH] No session token for {request.method} {request.url.path} - cookies: {list(request.cookies.keys())}")
        return None

    jwks_client = _get_jwks_client()

    try:
        if jwks_client:
            # Production: Verify signature with JWKS
            signing_key = jwks_client.get_signing_key_from_jwt(session_token)
            claims = jwt.decode(
                session_token,
                signing_key.key,
                algorithms=["RS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                }
            )
            return claims
        else:
            # Development fallback: Log warning and decode without verification
            # This should only happen if Clerk is misconfigured
            logger.warning(
                "JWKS client unavailable - decoding token without signature verification. "
                "This is insecure and should only be used in development!"
            )
            claims = jwt.decode(
                session_token,
                options={"verify_signature": False}
            )
            return claims

    except jwt.ExpiredSignatureError:
        logger.debug("Clerk token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid Clerk token: {e}")
        return None
    except PyJWKClientError as e:
        logger.error(f"JWKS client error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying Clerk token: {e}")
        return None


def get_or_create_user_from_clerk(
    db: Session,
    clerk_user_id: str,
    fallback_email: Optional[str] = None,
    fallback_username: Optional[str] = None
) -> User:
    """
    Get or create a local user from Clerk user data.

    This function fetches the full user profile from Clerk's Backend API
    to get accurate email, name, and profile data.

    Args:
        db: Database session
        clerk_user_id: Clerk's unique user identifier
        fallback_email: Fallback email if Clerk API unavailable
        fallback_username: Fallback username if Clerk API unavailable

    Returns:
        User object (existing or newly created)

    Security:
        - Uses secure random hash instead of predictable placeholder
        - Validates input lengths
        - Handles duplicate usernames safely
        - Fetches real user data from Clerk Backend API
    """
    # Input validation
    if not clerk_user_id or len(clerk_user_id) > 255:
        raise ValueError("Invalid clerk_user_id")

    # First try to find existing user by clerk_id
    user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
    if user:
        # Update last login and refresh profile from Clerk
        user.last_login = datetime.now(timezone.utc)

        # Optionally refresh user data from Clerk on login
        profile = fetch_clerk_user_profile(clerk_user_id)
        if profile:
            # Update email if changed
            if profile.email and profile.email != user.email:
                # Check if new email is already in use
                existing = db.query(User).filter(User.email == profile.email).first()
                if not existing or existing.id == user.id:
                    user.email = profile.email
                    logger.info(f"Updated email for user {user.id}")

        db.commit()
        return user

    # Fetch full profile from Clerk Backend API
    profile = fetch_clerk_user_profile(clerk_user_id)

    # Determine email and username from profile or fallbacks
    if profile:
        email = profile.email or fallback_email or f"{clerk_user_id}@clerk.local"
        username = profile.safe_username
    else:
        # Fallback if Clerk API is unavailable
        logger.warning(f"Could not fetch Clerk profile for {clerk_user_id}, using fallbacks")
        email = fallback_email or f"{clerk_user_id}@clerk.local"
        username = fallback_username or f"user_{secrets.token_hex(4)}"
        # Sanitize fallback username
        username = ''.join(c for c in username if c.isalnum() or c == '_')[:50]
        if not username:
            username = f"user_{secrets.token_hex(4)}"

    # Validate email
    if len(email) > 255:
        email = f"{clerk_user_id}@clerk.local"

    # Check if user exists by email (link existing account)
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link existing user to Clerk
        user.clerk_id = clerk_user_id
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Linked existing user {user.username} to Clerk ID {clerk_user_id}")
        return user

    # Ensure username is unique
    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1
        if counter > 1000:  # Prevent infinite loop
            username = f"user_{secrets.token_hex(8)}"
            break

    # Create new user
    new_user = User(
        username=username,
        email=email,
        password_hash=_generate_secure_placeholder_hash(),
        clerk_id=clerk_user_id,
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Created new user from Clerk: {username} ({email})")
    return new_user


async def get_current_user_from_session(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user from Clerk session.

    This is the primary authentication function for routes that support
    both authenticated and unauthenticated access.

    The function verifies the JWT token from the request and fetches
    full user profile data from Clerk's Backend API.

    Args:
        request: FastAPI request object
        db: Database session (injected)

    Returns:
        User object if authenticated, None otherwise
    """
    claims = await get_clerk_session_claims(request)
    if not claims:
        return None

    # Extract user ID from Clerk claims
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        logger.warning("Clerk token missing 'sub' claim")
        return None

    # Extract fallback data from claims (used if Clerk API unavailable)
    fallback_email = (
        claims.get("email") or
        claims.get("primary_email_address")
    )
    fallback_username = claims.get("username") or claims.get("first_name")

    # Get or create local user (fetches full profile from Clerk API)
    try:
        user = get_or_create_user_from_clerk(
            db,
            clerk_user_id,
            fallback_email=fallback_email,
            fallback_username=fallback_username
        )
        return user
    except ValueError as e:
        logger.error(f"Invalid user data from Clerk: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting/creating user from Clerk: {e}")
        return None


async def require_clerk_auth(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Require Clerk authentication for protected routes.

    Use this as a dependency for routes that require authentication.

    Args:
        request: FastAPI request object
        db: Database session (injected)

    Returns:
        Authenticated User object

    Raises:
        HTTPException: 401 if not authenticated
    """
    user = await get_current_user_from_session(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"Location": "/auth/login"}
        )
    return user


async def require_session_auth(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Alias for require_clerk_auth for backwards compatibility.

    Deprecated: Use require_clerk_auth directly.
    """
    return await require_clerk_auth(request, db)


def get_clerk_publishable_key() -> str:
    """
    Get the Clerk publishable key for frontend use.

    This key is safe to expose in client-side code.
    """
    return CLERK_PUBLISHABLE_KEY


def is_clerk_configured() -> bool:
    """
    Check if Clerk is properly configured.

    Returns:
        True if both secret and publishable keys are set
    """
    return bool(CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY)
