# Improve Coach (Sage) Conversation Experience

## Overview

Two improvements for the Sage coaching persona:
1. **Fix life areas sidebar not updating** when user provides ratings in conversation
2. **Improve question delivery** - shorter, grouped questions (2-3 per topic) instead of overwhelming paragraphs

---

## Problem Analysis

### Issue 1: Life Areas Not Updating from Conversation

**Current behavior:** User said "Career=9, Finances=6, Health=7..." but sidebar didn't update.

**Root cause:** The extraction regex patterns in `sidebar_extraction_service.py` expect phrases like:
- "my career is a 7"
- "I rate my health at 8/10"

They don't match the format "Career=9, Finances=6" that users naturally provide when listing multiple areas.

### Issue 2: Coach Responses Too Long/Overwhelming

**Current behavior:** Sage asks 5-6 questions in one response, making it hard to track.

**User preference:** 2-3 related questions grouped by topic, with frameworks used naturally (not explained).

---

## Implementation Plan

### Step 1: Improve Life Areas Extraction Patterns

**File:** `src/miachat/api/core/sidebar_extraction_service.py`

Add new regex patterns to handle list-style ratings:

```python
# Add to LIFE_AREA_PATTERNS list:
r'(?:career|work)\s*[=:]\s*(\d+)',
r'(?:finances?|money)\s*[=:]\s*(\d+)',
r'(?:health|fitness)\s*[=:]\s*(\d+)',
r'(?:relationships?)\s*[=:]\s*(\d+)',
r'(?:family)\s*[=:]\s*(\d+)',
r'(?:friendships?|friends)\s*[=:]\s*(\d+)',
r'(?:growth|personal\s*growth)\s*[=:]\s*(\d+)',
r'(?:fun|recreation)\s*[=:]\s*(\d+)',
r'(?:environment|home)\s*[=:]\s*(\d+)',
r'(?:contribution|giving)\s*[=:]\s*(\d+)',
```

Also update the LLM extraction prompt to explicitly handle comma-separated lists.

### Step 2: Update Sage System Prompt for Better Question Delivery

**File:** `character_cards/22221df6-b8ec-424b-ab94-65fd75837baa.json`

Add a RESPONSE STYLE section to the system prompt:

```
## RESPONSE STYLE GUIDELINES

CRITICAL - Follow these rules for every response:

1. **Question Limit**: Ask 2-3 related questions maximum per response
2. **Question Length**: Keep each question under 25 words
3. **Group by Topic**: All questions in one response should explore the same aspect
4. **Wait for Answers**: Don't ask follow-up questions until the user responds
5. **Framework Usage**: Use coaching frameworks internally - don't explain them unless asked
6. **No Preamble**: Skip lengthy introductions - get to the questions quickly

WRONG (too many questions):
"What does success look like? How do you define fulfillment? What are your core values? When do you feel most alive? What would you do differently?"

RIGHT (grouped, focused):
"Let's explore what fulfillment means to you. When you imagine your ideal day, what are you doing? Who are you with?"
```

### Step 3: Verify Sidebar Refresh After Extraction

**File:** `src/miachat/api/main.py` (chat endpoint)

Ensure extraction results are included in response so frontend can refresh sidebar.

**File:** `src/miachat/api/templates/chat/index.html`

Verify `loadLifeAreas()` is called after receiving extraction results in chat response.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/miachat/api/core/sidebar_extraction_service.py` | Add list-style rating patterns |
| `character_cards/22221df6-b8ec-424b-ab94-65fd75837baa.json` | Add response style guidelines to system prompt |
| `src/miachat/api/templates/chat/index.html` | Verify sidebar refresh after extraction (if needed) |

---

## Testing

1. Chat with Sage, provide ratings in format: "Career=9, Health=7, Finances=6"
2. Verify sidebar updates with new scores
3. Verify Sage asks 2-3 questions per response, not 5-6
4. Verify frameworks are used naturally without explanation
