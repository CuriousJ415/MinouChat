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
from sqlalchemy.orm import Session
from ...database.config import get_db
from .document_service import document_service
from .embedding_service import embedding_service
from .memory_service import memory_service

logger = logging.getLogger(__name__)

class EnhancedContextService:
    """Service for intelligent context synthesis and reasoning."""

    def __init__(
        self,
        max_context_chunks: int = 10,
        similarity_threshold: float = 0.5,
        max_context_length: int = 6000,
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
                    reasoning_chain=context['reasoning_chain'] if enable_reasoning else None
                )
                context.update(document_context)

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
                user_message=user_message
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
        reasoning_chain: Optional[List[Dict[str, Any]]] = None
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

        Returns:
            Dictionary with document context
        """
        try:
            # Start with referenced documents
            all_chunks = []

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
                    user_id, db, character_id, reasoning_chain
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
        reasoning_chain: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get comprehensive document chunks for complete analysis.

        Args:
            user_id: User ID
            db: Database session
            character_id: Optional character ID
            reasoning_chain: Optional reasoning chain to update

        Returns:
            List of document chunks
        """
        try:
            from ...database.models import Document, DocumentChunk

            # Get recent documents
            base_query = db.query(Document).filter(
                Document.user_id == user_id,
                Document.is_processed == 1
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
        user_message: str
    ) -> str:
        """Create an intelligent context summary for the LLM.

        Args:
            recent_interactions: Recent conversation interactions
            semantic_context: Semantic memory context
            document_chunks: Document chunks
            document_references: Parsed document references
            conflicts: Detected conflicts
            user_message: Current user message

        Returns:
            Formatted context string
        """
        context_parts = []

        # Add user request context
        context_parts.append("## Current User Request")
        context_parts.append(f"User Message: {user_message}")

        if document_references:
            ref_text = ", ".join([ref['reference_text'] for ref in document_references])
            context_parts.append(f"Document References Detected: {ref_text}")

        context_parts.append("")

        # Add recent conversation context (focused on last 4 interactions)
        if recent_interactions:
            context_parts.append("## Recent Conversation Context (Last 4 Interactions)")
            for msg in recent_interactions[-4:]:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                # Truncate very long messages
                if len(content) > 300:
                    content = content[:300] + "..."
                context_parts.append(f"**{role.title()}**: {content}")
            context_parts.append("")

        # Add relevant historical context if different from recent
        if semantic_context and len(semantic_context) > len(recent_interactions):
            additional_context = [msg for msg in semantic_context if msg not in recent_interactions]
            if additional_context:
                context_parts.append("## Relevant Historical Context")
                for msg in additional_context[:3]:  # Limit historical context
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    if len(content) > 200:
                        content = content[:200] + "..."
                    context_parts.append(f"**{role.title()}** (Historical): {content}")
                context_parts.append("")

        # Add document context
        if document_chunks:
            context_parts.append("## Relevant Document Information")

            # Group chunks by document
            docs_content = {}
            for chunk in document_chunks:
                doc_filename = chunk['document_filename']
                if doc_filename not in docs_content:
                    docs_content[doc_filename] = []
                docs_content[doc_filename].append(chunk)

            # Format each document's content
            for doc_filename, chunks in docs_content.items():
                context_parts.append(f"### From: {doc_filename}")
                for chunk in chunks[:5]:  # Limit chunks per document
                    similarity = chunk['similarity_score']
                    content = chunk['text_content']
                    # Truncate very long chunks
                    if len(content) > 1500:
                        content = content[:1500] + "..."
                    context_parts.append(f"- (Relevance: {similarity:.2f}) {content}")
                context_parts.append("")

        # Add conflict information if detected
        if conflicts:
            context_parts.append("## ⚠️ Potential Information Conflicts Detected")
            for conflict in conflicts:
                context_parts.append(f"- **Conflict**: {conflict.get('conflict_reason', 'Unknown conflict')}")
                context_parts.append(f"  - Source 1 ({conflict['source1']}): {conflict['snippet1']}")
                context_parts.append(f"  - Source 2 ({conflict['source2']}): {conflict['snippet2']}")
            context_parts.append("*Please address any conflicts in your response.*")
            context_parts.append("")

        # Add instructions
        context_parts.append("---")
        context_parts.append("**Instructions**: Use the above context to provide accurate, informed responses. "
                           "Reference specific sources when appropriate. If conflicts exist, acknowledge them "
                           "and help the user understand the different perspectives. Focus on addressing the "
                           "user's specific request while considering all available context.")

        return "\n".join(context_parts)

    def format_enhanced_prompt(
        self,
        user_message: str,
        context: Dict[str, Any],
        character_instructions: Optional[str] = None,
        show_reasoning: bool = False
    ) -> str:
        """Format a complete prompt with enhanced context for the LLM.

        Args:
            user_message: Original user message
            context: Enhanced context from get_enhanced_context
            character_instructions: Optional character-specific instructions
            show_reasoning: Whether to include reasoning chain in prompt

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Add character instructions if provided
        if character_instructions:
            prompt_parts.append(character_instructions)
            prompt_parts.append("")

        # Add reasoning chain if requested
        if show_reasoning and context.get('reasoning_chain'):
            prompt_parts.append("## Reasoning Process")
            for step in context['reasoning_chain']:
                prompt_parts.append(f"**{step['step'].title()}**: {step['thought']}")
            prompt_parts.append("")

        # Add context if available
        if context.get('context_summary'):
            prompt_parts.append("## Context Information")
            prompt_parts.append(context['context_summary'])
            prompt_parts.append("")

        # Add the user message
        prompt_parts.append("## User Message")
        prompt_parts.append(user_message)

        return "\n".join(prompt_parts)

# Global Enhanced Context Service instance
enhanced_context_service = EnhancedContextService()