# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiaChat is a privacy-first AI assistant platform that enables users to create and interact with customizable AI characters. The system features persistent memory, document analysis (RAG), and support for multiple LLM providers with Ollama (local) as the default.

## Development Commands

### Running the Application

```bash
# Local development (requires Python 3.11+)
python web_app.py

# Docker deployment (recommended)
./start.sh
# or
docker compose up -d

# With Ollama for local models
docker compose --profile with-ollama up -d

# Stop services
./stop.sh
# or
docker compose down
```

### Testing

```bash
# Run unit tests
pytest tests/unit/

# Run tests with coverage
pytest tests/unit/ --cov=src/miachat

# Run specific test file
pytest tests/unit/test_personality.py
```

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Type checking
mypy src/miachat

# Linting
flake8 .
```

### Database Management

```bash
# Initialize database manually
python init_db.py

# Restore default characters via API
curl -X POST http://localhost:8080/api/characters/restore-defaults
```

## Architecture Overview

### Package Structure

```
src/miachat/
├── api/                    # FastAPI application
│   ├── main.py            # Main app entry point
│   ├── core/              # Business logic
│   │   ├── auth.py        # Authentication
│   │   ├── character_manager.py
│   │   ├── conversation_service.py  # DB-backed conversations
│   │   ├── document_service.py
│   │   ├── embedding_service.py
│   │   ├── enhanced_context_service.py  # RAG & memory
│   │   ├── llm_client.py  # Multi-provider LLM
│   │   └── settings_service.py
│   ├── routes/            # API endpoints
│   │   ├── auth.py
│   │   ├── artifacts.py
│   │   ├── documents.py
│   │   ├── reminders.py
│   │   └── setup.py
│   └── static/            # Frontend (vanilla JS SPA)
├── database/
│   ├── config.py          # SQLAlchemy setup
│   └── models.py          # ORM models
└── personality/           # Character framework
```

### Technology Stack

- **Backend**: FastAPI with CORS support
- **Database**: SQLite for all data (conversations, users, documents)
- **Vector Search**: FAISS for semantic embeddings
- **LLM Providers**:
  - Ollama (local, default - fully private)
  - OpenAI (GPT-4, GPT-4o)
  - Anthropic (Claude 3.5)
  - OpenRouter (100+ models)
- **Embeddings**: Sentence Transformers
- **Document Processing**: PyMuPDF for PDFs, Markdown support
- **Deployment**: Docker with Uvicorn

### Core Services

| Service | Purpose |
|---------|---------|
| `LLMClient` | Multi-provider LLM with privacy-first design |
| `ConversationService` | Database-backed conversation management |
| `EnhancedContextService` | RAG, semantic memory, document retrieval |
| `CharacterManager` | Character CRUD and configuration |
| `DocumentService` | Document upload, processing, search |
| `EmbeddingService` | FAISS vector embeddings |

### LLM Provider Configuration

Set via environment variables:
```bash
# Local (default, fully private)
OLLAMA_HOST=localhost
OLLAMA_PORT=11434

# Cloud providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
```

### Data Storage

- **SQLite**: All persistent data (users, conversations, messages, documents)
- **FAISS indexes**: Semantic search vectors
- **File storage**:
  - `documents/` - Uploaded documents
  - `character_cards/` - Character JSON files
  - `output_documents/` - Generated artifacts

### API Endpoints

All endpoints are under `/api/` prefix:
- `/api/chat` - Main chat endpoint
- `/api/chat/document` - Document-aware chat
- `/api/characters/*` - Character management
- `/api/documents/*` - Document CRUD and search
- `/api/artifacts/*` - Export and generation
- `/auth/*` - Authentication

### Development Notes

- Single database (SQLite) for all storage - no file-based conversations
- Privacy-first: Ollama is default, cloud providers require explicit keys
- Enhanced context combines conversation history, semantic memory, and RAG
- Frontend is vanilla JavaScript SPA with modular design
