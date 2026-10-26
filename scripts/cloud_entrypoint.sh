#!/usr/bin/env bash
set -euo pipefail

# If a persistent volume (e.g. Cloud Run GCS FUSE /mnt/data or Fly.io /data) is mounted via BETSCOUT_DATA_DIR,
# automatically seed it from /app/data_seed on first boot if matches.sqlite does not exist yet.
TARGET_DATA_DIR="${BETSCOUT_DATA_DIR:-/app/data}"
mkdir -p "${TARGET_DATA_DIR}"

if [ -d "/app/data_seed" ] && [ ! -f "${TARGET_DATA_DIR}/matches.sqlite" ]; then
  echo "📦 Seeding initial database and recommendations into ${TARGET_DATA_DIR}..."
  cp -rn /app/data_seed/* "${TARGET_DATA_DIR}/" || true
fi

exec uv run betscout webapp --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}"
