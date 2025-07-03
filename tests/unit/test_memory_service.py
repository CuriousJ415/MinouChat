"""
Unit tests for MemoryService.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from miachat.api.core.memory_service import MemoryService
from miachat.database.models import Conversation, Message


class TestMemoryService:
    """Test cases for MemoryService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.memory_service = MemoryService(default_context_window=5)
        self.mock_db = Mock()
    
    def test_extract_keywords(self):
        """Test keyword extraction from text."""
        # Test basic keyword extraction
        text = "Hello, how are you doing today?"
        keywords = self.memory_service._extract_keywords(text)
        assert "hello" in keywords
        assert "doing" in keywords
        assert "today" in keywords
        
        # Test stop word filtering
        text = "The cat and the dog are running"
        keywords = self.memory_service._extract_keywords(text)
        assert "the" not in keywords
        assert "and" not in keywords
        assert "are" not in keywords
        assert "cat" in keywords
        assert "dog" in keywords
        assert "running" in keywords
        
        # Test short word filtering
        text = "I am a cat"
        keywords = self.memory_service._extract_keywords(text)
        assert "am" not in keywords  # too short
        assert "cat" in keywords
        
        # Test duplicate removal
        text = "cat cat dog cat"
        keywords = self.memory_service._extract_keywords(text)
        assert keywords.count("cat") == 1
        assert "dog" in keywords
    
    def test_combine_context(self):
        """Test combining recent and relevant messages."""
        recent_messages = [
            {"id": 1, "role": "user", "content": "Hello", "timestamp": "2023-01-01T10:00:00"},
            {"id": 2, "role": "assistant", "content": "Hi there!", "timestamp": "2023-01-01T10:01:00"},
        ]
        
        relevant_messages = [
            {"id": 2, "role": "assistant", "content": "Hi there!", "timestamp": "2023-01-01T10:01:00"},  # duplicate
            {"id": 3, "role": "user", "content": "How are you?", "timestamp": "2023-01-01T09:00:00"},  # older
        ]
        
        combined = self.memory_service._combine_context(recent_messages, relevant_messages)
        
        # Should have 3 unique messages
        assert len(combined) == 3
        
        # Should be sorted by timestamp
        assert combined[0]["id"] == 3  # oldest
        assert combined[1]["id"] == 1
        assert combined[2]["id"] == 2  # newest
        
        # Should not have duplicates
        ids = [msg["id"] for msg in combined]
        assert len(ids) == len(set(ids))
    
    @patch('miachat.api.core.memory_service.text')
    def test_search_conversation(self, mock_text):
        """Test conversation search functionality."""
        # Mock database query results
        mock_result = [
            (1, "user", "Hello there", datetime.now(), {}),
            (2, "assistant", "Hi! How can I help?", datetime.now(), {}),
        ]
        
        mock_execute = Mock()
        mock_execute.__iter__ = Mock(return_value=iter(mock_result))
        self.mock_db.execute = Mock(return_value=mock_execute)
        
        # Mock keyword extraction
        with patch.object(self.memory_service, '_extract_keywords', return_value=['hello']):
            results = self.memory_service._search_conversation(1, "Hello there", self.mock_db)
        
        assert len(results) == 2
        assert results[0]["role"] == "user"
        assert results[1]["role"] == "assistant"
    
    def test_get_conversation_summary(self):
        """Test conversation summary generation."""
        # Mock conversation and messages
        mock_conversation = Mock()
        mock_conversation.id = 1
        mock_conversation.started_at = datetime(2023, 1, 1, 10, 0, 0)
        mock_conversation.ended_at = None
        mock_conversation.is_active.return_value = True
        
        mock_messages = [
            Mock(role="user", content="Hello"),
            Mock(role="assistant", content="Hi!"),
            Mock(role="user", content="How are you?"),
        ]
        mock_conversation.get_messages.return_value = mock_messages
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_conversation
        
        summary = self.memory_service.get_conversation_summary(1, self.mock_db)
        
        assert summary["conversation_id"] == 1
        assert summary["total_messages"] == 3
        assert summary["user_messages"] == 2
        assert summary["assistant_messages"] == 1
        assert summary["is_active"] is True
    
    def test_get_context_fallback(self):
        """Test that get_context falls back to recent messages on error."""
        # Mock _get_recent_messages to work
        with patch.object(self.memory_service, '_get_recent_messages') as mock_recent:
            mock_recent.return_value = [{"id": 1, "role": "user", "content": "Hello"}]
            
            # Mock _search_conversation to raise an exception
            with patch.object(self.memory_service, '_search_conversation', side_effect=Exception("Search error")):
                context = self.memory_service.get_context(1, "test message", db=self.mock_db)
        
        # Should fall back to just recent messages
        assert len(context) == 1
        assert context[0]["content"] == "Hello"
    
    def test_default_context_window(self):
        """Test that default context window is used when none specified."""
        memory_service = MemoryService(default_context_window=15)
        assert memory_service.default_context_window == 15
        
        # Test that it's used when context_window is None
        with patch.object(memory_service, '_get_recent_messages') as mock_recent:
            mock_recent.return_value = []
            with patch.object(memory_service, '_search_conversation', return_value=[]):
                memory_service.get_context(1, "test", context_window=None, db=self.mock_db)
                mock_recent.assert_called_with(1, 15, self.mock_db)
    
    def test_custom_context_window(self):
        """Test that custom context window overrides default."""
        memory_service = MemoryService(default_context_window=10)
        
        with patch.object(memory_service, '_get_recent_messages') as mock_recent:
            mock_recent.return_value = []
            with patch.object(memory_service, '_search_conversation', return_value=[]):
                memory_service.get_context(1, "test", context_window=20, db=self.mock_db)
                mock_recent.assert_called_with(1, 20, self.mock_db)


class TestMemoryServiceIntegration:
    """Integration tests for MemoryService with real database."""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        from miachat.database.config import DatabaseConfig
        from miachat.database.models import Base
        import tempfile
        import os
        
        # Use a temporary database
        db_fd, db_path = tempfile.mkstemp()
        db_url = f"sqlite:///{db_path}"
        db_config = DatabaseConfig(db_url)
        Base.metadata.create_all(bind=db_config.engine)
        
        session = db_config.get_session()
        yield session
        
        session.close()
        os.close(db_fd)
        os.unlink(db_path)
    
    def test_full_context_retrieval(self, db_session):
        """Test full context retrieval with real database."""
        from miachat.database.models import Conversation, Message
        
        # Create a conversation
        conversation = Conversation(
            personality_id=1,
            conversation_data={"character_id": "test-char"}
        )
        db_session.add(conversation)
        db_session.commit()
        db_session.refresh(conversation)
        
        # Add some messages
        messages = [
            Message(conversation_id=conversation.id, role="user", content="Hello there"),
            Message(conversation_id=conversation.id, role="assistant", content="Hi! How can I help?"),
            Message(conversation_id=conversation.id, role="user", content="Tell me about cats"),
            Message(conversation_id=conversation.id, role="assistant", content="Cats are amazing pets"),
        ]
        
        for msg in messages:
            db_session.add(msg)
        db_session.commit()
        
        # Test context retrieval
        memory_service = MemoryService(default_context_window=3)
        context = memory_service.get_context(
            conversation_id=conversation.id,
            current_message="What about dogs?",
            db=db_session
        )
        
        # Should have recent messages (last 3) plus relevant messages about cats
        assert len(context) >= 3
        
        # Check that we have the cat-related messages
        cat_messages = [msg for msg in context if "cat" in msg["content"].lower()]
        assert len(cat_messages) > 0 