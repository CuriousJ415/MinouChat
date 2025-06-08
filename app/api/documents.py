"""
Documents API

This module provides API endpoints for document management, including uploading,
retrieving, and processing documents.
"""

from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename
import json

# Create blueprint
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

# Global flag for document processor availability
HAVE_DOCUMENT_PROCESSOR = False

def init_app(app):
    """Initialize document API routes"""
    global HAVE_DOCUMENT_PROCESSOR
    
    # Import document processing functions within app context
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
        app.logger.info("Document API routes registered with full processing capabilities")
    except ImportError:
        HAVE_DOCUMENT_PROCESSOR = False
        app.logger.warning("Document processing is not available - limited functionality only")
    
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
        from app.core.document_processor import get_character_documents
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
                        return jsonify({"error": f"Error reading document {filename}: {str(e)}"}), 500
        
        # Sort by upload date (newest first)
        documents.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
        
        return jsonify(documents)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to list documents: {str(e)}"
        }), 500

@documents_bp.route('/', methods=['POST'])
def upload_document():
    """Upload a document"""
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
    
    # Get character ID if provided
    character_id = request.form.get('character_id', '')
    
    # Process the uploaded document
    try:
        from app.core.document_processor import process_uploaded_document
        document = process_uploaded_document(
            file_obj=file,
            filename=secure_filename(file.filename),
            character_id=character_id
        )
        
        # Don't return the full text content
        if 'text_content' in document:
            document.pop('text_content')
        
        return jsonify(document)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error processing document: {str(e)}"
        }), 500

@documents_bp.route('/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """Get document details"""
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    try:
        from app.core.document_processor import get_document_by_id
        document = get_document_by_id(doc_id)
        if not document:
            return jsonify({
                "success": False,
                "error": "Document not found"
            }), 404
        
        # Don't return the full text content
        if 'text_content' in document:
            document.pop('text_content')
        
        return jsonify(document)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error retrieving document: {str(e)}"
        }), 500

@documents_bp.route('/<doc_id>', methods=['DELETE'])
def delete_document_route(doc_id):
    """Delete a document"""
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    try:
        from app.core.document_processor import delete_document
        if delete_document(doc_id):
            return jsonify({"success": True})
        else:
            return jsonify({
                "success": False,
                "error": "Document not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error deleting document: {str(e)}"
        }), 500

@documents_bp.route('/<doc_id>/summary', methods=['POST'])
def create_summary(doc_id):
    """Create a summary of a document"""
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    # Get character ID from request
    character_id = request.json.get('character_id')
    if not character_id:
        return jsonify({
            "success": False,
            "error": "Character ID is required"
        }), 400
    
    try:
        from app.core.document_processor import create_document_summary
        summary = create_document_summary(doc_id, character_id)
        if summary:
            return jsonify({"summary": summary})
        else:
            return jsonify({
                "success": False,
                "error": "Document not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error creating summary: {str(e)}"
        }), 500

@documents_bp.route('/<doc_id>/extract', methods=['POST'])
def extract_to_memory(doc_id):
    """Extract document content to character memory"""
    if not HAVE_DOCUMENT_PROCESSOR:
        return jsonify({
            "success": False,
            "error": "Document processing is not available"
        }), 501
    
    # Get character ID from request
    character_id = request.json.get('character_id')
    if not character_id:
        return jsonify({
            "success": False,
            "error": "Character ID is required"
        }), 400
    
    try:
        from app.core.document_processor import extract_document_to_memory
        if extract_document_to_memory(doc_id, character_id):
            return jsonify({"success": True})
        else:
            return jsonify({
                "success": False,
                "error": "Document not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error extracting document: {str(e)}"
        }), 500 