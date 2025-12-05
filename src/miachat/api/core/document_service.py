"""
Document service for managing document upload, processing, and retrieval.
"""

import os
import uuid
import shutil
import logging
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import UploadFile
from ...database.models import Document, DocumentChunk, User
from ...database.config import get_db
from .document_processor import document_processor
from .embedding_service import embedding_service

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for comprehensive document management with RAG capabilities."""
    
    def __init__(self, documents_dir: str = None, max_file_size: int = 50 * 1024 * 1024):
        """Initialize the document service.

        Args:
            documents_dir: Directory to store uploaded documents
            max_file_size: Maximum file size in bytes (default 50MB)
        """
        self.documents_dir = documents_dir or os.getenv("DOCUMENTS_DIR", "./documents")
        self.max_file_size = max_file_size

        # Ensure documents directory exists
        os.makedirs(self.documents_dir, exist_ok=True)
    
    async def upload_document(
        self, 
        file: UploadFile, 
        user_id: int, 
        db: Session = None
    ) -> Dict[str, Any]:
        """Upload and process a document.
        
        Args:
            file: Uploaded file object
            user_id: ID of the user uploading the document
            db: Database session
            
        Returns:
            Dictionary with upload result and document information
        """
        if db is None:
            db = next(get_db())
        
        try:
            # Validate file
            validation_result = self._validate_file(file)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'document': None
                }
            
            # Generate unique document ID and filename
            document_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix.lower()
            stored_filename = f"{document_id}{file_extension}"
            file_path = os.path.join(self.documents_dir, stored_filename)
            
            # Save file to disk
            await self._save_file(file, file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create document record
            document = Document(
                id=document_id,
                user_id=user_id,
                filename=stored_filename,
                original_filename=file.filename,
                file_path=file_path,
                doc_type=file_extension[1:],  # Remove the dot
                file_size=file_size,
                is_processed=0,
                processing_status='pending'
            )
            
            db.add(document)
            db.commit()
            
            # Process document asynchronously (in a real system, this would be queued)
            processing_result = await self._process_document_async(document, db)
            
            return {
                'success': True,
                'document': document.to_dict(),
                'processing_result': processing_result
            }
            
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            db.rollback()
            
            # Clean up file if it was saved
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            
            return {
                'success': False,
                'error': str(e),
                'document': None
            }
    
    def get_user_documents(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 50,
        db: Session = None
    ) -> Dict[str, Any]:
        """Get documents for a user.
        
        Args:
            user_id: User ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            db: Database session
            
        Returns:
            Dictionary with documents and pagination info
        """
        if db is None:
            db = next(get_db())
        
        try:
            # Get total count
            total = db.query(Document).filter(Document.user_id == user_id).count()
            
            # Get documents
            documents = (
                db.query(Document)
                .filter(Document.user_id == user_id)
                .order_by(Document.upload_date.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            
            return {
                'documents': [doc.to_dict() for doc in documents],
                'total': total,
                'skip': skip,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"Error getting user documents: {e}")
            return {
                'documents': [],
                'total': 0,
                'skip': skip,
                'limit': limit,
                'error': str(e)
            }
    
    def get_document(self, document_id: str, user_id: int, db: Session = None) -> Optional[Document]:
        """Get a specific document by ID.
        
        Args:
            document_id: Document ID
            user_id: User ID (for ownership check)
            db: Database session
            
        Returns:
            Document object or None if not found/accessible
        """
        if db is None:
            db = next(get_db())
        
        try:
            document = (
                db.query(Document)
                .filter(Document.id == document_id, Document.user_id == user_id)
                .first()
            )
            
            if document:
                document.mark_accessed()
                db.commit()
            
            return document
            
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {e}")
            return None
    
    def delete_document(self, document_id: str, user_id: int, db: Session = None) -> bool:
        """Delete a document and its associated data.
        
        Args:
            document_id: Document ID
            user_id: User ID (for ownership check)
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        if db is None:
            db = next(get_db())
        
        try:
            document = (
                db.query(Document)
                .filter(Document.id == document_id, Document.user_id == user_id)
                .first()
            )
            
            if not document:
                return False
            
            # Remove embeddings from FAISS index
            embedding_service.remove_document_embeddings(document_id, db)
            
            # Delete file from disk
            if os.path.exists(document.file_path):
                try:
                    os.remove(document.file_path)
                except Exception as e:
                    logger.warning(f"Could not delete file {document.file_path}: {e}")
            
            # Delete database records (chunks will be deleted via cascade)
            db.delete(document)
            db.commit()
            
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            db.rollback()
            return False
    
    def search_documents(
        self,
        query: str,
        user_id: int,
        top_k: int = 10,
        similarity_threshold: float = 0.3,
        character_id: Optional[str] = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Search user's documents using vector similarity.

        Args:
            query: Search query
            user_id: User ID
            top_k: Maximum number of results
            similarity_threshold: Minimum similarity score
            character_id: Optional character ID for persona-specific filtering
            db: Database session

        Returns:
            List of search results with document chunks and metadata
        """
        if db is None:
            db = next(get_db())
        
        try:
            # Use embedding service for vector search
            results = embedding_service.search_similar_chunks(
                query=query,
                user_id=user_id,
                top_k=top_k * 2,  # Get more results to filter
                similarity_threshold=similarity_threshold,
                db=db
            )

            # Filter by character if specified
            if character_id:
                # Get document IDs assigned to this character
                character_doc_ids = db.query(CharacterDocument.document_id).filter(
                    CharacterDocument.character_id == character_id,
                    CharacterDocument.is_active == True
                ).all()
                character_doc_ids = {doc_id[0] for doc_id in character_doc_ids}

                # Filter results to only include documents assigned to this character
                filtered_results = []
                for result in results:
                    if result.get('document_id') in character_doc_ids:
                        filtered_results.append(result)
                        if len(filtered_results) >= top_k:
                            break

                results = filtered_results
                logger.info(f"Character-filtered search for {character_id}: {len(results)} results")

            logger.info(f"Document search for user {user_id}: '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def get_document_content(self, document_id: str, user_id: int, db: Session = None) -> Optional[str]:
        """Get the full text content of a document.
        
        Args:
            document_id: Document ID
            user_id: User ID (for ownership check)
            db: Database session
            
        Returns:
            Document text content or None if not found/accessible
        """
        document = self.get_document(document_id, user_id, db)
        if document and document.text_content:
            return document.text_content
        return None
    
    async def reprocess_document(self, document_id: str, user_id: int, db: Session = None) -> bool:
        """Reprocess a document (useful if processing failed initially).
        
        Args:
            document_id: Document ID
            user_id: User ID (for ownership check)
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        if db is None:
            db = next(get_db())
        
        try:
            document = self.get_document(document_id, user_id, db)
            if not document:
                return False
            
            # Remove existing embeddings
            embedding_service.remove_document_embeddings(document_id, db)
            
            # Remove existing chunks
            db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
            
            # Reset processing status
            document.is_processed = 0
            document.processing_status = 'pending'
            db.commit()
            
            # Reprocess
            processing_result = await self._process_document_async(document, db)
            
            return processing_result['success']
            
        except Exception as e:
            logger.error(f"Error reprocessing document {document_id}: {e}")
            return False
    
    def _validate_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate uploaded file.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dictionary with validation result
        """
        # Check file size
        if hasattr(file, 'size') and file.size > self.max_file_size:
            return {
                'valid': False,
                'error': f'File size ({file.size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)'
            }
        
        # Check file type
        if not document_processor.is_supported(file.filename):
            supported = ', '.join(document_processor.get_supported_formats())
            return {
                'valid': False,
                'error': f'File type not supported. Supported formats: {supported}'
            }
        
        # Check filename
        if not file.filename or len(file.filename.strip()) == 0:
            return {
                'valid': False,
                'error': 'Invalid filename'
            }
        
        return {'valid': True, 'error': None}
    
    async def _save_file(self, file: UploadFile, file_path: str):
        """Save uploaded file to disk.
        
        Args:
            file: Uploaded file object
            file_path: Path where to save the file
        """
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"Error saving file to {file_path}: {e}")
            raise
    
    async def _process_document_async(self, document: Document, db: Session) -> Dict[str, Any]:
        """Process a document asynchronously.
        
        Args:
            document: Document object to process
            db: Database session
            
        Returns:
            Dictionary with processing result
        """
        try:
            # Update status
            document.processing_status = 'processing'
            db.commit()
            
            # Process document
            processing_result = document_processor.process_document(
                document.file_path, 
                document.original_filename
            )
            
            # Update document with extracted text and metadata
            document.text_content = processing_result['text_content']
            document.content_hash = processing_result['content_hash']
            document.doc_metadata = processing_result['metadata']
            
            # Create chunk records
            chunks_data = []
            for chunk_data in processing_result['chunks']:
                try:
                    chunk = DocumentChunk(
                        id=chunk_data['id'],
                        document_id=document.id,
                        chunk_index=chunk_data['chunk_index'],
                        text_content=chunk_data['text_content'],
                        chunk_type=chunk_data['chunk_type'],
                        start_char=chunk_data['start_char'],
                        end_char=chunk_data['end_char'],
                        word_count=chunk_data['word_count'],
                        doc_metadata={}
                    )
                    logger.info(f"Creating chunk {chunk.id} for document {document.id}")
                    db.add(chunk)
                    chunks_data.append(chunk_data)
                except Exception as e:
                    logger.error(f"Error creating chunk {chunk_data.get('id', 'unknown')}: {e}")
                    raise

            logger.info(f"Committing {len(chunks_data)} chunks to database")
            db.commit()
            logger.info(f"Successfully committed chunks to database")
            
            # Create embeddings
            embedding_success = embedding_service.add_document_embeddings(
                document.id, 
                chunks_data, 
                db
            )
            
            # Update processing status
            if embedding_success:
                document.is_processed = 1
                document.processing_status = 'completed'
            else:
                document.processing_status = 'failed'
            
            db.commit()
            
            logger.info(f"Processed document {document.id}: {len(chunks_data)} chunks created")
            
            return {
                'success': embedding_success,
                'chunks_created': len(chunks_data),
                'text_length': len(processing_result['text_content']),
                'embeddings_created': embedding_success
            }
            
        except Exception as e:
            logger.error(f"Error processing document {document.id}: {e}")
            
            # Update status to failed
            try:
                document.processing_status = 'failed'
                db.commit()
            except Exception:
                pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_stats(self, user_id: Optional[int] = None, db: Session = None) -> Dict[str, Any]:
        """Get statistics about documents.
        
        Args:
            user_id: Optional user ID to filter stats
            db: Database session
            
        Returns:
            Dictionary with statistics
        """
        if db is None:
            db = next(get_db())
        
        try:
            query = db.query(Document)
            if user_id:
                query = query.filter(Document.user_id == user_id)
            
            total_documents = query.count()
            processed_documents = query.filter(Document.is_processed == 1).count()
            failed_documents = query.filter(Document.processing_status == 'failed').count()
            
            # Get total file size
            total_size = db.query(Document.file_size).filter(Document.user_id == user_id if user_id else True).all()
            total_size = sum(size[0] for size in total_size if size[0])
            
            # Get format distribution
            format_counts = {}
            formats = db.query(Document.doc_type).filter(Document.user_id == user_id if user_id else True).all()
            for fmt in formats:
                if fmt[0]:
                    format_counts[fmt[0]] = format_counts.get(fmt[0], 0) + 1
            
            return {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'failed_documents': failed_documents,
                'processing_rate': (processed_documents / total_documents * 100) if total_documents > 0 else 0,
                'total_size_bytes': total_size,
                'format_distribution': format_counts,
                'supported_formats': document_processor.get_supported_formats()
            }
            
        except Exception as e:
            logger.error(f"Error getting document stats: {e}")
            return {}

# Global document service instance
document_service = DocumentService()