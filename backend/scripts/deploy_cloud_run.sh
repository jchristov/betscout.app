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
CRON_SECRET="${BETSCOUT_CRON_SECRET:-bs_cron_live_9f8e7d6c5b4a3210}"

echo "🚀 [1/4] Ensuring Google Cloud Storage bucket gs://${BUCKET_NAME} exists for persistent database..."
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" --project="${PROJECT_ID}" --location="${REGION}" --uniform-bucket-level-access
fi

echo "📦 [2/4] Uploading current data/betscout.db, recommendations.json & dashboard.html to gs://${BUCKET_NAME}..."
if [ -f "data/betscout.db" ]; then
  if [ "${FORCE_DB_UPLOAD:-0}" = "1" ] || ! gcloud storage ls "gs://${BUCKET_NAME}/betscout.db" >/dev/null 2>&1; then
    gcloud storage cp "data/betscout.db" "gs://${BUCKET_NAME}/betscout.db"
  else
    echo "   ✓ gs://${BUCKET_NAME}/betscout.db already exists (set FORCE_DB_UPLOAD=1 to overwrite)"
  fi
fi
for f in recommendations.json webapp_settings.json best_bets.json best_bets.csv dashboard.html; do
  if [ -f "data/${f}" ]; then
    gcloud storage cp "data/${f}" "gs://${BUCKET_NAME}/${f}"
  fi
done

echo "🧪 [3/6] Running Vitest unit tests & building Vue 3 + Tailwind SPA (frontend/dist)..."
(cd frontend && npm run test && npm run build)

echo "🐳 [4/6] Building & deploying Cloud Run service ${SERVICE_NAME} (${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
  --quiet \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="." \
  --execution-environment=gen2 \
  --allow-unauthenticated \
  --cpu=2 \
  --memory=2Gi \
  --min-instances=0 \
  --max-instances=3 \
  --timeout=900 \
  --add-volume="name=betscout-data,type=cloud-storage,bucket=${BUCKET_NAME}" \
  --add-volume-mount="volume=betscout-data,mount-path=/mnt/gcs" \
  --set-env-vars="^|^GCS_MOUNT_DIR=/mnt/gcs|BETSCOUT_DATA_DIR=/app/data|MONETIZATION_ENABLED=1|FREE_PREVIEW_PICKS_COUNT=0|BETSCOUT_CRON_SECRET=${CRON_SECRET}|FIREBASE_PROJECT_ID=${PROJECT_ID}|FIREBASE_WEB_API_KEY=${FB_API_KEY}|FIREBASE_AUTH_DOMAIN=${FB_AUTH_DOMAIN}|BETSCOUT_ADMIN_EMAILS=${ADMIN_EMAILS}|FIREBASE_ADMIN_EMAILS=${ADMIN_EMAILS}|DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL:-}|DISCORD_WEBHOOK_URL_FOOTBALL=${DISCORD_WEBHOOK_URL_FOOTBALL:-}|DISCORD_WEBHOOK_URL_TENNIS=${DISCORD_WEBHOOK_URL_TENNIS:-}|DISCORD_WEBHOOK_URL_HOCKEY=${DISCORD_WEBHOOK_URL_HOCKEY:-}|DISCORD_WEBHOOK_URL_BASKETBALL=${DISCORD_WEBHOOK_URL_BASKETBALL:-}|DISCORD_WEBHOOK_URL_VOLLEYBALL=${DISCORD_WEBHOOK_URL_VOLLEYBALL:-}|DISCORD_WEBHOOK_URL_BASEBALL=${DISCORD_WEBHOOK_URL_BASEBALL:-}|DISCORD_WEBHOOK_URL_AMERICAN_FOOTBALL=${DISCORD_WEBHOOK_URL_AMERICAN_FOOTBALL:-}|DISCORD_WEBHOOK_URL_TABLE_TENNIS=${DISCORD_WEBHOOK_URL_TABLE_TENNIS:-}|DISCORD_WEBHOOK_URL_FREE_TEASER=${DISCORD_WEBHOOK_URL_FREE_TEASER:-}|TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}|TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}"

echo "🌐 [4/5] Deploying Firebase Hosting edge CDN & rewrites..."
npx --yes firebase-tools deploy --only hosting --project "${PROJECT_ID}"

echo "🔐 [5/6] Ensuring custom domains (betscout.app, betscout.vip, betscout-ai.com) are whitelisted in Firebase Auth..."
TOK=$(gcloud auth print-access-token 2>/dev/null || true)
if [ -n "${TOK}" ]; then
  python3 -c '
import json, subprocess, sys
tok = sys.argv[1]
proj = sys.argv[2]
url = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{proj}/config"
out = subprocess.check_output(["curl", "-sS", url, "-H", f"Authorization: Bearer {tok}", "-H", f"x-goog-user-project: {proj}"], text=True)
cfg = json.loads(out)
doms = cfg.get("authorizedDomains") or []
for d in ["localhost", f"{proj}.firebaseapp.com", f"{proj}.web.app", "betscout.app", "www.betscout.app", "betscout.vip", "www.betscout.vip", "betscout-ai.com", "www.betscout-ai.com"]:
    if d not in doms:
        doms.append(d)
subprocess.run(["curl", "-sS", "-X", "PATCH", f"{url}?updateMask=authorizedDomains", "-H", f"Authorization: Bearer {tok}", "-H", f"x-goog-user-project: {proj}", "-H", "Content-Type: application/json", "-d", json.dumps({"authorizedDomains": doms})], check=False, stdout=subprocess.DEVNULL)
print("   ✓ Firebase Auth authorizedDomains whitelisted:", ", ".join(doms))
' "${TOK}" "${PROJECT_ID}" || true
fi

echo "⏰ [6/6] Ensuring 24/7 Cloud Scheduler jobs (betscout-auto-sync & betscout-auto-rescan) are active..."
gcloud services enable cloudscheduler.googleapis.com --project="${PROJECT_ID}" --quiet || true
CR_URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)")
if gcloud scheduler jobs describe betscout-auto-sync --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud scheduler jobs update http betscout-auto-sync \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="5,25,45 * * * *" \
    --uri="${CR_URL}/api/sync" \
    --http-method=POST \
    --update-headers="Content-Type=application/json,Authorization=Bearer ${CRON_SECRET}" \
    --message-body='{"rescan":false,"min_odds":1.10}' \
    --attempt-deadline=600s \
    --quiet || true
else
  gcloud scheduler jobs create http betscout-auto-sync \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="5,25,45 * * * *" \
    --uri="${CR_URL}/api/sync" \
    --http-method=POST \
    --headers="Content-Type=application/json,Authorization=Bearer ${CRON_SECRET}" \
    --message-body='{"rescan":false,"min_odds":1.10}' \
    --attempt-deadline=600s \
    --quiet || true
fi

if gcloud scheduler jobs describe betscout-auto-rescan --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud scheduler jobs update http betscout-auto-rescan \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="10 */3 * * *" \
    --uri="${CR_URL}/api/sync" \
    --http-method=POST \
    --update-headers="Content-Type=application/json,Authorization=Bearer ${CRON_SECRET}" \
    --message-body='{"rescan":true,"days":3,"min_odds":1.10}' \
    --attempt-deadline=900s \
    --quiet || true
else
  gcloud scheduler jobs create http betscout-auto-rescan \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="10 */3 * * *" \
    --uri="${CR_URL}/api/sync" \
    --http-method=POST \
    --headers="Content-Type=application/json,Authorization=Bearer ${CRON_SECRET}" \
    --message-body='{"rescan":true,"days":3,"min_odds":1.10}' \
    --attempt-deadline=900s \
    --quiet || true
fi

if gcloud scheduler jobs describe betscout-morning-digest --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud scheduler jobs update http betscout-morning-digest \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="0 9 * * *" \
    --time-zone="Europe/Vienna" \
    --uri="${CR_URL}/api/daily-digest" \
    --http-method=POST \
    --update-headers="Content-Type=application/json,Authorization=Bearer ${CRON_SECRET}" \
    --message-body='{"days":3,"min_odds":1.15,"day":"today"}' \
    --attempt-deadline=900s \
    --quiet || true
else
  gcloud scheduler jobs create http betscout-morning-digest \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="0 9 * * *" \
    --time-zone="Europe/Vienna" \
    --uri="${CR_URL}/api/daily-digest" \
    --http-method=POST \
    --headers="Content-Type=application/json,Authorization=Bearer ${CRON_SECRET}" \
    --message-body='{"days":3,"min_odds":1.15,"day":"today"}' \
    --attempt-deadline=900s \
    --quiet || true
fi

echo "✅ Deployment complete! BetScout is live on Firebase Hosting + Cloud Run + 24/7 Cloud Scheduler."
