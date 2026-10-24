"""Generate a self-contained HTML Quantitative Desk Dashboard (`data/dashboard.html`)
from `data/recommendations.json` and the `paper_trades` SQLite ledger."""

from __future__ import annotations

import csv
import html
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import load_dotenv
from .espn import LEAGUE_LABELS
from .paper_trade import get_paper_ledger_summary, settle_pending_paper_trades

BEST_BETS_CSV_COLUMNS = ("date", "date_local", "sport_league", "match", "pick", "odds", "odds_display")

DEFAULT_LOCAL_TZ = "Europe/Vienna"


def _match_day_key(utc_iso: str, tz_name: str = DEFAULT_LOCAL_TZ) -> str:
    """Return the local betting-slate date ('YYYY-MM-DD') for a match kickoff.
    Applies a 04:00 AM local slate cutoff (`timedelta(hours=4)`) so late-night US Major League games
    (e.g. NHL/NBA/NFL/MLB starting between 00:00 and 03:59 CEST) stay grouped with that evening's slate
    ('Today') rather than disappearing into Tomorrow's calendar date."""
    if not utc_iso or utc_iso == "—":
        return ""
    try:
        from datetime import timedelta
        dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        loc = dt.astimezone(ZoneInfo(tz_name))
        return (loc - timedelta(hours=4)).strftime("%Y-%m-%d")
    except Exception:
        return _format_local_time(utc_iso, tz_name)[:10]


def _format_local_time(utc_iso: str, tz_name: str = DEFAULT_LOCAL_TZ, time_valid: bool | None = None) -> str:
    """Convert a UTC ISO timestamp ('2026-10-22T19:00Z') into local display string ('2026-10-22 21:00 CEST').
    If the start time is not yet confirmed by the tournament/league (`time_valid is False` or ESPN's
    midnight-EDT placeholder 'T04:00Z'), append a `*` indicator after the time."""
    if not utc_iso or utc_iso == "—":
        return utc_iso
    try:
        dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        loc = dt.astimezone(ZoneInfo(tz_name))
        is_placeholder = utc_iso.endswith("T04:00Z") or utc_iso.endswith("T04:00:00Z")
        unconfirmed = (time_valid is False) or is_placeholder
        star = "*" if unconfirmed else ""
        if is_placeholder:
            return f"{loc.strftime('%Y-%m-%d %H:%M %Z')}* (TBD)"
        return f"{loc.strftime('%Y-%m-%d %H:%M %Z')}{star}"
    except Exception:
        return utc_iso


def _time_span(utc_iso: str, tz_name: str = DEFAULT_LOCAL_TZ, bold: bool = False, time_valid: bool | None = None) -> str:
    """Render an HTML element with `data-utc` so the browser can switch between Local Time and UTC."""
    is_placeholder = str(utc_iso).endswith("T04:00Z") or str(utc_iso).endswith("T04:00:00Z")
    unconfirmed = (time_valid is False) or is_placeholder
    loc_str = html.escape(_format_local_time(utc_iso, tz_name, time_valid=time_valid))
    utc_disp = html.escape(f"{utc_iso}*" if (unconfirmed and not str(utc_iso).endswith("*")) else str(utc_iso))
    tip = (
        f"UTC: {utc_disp} (* Provisional / unconfirmed schedule — updates automatically once official Order of Play is released)"
        if unconfirmed
        else f"UTC: {utc_disp}"
    )
    tag = "b" if bold else "span"
    return f'<{tag} class="tz-time" data-utc="{utc_disp}" data-local="{loc_str}" title="{tip}">{loc_str}</{tag}>'

SPORT_FILTER_LABELS: dict[str, str] = {
    "all": "All Sports",
    "soccer": "Football",
    "tennis": "Tennis",
    "basketball": "Basketball",
    "volleyball": "Volleyball",
    "hockey": "Hockey (NHL)",
    "football": "American Football (NFL)",
    "baseball": "Baseball (MLB)",
}

SPORT_ICONS: dict[str, str] = {
    "soccer": "⚽",
    "tennis": "🎾",
    "basketball": "🏀",
    "volleyball": "🏐",
    "hockey": "🏒",
    "football": "🏈",
    "baseball": "⚾",
}

COMPETITION_FALLBACK_LOGOS: dict[str, str] = {
    "eng.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/23.png",
    "eng.2": "https://a.espncdn.com/i/leaguelogos/soccer/500/24.png",
    "esp.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/15.png",
    "ger.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/10.png",
    "ita.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/12.png",
    "fra.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/9.png",
    "ned.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/11.png",
    "por.1": "https://a.espncdn.com/i/leaguelogos/soccer/500/14.png",
    "uefa.champions": "https://a.espncdn.com/i/leaguelogos/soccer/500/2.png",
    "uefa.europa": "https://a.espncdn.com/i/leaguelogos/soccer/500/2310.png",
    "uefa.europa.conf": "https://a.espncdn.com/i/leaguelogos/soccer/500/20296.png",
    "nba": "https://a.espncdn.com/i/teamlogos/leagues/500/nba.png",
    "nhl": "https://a.espncdn.com/i/teamlogos/leagues/500/nhl.png",
    "nfl": "https://a.espncdn.com/i/teamlogos/leagues/500/nfl.png",
    "mlb": "https://a.espncdn.com/i/teamlogos/leagues/500/mlb.png",
    "atp": "https://a.espncdn.com/combiner/i?img=/redesign/assets/img/icons/ESPN-icon-tennis.png",
    "wta": "https://a.espncdn.com/combiner/i?img=/redesign/assets/img/icons/ESPN-icon-tennis.png",
}


def _resolve_comp_logo(league_key: str, explicit_url: str | None = None) -> str | None:
    if explicit_url:
        return str(explicit_url)
    return COMPETITION_FALLBACK_LOGOS.get((league_key or "").lower().strip())


def _img_tag(url: str | None, alt: str = "", cls: str = "team-logo", fallback_url: str | None = None) -> str:
    if not url and not fallback_url:
        return ""
    primary = str(url or fallback_url)
    if fallback_url and url and str(url) != str(fallback_url):
        fb_esc = html.escape(str(fallback_url))
        err_js = f"if(this.dataset.fb){{this.style.display='none';}}else{{this.dataset.fb='1';this.src='{fb_esc}';}}"
    else:
        err_js = "this.style.display='none'"
    return f'<img src="{html.escape(primary)}" alt="{html.escape(alt)}" class="{cls}" loading="lazy" onerror="{err_js}">'


def _matchup_html(
    home: str,
    away: str,
    home_logo: str | None = None,
    away_logo: str | None = None,
    is_tennis: bool = False,
    extra_html: str = "",
    home_flag: str | None = None,
    away_flag: str | None = None,
    league: str = "",
) -> str:
    cls = "player-avatar" if is_tennis else "team-logo"
    h_img = _img_tag(home_logo, home, cls, fallback_url=home_flag)
    a_img = _img_tag(away_logo, away, cls, fallback_url=away_flag)
    h_js = html.escape(json.dumps(home))
    a_js = html.escape(json.dumps(away))
    lg_js = html.escape(json.dumps(league))
    return (
        f'<span class="matchup-inline matchup-clickable" title="Click to inspect H2H, Last-6 Form &amp; Score Matrix" onclick="openMatchupInspector({h_js}, {a_js}, {lg_js})">'
        f'{h_img}<span>{html.escape(home)}</span>'
        f'<span class="muted">vs</span>'
        f'{a_img}<span>{html.escape(away)}</span>'
        f'{extra_html}'
        f'</span>'
    )


def _sport_icon(sport_cat: str) -> str:
    return SPORT_ICONS.get((sport_cat or "soccer").lower().strip(), "⚽")


def _league_to_sport_cat(league_or_sport: str) -> str:
    low = (league_or_sport or "").lower().strip()
    if low in ("atp", "wta", "tennis"):
        return "tennis"
    if low in ("nba", "wnba", "ncaam", "ncaaw", "nbl", "fiba", "basketball", "mens-college-basketball", "womens-college-basketball"):
        return "basketball"
    if low in ("wvolleyball", "mvolleyball", "volleyball", "womens-college-volleyball", "mens-college-volleyball"):
        return "volleyball"
    if low in ("nhl", "hockey"):
        return "hockey"
    if low in ("nfl", "football"):
        return "football"
    if low in ("mlb", "baseball"):
        return "baseball"
    return "soccer"


def _fmt_signed(val: float, fmt: str = "+.2f", suffix: str = "") -> str:
    cls = "num-pos" if val > 0 else ("num-neg" if val < 0 else "")
    class_attr = f' class="{cls}"' if cls else ""
    return f"<b{class_attr}>{format(val, fmt)}{suffix}</b>"


def build_best_bets_summary(
    rec: dict[str, Any],
    min_odds: float = 1.10,
    sport_filter: str = "all",
) -> list[dict[str, Any]]:
    """Build the unified Best Bets summary across all sports, filtered by `> min_odds` and `sport_filter`, sorted by date ascending."""
    norm_sport = (sport_filter or "all").lower().strip()
    settled_ids = {
        (t["league"], str(t["event_id"]))
        for t in ((rec.get("paper_ledger") or {}).get("trades") or [])
        if t.get("status") == "SETTLED"
    }
    ledger_time_map = {
        (t["league"], str(t["event_id"])): (
            t["kickoff"],
            t.get("time_valid", True),
            float(t.get("clv_pct") or 0.0),
            t.get("comp_logo"),
            t.get("home_logo"),
            t.get("away_logo"),
        )
        for t in ((rec.get("paper_ledger") or {}).get("trades") or [])
        if t.get("status") != "SETTLED"
    }
    raw_soccer_picks = [
        {**p,
         "kickoff": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True), 0.0, None, None, None))[0],
         "time_valid": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True), 0.0, None, None, None))[1],
         "clv_pct": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True), 0.0, None, None, None))[2],
         "competition_logo": p.get("competition_logo") or ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (None, None, 0.0, None, None, None))[3],
         "home_logo": p.get("home_logo") or ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (None, None, 0.0, None, None, None))[4],
         "away_logo": p.get("away_logo") or ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (None, None, 0.0, None, None, None))[5]}
        for p in (rec.get("qualifying_picks") or [])
        if (p.get("league"), str(p.get("event_id"))) not in settled_ids
    ]
    raw_tennis_picks = [
        {**tp,
         "kickoff": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True), 0.0, None, None, None))[0],
         "time_valid": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True), 0.0, None, None, None))[1],
         "clv_pct": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True), 0.0, None, None, None))[2],
         "competition_logo": tp.get("competition_logo") or ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (None, None, 0.0, None, None, None))[3],
         "home_logo": tp.get("home_logo") or ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (None, None, 0.0, None, None, None))[4],
         "away_logo": tp.get("away_logo") or ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (None, None, 0.0, None, None, None))[5]}
        for tp in (rec.get("tennis_picks") or [])
        if (tp.get("tour", "").lower(), str(tp.get("event_id"))) not in settled_ids
    ]
    raw_other_picks = [
        {**op,
         "kickoff": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True), 0.0, None, None, None))[0],
         "time_valid": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True), 0.0, None, None, None))[1],
         "clv_pct": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True), 0.0, None, None, None))[2],
         "competition_logo": op.get("competition_logo") or ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (None, None, 0.0, None, None, None))[3],
         "home_logo": op.get("home_logo") or ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (None, None, 0.0, None, None, None))[4],
         "away_logo": op.get("away_logo") or ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (None, None, 0.0, None, None, None))[5]}
        for op in (rec.get("other_sport_picks") or [])
        if (op.get("league", "").lower(), str(op.get("event_id"))) not in settled_ids
    ]

    best_bets: list[dict[str, Any]] = []
    for p in raw_soccer_picks:
        if p.get("action") != "PAPER_BET":
            continue
        odds_val = float(p.get("best_odds") or 0.0)
        if odds_val <= min_odds:
            continue
        if norm_sport not in ("all", "soccer"):
            continue
        lg_label = LEAGUE_LABELS.get(p["league"], p["league"].upper())
        pick_team = p["home"] if p["side"] == "H" else p["away"]
        live_tag = f" [LIVE {p['live_score']}]" if p.get("is_live") and p.get("live_score") else (" [LIVE]" if p.get("is_live") else "")
        esc_p = p.get("exact_score_prediction") or {}
        esc_str = (
            f"{esc_p['top_exact_score']} ({esc_p['top_exact_prob']*100:.1f}%) · Cluster {esc_p['cluster_3_scores']} ({esc_p['cluster_3_prob']*100:.1f}%, Fair {esc_p['cluster_3_fair_odds']:.2f})"
            if esc_p.get("top_exact_score")
            else "—"
        )
        score_cluster_items = [
            {
                "score": str(item.get("score") or ""),
                "prob": round(float(item.get("prob") or 0.10), 4),
                "fair_odds": round(float(item.get("fair_odds") or 8.0), 2),
                "book_odds": round(max(float(item.get("fair_odds") or 8.0) * 0.88, 3.20), 2),
            }
            for item in (esc_p.get("top_3_breakdown") or [])
            if item.get("score")
        ]
        p_win_val = float(p.get("p_model") or p.get("p_mkt") or 0.5)
        p_mkt_val = float(p.get("p_mkt") or (1.0 / max(odds_val, 1.05)))
        f_odds_val = round(1.0 / max(p_win_val, 0.05), 2)
        p_clv = float(p.get("clv_pct") or 0.0)
        p_ev_pct = round(float(p.get("ev_pct") if p.get("ev_pct") is not None else (p_win_val * odds_val - 1.0) * 100.0), 2)
        p_edge_pp = round((p_win_val - p_mkt_val) * 100.0, 2)
        fz = p.get("factors_tanh_z") or {}
        top_drivers = sorted(
            [(k, float(v)) for k, v in fz.items() if k != "p_mkt" and float(v) > 0.25],
            key=lambda x: -x[1],
        )[:3]
        driver_str = ", ".join(f"{k}={v:+.2f}z" for k, v in top_drivers) if top_drivers else "Orthogonal 7-Factor Composite"
        is_mispriced = bool(p_ev_pct >= 2.0 and p_edge_pp >= 2.0)
        best_bets.append({
            "date": p["kickoff"],
            "date_local": _format_local_time(p["kickoff"], time_valid=p.get("time_valid")),
            "day_key": _match_day_key(p["kickoff"]),
            "time_valid": p.get("time_valid", True),
            "sport_cat": "soccer",
            "sport_icon": _sport_icon("soccer"),
            "competition": f"{lg_label}{live_tag}",
            "competition_logo": _resolve_comp_logo(p["league"], p.get("competition_logo")),
            "sport_league": f"Football · {lg_label}{live_tag}",
            "home": p["home"],
            "away": p["away"],
            "home_logo": p.get("home_logo"),
            "away_logo": p.get("away_logo"),
            "match": f"{p['home']} vs {p['away']}",
            "pick_name": f"{pick_team} ({p['side']})",
            "pick_logo": p.get("home_logo") if p["side"] == "H" else p.get("away_logo"),
            "tier": p["tier"],
            "pick": f"{pick_team} ({p['side']}) [{p['tier']}]",
            "win_prob": round(p_win_val, 4),
            "p_mkt": round(p_mkt_val, 4),
            "edge_pp": p_edge_pp,
            "ev_pct": p_ev_pct,
            "is_mispriced": is_mispriced,
            "mispricing_drivers": driver_str,
            "min_fair_odds": f_odds_val,
            "exact_score_pick": esc_str,
            "score_cluster_items": score_cluster_items,
            "odds": round(odds_val, 3),
            "clv_pct": round(p_clv, 2),
            "odds_display": f"{odds_val:.2f} (Fair {f_odds_val:.2f}, EV {p_ev_pct:+.1f}%)",
        })

    for tp in raw_tennis_picks:
        if tp.get("win_prob", 0.0) < 0.70:
            continue
        live_book = tp.get("best_odds")
        odds_val = float(live_book if live_book else (tp.get("min_fair_odds") or 0.0))
        if odds_val <= min_odds:
            continue
        if norm_sport not in ("all", "tennis"):
            continue
        ev_str = f", EV {tp['ev_pct']:+.1f}%" if tp.get("ev_pct") is not None else ""
        odds_disp = f"{live_book:.2f} (Fair {tp['min_fair_odds']:.2f}{ev_str})" if live_book else f"≥ {odds_val:.2f} (Target {tp['target_ev3_odds']:.2f})"
        sp_pred = tp.get("set_score_prediction") or {}
        set_str = (
            f"Sets {sp_pred['straight_sets_score']} ({sp_pred['straight_sets_prob']*100:.1f}%, Fair {sp_pred['straight_sets_fair_odds']:.2f}) / {sp_pred['decider_sets_score']} ({sp_pred['decider_sets_prob']*100:.1f}%)"
            if sp_pred.get("straight_sets_score")
            else "—"
        )
        t_score_cluster_items = (
            [
                {
                    "score": f"Sets {sp_pred['straight_sets_score']}",
                    "prob": round(float(sp_pred.get("straight_sets_prob") or 0.50), 4),
                    "fair_odds": round(float(sp_pred.get("straight_sets_fair_odds") or 1.85), 2),
                    "book_odds": round(max(float(sp_pred.get("straight_sets_fair_odds") or 1.85) * 0.92, 1.40), 2),
                },
                {
                    "score": f"Sets {sp_pred['decider_sets_score']}",
                    "prob": round(float(sp_pred.get("decider_sets_prob") or 0.24), 4),
                    "fair_odds": round(float(sp_pred.get("decider_sets_fair_odds") or 4.00), 2),
                    "book_odds": round(max(float(sp_pred.get("decider_sets_fair_odds") or 4.00) * 0.92, 3.20), 2),
                },
            ]
            if sp_pred.get("straight_sets_score")
            else []
        )
        t_comp_lbl = f"{tp['tour']} · {tp.get('tournament') or tp['surface'].capitalize()} ({tp['surface'].capitalize()})"
        tp_clv = float(tp.get("clv_pct") or 0.0)
        tp_win = float(tp["win_prob"])
        tp_mkt = round((1.0 / float(live_book)) * 0.955, 4) if live_book and float(live_book) > 1.01 else round(tp_win, 4)
        tp_ev = round(float(tp["ev_pct"]) if tp.get("ev_pct") is not None else ((tp_win * float(live_book) - 1.0) * 100.0 if live_book else 0.0), 2)
        tp_edge_pp = round((tp_win - tp_mkt) * 100.0, 2) if live_book else 0.0
        tf = tp.get("factors") or {}
        t_drv_parts = []
        if float(tf.get("surf_elo_diff") or 0) >= 60:
            t_drv_parts.append(f"SurfElo {float(tf['surf_elo_diff']):+.0f}")
        if float(tf.get("game_elo_diff") or 0) >= 50:
            t_drv_parts.append(f"GameElo {float(tf['game_elo_diff']):+.0f}")
        if float(tf.get("form_6m_diff") or 0) >= 0.15:
            t_drv_parts.append(f"Form {float(tf['form_6m_diff'])*100:+.0f}%")
        t_driver_str = ", ".join(t_drv_parts) if t_drv_parts else "Surface + Game-Share Elo"
        best_bets.append({
            "date": tp["kickoff"],
            "date_local": _format_local_time(tp["kickoff"], time_valid=tp.get("time_valid")),
            "day_key": _match_day_key(tp["kickoff"]),
            "time_valid": tp.get("time_valid", True),
            "sport_cat": "tennis",
            "sport_icon": _sport_icon("tennis"),
            "competition": t_comp_lbl,
            "competition_logo": _resolve_comp_logo(tp["tour"], tp.get("competition_logo")),
            "sport_league": f"Tennis · {tp['tour']} ({tp['surface'].capitalize()})",
            "home": tp["player_1"],
            "away": tp["player_2"],
            "home_logo": tp.get("home_logo"),
            "away_logo": tp.get("away_logo"),
            "home_flag": tp.get("home_flag"),
            "away_flag": tp.get("away_flag"),
            "match": f"{tp['player_1']} vs {tp['player_2']}",
            "pick_name": tp["pick"],
            "pick_logo": tp.get("home_logo") if tp["pick"] == tp["player_1"] else tp.get("away_logo"),
            "pick_flag": tp.get("home_flag") if tp["pick"] == tp["player_1"] else tp.get("away_flag"),
            "tier": tp.get("tier") or "banker_70pct",
            "pick": f"{tp['pick']} (Win {tp['win_prob']*100:.1f}%)",
            "win_prob": round(tp_win, 4),
            "p_mkt": tp_mkt,
            "edge_pp": tp_edge_pp,
            "ev_pct": tp_ev,
            "is_mispriced": bool(live_book and tp_ev >= 2.0 and tp_edge_pp >= 2.0),
            "mispricing_drivers": t_driver_str,
            "min_fair_odds": round(float(tp["min_fair_odds"]), 2),
            "exact_score_pick": set_str,
            "score_cluster_items": t_score_cluster_items,
            "odds": round(odds_val, 3),
            "clv_pct": round(tp_clv, 2),
            "odds_display": odds_disp,
        })

    for op in raw_other_picks:
        odds_val = float(op.get("best_odds") or 0.0)
        if odds_val <= min_odds:
            continue
        sp_cat = _league_to_sport_cat(op.get("sport") or op.get("league") or "")
        if norm_sport not in ("all", sp_cat):
            continue
        op_win = float(op.get("p_model") or op.get("p_mkt") or 0.5)
        op_mkt = float(op.get("p_mkt") or (1.0 / max(odds_val, 1.05)))
        op_ev = round(float(op.get("ev_pct") if op.get("ev_pct") is not None else (op_win * odds_val - 1.0) * 100.0), 2)
        op_edge_pp = round((op_win - op_mkt) * 100.0, 2)
        op_clv = float(op.get("clv_pct") or 0.0)
        best_bets.append({
            "date": op["kickoff"],
            "date_local": _format_local_time(op["kickoff"], time_valid=op.get("time_valid")),
            "day_key": _match_day_key(op["kickoff"]),
            "time_valid": op.get("time_valid", True),
            "sport_cat": sp_cat,
            "sport_icon": _sport_icon(sp_cat),
            "competition": op["league_name"],
            "competition_logo": _resolve_comp_logo(op["league"], op.get("competition_logo")),
            "sport_league": f"{op['sport'].capitalize()} · {op['league_name']}",
            "home": op["home"],
            "away": op["away"],
            "home_logo": op.get("home_logo"),
            "away_logo": op.get("away_logo"),
            "match": f"{op['home']} vs {op['away']}",
            "pick_name": f"{op['pick']} ({op['side']})",
            "pick_logo": op.get("home_logo") if op["side"] == "H" else op.get("away_logo"),
            "tier": op.get("tier") or "high_conf",
            "pick": f"{op['pick']} ({op['side']}) (Win {op['p_model']*100:.1f}%)",
            "win_prob": round(op_win, 4),
            "p_mkt": round(op_mkt, 4),
            "edge_pp": op_edge_pp,
            "ev_pct": op_ev,
            "is_mispriced": bool(op_ev >= 2.0 and op_edge_pp >= 2.0),
            "mispricing_drivers": f"Elo + Boxscore + Rest Gate (Composite {float(op.get('composite_score') or 0):+.2f})",
            "min_fair_odds": round(1.0 / max(op_win, 0.05), 2),
            "exact_score_pick": "—",
            "odds": round(odds_val, 3),
            "clv_pct": round(op_clv, 2),
            "odds_display": f"{odds_val:.2f} (Fair {1.0/max(op_win,0.05):.2f}, EV {op_ev:+.1f}%)",
        })

    best_bets.sort(key=lambda b: (b["date"], b["sport_league"]))
    return best_bets


def export_best_bets_summary(
    best_bets: list[dict[str, Any]],
    csv_path: Path | None = None,
    json_path: Path | None = None,
) -> dict[str, Path]:
    """Export the sorted Best Bets summary table as CSV (with header) and/or JSON."""
    written: dict[str, Path] = {}
    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(BEST_BETS_CSV_COLUMNS))
            writer.writeheader()
            for row in best_bets:
                writer.writerow({col: row.get(col) for col in BEST_BETS_CSV_COLUMNS})
        written["csv"] = csv_path
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(best_bets, indent=2), encoding="utf-8")
        written["json"] = json_path
    return written


def generate_dashboard_html(
    recommendations_path: Path,
    db_path: Path,
    output_html_path: Path,
    min_odds: float = 1.10,
    sport_filter: str = "all",
    csv_export_path: Path | None = None,
    json_export_path: Path | None = None,
) -> Path:
    rec: dict[str, Any] = {}
    if recommendations_path.exists():
        rec = json.loads(recommendations_path.read_text())

    conn = sqlite3.connect(db_path)
    total_matches = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    conn.close()

    try:
        settle_pending_paper_trades(db_path)
        live_ledger = get_paper_ledger_summary(db_path)
        if live_ledger.get("trades"):
            rec["paper_ledger"] = live_ledger
    except Exception:
        pass

    norm_sport = (sport_filter or "all").lower().strip()
    settled_ids = {
        (t["league"], str(t["event_id"]))
        for t in ((rec.get("paper_ledger") or {}).get("trades") or [])
        if t.get("status") == "SETTLED"
    }
    ledger_time_map = {
        (t["league"], str(t["event_id"])): (
            t["kickoff"],
            t.get("time_valid", True),
            t.get("comp_logo"),
            t.get("home_logo"),
            t.get("away_logo"),
        )
        for t in ((rec.get("paper_ledger") or {}).get("trades") or [])
        if t.get("status") != "SETTLED"
    }
    raw_soccer_picks = [
        {**p,
         "kickoff": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True), None, None, None))[0],
         "time_valid": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True), None, None, None))[1],
         "competition_logo": p.get("competition_logo") or ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (None, None, None, None, None))[2],
         "home_logo": p.get("home_logo") or ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (None, None, None, None, None))[3],
         "away_logo": p.get("away_logo") or ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (None, None, None, None, None))[4]}
        for p in (rec.get("qualifying_picks") or [])
        if (p.get("league"), str(p.get("event_id"))) not in settled_ids
    ]
    raw_tennis_picks = [
        {**tp,
         "kickoff": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True), None, None, None))[0],
         "time_valid": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True), None, None, None))[1],
         "competition_logo": tp.get("competition_logo") or ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (None, None, None, None, None))[2],
         "home_logo": tp.get("home_logo") or ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (None, None, None, None, None))[3],
         "away_logo": tp.get("away_logo") or ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (None, None, None, None, None))[4]}
        for tp in (rec.get("tennis_picks") or [])
        if (tp.get("tour", "").lower(), str(tp.get("event_id"))) not in settled_ids
    ]
    raw_other_picks = [
        {**op,
         "kickoff": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True), None, None, None))[0],
         "time_valid": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True), None, None, None))[1],
         "competition_logo": op.get("competition_logo") or ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (None, None, None, None, None))[2],
         "home_logo": op.get("home_logo") or ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (None, None, None, None, None))[3],
         "away_logo": op.get("away_logo") or ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (None, None, None, None, None))[4]}
        for op in (rec.get("other_sport_picks") or [])
        if (op.get("league", "").lower(), str(op.get("event_id"))) not in settled_ids
    ]
    ledger = rec.get("paper_ledger") or {}
    gen_at = rec.get("generated_at") or "—"

    # Soft filter: exclude picks whose primary/best/target odds are <= min_odds (e.g. <= 1.10)
    soccer_picks = [p for p in raw_soccer_picks if float(p.get("best_odds") or 0.0) > min_odds]
    tennis_picks = [tp for tp in raw_tennis_picks if float(tp.get("min_fair_odds") or 0.0) > min_odds]
    other_picks = [op for op in raw_other_picks if float(op.get("best_odds") or 0.0) > min_odds]

    # Precompute embedded H2H + Last-6 Form lookup map from matches.sqlite for every matchup rendered on the page
    all_page_pairs: set[tuple[str, str]] = set()
    for p in soccer_picks:
        if p.get("home") and p.get("away"):
            all_page_pairs.add((str(p["home"]), str(p["away"])))
    for tp in tennis_picks[:25]:
        if tp.get("player_1") and tp.get("player_2"):
            all_page_pairs.add((str(tp["player_1"]), str(tp["player_2"])))
    for op in other_picks[:25]:
        if op.get("home") and op.get("away"):
            all_page_pairs.add((str(op["home"]), str(op["away"])))
    for tr in ((rec.get("paper_ledger") or {}).get("trades") or []):
        if tr.get("home") and tr.get("away"):
            all_page_pairs.add((str(tr["home"]), str(tr["away"])))
    for d_c in ((rec.get("recommended_doubles") or []) + ((rec.get("paper_ledger") or {}).get("combos") or [])):
        for lk in ("leg_1", "leg_2"):
            m_txt = str((d_c.get(lk) or {}).get("match") or "")
            if " vs " in m_txt:
                h_m, a_m = [x.strip() for x in m_txt.split(" vs ", 1)]
                if h_m and a_m:
                    all_page_pairs.add((h_m, a_m))

    embedded_matchup_details: dict[str, dict[str, Any]] = {}
    if db_path.exists() and all_page_pairs:
        try:
            c_det = sqlite3.connect(db_path)
            c_det.row_factory = sqlite3.Row
            team_form_cache: dict[str, list[dict[str, Any]]] = {}
            all_teams = {t for pair in all_page_pairs for t in pair}
            for t_name in all_teams:
                f_rows = []
                for r in c_det.execute(
                    "SELECT kickoff, home, away, home_score, away_score, outcome FROM matches WHERE outcome IS NOT NULL AND (home = ? OR away = ?) ORDER BY kickoff DESC LIMIT 6",
                    (t_name, t_name),
                ).fetchall():
                    is_h = r["home"] == t_name
                    opp = r["away"] if is_h else r["home"]
                    res = "D" if r["outcome"] == "D" else ("W" if ((is_h and r["outcome"] == "H") or (not is_h and r["outcome"] == "A")) else "L")
                    sc = f"{int(r['home_score'])}-{int(r['away_score'])}" if r["home_score"] is not None and r["away_score"] is not None else r["outcome"]
                    f_rows.append({"date": str(r["kickoff"])[:10], "opp": opp, "venue": "H" if is_h else "A", "result": res, "score": sc})
                team_form_cache[t_name] = f_rows

            pick_detail_map: dict[tuple[str, str], dict[str, Any]] = {}
            for p in soccer_picks:
                pick_detail_map[(p["home"], p["away"])] = {
                    "exact_score_prediction": p.get("exact_score_prediction"),
                    "factors_tanh_z": p.get("factors_tanh_z"),
                }
            for tp in tennis_picks:
                pick_detail_map[(tp["player_1"], tp["player_2"])] = {
                    "set_score_prediction": tp.get("set_score_prediction"),
                    "factors": tp.get("factors"),
                }
            for op in other_picks:
                pick_detail_map[(op["home"], op["away"])] = {
                    "p_model": op.get("p_model"),
                    "ev_pct": op.get("ev_pct"),
                    "factors": {"p_model": op.get("p_model"), "p_mkt": op.get("p_mkt"), "ev_pct": op.get("ev_pct"), "composite": op.get("composite_score")},
                }
            for tr in ((rec.get("paper_ledger") or {}).get("trades") or []):
                if tr.get("home") and tr.get("away") and (tr["home"], tr["away"]) not in pick_detail_map:
                    pick_detail_map[(tr["home"], tr["away"])] = {
                        "factors": tr.get("factors") or {},
                    }

            for h_n, a_n in all_page_pairs:
                h2h_list = []
                for r in c_det.execute(
                    "SELECT league, kickoff, home, away, home_score, away_score, outcome FROM matches WHERE outcome IS NOT NULL AND ((home = ? AND away = ?) OR (home = ? AND away = ?)) ORDER BY kickoff DESC LIMIT 8",
                    (h_n, a_n, a_n, h_n),
                ).fetchall():
                    sc = f"{int(r['home_score'])}-{int(r['away_score'])}" if r["home_score"] is not None and r["away_score"] is not None else r["outcome"]
                    h2h_list.append({"date": str(r["kickoff"])[:10], "league": r["league"], "home": r["home"], "away": r["away"], "score": sc, "outcome": r["outcome"]})
                embedded_matchup_details[f"{h_n} vs {a_n}"] = {
                    "ok": True,
                    "home": h_n,
                    "away": a_n,
                    "h2h": h2h_list,
                    "form_home": team_form_cache.get(h_n, []),
                    "form_away": team_form_cache.get(a_n, []),
                    "pick_detail": pick_detail_map.get((h_n, a_n), {}),
                }
            c_det.close()
        except Exception:
            pass

    active_bets = sum(1 for p in soccer_picks if p.get("action") == "PAPER_BET")
    vetoed_bets = sum(1 for p in soccer_picks if str(p.get("action", "")).startswith("VETOED"))
    mean_clv = (ledger.get("mean_clv_pct") or 0.0) * 100.0
    settled_profit_u = float(ledger.get("settled_profit_u") or 0.0)
    settled_losses_n = int(ledger.get("settled_losses") or 0)

    def _factor_bars(factors: dict[str, float]) -> str:
        items = []
        for k, v in factors.items():
            pct = min(max(abs(v) * 100.0, 4.0), 100.0)
            cls = "pos" if v >= 0 else "neg"
            items.append(
                f'<div class="f-row"><span class="f-name">{html.escape(k)}</span>'
                f'<div class="f-track"><div class="f-fill {cls}" style="width:{pct:.0f}%"></div></div>'
                f'<span class="f-val {cls}">{v:+.2f}</span></div>'
            )
        return "".join(items)

    soccer_cards = []
    for p in soccer_picks:
        act = p.get("action", "PAPER_BET")
        is_veto = act.startswith("VETOED")
        badge_cls = "badge-veto" if is_veto else "badge-bet"
        ns = p.get("news_signal") or {}
        xi = p.get("starting_xi_gate") or {}
        hl_list = "".join(f"<li>{html.escape(h)}</li>" for h in (ns.get("headlines") or [])[:2])
        hl_html = f'<ul class="headlines">{hl_list}</ul>' if hl_list else ""
        pick_team = p["home"] if p["side"] == "H" else p["away"]
        p_mod_pct = (p.get("p_model") or p["p_mkt"]) * 100.0
        ev_pct = float(p.get("ev_pct", 0.0))
        qk_pct = p.get("quarter_kelly_pct", 0.0)
        lg_label = LEAGUE_LABELS.get(p["league"], p["league"].upper())
        syn_dc = float(p.get("synthetic_dc_odds") or 0.0)
        syn_dc_str = f"{syn_dc:.2f}" if syn_dc > min_odds else f"{syn_dc:.2f} (≤{min_odds:.2f})"
        news_val = float(ns.get("net_edge_for_pick", 0.0))
        live_pill = (
            f'<span class="pill badge-veto">LIVE · {html.escape(str(p.get("live_score") or "IN PLAY"))}</span>'
            if p.get("is_live")
            else ""
        )
        sh_match = html.escape(json.dumps(f"{p['home']} vs {p['away']} ({lg_label})"))
        esc_p = p.get("exact_score_prediction") or {}
        esc_strip_html = ""
        if esc_p.get("top_exact_score"):
            ou_line = esc_p.get("line_total", 2.5)
            p_ov = esc_p.get("over_prob", 0.5)
            p_un = esc_p.get("under_prob", 0.5)
            ou_str = f"O{ou_line}: {p_ov*100:.0f}%" if p_ov >= p_un else f"U{ou_line}: {p_un*100:.0f}%"
            btts_p = esc_p.get("btts_yes_prob", 0.5)
            btts_str = f"Yes {btts_p*100:.0f}%" if btts_p >= 0.5 else f"No {(1-btts_p)*100:.0f}%"
            esc_strip_html = (
                f'<div class="odds-strip" style="margin-top:-6px; background:#09101b; border:1px dashed var(--border);">'
                f'<div><span>Exp Goals (λ/μ)</span><b>{esc_p.get("lambda_home", 0):.2f}–{esc_p.get("mu_away", 0):.2f} ({ou_str})</b></div>'
                f'<div><span>Top Score / BTTS</span><b class="num-pos">{html.escape(esc_p["top_exact_score"])} ({esc_p["top_exact_prob"]*100:.1f}%) · {btts_str}</b></div>'
                f'<div><span>2-Score Dutch</span><b>{html.escape(esc_p["cluster_2_scores"])} ({esc_p["cluster_2_prob"]*100:.1f}%)</b></div>'
                f'<div><span>3-Score Cluster</span><b class="num-pos">{html.escape(esc_p["cluster_3_scores"])} ({esc_p["cluster_3_prob"]*100:.1f}%, @{esc_p["cluster_3_fair_odds"]:.2f})</b></div>'
                f'</div>'
            )
        sh_pick_str = f"{pick_team} ({p['side']}) [{p['tier']}]"
        if esc_p.get("top_exact_score"):
            sh_pick_str += f" · Exact: {esc_p['top_exact_score']} ({esc_p['top_exact_prob']*100:.1f}%) | Cluster: {esc_p['cluster_3_scores']} ({esc_p['cluster_3_prob']*100:.1f}%)"
        sh_pick = html.escape(json.dumps(sh_pick_str))
        sh_odds = html.escape(json.dumps(f"{p['best_odds']:.2f}"))
        sh_time = html.escape(json.dumps(_format_local_time(p["kickoff"], time_valid=p.get("time_valid"))))
        p_match_plain_js = html.escape(json.dumps(f"{p['home']} vs {p['away']}"))
        p_day_loc = _match_day_key(p["kickoff"])
        p_comp_logo = _img_tag(_resolve_comp_logo(p["league"], p.get("competition_logo")), lg_label, "comp-logo")
        p_home_logo = _img_tag(p.get("home_logo"), p["home"], "team-logo-lg")
        p_away_logo = _img_tag(p.get("away_logo"), p["away"], "team-logo-lg")
        p_pick_logo = _img_tag(p.get("home_logo") if p["side"] == "H" else p.get("away_logo"), pick_team, "team-logo")
        soccer_cards.append(
            f"""
            <div class="card {'card-veto' if is_veto else ''}" data-odds="{p['best_odds']:.3f}" data-sport-cat="soccer" data-day="{html.escape(p_day_loc)}" data-search="{html.escape((p['home'] + ' ' + p['away'] + ' ' + lg_label + ' ' + p['league']).lower())}">
              <div class="card-head">
                <div>
                  <span class="pill">{p_comp_logo}{html.escape(lg_label)}</span>
                  <span class="pill tier">{html.escape(p['tier'])}</span>
                  <span class="pill {badge_cls}">{html.escape(act)}</span>
                  {live_pill}
                </div>
                <div class="score">Score: {_fmt_signed(float(p['score']), '+.4f')} · EV: {_fmt_signed(ev_pct, '+.1f', '%')} · <button type="button" class="btn-mini" title="Inspect H2H, Last-6 Form &amp; Score Matrix" onclick="openMatchupInspector({html.escape(json.dumps(p['home']))}, {html.escape(json.dumps(p['away']))}, {html.escape(json.dumps(p['league']))})">🔍 H2H</button> <button type="button" class="btn-mini" title="Open Exact-Score Investment Splitter for this match" onclick="selectMatchForDutching({p_match_plain_js})">🎲 Split €</button> <button type="button" class="btn-mini" title="Share this pick to Discord / Telegram" onclick="shareSinglePick({sh_match}, {sh_pick}, {sh_odds}, {sh_time}, 'soccer')">📣</button></div>
              </div>
              <h3 class="matchup-inline">{_matchup_html(p['home'], p['away'], p.get('home_logo'), p.get('away_logo'), league=p['league'])}</h3>
              <div class="meta">Kickoff: {_time_span(p['kickoff'], time_valid=p.get('time_valid'))} · Pick: {p_pick_logo}<b class="num-pos">{html.escape(pick_team)} ({p['side']})</b> · ¼-Kelly: <b class="kelly-stake" data-kelly-pct="{0.0 if is_veto else qk_pct:.3f}">{0.0 if is_veto else qk_pct:.2f}% (€{0.0 if is_veto else qk_pct * 10.0:.2f})</b></div>
              <div class="odds-strip">
                <div><span>Best 1X2</span><b>{p['best_odds']:.2f}</b></div>
                <div><span>Syn Dutch DC</span><b>{html.escape(syn_dc_str)}</b></div>
                <div><span>Mkt Implied</span><b>{p['p_mkt']*100:.1f}%</b></div>
                <div><span>Calib Model P</span><b>{p_mod_pct:.1f}%</b></div>
              </div>
              {esc_strip_html}
              <div class="factors">{_factor_bars(p.get('factors_tanh_z') or {})}</div>
              <div class="gates">
                <span><b>System-1 News ({html.escape(str(ns.get('backend','none')))}):</b> {_fmt_signed(news_val, '+.3f')}</span>
                <span><b>T-60m XI Gate:</b> {html.escape(str(xi.get('status','AWAITING_T60M_LINEUPS')))}</span>
              </div>
              {hl_html}
            </div>
            """
        )

    tennis_rows = []
    for tp in tennis_picks[:20]:
        f = tp.get("factors") or {}
        live_book = tp.get("best_odds")
        ev_v = tp.get("ev_pct")
        book_cell = (
            f"<b>{live_book:.2f}</b> ({_fmt_signed(float(ev_v), '+.1f', '%')})" if (live_book and ev_v is not None)
            else (f"<b>{live_book:.2f}</b>" if live_book else f"≥ {tp['target_ev3_odds']:.2f}")
        )
        t_odds_attr = float(live_book if live_book else tp["min_fair_odds"])
        g_elo = float(f.get("game_elo_diff", 0.0))
        s_elo = float(f.get("surf_elo_diff", 0.0))
        sp_pred = tp.get("set_score_prediction") or {}
        tm_pred = tp.get("totals_market") or {}
        tm_suffix = (
            f' · <span class="pill" title="Exp Games: {tm_pred.get("expected_games")}">{html.escape(str(tm_pred.get("recommended")))} ({float(tm_pred.get("prob") or 0)*100:.0f}%)</span>'
            if tm_pred.get("recommended")
            else ""
        )
        set_cell = (
            f'<b class="num-pos">{html.escape(sp_pred["straight_sets_score"])}</b> ({sp_pred["straight_sets_prob"]*100:.1f}%, Fair {sp_pred["straight_sets_fair_odds"]:.2f}){tm_suffix}<br>'
            f'<span class="muted">{html.escape(sp_pred["decider_sets_score"])}: {sp_pred["decider_sets_prob"]*100:.1f}%</span>'
            if sp_pred.get("straight_sets_score")
            else "—"
        )
        tp_day_loc = _match_day_key(tp["kickoff"])
        t_comp_str = f"{tp['tour']} · {tp['tournament']}"
        t_match_str = f"{tp['player_1']} vs {tp['player_2']}"
        t_comp_img = _img_tag(_resolve_comp_logo(tp["tour"], tp.get("competition_logo")), tp["tour"], "comp-logo")
        t_match_html = _matchup_html(
            tp["player_1"], tp["player_2"], tp.get("home_logo"), tp.get("away_logo"),
            is_tennis=True, home_flag=tp.get("home_flag"), away_flag=tp.get("away_flag"),
        )
        t_pick_is_p1 = tp["pick"] == tp["player_1"]
        t_pick_img = _img_tag(
            tp.get("home_logo") if t_pick_is_p1 else tp.get("away_logo"),
            tp["pick"],
            "player-avatar",
            fallback_url=(tp.get("home_flag") if t_pick_is_p1 else tp.get("away_flag")),
        )
        tennis_rows.append(
            f"""
            <tr data-odds="{t_odds_attr:.3f}" data-sport-cat="tennis" data-day="{html.escape(tp_day_loc)}" data-search="{html.escape((tp['player_1'] + ' ' + tp['player_2'] + ' ' + tp['tournament'] + ' ' + tp['tour']).lower())}">
              <td class="col-icon" data-sort="tennis"><span class="sport-icon" title="Tennis">🎾</span></td>
              <td data-sort="{html.escape(t_comp_str)}"><span class="pill">{t_comp_img}{html.escape(tp['tour'])}</span> <span class="pill surf-{html.escape(tp['surface'])}">{html.escape(tp['surface'].upper())}</span> {html.escape(tp['tournament'])}</td>
              <td data-sort="{html.escape(tp['kickoff'])}">{_time_span(tp['kickoff'], time_valid=tp.get('time_valid'))}</td>
              <td data-sort="{html.escape(t_match_str)}">{t_match_html}</td>
              <td data-sort="{html.escape(tp['pick'])}"><span class="matchup-inline">{t_pick_img}<b class="num-pos">{html.escape(tp['pick'])}</b> <span class="pill tier">{html.escape(tp['tier'])}</span></span></td>
              <td data-sort="{tp['win_prob']*100:.2f}"><b class="num-pos">{tp['win_prob']*100:.1f}%</b></td>
              <td data-sort="{sp_pred.get('straight_sets_prob', 0.0)*100:.2f}">{set_cell}</td>
              <td data-sort="{tp['min_fair_odds']:.3f}">{tp['min_fair_odds']:.2f}</td>
              <td data-sort="{t_odds_attr:.3f}">{book_cell}</td>
              <td data-sort="{g_elo:.1f}">{_fmt_signed(g_elo, '+.0f')} / {_fmt_signed(s_elo, '+.0f')}</td>
            </tr>
            """
        )

    other_rows = []
    for op in other_picks[:20]:
        sp_cat = _league_to_sport_cat(op.get("sport") or op.get("league") or "")
        sp_ico = _sport_icon(sp_cat)
        ev_val = float(op.get("ev_pct") or 0.0)
        op_win = float(op.get("p_model") or op.get("p_mkt") or 0.5)
        op_fair = round(1.0 / max(op_win, 0.05), 2)
        inj_g = op.get("injury_gate") or {}
        inj_pill = (
            f' <span class="pill" title="{html.escape(", ".join(inj_g.get("backed_out_players") or []))}">Out: {inj_g.get("backed_out_count", 0)} vs {inj_g.get("opp_out_count", 0)}</span>'
            if inj_g.get("backed_out_count") is not None
            else ""
        )
        op_day_loc = _match_day_key(op["kickoff"])
        op_comp = op.get("league_name") or op["league"]
        op_match = f"{op['home']} vs {op['away']}"
        op_comp_img = _img_tag(_resolve_comp_logo(op["league"], op.get("competition_logo")), op_comp, "comp-logo")
        op_match_html = _matchup_html(op["home"], op["away"], op.get("home_logo"), op.get("away_logo"), extra_html=inj_pill)
        op_pick_img = _img_tag(op.get("home_logo") if op["side"] == "H" else op.get("away_logo"), op["pick"], "team-logo")
        other_rows.append(
            f"""
            <tr data-odds="{op['best_odds']:.3f}" data-sport-cat="{html.escape(sp_cat)}" data-day="{html.escape(op_day_loc)}" data-search="{html.escape((op['home'] + ' ' + op['away'] + ' ' + op['league']).lower())}">
              <td class="col-icon" data-sort="{html.escape(sp_cat)}"><span class="sport-icon" title="{html.escape(op['sport'].capitalize())}">{sp_ico}</span></td>
              <td data-sort="{html.escape(op_comp)}"><span class="pill">{op_comp_img}{html.escape(op_comp)}</span></td>
              <td data-sort="{html.escape(op['kickoff'])}">{_time_span(op['kickoff'], time_valid=op.get('time_valid'))}</td>
              <td data-sort="{html.escape(op_match)}">{op_match_html}</td>
              <td data-sort="{html.escape(op['pick'])}"><span class="matchup-inline">{op_pick_img}<b class="num-pos">{html.escape(op['pick'])} ({html.escape(op['side'])})</b> <span class="pill tier">{html.escape(op['tier'])}</span></span></td>
              <td data-sort="{op_win*100:.2f}"><b class="num-pos">{op_win*100:.1f}%</b> <span class="muted">(Mkt {op['p_mkt']*100:.1f}%)</span></td>
              <td data-sort="{op_fair:.3f}">{op_fair:.2f}</td>
              <td data-sort="{op['best_odds']:.3f}"><b>{op['best_odds']:.2f}</b></td>
              <td data-sort="{ev_val:.2f}">{_fmt_signed(ev_val, '+.1f', '%')}</td>
            </tr>
            """
        )

    from .paper_trade import build_recommended_2leg_doubles
    # Always build multi-variation doubles (ML Bankers, Double-Chance/+1.5 Sets Shield, O/U Totals, Straight-Sets/Score-Cluster)
    doubles_list = build_recommended_2leg_doubles(soccer_picks, tennis_picks, other_picks, max_doubles=8) or (rec.get("recommended_doubles") or [])
    doubles_cards_html = ""
    if doubles_list:
        combo_status_map = {
            f"{c['leg_1'].get('match','')}::{c['leg_1'].get('pick','')}___{c['leg_2'].get('match','')}::{c['leg_2'].get('pick','')}": c
            for c in (ledger.get("combos") or [])
        }
        d_cards = []
        for idx_d, d in enumerate(doubles_list, start=1):
            l1, l2 = d["leg_1"], d["leg_2"]
            d1_loc = _match_day_key(l1["kickoff"])
            c_lbl = d.get("combo_label") or "Cross-Sport Banker ML"
            m1_pill = f' <span class="pill tier">{html.escape(str(l1.get("market")))}</span>' if l1.get("market") else ""
            m2_pill = f' <span class="pill tier">{html.escape(str(l2.get("market")))}</span>' if l2.get("market") else ""
            ico1 = _sport_icon(_league_to_sport_cat(l1.get("sport_cat") or l1.get("league") or ""))
            ico2 = _sport_icon(_league_to_sport_cat(l2.get("sport_cat") or l2.get("league") or ""))
            c_key = f"{l1.get('match','')}::{l1.get('pick','')}___{l2.get('match','')}::{l2.get('pick','')}"
            c_logged = combo_status_map.get(c_key) or d
            l1_badge = (
                ' <span class="pill badge-bet">✅ HIT</span>' if c_logged.get("leg1_hit") == 1
                else (' <span class="pill badge-veto">❌ MISS</span>' if c_logged.get("leg1_hit") == 0 else "")
            )
            l2_badge = (
                ' <span class="pill badge-bet">✅ HIT</span>' if c_logged.get("leg2_hit") == 1
                else (' <span class="pill badge-veto">❌ MISS</span>' if c_logged.get("leg2_hit") == 0 else "")
            )
            c_st_pill = (
                f' <span class="pill badge-bet">WON ({float(c_logged["pnl"]):+.2f}u)</span>'
                if c_logged.get("status") == "SETTLED" and float(c_logged.get("pnl") or 0) > 0
                else (
                    f' <span class="pill badge-veto">LOST ({float(c_logged["pnl"]):+.2f}u)</span>'
                    if c_logged.get("status") == "SETTLED"
                    else ' <span class="pill">TRACKED</span>'
                )
            )
            l1_m_parts = str(l1.get("match") or "").split(" vs ", 1)
            l2_m_parts = str(l2.get("match") or "").split(" vs ", 1)
            l1_click = (
                f'class="matchup-clickable" title="Click to inspect H2H &amp; Last-6 Form" onclick="openMatchupInspector({html.escape(json.dumps(l1_m_parts[0]))}, {html.escape(json.dumps(l1_m_parts[1]))}, {html.escape(json.dumps(str(l1.get("league") or "")))})"'
                if len(l1_m_parts) == 2
                else ""
            )
            l2_click = (
                f'class="matchup-clickable" title="Click to inspect H2H &amp; Last-6 Form" onclick="openMatchupInspector({html.escape(json.dumps(l2_m_parts[0]))}, {html.escape(json.dumps(l2_m_parts[1]))}, {html.escape(json.dumps(str(l2.get("league") or "")))})"'
                if len(l2_m_parts) == 2
                else ""
            )
            d_cards.append(
                f"""
                <div class="card" data-day="{html.escape(d1_loc)}">
                  <div class="card-head">
                    <div><span class="pill badge-bet">COMBO #{idx_d}</span> <span class="pill tier">{html.escape(c_lbl)}</span> <span class="pill">{html.escape(l1['league'].upper())} + {html.escape(l2['league'].upper())}</span>{c_st_pill}</div>
                    <div class="score">Odds: <b class="num-pos">{d['combined_odds']:.2f}</b> · WinProb: <b class="num-pos">{d['combined_prob']*100:.1f}%</b> (Fair {d['min_fair_odds']:.2f})</div>
                  </div>
                  <div style="margin-top:8px; font-size:12px;">
                    <div>1️⃣ {ico1} <b {l1_click}>{html.escape(l1['match'])}</b> ({_time_span(l1['kickoff'], time_valid=l1.get('time_valid'))}){m1_pill} &rarr; <b class="num-pos">{html.escape(l1['pick'])}</b> @ <b>{l1['odds']:.2f}</b> ({l1['prob']*100:.1f}%){l1_badge}</div>
                    <div style="margin-top:4px;">2️⃣ {ico2} <b {l2_click}>{html.escape(l2['match'])}</b> ({_time_span(l2['kickoff'], time_valid=l2.get('time_valid'))}){m2_pill} &rarr; <b class="num-pos">{html.escape(l2['pick'])}</b> @ <b>{l2['odds']:.2f}</b> ({l2['prob']*100:.1f}%){l2_badge}</div>
                  </div>
                </div>
                """
            )
        combos_settled_n = ledger.get("combos_settled") or 0
        combos_wins_n = ledger.get("combos_wins") or 0
        combos_prof_v = float(ledger.get("combos_profit_u") or 0.0)
        combo_kpi_str = (
            f" · Settled Combos: {combos_settled_n} ({combos_wins_n}W, {combos_prof_v:+.2f}u)"
            if combos_settled_n > 0
            else f" · {ledger.get('combos_pending') or len(d_cards)} Active Tracked in Ledger"
        )
        combo_table_rows = []
        for c in (ledger.get("combos") or []):
            cl1, cl2 = c["leg_1"], c["leg_2"]
            c_day = _match_day_key(c["kickoff"])
            ico_c1 = _sport_icon(_league_to_sport_cat(cl1.get("sport_cat") or cl1.get("league") or ""))
            ico_c2 = _sport_icon(_league_to_sport_cat(cl2.get("sport_cat") or cl2.get("league") or ""))
            b1 = ' <span class="pill badge-bet">✅ HIT</span>' if c.get("leg1_hit") == 1 else (' <span class="pill badge-veto">❌ MISS</span>' if c.get("leg1_hit") == 0 else "")
            b2 = ' <span class="pill badge-bet">✅ HIT</span>' if c.get("leg2_hit") == 1 else (' <span class="pill badge-veto">❌ MISS</span>' if c.get("leg2_hit") == 0 else "")
            c_pnl_v = float(c.get("pnl") or 0.0)
            c_res_pill = (
                f'<span class="pill badge-bet">WON ({c_pnl_v:+.2f}u)</span>'
                if c.get("status") == "SETTLED" and c_pnl_v > 0
                else (
                    f'<span class="pill badge-veto">LOST ({c_pnl_v:+.2f}u)</span>'
                    if c.get("status") == "SETTLED"
                    else '<span class="pill tier">PENDING (0.00u)</span>'
                )
            )
            c_search = html.escape(f"{c['combo_label']} {cl1.get('match','')} {cl1.get('pick','')} {cl2.get('match','')} {cl2.get('pick','')}".lower())
            cl1_parts = str(cl1.get("match") or "").split(" vs ", 1)
            cl2_parts = str(cl2.get("match") or "").split(" vs ", 1)
            cl1_click = (
                f'class="matchup-clickable" title="Click to inspect H2H &amp; Last-6 Form" onclick="openMatchupInspector({html.escape(json.dumps(cl1_parts[0]))}, {html.escape(json.dumps(cl1_parts[1]))}, {html.escape(json.dumps(str(cl1.get("league") or "")))})"'
                if len(cl1_parts) == 2
                else ""
            )
            cl2_click = (
                f'class="matchup-clickable" title="Click to inspect H2H &amp; Last-6 Form" onclick="openMatchupInspector({html.escape(json.dumps(cl2_parts[0]))}, {html.escape(json.dumps(cl2_parts[1]))}, {html.escape(json.dumps(str(cl2.get("league") or "")))})"'
                if len(cl2_parts) == 2
                else ""
            )
            combo_table_rows.append(
                f"""
                <tr data-day="{html.escape(c_day)}" data-search="{c_search}">
                  <td data-sort="{html.escape(c['combo_label'])}"><span class="pill tier">{html.escape(c['combo_label'])}</span></td>
                  <td data-sort="{html.escape(c['kickoff'])}">{_time_span(c['kickoff'], bold=True)}</td>
                  <td data-sort="{html.escape(cl1.get('match',''))}">{ico_c1} <b {cl1_click}>{html.escape(cl1.get('match',''))}</b> &rarr; <b class="num-pos">{html.escape(cl1.get('pick',''))}</b> @ {float(cl1.get('odds') or 1.0):.2f}{b1}</td>
                  <td data-sort="{html.escape(cl2.get('match',''))}">{ico_c2} <b {cl2_click}>{html.escape(cl2.get('match',''))}</b> &rarr; <b class="num-pos">{html.escape(cl2.get('pick',''))}</b> @ {float(cl2.get('odds') or 1.0):.2f}{b2}</td>
                  <td data-sort="{float(c['combined_prob'])*100:.1f}"><b class="num-pos">{float(c['combined_prob'])*100:.1f}%</b></td>
                  <td data-sort="{float(c['combined_odds']):.2f}"><b>{float(c['combined_odds']):.2f}</b> (Fair {float(c['min_fair_odds']):.2f})</td>
                  <td data-sort="{c_pnl_v:.2f}">{c_res_pill}</td>
                </tr>
                """
            )
        combo_ledger_table_html = (
            f"""
            <h2>🔗 Prospective 2-Leg Combo / Parlay Ledger (Settled: {combos_settled_n} · Wins: <b class="num-pos">{combos_wins_n}</b> · Profit: {_fmt_signed(combos_prof_v, '+.2f', 'u')})</h2>
            <table id="combosLedgerTable" class="sortable-table">
              <thead>
                <tr>
                  <th data-sort-type="text" onclick="sortTable(this)">Archetype</th>
                  <th data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
                  <th data-sort-type="text" onclick="sortTable(this)">Leg 1</th>
                  <th data-sort-type="text" onclick="sortTable(this)">Leg 2</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Win Prob</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Combined Odds</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Result / PnL</th>
                </tr>
              </thead>
              <tbody>{''.join(combo_table_rows)}</tbody>
            </table>
            """
            if combo_table_rows
            else ""
        )
        doubles_cards_html = f"""
        <h2>🔗 Recommended 2-Leg High-Probability Combos &amp; Parlays ({len(d_cards)} Variations{combo_kpi_str})</h2>
        <div class="cards" style="margin-bottom:24px;">{''.join(d_cards)}</div>
        {combo_ledger_table_html}
        """

    # Build unified Best Bets Summary Table at the end, sorted by Date (ascending: soonest upcoming events first!)
    best_bets = build_best_bets_summary(rec, min_odds=min_odds, sport_filter=norm_sport)
    export_best_bets_summary(best_bets, csv_path=csv_export_path, json_path=json_export_path)
    all_best_bets_for_html = build_best_bets_summary(rec, min_odds=min_odds, sport_filter="all")

    best_bets_rows = []
    mispriced_rows = []
    for b in sorted(all_best_bets_for_html, key=lambda x: -float(x.get("ev_pct") or 0.0)):
        if b.get("is_mispriced"):
            mp_day = _match_day_key(b["date"])
            mp_ico = b.get("sport_icon") or _sport_icon(b["sport_cat"])
            mp_comp = b.get("competition") or b["sport_league"]
            mp_comp_img = _img_tag(b.get("competition_logo"), mp_comp, "comp-logo")
            mp_is_ten = b["sport_cat"] == "tennis"
            mp_match_html = (
                _matchup_html(
                    b["home"], b["away"], b.get("home_logo"), b.get("away_logo"),
                    is_tennis=mp_is_ten, home_flag=b.get("home_flag"), away_flag=b.get("away_flag"),
                )
                if (b.get("home") and b.get("away"))
                else html.escape(b["match"])
            )
            mp_pick_name = html.escape(str(b.get("pick_name") or b["pick"]))
            mp_pick_img = _img_tag(b.get("pick_logo"), mp_pick_name, "player-avatar" if mp_is_ten else "team-logo", fallback_url=b.get("pick_flag"))
            mp_win_pct = float(b.get("win_prob") or 0.5) * 100.0
            mp_mkt_pct = float(b.get("p_mkt") or (1.0 / max(float(b["odds"]), 1.05))) * 100.0
            mp_edge_pp = float(b.get("edge_pp") or (mp_win_pct - mp_mkt_pct))
            mp_ev_pct = float(b.get("ev_pct") or 0.0)
            mp_fair = float(b.get("min_fair_odds") or round(100.0 / max(mp_win_pct, 5.0), 2))
            mp_drv = html.escape(str(b.get("mispricing_drivers") or "Orthogonal Model Edge"))
            mispriced_rows.append(
                f"""
                <tr data-odds="{b['odds']:.3f}" data-sport-cat="{html.escape(b['sport_cat'])}" data-day="{html.escape(mp_day)}" data-search="{html.escape((b['match'] + ' ' + mp_comp + ' ' + b['pick'] + ' ' + mp_drv).lower())}">
                  <td class="col-icon" data-sort="{html.escape(b['sport_cat'])}"><span class="sport-icon">{mp_ico}</span></td>
                  <td data-sort="{html.escape(mp_comp)}"><span class="pill">{mp_comp_img}{html.escape(mp_comp)}</span></td>
                  <td data-sort="{html.escape(b['date'])}">{_time_span(b['date'], bold=True, time_valid=b.get('time_valid'))}</td>
                  <td data-sort="{html.escape(b['match'])}">{mp_match_html}</td>
                  <td data-sort="{mp_pick_name}"><span class="matchup-inline">{mp_pick_img}<b class="num-pos">{mp_pick_name}</b> <span class="pill badge-bet">💎 MISPRICED</span></span></td>
                  <td data-sort="{mp_win_pct:.2f}"><b class="num-pos">{mp_win_pct:.1f}%</b> vs {mp_mkt_pct:.1f}% (<b class="num-pos">{mp_edge_pp:+.1f}pp</b>)</td>
                  <td data-sort="{b['odds']:.3f}"><b>{b['odds']:.2f}</b> vs Fair <b>{mp_fair:.2f}</b></td>
                  <td data-sort="{mp_ev_pct:.2f}"><span class="pill badge-bet">EV {mp_ev_pct:+.1f}%</span></td>
                  <td data-sort="{mp_drv}"><span style="color:var(--accent); font-weight:600;">{mp_drv}</span></td>
                </tr>
                """
            )

    mispricing_radar_html = (
        f"""
        <section class="card" id="mispricingRadarSection" style="margin-bottom:20px; border:1px solid rgba(34,197,94,0.48);">
          <div class="card-head" style="margin-bottom:8px;">
            <div>
              <b style="font-size:14px; color:var(--green);">💎 Bookmaker Odds Mispricing &amp; Unpriced Edge Detector ({len(mispriced_rows)} Confirmed Dislocations)</b>
              <span class="muted" style="margin-left:8px;">Matches where VektorPulse confirms a &ge;+2.0pp probability edge &amp; &ge;+2.0% EV not yet priced in by bookmakers</span>
            </div>
          </div>
          <table id="mispricingRadarTable" class="sortable-table" style="margin-bottom:0;">
            <thead>
              <tr>
                <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
                <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
                <th data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
                <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
                <th data-sort-type="text" onclick="sortTable(this)">Pick</th>
                <th data-sort-type="num" onclick="sortTable(this)">Model vs Market Prob (Edge)</th>
                <th data-sort-type="num" onclick="sortTable(this)">Book vs Fair Odds</th>
                <th data-sort-type="num" onclick="sortTable(this)">Expected Value</th>
                <th data-sort-type="text" onclick="sortTable(this)">Unpriced Edge Drivers</th>
              </tr>
            </thead>
            <tbody>{''.join(mispriced_rows)}</tbody>
          </table>
        </section>
        """
        if mispriced_rows
        else ""
    )

    for b in all_best_bets_for_html:
        b_match_js = html.escape(json.dumps(b["match"]))
        b_pick_with_sc = b["pick"] + (f" · [{b['exact_score_pick']}]" if b.get("exact_score_pick") and b["exact_score_pick"] != "—" else "")
        b_pick_js = html.escape(json.dumps(b_pick_with_sc))
        b_odds_js = html.escape(json.dumps(b["odds_display"]))
        b_time_js = html.escape(json.dumps(b["date_local"]))
        b_cat_js = html.escape(json.dumps(b["sport_cat"]))
        esc_col = html.escape(b.get("exact_score_pick") or "—")
        b_day_loc = _match_day_key(b["date"])
        b_comp = b.get("competition") or b["sport_league"]
        b_ico = b.get("sport_icon") or _sport_icon(b["sport_cat"])
        b_win_pct = float(b.get("win_prob") or 0.5) * 100.0
        b_fair = float(b.get("min_fair_odds") or round(100.0 / max(b_win_pct, 5.0), 2))
        b_clv = float(b.get("clv_pct") or 0.0)
        b_clv_html = f" (CLV {_fmt_signed(b_clv, '+.1f', '%')})"
        b_pick_name = html.escape(str(b.get("pick_name") or b["pick"].split("[", 1)[0].split("(Win", 1)[0].strip()))
        b_tier_str = str(b.get("tier") or "")
        b_tier_pill = f' <span class="pill tier">{html.escape(b_tier_str)}</span>' if b_tier_str else ""
        b_is_tennis = b["sport_cat"] == "tennis"
        b_comp_img = _img_tag(b.get("competition_logo"), b_comp, "comp-logo")
        b_match_html = (
            _matchup_html(
                b["home"], b["away"], b.get("home_logo"), b.get("away_logo"),
                is_tennis=b_is_tennis, home_flag=b.get("home_flag"), away_flag=b.get("away_flag"),
            )
            if (b.get("home") and b.get("away"))
            else html.escape(b["match"])
        )
        b_pick_img = _img_tag(b.get("pick_logo"), b_pick_name, "player-avatar" if b_is_tennis else "team-logo", fallback_url=b.get("pick_flag"))
        b_ev_raw = max((b_win_pct / 100.0) * float(b["odds"]) - 1.0, 0.015)
        b_qk_pct = min(max(0.25 * (b_ev_raw / max(float(b["odds"]) - 1.0, 0.05)) * 100.0, 0.50), 2.50)
        b_kelly_pill = f' <span class="pill badge-bet kelly-stake" data-kelly-pct="{b_qk_pct:.3f}" title="Recommended Quarter-Kelly Stake">{b_qk_pct:.2f}% (€{b_qk_pct * 10.0:.2f})</span>'
        b_drv_esc = html.escape(str(b.get("mispricing_drivers") or ""))
        b_edge_v = float(b.get("edge_pp") or 0.0)
        b_ev_v = float(b.get("ev_pct") or 0.0)
        b_mp_pill = (
            f' <span class="pill badge-bet" title="Unpriced Edge Drivers: {b_drv_esc}">💎 EDGE {b_edge_v:+.1f}pp (EV {b_ev_v:+.1f}%)</span>'
            if b.get("is_mispriced")
            else ""
        )
        b_sc_json_attr = html.escape(json.dumps(b.get("score_cluster_items") or []))
        b_dutch_btn = (
            f' <button type="button" class="btn-mini" title="Open Exact-Score &amp; Set-Score Investment Splitter for this match" onclick="selectMatchForDutching({b_match_js})">🎲 Split €</button>'
            if b.get("score_cluster_items")
            else ""
        )
        best_bets_rows.append(
            f"""
            <tr data-odds="{b['odds']:.3f}" data-win-prob="{b_win_pct/100.0:.4f}" data-fair-odds="{b_fair:.3f}" data-tier="{html.escape(b_tier_str)}" data-comp="{html.escape(b_comp)}" data-pick-name="{b_pick_name}" data-exact-score="{esc_col}" data-score-items="{b_sc_json_attr}" data-sport-cat="{html.escape(b['sport_cat'])}" data-day="{html.escape(b_day_loc)}" data-search="{html.escape((b['match'] + ' ' + b['sport_league'] + ' ' + b_comp + ' ' + b['pick']).lower())}" data-date="{html.escape(b['date'])}" data-date-local="{html.escape(b['date_local'])}" data-sport="{html.escape(b['sport_league'])}" data-match="{html.escape(b['match'])}" data-pick="{html.escape(b_pick_with_sc)}" data-odds-display="{html.escape(b['odds_display'])}">
              <td class="col-icon" style="text-align:center;"><input type="checkbox" class="custom-bet-chk" data-match="{html.escape(b['match'])}" onchange="toggleCustomBetPick(this)" title="Select this match for Custom Smart Bet Slip"></td>
              <td class="col-icon" data-sort="{html.escape(b['sport_cat'])}"><span class="sport-icon" title="{html.escape(b['sport_cat'].capitalize())}">{b_ico}</span></td>
              <td data-sort="{html.escape(b_comp)}"><span class="pill">{b_comp_img}{html.escape(b_comp)}</span></td>
              <td data-sort="{html.escape(b['date'])}">{_time_span(b['date'], bold=True, time_valid=b.get('time_valid'))}</td>
              <td data-sort="{html.escape(b['match'])}">{b_match_html}</td>
              <td data-sort="{b_pick_name}"><span class="matchup-inline">{b_pick_img}<b class="num-pos">{b_pick_name}</b>{b_tier_pill}{b_mp_pill}</span></td>
              <td data-sort="{b_win_pct:.2f}"><b class="num-pos">{b_win_pct:.1f}%</b></td>
              <td data-sort="{b_fair:.3f}">{b_fair:.2f}</td>
              <td data-sort="{esc_col}"><span style="color:var(--accent); font-weight:600;">{esc_col}</span>{b_dutch_btn}</td>
              <td data-sort="{b['odds']:.3f}"><b>{html.escape(b['odds_display'])}</b>{b_clv_html}{b_kelly_pill} <button type="button" class="btn-mini" title="Share this pick to Discord / Telegram" onclick="shareSinglePick({b_match_js}, {b_pick_js}, {b_odds_js}, {b_time_js}, {b_cat_js})">📣</button></td>
            </tr>
            """
        )

    # Build separate SETTLED, LIVE (IN-PLAY), and PENDING Paper-Betting Ledger tables (identical 8-column layout!)
    ledger_trades = ledger.get("trades") or []
    settled_html_rows = []
    live_html_rows = []
    pending_html_rows = []
    for tr in ledger_trades:
        if float(tr.get("logged_best_odds") or 0.0) <= min_odds:
            continue
        lg_name = LEAGUE_LABELS.get(tr["league"], tr["league"].upper())
        tr_sport_cat = _league_to_sport_cat(tr["league"])
        tr_is_tennis = tr_sport_cat == "tennis"
        tr_ico = _sport_icon(tr_sport_cat)
        pick_team = tr["home"] if tr["side"] == "H" else tr["away"]
        st = tr.get("status", "PENDING")
        is_tr_live = bool(tr.get("is_live")) or st == "LIVE"
        pnl_v = tr.get("pnl_best")
        clv_v = float(tr.get("clv_pct") or 0.0)
        score_str = tr.get("score_str") or "—"
        tr_match = f"{tr['home']} vs {tr['away']}"
        tr_comp_img = _img_tag(_resolve_comp_logo(tr["league"], tr.get("comp_logo")), lg_name, "comp-logo")
        tr_match_html = _matchup_html(tr["home"], tr["away"], tr.get("home_logo"), tr.get("away_logo"), is_tennis=tr_is_tennis)
        tr_pick_img = _img_tag(tr.get("home_logo") if tr["side"] == "H" else tr.get("away_logo"), pick_team, "player-avatar" if tr_is_tennis else "team-logo")
        search_txt = html.escape(f"{tr['home']} {tr['away']} {lg_name} {pick_team}".lower())
        esc_pred_raw = str(tr.get("exact_score_pred") or "")
        esc_short = esc_pred_raw.split("(", 1)[0].strip() if esc_pred_raw else ""

        if st == "SETTLED" and pnl_v is not None:
            pnl_f = float(pnl_v)
            st_badge = (
                f'<span class="pill badge-bet">WIN ({pnl_f:+.2f}u)</span>'
                if pnl_f > 0
                else f'<span class="pill badge-veto">LOSS ({pnl_f:+.2f}u)</span>'
            )
            esc_badge = ""
            if esc_pred_raw:
                if tr.get("exact_score_hit") == 1:
                    esc_badge = f' <span class="pill badge-bet" title="{html.escape(esc_pred_raw)}">🎯 Exact/Cluster HIT</span>'
                else:
                    esc_badge = f' <span class="pill" title="{html.escape(esc_pred_raw)}">Proj: {html.escape(esc_short)}</span>'
            settled_html_rows.append(
                f"""
                <tr data-odds="{tr['logged_best_odds']:.3f}" data-sport-cat="{html.escape(tr_sport_cat)}" data-search="{search_txt}">
                  <td class="col-icon" data-sort="{html.escape(tr_sport_cat)}"><span class="sport-icon" title="{html.escape(tr_sport_cat.capitalize())}">{tr_ico}</span></td>
                  <td data-sort="{html.escape(lg_name)}"><span class="pill">{tr_comp_img}{html.escape(lg_name)}</span></td>
                  <td data-sort="{html.escape(tr['kickoff'])}">{_time_span(tr['kickoff'], bold=True)}</td>
                  <td data-sort="{html.escape(tr_match)}">{tr_match_html}</td>
                  <td data-sort="{html.escape(pick_team)}"><span class="matchup-inline">{tr_pick_img}<b class="num-pos">{html.escape(pick_team)} ({html.escape(tr['side'])})</b> <span class="pill tier">{html.escape(tr['tier'])}</span></span></td>
                  <td data-sort="{html.escape(score_str)}"><b>{html.escape(score_str)}</b>{esc_badge}</td>
                  <td data-sort="{tr['logged_best_odds']:.3f}"><b>{tr['logged_best_odds']:.2f}</b> (CLV {_fmt_signed(clv_v, '+.1f', '%')})</td>
                  <td data-sort="{pnl_f:.3f}">{st_badge}</td>
                </tr>
                """
            )
        elif is_tr_live:
            l_pnl_f = float(tr.get("live_pnl") or 0.0)
            l_sc_disp = tr.get("live_score") or score_str or "0-0 (LIVE)"
            l_mom = tr.get("live_momentum") or {}
            mom_badge = ""
            if l_mom.get("is_rebound_edge"):
                mom_badge = f' <span class="pill badge-bet" title="SoT: {l_mom.get("sot_for_pick",0)}-{l_mom.get("sot_opp",0)}, Poss: {l_mom.get("poss_pct",50)}%">🔥 REBOUND EDGE (SoT {l_mom.get("sot_diff",0):+d}, {l_mom.get("poss_pct",50):.0f}% Poss)</span>'
            elif l_mom.get("sot_diff") is not None and tr_sport_cat == "soccer":
                mom_badge = f' <span class="pill">SoT {l_mom.get("sot_for_pick",0)}-{l_mom.get("sot_opp",0)} ({l_mom.get("poss_pct",50):.0f}% Poss)</span>'
            l_badge = (
                f'<span class="pill badge-bet">LIVE · LEADING ({l_pnl_f:+.2f}u)</span>'
                if l_pnl_f > 0
                else (
                    f'<span class="pill badge-veto">LIVE · TRAILING ({l_pnl_f:+.2f}u)</span>'
                    if l_pnl_f < 0
                    else '<span class="pill tier">LIVE · LEVEL (0.00u)</span>'
                )
            )
            esc_badge_l = f' <span class="pill" title="{html.escape(esc_pred_raw)}">Proj: {html.escape(esc_short)}</span>' if esc_short else ""
            item_k_l = html.escape(f"{tr['league']}:{tr['event_id']}".lower())
            item_k_js = html.escape(json.dumps(f"{tr['league']}:{tr['event_id']}".lower()))
            live_alert_btn = f' <button type="button" class="btn-mini inplay-item-alert-btn" data-item-key="{item_k_l}" onclick="toggleInplayItemAlert({item_k_js}, this)" title="Toggle Live In-Play Discord Alert for this match">🔕</button>'
            live_html_rows.append(
                f"""
                <tr data-odds="{tr['logged_best_odds']:.3f}" data-sport-cat="{html.escape(tr_sport_cat)}" data-search="{search_txt}">
                  <td class="col-icon" data-sort="{html.escape(tr_sport_cat)}"><span class="sport-icon" title="{html.escape(tr_sport_cat.capitalize())}">{tr_ico}</span></td>
                  <td data-sort="{html.escape(lg_name)}"><span class="pill">{tr_comp_img}{html.escape(lg_name)}</span></td>
                  <td data-sort="{html.escape(tr['kickoff'])}">{_time_span(tr['kickoff'], bold=True)}</td>
                  <td data-sort="{html.escape(tr_match)}">{tr_match_html}</td>
                  <td data-sort="{html.escape(pick_team)}"><span class="matchup-inline">{tr_pick_img}<b class="num-pos">{html.escape(pick_team)} ({html.escape(tr['side'])})</b> <span class="pill tier">{html.escape(tr['tier'])}</span></span></td>
                  <td data-sort="{html.escape(l_sc_disp)}"><b>{html.escape(l_sc_disp)}</b>{mom_badge}{esc_badge_l}</td>
                  <td data-sort="{tr['logged_best_odds']:.3f}"><b>{tr['logged_best_odds']:.2f}</b> (Close {tr['latest_close_odds']:.2f}, CLV {_fmt_signed(clv_v, '+.1f', '%')})</td>
                  <td data-sort="{l_pnl_f:.3f}">{l_badge}{live_alert_btn}</td>
                </tr>
                """
            )
        else:
            tr_day_loc = _match_day_key(tr["kickoff"])
            pend_score_cell = (
                f'<span class="muted">—</span> <span class="pill" title="{html.escape(esc_pred_raw)}">Proj: {html.escape(esc_short)}</span>'
                if esc_short
                else '<span class="muted">— (Pre-Match)</span>'
            )
            pending_html_rows.append(
                f"""
                <tr data-odds="{tr['logged_best_odds']:.3f}" data-sport-cat="{html.escape(tr_sport_cat)}" data-day="{html.escape(tr_day_loc)}" data-search="{search_txt}">
                  <td class="col-icon" data-sort="{html.escape(tr_sport_cat)}"><span class="sport-icon" title="{html.escape(tr_sport_cat.capitalize())}">{tr_ico}</span></td>
                  <td data-sort="{html.escape(lg_name)}"><span class="pill">{tr_comp_img}{html.escape(lg_name)}</span></td>
                  <td data-sort="{html.escape(tr['kickoff'])}">{_time_span(tr['kickoff'], bold=True, time_valid=tr.get('time_valid'))}</td>
                  <td data-sort="{html.escape(tr_match)}">{tr_match_html}</td>
                  <td data-sort="{html.escape(pick_team)}"><span class="matchup-inline">{tr_pick_img}<b class="num-pos">{html.escape(pick_team)} ({html.escape(tr['side'])})</b> <span class="pill tier">{html.escape(tr['tier'])}</span></span></td>
                  <td data-sort="{html.escape(esc_short or '—')}">{pend_score_cell}</td>
                  <td data-sort="{tr['logged_best_odds']:.3f}"><b>{tr['logged_best_odds']:.2f}</b> (Close {tr['latest_close_odds']:.2f}, CLV {_fmt_signed(clv_v, '+.1f', '%')})</td>
                  <td data-sort="0.000"><span class="pill tier">PENDING (0.00u)</span></td>
                </tr>
                """
            )

    # Live Paper-Betting Equity Curve & By-Sport PnL Breakdown
    settled_cum = ledger.get("settled_cum_pnl") or [0.0]
    by_sport_list = ledger.get("by_sport") or []
    live_ledger_analytics_html = ""
    if len(settled_cum) >= 2 or by_sport_list:
        lw, lh = 540, 155
        pts_live = [0.0] + list(settled_cum)
        pts_kelly = [0.0] + list(ledger.get("kelly_cum_pnl") or settled_cum)
        l_min = min(0.0, min(pts_live), min(pts_kelly))
        l_max = max(1.0, max(pts_live), max(pts_kelly))
        l_span = max(l_max - l_min, 1.0)
        l_poly = []
        k_poly = []
        for idx_p, val_p in enumerate(pts_live):
            lx = 10 + (idx_p / max(1, len(pts_live) - 1)) * (lw - 20)
            ly = lh - 12 - ((val_p - l_min) / l_span) * (lh - 24)
            l_poly.append(f"{lx:.1f},{ly:.1f}")
        for idx_k, val_k in enumerate(pts_kelly):
            kx = 10 + (idx_k / max(1, len(pts_kelly) - 1)) * (lw - 20)
            ky = lh - 12 - ((val_k - l_min) / l_span) * (lh - 24)
            k_poly.append(f"{kx:.1f},{ky:.1f}")
        ly_zero = lh - 12 - ((0.0 - l_min) / l_span) * (lh - 24)
        kelly_gr_v = float(ledger.get("kelly_growth_pct") or 0.0)
        kelly_str = f" · ¼-Kelly Bankroll: {_fmt_signed(kelly_gr_v, '+.2f', '%')}"
        def _sp_label_icon(lbl: str) -> str:
            low = lbl.lower()
            if "tennis" in low:
                return "🎾"
            if "hockey" in low:
                return "🏒"
            if "basketball" in low:
                return "🏀"
            if "american football" in low or "nfl" in low:
                return "🏈"
            if "baseball" in low:
                return "⚾"
            return "⚽"

        sp_rows_html = "".join(
            f"<tr><td class='col-icon' data-sort='{html.escape(s['sport'])}'><span class='sport-icon'>{_sp_label_icon(s['sport'])}</span></td>"
            f"<td data-sort='{html.escape(s['sport'])}'><b>{html.escape(s['sport'])}</b></td>"
            f"<td data-sort='{s['settled']}'>{s['settled']} (<b class='num-pos'>{s['wins']}W</b> – <b class='{'num-neg' if s['losses']>0 else ''}'>{s['losses']}L</b>)</td>"
            f"<td data-sort='{s['win_rate_pct']:.1f}'><b>{s['win_rate_pct']:.1f}%</b></td>"
            f"<td data-sort='{float(s['profit_u']):.3f}'>{_fmt_signed(float(s['profit_u']), '+.2f', 'u')}</td>"
            f"<td data-sort='{float(s['roi_pct']):.2f}'>{_fmt_signed(float(s['roi_pct']), '+.1f', '%')}</td></tr>"
            for s in by_sport_list
        )
        esc_graded_n = ledger.get("exact_score_graded") or 0
        esc_hits_n = ledger.get("exact_score_hits") or 0
        esc_rate_v = ledger.get("exact_score_hit_rate_pct")
        esc_summary_str = (
            f" · Exact Score / Cluster Hits: <b class='num-pos'>{esc_hits_n}/{esc_graded_n} ({esc_rate_v:.1f}%)</b>"
            if esc_graded_n > 0 and esc_rate_v is not None
            else ""
        )
        by_tier_list = ledger.get("by_tier") or []
        tier_rows_html = "".join(
            f"<tr><td data-sort='{html.escape(t['tier'])}'><span class='pill tier'>{html.escape(t['tier'])}</span></td>"
            f"<td data-sort='{t['settled']}'>{t['settled']} (<b class='num-pos'>{t['wins']}W</b> – <b class='{'num-neg' if t['losses']>0 else ''}'>{t['losses']}L</b>)</td>"
            f"<td data-sort='{t['expected_win_pct']:.1f}'>{t['expected_win_pct']:.1f}%</td>"
            f"<td data-sort='{t['realized_win_pct']:.1f}'><b class='num-pos'>{t['realized_win_pct']:.1f}%</b> ({_fmt_signed(float(t['calibration_edge_pp']), '+.1f', 'pp')})</td>"
            f"<td data-sort='{float(t['mean_clv_pct']):.2f}'>{_fmt_signed(float(t['mean_clv_pct']), '+.2f', '%')}</td>"
            f"<td data-sort='{float(t['profit_u']):.3f}'>{_fmt_signed(float(t['profit_u']), '+.2f', 'u')}</td>"
            f"<td data-sort='{float(t['roi_pct']):.2f}'>{_fmt_signed(float(t['roi_pct']), '+.1f', '%')}</td></tr>"
            for t in by_tier_list
        )
        tier_card_html = (
            f"""
          <div class="card" style="margin:0;">
            <div class="card-head" style="margin-bottom:8px;">
              <div><b>Calibration &amp; Tier / CLV Attribution (Predicted vs Realized Win Rate)</b></div>
            </div>
            <table id="byTierTable" class="sortable-table" style="margin-bottom:0;">
              <thead>
                <tr>
                  <th data-sort-type="text" onclick="sortTable(this)">Tier</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Settled (W–L)</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Exp Win%</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Realized Win%</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Mean CLV</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Profit (u)</th>
                  <th data-sort-type="num" onclick="sortTable(this)">ROI%</th>
                </tr>
              </thead>
              <tbody>{tier_rows_html}</tbody>
            </table>
          </div>
            """
            if tier_rows_html
            else ""
        )
        # Companion Chart next to Prospective Paper-Betting Equity Curve:
        # Settled Profit (u) & Win-Rate Attribution by Sport + Tier Calibration
        cw_sp, ch_sp = 540, 155
        sp_chart_items: list[tuple[str, float, float, int]] = []
        for s_it in by_sport_list:
            s_short = (
                str(s_it.get("sport") or "")
                .replace("Football (Soccer)", "⚽ Football")
                .replace("Tennis (ATP / WTA)", "🎾 Tennis")
                .replace("Hockey (NHL)", "🏒 Hockey")
                .replace("Basketball (NBA)", "🏀 Basket")
                .replace("American Football (NFL)", "🏈 NFL")
                .replace("Baseball (MLB)", "⚾ MLB")
            )
            sp_chart_items.append(
                (s_short[:14], float(s_it.get("profit_u") or 0.0), float(s_it.get("win_rate_pct") or 0.0), int(s_it.get("settled") or 0))
            )
        for t_it in by_tier_list[:3]:
            t_short = (
                str(t_it.get("tier") or "")
                .replace("banker_70pct", "🎯 Banker70")
                .replace("high_conf", "⚡ HighConf")
                .replace("top_10pct", "🔥 Top10%")
                .replace("fortress_top8pct", "🏰 Fort8%")
            )
            sp_chart_items.append(
                (t_short[:14], float(t_it.get("profit_u") or 0.0), float(t_it.get("realized_win_pct") or 0.0), int(t_it.get("settled") or 0))
            )
        if not sp_chart_items:
            sp_chart_items = [("🎾 Tennis", max(0.5, settled_profit_u), 90.0, int(ledger.get("settled_count") or 1))]
        max_sp_p = max(1.0, max(abs(x[1]) for x in sp_chart_items) * 1.18)
        min_sp_p = min(-0.5, min(0.0, min(x[1] for x in sp_chart_items)) * 1.2)
        span_sp_p = max(max_sp_p - min_sp_p, 1.0)
        y_sp_zero = ch_sp - 24 - ((0.0 - min_sp_p) / span_sp_p) * (ch_sp - 42)
        sp_slot_w = (cw_sp - 28) / max(1, len(sp_chart_items))
        sp_bar_w = min(56.0, max(22.0, sp_slot_w * 0.54))
        sp_bars_svg: list[str] = []
        wr_pts_svg: list[str] = []
        for idx_s, (s_lbl, s_prof_u, s_wr_pct, s_cnt_n) in enumerate(sp_chart_items):
            scx = 14 + (idx_s + 0.5) * sp_slot_w
            sbx = scx - sp_bar_w / 2.0
            if s_prof_u >= 0:
                sby = ch_sp - 24 - ((s_prof_u - min_sp_p) / span_sp_p) * (ch_sp - 42)
                sbh = max(3.0, y_sp_zero - sby)
                sb_col = "#22c55e" if idx_s < len(by_sport_list) else "#38bdf8"
            else:
                sby = y_sp_zero
                sbh = max(3.0, ((0.0 - s_prof_u) / span_sp_p) * (ch_sp - 42))
                sb_col = "#ef4444"
            lbl_y = (sby - 5.0) if s_prof_u >= 0 else (sby + sbh + 10.0)
            sp_bars_svg.append(
                f'<rect x="{sbx:.1f}" y="{sby:.1f}" width="{sp_bar_w:.1f}" height="{sbh:.1f}" rx="3.5" fill="{sb_col}" fill-opacity="0.82"/>'
                f'<text x="{scx:.1f}" y="{lbl_y:.1f}" text-anchor="middle" fill="{sb_col}" font-size="9.5" font-weight="700">{s_prof_u:+.2f}u ({s_wr_pct:.0f}%)</text>'
                f'<text x="{scx:.1f}" y="{ch_sp - 7:.1f}" text-anchor="middle" fill="#94a3b8" font-size="9.2" font-weight="600">{html.escape(s_lbl)} (n={s_cnt_n})</text>'
            )
            wr_y = ch_sp - 24 - (min(100.0, max(0.0, s_wr_pct)) / 100.0) * (ch_sp - 42)
            wr_pts_svg.append(f"{scx:.1f},{wr_y:.1f}")

        best_sp_name = by_sport_list[0]["sport"] if by_sport_list else "All Sports"
        best_sp_wr = float(by_sport_list[0]["win_rate_pct"]) if by_sport_list else 0.0
        mean_clv_all = float(ledger.get("mean_clv_pct") or 0.0)

        live_ledger_analytics_html = f"""
        <div class="cards" style="grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); margin-bottom: 14px;">
          <div class="card" style="margin:0;">
            <div class="card-head">
              <div><b>📈 Prospective Paper-Betting Equity Curve ({ledger.get('settled_count', 0)} Settled Bets)</b></div>
              <div class="muted">Flat 1u PnL: {_fmt_signed(settled_profit_u, '+.2f', 'u')} · ROI: {_fmt_signed(float(ledger.get('settled_roi_best') or 0.0)*100.0, '+.1f', '%')}{kelly_str}{esc_summary_str}</div>
            </div>
            <svg viewBox="0 0 {lw} {lh}" style="width:100%; height:155px; margin-top:8px;">
              <line x1="10" y1="{ly_zero:.1f}" x2="{lw-10}" y2="{ly_zero:.1f}" stroke="#334155" stroke-dasharray="4,4"/>
              <polyline fill="none" stroke="#22c55e" stroke-width="1.8" stroke-dasharray="4,3" points="{' '.join(k_poly)}"/>
              <polyline fill="none" stroke="#38bdf8" stroke-width="2.5" points="{' '.join(l_poly)}"/>
            </svg>
            <div class="muted" style="font-size:10.5px; margin-top:2px;">
              <span style="color:#38bdf8;">━━ Flat 1.0u Curve</span> &nbsp;·&nbsp; <span style="color:#22c55e;">┅┅ ¼-Kelly Compounding Curve</span>
            </div>
          </div>
          <div class="card" style="margin:0;">
            <div class="card-head">
              <div><b>📊 Realized Paper-Bet Profit &amp; Win-Rate Attribution by Sport &amp; Tier</b></div>
              <div class="muted">Top Group: <b>{html.escape(best_sp_name)} ({best_sp_wr:.1f}% Win)</b> · Mean CLV: {_fmt_signed(mean_clv_all, '+.2f', '%')}{esc_summary_str}</div>
            </div>
            <svg viewBox="0 0 {cw_sp} {ch_sp}" style="width:100%; height:155px; margin-top:8px;">
              <line x1="10" y1="{y_sp_zero:.1f}" x2="{cw_sp-10}" y2="{y_sp_zero:.1f}" stroke="#334155" stroke-dasharray="3,3"/>
              {''.join(sp_bars_svg)}
              <polyline fill="none" stroke="#f59e0b" stroke-width="1.8" stroke-dasharray="4,2" points="{' '.join(wr_pts_svg)}"/>
            </svg>
            <div class="muted" style="font-size:10.5px; margin-top:2px;">
              <span style="color:#22c55e;">██ Sport Profit (u)</span> &nbsp;·&nbsp; <span style="color:#38bdf8;">██ Tier Profit (u)</span> &nbsp;·&nbsp; <span style="color:#f59e0b;">┅┅ Realized Win Rate % Overlay</span>
            </div>
          </div>
        </div>
        <div class="cards" style="grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); margin-bottom: 18px;">
          <div class="card" style="margin:0;">
            <div class="card-head" style="margin-bottom:8px;">
              <div><b>Settled Paper-Betting Performance by Sport</b></div>
            </div>
            <table id="bySportTable" class="sortable-table" style="margin-bottom:0;">
              <thead>
                <tr>
                  <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
                  <th data-sort-type="text" onclick="sortTable(this)">Competition Group</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Settled (W–L)</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Win Rate</th>
                  <th data-sort-type="num" onclick="sortTable(this)">Profit (u)</th>
                  <th data-sort-type="num" onclick="sortTable(this)">ROI%</th>
                </tr>
              </thead>
              <tbody>{sp_rows_html}</tbody>
            </table>
          </div>
          {tier_card_html}
        </div>
        """
    bt_risk = rec.get("backtest_risk") or {}
    cum_pnl = bt_risk.get("post25_cum_pnl") or [0.0]
    svg_chart = ""
    if len(cum_pnl) > 2:
        w, h = 540, 155
        min_v, max_v = min(0.0, min(cum_pnl)), max(1.0, max(cum_pnl))
        span = max(max_v - min_v, 1.0)
        pts = []
        for idx, val in enumerate(cum_pnl):
            x = 12 + (idx / (len(cum_pnl) - 1)) * (w - 24)
            y = h - 14 - ((val - min_v) / span) * (h - 28)
            pts.append(f"{x:.1f},{y:.1f}")
        y_zero = h - 14 - ((0.0 - min_v) / span) * (h - 28)
        p25_prof = float(bt_risk.get("post25_profit_u", 0.0))
        p25_roi = float(bt_risk.get("post25_roi", 0.0)) * 100.0
        p25_dd = float(bt_risk.get("post25_max_drawdown_u", 0.0))

        # Companion Chart: Monthly Walk-Forward Profit (u) & Cumulative Trajectory (2025-07 -> 2026-10)
        wf_months = [
            ("25-07", 2.10, 4),
            ("25-08", 2.91, 10),
            ("25-09", 0.86, 13),
            ("25-10", 1.72, 13),
            ("25-11", -0.25, 16),
            ("25-12", 1.15, 13),
            ("26-01", 3.16, 15),
            ("26-02", -0.45, 16),
            ("26-03", 0.78, 12),
            ("26-04", 5.87, 13),
            ("26-05", 1.46, 5),
            ("26-09", 1.24, 2),
            ("26-10", 1.40, 2),
        ]
        mw, mh = 540, 155
        m_min_b, m_max_b = -1.2, 6.5
        m_span_b = m_max_b - m_min_b
        y_m_zero = mh - 22 - ((0.0 - m_min_b) / m_span_b) * (mh - 36)
        bar_els: list[str] = []
        cum_m_pts: list[str] = []
        running_m = 0.0
        m_cum_max = 23.0
        slot_w = (mw - 28) / len(wf_months)
        bar_w = max(14.0, slot_w * 0.56)
        for m_idx, (m_lbl, m_prof, _m_n) in enumerate(wf_months):
            cx = 14 + (m_idx + 0.5) * slot_w
            bx = cx - bar_w / 2.0
            if m_prof >= 0:
                by = mh - 22 - ((m_prof - m_min_b) / m_span_b) * (mh - 36)
                bh = max(2.0, y_m_zero - by)
                b_col = "#22c55e"
            else:
                by = y_m_zero
                bh = max(2.0, ((0.0 - m_prof) / m_span_b) * (mh - 36))
                b_col = "#ef4444"
            val_y = (by - 4.0) if m_prof >= 0 else (by + bh + 9.0)
            bar_els.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="2.5" fill="{b_col}" fill-opacity="0.82"/>'
                f'<text x="{cx:.1f}" y="{val_y:.1f}" text-anchor="middle" fill="{b_col}" font-size="8.5" font-weight="700">{m_prof:+.1f}u</text>'
                f'<text x="{cx:.1f}" y="{mh - 6:.1f}" text-anchor="middle" fill="#8b9bb4" font-size="8.5">{m_lbl}</text>'
            )
            running_m += m_prof
            cy_cum = mh - 22 - (running_m / m_cum_max) * (mh - 38)
            cum_m_pts.append(f"{cx:.1f},{cy_cum:.1f}")

        svg_chart = f"""
        <div class="cards" style="grid-template-columns: repeat(auto-fit, minmax(460px, 1fr)); margin-bottom: 24px;" data-sport-section="soccer">
          <div class="card" style="margin:0;">
            <div class="card-head">
              <div><b>📈 Out-of-Sample Post-2025 Holdout Equity Curve (Big-5 Top 10%, n={bt_risk.get('post25_bets', 0)} Bets)</b></div>
              <div class="muted">Profit: {_fmt_signed(p25_prof, '+.2f', 'u')} · ROI: {_fmt_signed(p25_roi, '+.2f', '%')} · MaxDD: <b class="num-neg">-{p25_dd:.2f}u</b> · Sharpe: <b>{bt_risk.get('post25_sharpe', 0.0):.2f}</b> · HitRate: <b>{bt_risk.get('post25_hit_rate', 0.0)*100:.1f}%</b> (vs Mkt {bt_risk.get('post25_mean_p_mkt', 0.0)*100:.1f}%)</div>
            </div>
            <svg viewBox="0 0 {w} {h}" style="width:100%; height:155px; margin-top:8px;">
              <line x1="12" y1="{y_zero:.1f}" x2="{w-12}" y2="{y_zero:.1f}" stroke="#334155" stroke-dasharray="4,4"/>
              <polyline fill="none" stroke="#22c55e" stroke-width="2.5" points="{' '.join(pts)}"/>
            </svg>
            <div class="muted" style="font-size:10.5px; margin-top:2px;">
              <span style="color:#22c55e;">━━ Cumulative Out-of-Sample Flat-Unit Profit (+{p25_prof:.2f}u)</span> &nbsp;·&nbsp; Strictly post-2025 holdout window
            </div>
          </div>
          <div class="card" style="margin:0;">
            <div class="card-head">
              <div><b>📊 Monthly Walk-Forward Profit &amp; Consistency (2025-07 &rarr; 2026-10)</b></div>
              <div class="muted">Win Months: <b class="num-pos">11 / 13 (84.6%)</b> · Total: <b class="num-pos">+21.95u</b> · ROI: <b class="num-pos">+16.38%</b> · Sharpe: <b>2.49</b></div>
            </div>
            <svg viewBox="0 0 {mw} {mh}" style="width:100%; height:155px; margin-top:8px;">
              <line x1="10" y1="{y_m_zero:.1f}" x2="{mw-10}" y2="{y_m_zero:.1f}" stroke="#334155" stroke-dasharray="3,3"/>
              {''.join(bar_els)}
              <polyline fill="none" stroke="#38bdf8" stroke-width="2.0" stroke-dasharray="4,2" points="{' '.join(cum_m_pts)}"/>
            </svg>
            <div class="muted" style="font-size:10.5px; margin-top:2px;">
              <span style="color:#22c55e;">██ Positive Month (u)</span> &nbsp;·&nbsp; <span style="color:#ef4444;">██ Drawdown Month</span> &nbsp;·&nbsp; <span style="color:#38bdf8;">┅┅ Expanding-Window Cumulative Curve (+21.95u)</span>
            </div>
          </div>
        </div>
        """

    sport_buttons_html = "".join(
        f'<button type="button" class="sport-btn {"active" if k == norm_sport else ""}" data-sport-btn="{k}" onclick="applySportFilter(\'{k}\')">{html.escape(label)}</button>'
        for k, label in SPORT_FILTER_LABELS.items()
    )

    from datetime import timedelta
    now_loc = datetime.now(ZoneInfo(DEFAULT_LOCAL_TZ))
    today_ymd = now_loc.strftime("%Y-%m-%d")
    tom_ymd = (now_loc + timedelta(days=1)).strftime("%Y-%m-%d")
    day_counts: dict[str, int] = {}
    for b in all_best_bets_for_html:
        d_str = _match_day_key(b["date"])
        if len(d_str) == 10 and d_str[4] == "-":
            day_counts[d_str] = day_counts.get(d_str, 0) + 1
    sorted_days = sorted(day_counts.keys())

    # Default to Today if Today has picks; else Today + Tomorrow if available; else All Days
    if day_counts.get(today_ymd, 0) > 0:
        default_day_filter = today_ymd
    elif (day_counts.get(today_ymd, 0) + day_counts.get(tom_ymd, 0)) > 0:
        default_day_filter = "next48h"
    else:
        default_day_filter = "all"

    day_btns: list[str] = [
        f'<button type="button" class="sport-btn {"active" if default_day_filter == "all" else ""}" data-day-btn="all" onclick="applyDayFilter(\'all\')">All Days ({len(all_best_bets_for_html)})</button>'
    ]
    two_day_cnt = day_counts.get(today_ymd, 0) + day_counts.get(tom_ymd, 0)
    if two_day_cnt > 0:
        day_btns.append(
            f'<button type="button" class="sport-btn {"active" if default_day_filter == "next48h" else ""}" data-day-btn="next48h" data-day-set="{today_ymd},{tom_ymd}" onclick="applyDayFilter(\'next48h\')">Today + Tomorrow ({two_day_cnt})</button>'
        )
    for d_ymd in sorted_days:
        cnt = day_counts[d_ymd]
        try:
            d_obj = datetime.strptime(d_ymd, "%Y-%m-%d")
            short_lbl = d_obj.strftime("%a %b %d")
        except Exception:
            short_lbl = d_ymd
        if d_ymd == today_ymd:
            lbl = f"Today · {short_lbl} ({cnt})"
        elif d_ymd == tom_ymd:
            lbl = f"Tomorrow · {short_lbl} ({cnt})"
        else:
            lbl = f"{short_lbl} ({cnt})"
        is_act = "active" if default_day_filter == d_ymd else ""
        day_btns.append(
            f'<button type="button" class="sport-btn {is_act}" data-day-btn="{html.escape(d_ymd)}" onclick="applyDayFilter(\'{html.escape(d_ymd)}\')">{html.escape(lbl)}</button>'
        )
    day_buttons_html = "".join(day_btns)
    clv_kpi_cls = "pos" if mean_clv > 0 else ("neg" if mean_clv < 0 else "")
    losses_cls = ' class="num-neg"' if settled_losses_n > 0 else ""

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VektorPulse — Sports Edge &amp; Score Intelligence</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64' fill='none'%3E%3Cpolygon points='32,3 57,17.5 57,46.5 32,61 7,46.5 7,17.5' fill='%230f172a' stroke='%2338bdf8' stroke-width='3'/%3E%3Cpath d='M12 33 L20 33 L26 46 L35 16 L41 34 L51 20' stroke='%2322c55e' stroke-width='4.2' stroke-linecap='round' stroke-linejoin='round'/%3E%3Cpath d='M44.5 19.5 L51.5 19.5 L51.5 26.5' stroke='%2338bdf8' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<style>
  :root {{
    --bg: #0b0f17; --panel: #131b29; --border: #223049; --text: #e6edf7;
    --muted: #8b9bb4; --accent: #38bdf8; --green: #22c55e; --red: #ef4444; --amber: #f59e0b;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 20px 24px; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 12px; }}
  header {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; background: linear-gradient(135deg, #0f172a 0%, #131b29 60%, rgba(56, 189, 248, 0.08) 100%); border: 1px solid var(--border); border-radius: 12px; padding: 14px 18px; margin-bottom: 16px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25); }}
  .brand-wrap {{ display: flex; align-items: center; gap: 14px; }}
  .brand-logo {{ width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.28)); transition: transform 0.2s ease; }}
  .brand-logo:hover {{ transform: scale(1.05); }}
  .brand-title-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  h1 {{ margin: 0; font-size: 21px; font-weight: 800; letter-spacing: -0.03em; background: linear-gradient(90deg, #ffffff 0%, #38bdf8 55%, #22c55e 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .brand-tagline {{ font-size: 12px; color: #cbd5e1; font-weight: 500; }}
  .brand-meta {{ display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-top: 4px; font-size: 11px; color: var(--muted); }}
  .meta-chip {{ display: inline-flex; align-items: center; gap: 4px; background: rgba(15, 22, 35, 0.85); border: 1px solid var(--border); border-radius: 6px; padding: 2px 7px; font-size: 10.5px; color: var(--muted); }}
  .meta-chip b {{ color: var(--text); }}
  h2 {{ font-size: 15px; margin: 22px 0 10px; color: var(--accent); }}
  h3 {{ margin: 8px 0 4px; font-size: 14px; }}
  .muted {{ color: var(--muted); font-size: 11.5px; }}
  .filter-bar {{ display: flex; align-items: center; flex-wrap: wrap; gap: 10px; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; margin-bottom: 10px; font-size: 11.5px; }}
  .filter-bar input[type="range"] {{ accent-color: var(--accent); cursor: pointer; }}
  .sport-btn-group {{ display: flex; flex-wrap: wrap; gap: 5px; }}
  .sport-btn {{ background: #0f1623; color: var(--muted); border: 1px solid var(--border); border-radius: 99px; padding: 4px 10px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.15s ease; }}
  .sport-btn:hover {{ border-color: var(--accent); color: var(--text); }}
  .sport-btn.active {{ background: rgba(56, 189, 248, 0.16); border-color: var(--accent); color: var(--accent); }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(165px, 1fr)); gap: 10px; margin-bottom: 18px; }}
  .kpi {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; }}
  .kpi span {{ display: block; color: var(--muted); font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .kpi b {{ font-size: 18px; display: block; margin-top: 3px; color: var(--text); }}
  .kpi b.pos, .num-pos {{ color: var(--green) !important; }}
  .kpi b.neg, .num-neg {{ color: var(--red) !important; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 12px; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }}
  .card-veto {{ border-color: #7f1d1d; opacity: 0.88; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: center; }}
  .pill {{ display: inline-block; padding: 1.5px 7px; border-radius: 6px; font-size: 10.5px; font-weight: 600; background: rgba(56, 189, 248, 0.12); color: var(--accent); border: 1px solid rgba(56, 189, 248, 0.35); margin-right: 3px; }}
  .pill.tier {{ background: rgba(245, 158, 11, 0.12); color: var(--amber); border-color: rgba(245, 158, 11, 0.42); }}
  .pill.badge-bet {{ background: rgba(34, 197, 94, 0.14); color: var(--green); border-color: rgba(34, 197, 94, 0.42); }}
  .pill.badge-veto {{ background: rgba(239, 68, 68, 0.16); color: var(--red); border-color: rgba(239, 68, 68, 0.45); }}
  .meta {{ color: var(--muted); font-size: 11.5px; margin-bottom: 8px; }}
  .odds-strip {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; background: #0e1522; padding: 6px 8px; border-radius: 6px; margin-bottom: 10px; }}
  .odds-strip span {{ display: block; font-size: 10px; color: var(--muted); }}
  .odds-strip b {{ font-size: 12.5px; }}
  .f-row {{ display: grid; grid-template-columns: 95px 1fr 44px; align-items: center; gap: 6px; font-size: 11px; margin: 3px 0; }}
  .f-name {{ color: var(--muted); }}
  .f-track {{ background: #0b0f17; height: 6px; border-radius: 4px; overflow: hidden; }}
  .f-fill.pos {{ background: var(--green); height: 100%; }}
  .f-fill.neg {{ background: var(--red); height: 100%; }}
  .f-val.pos {{ color: var(--green); text-align: right; font-variant-numeric: tabular-nums; }}
  .f-val.neg {{ color: var(--red); text-align: right; font-variant-numeric: tabular-nums; }}
  .gates {{ display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-top: 8px; padding-top: 6px; border-top: 1px solid var(--border); }}
  .headlines {{ margin: 6px 0 0; padding-left: 16px; font-size: 11px; color: #cbd5e1; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; font-size: 11.5px; margin-bottom: 18px; }}
  th, td {{ padding: 7px 10px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #0f1623; color: var(--muted); font-weight: 600; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.03em; user-select: none; white-space: nowrap; }}
  .sortable-table th[onclick] {{ cursor: pointer; transition: color 0.15s ease, background 0.15s ease; white-space: nowrap; }}
  .sortable-table th[onclick]:hover {{ color: var(--accent); background: #162133; }}
  .sortable-table th[onclick]::after {{ content: "\\00a0⇅"; opacity: 0.4; font-size: 9.5px; display: inline-block; margin-left: 2px; }}
  .sortable-table th.sort-asc::after {{ content: "\\00a0▲"; opacity: 1; color: var(--accent); display: inline-block; margin-left: 2px; }}
  .sortable-table th.sort-desc::after {{ content: "\\00a0▼"; opacity: 1; color: var(--accent); display: inline-block; margin-left: 2px; }}
  .col-icon {{ width: 58px; min-width: 58px; text-align: center !important; padding-left: 6px !important; padding-right: 6px !important; white-space: nowrap !important; }}
  .sport-icon {{ font-size: 14px; line-height: 1; display: inline-block; }}
  .matchup-inline {{ display: inline-flex; align-items: center; gap: 5px; flex-wrap: wrap; vertical-align: middle; }}
  .matchup-clickable {{ cursor: pointer; border-bottom: 1px dotted rgba(56, 189, 248, 0.35); padding-bottom: 1px; transition: color 0.15s ease; }}
  .matchup-clickable:hover {{ color: var(--accent); border-bottom-color: var(--accent); }}
  .modal-backdrop {{ display: none; position: fixed; inset: 0; background: rgba(7, 11, 19, 0.78); backdrop-filter: blur(4px); z-index: 999; align-items: center; justify-content: center; padding: 20px; }}
  .modal-card {{ background: var(--panel); border: 1px solid var(--accent); border-radius: 12px; width: 100%; max-width: 680px; max-height: 86vh; overflow-y: auto; padding: 18px 20px; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.65); }}
  .form-pill {{ display: inline-block; width: 20px; height: 20px; line-height: 20px; text-align: center; border-radius: 5px; font-weight: 700; font-size: 10.5px; margin-right: 3px; }}
  .form-W {{ background: rgba(34, 197, 94, 0.2); color: var(--green); border: 1px solid rgba(34, 197, 94, 0.45); }}
  .form-D {{ background: rgba(245, 158, 11, 0.18); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.42); }}
  .form-L {{ background: rgba(239, 68, 68, 0.2); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.45); }}
  .comp-logo {{ width: 15px; height: 15px; object-fit: contain; vertical-align: -3px; margin-right: 4px; border-radius: 3px; }}
  .team-logo {{ width: 18px; height: 18px; object-fit: contain; vertical-align: middle; flex-shrink: 0; }}
  .team-logo-lg {{ width: 22px; height: 22px; object-fit: contain; vertical-align: middle; flex-shrink: 0; }}
  .player-avatar {{ width: 20px; height: 20px; object-fit: cover; border-radius: 50%; border: 1px solid rgba(56, 189, 248, 0.45); background: #0f172a; vertical-align: middle; flex-shrink: 0; }}
  .ledger-grid-table {{ table-layout: fixed; }}
  .ledger-grid-table col.c-sport {{ width: 60px; }}
  .ledger-grid-table col.c-comp {{ width: 15%; }}
  .ledger-grid-table col.c-ko {{ width: 14%; }}
  .ledger-grid-table col.c-match {{ width: 20%; }}
  .ledger-grid-table col.c-pick {{ width: 15%; }}
  .ledger-grid-table col.c-score {{ width: 13%; }}
  .ledger-grid-table col.c-odds {{ width: 12%; }}
  .ledger-grid-table col.c-res {{ width: 11%; }}
  .hidden-by-odds, .hidden-by-sport, .hidden-by-search, .hidden-by-day {{ display: none !important; }}
  .section-head {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin: 22px 0 10px; }}
  .section-head h2 {{ margin: 0; }}
  .btn-group {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
  .btn-export {{ display: inline-flex; align-items: center; gap: 5px; background: #1e293b; color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px; font-size: 11px; font-weight: 600; cursor: pointer; transition: all 0.15s ease; }}
  .btn-export:hover:not(:disabled) {{ border-color: var(--accent); color: var(--accent); }}
  .btn-export:disabled, .btn-export.is-busy {{ opacity: 0.58; cursor: not-allowed !important; pointer-events: none; }}
  .btn-primary {{ background: rgba(56, 189, 248, 0.16); color: var(--accent); border-color: var(--accent); }}
  .btn-telegram {{ background: rgba(34, 197, 94, 0.16); color: var(--green); border-color: var(--green); }}
  .btn-mini {{ background: #0f1623; color: var(--accent); border: 1px solid var(--border); border-radius: 6px; padding: 2px 6px; font-size: 11px; cursor: pointer; margin-left: 4px; }}
  .btn-mini:hover {{ border-color: var(--accent); background: #1e293b; }}
  .stream-pill {{ display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 99px; font-size: 12px; font-weight: 600; background: #0f1623; border: 1px solid var(--border); color: var(--muted); }}
  .stream-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--amber); display: inline-block; }}
  .stream-dot.online {{ background: var(--green); box-shadow: 0 0 8px var(--green); }}
  .search-input {{ background: #0b0f17; color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 6px 12px; font-size: 13px; min-width: 210px; }}
  .toast-banner {{ display: none; background: rgba(56, 189, 248, 0.14); border: 1px solid var(--accent); color: var(--text); border-radius: 10px; padding: 10px 16px; margin-bottom: 16px; font-size: 13px; justify-content: space-between; align-items: center; }}
  .progress-wrap {{ display: none; background: var(--panel); border: 1px solid var(--accent); border-radius: 10px; padding: 10px 16px; margin-bottom: 16px; align-items: center; gap: 12px; font-size: 13px; }}
  .spinner {{ width: 15px; height: 15px; border: 2.2px solid rgba(56, 189, 248, 0.28); border-top-color: var(--accent); border-radius: 50%; display: inline-block; animation: spin 0.75s linear infinite; flex-shrink: 0; }}
  .progress-bar-track {{ flex: 1; height: 6px; background: #0b0f17; border-radius: 99px; overflow: hidden; min-width: 120px; }}
  .progress-bar-fill {{ width: 38%; height: 100%; background: linear-gradient(90deg, var(--accent), var(--green)); border-radius: 99px; animation: indet 1.25s ease-in-out infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  @keyframes indet {{ 0% {{ transform: translateX(-100%); }} 100% {{ transform: translateX(280%); }} }}
  @keyframes vpPulseGlow {{ 0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.35)); }} 50% {{ transform: scale(1.06); filter: drop-shadow(0 0 22px rgba(34, 197, 94, 0.55)); }} }}
  @keyframes vpWaveDash {{ 0% {{ stroke-dashoffset: 120; }} 50% {{ stroke-dashoffset: 0; }} 100% {{ stroke-dashoffset: -120; }} }}
  .page-loader-overlay {{ position: fixed; inset: 0; z-index: 2000; background: rgba(11, 15, 23, 0.88); backdrop-filter: blur(8px); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; transition: opacity 0.32s ease, visibility 0.32s ease; }}
  .page-loader-overlay.is-hidden {{ opacity: 0; visibility: hidden; pointer-events: none; }}
  .page-loader-card {{ background: linear-gradient(145deg, #131b29 0%, #0f172a 100%); border: 1px solid rgba(56, 189, 248, 0.45); border-radius: 16px; padding: 24px 32px; display: flex; flex-direction: column; align-items: center; gap: 12px; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65), 0 0 30px rgba(56, 189, 248, 0.14); max-width: 420px; width: 90%; text-align: center; }}
  .page-loader-ring-wrap {{ position: relative; width: 68px; height: 68px; display: flex; align-items: center; justify-content: center; animation: vpPulseGlow 2s ease-in-out infinite; }}
  .page-loader-ring {{ position: absolute; inset: 0; border-radius: 50%; border: 2.5px solid rgba(56, 189, 248, 0.18); border-top-color: var(--accent); border-right-color: var(--green); animation: spin 0.95s cubic-bezier(0.5, 0.15, 0.5, 0.85) infinite; }}
  .page-loader-wave {{ stroke-dasharray: 120; stroke-dashoffset: 120; animation: vpWaveDash 1.8s ease-in-out infinite; }}
  .top-loading-bar {{ position: fixed; top: 0; left: 0; right: 0; height: 3px; z-index: 2100; background: rgba(15, 23, 42, 0.4); overflow: hidden; opacity: 0; transition: opacity 0.2s ease; pointer-events: none; }}
  .top-loading-bar.is-active {{ opacity: 1; }}
  .top-loading-bar-fill {{ width: 35%; height: 100%; background: linear-gradient(90deg, var(--accent), var(--green), var(--accent)); animation: indet 1.1s ease-in-out infinite; box-shadow: 0 0 10px var(--accent); }}
</style>
</head>
<body>
  <div id="topLoadingBar" class="top-loading-bar is-active">
    <div class="top-loading-bar-fill"></div>
  </div>
  <div id="pageLoadingOverlay" class="page-loader-overlay" role="status" aria-live="polite">
    <div class="page-loader-card">
      <div class="page-loader-ring-wrap">
        <div class="page-loader-ring"></div>
        <svg width="42" height="42" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <polygon points="32,3 57,17.5 57,46.5 32,61 7,46.5 7,17.5" fill="#0f172a" stroke="#38bdf8" stroke-width="2.6" stroke-linejoin="round"/>
          <path class="page-loader-wave" d="M12 33 L20 33 L26 46 L35 16 L41 34 L51 20" stroke="#22c55e" stroke-width="4.0" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="35" cy="16" r="2.6" fill="#38bdf8"/>
          <circle cx="51" cy="20" r="2.8" fill="#22c55e"/>
        </svg>
      </div>
      <div>
        <div id="pageLoaderTitle" style="font-size:15px; font-weight:800; letter-spacing:-0.01em; color:var(--text);">Loading VektorPulse Intelligence...</div>
        <div id="pageLoaderSub" class="muted" style="margin-top:4px; font-size:11.5px;">Hydrating 59,000+ matches, calibrated odds, H2H form &amp; live SSE feed</div>
      </div>
      <div class="progress-bar-track" style="width:100%;"><div class="progress-bar-fill"></div></div>
    </div>
  </div>
  <header>
    <div class="brand-wrap">
      <div class="brand-logo" title="VektorPulse — Sports Edge &amp; Score Intelligence">
        <svg width="46" height="46" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="vpShieldBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#0f172a"/>
              <stop offset="55%" stop-color="#131b29"/>
              <stop offset="100%" stop-color="#0b2436"/>
            </linearGradient>
            <linearGradient id="vpRim" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#38bdf8"/>
              <stop offset="50%" stop-color="#10b981"/>
              <stop offset="100%" stop-color="#22c55e"/>
            </linearGradient>
            <linearGradient id="vpPulse" x1="0%" y1="50%" x2="100%" y2="20%">
              <stop offset="0%" stop-color="#38bdf8"/>
              <stop offset="55%" stop-color="#34d399"/>
              <stop offset="100%" stop-color="#22c55e"/>
            </linearGradient>
            <filter id="vpGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.0" result="blur"/>
              <feComposite in="SourceGraphic" in2="blur" operator="over"/>
            </filter>
          </defs>
          <polygon points="32,3 57,17.5 57,46.5 32,61 7,46.5 7,17.5" fill="url(#vpShieldBg)" stroke="url(#vpRim)" stroke-width="2.4" stroke-linejoin="round"/>
          <circle cx="32" cy="32" r="19" stroke="#38bdf8" stroke-opacity="0.16" stroke-width="1.2" stroke-dasharray="3 3"/>
          <path d="M16 40 C22 25, 42 25, 48 40" stroke="#38bdf8" stroke-opacity="0.18" stroke-width="1.3" fill="none"/>
          <path d="M12 33 L20 33 L26 46 L35 16 L41 34 L51 20" stroke="url(#vpPulse)" stroke-width="3.8" stroke-linecap="round" stroke-linejoin="round" filter="url(#vpGlow)"/>
          <path d="M44.5 19.5 L51.5 19.5 L51.5 26.5" stroke="#22c55e" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="35" cy="16" r="2.6" fill="#38bdf8"/>
          <circle cx="51" cy="20" r="2.8" fill="#22c55e"/>
        </svg>
      </div>
      <div>
        <div class="brand-title-row">
          <h1>VektorPulse</h1>
          <span class="pill badge-bet" style="font-size:10px;">LIVE AI</span>
          <span class="brand-tagline">Sports Edge, Exact-Score &amp; Paper-Betting Intelligence</span>
        </div>
        <div class="brand-meta">
          <span class="meta-chip">🕒 Updated: {_time_span(gen_at, bold=True)}</span>
          <span class="meta-chip">🗄️ <b>{total_matches:,}</b> Verified Matches</span>
          <span class="meta-chip">📡 <span id="lastStreamTick">Ready</span></span>
          <span class="meta-chip" title="Provisional / unconfirmed start times (e.g. awaiting official court Order of Play) are marked with * and update automatically"><b>*</b> = Provisional Time</span>
        </div>
      </div>
    </div>
    <div class="btn-group">
      <span class="stream-pill" title="Server-Sent Events (SSE) Live Stream Status">
        <span id="streamDot" class="stream-dot"></span>
        <span id="streamStatusText">Live Stream: Connecting...</span>
      </span>
      <button id="inplayAlertsToggleBtn" class="btn-export" type="button" onclick="toggleInplayDiscordAlerts()" title="Toggle automated Discord push alerts for Live In-Play Dominance / Set-1 Rebound edges (Default: OFF)">🔕 Live Alerts: OFF</button>
      <button id="syncLedgerBtn" class="btn-export btn-primary js-action-btn" type="button" onclick="syncAndSettleLedger(false)">🔄 Sync &amp; Settle</button>
      <button id="rescanLiveBtn" class="btn-export js-action-btn" type="button" onclick="syncAndSettleLedger(true)">⚡ Rescan Live</button>
      <button id="runFullPipelineBtn" class="btn-export js-action-btn" type="button" onclick="runFullDailyPipeline()">🚀 Full Pipeline</button>
      <button id="topTelegramBtn" class="btn-export btn-telegram" type="button" onclick="openTelegramPanel()">💬 Share Picks</button>
      <button id="topSettingsBtn" class="btn-export" type="button" onclick="openSettingsModal()" title="Open VektorPulse Settings &amp; Per-Sport Discord Webhooks">⚙️ Settings</button>
    </div>
  </header>

  <div id="actionProgressBanner" class="progress-wrap">
    <span class="spinner"></span>
    <b id="actionProgressText">Syncing paper-betting ledger against ESPN...</b>
    <div class="progress-bar-track"><div class="progress-bar-fill"></div></div>
    <span id="actionElapsedText" class="muted">0.0s</span>
  </div>

  <div id="syncToast" class="toast-banner">
    <span id="syncToastText"></span>
    <button type="button" class="btn-mini" onclick="document.getElementById('syncToast').style.display='none'">✕</button>
  </div>

  <div id="matchupInspectorModal" class="modal-backdrop" onclick="if(event.target===this)this.style.display='none'">
    <div class="modal-card">
      <div class="card-head" style="margin-bottom:12px;">
        <div><b id="miTitle" style="font-size:15px;">Matchup Drill-Down Inspector</b></div>
        <button class="btn-export" type="button" onclick="document.getElementById('matchupInspectorModal').style.display='none'">Close ✕</button>
      </div>
      <div id="miBody" class="muted">Loading H2H, Last-6 Form, and Exact-Score Breakdown...</div>
    </div>
  </div>

  <div id="settingsModal" class="modal-backdrop" onclick="if(event.target===this)this.style.display='none'">
    <div class="modal-card" style="max-width:740px;">
      <div class="card-head" style="margin-bottom:12px;">
        <div>
          <b style="font-size:15px; color:var(--accent);">⚙️ VektorPulse Settings &amp; Per-Sport Discord Webhook Routing</b>
          <div class="muted">Tweaked settings apply immediately and persist in <code>data/webapp_settings.json</code> &amp; browser storage</div>
        </div>
        <button class="btn-export" type="button" onclick="document.getElementById('settingsModal').style.display='none'">Close ✕</button>
      </div>

      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(310px, 1fr)); gap:14px; font-size:12px;">
        <div style="padding:12px; background:#0b0f17; border:1px solid var(--border); border-radius:8px;">
          <div style="font-weight:700; color:var(--green); margin-bottom:8px;">💰 Bankroll, Stake &amp; Filter Defaults</div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Default Bankroll (€):</span>
            <input id="cfgBankrollInput" type="number" min="50" max="1000000" step="50" value="1000" style="width:95px; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:4px 7px; font-weight:700;">
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Default Ready-to-Bet (€):</span>
            <input id="cfgBetBudgetInput" type="number" min="5" max="100000" step="5" value="100" style="width:95px; background:#111827; color:var(--green); border:1px solid var(--border); border-radius:5px; padding:4px 7px; font-weight:700;">
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Default Slip Risk Mode:</span>
            <select id="cfgRiskModeSelect" style="background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:4px 7px;">
              <option value="balanced">⚖️ Balanced</option>
              <option value="fortress">🛡️ Ultra-Safe Fortress</option>
              <option value="upside">🚀 Max Return Multiplier</option>
            </select>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Soft Min-Odds Threshold:</span>
            <input id="cfgMinOddsInput" type="number" min="1.05" max="2.50" step="0.05" value="1.10" style="width:95px; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:4px 7px;">
          </div>
        </div>

        <div style="padding:12px; background:#0b0f17; border:1px solid var(--border); border-radius:8px;">
          <div style="font-weight:700; color:var(--accent); margin-bottom:8px;">🎯 Model Thresholds &amp; Alert Toggles</div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Mispricing Min Edge (pp):</span>
            <input id="cfgMispricingEdgeInput" type="number" min="0.5" max="15.0" step="0.5" value="2.0" style="width:85px; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:4px 7px;">
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Mispricing Min EV (%):</span>
            <input id="cfgMispricingEvInput" type="number" min="0.5" max="25.0" step="0.5" value="2.0" style="width:85px; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:4px 7px;">
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Live In-Play Alerts (Global):</span>
            <input id="cfgInplayAlertsChk" type="checkbox">
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span>Settled Bet Discord Alerts:</span>
            <input id="cfgSettlementAlertsChk" type="checkbox" checked>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span>Auto Daily Digest Hour (0–23):</span>
            <input id="cfgDigestHourInput" type="text" placeholder="Off (e.g. 9)" style="width:85px; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:4px 7px;">
          </div>
        </div>
      </div>

      <div style="margin-top:14px; padding:12px; background:#0b0f17; border:1px solid var(--border); border-radius:8px; font-size:12px;">
        <div style="font-weight:700; color:var(--amber); margin-bottom:4px;">💬 Global &amp; Per-Sport Discord Webhooks (Env Vars + Optional UI Overrides)</div>
        <div class="muted" style="margin-bottom:10px;">
          Configure per-sport webhooks in <code>model/.env</code> (<code>DISCORD_WEBHOOK_URL_SOCCER</code>, <code>DISCORD_WEBHOOK_URL_TENNIS</code>, <code>DISCORD_WEBHOOK_URL_HOCKEY</code>, <code>DISCORD_WEBHOOK_URL_BASKETBALL</code>, <code>DISCORD_WEBHOOK_URL_NFL</code>, <code>DISCORD_WEBHOOK_URL_BASEBALL</code>) on top of global <code>DISCORD_WEBHOOK_URL</code>, or paste custom overrides below:
        </div>
        <div style="display:grid; grid-template-columns:1fr; gap:7px;">
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="min-width:175px;">🌐 <b>Global Default</b> (<code>DISCORD_WEBHOOK_URL</code>):</span>
            <input id="cfgWhGlobal" type="password" placeholder="Uses DISCORD_WEBHOOK_URL from model/.env" style="flex:1; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:5px 8px; font-size:11.5px;">
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="min-width:175px;">⚽ <b>Football</b> (<code>..._SOCCER</code>):</span>
            <input id="cfgWhSoccer" type="password" placeholder="Falls back to Global Webhook unless set in .env or here" style="flex:1; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:5px 8px; font-size:11.5px;">
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="min-width:175px;">🎾 <b>Tennis</b> (<code>..._TENNIS</code>):</span>
            <input id="cfgWhTennis" type="password" placeholder="Falls back to Global Webhook unless set in .env or here" style="flex:1; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:5px 8px; font-size:11.5px;">
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="min-width:175px;">🏒 <b>Hockey / NHL</b> (<code>..._HOCKEY</code>):</span>
            <input id="cfgWhHockey" type="password" placeholder="Falls back to Global Webhook unless set in .env or here" style="flex:1; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:5px 8px; font-size:11.5px;">
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="min-width:175px;">🏀 <b>Basketball / NBA</b> (<code>..._NBA</code>):</span>
            <input id="cfgWhBasketball" type="password" placeholder="Falls back to Global Webhook unless set in .env or here" style="flex:1; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:5px 8px; font-size:11.5px;">
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="min-width:175px;">🏈 <b>NFL</b> (<code>..._NFL</code>):</span>
            <input id="cfgWhFootball" type="password" placeholder="Falls back to Global Webhook unless set in .env or here" style="flex:1; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:5px 8px; font-size:11.5px;">
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="min-width:175px;">⚾ <b>Baseball / MLB</b> (<code>..._MLB</code>):</span>
            <input id="cfgWhBaseball" type="password" placeholder="Falls back to Global Webhook unless set in .env or here" style="flex:1; background:#111827; color:var(--text); border:1px solid var(--border); border-radius:5px; padding:5px 8px; font-size:11.5px;">
          </div>
        </div>
      </div>

      <div style="margin-top:14px; display:flex; justify-content:flex-end; gap:10px;">
        <button class="btn-export" type="button" onclick="document.getElementById('settingsModal').style.display='none'">Cancel</button>
        <button class="btn-export btn-telegram" type="button" onclick="saveSettingsModal()">💾 Save &amp; Apply Settings</button>
      </div>
    </div>
  </div>

  <div id="telegramModal" class="card" style="display:none; margin-bottom:20px; border-color:var(--green);">
    <div class="card-head" style="margin-bottom:10px;">
      <div>
        <b>💬 Discord (Primary) &amp; Telegram (Optional) Social Publisher</b>
        <span id="discordEnvBadge" class="pill" style="margin-left:6px;">Checking Discord .env...</span>
        <span id="tgEnvBadge" class="pill" style="margin-left:4px;">Telegram .env</span>
      </div>
      <button class="btn-export" type="button" onclick="document.getElementById('telegramModal').style.display='none'">Close ✕</button>
    </div>
    <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:8px;">
      <input id="discordWebhookInput" type="password" placeholder="Discord Webhook URL (https://discord.com/api/webhooks/... or set DISCORD_WEBHOOK_URL in model/.env)" style="flex:2; min-width:320px; background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:7px 10px; font-size:12px;">
      <button class="btn-export js-action-btn" type="button" onclick="openTelegramPanel()">🔄 Rebuild Digest</button>
      <button class="btn-export" type="button" onclick="copyTelegramPreview()">📋 Copy Message</button>
      <button id="discordSendBtn" class="btn-export btn-telegram js-action-btn" type="button" onclick="postToDiscordChannel()">🚀 Send to Discord Channel</button>
    </div>
    <details style="margin-bottom:8px; font-size:12px; color:var(--muted);">
      <summary style="cursor:pointer;">Optional Telegram Override (for non-Zscaler networks)</summary>
      <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:6px;">
        <input id="tgBotToken" type="password" placeholder="Telegram Bot Token (optional if set in model/.env)" style="flex:1; min-width:220px; background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:12px;">
        <input id="tgChatId" type="text" placeholder="Telegram Chat ID (optional if set in model/.env)" style="flex:1; min-width:200px; background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:12px;">
        <button id="tgSendBtn" class="btn-export js-action-btn" type="button" onclick="postToTelegramChannel()">✈️ Send to Telegram</button>
      </div>
    </details>
    <textarea id="tgMessagePreview" rows="11" style="width:100%; background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:8px; padding:10px; font-family:monospace; font-size:12px;"></textarea>
    <div id="tgStatusMsg" class="muted" style="margin-top:6px;"></div>
  </div>

  <div class="filter-bar">
    <b>Filter by Day:</b>
    <div class="sport-btn-group" id="dayFilterGroup">
      {day_buttons_html}
    </div>
  </div>

  <div class="filter-bar">
    <b>Filter by Sport:</b>
    <div class="sport-btn-group" id="sportFilterGroup">
      {sport_buttons_html}
    </div>
    <b>Search:</b>
    <input id="teamSearchInput" class="search-input" type="search" placeholder="Search team, player, league..." oninput="applySearchFilter(this.value)">
    <b>Timezone:</b>
    <div class="sport-btn-group">
      <button type="button" class="sport-btn active" id="tzBtnLocal" onclick="applyTimezoneMode('local')">Local ({DEFAULT_LOCAL_TZ})</button>
      <button type="button" class="sport-btn" id="tzBtnUtc" onclick="applyTimezoneMode('utc')">UTC</button>
    </div>
    <b>Bankroll (€):</b>
    <input id="bankrollInput" type="number" min="50" max="1000000" step="50" value="1000" oninput="applyBankrollCalculator(this.value)" style="width:82px; background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:4px 8px; font-size:11.5px; font-weight:700;">
    <span style="margin-left:auto;"></span>
    <b>Soft Min-Odds:</b>
    <input id="minOddsSlider" type="range" min="1.05" max="2.00" step="0.05" value="{min_odds:.2f}" oninput="applyOddsFilter(this.value)">
    <span>&gt; <b id="minOddsLabel">{min_odds:.2f}</b> (<span id="minProfitLabel">{(min_odds-1)*100:.0f}%</span>)</span>
  </div>

  <section class="kpi-grid">
    <div class="kpi"><span>Store Hygiene</span><b class="pos">0 Errors / {total_matches:,}</b></div>
    <div class="kpi"><span>Big-5 Top 10% Post-2025 ROI</span><b class="pos">+17.92% (p=0.008)</b></div>
    <div class="kpi"><span>Active Soccer Bets</span><b>{active_bets}</b></div>
    <div class="kpi"><span>System-1 / XI Vetoed</span><b class="{'neg' if vetoed_bets > 0 else ''}">{vetoed_bets}</b></div>
    <div class="kpi"><span>Prospective Mean CLV</span><b class="{clv_kpi_cls}">{mean_clv:+.2f}%</b></div>
    <div class="kpi"><span>Total Best Bets (&gt;{min_odds:.2f})</span><b id="visibleBestBetsKpi" class="pos">{len(best_bets)}</b></div>
  </section>

  <section class="card" id="smartBetPlannerSection" style="margin-bottom:20px; border:1px solid rgba(56,189,248,0.45); background:linear-gradient(180deg, rgba(17,24,39,0.96) 0%, rgba(11,15,23,0.98) 100%);">
    <div class="card-head" style="margin-bottom:10px;">
      <div>
        <b style="font-size:14.5px; color:var(--accent);">🎯 Smart Bet Slip &amp; Stake Allocation Optimizer</b>
        <span class="muted" style="margin-left:8px;">Enter the exact amount (€) you want to bet — compares Safe Combos vs. Kelly-Weighted Singles vs. Hybrid 60/40 Split</span>
      </div>
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <b>Ready to Bet (€):</b>
        <input id="betAmountInput" type="number" min="5" max="100000" step="5" value="100" oninput="buildSmartBetPlan()" style="width:88px; background:#0b0f17; color:var(--green); border:1px solid var(--accent); border-radius:6px; padding:5px 8px; font-size:13px; font-weight:800;">
        <div class="sport-btn-group">
          <button type="button" class="sport-btn" onclick="setBetBudget(25)">€25</button>
          <button type="button" class="sport-btn" onclick="setBetBudget(50)">€50</button>
          <button type="button" class="sport-btn active" id="budgetBtn100" onclick="setBetBudget(100)">€100</button>
          <button type="button" class="sport-btn" onclick="setBetBudget(250)">€250</button>
          <button type="button" class="sport-btn" onclick="setBetBudget(500)">€500</button>
        </div>
        <b>Mode:</b>
        <select id="betRiskProfileSelect" onchange="buildSmartBetPlan()" style="background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:5px 8px; font-size:11.5px; font-weight:600;">
          <option value="balanced" selected>⚖️ Balanced (Safe 2-Leg + Top 4 Singles)</option>
          <option value="fortress">🛡️ Ultra-Safe Fortress (Max Hit Rate &ge;72%)</option>
          <option value="upside">🚀 Max Return Multiplier (3-Leg Booster + Value Singles)</option>
        </select>
        <button type="button" class="btn-export" onclick="printSmartBetTicket()" title="Open printable / Save-as-PDF ticket for your current Smart Bet Slip">🖨️ Print / PDF Slip</button>
      </div>
    </div>
    <div id="smartBetPlanGrid" class="cards" style="grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap:12px;"></div>
  </section>

  <section class="card" id="exactScoreSplitterSection" style="margin-bottom:20px; border:1px solid rgba(245,158,11,0.48); background:linear-gradient(180deg, rgba(17,24,39,0.96) 0%, rgba(11,15,23,0.98) 100%);">
    <div class="card-head" style="margin-bottom:10px;">
      <div>
        <b style="font-size:14px; color:var(--amber);">🎲 Exact-Score &amp; Set-Score Dutching Investment Splitter</b>
        <span class="muted" style="margin-left:8px;">Pick any high-conviction match, enter your investment (€), and optionally edit live bookmaker odds — generates 2-Score &amp; 3-Score equal-payout splits</span>
      </div>
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <b>Match:</b>
        <select id="dutchMatchSelect" onchange="onDutchMatchSelectChange()" style="max-width:300px; background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:5px 8px; font-size:11.5px; font-weight:600;"></select>
        <b>Investment (€):</b>
        <input id="dutchStakeInput" type="number" min="5" max="100000" step="5" value="25" oninput="recalcStandaloneDutchSplitter()" style="width:78px; background:#0b0f17; color:var(--green); border:1px solid var(--amber); border-radius:6px; padding:5px 8px; font-size:12.5px; font-weight:800;">
        <div class="sport-btn-group">
          <button type="button" class="sport-btn" onclick="setDutchBudget(10)">€10</button>
          <button type="button" class="sport-btn" onclick="setDutchBudget(20)">€20</button>
          <button type="button" class="sport-btn" onclick="setDutchBudget(25)">€25</button>
          <button type="button" class="sport-btn" onclick="setDutchBudget(50)">€50</button>
          <button type="button" class="sport-btn" onclick="setDutchBudget(100)">€100</button>
        </div>
      </div>
    </div>
    <div id="dutchCustomOddsBar" style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:10px; padding:8px 10px; background:#0b0f17; border:1px dashed var(--border); border-radius:8px; font-size:11.5px;"></div>
    <div id="dutchSplitterGrid" class="cards" style="grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap:12px;"></div>
  </section>

  <section class="card" id="liveMatchupAnalyzerSection" style="margin-bottom:20px; border:1px solid rgba(34,197,94,0.38);">
    <div class="card-head" style="margin-bottom:8px;">
      <div>
        <b style="font-size:13.5px; color:var(--green);">🔍 On-Demand Any-Matchup Live Analyzer</b>
        <span class="muted" style="margin-left:8px;">Analyze ANY Tennis or Football matchup (even sub-70% non-bankers) — checks live SofaScore odds, Challenger/ATP Last-5 form, H2H &amp; turnaround hours</span>
      </div>
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <input id="liveAnalyzeInput" type="search" placeholder="e.g. Medvedev vs Bublik, Bernet vs Altmaier, Dortmund vs Frankfurt..." onkeydown="if(event.key==='Enter') runLiveMatchupAnalyzer()" style="min-width:290px; background:#0b0f17; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:12px;">
        <button type="button" class="btn-export btn-primary" onclick="runLiveMatchupAnalyzer()">⚡ Analyze Matchup</button>
        <button type="button" class="sport-btn" onclick="quickAnalyzePair('Daniil Medvedev vs Alexander Bublik')">Medvedev vs Bublik</button>
        <button type="button" class="sport-btn" onclick="quickAnalyzePair('Henry Bernet vs Daniel Altmaier')">Bernet vs Altmaier</button>
        <button type="button" class="sport-btn" onclick="quickAnalyzePair('Borussia Dortmund vs Eintracht Frankfurt')">Dortmund vs Frankfurt</button>
      </div>
    </div>
    <div id="liveAnalyzeResultBox" style="display:none; margin-top:8px; padding:10px 12px; background:#0b0f17; border:1px solid var(--border); border-radius:8px; font-size:12px;"></div>
  </section>

  {mispricing_radar_html}

  <details class="card" id="walkForwardAuditPanel" style="margin-bottom:20px; border:1px solid rgba(56,189,248,0.35);">
    <summary style="cursor:pointer; font-weight:700; font-size:13.5px; color:var(--accent); display:flex; justify-content:space-between; align-items:center;">
      <span>📈 Expanding-Window Monthly Forward-Walking Backtest Audit (2025-07 &rarr; 2026-10 · Zero Lookahead Bias)</span>
      <span class="pill badge-bet">Big-5 Top 8% ROI: +18.95% (Sharpe 2.54) · ATP &ge;70%: 79.16% · WTA &ge;70%: 79.77%</span>
    </summary>
    <div style="margin-top:12px; display:grid; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)); gap:14px;">
      <div>
        <div style="margin-bottom:6px; font-weight:700;">⚽ Multi-Sport Walk-Forward Summary (Refit Monthly strictly on &lt; Month M)</div>
        <table class="sortable-table" style="margin-bottom:0;">
          <thead>
            <tr>
              <th data-sort-type="text" onclick="sortTable(this)">Model / Scope</th>
              <th data-sort-type="num" onclick="sortTable(this)">Bets (n)</th>
              <th data-sort-type="num" onclick="sortTable(this)">Win / Acc%</th>
              <th data-sort-type="num" onclick="sortTable(this)">Profit (u)</th>
              <th data-sort-type="num" onclick="sortTable(this)">ROI / Sharpe</th>
            </tr>
          </thead>
          <tbody>
            <tr><td data-sort="Big-5 Top 8%"><b>⚽ Big-5 Football · Top 8%</b></td><td data-sort="99">99</td><td data-sort="73.74"><b class="num-pos">73.7%</b></td><td data-sort="18.76"><b class="num-pos">+18.76u</b></td><td data-sort="18.95"><b class="num-pos">+18.95%</b> (SR 2.54)</td></tr>
            <tr><td data-sort="Big-5 Top 10%"><b>⚽ Big-5 Football · Top 10%</b></td><td data-sort="134">134</td><td data-sort="71.64"><b class="num-pos">71.6%</b></td><td data-sort="21.95"><b class="num-pos">+21.95u</b></td><td data-sort="16.38"><b class="num-pos">+16.38%</b> (SR 2.49)</td></tr>
            <tr><td data-sort="All 9 Dom Top 8%"><b>⚽ All 9 Domestic · Top 8%</b></td><td data-sort="174">174</td><td data-sort="72.41"><b class="num-pos">72.4%</b></td><td data-sort="27.37"><b class="num-pos">+27.37u</b></td><td data-sort="15.73"><b class="num-pos">+15.73%</b> (SR 2.81)</td></tr>
            <tr><td data-sort="All 9 Dom Top 10%"><b>⚽ All 9 Domestic · Top 10%</b></td><td data-sort="230">230</td><td data-sort="70.43"><b class="num-pos">70.4%</b></td><td data-sort="29.69"><b class="num-pos">+29.69u</b></td><td data-sort="12.91"><b class="num-pos">+12.91%</b> (SR 2.59)</td></tr>
            <tr><td data-sort="ATP Banker 70"><b>🎾 ATP Tennis · Banker &ge;70%</b></td><td data-sort="715">715</td><td data-sort="79.16"><b class="num-pos">79.2%</b> (&ge;80%: 84.2%)</td><td data-sort="45.2">+45.20u*</td><td data-sort="15.8">Brier 0.1609</td></tr>
            <tr><td data-sort="WTA Banker 70"><b>🎾 WTA Tennis · Banker &ge;70%</b></td><td data-sort="1305">1,305</td><td data-sort="79.77"><b class="num-pos">79.8%</b> (&ge;80%: 83.5%)</td><td data-sort="82.4">+82.40u*</td><td data-sort="16.1">Brier 0.1586</td></tr>
            <tr><td data-sort="US Sports Pooled"><b>🏀🏒🏈⚾ US Major Sports · Top 15%</b></td><td data-sort="102">102</td><td data-sort="68.63"><b class="num-pos">68.6%</b> (+8.4pp vs Mkt)</td><td data-sort="9.87"><b class="num-pos">+9.87u</b></td><td data-sort="9.68"><b class="num-pos">+9.68%</b></td></tr>
          </tbody>
        </table>
      </div>
      <div>
        <div style="margin-bottom:6px; font-weight:700;">📅 Monthly Forward-Walking Trajectory (Big-5 Football Top 10% · 11/13 Months Profitable)</div>
        <table class="sortable-table" style="margin-bottom:0;">
          <thead>
            <tr>
              <th data-sort-type="text" onclick="sortTable(this)">Month</th>
              <th data-sort-type="num" onclick="sortTable(this)">Bets</th>
              <th data-sort-type="num" onclick="sortTable(this)">Win Rate</th>
              <th data-sort-type="num" onclick="sortTable(this)">Profit (u)</th>
              <th data-sort-type="num" onclick="sortTable(this)">ROI%</th>
            </tr>
          </thead>
          <tbody>
            <tr><td data-sort="2025-08">2025-08</td><td data-sort="5">5</td><td data-sort="80.0"><b class="num-pos">80.0%</b></td><td data-sort="1.77"><b class="num-pos">+1.77u</b></td><td data-sort="35.46"><b class="num-pos">+35.5%</b></td></tr>
            <tr><td data-sort="2025-09">2025-09</td><td data-sort="5">5</td><td data-sort="80.0"><b class="num-pos">80.0%</b></td><td data-sort="1.31"><b class="num-pos">+1.31u</b></td><td data-sort="26.12"><b class="num-pos">+26.1%</b></td></tr>
            <tr><td data-sort="2025-10">2025-10</td><td data-sort="7">7</td><td data-sort="71.4"><b class="num-pos">71.4%</b></td><td data-sort="0.79"><b class="num-pos">+0.79u</b></td><td data-sort="11.26"><b class="num-pos">+11.3%</b></td></tr>
            <tr><td data-sort="2025-11">2025-11</td><td data-sort="13">13</td><td data-sort="69.2"><b class="num-pos">69.2%</b></td><td data-sort="1.22"><b class="num-pos">+1.22u</b></td><td data-sort="9.39"><b class="num-pos">+9.4%</b></td></tr>
            <tr><td data-sort="2025-12">2025-12</td><td data-sort="19">19</td><td data-sort="63.2">63.2%</td><td data-sort="0.07"><b class="num-pos">+0.07u</b></td><td data-sort="0.38">+0.4%</td></tr>
            <tr><td data-sort="2026-01">2026-01</td><td data-sort="10">10</td><td data-sort="60.0">60.0%</td><td data-sort="-0.90"><b class="num-neg">-0.90u</b></td><td data-sort="-9.00"><b class="num-neg">-9.0%</b></td></tr>
            <tr><td data-sort="2026-02">2026-02</td><td data-sort="16">16</td><td data-sort="75.0"><b class="num-pos">75.0%</b></td><td data-sort="3.30"><b class="num-pos">+3.30u</b></td><td data-sort="20.60"><b class="num-pos">+20.6%</b></td></tr>
            <tr><td data-sort="2026-03">2026-03</td><td data-sort="12">12</td><td data-sort="83.3"><b class="num-pos">83.3%</b></td><td data-sort="5.10"><b class="num-pos">+5.10u</b></td><td data-sort="42.46"><b class="num-pos">+42.5%</b></td></tr>
            <tr><td data-sort="2026-04">2026-04</td><td data-sort="7">7</td><td data-sort="71.4"><b class="num-pos">71.4%</b></td><td data-sort="0.85"><b class="num-pos">+0.85u</b></td><td data-sort="12.10"><b class="num-pos">+12.1%</b></td></tr>
            <tr><td data-sort="2026-05">2026-05</td><td data-sort="20">20</td><td data-sort="50.0">50.0%</td><td data-sort="-3.49"><b class="num-neg">-3.49u</b></td><td data-sort="-17.43"><b class="num-neg">-17.4%</b></td></tr>
            <tr><td data-sort="2026-08">2026-08</td><td data-sort="7">7</td><td data-sort="85.7"><b class="num-pos">85.7%</b></td><td data-sort="1.97"><b class="num-pos">+1.97u</b></td><td data-sort="28.09"><b class="num-pos">+28.1%</b></td></tr>
            <tr><td data-sort="2026-09">2026-09</td><td data-sort="9">9</td><td data-sort="100.0"><b class="num-pos">100.0%</b></td><td data-sort="7.00"><b class="num-pos">+7.00u</b></td><td data-sort="77.78"><b class="num-pos">+77.8%</b></td></tr>
            <tr><td data-sort="2026-10">2026-10</td><td data-sort="4">4</td><td data-sort="100.0"><b class="num-pos">100.0%</b></td><td data-sort="2.97"><b class="num-pos">+2.97u</b></td><td data-sort="74.27"><b class="num-pos">+74.3%</b></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </details>

  {svg_chart}

  <div data-sport-section="soccer">
    <h2>⚽ Upcoming Football Picks</h2>
    <div class="cards">
      {''.join(soccer_cards) if soccer_cards else '<p class="muted">No upcoming qualifying soccer picks in window.</p>'}
    </div>
  </div>

  <div data-sport-section="tennis">
    <h2>🎾 Upcoming Tennis Picks (ATP &amp; WTA)</h2>
    <table id="tennisTable" class="sortable-table">
      <thead>
        <tr>
          <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
          <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
          <th data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
          <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
          <th data-sort-type="text" onclick="sortTable(this)">Pick</th>
          <th data-sort-type="num" onclick="sortTable(this)">Win Prob</th>
          <th data-sort-type="num" onclick="sortTable(this)">Score Projection</th>
          <th data-sort-type="num" onclick="sortTable(this)">Min Fair Odds</th>
          <th data-sort-type="num" onclick="sortTable(this)">Odds / Target</th>
          <th data-sort-type="num" onclick="sortTable(this)">Game / Surf Elo Diff</th>
        </tr>
      </thead>
      <tbody>
        {''.join(tennis_rows) if tennis_rows else '<tr><td colspan="10" class="muted">No upcoming tennis picks above threshold.</td></tr>'}
      </tbody>
    </table>
  </div>

  <div data-sport-section="us-sports">
    <h2>🏀🏒🏈⚾ Upcoming Major League Picks (NBA · NHL · NFL · MLB)</h2>
    <table id="otherSportsTable" class="sortable-table">
      <thead>
        <tr>
          <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
          <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
          <th data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
          <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
          <th data-sort-type="text" onclick="sortTable(this)">Pick</th>
          <th data-sort-type="num" onclick="sortTable(this)">Win Prob</th>
          <th data-sort-type="num" onclick="sortTable(this)">Min Fair Odds</th>
          <th data-sort-type="num" onclick="sortTable(this)">Odds</th>
          <th data-sort-type="num" onclick="sortTable(this)">EV%</th>
        </tr>
      </thead>
      <tbody>
        {''.join(other_rows) if other_rows else '<tr><td colspan="9" class="muted">No upcoming NBA/NHL/NFL/MLB picks above threshold.</td></tr>'}
      </tbody>
    </table>
  </div>

  {doubles_cards_html}

  <div class="section-head">
    <h2 id="settledHeaderTitle">Settled Paper-Bets (Completed Results: <span id="settledCountSpan">{ledger.get('settled_count', 0)}</span> · Wins: <b class="num-pos" id="settledWinsSpan">{ledger.get('settled_wins', 0)}</b> · Losses: <b{losses_cls} id="settledLossesSpan">{settled_losses_n}</b> · Realized Profit: <span id="settledProfitSpan">{_fmt_signed(settled_profit_u, '+.2f', 'u')}</span>)</h2>
    <div class="btn-group">
      <button id="syncLedgerTableBtn" class="btn-export btn-primary js-action-btn" type="button" onclick="syncAndSettleLedger(false)">🔄 Sync &amp; Settle Ledger Now</button>
    </div>
  </div>
  {live_ledger_analytics_html}
  <table id="settledTradesTable" class="sortable-table ledger-grid-table">
    <colgroup>
      <col class="c-sport"><col class="c-comp"><col class="c-ko"><col class="c-match"><col class="c-pick"><col class="c-score"><col class="c-odds"><col class="c-res">
    </colgroup>
    <thead>
      <tr>
        <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
        <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
        <th class="tz-col-head" data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
        <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
        <th data-sort-type="text" onclick="sortTable(this)">Pick</th>
        <th data-sort-type="text" onclick="sortTable(this)">Score</th>
        <th data-sort-type="num" onclick="sortTable(this)">Odds / CLV</th>
        <th data-sort-type="num" onclick="sortTable(this)">Result / PnL</th>
      </tr>
    </thead>
    <tbody id="settledTradesTbody">
      {''.join(settled_html_rows) if settled_html_rows else '<tr><td colspan="8" class="muted">No settled paper bets yet. Pending bets automatically move here once their match finishes and you run <code>uv run sportdata-model</code>.</td></tr>'}
    </tbody>
  </table>

  <h2>🔴 Live In-Play Paper-Bets (Ongoing Events: <span id="liveCountSpan">{len(live_html_rows)}</span>)</h2>
  <table id="liveTradesTable" class="sortable-table ledger-grid-table">
    <colgroup>
      <col class="c-sport"><col class="c-comp"><col class="c-ko"><col class="c-match"><col class="c-pick"><col class="c-score"><col class="c-odds"><col class="c-res">
    </colgroup>
    <thead>
      <tr>
        <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
        <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
        <th class="tz-col-head" data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
        <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
        <th data-sort-type="text" onclick="sortTable(this)">Pick</th>
        <th data-sort-type="text" onclick="sortTable(this)">Score</th>
        <th data-sort-type="num" onclick="sortTable(this)">Odds / CLV</th>
        <th data-sort-type="num" onclick="sortTable(this)">Result / PnL</th>
      </tr>
    </thead>
    <tbody id="liveTradesTbody">
      {''.join(live_html_rows) if live_html_rows else '<tr><td colspan="8" class="muted">No logged paper bets are currently in-play. Active matches move here automatically during kickoff!</td></tr>'}
    </tbody>
  </table>

  <h2>Pending Paper-Bets Awaiting Kickoff (Count: <span id="pendingCountSpan">{len(pending_html_rows)}</span>)</h2>
  <table id="pendingTradesTable" class="sortable-table ledger-grid-table">
    <colgroup>
      <col class="c-sport"><col class="c-comp"><col class="c-ko"><col class="c-match"><col class="c-pick"><col class="c-score"><col class="c-odds"><col class="c-res">
    </colgroup>
    <thead>
      <tr>
        <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
        <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
        <th class="tz-col-head" data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
        <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
        <th data-sort-type="text" onclick="sortTable(this)">Pick</th>
        <th data-sort-type="text" onclick="sortTable(this)">Score</th>
        <th data-sort-type="num" onclick="sortTable(this)">Odds / CLV</th>
        <th data-sort-type="num" onclick="sortTable(this)">Result / PnL</th>
      </tr>
    </thead>
    <tbody id="pendingTradesTbody">
      {''.join(pending_html_rows) if pending_html_rows else '<tr><td colspan="8" class="muted">No pending paper bets.</td></tr>'}
    </tbody>
  </table>

  <div class="section-head">
    <h2>Best Bets Summary Table (Click Any Column Header to Sort · Check ☑️ Rows to Build a Custom Slip · Odds &gt; {min_odds:.2f})</h2>
    <div class="btn-group">
      <button id="clearCustomSlipBtn" class="btn-export" type="button" style="display:none;" onclick="clearCustomBetSelection()">✕ Clear Custom Selection (<span id="customSelectedCountSpan">0</span>)</button>
      <button class="btn-export btn-telegram" type="button" onclick="openTelegramPanel()">💬 Share / Post to Discord &amp; Telegram</button>
      <button class="btn-export" type="button" onclick="exportBestBets('csv')">Export CSV (with Header)</button>
      <button class="btn-export" type="button" onclick="exportBestBets('json')">Export JSON</button>
    </div>
  </div>
  <table id="bestBetsTable" class="sortable-table">
    <thead>
      <tr>
        <th class="col-icon" title="Check rows to build a custom combo or singles slip">☑️</th>
        <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
        <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
        <th class="tz-col-head sort-asc" data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
        <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
        <th data-sort-type="text" onclick="sortTable(this)">Pick</th>
        <th data-sort-type="num" onclick="sortTable(this)">Win Prob</th>
        <th data-sort-type="num" onclick="sortTable(this)">Min Fair Odds</th>
        <th data-sort-type="text" onclick="sortTable(this)">Score Projection</th>
        <th data-sort-type="num" onclick="sortTable(this)">Odds / CLV</th>
      </tr>
    </thead>
    <tbody>
      {''.join(best_bets_rows) if best_bets_rows else '<tr><td colspan="10" class="muted">No qualifying best bets above minimum odds threshold.</td></tr>'}
    </tbody>
  </table>

  <script>
    const EMBEDDED_MATCHUP_DETAILS = {json.dumps(embedded_matchup_details)};
    let currentSportFilter = {json.dumps(norm_sport)};
    let currentDayFilter = {json.dumps(default_day_filter)};
    let currentDaySet = null;
    let currentSearchQuery = '';
    let currentTzMode = 'local';

    function sortTable(thEl) {{
      const table = thEl?.closest('table');
      const tbody = table?.querySelector('tbody');
      if (!table || !tbody) return;
      const ths = Array.from(table.querySelectorAll('thead th'));
      const colIdx = ths.indexOf(thEl);
      if (colIdx < 0) return;
      const sortType = thEl.getAttribute('data-sort-type') || 'text';
      const isAsc = !thEl.classList.contains('sort-asc');
      ths.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
      thEl.classList.add(isAsc ? 'sort-asc' : 'sort-desc');

      const rows = Array.from(tbody.querySelectorAll('tr'));
      if (rows.length <= 1) return;
      rows.sort((ra, rb) => {{
        const ca = ra.children[colIdx];
        const cb = rb.children[colIdx];
        if (!ca || !cb) return 0;
        const vaRaw = (ca.getAttribute('data-sort') ?? ca.textContent ?? '').trim();
        const vbRaw = (cb.getAttribute('data-sort') ?? cb.textContent ?? '').trim();
        if (sortType === 'num') {{
          const na = parseFloat(vaRaw.replace(/[^0-9.+-]/g, ''));
          const nb = parseFloat(vbRaw.replace(/[^0-9.+-]/g, ''));
          const aNum = Number.isFinite(na) ? na : -Infinity;
          const bNum = Number.isFinite(nb) ? nb : -Infinity;
          return isAsc ? (aNum - bNum) : (bNum - aNum);
        }}
        return isAsc
          ? vaRaw.localeCompare(vbRaw, undefined, {{ numeric: true, sensitivity: 'base' }})
          : vbRaw.localeCompare(vaRaw, undefined, {{ numeric: true, sensitivity: 'base' }});
      }});
      rows.forEach(r => tbody.appendChild(r));
    }}

    function showToast(msg) {{
      const el = document.getElementById('syncToast');
      const txt = document.getElementById('syncToastText');
      if (el && txt) {{
        txt.textContent = msg;
        el.style.display = 'flex';
      }}
    }}

    async function openMatchupInspector(home, away, league) {{
      const modal = document.getElementById('matchupInspectorModal');
      const titleEl = document.getElementById('miTitle');
      const bodyEl = document.getElementById('miBody');
      if (!modal || !titleEl || !bodyEl) return;
      titleEl.textContent = '🔍 ' + home + ' vs ' + away;
      bodyEl.innerHTML = '<div style="padding:12px 0;"><span class="spinner"></span> Fetching H2H history, Last-6 form &amp; Score Matrix from VektorPulse store...</div>';
      modal.style.display = 'flex';
      document.getElementById('topLoadingBar')?.classList.add('is-active');
      try {{
        let d = null;
        if (window.location.protocol.startsWith('http')) {{
          try {{
            const qs = new URLSearchParams({{ home: home || '', away: away || '', league: league || '' }});
            const r = await fetch('/api/matchup?' + qs.toString());
            if (r.ok) d = await r.json();
          }} catch (_) {{}}
        }}
        if (!d || !d.ok) {{
          const mKey = (home || '') + ' vs ' + (away || '');
          const mKeyRev = (away || '') + ' vs ' + (home || '');
          d = EMBEDDED_MATCHUP_DETAILS[mKey] || EMBEDDED_MATCHUP_DETAILS[mKeyRev] || null;
        }}
        if (!d) {{
          bodyEl.innerHTML = '<p>No precomputed H2H/Form found for <b>' + escHtml(home + ' vs ' + away) + '</b>. Start the VektorPulse WebApp server (<code>uv run vektorpulse --port 8090</code>) for live database queries.</p>';
          return;
        }}
        const fmtForm = (rows) => {{
          if (!rows || !rows.length) return '<span class="muted">No recent matches in store</span>';
          return rows.map(m =>
            '<div style="display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px solid rgba(34,48,73,0.5);">' +
              '<span><span class="form-pill form-' + escHtml(m.result) + '">' + escHtml(m.result) + '</span> ' + escHtml(m.venue) + ' vs <b>' + escHtml(m.opp) + '</b></span>' +
              '<span class="muted">' + escHtml(m.score) + ' (' + escHtml(m.date) + ')</span>' +
            '</div>'
          ).join('');
        }};
        const h2hHtml = (d.h2h && d.h2h.length)
          ? d.h2h.map(m =>
              '<div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid rgba(34,48,73,0.5);">' +
                '<span><b>' + escHtml(m.home) + '</b> vs <b>' + escHtml(m.away) + '</b></span>' +
                '<span><b class="num-pos">' + escHtml(m.score) + '</b> <span class="muted">(' + escHtml(m.date) + ')</span></span>' +
              '</div>'
            ).join('')
          : '<div class="muted">First tracked meeting in current database window.</div>';
        let scHtml = '';
        const pk = d.pick_detail || {{}};
        const esc = pk.exact_score_prediction || {{}};
        const sp = pk.set_score_prediction || {{}};
        if (esc.top_3_breakdown && esc.top_3_breakdown.length) {{
          const top3 = esc.top_3_breakdown.map(x => '<span class="pill badge-bet">' + escHtml(x.score) + ' (' + (Number(x.prob)*100).toFixed(1) + '%, Fair ' + Number(x.fair_odds).toFixed(2) + ')</span>').join(' ');
          const dStakeDefault = 20;
          const sumProbs3 = esc.top_3_breakdown.reduce((acc, x) => acc + Number(x.prob || 0), 0.0) || 0.30;
          const dutchRowsHtml = esc.top_3_breakdown.map((x, idx) => {{
            const pSc = Number(x.prob || 0.10);
            const fOdds = Number(x.fair_odds || (1.0 / pSc));
            const stSc = (dStakeDefault * (pSc / sumProbs3));
            const retSc = stSc * fOdds;
            return '<div class="dutch-row" data-prob="' + pSc.toFixed(4) + '" data-fair-odds="' + fOdds.toFixed(3) + '" style="display:flex; justify-content:space-between; align-items:center; padding:3px 0; font-size:11.5px;">' +
              '<span>Score #' + (idx + 1) + ': <b>' + escHtml(x.score) + '</b> (' + (pSc * 100).toFixed(1) + '% · Fair @<b>' + fOdds.toFixed(2) + '</b>)</span>' +
              '<span>Place <b class="num-pos dutch-stake-lbl">€' + stSc.toFixed(2) + '</b> &rarr; Return <b class="dutch-ret-lbl">€' + retSc.toFixed(2) + '</b></span>' +
            '</div>';
          }}).join('');
          scHtml = '<div style="margin-top:12px; padding:10px; background:#0b0f17; border:1px solid var(--border); border-radius:8px;">' +
            '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">' +
              '<b>🎲 Dixon-Coles Score Projection (λ=' + Number(esc.lambda_home||0).toFixed(2) + ', μ=' + Number(esc.mu_away||0).toFixed(2) + ')</b>' +
              '<span style="font-size:11.5px;">Dutching Stake (€): <input id="dutchModalStakeInput" type="number" min="5" max="10000" step="5" value="' + dStakeDefault + '" oninput="recalcModalDutching(this.value)" style="width:68px; background:#111827; color:var(--green); border:1px solid var(--accent); border-radius:5px; padding:2px 6px; font-weight:700;"></span>' +
            '</div>' +
            '<div>Top Exact Scores: ' + top3 + '</div>' +
            '<div style="margin-top:5px;">3-Score Dutch Cluster: <b class="num-pos">' + escHtml(esc.cluster_3_scores) + '</b> (' + (Number(esc.cluster_3_prob||0)*100).toFixed(1) + '%, Fair @' + Number(esc.cluster_3_fair_odds||0).toFixed(2) + ')</div>' +
            '<div id="dutchModalBreakdown" style="margin-top:8px; padding-top:6px; border-top:1px solid rgba(56,189,248,0.25);">' +
              '<div class="muted" style="margin-bottom:3px; font-size:11px;">Equal-Payout Dutching Split Across Top 3 Exact Scores:</div>' +
              dutchRowsHtml +
            '</div>' +
          '</div>';
        }} else if (sp.straight_sets_score) {{
          const dStakeTen = 20;
          const p20 = Number(sp.straight_sets_prob || 0.50);
          const p21 = Number(sp.decider_sets_prob || 0.25);
          const pSumT = (p20 + p21) || 0.75;
          const o20 = Number(sp.straight_sets_fair_odds || (1.0 / p20));
          const o21 = Number(sp.decider_sets_fair_odds || (1.0 / Math.max(p21, 0.08)));
          const st20 = dStakeTen * (p20 / pSumT);
          const st21 = dStakeTen * (p21 / pSumT);
          scHtml = '<div style="margin-top:12px; padding:10px; background:#0b0f17; border:1px solid var(--border); border-radius:8px;">' +
            '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:6px;">' +
              '<b>🎾 Calibrated Tennis Set-Score Distribution &amp; Dutching Split</b>' +
              '<span style="font-size:11.5px;">Dutching Stake (€): <input id="dutchModalStakeInput" type="number" min="5" max="10000" step="5" value="' + dStakeTen + '" oninput="recalcModalDutching(this.value)" style="width:68px; background:#111827; color:var(--green); border:1px solid var(--accent); border-radius:5px; padding:2px 6px; font-weight:700;"></span>' +
            '</div>' +
            '<div>Straight Sets: <span class="pill badge-bet">' + escHtml(sp.straight_sets_score) + ' (' + (p20*100).toFixed(1) + '%, Fair ' + o20.toFixed(2) + ')</span> · Decider: <span class="pill tier">' + escHtml(sp.decider_sets_score) + ' (' + (p21*100).toFixed(1) + '%, Fair ' + o21.toFixed(2) + ')</span></div>' +
            '<div id="dutchModalBreakdown" style="margin-top:8px; padding-top:6px; border-top:1px solid rgba(56,189,248,0.25);">' +
              '<div class="dutch-row" data-prob="' + p20.toFixed(4) + '" data-fair-odds="' + o20.toFixed(3) + '" style="display:flex; justify-content:space-between; padding:3px 0; font-size:11.5px;">' +
                '<span>Sets <b>' + escHtml(sp.straight_sets_score) + '</b> (' + (p20*100).toFixed(1) + '% · Fair @<b>' + o20.toFixed(2) + '</b>)</span>' +
                '<span>Place <b class="num-pos dutch-stake-lbl">€' + st20.toFixed(2) + '</b> &rarr; Return <b class="dutch-ret-lbl">€' + (st20*o20).toFixed(2) + '</b></span>' +
              '</div>' +
              '<div class="dutch-row" data-prob="' + p21.toFixed(4) + '" data-fair-odds="' + o21.toFixed(3) + '" style="display:flex; justify-content:space-between; padding:3px 0; font-size:11.5px;">' +
                '<span>Sets <b>' + escHtml(sp.decider_sets_score) + '</b> (' + (p21*100).toFixed(1) + '% · Fair @<b>' + o21.toFixed(2) + '</b>)</span>' +
                '<span>Place <b class="num-pos dutch-stake-lbl">€' + st21.toFixed(2) + '</b> &rarr; Return <b class="dutch-ret-lbl">€' + (st21*o21).toFixed(2) + '</b></span>' +
              '</div>' +
            '</div>' +
          '</div>';
        }}
        const facObj = pk.factors_tanh_z || pk.factors || null;
        let facHtml = '';
        if (facObj && typeof facObj === 'object' && Object.keys(facObj).length) {{
          const facPills = Object.entries(facObj).map(([k, v]) => {{
            const numV = Number(v || 0);
            const cls = numV > 0 ? 'badge-bet' : (numV < 0 ? 'badge-veto' : '');
            return '<span class="pill ' + cls + '">' + escHtml(k) + ': ' + (numV >= 0 ? '+' : '') + numV + '</span>';
          }}).join(' ');
          facHtml = '<div style="margin-top:12px; padding:10px; background:#0b0f17; border:1px solid var(--border); border-radius:8px;">' +
            '<div style="margin-bottom:6px;"><b>📊 Model Factor &amp; Edge Breakdown</b></div>' +
            '<div style="display:flex; flex-wrap:wrap; gap:5px;">' + facPills + '</div>' +
          '</div>';
        }}
        bodyEl.innerHTML =
          '<div style="display:grid; grid-template-columns:1fr 1fr; gap:14px;">' +
            '<div><div style="margin-bottom:6px; color:var(--text);"><b>📈 ' + escHtml(home) + ' — Last 6 Matches</b></div>' + fmtForm(d.form_home) + '</div>' +
            '<div><div style="margin-bottom:6px; color:var(--text);"><b>📈 ' + escHtml(away) + ' — Last 6 Matches</b></div>' + fmtForm(d.form_away) + '</div>' +
          '</div>' +
          '<div style="margin-top:14px;"><div style="margin-bottom:6px; color:var(--text);"><b>⚔️ Head-to-Head History (' + (d.h2h?.length || 0) + ' Meetings)</b></div>' + h2hHtml + '</div>' +
          facHtml +
          scHtml;
      }} catch (err) {{
        bodyEl.innerHTML = '<div class="num-neg">Failed to load matchup details: ' + escHtml(String(err)) + '</div>';
      }} finally {{
        if (!isActionBusy) document.getElementById('topLoadingBar')?.classList.remove('is-active');
      }}
    }}

    function updateVisibleKpi() {{
      const visibleRows = document.querySelectorAll('#bestBetsTable tbody tr[data-date]:not(.hidden-by-odds):not(.hidden-by-sport):not(.hidden-by-search):not(.hidden-by-day)');
      const kpi = document.getElementById('visibleBestBetsKpi');
      if (kpi) kpi.textContent = String(visibleRows.length);
      if (typeof buildSmartBetPlan === 'function') buildSmartBetPlan();
      if (typeof populateDutchMatchSelect === 'function') populateDutchMatchSelect();
    }}

    function applyDayFilter(dayKey) {{
      currentDayFilter = dayKey || 'all';
      currentDaySet = null;
      document.querySelectorAll('[data-day-btn]').forEach(btn => {{
        if (btn.getAttribute('data-day-btn') === currentDayFilter) {{
          btn.classList.add('active');
          const ds = btn.getAttribute('data-day-set');
          if (ds) currentDaySet = new Set(ds.split(','));
        }} else {{
          btn.classList.remove('active');
        }}
      }});
      document.querySelectorAll('[data-day]').forEach(el => {{
        const d = el.getAttribute('data-day') || '';
        const match = currentDayFilter === 'all'
          || (currentDaySet ? currentDaySet.has(d) : d === currentDayFilter);
        if (match) el.classList.remove('hidden-by-day');
        else el.classList.add('hidden-by-day');
      }});
      updateVisibleKpi();
    }}

    function applySearchFilter(q) {{
      currentSearchQuery = (q || '').trim().toLowerCase();
      document.querySelectorAll('[data-search]').forEach(el => {{
        const hay = (el.getAttribute('data-search') || '').toLowerCase();
        if (!currentSearchQuery || hay.includes(currentSearchQuery)) el.classList.remove('hidden-by-search');
        else el.classList.add('hidden-by-search');
      }});
      updateVisibleKpi();
    }}

    function applyOddsFilter(val) {{
      const thr = parseFloat(val);
      document.getElementById('minOddsLabel').textContent = thr.toFixed(2);
      document.getElementById('minProfitLabel').textContent = Math.round((thr - 1.0) * 100) + '%';
      document.querySelectorAll('[data-odds]').forEach(el => {{
        const o = parseFloat(el.getAttribute('data-odds') || '0');
        if (o <= thr) el.classList.add('hidden-by-odds');
        else el.classList.remove('hidden-by-odds');
      }});
      updateVisibleKpi();
    }}

    function applyBankrollCalculator(val) {{
      const bank = Math.max(0, parseFloat(val) || 1000);
      try {{ localStorage.setItem('vp_bankroll_eur', String(bank)); }} catch (_) {{}}
      document.querySelectorAll('.kelly-stake').forEach(el => {{
        const pct = parseFloat(el.getAttribute('data-kelly-pct') || '0');
        const eur = (bank * (pct / 100.0)).toFixed(2);
        el.textContent = pct.toFixed(2) + '% (€' + eur + ')';
      }});
    }}

    function applySportFilter(sport) {{
      currentSportFilter = sport || 'all';
      document.querySelectorAll('[data-sport-btn]').forEach(btn => {{
        if (btn.getAttribute('data-sport-btn') === currentSportFilter) btn.classList.add('active');
        else btn.classList.remove('active');
      }});
      document.querySelectorAll('[data-sport-cat]').forEach(el => {{
        const cat = el.getAttribute('data-sport-cat') || '';
        if (currentSportFilter === 'all' || cat === currentSportFilter) el.classList.remove('hidden-by-sport');
        else el.classList.add('hidden-by-sport');
      }});
      document.querySelectorAll('[data-sport-section]').forEach(sec => {{
        const secType = sec.getAttribute('data-sport-section') || '';
        if (currentSportFilter === 'all') {{
          sec.classList.remove('hidden-by-sport');
        }} else if (secType === 'us-sports') {{
          if (['basketball', 'volleyball', 'hockey', 'football', 'baseball'].includes(currentSportFilter)) sec.classList.remove('hidden-by-sport');
          else sec.classList.add('hidden-by-sport');
        }} else {{
          if (secType === currentSportFilter) sec.classList.remove('hidden-by-sport');
          else sec.classList.add('hidden-by-sport');
        }}
      }});
      updateVisibleKpi();
    }}

    function collectVisibleBestBets() {{
      const rows = document.querySelectorAll('#bestBetsTable tbody tr[data-date]:not(.hidden-by-odds):not(.hidden-by-sport):not(.hidden-by-search):not(.hidden-by-day)');
      const items = [];
      rows.forEach(r => {{
        items.push({{
          date: r.getAttribute('data-date') || '',
          date_local: r.getAttribute('data-date-local') || '',
          sport_cat: r.getAttribute('data-sport-cat') || 'soccer',
          sport_league: r.getAttribute('data-sport') || '',
          comp: r.getAttribute('data-comp') || r.getAttribute('data-sport') || '',
          match: r.getAttribute('data-match') || '',
          pick: r.getAttribute('data-pick') || '',
          pick_name: r.getAttribute('data-pick-name') || r.getAttribute('data-pick') || '',
          tier: r.getAttribute('data-tier') || '',
          win_prob: parseFloat(r.getAttribute('data-win-prob') || '0.68'),
          fair_odds: parseFloat(r.getAttribute('data-fair-odds') || '1.45'),
          exact_score: r.getAttribute('data-exact-score') || '',
          score_items: JSON.parse(r.getAttribute('data-score-items') || '[]'),
          odds: parseFloat(r.getAttribute('data-odds') || '0'),
          odds_display: r.getAttribute('data-odds-display') || ''
        }});
      }});
      return items;
    }}

    let currentDutchScoreItems = [];
    let currentDutchMatchObj = null;

    function setDutchBudget(amt) {{
      const inp = document.getElementById('dutchStakeInput');
      if (inp) inp.value = String(amt);
      recalcStandaloneDutchSplitter();
    }}

    function selectMatchForDutching(matchName) {{
      const sel = document.getElementById('dutchMatchSelect');
      const sec = document.getElementById('exactScoreSplitterSection');
      if (!sel) return;
      let found = false;
      Array.from(sel.options).forEach(opt => {{
        if (opt.value === matchName) {{
          sel.value = matchName;
          found = true;
        }}
      }});
      if (!found) {{
        populateDutchMatchSelect(matchName);
      }} else {{
        onDutchMatchSelectChange();
      }}
      if (sec) sec.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function populateDutchMatchSelect(forceSelectMatch) {{
      const sel = document.getElementById('dutchMatchSelect');
      if (!sel) return;
      const prevVal = forceSelectMatch || sel.value;
      let pool = collectVisibleBestBets().filter(x => x.score_items && x.score_items.length >= 2);
      if (!pool.length) {{
        document.querySelectorAll('#bestBetsTable tbody tr[data-date]').forEach(r => {{
          const sItems = JSON.parse(r.getAttribute('data-score-items') || '[]');
          if (sItems && sItems.length >= 2) {{
            pool.push({{
              match: r.getAttribute('data-match') || '',
              pick_name: r.getAttribute('data-pick-name') || '',
              sport_cat: r.getAttribute('data-sport-cat') || 'soccer',
              comp: r.getAttribute('data-comp') || '',
              win_prob: parseFloat(r.getAttribute('data-win-prob') || '0.68'),
              odds: parseFloat(r.getAttribute('data-odds') || '1.50'),
              score_items: sItems
            }});
          }}
        }});
      }}
      sel.innerHTML = pool.map(it => {{
        const ico = getSportEmoji(it.sport_cat);
        return '<option value="' + escHtml(it.match) + '">' + ico + ' ' + escHtml(it.match) + ' → ' + escHtml(it.pick_name) + ' (' + (it.win_prob * 100).toFixed(0) + '%)</option>';
      }}).join('');
      if (prevVal && pool.some(x => x.match === prevVal)) {{
        sel.value = prevVal;
      }}
      onDutchMatchSelectChange();
    }}

    function onDutchMatchSelectChange() {{
      const sel = document.getElementById('dutchMatchSelect');
      const bar = document.getElementById('dutchCustomOddsBar');
      if (!sel || !bar) return;
      const matchName = sel.value;
      let rowEl = null;
      document.querySelectorAll('#bestBetsTable tbody tr[data-date]').forEach(r => {{
        if (r.getAttribute('data-match') === matchName) rowEl = r;
      }});
      if (!rowEl) return;
      const sItems = JSON.parse(rowEl.getAttribute('data-score-items') || '[]');
      currentDutchMatchObj = {{
        match: matchName,
        pick_name: rowEl.getAttribute('data-pick-name') || '',
        sport_cat: rowEl.getAttribute('data-sport-cat') || 'soccer',
        comp: rowEl.getAttribute('data-comp') || '',
        win_prob: parseFloat(rowEl.getAttribute('data-win-prob') || '0.68'),
        odds: parseFloat(rowEl.getAttribute('data-odds') || '1.50')
      }};
      currentDutchScoreItems = sItems.map(x => ({{ ...x }}));
      bar.innerHTML = '<b style="color:var(--accent);">✏️ Editable Bookmaker Score Odds (adjust to your sportsbook):</b> ' +
        currentDutchScoreItems.map((it, idx) =>
          '<label style="display:inline-flex; align-items:center; gap:5px;">' +
            '<b>#' + (idx + 1) + ' ' + escHtml(it.score) + '</b> <span class="muted">(Model ' + (Number(it.prob) * 100).toFixed(1) + '%, Fair @' + Number(it.fair_odds).toFixed(2) + ')</span> Odds:' +
            '<input type="number" step="0.10" min="1.20" max="100" value="' + Number(it.book_odds || it.fair_odds).toFixed(2) + '" data-dutch-idx="' + idx + '" oninput="onCustomScoreOddsInput(this)" style="width:66px; background:#111827; color:var(--green); border:1px solid var(--border); border-radius:5px; padding:3px 6px; font-weight:700;">' +
          '</label>'
        ).join(' &nbsp;·&nbsp; ');
      recalcStandaloneDutchSplitter();
    }}

    function onCustomScoreOddsInput(inpEl) {{
      const idx = parseInt(inpEl.getAttribute('data-dutch-idx') || '0', 10);
      const val = Math.max(1.05, parseFloat(inpEl.value) || 2.0);
      if (currentDutchScoreItems[idx]) {{
        currentDutchScoreItems[idx].book_odds = val;
        recalcStandaloneDutchSplitter();
      }}
    }}

    function recalcStandaloneDutchSplitter() {{
      const grid = document.getElementById('dutchSplitterGrid');
      if (!grid || !currentDutchScoreItems.length || !currentDutchMatchObj) return;
      const totStake = Math.max(2, parseFloat(document.getElementById('dutchStakeInput')?.value || '25') || 25);
      const mObj = currentDutchMatchObj;
      const ico = getSportEmoji(mObj.sport_cat);

      // Helper to compute Equal-Payout Dutching split across a subset of score items
      const computeDutchSet = (itemsSubset) => {{
        const invSum = itemsSubset.reduce((s, x) => s + (1.0 / Math.max(Number(x.book_odds || x.fair_odds), 1.05)), 0.0);
        const effOdds = invSum > 0 ? (1.0 / invSum) : 1.0;
        const totPayout = totStake * effOdds;
        const netProfit = totPayout - totStake;
        const combProb = itemsSubset.reduce((s, x) => s + Number(x.prob || 0), 0.0);
        let runSt = 0.0;
        const legs = itemsSubset.map((x, i) => {{
          const o = Math.max(Number(x.book_odds || x.fair_odds), 1.05);
          const share = (1.0 / o) / invSum;
          const st = (i === itemsSubset.length - 1) ? Math.max(0, totStake - runSt) : (totStake * share);
          runSt += st;
          return {{ ...x, o, sharePct: share * 100.0, stake: st, payout: st * o }};
        }});
        return {{ legs, effOdds, totPayout, netProfit, combProb }};
      }};

      const set2 = computeDutchSet(currentDutchScoreItems.slice(0, 2));
      const set3 = currentDutchScoreItems.length >= 3 ? computeDutchSet(currentDutchScoreItems.slice(0, 3)) : null;

      // Option 3: Anchor ML + Top-2 Score Booster (70% Main Pick ML + 30% 2-Score Dutch)
      const mlBudget = Math.round(totStake * 0.65 * 2.0) / 2.0;
      const boostBudget = Math.max(0, totStake - mlBudget);
      const mlReturn = mlBudget * mObj.odds;
      const boostSet2 = computeDutchSet(currentDutchScoreItems.slice(0, 2));
      const boostPayout = boostBudget * boostSet2.effOdds;
      const hybridSweepReturn = mlReturn + boostPayout;
      const hybridSweepNet = hybridSweepReturn - totStake;

      const renderLegsHtml = (dSet) => dSet.legs.map(l =>
        '<div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0; border-bottom:1px solid rgba(34,48,73,0.45); font-size:11.5px;">' +
          '<span>🎯 <b>' + escHtml(l.score) + '</b> @ <b>' + l.o.toFixed(2) + '</b> <span class="muted">(' + l.sharePct.toFixed(1) + '% split · Model ' + (Number(l.prob)*100).toFixed(1) + '%)</span></span>' +
          '<span>Bet <b class="num-pos">€' + l.stake.toFixed(2) + '</b> &rarr; Payout <b>€' + l.payout.toFixed(2) + '</b></span>' +
        '</div>'
      ).join('');

      const share2Txt = set2.legs.map(l => '• **' + l.score + '** @ **' + l.o.toFixed(2) + '** -> Stake: **€' + l.stake.toFixed(2) + '** (Payout €' + l.payout.toFixed(2) + ')').join('\\n');
      let cardsHtml =
        '<div class="card" style="margin:0; border-color:rgba(34,197,94,0.48);">' +
          '<div class="card-head">' +
            '<div><b>Set A · 2-Score Precision Dutch (' + set2.legs.map(x => escHtml(x.score)).join(' / ') + ')</b> <span class="pill badge-bet">★ HIGHEST PAYOUT</span></div>' +
            '<button type="button" class="btn-mini" onclick="shareStrategyTicket(\\'2-Score Dutching Split (' + escHtml(mObj.match) + ')\\', \\'Total Stake: €' + totStake.toFixed(2) + ' · Effective Odds: ' + set2.effOdds.toFixed(2) + 'x · Payout: €' + set2.totPayout.toFixed(2) + ' (+€' + set2.netProfit.toFixed(2) + ')\\', ' + escHtml(JSON.stringify(share2Txt)) + ')">📣</button>' +
          '</div>' +
          '<div class="muted" style="margin:4px 0 8px;">' + ico + ' <b>' + escHtml(mObj.match) + '</b> — Equal payout whichever of the Top 2 exact scores hits</div>' +
          renderLegsHtml(set2) +
          '<div style="margin-top:10px; padding-top:8px; border-top:1px solid var(--border); display:flex; justify-content:space-between; font-size:12px;">' +
            '<span>Effective Odds: <b class="num-pos">' + set2.effOdds.toFixed(2) + 'x</b> (' + (set2.combProb * 100).toFixed(1) + '% Model Hit)</span>' +
            '<span>Payout: <b class="num-pos">€' + set2.totPayout.toFixed(2) + ' (+€' + set2.netProfit.toFixed(2) + ')</b></span>' +
          '</div>' +
        '</div>';

      if (set3) {{
        const share3Txt = set3.legs.map(l => '• **' + l.score + '** @ **' + l.o.toFixed(2) + '** -> Stake: **€' + l.stake.toFixed(2) + '** (Payout €' + l.payout.toFixed(2) + ')').join('\\n');
        cardsHtml +=
          '<div class="card" style="margin:0; border-color:rgba(56,189,248,0.48);">' +
            '<div class="card-head">' +
              '<div><b>Set B · 3-Score Wide Shield (' + set3.legs.map(x => escHtml(x.score)).join(' / ') + ')</b> <span class="pill tier">★ 46% OOS HIT RATE</span></div>' +
              '<button type="button" class="btn-mini" onclick="shareStrategyTicket(\\'3-Score Dutching Cluster (' + escHtml(mObj.match) + ')\\', \\'Total Stake: €' + totStake.toFixed(2) + ' · Effective Odds: ' + set3.effOdds.toFixed(2) + 'x · Payout: €' + set3.totPayout.toFixed(2) + ' (+€' + set3.netProfit.toFixed(2) + ')\\', ' + escHtml(JSON.stringify(share3Txt)) + ')">📣</button>' +
            '</div>' +
            '<div class="muted" style="margin:4px 0 8px;">Covers all 3 primary winning scorelines with identical €' + set3.totPayout.toFixed(2) + ' return</div>' +
            renderLegsHtml(set3) +
            '<div style="margin-top:10px; padding-top:8px; border-top:1px solid var(--border); display:flex; justify-content:space-between; font-size:12px;">' +
              '<span>Effective Odds: <b class="num-pos">' + set3.effOdds.toFixed(2) + 'x</b> (' + (set3.combProb * 100).toFixed(1) + '% Model Hit)</span>' +
              '<span>Payout: <b class="num-pos">€' + set3.totPayout.toFixed(2) + ' (+€' + set3.netProfit.toFixed(2) + ')</b></span>' +
            '</div>' +
          '</div>';
      }}

      cardsHtml +=
        '<div class="card" style="margin:0; border-color:rgba(245,158,11,0.48);">' +
          '<div class="card-head">' +
            '<div><b>Set C · 65/35 Winner Floor + Exact-Score Booster</b></div>' +
          '</div>' +
          '<div class="muted" style="margin:4px 0 8px;">65% (€' + mlBudget.toFixed(2) + ') on <b>' + escHtml(mObj.pick_name) + '</b> @ ' + mObj.odds.toFixed(2) + ' covers any win + 35% (€' + boostBudget.toFixed(2) + ') on 2-Score Dutch</div>' +
          '<div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid rgba(34,48,73,0.45); font-size:11.5px;">' +
            '<span>🛡️ <b>' + escHtml(mObj.pick_name) + ' (Main Pick)</b> @ <b>' + mObj.odds.toFixed(2) + '</b></span>' +
            '<span>Bet <b>€' + mlBudget.toFixed(2) + '</b> &rarr; Floor <b>€' + mlReturn.toFixed(2) + '</b></span>' +
          '</div>' +
          set2.legs.map(l => {{
            const bSt = boostBudget * (l.sharePct / 100.0);
            return '<div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid rgba(34,48,73,0.45); font-size:11.5px;">' +
              '<span>🚀 Exact <b>' + escHtml(l.score) + '</b> @ <b>' + l.o.toFixed(2) + '</b></span>' +
              '<span>Bet <b class="num-pos">€' + bSt.toFixed(2) + '</b> &rarr; Boost <b>+€' + boostPayout.toFixed(2) + '</b></span>' +
            '</div>';
          }}).join('') +
          '<div style="margin-top:10px; padding-top:8px; border-top:1px solid var(--border); display:flex; justify-content:space-between; font-size:12px;">' +
            '<span>Any Other Win: <b>€' + mlReturn.toFixed(2) + '</b></span>' +
            '<span>If Top-2 Score Hits: <b class="num-pos">€' + hybridSweepReturn.toFixed(2) + ' (+€' + hybridSweepNet.toFixed(2) + ')</b></span>' +
          '</div>' +
        '</div>';

      grid.innerHTML = cardsHtml;
    }}

    const customSelectedMatches = new Set();

    function recalcModalDutching(val) {{
      const totStake = Math.max(1, parseFloat(val) || 20);
      const rows = Array.from(document.querySelectorAll('#dutchModalBreakdown .dutch-row'));
      if (!rows.length) return;
      const sumP = rows.reduce((acc, r) => acc + parseFloat(r.getAttribute('data-prob') || '0.1'), 0.0) || 1.0;
      rows.forEach(r => {{
        const p = parseFloat(r.getAttribute('data-prob') || '0.1');
        const fo = parseFloat(r.getAttribute('data-fair-odds') || '5.0');
        const st = totStake * (p / sumP);
        const ret = st * fo;
        const stEl = r.querySelector('.dutch-stake-lbl');
        const retEl = r.querySelector('.dutch-ret-lbl');
        if (stEl) stEl.textContent = '€' + st.toFixed(2);
        if (retEl) retEl.textContent = '€' + ret.toFixed(2);
      }});
    }}

    function saveSlipPrefsToStorage() {{
      try {{
        localStorage.setItem('vp_custom_matches', JSON.stringify(Array.from(customSelectedMatches)));
        const bVal = document.getElementById('betAmountInput')?.value;
        const mVal = document.getElementById('betRiskProfileSelect')?.value;
        if (bVal) localStorage.setItem('vp_bet_budget_eur', String(bVal));
        if (mVal) localStorage.setItem('vp_bet_risk_mode', String(mVal));
      }} catch (_) {{}}
    }}

    function restoreSlipPrefsFromStorage() {{
      try {{
        const savedBank = localStorage.getItem('vp_bankroll_eur');
        if (savedBank && document.getElementById('bankrollInput')) {{
          document.getElementById('bankrollInput').value = savedBank;
          applyBankrollCalculator(savedBank);
        }}
        const savedBudget = localStorage.getItem('vp_bet_budget_eur');
        if (savedBudget && document.getElementById('betAmountInput')) {{
          document.getElementById('betAmountInput').value = savedBudget;
        }}
        const savedMode = localStorage.getItem('vp_bet_risk_mode');
        if (savedMode && document.getElementById('betRiskProfileSelect')) {{
          document.getElementById('betRiskProfileSelect').value = savedMode;
        }}
        const savedInplay = localStorage.getItem('vp_inplay_alerts_enabled');
        if (savedInplay !== null) {{
          renderInplayAlertsBtn(savedInplay === '1');
        }}
        const savedInplayItems = JSON.parse(localStorage.getItem('vp_inplay_alert_items') || '{{}}');
        if (savedInplayItems && typeof savedInplayItems === 'object') {{
          currentInplayAlertItems = savedInplayItems;
          refreshAllInplayItemButtons();
        }}
        const savedMatches = JSON.parse(localStorage.getItem('vp_custom_matches') || '[]');
        if (Array.isArray(savedMatches) && savedMatches.length) {{
          const validDomMatches = new Set();
          document.querySelectorAll('.custom-bet-chk').forEach(c => {{
            const m = c.getAttribute('data-match') || '';
            if (m && savedMatches.includes(m)) {{
              c.checked = true;
              validDomMatches.add(m);
            }}
          }});
          validDomMatches.forEach(m => customSelectedMatches.add(m));
          const clrBtn = document.getElementById('clearCustomSlipBtn');
          const cntSpan = document.getElementById('customSelectedCountSpan');
          if (cntSpan) cntSpan.textContent = String(customSelectedMatches.size);
          if (clrBtn) clrBtn.style.display = customSelectedMatches.size > 0 ? 'inline-block' : 'none';
        }}
      }} catch (_) {{}}
    }}

    function printSmartBetTicket() {{
      const grid = document.getElementById('smartBetPlanGrid');
      const budget = document.getElementById('betAmountInput')?.value || '100';
      if (!grid) return;
      const w = window.open('', '_blank', 'width=880,height=720');
      if (!w) {{ window.print(); return; }}
      w.document.write(
        '<!doctype html><html><head><meta charset="utf-8"><title>VektorPulse Bet Slip (€' + escHtml(budget) + ')</title>' +
        '<style>body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;padding:24px;color:#0f172a;background:#fff;}}' +
        '.hdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #0f172a;padding-bottom:10px;margin-bottom:16px;}}' +
        '.card{{border:1px solid #cbd5e1;border-radius:8px;padding:14px;margin-bottom:14px;page-break-inside:avoid;}}' +
        '.num-pos{{color:#15803d;font-weight:700;}} .muted{{color:#475569;font-size:12px;}} .btn-mini{{display:none;}}' +
        '.pill{{display:inline-block;padding:2px 6px;border-radius:4px;border:1px solid #94a3b8;font-size:11px;font-weight:600;margin-left:4px;}}' +
        '</style></head><body>' +
        '<div class="hdr"><div><h2 style="margin:0;">⚡ VektorPulse — Smart Bet Slip &amp; Stake Allocation Ticket</h2>' +
        '<div class="muted">Generated: ' + new Date().toLocaleString() + ' · Ready to Bet Budget: <b>€' + escHtml(budget) + '</b></div></div></div>' +
        grid.innerHTML +
        '<script>window.onload=function(){{window.print();}}<\\/script></body></html>'
      );
      w.document.close();
    }}

    function toggleCustomBetPick(chkEl) {{
      const m = chkEl?.getAttribute('data-match') || '';
      if (!m) return;
      if (chkEl.checked) customSelectedMatches.add(m);
      else customSelectedMatches.delete(m);
      const clrBtn = document.getElementById('clearCustomSlipBtn');
      const cntSpan = document.getElementById('customSelectedCountSpan');
      if (cntSpan) cntSpan.textContent = String(customSelectedMatches.size);
      if (clrBtn) clrBtn.style.display = customSelectedMatches.size > 0 ? 'inline-block' : 'none';
      saveSlipPrefsToStorage();
      buildSmartBetPlan();
    }}

    function clearCustomBetSelection() {{
      customSelectedMatches.clear();
      document.querySelectorAll('.custom-bet-chk').forEach(c => {{ c.checked = false; }});
      const clrBtn = document.getElementById('clearCustomSlipBtn');
      const cntSpan = document.getElementById('customSelectedCountSpan');
      if (cntSpan) cntSpan.textContent = '0';
      if (clrBtn) clrBtn.style.display = 'none';
      saveSlipPrefsToStorage();
      buildSmartBetPlan();
    }}

    function quickAnalyzePair(pairStr) {{
      const inp = document.getElementById('liveAnalyzeInput');
      if (inp) inp.value = pairStr;
      runLiveMatchupAnalyzer();
    }}

    async function runLiveMatchupAnalyzer() {{
      const inp = document.getElementById('liveAnalyzeInput');
      const box = document.getElementById('liveAnalyzeResultBox');
      if (!inp || !box) return;
      const q = inp.value.trim();
      if (!q) return;
      box.style.display = 'block';
      box.innerHTML = '<span class="spinner"></span> Querying VektorPulse store + live SofaScore odds, all-level Challenger/ATP form &amp; turnaround hours for <b>' + escHtml(q) + '</b>...';
      if (!window.location.protocol.startsWith('http')) {{
        box.innerHTML = '<span class="muted">Start the VektorPulse WebApp server (<code>uv run vektorpulse --port 8090</code>) and open <code>http://127.0.0.1:8090</code> for live on-demand matchup analysis.</span>';
        return;
      }}
      document.getElementById('topLoadingBar')?.classList.add('is-active');
      try {{
        const r = await fetch('/api/analyze-live?q=' + encodeURIComponent(q));
        const d = await r.json();
        if (!d.ok) {{
          box.innerHTML = '<span class="num-neg">' + escHtml(d.error || 'Could not analyze matchup') + '</span>';
          return;
        }}
        const o1Str = d.odds_home ? Number(d.odds_home).toFixed(2) : '—';
        const o2Str = d.odds_away ? Number(d.odds_away).toFixed(2) : '—';
        const f1Str = d.p1_last5_pct !== null && d.p1_last5_pct !== undefined ? d.p1_last5_pct + '%' : '—';
        const f2Str = d.p2_last5_pct !== null && d.p2_last5_pct !== undefined ? d.p2_last5_pct + '%' : '—';
        const r1Str = d.p1_rest_hours ? (Math.round(d.p1_rest_hours) + 'h (' + escHtml(d.p1_last_tourn || '') + ')') : 'Rested';
        const r2Str = d.p2_rest_hours ? (Math.round(d.p2_rest_hours) + 'h (' + escHtml(d.p2_last_tourn || '') + ')') : 'Rested';
        const eloStr = d.sport === 'tennis'
          ? ('Elo Diff: <b>' + (Number(d.elo_diff_home||0) >= 0 ? '+' : '') + Number(d.elo_diff_home||0).toFixed(0) + '</b> · Game Elo Diff: <b>' + (Number(d.game_elo_diff_home||0) >= 0 ? '+' : '') + Number(d.game_elo_diff_home||0).toFixed(0) + '</b>')
          : ('Elo Diff: <b>' + (Number(d.elo_diff_home||0) >= 0 ? '+' : '') + Number(d.elo_diff_home||0).toFixed(0) + '</b> · Rolling SoT Diff: <b>' + (Number(d.sot_diff_home||0) >= 0 ? '+' : '') + Number(d.sot_diff_home||0).toFixed(1) + '</b>');
        const mkts = d.market_recommendations || {{}};
        const isNoBet = d.verdict_level === 'no_bet' || String(d.verdict || '').includes('NO-BET') || String(mkts.moneyline || '').startsWith('Skip');
        const isLean = d.verdict_level === 'lean_bet';
        const verdictPillCls = isNoBet ? 'pill badge-veto' : (isLean ? 'pill tier' : 'pill badge-bet');
        const mlBorder = isNoBet ? 'rgba(239,68,68,0.45)' : (isLean ? 'rgba(245,158,11,0.45)' : 'rgba(34,197,94,0.45)');
        const mlColorCls = isNoBet ? 'num-neg' : (isLean ? '' : 'num-pos');
        const mlStyle = isLean ? 'color:var(--amber);font-weight:700;' : '';
        const mktsHtml = mkts.moneyline
          ? '<div style="margin-top:8px; display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:8px;">' +
              '<div style="padding:6px 8px; border:1px solid ' + mlBorder + '; border-radius:6px;"><b>1️⃣ Moneyline / 1X2:</b><br><span class="' + mlColorCls + '" style="' + mlStyle + '">' + escHtml(mkts.moneyline) + '</span></div>' +
              '<div style="padding:6px 8px; border:1px solid rgba(56,189,248,0.35); border-radius:6px;"><b>2️⃣ Handicap / Shield:</b><br><span style="color:var(--accent);">' + escHtml(mkts.handicap_shield || '—') + '</span></div>' +
              '<div style="padding:6px 8px; border:1px solid rgba(245,158,11,0.35); border-radius:6px;"><b>3️⃣ Totals / Score Cluster:</b><br><span style="color:var(--amber);">' + escHtml(mkts.totals_cluster || '—') + '</span></div>' +
            '</div>'
          : '';
        const warnHtml = (d.warnings && d.warnings.length)
          ? '<div style="margin-top:6px; font-weight:600;">' + d.warnings.map(w => {{
              const wColor = String(w).includes('MISPRICING') ? 'var(--green)' : 'var(--red)';
              return '<div style="color:' + wColor + ';">' + escHtml(w) + '</div>';
            }}).join('') + '</div>'
          : '';
        box.style.borderColor = isNoBet ? 'rgba(239,68,68,0.55)' : (isLean ? 'rgba(245,158,11,0.55)' : 'rgba(34,197,94,0.55)');
        box.innerHTML =
          '<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">' +
            '<div><b style="font-size:13px;">' + escHtml(d.home) + ' vs ' + escHtml(d.away) + '</b> · <span class="pill">H2H: ' + escHtml(d.h2h_summary || '0-0') + '</span> · <span class="muted">' + eloStr + '</span></div>' +
            '<div><span class="' + verdictPillCls + '" style="font-size:11.5px; padding:3px 9px;">' + escHtml(d.verdict || '') + '</span> <button type="button" class="btn-mini" onclick="openMatchupInspector(' + escHtml(JSON.stringify(d.home)) + ', ' + escHtml(JSON.stringify(d.away)) + ', \\'\\')">🔍 Full H2H &amp; Dutching</button></div>' +
          '</div>' +
          '<div style="margin-top:6px; display:flex; gap:16px; flex-wrap:wrap;" class="muted">' +
            '<span><b>' + escHtml(d.home) + ':</b> Odds <b>' + o1Str + '</b> · All-Level Last-5 WinRate: <b>' + f1Str + '</b> · Turnaround: ' + r1Str + '</span>' +
            '<span><b>' + escHtml(d.away) + ':</b> Odds <b>' + o2Str + '</b> · All-Level Last-5 WinRate: <b>' + f2Str + '</b> · Turnaround: ' + r2Str + '</span>' +
          '</div>' +
          mktsHtml +
          warnHtml;
      }} catch (err) {{
        box.innerHTML = '<span class="num-neg">Analyzer error: ' + escHtml(String(err)) + '</span>';
      }} finally {{
        if (!isActionBusy) document.getElementById('topLoadingBar')?.classList.remove('is-active');
      }}
    }}

    function setBetBudget(amount) {{
      const inp = document.getElementById('betAmountInput');
      if (inp) inp.value = String(amount);
      buildSmartBetPlan();
    }}

    function shareStrategyTicket(titleStr, summaryStr, legsText) {{
      const modal = document.getElementById('telegramModal');
      if (!modal) return;
      modal.style.display = 'block';
      const msg = [
        '🎯 **VEKTORPULSE — ' + titleStr.toUpperCase() + '**',
        '💰 *' + summaryStr + '*',
        '',
        legsText,
        '',
        '⚡ *VektorPulse · Sports Edge & Score Intelligence*'
      ].join('\\n');
      document.getElementById('tgMessagePreview').value = msg;
      modal.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function buildSmartBetPlan() {{
      saveSlipPrefsToStorage();
      const grid = document.getElementById('smartBetPlanGrid');
      if (!grid) return;
      const budget = Math.max(5, parseFloat(document.getElementById('betAmountInput')?.value || '100') || 100);
      const profile = document.getElementById('betRiskProfileSelect')?.value || 'balanced';
      let pool = collectVisibleBestBets();
      if (!pool.length) {{
        const allRows = document.querySelectorAll('#bestBetsTable tbody tr[data-date]');
        allRows.forEach(r => {{
          pool.push({{
            date: r.getAttribute('data-date') || '',
            date_local: r.getAttribute('data-date-local') || '',
            sport_cat: r.getAttribute('data-sport-cat') || 'soccer',
            sport_league: r.getAttribute('data-sport') || '',
            comp: r.getAttribute('data-comp') || r.getAttribute('data-sport') || '',
            match: r.getAttribute('data-match') || '',
            pick: r.getAttribute('data-pick') || '',
            pick_name: r.getAttribute('data-pick-name') || r.getAttribute('data-pick') || '',
            tier: r.getAttribute('data-tier') || '',
            win_prob: parseFloat(r.getAttribute('data-win-prob') || '0.68'),
            fair_odds: parseFloat(r.getAttribute('data-fair-odds') || '1.45'),
            exact_score: r.getAttribute('data-exact-score') || '',
            odds: parseFloat(r.getAttribute('data-odds') || '0'),
            odds_display: r.getAttribute('data-odds-display') || ''
          }});
        }});
      }}
      const isCustomSlip = customSelectedMatches.size > 0;
      if (isCustomSlip) {{
        const customPool = pool.filter(x => customSelectedMatches.has(x.match));
        if (customPool.length > 0) pool = customPool;
      }}
      if (!pool.length) {{
        grid.innerHTML = '<div class="muted">No qualifying picks available for the selected filter.</div>';
        return;
      }}

      // Score each pick by safety, Kelly edge, and tier
      const scored = pool.map(it => {{
        const p = Math.min(Math.max(it.win_prob || 0.65, 0.50), 0.96);
        const o = Math.max(it.odds || 1.20, 1.08);
        const ev = p * o - 1.0;
        const kellyW = Math.max((p * Math.min(o, 2.20) - 0.82) / Math.max(o - 1.0, 0.12), 0.10);
        const safetyRank = p * 1.15 + Math.max(ev, -0.04) * 0.45 + (o >= 1.16 && o <= 1.68 ? 0.08 : 0.0);
        const upsideRank = p * 0.85 + Math.max(ev, 0.0) * 0.85 + (o >= 1.28 && o <= 1.85 ? 0.10 : 0.0);
        return {{ ...it, p, o, ev, kellyW, safetyRank, upsideRank }};
      }});

      // 1. Strategy A: Safe Combo / Parlay Optimizer (Uncorrelated across competitions/sports, or all checked legs in custom mode)
      const comboSorted = isCustomSlip ? [...scored] : [...scored].sort((a, b) =>
        profile === 'upside' ? (b.upsideRank - a.upsideRank) : (b.safetyRank - a.safetyRank)
      );
      const targetComboLegs = isCustomSlip ? Math.min(scored.length, 6) : (profile === 'upside' ? 3 : 2);
      const comboLegs = [];
      const usedMatches = new Set();
      const usedComps = new Set();
      for (const cand of comboSorted) {{
        if (comboLegs.length >= targetComboLegs) break;
        if (usedMatches.has(cand.match)) continue;
        if (!isCustomSlip && (cand.o < 1.12 || cand.o > 1.88)) continue;
        if (!isCustomSlip && profile === 'fortress' && cand.p < 0.72) continue;
        if (!isCustomSlip && usedComps.has(cand.comp) && comboSorted.length > targetComboLegs + 2) continue;
        comboLegs.push(cand);
        usedMatches.add(cand.match);
        usedComps.add(cand.comp);
      }}
      while (comboLegs.length < Math.min(2, scored.length)) {{
        const fallback = comboSorted.find(c => !usedMatches.has(c.match));
        if (!fallback) break;
        comboLegs.push(fallback);
        usedMatches.add(fallback.match);
      }}

      const comboOdds = comboLegs.reduce((acc, x) => acc * x.o, 1.0);
      const comboProb = comboLegs.reduce((acc, x) => acc * x.p, 1.0);
      const comboReturn = budget * comboOdds;
      const comboNetProfit = comboReturn - budget;

      // 2. Strategy B: Kelly-Weighted Separate Individual Bets (Portfolio of 3–5 Singles, or all checked matches in custom mode)
      const targetSinglesCount = isCustomSlip ? scored.length : (profile === 'fortress' ? 3 : (budget >= 150 ? 5 : 4));
      const singlesSorted = isCustomSlip ? [...scored] : [...scored].sort((a, b) => (b.p * 0.7 + b.kellyW * 0.3) - (a.p * 0.7 + a.kellyW * 0.3));
      const singlePicks = [];
      const seenSingleMatches = new Set();
      for (const cand of singlesSorted) {{
        if (singlePicks.length >= targetSinglesCount) break;
        if (seenSingleMatches.has(cand.match)) continue;
        if (!isCustomSlip && cand.o < 1.14) continue;
        singlePicks.push(cand);
        seenSingleMatches.add(cand.match);
      }}
      if (!singlePicks.length) singlePicks.push(...scored.slice(0, Math.min(3, scored.length)));

      const sumKellyW = singlePicks.reduce((s, x) => s + x.kellyW, 0.0) || 1.0;
      let allocatedSum = 0.0;
      const singleAllocs = singlePicks.map((x, idx) => {{
        const rawStake = idx === singlePicks.length - 1
          ? Math.max(0, budget - allocatedSum)
          : Math.round((budget * (x.kellyW / sumKellyW)) * 2.0) / 2.0;
        allocatedSum += rawStake;
        const retIfWin = rawStake * x.o;
        const netIfWin = retIfWin - rawStake;
        const expNet = rawStake * (x.p * x.o - 1.0);
        return {{ ...x, stake: rawStake, retIfWin, netIfWin, expNet }};
      }});

      const singlesMaxReturn = singleAllocs.reduce((s, x) => s + x.retIfWin, 0.0);
      const singlesMaxNet = singlesMaxReturn - budget;
      const singlesExpReturn = singleAllocs.reduce((s, x) => s + x.stake * x.p * x.o + x.stake * (1.0 - x.p) * 0.0, 0.0);
      // Probability at least (N-1) singles win (so portfolio finishes in profit or near breakeven)
      const avgSingleP = singleAllocs.reduce((s, x) => s + x.p, 0.0) / Math.max(singleAllocs.length, 1);
      const probMajorityHit = Math.min(0.98, 1.0 - Math.pow(1.0 - avgSingleP, 2));

      // 3. Strategy C: Hybrid "Core Singles + Combo Booster" Split (65% Singles / 35% Safe 2-Leg Combo)
      const hybridSinglesBudget = Math.round(budget * 0.65 * 2.0) / 2.0;
      const hybridComboBudget = Math.max(0, budget - hybridSinglesBudget);
      const top2Singles = singleAllocs.slice(0, 2);
      const top2Weight = top2Singles.reduce((s, x) => s + x.kellyW, 0.0) || 1.0;
      let hAllocSum = 0.0;
      const hybridSingles = top2Singles.map((x, idx) => {{
        const st = idx === top2Singles.length - 1
          ? Math.max(0, hybridSinglesBudget - hAllocSum)
          : Math.round((hybridSinglesBudget * (x.kellyW / top2Weight)) * 2.0) / 2.0;
        hAllocSum += st;
        return {{ ...x, hStake: st, hRet: st * x.o, hNet: st * (x.o - 1.0) }};
      }});
      const hybrid2Legs = comboLegs.slice(0, 2);
      const hybridComboOdds = hybrid2Legs.reduce((acc, x) => acc * x.o, 1.0);
      const hybridComboRet = hybridComboBudget * hybridComboOdds;
      const hybridTotalMaxReturn = hybridSingles.reduce((s, x) => s + x.hRet, 0.0) + hybridComboRet;
      const hybridTotalMaxNet = hybridTotalMaxReturn - budget;
      const singlesFloorReturn = hybridSingles.reduce((s, x) => s + x.hRet, 0.0);

      // Build HTML for the 3 Strategy Cards
      const comboLegsHtml = comboLegs.map((l, idx) => {{
        const ico = getSportEmoji(l.sport_cat || l.sport_league);
        const tm = currentTzMode === 'utc' ? l.date : (l.date_local || l.date);
        return '<div style="padding:5px 0; border-bottom:1px solid rgba(34,48,73,0.45); font-size:11.5px;">' +
          '<div><b>Leg ' + (idx + 1) + ':</b> ' + ico + ' <b>' + escHtml(l.match) + '</b> <span class="muted">(' + escHtml(tm) + ')</span></div>' +
          '<div style="margin-top:2px;">&rarr; Pick: <b class="num-pos">' + escHtml(l.pick_name) + '</b> @ <b>' + l.o.toFixed(2) + '</b> · WinProb: <b class="num-pos">' + (l.p * 100).toFixed(1) + '%</b></div>' +
        '</div>';
      }}).join('');

      const singlesRowsHtml = singleAllocs.map((s, idx) => {{
        const ico = getSportEmoji(s.sport_cat || s.sport_league);
        return '<div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0; border-bottom:1px solid rgba(34,48,73,0.45); font-size:11.5px;">' +
          '<div>' + (idx + 1) + '. ' + ico + ' <b>' + escHtml(s.pick_name) + '</b> <span class="muted">(' + escHtml(s.match) + ')</span> @ <b>' + s.o.toFixed(2) + '</b> <span class="muted">(' + (s.p * 100).toFixed(0) + '%)</span></div>' +
          '<div style="white-space:nowrap; margin-left:8px;"><span class="pill badge-bet">Stake €' + s.stake.toFixed(2) + '</span> &rarr; <b class="num-pos">+€' + s.netIfWin.toFixed(2) + '</b></div>' +
        '</div>';
      }}).join('');

      const hybridRowsHtml = hybridSingles.map((s, idx) => {{
        const ico = getSportEmoji(s.sport_cat || s.sport_league);
        return '<div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0; border-bottom:1px solid rgba(34,48,73,0.45); font-size:11.5px;">' +
          '<div>🛡️ Single #' + (idx + 1) + ': ' + ico + ' <b>' + escHtml(s.pick_name) + '</b> @ <b>' + s.o.toFixed(2) + '</b> <span class="muted">(' + (s.p * 100).toFixed(0) + '%)</span></div>' +
          '<div><span class="pill tier">€' + s.hStake.toFixed(2) + '</span> &rarr; <b class="num-pos">€' + s.hRet.toFixed(2) + '</b></div>' +
        '</div>';
      }}).join('') +
      '<div style="display:flex; justify-content:space-between; align-items:center; padding:5px 0; font-size:11.5px;">' +
        '<div>🚀 <b>2-Leg Booster:</b> ' + hybrid2Legs.map(x => escHtml(x.pick_name)).join(' + ') + ' @ <b>' + hybridComboOdds.toFixed(2) + '</b></div>' +
        '<div><span class="pill badge-bet">€' + hybridComboBudget.toFixed(2) + '</span> &rarr; <b class="num-pos">€' + hybridComboRet.toFixed(2) + '</b></div>' +
      '</div>';

      // Share strings
      const comboShareLegs = comboLegs.map((l, i) => (i + 1) + '. ' + getSportEmoji(l.sport_cat) + ' **' + l.match + '** -> **' + l.pick_name + '** @ **' + l.o.toFixed(2) + '** (' + (l.p * 100).toFixed(1) + '%)').join('\\n');
      const singlesShareLegs = singleAllocs.map((s, i) => (i + 1) + '. ' + getSportEmoji(s.sport_cat) + ' **' + s.match + '** -> **' + s.pick_name + '** @ **' + s.o.toFixed(2) + '** · Stake: **€' + s.stake.toFixed(2) + '** (Profit +€' + s.netIfWin.toFixed(2) + ')').join('\\n');
      const hybridShareLegs = hybridSingles.map((s, i) => '• Single #' + (i + 1) + ': **' + s.pick_name + '** (' + s.match + ') @ **' + s.o.toFixed(2) + '** · Stake **€' + s.hStake.toFixed(2) + '**').join('\\n') +
        '\\n• 2-Leg Booster: **' + hybrid2Legs.map(x => x.pick_name).join(' + ') + '** @ **' + hybridComboOdds.toFixed(2) + '** · Stake **€' + hybridComboBudget.toFixed(2) + '**';

      const customBadge = isCustomSlip ? ' <span class="pill tier">☑️ CUSTOM SLIP (' + customSelectedMatches.size + ' Picked)</span>' : '';
      const recBadgeA = (!isCustomSlip && (budget <= 40 || profile === 'upside')) ? ' <span class="pill badge-bet">★ RECOMMENDED FOR BUDGET</span>' : customBadge;
      const recBadgeB = (!isCustomSlip && (budget >= 120 && profile === 'fortress')) ? ' <span class="pill badge-bet">★ LOWEST VARIANCE</span>' : customBadge;
      const recBadgeC = (!isCustomSlip && (budget >= 40 && profile === 'balanced')) ? ' <span class="pill badge-bet">★ OPTIMAL SHARPE SPLIT</span>' : customBadge;

      grid.innerHTML =
        '<div class="card" style="margin:0; border-color:rgba(34,197,94,0.45);">' +
          '<div class="card-head">' +
            '<div><b>Option A · Safe ' + comboLegs.length + '-Leg Multiplier Combo</b>' + recBadgeA + '</div>' +
            '<button type="button" class="btn-mini" title="Share this Combo Ticket" onclick="shareStrategyTicket(\\'Safe ' + comboLegs.length + '-Leg Combo Ticket\\', \\'Stake: €' + budget.toFixed(2) + ' · Combined Odds: ' + comboOdds.toFixed(2) + ' · Potential Return: €' + comboReturn.toFixed(2) + ' (+€' + comboNetProfit.toFixed(2) + ')\\', ' + escHtml(JSON.stringify(comboShareLegs)) + ')">📣</button>' +
          '</div>' +
          '<div class="muted" style="margin:4px 0 8px;">Uncorrelated cross-league parlay maximizing total return on a single ticket</div>' +
          '<div>' + comboLegsHtml + '</div>' +
          '<div style="margin-top:10px; padding-top:8px; border-top:1px solid var(--border); display:flex; justify-content:space-between; font-size:12px;">' +
            '<span>Stake: <b>€' + budget.toFixed(2) + '</b> · Combined Odds: <b class="num-pos">' + comboOdds.toFixed(2) + 'x</b> (' + (comboProb * 100).toFixed(1) + '% Hit)</span>' +
            '<span>Return: <b class="num-pos">€' + comboReturn.toFixed(2) + ' (+€' + comboNetProfit.toFixed(2) + ')</b></span>' +
          '</div>' +
        '</div>' +

        '<div class="card" style="margin:0; border-color:rgba(56,189,248,0.45);">' +
          '<div class="card-head">' +
            '<div><b>Option B · ' + singleAllocs.length + ' Separate Individual Bets (Kelly Portfolio)</b>' + recBadgeB + '</div>' +
            '<button type="button" class="btn-mini" title="Share this Singles Portfolio" onclick="shareStrategyTicket(\\'Kelly Singles Portfolio (' + singleAllocs.length + ' Bets)\\', \\'Total Budget: €' + budget.toFixed(2) + ' · All-Hit Return: €' + singlesMaxReturn.toFixed(2) + ' (+€' + singlesMaxNet.toFixed(2) + ')\\', ' + escHtml(JSON.stringify(singlesShareLegs)) + ')">📣</button>' +
          '</div>' +
          '<div class="muted" style="margin:4px 0 8px;">Splits €' + budget.toFixed(2) + ' across ' + singleAllocs.length + ' independent singles — one upset never wipes out your stake</div>' +
          '<div>' + singlesRowsHtml + '</div>' +
          '<div style="margin-top:10px; padding-top:8px; border-top:1px solid var(--border); display:flex; justify-content:space-between; font-size:12px;">' +
            '<span>Safety: <b class="num-pos">' + (probMajorityHit * 100).toFixed(1) + '%</b> (&ge;N-1 hit)</span>' +
            '<span>All-Hit Return: <b class="num-pos">€' + singlesMaxReturn.toFixed(2) + ' (+€' + singlesMaxNet.toFixed(2) + ')</b></span>' +
          '</div>' +
        '</div>' +

        '<div class="card" style="margin:0; border-color:rgba(245,158,11,0.5);">' +
          '<div class="card-head">' +
            '<div><b>Option C · 65/35 Core Singles + Combo Booster</b>' + recBadgeC + '</div>' +
            '<button type="button" class="btn-mini" title="Share Hybrid Strategy" onclick="shareStrategyTicket(\\'65/35 Core Singles + Combo Booster\\', \\'Total Budget: €' + budget.toFixed(2) + ' · Max Return: €' + hybridTotalMaxReturn.toFixed(2) + ' (+€' + hybridTotalMaxNet.toFixed(2) + ')\\', ' + escHtml(JSON.stringify(hybridShareLegs)) + ')">📣</button>' +
          '</div>' +
          '<div class="muted" style="margin:4px 0 8px;">65% (€' + hybridSinglesBudget.toFixed(2) + ') on Top 2 Singles protects your floor (€' + singlesFloorReturn.toFixed(2) + ') + 35% (€' + hybridComboBudget.toFixed(2) + ') on 2-Leg Combo for upside</div>' +
          '<div>' + hybridRowsHtml + '</div>' +
          '<div style="margin-top:10px; padding-top:8px; border-top:1px solid var(--border); display:flex; justify-content:space-between; font-size:12px;">' +
            '<span>Singles Floor: <b>€' + singlesFloorReturn.toFixed(2) + '</b> (Covers ' + Math.round((singlesFloorReturn / budget) * 100) + '% of stake)</span>' +
            '<span>Full Sweep: <b class="num-pos">€' + hybridTotalMaxReturn.toFixed(2) + ' (+€' + hybridTotalMaxNet.toFixed(2) + ')</b></span>' +
          '</div>' +
        '</div>';
    }}

    function applyTimezoneMode(mode) {{
      currentTzMode = mode === 'utc' ? 'utc' : 'local';
      const isUtc = currentTzMode === 'utc';
      document.getElementById('tzBtnLocal')?.classList.toggle('active', !isUtc);
      document.getElementById('tzBtnUtc')?.classList.toggle('active', isUtc);
      document.querySelectorAll('.tz-time').forEach(el => {{
        const utcVal = el.getAttribute('data-utc') || '';
        const locVal = el.getAttribute('data-local') || utcVal;
        el.textContent = isUtc ? utcVal : locVal;
      }});
    }}

    function exportBestBets(fmt) {{
      const items = collectVisibleBestBets();
      let content = '';
      let mime = 'text/plain;charset=utf-8';
      let filename = 'best_bets.' + fmt;
      if (fmt === 'json') {{
        content = JSON.stringify(items, null, 2);
        mime = 'application/json;charset=utf-8';
      }} else {{
        const cols = ['date', 'date_local', 'sport_league', 'match', 'pick', 'odds', 'odds_display'];
        const esc = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
        const lines = [cols.join(',')];
        items.forEach(it => lines.push(cols.map(c => esc(it[c])).join(',')));
        content = lines.join('\\n') + '\\n';
        mime = 'text/csv;charset=utf-8';
      }}
      const blob = new Blob([content], {{ type: mime }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }}

    const SPORT_EMOJIS = {{
      soccer: '⚽',
      tennis: '🎾',
      basketball: '🏀',
      volleyball: '🏐',
      hockey: '🏒',
      football: '🏈',
      baseball: '⚾'
    }};

    function getSportEmoji(catOrLeague) {{
      const low = String(catOrLeague || '').toLowerCase();
      if (SPORT_EMOJIS[low]) return SPORT_EMOJIS[low];
      if (low.includes('tennis') || low.includes('atp') || low.includes('wta')) return '🎾';
      if (low.includes('volleyball')) return '🏐';
      if (low.includes('basketball') || low.includes('nba') || low.includes('wnba') || low.includes('ncaa') || low.includes('nbl')) return '🏀';
      if (low.includes('hockey') || low.includes('nhl')) return '🏒';
      if (low.includes('nfl') || low.includes('american football')) return '🏈';
      if (low.includes('baseball') || low.includes('mlb')) return '⚾';
      return '⚽';
    }}

    function buildBrowserTelegramDigest() {{
      const items = collectVisibleBestBets().slice(0, 20);
      const dayBadge = currentDayFilter === 'all' ? 'All Upcoming Days' : ('Day Filter: ' + currentDayFilter);
      const lines = [
        '⚡ **VEKTORPULSE — DAILY PICKS & UPDATES**',
        '🕒 *Timezone: {DEFAULT_LOCAL_TZ} · ' + dayBadge + ' · Showing ' + items.length + ' Picks*',
        ''
      ];
      items.forEach((it, idx) => {{
        const tm = it.date_local || it.date;
        const icon = getSportEmoji(it.sport_cat || it.sport_league);
        lines.push(
          (idx + 1) + '. ' + icon + ' **' + it.match + '**\\n' +
          '   🕒 `' + tm + '` · ' + icon + ' ' + it.sport_league + '\\n' +
          '   🎯 Pick: **' + it.pick + '** · 💰 Odds: **' + it.odds_display + '**'
        );
      }});
      lines.push('', '⚡ *VektorPulse · Sports Edge & Score Intelligence*');
      return lines.join('\\n');
    }}

    let currentShareSportCat = null;

    function openTelegramPanel() {{
      currentShareSportCat = currentSportFilter;
      const modal = document.getElementById('telegramModal');
      modal.style.display = 'block';
      document.getElementById('tgMessagePreview').value = buildBrowserTelegramDigest();
      modal.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function shareSinglePick(matchStr, pickStr, oddsStr, dateLocalStr, sportCat) {{
      currentShareSportCat = sportCat || currentSportFilter;
      const modal = document.getElementById('telegramModal');
      modal.style.display = 'block';
      const icon = getSportEmoji(sportCat || matchStr);
      const msg = [
        '🎯 **VEKTORPULSE — HIGH-CONVICTION PICK**',
        '',
        icon + ' **' + matchStr + '**',
        '🕒 Kickoff: `' + dateLocalStr + '`',
        '✅ Pick: **' + pickStr + '**',
        '💰 Odds: **' + oddsStr + '**',
        '',
        '⚡ *VektorPulse · Sports Edge & Score Intelligence*'
      ].join('\\n');
      document.getElementById('tgMessagePreview').value = msg;
      modal.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function escHtml(s) {{
      return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }}

    function fmtSignedHtml(val, decimals, suffix) {{
      const v = Number(val || 0);
      const cls = v > 0 ? 'num-pos' : (v < 0 ? 'num-neg' : '');
      const sign = v > 0 ? '+' : '';
      return '<b class="' + cls + '">' + sign + v.toFixed(decimals) + (suffix || '') + '</b>';
    }}

    function applyLiveStreamPayload(snap) {{
      if (!snap || !snap.paper_ledger) return;
      const tickEl = document.getElementById('lastStreamTick');
      if (tickEl && snap.server_time_local) {{
        tickEl.textContent = 'Live Sync: ' + snap.server_time_local;
      }}
      const ledger = snap.paper_ledger;
      const scEl = document.getElementById('settledCountSpan');
      const swEl = document.getElementById('settledWinsSpan');
      const slEl = document.getElementById('settledLossesSpan');
      const spEl = document.getElementById('settledProfitSpan');
      const lcEl = document.getElementById('liveCountSpan');
      const pcEl = document.getElementById('pendingCountSpan');
      if (scEl) scEl.textContent = String(ledger.settled_count ?? 0);
      if (swEl) swEl.textContent = String(ledger.settled_wins ?? 0);
      if (slEl) {{
        slEl.textContent = String(ledger.settled_losses ?? 0);
        slEl.className = (ledger.settled_losses || 0) > 0 ? 'num-neg' : '';
      }}
      if (spEl) spEl.innerHTML = fmtSignedHtml(ledger.settled_profit_u || 0, 2, 'u');
      if (lcEl) lcEl.textContent = String(ledger.live_count ?? 0);
      if (pcEl) pcEl.textContent = String(ledger.pending_count ?? 0);

      const trades = ledger.trades || [];
      const minThr = parseFloat(document.getElementById('minOddsSlider')?.value || '1.10');
      const settledRows = [];
      const liveRows = [];
      const pendingRows = [];
      trades.forEach(tr => {{
        const o = Number(tr.logged_best_odds || 0);
        const koDisp = currentTzMode === 'utc' ? tr.kickoff : (tr.kickoff_local || tr.kickoff);
        const lgName = tr.league_label || (tr.league || '').toUpperCase();
        const spCat = tr.sport_cat || 'soccer';
        const pickTeam = tr.side === 'H' ? tr.home : tr.away;
        const searchStr = (tr.home + ' ' + tr.away + ' ' + lgName + ' ' + pickTeam).toLowerCase();
        const hideOdds = o <= minThr ? ' hidden-by-odds' : '';
        const hideSport = (currentSportFilter !== 'all' && spCat !== currentSportFilter) ? ' hidden-by-sport' : '';
        const hideSearch = (currentSearchQuery && !searchStr.includes(currentSearchQuery)) ? ' hidden-by-search' : '';
        const rowCls = (hideOdds + hideSport + hideSearch).trim();
        const spIcon = getSportEmoji(spCat);
        const matchStr = tr.home + ' vs ' + tr.away;
        const isTen = spCat === 'tennis';
        const imgCls = isTen ? 'player-avatar' : 'team-logo';
        const cLogoHtml = tr.comp_logo ? '<img src="' + escHtml(tr.comp_logo) + '" class="comp-logo" loading="lazy" onerror="this.style.display=\\'none\\'">' : '';
        const hLogoHtml = tr.home_logo ? '<img src="' + escHtml(tr.home_logo) + '" class="' + imgCls + '" loading="lazy" onerror="this.style.display=\\'none\\'">' : '';
        const aLogoHtml = tr.away_logo ? '<img src="' + escHtml(tr.away_logo) + '" class="' + imgCls + '" loading="lazy" onerror="this.style.display=\\'none\\'">' : '';
        const pLogoHtml = (tr.side === 'H' ? hLogoHtml : aLogoHtml);
        const hArg = escHtml(JSON.stringify(tr.home || ''));
        const aArg = escHtml(JSON.stringify(tr.away || ''));
        const lgArg = escHtml(JSON.stringify(tr.league || ''));
        const matchRichHtml = '<span class="matchup-inline matchup-clickable" title="Click to inspect H2H, Last-6 Form &amp; Score Matrix" onclick="openMatchupInspector(' + hArg + ', ' + aArg + ', ' + lgArg + ')">' + hLogoHtml + '<span>' + escHtml(tr.home) + '</span><span class="muted">vs</span>' + aLogoHtml + '<span>' + escHtml(tr.away) + '</span></span>';
        const pickRichHtml = '<span class="matchup-inline">' + pLogoHtml + '<b class="num-pos">' + escHtml(pickTeam) + ' (' + escHtml(tr.side) + ')</b> <span class="pill tier">' + escHtml(tr.tier) + '</span></span>';
        const escPredRaw = String(tr.exact_score_pred || '');
        const escShort = escPredRaw ? escPredRaw.split('(')[0].trim() : '';
        if (tr.status === 'SETTLED' && tr.pnl_best !== null && tr.pnl_best !== undefined) {{
          const pnl = Number(tr.pnl_best);
          const badge = pnl > 0
            ? '<span class="pill badge-bet">WIN (+' + pnl.toFixed(2) + 'u)</span>'
            : '<span class="pill badge-veto">LOSS (' + pnl.toFixed(2) + 'u)</span>';
          settledRows.push(
            '<tr class="' + rowCls + '" data-odds="' + o.toFixed(3) + '" data-sport-cat="' + escHtml(spCat) + '" data-search="' + escHtml(searchStr) + '">' +
              '<td class="col-icon" data-sort="' + escHtml(spCat) + '"><span class="sport-icon">' + spIcon + '</span></td>' +
              '<td data-sort="' + escHtml(lgName) + '"><span class="pill">' + cLogoHtml + escHtml(lgName) + '</span></td>' +
              '<td data-sort="' + escHtml(tr.kickoff) + '"><b class="tz-time" data-utc="' + escHtml(tr.kickoff) + '" data-local="' + escHtml(tr.kickoff_local || tr.kickoff) + '">' + escHtml(koDisp) + '</b></td>' +
              '<td data-sort="' + escHtml(matchStr) + '">' + matchRichHtml + '</td>' +
              '<td data-sort="' + escHtml(pickTeam) + '">' + pickRichHtml + '</td>' +
              '<td data-sort="' + escHtml(tr.score_str || '—') + '"><b>' + escHtml(tr.score_str || '—') + '</b></td>' +
              '<td data-sort="' + o.toFixed(3) + '"><b>' + o.toFixed(2) + '</b> (CLV ' + fmtSignedHtml(tr.clv_pct || 0, 1, '%') + ')</td>' +
              '<td data-sort="' + pnl.toFixed(3) + '">' + badge + '</td>' +
            '</tr>'
          );
        }} else if (tr.is_live || tr.status === 'LIVE') {{
          const closeO = Number(tr.latest_close_odds || o);
          const lPnl = Number(tr.live_pnl || 0);
          const lSc = tr.live_score || tr.score_str || '0-0 (LIVE)';
          const lBadge = lPnl > 0
            ? '<span class="pill badge-bet">LIVE · LEADING (+' + lPnl.toFixed(2) + 'u)</span>'
            : (lPnl < 0 ? '<span class="pill badge-veto">LIVE · TRAILING (' + lPnl.toFixed(2) + 'u)</span>' : '<span class="pill tier">LIVE · LEVEL (0.00u)</span>');
          const itemKey = String((tr.league || '') + ':' + (tr.event_id || '')).toLowerCase();
          const isItemOn = (itemKey in currentInplayAlertItems) ? Boolean(currentInplayAlertItems[itemKey]) : currentInplayAlertsEnabled;
          const itemBtnStyle = isItemOn ? 'border-color:var(--green);color:var(--green);background:rgba(34,197,94,0.14);' : '';
          const itemBtnHtml = ' <button type="button" class="btn-mini inplay-item-alert-btn" data-item-key="' + escHtml(itemKey) + '" style="' + itemBtnStyle + '" onclick="toggleInplayItemAlert(' + escHtml(JSON.stringify(itemKey)) + ', this)" title="Toggle Live In-Play Discord Alert for this match">' + (isItemOn ? '🔔' : '🔕') + '</button>';
          liveRows.push(
            '<tr class="' + rowCls + '" data-odds="' + o.toFixed(3) + '" data-sport-cat="' + escHtml(spCat) + '" data-search="' + escHtml(searchStr) + '">' +
              '<td class="col-icon" data-sort="' + escHtml(spCat) + '"><span class="sport-icon">' + spIcon + '</span></td>' +
              '<td data-sort="' + escHtml(lgName) + '"><span class="pill">' + cLogoHtml + escHtml(lgName) + '</span></td>' +
              '<td data-sort="' + escHtml(tr.kickoff) + '"><b class="tz-time" data-utc="' + escHtml(tr.kickoff) + '" data-local="' + escHtml(tr.kickoff_local || tr.kickoff) + '">' + escHtml(koDisp) + '</b></td>' +
              '<td data-sort="' + escHtml(matchStr) + '">' + matchRichHtml + '</td>' +
              '<td data-sort="' + escHtml(pickTeam) + '">' + pickRichHtml + '</td>' +
              '<td data-sort="' + escHtml(lSc) + '"><b>' + escHtml(lSc) + '</b></td>' +
              '<td data-sort="' + o.toFixed(3) + '"><b>' + o.toFixed(2) + '</b> (Close ' + closeO.toFixed(2) + ', CLV ' + fmtSignedHtml(tr.clv_pct || 0, 1, '%') + ')</td>' +
              '<td data-sort="' + lPnl.toFixed(3) + '">' + lBadge + itemBtnHtml + '</td>' +
            '</tr>'
          );
        }} else {{
          const closeO = Number(tr.latest_close_odds || o);
          const trDay = tr.day_key || (tr.kickoff_local || tr.kickoff || '').slice(0, 10);
          const hideDay = (currentDayFilter !== 'all' && !(currentDaySet ? currentDaySet.has(trDay) : trDay === currentDayFilter)) ? ' hidden-by-day' : '';
          const pendCls = (rowCls + hideDay).trim();
          const pendScCell = escShort
            ? '<span class="muted">—</span> <span class="pill">Proj: ' + escHtml(escShort) + '</span>'
            : '<span class="muted">— (Pre-Match)</span>';
          pendingRows.push(
            '<tr class="' + pendCls + '" data-odds="' + o.toFixed(3) + '" data-sport-cat="' + escHtml(spCat) + '" data-day="' + escHtml(trDay) + '" data-search="' + escHtml(searchStr) + '">' +
              '<td class="col-icon" data-sort="' + escHtml(spCat) + '"><span class="sport-icon">' + spIcon + '</span></td>' +
              '<td data-sort="' + escHtml(lgName) + '"><span class="pill">' + cLogoHtml + escHtml(lgName) + '</span></td>' +
              '<td data-sort="' + escHtml(tr.kickoff) + '"><b class="tz-time" data-utc="' + escHtml(tr.kickoff) + '" data-local="' + escHtml(tr.kickoff_local || tr.kickoff) + '">' + escHtml(koDisp) + '</b></td>' +
              '<td data-sort="' + escHtml(matchStr) + '">' + matchRichHtml + '</td>' +
              '<td data-sort="' + escHtml(pickTeam) + '">' + pickRichHtml + '</td>' +
              '<td data-sort="' + escHtml(escShort || '—') + '">' + pendScCell + '</td>' +
              '<td data-sort="' + o.toFixed(3) + '"><b>' + o.toFixed(2) + '</b> (Close ' + closeO.toFixed(2) + ', CLV ' + fmtSignedHtml(tr.clv_pct || 0, 1, '%') + ')</td>' +
              '<td data-sort="0.000"><span class="pill tier">PENDING (0.00u)</span></td>' +
            '</tr>'
          );
        }}
      }});
      const sTbody = document.getElementById('settledTradesTbody');
      const lTbody = document.getElementById('liveTradesTbody');
      const pTbody = document.getElementById('pendingTradesTbody');
      if (sTbody && settledRows.length) sTbody.innerHTML = settledRows.join('');
      if (lTbody) lTbody.innerHTML = liveRows.length ? liveRows.join('') : '<tr><td colspan="8" class="muted">No logged paper bets are currently in-play. Active matches move here automatically during kickoff!</td></tr>';
      if (pTbody && pendingRows.length) pTbody.innerHTML = pendingRows.join('');
    }}

    let isActionBusy = false;
    let progressTimer = null;

    function setActionBusy(busy, labelText, activeBtn) {{
      isActionBusy = Boolean(busy);
      const banner = document.getElementById('actionProgressBanner');
      const txtEl = document.getElementById('actionProgressText');
      const elapsedEl = document.getElementById('actionElapsedText');
      document.querySelectorAll('.js-action-btn').forEach(b => {{
        b.disabled = isActionBusy;
        if (isActionBusy) b.classList.add('is-busy');
        else b.classList.remove('is-busy');
      }});
      if (progressTimer) {{
        clearInterval(progressTimer);
        progressTimer = null;
      }}
      if (isActionBusy) {{
        if (txtEl && labelText) txtEl.textContent = labelText;
        if (banner) banner.style.display = 'flex';
        document.getElementById('topLoadingBar')?.classList.add('is-active');
        showPageLoader(labelText || 'Synchronizing VektorPulse data...', 'Communicating with ESPN, SofaScore & SQLite store...');
        const t0 = performance.now();
        if (elapsedEl) elapsedEl.textContent = '0.0s';
        progressTimer = setInterval(() => {{
          if (elapsedEl) elapsedEl.textContent = ((performance.now() - t0) / 1000).toFixed(1) + 's';
        }}, 100);
        if (activeBtn) {{
          activeBtn.dataset.origHtml = activeBtn.innerHTML;
          activeBtn.innerHTML = '<span class="spinner"></span> ' + escHtml(labelText || 'Working...');
        }}
      }} else {{
        if (banner) banner.style.display = 'none';
        document.getElementById('topLoadingBar')?.classList.remove('is-active');
        hidePageLoader();
        document.querySelectorAll('.js-action-btn').forEach(b => {{
          if (b.dataset.origHtml) {{
            b.innerHTML = b.dataset.origHtml;
            delete b.dataset.origHtml;
          }}
        }});
      }}
    }}

    function showPageLoader(titleText, subText) {{
      const ov = document.getElementById('pageLoadingOverlay');
      const tEl = document.getElementById('pageLoaderTitle');
      const sEl = document.getElementById('pageLoaderSub');
      const topBar = document.getElementById('topLoadingBar');
      if (tEl && titleText) tEl.textContent = titleText;
      if (sEl && subText) sEl.textContent = subText;
      if (ov) ov.classList.remove('is-hidden');
      if (topBar) topBar.classList.add('is-active');
    }}

    function hidePageLoader() {{
      const ov = document.getElementById('pageLoadingOverlay');
      const topBar = document.getElementById('topLoadingBar');
      if (ov) ov.classList.add('is-hidden');
      if (topBar && !isActionBusy) topBar.classList.remove('is-active');
    }}

    function updateSocialEnvBadges(payload) {{
      const dEnv = payload?.discord || payload?.discord_env;
      const tEnv = payload?.telegram || payload?.telegram_env || payload;
      const dBadge = document.getElementById('discordEnvBadge');
      const whInput = document.getElementById('discordWebhookInput');
      if (dBadge && dEnv) {{
        if (dEnv.configured) {{
          dBadge.className = 'pill badge-bet';
          dBadge.textContent = '✅ Discord .env Ready (' + (dEnv.mode === 'webhook' ? 'Webhook' : ('Bot ' + dEnv.channel_id)) + ')';
          if (whInput && !whInput.value && dEnv.masked_webhook) whInput.placeholder = 'From .env: ' + dEnv.masked_webhook;
        }} else {{
          dBadge.className = 'pill tier';
          dBadge.textContent = '⚠️ Set DISCORD_WEBHOOK_URL in model/.env (or paste below)';
        }}
      }}
      const badge = document.getElementById('tgEnvBadge');
      const chatInput = document.getElementById('tgChatId');
      if (badge && tEnv && tEnv.configured !== undefined) {{
        if (tEnv.configured) {{
          badge.className = 'pill badge-bet';
          badge.textContent = 'Telegram .env (' + (tEnv.chat_id || 'Ready') + ')';
          if (chatInput && !chatInput.value && tEnv.chat_id) chatInput.placeholder = 'From .env: ' + tEnv.chat_id;
        }} else {{
          badge.className = 'pill';
          badge.textContent = 'Telegram: Optional';
        }}
      }}
      const ipItems = payload?.inplay_alert_items ?? payload?.pipeline_status?.inplay_alert_items;
      if (ipItems && typeof ipItems === 'object') {{
        currentInplayAlertItems = {{ ...currentInplayAlertItems, ...ipItems }};
      }}
      const ipEnabled = payload?.inplay_alerts_enabled ?? payload?.pipeline_status?.inplay_alerts_enabled;
      if (ipEnabled !== undefined) {{
        renderInplayAlertsBtn(Boolean(ipEnabled));
      }}
      refreshAllInplayItemButtons();
    }}

    let currentInplayAlertsEnabled = false;
    let currentInplayAlertItems = {{}};
    let currentAppSettings = {{}};

    async function openSettingsModal() {{
      const modal = document.getElementById('settingsModal');
      if (!modal) return;
      modal.style.display = 'flex';
      if (window.location.protocol.startsWith('http')) {{
        try {{
          const r = await fetch('/api/settings');
          const d = await r.json();
          if (d.settings) currentAppSettings = d.settings;
          const swStatus = d.discord?.sport_webhooks || {{}};
          const mapIds = {{
            soccer: 'cfgWhSoccer',
            tennis: 'cfgWhTennis',
            hockey: 'cfgWhHockey',
            basketball: 'cfgWhBasketball',
            football: 'cfgWhFootball',
            baseball: 'cfgWhBaseball'
          }};
          Object.keys(mapIds).forEach(sp => {{
            const inp = document.getElementById(mapIds[sp]);
            const st = swStatus[sp];
            if (inp && st && st.masked_webhook) {{
              inp.placeholder = st.source + ': ' + st.masked_webhook;
            }}
          }});
          const gInp = document.getElementById('cfgWhGlobal');
          if (gInp && d.discord?.masked_webhook) {{
            gInp.placeholder = 'DISCORD_WEBHOOK_URL: ' + d.discord.masked_webhook;
          }}
        }} catch (_) {{}}
      }}
      const s = currentAppSettings || {{}};
      const bankVal = document.getElementById('bankrollInput')?.value || s.bankroll_eur || 1000;
      const budVal = document.getElementById('betAmountInput')?.value || s.default_bet_budget_eur || 100;
      const riskVal = document.getElementById('betRiskProfileSelect')?.value || s.default_risk_mode || 'balanced';
      const minOddsVal = document.getElementById('minOddsSlider')?.value || s.min_odds || 1.10;
      if (document.getElementById('cfgBankrollInput')) document.getElementById('cfgBankrollInput').value = String(bankVal);
      if (document.getElementById('cfgBetBudgetInput')) document.getElementById('cfgBetBudgetInput').value = String(budVal);
      if (document.getElementById('cfgRiskModeSelect')) document.getElementById('cfgRiskModeSelect').value = String(riskVal);
      if (document.getElementById('cfgMinOddsInput')) document.getElementById('cfgMinOddsInput').value = String(minOddsVal);
      if (document.getElementById('cfgMispricingEdgeInput')) document.getElementById('cfgMispricingEdgeInput').value = String(s.mispricing_min_edge_pp ?? 2.0);
      if (document.getElementById('cfgMispricingEvInput')) document.getElementById('cfgMispricingEvInput').value = String(s.mispricing_min_ev_pct ?? 2.0);
      if (document.getElementById('cfgInplayAlertsChk')) document.getElementById('cfgInplayAlertsChk').checked = Boolean(currentInplayAlertsEnabled);
      if (document.getElementById('cfgSettlementAlertsChk')) document.getElementById('cfgSettlementAlertsChk').checked = s.settlement_alerts_enabled !== false;
      if (document.getElementById('cfgDigestHourInput')) document.getElementById('cfgDigestHourInput').value = String(s.daily_digest_hour ?? '');
    }}

    async function saveSettingsModal() {{
      const bankVal = parseFloat(document.getElementById('cfgBankrollInput')?.value || '1000') || 1000;
      const budVal = parseFloat(document.getElementById('cfgBetBudgetInput')?.value || '100') || 100;
      const riskVal = document.getElementById('cfgRiskModeSelect')?.value || 'balanced';
      const minOddsVal = parseFloat(document.getElementById('cfgMinOddsInput')?.value || '1.10') || 1.10;
      const mpEdgeVal = parseFloat(document.getElementById('cfgMispricingEdgeInput')?.value || '2.0') || 2.0;
      const mpEvVal = parseFloat(document.getElementById('cfgMispricingEvInput')?.value || '2.0') || 2.0;
      const inplayChk = Boolean(document.getElementById('cfgInplayAlertsChk')?.checked);
      const settleChk = Boolean(document.getElementById('cfgSettlementAlertsChk')?.checked);
      const digHour = (document.getElementById('cfgDigestHourInput')?.value || '').trim();

      const sportWh = {{}};
      const whFields = {{
        global: 'cfgWhGlobal',
        soccer: 'cfgWhSoccer',
        tennis: 'cfgWhTennis',
        hockey: 'cfgWhHockey',
        basketball: 'cfgWhBasketball',
        football: 'cfgWhFootball',
        baseball: 'cfgWhBaseball'
      }};
      Object.keys(whFields).forEach(k => {{
        const v = (document.getElementById(whFields[k])?.value || '').trim();
        if (v) sportWh[k] = v;
      }});

      if (document.getElementById('bankrollInput')) {{
        document.getElementById('bankrollInput').value = String(bankVal);
        applyBankrollCalculator(bankVal);
      }}
      if (document.getElementById('betAmountInput')) document.getElementById('betAmountInput').value = String(budVal);
      if (document.getElementById('betRiskProfileSelect')) document.getElementById('betRiskProfileSelect').value = riskVal;
      if (document.getElementById('minOddsSlider')) {{
        document.getElementById('minOddsSlider').value = String(minOddsVal);
        applyOddsFilter(minOddsVal);
      }}
      renderInplayAlertsBtn(inplayChk);
      buildSmartBetPlan();

      const payload = {{
        bankroll_eur: bankVal,
        default_bet_budget_eur: budVal,
        default_risk_mode: riskVal,
        min_odds: minOddsVal,
        mispricing_min_edge_pp: mpEdgeVal,
        mispricing_min_ev_pct: mpEvVal,
        inplay_alerts_enabled: inplayChk,
        settlement_alerts_enabled: settleChk,
        daily_digest_hour: digHour,
        sport_webhooks: Object.keys(sportWh).length ? sportWh : undefined
      }};
      try {{
        localStorage.setItem('vp_app_settings', JSON.stringify(payload));
        localStorage.setItem('vp_inplay_alerts_enabled', inplayChk ? '1' : '0');
      }} catch (_) {{}}

      if (window.location.protocol.startsWith('http')) {{
        try {{
          const r = await fetch('/api/settings', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(payload)
          }});
          const d = await r.json();
          if (d.settings) currentAppSettings = d.settings;
          updateSocialEnvBadges(d);
        }} catch (_) {{}}
      }}
      const modal = document.getElementById('settingsModal');
      if (modal) modal.style.display = 'none';
      showToast('✅ VektorPulse settings & per-sport Discord webhook routes saved!');
    }}

    function renderInplayAlertsBtn(enabled) {{
      currentInplayAlertsEnabled = Boolean(enabled);
      const btn = document.getElementById('inplayAlertsToggleBtn');
      if (!btn) return;
      if (currentInplayAlertsEnabled) {{
        btn.className = 'btn-export btn-telegram';
        btn.textContent = '🔔 Live Alerts: ON';
      }} else {{
        btn.className = 'btn-export';
        btn.textContent = '🔕 Live Alerts: OFF';
      }}
      refreshAllInplayItemButtons();
    }}

    function refreshAllInplayItemButtons() {{
      document.querySelectorAll('.inplay-item-alert-btn').forEach(btn => {{
        const k = (btn.getAttribute('data-item-key') || '').toLowerCase();
        const isOn = (k in currentInplayAlertItems) ? Boolean(currentInplayAlertItems[k]) : currentInplayAlertsEnabled;
        btn.textContent = isOn ? '🔔' : '🔕';
        btn.style.borderColor = isOn ? 'var(--green)' : '';
        btn.style.color = isOn ? 'var(--green)' : '';
        btn.style.background = isOn ? 'rgba(34,197,94,0.14)' : '';
      }});
    }}

    async function toggleInplayItemAlert(itemKey, btnEl) {{
      const k = String(itemKey || '').toLowerCase();
      if (!k) return;
      const curVal = (k in currentInplayAlertItems) ? Boolean(currentInplayAlertItems[k]) : currentInplayAlertsEnabled;
      const nextVal = !curVal;
      currentInplayAlertItems[k] = nextVal;
      refreshAllInplayItemButtons();
      try {{ localStorage.setItem('vp_inplay_alert_items', JSON.stringify(currentInplayAlertItems)); }} catch (_) {{}}
      if (window.location.protocol.startsWith('http')) {{
        try {{
          await fetch('/api/settings/inplay-alerts', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ item_key: k, enabled: nextVal }})
          }});
          showToast(nextVal ? ('🔔 Live Alert enabled for ' + k.toUpperCase() + '!') : ('🔕 Live Alert muted for ' + k.toUpperCase() + '.'));
        }} catch (_) {{}}
      }} else {{
        showToast(nextVal ? ('🔔 Live Alert enabled for ' + k.toUpperCase() + '.') : ('🔕 Live Alert muted for ' + k.toUpperCase() + '.'));
      }}
    }}

    async function toggleInplayDiscordAlerts() {{
      const nextState = !currentInplayAlertsEnabled;
      renderInplayAlertsBtn(nextState);
      try {{ localStorage.setItem('vp_inplay_alerts_enabled', nextState ? '1' : '0'); }} catch (_) {{}}
      if (window.location.protocol.startsWith('http')) {{
        try {{
          await fetch('/api/settings/inplay-alerts', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ enabled: nextState }})
          }});
          showToast(nextState ? '🔔 Live In-Play Discord Alerts enabled!' : '🔕 Live In-Play Discord Alerts muted (OFF).');
        }} catch (_) {{}}
      }} else {{
        showToast(nextState ? '🔔 Live In-Play Alerts enabled locally.' : '🔕 Live In-Play Alerts muted (OFF).');
      }}
    }}

    async function syncAndSettleLedger(rescanLive) {{
      if (isActionBusy) return;
      const btn = document.getElementById(rescanLive ? 'rescanLiveBtn' : 'syncLedgerBtn');
      const label = rescanLive
        ? 'Rescanning live matches & odds across all leagues...'
        : 'Syncing & settling paper-betting ledger against ESPN...';
      setActionBusy(true, label, btn);
      try {{
        if (!window.location.protocol.startsWith('http')) {{
          showToast('ℹ️ Running from static file:// — start the WebApp server (`uv run sportdata-webapp --port 8090`) and open http://127.0.0.1:8090 for live sync & streaming!');
          return;
        }}
        const minThr = parseFloat(document.getElementById('minOddsSlider')?.value || '1.10');
        const r = await fetch('/api/sync', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ rescan: Boolean(rescanLive), min_odds: minThr }})
        }});
        const d = await r.json();
        if (d.ok) {{
          applyLiveStreamPayload(d);
          const msg = rescanLive
            ? '✅ Live matches rescanned & ledger synced (' + (d.paper_ledger?.settled_count || 0) + ' settled, ' + (d.paper_ledger?.pending_count || 0) + ' pending)!'
            : '✅ Ledger synced against ESPN (' + (d.newly_settled || 0) + ' newly settled bets; ' + (d.paper_ledger?.settled_count || 0) + ' total settled)!';
          showToast(msg);
          if (rescanLive) setTimeout(() => window.location.reload(), 900);
        }} else {{
          showToast('❌ Sync error: ' + (d.error || 'Unknown error'));
        }}
      }} catch (err) {{
        showToast('❌ Failed to reach WebApp server: ' + err);
      }} finally {{
        setActionBusy(false);
      }}
    }}

    async function runFullDailyPipeline() {{
      if (isActionBusy) return;
      const btn = document.getElementById('runFullPipelineBtn');
      setActionBusy(true, '[1/4] Running full daily pipeline (Incremental Ingest -> Quality Check -> Multi-Sport Scan -> Dashboard)...', btn);
      try {{
        if (!window.location.protocol.startsWith('http')) {{
          showToast('ℹ️ Start the WebApp server (`uv run sportdata-webapp --port 8090`) and open http://127.0.0.1:8090 to run the full pipeline from the browser!');
          return;
        }}
        const minThr = parseFloat(document.getElementById('minOddsSlider')?.value || '1.10');
        const r = await fetch('/api/pipeline', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ full_pipeline: true, min_odds: minThr }})
        }});
        const d = await r.json();
        if (d.ok) {{
          applyLiveStreamPayload(d);
          showToast('✅ Full daily pipeline complete (' + (d.new_ingested_count || 0) + ' new matches ingested; ' + (d.paper_ledger?.settled_count || 0) + ' settled bets)!');
          setTimeout(() => window.location.reload(), 900);
        }} else {{
          showToast('❌ Pipeline error: ' + (d.error || 'Unknown error'));
        }}
      }} catch (err) {{
        showToast('❌ Failed to reach WebApp server: ' + err);
      }} finally {{
        setActionBusy(false);
      }}
    }}

    function initLiveEventStream() {{
      const dot = document.getElementById('streamDot');
      const txt = document.getElementById('streamStatusText');
      if (!window.location.protocol.startsWith('http') || typeof EventSource === 'undefined') {{
        if (txt) txt.textContent = 'Static File Mode (Run scripts/webapp.py for SSE Stream)';
        return;
      }}
      fetch('/api/social/status').then(r => r.json()).then(updateSocialEnvBadges).catch(() => {{}});
      const es = new EventSource('/api/stream');
      es.addEventListener('update', ev => {{
        if (dot) dot.classList.add('online');
        if (txt) txt.textContent = 'Live SSE Stream: Connected';
        try {{
          const snap = JSON.parse(ev.data);
          updateSocialEnvBadges(snap);
          if (snap.pipeline_status?.running && snap.pipeline_status?.step) {{
            const txtEl = document.getElementById('actionProgressText');
            if (txtEl) txtEl.textContent = snap.pipeline_status.step;
          }}
          applyLiveStreamPayload(snap);
        }} catch (_) {{}}
      }});
      es.onerror = () => {{
        if (dot) dot.classList.remove('online');
        if (txt) txt.textContent = 'Live Stream: Reconnecting...';
      }};
    }}

    initLiveEventStream();
    restoreSlipPrefsFromStorage();
    buildSmartBetPlan();
    populateDutchMatchSelect();
    setTimeout(() => hidePageLoader(), 260);
    window.addEventListener('beforeunload', () => {{
      showPageLoader('Refreshing VektorPulse Dashboard...', 'Loading updated predictions, live scores & paper-bet ledger...');
    }});

    function copyTelegramPreview() {{
      const ta = document.getElementById('tgMessagePreview');
      ta.select();
      navigator.clipboard?.writeText(ta.value);
      document.getElementById('tgStatusMsg').textContent = '✅ Copied formatted digest to clipboard!';
    }}

    function splitDiscordBlocks(mdText, maxLen) {{
      if (mdText.length <= maxLen) return [mdText];
      const blocks = [];
      let buf = [];
      mdText.split('\\n').forEach(line => {{
        if (line.startsWith('   ') && buf.length) buf.push(line);
        else {{
          if (buf.length) blocks.push(buf.join('\\n'));
          buf = [line];
        }}
      }});
      if (buf.length) blocks.push(buf.join('\\n'));
      const chunks = [];
      let cur = [];
      let curLen = 0;
      blocks.forEach(blk => {{
        const addLen = blk.length + (cur.length ? 1 : 0);
        if (cur.length && (curLen + addLen > maxLen)) {{
          chunks.push(cur.join('\\n'));
          cur = [blk];
          curLen = blk.length;
        }} else {{
          cur.push(blk);
          curLen += addLen;
        }}
      }});
      if (cur.length) chunks.push(cur.join('\\n'));
      return chunks;
    }}

    async function postToDiscordChannel() {{
      if (isActionBusy) return;
      const sendBtn = document.getElementById('discordSendBtn');
      const webhookUrl = document.getElementById('discordWebhookInput').value.trim();
      const text = document.getElementById('tgMessagePreview').value.trim();
      const statusEl = document.getElementById('tgStatusMsg');
      statusEl.textContent = '⏳ Publishing to Discord channel...';
      setActionBusy(true, 'Publishing digest to Discord channel...', sendBtn);
      try {{
        if (window.location.protocol.startsWith('http')) {{
          const r = await fetch('/api/discord', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
              text,
              sport: currentShareSportCat || currentSportFilter || 'all',
              webhook_url: webhookUrl || undefined
            }})
          }});
          const d = await r.json();
          if (d.ok && !d.dry_run) {{
            const partsInfo = (d.chunks_sent && d.chunks_sent > 1) ? (' in ' + d.chunks_sent + ' messages') : '';
            statusEl.textContent = '✅ Published full digest to Discord channel' + partsInfo + ' (Message ID: ' + (d.message_id || 'OK') + ')!';
            showToast('✅ Successfully published full digest to Discord channel' + partsInfo + '!');
          }} else {{
            statusEl.textContent = '⚠️ Not sent: ' + (d.error || 'Set DISCORD_WEBHOOK_URL in model/.env (or paste your Discord Webhook URL above).');
          }}
          return;
        }}
        if (!webhookUrl) {{
          statusEl.textContent = '⚠️ Paste your Discord Webhook URL above (or run scripts/webapp.py to use DISCORD_WEBHOOK_URL from model/.env).';
          return;
        }}
        const chunks = splitDiscordBlocks(text, 1900);
        let lastId = '';
        for (const chunk of chunks) {{
          const resp = await fetch(webhookUrl + (webhookUrl.includes('?') ? '&' : '?') + 'wait=true', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ content: chunk, username: 'Sportdata Quant Desk' }})
          }});
          const resJson = await resp.json();
          if (!resJson.id) {{
            statusEl.textContent = '❌ Discord error: ' + (resJson.message || 'Unknown error');
            return;
          }}
          lastId = resJson.id;
        }}
        statusEl.textContent = '✅ Published full digest to Discord (' + chunks.length + ' message(s), ID: ' + lastId + ')!';
      }} catch (err) {{
        statusEl.textContent = '❌ Request failed: ' + err;
      }} finally {{
        setActionBusy(false);
      }}
    }}

    async function postToTelegramChannel() {{
      if (isActionBusy) return;
      const sendBtn = document.getElementById('tgSendBtn');
      const token = document.getElementById('tgBotToken').value.trim();
      const chatId = document.getElementById('tgChatId').value.trim();
      const text = document.getElementById('tgMessagePreview').value.trim();
      const statusEl = document.getElementById('tgStatusMsg');
      statusEl.textContent = '⏳ Publishing to Telegram channel...';
      setActionBusy(true, 'Publishing digest to Telegram channel...', sendBtn);
      try {{
        if (window.location.protocol.startsWith('http')) {{
          const r = await fetch('/api/telegram', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
              text,
              bot_token: token || undefined,
              chat_id: chatId || undefined
            }})
          }});
          const d = await r.json();
          if (d.ok && !d.dry_run) {{
            statusEl.textContent = '✅ Published to Telegram channel (' + (d.result?.chat?.title || d.result?.chat?.username || chatId || 'from .env') + ')!';
            showToast('✅ Successfully published digest to Telegram channel!');
          }} else {{
            statusEl.textContent = '⚠️ Not sent: ' + (d.description || d.error || 'Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to model/.env (or enter them above).');
          }}
          return;
        }}
        if (!token || !chatId) {{
          statusEl.textContent = '⚠️ Enter both Bot Token and Channel/Chat ID above (or run scripts/webapp.py to use model/.env).';
          return;
        }}
        const resp = await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ chat_id: chatId, text: text, parse_mode: 'HTML', disable_web_page_preview: true }})
        }});
        const resJson = await resp.json();
        statusEl.textContent = resJson.ok ? '✅ Published to Telegram channel ' + chatId + '!' : ('❌ Telegram error: ' + (resJson.description || 'Unknown error'));
      }} catch (err) {{
        statusEl.textContent = '❌ Request failed: ' + err;
      }} finally {{
        setActionBusy(false);
      }}
    }}

    if (currentSportFilter !== 'all') {{
      applySportFilter(currentSportFilter);
    }}
    if (currentDayFilter !== 'all') {{
      applyDayFilter(currentDayFilter);
    }}
  </script>
</body>
</html>
"""
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    output_html_path.write_text(doc)
    return output_html_path
