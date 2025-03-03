# MiaAI - AI Character Chat Application

MiaAI is a web application that allows users to create and chat with AI characters. It uses language models to generate responses and maintains memory of conversations.

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