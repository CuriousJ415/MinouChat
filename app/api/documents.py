"""
Documents API

This module provides API endpoints for document management, including uploading,
retrieving, and processing documents.
"""

from flask import Blueprint, request, jsonify, current_app
import os
from werkzeug.utils import secure_filename
import json

# Import document processing functions
try:
    from app.core.document_processor import (
        process_uploaded_document,
        get_document_by_id,
        get_character_documents,
        delete_document,
        create_document_summary,
        extract_document_to_memory
    )
    HAVE_DOCUMENT_PROCESSOR = True
except ImportError:
    HAVE_DOCUMENT_PROCESSOR = False

# Create blueprint
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

def init_app(app):
    """Initialize document API routes"""
    # Register the blueprint directly
    app.register_blueprint(documents_bp)
    current_app.logger.info("Document API routes registered")
    return app

@documents_bp.route('/', methods=['GET'])
def list_documents():
    """List all documents"""
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    try:
        # Get all documents from all characters
        documents = []
        document_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "documents")
        
        if os.path.exists(document_dir):
            for filename in os.listdir(document_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(document_dir, filename), 'r') as f:
                            doc = json.load(f)
                            # Don't include full text content in listing
                            if 'text_content' in doc:
                                doc.pop('text_content')
                            documents.append(doc)
                    except Exception as e:
                        current_app.logger.error(f"Error reading document {filename}: {str(e)}")
        
        # Sort by upload date (newest first)
        documents.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
        
        return jsonify(documents)
    except Exception as e:
        current_app.logger.error(f"Error listing documents: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to list documents: {str(e)}"
        }), 500

@documents_bp.route('/', methods=['POST'])
def upload_document():
    """Upload a document"""
    if not HAVE_DOCUMENT_PROCESSOR:
        current_app.logger.error("Document processing is not available")
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    current_app.logger.info(f"Received document upload request: {request.files}")
    
    if 'file' not in request.files:
        current_app.logger.error("No file provided in request")
        return jsonify({
            "success": False,
            "error": "No file provided"
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        current_app.logger.error("Empty filename provided")
        return jsonify({
            "success": False,
            "error": "No file selected"
        }), 400
    
    # Get character ID if provided
    character_id = request.form.get('character_id', '')
    current_app.logger.info(f"Processing document upload: {file.filename} for character: {character_id}")
    
    # Process the uploaded document
    try:
        document = process_uploaded_document(
            file_obj=file,
            filename=secure_filename(file.filename),
            character_id=character_id
        )
        
        current_app.logger.info(f"Document processed successfully: {document['id']}, type: {document['doc_type']}")
        
        # Don't return the full text content
        if 'text_content' in document:
            document.pop('text_content')
        
        return jsonify(document)
    except Exception as e:
        current_app.logger.error(f"Error processing document: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Error processing document: {str(e)}"
        }), 500

@documents_bp.route('/upload/<character_id>', methods=['POST'])
def upload_document_for_character(character_id):
    """
    Upload a document for a character.
    
    Request:
        - file: The document file to upload
        
    Response:
        - JSON with document details or error message
    """
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    if 'file' not in request.files:
        return jsonify({
            "success": False,
            "error": "No file provided"
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "success": False,
            "error": "No file selected"
        }), 400
    
    # Process the uploaded document
    try:
        document = process_uploaded_document(
            file_obj=file,
            filename=secure_filename(file.filename),
            character_id=character_id
        )
        
        return jsonify({
            "success": True,
            "document": {
                "id": document["id"],
                "filename": document["filename"],
                "doc_type": document["doc_type"],
                "upload_date": document["upload_date"],
                "file_size": document["file_size"]
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error processing document: {e}")
        return jsonify({
            "success": False,
            "error": f"Error processing document: {str(e)}"
        }), 500

@documents_bp.route('/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """
    Get document details by ID.
    
    Response:
        - JSON with document details or error message
    """
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    document = get_document_by_id(doc_id)
    if not document:
        return jsonify({
            "success": False,
            "error": "Document not found"
        }), 404
    
    # Include the full text content
    return jsonify(document)

@documents_bp.route('/<doc_id>/content', methods=['GET'])
def get_document_content(doc_id):
    """
    Get the full text content of a document.
    
    Response:
        - JSON with document content or error message
    """
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    document = get_document_by_id(doc_id)
    if not document:
        return jsonify({
            "success": False,
            "error": "Document not found"
        }), 404
    
    return jsonify({
        "success": True,
        "document_id": doc_id,
        "filename": document.get("filename", ""),
        "content": document.get("text_content", "")
    })

@documents_bp.route('/character/<character_id>', methods=['GET'])
def list_character_documents(character_id):
    """
    List all documents for a character.
    
    Query parameters:
        - limit: Maximum number of documents to return (default: 20)
        - offset: Number of documents to skip (default: 0)
        
    Response:
        - JSON with list of documents or error message
    """
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    documents = get_character_documents(character_id, limit, offset)
    
    return jsonify({
        "success": True,
        "documents": documents,
        "count": len(documents),
        "limit": limit,
        "offset": offset
    })

@documents_bp.route('/<doc_id>', methods=['DELETE'])
def remove_document(doc_id):
    """
    Delete a document.
    
    Response:
        - JSON with success status or error message
    """
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    success = delete_document(doc_id)
    if not success:
        return jsonify({
            "success": False,
            "error": "Document not found or could not be deleted"
        }), 404
    
    return jsonify({
        "success": True,
        "message": "Document deleted successfully"
    })

@documents_bp.route('/summarize', methods=['POST'])
def summarize_document_post():
    """
    Create a summary of a document using POST with JSON body.
    
    Request:
        - document_id: ID of the document to summarize
        - character_id: (optional) ID of the character to associate with
        
    Response:
        - JSON with summary or error message
    """
    if not HAVE_DOCUMENT_PROCESSOR:
        current_app.logger.error("Document processing not available for summarize")
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    # Get parameters from JSON body
    if not request.is_json:
        current_app.logger.error("Request is not JSON")
        return jsonify({
            "success": False,
            "error": "Request must be JSON"
        }), 400
    
    data = request.json
    doc_id = data.get('document_id')
    character_id = data.get('character_id', '')
    
    if not doc_id:
        current_app.logger.error("Missing document_id parameter")
        return jsonify({
            "success": False,
            "error": "document_id is required"
        }), 400
    
    # Verify the document exists
    document = get_document_by_id(doc_id)
    if not document:
        current_app.logger.error(f"Document {doc_id} not found for summarize")
        return jsonify({
            "success": False,
            "error": "Document not found"
        }), 404
    
    current_app.logger.info(f"Summarizing document {doc_id} (character_id: {character_id})")
    
    try:
        # Get document content
        filename = document.get('filename', 'document')
        text_content = document.get('text_content', '')
        
        if not text_content:
            current_app.logger.warning(f"Document {doc_id} has no text content to summarize")
            return jsonify({
                "success": True,
                "summary": f"Document {filename} has no text content to summarize."
            })
        
        # Generate a simple summary
        summary = f"Summary of {filename}\n\n"
        summary += f"**Document Type:** {document.get('doc_type', 'unknown').upper()}\n"
        summary += f"**Size:** {document.get('file_size', 0)} bytes\n"
        summary += f"**Uploaded:** {document.get('upload_date')}\n\n"
        summary += "## Content Summary\n\n"
        
        # Add a simple excerpt of the content
        if len(text_content) > 500:
            summary += f"{text_content[:500]}...\n\n(Document contains {len(text_content)} characters total)"
        else:
            summary += text_content
        
        current_app.logger.info(f"Successfully generated summary of {len(summary)} characters")
        return jsonify({
            "success": True,
            "summary": summary
        })
    except Exception as e:
        current_app.logger.error(f"Error summarizing document: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Failed to summarize document: {str(e)}"
        }), 500

@documents_bp.route('/extract-memory', methods=['POST'])
def extract_to_memory_post():
    """
    Extract document content to character memory using POST with JSON body.
    
    Request:
        - document_id: ID of the document to extract
        - character_id: ID of the character to associate with
        
    Response:
        - JSON with success status or error message
    """
    if not HAVE_DOCUMENT_PROCESSOR:
        current_app.logger.error("Document processing not available for extract to memory")
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    # Get parameters from JSON body
    if not request.is_json:
        current_app.logger.error("Request is not JSON")
        return jsonify({
            "success": False,
            "error": "Request must be JSON"
        }), 400
    
    data = request.json
    doc_id = data.get('document_id')
    character_id = data.get('character_id')
    
    if not doc_id:
        current_app.logger.error("Missing document_id parameter")
        return jsonify({
            "success": False,
            "error": "document_id is required"
        }), 400
    
    if not character_id:
        current_app.logger.error("Missing character_id parameter")
        return jsonify({
            "success": False,
            "error": "character_id is required"
        }), 400
    
    # Log the attempt to extract document to memory
    current_app.logger.info(f"Extracting document {doc_id} to memory for character {character_id}")
    
    # Verify the document exists first
    document = get_document_by_id(doc_id)
    if not document:
        current_app.logger.error(f"Document {doc_id} not found")
        return jsonify({
            "success": False,
            "error": f"Document {doc_id} not found"
        }), 404
    
    # Now attempt to extract it to memory
    try:
        success = extract_document_to_memory(doc_id, character_id)
        if not success:
            current_app.logger.error(f"Failed to extract document {doc_id} to memory")
            return jsonify({
                "success": False,
                "error": "Document could not be extracted to memory"
            }), 500
        
        current_app.logger.info(f"Successfully extracted document {doc_id} to memory for character {character_id}")
        return jsonify({
            "success": True,
            "message": "Document content extracted to memory successfully"
        })
    except Exception as e:
        current_app.logger.error(f"Error extracting document {doc_id} to memory: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"Error extracting document: {str(e)}"
        }), 500 