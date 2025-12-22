"""
Export API routes for MinouChat.

Provides endpoints for exporting conversations and summaries to various formats:
- PDF (.pdf) - Final documents, sharing
- Word (.docx) - Formal reports, editable documents
- Markdown (.md) - Technical docs, GitHub-friendly
- Plain text (.txt) - Universal, simple notes

Supports LLM-powered document generation with category-specific templates:
- Assistant: Research Summary, Decision Log, Project Brief, Email Draft
- Coach: Goal Progress, Weekly Review, Action Plan, Values Assessment, Life Areas
- Teacher: Lesson Summary, Study Guide, Concept Explanation, Practice Problems
- Friend: Advice & Wisdom, Collaborative Short Story
- Creative: Story Summary (brief/detailed)
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.export_service import (
    export_service,
    ExportFormat,
    DocumentType,
    DOCUMENT_TYPES,
    get_document_types_for_category
)
from ..core.conversation_service import conversation_service
from ..core.clerk_auth import get_current_user_from_session
from ..core.llm_client import llm_client
from ..core.character_manager import character_manager
from ...database.config import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


# Request models
class ConversationExportRequest(BaseModel):
    format: str = "pdf"  # pdf, docx, md, txt
    include_system: bool = False
    include_timestamps: bool = True


class SummaryExportRequest(BaseModel):
    format: str = "pdf"  # pdf, docx, md, txt


class DocumentGenerateRequest(BaseModel):
    """Request model for LLM-powered document generation."""
    document_type: str  # e.g., "research_summary", "goal_progress_report"
    format: str = "pdf"  # pdf, docx, md, txt
    custom_instructions: Optional[str] = None
    sfw_mode: bool = True  # For Creative/Roleplay content


def _parse_format(format_str: str) -> ExportFormat:
    """Parse format string to ExportFormat enum."""
    format_map = {
        "pdf": ExportFormat.PDF,
        "docx": ExportFormat.DOCX,
        "word": ExportFormat.DOCX,
        "md": ExportFormat.MARKDOWN,
        "markdown": ExportFormat.MARKDOWN,
        "txt": ExportFormat.TEXT,
        "text": ExportFormat.TEXT
    }
    format_lower = format_str.lower()
    if format_lower not in format_map:
        raise ValueError(f"Invalid format: {format_str}. Supported: pdf, docx, md, txt")
    return format_map[format_lower]


@router.post("/conversation/{session_id}")
async def export_conversation(
    session_id: str,
    request_data: ConversationExportRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Export a conversation to the specified format.

    Args:
        session_id: The conversation session ID
        request_data: Export options (format, include_system, include_timestamps)

    Returns:
        StreamingResponse with the exported file
    """
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Parse format
        try:
            export_format = _parse_format(request_data.format)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Get session info
        session = conversation_service.get_session(session_id, db)
        if not session:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify ownership
        if str(session.get("user_id")) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get conversation history
        messages = conversation_service.get_conversation_history(session_id, limit=500, db=db)
        if not messages:
            raise HTTPException(status_code=404, detail="No messages found in conversation")

        # Get character name
        character_id = session.get("character_id")
        character_name = "AI Assistant"
        if character_id:
            character = character_manager.get_character(character_id)
            if character:
                character_name = character.get("name", "AI Assistant")

        # Generate title from conversation title or first message
        conversation_id = session.get("conversation_id")
        if conversation_id:
            from ...database.models import Conversation
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            title = conv.title if conv and conv.title else f"Conversation with {character_name}"
        else:
            title = f"Conversation with {character_name}"

        # Export
        buffer = export_service.export_conversation(
            messages=messages,
            title=title,
            format=export_format,
            character_name=character_name,
            include_system=request_data.include_system,
            include_timestamps=request_data.include_timestamps
        )

        # Generate filename
        safe_title = "".join(c for c in title if c.isalnum() or c in ' -_').strip()[:50]
        safe_title = safe_title.replace(' ', '_')
        filename = f"{safe_title}.{export_service.get_file_extension(export_format)}"

        content_type = export_service.get_content_type(export_format)

        return StreamingResponse(
            buffer,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting conversation {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export conversation")


@router.post("/summary/{session_id}")
async def export_summary(
    session_id: str,
    request_data: SummaryExportRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Generate and export an LLM-summarized version of a conversation.

    Args:
        session_id: The conversation session ID
        request_data: Export options (format)

    Returns:
        StreamingResponse with the exported summary file
    """
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Parse format
        try:
            export_format = _parse_format(request_data.format)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Get session info
        session = conversation_service.get_session(session_id, db)
        if not session:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify ownership
        if str(session.get("user_id")) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get conversation history
        messages = conversation_service.get_conversation_history(session_id, limit=500, db=db)
        if not messages:
            raise HTTPException(status_code=404, detail="No messages found in conversation")

        # Get character info
        character_id = session.get("character_id")
        character_name = "AI Assistant"
        model_config = None

        if character_id:
            character = character_manager.get_character(character_id)
            if character:
                character_name = character.get("name", "AI Assistant")
                model_config = character.get("model_config")

        # Default model config if not set
        if not model_config:
            model_config = {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "temperature": 0.5,
                "max_tokens": 1024
            }

        # Build conversation context for summarization
        conversation_text = []
        for msg in messages:
            role = "User" if msg.get("role") == "user" else character_name
            content = msg.get("content", "")[:500]  # Truncate long messages
            conversation_text.append(f"{role}: {content}")

        # Limit context size
        context = "\n\n".join(conversation_text[-30:])  # Last 30 messages

        # Generate summary using LLM
        system_prompt = """You are a helpful assistant that creates concise, well-organized summaries of conversations.
Create a summary that captures:
1. The main topics discussed
2. Key decisions or conclusions reached
3. Any action items or next steps mentioned
4. The overall tone and outcome of the conversation

Format your response with clear sections. Be concise but comprehensive."""

        prompt_messages = [
            {"role": "user", "content": f"Please summarize this conversation:\n\n{context}"}
        ]

        try:
            summary_text = llm_client.generate_response_with_config(
                messages=prompt_messages,
                system_prompt=system_prompt,
                model_config=model_config
            )
        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
            # Fallback to basic summary
            summary_text = f"Conversation between User and {character_name} containing {len(messages)} messages."

        # Extract key points (simplified - could use LLM for this too)
        key_points = []
        if len(messages) > 0:
            # Get first and last topics mentioned
            first_msg = messages[0].get("content", "")[:100]
            last_msg = messages[-1].get("content", "")[:100]
            key_points.append(f"Started with: {first_msg}...")
            if len(messages) > 1:
                key_points.append(f"Ended with: {last_msg}...")
            key_points.append(f"Total messages: {len(messages)}")

        # Generate title
        title = f"Summary: Conversation with {character_name}"

        # Export
        buffer = export_service.export_summary(
            summary_text=summary_text,
            title=title,
            format=export_format,
            character_name=character_name,
            key_points=key_points,
            original_message_count=len(messages)
        )

        # Generate filename
        safe_title = "".join(c for c in title if c.isalnum() or c in ' -_').strip()[:50]
        safe_title = safe_title.replace(' ', '_')
        filename = f"{safe_title}.{export_service.get_file_extension(export_format)}"

        content_type = export_service.get_content_type(export_format)

        return StreamingResponse(
            buffer,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting summary for {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate summary")


@router.get("/formats")
async def list_formats():
    """List available export formats.

    Returns:
        List of supported export formats with descriptions
    """
    return {
        "formats": [
            {
                "id": "pdf",
                "name": "PDF",
                "description": "Final documents, sharing",
                "extension": ".pdf"
            },
            {
                "id": "docx",
                "name": "Word Document",
                "description": "Formal reports, editable documents",
                "extension": ".docx"
            },
            {
                "id": "md",
                "name": "Markdown",
                "description": "Technical docs, GitHub-friendly",
                "extension": ".md"
            },
            {
                "id": "txt",
                "name": "Plain Text",
                "description": "Universal, simple notes",
                "extension": ".txt"
            }
        ]
    }


@router.get("/document-types/{category}")
async def get_document_types(category: str):
    """Get available document types for a persona category.

    Args:
        category: The persona category (Assistant, Coach, Teacher, Friend, Creative)

    Returns:
        List of available document types for the category
    """
    # Normalize category name
    category_normalized = category.title()

    doc_types = get_document_types_for_category(category_normalized)
    if not doc_types:
        # Return empty list for unknown categories
        return {"category": category_normalized, "document_types": []}

    return {
        "category": category_normalized,
        "document_types": doc_types
    }


def _parse_document_type(doc_type_str: str) -> DocumentType:
    """Parse document type string to DocumentType enum."""
    try:
        return DocumentType(doc_type_str.lower())
    except ValueError:
        valid_types = [dt.value for dt in DocumentType]
        raise ValueError(f"Invalid document type: {doc_type_str}. Valid types: {valid_types}")


@router.post("/generate/{session_id}")
async def generate_document(
    session_id: str,
    request_data: DocumentGenerateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Generate a document using LLM from a conversation.

    This endpoint uses the conversation context to generate well-structured
    documents based on the persona category and selected document type.

    Args:
        session_id: The conversation session ID
        request_data: Document generation options

    Returns:
        StreamingResponse with the generated document file
    """
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Parse format
        try:
            export_format = _parse_format(request_data.format)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Parse document type
        try:
            document_type = _parse_document_type(request_data.document_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Get session info
        session = conversation_service.get_session(session_id, db)
        if not session:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify ownership
        if str(session.get("user_id")) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get conversation history
        messages = conversation_service.get_conversation_history(session_id, limit=500, db=db)
        if not messages:
            raise HTTPException(status_code=404, detail="No messages found in conversation")

        # Get character info
        character_id = session.get("character_id")
        character_name = "AI Assistant"
        character_category = "Assistant"
        model_config = None

        if character_id:
            character = character_manager.get_character(character_id)
            if character:
                character_name = character.get("name", "AI Assistant")
                character_category = character.get("category", "Assistant")
                model_config = character.get("model_config")

        # Default model config if not set
        if not model_config:
            model_config = {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "temperature": 0.7,
                "max_tokens": 4096
            }

        # Generate the document using LLM
        try:
            buffer, filename = export_service.generate_document_with_llm(
                messages=messages,
                document_type=document_type,
                export_format=export_format,
                character_name=character_name,
                character_category=character_category,
                custom_instructions=request_data.custom_instructions,
                sfw_mode=request_data.sfw_mode,
                llm_client=llm_client,
                model_config=model_config
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        content_type = export_service.get_content_type(export_format)

        return StreamingResponse(
            buffer,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating document for {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate document")


@router.get("/document-types")
async def list_all_document_types():
    """List all available document types grouped by category.

    Returns:
        All document types organized by persona category
    """
    categories = ["Assistant", "Coach", "Teacher", "Friend", "Creative"]
    result = {}

    for category in categories:
        result[category] = get_document_types_for_category(category)

    return {"document_types_by_category": result}
