# MinouChat Development Plan

## Summary

All major feature phases are complete. Current focus is on polish, testing, and optimization.

## Status Overview

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Chat History Library | COMPLETE |
| 2a | Export Functionality | COMPLETE |
| 2b | Per-Persona Tracking | COMPLETE |
| 3 | Interactive Documents | COMPLETE |
| 4 | Web Search (DuckDuckGo) | COMPLETE |
| 5 | Google Calendar + Tasks | COMPLETE |
| 6 | Dashboard Redesign | COMPLETE |
| 7 | Memory & Help System | COMPLETE |

---

## Phase 7: Memory & Help System (COMPLETE)

### 7.1 Help/FAQ Page
Create a user documentation page explaining how MinouChat works.

**Content Sections:**
- How Memory Works (3 layers: User Profile > Backstory > Learned Facts)
- Learned Facts (auto-extraction, how to correct, how to view)
- Best Practices (building memory, controlling memory, personalizing personas)
- Per-Persona vs Global facts
- Privacy (local LLM processing)
- FAQ

**Files:**
- CREATE: `templates/help.html`
- MODIFY: `core/templates.py` (add mapping)
- MODIFY: `main.py` (add /help route, logged-in only)

---

### 7.2 Memory Page Redesign
Improve the memory page UI with luxury styling and better UX.

**Changes:**
- Add page description: "View, edit, and manage what your personas remember about you"
- Add "New Fact" button with modal form
- Cleaner layout with better spacing
- Smooth animations on hover/edit
- Better empty state

**File:** `templates/memory.html`

---

### 7.3 Context Visualization
Show users what the persona "knows" during a conversation.

**Implementation:**
- Add "What I Know" collapsible panel in chat sidebar
- Display: facts used, setting, backstory chunks, documents
- Modify chat response to include `context_used` field

**Files:**
- MODIFY: `templates/chat/index.html` (add panel)
- MODIFY: `main.py` (return context_used in ChatResponse)

---

### 7.4 Improved Correction Patterns
Add flexible patterns for positive fact corrections.

**Current Gap:** "Actually, I moved to Portland" doesn't trigger correction

**New Patterns:**
```python
r'\bactually,?\s+i\s+(live|work|am|moved|have)\b'
r'\bno,?\s+i\s+(live|work|am|have)\b'
r'\bwell,?\s+actually,?\s+i\b'
r'\bi\s+should\s+(mention|say|clarify)\b'
r'\bto\s+be\s+(clear|accurate)\b'
```

**File:** `core/fact_extraction_service.py`

---

## Implementation Order

1. [ ] Help Page (standalone)
2. [ ] Memory Page Redesign + Add Fact button
3. [ ] Context Visualization in chat sidebar
4. [ ] Correction Patterns

---

## Future: Comprehensive Tests
Add tests for core context services:
- `setting_service.py`
- `backstory_service.py`
- `fact_extraction_service.py`
- `tracking_service.py`
- `enhanced_context_service.py`

---

## Completed Features Reference

### Chat History Library
- Persona dropdown at top of sidebar
- "New Chat" button
- Conversation history grouped by date (Today, Yesterday, Previous 7 Days, Older)
- Delete conversations with confirmation modal
- LLM-generated titles (async, 3-6 words)

### Export Functionality
- Export dropdown button in chat header
- Export conversation to PDF, Word (.docx), Markdown, Plain text
- Export AI-generated summary to PDF or Word

### Per-Persona Tracking
- Goals with progress tracking (numeric targets, progress bars)
- Habits with streak tracking (daily completion, streak counts)
- Todos with priority and due dates
- Sidebar sections visible for all personas
- Tracking context injected into chat

### Interactive Documents
- Persona auto-extracts goals and habits from chat messages using LLM
- Interactive tracking cards displayed in chat messages
- Card actions: Complete todo, Mark habit done, Log goal progress

### Web Search (DuckDuckGo)
- Privacy-focused (no API key needed)
- Per-persona capability toggle
- Search button in chat input
- Clickable source links
- Search results in chat context

### Google Calendar + Tasks
- OAuth2 flow for Google account connection
- Two-way sync with Google Tasks (last-write-wins)
- Per-persona sync configuration
- Calendar event creation from natural language
- Timezone-aware event creation

---

## Architecture

```
src/miachat/api/
├── core/
│   ├── setting_service.py          # World/location/time
│   ├── backstory_service.py        # Semantic backstory retrieval
│   ├── fact_extraction_service.py  # Auto-learn facts from chat
│   ├── tracking_service.py         # Goals, habits, todos
│   ├── web_search_service.py       # DuckDuckGo integration
│   ├── google_auth_service.py      # OAuth2 flow
│   ├── google_calendar_service.py  # Calendar read/write
│   ├── google_tasks_service.py     # Tasks CRUD
│   ├── google_sync_service.py      # Two-way sync logic
│   ├── export_service.py           # PDF/DOCX/MD export
│   ├── sidebar_extraction_service.py
│   └── enhanced_context_service.py # Combines all context
├── routes/
│   ├── tracking.py
│   ├── export.py
│   ├── web_search.py
│   ├── google_auth.py
│   ├── google_calendar.py
│   └── google_tasks.py
└── templates/
    ├── landing.html        # Luxury aesthetic (reference)
    ├── dashboard.html      # Needs redesign
    ├── chat/index.html
    ├── settings.html
    └── ...
```
