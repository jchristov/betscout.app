"""Harvest sports news headlines from cached ESPN summaries and live league feeds,
label them with `ms-decision-1` (teacher model) into `data/decision_training_pairs.jsonl`,
and optionally fine-tune a local `Laya` checkpoint (`data/laya_sports_ckpt`).

Usage:
    uv run python scripts/distill_laya_sports.py --limit 60
    uv run python scripts/distill_laya_sports.py --limit 120 --finetune --epochs 2
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.decision_signal import (  # noqa: E402
    DEFAULT_TRAINING_PAIRS_PATH,
    LAYA_CKPT,
    LAYA_DIR,
    LAYA_SPORTS_CKPT,
    MS_DECISION_URL,
    _get_rbi_token,
    build_laya_match_questions,
    extract_team_news_text,
    score_with_ms_decision_1,
)
from sportdata_model.espn import ALL_LEAGUES, BASE  # noqa: E402

SPORTS_HEADLINE_QUESTIONS_LAYA: dict[str, dict[str, Any]] = {
    "event": {
        "type": "choice",
        "instructions": "What kind of sports news is this headline?",
        "criteria": {
            "injury_out": "key player injured, suspended, ruled out, surgery, illness",
            "return_boost": "player returning from injury, fit to play, cleared, boost",
            "crisis": "managerial sacking, dressing room crisis, points deduction, slump",
            "momentum": "winning streak, record broken, dominant form, morale high",
            "other": "transfer rumors, general preview, ceremony, unrelated news",
        },
    },
    "negative_impact": {
        "type": "noul",
        "instructions": "Does this news report a key player injured, suspended, ruled out, or team crisis that hurts win probability?",
    },
    "positive_impact": {
        "type": "noul",
        "instructions": "Does this news report a key player returning fit, lineup boost, or strong positive momentum?",
    },
}

SPORTS_HEADLINE_QUESTIONS_MS: list[dict[str, Any]] = [
    {
        "type": "choice",
        "name": "event",
        "instructions": "What kind of sports news is this headline?",
        "choices": [
            {"value": "injury_out", "description": "key player injured, suspended, ruled out, surgery, illness"},
            {"value": "return_boost", "description": "player returning from injury, fit to play, cleared, boost"},
            {"value": "crisis", "description": "managerial sacking, dressing room crisis, points deduction, slump"},
            {"value": "momentum", "description": "winning streak, record broken, dominant form, morale high"},
            {"value": "other", "description": "transfer rumors, general preview, ceremony, unrelated news"},
        ],
    },
    {
        "type": "predicate",
        "name": "negative_impact",
        "instructions": "Does this news report a key player injured, suspended, ruled out, or team crisis that hurts win probability?",
    },
    {
        "type": "predicate",
        "name": "positive_impact",
        "instructions": "Does this news report a key player returning fit, lineup boost, or strong positive momentum?",
    },
]


def harvest_sports_headlines(max_items: int = 120) -> list[str]:
    """Harvest unique sports headlines + descriptions from cached ESPN summaries first."""
    seen: set[str] = set()
    texts: list[str] = []
    cache_dir = ROOT / "data" / "cache"
    if cache_dir.exists():
        sum_files = sorted(
            (p for p in cache_dir.iterdir() if p.name.startswith("sum_") and p.name.endswith(".json")),
            reverse=True,
        )
        for p in sum_files[:1200]:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            tag = p.stem.split("_")[1] if "_" in p.stem else "sport"
            for art in ((d.get("news") or {}).get("articles")) or []:
                hl = (art.get("headline") or "").strip()
                desc = (art.get("description") or "").strip()
                if not hl:
                    continue
                combined = f"[{tag}] {hl}. {desc}".strip()
                if combined not in seen:
                    seen.add(combined)
                    texts.append(combined)
                    if len(texts) >= max_items:
                        return texts
            prev = ((d.get("article") or {}).get("headline") or "").strip()
            if prev:
                combined = f"[{tag}] {prev}".strip()
                if combined not in seen:
                    seen.add(combined)
                    texts.append(combined)
                    if len(texts) >= max_items:
                        return texts
    return texts


def label_headline_with_teacher(text: str, token: str) -> dict[str, Any] | None:
    payload = {
        "model": "ms-decision-1",
        "input": text,
        "questions": SPORTS_HEADLINE_QUESTIONS_MS,
    }
    proc = subprocess.run(
        [
            "curl", "-s", "-f", "-m", "20", "-X", "POST", MS_DECISION_URL,
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        data = json.loads(proc.stdout)
        gold: dict[str, Any] = {}
        expected: dict[str, Any] = {}
        for ans in data.get("answers") or []:
            name = ans["name"]
            if ans["type"] == "choice":
                probs = {p["value"]: round(float(p["probability"]), 6) for p in ans.get("probabilities", [])}
                gold[name] = {"probabilities": probs}
                expected[name] = ans["choice"]
            else:
                p = max(0.0, min(1.0, float(ans["probability"])))
                gold[name] = {"probabilities": {"false": round(1.0 - p, 6), "true": round(p, 6)}}
                expected[name] = bool(p >= 0.5)
        return {
            "state": text,
            "questions": SPORTS_HEADLINE_QUESTIONS_LAYA,
            "gold": gold,
            "expected": expected,
            "meta": {"teacher": "ms-decision-1"},
        }
    except Exception:
        return None


def harvest_match_news_contexts(max_items: int = 80) -> list[tuple[str, str, str]]:
    """Harvest real (text, home, away) match news contexts from cached ESPN summaries."""
    seen: set[str] = set()
    items: list[tuple[str, str, str]] = []
    cache_dir = ROOT / "data" / "cache"
    if not cache_dir.exists():
        return items
    sum_files = sorted(
        (p for p in cache_dir.iterdir() if p.name.startswith("sum_") and p.name.endswith(".json")),
        reverse=True,
    )
    for p in sum_files[:2500]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        comps = (d.get("header") or {}).get("competitions") or []
        if not comps:
            continue
        competitors = comps[0].get("competitors") or []
        if len(competitors) != 2:
            continue
        home_c = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_c = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        home = ((home_c.get("team") or {}).get("displayName") or "").strip()
        away = ((away_c.get("team") or {}).get("displayName") or "").strip()
        if not home or not away:
            continue
        text, matched = extract_team_news_text(d, home, away)
        if not matched or text in seen:
            continue
        seen.add(text)
        items.append((text, home, away))
        if len(items) >= max_items:
            break
    return items


def build_distillation_dataset(
    pairs_path: Path = DEFAULT_TRAINING_PAIRS_PATH,
    limit: int = 80,
    workers: int = 6,
) -> list[dict[str, Any]]:
    existing_rows: list[dict[str, Any]] = []
    seen_states: set[str] = set()
    if pairs_path.exists():
        for line in pairs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                existing_rows.append(r)
                seen_states.add(r.get("state", ""))
            except Exception:
                continue

    tok = _get_rbi_token("uat")
    if tok:
        raw_texts = [t for t in harvest_sports_headlines(max_items=limit) if t not in seen_states]
        if raw_texts:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                labeled = list(pool.map(lambda t: label_headline_with_teacher(t, tok), raw_texts))
            new_rows = [r for r in labeled if r is not None]
            if new_rows:
                pairs_path.parent.mkdir(parents=True, exist_ok=True)
                with pairs_path.open("a", encoding="utf-8") as f:
                    for r in new_rows:
                        f.write(json.dumps(r) + "\n")
                existing_rows.extend(new_rows)
                seen_states.update(r["state"] for r in new_rows)

        # Filter out mixed-schema rows so Laya trains cleanly on SPORTS_HEADLINE_QUESTIONS_LAYA
        existing_rows = [
            json.loads(line)
            for line in pairs_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and "negative_impact" in json.loads(line).get("questions", {})
        ]
    return existing_rows


def run_laya_finetune(
    rows: list[dict[str, Any]],
    epochs: int = 2,
    dry_run: bool = False,
) -> int:
    laya_py = LAYA_DIR / ".venv" / "bin" / "python"
    if not (laya_py.exists() and LAYA_CKPT.exists()):
        print("Laya environment or base checkpoint not found.")
        return 1

    train_path = ROOT / "data" / "laya_sports_train.jsonl"
    val_path = ROOT / "data" / "laya_sports_val.jsonl"
    cut = max(1, int(len(rows) * 0.8))
    train_rows, val_rows = rows[:cut], rows[cut:]
    train_path.write_text("\n".join(json.dumps(r) for r in train_rows) + "\n", encoding="utf-8")
    val_path.write_text("\n".join(json.dumps(r) for r in val_rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(train_rows)} train rows -> {train_path} and {len(val_rows)} val rows -> {val_path}")

    cmd = [
        str(laya_py), "-m", "laya.train_cli",
        "--data", str(train_path),
        "--eval", str(val_path),
        "--base", str(LAYA_CKPT),
        "--out", str(LAYA_SPORTS_CKPT),
        "--epochs", str(epochs),
        "--loss", "soft-ce",
        "--freeze-encoder",
    ]
    if dry_run:
        cmd.append("--dry-run")
    env = {**os.environ, "HF_HUB_OFFLINE": "1"}
    proc = subprocess.run(cmd, env=env)
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Distill ms-decision-1 sports labels into Laya dataset & checkpoint.")
    parser.add_argument("--limit", type=int, default=80, help="Max sports headlines to harvest & label (default: 80)")
    parser.add_argument("--finetune", action="store_true", help="Run Laya head fine-tuning on the distilled dataset")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset with laya.train_cli --dry-run")
    parser.add_argument("--epochs", type=int, default=2, help="Epochs for Laya fine-tuning (default: 2)")
    args = parser.parse_args()

    rows = build_distillation_dataset(limit=args.limit)
    print(f"Total teacher-labeled sports rows in {DEFAULT_TRAINING_PAIRS_PATH}: {len(rows)}")
    if args.dry_run or args.finetune:
        run_laya_finetune(rows, epochs=args.epochs, dry_run=args.dry_run and not args.finetune)


if __name__ == "__main__":
    main()
