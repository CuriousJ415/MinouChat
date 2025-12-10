# MiaChat Documentation

> **MiaChat** - A privacy-focused AI personality chat application with local LLM support

## Project Status

**Current Phase**: Phase 6 - LLM Provider Integration  
**Last Updated**: July 7, 2025  
**Status**: Active Development  

### Recent Achievements 🎉
- **Personality Editing System**: Complete CRUD operations with AI-powered trait suggestions
- **Modern UI**: Bootstrap-based responsive design with real-time validation
- **FastAPI Integration**: Full migration from Flask with proper routing and templates
- **Local LLM Support**: Ollama integration for privacy-first AI processing

## Quick Start

### Prerequisites
- Python 3.11+
- Ollama with llama3:8b model
- SQLite (included)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd MiaChat

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start Ollama (if not running)
ollama serve

# Run the application
python run.py
```

### First Time Setup
1. Visit `http://localhost:8000`
2. Register a new account
3. Create your first AI personality
4. Start chatting!

## Core Features

### ✅ Completed Features

#### Authentication & User Management
- User registration and login
- Session-based authentication
- Secure password hashing
- User dashboard and profile management

#### Personality System
- **Comprehensive personality creation** with AI-powered trait suggestions
- **Full editing capabilities** for existing personalities
- **Communication style customization** with interactive sliders
- **Backstory integration** for rich personality development
- **XML-based personality definitions** with validation
- **Character cards** with visual trait representation

#### Chat System
- Real-time chat interface
- Character selection and switching
- Conversation history persistence
- Context-aware responses
- Privacy-focused local LLM processing

#### Memory & Context
- SQLite-based conversation memory
- Intelligent context retrieval
- Keyword-based search
- Conversation analytics and statistics

#### Technical Infrastructure
- FastAPI backend with async architecture
- SQLAlchemy ORM with SQLite
- Jinja2 templating system
- Bootstrap-responsive UI
- Comprehensive error handling

### 🔄 In Progress

#### LLM Provider Integration (Phase 6)
- **User settings page** for LLM provider selection
- **Multi-provider support** (Ollama, OpenAI, Anthropic, LiteLM, OpenRouter)
- **Provider-specific trait suggestions** with quality improvements
- **API key management** for cloud providers
- **Privacy controls** and local-first processing

### 📋 Planned Features

#### Advanced Personality Features (Phase 7)
- Personality templates and presets
- Bulk import/export operations
- Community sharing features
- Advanced trait customization

#### Memory Enhancements (Phase 8)
- Improved memory retrieval algorithms
- Long-term memory management
- Memory visualization tools
- Context-aware response optimization

#### AI Intelligence (Phase 9)
- Emotional intelligence analysis
- Dynamic personality evolution
- Conflict resolution systems
- Complex relationship dynamics

## Architecture

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   FastAPI       │    │   Local LLM     │
│   (Bootstrap)   │◄──►│   Backend       │◄──►│   (Ollama)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite        │
                       │   Database      │
                       └─────────────────┘
```

### Key Components

#### Frontend
- **Templates**: Jinja2-based HTML templates with Bootstrap
- **JavaScript**: Vanilla JS for interactive features
- **CSS**: Bootstrap 5 with custom styling
- **Responsive Design**: Mobile-friendly interface

#### Backend
- **FastAPI**: Modern async web framework
- **SQLAlchemy**: ORM for database operations
- **Pydantic**: Data validation and serialization
- **Jinja2**: Template rendering engine

#### AI Integration
- **Ollama**: Local LLM processing
- **Personality System**: XML-based character definitions
- **Memory Service**: Context-aware conversation management
- **Trait Suggestions**: AI-powered personality development

## API Documentation

### Core Endpoints

#### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout

#### Personalities
- `GET /personality` - List all personalities
- `GET /personality/create` - Create personality form
- `POST /personality/create` - Create new personality
- `GET /personality/edit/{id}` - Edit personality form
- `PUT /personality/edit/{id}` - Update personality
- `DELETE /personality/{id}` - Delete personality

#### Chat
- `GET /chat` - Chat interface
- `POST /api/chat` - Send message
- `GET /api/chat/history` - Get conversation history

#### AI Services
- `POST /api/suggest_traits` - AI trait suggestions
- `GET /api/characters` - List available characters

### Data Models

#### Personality Schema
```json
{
  "id": "uuid",
  "name": "string",
  "category": "string",
  "backstory": "string",
  "traits": ["string"],
  "communication_style": {
    "directness": 0-100,
    "warmth": 0-100,
    "formality": 0-100,
    "empathy": 0-100,
    "humor": 0-100
  }
}
```

## Development

### Project Structure
```
MiaChat/
├── app/                    # Main application
│   ├── api/               # FastAPI routes and endpoints
│   ├── core/              # Core business logic
│   ├── llm/               # LLM integration
│   ├── memory/            # Memory and context system
│   ├── static/            # Static assets (CSS, JS, images)
│   └── templates/         # HTML templates
├── config/                # Configuration files
├── docs/                  # Documentation
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with auto-reload
uvicorn app.api.main:app --reload

# Check code quality
flake8 app/
black app/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## Privacy & Security

### Privacy-First Design
- **Local Processing**: All AI processing happens locally with Ollama
- **No External Data**: No conversation data leaves your system
- **User Control**: Complete control over data and settings
- **Open Source**: Transparent code for security verification

### Security Features
- **Password Hashing**: bcrypt for secure password storage
- **Session Management**: Secure session handling
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries

## Performance

### Current Metrics
- **Response Time**: <2 seconds for local LLM responses
- **Memory Usage**: ~2GB RAM for Ollama with llama3:8b
- **Database**: SQLite with optimized queries
- **Concurrent Users**: Single-user focused design

### Optimization Opportunities
- **Caching**: Redis for session and response caching
- **Connection Pooling**: For future cloud provider support
- **Database Indexing**: Optimize frequently queried fields
- **Async Operations**: Non-blocking I/O operations

## Troubleshooting

### Common Issues

#### Ollama Connection
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# Pull required model
ollama pull llama3:8b
```

#### Database Issues
```bash
# Reset database
rm instance/miachat.db
python init_db.py
```

#### Port Conflicts
```bash
# Check what's using port 8000
lsof -i :8000

# Kill conflicting process
kill -9 <PID>
```

## Support

### Documentation
- [Progress Tracking](tracking/progress.md) - Current development status
- [Implementation Roadmap](implementation/roadmap.md) - Detailed development plans
- [Architecture Overview](architecture/system-design.md) - System design details

### Issues
- Check the [troubleshooting section](#troubleshooting) above
- Review recent commits for fixes
- Open an issue on GitHub with detailed error information

### Community
- GitHub Discussions for questions and ideas
- Pull requests welcome for improvements
- Feature requests through GitHub Issues

---

**MiaChat** - Empowering private, personalized AI conversations  
*Built with ❤️ and FastAPI* 