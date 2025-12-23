"""
Google Tasks API service.

Handles CRUD operations for Google Tasks:
- List task lists
- Create/get/update/delete tasks
- Manage MinouChat task lists per persona
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from miachat.database.models import PersonaGoogleSyncConfig, TodoItem
from miachat.api.core.google_auth_service import google_auth_service

logger = logging.getLogger(__name__)


class GoogleTasksService:
    """Service for Google Tasks API operations."""

    def __init__(self):
        self.api_name = 'tasks'
        self.api_version = 'v1'

    def _get_service(self, credentials: Credentials):
        """Build the Google Tasks API service."""
        return build(self.api_name, self.api_version, credentials=credentials)

    # =========================================================================
    # Task List Operations
    # =========================================================================

    def list_tasklists(
        self,
        credentials: Credentials,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List all task lists for the user.

        Args:
            credentials: Google OAuth credentials
            max_results: Maximum number of lists to return

        Returns:
            List of task list dictionaries
        """
        try:
            service = self._get_service(credentials)
            result = service.tasklists().list(maxResults=max_results).execute()
            return result.get('items', [])
        except HttpError as e:
            logger.error(f"Failed to list task lists: {e}")
            raise

    def get_or_create_tasklist(
        self,
        credentials: Credentials,
        list_name: str
    ) -> Dict[str, Any]:
        """Get existing task list by name or create a new one.

        Args:
            credentials: Google OAuth credentials
            list_name: Name of the task list (e.g., "MinouChat - Coach")

        Returns:
            Task list dictionary with 'id' and 'title'
        """
        try:
            service = self._get_service(credentials)

            # Check if list already exists
            existing_lists = self.list_tasklists(credentials)
            for task_list in existing_lists:
                if task_list.get('title') == list_name:
                    return task_list

            # Create new list
            new_list = service.tasklists().insert(body={'title': list_name}).execute()
            logger.info(f"Created Google Tasks list: {list_name}")
            return new_list

        except HttpError as e:
            logger.error(f"Failed to get/create task list '{list_name}': {e}")
            raise

    def delete_tasklist(
        self,
        credentials: Credentials,
        tasklist_id: str
    ) -> bool:
        """Delete a task list.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list to delete

        Returns:
            True if deleted successfully
        """
        try:
            service = self._get_service(credentials)
            service.tasklists().delete(tasklist=tasklist_id).execute()
            logger.info(f"Deleted Google Tasks list: {tasklist_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete task list: {e}")
            raise

    # =========================================================================
    # Task Operations
    # =========================================================================

    def list_tasks(
        self,
        credentials: Credentials,
        tasklist_id: str,
        show_completed: bool = True,
        show_deleted: bool = False,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List all tasks in a task list.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list
            show_completed: Include completed tasks
            show_deleted: Include deleted tasks
            max_results: Maximum number of tasks to return

        Returns:
            List of task dictionaries
        """
        try:
            service = self._get_service(credentials)
            result = service.tasks().list(
                tasklist=tasklist_id,
                showCompleted=show_completed,
                showDeleted=show_deleted,
                maxResults=max_results
            ).execute()
            return result.get('items', [])
        except HttpError as e:
            logger.error(f"Failed to list tasks: {e}")
            raise

    def get_task(
        self,
        credentials: Credentials,
        tasklist_id: str,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific task.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list
            task_id: The ID of the task

        Returns:
            Task dictionary or None if not found
        """
        try:
            service = self._get_service(credentials)
            return service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        except HttpError as e:
            if e.resp.status == 404:
                return None
            logger.error(f"Failed to get task: {e}")
            raise

    def create_task(
        self,
        credentials: Credentials,
        tasklist_id: str,
        title: str,
        notes: Optional[str] = None,
        due: Optional[datetime] = None,
        status: str = 'needsAction'
    ) -> Dict[str, Any]:
        """Create a new task.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list
            title: Task title
            notes: Optional task notes/description
            due: Optional due date
            status: Task status ('needsAction' or 'completed')

        Returns:
            Created task dictionary
        """
        try:
            service = self._get_service(credentials)

            task_body = {
                'title': title,
                'status': status
            }

            if notes:
                task_body['notes'] = notes

            if due:
                # Google Tasks uses RFC 3339 format for due dates
                task_body['due'] = due.strftime('%Y-%m-%dT%H:%M:%S.000Z')

            result = service.tasks().insert(tasklist=tasklist_id, body=task_body).execute()
            logger.debug(f"Created Google Task: {title}")
            return result

        except HttpError as e:
            logger.error(f"Failed to create task: {e}")
            raise

    def update_task(
        self,
        credentials: Credentials,
        tasklist_id: str,
        task_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        due: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing task.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list
            task_id: The ID of the task
            title: New title (optional)
            notes: New notes (optional)
            due: New due date (optional)
            status: New status (optional)

        Returns:
            Updated task dictionary
        """
        try:
            service = self._get_service(credentials)

            # Get current task
            task = self.get_task(credentials, tasklist_id, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            # Update fields
            if title is not None:
                task['title'] = title
            if notes is not None:
                task['notes'] = notes
            if due is not None:
                task['due'] = due.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            if status is not None:
                task['status'] = status
                if status == 'completed':
                    task['completed'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')

            result = service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()

            logger.debug(f"Updated Google Task: {task_id}")
            return result

        except HttpError as e:
            logger.error(f"Failed to update task: {e}")
            raise

    def delete_task(
        self,
        credentials: Credentials,
        tasklist_id: str,
        task_id: str
    ) -> bool:
        """Delete a task.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list
            task_id: The ID of the task

        Returns:
            True if deleted successfully
        """
        try:
            service = self._get_service(credentials)
            service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
            logger.debug(f"Deleted Google Task: {task_id}")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                # Already deleted
                return True
            logger.error(f"Failed to delete task: {e}")
            raise

    def complete_task(
        self,
        credentials: Credentials,
        tasklist_id: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Mark a task as completed.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list
            task_id: The ID of the task

        Returns:
            Updated task dictionary
        """
        return self.update_task(
            credentials=credentials,
            tasklist_id=tasklist_id,
            task_id=task_id,
            status='completed'
        )

    def uncomplete_task(
        self,
        credentials: Credentials,
        tasklist_id: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Mark a task as not completed.

        Args:
            credentials: Google OAuth credentials
            tasklist_id: The ID of the task list
            task_id: The ID of the task

        Returns:
            Updated task dictionary
        """
        try:
            service = self._get_service(credentials)
            task = self.get_task(credentials, tasklist_id, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            task['status'] = 'needsAction'
            # Remove completed timestamp
            task.pop('completed', None)

            result = service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()

            return result
        except HttpError as e:
            logger.error(f"Failed to uncomplete task: {e}")
            raise

    # =========================================================================
    # Conversion Helpers
    # =========================================================================

    def todo_to_google_task(self, todo: TodoItem) -> Dict[str, Any]:
        """Convert a MinouChat TodoItem to Google Task format.

        Args:
            todo: MinouChat TodoItem model

        Returns:
            Google Task body dictionary
        """
        task = {
            'title': todo.text,
            'status': 'completed' if todo.is_completed else 'needsAction'
        }

        if todo.due_date:
            task['due'] = todo.due_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        # Add priority as note prefix
        priority_prefix = ''
        if todo.priority == 1:
            priority_prefix = '[HIGH] '
        elif todo.priority == 3:
            priority_prefix = '[LOW] '

        if priority_prefix:
            task['notes'] = f"{priority_prefix}Priority task from MinouChat"

        return task

    def google_task_to_todo_data(self, google_task: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a Google Task to MinouChat TodoItem data.

        Args:
            google_task: Google Task dictionary

        Returns:
            Dictionary suitable for creating/updating TodoItem
        """
        data = {
            'text': google_task.get('title', ''),
            'is_completed': google_task.get('status') == 'completed'
        }

        # Parse due date
        due_str = google_task.get('due')
        if due_str:
            try:
                data['due_date'] = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        # Parse priority from notes
        notes = google_task.get('notes', '')
        if '[HIGH]' in notes:
            data['priority'] = 1
        elif '[LOW]' in notes:
            data['priority'] = 3
        else:
            data['priority'] = 2

        return data

    def parse_google_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse a Google API timestamp string to datetime.

        Args:
            timestamp_str: RFC 3339 timestamp string

        Returns:
            datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None

        try:
            # Handle various formats Google might return
            timestamp_str = timestamp_str.replace('Z', '+00:00')
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError):
            return None


# Singleton instance
google_tasks_service = GoogleTasksService()
