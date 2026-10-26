# Production Dockerfile for BetScout (Option D: Google Cloud Run / Fly.io + Firebase Hosting & Auth)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    HOST=0.0.0.0 \
    PORT=8080

# Install curl (used by Sportradar Gismo, ESPN & Discord API clients) and DejaVu fonts (for Pillow 1080x580 PNG Pick Cards)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies first for layer caching
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Copy static assets & ingestion config
COPY ingestion_config.json betscout-logo.svg betscout-logo.png ./
RUN mkdir -p /app/data

# Entrypoint script seeds mounted volume (/mnt/data) with initial matches.sqlite if empty, then starts the server
COPY scripts/cloud_entrypoint.sh /app/scripts/cloud_entrypoint.sh
RUN chmod +x /app/scripts/cloud_entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/app/scripts/cloud_entrypoint.sh"]
