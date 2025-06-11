"""
Memory management for MiaChat.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class Memory:
    """Represents a single memory entry."""
    content: str
    timestamp: datetime
    context: Dict[str, str]
    importance: float
    category: str

class MemoryManager:
    """Manages conversation history and context."""
    
    def __init__(self):
        self.memories: List[Memory] = []
        self.context: Dict[str, str] = {}
    
    def add_memory(
        self,
        content: str,
        context: Optional[Dict[str, str]] = None,
        importance: float = 0.5,
        category: str = "general"
    ) -> None:
        """Add a new memory entry."""
        memory = Memory(
            content=content,
            timestamp=datetime.now(),
            context=context or {},
            importance=importance,
            category=category
        )
        self.memories.append(memory)
    
    def get_recent_memories(
        self,
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[Memory]:
        """Retrieve recent memories, optionally filtered by category."""
        memories = self.memories
        if category:
            memories = [m for m in memories if m.category == category]
        return sorted(memories, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def search_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories by content."""
        # TODO: Implement semantic search
        raise NotImplementedError
    
    def update_context(self, key: str, value: str) -> None:
        """Update the current context."""
        self.context[key] = value
    
    def get_context(self) -> Dict[str, str]:
        """Get the current context."""
        return self.context.copy() 