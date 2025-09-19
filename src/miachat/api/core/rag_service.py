"""
RAG (Retrieval-Augmented Generation) service for document-aware conversations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from ...database.config import get_db
from .document_service import document_service
from .embedding_service import embedding_service
from .memory_service import memory_service

logger = logging.getLogger(__name__)

class RAGService:
    """Service for integrating document retrieval into conversations."""
    
    def __init__(
        self,
        max_context_chunks: int = 10,  # Increased for better document coverage
        similarity_threshold: float = 0.2,  # Lower threshold for more inclusive matching
        max_context_length: int = 6000  # Increased context length
    ):
        """Initialize the RAG service.
        
        Args:
            max_context_chunks: Maximum number of document chunks to include in context
            similarity_threshold: Minimum similarity score for including chunks
            max_context_length: Maximum total character length of document context
        """
        self.max_context_chunks = max_context_chunks
        self.similarity_threshold = similarity_threshold
        self.max_context_length = max_context_length
    
    def get_enhanced_context(
        self,
        user_message: str,
        user_id: int,
        conversation_id: Optional[int] = None,
        character_id: Optional[str] = None,
        include_conversation_history: bool = True,
        include_documents: bool = True,
        comprehensive_analysis: bool = False,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get enhanced context combining conversation history and relevant documents.

        Args:
            user_message: Current user message
            user_id: User ID for document access
            conversation_id: Optional conversation ID for history
            character_id: Optional character ID for personalized retrieval
            include_conversation_history: Whether to include conversation context
            include_documents: Whether to include document context
            comprehensive_analysis: If True, retrieves ALL chunks for complete document analysis
            db: Database session

        Returns:
            Dictionary with enhanced context information
        """
        if db is None:
            db = next(get_db())
        
        try:
            context = {
                'conversation_history': [],
                'relevant_documents': [],
                'document_chunks': [],
                'context_summary': '',
                'sources': []
            }
            
            # Get conversation history if requested
            if include_conversation_history and conversation_id:
                conversation_context = memory_service.get_context(
                    conversation_id=conversation_id,
                    current_message=user_message,
                    db=db
                )
                context['conversation_history'] = conversation_context
            
            # Get relevant documents if requested
            if include_documents:
                document_context = self._get_document_context(
                    query=user_message,
                    user_id=user_id,
                    db=db,
                    conversation_id=conversation_id,
                    character_id=character_id,
                    comprehensive_analysis=comprehensive_analysis
                )
                context.update(document_context)
            
            # Create context summary (full version for LLM)
            context['context_summary'] = self._create_context_summary(
                conversation_history=context['conversation_history'],
                document_chunks=context['document_chunks'],
                compact_mode=False
            )

            # Create compact summary for UI display
            context['context_summary_compact'] = self._create_context_summary(
                conversation_history=context['conversation_history'],
                document_chunks=context['document_chunks'],
                compact_mode=True
            )
            
            logger.info(f"Enhanced context created: {len(context['conversation_history'])} history messages, "
                       f"{len(context['document_chunks'])} document chunks")
            
            return context
            
        except Exception as e:
            logger.error(f"Error creating enhanced context: {e}")
            return {
                'conversation_history': [],
                'relevant_documents': [],
                'document_chunks': [],
                'context_summary': '',
                'context_summary_compact': '',
                'sources': [],
                'error': str(e)
            }
    
    def _get_document_context(
        self,
        query: str,
        user_id: int,
        db: Session,
        conversation_id: Optional[int] = None,
        character_id: Optional[str] = None,
        comprehensive_analysis: bool = False
    ) -> Dict[str, Any]:
        """Get relevant document context for a query.

        Args:
            query: Search query
            user_id: User ID for document access
            db: Database session
            conversation_id: Optional conversation ID for recent document context
            character_id: Optional character ID for persona-specific document filtering
            comprehensive_analysis: If True, retrieve ALL document chunks for complete analysis

        Returns:
            Dictionary with document context
        """
        try:
            # First, get recently uploaded documents (prioritize recent uploads)
            recent_chunks = []
            try:
                from ...database.models import Document, DocumentChunk
                from datetime import datetime, timedelta

                # Build base query for documents
                base_query = db.query(Document).filter(
                    Document.user_id == user_id,
                    Document.is_processed == 1
                )

                # Filter by character if specified using metadata
                if character_id:
                    # Filter documents that have this character in their associations
                    all_documents = base_query.all()
                    character_documents = [
                        doc for doc in all_documents
                        if (doc.doc_metadata and
                            'character_associations' in doc.doc_metadata and
                            character_id in doc.doc_metadata['character_associations'])
                    ]
                    document_ids = [doc.id for doc in character_documents]
                    if document_ids:
                        base_query = base_query.filter(Document.id.in_(document_ids))
                    else:
                        # No documents for this character
                        base_query = base_query.filter(Document.id.in_([]))

                # Get documents uploaded in the last 10 minutes (very recent uploads)
                very_recent_time = datetime.utcnow() - timedelta(minutes=10)
                very_recent_documents = base_query.filter(
                    Document.upload_date >= very_recent_time
                ).order_by(Document.upload_date.desc()).limit(2).all()

                # If no very recent documents, check last hour
                if not very_recent_documents:
                    recent_time = datetime.utcnow() - timedelta(hours=1)
                    very_recent_documents = base_query.filter(
                        Document.upload_date >= recent_time
                    ).order_by(Document.upload_date.desc()).limit(3).all()

                for doc in very_recent_documents:
                    # Get chunks from recent documents
                    chunks = db.query(DocumentChunk).filter(
                        DocumentChunk.document_id == doc.id
                    ).limit(8).all()  # Increased chunks for better recent document coverage

                    for chunk in chunks:
                        recent_chunks.append({
                            'chunk_id': chunk.id,
                            'document_id': chunk.document_id,
                            'document_filename': doc.original_filename,
                            'text_content': chunk.text_content,
                            'chunk_type': chunk.chunk_type,
                            'chunk_index': chunk.chunk_index,
                            'similarity_score': 1.0,  # High score for recent documents
                            'metadata': chunk.doc_metadata or {},
                            'document_metadata': doc.doc_metadata or {}
                        })

                if recent_chunks:
                    logger.info(f"Found {len(recent_chunks)} chunks from recent documents")

            except Exception as e:
                logger.warning(f"Failed to get recent documents: {e}")

            # Get document chunks based on analysis mode
            if comprehensive_analysis:
                # COMPREHENSIVE MODE: Get ALL chunks from recent documents for complete analysis
                logger.info("Using comprehensive analysis mode - retrieving all document chunks")
                from ...database.models import Document, DocumentChunk

                # Get all documents for this user/character
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
                    document_ids = [doc.id for doc in character_documents]
                    if document_ids:
                        base_query = base_query.filter(Document.id.in_(document_ids))
                    else:
                        base_query = base_query.filter(Document.id.in_([]))

                # Get recent documents (last 3 documents uploaded)
                recent_documents = base_query.order_by(Document.upload_date.desc()).limit(3).all()

                search_results = []
                for doc in recent_documents:
                    # Get ALL chunks from this document
                    chunks = db.query(DocumentChunk).filter(
                        DocumentChunk.document_id == doc.id
                    ).order_by(DocumentChunk.chunk_index).all()

                    for chunk in chunks:
                        search_results.append({
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

                logger.info(f"Comprehensive analysis: Retrieved {len(search_results)} chunks from {len(recent_documents)} recent documents")

            else:
                # SEMANTIC MODE: Search for semantically relevant document chunks
                search_results = document_service.search_documents(
                    query=query,
                    user_id=user_id,
                    top_k=self.max_context_chunks * 2,  # Get extra results for filtering
                    similarity_threshold=self.similarity_threshold,
                    character_id=character_id,
                    db=db
                )

            # Combine recent chunks with search results, avoiding duplicates
            all_chunks = recent_chunks.copy()
            seen_chunk_ids = {chunk['chunk_id'] for chunk in recent_chunks}

            for result in search_results:
                if result['chunk_id'] not in seen_chunk_ids:
                    all_chunks.append(result)
                    seen_chunk_ids.add(result['chunk_id'])

            if not all_chunks:
                return {
                    'relevant_documents': [],
                    'document_chunks': [],
                    'sources': []
                }
            
            # Process and filter results
            document_chunks = []
            seen_documents = set()
            sources = []
            total_length = 0

            for result in all_chunks:
                # Check if we've reached max context length (increased for comprehensive analysis)
                max_length = self.max_context_length * 3 if comprehensive_analysis else self.max_context_length
                chunk_length = len(result['text_content'])
                if total_length + chunk_length > max_length:
                    if len(document_chunks) == 0:
                        # Include at least one chunk even if it's long
                        truncated_content = result['text_content'][:self.max_context_length]
                        result['text_content'] = truncated_content + "..." if len(result['text_content']) > self.max_context_length else truncated_content
                        document_chunks.append(result)
                        total_length = len(result['text_content'])
                    break
                
                document_chunks.append(result)
                total_length += chunk_length
                
                # Track unique documents and sources
                doc_id = result['document_id']
                if doc_id not in seen_documents:
                    seen_documents.add(doc_id)
                    sources.append({
                        'document_id': doc_id,
                        'filename': result['document_filename'],
                        'similarity_score': result['similarity_score']
                    })
                
                # Stop if we have enough chunks (but allow more for comprehensive analysis)
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
            logger.error(f"Error getting document context: {e}")
            return {
                'relevant_documents': [],
                'document_chunks': [],
                'sources': []
            }
    
    def _create_context_summary(
        self,
        conversation_history: List[Dict[str, Any]],
        document_chunks: List[Dict[str, Any]],
        compact_mode: bool = False
    ) -> str:
        """Create a formatted context summary for the LLM.

        Args:
            conversation_history: List of conversation messages
            document_chunks: List of relevant document chunks
            compact_mode: If True, creates a condensed version for UI display

        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add conversation history
        if conversation_history:
            context_parts.append("## Recent Conversation History")
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                context_parts.append(f"**{role.title()}**: {content}")
            context_parts.append("")
        
        # Add document context
        if document_chunks:
            if compact_mode:
                # COMPACT MODE: Create condensed reference display
                context_parts.append("## Document Sources")

                # Group chunks by document and create summaries
                docs_summary = {}
                for chunk in document_chunks:
                    doc_filename = chunk['document_filename']
                    if doc_filename not in docs_summary:
                        docs_summary[doc_filename] = {
                            'chunks': [],
                            'max_relevance': 0,
                            'topics': set()
                        }

                    docs_summary[doc_filename]['chunks'].append(chunk)
                    docs_summary[doc_filename]['max_relevance'] = max(
                        docs_summary[doc_filename]['max_relevance'],
                        chunk['similarity_score']
                    )

                    # Extract topic keywords from content
                    content_words = chunk['text_content'].lower().split()
                    topics = [word for word in content_words if len(word) > 4 and word.isalpha()][:3]
                    docs_summary[doc_filename]['topics'].update(topics)

                # Format compact document references
                for doc_filename, info in docs_summary.items():
                    chunk_count = len(info['chunks'])
                    relevance = info['max_relevance']
                    topics = list(info['topics'])[:3]  # Top 3 topics

                    topics_str = ", ".join(topics) if topics else "general content"
                    context_parts.append(f"📄 **{doc_filename}** ({chunk_count} sections, {relevance:.0%} relevance)")
                    context_parts.append(f"   Topics: {topics_str}")
                    context_parts.append("")

            else:
                # FULL MODE: Complete document context (existing behavior)
                context_parts.append("## Relevant Information from User's Documents")

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
                    for chunk in chunks:
                        similarity = chunk['similarity_score']
                        content = chunk['text_content']
                        # Truncate extremely long chunks but allow much more content
                        if len(content) > 2000:
                            content = content[:2000] + "..."
                        context_parts.append(f"- (Relevance: {similarity:.2f}) {content}")
                    context_parts.append("")
        
        if not context_parts:
            return "No additional context available."
        
        context_parts.append("---")
        context_parts.append("Please use the above information to provide more accurate and informed responses. "
                           "When referencing information from documents, you may mention the source document.")
        
        return "\n".join(context_parts)
    
    def format_rag_prompt(
        self,
        user_message: str,
        context: Dict[str, Any],
        character_instructions: Optional[str] = None
    ) -> str:
        """Format a complete prompt with RAG context for the LLM.
        
        Args:
            user_message: Original user message
            context: Enhanced context from get_enhanced_context
            character_instructions: Optional character-specific instructions
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Add character instructions if provided
        if character_instructions:
            prompt_parts.append(character_instructions)
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
    
    def extract_sources_from_response(
        self,
        response: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract and format sources referenced in a response.
        
        Args:
            response: Generated response text
            context: Context used for generation
            
        Returns:
            Dictionary with response and source information
        """
        sources = context.get('sources', [])
        document_chunks = context.get('document_chunks', [])
        
        # Create source citations
        citations = []
        for i, source in enumerate(sources, 1):
            citations.append({
                'number': i,
                'document_id': source['document_id'],
                'filename': source['filename'],
                'similarity_score': source['similarity_score']
            })
        
        return {
            'response': response,
            'sources': citations,
            'context_used': {
                'conversation_messages': len(context.get('conversation_history', [])),
                'document_chunks': len(document_chunks),
                'documents_referenced': len(sources)
            },
            'context_summary_compact': context.get('context_summary_compact', ''),
            'context_summary_full': context.get('context_summary', '')
        }
    
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

# Global RAG service instance
rag_service = RAGService()