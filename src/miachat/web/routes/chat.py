from flask import Blueprint, request, jsonify, current_app
from miachat.core.conversation import ConversationManager
from miachat.core.memory import MemoryManager
from miachat.core.personality import PersonalityManager
from miachat.llm.base import LLMProvider
from miachat.database.config import db_config
from miachat.database.models import Conversation, Message, File
from sqlalchemy import desc
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from ..core.template import render_template
from sqlalchemy.orm import Session

bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Dummy managers for now (replace with real instances as needed)
memory_manager = MemoryManager()
personality_manager = PersonalityManager()
llm_provider = LLMProvider()
conversation_manager = ConversationManager(memory_manager, personality_manager, llm_provider)

router = APIRouter()

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'mp3', 'mp4'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400

    uploaded_files = []
    session = db_config.get_session()
    
    try:
        for file in files:
            if file and allowed_file(file.filename):
                # Generate unique filename
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}.{file_ext}"
                
                # Create upload directory if it doesn't exist
                upload_dir = os.path.join(current_app.static_folder, 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                
                # Create file record in database
                file_record = File(
                    original_name=original_filename,
                    stored_name=unique_filename,
                    file_type=file.content_type,
                    file_size=os.path.getsize(file_path),
                    upload_date=datetime.utcnow()
                )
                session.add(file_record)
                session.flush()  # Get the ID without committing
                
                uploaded_files.append({
                    'id': file_record.id,
                    'name': original_filename,
                    'type': file.content_type,
                    'url': f"/static/uploads/{unique_filename}",
                    'size': file_record.file_size
                })
        
        session.commit()
        return jsonify({'files': uploaded_files})
    
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    
    finally:
        session.close()

@bp.route('/history/<int:conversation_id>', methods=['GET'])
def get_conversation_history(conversation_id):
    session = db_config.get_session()
    try:
        # Get the conversation
        conversation = session.query(Conversation).get(conversation_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404

        # Get query parameters for filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        message_type = request.args.get('type')  # 'text', 'file', or None for all
        
        # Base query
        query = session.query(Message).filter(Message.conversation_id == conversation_id)
        
        # Apply date filters if provided
        if start_date:
            query = query.filter(Message.timestamp >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(Message.timestamp <= datetime.fromisoformat(end_date))
            
        # Apply type filter if provided
        if message_type:
            if message_type == 'file':
                query = query.filter(Message.files.any())
            elif message_type == 'text':
                query = query.filter(~Message.files.any())
        
        # Get all messages for this conversation, ordered by timestamp
        messages = query.order_by(Message.timestamp).all()

        # Format the response
        conversation_data = {
            'id': conversation.id,
            'personality_id': conversation.personality_id,
            'metadata': conversation.metadata,
            'created_at': conversation.created_at.isoformat(),
            'messages': [
                {
                    'id': msg.id,
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat(),
                    'metadata': msg.metadata,
                    'files': [
                        {
                            'id': file.id,
                            'name': file.original_name,
                            'type': file.file_type,
                            'url': f"/static/uploads/{file.stored_name}",
                            'size': file.file_size
                        }
                        for file in msg.files
                    ] if msg.files else []
                }
                for msg in messages
            ]
        }

        return jsonify(conversation_data)

    finally:
        session.close()

@bp.route('/send', methods=['POST'])
def send_message():
    data = request.json
    conversation_id = data.get('conversation_id')
    personality_id = data.get('personality_id')
    message = data.get('message')
    metadata = data.get('metadata', {})
    files = data.get('files', [])

    if not message and not files:
        return jsonify({'error': 'Message or files required'}), 400
    if not personality_id:
        return jsonify({'error': 'Missing personality_id'}), 400

    session = db_config.get_session()
    try:
        # Start a new conversation if needed
        if not conversation_id:
            conversation = Conversation.create(personality_id=personality_id, metadata=metadata)
            session.add(conversation)
            session.commit()
            conversation_id = conversation.id

        # Create message record
        message_record = Message(
            conversation_id=conversation_id,
            role='user',
            content=message or '',
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        session.add(message_record)

        # Associate files with message if any
        if files:
            file_records = session.query(File).filter(File.id.in_([f['id'] for f in files])).all()
            message_record.files.extend(file_records)

        session.commit()

        # Process the message and get a response
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(
            conversation_manager.process_message(
                conversation_id=conversation_id,
                message=message,
                metadata=metadata
            )
        )
        loop.close()

        # Create AI response message
        ai_message = Message(
            conversation_id=conversation_id,
            role='assistant',
            content=response,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        session.add(ai_message)
        session.commit()

        return jsonify({
            'conversation_id': conversation_id,
            'response': response,
            'files': [
                {
                    'id': file.id,
                    'name': file.original_name,
                    'type': file.file_type,
                    'url': f"/static/uploads/{file.stored_name}",
                    'size': file.file_size
                }
                for file in message_record.files
            ] if message_record.files else []
        })

    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        session.close()

@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request, db: Session = Depends(get_db)):
    """Render the chat interface with personality selector."""
    # Get all personalities
    personalities = [
        personality_manager.get_personality(name)
        for name in personality_manager.list_personalities()
    ]
    
    # Get active personality
    active_personality = personality_manager.get_active_personality()
    active_name = active_personality.name if active_personality else None
    
    # Get categories and tags
    categories = personality_manager.get_categories()
    tags = personality_manager.get_tags()
    
    # Get chat history (implement this based on your database schema)
    chat_history = []  # TODO: Implement chat history retrieval
    
    return render_template(
        "chat/index.html",
        request=request,
        personalities=personalities,
        active_personality=active_name,
        categories=categories,
        tags=tags,
        chat_history=chat_history,
        messages=[]  # Start with empty messages
    )

@router.post("/api/chat")
async def chat_endpoint(message: str, db: Session = Depends(get_db)):
    """Handle chat messages and return AI responses."""
    # Get active personality
    active_personality = personality_manager.get_active_personality()
    if not active_personality:
        return {"error": "No active personality selected"}
    
    # TODO: Implement chat logic with personality-specific responses
    # This should use the active personality's configuration to generate responses
    
    return {"response": "This is a placeholder response. Chat implementation pending."} 