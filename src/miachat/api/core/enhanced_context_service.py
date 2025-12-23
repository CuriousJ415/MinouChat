"""
Enhanced Context Service for intelligent AI assistant capabilities.

Provides unified context orchestration combining:
- Recent conversation context (focused on last 4 interactions)
- Semantic memory retrieval (relevant historical insights)
- Document context (user-referenced + semantically relevant)
- Natural language document reference parsing
- Reasoning chain generation
- Conflict detection between sources
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from ...database.config import get_db
from .document_service import document_service
from .embedding_service import embedding_service
from .memory_service import memory_service
from .setting_service import setting_service
from .backstory_service import backstory_service
from .fact_extraction_service import fact_extraction_service
from .user_profile_service import user_profile_service
from .security.prompt_sanitizer import prompt_sanitizer
from .tracking_service import tracking_service
from .web_search_service import web_search_service
from .google_calendar_service import google_calendar_service
from ...database.models import PersonaGoogleSyncConfig

logger = logging.getLogger(__name__)

class EnhancedContextService:
    """Service for intelligent context synthesis and reasoning."""

    def __init__(
        self,
        max_context_chunks: int = 10,
        similarity_threshold: float = 0.35,  # Lowered for better recall
        max_context_length: int = 8000,  # Increased for richer context
        max_recent_interactions: int = 4  # Focus on last 4 interactions
    ):
        """Initialize the Enhanced Context Service.

        Args:
            max_context_chunks: Maximum number of document chunks to include
            similarity_threshold: Minimum similarity score for including chunks
            max_context_length: Maximum total character length of document context
            max_recent_interactions: Maximum recent chat interactions to include
        """
        self.max_context_chunks = max_context_chunks
        self.similarity_threshold = similarity_threshold
        self.max_context_length = max_context_length
        self.max_recent_interactions = max_recent_interactions

        # Context budget allocation (percentages)
        self.context_budget = {
            'user_profile': 0.10, # 10% for user's "About You" profile (highest priority)
            'setting': 0.08,      # 8% for world/location/time
            'tracking': 0.10,     # 10% for goals, todos, habits
            'calendar': 0.08,     # 8% for upcoming calendar events
            'user_facts': 0.10,   # 10% for learned user facts
            'backstory': 0.10,    # 10% for character backstory
            'conversation': 0.18, # 18% for recent conversation (reduced from 22%)
            'documents': 0.18,    # 18% for document RAG (reduced from 20%)
            'web_search': 0.08    # 8% for web search results (reduced from 10%)
        }

        # Document reference patterns for natural language parsing
        self.doc_reference_patterns = [
            r"my (\w+(?:\s+\w+){0,2}) (?:report|document|file)",
            r"the (\w+(?:\s+\w+){0,2}) (?:report|document|file)",
            r"(?:look at|analyze|review|based on) (?:my |the )?(\w+(?:\s+\w+){0,2}) (?:report|document|file|doc)",
            r"values? (?:report|profile|assessment|inventory)",
            r"(?:document|file) (?:I uploaded|about) (\w+(?:\s+\w+){0,2})",
            r"(\w+(?:\s+\w+){0,2}) analysis",
            r"my (\w+) profile"
        ]

    def get_enhanced_context(
        self,
        user_message: str,
        user_id: int,
        conversation_id: Optional[int] = None,
        character_id: Optional[str] = None,
        include_conversation_history: bool = True,
        include_documents: bool = True,
        comprehensive_analysis: bool = False,
        enable_reasoning: bool = True,
        force_document_ids: Optional[List[str]] = None,
        force_search: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get enhanced context with intelligent synthesis and reasoning.

        Args:
            user_message: Current user message
            user_id: User ID for document access
            conversation_id: Optional conversation ID for history
            character_id: Optional character ID for personalized retrieval
            include_conversation_history: Whether to include conversation context
            include_documents: Whether to include document context
            comprehensive_analysis: If True, retrieves ALL chunks for complete analysis
            enable_reasoning: Whether to generate reasoning chains
            force_document_ids: Optional list of document IDs to always include (for session persistence)
            force_search: If True, always perform web search (bypasses intent detection)
            db: Database session

        Returns:
            Dictionary with enhanced context and reasoning information
        """
        if db is None:
            db = next(get_db())

        try:
            context = {
                'conversation_history': [],
                'recent_interactions': [],
                'semantic_context': [],
                'relevant_documents': [],
                'document_chunks': [],
                'document_references': [],
                'user_profile_context': '',  # User's "About You" info (highest priority)
                'setting_context': '',
                'tracking_context': '',  # Goals, todos, habits
                'calendar_context': '',  # Upcoming calendar events
                'backstory_context': [],
                'user_facts': [],
                'web_search_results': [],  # Web search results if capability enabled
                'web_search_context': '',  # Formatted web search context
                'context_summary': '',
                'reasoning_chain': [],
                'conflicts_detected': [],
                'sources': []
            }

            # Generate reasoning chain if enabled
            if enable_reasoning:
                context['reasoning_chain'].append({
                    'step': 'initialization',
                    'thought': f"Starting context analysis for user message: '{user_message[:100]}...'"
                })

            # Parse natural language document references
            doc_references = self._parse_document_references(user_message)
            context['document_references'] = doc_references

            if enable_reasoning and doc_references:
                context['reasoning_chain'].append({
                    'step': 'document_parsing',
                    'thought': f"Detected document references: {doc_references}"
                })

            # Get recent conversation context (focused on last 4 interactions)
            if include_conversation_history and conversation_id:
                recent_context = self._get_recent_conversation_context(
                    conversation_id=conversation_id,
                    user_message=user_message,
                    db=db
                )
                context['recent_interactions'] = recent_context

                if enable_reasoning:
                    context['reasoning_chain'].append({
                        'step': 'conversation_context',
                        'thought': f"Retrieved {len(recent_context)} recent conversation interactions"
                    })

                # Get broader semantic context for relevant historical insights
                semantic_context = memory_service.get_context(
                    conversation_id=conversation_id,
                    current_message=user_message,
                    context_window=8,  # Broader search for semantic relevance
                    db=db
                )
                context['semantic_context'] = semantic_context

                if enable_reasoning and semantic_context:
                    context['reasoning_chain'].append({
                        'step': 'semantic_memory',
                        'thought': f"Found {len(semantic_context)} semantically relevant past interactions"
                    })

            # Get relevant documents based on references and semantic search
            if include_documents:
                document_context = self._get_intelligent_document_context(
                    query=user_message,
                    user_id=user_id,
                    db=db,
                    conversation_id=conversation_id,
                    character_id=character_id,
                    document_references=doc_references,
                    comprehensive_analysis=comprehensive_analysis,
                    reasoning_chain=context['reasoning_chain'] if enable_reasoning else None,
                    force_document_ids=force_document_ids
                )
                context.update(document_context)

            # Get simplified context system data (user profile, setting, backstory, facts)
            if character_id:
                # Get user profile context (highest priority - explicitly set by user)
                user_profile_ctx = user_profile_service.format_user_profile_context(character_id)
                if user_profile_ctx:
                    context['user_profile_context'] = user_profile_ctx
                    if enable_reasoning:
                        context['reasoning_chain'].append({
                            'step': 'user_profile_context',
                            'thought': "Retrieved user's 'About You' profile"
                        })

                # Get setting context
                setting_ctx = setting_service.format_setting_context(character_id)
                if setting_ctx:
                    context['setting_context'] = setting_ctx
                    if enable_reasoning:
                        context['reasoning_chain'].append({
                            'step': 'setting_context',
                            'thought': "Retrieved character setting/world context"
                        })

                # Get tracking context (goals, todos, habits)
                try:
                    tracking_ctx = tracking_service.get_tracking_context(
                        user_id=user_id,
                        character_id=character_id,
                        db=db
                    )
                    if tracking_ctx:
                        context['tracking_context'] = tracking_ctx
                        if enable_reasoning:
                            context['reasoning_chain'].append({
                                'step': 'tracking_context',
                                'thought': "Retrieved user's goals, todos, and habits"
                            })
                except Exception as e:
                    logger.warning(f"Failed to get tracking context: {e}")

                # Get calendar context (only if enabled for this persona)
                try:
                    # Check if calendar access is enabled for this persona
                    sync_config = db.query(PersonaGoogleSyncConfig).filter_by(
                        user_id=user_id,
                        character_id=character_id
                    ).first()

                    if sync_config and sync_config.calendar_sync_enabled:
                        calendar_ctx = google_calendar_service.get_calendar_context(
                            user_id=user_id,
                            db=db,
                            days_ahead=7,
                            max_events=10
                        )
                        if calendar_ctx:
                            context['calendar_context'] = calendar_ctx
                            if enable_reasoning:
                                context['reasoning_chain'].append({
                                    'step': 'calendar_context',
                                    'thought': "Retrieved user's upcoming calendar events"
                                })
                except Exception as e:
                    logger.warning(f"Failed to get calendar context: {e}")

                # Get relevant backstory chunks
                backstory_chunks = backstory_service.get_relevant_backstory(
                    character_id=character_id,
                    user_id=user_id,
                    query=user_message,
                    db=db,
                    top_k=2
                )
                if backstory_chunks:
                    context['backstory_context'] = backstory_chunks
                    if enable_reasoning:
                        context['reasoning_chain'].append({
                            'step': 'backstory_retrieval',
                            'thought': f"Retrieved {len(backstory_chunks)} relevant backstory chunks"
                        })

                # Get user facts
                user_facts = fact_extraction_service.get_user_facts(
                    user_id=user_id,
                    character_id=character_id,
                    db=db
                )
                if user_facts:
                    context['user_facts'] = user_facts
                    if enable_reasoning:
                        context['reasoning_chain'].append({
                            'step': 'user_facts',
                            'thought': f"Retrieved {len(user_facts)} known facts about user"
                        })

            # Web search if force_search=True or (character has capability and search intent detected)
            if character_id:
                try:
                    from .character_manager import character_manager
                    character = character_manager.get_character(character_id)
                    logger.debug(f"Web search check - character_id={character_id}, character found={character is not None}")

                    if character:
                        has_capability = web_search_service.check_capability(character)
                        logger.debug(f"Web search capability check: {has_capability}, capabilities={character.get('capabilities', {})}")

                        # Determine if we should search
                        should_search = False
                        search_query = user_message
                        search_type = 'web'

                        if force_search and has_capability:
                            # User explicitly requested search via button
                            should_search = True
                            logger.warning(f"[SEARCH] Force search enabled - searching for: '{user_message[:50]}...'")
                        elif has_capability:
                            # Check if message implies search intent (auto-detection fallback)
                            search_intent = web_search_service.detect_search_intent(user_message)
                            logger.debug(f"Search intent: should_search={search_intent.should_search}, type={search_intent.intent_type}")
                            if search_intent.should_search:
                                should_search = True
                                search_query = search_intent.query or user_message
                                search_type = search_intent.intent_type or 'web'

                        if should_search:
                            # Perform the search
                            if search_type == 'current_events':
                                results = web_search_service.search_news(
                                    query=search_query,
                                    max_results=5,
                                    timelimit='w'
                                )
                            else:
                                results = web_search_service.search(
                                    query=search_query,
                                    max_results=5
                                )

                            if results:
                                # Convert SearchResult objects to dicts for serialization
                                context['web_search_results'] = [r.to_dict() for r in results]
                                context['web_search_context'] = web_search_service.format_results_for_context(
                                    results, search_query, max_chars=int(self.max_context_length * self.context_budget['web_search'])
                                )
                                if enable_reasoning:
                                    context['reasoning_chain'].append({
                                        'step': 'web_search',
                                        'thought': f"Performed web search for '{search_query}' - found {len(results)} results"
                                    })
                                logger.warning(f"[SEARCH] Web search SUCCESS: {len(results)} results for '{search_query[:30]}...'")
                except Exception as e:
                    logger.warning(f"Web search failed: {e}", exc_info=True)

            # Detect conflicts between sources
            if enable_reasoning:
                conflicts = self._detect_conflicts(
                    conversation_context=context['recent_interactions'],
                    semantic_context=context['semantic_context'],
                    document_chunks=context['document_chunks']
                )
                context['conflicts_detected'] = conflicts

                if conflicts:
                    context['reasoning_chain'].append({
                        'step': 'conflict_detection',
                        'thought': f"Detected {len(conflicts)} potential conflicts between sources"
                    })

            # Create comprehensive context summary with reasoning
            context['context_summary'] = self._create_intelligent_context_summary(
                recent_interactions=context['recent_interactions'],
                semantic_context=context['semantic_context'],
                document_chunks=context['document_chunks'],
                document_references=context['document_references'],
                conflicts=context['conflicts_detected'],
                user_message=user_message,
                user_profile_context=context.get('user_profile_context', ''),
                setting_context=context.get('setting_context', ''),
                tracking_context=context.get('tracking_context', ''),
                calendar_context=context.get('calendar_context', ''),
                backstory_context=context.get('backstory_context', []),
                user_facts=context.get('user_facts', []),
                web_search_context=context.get('web_search_context', '')
            )

            # Final reasoning step
            if enable_reasoning:
                context['reasoning_chain'].append({
                    'step': 'synthesis',
                    'thought': f"Synthesized context with {len(context['recent_interactions'])} recent interactions, "
                             f"{len(context['document_chunks'])} document chunks, "
                             f"and {len(context['conflicts_detected'])} conflicts detected"
                })

            logger.info(f"Enhanced context created: {len(context['recent_interactions'])} recent interactions, "
                       f"{len(context['semantic_context'])} semantic messages, "
                       f"{len(context['document_chunks'])} document chunks, "
                       f"{len(context['conflicts_detected'])} conflicts")

            return context

        except Exception as e:
            logger.error(f"Error creating enhanced context: {e}")
            return {
                'conversation_history': [],
                'recent_interactions': [],
                'semantic_context': [],
                'relevant_documents': [],
                'document_chunks': [],
                'document_references': [],
                'context_summary': '',
                'reasoning_chain': [{'step': 'error', 'thought': f"Error during context creation: {str(e)}"}],
                'conflicts_detected': [],
                'sources': [],
                'error': str(e)
            }

    def _parse_document_references(self, user_message: str) -> List[Dict[str, Any]]:
        """Parse natural language references to documents in user message.

        Args:
            user_message: User's message to parse

        Returns:
            List of detected document references
        """
        references = []
        message_lower = user_message.lower()

        # Check for specific document type patterns
        for pattern in self.doc_reference_patterns:
            matches = re.finditer(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                # Extract the document type/name
                if match.groups():
                    doc_name = match.group(1).strip()
                else:
                    doc_name = match.group(0)

                references.append({
                    'type': 'document_reference',
                    'reference_text': match.group(0),
                    'extracted_name': doc_name,
                    'confidence': 0.8
                })

        # Check for general document requests
        if any(phrase in message_lower for phrase in [
            'document i uploaded', 'my documents', 'uploaded file',
            'the file', 'analyze my', 'look at my', 'based on my'
        ]):
            references.append({
                'type': 'general_document_request',
                'reference_text': 'general document reference',
                'extracted_name': 'user_documents',
                'confidence': 0.6
            })

        return references

    def _get_recent_conversation_context(
        self,
        conversation_id: int,
        user_message: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Get recent conversation context (last 4 interactions).

        Args:
            conversation_id: Conversation ID
            user_message: Current user message
            db: Database session

        Returns:
            List of recent conversation messages
        """
        try:
            # Get recent messages using memory service but limit to recent interactions
            all_context = memory_service.get_context(
                conversation_id=conversation_id,
                current_message=user_message,
                context_window=self.max_recent_interactions * 2,  # Get a few extra to filter
                db=db
            )

            # Return only the most recent interactions (last 4 messages)
            return all_context[-self.max_recent_interactions:] if all_context else []

        except Exception as e:
            logger.warning(f"Failed to get recent conversation context: {e}")
            return []

    def _get_intelligent_document_context(
        self,
        query: str,
        user_id: int,
        db: Session,
        conversation_id: Optional[int] = None,
        character_id: Optional[str] = None,
        document_references: List[Dict[str, Any]] = None,
        comprehensive_analysis: bool = False,
        reasoning_chain: Optional[List[Dict[str, Any]]] = None,
        force_document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get intelligent document context based on references and semantic search.

        Args:
            query: Search query
            user_id: User ID for document access
            db: Database session
            conversation_id: Optional conversation ID
            character_id: Optional character ID
            document_references: Parsed document references from user message
            comprehensive_analysis: Whether to do comprehensive analysis
            reasoning_chain: Optional reasoning chain to update
            force_document_ids: Document IDs to always include (session persistence)

        Returns:
            Dictionary with document context
        """
        try:
            # Start with forced documents (session persistence)
            all_chunks = []

            if force_document_ids:
                forced_chunks = self._get_chunks_by_document_ids(
                    force_document_ids, user_id, db, reasoning_chain
                )
                all_chunks.extend(forced_chunks)
                if reasoning_chain:
                    reasoning_chain.append({
                        'step': 'session_document_persistence',
                        'thought': f"Including {len(forced_chunks)} chunks from {len(force_document_ids)} session documents"
                    })

            # Add referenced documents

            if document_references:
                # Get documents that match the references
                referenced_chunks = self._get_referenced_documents(
                    document_references, user_id, db, reasoning_chain
                )
                all_chunks.extend(referenced_chunks)

            # Add semantically relevant documents
            if comprehensive_analysis:
                # Get all recent documents for comprehensive analysis
                comprehensive_chunks = self._get_comprehensive_document_chunks(
                    user_id, db, character_id, reasoning_chain, conversation_id
                )
                all_chunks.extend(comprehensive_chunks)
            else:
                # Get semantically relevant chunks
                semantic_chunks = self._get_semantic_document_chunks(
                    query, user_id, db, character_id, reasoning_chain
                )
                all_chunks.extend(semantic_chunks)

            # Remove duplicates and process
            seen_chunk_ids = set()
            unique_chunks = []
            for chunk in all_chunks:
                if chunk['chunk_id'] not in seen_chunk_ids:
                    unique_chunks.append(chunk)
                    seen_chunk_ids.add(chunk['chunk_id'])

            # Apply length and relevance limits
            document_chunks = []
            sources = []
            seen_documents = set()
            total_length = 0

            for chunk in unique_chunks:
                # Check length limits
                chunk_length = len(chunk['text_content'])
                max_length = self.max_context_length * 3 if comprehensive_analysis else self.max_context_length

                if total_length + chunk_length > max_length and document_chunks:
                    break

                document_chunks.append(chunk)
                total_length += chunk_length

                # Track sources
                doc_id = chunk['document_id']
                if doc_id not in seen_documents:
                    seen_documents.add(doc_id)
                    sources.append({
                        'document_id': doc_id,
                        'filename': chunk['document_filename'],
                        'similarity_score': chunk['similarity_score']
                    })

                # Check chunk limits
                max_chunks = self.max_context_chunks * 3 if comprehensive_analysis else self.max_context_chunks
                if len(document_chunks) >= max_chunks:
                    break

            # Get unique document info
            relevant_documents = list({
                chunk['document_id']: {
                    'id': chunk['document_id'],
                    'filename': chunk['document_filename'],
                    'max_similarity': max([c['similarity_score'] for c in document_chunks if c['document_id'] == chunk['document_id']])
                }
                for chunk in document_chunks
            }.values())

            return {
                'relevant_documents': relevant_documents,
                'document_chunks': document_chunks,
                'sources': sources
            }

        except Exception as e:
            logger.error(f"Error getting intelligent document context: {e}")
            return {
                'relevant_documents': [],
                'document_chunks': [],
                'sources': []
            }

    def _get_referenced_documents(
        self,
        document_references: List[Dict[str, Any]],
        user_id: int,
        db: Session,
        reasoning_chain: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get documents that match natural language references.

        Args:
            document_references: Parsed document references
            user_id: User ID
            db: Database session
            reasoning_chain: Optional reasoning chain to update

        Returns:
            List of matching document chunks
        """
        chunks = []

        try:
            from ...database.models import Document, DocumentChunk

            for ref in document_references:
                extracted_name = ref['extracted_name'].lower()

                # Search for documents with matching names/content
                if extracted_name == 'user_documents':
                    # General request - get recent documents
                    recent_docs = db.query(Document).filter(
                        Document.user_id == user_id,
                        Document.is_processed == 1
                    ).order_by(Document.upload_date.desc()).limit(2).all()
                else:
                    # Specific document name search
                    matching_docs = db.query(Document).filter(
                        Document.user_id == user_id,
                        Document.is_processed == 1,
                        Document.original_filename.ilike(f'%{extracted_name}%')
                    ).all()

                    if not matching_docs:
                        # Try searching in document content
                        matching_docs = db.query(Document).filter(
                            Document.user_id == user_id,
                            Document.is_processed == 1
                        ).all()

                        # Filter by content similarity
                        content_matches = []
                        for doc in matching_docs:
                            if any(extracted_name in (doc.doc_metadata or {}).get('title', '').lower() or
                                  extracted_name in doc.original_filename.lower() for _ in [None]):
                                content_matches.append(doc)

                        matching_docs = content_matches

                    recent_docs = matching_docs[:2]  # Limit to most relevant

                # Get chunks from matching documents
                for doc in recent_docs:
                    doc_chunks = db.query(DocumentChunk).filter(
                        DocumentChunk.document_id == doc.id
                    ).limit(5).all()  # Limit chunks per document

                    for chunk in doc_chunks:
                        chunks.append({
                            'chunk_id': chunk.id,
                            'document_id': chunk.document_id,
                            'document_filename': doc.original_filename,
                            'text_content': chunk.text_content,
                            'chunk_type': chunk.chunk_type,
                            'chunk_index': chunk.chunk_index,
                            'similarity_score': 0.9,  # High score for explicitly referenced docs
                            'metadata': chunk.doc_metadata or {},
                            'document_metadata': doc.doc_metadata or {},
                            'reference_match': ref
                        })

                if reasoning_chain is not None:
                    reasoning_chain.append({
                        'step': 'document_reference_resolution',
                        'thought': f"Found {len([c for c in chunks if c.get('reference_match') == ref])} chunks for reference '{ref['reference_text']}'"
                    })

        except Exception as e:
            logger.warning(f"Error getting referenced documents: {e}")

        return chunks

    def _get_comprehensive_document_chunks(
        self,
        user_id: int,
        db: Session,
        character_id: Optional[str] = None,
        reasoning_chain: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        hours_back: int = 2
    ) -> List[Dict[str, Any]]:
        """Get comprehensive document chunks for complete analysis.

        Args:
            user_id: User ID
            db: Database session
            character_id: Optional character ID
            reasoning_chain: Optional reasoning chain to update
            session_id: Optional session ID for session-scoped analysis
            hours_back: How many hours back to look for documents

        Returns:
            List of document chunks
        """
        try:
            from ...database.models import Document, DocumentChunk

            # Get recent documents with time-based filtering
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            base_query = db.query(Document).filter(
                Document.user_id == user_id,
                Document.is_processed == 1,
                Document.upload_date >= cutoff_time  # Only recent uploads
            )

            # Filter by character if specified
            if character_id:
                all_documents = base_query.all()
                character_documents = [
                    doc for doc in all_documents
                    if (doc.doc_metadata and
                        'character_associations' in doc.doc_metadata and
                        character_id in doc.doc_metadata['character_associations'])
                ]
                if character_documents:
                    document_ids = [doc.id for doc in character_documents]
                    base_query = base_query.filter(Document.id.in_(document_ids))
                else:
                    return []  # No documents for this character

            # Prioritize session-specific documents if session_id provided
            if session_id:
                # Get documents uploaded in current session (most recent)
                session_documents = base_query.order_by(Document.upload_date.desc()).limit(1).all()
                recent_documents = session_documents

                if reasoning_chain:
                    reasoning_chain.append({
                        'step': 'session_filtering',
                        'thought': f"Prioritizing {len(session_documents)} most recent documents for session-focused analysis"
                    })
            else:
                # Fallback to recent documents
                recent_documents = base_query.order_by(Document.upload_date.desc()).limit(2).all()

            chunks = []
            for doc in recent_documents:
                doc_chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).order_by(DocumentChunk.chunk_index).all()

                for chunk in doc_chunks:
                    chunks.append({
                        'chunk_id': chunk.id,
                        'document_id': chunk.document_id,
                        'document_filename': doc.original_filename,
                        'text_content': chunk.text_content,
                        'chunk_type': chunk.chunk_type,
                        'chunk_index': chunk.chunk_index,
                        'similarity_score': 1.0,  # High score for comprehensive analysis
                        'metadata': chunk.doc_metadata or {},
                        'document_metadata': doc.doc_metadata or {}
                    })

            if reasoning_chain is not None:
                reasoning_chain.append({
                    'step': 'comprehensive_document_retrieval',
                    'thought': f"Retrieved {len(chunks)} chunks from {len(recent_documents)} recent documents for comprehensive analysis"
                })

            return chunks

        except Exception as e:
            logger.warning(f"Error getting comprehensive document chunks: {e}")
            return []

    def _get_semantic_document_chunks(
        self,
        query: str,
        user_id: int,
        db: Session,
        character_id: Optional[str] = None,
        reasoning_chain: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get semantically relevant document chunks.

        Args:
            query: Search query
            user_id: User ID
            db: Database session
            character_id: Optional character ID
            reasoning_chain: Optional reasoning chain to update

        Returns:
            List of relevant document chunks
        """
        try:
            search_results = document_service.search_documents(
                query=query,
                user_id=user_id,
                top_k=self.max_context_chunks * 2,
                similarity_threshold=self.similarity_threshold,
                character_id=character_id,
                db=db
            )

            if reasoning_chain is not None:
                reasoning_chain.append({
                    'step': 'semantic_document_search',
                    'thought': f"Found {len(search_results)} semantically relevant document chunks"
                })

            return search_results

        except Exception as e:
            logger.warning(f"Error getting semantic document chunks: {e}")
            return []

    def _get_chunks_by_document_ids(
        self,
        document_ids: List[str],
        user_id: int,
        db: Session,
        reasoning_chain: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get all chunks for specific document IDs (for session persistence).

        Args:
            document_ids: List of document IDs to retrieve
            user_id: User ID for ownership verification
            db: Database session
            reasoning_chain: Optional reasoning chain to update

        Returns:
            List of document chunks
        """
        try:
            from ...database.models import Document, DocumentChunk

            chunks = []
            for doc_id in document_ids:
                # Get document with ownership check
                document = db.query(Document).filter(
                    Document.id == doc_id,
                    Document.user_id == user_id,
                    Document.is_processed == 1
                ).first()

                if not document:
                    logger.warning(f"Document {doc_id} not found or not accessible for user {user_id}")
                    continue

                # Get all chunks for this document
                doc_chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc_id
                ).order_by(DocumentChunk.chunk_index).all()

                for chunk in doc_chunks:
                    chunks.append({
                        'chunk_id': chunk.id,
                        'document_id': chunk.document_id,
                        'document_filename': document.original_filename,
                        'text_content': chunk.text_content,
                        'chunk_type': chunk.chunk_type,
                        'chunk_index': chunk.chunk_index,
                        'similarity_score': 1.0,  # High priority for session documents
                        'metadata': chunk.doc_metadata or {},
                        'document_metadata': document.doc_metadata or {},
                        'is_session_document': True  # Flag for session persistence
                    })

            if reasoning_chain is not None:
                reasoning_chain.append({
                    'step': 'forced_document_retrieval',
                    'thought': f"Retrieved {len(chunks)} chunks from {len(document_ids)} session documents"
                })

            return chunks

        except Exception as e:
            logger.warning(f"Error getting chunks by document IDs: {e}")
            return []

    def _detect_conflicts(
        self,
        conversation_context: List[Dict[str, Any]],
        semantic_context: List[Dict[str, Any]],
        document_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect potential conflicts between different information sources.

        Args:
            conversation_context: Recent conversation messages
            semantic_context: Semantic memory context
            document_chunks: Document chunks

        Returns:
            List of detected conflicts
        """
        conflicts = []

        try:
            # Simple conflict detection - look for contradictory statements
            # This is a basic implementation - could be enhanced with more sophisticated NLP

            # Collect all text content
            all_content = []

            # Add conversation content
            for msg in conversation_context:
                all_content.append({
                    'source': 'recent_conversation',
                    'content': msg.get('content', ''),
                    'metadata': msg
                })

            # Add semantic context
            for msg in semantic_context:
                all_content.append({
                    'source': 'semantic_memory',
                    'content': msg.get('content', ''),
                    'metadata': msg
                })

            # Add document content
            for chunk in document_chunks:
                all_content.append({
                    'source': 'document',
                    'content': chunk.get('text_content', ''),
                    'metadata': chunk
                })

            # Look for potential conflicts using simple keyword analysis
            # This could be enhanced with more sophisticated methods
            conflict_indicators = [
                ('not', 'yes'), ('no', 'yes'), ('false', 'true'),
                ('disagree', 'agree'), ('against', 'for'),
                ('incorrect', 'correct'), ('wrong', 'right')
            ]

            for i, content1 in enumerate(all_content):
                for j, content2 in enumerate(all_content[i+1:], i+1):
                    if content1['source'] != content2['source']:
                        # Check for conflicting keywords
                        text1 = content1['content'].lower()
                        text2 = content2['content'].lower()

                        for negative, positive in conflict_indicators:
                            if negative in text1 and positive in text2:
                                conflicts.append({
                                    'type': 'keyword_conflict',
                                    'source1': content1['source'],
                                    'source2': content2['source'],
                                    'snippet1': content1['content'][:100] + "...",
                                    'snippet2': content2['content'][:100] + "...",
                                    'conflict_reason': f"Contains '{negative}' vs '{positive}'"
                                })

        except Exception as e:
            logger.warning(f"Error detecting conflicts: {e}")

        return conflicts

    def _create_intelligent_context_summary(
        self,
        recent_interactions: List[Dict[str, Any]],
        semantic_context: List[Dict[str, Any]],
        document_chunks: List[Dict[str, Any]],
        document_references: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]],
        user_message: str,
        user_profile_context: str = '',
        setting_context: str = '',
        tracking_context: str = '',
        calendar_context: str = '',
        backstory_context: Optional[List[str]] = None,
        user_facts: Optional[List[Dict[str, Any]]] = None,
        web_search_context: str = ''
    ) -> str:
        """Create an intelligent context summary for the LLM with smart budget allocation.

        Args:
            recent_interactions: Recent conversation interactions
            semantic_context: Semantic memory context
            document_chunks: Document chunks
            document_references: Parsed document references
            conflicts: Detected conflicts
            user_message: Current user message
            user_profile_context: User's "About You" profile (highest priority)
            setting_context: Formatted setting/world context
            tracking_context: User's goals, todos, and habits
            calendar_context: User's upcoming calendar events
            backstory_context: Relevant backstory chunks
            user_facts: Known facts about the user
            web_search_context: Formatted web search results

        Returns:
            Formatted context string
        """
        backstory_context = backstory_context or []
        user_facts = user_facts or []

        context_parts = []

        # Calculate budget allocations based on max_context_length
        budgets = {k: int(v * self.max_context_length) for k, v in self.context_budget.items()}

        # ============================================
        # SECTION 1: User Profile (highest priority - explicitly set by user)
        # ============================================
        if user_profile_context:
            truncated_profile = self._truncate_to_budget(user_profile_context, budgets['user_profile'])
            context_parts.append(truncated_profile)
            context_parts.append("")

        # ============================================
        # SECTION 2: Setting Context (defines the world)
        # ============================================
        if setting_context:
            truncated_setting = self._truncate_to_budget(setting_context, budgets['setting'])
            context_parts.append(truncated_setting)
            context_parts.append("")

        # ============================================
        # SECTION 3: Tracking Context (goals, todos, habits)
        # ============================================
        if tracking_context:
            truncated_tracking = self._truncate_to_budget(tracking_context, budgets['tracking'])
            context_parts.append(truncated_tracking)
            context_parts.append("")

        # ============================================
        # SECTION 3.5: Calendar Context (upcoming events)
        # ============================================
        if calendar_context:
            truncated_calendar = self._truncate_to_budget(calendar_context, budgets['calendar'])
            context_parts.append(truncated_calendar)
            context_parts.append("")

        # ============================================
        # SECTION 4: User Facts (learned facts - personalizes interaction)
        # ============================================
        if user_facts:
            facts_content = []
            facts_content.append("[Background info about user - reference ONLY when directly relevant to what they're asking. Do NOT bring up unsolicited or repeatedly. If user says something isn't true, believe them immediately and stop referencing it.]")

            # Sort facts by recency and confidence
            sorted_facts = sorted(
                user_facts,
                key=lambda f: (f.get('confidence', 0.5), f.get('created_at', '')),
                reverse=True
            )

            current_length = 0
            for fact in sorted_facts:
                safe_value = prompt_sanitizer.sanitize_context_injection(fact.get('fact_value', ''))
                fact_line = f"- {fact.get('fact_key', 'info')}: {safe_value}"
                if current_length + len(fact_line) < budgets['user_facts']:
                    facts_content.append(fact_line)
                    current_length += len(fact_line)
                else:
                    break

            if len(facts_content) > 1:  # More than just the header
                context_parts.extend(facts_content)
                context_parts.append("")

        # ============================================
        # SECTION 5: Relevant Backstory (character context)
        # ============================================
        if backstory_context:
            context_parts.append("[Relevant Background - use naturally, don't explicitly reference]")
            current_length = 0
            for chunk in backstory_context:
                safe_chunk = prompt_sanitizer.sanitize_context_injection(chunk)
                if current_length + len(safe_chunk) < budgets['backstory']:
                    context_parts.append(safe_chunk)
                    current_length += len(safe_chunk)
                else:
                    # Truncate this chunk to fit remaining budget
                    remaining = budgets['backstory'] - current_length
                    if remaining > 50:  # Only add if meaningful content fits
                        context_parts.append(safe_chunk[:remaining] + "...")
                    break
            context_parts.append("")

        # ============================================
        # SECTION 6: Recent Conversation Context
        # ============================================
        if recent_interactions:
            context_parts.append("Recent conversation:")
            current_length = 0
            max_per_message = budgets['conversation'] // max(len(recent_interactions[-4:]), 1)

            for msg in recent_interactions[-4:]:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')

                # Truncate based on available budget per message
                if len(content) > max_per_message:
                    content = content[:max_per_message - 3] + "..."

                line = f"{role.title()}: {content}"
                if current_length + len(line) < budgets['conversation']:
                    context_parts.append(line)
                    current_length += len(line)

            context_parts.append("")

        # Add relevant semantic context if significantly different from recent
        unique_semantic = []
        recent_contents = {msg.get('content', '')[:100] for msg in recent_interactions}
        for msg in semantic_context:
            content = msg.get('content', '')
            if content[:100] not in recent_contents:
                unique_semantic.append(msg)

        if unique_semantic:
            context_parts.append("Relevant past context:")
            for msg in unique_semantic[:2]:  # Limit to 2 unique historical items
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:150]
                context_parts.append(f"{role.title()} (earlier): {content}...")
            context_parts.append("")

        # ============================================
        # SECTION 7: Document RAG Context
        # ============================================
        if document_chunks:
            context_parts.append("Relevant documents:")

            # Sort chunks by relevance score
            sorted_chunks = sorted(
                document_chunks,
                key=lambda c: c.get('similarity_score', 0),
                reverse=True
            )

            # Group by document but maintain relevance order
            docs_seen = set()
            current_length = 0

            for chunk in sorted_chunks:
                doc_filename = chunk['document_filename']
                similarity = chunk.get('similarity_score', 0)
                content = chunk.get('text_content', '')

                # Skip low-relevance chunks
                if similarity < self.similarity_threshold:
                    continue

                # Calculate remaining budget
                remaining_budget = budgets['documents'] - current_length
                if remaining_budget < 100:
                    break

                # Add document header if first chunk from this doc
                if doc_filename not in docs_seen:
                    docs_seen.add(doc_filename)
                    header = f"From {doc_filename}:"
                    context_parts.append(header)
                    current_length += len(header)

                # Truncate content to fit budget
                max_chunk_size = min(remaining_budget - 50, 1200)  # Reserve space for formatting
                if len(content) > max_chunk_size:
                    content = content[:max_chunk_size] + "..."

                # Format with relevance indicator
                relevance_label = "High" if similarity > 0.7 else "Medium" if similarity > 0.5 else "Low"
                chunk_line = f"[{relevance_label} relevance] {content}"
                context_parts.append(chunk_line)
                current_length += len(chunk_line)

            context_parts.append("")

        # ============================================
        # SECTION 8: Web Search Results (if available)
        # ============================================
        if web_search_context:
            # Web search context is already formatted by web_search_service
            context_parts.append(web_search_context)
            context_parts.append("")

        # ============================================
        # SECTION 9: Conflict Warnings (if any)
        # ============================================
        if conflicts:
            context_parts.append("Note: Potential information conflicts detected:")
            for conflict in conflicts[:2]:  # Limit to 2 conflicts
                context_parts.append(f"- {conflict.get('conflict_reason', 'Conflict detected')}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _truncate_to_budget(self, text: str, budget: int) -> str:
        """Truncate text to fit within a character budget."""
        if len(text) <= budget:
            return text
        return text[:budget - 3] + "..."

    def format_enhanced_prompt(
        self,
        user_message: str,
        context: Dict[str, Any],
        character_instructions: Optional[str] = None,
        show_reasoning: bool = False
    ) -> str:
        """Format the user message with context for the LLM.

        NOTE: This method now ONLY formats the user message with context.
        Character instructions should be added to the system message separately,
        not duplicated here.

        Args:
            user_message: Original user message
            context: Enhanced context from get_enhanced_context
            character_instructions: DEPRECATED - not used (kept for backward compat)
            show_reasoning: Whether to include reasoning chain in prompt

        Returns:
            Formatted user message with context (NOT including system instructions)
        """
        prompt_parts = []

        # NOTE: character_instructions are intentionally NOT added here
        # They should be in the system message, not duplicated in user message
        # This prevents double-injection of system prompts

        # Add context summary if available (uses subtle formatting to avoid LLM mimicry)
        context_summary = context.get('context_summary', '')
        if context_summary:
            # Use subtle markers that won't be mimicked by the LLM
            prompt_parts.append("[Background context for this conversation]")
            prompt_parts.append(context_summary)
            prompt_parts.append("[End background context]")
            prompt_parts.append("")

        # Add reasoning chain if requested (internal use, not shown to user)
        if show_reasoning and context.get('reasoning_chain'):
            prompt_parts.append("[Internal reasoning]")
            for step in context['reasoning_chain']:
                prompt_parts.append(f"- {step['step']}: {step['thought']}")
            prompt_parts.append("[End reasoning]")
            prompt_parts.append("")

        # Add the user message without markdown headers
        # The LLM should respond naturally to this message
        prompt_parts.append(user_message)

        return "\n".join(prompt_parts)

    def suggest_related_documents(
        self,
        query: str,
        user_id: int,
        exclude_documents: Optional[List[str]] = None,
        max_suggestions: int = 3,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Suggest documents that might be relevant to a query.

        Args:
            query: Search query
            user_id: User ID
            exclude_documents: Document IDs to exclude from suggestions
            max_suggestions: Maximum number of suggestions
            db: Database session

        Returns:
            List of suggested documents with relevance scores
        """
        if db is None:
            db = next(get_db())

        try:
            # Get search results
            search_results = document_service.search_documents(
                query=query,
                user_id=user_id,
                top_k=max_suggestions * 3,  # Get more results to filter
                similarity_threshold=0.2,  # Lower threshold for suggestions
                db=db
            )

            # Group by document and get best score per document
            document_scores = {}
            for result in search_results:
                doc_id = result['document_id']
                if exclude_documents and doc_id in exclude_documents:
                    continue

                current_score = document_scores.get(doc_id, {}).get('similarity_score', 0)
                if result['similarity_score'] > current_score:
                    document_scores[doc_id] = {
                        'document_id': doc_id,
                        'filename': result['document_filename'],
                        'similarity_score': result['similarity_score'],
                        'relevant_chunk': result['text_content'][:200] + "..." if len(result['text_content']) > 200 else result['text_content']
                    }

            # Sort by similarity and return top suggestions
            suggestions = sorted(
                document_scores.values(),
                key=lambda x: x['similarity_score'],
                reverse=True
            )[:max_suggestions]

            return suggestions

        except Exception as e:
            logger.error(f"Error suggesting related documents: {e}")
            return []

    def format_rag_prompt(
        self,
        user_message: str,
        context: Dict[str, Any],
        character_instructions: Optional[str] = None
    ) -> str:
        """Alias for format_enhanced_prompt for backward compatibility."""
        return self.format_enhanced_prompt(user_message, context, character_instructions)

# Global Enhanced Context Service instance
enhanced_context_service = EnhancedContextService()