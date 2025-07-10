"""
Conversation Manager with Character Versioning
Handles conversation sessions, character versions, and memory management
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from .models import CharacterVersion, ConversationSession, ChatMessage, CharacterUpdateEvent

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages conversation sessions with character versioning support."""
    
    def __init__(self, storage_dir: str = "conversations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        self.versions_file = self.storage_dir / "character_versions.json"
        self.messages_file = self.storage_dir / "messages.json"
        self._load_data()
    
    def _load_data(self):
        """Load existing data from storage."""
        self.sessions = self._load_json(self.sessions_file, {})
        self.character_versions = self._load_json(self.versions_file, {})
        self.messages = self._load_json(self.messages_file, {})
    
    def _load_json(self, file_path: Path, default: Any):
        """Load JSON data from file."""
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        return default
    
    def _save_json(self, file_path: Path, data: Any):
        """Save JSON data to file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
    
    def create_character_version(self, character_data: Dict, change_reason: str = "Initial version") -> CharacterVersion:
        """Create a new version of a character."""
        character_id = character_data['id']
        
        # Get next version number
        existing_versions = [v for v in self.character_versions.values() 
                           if v['character_id'] == character_id]
        next_version = max([v['version'] for v in existing_versions], default=0) + 1
        
        # Create new version
        version = CharacterVersion(
            character_id=character_id,
            version=next_version,
            system_prompt=character_data['system_prompt'],
            personality=character_data['personality'],
            traits=character_data.get('traits'),
            communication_style=character_data.get('communication_style'),
            created_at=datetime.now(),
            is_active=True,
            change_reason=change_reason
        )
        
        # Deactivate previous versions
        for v in existing_versions:
            v['is_active'] = False
        
        # Save new version
        version_key = f"{character_id}_v{next_version}"
        self.character_versions[version_key] = version.dict()
        self._save_json(self.versions_file, self.character_versions)
        
        logger.info(f"Created character version {next_version} for {character_id}")
        return version
    
    def get_latest_version(self, character_id: str) -> Optional[CharacterVersion]:
        """Get the latest active version of a character."""
        versions = [v for v in self.character_versions.values() 
                   if v['character_id'] == character_id and v['is_active']]
        if not versions:
            return None
        
        latest = max(versions, key=lambda v: v['version'])
        return CharacterVersion(**latest)
    
    def create_conversation_session(self, character_id: str, user_id: str) -> ConversationSession:
        """Create a new conversation session."""
        # Get latest character version
        character_version = self.get_latest_version(character_id)
        if not character_version:
            raise ValueError(f"No active version found for character {character_id}")
        
        session = ConversationSession(
            session_id=str(uuid.uuid4()),
            character_id=character_id,
            character_version=character_version.version,
            user_id=user_id,
            started_at=datetime.now(),
            last_activity=datetime.now(),
            message_count=0
        )
        
        self.sessions[session.session_id] = session.dict()
        self._save_json(self.sessions_file, self.sessions)
        
        logger.info(f"Created conversation session {session.session_id} for character {character_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get a conversation session by ID."""
        session_data = self.sessions.get(session_id)
        if session_data:
            return ConversationSession(**session_data)
        return None
    
    def save_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        """Save a chat message."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            character_version=session.character_version
        )
        
        # Save message
        message_key = f"{session_id}_{message.timestamp.isoformat()}"
        self.messages[message_key] = message.dict()
        
        # Update session
        session.last_activity = datetime.now()
        session.message_count += 1
        self.sessions[session_id] = session.dict()
        
        # Save data
        self._save_json(self.messages_file, self.messages)
        self._save_json(self.sessions_file, self.sessions)
        
        return message
    
    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[ChatMessage]:
        """Get conversation history for a session."""
        session_messages = [
            msg for key, msg in self.messages.items() 
            if msg['session_id'] == session_id
        ]
        
        # Sort by timestamp and limit
        sorted_messages = sorted(session_messages, key=lambda m: m['timestamp'])[-limit:]
        return [ChatMessage(**msg) for msg in sorted_messages]
    
    def check_version_compatibility(self, session_id: str) -> Optional[CharacterUpdateEvent]:
        """Check if a session needs to be updated due to character changes."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        current_version = self.get_latest_version(session.character_id)
        if not current_version:
            return None
        
        if current_version.version > session.character_version:
            # Character has been updated
            return CharacterUpdateEvent(
                character_id=session.character_id,
                old_version=session.character_version,
                new_version=current_version.version,
                updated_at=datetime.now(),
                changes={
                    "system_prompt_changed": True,
                    "personality_changed": True
                },
                migration_required=True
            )
        
        return None
    
    def migrate_session(self, session_id: str, user_choice: str = "auto") -> bool:
        """Migrate a session to the latest character version."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        current_version = self.get_latest_version(session.character_id)
        if not current_version or current_version.version == session.character_version:
            return True  # No migration needed
        
        if user_choice == "auto":
            # Auto-migrate: update session to new version
            session.character_version = current_version.version
            self.sessions[session_id] = session.dict()
            self._save_json(self.sessions_file, self.sessions)
            
            logger.info(f"Auto-migrated session {session_id} to version {current_version.version}")
            return True
        
        elif user_choice == "new_session":
            # Create new session with latest version
            new_session = self.create_conversation_session(session.character_id, session.user_id)
            return True
        
        return False
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        sessions_to_remove = []
        for session_id, session_data in self.sessions.items():
            last_activity = datetime.fromisoformat(session_data['last_activity'])
            if last_activity < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
        
        if sessions_to_remove:
            self._save_json(self.sessions_file, self.sessions)
            logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
    
    def get_character_version_history(self, character_id: str) -> List[CharacterVersion]:
        """Get version history for a character."""
        versions = [
            v for v in self.character_versions.values() 
            if v['character_id'] == character_id
        ]
        sorted_versions = sorted(versions, key=lambda v: v['version'])
        return [CharacterVersion(**v) for v in sorted_versions] 