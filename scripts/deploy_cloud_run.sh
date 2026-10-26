#!/usr/bin/env bash
# Deploy BetScout (Option D) to Google Cloud Run + Firebase Hosting
set -euo pipefail

# Load local .env if present
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
FB_API_KEY="${FIREBASE_WEB_API_KEY:-${VITE_FIREBASE_API_KEY:-}}"
FB_AUTH_DOMAIN="${FIREBASE_AUTH_DOMAIN:-${VITE_FIREBASE_AUTH_DOMAIN:-${PROJECT_ID}.firebaseapp.com}}"
ADMIN_EMAILS="${BETSCOUT_ADMIN_EMAILS:-${FIREBASE_ADMIN_EMAILS:-julian.christ@gmail.com,julian.christov@gmail.com}}"

echo "🚀 [1/4] Ensuring Google Cloud Storage bucket gs://${BUCKET_NAME} exists for persistent database..."
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" --location="${REGION}" --uniform-bucket-level-access
fi

echo "📦 [2/4] Uploading current data/betscout.db & recommendations.json to gs://${BUCKET_NAME} (if not already present)..."
if [ -f "data/betscout.db" ]; then
  gcloud storage cp -n data/betscout.db "gs://${BUCKET_NAME}/betscout.db" || true
fi
if [ -f "data/recommendations.json" ]; then
  gcloud storage cp data/recommendations.json "gs://${BUCKET_NAME}/recommendations.json"
fi
if [ -f "data/webapp_settings.json" ]; then
  gcloud storage cp data/webapp_settings.json "gs://${BUCKET_NAME}/webapp_settings.json"
fi

echo "🐳 [3/4] Building & deploying Cloud Run service ${SERVICE_NAME} (${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="." \
  --execution-environment=gen2 \
  --allow-unauthenticated \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=2 \
  --timeout=900 \
  --add-volume="name=betscout-data,type=cloud-storage,bucket=${BUCKET_NAME}" \
  --add-volume-mount="volume=betscout-data,mount-path=/mnt/data" \
  --set-env-vars="^@^BETSCOUT_DATA_DIR=/mnt/data@FIREBASE_PROJECT_ID=${PROJECT_ID}@FIREBASE_WEB_API_KEY=${FB_API_KEY}@FIREBASE_AUTH_DOMAIN=${FB_AUTH_DOMAIN}@BETSCOUT_ADMIN_EMAILS=${ADMIN_EMAILS}@FIREBASE_ADMIN_EMAILS=${ADMIN_EMAILS}"

echo "🌐 [4/4] Deploying Firebase Hosting edge CDN & rewrites..."
mkdir -p public
cp -f betscout-logo.png betscout-logo.svg public/ 2>/dev/null || true
firebase deploy --only hosting --project "${PROJECT_ID}"

echo "✅ Deployment complete! BetScout is live on Firebase Hosting + Cloud Run."
