"""
Google OAuth2 authentication service.

Handles OAuth2 flow for Google Calendar and Tasks APIs:
- Generate consent URL
- Handle callback and token exchange
- Store and refresh tokens
- Provide authenticated credentials for API calls
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Allow HTTP for local development (required for localhost OAuth)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from miachat.database.models import GoogleCredentials, User

logger = logging.getLogger(__name__)

# Google API scopes (openid is added automatically by Google)
GOOGLE_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/userinfo.email',
]

# Environment variables
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8080/api/google/auth/callback')


class GoogleAuthService:
    """Service for Google OAuth2 authentication."""

    def __init__(self):
        self.client_id = GOOGLE_CLIENT_ID
        self.client_secret = GOOGLE_CLIENT_SECRET
        self.redirect_uri = GOOGLE_REDIRECT_URI
        self.scopes = GOOGLE_SCOPES

    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Generate the OAuth consent URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            The authorization URL to redirect the user to
        """
        if not self.is_configured():
            raise ValueError("Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

        flow = self._create_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',  # Get refresh token
            include_granted_scopes='true',
            prompt='consent',  # Force consent to ensure refresh token
            state=state
        )
        return auth_url

    def handle_callback(
        self,
        authorization_response: str,
        user_id: int,
        db: Session
    ) -> GoogleCredentials:
        """Handle the OAuth callback and store credentials.

        Args:
            authorization_response: Full callback URL with authorization code
            user_id: The MinouChat user ID
            db: Database session

        Returns:
            GoogleCredentials model instance
        """
        if not self.is_configured():
            raise ValueError("Google OAuth not configured")

        flow = self._create_flow()
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        # Get user info (email)
        google_email = self._get_user_email(credentials)

        # Store or update credentials
        google_creds = db.query(GoogleCredentials).filter_by(user_id=user_id).first()

        if google_creds:
            # Update existing
            google_creds.access_token = credentials.token
            google_creds.refresh_token = credentials.refresh_token or google_creds.refresh_token
            google_creds.token_expiry = credentials.expiry
            google_creds.scopes = list(credentials.scopes) if credentials.scopes else self.scopes
            google_creds.google_email = google_email
            google_creds.is_enabled = 1
            google_creds.updated_at = datetime.utcnow()
        else:
            # Create new
            google_creds = GoogleCredentials(
                user_id=user_id,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=credentials.expiry,
                scopes=list(credentials.scopes) if credentials.scopes else self.scopes,
                google_email=google_email,
                is_enabled=1
            )
            db.add(google_creds)

        db.commit()
        db.refresh(google_creds)

        logger.info(f"Google credentials stored for user {user_id} ({google_email})")
        return google_creds

    def get_credentials(self, user_id: int, db: Session) -> Optional[Credentials]:
        """Get valid Google credentials for a user.

        Automatically refreshes expired tokens.

        Args:
            user_id: The MinouChat user ID
            db: Database session

        Returns:
            Google Credentials object or None if not connected
        """
        google_creds = db.query(GoogleCredentials).filter_by(
            user_id=user_id,
            is_enabled=1
        ).first()

        if not google_creds:
            return None

        credentials = Credentials(
            token=google_creds.access_token,
            refresh_token=google_creds.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=google_creds.scopes
        )

        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                # Update stored tokens
                google_creds.access_token = credentials.token
                google_creds.token_expiry = credentials.expiry
                google_creds.updated_at = datetime.utcnow()
                db.commit()
                logger.debug(f"Refreshed Google token for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to refresh Google token for user {user_id}: {e}")
                # Mark as disabled if refresh fails
                google_creds.is_enabled = 0
                db.commit()
                return None

        return credentials

    def disconnect(self, user_id: int, db: Session) -> bool:
        """Disconnect Google account for a user.

        Args:
            user_id: The MinouChat user ID
            db: Database session

        Returns:
            True if disconnected successfully
        """
        google_creds = db.query(GoogleCredentials).filter_by(user_id=user_id).first()

        if google_creds:
            # Try to revoke the token
            try:
                credentials = self.get_credentials(user_id, db)
                if credentials:
                    import requests
                    requests.post(
                        'https://oauth2.googleapis.com/revoke',
                        params={'token': credentials.token},
                        headers={'content-type': 'application/x-www-form-urlencoded'}
                    )
            except Exception as e:
                logger.warning(f"Failed to revoke Google token: {e}")

            # Delete credentials
            db.delete(google_creds)
            db.commit()
            logger.info(f"Disconnected Google account for user {user_id}")
            return True

        return False

    def get_connection_status(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Get the Google connection status for a user.

        Args:
            user_id: The MinouChat user ID
            db: Database session

        Returns:
            Dict with connection status info
        """
        if not self.is_configured():
            return {
                'configured': False,
                'connected': False,
                'error': 'Google OAuth not configured'
            }

        google_creds = db.query(GoogleCredentials).filter_by(user_id=user_id).first()

        if not google_creds:
            return {
                'configured': True,
                'connected': False
            }

        return {
            'configured': True,
            'connected': bool(google_creds.is_enabled),
            'google_email': google_creds.google_email,
            'scopes': google_creds.scopes,
            'token_expired': google_creds.is_token_expired(),
            'connected_at': google_creds.created_at.isoformat() if google_creds.created_at else None
        }

    def _create_flow(self) -> Flow:
        """Create an OAuth2 flow instance."""
        client_config = {
            'web': {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [self.redirect_uri],
            }
        }

        return Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )

    def _get_user_email(self, credentials: Credentials) -> Optional[str]:
        """Get the user's email from Google."""
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            return user_info.get('email')
        except Exception as e:
            logger.warning(f"Failed to get Google user email: {e}")
            return None


# Singleton instance
google_auth_service = GoogleAuthService()
