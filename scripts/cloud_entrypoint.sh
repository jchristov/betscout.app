#!/usr/bin/env bash
set -euo pipefail

# Hybrid Local-NVMe + Cloud Storage FUSE persistence for Cloud Run:
# SQLite WAL mode requires POSIX shared-memory/locking that GCS FUSE does not support directly.
# We keep the active working database on fast local container storage (/app/data) for <1ms query latency,
# and automatically hydrate from / sync back to the mounted GCS bucket (/mnt/gcs) on boot, every 60s, and on SIGTERM.
LOCAL_DATA_DIR="/app/data"
GCS_SYNC_DIR="${GCS_MOUNT_DIR:-/mnt/gcs}"
mkdir -p "${LOCAL_DATA_DIR}"

sync_from_gcs() {
  if [ -d "${GCS_SYNC_DIR}" ]; then
    echo "📥 Hydrating local ${LOCAL_DATA_DIR} from persistent volume ${GCS_SYNC_DIR}..."
    for f in betscout.db recommendations.json webapp_settings.json best_bets.json best_bets.csv dashboard.html; do
      if [ -f "${GCS_SYNC_DIR}/${f}" ]; then
        cp -f "${GCS_SYNC_DIR}/${f}" "${LOCAL_DATA_DIR}/${f}" || true
      fi
    done
  fi
}

sync_to_gcs() {
  if [ -d "${GCS_SYNC_DIR}" ]; then
    for f in betscout.db recommendations.json webapp_settings.json best_bets.json best_bets.csv dashboard.html; do
      if [ -f "${LOCAL_DATA_DIR}/${f}" ]; then
        if [ ! -f "${GCS_SYNC_DIR}/${f}" ] || [ "${LOCAL_DATA_DIR}/${f}" -nt "${GCS_SYNC_DIR}/${f}" ]; then
          cp -f "${LOCAL_DATA_DIR}/${f}" "${GCS_SYNC_DIR}/${f}.tmp" && mv -f "${GCS_SYNC_DIR}/${f}.tmp" "${GCS_SYNC_DIR}/${f}" || true
        fi
      fi
    done
  fi
}

sync_from_gcs

# Background periodic sync loop + graceful SIGTERM flush when Cloud Run scales down a container
if [ -d "${GCS_SYNC_DIR}" ]; then
  (
    while true; do
      sleep 60
      sync_to_gcs
    done
  ) &
  trap 'echo "📤 Flushing local state to ${GCS_SYNC_DIR} before shutdown..."; sync_to_gcs; exit 0' SIGTERM SIGINT
fi

export BETSCOUT_DATA_DIR="${LOCAL_DATA_DIR}"
exec /app/.venv/bin/betscout webapp --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}"
