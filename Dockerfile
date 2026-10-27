# Production Dockerfile for BetScout (Option D: Google Cloud Run / Fly.io + Firebase Hosting & Auth)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    HOST=0.0.0.0 \
    PORT=8080

# Install curl (used by Sportradar Gismo, ESPN & Discord API clients) and DejaVu + Noto Color Emoji fonts (for Pillow PNG Pick Cards)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies first for layer caching (resolve from public PyPI in Cloud Build)
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv sync --no-dev --default-index https://pypi.org/simple

# Copy static assets, CLI scripts, Vue 3 SPA bundle & ingestion config
COPY ingestion_config.json betscout-logo.svg betscout-logo.png ./
COPY scripts ./scripts
COPY frontend/dist ./frontend/dist
RUN mkdir -p /app/data && chmod +x /app/scripts/cloud_entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/app/scripts/cloud_entrypoint.sh"]
