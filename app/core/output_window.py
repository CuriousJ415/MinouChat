"""
Output Window Core Module

This module provides functionality for managing output documents and formatted content.
It handles document creation, updating, retrieval, and summarization.
"""

import os
import json
import uuid
import datetime
from typing import Dict, List, Optional, Union

# Database path
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output_documents")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_document_path(doc_id: str) -> str:
    """Get the file path for a document."""
    return os.path.join(OUTPUT_DIR, f"{doc_id}.json")

def create_document(character_id: str, title: str, content: str, doc_type: str = "note") -> Dict:
    """
    Create a new output document.
    
    Args:
        character_id: ID of the character associated with the document
        title: Document title
        content: Document content (markdown formatted)
        doc_type: Document type (note, summary, etc.)
        
    Returns:
        Dict containing the document details
    """
    doc_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    document = {
        "id": doc_id,
        "character_id": character_id,
        "title": title,
        "content": content,
        "type": doc_type,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    with open(get_document_path(doc_id), 'w') as f:
        json.dump(document, f, indent=2)
    
    return document

def get_document(doc_id: str) -> Optional[Dict]:
    """
    Retrieve a document by ID.
    
    Args:
        doc_id: Document ID
        
    Returns:
        Document dict or None if not found
    """
    doc_path = get_document_path(doc_id)
    if not os.path.exists(doc_path):
        return None
    
    with open(doc_path, 'r') as f:
        return json.load(f)

def update_document(doc_id: str, updates: Dict) -> Optional[Dict]:
    """
    Update an existing document.
    
    Args:
        doc_id: Document ID
        updates: Dict containing fields to update
        
    Returns:
        Updated document or None if document not found
    """
    document = get_document(doc_id)
    if not document:
        return None
    
    # Update allowed fields
    allowed_updates = ['title', 'content']
    for field in allowed_updates:
        if field in updates:
            document[field] = updates[field]
    
    document["updated_at"] = datetime.datetime.now().isoformat()
    
    with open(get_document_path(doc_id), 'w') as f:
        json.dump(document, f, indent=2)
    
    return document

def append_to_document(doc_id: str, content: str) -> Optional[Dict]:
    """
    Append content to an existing document.
    
    Args:
        doc_id: Document ID
        content: Content to append
        
    Returns:
        Updated document or None if document not found
    """
    document = get_document(doc_id)
    if not document:
        return None
    
    document["content"] = document["content"] + "\n\n" + content
    document["updated_at"] = datetime.datetime.now().isoformat()
    
    with open(get_document_path(doc_id), 'w') as f:
        json.dump(document, f, indent=2)
    
    return document

def delete_document(doc_id: str) -> bool:
    """
    Delete a document.
    
    Args:
        doc_id: Document ID
        
    Returns:
        True if document was deleted, False otherwise
    """
    doc_path = get_document_path(doc_id)
    if not os.path.exists(doc_path):
        return False
    
    os.remove(doc_path)
    return True

def get_character_documents(character_id: str, limit: int = 20, offset: int = 0) -> List[Dict]:
    """
    Get all documents for a character.
    
    Args:
        character_id: Character ID
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        
    Returns:
        List of document dicts
    """
    documents = []
    
    if not os.path.exists(OUTPUT_DIR):
        return documents
    
    for filename in os.listdir(OUTPUT_DIR):
        if not filename.endswith('.json'):
            continue
        
        file_path = os.path.join(OUTPUT_DIR, filename)
        try:
            with open(file_path, 'r') as f:
                doc = json.load(f)
                if doc.get('character_id') == character_id:
                    documents.append(doc)
        except (json.JSONDecodeError, IOError):
            continue
    
    # Sort by updated_at (newest first)
    documents.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    
    # Apply pagination
    return documents[offset:offset+limit]

def summarize_document(character_id: str, source_doc_id: str, title: str = None) -> Optional[Dict]:
    """
    Create a summary document from a source document.
    
    Args:
        character_id: Character ID
        source_doc_id: Source document ID
        title: Optional title for the summary (defaults to "Summary of [original title]")
        
    Returns:
        Summary document or None if source document not found
    """
    source_doc = get_document(source_doc_id)
    if not source_doc:
        return None
    
    if not title:
        title = f"Summary of {source_doc['title']}"
    
    # In a real implementation, we would use an LLM to generate the summary
    # For now, we'll just create a placeholder summary
    summary_content = f"# Summary of {source_doc['title']}\n\nThis is a placeholder summary of the document."
    
    return create_document(
        character_id=character_id,
        title=title,
        content=summary_content,
        doc_type="summary"
    ) 