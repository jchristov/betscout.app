"""CLI runner for pre-kickoff paper-betting, prospective CLV tracking, decision-model news scoring,
and exporting `data/recommendations.json`.

Usage:
    uv run betscout-bet
    uv run betscout-bet --days 6 --decision-backend ms-decision-1
    uv run betscout-bet --days 6 --decision-backend laya
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "data").exists() else Path(__file__).resolve().parents[1]

from betscout.paper_bet import scan_upcoming_and_log_paper_bets  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan upcoming fixtures, score 7-factor composite + news, log paper bets.")
    parser.add_argument("--days", type=int, default=5, help="Number of days ahead to scan (default: 5)")
    parser.add_argument(
        "--decision-backend",
        choices=("laya", "laya-sports", "laya-base", "ms-decision-1", "auto", "none"),
        default="laya",
        help="Decision model backend for injury/preview news scoring (default: laya)",
    )
    args = parser.parse_args()

    db_path = ROOT / "data" / "betscout.db"
    out_json = ROOT / "data" / "recommendations.json"

    rep = scan_upcoming_and_log_paper_bets(
        db_path=db_path,
        days_ahead=args.days,
        decision_backend=args.decision_backend,
        export_json_path=out_json,
    )

    print(f"Evaluated upcoming Big-5 fixtures: {rep['evaluated_upcoming_count']} | Qualifying picks: {rep['qualifying_picks_count']}")
    print(f"Thresholds (tanh(Z)): {rep['thresholds']}")
    print(f"Paper Ledger: {rep['paper_ledger']}")
    print(f"Exported JSON feed to: {out_json}\n")

    if rep["qualifying_picks"]:
        print("=== Qualifying Upcoming Paper-Bet Picks ===")
        for p in rep["qualifying_picks"]:
            ns = p.get("news_signal") or {}
            act = p.get("action", "PAPER_BET")
            print(
                f"  [{p['tier']:<9} | {act:<21}] {p['kickoff']} | {p['league']:<5} | {p['home']} vs {p['away']} -> "
                f"Pick: {p['side']} | Score: {p['score']:+.4f} | BestOdds: {p['best_odds']:.2f} "
                f"(Pri: {p['primary_odds']:.2f}, SynDC: {p['synthetic_dc_odds']:.2f}) | "
                f"News({ns.get('backend','none')}): {ns.get('net_edge_for_pick', 0.0):+.3f}"
            )
            print(f"             Factors tanh(Z): {p['factors_tanh_z']}")
            if ns.get("headlines"):
                print(f"             Headlines: {ns['headlines'][:2]}")
            xi_g = p.get("starting_xi_gate") or {}
            if xi_g:
                print(f"             Starting XI Gate: {xi_g.get('status')} (starters={xi_g.get('starters_announced')}, att_share={xi_g.get('attack_share')})")

    if rep.get("tennis_picks"):
        print(f"\n=== Upcoming High-Confidence ATP/WTA Tennis Picks (n={len(rep['tennis_picks'])}) ===")
        for tp in rep["tennis_picks"][:10]:
            print(
                f"  [{tp['tier']:<12}] {tp['kickoff']} | {tp['tour']} {tp['surface'].upper():<5} | "
                f"{tp['player_1']} vs {tp['player_2']} -> Pick: {tp['pick']} | "
                f"WinProb: {tp['win_prob']:.1%} | MinFairOdds: {tp['min_fair_odds']:.2f} (+3%EV >= {tp['target_ev3_odds']:.2f}) | "
                f"GameEloDiff: {tp['factors']['game_elo_diff']:+.0f}"
            )
    else:
        print("Top 5 Upcoming Candidates (below threshold):")
        for p in rep["all_evaluated_upcoming"][:5]:
            print(
                f"  [{p['tier']:<9}] {p['kickoff']} | {p['league']:<5} | {p['home']} vs {p['away']} -> "
                f"Side: {p['side']} | Score: {p['score']:+.4f} | BestOdds: {p['best_odds']:.2f}"
            )


if __name__ == "__main__":
    main()
