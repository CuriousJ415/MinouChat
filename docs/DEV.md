# MinouChat Development Guide

This guide covers everything you need to know to develop and debug MinouChat.

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Running Locally](#running-locally)
- [VS Code Setup](#vs-code-setup)
- [Debugging](#debugging)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Architecture Overview](#architecture-overview)
  - [Core Services](#core-services)
  - [Simplified Context System](#simplified-context-system)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Quick Start

```bash
# 1. Clone and enter directory
cd MinouChat

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn src.miachat.api.main:app --host 0.0.0.0 --port 8080 --reload

# 5. Open http://localhost:8080 in your browser
```

---

## Project Structure

```
MinouChat/
├── src/miachat/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # App entry point
│   │   ├── core/              # Business logic
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── character_manager.py
│   │   │   ├── conversation_service.py
│   │   │   ├── document_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── enhanced_context_service.py  # RAG & context synthesis
│   │   │   ├── fact_extraction_service.py   # Auto-learn user facts
│   │   │   ├── llm_client.py  # Multi-provider LLM
│   │   │   ├── backstory_service.py   # Character backstory w/ embeddings
│   │   │   ├── setting_service.py     # World/location/time settings
│   │   │   ├── persistent_memory_service.py  # Long-term memory (legacy)
│   │   │   ├── settings_service.py
│   │   │   ├── token_service.py   # Token counting
│   │   │   ├── world_info_service.py  # World info/lore (legacy)
│   │   │   └── security/
│   │   │       └── prompt_sanitizer.py  # Prompt injection protection
│   │   ├── routes/            # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── artifacts.py
│   │   │   ├── backstory.py   # Character backstory API
│   │   │   ├── documents.py
│   │   │   ├── facts.py       # Learned facts API
│   │   │   ├── memory.py      # Persistent memory API (legacy)
│   │   │   ├── reminders.py
│   │   │   ├── setting.py     # Character setting API
│   │   │   ├── setup.py
│   │   │   └── world_info.py  # World info API (legacy)
│   │   ├── templates/         # Jinja2 HTML templates
│   │   └── static/            # CSS, JS, images
│   ├── database/
│   │   ├── config.py          # SQLAlchemy setup
│   │   └── models.py          # ORM models
│   └── personality/           # Character framework
├── character_cards/           # Character JSON files
├── documents/                 # Uploaded documents
├── data/                      # FAISS indexes, SQLite DB
├── tests/                     # Test suite
│   └── unit/
├── .vscode/                   # VS Code configuration
├── requirements.txt
├── docker-compose.yml
├── start.sh / stop.sh         # Docker helpers
└── README.md
```

---

## Running Locally

### Method 1: Direct Python (Recommended for Development)

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with hot reload (auto-restarts on file changes)
uvicorn src.miachat.api.main:app --host 0.0.0.0 --port 8080 --reload

# Run without reload (for debugging)
uvicorn src.miachat.api.main:app --host 0.0.0.0 --port 8080
```

### Method 2: Docker

```bash
# Start all services
./start.sh
# or
docker compose up -d

# With local Ollama for AI
docker compose --profile with-ollama up -d

# Stop services
./stop.sh
# or
docker compose down
```

### Environment Variables

Create a `.env` file for configuration:

```bash
# LLM Provider (default: ollama for privacy)
OLLAMA_HOST=localhost
OLLAMA_PORT=11434

# Optional: Cloud providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# Database (default: SQLite)
DATABASE_URL=sqlite:///./data/miachat.db
```

---

## VS Code Setup

The project includes VS Code configuration in `.vscode/`:

### Recommended Extensions

Open VS Code and install recommended extensions:
- **Cmd/Ctrl + Shift + P** → "Extensions: Show Recommended Extensions"

Key extensions:
- Python, Pylance, Debugpy (Python development)
- Black Formatter, isort (code formatting)
- Jinja (template syntax highlighting)
- REST Client or Thunder Client (API testing)
- GitLens (Git integration)
- Claude Code (AI assistant)

### Debug Configurations

Press **F5** or go to **Run and Debug** panel:

| Configuration | Description |
|--------------|-------------|
| **MinouChat: FastAPI Server** | Run with hot reload |
| **MinouChat: FastAPI (No Reload)** | Run for breakpoint debugging |
| **Python: Current File** | Debug any Python file |
| **Python: Debug Tests** | Debug all tests |
| **Python: Debug Single Test** | Debug current test file |

### Tasks

Press **Cmd/Ctrl + Shift + P** → "Tasks: Run Task":

- **Start Server** - Run uvicorn with reload
- **Run Tests** - Run pytest
- **Run Tests with Coverage** - Generate coverage report
- **Format Code (Black)** - Auto-format Python
- **Sort Imports (isort)** - Organize imports
- **Type Check (mypy)** - Check type annotations
- **Docker: Start/Stop** - Container management

---

## Debugging

### Setting Breakpoints

1. Click in the gutter (left of line numbers) to add breakpoints
2. Start **"MinouChat: FastAPI (No Reload)"** configuration
3. Make a request to trigger the code path
4. Use debug controls: Step Over (F10), Step Into (F11), Continue (F5)

### Debug Tips

- Use `--reload` flag for development, disable for breakpoint debugging
- Check **Debug Console** for variable inspection
- Use **Watch** panel to monitor specific variables
- Set **conditional breakpoints** by right-clicking the breakpoint

### Common Issues

**Port already in use:**
```bash
lsof -i :8080
kill -9 <PID>
```

**Database not found:**
```bash
python init_db.py
```

**Import errors:**
```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH="${PWD}/src:$PYTHONPATH"
```

---

## API Reference

Base URL: `http://localhost:8080`

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | Login (returns session cookie) |
| `/auth/logout` | POST | Logout |
| `/auth/change-password` | POST | Change password |

### Characters (Personas)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/characters` | GET | List all characters |
| `/api/characters/{id}` | GET | Get character by ID |
| `/api/characters` | POST | Create character |
| `/api/characters/{id}` | PUT | Update character |
| `/api/characters/{id}` | DELETE | Delete character |
| `/api/characters/restore-defaults` | POST | Restore default characters |

### Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message |
| `/api/chat/with-document` | POST | Chat with document upload |
| `/api/conversations` | GET | List conversations |
| `/api/conversations/{id}` | GET | Get conversation |
| `/api/conversations/recent` | GET | Recent conversations |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents/` | GET | List documents |
| `/api/documents/{id}` | GET | Get document |
| `/api/documents/upload` | POST | Upload document |
| `/api/documents/{id}` | DELETE | Delete document |
| `/api/documents/search` | POST | Semantic search |

### Setting & Memory (Simplified Context System)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/characters/{id}/setting` | GET | Get character setting (world, location, time, key facts) |
| `/api/characters/{id}/setting` | PUT | Update character setting |
| `/api/characters/{id}/backstory` | GET | Get character backstory |
| `/api/characters/{id}/backstory` | PUT | Save backstory (auto-creates embeddings) |
| `/api/facts` | GET | List learned facts (query: `character_id`) |
| `/api/facts/{id}` | PUT | Update a fact |
| `/api/facts/{id}` | DELETE | Delete a fact |

### World Info & Memory (Legacy)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/world-info` | GET/POST | World info entries (keyword-triggered) |
| `/api/world-info/{id}` | PUT/DELETE | Manage entry |
| `/api/world-info/test` | POST | Test keyword triggers |
| `/api/memory` | GET/POST | Persistent memories |
| `/api/memory/{id}` | PUT/DELETE | Manage memory |

### Settings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings/llm` | GET/PUT | LLM provider settings |

---

## Testing

### Run All Tests

```bash
pytest tests/unit/ -v
```

### Run with Coverage

```bash
pytest tests/unit/ --cov=src/miachat --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Run Specific Test File

```bash
pytest tests/unit/test_personality.py -v
```

### Run Specific Test

```bash
pytest tests/unit/test_personality.py::test_create_character -v
```

### Debug Tests in VS Code

1. Open test file
2. Set breakpoints
3. Run **"Python: Debug Single Test"** configuration

---

## Code Quality

### Format Code

```bash
# Auto-format with Black
black .

# Sort imports
isort .

# Both (recommended before commit)
black . && isort .
```

### Type Checking

```bash
mypy src/miachat
```

### Linting

```bash
flake8 .
```

### Pre-commit (Optional)

```bash
pip install pre-commit
pre-commit install

# Now formatting runs automatically on commit
```

---

## Architecture Overview

### Core Services

| Service | File | Purpose |
|---------|------|---------|
| `LLMClient` | `llm_client.py` | Multi-provider LLM (Ollama, OpenAI, Anthropic, OpenRouter) |
| `ConversationService` | `conversation_service.py` | Database-backed conversations |
| `EnhancedContextService` | `enhanced_context_service.py` | RAG, semantic memory, context synthesis |
| `FactExtractionService` | `fact_extraction_service.py` | Auto-extract user facts from conversations |
| `BackstoryService` | `backstory_service.py` | Character backstory with semantic embeddings |
| `SettingService` | `setting_service.py` | World/location/time settings |
| `CharacterManager` | `character_manager.py` | Character CRUD |
| `DocumentService` | `document_service.py` | Document upload/processing |
| `EmbeddingService` | `embedding_service.py` | FAISS vector embeddings |
| `TokenService` | `token_service.py` | Token counting for context management |
| `PromptSanitizer` | `security/prompt_sanitizer.py` | Protect against prompt injection |
| `PersistentMemoryService` | `persistent_memory_service.py` | Long-term memories (legacy) |
| `WorldInfoService` | `world_info_service.py` | World info/lore (legacy) |

### Tech Stack

- **Backend**: FastAPI with async support
- **Database**: SQLite (all data)
- **Vector Search**: FAISS for semantic embeddings
- **Templates**: Jinja2
- **LLM**: Ollama (default, local), OpenAI, Anthropic, OpenRouter
- **Deployment**: Docker with Uvicorn

### Data Flow

```
User Request
    ↓
FastAPI Route (routes/*.py)
    ↓
Business Logic (core/*.py)
    ↓
Database/FAISS (database/*.py)
    ↓
LLM Provider (llm_client.py)
    ↓
Response
```

### Privacy-First Design

- Default LLM is Ollama (local, no data leaves your machine)
- Cloud providers require explicit API keys
- All data stored locally in SQLite
- No telemetry or external data transmission

### Simplified Context System

The new context system replaces the complex keyword-triggered World Info/Memory approach with a more intuitive design:

#### Components

1. **Setting** - Defines the world context
   - World/Universe (e.g., "Modern day Earth", "Star Wars universe")
   - Location (e.g., "San Francisco", "The Kingdom of Aldoria")
   - Time Period (e.g., "Present day", "Year 2087")
   - Key Facts (important context like "Magic exists")

2. **Backstory** - Character background with semantic retrieval
   - Free-form text for character history, relationships, events
   - Automatically chunked and embedded for semantic search
   - Relevant portions retrieved based on conversation context

3. **Learned Facts** - Auto-extracted user information
   - System uses LLM to extract facts from conversations
   - Stores: name, preferences, relationships, occupation, hobbies, etc.
   - Users can edit or delete incorrect facts
   - Facts are injected into context for personalized responses

#### Context Budget Allocation

The `EnhancedContextService` manages context with smart budget allocation:

```
Setting:       10% - World/location/time context
User Facts:    15% - Known facts about the user
Backstory:     15% - Character background
Conversation:  25% - Recent chat history
Documents:     35% - RAG document retrieval
```

#### Fact Extraction Flow

```
User Message → Chat Response → Background Task → LLM Extraction → Database
                                    ↓
                             Parse JSON facts
                                    ↓
                             Validate & Save
```

Facts are extracted using a local Ollama model (llama3.1:8b) for privacy.

#### Security

- `PromptSanitizer` protects against prompt injection
- User content wrapped in safety markers
- Dangerous patterns filtered from extracted facts
- API keys never exposed in responses

---

## Performance Optimization

If you're experiencing slow response times, here are the main factors to investigate:

### LLM Response Time

The biggest factor in response latency is usually the LLM itself:

| Model Size | Typical Response Time | Use Case |
|------------|----------------------|----------|
| 7B params (llama3.1:8b) | 1-5 seconds | Fast responses, simple conversations |
| 13B params | 3-10 seconds | Balanced quality/speed |
| 70B+ params | 10-60+ seconds | Highest quality, slower |

**Tips:**
- Use smaller models for development/testing
- GPU inference is 5-10x faster than CPU - ensure Ollama is using your GPU
- Cloud providers (OpenAI, Anthropic) are often faster than local Ollama

### Context Building

The `EnhancedContextService` assembles context from multiple sources. Large contexts take longer to process:

```python
# Context budget allocation (in enhanced_context_service.py)
Setting:       10%  # World/location/time
User Facts:    15%  # Learned facts about user
Backstory:     15%  # Character background
Conversation:  25%  # Recent chat history
Documents:     35%  # RAG document retrieval
```

**Tips:**
- Reduce `max_context_tokens` in LLM settings for faster responses
- Clear old conversations periodically
- Limit document uploads to relevant content only

### Embedding Generation

FAISS embeddings can be slow for large documents:

**Tips:**
- Keep individual documents under 50 pages
- Embeddings are cached - first query is slowest
- The embedding model loads on first use (~2-3 second delay)

### Database Performance

SQLite is fast for most operations, but can slow down with:
- Very long conversation histories (1000+ messages)
- Many documents with large FAISS indexes

**Tips:**
- Archive old conversations periodically
- Delete unused documents

### Quick Wins Checklist

1. **Use a smaller Ollama model** - `llama3.1:8b` instead of larger variants
2. **Enable streaming** - Responses appear progressively (feels faster)
3. **Reduce context budget** - Lower `max_context_tokens` in settings
4. **Clear conversation history** - Start fresh for unrelated topics
5. **Check GPU utilization** - Ensure Ollama is using GPU (`nvidia-smi` or `ollama ps`)
6. **Use cloud providers** - OpenAI/Anthropic APIs are often faster than local inference

---

## Troubleshooting

### Server won't start

1. Check port 8080 is available: `lsof -i :8080`
2. Verify virtual environment is active
3. Check all dependencies installed: `pip install -r requirements.txt`

### Database errors

```bash
# Reset database
rm data/miachat.db
python init_db.py
```

### Template errors

- Ensure all templates exist in `src/miachat/api/templates/`
- Check Jinja2 syntax in template files

### LLM not responding

- For Ollama: ensure it's running (`ollama serve`)
- For cloud providers: verify API keys in `.env`

### Import errors in VS Code

- Set Python interpreter to `.venv/bin/python`
- Ensure `src/` is in PYTHONPATH (configured in `.vscode/settings.json`)

---

## TODO / Known Issues

### Completed Items ✅

The following improvements have been implemented:

- **Dashboard Simplification** - Removed inaccurate statistics, kept Welcome/Quick Actions/System Status with provider indicators
- **Settings Page Consolidation** - Merged into single "LLM Configuration" section with API Keys & Connections subsection and Active Model dropdown
- **Danger Zone Expansion** - Three reset options: Restore to Default, Clear User Data, Clear Conversations Only
- **Chat Interface Improvements** - Edit persona link, descriptive tooltips, auto-collapse sidebar on all screens, dark mode user bubbles
- **Memory Tab UX** - Prominent fact values, "Add Memory" button for manual entry, improved empty state

---

### Character Avatars/Icons (Future Phase)

Design and implement a default icon set for personas:

**Icon Types:**
- Male/female variants
- Line art, monochromatic style
- Anime/cartoon aesthetic

**Role Variants:**
- Friend, Coach, Teacher, Assistant, Advisor

**Age Variants:**
- Young adult, Middle-aged, Senior

**Implementation Notes:**
- User selects icon during persona creation/edit
- Icon shown in sidebar persona list
- Icon NOT shown when sidebar is collapsed (just show name)
- May require external design work ("glow up" phase)

### Chat Bubble Animations (Future/Optional)

- Add subtle animation for message appearance
- Consider smooth fade-in or slide-up effect
- Potential streaming text animation (typewriter effect)

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and test: `pytest tests/unit/`
3. Format code: `black . && isort .`
4. Commit with descriptive message
5. Push and create pull request
