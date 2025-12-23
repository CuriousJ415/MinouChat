"""
Google Calendar API service.

Handles read/write operations for Google Calendar:
- List calendars
- Get upcoming events
- Create events
- Format calendar context for chat
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from miachat.api.core.google_auth_service import google_auth_service

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service for Google Calendar API operations."""

    def __init__(self):
        self.api_name = 'calendar'
        self.api_version = 'v3'

    def _get_service(self, credentials: Credentials):
        """Build the Google Calendar API service."""
        return build(self.api_name, self.api_version, credentials=credentials)

    # =========================================================================
    # Calendar List Operations
    # =========================================================================

    def list_calendars(
        self,
        credentials: Credentials
    ) -> List[Dict[str, Any]]:
        """List all calendars for the user.

        Args:
            credentials: Google OAuth credentials

        Returns:
            List of calendar dictionaries
        """
        try:
            service = self._get_service(credentials)
            result = service.calendarList().list().execute()
            calendars = result.get('items', [])

            return [
                {
                    'id': cal.get('id'),
                    'summary': cal.get('summary'),
                    'description': cal.get('description'),
                    'primary': cal.get('primary', False),
                    'backgroundColor': cal.get('backgroundColor'),
                    'accessRole': cal.get('accessRole')
                }
                for cal in calendars
            ]
        except HttpError as e:
            logger.error(f"Failed to list calendars: {e}")
            raise

    # =========================================================================
    # Event Operations
    # =========================================================================

    def get_upcoming_events(
        self,
        credentials: Credentials,
        calendar_id: str = 'primary',
        days_ahead: int = 7,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Get upcoming events from a calendar.

        Args:
            credentials: Google OAuth credentials
            calendar_id: Calendar ID ('primary' for main calendar)
            days_ahead: Number of days to look ahead
            max_results: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        try:
            service = self._get_service(credentials)

            # Time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

            result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = result.get('items', [])

            return [self._format_event(event) for event in events]

        except HttpError as e:
            logger.error(f"Failed to get upcoming events: {e}")
            raise

    def get_event(
        self,
        credentials: Credentials,
        calendar_id: str,
        event_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific event.

        Args:
            credentials: Google OAuth credentials
            calendar_id: Calendar ID
            event_id: Event ID

        Returns:
            Event dictionary or None
        """
        try:
            service = self._get_service(credentials)
            event = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return self._format_event(event)
        except HttpError as e:
            if e.resp.status == 404:
                return None
            logger.error(f"Failed to get event: {e}")
            raise

    def create_event(
        self,
        credentials: Credentials,
        calendar_id: str = 'primary',
        summary: str = '',
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        all_day: bool = False,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        Args:
            credentials: Google OAuth credentials
            calendar_id: Calendar ID ('primary' for main calendar)
            summary: Event title
            description: Event description
            start_time: Start datetime
            end_time: End datetime (defaults to 1 hour after start)
            all_day: If True, create an all-day event
            location: Event location
            attendees: List of attendee email addresses

        Returns:
            Created event dictionary
        """
        try:
            service = self._get_service(credentials)

            # Default times
            if not start_time:
                start_time = datetime.utcnow() + timedelta(hours=1)
            if not end_time:
                end_time = start_time + timedelta(hours=1)

            event_body = {
                'summary': summary
            }

            if description:
                event_body['description'] = description

            if location:
                event_body['location'] = location

            if all_day:
                event_body['start'] = {'date': start_time.strftime('%Y-%m-%d')}
                event_body['end'] = {'date': end_time.strftime('%Y-%m-%d')}
            else:
                # Use local timezone instead of UTC so times match user expectations
                import time
                local_tz = time.tzname[time.daylight] if time.daylight else time.tzname[0]
                # Map common timezone abbreviations to IANA format
                tz_map = {
                    'PST': 'America/Los_Angeles',
                    'PDT': 'America/Los_Angeles',
                    'MST': 'America/Denver',
                    'MDT': 'America/Denver',
                    'CST': 'America/Chicago',
                    'CDT': 'America/Chicago',
                    'EST': 'America/New_York',
                    'EDT': 'America/New_York',
                }
                timezone = tz_map.get(local_tz, 'America/Los_Angeles')  # Default to Pacific

                event_body['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone
                }
                event_body['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone
                }

            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]

            event = service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()

            logger.info(f"Created calendar event: {summary}")
            return self._format_event(event)

        except HttpError as e:
            logger.error(f"Failed to create event: {e}")
            raise

    def delete_event(
        self,
        credentials: Credentials,
        calendar_id: str,
        event_id: str
    ) -> bool:
        """Delete a calendar event.

        Args:
            credentials: Google OAuth credentials
            calendar_id: Calendar ID
            event_id: Event ID

        Returns:
            True if deleted successfully
        """
        try:
            service = self._get_service(credentials)
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            logger.info(f"Deleted calendar event: {event_id}")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                return True  # Already deleted
            logger.error(f"Failed to delete event: {e}")
            raise

    # =========================================================================
    # Context for Chat
    # =========================================================================

    def get_calendar_context(
        self,
        user_id: int,
        db: Session,
        days_ahead: int = 7,
        max_events: int = 10
    ) -> Optional[str]:
        """Get calendar context formatted for chat.

        Fetches events from ALL calendars the user has access to,
        not just the primary calendar.

        Args:
            user_id: MinouChat user ID
            db: Database session
            days_ahead: Number of days to look ahead
            max_events: Maximum events to include

        Returns:
            Formatted string for chat context, or None if not connected
        """
        credentials = google_auth_service.get_credentials(user_id, db)
        if not credentials:
            return None

        try:
            # Get all calendars the user has access to
            calendars = self.list_calendars(credentials)

            all_events = []
            for cal in calendars:
                try:
                    cal_events = self.get_upcoming_events(
                        credentials=credentials,
                        calendar_id=cal['id'],
                        days_ahead=days_ahead,
                        max_results=max_events
                    )
                    all_events.extend(cal_events)
                except Exception as e:
                    logger.warning(f"Failed to get events from calendar {cal.get('summary', cal['id'])}: {e}")
                    continue

            if not all_events:
                return "[User's Upcoming Calendar]\nNo upcoming events in the next week."

            # Sort by start time and limit
            all_events.sort(key=lambda e: e.get('start_time') or e.get('start_date') or '')
            all_events = all_events[:max_events]

            lines = ["[User's Upcoming Calendar]"]
            for event in all_events:
                time_str = self._format_event_time(event)
                lines.append(f"- {time_str}: {event['summary']}")

            return '\n'.join(lines)

        except Exception as e:
            logger.error(f"Failed to get calendar context: {e}")
            return None

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Google Calendar event for our API.

        Args:
            event: Raw Google Calendar event

        Returns:
            Formatted event dictionary
        """
        start = event.get('start', {})
        end = event.get('end', {})

        # Handle all-day vs timed events
        if 'date' in start:
            start_str = start['date']
            end_str = end.get('date', start_str)
            all_day = True
        else:
            start_str = start.get('dateTime', '')
            end_str = end.get('dateTime', '')
            all_day = False

        return {
            'id': event.get('id'),
            'summary': event.get('summary', '(No title)'),
            'description': event.get('description'),
            'location': event.get('location'),
            'start': start_str,
            'end': end_str,
            'all_day': all_day,
            'html_link': event.get('htmlLink'),
            'status': event.get('status'),
            'creator': event.get('creator', {}).get('email'),
            'attendees': [
                {
                    'email': a.get('email'),
                    'responseStatus': a.get('responseStatus')
                }
                for a in event.get('attendees', [])
            ]
        }

    def _format_event_time(self, event: Dict[str, Any]) -> str:
        """Format event time for display.

        Args:
            event: Formatted event dictionary

        Returns:
            Human-readable time string
        """
        if event.get('all_day'):
            try:
                date = datetime.strptime(event['start'], '%Y-%m-%d')
                return date.strftime('%A, %b %d')
            except (ValueError, TypeError):
                return event['start']
        else:
            try:
                # Parse ISO datetime
                start_str = event['start']
                if 'T' in start_str:
                    # Remove timezone info for parsing
                    if '+' in start_str:
                        start_str = start_str[:start_str.index('+')]
                    elif start_str.endswith('Z'):
                        start_str = start_str[:-1]

                    start = datetime.fromisoformat(start_str)
                    now = datetime.utcnow()

                    # Format based on how far away
                    if start.date() == now.date():
                        return f"Today {start.strftime('%I:%M %p')}"
                    elif start.date() == (now + timedelta(days=1)).date():
                        return f"Tomorrow {start.strftime('%I:%M %p')}"
                    else:
                        return start.strftime('%A %I:%M %p')
                else:
                    return event['start']
            except (ValueError, TypeError):
                return event['start']


# Singleton instance
google_calendar_service = GoogleCalendarService()
