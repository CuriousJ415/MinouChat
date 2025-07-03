#!/usr/bin/env python3
"""
Test script for the conversation system.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

def test_database_initialization():
    """Test database initialization."""
    print("Testing database initialization...")
    
    try:
        from miachat.database.init_db import init_database, create_default_personality
        
        if init_database():
            print("✓ Database initialization successful")
            
            if create_default_personality():
                print("✓ Default personality creation successful")
                return True
            else:
                print("✗ Default personality creation failed")
                return False
        else:
            print("✗ Database initialization failed")
            return False
            
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        return False

def test_conversation_service():
    """Test conversation service functionality."""
    print("\nTesting conversation service...")
    
    try:
        from miachat.database.config import get_db
        from miachat.api.core.conversation_service import conversation_service
        
        # Get a database session
        db = next(get_db())
        
        # Test creating a conversation
        test_character_id = "test-character-123"
        conversation = conversation_service.get_or_create_conversation(test_character_id, db)
        
        if conversation:
            print(f"✓ Conversation created with ID: {conversation.id}")
            
            # Test adding messages
            user_message = conversation_service.add_message(
                conversation.id, 
                "Hello, this is a test message", 
                "user", 
                db
            )
            print(f"✓ User message added with ID: {user_message.id}")
            
            assistant_message = conversation_service.add_message(
                conversation.id, 
                "Hello! This is a test response", 
                "assistant", 
                db
            )
            print(f"✓ Assistant message added with ID: {assistant_message.id}")
            
            # Test getting messages
            messages = conversation_service.get_conversation_messages(conversation.id, db=db)
            if len(messages) == 2:
                print(f"✓ Retrieved {len(messages)} messages")
            else:
                print(f"✗ Expected 2 messages, got {len(messages)}")
                return False
            
            # Test getting character conversations
            conversations = conversation_service.get_character_conversations(test_character_id, db)
            if len(conversations) >= 1:
                print(f"✓ Retrieved {len(conversations)} conversations for character")
            else:
                print("✗ No conversations found for character")
                return False
            
            # Test ending conversation
            if conversation_service.end_conversation(test_character_id, db):
                print("✓ Conversation ended successfully")
            else:
                print("✗ Failed to end conversation")
                return False
            
            return True
        else:
            print("✗ Failed to create conversation")
            return False
            
    except Exception as e:
        print(f"✗ Conversation service error: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints (basic structure test)."""
    print("\nTesting API endpoint structure...")
    
    try:
        # Try to import FastAPI
        try:
            import fastapi
        except ImportError:
            print("⚠ FastAPI not available, skipping API endpoint test")
            return True  # Skip this test if FastAPI is not available
        
        from miachat.api.main import app
        
        # Check if the app has the expected endpoints
        routes = [route.path for route in app.routes]
        
        expected_endpoints = [
            "/api/chat",
            "/api/conversations",
            "/api/characters/{character_id}/conversations"
        ]
        
        for endpoint in expected_endpoints:
            if any(endpoint in route for route in routes):
                print(f"✓ Found endpoint: {endpoint}")
            else:
                print(f"✗ Missing endpoint: {endpoint}")
                return False
        
        print("✓ All expected API endpoints found")
        return True
        
    except Exception as e:
        print(f"✗ API endpoint test error: {e}")
        return False

def main():
    """Run all tests."""
    print("MiaChat Conversation System Test")
    print("=" * 40)
    
    tests = [
        ("Database Initialization", test_database_initialization),
        ("Conversation Service", test_conversation_service),
        ("API Endpoints", test_api_endpoints)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} failed")
    
    print(f"\n{'=' * 40}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Conversation system is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 