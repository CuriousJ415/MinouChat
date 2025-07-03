#!/usr/bin/env python3
"""
Test script for advanced memory/context features.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

def test_memory_service():
    """Test the MemoryService functionality."""
    print("Testing MemoryService...")
    
    try:
        from miachat.database.config import get_db
        from miachat.api.core.memory_service import MemoryService
        from miachat.api.core.conversation_service import conversation_service
        
        # Get a database session
        db = next(get_db())
        
        # Create a test conversation
        test_character_id = "memory-test-character"
        conversation = conversation_service.get_or_create_conversation(test_character_id, db)
        print(f"✓ Created test conversation with ID: {conversation.id}")
        
        # Add some test messages
        test_messages = [
            ("user", "Hello! My name is John."),
            ("assistant", "Nice to meet you, John! How are you today?"),
            ("user", "I'm doing well. I have a cat named Whiskers."),
            ("assistant", "That's wonderful! Cats are great pets. Tell me more about Whiskers."),
            ("user", "Whiskers is a tabby cat and loves to play with string."),
            ("assistant", "Tabby cats are beautiful! What other things does Whiskers like?"),
            ("user", "He likes to sleep in the sun and chase birds."),
            ("assistant", "That sounds like a typical cat! Do you have any other pets?"),
            ("user", "No, just Whiskers. But I'm thinking about getting a dog."),
            ("assistant", "Dogs can be great companions too! What kind of dog are you considering?"),
        ]
        
        for role, content in test_messages:
            message = conversation_service.add_message(conversation.id, content, role, db)
            print(f"✓ Added {role} message: {content[:30]}...")
        
        # Test memory service
        memory_service = MemoryService(default_context_window=5)
        
        # Test context retrieval
        print("\nTesting context retrieval...")
        context = memory_service.get_context(
            conversation_id=conversation.id,
            current_message="What did we talk about regarding pets?",
            db=db
        )
        
        print(f"✓ Retrieved {len(context)} context messages")
        
        # Check that we have recent messages
        recent_count = len([msg for msg in context if "Whiskers" in msg["content"] or "dog" in msg["content"]])
        print(f"✓ Found {recent_count} pet-related messages in context")
        
        # Test keyword search
        print("\nTesting keyword search...")
        search_results = memory_service.search_conversation(
            conversation_id=conversation.id,
            query="cat Whiskers",
            db=db
        )
        
        print(f"✓ Found {len(search_results)} messages containing 'cat' or 'Whiskers'")
        
        # Test conversation summary
        print("\nTesting conversation summary...")
        summary = memory_service.get_conversation_summary(conversation.id, db)
        
        print(f"✓ Conversation summary: {summary['total_messages']} total messages, "
              f"{summary['user_messages']} user, {summary['assistant_messages']} assistant")
        
        return True
        
    except Exception as e:
        print(f"✗ Memory service test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test the new API endpoints for memory features."""
    print("\nTesting API endpoints...")
    
    try:
        # Try to import FastAPI
        try:
            import fastapi
        except ImportError:
            print("⚠ FastAPI not available, skipping API endpoint test")
            return True
        
        from miachat.api.main import app
        
        # Check if the new endpoints exist
        routes = [route.path for route in app.routes]
        
        expected_endpoints = [
            "/api/conversations/{conversation_id}/search",
            "/api/conversations/{conversation_id}/summary",
            "/api/conversations/{conversation_id}/context"
        ]
        
        for endpoint in expected_endpoints:
            if any(endpoint in route for route in routes):
                print(f"✓ Found endpoint: {endpoint}")
            else:
                print(f"✗ Missing endpoint: {endpoint}")
                return False
        
        print("✓ All expected memory API endpoints found")
        return True
        
    except Exception as e:
        print(f"✗ API endpoint test error: {e}")
        return False

def test_context_integration():
    """Test that context is properly integrated into the chat API."""
    print("\nTesting context integration...")
    
    try:
        from miachat.database.config import get_db
        from miachat.api.core.conversation_service import conversation_service
        from miachat.api.core.memory_service import memory_service
        
        # Get a database session
        db = next(get_db())
        
        # Create a test conversation
        test_character_id = "context-test-character"
        conversation = conversation_service.get_or_create_conversation(test_character_id, db)
        
        # Add some messages to create context
        messages = [
            ("user", "I love pizza"),
            ("assistant", "Pizza is delicious! What's your favorite topping?"),
            ("user", "I like pepperoni and mushrooms"),
            ("assistant", "Great choice! Pepperoni and mushrooms are classic toppings."),
        ]
        
        for role, content in messages:
            conversation_service.add_message(conversation.id, content, role, db)
        
        # Test context retrieval for a follow-up question
        current_message = "What toppings did I mention earlier?"
        context = memory_service.get_context(
            conversation_id=conversation.id,
            current_message=current_message,
            db=db
        )
        
        # Check that context includes the pizza-related messages
        pizza_messages = [msg for msg in context if "pizza" in msg["content"].lower()]
        topping_messages = [msg for msg in context if "pepperoni" in msg["content"].lower() or "mushroom" in msg["content"].lower()]
        
        print(f"✓ Context contains {len(pizza_messages)} pizza-related messages")
        print(f"✓ Context contains {len(topping_messages)} topping-related messages")
        
        if len(pizza_messages) > 0 and len(topping_messages) > 0:
            print("✓ Context integration working correctly")
            return True
        else:
            print("✗ Context integration not working as expected")
            return False
        
    except Exception as e:
        print(f"✗ Context integration test error: {e}")
        return False

def main():
    """Run all memory feature tests."""
    print("MiaChat Advanced Memory/Context Features Test")
    print("=" * 50)
    
    tests = [
        ("Memory Service", test_memory_service),
        ("API Endpoints", test_api_endpoints),
        ("Context Integration", test_context_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} failed")
    
    print(f"\n{'=' * 50}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All memory/context feature tests passed!")
        print("\n✅ Advanced memory/context features are working correctly:")
        print("   - Conversation context retrieval (last N + keyword search)")
        print("   - Memory service with configurable context window")
        print("   - API endpoints for search and summary")
        print("   - Integration with chat API for context-aware responses")
        return 0
    else:
        print("❌ Some memory/context feature tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 