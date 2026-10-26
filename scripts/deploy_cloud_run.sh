#!/usr/bin/env bash
# Deploy BetScout (Option D) to Google Cloud Run + Firebase Hosting
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

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

echo "📦 [2/4] Uploading current data/betscout.db, recommendations.json & dashboard.html to gs://${BUCKET_NAME}..."
for f in betscout.db recommendations.json webapp_settings.json best_bets.json best_bets.csv dashboard.html; do
  if [ -f "data/${f}" ]; then
    gcloud storage cp "data/${f}" "gs://${BUCKET_NAME}/${f}"
  fi
done

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
  --add-volume-mount="volume=betscout-data,mount-path=/mnt/gcs" \
  --set-env-vars="^@^GCS_MOUNT_DIR=/mnt/gcs@BETSCOUT_DATA_DIR=/app/data@FIREBASE_PROJECT_ID=${PROJECT_ID}@FIREBASE_WEB_API_KEY=${FB_API_KEY}@FIREBASE_AUTH_DOMAIN=${FB_AUTH_DOMAIN}@BETSCOUT_ADMIN_EMAILS=${ADMIN_EMAILS}@FIREBASE_ADMIN_EMAILS=${ADMIN_EMAILS}@DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL:-}@DISCORD_WEBHOOK_URL_FOOTBALL=${DISCORD_WEBHOOK_URL_FOOTBALL:-}@DISCORD_WEBHOOK_URL_TENNIS=${DISCORD_WEBHOOK_URL_TENNIS:-}@DISCORD_WEBHOOK_URL_HOCKEY=${DISCORD_WEBHOOK_URL_HOCKEY:-}@DISCORD_WEBHOOK_URL_BASKETBALL=${DISCORD_WEBHOOK_URL_BASKETBALL:-}@DISCORD_WEBHOOK_URL_VOLLEYBALL=${DISCORD_WEBHOOK_URL_VOLLEYBALL:-}@DISCORD_WEBHOOK_URL_BASEBALL=${DISCORD_WEBHOOK_URL_BASEBALL:-}@DISCORD_WEBHOOK_URL_AMERICAN_FOOTBALL=${DISCORD_WEBHOOK_URL_AMERICAN_FOOTBALL:-}@DISCORD_WEBHOOK_URL_TABLE_TENNIS=${DISCORD_WEBHOOK_URL_TABLE_TENNIS:-}@TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}@TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}"

echo "🌐 [4/4] Deploying Firebase Hosting edge CDN & rewrites..."
mkdir -p public
cp -f betscout-logo.png betscout-logo.svg public/ 2>/dev/null || true
npx --yes firebase-tools deploy --only hosting --project "${PROJECT_ID}"

echo "✅ Deployment complete! BetScout is live on Firebase Hosting + Cloud Run."
