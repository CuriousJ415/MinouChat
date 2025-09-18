from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, nullable=True)  # Removed foreign key constraint for now
    title = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add character metadata
    conversation_data = Column(JSON, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    messages = relationship("Message", back_populates="conversation")

    def is_active(self):
        """Check if conversation is still active."""
        return self.ended_at is None

    def get_messages(self, limit=None):
        """Get messages from this conversation."""
        from sqlalchemy.orm import Session
        from sqlalchemy import desc

        # Get the session from the current object
        session = Session.object_session(self)
        if not session:
            return []

        query = session.query(Message).filter(Message.conversation_id == self.id).order_by(desc(Message.timestamp))
        if limit:
            query = query.limit(limit)
        return query.all()

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    content = Column(String)
    role = Column(String)  # 'user' or 'assistant'
    file_attachments = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        """Convert message to dictionary for memory service."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.file_attachments or {}
        }