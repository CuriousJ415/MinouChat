# MiaChat Architecture Decision

## Package Structure Decision

**Canonical Structure: `/src/miachat/`**

### Rationale
1. **Standard Python Practice**: `/src/` layout is the recommended modern Python package structure
2. **Import Safety**: Prevents accidental local imports during development
3. **Clear Separation**: Distinguishes between package code and project infrastructure
4. **Testing Isolation**: Tests run against installed package, not local files

### Directory Organization
```
/Users/jasonnau/projects/MiaChat/
├── src/miachat/           # Main package (CANONICAL)
│   ├── api/               # FastAPI application
│   │   ├── core/         # Business logic
│   │   ├── routes/       # API endpoints
│   │   └── templates/    # Jinja2 templates
│   ├── database/         # Database models and migrations
│   ├── llm/              # LLM provider adapters
│   └── core/             # Core personality and memory systems
├── character_cards/       # User character definitions (JSON)
├── conversations/        # Conversation history and versioning
├── config/               # Configuration files
├── data/                 # Runtime data (SQLite, etc.)
├── documents/            # User uploaded documents
└── app/                  # DEPRECATED - remove after migration
```

## Development Workflow

### Option 1: Development Volume Mounting (Recommended)
- Mount `/src` for live development
- Faster iteration, immediate reflection of changes
- Requires updating docker-compose.yml

### Option 2: Rebuild-Based Development
- Rebuild container for each change
- Slower but more production-like
- Current approach

### Option 3: Local Development with Docker Services
- Run FastAPI locally via `uvicorn`
- Use Docker only for Ollama and other services
- Fastest development iteration

## Implementation Plan

1. **Remove `/app` directory** - it's empty and causing confusion
2. **Update Docker configuration** to mount `/src` for development
3. **Add development vs production docker-compose files**
4. **Update documentation** to reflect canonical structure