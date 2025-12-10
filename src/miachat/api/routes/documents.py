"""
FastAPI routes for document management and RAG functionality.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from ...database.config import get_db
from ...database.models import User, Document
from ..core.document_service import document_service
from ..core.enhanced_context_service import enhanced_context_service
from ..core.embedding_service import embedding_service
from ..core.auth import get_current_user_from_session
from fastapi import Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Pydantic models for request/response
class DocumentResponse(BaseModel):
    id: str
    user_id: int
    filename: str
    original_filename: str
    doc_type: str
    file_size: int
    upload_date: str
    last_accessed: Optional[str]
    access_count: int
    is_processed: bool
    processing_status: str
    metadata: Dict[str, Any]

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    skip: int
    limit: int

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(10, ge=1, le=50, description="Maximum number of results")
    similarity_threshold: float = Field(0.3, ge=0, le=1, description="Minimum similarity score")

class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str
    text_content: str
    chunk_type: str
    chunk_index: int
    similarity_score: float
    metadata: Dict[str, Any]
    document_metadata: Dict[str, Any]

class RAGContextRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_id: Optional[int] = Field(None, description="Conversation ID")
    character_id: Optional[str] = Field(None, description="Character ID")
    include_conversation_history: bool = Field(True, description="Include conversation history")
    include_documents: bool = Field(True, description="Include document context")

class DocumentStats(BaseModel):
    total_documents: int
    processed_documents: int
    failed_documents: int
    processing_rate: float
    total_size_bytes: int
    format_distribution: Dict[str, int]
    supported_formats: List[str]

# Dependency to get current user from session
async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from session."""
    user = await get_current_user_from_session(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user

@router.post("/upload", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process a document."""
    try:
        result = await document_service.upload_document(
            file=file,
            user_id=current_user.id,
            db=db
        )
        
        if result['success']:
            return {
                "message": "Document uploaded successfully",
                "document": result['document'],
                "processing_result": result['processing_result']
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result['error']
            )
            
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of documents to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's documents with pagination."""
    try:
        result = document_service.get_user_documents(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            db=db
        )
        
        return DocumentListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in list documents endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document by ID."""
    try:
        document = document_service.get_document(
            document_id=document_id,
            user_id=current_user.id,
            db=db
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentResponse(**document.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get document endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its associated data."""
    try:
        success = document_service.delete_document(
            document_id=document_id,
            user_id=current_user.id,
            db=db
        )
        
        if success:
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete document endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the full text content of a document."""
    try:
        logger.info(f"Fetching content for document {document_id} for user {current_user.id}")

        # First check if document exists and user has access
        document = document_service.get_document(document_id, current_user.id, db)
        if not document:
            logger.warning(f"Document {document_id} not found or user {current_user.id} has no access")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )

        content = document_service.get_document_content(
            document_id=document_id,
            user_id=current_user.id,
            db=db
        )

        if content is None:
            logger.warning(f"Document {document_id} exists but has no content")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document content not available"
            )

        logger.info(f"Successfully retrieved content for document {document_id} ({len(content)} characters)")
        return {"content": content}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get document content endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/search", response_model=List[SearchResult])
async def search_documents(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search user's documents using vector similarity."""
    try:
        results = document_service.search_documents(
            query=search_request.query,
            user_id=current_user.id,
            top_k=search_request.top_k,
            similarity_threshold=search_request.similarity_threshold,
            db=db
        )
        
        return [SearchResult(**result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in search documents endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/rag/context")
async def get_rag_context(
    context_request: RAGContextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enhanced context for RAG-powered conversations."""
    try:
        context = enhanced_context_service.get_enhanced_context(
            user_message=context_request.message,
            user_id=current_user.id,
            conversation_id=context_request.conversation_id,
            character_id=context_request.character_id,
            include_conversation_history=context_request.include_conversation_history,
            include_documents=context_request.include_documents,
            db=db
        )
        
        return context
        
    except Exception as e:
        logger.error(f"Error in RAG context endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/rag/prompt")
async def format_rag_prompt(
    message: str,
    context_request: RAGContextRequest,
    character_instructions: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Format a complete RAG prompt for LLM consumption."""
    try:
        # Get context first
        context = enhanced_context_service.get_enhanced_context(
            user_message=context_request.message,
            user_id=current_user.id,
            conversation_id=context_request.conversation_id,
            character_id=context_request.character_id,
            include_conversation_history=context_request.include_conversation_history,
            include_documents=context_request.include_documents,
            db=db
        )
        
        # Format prompt
        formatted_prompt = enhanced_context_service.format_rag_prompt(
            user_message=message,
            context=context,
            character_instructions=character_instructions
        )
        
        return {
            "formatted_prompt": formatted_prompt,
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error in format RAG prompt endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/suggestions/related")
async def suggest_related_documents(
    query: str = Query(..., description="Query for finding related documents"),
    exclude: Optional[str] = Query(None, description="Comma-separated document IDs to exclude"),
    max_suggestions: int = Query(3, ge=1, le=10, description="Maximum number of suggestions"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Suggest documents related to a query."""
    try:
        exclude_list = exclude.split(',') if exclude else None
        
        suggestions = enhanced_context_service.suggest_related_documents(
            query=query,
            user_id=current_user.id,
            exclude_documents=exclude_list,
            max_suggestions=max_suggestions,
            db=db
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Error in suggest related documents endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reprocess a document (useful if processing failed initially)."""
    try:
        success = await document_service.reprocess_document(
            document_id=document_id,
            user_id=current_user.id,
            db=db
        )
        
        if success:
            return {"message": "Document reprocessing initiated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or reprocessing failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reprocess document endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/stats/overview", response_model=DocumentStats)
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics about user's documents."""
    try:
        stats = document_service.get_stats(
            user_id=current_user.id,
            db=db
        )
        
        return DocumentStats(**stats)
        
    except Exception as e:
        logger.error(f"Error in document stats endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/stats/embedding-service")
async def get_embedding_stats(
    current_user: User = Depends(get_current_user)
):
    """Get statistics about the embedding service."""
    try:
        stats = embedding_service.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error in embedding stats endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/admin/rebuild-index")
async def rebuild_embedding_index(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rebuild the FAISS embedding index (admin function)."""
    try:
        # Note: In a real system, this should be protected with admin permissions
        success = embedding_service.rebuild_index(db=db)
        
        if success:
            return {"message": "Embedding index rebuilt successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to rebuild embedding index"
            )
            
    except Exception as e:
        logger.error(f"Error in rebuild index endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/formats/supported")
async def get_supported_formats():
    """Get list of supported document formats."""
    try:
        from ..core.document_processor import document_processor
        formats = document_processor.get_supported_formats()
        
        return {
            "supported_formats": formats,
            "format_descriptions": {
                ".pdf": "Portable Document Format",
                ".docx": "Microsoft Word Document",
                ".doc": "Microsoft Word Document (legacy)",
                ".txt": "Plain Text",
                ".md": "Markdown",
                ".xlsx": "Microsoft Excel Spreadsheet",
                ".xls": "Microsoft Excel Spreadsheet (legacy)",
                ".csv": "Comma-Separated Values"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in supported formats endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Pydantic models for character-document association
class CharacterDocumentAssignRequest(BaseModel):
    character_id: str
    document_id: str
    is_active: bool = True


class CharacterDocumentResponse(BaseModel):
    character_id: str
    document_id: str
    user_id: int
    assigned_date: str
    is_active: bool
    assigned_by_user: bool


@router.get("/character-associations/{document_id}")
async def get_document_character_associations(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all character associations for a document."""
    try:
        # Get document and verify ownership
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Get character associations from metadata and format for frontend
        associations = []
        if document.doc_metadata and 'character_associations' in document.doc_metadata:
            character_ids = document.doc_metadata['character_associations']
            # Convert character IDs to the format expected by frontend
            for char_id in character_ids:
                associations.append({
                    "character_id": char_id,
                    "is_active": True,  # All metadata-based associations are active
                    "assigned_at": document.upload_date.isoformat() if document.upload_date else None
                })

        return {
            "document_id": document_id,
            "associations": associations,  # Use 'associations' key for consistency
            "character_associations": [assoc["character_id"] for assoc in associations],  # Backward compatibility
            "auto_assigned": document.doc_metadata.get('auto_assigned', False) if document.doc_metadata else False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting character associations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/character-associations")
async def assign_document_to_character(
    request: CharacterDocumentAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a document to a character/persona."""
    try:
        # Get document and verify ownership
        document = db.query(Document).filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Initialize metadata if it doesn't exist
        if not document.doc_metadata:
            document.doc_metadata = {}

        # Initialize character associations if they don't exist
        if 'character_associations' not in document.doc_metadata:
            document.doc_metadata['character_associations'] = []

        # Update character association
        if request.is_active:
            # Add character if not already associated
            if request.character_id not in document.doc_metadata['character_associations']:
                document.doc_metadata['character_associations'].append(request.character_id)
                document.doc_metadata['assigned_by_user'] = True
        else:
            # Remove character association
            if request.character_id in document.doc_metadata['character_associations']:
                document.doc_metadata['character_associations'].remove(request.character_id)

        db.commit()

        return {
            "success": True,
            "message": f"Document {'assigned to' if request.is_active else 'unassigned from'} character"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning document to character: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/characters/{character_id}/documents")
async def get_character_documents(
    character_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents assigned to a specific character."""
    try:
        # Get all user documents
        documents = db.query(Document).filter(
            Document.user_id == current_user.id
        ).all()

        # Filter documents that are associated with this character
        character_documents = []
        for doc in documents:
            if (doc.doc_metadata and
                'character_associations' in doc.doc_metadata and
                character_id in doc.doc_metadata['character_associations']):
                character_documents.append(doc.to_dict())

        return {
            "character_id": character_id,
            "documents": character_documents,
            "total_count": len(character_documents)
        }

    except Exception as e:
        logger.error(f"Error getting character documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/character-associations/{character_id}/{document_id}")
async def remove_document_from_character(
    character_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a document assignment from a character."""
    try:
        # Get document and verify ownership
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Remove character association from metadata
        if (document.doc_metadata and
            'character_associations' in document.doc_metadata and
            character_id in document.doc_metadata['character_associations']):

            document.doc_metadata['character_associations'].remove(character_id)
            db.commit()
            return {"success": True, "message": "Document unassigned from character"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Association not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing document from character: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )