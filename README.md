# MiaAI: Personal AI Assistant with Memory

MiaAI is a personal AI assistant platform that allows you to create and interact with AI characters that have persistent memory and can analyze documents.

## 🚀 Quick Start (Docker)

The easiest way to get started with MiaAI is using Docker:

```bash
# Clone the repository
git clone https://github.com/yourusername/miaai.git
cd miaai

# Create a .env file with your API key
echo "OPENAI_API_KEY=your_api_key_here" > .env

# Start MiaAI
docker compose up -d

# Access at http://localhost:8080
```

For detailed installation instructions, see [QUICKSTART.md](QUICKSTART.md).

## ✨ Features

- **AI Characters**: Create and interact with customizable AI personas
- **Memory System**: Characters remember conversations and can retrieve relevant information
- **Document Analysis**: Upload documents for AI to reference
- **Multiple LLM Providers**: Support for OpenAI, Anthropic, and Ollama (local models)
- **Docker Ready**: Simple containerized deployment

## 💾 Installation Options

MiaAI can be installed in several ways:

- **Standard Docker** (recommended): Simple setup with your API key
- **Local Models**: Use with Ollama for fully local deployment
- **Remote Access**: Optional Ngrok integration for access from anywhere

For complete setup instructions, see [QUICKSTART.md](QUICKSTART.md).

## Features

- Create and customize AI characters with unique personalities
- Chat with AI characters in a user-friendly interface
- Memory system that allows characters to remember past conversations
- Support for multiple LLM providers (Ollama, OpenAI, Anthropic)
- Settings page to configure LLM providers
- Docker support for easy deployment

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (optional, for containerized deployment)
- An LLM provider (Ollama, OpenAI API key, or Anthropic API key)

### Installation

#### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/miaai.git
   cd miaai
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:
   ```
   # MiaAI Configuration
   DATABASE_PATH=memories.db
   PORT=8080
   DEBUG=True
   SECRET_KEY=your_secret_key_here

   # LLM Configuration
   LLM_PROVIDER=ollama  # ollama, openai, or anthropic
   LLM_API_URL=http://localhost:11434/api  # For Ollama
   LLM_MODEL=mistral  # Or any other model you have
   LLM_API_KEY=  # Only needed for OpenAI or Anthropic

   # Ngrok Configuration (optional, for exposing to the internet)
   NGROK_AUTH_TOKEN=
   NGROK_DOMAIN=
   ```

4. Run the application:
   ```
   python web_app.py
   ```

5. Open your browser and navigate to `http://localhost:8080`

#### Docker Deployment

1. Make sure Docker and Docker Compose are installed

2. Build and start the containers:
   ```
   docker-compose up -d
   ```

3. Access the application at `http://localhost:8080`

## Usage

### Creating a Character

1. Click on the "New Character" button in the sidebar
2. Fill in the character details:
   - Name: The character's name
   - Role: A brief description of who they are
   - Personality: Traits and characteristics
   - Backstory: Background information
   - System Prompt: Advanced configuration for the AI

3. Click "Create" to save the character

### Chatting with Characters

1. Select a character from the sidebar
2. Type your message in the input field and press Enter or click the send button
3. The character will respond based on their personality and the conversation history

### Configuring LLM Settings

1. Click on the settings icon in the sidebar footer
2. Select your preferred LLM provider
3. Enter the required configuration details
4. Click "Test Connection" to verify your settings
5. Click "Save Settings" to apply the changes

## Project Structure

```
miaai/
├── app/                    # Application package
│   ├── api/                # API endpoints
│   ├── core/               # Core functionality
│   ├── llm/                # LLM adapters
│   ├── memory/             # Memory systems
│   ├── static/             # Static files (CSS, JS)
│   └── templates/          # HTML templates
├── config/                 # Configuration files
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
└── web_app.py              # Application entry point
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project uses various open-source libraries and frameworks
- Inspired by the growing interest in personalized AI assistants 

## Database Initialization

MiaAI uses SQLite for storing character data and conversation history. The database is automatically initialized when:

1. Running the application with Docker using the provided `docker-compose.yml`
2. Running the application directly with `python web_app.py` (if the database doesn't exist)

If you encounter issues with missing characters or database errors, you can manually initialize the database:

```bash
# Set the database path (optional, defaults to memories.db)
export DATABASE_PATH=data/memories.db

# Run the initialization script
python init_db.py
```

### Troubleshooting Database Issues

If you see errors like "no such table: characters" or if no characters appear in the UI:

1. Make sure the database file exists and is accessible
2. Try restoring default characters through the UI or API:
   ```bash
   curl -X POST http://localhost:8080/api/characters/restore-defaults
   ```
3. Check that the `DATABASE_PATH` environment variable is set correctly
4. For Docker installations, ensure the data volume is properly mounted 