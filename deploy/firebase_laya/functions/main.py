"""Firebase Cloud Function (2nd Gen Python 3.12) & GCP Cloud Function handler
for the fine-tuned `laya-sports` (`data/laya_sports_ckpt`) System-1 decision model.

Features:
  - Lazy global singleton (`_AGENT`) kept warm across invocations in the same instance
  - Loads checkpoint either from:
      1. Local bundled directory (`./laya_sports_ckpt` or `LAYA_CKPT_DIR`), OR
      2. Google Cloud Storage / Firebase Storage bucket (`LAYA_GCS_URI=gs://<bucket>/laya_sports_ckpt`)
         downloaded once on cold start into `/tmp/laya_sports_ckpt`
  - Accepts both:
      1. Laya native wire format: `{"state": "...", "questions": {"q1": {"type": "noul", ...}}}`
      2. `ms-decision-1` wire format: `{"input": "...", "questions": [{"name": "q1", "type": "predicate", ...}]}`
  - Optional Bearer token guard via `LAYA_API_TOKEN` environment variable.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from firebase_functions import https_fn, options

os.environ.setdefault("HF_HUB_OFFLINE", "1")

_AGENT: Any = None
_AGENT_CKPT_PATH: str | None = None


def _ensure_checkpoint_on_disk() -> Path:
    """Resolve checkpoint from local bundle or download once from GCS into `/tmp/laya_sports_ckpt`."""
    local_dir = Path(os.environ.get("LAYA_CKPT_DIR", Path(__file__).parent / "laya_sports_ckpt"))
    if (local_dir / "model.safetensors").exists():
        return local_dir

    tmp_dir = Path("/tmp/laya_sports_ckpt")
    if (tmp_dir / "model.safetensors").exists():
        return tmp_dir

    gcs_uri = os.environ.get("LAYA_GCS_URI", "").strip()
    if not gcs_uri.startswith("gs://"):
        raise RuntimeError(
            f"No checkpoint found at {local_dir} and LAYA_GCS_URI is not set. "
            "Run ./package_checkpoint.sh or set LAYA_GCS_URI=gs://<bucket>/laya_sports_ckpt."
        )

    from google.cloud import storage

    without_scheme = gcs_uri[len("gs://") :]
    bucket_name, _, prefix = without_scheme.partition("/")
    prefix = prefix.rstrip("/")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    if not blobs:
        raise RuntimeError(f"No objects found in {gcs_uri}")

    for blob in blobs:
        rel = blob.name[len(prefix) :].lstrip("/")
        if not rel or rel.startswith("checkpoint_latest/"):
            continue
        dest = tmp_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))

    return tmp_dir


def get_agent() -> Any:
    """Load `laya.Agent` once per warm Cloud Function / Cloud Run container instance."""
    global _AGENT, _AGENT_CKPT_PATH
    if _AGENT is not None:
        return _AGENT
    from laya import Agent

    ckpt_dir = _ensure_checkpoint_on_disk()
    _AGENT = Agent(str(ckpt_dir))
    _AGENT_CKPT_PATH = str(ckpt_dir)
    return _AGENT


def _normalize_questions(raw_questions: Any) -> tuple[dict[str, dict[str, Any]], bool]:
    """Support both Laya dict questions and `ms-decision-1` list-of-dicts questions."""
    if isinstance(raw_questions, dict):
        return raw_questions, False
    if isinstance(raw_questions, list):
        laya_q: dict[str, dict[str, Any]] = {}
        for item in raw_questions:
            name = item["name"]
            qtype = item.get("type", "predicate")
            if qtype in ("predicate", "noul"):
                laya_q[name] = {"type": "noul", "instructions": item["instructions"]}
            elif qtype == "choice":
                criteria = {c["value"]: c.get("description", c["value"]) for c in item.get("choices", [])}
                laya_q[name] = {"type": "choice", "instructions": item["instructions"], "criteria": criteria}
        return laya_q, True
    raise ValueError("`questions` must be a dict (Laya format) or list (ms-decision-1 format)")


@https_fn.on_request(
    memory=options.MemoryOption.GB_2,
    cpu=2,
    timeout_sec=60,
    min_instances=0,
    max_instances=4,
    concurrency=8,
)
def laya_sports_decisions(req: https_fn.Request) -> https_fn.Response:
    """HTTP entrypoint for Firebase Functions (2nd Gen) & GCP Cloud Functions."""
    if req.method == "GET" and req.path.endswith("/healthz"):
        return https_fn.Response(
            json.dumps({"status": "ok", "model": "laya-sports", "loaded": _AGENT is not None}),
            status=200,
            headers={"Content-Type": "application/json"},
        )

    expected_token = os.environ.get("LAYA_API_TOKEN", "").strip()
    if expected_token:
        auth_header = req.headers.get("Authorization", "")
        if auth_header != f"Bearer {expected_token}":
            return https_fn.Response(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                headers={"Content-Type": "application/json"},
            )

    try:
        body = req.get_json(silent=True) or {}
        text = (body.get("state") or body.get("input") or "").strip()
        raw_questions = body.get("questions")
        if not text or not raw_questions:
            return https_fn.Response(
                json.dumps({"error": "Both `state` (or `input`) and `questions` are required."}),
                status=400,
                headers={"Content-Type": "application/json"},
            )

        laya_questions, is_ms_format = _normalize_questions(raw_questions)
        t0 = time.perf_counter()
        agent = get_agent()
        pred = agent.predict(text, laya_questions)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        if is_ms_format:
            ms_answers = []
            for name, ans in (pred.get("answers") or {}).items():
                if "noul" in ans:
                    ms_answers.append({"type": "predicate", "name": name, "probability": float(ans["noul"])})
                else:
                    probs = [
                        {"value": k, "probability": float(v)}
                        for k, v in (ans.get("probabilities") or {}).items()
                    ]
                    ms_answers.append({
                        "type": "choice",
                        "name": name,
                        "choice": ans.get("choice"),
                        "probabilities": probs,
                        "confidence": float(ans.get("confidence", 0.0)),
                    })
            resp_payload = {
                "model": "laya-sports",
                "answers": ms_answers,
                "latency_ms": latency_ms,
                "usage": pred.get("usage", {}),
            }
        else:
            resp_payload = {
                "model": "laya-sports",
                "answers": pred.get("answers", {}),
                "latency_ms": latency_ms,
                "usage": pred.get("usage", {}),
            }

        return https_fn.Response(
            json.dumps(resp_payload),
            status=200,
            headers={"Content-Type": "application/json"},
        )
    except Exception as exc:
        return https_fn.Response(
            json.dumps({"error": str(exc)}),
            status=500,
            headers={"Content-Type": "application/json"},
        )
