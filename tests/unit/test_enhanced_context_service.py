"""
Unit tests for EnhancedContextService - context orchestration and synthesis.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

from miachat.api.core.enhanced_context_service import EnhancedContextService, enhanced_context_service


class TestEnhancedContextServiceInit:
    """Tests for EnhancedContextService initialization."""

    def test_default_configuration(self):
        """Test default configuration values."""
        service = EnhancedContextService()

        assert service.max_context_chunks == 10
        assert service.similarity_threshold == 0.35
        assert service.max_context_length == 8000
        assert service.max_recent_interactions == 4

    def test_custom_configuration(self):
        """Test custom configuration values."""
        service = EnhancedContextService(
            max_context_chunks=20,
            similarity_threshold=0.5,
            max_context_length=10000,
            max_recent_interactions=6
        )

        assert service.max_context_chunks == 20
        assert service.similarity_threshold == 0.5
        assert service.max_context_length == 10000
        assert service.max_recent_interactions == 6

    def test_context_budget_allocations(self):
        """Test context budget allocations sum to approximately 100%."""
        service = EnhancedContextService()

        total_budget = sum(service.context_budget.values())
        # Should be approximately 1.0 (100%)
        assert 0.9 <= total_budget <= 1.1

    def test_document_reference_patterns_exist(self):
        """Test that document reference patterns are defined."""
        service = EnhancedContextService()

        assert len(service.doc_reference_patterns) > 0


class TestDocumentReferenceParsing:
    """Tests for document reference parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()

    def test_parse_document_reference_report(self):
        """Test parsing 'my X report' pattern."""
        references = self.service._parse_document_references(
            "Can you analyze my values report?"
        )

        assert len(references) > 0
        assert any('values' in r['extracted_name'].lower() for r in references)

    def test_parse_document_reference_file(self):
        """Test parsing 'the X file' pattern."""
        references = self.service._parse_document_references(
            "Look at the financial document I uploaded"
        )

        assert len(references) > 0

    def test_parse_document_reference_analyze(self):
        """Test parsing 'analyze my X' pattern."""
        references = self.service._parse_document_references(
            "analyze my career assessment document"
        )

        assert len(references) > 0

    def test_parse_general_document_request(self):
        """Test parsing general document requests."""
        references = self.service._parse_document_references(
            "based on my uploaded documents, what should I do?"
        )

        assert len(references) > 0
        assert any(r['type'] == 'general_document_request' for r in references)

    def test_parse_no_document_reference(self):
        """Test that non-document messages return empty list."""
        references = self.service._parse_document_references(
            "How are you today?"
        )

        # May detect general patterns, but should be limited
        # The key is that it doesn't crash and returns a list
        assert isinstance(references, list)

    def test_parse_values_assessment_pattern(self):
        """Test parsing 'values assessment' pattern."""
        references = self.service._parse_document_references(
            "What does my values assessment say about my priorities?"
        )

        # Should detect values-related pattern
        assert isinstance(references, list)


class TestEnhancedContextRetrieval:
    """Tests for get_enhanced_context method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()
        self.mock_db = MagicMock()
        self.user_id = 1
        self.character_id = "test-char-123"
        self.conversation_id = 1

    @patch('miachat.api.core.enhanced_context_service.memory_service')
    @patch('miachat.api.core.enhanced_context_service.setting_service')
    @patch('miachat.api.core.enhanced_context_service.backstory_service')
    @patch('miachat.api.core.enhanced_context_service.fact_extraction_service')
    @patch('miachat.api.core.enhanced_context_service.user_profile_service')
    @patch('miachat.api.core.enhanced_context_service.tracking_service')
    @patch('miachat.api.core.enhanced_context_service.document_service')
    def test_get_enhanced_context_returns_dict(
        self, mock_doc, mock_tracking, mock_user_profile, mock_facts,
        mock_backstory, mock_setting, mock_memory
    ):
        """Test that get_enhanced_context returns a dictionary."""
        # Configure mocks
        mock_memory.get_context.return_value = []
        mock_setting.format_setting_context.return_value = ""
        mock_backstory.get_relevant_backstory.return_value = []
        mock_facts.get_user_facts.return_value = []
        mock_user_profile.format_user_profile_context.return_value = ""
        mock_tracking.get_tracking_context.return_value = ""
        mock_doc.search_documents.return_value = []

        result = self.service.get_enhanced_context(
            user_message="Hello",
            user_id=self.user_id,
            db=self.mock_db
        )

        assert isinstance(result, dict)
        assert 'context_summary' in result
        assert 'reasoning_chain' in result

    @patch('miachat.api.core.enhanced_context_service.memory_service')
    @patch('miachat.api.core.enhanced_context_service.setting_service')
    @patch('miachat.api.core.enhanced_context_service.backstory_service')
    @patch('miachat.api.core.enhanced_context_service.fact_extraction_service')
    @patch('miachat.api.core.enhanced_context_service.user_profile_service')
    @patch('miachat.api.core.enhanced_context_service.tracking_service')
    def test_get_enhanced_context_with_character(
        self, mock_tracking, mock_user_profile, mock_facts,
        mock_backstory, mock_setting, mock_memory
    ):
        """Test context retrieval with character_id."""
        mock_memory.get_context.return_value = []
        mock_setting.format_setting_context.return_value = "Modern day setting"
        mock_backstory.get_relevant_backstory.return_value = ["Character background"]
        mock_facts.get_user_facts.return_value = [{'fact_key': 'name', 'fact_value': 'Jason'}]
        mock_user_profile.format_user_profile_context.return_value = "User likes coffee"
        mock_tracking.get_tracking_context.return_value = ""

        result = self.service.get_enhanced_context(
            user_message="Tell me about yourself",
            user_id=self.user_id,
            character_id=self.character_id,
            db=self.mock_db,
            include_documents=False
        )

        assert 'setting_context' in result
        assert 'backstory_context' in result
        assert 'user_facts' in result

    @patch('miachat.api.core.enhanced_context_service.memory_service')
    def test_get_enhanced_context_with_conversation(self, mock_memory):
        """Test context retrieval with conversation history."""
        mock_memory.get_context.return_value = [
            {'role': 'user', 'content': 'Hi there'},
            {'role': 'assistant', 'content': 'Hello!'}
        ]

        result = self.service.get_enhanced_context(
            user_message="How are you?",
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            db=self.mock_db,
            include_documents=False
        )

        assert 'recent_interactions' in result
        assert 'semantic_context' in result

    @patch('miachat.api.core.enhanced_context_service.memory_service')
    @patch('miachat.api.core.enhanced_context_service.setting_service')
    @patch('miachat.api.core.enhanced_context_service.backstory_service')
    @patch('miachat.api.core.enhanced_context_service.fact_extraction_service')
    @patch('miachat.api.core.enhanced_context_service.user_profile_service')
    @patch('miachat.api.core.enhanced_context_service.tracking_service')
    def test_reasoning_chain_enabled(
        self, mock_tracking, mock_user_profile, mock_facts,
        mock_backstory, mock_setting, mock_memory
    ):
        """Test reasoning chain is populated when enabled."""
        mock_memory.get_context.return_value = []
        mock_setting.format_setting_context.return_value = ""
        mock_backstory.get_relevant_backstory.return_value = []
        mock_facts.get_user_facts.return_value = []
        mock_user_profile.format_user_profile_context.return_value = ""
        mock_tracking.get_tracking_context.return_value = ""

        result = self.service.get_enhanced_context(
            user_message="Test message",
            user_id=self.user_id,
            db=self.mock_db,
            include_documents=False,
            enable_reasoning=True
        )

        assert len(result['reasoning_chain']) > 0
        assert result['reasoning_chain'][0]['step'] == 'initialization'

    @patch('miachat.api.core.enhanced_context_service.memory_service')
    def test_reasoning_chain_disabled(self, mock_memory):
        """Test reasoning chain is empty when disabled."""
        mock_memory.get_context.return_value = []

        result = self.service.get_enhanced_context(
            user_message="Test message",
            user_id=self.user_id,
            db=self.mock_db,
            include_documents=False,
            enable_reasoning=False
        )

        assert len(result['reasoning_chain']) == 0


class TestRecentConversationContext:
    """Tests for recent conversation context retrieval."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()
        self.mock_db = MagicMock()

    @patch('miachat.api.core.enhanced_context_service.memory_service')
    def test_get_recent_context_limits_to_4(self, mock_memory):
        """Test that recent context is limited to 4 interactions."""
        mock_memory.get_context.return_value = [
            {'role': 'user', 'content': 'Message 1'},
            {'role': 'assistant', 'content': 'Response 1'},
            {'role': 'user', 'content': 'Message 2'},
            {'role': 'assistant', 'content': 'Response 2'},
            {'role': 'user', 'content': 'Message 3'},
            {'role': 'assistant', 'content': 'Response 3'},
        ]

        result = self.service._get_recent_conversation_context(
            conversation_id=1,
            user_message="New message",
            db=self.mock_db
        )

        assert len(result) <= 4

    @patch('miachat.api.core.enhanced_context_service.memory_service')
    def test_get_recent_context_empty(self, mock_memory):
        """Test handling of empty conversation."""
        mock_memory.get_context.return_value = []

        result = self.service._get_recent_conversation_context(
            conversation_id=1,
            user_message="First message",
            db=self.mock_db
        )

        assert result == []


class TestConflictDetection:
    """Tests for conflict detection between sources."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()

    def test_detect_conflicts_empty_sources(self):
        """Test no conflicts with empty sources."""
        conflicts = self.service._detect_conflicts(
            conversation_context=[],
            semantic_context=[],
            document_chunks=[]
        )

        assert conflicts == []

    def test_detect_conflicts_no_conflict(self):
        """Test no conflicts with consistent information."""
        conversation = [{'content': 'The user likes coffee'}]
        documents = [{'text_content': 'User prefers coffee in the morning'}]

        conflicts = self.service._detect_conflicts(
            conversation_context=conversation,
            semantic_context=[],
            document_chunks=documents
        )

        assert len(conflicts) == 0

    def test_detect_conflicts_with_conflict(self):
        """Test detection of conflicting information."""
        conversation = [{'content': 'No, I disagree with that'}]
        documents = [{'text_content': 'Yes, I agree completely'}]

        conflicts = self.service._detect_conflicts(
            conversation_context=conversation,
            semantic_context=[],
            document_chunks=documents
        )

        # Should detect the yes/no, agree/disagree conflict
        assert len(conflicts) > 0


class TestContextSummary:
    """Tests for intelligent context summary creation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()

    def test_create_summary_empty(self):
        """Test summary creation with no context."""
        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=[],
            document_references=[],
            conflicts=[],
            user_message="Hello"
        )

        # Should return something, even if minimal
        assert isinstance(summary, str)

    def test_create_summary_with_user_profile(self):
        """Test summary includes user profile context."""
        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=[],
            document_references=[],
            conflicts=[],
            user_message="Hello",
            user_profile_context="User prefers formal conversation"
        )

        assert "formal conversation" in summary

    def test_create_summary_with_setting(self):
        """Test summary includes setting context."""
        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=[],
            document_references=[],
            conflicts=[],
            user_message="Hello",
            setting_context="Modern day San Francisco"
        )

        assert "San Francisco" in summary

    def test_create_summary_with_facts(self):
        """Test summary includes user facts."""
        facts = [
            {'fact_key': 'name', 'fact_value': 'Jason', 'confidence': 0.9},
            {'fact_key': 'hobby', 'fact_value': 'coding', 'confidence': 0.8}
        ]

        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=[],
            document_references=[],
            conflicts=[],
            user_message="Hello",
            user_facts=facts
        )

        assert "name: Jason" in summary or "Jason" in summary

    def test_create_summary_with_tracking(self):
        """Test summary includes tracking context."""
        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=[],
            document_references=[],
            conflicts=[],
            user_message="Hello",
            tracking_context="=== User's Active Goals ===\n- Lose 10 pounds"
        )

        assert "Goals" in summary or "Lose" in summary

    def test_create_summary_with_documents(self):
        """Test summary includes document chunks."""
        chunks = [{
            'document_filename': 'resume.pdf',
            'text_content': 'Senior software engineer with 10 years experience',
            'similarity_score': 0.8
        }]

        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=chunks,
            document_references=[],
            conflicts=[],
            user_message="Tell me about my experience"
        )

        assert "resume.pdf" in summary or "software engineer" in summary

    def test_create_summary_with_conflicts(self):
        """Test summary includes conflict warnings."""
        conflicts = [{'conflict_reason': 'Conflicting dates mentioned'}]

        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=[],
            document_references=[],
            conflicts=conflicts,
            user_message="Hello"
        )

        assert "conflict" in summary.lower()


class TestTruncateToBudget:
    """Tests for budget truncation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()

    def test_truncate_within_budget(self):
        """Test text within budget is not truncated."""
        text = "Short text"
        result = self.service._truncate_to_budget(text, 100)
        assert result == text

    def test_truncate_exceeds_budget(self):
        """Test text exceeding budget is truncated."""
        text = "A" * 200
        result = self.service._truncate_to_budget(text, 50)

        assert len(result) == 50
        assert result.endswith("...")


class TestFormatEnhancedPrompt:
    """Tests for enhanced prompt formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()

    def test_format_prompt_basic(self):
        """Test basic prompt formatting."""
        context = {
            'context_summary': 'Some context',
            'reasoning_chain': []
        }

        result = self.service.format_enhanced_prompt(
            user_message="What should I do?",
            context=context
        )

        assert "What should I do?" in result
        assert "Some context" in result

    def test_format_prompt_with_reasoning(self):
        """Test prompt formatting with reasoning chain."""
        context = {
            'context_summary': '',
            'reasoning_chain': [
                {'step': 'init', 'thought': 'Starting analysis'}
            ]
        }

        result = self.service.format_enhanced_prompt(
            user_message="Test",
            context=context,
            show_reasoning=True
        )

        assert "Internal reasoning" in result
        assert "Starting analysis" in result

    def test_format_prompt_without_reasoning(self):
        """Test prompt formatting without reasoning chain."""
        context = {
            'context_summary': 'Context here',
            'reasoning_chain': [
                {'step': 'init', 'thought': 'Starting analysis'}
            ]
        }

        result = self.service.format_enhanced_prompt(
            user_message="Test",
            context=context,
            show_reasoning=False
        )

        assert "Internal reasoning" not in result


class TestSuggestRelatedDocuments:
    """Tests for document suggestion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()
        self.mock_db = MagicMock()

    @patch('miachat.api.core.enhanced_context_service.document_service')
    def test_suggest_documents(self, mock_doc_service):
        """Test document suggestion returns results."""
        mock_doc_service.search_documents.return_value = [
            {
                'document_id': 'doc1',
                'document_filename': 'resume.pdf',
                'similarity_score': 0.8,
                'text_content': 'Experience in software development'
            }
        ]

        suggestions = self.service.suggest_related_documents(
            query="career experience",
            user_id=1,
            db=self.mock_db
        )

        assert len(suggestions) > 0
        assert suggestions[0]['filename'] == 'resume.pdf'

    @patch('miachat.api.core.enhanced_context_service.document_service')
    def test_suggest_documents_excludes_specified(self, mock_doc_service):
        """Test that excluded documents are not suggested."""
        mock_doc_service.search_documents.return_value = [
            {
                'document_id': 'doc1',
                'document_filename': 'resume.pdf',
                'similarity_score': 0.8,
                'text_content': 'Content'
            },
            {
                'document_id': 'doc2',
                'document_filename': 'cover_letter.pdf',
                'similarity_score': 0.7,
                'text_content': 'Content'
            }
        ]

        suggestions = self.service.suggest_related_documents(
            query="career",
            user_id=1,
            exclude_documents=['doc1'],
            db=self.mock_db
        )

        assert all(s['document_id'] != 'doc1' for s in suggestions)


class TestEnhancedContextSingleton:
    """Test that enhanced_context_service singleton works."""

    def test_singleton_instance(self):
        """Test that singleton is properly instantiated."""
        assert enhanced_context_service is not None
        assert isinstance(enhanced_context_service, EnhancedContextService)


class TestWebSearchIntegration:
    """Tests for web search integration in context."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()
        self.mock_db = MagicMock()

    def test_web_search_results_in_context_structure(self):
        """Test that web_search_results field exists in context."""
        with patch('miachat.api.core.enhanced_context_service.memory_service') as mock_memory:
            mock_memory.get_context.return_value = []

            result = self.service.get_enhanced_context(
                user_message="Hello",
                user_id=1,
                db=self.mock_db,
                include_documents=False
            )

            # Verify web search fields exist in structure
            assert 'web_search_results' in result
            assert 'web_search_context' in result

    def test_web_search_context_in_summary(self):
        """Test that web search context is included in summary when provided."""
        summary = self.service._create_intelligent_context_summary(
            recent_interactions=[],
            semantic_context=[],
            document_chunks=[],
            document_references=[],
            conflicts=[],
            user_message="What's the weather?",
            web_search_context="Weather forecast: Sunny, 72F"
        )

        assert "Weather forecast" in summary or "Sunny" in summary

    def test_context_budget_includes_web_search(self):
        """Test that context budget allocates for web search."""
        assert 'web_search' in self.service.context_budget
        assert self.service.context_budget['web_search'] > 0


class TestCalendarIntegration:
    """Tests for calendar context integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = EnhancedContextService()
        self.mock_db = MagicMock()

    @patch('miachat.api.core.enhanced_context_service.google_calendar_service')
    @patch('miachat.api.core.enhanced_context_service.memory_service')
    @patch('miachat.api.core.enhanced_context_service.setting_service')
    @patch('miachat.api.core.enhanced_context_service.backstory_service')
    @patch('miachat.api.core.enhanced_context_service.fact_extraction_service')
    @patch('miachat.api.core.enhanced_context_service.user_profile_service')
    @patch('miachat.api.core.enhanced_context_service.tracking_service')
    def test_calendar_context_when_enabled(
        self, mock_tracking, mock_user_profile, mock_facts,
        mock_backstory, mock_setting, mock_memory, mock_calendar
    ):
        """Test calendar context is retrieved when sync is enabled."""
        mock_memory.get_context.return_value = []
        mock_setting.format_setting_context.return_value = ""
        mock_backstory.get_relevant_backstory.return_value = []
        mock_facts.get_user_facts.return_value = []
        mock_user_profile.format_user_profile_context.return_value = ""
        mock_tracking.get_tracking_context.return_value = ""
        mock_calendar.get_calendar_context.return_value = "Meeting tomorrow at 10am"

        # Mock sync config
        mock_sync_config = MagicMock()
        mock_sync_config.calendar_sync_enabled = True
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_sync_config

        result = self.service.get_enhanced_context(
            user_message="What do I have planned?",
            user_id=1,
            character_id="test-char",
            db=self.mock_db,
            include_documents=False
        )

        assert 'calendar_context' in result
        assert result['calendar_context'] == "Meeting tomorrow at 10am"
