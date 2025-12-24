"""
Unit tests for TrackingService - goals, todos, and habits tracking.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from miachat.api.core.tracking_service import TrackingService, tracking_service
from miachat.database.models import PersonaGoal, TodoItem, PersonaHabit, HabitCompletion, GoalProgressLog


class TestTrackingServiceGoals:
    """Tests for TrackingService goal management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TrackingService()
        self.mock_db = MagicMock()
        self.user_id = 1
        self.character_id = "test-char-123"

    def test_get_goals_returns_list(self):
        """Test getting goals returns a list."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.to_dict.return_value = {
            'id': 1,
            'title': 'Lose weight',
            'status': 'active',
            'current_value': 5,
            'target_value': 10
        }

        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_goal]
        self.mock_db.query.return_value = mock_query

        result = self.service.get_goals(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['title'] == 'Lose weight'

    def test_get_goals_filters_completed_by_default(self):
        """Test that completed goals are filtered out by default."""
        mock_query = MagicMock()
        filter_mock = MagicMock()
        mock_query.filter.return_value = filter_mock
        filter_mock.filter.return_value.order_by.return_value.all.return_value = []
        self.mock_db.query.return_value = mock_query

        self.service.get_goals(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db,
            include_completed=False
        )

        # Verify filter was called (for status != 'completed')
        assert filter_mock.filter.called

    def test_get_goals_includes_completed_when_requested(self):
        """Test that completed goals are included when requested."""
        mock_query = MagicMock()
        filter_mock = MagicMock()
        mock_query.filter.return_value = filter_mock
        filter_mock.order_by.return_value.all.return_value = []
        self.mock_db.query.return_value = mock_query

        self.service.get_goals(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db,
            include_completed=True
        )

        # Should call order_by directly without additional filter
        assert filter_mock.order_by.called

    def test_get_goal_by_id(self):
        """Test getting a single goal by ID."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.to_dict.return_value = {'id': 1, 'title': 'Test Goal'}

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_goal
        self.mock_db.query.return_value = mock_query

        result = self.service.get_goal(
            goal_id=1,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert result is not None
        assert result['id'] == 1

    def test_get_goal_returns_none_when_not_found(self):
        """Test getting nonexistent goal returns None."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = mock_query

        result = self.service.get_goal(
            goal_id=999,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert result is None

    def test_create_goal(self):
        """Test creating a new goal."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.to_dict.return_value = {
            'id': 1,
            'title': 'Read 12 books',
            'target_value': 12,
            'current_value': 0,
            'status': 'active'
        }

        with patch('miachat.api.core.tracking_service.PersonaGoal', return_value=mock_goal):
            result = self.service.create_goal(
                user_id=self.user_id,
                character_id=self.character_id,
                title='Read 12 books',
                target_value=12,
                unit='books',
                db=self.mock_db
            )

        assert result['title'] == 'Read 12 books'
        assert result['target_value'] == 12
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()

    def test_update_goal(self):
        """Test updating a goal."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.status = 'active'
        mock_goal.completed_at = None
        mock_goal.to_dict.return_value = {
            'id': 1,
            'title': 'Updated Goal',
            'status': 'active'
        }

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_goal
        self.mock_db.query.return_value = mock_query

        result = self.service.update_goal(
            goal_id=1,
            user_id=self.user_id,
            db=self.mock_db,
            title='Updated Goal'
        )

        assert result is not None
        assert mock_goal.title == 'Updated Goal'
        self.mock_db.commit.assert_called_once()

    def test_update_goal_marks_completed(self):
        """Test updating goal status to completed calls mark_completed."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.status = 'active'
        mock_goal.completed_at = None
        mock_goal.to_dict.return_value = {'id': 1, 'status': 'completed'}

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_goal
        self.mock_db.query.return_value = mock_query

        self.service.update_goal(
            goal_id=1,
            user_id=self.user_id,
            db=self.mock_db,
            status='completed'
        )

        mock_goal.mark_completed.assert_called_once()

    def test_log_goal_progress(self):
        """Test logging progress on a goal."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.current_value = 5
        mock_goal.target_value = 10
        mock_goal.to_dict.return_value = {
            'id': 1,
            'current_value': 7
        }

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_goal
        self.mock_db.query.return_value = mock_query

        with patch('miachat.api.core.tracking_service.GoalProgressLog'):
            result = self.service.log_goal_progress(
                goal_id=1,
                user_id=self.user_id,
                value_change=2,
                db=self.mock_db
            )

        assert result is not None
        assert mock_goal.current_value == 7  # 5 + 2

    def test_log_goal_progress_auto_completes(self):
        """Test that goal auto-completes when target is reached."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.current_value = 9
        mock_goal.target_value = 10
        mock_goal.to_dict.return_value = {'id': 1, 'current_value': 10}

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_goal
        self.mock_db.query.return_value = mock_query

        with patch('miachat.api.core.tracking_service.GoalProgressLog'):
            self.service.log_goal_progress(
                goal_id=1,
                user_id=self.user_id,
                value_change=1,
                db=self.mock_db
            )

        mock_goal.mark_completed.assert_called_once()

    def test_log_goal_progress_prevents_negative(self):
        """Test that progress can't go negative."""
        mock_goal = MagicMock(spec=PersonaGoal)
        mock_goal.current_value = 2
        mock_goal.target_value = 10
        mock_goal.to_dict.return_value = {'id': 1, 'current_value': 0}

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_goal
        self.mock_db.query.return_value = mock_query

        with patch('miachat.api.core.tracking_service.GoalProgressLog'):
            self.service.log_goal_progress(
                goal_id=1,
                user_id=self.user_id,
                value_change=-10,  # Try to subtract more than current
                db=self.mock_db
            )

        assert mock_goal.current_value == 0  # Should be clamped to 0

    def test_delete_goal(self):
        """Test deleting a goal."""
        mock_goal = MagicMock(spec=PersonaGoal)

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_goal
        self.mock_db.query.return_value = mock_query

        result = self.service.delete_goal(
            goal_id=1,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert result is True
        self.mock_db.delete.assert_called_once_with(mock_goal)
        self.mock_db.commit.assert_called_once()

    def test_delete_goal_returns_false_when_not_found(self):
        """Test deleting nonexistent goal returns False."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = mock_query

        result = self.service.delete_goal(
            goal_id=999,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert result is False
        self.mock_db.delete.assert_not_called()


class TestTrackingServiceTodos:
    """Tests for TrackingService todo management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TrackingService()
        self.mock_db = MagicMock()
        self.user_id = 1
        self.character_id = "test-char-123"

    def test_get_todos_returns_list(self):
        """Test getting todos returns a list."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.to_dict.return_value = {
            'id': 1,
            'text': 'Buy groceries',
            'is_completed': False
        }

        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_todo]
        self.mock_db.query.return_value = mock_query

        result = self.service.get_todos(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db
        )

        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_todos_filters_completed_by_default(self):
        """Test that completed todos are filtered out by default."""
        mock_query = MagicMock()
        filter_mock = MagicMock()
        mock_query.filter.return_value = filter_mock
        filter_mock.filter.return_value.order_by.return_value.all.return_value = []
        self.mock_db.query.return_value = mock_query

        self.service.get_todos(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db,
            include_completed=False
        )

        assert filter_mock.filter.called

    def test_create_todo(self):
        """Test creating a new todo."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.to_dict.return_value = {
            'id': 1,
            'text': 'Call dentist',
            'priority': 1,
            'is_completed': False
        }

        mock_count_query = MagicMock()
        mock_count_query.filter.return_value.count.return_value = 0
        self.mock_db.query.return_value = mock_count_query

        with patch('miachat.api.core.tracking_service.TodoItem', return_value=mock_todo):
            with patch('miachat.api.core.tracking_service._sync_todo_to_google'):
                result = self.service.create_todo(
                    user_id=self.user_id,
                    character_id=self.character_id,
                    text='Call dentist',
                    priority=1,
                    db=self.mock_db
                )

        assert result['text'] == 'Call dentist'
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()

    def test_toggle_todo_completes(self):
        """Test toggling incomplete todo to complete."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.is_completed = False
        mock_todo.completed_at = None
        mock_todo.character_id = self.character_id
        mock_todo.to_dict.return_value = {'id': 1, 'is_completed': True}

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_todo
        self.mock_db.query.return_value = mock_query

        with patch('miachat.api.core.tracking_service._sync_todo_to_google'):
            result = self.service.toggle_todo(
                todo_id=1,
                user_id=self.user_id,
                db=self.mock_db
            )

        assert mock_todo.is_completed == 1
        assert mock_todo.completed_at is not None

    def test_toggle_todo_uncompletes(self):
        """Test toggling complete todo back to incomplete."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.is_completed = True
        mock_todo.completed_at = datetime.utcnow()
        mock_todo.character_id = self.character_id
        mock_todo.to_dict.return_value = {'id': 1, 'is_completed': False}

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_todo
        self.mock_db.query.return_value = mock_query

        with patch('miachat.api.core.tracking_service._sync_todo_to_google'):
            result = self.service.toggle_todo(
                todo_id=1,
                user_id=self.user_id,
                db=self.mock_db
            )

        assert mock_todo.is_completed == 0
        assert mock_todo.completed_at is None

    def test_delete_todo(self):
        """Test deleting a todo."""
        mock_todo = MagicMock(spec=TodoItem)
        mock_todo.character_id = self.character_id

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_todo
        self.mock_db.query.return_value = mock_query

        # Patch the lazy import inside delete_todo
        mock_sync = MagicMock()
        with patch.dict('sys.modules', {'miachat.api.core.google_sync_service': mock_sync}):
            result = self.service.delete_todo(
                todo_id=1,
                user_id=self.user_id,
                db=self.mock_db
            )

        assert result is True
        self.mock_db.delete.assert_called_once()


class TestTrackingServiceHabits:
    """Tests for TrackingService habit management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TrackingService()
        self.mock_db = MagicMock()
        self.user_id = 1
        self.character_id = "test-char-123"

    def test_get_habits_returns_list(self):
        """Test getting habits returns a list."""
        mock_habit = MagicMock(spec=PersonaHabit)
        mock_habit.to_dict.return_value = {
            'id': 1,
            'title': 'Meditate',
            'current_streak': 5
        }

        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_habit]
        self.mock_db.query.return_value = mock_query

        result = self.service.get_habits(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db
        )

        assert isinstance(result, list)
        assert len(result) == 1

    def test_create_habit(self):
        """Test creating a new habit."""
        mock_habit = MagicMock(spec=PersonaHabit)
        mock_habit.to_dict.return_value = {
            'id': 1,
            'title': 'Exercise',
            'frequency': 'daily',
            'current_streak': 0
        }

        with patch('miachat.api.core.tracking_service.PersonaHabit', return_value=mock_habit):
            result = self.service.create_habit(
                user_id=self.user_id,
                character_id=self.character_id,
                title='Exercise',
                frequency='daily',
                db=self.mock_db
            )

        assert result['title'] == 'Exercise'
        self.mock_db.add.assert_called_once()

    def test_complete_habit_increments_streak(self):
        """Test completing habit increments streak on consecutive days."""
        yesterday = datetime.utcnow() - timedelta(days=1)

        mock_habit = MagicMock(spec=PersonaHabit)
        mock_habit.current_streak = 5
        mock_habit.longest_streak = 10
        mock_habit.last_completed_date = yesterday
        mock_habit.to_dict.return_value = {
            'id': 1,
            'current_streak': 6
        }

        mock_habit_query = MagicMock()
        mock_habit_query.filter.return_value.first.return_value = mock_habit

        mock_completion_query = MagicMock()
        mock_completion_query.filter.return_value.order_by.return_value.first.return_value = None

        def query_side_effect(model):
            if model == PersonaHabit:
                return mock_habit_query
            return mock_completion_query

        self.mock_db.query.side_effect = query_side_effect

        with patch('miachat.api.core.tracking_service.HabitCompletion'):
            result = self.service.complete_habit(
                habit_id=1,
                user_id=self.user_id,
                db=self.mock_db
            )

        assert mock_habit.current_streak == 6

    def test_complete_habit_resets_streak_on_gap(self):
        """Test streak resets when there's a gap."""
        two_days_ago = datetime.utcnow() - timedelta(days=2)

        mock_habit = MagicMock(spec=PersonaHabit)
        mock_habit.current_streak = 5
        mock_habit.longest_streak = 10
        mock_habit.last_completed_date = two_days_ago
        mock_habit.to_dict.return_value = {'id': 1, 'current_streak': 1}

        mock_habit_query = MagicMock()
        mock_habit_query.filter.return_value.first.return_value = mock_habit

        mock_completion_query = MagicMock()
        mock_completion_query.filter.return_value.order_by.return_value.first.return_value = None

        def query_side_effect(model):
            if model == PersonaHabit:
                return mock_habit_query
            return mock_completion_query

        self.mock_db.query.side_effect = query_side_effect

        with patch('miachat.api.core.tracking_service.HabitCompletion'):
            result = self.service.complete_habit(
                habit_id=1,
                user_id=self.user_id,
                db=self.mock_db
            )

        assert mock_habit.current_streak == 1  # Reset to 1

    def test_complete_habit_updates_longest_streak(self):
        """Test that longest streak is updated when current exceeds it."""
        yesterday = datetime.utcnow() - timedelta(days=1)

        mock_habit = MagicMock(spec=PersonaHabit)
        mock_habit.current_streak = 10
        mock_habit.longest_streak = 10
        mock_habit.last_completed_date = yesterday
        mock_habit.to_dict.return_value = {'id': 1, 'current_streak': 11, 'longest_streak': 11}

        mock_habit_query = MagicMock()
        mock_habit_query.filter.return_value.first.return_value = mock_habit

        mock_completion_query = MagicMock()
        mock_completion_query.filter.return_value.order_by.return_value.first.return_value = None

        def query_side_effect(model):
            if model == PersonaHabit:
                return mock_habit_query
            return mock_completion_query

        self.mock_db.query.side_effect = query_side_effect

        with patch('miachat.api.core.tracking_service.HabitCompletion'):
            self.service.complete_habit(
                habit_id=1,
                user_id=self.user_id,
                db=self.mock_db
            )

        assert mock_habit.longest_streak == 11

    def test_get_habit_stats(self):
        """Test getting habit statistics."""
        mock_habit = MagicMock(spec=PersonaHabit)
        mock_habit.current_streak = 5
        mock_habit.longest_streak = 10

        mock_completion = MagicMock(spec=HabitCompletion)
        mock_completion.completed_at = datetime.utcnow()

        mock_habit_query = MagicMock()
        mock_habit_query.filter.return_value.first.return_value = mock_habit

        mock_completion_query = MagicMock()
        mock_completion_query.filter.return_value.all.return_value = [mock_completion]

        def query_side_effect(model):
            if model == PersonaHabit:
                return mock_habit_query
            return mock_completion_query

        self.mock_db.query.side_effect = query_side_effect

        result = self.service.get_habit_stats(
            habit_id=1,
            user_id=self.user_id,
            db=self.mock_db,
            days=30
        )

        assert result['current_streak'] == 5
        assert result['longest_streak'] == 10
        assert result['days_analyzed'] == 30

    def test_delete_habit(self):
        """Test deleting a habit."""
        mock_habit = MagicMock(spec=PersonaHabit)

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_habit
        self.mock_db.query.return_value = mock_query

        result = self.service.delete_habit(
            habit_id=1,
            user_id=self.user_id,
            db=self.mock_db
        )

        assert result is True
        self.mock_db.delete.assert_called_once()


class TestTrackingServiceSummary:
    """Tests for TrackingService summary methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TrackingService()
        self.mock_db = MagicMock()
        self.user_id = 1
        self.character_id = "test-char-123"

    def test_get_tracking_summary(self):
        """Test getting tracking summary for sidebar badges."""
        # Mock goal count
        mock_goal_query = MagicMock()
        mock_goal_query.filter.return_value.filter.return_value.count.return_value = 3

        # Mock todo count
        mock_todo_query = MagicMock()
        mock_todo_query.filter.return_value.filter.return_value.count.return_value = 5

        # Mock habits
        mock_habit = MagicMock(spec=PersonaHabit)
        mock_habit.last_completed_date = datetime.utcnow()
        mock_habit_query = MagicMock()
        mock_habit_query.filter.return_value.filter.return_value.all.return_value = [mock_habit, MagicMock(last_completed_date=None)]

        call_count = [0]

        def query_side_effect(model):
            call_count[0] += 1
            if model == PersonaGoal:
                return mock_goal_query
            elif model == TodoItem:
                return mock_todo_query
            else:
                return mock_habit_query

        self.mock_db.query.side_effect = query_side_effect

        result = self.service.get_tracking_summary(
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db
        )

        assert 'goals' in result
        assert 'todos' in result
        assert 'habits' in result

    def test_get_tracking_context_empty(self):
        """Test tracking context returns empty string when no data."""
        with patch.object(self.service, 'get_goals', return_value=[]):
            with patch.object(self.service, 'get_todos', return_value=[]):
                with patch.object(self.service, 'get_habits', return_value=[]):
                    result = self.service.get_tracking_context(
                        user_id=self.user_id,
                        character_id=self.character_id,
                        db=self.mock_db
                    )

        assert result == ""

    def test_get_tracking_context_with_data(self):
        """Test tracking context formats data properly."""
        mock_goal = {'title': 'Run marathon', 'current_value': 10, 'target_value': 26, 'unit': 'miles', 'target_date': None}
        mock_todo = {'text': 'Buy running shoes', 'priority': 1, 'due_date': None}
        mock_habit = {'title': 'Morning run', 'current_streak': 7, 'completed_today': True}

        with patch.object(self.service, 'get_goals', return_value=[mock_goal]):
            with patch.object(self.service, 'get_todos', return_value=[mock_todo]):
                with patch.object(self.service, 'get_habits', return_value=[mock_habit]):
                    result = self.service.get_tracking_context(
                        user_id=self.user_id,
                        character_id=self.character_id,
                        db=self.mock_db
                    )

        assert "User's Active Goals" in result
        assert "Run marathon" in result
        assert "User's Active Todos" in result
        assert "Buy running shoes" in result
        assert "User's Habits" in result
        assert "Morning run" in result


class TestTrackingSingleton:
    """Test that tracking_service singleton works."""

    def test_singleton_instance(self):
        """Test that tracking_service is properly instantiated."""
        assert tracking_service is not None
        assert isinstance(tracking_service, TrackingService)
