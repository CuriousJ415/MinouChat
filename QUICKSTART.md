# MiaAI Docker Quick Start Guide

This guide will help you get MiaAI up and running quickly using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed
- Approximately 2GB of free disk space
- Internet connection for pulling Docker images

## Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/miaai.git
   cd miaai
   ```

2. **Setup environment variables (optional)**

   Create a `.env` file in the project root:

   ```bash
   # For OpenAI (recommended for first-time setup)
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Or for Anthropic
   # LLM_PROVIDER=anthropic
   # ANTHROPIC_API_KEY=your_anthropic_api_key_here
   
   # Or for local models with Ollama
   # LLM_PROVIDER=ollama
   ```

3. **Launch MiaAI**

   ```bash
   # Basic setup with your chosen API provider
   docker compose up -d
   
   # OR with Ollama for local model support
   docker compose --profile with-ollama up -d
   
   # OR with Ngrok for remote access (requires NGROK_AUTH_TOKEN in .env)
   docker compose --profile with-ngrok up -d
   ```

4. **Access the application**

   Open your browser and go to: http://localhost:8080

## Key Features

- **Chat with AI Characters**: Create and interact with AI personas
- **Memory System**: Characters remember your conversations
- **Document Analysis**: Upload documents for AI to reference
- **Multiple LLM Providers**: Support for OpenAI, Anthropic, and local models

## Configuration Options

### Using Different Language Models

Edit the `.env` file to change your LLM provider:

```bash
# OpenAI Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo

# Anthropic Configuration
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=claude-3-opus-20240229  # or another Claude model

# Ollama Configuration (local)
LLM_PROVIDER=ollama
OLLAMA_MODEL=mistral  # or llama2, orca-mini, etc.
```

### Customizing the Port

Change the port in your `.env` file:

```bash
PORT=9000  # Change from default 8080
```

## Using Ollama for Local Models

To use MiaAI with local models:

1. **Launch with Ollama profile**

   ```bash
   docker compose --profile with-ollama up -d
   ```

2. **Pull your desired models**

   ```bash
   # Access the Ollama container
   docker exec -it ollama-server bash
   
   # Pull models
   ollama pull mistral
   ollama pull llama2
   ollama pull orca-mini
   
   # Exit the container
   exit
   ```

3. **Configure MiaAI to use Ollama**

   Edit your `.env` file:

   ```bash
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=mistral  # or any model you pulled
   ```

4. **Restart the MiaAI container**

   ```bash
   docker compose restart miaai
   ```

## Data Persistence

Your data is stored in these directories, which are mounted as volumes:

- `./data`: Database files
- `./documents`: Uploaded documents
- `./output_documents`: Generated documents
- `./config`: Configuration files

## Stopping and Restarting

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (will erase all data)
docker compose down -v

# Restart after changes
docker compose up -d
```

## Troubleshooting

### Container won't start

Check the logs:
```bash
docker compose logs miaai
```

### API key issues

Verify your `.env` file and restart:
```bash
docker compose restart miaai
```

### Ollama models not loading

Check Ollama logs:
```bash
docker compose logs ollama
```

## Updating MiaAI

```bash
# Pull latest changes
git pull

# Rebuild containers
docker compose build

# Restart
docker compose up -d
```

## 5. Key Features

- **Chat with AI Characters**: Create and interact with AI personas
- **Memory System**: Characters remember your conversations
- **Document Analysis**: Upload documents for AI to reference
- **Multiple LLM Providers**: Support for OpenAI, Anthropic, and local models

## 6. Configuration

MiaAI uses environment variables for configuration. Create a `.env` file:

```
# Basic settings
PORT=8080
DEBUG=False

# LLM Configuration
LLM_PROVIDER=openai  # or anthropic, ollama, etc.
OPENAI_API_KEY=your_api_key_here
# For Anthropic:
# ANTHROPIC_API_KEY=your_api_key_here
```

## 7. Common Issues

### Memory Issues

If you experience out-of-memory errors:
- Reduce the number of documents being processed
- Use smaller language models
- Increase system swap space

### Missing Dependencies

If you see errors about missing modules:
- Try installing the specific package: `pip install package_name`
- Check for C++ build tools on your system

### Database Errors

If you see database errors:
- Ensure the application has write permissions to the directory
- Try deleting `conversations.sqlite` and restarting

## 8. Next Steps

- See `MACOS_INSTALL.md` or `UBUNTU_DEPLOY.md` for detailed platform-specific guides
- Check `INSTALL.md` for complete installation instructions
- Explore `docs/` for usage documentation

## Need Help?

If you encounter any issues:
- Check the troubleshooting sections in the platform-specific guides
- Run `python check_compatibility.py` to identify potential problems
- Create an issue on GitHub 