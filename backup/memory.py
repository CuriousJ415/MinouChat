from __future__ import annotations
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Set
from contextlib import contextmanager

class Memory:
    """Memory management system for AI conversations"""
    
    def __init__(self, db_path: str = "memories.db"):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _db_transaction(self):
        """Context manager for database transactions"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Initialize database tables"""
        with self._db_transaction() as conn:
            # Memories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    conversation TEXT NOT NULL,
                    location TEXT,
                    importance INTEGER DEFAULT 0,
                    CONSTRAINT valid_json CHECK (json_valid(conversation))
                )
            """)
            
            # Character info table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS character_info (
                    name TEXT PRIMARY KEY,
                    personality TEXT,
                    system_prompt TEXT,
                    model TEXT,
                    role TEXT,
                    backstory TEXT,
                    last_location TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_char_time ON memories(character, timestamp)")

    def save(self, character: str, messages: List[Dict[str, str]]) -> bool:
        """Save conversation with context tracking"""
        if not messages:
            return False
            
        try:
            # Validate messages
            valid_messages = self._validate_messages(messages)
            if not valid_messages:
                return False
                
            # Extract location and importance
            location = self._extract_location(valid_messages)
            importance = self._calculate_importance(valid_messages)
            
            # Save conversation
            with self._db_transaction() as conn:
                conn.execute("""
                    INSERT INTO memories 
                    (character, conversation, location, importance)
                    VALUES (?, ?, ?, ?)
                """, (
                    character.lower(),
                    json.dumps(valid_messages),
                    location,
                    importance
                ))
                
                # Update character's last location
                if location:
                    conn.execute("""
                        UPDATE character_info 
                        SET last_location = ?, last_used = CURRENT_TIMESTAMP
                        WHERE name = ?
                    """, (location, character.lower()))
                    
            return True
            
        except Exception as e:
            logging.error(f"Save error: {str(e)}")
            return False

    def get_relevant(self, character: str, query: str, limit: int = 3) -> List[Dict]:
        """Get relevant conversation history with improved context tracking"""
        try:
            with self._db_transaction() as conn:
                # Get character's context
                cursor = conn.execute(
                    "SELECT last_location FROM character_info WHERE name = ?",
                    (character.lower(),)
                )
                last_location = cursor.fetchone()
                
                # First, get the most recent conversations regardless of query
                cursor = conn.execute("""
                    SELECT conversation
                    FROM memories 
                    WHERE character = ?
                    ORDER BY timestamp DESC
                    LIMIT 2
                """, (character.lower(),))
                recent_convs = [json.loads(row[0]) for row in cursor.fetchall() if row[0]]
                
                # Then, get conversations that match the query or location
                query_words = set(query.lower().split())
                cursor = conn.execute("""
                    SELECT conversation
                    FROM memories 
                    WHERE character = ?
                    AND (
                        location = ? 
                        OR conversation LIKE ?
                    )
                    ORDER BY 
                        importance DESC,
                        timestamp DESC
                    LIMIT ?
                """, (
                    character.lower(),
                    last_location[0] if last_location else None,
                    f"%{query}%",
                    limit
                ))
                
                query_convs = []
                for row in cursor.fetchall():
                    try:
                        conv = json.loads(row[0])
                        if isinstance(conv, list):
                            # Score by relevance to query
                            score = self._calculate_relevance(conv, query_words)
                            if score > 0:
                                query_convs.append((conv, score))
                    except json.JSONDecodeError:
                        continue
                
                # Sort by relevance score
                query_convs.sort(key=lambda x: x[1], reverse=True)
                relevant_convs = [conv for conv, _ in query_convs]
                
                # Combine results, ensuring recency and relevance
                result = []
                # Include recent conversations first
                for conv in recent_convs:
                    if conv not in result:
                        result.append(conv)
                # Add query-relevant conversations
                for conv in relevant_convs:
                    if conv not in result:
                        result.append(conv)
                
                # Limit total results
                return result[:limit + 1]  # Add 1 to improve context
                
        except Exception as e:
            logging.error(f"Retrieval error: {str(e)}")
            return []
        
    def _calculate_relevance(self, conversation: List[Dict], query_words: Set[str]) -> float:
        """Calculate conversation relevance to query"""
        score = 0.0
        for msg in conversation:
            if 'content' not in msg:
                continue
                
            content = msg['content'].lower()
            content_words = set(content.split())
            
            # Calculate word overlap
            matches = content_words.intersection(query_words)
            if matches:
                score += len(matches) * 1.0
                
            # Boost score for location mentions
            locations = ['home', 'house', 'office', 'store', 'library', 'park']
            for loc in locations:
                if loc in content:
                    score += 0.5
                    
            # Boost score for action mentions
            actions = ['went', 'going', 'moved', 'bought', 'read', 'looking']
            for action in actions:
                if action in content:
                    score += 0.3
        
        return score

    def save_character(self, name: str, personality: str, system_prompt: str, 
                      model: str, role: str = None, backstory: str = None) -> bool:
        """Save or update character information"""
        try:
            with self._db_transaction() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO character_info 
                    (name, personality, system_prompt, model, role, backstory, last_used)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    name.lower(), personality, system_prompt, 
                    model, role, backstory
                ))
            return True
        except Exception as e:
            logging.error(f"Character save error: {str(e)}")
            return False

    def load_characters(self) -> List[Dict]:
        """Load all character configurations"""
        try:
            with self._db_transaction() as conn:
                cursor = conn.execute("""
                    SELECT name, personality, system_prompt, model, 
                           role, backstory, created_at, last_used
                    FROM character_info
                    ORDER BY last_used DESC
                """)
                return [
                    {
                        "name": row[0],
                        "personality": row[1],
                        "system_prompt": row[2],
                        "model": row[3],
                        "role": row[4],
                        "backstory": row[5],
                        "created_at": row[6],
                        "last_used": row[7]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logging.error(f"Character load error: {str(e)}")
            return []

    def _validate_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Validate conversation messages"""
        valid = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if 'role' not in msg or 'content' not in msg:
                continue
            if msg['role'] not in ('user', 'assistant', 'system'):
                continue
            content = str(msg.get('content', '')).strip()
            if not content:
                continue
            valid.append({
                'role': msg['role'],
                'content': content
            })
        return valid

    def _extract_location(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Extract location from conversation"""
        locations = ['home', 'house', 'office', 'store', 'library', 'park']
        for msg in reversed(messages):
            content = msg['content'].lower()
            for loc in locations:
                if loc in content:
                    return loc
        return None

    def _calculate_importance(self, messages: List[Dict[str, str]]) -> int:
        """Calculate conversation importance (0-5)"""
        importance = 0
        markers = {
            'high': ['important', 'urgent', 'critical', 'remember'],
            'medium': ['need', 'should', 'must', 'plan'],
            'low': ['maybe', 'sometime', 'later', 'could']
        }
        
        for msg in messages:
            content = msg['content'].lower()
            if any(m in content for m in markers['high']):
                importance += 2
            elif any(m in content for m in markers['medium']):
                importance += 1
            elif any(m in content for m in markers['low']):
                importance -= 1
        
        return min(max(importance, 0), 5)