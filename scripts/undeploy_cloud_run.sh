#!/usr/bin/env bash
# Tear down / undeploy BetScout from Google Cloud Run & Firebase Hosting.
# Usage:
#   ./scripts/undeploy_cloud_run.sh               # Deletes Cloud Run service & disables Firebase Hosting (keeps GCS data bucket)
#   ./scripts/undeploy_cloud_run.sh --purge-data  # Also deletes gs://<project>-data bucket
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:-${FIREBASE_PROJECT_ID:-${VITE_FIREBASE_PROJECT_ID:-betscout-ai}}}"
REGION="${GCP_REGION:-europe-west3}"
SERVICE_NAME="${CLOUD_RUN_SERVICE:-betscout-app}"
BUCKET_NAME="${GCS_DATA_BUCKET:-${PROJECT_ID}-data}"
PURGE_DATA="${1:-}"

echo "🛑 [1/4] Deleting 24/7 Cloud Scheduler jobs (${REGION})..."
for JOB_NAME in betscout-auto-sync betscout-auto-rescan betscout-morning-digest; do
  gcloud scheduler jobs delete "${JOB_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --quiet 2>/dev/null || echo "   (Cloud Scheduler job ${JOB_NAME} already deleted)"
done

echo "🛑 [2/4] Deleting Cloud Run service ${SERVICE_NAME} (${REGION}) in project ${PROJECT_ID}..."
gcloud run services delete "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --quiet || echo "   (Cloud Run service ${SERVICE_NAME} already deleted)"

echo "🌐 [3/4] Disabling Firebase Hosting for ${PROJECT_ID}.web.app..."
npx --yes firebase-tools hosting:disable --project "${PROJECT_ID}" --force || echo "   (Firebase Hosting already disabled)"

if [ "${PURGE_DATA}" = "--purge-data" ]; then
  echo "🗑️ [4/4] Deleting persistent Cloud Storage bucket gs://${BUCKET_NAME}..."
  gcloud storage rm -r "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" --quiet || echo "   (Bucket gs://${BUCKET_NAME} already removed)"
else
  echo "💾 [4/4] Keeping persistent Cloud Storage bucket gs://${BUCKET_NAME} (pass --purge-data to delete it as well)."
fi

echo "✅ BetScout has been undeployed from Cloud Run and Firebase Hosting."
