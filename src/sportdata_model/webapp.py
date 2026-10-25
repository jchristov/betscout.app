"""Interactive Web App Server & Social Publishing Addon (`src/sportdata_model/webapp.py`).

Serves:
  - `GET  /`                  -> Enhanced Quant Desk Web App (`data/dashboard.html`) with live controls
  - `GET  /api/data`          -> JSON payload of `recommendations.json` + live `paper_ledger` + `best_bets`
  - `GET  /api/stream`        -> Server-Sent Events (SSE) live stream pushing ledger, live scores & best bets
  - `GET  /api/best-bets.csv` -> Downloadable CSV (with header) of current best bets
  - `GET  /api/settled.csv`   -> Downloadable CSV (with header) of settled paper bets
  - `POST /api/settle`        -> Trigger immediate live settlement against ESPN & refresh `dashboard.html`
  - `POST /api/sync`          -> Sync & settle ledger + optionally rescan live/upcoming fixtures
  - `POST /api/telegram`      -> Preview or post the formatted Telegram Channel digest (`send_telegram_message`)
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .dashboard import (
    DEFAULT_LOCAL_TZ,
    _format_local_time,
    _league_to_sport_cat,
    _match_day_key,
    build_best_bets_summary,
    generate_dashboard_html,
)
from .espn import LEAGUE_LABELS
from .paper_trade import (
    get_paper_ledger_summary,
    refresh_t60_starting_xi_gates,
    scan_upcoming_and_log_paper_trades,
    settle_pending_paper_trades,
)
from .telegram_bot import (
    format_discord_digest,
    format_telegram_digest,
    get_discord_env_config,
    get_telegram_env_config,
    notify_inplay_rebound_edges_to_discord,
    notify_new_settlements_to_discord,
    send_discord_message,
    send_telegram_message,
)
from .universal_ingest import ingest_universal

_PIPELINE_STATUS: dict[str, Any] = {
    "running": False,
    "step": "Idle",
    "updated_at": None,
    "inplay_alerts_enabled": False,
    "inplay_alert_items": {},
}


def _load_webapp_settings(data_dir: Path) -> dict[str, Any]:
    import os
    cfg_file = data_dir / "webapp_settings.json"
    env_default = (os.environ.get("INPLAY_ALERTS_ENABLED") or "").strip().lower() in ("1", "true", "yes", "on")
    defaults: dict[str, Any] = {
        "inplay_alerts_enabled": env_default,
        "inplay_alert_items": {},
        "settlement_alerts_enabled": True,
        "bankroll_eur": 1000.0,
        "default_bet_budget_eur": 100.0,
        "default_risk_mode": "balanced",
        "min_odds": 1.10,
        "tennis_banker_min_prob": 0.70,
        "mispricing_min_edge_pp": 2.0,
        "mispricing_min_ev_pct": 2.0,
        "daily_digest_hour": (os.environ.get("DAILY_DIGEST_HOUR") or "").strip(),
        "sport_webhooks": {},
    }
    if cfg_file.exists():
        try:
            d = json.loads(cfg_file.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                defaults.update(d)
        except Exception:
            pass
    _PIPELINE_STATUS["inplay_alerts_enabled"] = bool(defaults.get("inplay_alerts_enabled", False))
    raw_items = defaults.get("inplay_alert_items")
    _PIPELINE_STATUS["inplay_alert_items"] = dict(raw_items) if isinstance(raw_items, dict) else {}
    defaults["inplay_alerts_enabled"] = _PIPELINE_STATUS["inplay_alerts_enabled"]
    defaults["inplay_alert_items"] = _PIPELINE_STATUS["inplay_alert_items"]
    if not isinstance(defaults.get("sport_webhooks"), dict):
        defaults["sport_webhooks"] = {}
    return defaults


def _save_webapp_settings(
    data_dir: Path,
    inplay_alerts_enabled: bool | None = None,
    item_key: str | None = None,
    item_enabled: bool | None = None,
    updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cur = _load_webapp_settings(data_dir)
    if updates and isinstance(updates, dict):
        for k in (
            "inplay_alerts_enabled",
            "settlement_alerts_enabled",
            "bankroll_eur",
            "default_bet_budget_eur",
            "default_risk_mode",
            "min_odds",
            "tennis_banker_min_prob",
            "mispricing_min_edge_pp",
            "mispricing_min_ev_pct",
            "daily_digest_hour",
        ):
            if k in updates and updates[k] is not None:
                cur[k] = updates[k]
        if isinstance(updates.get("sport_webhooks"), dict):
            sw = dict(cur.get("sport_webhooks") or {})
            for sk, sv in updates["sport_webhooks"].items():
                sw[str(sk).lower()] = str(sv or "").strip()
            cur["sport_webhooks"] = sw
    if inplay_alerts_enabled is not None:
        cur["inplay_alerts_enabled"] = bool(inplay_alerts_enabled)
    items_map = dict(cur.get("inplay_alert_items") or {})
    if item_key:
        items_map[str(item_key).lower()] = bool(item_enabled)
    cur["inplay_alert_items"] = items_map
    _PIPELINE_STATUS["inplay_alerts_enabled"] = bool(cur.get("inplay_alerts_enabled", False))
    _PIPELINE_STATUS["inplay_alert_items"] = items_map
    cfg_file = data_dir / "webapp_settings.json"
    try:
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    except Exception:
        pass
    return cur


def _build_live_snapshot(
    rec_path: Path,
    db_path: Path,
    min_odds: float = 1.10,
    sport: str = "all",
    run_settle: bool = False,
) -> dict[str, Any]:
    newly_settled = 0
    if run_settle and db_path.exists():
        try:
            newly_settled = settle_pending_paper_trades(db_path)
            if newly_settled > 0:
                notify_new_settlements_to_discord(db_path)
        except Exception:
            newly_settled = 0

    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
    ledger = get_paper_ledger_summary(db_path) if db_path.exists() else {}
    for tr in ledger.get("trades") or []:
        tr["kickoff_local"] = _format_local_time(tr.get("kickoff") or "", DEFAULT_LOCAL_TZ)
        tr["day_key"] = _match_day_key(tr.get("kickoff") or "", DEFAULT_LOCAL_TZ)
        tr["league_label"] = LEAGUE_LABELS.get(tr["league"], tr["league"].upper())
        tr["sport_cat"] = _league_to_sport_cat(tr["league"])
    rec["paper_ledger"] = ledger
    best_bets = build_best_bets_summary(rec, min_odds=min_odds, sport_filter=sport)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "server_time_utc": now_utc,
        "server_time_local": _format_local_time(now_utc, DEFAULT_LOCAL_TZ),
        "generated_at": rec.get("generated_at"),
        "generated_at_local": _format_local_time(rec.get("generated_at") or "", DEFAULT_LOCAL_TZ),
        "timezone": DEFAULT_LOCAL_TZ,
        "discord_env": get_discord_env_config(),
        "telegram_env": get_telegram_env_config(),
        "pipeline_status": dict(_PIPELINE_STATUS),
        "newly_settled": newly_settled,
        "paper_ledger": ledger,
        "best_bets_count": len(best_bets),
        "best_bets": best_bets,
        "qualifying_picks": rec.get("qualifying_picks", []),
        "tennis_picks": rec.get("tennis_picks", []),
        "other_sport_picks": rec.get("other_sport_picks", []),
    }


def _lookup_matchup_detail(db_path: Path, rec_path: Path, home: str, away: str, league: str = "") -> dict[str, Any]:
    """Return H2H history, Last-6 form for both sides, and Exact-Score / Set-Score breakdown for the Matchup Inspector modal."""
    h = (home or "").strip()
    a = (away or "").strip()
    lg = (league or "").strip().lower()
    h2h_rows: list[dict[str, Any]] = []
    form_home: list[dict[str, Any]] = []
    form_away: list[dict[str, Any]] = []
    if db_path.exists() and h and a:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for r in conn.execute(
            """
            SELECT league, kickoff, home, away, home_score, away_score, outcome
            FROM matches
            WHERE outcome IS NOT NULL AND ((home = ? AND away = ?) OR (home = ? AND away = ?))
            ORDER BY kickoff DESC LIMIT 8
            """,
            (h, a, a, h),
        ).fetchall():
            sc = f"{int(r['home_score'])}-{int(r['away_score'])}" if r["home_score"] is not None and r["away_score"] is not None else r["outcome"]
            h2h_rows.append({"date": str(r["kickoff"])[:10], "league": r["league"], "home": r["home"], "away": r["away"], "score": sc, "outcome": r["outcome"]})

        for team_name, bucket in ((h, form_home), (a, form_away)):
            for r in conn.execute(
                """
                SELECT league, kickoff, home, away, home_score, away_score, outcome
                FROM matches
                WHERE outcome IS NOT NULL AND (home = ? OR away = ?)
                ORDER BY kickoff DESC LIMIT 6
                """,
                (team_name, team_name),
            ).fetchall():
                is_h = r["home"] == team_name
                opp = r["away"] if is_h else r["home"]
                res = "D" if r["outcome"] == "D" else ("W" if ((is_h and r["outcome"] == "H") or (not is_h and r["outcome"] == "A")) else "L")
                sc = f"{int(r['home_score'])}-{int(r['away_score'])}" if r["home_score"] is not None and r["away_score"] is not None else r["outcome"]
                bucket.append({"date": str(r["kickoff"])[:10], "opp": opp, "venue": "H" if is_h else "A", "result": res, "score": sc})
        conn.close()

    model_pick_detail: dict[str, Any] = {}
    if rec_path.exists():
        try:
            rec = json.loads(rec_path.read_text(encoding="utf-8"))
            for p in rec.get("qualifying_picks") or []:
                if p.get("home") == h and p.get("away") == a:
                    model_pick_detail = p
                    break
            if not model_pick_detail:
                for tp in rec.get("tennis_picks") or []:
                    if tp.get("player_1") == h and tp.get("player_2") == a:
                        model_pick_detail = tp
                        break
            if not model_pick_detail:
                for op in rec.get("other_sport_picks") or []:
                    if op.get("home") == h and op.get("away") == a:
                        model_pick_detail = op
                        break
        except Exception:
            pass
    if not model_pick_detail and db_path.exists():
        try:
            conn_pt = sqlite3.connect(db_path)
            conn_pt.row_factory = sqlite3.Row
            pt_r = conn_pt.execute(
                "SELECT * FROM paper_trades WHERE home = ? AND away = ? ORDER BY kickoff DESC LIMIT 1",
                (h, a),
            ).fetchone()
            conn_pt.close()
            if pt_r:
                model_pick_detail = {
                    "tier": pt_r["tier"],
                    "score": pt_r["composite_score"],
                    "p_mkt": pt_r["p_mkt"],
                    "best_odds": pt_r["logged_best_odds"],
                    "factors": json.loads(pt_r["factor_breakdown_json"] or "{}"),
                }
        except Exception:
            pass

    statshub_intel: dict[str, Any] = {}
    try:
        from .sportradar_statshub import lookup_statshub_match_intel

        sp_hint = "tennis" if lg in ("atp", "wta") else (_league_to_sport_cat(lg) if lg else "soccer")
        sh_res = lookup_statshub_match_intel(h, a, sport=sp_hint)
        if sh_res.get("found"):
            statshub_intel = sh_res
    except Exception:
        statshub_intel = {}

    return {
        "ok": True,
        "home": h,
        "away": a,
        "league": lg,
        "h2h": h2h_rows,
        "form_home": form_home,
        "form_away": form_away,
        "pick_detail": model_pick_detail,
        "statshub": statshub_intel,
    }


def _analyze_live_matchup(db_path: Path, rec_path: Path, query: str) -> dict[str, Any]:
    """On-demand live matchup analyzer (`GET /api/analyze-live?q=Player1 vs Player2`).
    Works for ANY Tennis or Football matchup (even sub-70% non-bankers), combining live 8-Feature Tennis Elo /
    7-Factor Football state from `matches.sqlite` with live SofaScore bookmaker odds, all-level (ATP/WTA/Challenger)
    Last-5 form, rest/turnaround hours, and 3 explicit market verdicts (Moneyline/1X2, Handicap/Shield, Totals)."""
    import math
    from collections import defaultdict, deque
    from .elo import Elo
    from .exact_score import predict_soccer_exact_scores, predict_tennis_set_scores
    from .paper_trade import _fetch_sofascore_tennis_odds

    raw_q = (query or "").strip()
    if " vs " in raw_q.lower():
        idx_v = raw_q.lower().index(" vs ")
        p1_q, p2_q = raw_q[:idx_v].strip(), raw_q[idx_v + 4:].strip()
    elif "-" in raw_q and len(raw_q.split("-")) == 2:
        p1_q, p2_q = [x.strip() for x in raw_q.split("-", 1)]
    else:
        parts = raw_q.split()
        mid = max(1, len(parts) // 2)
        p1_q, p2_q = " ".join(parts[:mid]), " ".join(parts[mid:])

    if not p1_q or not p2_q:
        return {"ok": False, "error": "Enter two players or teams separated by 'vs' (e.g. 'Medvedev vs Bublik')"}

    h_name, a_name = p1_q, p2_q
    detected_sport = "tennis"
    detected_league = "atp"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        for idx_s, tok in ((0, p1_q), (1, p2_q)):
            row_n = conn.execute(
                "SELECT home, league FROM matches WHERE lower(home) LIKE ? ORDER BY kickoff DESC LIMIT 1",
                (f"%{tok.lower()}%",),
            ).fetchone()
            if not row_n:
                row_n = conn.execute(
                    "SELECT away, league FROM matches WHERE lower(away) LIKE ? ORDER BY kickoff DESC LIMIT 1",
                    (f"%{tok.lower()}%",),
                ).fetchone()
            if row_n and row_n[0]:
                if idx_s == 0:
                    h_name = str(row_n[0])
                    detected_league = str(row_n[1] or "atp").lower()
                    detected_sport = "tennis" if detected_league in ("atp", "wta") else _league_to_sport_cat(detected_league)
                else:
                    a_name = str(row_n[0])
        conn.close()

    base_detail = _lookup_matchup_detail(db_path, rec_path, h_name, a_name, detected_league)
    pk_existing = base_detail.get("pick_detail") or {}

    # Compute live Elo & rolling stats from matches.sqlite for the detected sport
    elo_diff_1 = 0.0
    game_elo_diff_1 = 0.0
    game_share_diff_1 = 0.0
    sot_diff_1 = 0.0
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            has_details = bool(conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_details'").fetchone())
            if detected_sport == "tennis":
                ea = Elo(k=28.0, home_adv=0.0)
                eg = Elo(k=28.0, home_adv=0.0)
                gh: dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
                q_sql = (
                    "SELECT m.home, m.away, m.outcome, d.home_games, d.away_games FROM matches m LEFT JOIN match_details d ON m.league = d.league AND m.event_id = d.event_id WHERE m.league = ? AND m.outcome IS NOT NULL ORDER BY m.kickoff"
                    if has_details
                    else "SELECT home, away, outcome, NULL as home_games, NULL as away_games FROM matches WHERE league = ? AND outcome IS NOT NULL ORDER BY kickoff"
                )
                for r in conn.execute(q_sql, (detected_league,)):
                    wh = 1.0 if r["outcome"] == "H" else 0.0
                    ea.update(r["home"], r["away"], wh)
                    hg, ag = r["home_games"], r["away_games"]
                    if hg is not None and ag is not None and (hg + ag) > 0:
                        gs = float(hg) / float(hg + ag)
                        eg.update(r["home"], r["away"], 1.0 / (1.0 + math.exp(-6.0 * (gs - 0.5))))
                        gh[r["home"]].append(gs)
                        gh[r["away"]].append(1.0 - gs)
                    else:
                        eg.update(r["home"], r["away"], wh)
                elo_diff_1 = round(ea.ratings[h_name] - ea.ratings[a_name], 1)
                game_elo_diff_1 = round(eg.ratings[h_name] - eg.ratings[a_name], 1)
                g1 = float(sum(gh[h_name]) / len(gh[h_name])) if gh[h_name] else 0.50
                g2 = float(sum(gh[a_name]) / len(gh[a_name])) if gh[a_name] else 0.50
                game_share_diff_1 = round(g1 - g2, 3)
            else:
                es = Elo(k=20.0, home_adv=55.0)
                sot_q: dict[str, deque] = defaultdict(lambda: deque(maxlen=6))
                q_sql = (
                    "SELECT m.home, m.away, m.outcome, d.home_sot, d.away_sot FROM matches m LEFT JOIN match_details d ON m.league = d.league AND m.event_id = d.event_id WHERE m.league = ? AND m.outcome IS NOT NULL ORDER BY m.kickoff"
                    if has_details
                    else "SELECT home, away, outcome, NULL as home_sot, NULL as away_sot FROM matches WHERE league = ? AND outcome IS NOT NULL ORDER BY kickoff"
                )
                for r in conn.execute(q_sql, (detected_league,)):
                    sc = {"H": 1.0, "D": 0.5, "A": 0.0}.get(r["outcome"], 0.5)
                    es.update(r["home"], r["away"], sc)
                    if r["home_sot"] is not None and r["away_sot"] is not None:
                        sd = float(r["home_sot"]) - float(r["away_sot"])
                        sot_q[r["home"]].append(sd)
                        sot_q[r["away"]].append(-sd)
                elo_diff_1 = round(es.ratings[h_name] - es.ratings[a_name], 1)
                s1 = float(sum(sot_q[h_name]) / len(sot_q[h_name])) if sot_q[h_name] else 0.0
                s2 = float(sum(sot_q[a_name]) / len(sot_q[a_name])) if sot_q[a_name] else 0.0
                sot_diff_1 = round(s1 - s2, 2)
            conn.close()
        except Exception:
            pass

    sf_odds = (
        _fetch_sofascore_tennis_odds(h_name, a_name, datetime.now(timezone.utc).strftime("%Y%m%d"))
        if detected_sport == "tennis"
        else {}
    )
    o1 = sf_odds.get("odds_p1") or (pk_existing.get("best_odds") if pk_existing.get("side") == "H" else None)
    o2 = sf_odds.get("odds_p2") or (pk_existing.get("best_odds") if pk_existing.get("side") == "A" else None)
    p1_f5 = sf_odds.get("p1_last5_win_rate")
    p2_f5 = sf_odds.get("p2_last5_win_rate")
    p1_rest = sf_odds.get("p1_rest_hours")
    p2_rest = sf_odds.get("p2_rest_hours")
    p1_tourn = sf_odds.get("p1_last_tourn")
    p2_tourn = sf_odds.get("p2_last_tourn")

    h2h_list = base_detail.get("h2h") or []
    h_wins = sum(1 for m in h2h_list if (m["home"] == h_name and m["outcome"] == "H") or (m["away"] == h_name and m["outcome"] == "A"))
    a_wins = sum(1 for m in h2h_list if (m["home"] == a_name and m["outcome"] == "H") or (m["away"] == a_name and m["outcome"] == "A"))

    if p1_f5 is None and base_detail.get("form_home"):
        fh = base_detail["form_home"]
        p1_f5 = round(sum(1 for x in fh if x["result"] == "W") / len(fh), 3)
    if p2_f5 is None and base_detail.get("form_away"):
        fa = base_detail["form_away"]
        p2_f5 = round(sum(1 for x in fa if x["result"] == "W") / len(fa), 3)

    p_elo_1 = 1.0 / (1.0 + 10.0 ** (-(0.6 * elo_diff_1 + 0.4 * game_elo_diff_1) / 400.0))
    if o1 and o2 and float(o1) > 1.01 and float(o2) > 1.01:
        i1, i2 = 1.0 / float(o1), 1.0 / float(o2)
        p_mkt_1 = i1 / (i1 + i2)
    else:
        p_mkt_1 = p_elo_1

    f_diff = (float(p1_f5 if p1_f5 is not None else 0.5) - float(p2_f5 if p2_f5 is not None else 0.5))
    h2h_diff = ((h_wins + 1.0) / (h_wins + a_wins + 2.0)) - 0.5
    p_model_1 = min(
        max(0.50 * p_mkt_1 + 0.26 * p_elo_1 + 0.14 * (0.5 + 0.45 * f_diff) + 0.10 * (0.5 + 0.60 * h2h_diff), 0.08),
        0.92,
    )
    fav_is_1 = p_model_1 >= 0.50
    fav_name = h_name if fav_is_1 else a_name
    dog_name = a_name if fav_is_1 else h_name
    fav_prob = p_model_1 if fav_is_1 else (1.0 - p_model_1)
    fav_mkt_prob = p_mkt_1 if fav_is_1 else (1.0 - p_mkt_1)
    fav_odds = (o1 if fav_is_1 else o2)
    fav_edge_pp = round((fav_prob - fav_mkt_prob) * 100.0, 2)
    fav_ev_pct = round((fav_prob * float(fav_odds) - 1.0) * 100.0, 2) if fav_odds and float(fav_odds) > 1.01 else None
    is_mispriced_live = bool(fav_ev_pct is not None and fav_ev_pct >= 2.0 and fav_edge_pp >= 2.0)
    fav_f5 = p1_f5 if fav_is_1 else p2_f5
    opp_f5 = p2_f5 if fav_is_1 else p1_f5
    fav_rest = p1_rest if fav_is_1 else p2_rest
    sgn_fav = 1.0 if fav_is_1 else -1.0

    warnings: list[str] = []
    if is_mispriced_live:
        warnings.append(
            f"💎 CONFIRMED BOOKMAKER MISPRICING: Model gives {fav_name} {fav_prob*100:.1f}% vs Market {fav_mkt_prob*100:.1f}% ({fav_edge_pp:+.1f}pp Edge · EV {fav_ev_pct:+.1f}% @ {float(fav_odds):.2f} vs Fair {1.0/fav_prob:.2f})!"
        )
    if fav_f5 is not None and opp_f5 is not None and fav_f5 <= 0.25 and opp_f5 >= 0.60:
        warnings.append(f"⚠️ Form Divergence Alert: {fav_name} is {int(round(fav_f5*5))}-{5-int(round(fav_f5*5))} in Last 5 while {dog_name} is {int(round(opp_f5*5))}-{5-int(round(opp_f5*5))}!")
    if isinstance(fav_rest, (int, float)) and fav_rest <= 36.0:
        warnings.append(f"⚠️ Short Turnaround Alert: {fav_name} played just {fav_rest:.0f}h ago ({p1_tourn if fav_is_1 else p2_tourn}).")

    # Also enrich with Sportradar StatsHub (Tipico) markets, injuries, streaks & surface records
    sh_intel = base_detail.get("statshub") or {}
    if not sh_intel.get("found"):
        try:
            from .sportradar_statshub import lookup_statshub_match_intel

            sh_intel = lookup_statshub_match_intel(h_name, a_name, sport=detected_sport)
        except Exception:
            sh_intel = {}
    sh_mkts = sh_intel.get("tipico_markets") or {}
    if not o1 and sh_mkts.get("odds_home"):
        o1 = sh_mkts["odds_home"]
    if not o2 and sh_mkts.get("odds_away"):
        o2 = sh_mkts["odds_away"]
    h_inj = sh_intel.get("home_injuries") or []
    a_inj = sh_intel.get("away_injuries") or []
    if len(h_inj) >= 3 and fav_is_1:
        warnings.append(f"⚠️ Sportradar StatsHub Injury Alert: {h_name} has {len(h_inj)} players missing ({', '.join(h_inj[:3])}).")
    elif len(a_inj) >= 3 and not fav_is_1:
        warnings.append(f"⚠️ Sportradar StatsHub Injury Alert: {a_name} has {len(a_inj)} players missing ({', '.join(a_inj[:3])}).")
    if detected_sport == "tennis":
        set_pred = predict_tennis_set_scores(
            win_prob=fav_prob,
            side="H" if fav_is_1 else "A",
            game_win_pct_diff=sgn_fav * game_share_diff_1,
            form_6m_diff=sgn_fav * f_diff,
            best_of=3,
        )
        p_plus15_fav = round(min(0.97, fav_prob + (1.0 - fav_prob) * 0.52), 3)
        p_plus15_dog = round(min(0.88, (1.0 - fav_prob) + set_pred["decider_sets_prob"]), 3)
        g_line = sf_odds.get("games_line") or (21.5 if fav_prob >= 0.74 else 22.5)
        is_dogfight = bool(warnings or fav_prob < 0.64)
        mkt_1 = (
            f"Skip {fav_name} ML ({fav_prob*100:.1f}% WinProb, Fair @{1.0/fav_prob:.2f})"
            if warnings or fav_prob < 0.58
            else f"{fav_name} ML ({fav_prob*100:.1f}% WinProb, Fair @{1.0/fav_prob:.2f}" + (f", Book @{float(fav_odds):.2f})" if fav_odds else ")")
        )
        mkt_2 = (
            f"{dog_name} +1.5 Sets ({p_plus15_dog*100:.1f}% HitProb, Fair @{1.0/max(p_plus15_dog,0.1):.2f})"
            if is_dogfight
            else f"{fav_name} {set_pred['straight_sets_score']} Straight Sets ({set_pred['straight_sets_prob']*100:.1f}%, Fair @{set_pred['straight_sets_fair_odds']:.2f}) | Safe Shield: {fav_name} +1.5 Sets ({p_plus15_fav*100:.1f}%)"
        )
        mkt_3 = (
            f"Over {g_line} Total Games (3-Set Dogfight Profile · Decider Prob {(set_pred['decider_sets_prob']+0.18)*100:.0f}%)"
            if is_dogfight
            else f"Under {g_line} Total Games (Straight-Sets Share {(set_pred['straight_sets_prob']/max(fav_prob,0.5))*100:.0f}%)"
        )
    else:
        sc_pred = predict_soccer_exact_scores(
            ph=p_model_1 * 0.78,
            pd=0.22,
            pa=(1.0 - p_model_1) * 0.78,
            side="H" if fav_is_1 else "A",
            line_total=2.5,
            p_model=fav_prob,
            sot_z=max(-1.0, min(1.0, sgn_fav * sot_diff_1 / 3.0)),
        )
        dc_lbl = f"{fav_name} or Draw ({'1X' if fav_is_1 else 'X2'})"
        dc_prob = min(0.95, fav_prob + 0.18)
        mkt_1 = f"{fav_name} 1X2 Moneyline ({fav_prob*100:.1f}% WinProb, Fair @{1.0/fav_prob:.2f})"
        mkt_2 = f"Double Chance Shield: {dc_lbl} ({dc_prob*100:.1f}% HitProb, Fair @{1.0/dc_prob:.2f})"
        mkt_3 = f"Over 1.5 Goals & 3-Score Dutch Cluster [{sc_pred['cluster_3_scores']}] ({sc_pred['cluster_3_prob']*100:.1f}%, Fair @{sc_pred['cluster_3_fair_odds']:.2f})"

    if warnings or fav_prob < 0.58:
        verdict = f"⛔ NO-BET / HIGH VARIANCE — {mkt_2} or {mkt_3}"
        verdict_level = "no_bet"
    elif fav_prob >= 0.70:
        verdict = f"✅ STRONG BANKER — {mkt_1}"
        verdict_level = "strong_bet"
    else:
        verdict = f"⚖️ SOLID VALUE LEAN — {mkt_1}"
        verdict_level = "lean_bet"

    return {
        **base_detail,
        "ok": True,
        "sport": detected_sport,
        "league": detected_league,
        "home": h_name,
        "away": a_name,
        "h2h_summary": f"{h_name} {h_wins} – {a_wins} {a_name}",
        "elo_diff_home": elo_diff_1,
        "game_elo_diff_home": game_elo_diff_1,
        "game_share_diff_home": game_share_diff_1,
        "sot_diff_home": sot_diff_1,
        "odds_home": o1,
        "odds_away": o2,
        "games_line": sf_odds.get("games_line"),
        "p1_last5_pct": round(p1_f5 * 100.0, 1) if p1_f5 is not None else None,
        "p2_last5_pct": round(p2_f5 * 100.0, 1) if p2_f5 is not None else None,
        "p1_rest_hours": p1_rest,
        "p2_rest_hours": p2_rest,
        "p1_last_tourn": p1_tourn,
        "p2_last_tourn": p2_tourn,
        "fav_name": fav_name,
        "fav_prob_pct": round(fav_prob * 100.0, 1),
        "fav_mkt_prob_pct": round(fav_mkt_prob * 100.0, 1),
        "fav_edge_pp": fav_edge_pp,
        "fav_ev_pct": fav_ev_pct,
        "is_mispriced": is_mispriced_live,
        "fav_fair_odds": round(1.0 / max(fav_prob, 0.05), 2),
        "fav_book_odds": fav_odds,
        "market_recommendations": {
            "moneyline": mkt_1,
            "handicap_shield": mkt_2,
            "totals_cluster": mkt_3,
        },
        "warnings": warnings,
        "verdict": verdict,
        "verdict_level": verdict_level,
    }


def _start_background_auto_poller(root_dir: Path, interval_sec: int = 90) -> threading.Thread:
    """Start a daemon background thread that periodically settles finished/in-play matches
    and evaluates T-60m starting XI gates for upcoming soccer fixtures."""
    data_dir = root_dir / "data"
    db_path = data_dir / "matches.sqlite"
    rec_path = data_dir / "recommendations.json"
    dash_path = data_dir / "dashboard.html"
    last_digest_ymd: list[str] = [""]
    _load_webapp_settings(data_dir)

    def _loop() -> None:
        import os
        from zoneinfo import ZoneInfo
        while True:
            time.sleep(interval_sec)
            if _PIPELINE_STATUS.get("running") or not db_path.exists():
                continue
            try:
                settled_n = settle_pending_paper_trades(db_path)
                vetoes = refresh_t60_starting_xi_gates(db_path)
                cfg_now = _load_webapp_settings(data_dir)
                if cfg_now.get("inplay_alerts_enabled") or any(cfg_now.get("inplay_alert_items", {}).values()):
                    notify_inplay_rebound_edges_to_discord(
                        db_path,
                        global_enabled=bool(cfg_now.get("inplay_alerts_enabled", False)),
                        item_overrides=cfg_now.get("inplay_alert_items") or {},
                    )
                if settled_n > 0:
                    notify_new_settlements_to_discord(db_path)
                if vetoes:
                    lines = ["🚨 **BETSCOUT — T-60m STARTING XI VETO ALERT**", ""]
                    for v in vetoes:
                        lines.append(
                            f"⛔ **{v['home']} vs {v['away']}** ({v['league'].upper()}) — "
                            f"`{v['status']}` (Attack Share: {v['attack_share']*100:.0f}%) -> Removed from active Paper-Bets!"
                        )
                    send_discord_message("\n".join(lines))
                if settled_n > 0 or vetoes:
                    generate_dashboard_html(rec_path, db_path, dash_path, min_odds=1.10)

                # Optional Morning Daily Digest Scheduler (set DAILY_DIGEST_HOUR=9 in model/.env; default disabled unless configured)
                digest_hr_str = (os.environ.get("DAILY_DIGEST_HOUR") or "").strip()
                if digest_hr_str.isdigit():
                    now_loc = datetime.now(ZoneInfo(DEFAULT_LOCAL_TZ))
                    today_str = now_loc.strftime("%Y-%m-%d")
                    if now_loc.hour == int(digest_hr_str) and last_digest_ymd[0] != today_str:
                        last_digest_ymd[0] = today_str
                        scan_upcoming_and_log_paper_trades(db_path=db_path, days_ahead=3, decision_backend="laya", export_json_path=rec_path)
                        generate_dashboard_html(rec_path, db_path, dash_path, min_odds=1.10)
                        rec_d = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
                        msg_d = format_discord_digest(rec=rec_d, db_path=db_path, min_odds=1.15, day_filter="today")
                        send_discord_message(msg_d)
            except Exception:
                pass

    t = threading.Thread(target=_loop, name="vektorpulse-auto-poller", daemon=True)
    t.start()
    return t


def build_webapp_handler(root_dir: Path) -> type[BaseHTTPRequestHandler]:
    data_dir = root_dir / "data"
    rec_path = data_dir / "recommendations.json"
    db_path = data_dir / "matches.sqlite"
    dash_path = data_dir / "dashboard.html"
    best_csv_path = data_dir / "best_bets.csv"
    best_json_path = data_dir / "best_bets.json"
    settled_csv_path = data_dir / "settled_bets.csv"

    class QuantDeskRequestHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any] | list[Any], status: int = 200) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                return

        def handle_one_request(self) -> None:
            try:
                super().handle_one_request()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, OSError):
                self.close_connection = True

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            min_odds = float((qs.get("min_odds") or ["1.10"])[0])
            sport = (qs.get("sport") or ["all"])[0]

            if parsed.path in ("/", "/index.html", "/dashboard.html"):
                generate_dashboard_html(
                    rec_path,
                    db_path,
                    dash_path,
                    min_odds=min_odds,
                    sport_filter=sport,
                    csv_export_path=best_csv_path,
                    json_export_path=best_json_path,
                )
                html_bytes = dash_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.end_headers()
                self.wfile.write(html_bytes)
                return

            if parsed.path == "/api/data":
                snap = _build_live_snapshot(rec_path, db_path, min_odds=min_odds, sport=sport, run_settle=False)
                self._send_json(snap)
                return

            if parsed.path == "/api/matchup":
                home_q = (qs.get("home") or [""])[0]
                away_q = (qs.get("away") or [""])[0]
                lg_q = (qs.get("league") or [""])[0]
                self._send_json(_lookup_matchup_detail(db_path, rec_path, home_q, away_q, lg_q))
                return

            if parsed.path == "/api/analyze-live":
                q_str = (qs.get("q") or [""])[0]
                self._send_json(_analyze_live_matchup(db_path, rec_path, q_str))
                return

            if parsed.path == "/api/pick-card.png":
                from .pick_card import render_digest_slate_png, render_pick_card_png

                mode_q = (qs.get("mode") or ["single"])[0]
                if mode_q == "slate":
                    rec_d = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
                    b_list = build_best_bets_summary(rec_d, min_odds=min_odds, sport_filter=sport)
                    png_data = render_digest_slate_png(b_list[:10])
                else:
                    match_q = (qs.get("match") or [""])[0]
                    rec_d = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
                    b_list = build_best_bets_summary(rec_d, min_odds=1.01, sport_filter="all")
                    found_b = next((x for x in b_list if x.get("match") == match_q), None)
                    p_payload = dict(found_b) if found_b else {}
                    for k in ("match", "pick", "pick_name", "odds_display", "date_local", "sport_cat", "competition", "tier", "exact_score_pick"):
                        if qs.get(k):
                            p_payload[k] = qs[k][0]
                    if qs.get("win_prob"):
                        try:
                            p_payload["win_prob"] = float(qs["win_prob"][0])
                        except Exception:
                            pass
                    if qs.get("odds"):
                        try:
                            p_payload["odds"] = float(qs["odds"][0])
                        except Exception:
                            pass
                    png_data = render_pick_card_png(p_payload)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(png_data)))
                self.end_headers()
                self.wfile.write(png_data)
                return

            if parsed.path in ("/api/telegram/status", "/api/social/status", "/api/discord/status", "/api/settings"):
                cfg_s = _load_webapp_settings(data_dir)
                self._send_json({
                    "ok": True,
                    "discord": get_discord_env_config(custom_sport_webhooks=cfg_s.get("sport_webhooks")),
                    "telegram": get_telegram_env_config(),
                    "settings": cfg_s,
                    "inplay_alerts_enabled": bool(cfg_s.get("inplay_alerts_enabled", False)),
                    "inplay_alert_items": cfg_s.get("inplay_alert_items") or {},
                })
                return

            if parsed.path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    while True:
                        # Fast DB snapshot every 15s (live ESPN settlement & Discord alerts are handled by the singleton background poller)
                        snap = _build_live_snapshot(
                            rec_path,
                            db_path,
                            min_odds=min_odds,
                            sport=sport,
                            run_settle=False,
                        )
                        msg = f"event: update\ndata: {json.dumps(snap)}\n\n"
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                        time.sleep(15)
                except (BrokenPipeError, ConnectionResetError, Exception):
                    return

            if parsed.path == "/api/best-bets.csv":
                if not best_csv_path.exists():
                    generate_dashboard_html(rec_path, db_path, dash_path, min_odds=min_odds, csv_export_path=best_csv_path)
                data = best_csv_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="best_bets.csv"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if parsed.path == "/api/settled.csv" and settled_csv_path.exists():
                data = settled_csv_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="settled_bets.csv"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            self._send_json({"error": "Not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or "0")
            raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                body = json.loads(raw_body) if raw_body.strip() else {}
            except Exception:
                body = {}

            if parsed.path in ("/api/settings", "/api/settings/inplay-alerts"):
                item_k = body.get("item_key")
                if item_k:
                    saved = _save_webapp_settings(data_dir, item_key=str(item_k), item_enabled=bool(body.get("enabled", False)))
                elif parsed.path == "/api/settings":
                    saved = _save_webapp_settings(data_dir, updates=body)
                else:
                    saved = _save_webapp_settings(data_dir, inplay_alerts_enabled=bool(body.get("enabled", False)))
                self._send_json({
                    "ok": True,
                    "settings": saved,
                    "discord": get_discord_env_config(custom_sport_webhooks=saved.get("sport_webhooks")),
                    **saved,
                })
                return

            if parsed.path in ("/api/settle", "/api/sync", "/api/pipeline"):
                is_full_pipeline = parsed.path == "/api/pipeline" or bool(body.get("full_pipeline", False))
                rescan = is_full_pipeline or bool(body.get("rescan", False))
                min_odds = float(body.get("min_odds") or 1.10)
                new_ingested_count = 0
                try:
                    _PIPELINE_STATUS["running"] = True
                    if is_full_pipeline:
                        _PIPELINE_STATUS["step"] = "[1/4] Running incremental config-driven ingestion & quality check..."
                        ing_res = ingest_universal(
                            db_path=db_path,
                            cache_dir=data_dir / "cache",
                            config_path=root_dir / "ingestion_config.json",
                            mode="incremental",
                        )
                        new_ingested_count = sum(ing_res.get("new_ingested", {}).values())
                    if rescan:
                        _PIPELINE_STATUS["step"] = "[2/4] Settling paper bets & scanning upcoming fixtures across all sports..."
                        scan_upcoming_and_log_paper_trades(
                            db_path=db_path,
                            days_ahead=int(body.get("days") or 3),
                            decision_backend="laya",
                            export_json_path=rec_path,
                        )
                        newly_settled = 0
                    else:
                        _PIPELINE_STATUS["step"] = "Syncing & settling paper-betting ledger against ESPN..."
                        newly_settled = settle_pending_paper_trades(db_path)

                    _PIPELINE_STATUS["step"] = "[3/4] Sending Discord settlement alerts & regenerating dashboard..."
                    notify_new_settlements_to_discord(db_path)
                    generate_dashboard_html(
                        rec_path,
                        db_path,
                        dash_path,
                        min_odds=min_odds,
                        csv_export_path=best_csv_path,
                        json_export_path=best_json_path,
                    )
                finally:
                    _PIPELINE_STATUS["running"] = False
                    _PIPELINE_STATUS["step"] = "Idle"

                snap = _build_live_snapshot(rec_path, db_path, min_odds=min_odds, sport="all", run_settle=False)
                snap["newly_settled"] = newly_settled
                snap["new_ingested_count"] = new_ingested_count
                self._send_json({"ok": True, **snap})
                return

            if parsed.path == "/api/discord":
                from .pick_card import render_digest_slate_png, render_pick_card_png

                cfg_d = _load_webapp_settings(data_dir)
                rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
                custom_text = (body.get("text") or "").strip()
                sp_f = str(body.get("sport") or "all")
                msg = custom_text or format_discord_digest(
                    rec=rec,
                    db_path=db_path,
                    min_odds=float(body.get("min_odds") or 1.15),
                    sport_filter=sp_f,
                    day_filter=str(body.get("day") or "today"),
                    max_picks=int(body.get("max_picks") or 12),
                )
                img_bytes: bytes | None = None
                if body.get("include_image", True):
                    try:
                        pick_card_meta = body.get("pick_card")
                        if isinstance(pick_card_meta, dict) and (pick_card_meta.get("match") or pick_card_meta.get("pick")):
                            b_all = build_best_bets_summary(rec, min_odds=1.01, sport_filter="all")
                            matched_row = next((x for x in b_all if x.get("match") == pick_card_meta.get("match")), {})
                            merged_meta = {**matched_row, **{k: v for k, v in pick_card_meta.items() if v}}
                            img_bytes = render_pick_card_png(merged_meta)
                        else:
                            b_slate = build_best_bets_summary(rec, min_odds=float(body.get("min_odds") or 1.10), sport_filter=sp_f)
                            if b_slate:
                                img_bytes = render_digest_slate_png(b_slate[:10])
                    except Exception:
                        img_bytes = None
                res = send_discord_message(
                    text=msg,
                    webhook_url=body.get("webhook_url"),
                    bot_token=body.get("bot_token"),
                    channel_id=body.get("channel_id"),
                    dry_run=bool(body.get("dry_run", False)),
                    sport=sp_f,
                    custom_sport_webhooks=cfg_d.get("sport_webhooks"),
                    image_bytes=img_bytes,
                )
                # Also route daily digest picks per sport to any dedicated sport webhooks configured in .env
                if sp_f == "all" and not body.get("webhook_url") and not body.get("pick_card"):
                    from .telegram_bot import resolve_discord_webhook_for_sport

                    global_wh = resolve_discord_webhook_for_sport(None, custom_sport_webhooks=cfg_d.get("sport_webhooks"))
                    for sp_cat_k in ("soccer", "tennis", "basketball", "volleyball", "hockey", "football", "baseball"):
                        sp_wh = resolve_discord_webhook_for_sport(sp_cat_k, custom_sport_webhooks=cfg_d.get("sport_webhooks"))
                        if sp_wh and sp_wh != global_wh:
                            sp_bets = build_best_bets_summary(rec, min_odds=float(body.get("min_odds") or 1.15), sport_filter=sp_cat_k)
                            if sp_bets:
                                sp_msg = format_discord_digest(
                                    rec=rec,
                                    db_path=db_path,
                                    min_odds=float(body.get("min_odds") or 1.15),
                                    sport_filter=sp_cat_k,
                                    day_filter=str(body.get("day") or "today"),
                                    max_picks=int(body.get("max_picks") or 12),
                                    include_settled=False,
                                )
                                sp_img = render_digest_slate_png(sp_bets[:10], title=f"{sp_cat_k.upper()} HIGH-CONVICTION PICKS") if body.get("include_image", True) else None
                                send_discord_message(
                                    text=sp_msg,
                                    webhook_url=sp_wh,
                                    dry_run=bool(body.get("dry_run", False)),
                                    image_bytes=sp_img,
                                    also_send_to_global=False,
                                )
                self._send_json({**res, "formatted_message": msg})
                return

            if parsed.path == "/api/telegram":
                from .pick_card import render_digest_slate_png, render_pick_card_png

                rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}
                custom_text = (body.get("text") or "").strip()
                sp_f_tg = str(body.get("sport") or "all")
                msg = custom_text or format_telegram_digest(
                    rec=rec,
                    db_path=db_path,
                    min_odds=float(body.get("min_odds") or 1.15),
                    sport_filter=sp_f_tg,
                    day_filter=str(body.get("day") or "today"),
                    max_picks=int(body.get("max_picks") or 12),
                )
                tg_img_bytes: bytes | None = None
                if body.get("include_image", True):
                    try:
                        pick_card_meta = body.get("pick_card")
                        if isinstance(pick_card_meta, dict) and (pick_card_meta.get("match") or pick_card_meta.get("pick")):
                            b_all = build_best_bets_summary(rec, min_odds=1.01, sport_filter="all")
                            matched_row = next((x for x in b_all if x.get("match") == pick_card_meta.get("match")), {})
                            merged_meta = {**matched_row, **{k: v for k, v in pick_card_meta.items() if v}}
                            tg_img_bytes = render_pick_card_png(merged_meta)
                        else:
                            b_slate = build_best_bets_summary(rec, min_odds=float(body.get("min_odds") or 1.10), sport_filter=sp_f_tg)
                            if b_slate:
                                tg_img_bytes = render_digest_slate_png(b_slate[:10])
                    except Exception:
                        tg_img_bytes = None
                res = send_telegram_message(
                    text=msg,
                    bot_token=body.get("bot_token"),
                    chat_id=body.get("chat_id"),
                    dry_run=bool(body.get("dry_run", False)),
                    image_bytes=tg_img_bytes,
                )
                self._send_json({**res, "formatted_message": msg})
                return

            self._send_json({"error": "Unknown endpoint"}, status=404)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return QuantDeskRequestHandler


class _DaemonThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        _, exc, _ = sys.exc_info()
        if isinstance(exc, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError, OSError)):
            return
        super().handle_error(request, client_address)


def run_webapp_server(root_dir: Path, host: str = "127.0.0.1", port: int = 8090) -> None:
    _start_background_auto_poller(root_dir, interval_sec=90)
    handler_cls = build_webapp_handler(root_dir)
    server = _DaemonThreadingHTTPServer((host, port), handler_cls)
    print(f"🚀 BetScout Web App, Auto-Poller & Social Addon running at http://{host}:{port}")
    print(f"   - Dashboard UI:       http://{host}:{port}/")
    print(f"   - Live SSE Stream:    http://{host}:{port}/api/stream")
    print(f"   - Sync & Settle API:  http://{host}:{port}/api/sync")
    print(f"   - Discord POST API:   http://{host}:{port}/api/discord")
    print(f"   - Telegram POST API:  http://{host}:{port}/api/telegram")
    print("   (Press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down Sportdata Quant Desk Web App server...")
    finally:
        server.server_close()
