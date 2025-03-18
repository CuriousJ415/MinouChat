FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-core.txt .
RUN pip install --no-cache-dir -r requirements-core.txt

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Verify Flask and Flask-CORS installation
RUN python -c "import flask; import flask_cors"

# Set environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=development
ENV PYTHONPATH=/app

# Run the application
ENTRYPOINT ["/app/entrypoint.sh"]