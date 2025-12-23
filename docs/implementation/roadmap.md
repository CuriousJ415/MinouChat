# MinouChat Implementation Roadmap

## Overview
This document outlines the implementation roadmap for MinouChat, a privacy-focused AI personality chat application with local LLM support.

**Last Updated**: December 2025
**Status**: Production Ready

---

## Completed Phases

### Phase 1: Core Infrastructure (COMPLETED)
- FastAPI migration from Flask
- Database setup with SQLAlchemy (SQLite)
- Authentication system (Clerk-based)
- Basic routing and template system
- Character management with JSON cards
- LLM integration with Ollama

### Phase 2: Chat System (COMPLETED)
- Real-time chat interface
- Message persistence in database
- Character-specific responses
- Privacy controls for local processing

### Phase 3: Personality Framework (COMPLETED)
- Comprehensive personality schema
- XML-based personality definitions
- Character cards with visual traits
- Validation and parsing system

### Phase 4: Advanced Features (COMPLETED)
- Memory system with SQLite backend
- Conversation history tracking
- Character usage statistics
- Privacy controls

### Phase 5: Personality Editing System (COMPLETED)
- Creation and editing interfaces
- AI-powered trait suggestions
- Communication style sliders
- Backstory integration
- Category system with warnings
- Dynamic trait suggestions
- System prompt generation

### Phase 6: LLM Provider Integration (COMPLETED)
- User settings page
- Multi-provider support (Ollama, OpenAI, Anthropic, OpenRouter)
- API key management
- Privacy mode selection
- Connection testing
- Dynamic model discovery

### Phase 7: Simplified Context System (COMPLETED)
- SettingService (world/location/time)
- BackstoryService with semantic embeddings
- FactExtractionService (auto-learn facts)
- PromptSanitizer (security layer)
- EnhancedContextService integration
- Token budget allocation

### Phase 8: Authentication Migration (COMPLETED)
- Clerk authentication integration
- Google SSO support
- JWT verification with JWKS
- 60-second token TTL handling
- Proactive session refresh (45s interval)
- authFetch() with 401 retry logic

### Phase 9: UI/UX Improvements (COMPLETED)
- Luxury landing page (Aura.build inspired)
- Dark theme default (#050505 obsidian)
- Frosted glass styling
- Responsive chat interface
- Memory management UI
- Settings consolidation

### Phase 10: Chat History & Export (COMPLETED)
- Persona dropdown at top of sidebar
- "New Chat" button
- Conversation history grouped by date
- Delete conversations with confirmation modal
- LLM-generated titles (async, 3-6 words)
- Export to PDF, Word, Markdown, Plain text
- Export AI-generated summaries

### Phase 11: Per-Persona Tracking (COMPLETED)
- Goals with progress tracking (numeric targets, progress bars)
- Habits with streak tracking (daily completion, streak counts)
- Todos with priority levels
- Sidebar sections for Goals, Habits, Todos
- Tracking context injected into chat
- Interactive tracking cards in chat messages

### Phase 12: Web Search Integration (COMPLETED)
- Privacy-focused DuckDuckGo integration (no API key)
- Per-persona capability toggle
- Automatic search intent detection
- Manual search button in chat
- Clickable source links in responses
- Search results context injection

### Phase 13: Google Calendar + Tasks (COMPLETED)
- OAuth2 flow for Google account connection
- Two-way sync with Google Tasks
- Per-persona sync configuration
- Calendar event reading (multi-calendar)
- Calendar event creation from natural language
- Last-write-wins conflict resolution
- Timezone-aware event creation

---

## Current Phase

### Phase 14: Polish & Quality (IN PROGRESS)
- [ ] Dashboard redesign (match landing page aesthetic)
- [ ] Comprehensive tests for context services
- [ ] UX polish - animations, micro-interactions
- [ ] Code optimization and cleanup
- [ ] Template consolidation

---

## Success Metrics (Achieved)

- [x] 100% local processing capability (Ollama default)
- [x] Support for 4+ LLM providers
- [x] Sub-2 second response times (provider dependent)
- [x] Clerk authentication working
- [x] Simplified context system operational
- [x] Security layer (PromptSanitizer) active
- [x] Google Calendar/Tasks integration
- [x] Web search capability
- [x] Goal/habit/todo tracking

---

## Architecture

```
src/miachat/
├── api/
│   ├── main.py                    # FastAPI entry point
│   ├── core/
│   │   ├── clerk_auth.py          # Clerk JWT authentication
│   │   ├── llm_client.py          # Multi-provider LLM client
│   │   ├── backstory_service.py   # Semantic backstory retrieval
│   │   ├── fact_extraction_service.py
│   │   ├── setting_service.py     # World/location/time
│   │   ├── enhanced_context_service.py
│   │   ├── conversation_service.py
│   │   ├── tracking_service.py    # Goals, habits, todos
│   │   ├── web_search_service.py  # DuckDuckGo integration
│   │   ├── google_auth_service.py
│   │   ├── google_calendar_service.py
│   │   ├── google_tasks_service.py
│   │   ├── google_sync_service.py
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

*For development setup and debugging, see [DEV.md](../DEV.md)*
*For progress tracking, see [progress.md](../tracking/progress.md)*
