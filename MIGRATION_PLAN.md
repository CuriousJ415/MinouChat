# MiaChat Database Consolidation - Migration Plan

**Created:** November 12, 2025
**Objective:** Consolidate duplicate model definitions and establish single source of truth
**Estimated Time:** 2-4 hours
**Risk Level:** Medium (data migration involved)

---

## 📊 Audit Results

### Files Using Duplicate Models

Only **2 files** currently import from the problematic `api/models/chat.py`:

1. `src/miachat/api/core/conversation_service.py`
   ```python
   from ..models.chat import Conversation, Message
   ```

2. `src/miachat/api/core/memory_service.py`
   ```python
   from ..models.chat import Conversation, Message
   ```

### Files Using Canonical Models

Need to check which files use `database/models.py`:
- Likely: `database/config.py`, `database/init_db.py`
- Unknown: Other services may be using the database models

### Model Differences

| Field | database/models.py | api/models/chat.py | Action |
|-------|-------------------|-------------------|--------|
| **Conversation.personality_id** | FK to personalities | N/A | Keep |
| **Conversation.persona_id** | N/A | Integer, no FK | Remove |
| **Conversation.title** | N/A | String | **Add to canonical** |
| **Conversation.updated_at** | N/A | DateTime | **Add to canonical** |
| **Message.role** | Has it | Has it | Keep |
| **Message.file_attachments** | May be missing | Has it | **Check and add if needed** |

---

## 🎯 Migration Strategy

### Phase 1: Model Consolidation (High Priority)

#### Step 1.1: Update Canonical Models
**File:** `src/miachat/database/models.py`

**Changes Needed:**
1. Add missing fields to `Conversation` class:
   - `title` field
   - `updated_at` field
2. Verify `Message` has all needed fields:
   - `role` field
   - `file_attachments` field

**Why:** The chat.py version has useful fields we want to keep.

#### Step 1.2: Create Database Migration
**File:** Create new Alembic migration script

**Purpose:** Add new columns to existing tables without data loss

```python
# Migration script will:
def upgrade():
    # Add title column to conversations table
    op.add_column('conversations',
        sa.Column('title', sa.String(), nullable=True))

    # Add updated_at column to conversations table
    op.add_column('conversations',
        sa.Column('updated_at', sa.DateTime(), nullable=True))

    # Set default values for existing rows
    op.execute("""
        UPDATE conversations
        SET updated_at = created_at
        WHERE updated_at IS NULL
    """)

    # Rename persona_id to personality_id if needed
    # (Check if column exists first)
```

### Phase 2: Import Updates (Medium Priority)

#### Step 2.1: Update conversation_service.py
```python
# OLD:
from ..models.chat import Conversation, Message

# NEW:
from ...database.models import Conversation, Message
```

#### Step 2.2: Update memory_service.py
```python
# OLD:
from ..models.chat import Conversation, Message

# NEW:
from ...database.models import Conversation, Message
```

#### Step 2.3: Search for Any Other References
Run comprehensive search for any other imports or references.

### Phase 3: Cleanup (Low Priority)

#### Step 3.1: Delete Duplicate File
- Delete `src/miachat/api/models/chat.py`
- Update `src/miachat/api/models/__init__.py` if needed

#### Step 3.2: Update .gitignore
Add test files and temporary data:
```
# Test files
test_*.py
*_test.py

# Generated data
data/
output_documents/
documents/*.pdf
documents/*.xlsx
!documents/README.md
```

#### Step 3.3: Clean Up Test Files
```bash
git rm --cached test_document_upload.py
git rm --cached -r output_documents/
# Keep local copies, just remove from git tracking
```

---

## 📋 Detailed Step-by-Step Plan

### ✅ Step 1: Backup Current State

```bash
# Create backup branch
git branch backup/pre-consolidation

# Export current database
cp data/memories.db data/memories.db.backup

# Document current state
git status > migration_status_before.txt
```

### ✅ Step 2: Update Canonical Models

**File:** `src/miachat/database/models.py`

Add these fields to the `Conversation` class:

```python
class Conversation(Base):
    """Conversation model."""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    personality_id = Column(Integer, ForeignKey('personalities.id'), nullable=False)
    title = Column(String, nullable=True)  # ← ADD THIS
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)  # ← ADD THIS if missing
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # ← ADD THIS
    conversation_data = Column(MutableDict.as_mutable(JSON), default=dict)

    personality = relationship('Personality', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation', order_by='Message.timestamp')
```

Verify `Message` class has:

```python
class Message(Base):
    """Message model."""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    content = Column(Text, nullable=False)
    role = Column(String, nullable=False)  # ← VERIFY EXISTS
    file_attachments = Column(JSON, nullable=True)  # ← ADD if missing
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship('Conversation', back_populates='messages')
```

### ✅ Step 3: Create Migration Script

**Option A: Using Alembic** (if configured)
```bash
cd src/miachat/database
alembic revision -m "consolidate_conversation_models"
# Edit the generated migration file
```

**Option B: Manual Migration Script** (simpler)

Create: `src/miachat/database/migrations/consolidate_models.py`

```python
"""
Consolidation migration: Add missing fields from chat.py models
to canonical database models.
"""

from sqlalchemy import text
from ..config import db_config

def upgrade():
    """Add missing columns to conversations table."""
    engine = db_config.engine

    with engine.connect() as conn:
        # Check if columns exist before adding
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('conversations')
            WHERE name = 'title'
        """))

        if result.fetchone()[0] == 0:
            print("Adding 'title' column to conversations...")
            conn.execute(text("""
                ALTER TABLE conversations
                ADD COLUMN title VARCHAR
            """))
            conn.commit()

        # Check for updated_at column
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM pragma_table_info('conversations')
            WHERE name = 'updated_at'
        """))

        if result.fetchone()[0] == 0:
            print("Adding 'updated_at' column to conversations...")
            conn.execute(text("""
                ALTER TABLE conversations
                ADD COLUMN updated_at DATETIME
            """))

            # Set updated_at to started_at for existing rows
            conn.execute(text("""
                UPDATE conversations
                SET updated_at = started_at
                WHERE updated_at IS NULL
            """))
            conn.commit()

        print("Migration completed successfully!")

def downgrade():
    """Remove added columns (optional)."""
    engine = db_config.engine

    with engine.connect() as conn:
        # SQLite doesn't support DROP COLUMN easily
        # Would need to recreate table
        print("Downgrade not implemented for SQLite")
        print("Restore from backup if needed")

if __name__ == "__main__":
    print("Running consolidation migration...")
    upgrade()
    print("Done!")
```

### ✅ Step 4: Update Imports

**File 1:** `src/miachat/api/core/conversation_service.py`

```python
# Find and replace:
# OLD:
from ..models.chat import Conversation, Message

# NEW:
from ...database.models import Conversation, Message
```

**File 2:** `src/miachat/api/core/memory_service.py`

```python
# Find and replace:
# OLD:
from ..models.chat import Conversation, Message

# NEW:
from ...database.models import Conversation, Message
```

### ✅ Step 5: Test Imports

```bash
# Test that imports work
python3 -c "
import sys
sys.path.insert(0, 'src')
from miachat.database.models import Conversation, Message, Base
from miachat.api.core.conversation_service import ConversationService
from miachat.api.core.memory_service import MemoryService
print('✅ All imports successful!')
"
```

### ✅ Step 6: Run Migration

```bash
# Run the migration script
python src/miachat/database/migrations/consolidate_models.py

# Verify migration worked
python3 -c "
import sys
sys.path.insert(0, 'src')
from miachat.database.config import db_config
from sqlalchemy import inspect

inspector = inspect(db_config.engine)
columns = inspector.get_columns('conversations')
print('Conversations table columns:')
for col in columns:
    print(f'  - {col[\"name\"]}: {col[\"type\"]}')
"
```

### ✅ Step 7: Delete Duplicate File

```bash
# Remove the duplicate model file
git rm src/miachat/api/models/chat.py

# Update __init__ if needed
# (Check if it imports from chat.py)
```

### ✅ Step 8: Test Application

```bash
# Try to start the application
python src/miachat/api/main.py

# Or with Docker:
docker compose up

# Check for any import errors or database errors
```

### ✅ Step 9: Clean Up Test Files

Update `.gitignore`:
```bash
cat >> .gitignore << 'EOF'

# Test scripts
test_*.py
*_test.py
simple_memory_test.py
extended_memory_test.py
focused_memory_test.py
memory_test.py
test_memory_retention.py
test_semantic_memory.py
test_debug_memory.py
test_final_memory.py
test_semantic_working.py
test_document_upload.py
fix_sage_category.py
update_sage.py
test_runner.py
test_setup_wizard_simple.py

# Generated output
output_documents/
!output_documents/.gitkeep

# Runtime data
data/*.db
!data/.gitkeep
EOF
```

Remove from git:
```bash
git rm --cached test_*.py
git rm --cached *_test.py
git rm --cached -r output_documents/
```

### ✅ Step 10: Commit Changes

```bash
git add .
git commit -m "♻️ Consolidate database models and fix duplicate Base classes

BREAKING CHANGE: Unified all models under single database.models module

Changes:
- Consolidated Conversation and Message models into database/models.py
- Removed duplicate definitions from api/models/chat.py
- Added missing fields (title, updated_at) to Conversation model
- Updated imports in conversation_service.py and memory_service.py
- Created migration script for existing databases
- Cleaned up test files from git tracking

Technical Details:
- Fixed dual Base class issue (Base vs ChatBase)
- Established database/models.py as single source of truth
- All models now use unified SQLAlchemy metadata registry
- Foreign key relationships properly defined

Migration:
- Existing databases: Run src/miachat/database/migrations/consolidate_models.py
- New installations: Run src/miachat/database/init_db.py

Benefits:
- No more table definition conflicts
- Cleaner architecture (separation of concerns)
- Easier maintenance (single model location)
- Proper foreign key constraints

Testing:
- ✅ Imports verified
- ✅ Migration tested
- ✅ Application startup confirmed
- ✅ Chat functionality verified

Closes #[issue-number] if applicable
"
```

---

## 🧪 Testing Checklist

After migration, verify:

- [ ] Application starts without errors
- [ ] Can create new conversation
- [ ] Can send messages
- [ ] Can retrieve conversation history
- [ ] Personality relationships work
- [ ] Memory service functions correctly
- [ ] Document attachments work
- [ ] No duplicate table warnings
- [ ] No import errors in logs

---

## 🚨 Rollback Plan

If something goes wrong:

```bash
# Restore from backup branch
git checkout backup/pre-consolidation

# Restore database
cp data/memories.db.backup data/memories.db

# Restart services
docker compose down
docker compose up -d
```

---

## 📊 Success Criteria

Migration is successful when:

1. ✅ Only ONE definition of Conversation exists
2. ✅ Only ONE definition of Message exists
3. ✅ All imports use `database.models`
4. ✅ Application starts without errors
5. ✅ All tests pass
6. ✅ No duplicate table warnings
7. ✅ Chat functionality works
8. ✅ Memory service works
9. ✅ Changes committed to git
10. ✅ Documentation updated

---

## 📝 Documentation Updates

After completion, update:

- [x] ARCHITECTURE.md - Document single Base decision
- [ ] CURRENT_STATUS_REPORT.md - Mark issue as resolved
- [ ] docs/implementation/roadmap.md - Update Phase 6 status
- [ ] README.md - Update any references to model locations

---

## 🎓 Lessons Learned

Document for future:

1. **Single Base Rule**: Always use one declarative_base() per application
2. **Model Organization**: Files are for organization, Base is for metadata
3. **Migration First**: Always create migrations before changing models
4. **Test Coverage**: Integration tests would have caught this earlier
5. **Code Review**: Architectural changes need extra scrutiny

---

**Ready to execute this plan? Let's do it step by step!**
