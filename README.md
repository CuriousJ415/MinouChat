# MinouChat - Privacy-First AI Companion Platform

MinouChat is a FastAPI-based web application for creating and chatting with AI companions. Features persistent memory, document analysis (RAG), and supports multiple LLM providers with Ollama (local) as the default for complete privacy.

## Features

### Core
- **Multiple AI Personas**: Create customizable AI companions with unique personalities
- **Multi-Provider LLM Support**: Ollama (local/default), OpenAI, Anthropic, OpenRouter
- **Privacy-First Design**: Local LLM processing with Ollama - no external data transmission
- **User Authentication**: Secure login/registration with session management

### Intelligent Context System
- **Automatic Fact Extraction**: AI learns facts about you from conversations (name, preferences, etc.)
- **Semantic Backstory Retrieval**: Character backstories are chunked and embedded for contextual retrieval
- **Structured Settings**: Define world, location, and time period for each character
- **Prompt Injection Protection**: Security layer sanitizes inputs to prevent injection attacks
- **Memory Management**: View, edit, and delete learned facts from the Memory page

### Document Intelligence (RAG)
- **Document Upload**: Support for PDF and Markdown files
- **Semantic Search**: FAISS-powered vector search across documents
- **Document-Aware Chat**: Ask questions about your uploaded documents

### Conversation Features
- **Persistent History**: Database-backed conversation storage
- **Context Windowing**: Intelligent message selection for context limits
- **Export/Artifacts**: Generate and export conversation summaries

## Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Start the application
python run.py
# or
uvicorn src.miachat.api.main:app --host 0.0.0.0 --port 8080 --reload
```

### Docker (Recommended)

```bash
# Start services
./start.sh
# or
docker compose up -d

# With Ollama for local models
docker compose --profile with-ollama up -d

# Stop services
./stop.sh
```

Access the application at http://localhost:8080

## LLM Provider Configuration

| Provider | Environment Variable | Notes |
|----------|---------------------|-------|
| Ollama (default) | `OLLAMA_HOST`, `OLLAMA_PORT` | Local, private, free |
| OpenAI | `OPENAI_API_KEY` | GPT-4, GPT-4o |
| Anthropic | `ANTHROPIC_API_KEY` | Claude 3.5 |
| OpenRouter | `OPENROUTER_API_KEY` | 100+ models |

## Architecture

```
src/miachat/
├── api/
│   ├── main.py                    # FastAPI entry point
│   ├── core/
│   │   ├── backstory_service.py   # Semantic backstory retrieval
│   │   ├── fact_extraction_service.py  # Auto-learn facts from chat
│   │   ├── setting_service.py     # World/location/time settings
│   │   ├── enhanced_context_service.py  # RAG & memory integration
│   │   ├── llm_client.py          # Multi-provider LLM client
│   │   ├── conversation_service.py
│   │   ├── document_service.py
│   │   ├── embedding_service.py
│   │   └── security/
│   │       └── prompt_sanitizer.py  # Injection protection
│   ├── routes/                    # API endpoints
│   └── templates/                 # Jinja2 templates
├── database/
│   ├── config.py                  # SQLAlchemy setup
│   └── models.py                  # ORM models
└── personality/                   # Character framework
```

## Key Pages

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/dashboard` | Overview with stats and quick actions |
| Chat | `/chat` | Main conversation interface |
| Personas | `/persona` | Manage AI companions |
| Memory | `/memory` | View and manage learned facts |
| Documents | `/documents` | Upload and search documents |
| Settings | `/settings` | API keys and preferences |

## Context System

MinouChat uses a simplified, intuitive context system:

### Setting (per character)
Define the world, location, and time period. This context is always available to the AI.

### Backstory (per character)
Free-form character backstory that is chunked into semantic embeddings. Relevant portions are retrieved based on conversation context.

### Learned Facts (per user)
Facts automatically extracted from conversations:
- **Name**: User's name
- **Preferences**: Likes, dislikes, preferences
- **Occupation**: Job, profession
- **Location**: Where the user lives
- **Hobbies**: Activities, interests
- **Relationships**: People mentioned

Facts can be viewed and managed in the Memory page.

## Development

```bash
# Run tests
pytest tests/unit/

# Format code
black .

# Type checking
mypy src/miachat

# Linting
flake8 .
```

## Data Storage

- **SQLite**: Users, conversations, messages, documents, facts
- **FAISS**: Vector embeddings for semantic search
- **File System**:
  - `character_cards/` - Character JSON files
  - `documents/` - Uploaded documents
  - `output_documents/` - Generated artifacts

## Security

- Session-based authentication with secure cookies
- Prompt sanitizer protects against injection attacks
- API keys stored securely (masked in UI responses)
- User ownership verified on all operations

## License

This project is for educational and personal use.
