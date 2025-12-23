# MinouChat UX Enhancement Plan

## Summary

Phased feature rollout to improve chat experience and enable persona capabilities.

## Current Status

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Chat History Library | ✅ COMPLETE |
| 2a | Export Functionality | ✅ COMPLETE |
| 2b | Per-Persona Tracking | ✅ COMPLETE |
| 3 | Interactive Documents | ✅ COMPLETE |
| 4 | Web Search (DuckDuckGo) | ✅ COMPLETE |
| 5 | Google Calendar + Tasks | ✅ COMPLETE |

---

## Completed Features

### Phase 1: Chat History Library ✅
- Persona dropdown at top of sidebar
- "New Chat" button
- Conversation history grouped by date (Today, Yesterday, Previous 7 Days, Older)
- Delete conversations with confirmation modal
- LLM-generated titles (async, 3-6 words)
- Auto-refresh sidebar after title generation

### Phase 2a: Export Functionality ✅
- Export dropdown button in chat header
- Export conversation to PDF, Word (.docx), Markdown, Plain text
- Export AI-generated summary to PDF or Word
- Streaming file downloads
- Files created:
  - `src/miachat/api/core/export_service.py` - Format conversion (PDF via reportlab, DOCX via python-docx)
  - `src/miachat/api/routes/export.py` - `/api/export/conversation/{session_id}`, `/api/export/summary/{session_id}`

### Phase 2b: Per-Persona Tracking ✅
- Goals with progress tracking (numeric targets, progress bars)
- Habits with streak tracking (daily completion, streak counts)
- Sidebar sections for Goals and Habits (visible for all personas)
- Tracking context injected into chat so persona is aware of user's goals/habits
- Database models: PersonaGoal, GoalProgressLog, PersonaHabit, HabitCompletion
- Files created:
  - `src/miachat/api/core/tracking_service.py` - CRUD and context generation
  - `src/miachat/api/routes/tracking.py` - REST API endpoints
- Files modified:
  - `src/miachat/database/models.py` - New tracking models
  - `src/miachat/api/core/enhanced_context_service.py` - Tracking context injection
  - `src/miachat/api/templates/chat/index.html` - Sidebar UI panels

### Phase 3: Interactive Documents ✅
- Persona auto-extracts goals and habits from chat messages using LLM
- Interactive tracking cards displayed in chat messages
- Cards show progress (goals), streaks (habits), or completion status (todos)
- Card actions: Complete todo, Mark habit done, Log goal progress, View in sidebar
- Real-time sidebar refresh after card actions
- Trigger patterns for goal extraction (e.g., "I want to save $5000", "let's set a goal")
- Trigger patterns for habit extraction (e.g., "I want to start a habit of meditating daily")
- Files modified:
  - `src/miachat/api/core/sidebar_extraction_service.py` - Goal/habit trigger patterns and LLM extraction
  - `src/miachat/api/main.py` - tracking_cards field in ChatResponse
  - `src/miachat/api/templates/chat/index.html` - Card CSS, rendering functions, event handlers

### Phase 4: Web Search (DuckDuckGo) ✅
- Privacy-focused web search using DuckDuckGo (no API key needed)
- Search capability enabled per-persona via `capabilities.web_search` field
- Automatic search intent detection in messages (e.g., "search for...", "what's the latest on...")
- Manual search button in chat input (visible only for personas with capability)
- Search results displayed in dropdown panel with clickable links
- Search results automatically included in chat context for LLM responses
- Default capabilities by category:
  - Assistant: web_search=true, calendar_access=true, goal_tracking=true
  - Coach: web_search=false, calendar_access=true, goal_tracking=true
  - Friend: all capabilities=false
  - Creative: all capabilities=false
- Files created:
  - `src/miachat/api/core/web_search_service.py` - DuckDuckGo integration
  - `src/miachat/api/routes/web_search.py` - REST API endpoints
- Files modified:
  - `src/miachat/api/core/enhanced_context_service.py` - Web search context injection
  - `src/miachat/api/main.py` - Router registration
  - `src/miachat/api/templates/chat/index.html` - Search button, results panel, JavaScript
  - `character_cards/*.json` - Added capabilities field
  - `requirements.txt` - Added ddgs>=9.0.0

### Phase 5: Google Calendar + Tasks ✅
- Two-way sync between MinouChat todos and Google Tasks
- Per-persona sync control (user chooses which personas sync)
- Separate Google Tasks list per synced persona (e.g., "MinouChat - Coach")
- Google Calendar read access with events injected into chat context
- Calendar event creation from chat
- OAuth2 flow with token refresh
- Last-write-wins conflict resolution for two-way sync
- Database models:
  - `GoogleCredentials` - OAuth2 tokens per user
  - `PersonaGoogleSyncConfig` - Per-persona sync settings
  - `TodoGoogleTaskMapping` - Maps todos to Google Tasks for sync tracking
- Files created:
  - `src/miachat/api/core/google_auth_service.py` - OAuth2 flow, token management
  - `src/miachat/api/core/google_tasks_service.py` - Google Tasks API operations
  - `src/miachat/api/core/google_sync_service.py` - Two-way sync logic
  - `src/miachat/api/core/google_calendar_service.py` - Calendar read/write
  - `src/miachat/api/routes/google_auth.py` - OAuth endpoints
  - `src/miachat/api/routes/google_tasks.py` - Sync config endpoints
  - `src/miachat/api/routes/google_calendar.py` - Calendar endpoints
- Files modified:
  - `src/miachat/database/models.py` - 3 new models
  - `src/miachat/api/core/tracking_service.py` - Sync hooks on todo CRUD
  - `src/miachat/api/core/enhanced_context_service.py` - Calendar context injection
  - `src/miachat/api/templates/settings.html` - Google connection UI
  - `src/miachat/api/main.py` - Router registration
  - `requirements.txt` - Added google-auth, google-auth-oauthlib, google-api-python-client
- Environment variables required:
  - `GOOGLE_CLIENT_ID` - OAuth client ID
  - `GOOGLE_CLIENT_SECRET` - OAuth client secret
  - `GOOGLE_REDIRECT_URI` - OAuth callback URL

---

## Feature 2a: Export Functionality (COMPLETE)

### Overview
Enable personas to generate exportable documents from chat conversations and artifacts.

### Export Formats
| Format | Library | Use Case |
|--------|---------|----------|
| Word (.docx) | `python-docx` | Formal reports, editable documents |
| PDF | `reportlab` or `weasyprint` | Final documents, sharing |
| Markdown (.md) | Built-in | Technical docs, GitHub-friendly |
| Plain text (.txt) | Built-in | Universal, simple notes |

### What Can Be Exported
1. **Chat transcripts** - Full conversation or selected messages
2. **Document artifacts** - Existing generated content
3. **Conversation summaries** - LLM-generated summary of chat

### Files to Create
- `src/miachat/api/core/export_service.py` - Format conversion logic
- `src/miachat/api/routes/export.py` - Export endpoints

### Files to Modify
- `src/miachat/api/main.py` - Register export router
- `src/miachat/api/templates/chat/index.html` - Add export button/menu
- `requirements.txt` - Add `python-docx`, `reportlab`

### New Endpoints
```
POST /api/export/conversation/{session_id}
  Body: { "format": "pdf|docx|md|txt", "include_system": false }
  Returns: File download

POST /api/export/artifact/{artifact_id}
  Body: { "format": "pdf|docx|md|txt" }
  Returns: File download

POST /api/export/summary/{session_id}
  Body: { "format": "pdf|docx|md|txt" }
  Returns: LLM-generated summary as file
```

### UI Integration
- Export dropdown button in chat header (near persona name)
- Options: "Export as PDF", "Export as Word", "Export as Markdown", "Export as Text"
- Optional: "Export Summary" generates LLM summary first

### Implementation Steps
1. Add `python-docx` and `reportlab` to requirements
2. Create `export_service.py` with format converters
3. Create `/api/export/` endpoints
4. Add export button to chat UI
5. Test all format outputs

---

## Feature 1: Chat History Library (ChatGPT-style) ✅ COMPLETE

### Design
- Dropdown list of personas at TOP of sidebar
- "New Chat" button below dropdown
- **Interactive Documents section** (between New Chat and History):
  - To-dos (quick access to persona's todo list)
  - Goals (progress overview)
  - Habit Tracker (today's habits)
  - This Week's Schedule (calendar summary)
  - Each item opens a panel/modal for full interaction
- List of recent conversations for SELECTED persona below
- Conversations grouped by date (Today, Yesterday, Previous 7 Days, etc.)
- Delete button on hover with confirmation modal
- Auto-generated titles from first message

### Sidebar Structure (Top to Bottom)
```
┌─────────────────────────┐
│ [Persona Dropdown ▼]    │
├─────────────────────────┤
│ [+ New Chat]            │
├─────────────────────────┤
│ 📋 To-dos          (3)  │  ← Interactive
│ 🎯 Goals           (2)  │    Documents
│ ✅ Habits          (5)  │    Section
│ 📅 This Week            │
├─────────────────────────┤
│ Today                   │
│   Chat about goals...   │  ← Conversation
│   Morning check-in...   │    History
│ Yesterday               │
│   Weekly review...      │
└─────────────────────────┘
```

### Files to Modify
- `src/miachat/api/templates/chat/index.html` - Sidebar redesign
- `src/miachat/api/core/conversation_service.py` - Add methods
- `src/miachat/api/main.py` - New endpoints

### New Endpoints
```
GET  /api/conversations/character/{character_id}  - List conversations for persona
DELETE /api/conversations/{session_id}            - Delete conversation
GET  /api/tracking/summary/{character_id}         - Get counts for sidebar badges
```

### Interactive Documents Section
Each item in the sidebar shows a count badge and opens a panel:
- **To-dos**: Shows count of incomplete items → Opens todo list panel
- **Goals**: Shows count of active goals → Opens goals panel with progress bars
- **Habits**: Shows count of habits due today → Opens habit tracker
- **This Week**: No badge → Opens weekly calendar view (from Google Calendar if connected)

### Implementation Steps
1. Add `get_conversations_for_character()` to ConversationService
2. Add `delete_conversation()` method with cascade delete
3. Add `auto_generate_title()` using first user message
4. Redesign sidebar HTML (dropdown + history list)
5. Add CSS for conversation history items
6. Add JavaScript for dynamic loading and delete

---

## Feature 2: Google Calendar Integration

### Design
- On/off toggle in Settings page
- OAuth2 flow for Google Calendar API
- Read upcoming events + Create new events (no modify/delete)
- Persona can reference calendar in responses

### Files to Create
- `src/miachat/api/core/calendar_service.py`
- `src/miachat/api/routes/calendar.py`

### Files to Modify
- `src/miachat/database/models.py` - Add GoogleCalendarCredentials model
- `src/miachat/api/templates/settings.html` - Add calendar section
- `src/miachat/api/main.py` - Register router
- `requirements.txt` - Add `google-auth`, `google-api-python-client`

### Database Model
```python
class GoogleCalendarCredentials(Base):
    __tablename__ = 'google_calendar_credentials'
    id, user_id, access_token, refresh_token, token_expiry, is_enabled, scopes
```

### New Endpoints
```
GET  /api/calendar/auth/url        - Get OAuth URL
GET  /api/calendar/auth/callback   - OAuth callback handler
POST /api/calendar/disconnect      - Revoke access
GET  /api/calendar/status          - Check connection status
GET  /api/calendar/events          - Get upcoming events
POST /api/calendar/events          - Create event
```

---

## Feature 3: Web Search (DuckDuckGo)

### Design
- Privacy-focused using DuckDuckGo (no API key needed)
- Only for personas with `web_search` capability
- Results included in chat context with citations
- Links open in new tab

### Files to Create
- `src/miachat/api/core/web_search_service.py`
- `src/miachat/api/routes/web_search.py`

### Files to Modify
- `src/miachat/api/core/enhanced_context_service.py` - Add search results to context
- `src/miachat/api/main.py` - Register router
- `requirements.txt` - Add `duckduckgo-search`
- Character JSON files - Add `capabilities` field

### Character Schema Update
```json
{
  "capabilities": {
    "web_search": true,
    "calendar_access": true,
    "goal_tracking": true
  }
}
```

### Default Capabilities by Category
- **Assistant**: web_search, calendar_access, goal_tracking
- **Coach**: goal_tracking, calendar_access
- **Friend**: (none)

---

## Feature 4: Per-Persona Tracking

### Design
- Goals with progress tracking (numeric targets, due dates)
- To-do lists with completion status
- Habits with streak tracking
- Tracking context injected into chat so persona is aware
- Collapsible panel in chat or dedicated tracking page

### Files to Create
- `src/miachat/api/core/tracking_service.py`
- `src/miachat/api/routes/tracking.py`

### Files to Modify
- `src/miachat/database/models.py` - Add 4 models
- `src/miachat/api/core/enhanced_context_service.py` - Add tracking context
- `src/miachat/api/templates/chat/index.html` - Add tracking panel toggle
- `src/miachat/api/main.py` - Register router

### Database Models
```python
PersonaGoal: id, user_id, character_id, title, description, target_value,
             current_value, unit, target_date, status, priority, category

GoalProgressLog: id, goal_id, value_change, note, logged_at

PersonaTodo: id, user_id, character_id, title, description, priority,
             due_date, is_completed, completed_at, parent_goal_id

PersonaHabit: id, user_id, character_id, title, description, frequency,
              frequency_days, target_per_period, current_streak, longest_streak

HabitCompletion: id, habit_id, completed_at, note
```

### New Endpoints
```
# Goals
GET/POST   /api/tracking/goals
PUT/DELETE /api/tracking/goals/{id}
POST       /api/tracking/goals/{id}/progress

# Todos
GET/POST   /api/tracking/todos
PUT/DELETE /api/tracking/todos/{id}
POST       /api/tracking/todos/{id}/toggle

# Habits
GET/POST   /api/tracking/habits
PUT/DELETE /api/tracking/habits/{id}
POST       /api/tracking/habits/{id}/complete
GET        /api/tracking/habits/{id}/stats
```

---

## Implementation Phases

### Phase 1: Chat History Library ✅ COMPLETE
- Core UX improvement, no external dependencies
- Foundation for other features

### Phase 2a: Export Functionality 🔜 NEXT
- Export chat transcripts to Word, PDF, Markdown, Plain text
- Export document artifacts
- No new database models needed
- Quick win with immediate user value

### Phase 2b: Per-Persona Tracking
- Goals with progress tracking (numeric targets, due dates)
- To-do lists with completion status
- Habits with streak tracking
- Database models foundation for interactive documents
- Context injection into chat

### Phase 3: Interactive Documents
- Persona-generated habit tracking documents
- Goals with mini-step breakdowns
- Requires Phase 2b tracking models

### Phase 4: Web Search Integration
- DuckDuckGo integration (no API key needed)
- Only for personas with `web_search` capability
- Quick standalone feature

### Phase 5: Google Calendar + Reminders
- OAuth2 flow for Google Calendar API
- Read upcoming events + Create new events
- Reminders that sync with Google Reminders
- Requires Google Cloud Console setup

---

## Dependencies to Add

```
# requirements.txt additions
duckduckgo-search>=5.0.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
```

---

## Critical Files Summary

| File | Changes |
|------|---------|
| `src/miachat/database/models.py` | Add 6 new models |
| `src/miachat/api/templates/chat/index.html` | Major sidebar redesign |
| `src/miachat/api/core/conversation_service.py` | Per-character queries, delete |
| `src/miachat/api/core/enhanced_context_service.py` | Tracking + calendar + search context |
| `src/miachat/api/main.py` | Register 3 new routers |
| `src/miachat/api/templates/settings.html` | Calendar toggle section |
| `character_cards/*.json` | Add capabilities field |

---

## Roadmap Update

Add to `docs/implementation/roadmap.md`:

```markdown
### Phase 10: UX Enhancements
- [x] Chat History Library (ChatGPT-style sidebar) ✅
- [x] Conversation delete functionality ✅
- [x] LLM-generated conversation titles ✅

### Phase 11: Export & Tracking
- [ ] Export to Word, PDF, Markdown, Plain text
- [ ] Per-persona tracking (goals, habits, to-dos)
- [ ] Context injection into chat

### Phase 12: Interactive Documents
- [ ] Persona-generated habit tracking documents
- [ ] Goals with mini-step breakdowns

### Phase 13: External Integrations
- [ ] Web search for assistant personas (DuckDuckGo)
- [ ] Google Calendar integration (read + create)
- [ ] Google Reminders sync
- [ ] Capabilities schema for character JSON
```

---

## Feature 5: Persona Document Generation (BACKLOG)

### Interactive Documents
Personas can create and manage interactive documents that sync with external services:

- **Reminders**: Create reminders during chat that sync with Google Reminders
- **Habit Trackers**: Generate habit tracking documents with daily/weekly check-ins
- **Goals with Mini-steps**: Break down goals into actionable steps with progress tracking

### Export Documents
Personas can generate documents for export in multiple formats:

| Format | Use Case |
|--------|----------|
| Word (.docx) | Formal reports, meeting notes |
| PDF | Final documents, shareable reports |
| Markdown (.md) | Technical docs, notes for developers |
| Plain text (.txt) | Simple notes, universal compatibility |

### Implementation Notes
- Leverage existing artifacts system (`/api/artifacts/`)
- Add format conversion using `python-docx`, `reportlab`, `markdown`
- Interactive documents stored in database with sync status
- Export triggered via chat command or UI button
