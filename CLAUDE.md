# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiaChat (also known as MiaAI) is a sophisticated personal AI assistant platform that enables users to create and interact with customizable AI characters. The system features persistent memory, document analysis capabilities, and support for multiple LLM providers.

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

### Core Package Structure

- **`/app/`** - Main Flask application package
  - `api/` - REST API endpoints organized by feature (chat, characters, memories, documents, settings, models)
  - `core/` - Business logic layer (chat processing, character management, document analysis)
  - `llm/` - Language model adapters with unified interface for multiple providers
  - `memory/` - Multi-tiered memory system (short-term, long-term, permanent) with vector search
  - `static/` - Frontend assets (vanilla JavaScript SPA)
  - `templates/` - Jinja2 HTML templates

- **`/src/miachat/`** - Alternative package structure with additional features
  - `personality/` - Advanced personality framework with conflict resolution and evolution

### Technology Stack

- **Backend**: Flask 3.0.0 with CORS support
- **Database**: SQLite for relational data, FAISS for vector embeddings
- **LLM Providers**: OpenAI, Anthropic, Ollama (local models)
- **Memory**: Sentence Transformers for embeddings, tiktoken for token counting
- **Document Processing**: PyMuPDF for PDFs, Markdown support
- **Deployment**: Docker with Gunicorn, optional Ngrok tunneling

### Key System Components

1. **Character System**: XML-based personality definitions with validation schema
2. **Memory Architecture**: Tiered memory with automatic summarization and relevance scoring
3. **Multi-Provider LLM Interface**: Unified adapter pattern supporting multiple AI providers
4. **Document Analysis**: Upload and reference system for PDFs and text documents
5. **Conversation Management**: Persistent chat history with memory injection

### Configuration

- Environment variables configured via `.env` file
- LLM provider settings in `config/llm_config.json`
- Character personalities defined in `config/personalities/` as XML files
- Database path configurable via `DATABASE_PATH` environment variable

### Development Notes

- The application supports both `/app/` and `/src/miachat/` package structures
- Memory system uses vector embeddings for semantic search across conversation history
- Character personalities can evolve and develop conflicts through the personality framework
- Document analysis integrates with conversation context for reference during chat
- All API endpoints return JSON and follow RESTful conventions
- Frontend uses vanilla JavaScript with modular chat management system

### Data Persistence

- SQLite database stores characters, conversations, and metadata
- Vector embeddings stored in FAISS indexes for memory search
- Documents uploaded to `documents/` directory with JSON metadata
- Generated outputs saved to `output_documents/` directory
- Docker volumes ensure data persistence: `./data`, `./documents`, `./output_documents`, `./config`