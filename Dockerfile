FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Verify FastAPI and dependencies installation
RUN python -c "import fastapi; import uvicorn"

# Set environment variables
ENV PYTHONPATH=/app
ENV FASTAPI_ENV=development

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]