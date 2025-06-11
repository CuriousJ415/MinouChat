"""
Unit tests for the Memory class.
"""

import pytest
from datetime import datetime

from miachat.core.memory import Memory, MemoryManager

def test_memory_creation():
    """Test creating a new Memory instance."""
    memory = Memory(
        content="Test memory content",
        timestamp=datetime.now(),
        context={"location": "test"},
        importance=0.8,
        category="test"
    )
    
    assert memory.content == "Test memory content"
    assert memory.importance == 0.8
    assert memory.category == "test"
    assert memory.context["location"] == "test"

def test_memory_manager():
    """Test MemoryManager functionality."""
    manager = MemoryManager()
    
    # Test adding memory
    manager.add_memory(
        content="Test memory 1",
        context={"location": "test1"},
        importance=0.8,
        category="test"
    )
    
    manager.add_memory(
        content="Test memory 2",
        context={"location": "test2"},
        importance=0.6,
        category="test"
    )
    
    # Test getting recent memories
    recent = manager.get_recent_memories(limit=1)
    assert len(recent) == 1
    assert recent[0].content == "Test memory 2"
    
    # Test context management
    manager.update_context("user", "test_user")
    context = manager.get_context()
    assert context["user"] == "test_user"
    
    # Test category filtering
    category_memories = manager.get_recent_memories(category="test")
    assert len(category_memories) == 2
    assert all(m.category == "test" for m in category_memories) 