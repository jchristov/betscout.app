"""Evaluate the Football Feature-Adjusted Dixon-Coles Exact Score & Cluster Model
and the Tennis Calibrated Set-Score (`2:0` / `2:1`) Model out-of-sample.

Usage:
    uv run python scripts/exact_score_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.exact_score import evaluate_exact_score_models  # noqa: E402


def main() -> None:
    db_path = ROOT / "data" / "betscout.db"
    res = evaluate_exact_score_models(db_path)
    se = res["soccer_exact_score"]
    te = res["tennis_set_score"]

    print("=== 1. Football Exact Score & Score-Cluster Out-of-Sample Evaluation (Post-2025 Holdout, Big-5) ===")
    print(
        f"  Top 15% Picks (n={se['post25_top15_n']:<3}) | 1X2 Win: {se['post25_top15_1x2_hit']*100:.1f}% | "
        f"Top-1 Exact Score Hit: {se['post25_top15_top1_hit']*100:.1f}% | "
        f"2-Score Cluster Hit: {se['post25_top15_cluster2_hit']*100:.1f}% | "
        f"3-Score Cluster Hit: {se['post25_top15_cluster3_hit']*100:.1f}%"
    )
    print(
        f"  Top 10% Picks (n={se['post25_top10_n']:<3}) | 1X2 Win: {se['post25_top10_1x2_hit']*100:.1f}% | "
        f"Top-1 Exact Score Hit: {se['post25_top10_top1_hit']*100:.1f}% | "
        f"2-Score Cluster Hit: {se['post25_top10_cluster2_hit']*100:.1f}% | "
        f"3-Score Cluster Hit: {se['post25_top10_cluster3_hit']*100:.1f}% "
        f"(Mean Model Cluster-3 Prob: {se['post25_top10_mean_cluster3_prob']*100:.1f}%)"
    )

    print("\n=== 2. Tennis Exact Set-Score (`2:0` Straight Sets) Out-of-Sample Evaluation ===")
    for tour, m in te.items():
        print(
            f"  {tour.upper():<4} (n={m['oos_bo3_n']}) | 2:0 Brier={m['brier_2_0']:.4f} | "
            f"WinProb>=70% (n={m['hc70_n']}): Actual 2:0={m['hc70_actual_2_0_rate']*100:.1f}% vs Model={m['hc70_pred_2_0_prob']*100:.1f}% | "
            f"WinProb>=80% (n={m['hc80_n']}): Actual 2:0={m['hc80_actual_2_0_rate']*100:.1f}% vs Model={m['hc80_pred_2_0_prob']*100:.1f}%"
        )

    out_json = ROOT / "data" / "exact_score_eval.json"
    out_json.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved evaluation report -> {out_json}")


if __name__ == "__main__":
    main()
