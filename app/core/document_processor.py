"""
Document Processor Module

This module handles document uploads, text extraction, and processing for various file types.
It supports PDF, text, markdown, and other document formats.
"""

import os
import json
import uuid
import datetime
import logging
from typing import Dict, List, Optional, Union, BinaryIO

# Configure logging
logger = logging.getLogger(__name__)

# Try to import PDF processing libraries
try:
    import fitz  # PyMuPDF
    HAVE_PYMUPDF = True
except ImportError:
    HAVE_PYMUPDF = False
    logger.warning("PyMuPDF not available. PDF processing will be limited.")

# Try to import markdown
try:
    import markdown
    HAVE_MARKDOWN = True
except ImportError:
    HAVE_MARKDOWN = False
    logger.warning("Markdown library not available. Markdown processing will be limited.")

# Try to import docx
try:
    import docx
    HAVE_DOCX = True
    logger.info("python-docx library is available for DOCX processing")
except ImportError:
    HAVE_DOCX = False
    logger.warning("python-docx not available. DOCX processing will be limited.")

# Document storage path
DOCUMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "documents")

# Ensure documents directory exists
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
logger.info(f"Document storage directory: {DOCUMENTS_DIR}")

def get_document_path(doc_id: str) -> str:
    """Get the file path for a document."""
    return os.path.join(DOCUMENTS_DIR, doc_id)

def process_uploaded_document(file_obj: BinaryIO, filename: str, character_id: str) -> Dict:
    """
    Process an uploaded document and extract its text.
    
    Args:
        file_obj: File-like object containing the document data
        filename: Original filename
        character_id: ID of the character to associate with the document
        
    Returns:
        Dictionary with document details
    """
    # Generate a unique ID for the document
    doc_id = str(uuid.uuid4())
    
    # Determine file extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    logger.info(f"Processing document: {filename}, extension: {ext}, id: {doc_id}")
    
    # Save the original file
    file_path = get_document_path(f"{doc_id}{ext}")
    with open(file_path, 'wb') as f:
        f.write(file_obj.read())
    
    logger.info(f"Saved document to: {file_path}")
    
    # Extract text based on file type
    extracted_text = ""
    doc_type = "unknown"
    
    if ext == '.pdf' and HAVE_PYMUPDF:
        logger.info("Processing PDF document")
        extracted_text = extract_text_from_pdf(file_path)
        doc_type = "pdf"
    elif ext == '.txt':
        logger.info("Processing TXT document")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            extracted_text = f.read()
        doc_type = "text"
    elif ext in ['.md', '.markdown'] and HAVE_MARKDOWN:
        logger.info("Processing Markdown document")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            md_text = f.read()
            extracted_text = md_text  # Store original markdown
        doc_type = "markdown"
    elif ext in ['.docx', '.doc'] and HAVE_DOCX:
        logger.info("Processing DOCX document")
        extracted_text = extract_text_from_docx(file_path)
        doc_type = "docx"
    else:
        logger.warning(f"Unsupported document format: {ext}")
        # For unsupported formats, just store metadata
        extracted_text = f"Unsupported document format: {ext}"
        doc_type = "unsupported"
    
    logger.info(f"Extracted {len(extracted_text)} characters from document")
    
    # Create document metadata
    document = {
        "id": doc_id,
        "filename": filename,
        "character_id": character_id,
        "file_path": file_path,
        "doc_type": doc_type,
        "text_content": extracted_text,
        "upload_date": datetime.datetime.now().isoformat(),
        "file_size": os.path.getsize(file_path)
    }
    
    # Save metadata
    metadata_path = get_document_path(f"{doc_id}.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(document, f, indent=2)
    
    logger.info(f"Document metadata saved to: {metadata_path}")
    return document

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text
    """
    if not HAVE_PYMUPDF:
        return "PDF text extraction requires PyMuPDF library."
    
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return f"Error extracting text: {str(e)}"

def extract_text_from_docx(docx_path: str) -> str:
    """
    Extract text from a DOCX file.
    
    Args:
        docx_path: Path to the DOCX file
        
    Returns:
        Extracted text
    """
    if not HAVE_DOCX:
        logger.error("Attempted to process DOCX but python-docx is not available")
        return "DOCX text extraction requires python-docx library."
    
    try:
        logger.info(f"Opening DOCX file: {docx_path}")
        doc = docx.Document(docx_path)
        full_text = []
        
        # Extract text from paragraphs
        logger.info(f"Extracting text from {len(doc.paragraphs)} paragraphs")
        for para in doc.paragraphs:
            full_text.append(para.text)
        
        # Extract text from tables
        logger.info(f"Extracting text from {len(doc.tables)} tables")
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text.append(cell.text)
        
        # Join all text with newlines
        result = '\n'.join(full_text)
        logger.info(f"Successfully extracted {len(result)} characters from DOCX")
        return result
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error extracting text: {str(e)}"

def get_document_by_id(doc_id: str) -> Optional[Dict]:
    """
    Get document details by ID.
    
    Args:
        doc_id: Document ID
        
    Returns:
        Document details or None if not found
    """
    metadata_path = get_document_path(f"{doc_id}.json")
    if not os.path.exists(metadata_path):
        return None
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading document metadata: {e}")
        return None

def get_character_documents(character_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    """
    Get all documents for a character.
    
    Args:
        character_id: Character ID
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        
    Returns:
        List of document metadata
    """
    documents = []
    
    if not os.path.exists(DOCUMENTS_DIR):
        return documents
    
    for filename in os.listdir(DOCUMENTS_DIR):
        if not filename.endswith('.json'):
            continue
        
        file_path = os.path.join(DOCUMENTS_DIR, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                doc = json.load(f)
                if doc.get('character_id') == character_id:
                    # Don't include the full text content in the listing
                    if 'text_content' in doc:
                        doc['text_content'] = f"[{len(doc['text_content'])} characters]"
                    documents.append(doc)
        except (json.JSONDecodeError, IOError):
            continue
    
    # Sort by upload date (newest first)
    documents.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
    
    # Apply pagination
    return documents[offset:offset+limit]

def delete_document(doc_id: str) -> bool:
    """
    Delete a document and its metadata.
    
    Args:
        doc_id: Document ID
        
    Returns:
        True if document was deleted, False otherwise
    """
    metadata_path = get_document_path(f"{doc_id}.json")
    if not os.path.exists(metadata_path):
        return False
    
    try:
        # Get document metadata to find the original file
        with open(metadata_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        
        # Delete the original file if it exists
        if 'file_path' in doc and os.path.exists(doc['file_path']):
            os.remove(doc['file_path'])
        
        # Delete the metadata file
        os.remove(metadata_path)
        return True
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return False

def create_document_summary(doc_id: str, character_id: str) -> str:
    """
    Create a summary of a document.
    
    Args:
        doc_id: Document ID
        character_id: Character ID (optional)
        
    Returns:
        Summary text or None if document not found
    """
    document = get_document_by_id(doc_id)
    if not document:
        return None
    
    # Create a simple summary
    text_content = document.get('text_content', '')
    filename = document.get('filename', 'document')
            
    # Create a basic summary text
    summary = f"# Summary of {filename}\n\n"
    summary += f"**Document Type:** {document.get('doc_type', 'unknown').upper()}\n"
    summary += f"**Size:** {document.get('file_size', 0)} bytes\n"
    summary += f"**Uploaded:** {document.get('upload_date')}\n\n"
    summary += "## Content Summary\n\n"
    
    # Add a simple excerpt
    if len(text_content) > 500:
        summary += f"{text_content[:500]}...\n\n(Document contains {len(text_content)} characters total)"
    else:
        summary += text_content
    
    return summary

def extract_document_to_memory(doc_id: str, character_id: str) -> bool:
    """
    Extract document content to character memory.
    
    Args:
        doc_id: Document ID
        character_id: Character ID
        
    Returns:
        True if successful, False otherwise
    """
    document = get_document_by_id(doc_id)
    if not document:
        logger.error(f"Document {doc_id} not found for extraction to memory")
        return False
    
    # Get document content
    text_content = document.get('text_content', '')
    filename = document.get('filename', 'document')
    
    if not text_content:
        logger.warning(f"Document {doc_id} has no text content to extract")
        return False
        
    logger.info(f"Extracting document {filename} ({len(text_content)} chars) to memory for character {character_id}")
    
    try:
        # Direct database access for conversation storage
        import sqlite3
        from datetime import datetime
        
        # Use the correct database path from Flask app configuration (hardcoded for reliability)
        db_path = "/app/instance/memories.db"
        logger.info(f"Using database at {db_path}")
        
        # Split content into chunks if it's too large
        chunk_size = 1000
        if len(text_content) > chunk_size:
            chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
        else:
            chunks = [text_content]
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
            
        # Save each chunk directly to database
        for i, chunk in enumerate(chunks):
            chunk_label = f" (part {i+1}/{len(chunks)})" if len(chunks) > 1 else ""
            
            # Format as conversations - using the correct column names (role instead of speaker, content instead of message)
            user_message = f"Please remember this content from {filename}{chunk_label}"
            ai_response = chunk
            
            # Insert user message
            logger.info(f"Inserting user message ({len(user_message)} chars)")
            cursor.execute(
                "INSERT INTO conversations (character_id, role, content) VALUES (?, ?, ?)",
                (character_id, "user", user_message)
            )
            
            # Insert AI response
            logger.info(f"Inserting AI message ({len(ai_response)} chars)")
            cursor.execute(
                "INSERT INTO conversations (character_id, role, content) VALUES (?, ?, ?)",
                (character_id, "assistant", ai_response)
            )
            
            logger.info(f"Saved chunk {i+1}/{len(chunks)} to database for character {character_id}")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        logger.info("Successfully extracted document to memory")
        return True
    except Exception as e:
        logger.error(f"Error extracting document to memory: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False 