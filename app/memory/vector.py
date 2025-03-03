"""
Vector Memory System
Implements RAG for semantic memory storage and retrieval
"""
import os
import json
import sqlite3
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from flask import current_app
import numpy as np

# Lazy loading for performance
_embeddings = None
_vector_store = None

def _get_embeddings():
    """
    Lazy-load the sentence transformer embeddings model
    
    Returns:
        SentenceTransformer model
    """
    global _embeddings
    if _embeddings is None:
        from sentence_transformers import SentenceTransformer
        _embeddings = SentenceTransformer('all-MiniLM-L6-v2')
    return _embeddings

def _ensure_vector_store(character_id: str):
    """
    Ensure vector store exists for character
    
    Args:
        character_id: Character ID
    """
    # Initialize vector store table
    with sqlite3.connect(current_app.config['DATABASE_PATH']) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vector_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)
        
        # Create index for faster queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vector_memories_character_id ON vector_memories(character_id)")

def add_memory(character_id: str, content: str, metadata: Dict = None) -> int:
    """
    Add a memory to the vector store
    
    Args:
        character_id: Character's unique identifier
        content: Memory content text
        metadata: Optional metadata dictionary
        
    Returns:
        ID of the created memory
        
    Raises:
        ValueError: If embedding generation fails
    """
    _ensure_vector_store(character_id)
    
    # Generate embedding
    try:
        embeddings_model = _get_embeddings()
        embedding = embeddings_model.encode(content)
        embedding_bytes = embedding.tobytes()
    except Exception as e:
        current_app.logger.error(f"Error generating embedding: {str(e)}")
        raise ValueError(f"Failed to generate embedding: {str(e)}")
    
    # Store in database
    with sqlite3.connect(current_app.config['DATABASE_PATH']) as conn:
        cursor = conn.execute(
            """
            INSERT INTO vector_memories 
            (character_id, content, embedding, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                character_id,
                content,
                embedding_bytes,
                json.dumps(metadata) if metadata else None,
                datetime.now().isoformat()
            )
        )
        conn.commit()
        return cursor.lastrowid

def query_memories(character_id: str, query: str, limit: int = 5) -> List[Dict]:
    """
    Query vector store for semantic matches
    
    Args:
        character_id: Character's unique identifier
        query: Query text
        limit: Maximum number of results
        
    Returns:
        List of matching memory dictionaries
        
    Raises:
        ValueError: If query embedding fails
    """
    _ensure_vector_store(character_id)
    
    # Generate query embedding
    try:
        embeddings_model = _get_embeddings()
        query_embedding = embeddings_model.encode(query)
    except Exception as e:
        current_app.logger.error(f"Error generating query embedding: {str(e)}")
        raise ValueError(f"Failed to generate query embedding: {str(e)}")
    
    # Get all memories for this character
    with sqlite3.connect(current_app.config['DATABASE_PATH']) as conn:
        cursor = conn.execute(
            "SELECT id, content, embedding, metadata, timestamp FROM vector_memories WHERE character_id = ?",
            (character_id,)
        )
        
        results = []
        for row in cursor:
            memory_id, content, embedding_bytes, metadata_json, timestamp = row
            
            # Convert embedding bytes to numpy array
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            # Calculate similarity
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            
            # Parse metadata
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            results.append({
                'id': memory_id,
                'content': content,
                'similarity': float(similarity),
                'metadata': metadata,
                'timestamp': timestamp
            })
    
    # Sort by similarity and return top results
    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:limit]

def delete_memory(memory_id: int) -> bool:
    """
    Delete a memory from vector store
    
    Args:
        memory_id: Memory ID
        
    Returns:
        True if successful, False if memory not found
    """
    with sqlite3.connect(current_app.config['DATABASE_PATH']) as conn:
        cursor = conn.execute("DELETE FROM vector_memories WHERE id = ?", (memory_id,))
        conn.commit()
        return cursor.rowcount > 0

def clear_character_memories(character_id: str) -> int:
    """
    Clear all memories for a character
    
    Args:
        character_id: Character's unique identifier
        
    Returns:
        Number of memories deleted
    """
    with sqlite3.connect(current_app.config['DATABASE_PATH']) as conn:
        cursor = conn.execute("DELETE FROM vector_memories WHERE character_id = ?", (character_id,))
        conn.commit()
        return cursor.rowcount

def add_conversation_to_memories(character_id: str, messages: List[Dict]) -> bool:
    """
    Extract important information from a conversation and store as memory
    
    Args:
        character_id: Character's unique identifier
        messages: List of message dictionaries
        
    Returns:
        True if successful
    """
    # Combine messages into a single text
    conversation_text = ""
    for msg in messages:
        role = msg['role']
        content = msg['content']
        conversation_text += f"{role.upper()}: {content}\n\n"
    
    # Add to memory
    add_memory(
        character_id=character_id,
        content=conversation_text,
        metadata={
            'type': 'conversation',
            'timestamp': datetime.now().isoformat()
        }
    )
    
    return True 