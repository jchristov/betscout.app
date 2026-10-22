#!/usr/bin/env bash
# Prepare the fine-tuned `data/laya_sports_ckpt` checkpoint for Firebase / GCP Cloud Functions deployment.
# Copies only the 804 MB inference artifacts (excluding the 804 MB `checkpoint_latest/` training state)
# and optionally uploads them to a Google Cloud Storage / Firebase Storage bucket.
#
# Usage:
#   ./package_checkpoint.sh                           # Stage 804 MB bundle into ./functions/laya_sports_ckpt
#   ./package_checkpoint.sh gs://my-bucket/laya-ckpt  # Stage + upload to GCS for fast serverless cold starts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_CKPT="${MODEL_ROOT}/data/laya_sports_ckpt"
DEST_CKPT="${SCRIPT_DIR}/functions/laya_sports_ckpt"

if [[ ! -f "${SRC_CKPT}/model.safetensors" ]]; then
  echo "Error: ${SRC_CKPT}/model.safetensors not found. Run scripts/distill_laya_sports.py --finetune first." >&2
  exit 1
fi

echo "[1/2] Staging inference-only Laya Sports checkpoint into ${DEST_CKPT} ..."
rm -rf "${DEST_CKPT}"
mkdir -p "${DEST_CKPT}"

cp "${SRC_CKPT}/model.safetensors" "${DEST_CKPT}/"
cp "${SRC_CKPT}/rl_agent_config.json" "${DEST_CKPT}/"
[[ -f "${SRC_CKPT}/questions.json" ]] && cp "${SRC_CKPT}/questions.json" "${DEST_CKPT}/"
cp -R "${SRC_CKPT}/encoder" "${DEST_CKPT}/encoder"
cp -R "${SRC_CKPT}/tokenizer" "${DEST_CKPT}/tokenizer"

BUNDLE_SIZE="$(du -sh "${DEST_CKPT}" | awk '{print $1}')"
echo "      Staged inference bundle size: ${BUNDLE_SIZE} (stripped checkpoint_latest/ training state)"

if [[ $# -ge 1 && "$1" == gs://* ]]; then
  GCS_URI="${1%/}"
  echo "[2/2] Uploading inference bundle to ${GCS_URI} ..."
  gcloud storage rsync --recursive "${DEST_CKPT}" "${GCS_URI}"
  echo "      Uploaded to ${GCS_URI}"
else
  echo "[2/2] Local staging complete. Pass a gs://<bucket>/path argument to also upload to GCS."
fi
