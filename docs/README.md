# MiaAI Project Documentation

## Project Overview
This documentation tracks the development and implementation of the MiaAI system, a sophisticated AI personality application capable of sustained, meaningful dialogue with advanced memory and context awareness.

## Documentation Structure
- [System Design](architecture/system-design.md): Architecture, design principles, and requirements
- [Implementation Roadmap](implementation/roadmap.md): Phase-by-phase plan, milestones, and implementation details
- [Progress Tracking](tracking/progress.md): Ongoing progress, completed and pending features, blockers, next actions
- [Personality Framework](../personality_framework.md): In-depth technical documentation for the personality system and API

## Project Status & Next Steps
**Last updated: 2025-01-15**

### Current Status
**Phase 1: Core Personality Framework** ✅ **COMPLETED**
**Phase 2: Memory System** ✅ **COMPLETED**
**Phase 3: API and Web Interface** 🔄 **IN PROGRESS**

### Immediate Next Steps
- [ ] Add user authentication and multi-user support
- [ ] Expand automated tests for new memory endpoints
- [ ] Polish UI/UX and add conversation history display
- [ ] Implement character evolution system
- [ ] Add user-character conflict resolution
- [ ] Update documentation as new features are added

### In Progress
- [ ] User authentication and authorization
- [ ] WebSocket support for real-time chat
- [ ] Real-time personality testing

### Completed ✅
- [x] Fix dependency and environment issues
- [x] Restore and test web routes
- [x] Static image loading
- [x] FastAPI migration for all main routes
- [x] Ollama/llama3:8b integration for local LLM
- [x] Web UI connected to real API (no hardcoded responses)
- [x] Conversation history and persistence
- [x] Advanced memory/context features
- [x] Memory storage implementation
- [x] Context management with configurable window
- [x] Memory retrieval and search functionality
- [x] Memory prioritization and cleanup
- [x] Comprehensive API endpoints for all functionality
- [x] Complete testing suite for all components

---

## Quick Links
- [System Design](architecture/system-design.md)
- [Implementation Roadmap](implementation/roadmap.md)
- [Progress Tracking](tracking/progress.md)
- [Personality Framework](../personality_framework.md)

# MiaChat Personality Framework

## What Exists

- **XML Personality Files**
  - Example: `config/personalities/mia.xml`
  - Define traits, backstory, knowledge, and style for a character.
- **Loader Code**
  - `src/miachat/personality/loader.py`
  - Loads and parses XML personality files into Python objects.
- **Personality Analysis**
  - `app/core/personality.py`
  - Function `analyze_character_description` uses an LLM to generate traits, style, knowledge, and backstory from a description.
- **API Endpoints**
  - See `docs/personality_framework.md`
  - Endpoints like `/api/characters/analyze-character` and `/api/characters/save-personality` for analyzing and saving personalities.
- **UI for Analysis**
  - `app/templates/personality.html`
  - Textarea and button for analyzing a character description, and a form for editing traits, style, knowledge, and backstory.

## Advanced Features Completed

### Memory and Context System
- **MemoryService**: Intelligent context retrieval with configurable window (default: 10 messages)
- **Context-Aware Responses**: LLM responses enhanced with relevant conversation history
- **Keyword Search**: Find relevant historical messages using intelligent search
- **Conversation Persistence**: Full database integration with SQLAlchemy ORM
- **API Endpoints**: Complete REST API for memory operations and conversation management

### Conversation Management
- **Conversation Service**: Bridges character manager with database models
- **Message Persistence**: All chat messages stored with proper transaction handling
- **Conversation Lifecycle**: Start, end, and delete conversations with proper cleanup
- **History Retrieval**: Access to complete conversation history with search capabilities

## How to Get It Working

### A. Use the AI Generator from the UI
1. Go to `/personality` in your app.
2. You should see a page with a "Describe your character" textarea and "Analyze Character" button.
3. Enter a description and click "Analyze Character".
4. The AI will generate traits, style, knowledge, and backstory, and fill the form.
5. Edit and save the generated personality using the form.

### B. Use the XML Loader for Default Characters
- The loader in `src/miachat/personality/loader.py` can load XML files like `mia.xml` and convert them to character objects.
- You can call this loader in your backend to initialize or update characters from XML.

### C. Use the API Directly
- `POST` to `/api/characters/analyze-character` with a description to get AI-generated traits.
- `POST` to `/api/characters/save-personality` to save a new personality.
- `GET` to `/api/conversations/{character_id}/context` to retrieve conversation context.
- `GET` to `/api/conversations/{character_id}/search` to search conversation history.

## What Might Be Missing
- The `/personality` UI and API endpoints must be wired up in your FastAPI app.
- If you don't see the "Personality Customization" page, the route may not be enabled.

## Next Steps
- If you want to use the UI, try visiting `/personality` in your browser.
- If you want to integrate XML loading for new characters, call the loader in your backend.
- If you want to use the API, use the endpoints described above.
- If you need help wiring up the UI or endpoints, see `docs/personality_framework.md` or ask for further guidance. 