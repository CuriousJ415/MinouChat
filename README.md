# MiaChat - AI Personality Chat Application

MiaChat is a FastAPI-based web application that allows you to chat with AI personalities, each with unique traits and communication styles.

## Features

- **Multiple AI Personalities**: Choose from Gordon (Business Coach), Sage (Life Coach), and Mia (Friend)
- **Personality Management**: View, create, and edit AI personalities with full CRUD operations
- **Interactive Chat Interface**: Clean, modern chat interface with personality switching
- **AI-Powered Trait Suggestions**: Automatic personality trait suggestions using local Ollama LLM
- **Communication Style Customization**: Sliders for directness, warmth, formality, empathy, and humor
- **Privacy-First Design**: Local LLM processing with Ollama (no external data transmission)
- **Modern UI**: Bootstrap-based responsive design with real-time form validation
- **File-based Storage**: Simple JSON-based personality storage (no database required)

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Application**:
   ```bash
   python run.py
   ```

3. **Access the Application**:
   - Open your browser and go to: http://127.0.0.1:8080
   - The application will automatically create default personalities on first run

## Available Pages

- **Home** (`/`): Landing page with feature overview
- **Chat** (`/chat`): Interactive chat interface with personality selector
- **Personalities** (`/personality`): View all available personalities and their traits
- **Settings** (`/settings`): Application settings (coming soon)
- **Config** (`/config`): System configuration (coming soon)

## Default Personalities

### Gordon - Business Coach
- **Category**: Business
- **Traits**: High conscientiousness, moderate extraversion
- **Style**: Formal, direct, practical advice
- **Best for**: Business discussions, goal setting, strategic planning

### Sage - Life Coach
- **Category**: Life Coaching
- **Traits**: High openness, high agreeableness
- **Style**: Compassionate, thoughtful, wisdom-based guidance
- **Best for**: Personal growth, life decisions, emotional support

### Mia - Friend
- **Category**: Friend
- **Traits**: High extraversion, high agreeableness
- **Style**: Casual, supportive, conversational
- **Best for**: Casual chat, emotional support, friendly conversation

## Personality Storage

Personalities are stored as JSON files in the `personalities/` directory. Each personality includes:

- Basic information (name, description, category, tags)
- Personality traits (Big Five model)
- Communication style preferences
- System prompt for AI behavior

## Development

The application is built with:
- **FastAPI**: Modern Python web framework
- **Jinja2**: Template engine
- **Bootstrap 5**: Frontend styling
- **File-based storage**: Simple JSON files for data persistence

## Project Structure

```
src/miachat/api/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── personality_manager.py  # Personality management logic
│   ├── templates.py            # Template rendering
│   ├── static.py               # Static file serving
│   └── flash.py                # Flash message system
├── templates/              # HTML templates
│   ├── index.html
│   ├── chat/
│   │   └── index.html
│   └── personality/
│       └── list.html
└── static/                 # Static assets (CSS, JS, images)
personalities/              # Personality JSON files
```

## Future Enhancements

- [x] **Real AI integration** with Ollama (completed)
- [x] **Personality creation and editing interface** (completed)
- [x] **Chat history persistence** (completed)
- [x] **User authentication** (completed)
- [x] **Advanced personality customization** (completed)
- [ ] **Multi-provider LLM support** (OpenAI, Anthropic, etc.)
- [ ] **Export/import personality configurations**
- [ ] **Enhanced trait suggestions** with multiple LLM providers
- [ ] **Personality templates and presets**

## Troubleshooting

If you encounter issues:

1. **Port already in use**: The application uses port 8080 by default. Kill any existing processes or change the port in `run.py`
2. **Missing dependencies**: Ensure all requirements are installed with `pip install -r requirements.txt`
3. **Template errors**: Check that all template files exist in the correct locations

## License

This project is for educational and personal use. 