"""
Vector embedding service for RAG functionality with FAISS integration.
"""

import json
import os
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from ...database.models import Document, DocumentChunk
from ...database.config import get_db

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for creating and managing vector embeddings with FAISS."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_path: str = "/app/data/faiss_index"):
        """Initialize the embedding service.
        
        Args:
            model_name: SentenceTransformer model name for embeddings
            index_path: Path to store FAISS index files
        """
        self.model_name = model_name
        self.index_path = index_path
        self.embedding_model = None
        self.faiss_index = None
        self.chunk_id_mapping = {}  # Maps FAISS index position to chunk ID
        self.dimension = 384  # Default for all-MiniLM-L6-v2
        
        # Ensure index directory exists
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        self._initialize_model()
        self._load_or_create_index()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.embedding_model = SentenceTransformer(self.model_name)
            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Embedding dimension: {self.dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create a new one."""
        index_file = f"{self.index_path}.index"
        mapping_file = f"{self.index_path}_mapping.json"
        
        try:
            if os.path.exists(index_file) and os.path.exists(mapping_file):
                # Load existing index
                logger.info(f"Loading existing FAISS index from {index_file}")
                self.faiss_index = faiss.read_index(index_file)
                
                with open(mapping_file, 'r') as f:
                    # Convert string keys back to integers
                    mapping_data = json.load(f)
                    self.chunk_id_mapping = {int(k): v for k, v in mapping_data.items()}
                
                logger.info(f"Loaded FAISS index with {self.faiss_index.ntotal} vectors")
            else:
                # Create new index
                logger.info("Creating new FAISS index")
                self.faiss_index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                self.chunk_id_mapping = {}
                
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            # Fallback to new index
            self.faiss_index = faiss.IndexFlatIP(self.dimension)
            self.chunk_id_mapping = {}
    
    def _save_index(self):
        """Save FAISS index and mapping to disk."""
        try:
            index_file = f"{self.index_path}.index"
            mapping_file = f"{self.index_path}_mapping.json"
            
            faiss.write_index(self.faiss_index, index_file)
            
            with open(mapping_file, 'w') as f:
                # Convert integer keys to strings for JSON serialization
                mapping_data = {str(k): v for k, v in self.chunk_id_mapping.items()}
                json.dump(mapping_data, f)
            
            logger.info(f"Saved FAISS index with {self.faiss_index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of embeddings
        """
        try:
            if not texts:
                return np.array([])
            
            embeddings = self.embedding_model.encode(texts, normalize_embeddings=True)
            return embeddings
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}")
            raise
    
    def add_document_embeddings(self, document_id: str, chunks: List[Dict[str, Any]], db: Session = None) -> bool:
        """Add embeddings for document chunks to the FAISS index.
        
        Args:
            document_id: Document ID
            chunks: List of chunk dictionaries with text_content and metadata
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        if db is None:
            db = next(get_db())
        
        try:
            texts = [chunk['text_content'] for chunk in chunks]
            embeddings = self.create_embeddings(texts)
            
            if len(embeddings) == 0:
                logger.warning(f"No embeddings created for document {document_id}")
                return False
            
            # Add to FAISS index
            current_index = self.faiss_index.ntotal
            self.faiss_index.add(embeddings)
            
            # Update chunk records with embeddings and add to mapping
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_obj = db.query(DocumentChunk).filter(DocumentChunk.id == chunk['id']).first()
                if chunk_obj:
                    # Store embedding as JSON string
                    chunk_obj.embedding_vector = json.dumps(embedding.tolist())
                    
                    # Add to index mapping
                    faiss_idx = current_index + i
                    self.chunk_id_mapping[faiss_idx] = chunk['id']
            
            db.commit()
            self._save_index()
            
            logger.info(f"Added {len(embeddings)} embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document embeddings: {e}")
            db.rollback()
            return False
    
    def search_similar_chunks(
        self, 
        query: str, 
        user_id: Optional[int] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Search for similar document chunks using vector similarity.
        
        Args:
            query: Search query text
            user_id: Optional user ID to filter results to user's documents
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            db: Database session
            
        Returns:
            List of similar chunks with metadata and similarity scores
        """
        if db is None:
            db = next(get_db())
        
        try:
            if self.faiss_index.ntotal == 0:
                logger.warning("FAISS index is empty")
                return []
            
            # Create query embedding
            query_embedding = self.create_embeddings([query])
            if len(query_embedding) == 0:
                return []
            
            # Search FAISS index
            scores, indices = self.faiss_index.search(query_embedding, min(top_k * 2, self.faiss_index.ntotal))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # Invalid index
                    continue
                
                similarity = float(score)
                if similarity < similarity_threshold:
                    continue
                
                # Get chunk ID from mapping
                chunk_id = self.chunk_id_mapping.get(int(idx))
                if not chunk_id:
                    continue
                
                # Get chunk from database
                chunk = db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
                if not chunk:
                    continue
                
                # Get document and check user ownership if specified
                document = chunk.document
                if user_id and document.user_id != user_id:
                    continue
                
                # Update document access tracking
                document.mark_accessed()
                
                result = {
                    'chunk_id': chunk.id,
                    'document_id': chunk.document_id,
                    'document_filename': document.filename,
                    'text_content': chunk.text_content,
                    'chunk_type': chunk.chunk_type,
                    'chunk_index': chunk.chunk_index,
                    'similarity_score': similarity,
                    'metadata': chunk.doc_metadata,
                    'document_metadata': document.doc_metadata
                }
                results.append(result)
            
            # Sort by similarity score and limit results
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = results[:top_k]
            
            db.commit()
            
            logger.info(f"Found {len(results)} similar chunks for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def remove_document_embeddings(self, document_id: str, db: Session = None) -> bool:
        """Remove embeddings for a document from the FAISS index.
        
        Note: FAISS doesn't support efficient deletion, so this marks chunks as removed
        and rebuilds the index periodically.
        
        Args:
            document_id: Document ID to remove
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        if db is None:
            db = next(get_db())
        
        try:
            # Get all chunks for the document
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
            
            # Clear embedding vectors in database
            for chunk in chunks:
                chunk.embedding_vector = None
            
            db.commit()
            
            # Note: For efficiency, we don't rebuild the FAISS index immediately.
            # The chunks will be filtered out during search since they won't be found in the database.
            # A periodic rebuild process should be implemented to clean up the index.
            
            logger.info(f"Marked embeddings for removal for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing document embeddings: {e}")
            db.rollback()
            return False
    
    def rebuild_index(self, db: Session = None) -> bool:
        """Rebuild the FAISS index from all document chunks in the database.
        
        Args:
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        if db is None:
            db = next(get_db())
        
        try:
            logger.info("Rebuilding FAISS index from database")
            
            # Create new index
            new_index = faiss.IndexFlatIP(self.dimension)
            new_mapping = {}
            
            # Get all chunks with embeddings
            chunks = db.query(DocumentChunk).filter(DocumentChunk.embedding_vector.isnot(None)).all()
            
            if not chunks:
                logger.info("No chunks with embeddings found")
                self.faiss_index = new_index
                self.chunk_id_mapping = new_mapping
                self._save_index()
                return True
            
            # Collect embeddings
            embeddings = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding_vector = json.loads(chunk.embedding_vector)
                    embeddings.append(embedding_vector)
                    new_mapping[i] = chunk.id
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Invalid embedding vector for chunk {chunk.id}")
                    continue
            
            if embeddings:
                embeddings_array = np.array(embeddings, dtype=np.float32)
                new_index.add(embeddings_array)
            
            # Replace current index
            self.faiss_index = new_index
            self.chunk_id_mapping = new_mapping
            self._save_index()
            
            logger.info(f"Rebuilt FAISS index with {len(embeddings)} embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding FAISS index: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the embedding service.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            'model_name': self.model_name,
            'embedding_dimension': self.dimension,
            'total_vectors': self.faiss_index.ntotal if self.faiss_index else 0,
            'index_path': self.index_path,
            'mapping_size': len(self.chunk_id_mapping)
        }

# Global embedding service instance
embedding_service = EmbeddingService()