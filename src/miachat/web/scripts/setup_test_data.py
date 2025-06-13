#!/usr/bin/env python3
"""
Script to set up test data for the MiaChat application.
This script creates sample personalities, conversations, and messages.
"""

import os
import sys
import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from miachat.web.app import create_app
from miachat.web.models import db, Personality, Conversation, Message
from miachat.web.utils import generate_uuid
from miachat.core.personality import PersonalityManager
from miachat.llm.base import LLMProvider
from datetime import datetime, timedelta

def create_test_data():
    """Create test data for the application."""
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        Message.query.delete()
        Conversation.query.delete()
        Personality.query.delete()
        
        # Create personalities
        personalities = [
            Personality(
                id=generate_uuid(),
                name="Mia",
                description="A friendly and helpful assistant",
                system_prompt="You are Mia, a friendly and helpful assistant.",
                avatar_url="/static/avatars/mia.png"
            ),
            Personality(
                id=generate_uuid(),
                name="Alex",
                description="A technical expert",
                system_prompt="You are Alex, a technical expert.",
                avatar_url="/static/avatars/alex.png"
            ),
            Personality(
                id=generate_uuid(),
                name="Sam",
                description="A creative writer",
                system_prompt="You are Sam, a creative writer.",
                avatar_url="/static/avatars/sam.png"
            )
        ]
        for personality in personalities:
            db.session.add(personality)
        db.session.commit()

        # Create conversations and messages
        for personality in personalities:
            conversation = Conversation(
                id=generate_uuid(),
                personality_id=personality.id,
                title=f"Chat with {personality.name}"
            )
            db.session.add(conversation)
            db.session.commit()

            # Add some messages
            messages = [
                Message(
                    id=generate_uuid(),
                    conversation_id=conversation.id,
                    role="user",
                    content=f"Hello {personality.name}!",
                    timestamp=datetime.utcnow() - timedelta(minutes=30)
                ),
                Message(
                    id=generate_uuid(),
                    conversation_id=conversation.id,
                    role="assistant",
                    content=f"Hi there! How can I help you today?",
                    timestamp=datetime.utcnow() - timedelta(minutes=29)
                ),
                Message(
                    id=generate_uuid(),
                    conversation_id=conversation.id,
                    role="user",
                    content="Can you tell me about yourself?",
                    timestamp=datetime.utcnow() - timedelta(minutes=28)
                ),
                Message(
                    id=generate_uuid(),
                    conversation_id=conversation.id,
                    role="assistant",
                    content=f"I am {personality.name}, {personality.description}",
                    timestamp=datetime.utcnow() - timedelta(minutes=27)
                )
            ]
            for message in messages:
                db.session.add(message)
            db.session.commit()

            # Add a message with file attachment
            file_message = Message(
                id=generate_uuid(),
                conversation_id=conversation.id,
                role="user",
                content="Here's a file for you",
                file_attachments=[{
                    "filename": "sample.txt",
                    "url": "/static/files/sample.txt",
                    "type": "text/plain"
                }],
                timestamp=datetime.utcnow() - timedelta(minutes=20)
            )
            db.session.add(file_message)
            db.session.commit()
        
        print("Test data created successfully!")
        print(f"Created {len(personalities)} personalities")
        print(f"Created {len(conversations)} conversations")
        print(f"Created {len(messages)} messages")

if __name__ == "__main__":
    create_test_data() 