"""
Unit tests for sidebar document services (todos, life areas).
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Import services
from miachat.api.core.todo_service import TodoService
from miachat.api.core.life_area_service import LifeAreaService
from miachat.database.models import TodoItem, LifeAreaScore, LIFE_AREAS


class TestTodoService:
    """Tests for TodoService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TodoService()
        self.mock_db = MagicMock()
        self.user_id = 1
        self.character_id = "test-char-123"

    def test_create_todo_basic(self):
        """Test creating a basic todo item."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.id = 1
        mock_todo.text = "Buy groceries"
        mock_todo.priority = 2
        mock_todo.is_completed = False
        mock_todo.source_type = 'manual'
        mock_todo.to_dict.return_value = {
            'id': 1,
            'text': 'Buy groceries',
            'priority': 2,
            'is_completed': False,
            'source_type': 'manual'
        }

        self.mock_db.add = MagicMock()
        self.mock_db.commit = MagicMock()
        self.mock_db.refresh = MagicMock()

        with patch('miachat.api.core.todo_service.TodoItem', return_value=mock_todo):
            result = self.service.create_todo(
                user_id=self.user_id,
                character_id=self.character_id,
                text="Buy groceries",
                priority=2,
                source_type='manual',
                db=self.mock_db
            )

        assert result['text'] == 'Buy groceries'
        assert result['priority'] == 2
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()

    def test_toggle_todo(self):
        """Test toggling todo completion status."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.id = 1
        mock_todo.user_id = self.user_id
        mock_todo.is_completed = False
        mock_todo.to_dict.return_value = {
            'id': 1,
            'is_completed': True
        }

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_todo
        self.mock_db.query.return_value = mock_query

        result = self.service.toggle_todo(
            todo_id=1,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert mock_todo.is_completed == True
        self.mock_db.commit.assert_called_once()

    def test_delete_todo(self):
        """Test deleting a todo item."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.id = 1
        mock_todo.user_id = self.user_id

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_todo
        self.mock_db.query.return_value = mock_query

        result = self.service.delete_todo(
            todo_id=1,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert result == True
        self.mock_db.delete.assert_called_once_with(mock_todo)
        self.mock_db.commit.assert_called_once()

    def test_delete_nonexistent_todo(self):
        """Test deleting a todo that doesn't exist."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = mock_query

        result = self.service.delete_todo(
            todo_id=999,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert result == False
        self.mock_db.delete.assert_not_called()


class TestLifeAreaService:
    """Tests for LifeAreaService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = LifeAreaService()
        self.mock_db = MagicMock()
        self.user_id = 1
        self.character_id = "coach-char-123"

    def test_life_areas_constant(self):
        """Test that all 10 life areas are defined."""
        assert len(LIFE_AREAS) == 10
        assert 'career' in LIFE_AREAS
        assert 'health' in LIFE_AREAS
        assert 'relationships' in LIFE_AREAS
        assert 'finances' in LIFE_AREAS
        assert 'growth' in LIFE_AREAS

    def test_get_areas_list(self):
        """Test getting list of areas with display names."""
        areas = self.service.get_areas_list()

        assert len(areas) == 10
        # Check display names
        career_area = next(a for a in areas if a['id'] == 'career')
        assert career_area['name'] == 'Career/Work'

    def test_update_score_creates_new(self):
        """Test creating a new life area score."""
        mock_score = MagicMock(spec=LifeAreaScore)
        mock_score.id = 1
        mock_score.area = 'health'
        mock_score.score = 7
        mock_score.to_dict.return_value = {
            'id': 1,
            'area': 'health',
            'score': 7,
            'source_type': 'manual'
        }

        # No existing score
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = mock_query

        with patch('miachat.api.core.life_area_service.LifeAreaScore', return_value=mock_score):
            result = self.service.update_score(
                user_id=self.user_id,
                character_id=self.character_id,
                area='health',
                score=7,
                source_type='manual',
                db=self.mock_db
            )

        assert result['area'] == 'health'
        assert result['score'] == 7
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()

    def test_update_score_updates_existing(self):
        """Test updating an existing life area score."""
        existing_score = MagicMock(spec=LifeAreaScore)
        existing_score.id = 1
        existing_score.area = 'health'
        existing_score.score = 5
        existing_score.notes = None
        existing_score.to_dict.return_value = {
            'id': 1,
            'area': 'health',
            'score': 8,
            'source_type': 'manual'
        }

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = existing_score
        self.mock_db.query.return_value = mock_query

        result = self.service.update_score(
            user_id=self.user_id,
            character_id=self.character_id,
            area='health',
            score=8,
            source_type='manual',
            db=self.mock_db
        )

        assert existing_score.score == 8
        self.mock_db.add.assert_not_called()  # Should update, not add
        self.mock_db.commit.assert_called_once()

    def test_update_score_invalid_area(self):
        """Test that invalid areas raise ValueError."""
        with pytest.raises(ValueError, match="Invalid area"):
            self.service.update_score(
                user_id=self.user_id,
                character_id=self.character_id,
                area='invalid_area',
                score=5,
                db=self.mock_db
            )

    def test_update_score_invalid_score_too_low(self):
        """Test that score below 1 raises ValueError."""
        with pytest.raises(ValueError, match="Score must be between"):
            self.service.update_score(
                user_id=self.user_id,
                character_id=self.character_id,
                area='health',
                score=0,
                db=self.mock_db
            )

    def test_update_score_invalid_score_too_high(self):
        """Test that score above 10 raises ValueError."""
        with pytest.raises(ValueError, match="Score must be between"):
            self.service.update_score(
                user_id=self.user_id,
                character_id=self.character_id,
                area='health',
                score=11,
                db=self.mock_db
            )

    def test_get_scorecard_with_missing_areas(self):
        """Test that scorecard fills missing areas with default score of 5."""
        # Only return 2 existing scores
        mock_score1 = MagicMock(spec=LifeAreaScore)
        mock_score1.area = 'health'
        mock_score1.to_dict.return_value = {'area': 'health', 'score': 8}

        mock_score2 = MagicMock(spec=LifeAreaScore)
        mock_score2.area = 'career'
        mock_score2.to_dict.return_value = {'area': 'career', 'score': 6}

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_score1, mock_score2]
        self.mock_db.query.return_value = mock_query

        scorecard = self.service.get_scorecard(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db
        )

        # Should have all 10 areas
        assert len(scorecard) == 10

        # Existing scores should be present
        assert scorecard['health']['score'] == 8
        assert scorecard['career']['score'] == 6

        # Missing areas should default to 5
        assert scorecard['finances']['score'] == 5
        assert scorecard['relationships']['score'] == 5

    def test_get_average_score(self):
        """Test calculating average score."""
        # Mock 3 scores: 6, 8, 7 -> average 7.0
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [(6,), (8,), (7,)]
        self.mock_db.query.return_value = mock_query

        average = self.service.get_average_score(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db
        )

        assert average == 7.0

    def test_get_average_score_no_ratings(self):
        """Test average returns 5.0 when no ratings exist."""
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        self.mock_db.query.return_value = mock_query

        average = self.service.get_average_score(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db
        )

        assert average == 5.0


class TestSidebarExtractionService:
    """Tests for SidebarExtractionService."""

    def setup_method(self):
        """Set up test fixtures."""
        from miachat.api.core.sidebar_extraction_service import SidebarExtractionService
        self.service = SidebarExtractionService()

    def test_should_extract_todos_positive(self):
        """Test that todo trigger phrases are detected."""
        positive_cases = [
            "add buy milk to my todo list",
            "remind me to call mom tomorrow",
            "I need to finish the report",
            "don't forget to email John",
            "I have to pick up the kids",
            "make sure I book the hotel"
        ]

        for msg in positive_cases:
            assert self.service.should_extract_todos(msg), f"Should trigger for: {msg}"

    def test_should_extract_todos_negative(self):
        """Test that unrelated messages don't trigger todo extraction."""
        negative_cases = [
            "How are you today?",
            "What's the weather like?",
            "Tell me about yourself",
            "I like pizza"
        ]

        for msg in negative_cases:
            assert not self.service.should_extract_todos(msg), f"Should NOT trigger for: {msg}"

    def test_should_extract_life_areas_positive(self):
        """Test that life area rating phrases are detected."""
        positive_cases = [
            "my health is at a 7",
            "my career feels like a 4",
            "rate my finances as 8",
            "I'd say my relationships are at 6",
            "6 out of 10 for my growth"
        ]

        for msg in positive_cases:
            assert self.service.should_extract_life_areas(msg), f"Should trigger for: {msg}"

    def test_should_extract_life_areas_negative(self):
        """Test that unrelated messages don't trigger life area extraction."""
        negative_cases = [
            "How's your health?",
            "Tell me about career options",
            "What should I do for growth?",
            "I feel happy today"
        ]

        for msg in negative_cases:
            assert not self.service.should_extract_life_areas(msg), f"Should NOT trigger for: {msg}"

    def test_parse_json_array_direct(self):
        """Test parsing a direct JSON array."""
        result = self.service._parse_json_array('[{"text": "Buy milk"}]')
        assert result == [{"text": "Buy milk"}]

    def test_parse_json_array_markdown_code_block(self):
        """Test parsing JSON from markdown code block."""
        text = '```json\n[{"text": "Test"}]\n```'
        result = self.service._parse_json_array(text)
        assert result == [{"text": "Test"}]

    def test_parse_json_array_embedded(self):
        """Test parsing JSON embedded in other text."""
        text = 'Here are the todos: [{"text": "Item 1"}, {"text": "Item 2"}] and more text'
        result = self.service._parse_json_array(text)
        assert len(result) == 2

    def test_parse_json_array_invalid(self):
        """Test that invalid JSON returns None."""
        result = self.service._parse_json_array("not json at all")
        assert result is None
