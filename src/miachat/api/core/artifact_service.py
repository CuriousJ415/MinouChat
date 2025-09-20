"""
Artifact Generation Service for MiaChat

This service handles the creation of various document artifacts including:
- Reports and summaries
- Data tables and analysis
- Professional documents
- Export to multiple formats (MD, TXT, PDF, CSV)
"""

import os
import csv
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

# PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("ReportLab not available. PDF generation will be disabled.")

logger = logging.getLogger(__name__)

class ArtifactType(Enum):
    """Types of artifacts that can be generated."""
    SUMMARY = "summary"
    REPORT = "report"
    ANALYSIS = "analysis"
    DATA_TABLE = "data_table"
    CONVERSATION_EXPORT = "conversation_export"
    DOCUMENT_ANALYSIS = "document_analysis"

class ExportFormat(Enum):
    """Supported export formats."""
    MARKDOWN = "md"
    TEXT = "txt"
    PDF = "pdf"
    CSV = "csv"

@dataclass
class ArtifactMetadata:
    """Metadata for generated artifacts."""
    id: str
    title: str
    artifact_type: ArtifactType
    format: ExportFormat
    created_at: datetime
    user_id: int
    character_id: Optional[str] = None
    session_id: Optional[str] = None
    source_documents: List[str] = None
    file_path: str = None
    file_size: int = None

class ArtifactService:
    """Service for generating and managing document artifacts."""

    def __init__(self, output_dir: str = "./output_documents"):
        """Initialize the artifact service.

        Args:
            output_dir: Directory to store generated artifacts
        """
        self.output_dir = output_dir
        self.ensure_output_directory()

    def ensure_output_directory(self):
        """Ensure the output directory exists."""
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_artifact(
        self,
        artifact_type: ArtifactType,
        content: Dict[str, Any],
        format: ExportFormat,
        user_id: int,
        title: Optional[str] = None,
        character_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_documents: Optional[List[str]] = None
    ) -> ArtifactMetadata:
        """Generate an artifact with the specified content and format.

        Args:
            artifact_type: Type of artifact to generate
            content: Content data for the artifact
            format: Export format
            user_id: User ID for the artifact
            title: Optional title for the artifact
            character_id: Optional character ID associated with the artifact
            session_id: Optional session ID for conversation exports
            source_documents: Optional list of source document names

        Returns:
            ArtifactMetadata object with details about the generated artifact
        """
        try:
            # Generate unique ID and title
            artifact_id = str(uuid.uuid4())
            if not title:
                title = self._generate_default_title(artifact_type)

            # Create metadata
            metadata = ArtifactMetadata(
                id=artifact_id,
                title=title,
                artifact_type=artifact_type,
                format=format,
                created_at=datetime.utcnow(),
                user_id=user_id,
                character_id=character_id,
                session_id=session_id,
                source_documents=source_documents or []
            )

            # Generate the artifact content based on type
            if artifact_type == ArtifactType.SUMMARY:
                artifact_content = self._generate_summary(content, metadata)
            elif artifact_type == ArtifactType.REPORT:
                artifact_content = self._generate_report(content, metadata)
            elif artifact_type == ArtifactType.ANALYSIS:
                artifact_content = self._generate_analysis(content, metadata)
            elif artifact_type == ArtifactType.DATA_TABLE:
                artifact_content = self._generate_data_table(content, metadata)
            elif artifact_type == ArtifactType.CONVERSATION_EXPORT:
                artifact_content = self._generate_conversation_export(content, metadata)
            elif artifact_type == ArtifactType.DOCUMENT_ANALYSIS:
                artifact_content = self._generate_document_analysis(content, metadata)
            else:
                raise ValueError(f"Unsupported artifact type: {artifact_type}")

            # Export in the specified format
            file_path = self._export_artifact(artifact_content, metadata)

            # Update metadata with file information
            metadata.file_path = file_path
            metadata.file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

            logger.info(f"Generated artifact {artifact_id}: {title} ({format.value})")
            return metadata

        except Exception as e:
            logger.error(f"Error generating artifact: {str(e)}")
            raise

    def _generate_default_title(self, artifact_type: ArtifactType) -> str:
        """Generate a default title for an artifact."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        type_name = artifact_type.value.replace("_", " ").title()
        return f"{type_name} - {timestamp}"

    def _generate_summary(self, content: Dict[str, Any], metadata: ArtifactMetadata) -> Dict[str, Any]:
        """Generate a summary artifact."""
        return {
            "title": metadata.title,
            "type": "Summary",
            "created_at": metadata.created_at.isoformat(),
            "content": content.get("summary_text", ""),
            "key_points": content.get("key_points", []),
            "source_documents": metadata.source_documents,
            "character": content.get("character_name", "AI Assistant")
        }

    def _generate_report(self, content: Dict[str, Any], metadata: ArtifactMetadata) -> Dict[str, Any]:
        """Generate a report artifact."""
        return {
            "title": metadata.title,
            "type": "Report",
            "created_at": metadata.created_at.isoformat(),
            "executive_summary": content.get("executive_summary", ""),
            "sections": content.get("sections", []),
            "conclusions": content.get("conclusions", []),
            "recommendations": content.get("recommendations", []),
            "source_documents": metadata.source_documents,
            "character": content.get("character_name", "AI Assistant")
        }

    def _generate_analysis(self, content: Dict[str, Any], metadata: ArtifactMetadata) -> Dict[str, Any]:
        """Generate an analysis artifact."""
        return {
            "title": metadata.title,
            "type": "Analysis",
            "created_at": metadata.created_at.isoformat(),
            "analysis_text": content.get("analysis_text", ""),
            "findings": content.get("findings", []),
            "methodology": content.get("methodology", ""),
            "data_sources": content.get("data_sources", []),
            "source_documents": metadata.source_documents,
            "character": content.get("character_name", "AI Assistant")
        }

    def _generate_data_table(self, content: Dict[str, Any], metadata: ArtifactMetadata) -> Dict[str, Any]:
        """Generate a data table artifact."""
        return {
            "title": metadata.title,
            "type": "Data Table",
            "created_at": metadata.created_at.isoformat(),
            "description": content.get("description", ""),
            "headers": content.get("headers", []),
            "rows": content.get("rows", []),
            "summary_stats": content.get("summary_stats", {}),
            "source_documents": metadata.source_documents
        }

    def _generate_conversation_export(self, content: Dict[str, Any], metadata: ArtifactMetadata) -> Dict[str, Any]:
        """Generate a conversation export artifact."""
        return {
            "title": metadata.title,
            "type": "Conversation Export",
            "created_at": metadata.created_at.isoformat(),
            "session_id": metadata.session_id,
            "character": content.get("character_name", "AI Assistant"),
            "messages": content.get("messages", []),
            "message_count": len(content.get("messages", [])),
            "date_range": content.get("date_range", "")
        }

    def _generate_document_analysis(self, content: Dict[str, Any], metadata: ArtifactMetadata) -> Dict[str, Any]:
        """Generate a document analysis artifact."""
        return {
            "title": metadata.title,
            "type": "Document Analysis",
            "created_at": metadata.created_at.isoformat(),
            "document_name": content.get("document_name", ""),
            "analysis": content.get("analysis", ""),
            "key_insights": content.get("key_insights", []),
            "document_summary": content.get("document_summary", ""),
            "topics": content.get("topics", []),
            "word_count": content.get("word_count", 0),
            "source_documents": metadata.source_documents,
            "character": content.get("character_name", "AI Assistant")
        }

    def _export_artifact(self, artifact_content: Dict[str, Any], metadata: ArtifactMetadata) -> str:
        """Export artifact content to the specified format."""
        # Generate safe filename
        safe_title = "".join(c for c in metadata.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        filename = f"{metadata.id}_{safe_title}.{metadata.format.value}"
        file_path = os.path.join(self.output_dir, filename)

        if metadata.format == ExportFormat.MARKDOWN:
            self._export_markdown(artifact_content, file_path)
        elif metadata.format == ExportFormat.TEXT:
            self._export_text(artifact_content, file_path)
        elif metadata.format == ExportFormat.PDF:
            self._export_pdf(artifact_content, file_path)
        elif metadata.format == ExportFormat.CSV:
            self._export_csv(artifact_content, file_path)
        else:
            raise ValueError(f"Unsupported export format: {metadata.format}")

        return file_path

    def _export_markdown(self, content: Dict[str, Any], file_path: str):
        """Export content as Markdown."""
        with open(file_path, 'w', encoding='utf-8') as f:
            # Title
            f.write(f"# {content['title']}\n\n")

            # Metadata
            f.write(f"**Type:** {content['type']}  \n")
            f.write(f"**Created:** {content['created_at']}  \n")
            if content.get('character'):
                f.write(f"**Generated by:** {content['character']}  \n")
            f.write("\n")

            # Content based on type
            if content['type'] == 'Summary':
                if content.get('content'):
                    f.write(f"## Summary\n\n{content['content']}\n\n")
                if content.get('key_points'):
                    f.write("## Key Points\n\n")
                    for point in content['key_points']:
                        f.write(f"- {point}\n")
                    f.write("\n")

            elif content['type'] == 'Report':
                if content.get('executive_summary'):
                    f.write(f"## Executive Summary\n\n{content['executive_summary']}\n\n")
                if content.get('sections'):
                    for section in content['sections']:
                        f.write(f"## {section.get('title', 'Section')}\n\n")
                        f.write(f"{section.get('content', '')}\n\n")
                if content.get('conclusions'):
                    f.write("## Conclusions\n\n")
                    for conclusion in content['conclusions']:
                        f.write(f"- {conclusion}\n")
                    f.write("\n")
                if content.get('recommendations'):
                    f.write("## Recommendations\n\n")
                    for rec in content['recommendations']:
                        f.write(f"- {rec}\n")
                    f.write("\n")

            elif content['type'] == 'Analysis':
                if content.get('analysis_text'):
                    f.write(f"## Analysis\n\n{content['analysis_text']}\n\n")
                if content.get('findings'):
                    f.write("## Key Findings\n\n")
                    for finding in content['findings']:
                        f.write(f"- {finding}\n")
                    f.write("\n")
                if content.get('methodology'):
                    f.write(f"## Methodology\n\n{content['methodology']}\n\n")

            elif content['type'] == 'Data Table':
                if content.get('description'):
                    f.write(f"## Description\n\n{content['description']}\n\n")
                if content.get('headers') and content.get('rows'):
                    f.write("## Data\n\n")
                    # Create markdown table
                    headers = content['headers']
                    f.write("| " + " | ".join(headers) + " |\n")
                    f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
                    for row in content['rows']:
                        f.write("| " + " | ".join(str(cell) for cell in row) + " |\n")
                    f.write("\n")

            elif content['type'] == 'Conversation Export':
                f.write(f"**Session ID:** {content.get('session_id', 'N/A')}  \n")
                f.write(f"**Messages:** {content.get('message_count', 0)}  \n")
                if content.get('date_range'):
                    f.write(f"**Date Range:** {content['date_range']}  \n")
                f.write("\n")

                f.write("## Conversation\n\n")
                for message in content.get('messages', []):
                    role = message.get('role', 'unknown').title()
                    timestamp = message.get('timestamp', '')
                    text = message.get('content', '')
                    f.write(f"### {role} ({timestamp})\n\n{text}\n\n")

            elif content['type'] == 'Document Analysis':
                if content.get('document_name'):
                    f.write(f"**Document:** {content['document_name']}  \n")
                if content.get('word_count'):
                    f.write(f"**Word Count:** {content['word_count']}  \n")
                f.write("\n")

                if content.get('document_summary'):
                    f.write(f"## Summary\n\n{content['document_summary']}\n\n")
                if content.get('analysis'):
                    f.write(f"## Analysis\n\n{content['analysis']}\n\n")
                if content.get('reasoning_chain'):
                    f.write(f"{content['reasoning_chain']}")
                if content.get('key_insights'):
                    f.write("## Key Insights\n\n")
                    for insight in content['key_insights']:
                        f.write(f"- {insight}\n")
                    f.write("\n")
                if content.get('topics'):
                    f.write("## Topics\n\n")
                    for topic in content['topics']:
                        f.write(f"- {topic}\n")
                    f.write("\n")

            # Source documents
            if content.get('source_documents'):
                f.write("## Source Documents\n\n")
                for doc in content['source_documents']:
                    f.write(f"- {doc}\n")
                f.write("\n")

            # Footer
            f.write("---\n")
            f.write("*Generated by MiaChat Artifact System*\n")

    def _export_text(self, content: Dict[str, Any], file_path: str):
        """Export content as plain text."""
        with open(file_path, 'w', encoding='utf-8') as f:
            # Title
            f.write(f"{content['title']}\n")
            f.write("=" * len(content['title']) + "\n\n")

            # Metadata
            f.write(f"Type: {content['type']}\n")
            f.write(f"Created: {content['created_at']}\n")
            if content.get('character'):
                f.write(f"Generated by: {content['character']}\n")
            f.write("\n")

            # Content (simplified version of markdown logic)
            if content['type'] == 'Summary':
                if content.get('content'):
                    f.write(f"SUMMARY\n--------\n{content['content']}\n\n")
                if content.get('key_points'):
                    f.write("KEY POINTS\n----------\n")
                    for point in content['key_points']:
                        f.write(f"• {point}\n")
                    f.write("\n")

            elif content['type'] == 'Data Table':
                if content.get('description'):
                    f.write(f"DESCRIPTION\n-----------\n{content['description']}\n\n")
                if content.get('headers') and content.get('rows'):
                    f.write("DATA\n----\n")
                    headers = content['headers']
                    # Simple table formatting
                    f.write(" | ".join(headers) + "\n")
                    f.write("-" * (len(" | ".join(headers))) + "\n")
                    for row in content['rows']:
                        f.write(" | ".join(str(cell) for cell in row) + "\n")
                    f.write("\n")

            # Add other content types as needed...

            # Source documents
            if content.get('source_documents'):
                f.write("SOURCE DOCUMENTS\n----------------\n")
                for doc in content['source_documents']:
                    f.write(f"• {doc}\n")
                f.write("\n")

            f.write("\n---\nGenerated by MiaChat Artifact System\n")

    def _export_pdf(self, content: Dict[str, Any], file_path: str):
        """Export content as PDF."""
        if not PDF_AVAILABLE:
            raise ValueError("PDF export not available. Install reportlab: pip install reportlab")

        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.black
        )
        story.append(Paragraph(content['title'], title_style))
        story.append(Spacer(1, 12))

        # Metadata
        meta_text = f"<b>Type:</b> {content['type']}<br/>"
        meta_text += f"<b>Created:</b> {content['created_at']}<br/>"
        if content.get('character'):
            meta_text += f"<b>Generated by:</b> {content['character']}<br/>"
        story.append(Paragraph(meta_text, styles['Normal']))
        story.append(Spacer(1, 12))

        # Content based on type
        if content['type'] == 'Data Table' and content.get('headers') and content.get('rows'):
            # Create table
            table_data = [content['headers']] + content['rows']
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
        else:
            # Text content
            if content.get('content'):
                story.append(Paragraph(content['content'], styles['Normal']))
            elif content.get('analysis_text'):
                story.append(Paragraph(content['analysis_text'], styles['Normal']))
            elif content.get('analysis'):
                # Handle document analysis content
                story.append(Paragraph(content['analysis'], styles['Normal']))

        story.append(Spacer(1, 12))

        # Source documents
        if content.get('source_documents'):
            story.append(Paragraph("<b>Source Documents:</b>", styles['Heading3']))
            for doc in content['source_documents']:
                story.append(Paragraph(f"• {doc}", styles['Normal']))

        doc.build(story)

    def _export_csv(self, content: Dict[str, Any], file_path: str):
        """Export content as CSV (mainly for data tables)."""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            if content['type'] == 'Data Table' and content.get('headers') and content.get('rows'):
                writer = csv.writer(csvfile)
                writer.writerow(content['headers'])
                writer.writerows(content['rows'])
            else:
                # For non-table content, create a simple structure
                writer = csv.writer(csvfile)
                writer.writerow(['Field', 'Value'])
                writer.writerow(['Title', content['title']])
                writer.writerow(['Type', content['type']])
                writer.writerow(['Created', content['created_at']])
                if content.get('character'):
                    writer.writerow(['Generated by', content['character']])

                # Add content if available
                if content.get('content'):
                    writer.writerow(['Content', content['content']])
                elif content.get('analysis_text'):
                    writer.writerow(['Analysis', content['analysis_text']])

    def get_user_artifacts(self, user_id: int) -> List[str]:
        """Get list of artifacts for a specific user."""
        artifacts = []
        if not os.path.exists(self.output_dir):
            return artifacts

        for filename in os.listdir(self.output_dir):
            # Simple check - in a real implementation, you'd store metadata in a database
            if filename.startswith(str(user_id)) or f"_{user_id}_" in filename:
                artifacts.append(filename)

        return artifacts

    def delete_artifact(self, file_path: str) -> bool:
        """Delete an artifact file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted artifact: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting artifact {file_path}: {str(e)}")
            return False

# Global service instance
artifact_service = ArtifactService()