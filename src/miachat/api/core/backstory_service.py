"""
Backstory Service for managing character backstory with semantic embeddings.

Stores backstory text chunked and embedded for semantic retrieval,
allowing relevant backstory parts to be retrieved based on conversation context.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from ...database.models import BackstoryChunk
from .embedding_service import embedding_service

logger = logging.getLogger(__name__)


class BackstoryService:
    """Manages character backstory with semantic embeddings."""

    def __init__(self, storage_dir: str = "character_cards"):
        self.storage_dir = Path(storage_dir)
        self.chunk_size = 200  # Target words per chunk
        self.chunk_overlap = 20  # Words of overlap between chunks

        # Cache for backstory chunks with parsed embeddings
        # Key: "character_id:user_id", Value: {"chunks": [...], "timestamp": datetime}
        self._chunks_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minute TTL for backstory (changes less frequently)

    def _get_cache_key(self, character_id: str, user_id: int) -> str:
        """Generate cache key for character/user combination."""
        return f"{character_id}:{user_id}"

    def _get_from_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached chunks with pre-parsed embeddings."""
        if key not in self._chunks_cache:
            return None

        cached = self._chunks_cache[key]
        age = (datetime.now(timezone.utc) - cached['timestamp']).total_seconds()

        if age > self.cache_ttl:
            del self._chunks_cache[key]
            return None

        return cached['chunks']

    def _set_cache(self, key: str, chunks: List[Dict[str, Any]]):
        """Store chunks in cache with pre-parsed embeddings."""
        self._chunks_cache[key] = {
            'chunks': chunks,
            'timestamp': datetime.now(timezone.utc)
        }

    def invalidate_cache(self, character_id: str, user_id: int):
        """Invalidate cache for a character/user."""
        key = self._get_cache_key(character_id, user_id)
        if key in self._chunks_cache:
            del self._chunks_cache[key]
            logger.debug(f"Invalidated backstory cache for {key}")

    def save_backstory(
        self,
        character_id: str,
        user_id: int,
        backstory_text: str,
        db: Session
    ) -> bool:
        """
        Save backstory and create semantic embeddings.

        Steps:
        1. Delete existing chunks for this character
        2. Split backstory into semantic chunks (by paragraph or ~200 words)
        3. Generate embeddings for each chunk
        4. Store in BackstoryChunk table

        Args:
            character_id: The character UUID
            user_id: The user ID who owns this backstory
            backstory_text: The full backstory text
            db: Database session

        Returns:
            True if successful, False otherwise
        """
        try:
            # 1. Delete existing chunks for this character/user
            self._delete_existing_chunks(character_id, user_id, db)

            # Clean and validate backstory
            backstory_text = (backstory_text or "").strip()
            if not backstory_text:
                logger.info(f"Empty backstory for character {character_id}, cleared existing chunks")
                # Also update the character card JSON
                self._update_character_backstory(character_id, "")
                return True

            # 2. Split into semantic chunks
            chunks = self._split_into_chunks(backstory_text)

            if not chunks:
                logger.warning(f"No chunks created from backstory for {character_id}")
                return False

            # 3. Generate embeddings for all chunks
            embeddings = embedding_service.create_embeddings(chunks)

            # 4. Store chunks in database
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = BackstoryChunk(
                    character_id=character_id,
                    user_id=user_id,
                    chunk_index=i,
                    text_content=chunk_text,
                    embedding_vector=json.dumps(embedding.tolist()),
                    created_at=datetime.now(timezone.utc)
                )
                db.add(chunk)

            db.commit()

            # 5. Invalidate cache after saving new chunks
            self.invalidate_cache(character_id, user_id)

            # 6. Update the character card JSON with full backstory
            self._update_character_backstory(character_id, backstory_text)

            logger.info(f"Saved {len(chunks)} backstory chunks for character {character_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving backstory for {character_id}: {e}")
            db.rollback()
            return False

    def _load_chunks_with_embeddings(
        self,
        character_id: str,
        user_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        Load chunks from DB and parse embeddings, using cache when available.

        This avoids repeated JSON parsing of embeddings on every query.

        Returns:
            List of dicts with 'text', 'index', and 'embedding' (numpy array)
        """
        cache_key = self._get_cache_key(character_id, user_id)

        # Try cache first
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for backstory chunks: {cache_key}")
            return cached

        # Load from database
        db_chunks = db.query(BackstoryChunk).filter(
            BackstoryChunk.character_id == character_id,
            BackstoryChunk.user_id == user_id
        ).order_by(BackstoryChunk.chunk_index).all()

        if not db_chunks:
            return []

        # Parse embeddings once and cache
        chunks = []
        for chunk in db_chunks:
            if not chunk.embedding_vector:
                continue

            try:
                embedding = np.array(json.loads(chunk.embedding_vector))
                chunks.append({
                    'text': chunk.text_content,
                    'index': chunk.chunk_index,
                    'embedding': embedding
                })
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid embedding for chunk {chunk.id}: {e}")
                continue

        # Store in cache
        self._set_cache(cache_key, chunks)
        logger.debug(f"Cached {len(chunks)} backstory chunks for {cache_key}")

        return chunks

    def get_relevant_backstory(
        self,
        character_id: str,
        user_id: int,
        query: str,
        db: Session,
        top_k: int = 3,
        similarity_threshold: float = 0.3
    ) -> List[str]:
        """
        Retrieve backstory chunks relevant to current conversation context.

        Uses semantic similarity to find relevant parts of the backstory
        that should be included in the context.

        Args:
            character_id: The character UUID
            user_id: The user ID
            query: The query text (usually recent conversation)
            db: Database session
            top_k: Maximum number of chunks to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of relevant backstory text chunks
        """
        try:
            # Get chunks with pre-parsed embeddings (cached)
            chunks = self._load_chunks_with_embeddings(character_id, user_id, db)

            if not chunks:
                return []

            # Create query embedding
            query_embedding = embedding_service.create_embeddings([query])
            if len(query_embedding) == 0:
                return []

            query_vec = query_embedding[0]

            # Score each chunk by similarity (embeddings already parsed)
            scored_chunks = []
            for chunk in chunks:
                # Cosine similarity (embeddings are normalized)
                similarity = float(np.dot(query_vec, chunk['embedding']))

                if similarity >= similarity_threshold:
                    scored_chunks.append({
                        'text': chunk['text'],
                        'index': chunk['index'],
                        'similarity': similarity
                    })

            # Sort by similarity and return top_k
            scored_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            top_chunks = scored_chunks[:top_k]

            # Sort by original index to maintain narrative order
            top_chunks.sort(key=lambda x: x['index'])

            return [c['text'] for c in top_chunks]

        except Exception as e:
            logger.error(f"Error getting relevant backstory: {e}")
            return []

    def get_full_backstory(self, character_id: str) -> str:
        """
        Return the complete backstory text from the character card.

        Args:
            character_id: The character UUID

        Returns:
            Full backstory text or empty string
        """
        file_path = self.storage_dir / f"{character_id}.json"

        if not file_path.exists():
            return ""

        try:
            with open(file_path, 'r') as f:
                character = json.load(f)
            return character.get('backstory', '') or ''
        except Exception as e:
            logger.error(f"Error loading backstory for {character_id}: {e}")
            return ""

    def get_backstory_stats(
        self,
        character_id: str,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get statistics about the backstory chunks.

        Args:
            character_id: The character UUID
            user_id: The user ID
            db: Database session

        Returns:
            Dict with chunk_count, total_words, etc.
        """
        chunks = db.query(BackstoryChunk).filter(
            BackstoryChunk.character_id == character_id,
            BackstoryChunk.user_id == user_id
        ).all()

        total_words = 0
        total_chars = 0
        for chunk in chunks:
            total_words += len(chunk.text_content.split())
            total_chars += len(chunk.text_content)

        return {
            'chunk_count': len(chunks),
            'total_words': total_words,
            'total_characters': total_chars,
            'has_embeddings': all(c.embedding_vector for c in chunks) if chunks else False
        }

    def format_backstory_context(
        self,
        character_id: str,
        user_id: int,
        query: str,
        db: Session,
        top_k: int = 2
    ) -> str:
        """
        Format relevant backstory as context for system prompt.

        Args:
            character_id: The character UUID
            user_id: The user ID
            query: Query for relevance (usually recent messages)
            db: Database session
            top_k: Max chunks to include

        Returns:
            Formatted context string or empty string
        """
        relevant_chunks = self.get_relevant_backstory(
            character_id, user_id, query, db, top_k=top_k
        )

        if not relevant_chunks:
            return ""

        context_parts = [
            "[Relevant Background - use naturally in conversation, don't explicitly reference]"
        ]
        context_parts.extend(relevant_chunks)

        return "\n\n".join(context_parts)

    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into semantic chunks.

        Strategy:
        1. Split by paragraphs first (double newline)
        2. If paragraph is too long, split by sentences
        3. Aim for ~200 words per chunk with some overlap

        Args:
            text: The full text to chunk

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Split by paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        chunks = []
        current_chunk = []
        current_word_count = 0

        for para in paragraphs:
            para_words = len(para.split())

            # If paragraph alone exceeds chunk size, split by sentences
            if para_words > self.chunk_size * 1.5:
                # Flush current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_word_count = 0

                # Split long paragraph into sentence chunks
                sentences = self._split_into_sentences(para)
                sentence_chunk = []
                sentence_word_count = 0

                for sentence in sentences:
                    sentence_words = len(sentence.split())

                    if sentence_word_count + sentence_words > self.chunk_size:
                        if sentence_chunk:
                            chunks.append(' '.join(sentence_chunk))
                        # Start new chunk with overlap
                        overlap_sentences = sentence_chunk[-2:] if len(sentence_chunk) >= 2 else sentence_chunk
                        sentence_chunk = overlap_sentences + [sentence]
                        sentence_word_count = sum(len(s.split()) for s in sentence_chunk)
                    else:
                        sentence_chunk.append(sentence)
                        sentence_word_count += sentence_words

                if sentence_chunk:
                    chunks.append(' '.join(sentence_chunk))

            # Normal paragraph handling
            elif current_word_count + para_words > self.chunk_size:
                # Flush current chunk and start new one
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_word_count = para_words
            else:
                # Add to current chunk
                current_chunk.append(para)
                current_word_count += para_words

        # Don't forget the last chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting - handles common cases
        # Pattern matches sentence-ending punctuation followed by space and capital
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [s.strip() for s in sentences if s.strip()]

    def _delete_existing_chunks(
        self,
        character_id: str,
        user_id: int,
        db: Session
    ):
        """Delete existing backstory chunks for a character/user."""
        db.query(BackstoryChunk).filter(
            BackstoryChunk.character_id == character_id,
            BackstoryChunk.user_id == user_id
        ).delete()

    def _update_character_backstory(self, character_id: str, backstory_text: str):
        """Update the backstory field in the character JSON file."""
        file_path = self.storage_dir / f"{character_id}.json"

        if not file_path.exists():
            logger.warning(f"Character file not found: {character_id}")
            return

        try:
            with open(file_path, 'r') as f:
                character = json.load(f)

            character['backstory'] = backstory_text
            character['updated_at'] = datetime.now().isoformat()

            with open(file_path, 'w') as f:
                json.dump(character, f, indent=2)

        except Exception as e:
            logger.error(f"Error updating character backstory: {e}")


# Global instance
backstory_service = BackstoryService()
