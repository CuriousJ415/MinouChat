# Technical Architecture Documentation

## System Overview

MiaChat is a privacy-first AI assistant platform that supports multiple LLM providers and includes advanced document processing capabilities.

## Core Components

### 1. Document Processing Pipeline

- **Supported Formats**: PDF, DOCX, TXT, MD, CSV, XLSX
- **Text Extraction**: Format-specific processors
- **Chunking Strategy**: Token-aware splitting with overlap
- **Vector Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Storage**: FAISS for similarity search

### 2. RAG (Retrieval-Augmented Generation) System

```python
def get_enhanced_context(user_message: str, user_id: int):
    # 1. Create query embedding
    query_embedding = embedding_service.create_embeddings([user_message])
    
    # 2. Search similar chunks
    similar_chunks = embedding_service.search_similar_chunks(
        query=user_message,
        user_id=user_id,
        top_k=5,
        similarity_threshold=0.3
    )
    
    # 3. Format context for LLM
    context = format_rag_context(similar_chunks)
    return context
```

### 3. LLM Integration

- **Local Models**: Ollama (llama3.1, llama3:8b)
- **Cloud Providers**: OpenAI, Anthropic, OpenRouter
- **Privacy Mode**: All processing can be done locally
- **Model Configuration**: Per-character model selection

### 4. Database Schema

- **Users**: Authentication and preferences
- **Documents**: File metadata and processing status
- **DocumentChunks**: Text chunks with embeddings
- **Characters**: AI personality definitions
- **Conversations**: Chat history and context

## API Endpoints

- `GET /api/health` - System health check
- `POST /api/documents/upload` - Document upload
- `POST /api/documents/search` - Vector similarity search
- `POST /api/documents/rag/context` - RAG context retrieval
- `POST /api/chat` - Chat with document awareness

## Security Features

- User-scoped document access
- Local processing option for privacy
- Content hash deduplication
- File size and type validation
- SQL injection prevention