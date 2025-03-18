# MiaAI Installation Guide

This guide provides detailed instructions for installing MiaAI on different platforms.

## Prerequisites

- Python 3.8 or newer (3.8-3.12 recommended for best compatibility)
- pip (Python package manager)
- Git (to clone the repository)

## Installation Options

### Option 1: Using the Installation Script (Recommended)

The easiest way to install MiaAI is using our installation script:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/yourusername/miaai.git
cd miaai-v1

# Run the installation script
python install.py
```

You can customize the installation with the following options:
- `--core-only`: Install only core dependencies (minimal installation)
- `--no-docs`: Skip document processing dependencies
- `--no-memory`: Skip advanced memory system dependencies
- `--upgrade`: Upgrade existing packages

### Option 2: Manual Installation

#### Step 1: Clone the repository
```bash
git clone https://github.com/yourusername/miaai.git
cd miaai-v1
```

#### Step 2: Create a virtual environment (optional but recommended)
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install dependencies
```bash
# Install core dependencies
pip install -r requirements-core.txt

# Install memory system dependencies
pip install -r requirements-memory.txt

# Install document processing dependencies
pip install -r requirements-docs.txt
```

#### Step 4: Create necessary directories
```bash
mkdir -p documents output_documents
```

### Option 3: Docker Installation (Most Reliable)

Using Docker ensures a consistent environment across platforms:

```bash
# Clone the repository
git clone https://github.com/yourusername/miaai.git
cd miaai-v1

# Build and start the Docker container
docker-compose up -d
```

The Docker setup includes:

- Automatic database initialization
- Volume mounting for persistent data
- Environment variable configuration via `.env` file
- Optional Ollama integration for local LLM support

### Docker Entrypoint

The Docker container uses an entrypoint script that:

1. Creates necessary directories
2. Initializes the database with default characters
3. Starts the web application

If you need to customize the entrypoint behavior, you can modify `docker-entrypoint.sh`.

## Platform-Specific Instructions

### Windows

If you encounter issues with PyMuPDF or other C-based extensions:

1. Install Visual C++ Build Tools:
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "Desktop development with C++"

2. Try installing pre-built wheels:
   ```bash
   pip install --only-binary=:all: numpy scikit-learn
   ```

### macOS

If you encounter issues with PyMuPDF:

1. Install system dependencies with Homebrew:
   ```bash
   brew install mupdf swig freetype
   ```

2. For Apple Silicon (M1/M2) Macs:
   ```bash
   # Use miniforge for better compatibility
   brew install miniforge
   conda create -n miaai-env python=3.10
   conda activate miaai-env
   
   # Then proceed with pip installation
   pip install -r requirements-core.txt
   pip install -r requirements-memory.txt
   pip install -r requirements-docs.txt
   ```

### Linux

Install system dependencies first:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential libffi-dev libssl-dev python3-dev

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install libffi-devel openssl-devel
```

## Troubleshooting

### Common Issues

1. **ImportError: DLL load failed**: Missing system libraries. Check the platform-specific instructions.

2. **Error: Microsoft Visual C++ is required**: Install Visual C++ Build Tools as per Windows instructions.

3. **Could not find a version that satisfies the requirement**: Try removing version constraints:
   ```bash
   pip install --no-deps -r requirements-updated.txt
   ```

4. **Memory errors during installation**: Some packages require significant memory to build. Try:
   ```bash
   pip install --no-cache-dir package_name
   ```

### Getting Help

If you continue to have installation issues:

1. Check our [GitHub issues](https://github.com/yourusername/miaai/issues) for similar problems
2. Create a new issue with details about your environment and the exact error message
3. Join our community Discord for real-time help

## Running MiaAI

After installation:

```bash
python web_app.py
```

Visit http://localhost:8080 in your browser to access MiaAI. 