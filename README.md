# MiaChat

A sophisticated AI personality application capable of sustained, meaningful dialogue.

## Project Overview

MiaChat is an AI personality system that enables natural, context-aware conversations with customizable personalities. The system features:

- XML/JSON-based personality definitions
- Memory management for context retention
- Conversation management with personality integration
- Extensible architecture for future enhancements

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/CuriousJ415/MiaAI.git
cd MiaAI
```

### 2. Create and activate a Python 3.11 virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize the database

```bash
python -m src.miachat.cli init_database
```

### 5. Run the application

```bash
python -m src.miachat.web.run
```

Visit [http://localhost:5001](http://localhost:5001) in your browser.

---

### 6. Static Files

- Place images and other static assets in `src/miachat/web/static/`.
- Example: `src/miachat/web/static/images/ai_face_glow.jpg`

---

### 7. Troubleshooting

- If you see `ModuleNotFoundError`, ensure all dependencies are installed and you are using Python 3.11.
- For database issues, re-run the `init_database` command.

## Project Structure

```
miachat/
├── src/
│   └── miachat/
│       ├── core/           # Core functionality
│       ├── personality/    # Personality management
│       ├── memory/         # Memory management
│       ├── api/           # API endpoints
│       └── utils/         # Utility functions
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── config/
│   └── personalities/    # Personality definitions
└── docs/                # Documentation
```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest
   ```

## Core Components

### Personality Management
- Define personalities using XML or JSON
- Customize traits, style, knowledge, and backstory
- Serialize/deserialize personality definitions

### Memory Management
- Store and retrieve conversation history
- Maintain context across interactions
- Categorize and prioritize memories

### Conversation Management
- Handle message flow and context
- Integrate personality traits into responses
- Manage conversation state

## Development Guidelines

1. Code Style
   - Follow PEP 8 guidelines
   - Use type hints
   - Write docstrings for all public functions/classes

2. Testing
   - Write unit tests for all new functionality
   - Maintain test coverage above 80%
   - Run tests before committing changes

3. Documentation
   - Update README.md for significant changes
   - Document new features in docs/
   - Keep docstrings up to date

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure they pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 