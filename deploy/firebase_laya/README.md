# Deploying Sports-Tuned `Laya` (`laya_sports_ckpt`) on Firebase Functions & GCP Cloud Functions

This directory packages the fine-tuned **`laya-sports`** System-1 decision model (`ModernBERT-large` + 2-layer typed decision head, **`804 MB`** inference bundle) as a serverless HTTP endpoint using **Firebase Cloud Functions (2nd Gen Python 3.12)** or **GCP Cloud Functions (2nd Gen) / Cloud Run**.

---

## 1. Architecture & Sizing Summary

| Component | Details |
| :--- | :--- |
| **Inference Bundle Size** | **`804 MB`** (`model.safetensors` + `rl_agent_config.json` + `encoder/` + `tokenizer/`). The `804 MB` `checkpoint_latest/` resumable training snapshot is stripped by `package_checkpoint.sh`. |
| **Recommended Runtime** | Python 3.12 (`2 GiB` or `4 GiB` RAM, `2 vCPU`, `concurrency=8`) |
| **Cold-Start Load Time** | ~6–10 seconds (loaded once per container instance in global scope `_AGENT`) |
| **Warm Latency** | **~50–150 ms** per request on CPU |
| **Supported Wire Formats** | Both **Laya Native** (`{"state": "...", "questions": {...}}`) and **`ms-decision-1` Compatible** (`{"input": "...", "questions": [...]}`) |

---

## 2. Step-by-Step Setup: Firebase Functions (2nd Gen, Recommended)

Firebase Functions 2nd Gen runs on Cloud Run under the hood, supporting up to `32 GiB` RAM, multi-request concurrency, and Cloud Storage bucket mounts/downloads.

### Step 1 — Stage the `804 MB` Inference Checkpoint
Run `package_checkpoint.sh` to strip `checkpoint_latest/` and optionally upload the clean `804 MB` weights to your Firebase / Google Cloud Storage bucket (recommended so `firebase deploy` uploads only code and pulls weights at cold start into `/tmp/laya_sports_ckpt`):

```bash
cd deploy/firebase_laya
chmod +x package_checkpoint.sh

# Option A: Stage locally + upload to your Firebase/GCS bucket (recommended for fast deploys)
./package_checkpoint.sh gs://<your-firebase-project>.appspot.com/models/laya_sports_ckpt

# Option B: Stage locally inside functions/laya_sports_ckpt (bundled directly)
./package_checkpoint.sh
```

### Step 2 — Configure Your Firebase Project ID
Update [`.firebaserc`](./.firebaserc) with your Firebase project ID:
```json
{
  "projects": {
    "default": "your-firebase-project-id"
  }
}
```

### Step 3 — Test Locally with Functions Framework or Firebase Emulator
```bash
cd deploy/firebase_laya/functions
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# Run local HTTP server on port 8085
LAYA_CKPT_DIR="../../../data/laya_sports_ckpt" \
  .venv/bin/functions-framework --target=laya_sports_decisions --port=8085
```

Test a live request against the local endpoint:
```bash
curl -s -X POST http://127.0.0.1:8085 \
  -H "Content-Type: application/json" \
  -d '{
    "state": "PSG star Khvicha Kvaratskhelia ruptures ACL; Dembele and Marquinhos ruled out for weeks.",
    "questions": {
      "negative_impact": {
        "type": "noul",
        "instructions": "Does this news report a key player injured, suspended, ruled out, or team crisis that hurts win probability?"
      }
    }
  }' | jq
```

### Step 4 — Deploy to Firebase Functions (2nd Gen)
```bash
cd deploy/firebase_laya
firebase deploy --only functions
```
If using the GCS bucket option (`Option A`), set `LAYA_GCS_URI` (and optional `LAYA_API_TOKEN`):
```bash
gcloud functions deploy laya-sports-decisions \
  --gen2 \
  --runtime=python312 \
  --region=europe-west1 \
  --source=./functions \
  --entry-point=laya_sports_decisions \
  --trigger-http \
  --memory=2Gi \
  --cpu=2 \
  --concurrency=8 \
  --timeout=60s \
  --set-env-vars="LAYA_GCS_URI=gs://<your-firebase-project>.appspot.com/models/laya_sports_ckpt,LAYA_API_TOKEN=<your-secret-token>"
```

---

## 3. Connecting `sportdata-model` to Your Hosted Function

`src/sportdata_model/decision_signal.py` natively supports your deployed Firebase / GCP Cloud Function via `LAYA_REMOTE_URL` (and optional `LAYA_REMOTE_TOKEN`):

```bash
export LAYA_REMOTE_URL="https://europe-west1-<your-project>.cloudfunctions.net/laya_sports_decisions"
export LAYA_REMOTE_TOKEN="<your-secret-token>"

# Runs using the hosted Firebase/GCP Laya function automatically!
uv run sportdata-model
```
When `LAYA_REMOTE_URL` is unset, `sportdata-model` automatically uses the local [`data/laya_sports_ckpt`](../../data/laya_sports_ckpt) checkpoint via a persistent warm worker process.
