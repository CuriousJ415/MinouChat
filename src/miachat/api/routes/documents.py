"""
FastAPI routes for document management and RAG functionality.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from ..core.database import get_db
from ..core.models import User
from ..core.document_service import document_service
from ..core.rag_service import rag_service
from ..core.embedding_service import embedding_service

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

# Dependency to get current user (placeholder - implement based on your auth system)
async def get_current_user() -> User:
    """Get current authenticated user. Replace with your auth implementation."""
    # This is a placeholder - implement based on your authentication system
    # For now, return a mock user with ID 1
    user = User()
    user.id = 1
    user.username = "test_user"
    user.email = "test@example.com"
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
        content = document_service.get_document_content(
            document_id=document_id,
            user_id=current_user.id,
            db=db
        )
        
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or not processed"
            )
        
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
        context = rag_service.get_enhanced_context(
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
        context = rag_service.get_enhanced_context(
            user_message=context_request.message,
            user_id=current_user.id,
            conversation_id=context_request.conversation_id,
            character_id=context_request.character_id,
            include_conversation_history=context_request.include_conversation_history,
            include_documents=context_request.include_documents,
            db=db
        )
        
        # Format prompt
        formatted_prompt = rag_service.format_rag_prompt(
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
        
        suggestions = rag_service.suggest_related_documents(
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