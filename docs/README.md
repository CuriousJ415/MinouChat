# MinouChat Documentation

> **MinouChat** - A privacy-focused AI personality chat application with local LLM support

## Project Status

**Current Phase**: Production Ready - Active Maintenance
**Last Updated**: December 2025
**Status**: Running in Docker with Clerk authentication

---

## Quick Start

### Docker (Recommended)
```bash
./start.sh
# or
docker compose up -d
```

### Local Development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.miachat.api.main:app --host 0.0.0.0 --port 8080 --reload
```

Access at http://localhost:8080

---

## Documentation Index

### Setup & Configuration
- [CLERK_SETUP.md](CLERK_SETUP.md) - Clerk authentication setup
- [DEV.md](DEV.md) - Development guide and debugging

### Architecture
- [authentication_system.md](authentication_system.md) - Auth system details
- [architecture/system-design.md](architecture/system-design.md) - System architecture

### Progress Tracking
- [tracking/progress.md](tracking/progress.md) - Project progress
- [implementation/roadmap.md](implementation/roadmap.md) - Implementation roadmap

---

## Core Features

### Completed
- **Multi-Provider LLM**: Ollama (local), OpenAI, Anthropic, OpenRouter
- **Privacy-First**: Local processing with Ollama default
- **Clerk Authentication**: Google SSO, email/password
- **Simplified Context System**:
  - Setting (world/location/time)
  - Backstory (semantic embeddings)
  - Learned Facts (auto-extraction)
- **Document Intelligence**: PDF/Markdown upload, RAG search
- **Security**: PromptSanitizer, API key masking

### Key Pages
| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/dashboard` | Overview and quick actions |
| Chat | `/chat` | Conversation interface |
| Personas | `/personas` | AI character management |
| Memory | `/memory` | Facts and backstory |
| Settings | `/settings` | LLM and API configuration |
| Documents | `/documents` | Upload and search |

---

## Architecture

```
src/miachat/
├── api/
│   ├── main.py                 # FastAPI entry point
│   ├── core/
│   │   ├── clerk_auth.py       # Clerk JWT authentication
│   │   ├── llm_client.py       # Multi-provider LLM
│   │   ├── backstory_service.py
│   │   ├── fact_extraction_service.py
│   │   ├── setting_service.py
│   │   ├── enhanced_context_service.py
│   │   └── security/
│   │       └── prompt_sanitizer.py
│   ├── routes/
│   └── templates/
├── database/
│   ├── config.py
│   └── models.py
└── personality/
```

---

## Development

```bash
# Run tests
pytest tests/unit/ -v

# Format code
black . && isort .

# Type checking
mypy src/miachat
```

See [DEV.md](DEV.md) for detailed development instructions.

---

## Support

- Check [CLAUDE.md](../CLAUDE.md) for troubleshooting
- Review [DEV.md](DEV.md) for common issues
- See Docker logs: `docker logs minouchat-app --tail 50`

---

**MinouChat** - Private AI conversations, thoughtfully designed
