"""
Google Tasks sync service.

Handles two-way synchronization between MinouChat todos and Google Tasks:
- Full sync for a persona
- Incremental sync on todo changes
- Conflict resolution with last-write-wins
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session

from miachat.database.models import (
    TodoItem,
    PersonaGoogleSyncConfig,
    TodoGoogleTaskMapping,
    User
)
from miachat.api.core.google_auth_service import google_auth_service
from miachat.api.core.google_tasks_service import google_tasks_service
from miachat.api.core.character_manager import character_manager

logger = logging.getLogger(__name__)


class GoogleSyncService:
    """Service for two-way sync between MinouChat and Google Tasks."""

    # =========================================================================
    # Sync Configuration
    # =========================================================================

    def get_sync_config(
        self,
        user_id: int,
        character_id: str,
        db: Session
    ) -> Optional[PersonaGoogleSyncConfig]:
        """Get sync configuration for a persona.

        Args:
            user_id: MinouChat user ID
            character_id: Persona/character ID
            db: Database session

        Returns:
            PersonaGoogleSyncConfig or None
        """
        return db.query(PersonaGoogleSyncConfig).filter_by(
            user_id=user_id,
            character_id=character_id
        ).first()

    def enable_sync(
        self,
        user_id: int,
        character_id: str,
        db: Session,
        tasks_enabled: bool = True,
        calendar_enabled: bool = False
    ) -> PersonaGoogleSyncConfig:
        """Enable Google sync for a persona.

        Creates the Google Tasks list if tasks sync is enabled.

        Args:
            user_id: MinouChat user ID
            character_id: Persona/character ID
            db: Database session
            tasks_enabled: Enable Tasks sync
            calendar_enabled: Enable Calendar sync

        Returns:
            PersonaGoogleSyncConfig
        """
        # Get or create sync config
        config = self.get_sync_config(user_id, character_id, db)
        if not config:
            config = PersonaGoogleSyncConfig(
                user_id=user_id,
                character_id=character_id
            )
            db.add(config)

        # Get persona name for list naming
        persona_name = self._get_persona_name(character_id)
        list_name = f"MinouChat - {persona_name}"

        # Set up Google Tasks list if enabling
        if tasks_enabled and not config.tasks_sync_enabled:
            credentials = google_auth_service.get_credentials(user_id, db)
            if credentials:
                try:
                    task_list = google_tasks_service.get_or_create_tasklist(
                        credentials=credentials,
                        list_name=list_name
                    )
                    config.google_tasklist_id = task_list['id']
                    config.google_tasklist_name = list_name
                except Exception as e:
                    logger.error(f"Failed to create Google Tasks list: {e}")
                    raise

        config.tasks_sync_enabled = 1 if tasks_enabled else 0
        config.calendar_sync_enabled = 1 if calendar_enabled else 0
        config.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(config)

        logger.info(f"Enabled Google sync for persona {character_id} (tasks={tasks_enabled}, calendar={calendar_enabled})")
        return config

    def disable_sync(
        self,
        user_id: int,
        character_id: str,
        db: Session,
        delete_google_list: bool = False
    ) -> bool:
        """Disable Google sync for a persona.

        Args:
            user_id: MinouChat user ID
            character_id: Persona/character ID
            db: Database session
            delete_google_list: Also delete the Google Tasks list

        Returns:
            True if disabled successfully
        """
        config = self.get_sync_config(user_id, character_id, db)
        if not config:
            return True

        # Optionally delete the Google Tasks list
        if delete_google_list and config.google_tasklist_id:
            credentials = google_auth_service.get_credentials(user_id, db)
            if credentials:
                try:
                    google_tasks_service.delete_tasklist(
                        credentials=credentials,
                        tasklist_id=config.google_tasklist_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete Google Tasks list: {e}")

        # Clear mappings for this persona's todos
        todo_ids = db.query(TodoItem.id).filter_by(
            user_id=user_id,
            character_id=character_id
        ).all()
        todo_ids = [t[0] for t in todo_ids]

        if todo_ids:
            db.query(TodoGoogleTaskMapping).filter(
                TodoGoogleTaskMapping.todo_id.in_(todo_ids)
            ).delete(synchronize_session=False)

        config.tasks_sync_enabled = 0
        config.calendar_sync_enabled = 0
        config.google_tasklist_id = None
        config.updated_at = datetime.utcnow()

        db.commit()
        logger.info(f"Disabled Google sync for persona {character_id}")
        return True

    # =========================================================================
    # Full Sync
    # =========================================================================

    def full_sync(
        self,
        user_id: int,
        character_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Perform full two-way sync for a persona.

        Args:
            user_id: MinouChat user ID
            character_id: Persona/character ID
            db: Database session

        Returns:
            Sync result summary
        """
        config = self.get_sync_config(user_id, character_id, db)
        if not config or not config.tasks_sync_enabled:
            return {'error': 'Sync not enabled for this persona'}

        credentials = google_auth_service.get_credentials(user_id, db)
        if not credentials:
            return {'error': 'Google not connected'}

        result = {
            'pushed': 0,
            'pulled': 0,
            'conflicts': 0,
            'deleted_local': 0,
            'deleted_remote': 0,
            'errors': []
        }

        try:
            # Ensure task list exists
            tasklist_id = config.google_tasklist_id
            if not tasklist_id:
                persona_name = self._get_persona_name(character_id)
                task_list = google_tasks_service.get_or_create_tasklist(
                    credentials=credentials,
                    list_name=f"MinouChat - {persona_name}"
                )
                tasklist_id = task_list['id']
                config.google_tasklist_id = tasklist_id
                config.google_tasklist_name = task_list['title']

            # Get all local todos for this persona
            local_todos = db.query(TodoItem).filter_by(
                user_id=user_id,
                character_id=character_id
            ).all()

            # Get all Google tasks
            google_tasks = google_tasks_service.list_tasks(
                credentials=credentials,
                tasklist_id=tasklist_id,
                show_completed=True
            )

            # Build lookup maps
            local_by_id = {t.id: t for t in local_todos}
            google_by_id = {t['id']: t for t in google_tasks}

            # Get existing mappings
            mappings = db.query(TodoGoogleTaskMapping).filter(
                TodoGoogleTaskMapping.todo_id.in_(local_by_id.keys())
            ).all() if local_by_id else []
            mapping_by_todo = {m.todo_id: m for m in mappings}
            mapping_by_google = {m.google_task_id: m for m in mappings}

            # Process local todos
            for todo in local_todos:
                mapping = mapping_by_todo.get(todo.id)

                if mapping:
                    google_task = google_by_id.get(mapping.google_task_id)
                    if google_task:
                        # Both exist - check for sync
                        action = self._resolve_conflict(todo, google_task, mapping)
                        if action == 'push_to_google':
                            self._push_to_google(todo, mapping, credentials, tasklist_id, db)
                            result['pushed'] += 1
                        elif action == 'pull_from_google':
                            self._pull_from_google(todo, google_task, mapping, db)
                            result['pulled'] += 1
                    else:
                        # Deleted on Google - delete locally
                        db.delete(mapping)
                        db.delete(todo)
                        result['deleted_local'] += 1
                else:
                    # New local todo - push to Google
                    try:
                        self._create_google_task(todo, credentials, tasklist_id, db)
                        result['pushed'] += 1
                    except Exception as e:
                        result['errors'].append(f"Failed to push todo {todo.id}: {str(e)}")

            # Check for new Google tasks (not mapped to local)
            for google_id, google_task in google_by_id.items():
                if google_id not in mapping_by_google:
                    # New on Google - create locally
                    try:
                        self._create_local_todo(
                            google_task=google_task,
                            user_id=user_id,
                            character_id=character_id,
                            tasklist_id=tasklist_id,
                            db=db
                        )
                        result['pulled'] += 1
                    except Exception as e:
                        result['errors'].append(f"Failed to pull task {google_id}: {str(e)}")

            # Update sync status
            config.last_sync_at = datetime.utcnow()
            config.last_sync_status = 'success' if not result['errors'] else 'partial'
            config.last_sync_error = '; '.join(result['errors'][:3]) if result['errors'] else None

            db.commit()
            logger.info(f"Full sync complete for persona {character_id}: {result}")

        except Exception as e:
            logger.error(f"Full sync failed for persona {character_id}: {e}")
            config.last_sync_status = 'error'
            config.last_sync_error = str(e)[:500]
            db.commit()
            result['errors'].append(str(e))

        return result

    # =========================================================================
    # Incremental Sync (on todo changes)
    # =========================================================================

    def sync_todo_create(
        self,
        todo: TodoItem,
        db: Session
    ) -> bool:
        """Sync a newly created todo to Google.

        Args:
            todo: The created TodoItem
            db: Database session

        Returns:
            True if synced successfully
        """
        config = self.get_sync_config(todo.user_id, todo.character_id, db)
        if not config or not config.tasks_sync_enabled:
            return False

        credentials = google_auth_service.get_credentials(todo.user_id, db)
        if not credentials:
            return False

        try:
            self._create_google_task(todo, credentials, config.google_tasklist_id, db)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to sync todo create: {e}")
            return False

    def sync_todo_update(
        self,
        todo: TodoItem,
        db: Session
    ) -> bool:
        """Sync an updated todo to Google.

        Args:
            todo: The updated TodoItem
            db: Database session

        Returns:
            True if synced successfully
        """
        config = self.get_sync_config(todo.user_id, todo.character_id, db)
        if not config or not config.tasks_sync_enabled:
            return False

        credentials = google_auth_service.get_credentials(todo.user_id, db)
        if not credentials:
            return False

        # Get mapping
        mapping = db.query(TodoGoogleTaskMapping).filter_by(todo_id=todo.id).first()
        if not mapping:
            # No mapping - create new task
            return self.sync_todo_create(todo, db)

        try:
            self._push_to_google(todo, mapping, credentials, config.google_tasklist_id, db)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to sync todo update: {e}")
            return False

    def sync_todo_delete(
        self,
        todo_id: int,
        user_id: int,
        character_id: str,
        db: Session
    ) -> bool:
        """Sync a deleted todo to Google.

        Args:
            todo_id: The deleted todo ID
            user_id: User ID
            character_id: Character ID
            db: Database session

        Returns:
            True if synced successfully
        """
        config = self.get_sync_config(user_id, character_id, db)
        if not config or not config.tasks_sync_enabled:
            return False

        credentials = google_auth_service.get_credentials(user_id, db)
        if not credentials:
            return False

        # Get mapping
        mapping = db.query(TodoGoogleTaskMapping).filter_by(todo_id=todo_id).first()
        if not mapping:
            return True  # No mapping, nothing to delete on Google

        try:
            google_tasks_service.delete_task(
                credentials=credentials,
                tasklist_id=mapping.google_tasklist_id,
                task_id=mapping.google_task_id
            )
            db.delete(mapping)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to sync todo delete: {e}")
            return False

    def sync_todo_toggle(
        self,
        todo: TodoItem,
        db: Session
    ) -> bool:
        """Sync a todo completion toggle to Google.

        Args:
            todo: The toggled TodoItem
            db: Database session

        Returns:
            True if synced successfully
        """
        return self.sync_todo_update(todo, db)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _resolve_conflict(
        self,
        local_todo: TodoItem,
        google_task: Dict[str, Any],
        mapping: TodoGoogleTaskMapping
    ) -> str:
        """Resolve sync conflict using last-write-wins.

        Args:
            local_todo: MinouChat TodoItem
            google_task: Google Task dict
            mapping: Existing mapping record

        Returns:
            'push_to_google', 'pull_from_google', or 'no_change'
        """
        local_changed = local_todo.updated_at > mapping.local_updated_at
        google_updated = google_tasks_service.parse_google_timestamp(google_task.get('updated'))
        google_changed = google_updated and google_updated > mapping.google_updated_at

        if local_changed and google_changed:
            # Both changed - last write wins
            if local_todo.updated_at > google_updated:
                return 'push_to_google'
            else:
                return 'pull_from_google'
        elif local_changed:
            return 'push_to_google'
        elif google_changed:
            return 'pull_from_google'
        else:
            return 'no_change'

    def _create_google_task(
        self,
        todo: TodoItem,
        credentials,
        tasklist_id: str,
        db: Session
    ):
        """Create a Google Task from a local todo."""
        task_data = google_tasks_service.todo_to_google_task(todo)
        google_task = google_tasks_service.create_task(
            credentials=credentials,
            tasklist_id=tasklist_id,
            title=task_data['title'],
            notes=task_data.get('notes'),
            due=todo.due_date,
            status=task_data['status']
        )

        # Create mapping
        mapping = TodoGoogleTaskMapping(
            todo_id=todo.id,
            google_task_id=google_task['id'],
            google_tasklist_id=tasklist_id,
            local_updated_at=todo.updated_at,
            google_updated_at=google_tasks_service.parse_google_timestamp(google_task.get('updated')) or datetime.utcnow(),
            last_sync_at=datetime.utcnow(),
            sync_status='synced'
        )
        db.add(mapping)

    def _push_to_google(
        self,
        todo: TodoItem,
        mapping: TodoGoogleTaskMapping,
        credentials,
        tasklist_id: str,
        db: Session
    ):
        """Push local changes to Google."""
        google_task = google_tasks_service.update_task(
            credentials=credentials,
            tasklist_id=tasklist_id,
            task_id=mapping.google_task_id,
            title=todo.text,
            due=todo.due_date,
            status='completed' if todo.is_completed else 'needsAction'
        )

        # Update mapping
        mapping.local_updated_at = todo.updated_at
        mapping.google_updated_at = google_tasks_service.parse_google_timestamp(google_task.get('updated')) or datetime.utcnow()
        mapping.last_sync_at = datetime.utcnow()
        mapping.sync_status = 'synced'

    def _pull_from_google(
        self,
        todo: TodoItem,
        google_task: Dict[str, Any],
        mapping: TodoGoogleTaskMapping,
        db: Session
    ):
        """Pull Google changes to local."""
        data = google_tasks_service.google_task_to_todo_data(google_task)

        todo.text = data['text']
        todo.is_completed = 1 if data['is_completed'] else 0
        todo.priority = data.get('priority', 2)
        if data.get('due_date'):
            todo.due_date = data['due_date']
        if data['is_completed'] and not todo.completed_at:
            todo.completed_at = datetime.utcnow()
        elif not data['is_completed']:
            todo.completed_at = None
        todo.updated_at = datetime.utcnow()

        # Update mapping
        mapping.local_updated_at = todo.updated_at
        mapping.google_updated_at = google_tasks_service.parse_google_timestamp(google_task.get('updated')) or datetime.utcnow()
        mapping.last_sync_at = datetime.utcnow()
        mapping.sync_status = 'synced'

    def _create_local_todo(
        self,
        google_task: Dict[str, Any],
        user_id: int,
        character_id: str,
        tasklist_id: str,
        db: Session
    ):
        """Create a local todo from a Google Task."""
        data = google_tasks_service.google_task_to_todo_data(google_task)

        todo = TodoItem(
            user_id=user_id,
            character_id=character_id,
            text=data['text'],
            is_completed=1 if data['is_completed'] else 0,
            priority=data.get('priority', 2),
            due_date=data.get('due_date'),
            source_type='google_sync'
        )
        if data['is_completed']:
            todo.completed_at = datetime.utcnow()

        db.add(todo)
        db.flush()  # Get todo.id

        # Create mapping
        mapping = TodoGoogleTaskMapping(
            todo_id=todo.id,
            google_task_id=google_task['id'],
            google_tasklist_id=tasklist_id,
            local_updated_at=todo.updated_at,
            google_updated_at=google_tasks_service.parse_google_timestamp(google_task.get('updated')) or datetime.utcnow(),
            last_sync_at=datetime.utcnow(),
            sync_status='synced'
        )
        db.add(mapping)

    def _get_persona_name(self, character_id: str) -> str:
        """Get the display name of a persona."""
        try:
            character = character_manager.get_character(character_id)
            if character:
                return character.get('name', 'Unknown')
        except Exception:
            pass
        return 'Unknown'


# Singleton instance
google_sync_service = GoogleSyncService()
