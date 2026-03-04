# Kinfolk Backend — Production Dockerfile
# Base: Python 3.11 slim for broad SQLCipher compatibility
# Target: Ubuntu 24.04 ARM64 (Raspberry Pi 5) and x86-64

FROM python:3.11-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by:
# - libsqlcipher-dev: SQLCipher encrypted database
# - portaudio19-dev: sounddevice (microphone capture)
# - ffmpeg: audio format conversion (TTS/STT pipelines)
# - build-essential: compile native Python extensions
# - libffi-dev: cffi (required by some crypto packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlcipher-dev \
    portaudio19-dev \
    ffmpeg \
    build-essential \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY rhasspy/ ./rhasspy/

# Create data directories
RUN mkdir -p /data /data/photos /data/music /data/models

EXPOSE 8080

# Health check — matches /health endpoint in main.py
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run with uvicorn — bind to all interfaces for Docker networking
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
