"""
API routes for artifact generation and management.
"""

import os
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.artifact_service import (
    artifact_service,
    ArtifactType,
    ExportFormat,
    ArtifactMetadata
)
from ..core.clerk_auth import get_current_user_from_session
from ...database.config import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Request models
class GenerateArtifactRequest(BaseModel):
    artifact_type: str  # Will be converted to ArtifactType
    format: str  # Will be converted to ExportFormat
    title: Optional[str] = None
    content: dict
    character_id: Optional[str] = None
    session_id: Optional[str] = None
    source_documents: Optional[List[str]] = None

class ArtifactResponse(BaseModel):
    id: str
    title: str
    artifact_type: str
    format: str
    created_at: str
    file_size: int
    download_url: str

# Helper functions
def convert_artifact_type(type_str: str) -> ArtifactType:
    """Convert string to ArtifactType enum."""
    type_mapping = {
        'summary': ArtifactType.SUMMARY,
        'report': ArtifactType.REPORT,
        'analysis': ArtifactType.ANALYSIS,
        'data_table': ArtifactType.DATA_TABLE,
        'conversation_export': ArtifactType.CONVERSATION_EXPORT,
        'document_analysis': ArtifactType.DOCUMENT_ANALYSIS
    }
    if type_str not in type_mapping:
        raise ValueError(f"Invalid artifact type: {type_str}")
    return type_mapping[type_str]

def convert_export_format(format_str: str) -> ExportFormat:
    """Convert string to ExportFormat enum."""
    format_mapping = {
        'md': ExportFormat.MARKDOWN,
        'markdown': ExportFormat.MARKDOWN,
        'txt': ExportFormat.TEXT,
        'text': ExportFormat.TEXT,
        'csv': ExportFormat.CSV
    }
    if format_str.lower() not in format_mapping:
        raise ValueError(f"Invalid export format: {format_str}")
    return format_mapping[format_str.lower()]

@router.post("/generate", response_model=ArtifactResponse)
async def generate_artifact(
    request: GenerateArtifactRequest,
    request_obj: Request,
    db: Session = Depends(get_db)
):
    """Generate a new artifact with the specified content and format."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request_obj, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Convert string enums
        artifact_type = convert_artifact_type(request.artifact_type)
        export_format = convert_export_format(request.format)

        # Generate the artifact
        metadata = artifact_service.generate_artifact(
            artifact_type=artifact_type,
            content=request.content,
            format=export_format,
            user_id=current_user.id,
            title=request.title,
            character_id=request.character_id,
            session_id=request.session_id,
            source_documents=request.source_documents
        )

        return ArtifactResponse(
            id=metadata.id,
            title=metadata.title,
            artifact_type=metadata.artifact_type.value,
            format=metadata.format.value,
            created_at=metadata.created_at.isoformat(),
            file_size=metadata.file_size or 0,
            download_url=f"/api/artifacts/{metadata.id}/download"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating artifact: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate artifact")

@router.get("/list")
async def list_artifacts(
    request: Request,
    db: Session = Depends(get_db)
):
    """List all artifacts for the current user."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Get user artifacts (simplified - in a real implementation, store metadata in DB)
        artifacts = []
        output_dir = artifact_service.output_dir

        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                # Extract artifact ID from filename (first part before underscore)
                parts = filename.split('_')
                if len(parts) >= 2:
                    artifact_id = parts[0]
                    file_path = os.path.join(output_dir, filename)
                    if os.path.isfile(file_path):
                        # Get file info
                        stat = os.stat(file_path)

                        artifacts.append({
                            "id": artifact_id,
                            "filename": filename,
                            "size": stat.st_size,
                            "created_at": stat.st_ctime,
                            "download_url": f"/api/artifacts/{artifact_id}/download"
                        })

        return {"artifacts": artifacts}

    except Exception as e:
        logger.error(f"Error listing artifacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list artifacts")

@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Download an artifact file."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Find the artifact file
        output_dir = artifact_service.output_dir
        artifact_file = None

        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if filename.startswith(artifact_id):
                    artifact_file = os.path.join(output_dir, filename)
                    break

        if not artifact_file or not os.path.exists(artifact_file):
            raise HTTPException(status_code=404, detail="Artifact not found")

        # Return file
        filename = os.path.basename(artifact_file)
        return FileResponse(
            path=artifact_file,
            filename=filename,
            media_type='application/octet-stream'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading artifact {artifact_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download artifact")

@router.delete("/{artifact_id}")
async def delete_artifact(
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete an artifact."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Find the artifact file
        output_dir = artifact_service.output_dir
        artifact_file = None

        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                if filename.startswith(artifact_id):
                    # Verify user has access
                    if f"user_{current_user.id}_" in filename or f"_{current_user.id}_" in filename:
                        artifact_file = os.path.join(output_dir, filename)
                        break

        if not artifact_file:
            raise HTTPException(status_code=404, detail="Artifact not found")

        # Delete the file
        success = artifact_service.delete_artifact(artifact_file)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete artifact")

        return {"message": "Artifact deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting artifact {artifact_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete artifact")

# Convenience endpoints for common artifact types

@router.post("/summary", response_model=ArtifactResponse)
async def generate_summary(
    title: Optional[str] = None,
    format: str = "md",
    summary_text: str = "",
    key_points: List[str] = [],
    character_name: Optional[str] = None,
    source_documents: Optional[List[str]] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Generate a summary artifact."""
    content = {
        "summary_text": summary_text,
        "key_points": key_points,
        "character_name": character_name
    }

    request_obj = GenerateArtifactRequest(
        artifact_type="summary",
        format=format,
        title=title or "Summary",
        content=content,
        source_documents=source_documents
    )

    return await generate_artifact(request_obj, request, db)

class ConversationExportRequest(BaseModel):
    session_id: str
    format: str = "md"
    title: Optional[str] = None

@router.post("/conversation-export", response_model=ArtifactResponse)
async def export_conversation(
    request_data: ConversationExportRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Export a conversation as an artifact."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Get conversation data from database
        from ..core.conversation_service import conversation_service

        try:
            # Get session info
            session = conversation_service.get_session(request_data.session_id, db)
            if not session or str(session.get("user_id")) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Access denied")

            # Get conversation history
            history = conversation_service.get_conversation_history(request_data.session_id, limit=100, db=db)

            # Format messages
            messages = []
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp", "")
                })

            content = {
                "messages": messages,
                "character_name": "AI Assistant",
                "date_range": f"{session.get('started_at', '')} - {session.get('ended_at', 'ongoing')}"
            }

            request_obj = GenerateArtifactRequest(
                artifact_type="conversation_export",
                format=request_data.format,
                title=request_data.title or f"Conversation Export - {session.get('started_at', 'Unknown')}",
                content=content,
                session_id=request_data.session_id
            )

            return await generate_artifact(request_obj, request, db)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving conversation {request_data.session_id}: {str(e)}")
            raise HTTPException(status_code=404, detail="Conversation not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export conversation")

class DocumentAnalysisRequest(BaseModel):
    session_id: str
    format: str = "md"
    title: Optional[str] = None

@router.post("/document-analysis", response_model=ArtifactResponse)
async def generate_document_analysis(
    request_data: DocumentAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Generate a document analysis artifact based on uploaded documents and conversation context."""
    try:
        # Get current user
        current_user = await get_current_user_from_session(request, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Get conversation data and enhanced context for intelligent analysis
        from ..core.conversation_service import conversation_service
        from ..core.enhanced_context_service import enhanced_context_service

        try:
            # Get session info
            session = conversation_service.get_session(request_data.session_id, db)
            if not session or str(session.get("user_id")) != str(current_user.id):
                raise HTTPException(status_code=403, detail="Access denied")

            # Get conversation history to understand what documents are being referenced
            history = conversation_service.get_conversation_history(request_data.session_id, limit=20, db=db)

            # Extract the most recent user message to understand the analysis request
            latest_user_message = None
            for msg in reversed(history):
                if msg.get("role") == "user":
                    latest_user_message = msg.get("content")
                    break

            if not latest_user_message:
                latest_user_message = "Analyze and summarize the uploaded documents"

            # Use Enhanced Context Service for intelligent analysis
            enhanced_context = enhanced_context_service.get_enhanced_context(
                user_message=latest_user_message,
                user_id=current_user.id,
                conversation_id=request_data.session_id,
                character_id=session.get("character_id"),
                include_conversation_history=True,
                include_documents=True,
                comprehensive_analysis=True,
                enable_reasoning=True,
                db=db
            )

            # Extract document content and metadata from enhanced context
            document_chunks = enhanced_context.get('document_chunks', [])
            sources = enhanced_context.get('sources', [])
            reasoning_chain = enhanced_context.get('reasoning_chain', [])
            conflicts_detected = enhanced_context.get('conflicts_detected', [])

            if not document_chunks:
                raise HTTPException(
                    status_code=400,
                    detail="No documents uploaded. Please upload documents first using the document upload feature, or use 'Export Conversation' to save your chat instead."
                )

            # Generate the actual analysis content using Enhanced Context Service
            document_names = [source.get('filename', 'Unknown') for source in sources]

            # Use Enhanced Context Service to format the complete prompt with all context
            from ..core.llm_client import llm_client
            from ..core.character_manager import character_manager

            # Get the character's model configuration to use the same LLM as the persona
            try:
                character = character_manager.get_character(session.character_id)
                model_config = character.get('model_config') if character else None

                if not model_config:
                    # Fallback to default ollama config
                    model_config = {"provider": "ollama", "model": "llama3.1:8b", "temperature": 0.7, "max_tokens": 2048}

                logger.info(f"Using character's model config for enhanced document analysis: {model_config}")
            except Exception as e:
                logger.warning(f"Could not get character model config, using default: {e}")
                model_config = {"provider": "ollama", "model": "llama3.1:8b", "temperature": 0.7, "max_tokens": 2048}

            # Detect document types for specialized analysis
            document_types = []
            excel_files = []
            for source in sources:
                filename = source.get('filename', '').lower()
                if filename.endswith(('.xlsx', '.xls', '.csv')):
                    document_types.append('data')
                    excel_files.append(source.get('filename', ''))
                elif filename.endswith('.pdf'):
                    document_types.append('text')
                else:
                    document_types.append('text')

            # Create specialized prompt based on document types
            if 'data' in document_types and len(excel_files) > 0:
                # Specialized Excel/Data Analysis Prompt
                character_instructions = f"""You are an expert data analyst specializing in business intelligence and data insights.
You're analyzing data from: {', '.join(excel_files)}

The user asked: "{latest_user_message}"

## Your Analysis Mission:
Provide **actionable business insights** from the data, not just descriptions.

## Focus On:
• **Trends & Patterns**: What's increasing/decreasing over time?
• **Top Performers**: Which products/regions/reps are winning?
• **Key Metrics**: Total sales, average order size, growth rates
• **Opportunities**: Where can performance be improved?
• **Data Quality**: Any anomalies or data issues noticed?

## Response Format:
Keep responses **concise and structured**:

**📊 Key Insights**
• [Top 3 most important findings from the data]

**🏆 Performance Highlights**
• [Best performing products/regions/metrics]

**📈 Trends Observed**
• [Notable patterns or changes over time]

**💡 Recommendations**
• [Specific, actionable next steps]

**📋 Data Summary**
• [Brief overview of data scope and quality]

{("⚠️ **Data Conflicts Detected:** " + ", ".join([conflict.get('conflict_reason', 'Unknown') for conflict in conflicts_detected])) if conflicts_detected else ""}

Focus on **insights that drive business decisions**, not just data descriptions."""
            else:
                # Standard document analysis prompt
                character_instructions = f"""You are an expert document analyst working with a user who has specific questions and context.
Your goal is to provide intelligent, context-aware analysis that addresses their specific request.

## Analysis Requirements:
- Address the user's specific request: "{latest_user_message}"
- Analyze documents intelligently, not just summarize content
- Provide actionable insights and recommendations
- Format your response clearly and professionally

Please provide your analysis in a **structured, readable format**:

**📄 Document Overview**
[Brief context about what this document covers]

**🔍 Key Findings**
• [3-5 most important points that relate to the user's question]

**💡 Analysis & Insights**
[Your analysis of what this document means for the user's goals]

**📋 Recommendations**
[Specific recommendations or next steps]

{("⚠️ **Information Conflicts:** " + ", ".join([conflict.get('conflict_reason', 'Unknown') for conflict in conflicts_detected])) if conflicts_detected else ""}

Provide clear, actionable insights that go beyond simple summarization."""

            # Use Enhanced Context Service to create the complete prompt
            enhanced_prompt = enhanced_context_service.format_enhanced_prompt(
                user_message=latest_user_message,
                context=enhanced_context,
                character_instructions=character_instructions,
                show_reasoning=False  # Don't show reasoning in main prompt
            )

            # Generate the analysis using the LLM with enhanced context
            try:
                messages = [{"role": "user", "content": enhanced_prompt}]
                llm_analysis = llm_client.generate_response_with_config(
                    messages=messages,
                    system_prompt="",
                    model_config=model_config
                )
                logger.info("Successfully generated enhanced LLM analysis using full context")
            except Exception as e:
                logger.error(f"Error generating enhanced LLM analysis: {str(e)}")
                # Fallback to basic analysis
                context_summary = enhanced_context.get('context_summary', 'No context available')
                llm_analysis = f"""## Document Analysis

**Documents:** {', '.join(document_names)}
**User Request:** {latest_user_message}

## Context Summary
{context_summary}

## Analysis Notes
The enhanced analysis system is temporarily unavailable. Please try again later.

*Note: Analysis generated using fallback method.*"""

            # Create comprehensive content with reasoning chain
            reasoning_summary = ""
            if reasoning_chain:
                reasoning_steps = [f"- **{step['step'].title()}**: {step['thought']}" for step in reasoning_chain]
                reasoning_summary = "## AI Reasoning Process\n\n" + "\n".join(reasoning_steps) + "\n\n"

            content = {
                "document_name": ", ".join(document_names) if document_names else "Uploaded Documents",
                "analysis": llm_analysis,
                "key_insights": [
                    f"Enhanced analysis with conversation context",
                    f"Document contains {len(document_chunks)} sections",
                    f"Analysis addresses user request: {latest_user_message[:100]}...",
                    f"Source files: {', '.join(document_names)}",
                    f"Conflicts detected: {len(conflicts_detected)}" if conflicts_detected else "No conflicts detected"
                ],
                "document_summary": f"Document analysis based on conversation context and user request: '{latest_user_message}'\n\nProcessed {len(document_chunks)} document sections containing {sum(len(chunk.get('text_content', '').split()) for chunk in document_chunks)} words.",  # Clean summary without duplicating analysis
                "reasoning_chain": reasoning_summary if reasoning_summary else None,  # Optional thinking process
                "topics": [ref.get('extracted_name', '') for ref in enhanced_context.get('document_references', [])],
                "word_count": sum(len(chunk.get('text_content', '').split()) for chunk in document_chunks),
                "character_name": session.character_id
            }

            request_obj = GenerateArtifactRequest(
                artifact_type="document_analysis",
                format=request_data.format,
                title=request_data.title or f"Document Analysis - {session.started_at}",
                content=content,
                session_id=request_data.session_id,
                source_documents=[source.get('filename', '') for source in sources]
            )

            return await generate_artifact(request_obj, request, db)

        except Exception as e:
            logger.error(f"Error retrieving documents for analysis {request_data.session_id}: {str(e)}")
            raise HTTPException(status_code=404, detail="Documents or conversation not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating document analysis: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate document analysis")