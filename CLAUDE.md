# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MinouChat is a privacy-first AI assistant platform that enables users to create and interact with customizable AI characters. The system features persistent memory, document analysis (RAG), and support for multiple LLM providers with Ollama (local) as the default.

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

### LLM Selection Guidelines (from Market Analysis)

**Key Insight:** Service-model matching is critical. Different LLMs excel at different use cases.

| Use Case | Recommended Model | Why |
|----------|-------------------|-----|
| **Character Roleplay** | DeepSeek R1T2 Chimera | Best reasoning + character consistency, 30.5% market leader |
| **Privacy-First** | Local Ollama (llama3.1:8b) | Zero data leaves machine, fully private |
| **Power Users** | Claude Sonnet 4.5 | Best instruction-following, 200K context window |
| **Cost-Effective** | DeepSeek V3.1 | Best cost-to-quality ratio for streaming chat |
| **Balanced** | DeepSeek V3 0324 | Good across all metrics, maintains character 50+ turns |

**Model Behavior Differences:**
- **Claude (Anthropic):** Constitutional AI, high refusal rate (98.7%), best for SFW/professional use
- **DeepSeek:** Minimal safety training, high flexibility, ideal for creative/character work
- **Grok:** Intentionally unfiltered, designed for edgy/controversial content

**Chat Interface Success Factors:**
1. Context preservation across 50+ turns without coherence loss
2. Effective response to system prompts defining behavior/personality
3. Real-time streaming for natural conversation flow
4. "Think through" complex interactions before responding (reasoning models)
5. Sufficient flexibility to support creative expression

**OpenRouter Privacy Notes:**
- OpenRouter acts as proxy - providers don't see your IP/email/account info
- Providers only receive: prompts, model parameters
- Check provider data policies (some retain prompts for training)
- For maximum privacy: use local Ollama models

See `/documents/LLM_Market_Analysis_OpenRouter_2025.md` for full analysis.

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

## Troubleshooting

### Clerk Authentication Issues

**Problem:** User sees a generated username like `user_3ffabdde` instead of their real name.

**Cause:** Clerk API calls failing with 403 errors. Check Docker logs for:
```
ERROR:src.miachat.api.core.clerk_auth:Clerk API HTTP error 403: Forbidden
```

**Root Cause:** External API calls from Docker containers can be blocked by Cloudflare if they lack a `User-Agent` header. Python's `urllib` doesn't send one by default.

**Solution:** Ensure all external API calls in `clerk_auth.py` include:
```python
headers = {
    "Authorization": f"Bearer {CLERK_SECRET_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "MinouChat/1.0",  # Required to avoid Cloudflare blocks
}
```

**Fix existing user:** If a user was created with a fallback username, update directly:
```bash
docker exec minouchat-app python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/memories.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE users SET username = 'RealName' WHERE clerk_id = 'user_xxx'\")
conn.commit()
conn.close()
"
```

### Clerk Token Expiry (401 errors after ~60 seconds)

**Problem:** API calls return 401 after the user has been on a page for ~60 seconds.

**Cause:** Clerk uses short-lived JWT tokens (60-second TTL) by design. This is a security feature, not a bug.

**Why 60 seconds?** Clerk's security model:
- Limits exposure window if a token is stolen
- Enables stateless verification (no database lookups)
- Expects their SDK to handle automatic refresh

**Industry comparison:**
| Provider | Token TTL |
|----------|-----------|
| Clerk | 60s (aggressive) |
| Auth0 | 24h (configurable) |
| Firebase/Supabase | 1 hour |

**Our solution (implemented in `chat/index.html`):**
1. **Proactive refresh:** `session.touch()` runs every 45 seconds to keep tokens fresh
2. **Retry on 401:** `authFetch()` automatically retries with a fresh token on 401
3. **Graceful fallback:** Redirects to login if retry also fails

**Key code locations:**
- `src/miachat/api/templates/chat/index.html` - `authFetch()` and `startTokenRefresh()`
- `src/miachat/api/core/clerk_auth.py` - 30-second leeway, error codes in response

**Future considerations:**
- If Clerk's 60s TTL causes issues, consider switching to session-based auth or Auth0 (configurable TTL)
- The current solution works well for active sessions but requires Clerk SDK on every authenticated page

### OpenRouter 404 Errors

**Problem:** Character configured with OpenRouter model returns 404 error.

**Cause:** OpenRouter data policy restrictions blocking certain models.

**Solution:**
1. Go to https://openrouter.ai/settings/privacy
2. Adjust your data policy settings to allow the models you want to use
3. Some models require less restrictive privacy settings

### Docker Container Debugging

```bash
# Check logs
docker logs minouchat-app --tail 50

# Test Clerk API from container
docker exec minouchat-app python3 -c "
import sys
sys.path.insert(0, '/app/src')
from miachat.api.core.clerk_auth import fetch_clerk_user_profile
profile = fetch_clerk_user_profile('user_xxx')
print(profile.display_name if profile else 'FAILED')
"

# Query database
docker exec minouchat-app python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/memories.db')
cursor = conn.cursor()
cursor.execute('SELECT id, username, email, clerk_id FROM users')
for row in cursor.fetchall(): print(row)
"
```
