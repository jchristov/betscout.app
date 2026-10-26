"""View and export Settled and Pending Paper-Bets from `data/betscout.db`.

Usage:
    uv run betscout-ledger                 # Print Settled & Pending paper bets + summary
    uv run betscout-ledger --settled-only  # Show only SETTLED paper bets
    uv run betscout-ledger --export-csv data/settled_bets.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.espn import LEAGUE_LABELS  # noqa: E402
from betscout.paper_trade import get_paper_ledger_summary, settle_pending_paper_trades  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and export Settled and Pending paper bets.")
    parser.add_argument("--settled-only", action="store_true", help="Display only SETTLED paper bets")
    parser.add_argument(
        "--export-csv",
        type=Path,
        default=ROOT / "data" / "settled_bets.csv",
        help="Path to export settled paper bets CSV (default: data/settled_bets.csv)",
    )
    args = parser.parse_args()

    db_path = ROOT / "data" / "betscout.db"
    newly_settled = settle_pending_paper_trades(db_path)
    summary = get_paper_ledger_summary(db_path)

    trades = summary.get("trades") or []
    settled = [t for t in trades if t["status"] == "SETTLED"]
    pending = [t for t in trades if t["status"] == "PENDING"]

    roi_pct = (summary["settled_roi_best"] * 100.0) if summary.get("settled_roi_best") is not None else 0.0
    print(
        f"Paper-Betting Ledger Summary: Total={summary['total_logged']} | "
        f"Settled={summary['settled_count']} (Wins={summary.get('settled_wins', 0)}, Losses={summary.get('settled_losses', 0)}, "
        f"Profit={summary.get('settled_profit_u', 0.0):+.2f}u, ROI={roi_pct:+.2f}%) | "
        f"Pending={summary['pending_count']} | Newly Settled This Run={newly_settled}"
    )

    print("\n=== SETTLED PAPER BETS ===")
    if settled:
        print(f"{'Date (UTC)':<18}{'League':<24}{'Match':<38}{'Pick':<26}{'Score':<8}{'Odds':>7}{'Result / PnL':>16}")
        print("-" * 137)
        for t in settled:
            lg_name = LEAGUE_LABELS.get(t["league"], t["league"].upper())[:22]
            match_str = f"{t['home']} vs {t['away']}"[:36]
            pick_team = t["home"] if t["side"] == "H" else t["away"]
            pick_str = f"{pick_team} ({t['side']})"[:24]
            res_str = f"WIN ({t['pnl_best']:+.2f}u)" if (t["pnl_best"] or 0) > 0 else f"LOSS ({t['pnl_best']:+.2f}u)"
            print(
                f"{t['kickoff']:<18}{lg_name:<24}{match_str:<38}{pick_str:<26}"
                f"{t['score_str']:<8}{t['logged_best_odds']:>7.2f}{res_str:>16}"
            )
    else:
        print("  (No settled paper bets yet)")

    if args.export_csv:
        args.export_csv.parent.mkdir(parents=True, exist_ok=True)
        cols = ["kickoff", "league", "home", "away", "side", "tier", "score_str", "logged_best_odds", "clv_pct", "status", "settled_outcome", "pnl_best"]
        with args.export_csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols)
            writer.writeheader()
            for t in settled:
                writer.writerow({c: t.get(c) for c in cols})
        print(f"\nExported settled paper bets CSV (with header): {args.export_csv}")

    if not args.settled_only and pending:
        print(f"\n=== PENDING PAPER BETS (Next {min(len(pending), 15)} of {len(pending)}) ===")
        print(f"{'Date (UTC)':<18}{'League':<24}{'Match':<38}{'Pick':<26}{'Odds':>7}{'Status':>10}")
        print("-" * 123)
        for t in pending[:15]:
            lg_name = LEAGUE_LABELS.get(t["league"], t["league"].upper())[:22]
            match_str = f"{t['home']} vs {t['away']}"[:36]
            pick_team = t["home"] if t["side"] == "H" else t["away"]
            pick_str = f"{pick_team} ({t['side']})"[:24]
            print(f"{t['kickoff']:<18}{lg_name:<24}{match_str:<38}{pick_str:<26}{t['logged_best_odds']:>7.2f}{'PENDING':>10}")


if __name__ == "__main__":
    main()
