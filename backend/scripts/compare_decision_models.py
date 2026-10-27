"""Head-to-head benchmark comparing `ms-decision-1` (Microsoft Decision-1 teacher) vs
Base `Laya` (`typed-decisions`) vs Sports-Fine-Tuned `Laya` (`data/laya_sports_ckpt`).

Evaluates:
  1. Held-out validation dataset (`data/laya_sports_val.jsonl`): Accuracy, Cross-Entropy Loss,
     Brier Score, Expected Calibration Error (ECE), Mean Confidence, and Warm Latency (ms/item).
  2. Match-level (`home_positive`, `home_negative`, `away_positive`, `away_negative`) agreement,
     `net_edge` correlation, and Injury Veto Gate (`net_edge <= -0.50`) concordance on real
     sports news cases (including PSG injury crisis, Bayern momentum, AC Milan boost, etc.).

Usage:
    uv run python scripts/compare_decision_models.py
    uv run python scripts/compare_decision_models.py --export-json data/decision_model_comparison.json
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "data").exists() else Path(__file__).resolve().parents[1]

from betscout.decision_signal import (  # noqa: E402
    LAYA_CKPT,
    LAYA_RUN,
    LAYA_SPORTS_CKPT,
    score_with_laya,
    score_with_ms_decision_1,
)

CURATED_MATCH_CASES: list[dict[str, Any]] = [
    {
        "label": "PSG vs Lyon (Major Home ACL/Injury Crisis)",
        "home": "Paris Saint-Germain",
        "away": "Lyon",
        "side": "H",
        "expected_veto": True,
        "text": (
            "Match: Paris Saint-Germain (Home) vs Lyon (Away).\n"
            "- PSG star Khvicha Kvaratskhelia ruptures ACL; Ousmane Dembélé and captain Marquinhos ruled out for weeks."
        ),
    },
    {
        "label": "Udinese vs AC Milan (Away Captain Returns + Boost)",
        "home": "Udinese",
        "away": "AC Milan",
        "side": "A",
        "expected_veto": False,
        "text": (
            "Match: Udinese (Home) vs AC Milan (Away).\n"
            "- AC Milan captain returns to full training and is cleared to start ahead of Udinese trip.\n"
            "- Udinese missing two suspended defenders."
        ),
    },
    {
        "label": "Freiburg vs Bayern Munich (Away Dominant Streak)",
        "home": "SC Freiburg",
        "away": "Bayern Munich",
        "side": "A",
        "expected_veto": False,
        "text": (
            "Match: SC Freiburg (Home) vs Bayern Munich (Away).\n"
            "- Bayern Munich ride 6-match winning streak with Harry Kane in record-breaking scoring form."
        ),
    },
    {
        "label": "Arsenal vs Chelsea (Home Star Ruled Out, Away Star Fit)",
        "home": "Arsenal",
        "away": "Chelsea",
        "side": "H",
        "expected_veto": True,
        "text": (
            "Match: Arsenal (Home) vs Chelsea (Away).\n"
            "- Arsenal stars Bukayo Saka and Martin Odegaard ruled out of Chelsea clash with hamstring injuries.\n"
            "- Chelsea star Cole Palmer returns fit and starts for Chelsea."
        ),
    },
    {
        "label": "Real Madrid vs Sevilla (Home Managerial Crisis & Suspensions)",
        "home": "Real Madrid",
        "away": "Sevilla",
        "side": "H",
        "expected_veto": True,
        "text": (
            "Match: Real Madrid (Home) vs Sevilla (Away).\n"
            "- Real Madrid hit by dressing-room crisis as Bellingham and Vinicius Jr suspended and three defenders injured."
        ),
    },
    {
        "label": "Neutral Preview (No Injury or Momentum Edge)",
        "home": "Brentford",
        "away": "Fulham",
        "side": "H",
        "expected_veto": False,
        "text": (
            "Match: Brentford (Home) vs Fulham (Away).\n"
            "- Kickoff time, referee assignment, and broadcast details confirmed for Saturday's West London derby."
        ),
    },
]


def evaluate_laya_on_val_split(val_path: Path) -> dict[str, dict[str, float]]:
    """Run both base `typed-decisions` and fine-tuned `laya_sports_ckpt` on `val_path` inside Laya's venv."""
    if not (LAYA_RUN.exists() and val_path.exists()):
        return {}
    eval_code = """
import json, math, sys, time
from laya import Agent

cfg = json.loads(sys.stdin.read())
rows = [json.loads(line) for line in open(cfg["val_path"], encoding="utf-8") if line.strip()]

results = {}
for name, ckpt in cfg["models"].items():
    t_load0 = time.perf_counter()
    agent = Agent(ckpt)
    load_s = time.perf_counter() - t_load0
    # Warmup call
    if rows:
        agent.predict(rows[0]["state"], rows[0]["questions"])

    n_items = 0
    correct = 0
    total_ce = 0.0
    total_brier = 0.0
    confs = []
    accs = []
    teacher_corrs_p = []
    student_corrs_p = []

    t0 = time.perf_counter()
    for r in rows:
        pred = agent.predict(r["state"], r["questions"])["answers"]
        for qid, qspec in r["questions"].items():
            if qid not in pred or qid not in r.get("gold", {}):
                continue
            gold_probs = r["gold"][qid]["probabilities"]
            exp = r["expected"][qid]
            ans = pred[qid]
            n_items += 1
            if qspec["type"] == "noul":
                p_true = max(1e-6, min(1.0 - 1e-6, float(ans["noul"])))
                g_true = float(gold_probs.get("true", 1.0 if exp else 0.0))
                pred_lbl = bool(p_true >= 0.5)
                is_corr = 1.0 if pred_lbl == bool(exp) else 0.0
                conf = p_true if pred_lbl else (1.0 - p_true)
                ce = -(g_true * math.log(p_true) + (1.0 - g_true) * math.log(1.0 - p_true))
                brier = (p_true - g_true) ** 2
                teacher_corrs_p.append(g_true)
                student_corrs_p.append(p_true)
            else:
                p_map = ans.get("probabilities") or {}
                pred_choice = ans.get("choice")
                is_corr = 1.0 if pred_choice == exp else 0.0
                conf = float(p_map.get(pred_choice, 0.5))
                ce = -sum(float(gp) * math.log(max(1e-6, float(p_map.get(k, 1e-6)))) for k, gp in gold_probs.items())
                brier = sum((float(p_map.get(k, 0.0)) - float(gp)) ** 2 for k, gp in gold_probs.items()) / max(1, len(gold_probs))
            correct += is_corr
            total_ce += ce
            total_brier += brier
            confs.append(conf)
            accs.append(is_corr)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # 10-bin ECE
    ece = 0.0
    for b in range(10):
        lo, hi = b / 10.0, (b + 1) / 10.0
        idx = [i for i, c in enumerate(confs) if (lo <= c < hi if b < 9 else lo <= c <= hi)]
        if idx:
            avg_c = sum(confs[i] for i in idx) / len(idx)
            avg_a = sum(accs[i] for i in idx) / len(idx)
            ece += (len(idx) / max(1, n_items)) * abs(avg_a - avg_c)

    # Pearson r with ms-decision-1 teacher probabilities on binary noul items
    corr = 0.0
    if len(teacher_corrs_p) >= 2:
        mt = sum(teacher_corrs_p) / len(teacher_corrs_p)
        ms = sum(student_corrs_p) / len(student_corrs_p)
        num = sum((a - mt) * (b - ms) for a, b in zip(teacher_corrs_p, student_corrs_p))
        den = math.sqrt(sum((a - mt) ** 2 for a in teacher_corrs_p) * sum((b - ms) ** 2 for b in student_corrs_p))
        corr = num / den if den > 1e-12 else 0.0

    results[name] = {
        "n_questions": n_items,
        "n_contexts": len(rows),
        "accuracy_vs_teacher": round(correct / max(1, n_items), 4),
        "soft_cross_entropy": round(total_ce / max(1, n_items), 4),
        "brier_vs_teacher": round(total_brier / max(1, n_items), 4),
        "ece": round(ece, 4),
        "mean_confidence": round(sum(confs) / max(1, n_items), 4),
        "pearson_r_with_teacher": round(corr, 4),
        "cold_load_sec": round(load_s, 2),
        "warm_ms_per_context": round(elapsed_ms / max(1, len(rows)), 1),
    }

print("COMPARE_VAL_JSON:" + json.dumps(results))
"""
    payload = {
        "val_path": str(val_path),
        "models": {
            "laya-base (typed-decisions)": str(LAYA_CKPT),
            "laya-sports (fine-tuned)": str(LAYA_SPORTS_CKPT),
        },
    }
    proc = subprocess.run(
        [str(LAYA_RUN), "-c", eval_code],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=180,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("COMPARE_VAL_JSON:"):
            return json.loads(line.split("COMPARE_VAL_JSON:", 1)[1])
    return {}


def evaluate_curated_match_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # Warm up Laya workers first so latency reflects warm inference
    if CURATED_MATCH_CASES:
        c0 = CURATED_MATCH_CASES[0]
        score_with_laya(c0["text"], c0["home"], c0["away"], ckpt_path=LAYA_CKPT)
        score_with_laya(c0["text"], c0["home"], c0["away"], ckpt_path=LAYA_SPORTS_CKPT)

    for case in CURATED_MATCH_CASES:
        text, home, away, side = case["text"], case["home"], case["away"], case["side"]

        t0 = time.perf_counter()
        sig_ms = score_with_ms_decision_1(text, home, away, log_training_pair=False)
        ms_lat = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        sig_base = score_with_laya(text, home, away, ckpt_path=LAYA_CKPT)
        base_lat = (time.perf_counter() - t1) * 1000.0

        t2 = time.perf_counter()
        sig_sports = score_with_laya(text, home, away, ckpt_path=LAYA_SPORTS_CKPT)
        sports_lat = (time.perf_counter() - t2) * 1000.0

        ms_edge = round(sig_ms.net_edge(side), 4) if sig_ms else None
        base_edge = round(sig_base.net_edge(side), 4) if sig_base else None
        sports_edge = round(sig_sports.net_edge(side), 4) if sig_sports else None

        rows.append({
            "label": case["label"],
            "side": side,
            "expected_veto": case["expected_veto"],
            "ms_decision_1": {
                "net_edge": ms_edge,
                "veto_triggered": bool(ms_edge is not None and ms_edge <= -0.50),
                "latency_ms": round(ms_lat, 1),
            },
            "laya_base": {
                "net_edge": base_edge,
                "veto_triggered": bool(base_edge is not None and base_edge <= -0.50),
                "latency_ms": round(base_lat, 1),
            },
            "laya_sports": {
                "net_edge": sports_edge,
                "veto_triggered": bool(sports_edge is not None and sports_edge <= -0.50),
                "latency_ms": round(sports_lat, 1),
            },
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ms-decision-1 vs Base Laya vs Sports-Fine-Tuned Laya.")
    parser.add_argument(
        "--export-json",
        type=str,
        default=str(ROOT / "data" / "decision_model_comparison.json"),
        help="Path to write JSON comparison report",
    )
    args = parser.parse_args()

    val_path = ROOT / "data" / "laya_sports_val.jsonl"
    val_metrics = evaluate_laya_on_val_split(val_path)
    case_results = evaluate_curated_match_cases()

    print("=== 1. Held-Out Validation Benchmark vs `ms-decision-1` Teacher (`data/laya_sports_val.jsonl`) ===")
    print(f"{'Model':<30} | {'Acc vs Teacher':>14} | {'Soft CE Loss':>12} | {'Brier':>8} | {'ECE':>8} | {'Pearson r':>9} | {'Warm ms/ctx':>11}")
    print("-" * 108)
    for m_name, m in val_metrics.items():
        print(
            f"{m_name:<30} | {m['accuracy_vs_teacher']*100:>13.2f}% | {m['soft_cross_entropy']:>12.4f} | "
            f"{m['brier_vs_teacher']:>8.4f} | {m['ece']:>8.4f} | {m['pearson_r_with_teacher']:>9.4f} | {m['warm_ms_per_context']:>9.1f}ms"
        )

    print("\n=== 2. Curated Match-Level Injury Veto & Edge Concordance (`net_edge` in [-1, +1], Veto <= -0.50) ===")
    print(f"{'Match Scenario':<45} | {'ExpVeto':>7} | {'ms-decision-1 (ms)':>20} | {'laya-base (ms)':>18} | {'laya-sports (ms)':>18}")
    print("-" * 118)
    for r in case_results:
        ms = r["ms_decision_1"]
        lb = r["laya_base"]
        ls = r["laya_sports"]
        ms_s = f"{ms['net_edge']:+.3f} ({'VETO' if ms['veto_triggered'] else 'KEEP'}, {ms['latency_ms']:.0f}ms)" if ms["net_edge"] is not None else "N/A"
        lb_s = f"{lb['net_edge']:+.3f} ({'VETO' if lb['veto_triggered'] else 'KEEP'}, {lb['latency_ms']:.0f}ms)" if lb["net_edge"] is not None else "N/A"
        ls_s = f"{ls['net_edge']:+.3f} ({'VETO' if ls['veto_triggered'] else 'KEEP'}, {ls['latency_ms']:.0f}ms)" if ls["net_edge"] is not None else "N/A"
        print(f"{r['label']:<45} | {str(r['expected_veto']):>7} | {ms_s:>20} | {lb_s:>18} | {ls_s:>18}")

    out_path = Path(args.export_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"validation_split_metrics": val_metrics, "curated_match_cases": case_results}, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved full comparison report -> {out_path}")


if __name__ == "__main__":
    main()
