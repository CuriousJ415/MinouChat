# MiaChat Deployment Notes

## Database Cleanup Required Before Publication

### Test Data to Remove
The current database contains test data from development and debugging sessions:

1. **Alice from Portland** - Test conversation used for semantic memory debugging
2. **Various test personas** - Development test data
3. **Debug message logs** - Testing conversations

### Cleanup Process
Before deploying to production:

1. Clear conversations database:
   - Remove test conversation data
   - Keep conversation schema intact

2. Clear test personas:
   - Remove debug/test persona files
   - Keep default personas (Mia, Sage, etc.)

3. Reset message counters and conversation IDs

### Commands to Run
```bash
# Clear test conversations (preserve schema)
# TODO: Add specific database cleanup commands

# Remove test files
rm -f test_*.py
rm -f *memory_test.py
rm -f simple_memory_test.py
rm -f debug_*.py

# Keep deployment-ready test files if needed
```

### Post-Cleanup Verification
- [ ] Fresh user registration works
- [ ] Persona creation works
- [ ] Semantic memory starts clean
- [ ] No test data visible to new users

## Major Features Completed in This Version

### ✅ Semantic Memory System
- Long-term memory for therapeutic/coaching relationships
- Database persistence with SQLite + SQLAlchemy
- Keyword-based semantic search
- Combines recent + relevant message retrieval
- Supports year+ conversation history

### ✅ Setup Wizard Enhancements
- Model selection dropdowns
- API key validation
- Full model switching capability
- Interactive persona assignment

### ✅ Persona Management System
- XML-based persona definitions
- Category system with guidance
- Model assignment per persona
- Privacy-first recommendations

### ✅ Privacy & Security
- Local Ollama model support
- No data sent to cloud by default
- Optional cloud provider integration
- User authentication system

## Architecture Notes
- FastAPI backend with SQLAlchemy ORM
- Dual memory system: File-based + Database
- Containerized deployment with Docker
- Privacy-first design principles