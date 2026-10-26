# Option D Deployment Guide: Google Firebase (Hosting + Auth) & Cloud Run

This guide walks through deploying **BetScout (`betscout.app`)** using **Option D** so the app runs 24/7 in Google Cloud without your MacBook, with global CDN delivery via **Firebase Hosting**, Google Sign-In RBAC via **Firebase Authentication**, persistent database storage on **Cloud Run Gen2**, and unattended scans via **Cloud Scheduler**.

---

## 1. What Has Already Been Prepared in the Repository

1. **Production Container (`Dockerfile` + `.dockerignore` + `scripts/cloud_entrypoint.sh`):**
   - Uses `python:3.12-slim` + `uv` + `curl` + `fonts-dejavu-core` (for 1080×580 Pillow PNG Pick Cards).
   - Automatically binds to `0.0.0.0:$PORT` in Cloud Run and reads/writes `matches.sqlite`, `recommendations.json`, and `webapp_settings.json` from `BETSCOUT_DATA_DIR` (`/mnt/data`).
2. **Firebase Hosting Config (`firebase.json` + `.firebaserc`):**
   - Configures no-cache headers for `/sw.js` and `/api/stream` (SSE) and proxies all routes (`**`) to the `betscout-app` Cloud Run service in `europe-west3` (Frankfurt).
3. **Firebase Auth & Cloud Scheduler RBAC (`src/betscout/webapp.py` + `src/betscout/dashboard.py`):**
   - **Local Mode Default (`FIREBASE_WEB_API_KEY` unset):** Zero login required when running `uv run betscout` on your MacBook.
   - **Cloud Mode (`FIREBASE_WEB_API_KEY` + `FIREBASE_ADMIN_EMAILS` set):**
     - **Public / Shared Viewers:** Can open `https://betscout.app`, view all live scores, filter picks, inspect H2H modals, use the Smart Bet Slip & Dutching calculators, and save personal browser settings.
     - **Admin (`FIREBASE_ADMIN_EMAILS`):** Clicking **`🔐 Admin Sign In`** in the top-right header signs in with Google via Firebase Auth and attaches `Authorization: Bearer <idToken>` to all administrative `POST` calls (`🔄 Sync & Settle`, `⚡ Rescan Live`, `🚀 Full Pipeline`, `📌 Track Live`, `💬 Share Picks`, and global `⚙️ Settings`).
     - **Cloud Scheduler (`BETSCOUT_CRON_SECRET`):** Allows automated Cloud Scheduler jobs to call `POST /api/settle` and `POST /api/pipeline` using `Authorization: Bearer <BETSCOUT_CRON_SECRET>`.
4. **Health Check Endpoint (`GET /api/healthz`):**
   - Returns `{"ok": true, "status": "healthy", "db_exists": true, ...}` for Cloud Run startup/liveness probes.

---

## 2. One-Time Google Cloud & Firebase Setup (5 Minutes)

### Step 1: Create / Select Your Firebase & GCP Project
1. Go to the [Firebase Console](https://console.firebase.google.com/) and create a project (e.g. `betscout-app`), or select an existing project, and upgrade it to the **Blaze (pay-as-you-go)** plan (required for Cloud Run; usage stays within free tiers or ~$2–$4/month).
2. In **Firebase Console $\rightarrow$ Authentication $\rightarrow$ Sign-in method**, enable **Google** as a sign-in provider.
3. In **Firebase Console $\rightarrow$ Project Settings $\rightarrow$ General**, register a **Web App** (`betscout-web`) and copy its `apiKey` (`AIzaSy...`).

### Step 2: Set Your Environment Variables on Cloud Run
After running `./scripts/deploy_cloud_run.sh` (or during deployment), set your secrets and admin email in Cloud Run:

```bash
export GCP_PROJECT_ID="betscout-app"
export GCP_REGION="europe-west3"

gcloud run services update betscout-app \
  --project="${GCP_PROJECT_ID}" \
  --region="${GCP_REGION}" \
  --update-env-vars="FIREBASE_PROJECT_ID=${GCP_PROJECT_ID},FIREBASE_WEB_API_KEY=AIzaSy_YOUR_FIREBASE_WEB_KEY,FIREBASE_ADMIN_EMAILS=your.email@gmail.com,BETSCOUT_CRON_SECRET=your_random_cron_secret_token" \
  --update-env-vars="DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_FOOTBALL=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_TENNIS=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_HOCKEY=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_BASKETBALL=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_VOLLEYBALL=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_BASEBALL=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_AMERICAN_FOOTBALL=https://discord.com/api/webhooks/..." \
  --update-env-vars="DISCORD_WEBHOOK_URL_TABLE_TENNIS=https://discord.com/api/webhooks/..."
```

### Step 3: Deploy with One Command
```bash
chmod +x scripts/deploy_cloud_run.sh
./scripts/deploy_cloud_run.sh
```

---

## 3. Optional: Configure Unattended Cloud Scheduler Jobs (When `min-instances=0`)

If you run Cloud Run with `--min-instances=1`, BetScout's built-in 90-second background auto-poller runs 24/7 automatically inside the container.

If you prefer `--min-instances=0` (scale-to-zero so you pay $0 when idle), create two **Google Cloud Scheduler** jobs to wake the container for morning scans and match-window settlements:

```bash
SERVICE_URL=$(gcloud run services describe betscout-app --region=europe-west3 --format='value(status.url)')

# 1. Daily Full Pipeline & Morning Scan (08:30 & 16:30 Europe/Berlin)
gcloud scheduler jobs create http betscout-daily-pipeline \
  --location=europe-west3 \
  --schedule="30 8,16 * * *" \
  --time-zone="Europe/Berlin" \
  --uri="${SERVICE_URL}/api/pipeline" \
  --http-method=POST \
  --headers="Content-Type=application/json,Authorization=Bearer your_random_cron_secret_token" \
  --message-body='{"full_pipeline": true, "min_odds": 1.10}'

# 2. Live Score Settlement & Discord Recap Check (Every 5 minutes)
gcloud scheduler jobs create http betscout-settle-poller \
  --location=europe-west3 \
  --schedule="*/5 * * * *" \
  --time-zone="Europe/Berlin" \
  --uri="${SERVICE_URL}/api/settle" \
  --http-method=POST \
  --headers="Content-Type=application/json,Authorization=Bearer your_random_cron_secret_token" \
  --message-body='{"rescan": false}'
```
