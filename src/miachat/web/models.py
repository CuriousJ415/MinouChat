from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()

class Personality(db.Model):
    """Model for AI personalities."""
    __tablename__ = 'personalities'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    system_prompt = db.Column(db.Text, nullable=False)
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Conversation(db.Model):
    """Model for chat conversations."""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True)
    personality_id = db.Column(db.String(36), db.ForeignKey('personalities.id'), nullable=False)
    title = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    personality = db.relationship('Personality', backref=db.backref('conversations', lazy=True))
    messages = db.relationship('Message', backref='conversation', lazy=True, order_by='Message.timestamp')

    def to_dict(self):
        return {
            'id': self.id,
            'personality_id': self.personality_id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Message(db.Model):
    """Model for chat messages."""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    file_attachments = db.Column(db.JSON)  # Changed from JSONB to JSON
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'file_attachments': self.file_attachments,
            'timestamp': self.timestamp.isoformat()
        } 