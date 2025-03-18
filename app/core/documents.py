"""
Document Management System
Handles document uploading, processing, and retrieval for RAG applications
"""
import os
import json
import uuid
import sqlite3
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
import hashlib

# File type handlers
try:
    import fitz  # PyMuPDF for PDF handling
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from app.memory.vector import add_memory, query_memories
from app.memory.sql import _db_conn

ALLOWED_EXTENSIONS = {
    'txt': 'text/plain',
    'md': 'text/markdown', 
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

def init_document_db():
    """Initialize document database tables"""
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        # Documents table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                file_type TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                metadata TEXT    -- JSON metadata including summary
            )
        """)
        
        # Character-document association table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS character_documents (
                character_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,  -- Whether actively used in RAG
                last_accessed TEXT,
                PRIMARY KEY (character_id, document_id),
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

def allowed_file(filename):
    """Check if a filename has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path, file_type):
    """Extract text content from various file types"""
    if file_type == 'text/plain' or file_type == 'text/markdown':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    elif file_type == 'application/pdf' and PDF_SUPPORT:
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    
    # Add handlers for other document types as needed
    return None  # Unsupported file type

def save_uploaded_file(file, upload_dir):
    """Save an uploaded file to disk and return the file path"""
    filename = secure_filename(file.filename)
    # Create a unique filename to avoid collisions
    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Ensure upload directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save the file
    file.save(file_path)
    return file_path, unique_filename

def process_document(file, upload_dir=None):
    """
    Process an uploaded document
    
    Args:
        file: The uploaded file object
        upload_dir: Directory to save the file (defaults to app config)
        
    Returns:
        Tuple of (success, document_id or error_message)
    """
    if not allowed_file(file.filename):
        return False, "File type not supported"
    
    if upload_dir is None:
        upload_dir = os.path.join(current_app.instance_path, 'uploads')
    
    # Save file to disk
    file_path, unique_filename = save_uploaded_file(file, upload_dir)
    
    # Determine file type
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    file_type = ALLOWED_EXTENSIONS.get(file_extension)
    
    # Extract text
    text_content = extract_text_from_file(file_path, file_type)
    if text_content is None:
        os.remove(file_path)  # Clean up the file
        return False, "Could not extract text from file"
    
    # Create document record
    document_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Generate basic metadata
    metadata = {
        'filename': file.filename,
        'file_size': os.path.getsize(file_path),
        'stored_path': file_path,
        'extraction_date': timestamp,
    }
    
    # Store in database
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        conn.execute(
            """
            INSERT INTO documents (id, name, content, file_type, upload_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (document_id, file.filename, text_content, file_type, timestamp, json.dumps(metadata))
        )
    
    return True, document_id

def assign_document_to_character(document_id, character_id):
    """Assign a document to a character for use in RAG"""
    timestamp = datetime.now().isoformat()
    
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        try:
            conn.execute(
                """
                INSERT INTO character_documents (character_id, document_id, is_active, last_accessed)
                VALUES (?, ?, 1, ?)
                """,
                (character_id, document_id, timestamp)
            )
            return True
        except sqlite3.IntegrityError:
            # Update if already exists
            conn.execute(
                """
                UPDATE character_documents
                SET is_active = 1, last_accessed = ?
                WHERE character_id = ? AND document_id = ?
                """,
                (timestamp, character_id, document_id)
            )
            return True
        except Exception as e:
            current_app.logger.error(f"Error assigning document: {e}")
            return False

def get_character_documents(character_id):
    """Get all documents associated with a character"""
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        cursor = conn.execute(
            """
            SELECT d.id, d.name, d.file_type, d.upload_date, cd.is_active, cd.last_accessed
            FROM documents d
            JOIN character_documents cd ON d.id = cd.document_id
            WHERE cd.character_id = ?
            ORDER BY cd.is_active DESC, cd.last_accessed DESC
            """,
            (character_id,)
        )
        
        documents = []
        for row in cursor:
            documents.append({
                'id': row[0],
                'name': row[1],
                'file_type': row[2],
                'upload_date': row[3],
                'is_active': bool(row[4]),
                'last_accessed': row[5]
            })
        
        return documents

def get_document_by_id(document_id):
    """Retrieve a document by its ID"""
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        cursor = conn.execute(
            """
            SELECT id, name, content, file_type, upload_date, metadata
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
            
        return {
            'id': row[0],
            'name': row[1],
            'content': row[2],
            'file_type': row[3],
            'upload_date': row[4],
            'metadata': json.loads(row[5]) if row[5] else {}
        }

def update_document_access(document_id, character_id):
    """Update the last accessed timestamp for a document"""
    timestamp = datetime.now().isoformat()
    
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        conn.execute(
            """
            UPDATE character_documents
            SET last_accessed = ?
            WHERE character_id = ? AND document_id = ?
            """,
            (timestamp, character_id, document_id)
        )

def toggle_document_active_status(document_id, character_id, is_active):
    """Toggle whether a document is active for a character's RAG"""
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        conn.execute(
            """
            UPDATE character_documents
            SET is_active = ?
            WHERE character_id = ? AND document_id = ?
            """,
            (1 if is_active else 0, character_id, document_id)
        )
        return True

def unassign_document(document_id, character_id):
    """Remove a document from a character's collection"""
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        conn.execute(
            """
            DELETE FROM character_documents
            WHERE character_id = ? AND document_id = ?
            """,
            (character_id, document_id)
        )
        return True

def delete_document(document_id):
    """Delete a document and remove all character associations"""
    # First get the document to find the file path
    document = get_document_by_id(document_id)
    if not document:
        return False
    
    # Delete from database
    with _db_conn(current_app.config['DATABASE_PATH']) as conn:
        # Delete associations first (should cascade, but being explicit)
        conn.execute("DELETE FROM character_documents WHERE document_id = ?", (document_id,))
        # Delete the document
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    
    # Delete physical file if path is in metadata
    if document.get('metadata') and 'stored_path' in document['metadata']:
        file_path = document['metadata']['stored_path']
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                current_app.logger.error(f"Error deleting file {file_path}: {e}")
    
    return True

def index_document_for_rag(document_id, character_id=None):
    """
    Index a document for RAG by adding its content to vector store
    
    Args:
        document_id: ID of the document to index
        character_id: Optional character ID to associate with
    
    Returns:
        Boolean indicating success
    """
    document = get_document_by_id(document_id)
    if not document:
        return False
    
    # Split content into chunks 
    chunks = chunk_document(document['content'])
    
    # Store metadata about the document
    doc_metadata = {
        'source': 'document',
        'document_id': document_id,
        'document_name': document['name'],
    }
    
    # Add character if specified
    if character_id:
        doc_metadata['character_id'] = character_id
    
    # Add each chunk to vector store
    for i, chunk in enumerate(chunks):
        chunk_metadata = doc_metadata.copy()
        chunk_metadata['chunk_index'] = i
        
        # Add to vector store
        add_memory(
            character_id if character_id else 'global',
            chunk,
            chunk_metadata
        )
    
    return True

def chunk_document(text, chunk_size=1000, overlap=200):
    """
    Split document into overlapping chunks
    
    Args:
        text: Document text
        chunk_size: Max characters per chunk
        overlap: Character overlap between chunks
    
    Returns:
        List of text chunks
    """
    chunks = []
    
    # Simple character-based chunking
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Try to find a good break point (period followed by space or newline)
        if end < len(text):
            # Look for the last sentence break within the last 20% of the chunk
            search_start = max(start + int(chunk_size * 0.8), start)
            last_period = text.rfind('. ', search_start, end)
            last_newline = text.rfind('\n', search_start, end)
            
            break_point = max(last_period + 1, last_newline + 1)
            
            if break_point > search_start:
                end = break_point
        
        chunks.append(text[start:end])
        
        # Start the next chunk with overlap
        start = end - overlap if end - overlap > start else start + 1
    
    return chunks 