# MiaAI Project Documentation

## Project Overview
This documentation tracks the development and implementation of the MiaAI system, a sophisticated AI personality application capable of sustained, meaningful dialogue.

## Documentation Structure
- [System Design](architecture/system-design.md): Architecture, design principles, and requirements
- [Implementation Roadmap](implementation/roadmap.md): Phase-by-phase plan, milestones, and implementation details
- [Progress Tracking](tracking/progress.md): Ongoing progress, completed and pending features, blockers, next actions
- [Personality Framework](../personality_framework.md): In-depth technical documentation for the personality system and API

## Project Status & Next Steps
**Last updated: 2024-06-11**

### Immediate Next Steps
- [ ] Restore or scaffold missing code files (e.g., `core/conversation.py`)
- [ ] Add/restore any missing templates (dashboard)
- [ ] Initialize the database (`python -m src.miachat.cli init_database`)
- [ ] Add automated tests for routes and models
- [ ] Add Dockerfile and .dockerignore for containerization
- [ ] Update documentation as features are added

### In Progress
- [ ] Review and polish UI/UX
- [ ] Expand personality framework

### Completed
- [x] Fix dependency and environment issues
- [x] Restore and test web routes
- [x] Static image loading

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

## What Might Be Missing
- The `/personality` UI and API endpoints must be wired up in your Flask app.
- If you don't see the "Personality Customization" page, the route may not be enabled.

## Next Steps
- If you want to use the UI, try visiting `/personality` in your browser.
- If you want to integrate XML loading for new characters, call the loader in your backend.
- If you want to use the API, use the endpoints described above.
- If you need help wiring up the UI or endpoints, see `docs/personality_framework.md` or ask for further guidance. 