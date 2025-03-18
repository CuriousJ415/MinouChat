"""
Output Window API
Endpoints for managing output documents and formatted content
"""

from flask import request, jsonify, current_app
from app.api import output_bp
from app.core.output_window import (
    create_output_document,
    update_output_document,
    get_output_document,
    get_character_output_documents,
    delete_output_document,
    append_to_output_document,
    create_summary_document,
    count_character_output_documents
)

@output_bp.route('/create', methods=['POST'])
def create_document():
    """Create a new output document"""
    data = request.json
    
    if not data or 'character_id' not in data or 'title' not in data or 'content' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    character_id = data['character_id']
    title = data['title']
    content = data['content']
    doc_type = data.get('doc_type', 'markdown')
    metadata = data.get('metadata')
    
    # Create document
    doc_id = create_output_document(character_id, title, content, doc_type, metadata)
    
    return jsonify({
        'success': True,
        'message': 'Document created successfully',
        'document_id': doc_id
    }), 201

@output_bp.route('/update/<doc_id>', methods=['PUT'])
def update_document(doc_id):
    """Update an existing output document"""
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No update data provided'
        }), 400
    
    # Check if document exists
    document = get_output_document(doc_id)
    if not document:
        return jsonify({
            'success': False,
            'message': 'Document not found'
        }), 404
    
    title = data.get('title')
    content = data.get('content')
    metadata = data.get('metadata')
    
    # Update document
    success = update_output_document(doc_id, title, content, metadata)
    
    return jsonify({
        'success': success,
        'message': 'Document updated successfully' if success else 'Failed to update document'
    }), 200 if success else 500

@output_bp.route('/append/<doc_id>', methods=['POST'])
def append_to_document(doc_id):
    """Append content to an existing document"""
    data = request.json
    
    if not data or 'content' not in data:
        return jsonify({
            'success': False,
            'message': 'No content provided'
        }), 400
    
    # Check if document exists
    document = get_output_document(doc_id)
    if not document:
        return jsonify({
            'success': False,
            'message': 'Document not found'
        }), 404
    
    content = data['content']
    
    # Append to document
    success = append_to_output_document(doc_id, content)
    
    return jsonify({
        'success': success,
        'message': 'Content appended successfully' if success else 'Failed to append content'
    }), 200 if success else 500

@output_bp.route('/character/<character_id>', methods=['GET'])
def character_documents(character_id):
    """Get output documents for a character"""
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    documents = get_character_output_documents(character_id, limit, offset)
    count = count_character_output_documents(character_id)
    
    return jsonify({
        'success': True,
        'documents': documents,
        'total': count
    }), 200

@output_bp.route('/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """Get an output document"""
    document = get_output_document(doc_id)
    if not document:
        return jsonify({
            'success': False,
            'message': 'Document not found'
        }), 404
    
    return jsonify({
        'success': True,
        'document': document
    }), 200

@output_bp.route('/delete/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete an output document"""
    # Check if document exists
    document = get_output_document(doc_id)
    if not document:
        return jsonify({
            'success': False,
            'message': 'Document not found'
        }), 404
    
    # Delete document
    success = delete_output_document(doc_id)
    
    return jsonify({
        'success': success,
        'message': 'Document deleted successfully' if success else 'Failed to delete document'
    }), 200 if success else 500

@output_bp.route('/summarize', methods=['POST'])
def summarize_document():
    """Create a summary document from a source document"""
    data = request.json
    
    if not data or 'character_id' not in data or 'source_document_id' not in data:
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400
    
    character_id = data['character_id']
    source_document_id = data['source_document_id']
    prompt = data.get('prompt')
    
    # Create summary document
    doc_id = create_summary_document(character_id, source_document_id, prompt)
    
    if not doc_id:
        return jsonify({
            'success': False,
            'message': 'Failed to create summary document'
        }), 500
    
    return jsonify({
        'success': True,
        'message': 'Summary document created successfully',
        'document_id': doc_id
    }), 201 