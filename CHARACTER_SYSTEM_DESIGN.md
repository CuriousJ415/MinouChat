# Character System Architecture

## Design Principles

1. **User Data Ownership**: Users own their characters completely
2. **Example Templates**: Separate example characters that can be imported
3. **Privacy First**: No automatic data collection or sharing
4. **Version Tracking**: Character changes are versioned for conversation continuity

## Character Types

### 1. User Characters (`/character_cards/`)
- **Location**: `/character_cards/{uuid}.json`
- **Ownership**: Belongs to specific user
- **Persistence**: Permanent, user-controlled
- **Versioning**: Full versioning via conversation_manager
- **Editing**: Full CRUD operations

### 2. Example Characters (`/character_examples/`)
- **Location**: `/character_examples/{example-id}.json`
- **Purpose**: Templates and inspiration for users
- **Source**: Curated by application, community contributions
- **Usage**: Import-only (copy to user characters)
- **Versioning**: Static, updated with application releases

### 3. System Characters (Optional Future)
- **Purpose**: Built-in assistants for onboarding, help
- **Scope**: Application functionality, not user content

## File Structure

```
/Users/jasonnau/projects/MiaChat/
├── character_cards/          # User's personal characters
│   ├── {user-uuid}.json     # Individual character files
│   └── metadata.json        # User preferences, categories
├── character_examples/       # Example templates
│   ├── business-coach.json  # Gordon template
│   ├── life-coach.json      # Sage template
│   ├── friend.json          # Mia template
│   └── examples.json        # Example metadata
└── conversations/           # Conversation versioning
    ├── sessions.json        # Active sessions
    ├── character_versions.json  # Character version history
    └── messages.json        # Message history
```

## Character Lifecycle

### Example Character Flow
1. **Discovery**: User browses available examples via `/api/characters/examples`
2. **Preview**: User views example character details
3. **Import**: User imports example as new personal character
4. **Customization**: User modifies imported character as needed

### User Character Flow
1. **Creation**: User creates new character via UI/API
2. **Versioning**: System creates initial version for conversations
3. **Usage**: Character used in conversations
4. **Evolution**: User updates character, new version created
5. **Migration**: Existing conversations can migrate to new version

## API Design

### Example Characters (Read-Only)
- `GET /api/characters/examples` - List available examples
- `GET /api/characters/examples/{id}` - Get example details
- `POST /api/characters/examples/{id}/import` - Import as user character

### User Characters (Full CRUD)
- `GET /api/characters` - List user's characters
- `POST /api/characters` - Create new character
- `GET /api/characters/{id}` - Get character details
- `PUT /api/characters/{id}` - Update character (creates new version)
- `DELETE /api/characters/{id}` - Delete character

## Implementation Benefits

1. **Clear Separation**: No confusion between templates and user data
2. **User Control**: Users fully own their character data
3. **Privacy**: No mixing of user content with system content
4. **Extensibility**: Easy to add new examples without affecting user data
5. **Backup/Export**: User characters are easily portable

## Migration Strategy

1. **Identify Current Characters**: Determine which are examples vs user-created
2. **Move Examples**: Relocate example characters to `/character_examples/`
3. **Update References**: Ensure UI and API point to correct locations
4. **Version Management**: Ensure conversation versioning works with new structure