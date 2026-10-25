"""Post-Match Model Calibration, Brier Skill Score & Factor Attribution Monitor (`scripts/calibration_report.py`).

Run:
    uv run betscout-calibrate
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.paper_trade import _open_db, settle_pending_paper_trades  # noqa: E402


def compute_calibration_report(db_path: Path) -> dict[str, Any]:
    """Compute Brier Score, Brier Skill Score (vs market implied), Expected Calibration Error (ECE),
    and per-factor attribution across all settled `paper_trades`."""
    if not db_path.exists():
        return {"settled_count": 0}
    try:
        settle_pending_paper_trades(db_path)
    except Exception:
        pass

    conn = _open_db(db_path)
    conn.row_factory = sqlite3.Row
    settled = [
        dict(r)
        for r in conn.execute("SELECT * FROM paper_trades WHERE status = 'SETTLED' ORDER BY kickoff ASC").fetchall()
    ]
    conn.close()
    if not settled:
        return {"settled_count": 0}

    y_true = np.array([1.0 if float(r.get("pnl_best") or 0.0) > 0 else 0.0 for r in settled])
    # Model probability estimate vs Market implied probability
    p_mod_list = []
    p_mkt_list = []
    for r in settled:
        lg = str(r["league"]).lower()
        comp_sc = float(r.get("composite_score") or 0.65)
        p_m_raw = float(r.get("p_mkt") or 0.65)
        o_pri = max(float(r.get("logged_primary_odds") or r.get("logged_best_odds") or 1.35), 1.05)
        mkt_imp = min(max(1.0 / (o_pri * 1.03), 0.15), 0.95)
        if lg in ("atp", "wta", "nba", "nhl", "nfl", "mlb") and 0.45 <= comp_sc <= 0.99:
            p_mod = comp_sc
        else:
            p_mod = min(max(p_m_raw + 0.04, 0.45), 0.92)
        p_mod_list.append(p_mod)
        p_mkt_list.append(mkt_imp)

    p_mod_arr = np.array(p_mod_list)
    p_mkt_arr = np.array(p_mkt_list)

    brier_model = float(np.mean((p_mod_arr - y_true) ** 2))
    brier_market = float(np.mean((p_mkt_arr - y_true) ** 2))
    brier_clim = float(np.mean((np.mean(y_true) - y_true) ** 2))
    bss_vs_market = round(1.0 - (brier_model / max(brier_market, 1e-6)), 4)

    # 3-bin Expected Calibration Error (ECE)
    bins = [(0.50, 0.70), (0.70, 0.80), (0.80, 1.01)]
    ece = 0.0
    bin_rows = []
    for lo, hi in bins:
        mask = (p_mod_arr >= lo) & (p_mod_arr < hi)
        cnt = int(np.sum(mask))
        if cnt == 0:
            continue
        pred_m = float(np.mean(p_mod_arr[mask]))
        act_m = float(np.mean(y_true[mask]))
        ece += (cnt / len(y_true)) * abs(act_m - pred_m)
        bin_rows.append({
            "bucket": f"{int(lo*100)}–{min(int(hi*100), 100)}%",
            "count": cnt,
            "pred_win_pct": round(pred_m * 100.0, 1),
            "actual_win_pct": round(act_m * 100.0, 1),
            "delta_pp": round((act_m - pred_m) * 100.0, 1),
        })

    # Per-factor attribution from factor_breakdown_json
    factor_pnls: dict[str, list[float]] = defaultdict(list)
    factor_vals_win: dict[str, list[float]] = defaultdict(list)
    for r, won in zip(settled, y_true):
        try:
            fb = json.loads(r.get("factor_breakdown_json") or "{}")
        except Exception:
            fb = {}
        pnl = float(r.get("pnl_best") or 0.0)
        for fk, fv in fb.items():
            if fk == "h2h_n" or not isinstance(fv, (int, float)):
                continue
            if float(fv) > 0:
                factor_pnls[fk].append(pnl)
                factor_vals_win[fk].append(1.0 if won > 0.5 else 0.0)

    factor_summary = [
        {
            "factor": fk,
            "positive_picks": len(vals),
            "win_rate_pct": round(float(np.mean(factor_vals_win[fk])) * 100.0, 1),
            "profit_u": round(float(np.sum(vals)), 2),
            "roi_pct": round(float(np.mean(vals)) * 100.0, 1),
        }
        for fk, vals in sorted(factor_pnls.items(), key=lambda kv: -sum(kv[1]))
        if len(vals) >= 2
    ]

    report = {
        "settled_count": len(settled),
        "wins": int(np.sum(y_true)),
        "losses": int(len(settled) - np.sum(y_true)),
        "win_rate_pct": round(float(np.mean(y_true)) * 100.0, 1),
        "mean_pred_prob_pct": round(float(np.mean(p_mod_arr)) * 100.0, 1),
        "mean_mkt_prob_pct": round(float(np.mean(p_mkt_arr)) * 100.0, 1),
        "brier_model": round(brier_model, 4),
        "brier_market": round(brier_market, 4),
        "brier_climatology": round(brier_clim, 4),
        "brier_skill_vs_market": bss_vs_market,
        "ece": round(float(ece), 4),
        "calibration_bins": bin_rows,
        "factor_attribution": factor_summary,
    }
    out_path = db_path.parent / "calibration_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    db_path = ROOT / "data" / "matches.sqlite"
    rep = compute_calibration_report(db_path)
    print(f"=== VektorPulse Post-Match Calibration & Attribution Monitor (n={rep.get('settled_count', 0)} Settled) ===")
    if not rep.get("settled_count"):
        print("No settled bets yet.")
        return
    print(
        f"  Realized Win Rate: {rep['win_rate_pct']:.1f}% ({rep['wins']}W - {rep['losses']}L) | "
        f"Model Pred: {rep['mean_pred_prob_pct']:.1f}% | Market Implied: {rep['mean_mkt_prob_pct']:.1f}%"
    )
    print(
        f"  Brier Score (Model): {rep['brier_model']:.4f} vs Market: {rep['brier_market']:.4f} "
        f"(Brier Skill Score vs Market: {rep['brier_skill_vs_market']:+.2%}) | ECE: {rep['ece']:.4f}"
    )
    print("\n  Calibration Bins:")
    for b in rep.get("calibration_bins") or []:
        print(f"    {b['bucket']:<10} | n={b['count']:<3} | Pred={b['pred_win_pct']:5.1f}% -> Actual={b['actual_win_pct']:5.1f}% ({b['delta_pp']:+.1f}pp)")
    print("\n  Positive-Factor Attribution:")
    for f in rep.get("factor_attribution") or []:
        print(f"    {f['factor']:<18} | n={f['positive_picks']:<3} | WinRate={f['win_rate_pct']:5.1f}% | Profit={f['profit_u']:+.2f}u (ROI {f['roi_pct']:+.1f}%)")


if __name__ == "__main__":
    main()
