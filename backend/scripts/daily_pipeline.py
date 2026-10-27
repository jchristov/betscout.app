"""Master daily pipeline:
1. Incrementally sync recent completed soccer & tennis matches into `matches` and `match_details`
2. Run database quality & anomaly checks (`0 errors` required)
3. Settle pending paper bets, score upcoming Big-5 soccer & ATP/WTA tennis fixtures, run System-1 news veto & T-60m XI gate
4. Export `data/recommendations.json` and regenerate `data/dashboard.html`

Usage:
    uv run python scripts/daily_pipeline.py
    uv run betscout-model
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "data").exists() else Path(__file__).resolve().parents[1]

from betscout.dashboard import generate_dashboard_html  # noqa: E402
from betscout.paper_bet import scan_upcoming_and_log_paper_bets  # noqa: E402
from betscout.telegram_bot import notify_new_settlements_to_discord  # noqa: E402
from betscout.universal_ingest import ingest_universal  # noqa: E402


def run_pipeline(
    lookback_days: int | None = None,
    days_ahead: int = 5,
    decision_backend: str = "laya",
    min_odds: float = 1.10,
) -> None:
    db_path = ROOT / "data" / "betscout.db"
    cache_dir = ROOT / "data" / "cache"
    cfg_path = ROOT / "ingestion_config.json"
    rec_json = ROOT / "data" / "recommendations.json"
    dash_html = ROOT / "data" / "dashboard.html"

    mode = "days" if lookback_days else "incremental"
    print(f"[1/4] Running universal ingestion (mode={mode}, config={cfg_path.name})...")
    ing_res = ingest_universal(
        db_path=db_path,
        cache_dir=cache_dir,
        config_path=cfg_path,
        mode=mode,
        days_back=lookback_days,
    )
    print(f"      New matches ingested: {sum(ing_res['new_ingested'].values())} | Normalization: {ing_res['normalization']}")

    print("[2/4] Verifying database quality and anomaly checks...")
    errors = ing_res["quality_errors"]
    total_rows = sum(s["rows"] for s in ing_res["stats"].values())
    print(f"      Quality check complete: {len(errors)} errors across {total_rows:,} matches.")
    if errors:
        for err in errors:
            print(f"      [ERROR] {err.check} ({err.league}): {err.count} — {err.note}")
        raise RuntimeError("Database quality check failed with errors.")

    print(f"[3/4] Settling paper bets & scanning upcoming fixtures ({days_ahead} days ahead, news={decision_backend})...")
    rep = scan_upcoming_and_log_paper_bets(
        db_path=db_path,
        days_ahead=days_ahead,
        decision_backend=decision_backend,
        export_json_path=rec_json,
    )
    notify_new_settlements_to_discord(db_path)
    bt = rep.get("backtest_risk") or {}
    print(
        f"      Post-2025 Holdout Top-10%: Profit={bt.get('post25_profit_u', 0):+.2f}u | "
        f"ROI={bt.get('post25_roi', 0)*100:+.2f}% | MaxDD={bt.get('post25_max_drawdown_u', 0):.2f}u | "
        f"Sharpe={bt.get('post25_sharpe', 0):.2f}"
    )
    print(
        f"      Evaluated {rep['evaluated_upcoming_count']} upcoming football fixtures -> "
        f"{rep['qualifying_picks_count']} football picks, {rep['tennis_picks_count']} tennis picks, "
        f"{rep.get('other_sport_picks_count', 0)} NBA/NHL/NFL/MLB picks."
    )

    print(f"[4/4] Generating HTML Quantitative Desk Dashboard & Best Bets CSV/JSON (min_odds > {min_odds:.2f})...")
    best_csv = ROOT / "data" / "best_bets.csv"
    best_json = ROOT / "data" / "best_bets.json"
    generate_dashboard_html(
        rec_json,
        db_path,
        dash_html,
        min_odds=min_odds,
        csv_export_path=best_csv,
        json_export_path=best_json,
    )
    app_public_model_dir = ROOT.parent / "app" / "public" / "model"
    if (ROOT.parent / "app" / "public").exists():
        app_public_model_dir.mkdir(parents=True, exist_ok=True)
        for src_p in (best_json, best_csv, rec_json, dash_html):
            if src_p.exists():
                shutil.copy2(src_p, app_public_model_dir / src_p.name)
    print(f"      Done! Dashboard: {dash_html} | Best Bets CSV: {best_csv} | Best Bets JSON: {best_json}\n")

    active_soccer = [p for p in (rep.get("qualifying_picks") or []) if p.get("action") == "PAPER_BET"]
    vetoed_soccer = [p for p in (rep.get("qualifying_picks") or []) if p.get("action") != "PAPER_BET"]
    if active_soccer:
        print("=== ACTIVE HIGH-CONVICTION SOCCER PAPER TIPS ===")
        for p in active_soccer:
            ns = p.get("news_signal") or {}
            xi = p.get("starting_xi_gate") or {}
            pick_team = p["home"] if p["side"] == "H" else p["away"]
            print(
                f"  * [{p['tier']:<9}] {p['kickoff']} | {p['league'].upper():<5} | {p['home']} vs {p['away']} -> "
                f"PICK: {pick_team} ({p['side']}) @ BestOdds {p['best_odds']:.2f} (SynDC {p['synthetic_dc_odds']:.2f}) | "
                f"CalibP: {p.get('p_model', p['p_mkt'])*100:.1f}% (Mkt {p['p_mkt']*100:.1f}%, EV {p.get('ev_pct', 0.0):+.1f}%, 1/4-Kelly {p.get('quarter_kelly_pct', 0.0):.2f}%) | "
                f"News: {ns.get('net_edge_for_pick', 0.0):+.2f} | XI: {xi.get('status')}"
            )
    if vetoed_soccer:
        print("\n=== VETOED SOCCER CANDIDATES (DO NOT BET) ===")
        for p in vetoed_soccer:
            ns = p.get("news_signal") or {}
            print(
                f"  x [{p['tier']:<9} | {p['action']}] {p['kickoff']} | {p['home']} vs {p['away']} -> "
                f"News={ns.get('net_edge_for_pick', 0.0):+.2f} ({(ns.get('headlines') or [''])[0]})"
            )
    tennis_bankers = [
        t for t in (rep.get("tennis_picks") or [])
        if t.get("win_prob", 0) >= 0.70 and float(t.get("min_fair_odds") or 0.0) > min_odds
    ]
    if tennis_bankers:
        print(f"\n=== HIGH-WIN-POTENTIAL TENNIS BANKERS (WinProb >= 70%, Odds > {min_odds:.2f}, top 8 of {len(tennis_bankers)}) ===")
        for tp in tennis_bankers[:8]:
            print(
                f"  * [{tp['tour']} {tp['surface'].upper():<5}] {tp['kickoff']} | {tp['player_1']} vs {tp['player_2']} -> "
                f"PICK: {tp['pick']} | WinProb: {tp['win_prob']*100:.1f}% | MinFairOdds: {tp['min_fair_odds']:.2f} (+3%EV >= {tp['target_ev3_odds']:.2f})"
            )
    other_picks = [
        op for op in (rep.get("other_sport_picks") or [])
        if float(op.get("best_odds") or 0.0) > min_odds
    ]
    if other_picks:
        print(f"\n=== HIGH-WIN-POTENTIAL NBA / NHL / NFL / MLB PICKS (Odds > {min_odds:.2f}, n={len(other_picks)}) ===")
        for op in other_picks[:8]:
            print(
                f"  * [{op['sport'].upper()} {op['league']:<4}] {op['kickoff']} | {op['home']} vs {op['away']} -> "
                f"PICK: {op['pick']} ({op['side']}) @ {op['best_odds']:.2f} | ModelP: {op['p_model']*100:.1f}% (Mkt {op['p_mkt']*100:.1f}%, EV {op['ev_pct']:+.1f}%)"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the end-to-end BetScout daily quantitative pipeline.")
    parser.add_argument("--lookback", type=int, default=None, help="Days of recent completed results to force-scan (default: incremental watermark from ingestion_config.json)")
    parser.add_argument("--days", type=int, default=5, help="Days of upcoming fixtures to scan (default: 5)")
    parser.add_argument("--min-odds", type=float, default=1.10, help="Soft filter threshold: exclude odds <= min-odds (default: 1.10)")
    parser.add_argument(
        "--decision-backend",
        choices=("laya", "laya-sports", "laya-base", "ms-decision-1", "auto", "none"),
        default="laya",
        help="Decision model backend for pre-match news veto gate (default: laya)",
    )
    args = parser.parse_args()
    run_pipeline(lookback_days=args.lookback, days_ahead=args.days, decision_backend=args.decision_backend, min_odds=args.min_odds)


if __name__ == "__main__":
    main()
