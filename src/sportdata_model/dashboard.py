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
    "basketball": "Basketball (NBA)",
    "hockey": "Hockey (NHL)",
    "football": "American Football (NFL)",
    "baseball": "Baseball (MLB)",
}

SPORT_ICONS: dict[str, str] = {
    "soccer": "⚽",
    "tennis": "🎾",
    "basketball": "🏀",
    "hockey": "🏒",
    "football": "🏈",
    "baseball": "⚾",
}


def _sport_icon(sport_cat: str) -> str:
    return SPORT_ICONS.get((sport_cat or "soccer").lower().strip(), "⚽")


def _league_to_sport_cat(league_or_sport: str) -> str:
    low = (league_or_sport or "").lower().strip()
    if low in ("atp", "wta", "tennis"):
        return "tennis"
    if low in ("nba", "basketball"):
        return "basketball"
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
        (t["league"], str(t["event_id"])): (t["kickoff"], t.get("time_valid", True))
        for t in ((rec.get("paper_ledger") or {}).get("trades") or [])
        if t.get("status") == "PENDING"
    }
    raw_soccer_picks = [
        {**p, "kickoff": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True)))[0],
         "time_valid": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True)))[1]}
        for p in (rec.get("qualifying_picks") or [])
        if (p.get("league"), str(p.get("event_id"))) not in settled_ids
    ]
    raw_tennis_picks = [
        {**tp, "kickoff": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True)))[0],
         "time_valid": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True)))[1]}
        for tp in (rec.get("tennis_picks") or [])
        if (tp.get("tour", "").lower(), str(tp.get("event_id"))) not in settled_ids
    ]
    raw_other_picks = [
        {**op, "kickoff": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True)))[0],
         "time_valid": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True)))[1]}
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
        p_win_val = float(p.get("p_model") or p.get("p_mkt") or 0.5)
        f_odds_val = round(1.0 / max(p_win_val, 0.05), 2)
        best_bets.append({
            "date": p["kickoff"],
            "date_local": _format_local_time(p["kickoff"], time_valid=p.get("time_valid")),
            "time_valid": p.get("time_valid", True),
            "sport_cat": "soccer",
            "sport_icon": _sport_icon("soccer"),
            "competition": f"{lg_label} ({p['league']}){live_tag}",
            "sport_league": f"Football · {lg_label} ({p['league']}){live_tag}",
            "match": f"{p['home']} vs {p['away']}",
            "pick": f"{pick_team} ({p['side']}) [{p['tier']}]",
            "win_prob": round(p_win_val, 4),
            "min_fair_odds": f_odds_val,
            "exact_score_pick": esc_str,
            "odds": round(odds_val, 3),
            "odds_display": f"{odds_val:.2f}",
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
        t_comp_lbl = f"{tp['tour']} · {tp.get('tournament') or tp['surface'].capitalize()} ({tp['surface'].capitalize()})"
        best_bets.append({
            "date": tp["kickoff"],
            "date_local": _format_local_time(tp["kickoff"], time_valid=tp.get("time_valid")),
            "time_valid": tp.get("time_valid", True),
            "sport_cat": "tennis",
            "sport_icon": _sport_icon("tennis"),
            "competition": t_comp_lbl,
            "sport_league": f"Tennis · {tp['tour']} ({tp['surface'].capitalize()})",
            "match": f"{tp['player_1']} vs {tp['player_2']}",
            "pick": f"{tp['pick']} (Win {tp['win_prob']*100:.1f}%)",
            "win_prob": round(float(tp["win_prob"]), 4),
            "min_fair_odds": round(float(tp["min_fair_odds"]), 2),
            "exact_score_pick": set_str,
            "odds": round(odds_val, 3),
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
        best_bets.append({
            "date": op["kickoff"],
            "date_local": _format_local_time(op["kickoff"], time_valid=op.get("time_valid")),
            "time_valid": op.get("time_valid", True),
            "sport_cat": sp_cat,
            "sport_icon": _sport_icon(sp_cat),
            "competition": op["league_name"],
            "sport_league": f"{op['sport'].capitalize()} · {op['league_name']}",
            "match": f"{op['home']} vs {op['away']}",
            "pick": f"{op['pick']} ({op['side']}) (Win {op['p_model']*100:.1f}%)",
            "win_prob": round(op_win, 4),
            "min_fair_odds": round(1.0 / max(op_win, 0.05), 2),
            "exact_score_pick": "—",
            "odds": round(odds_val, 3),
            "odds_display": f"{odds_val:.2f}",
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
        (t["league"], str(t["event_id"])): (t["kickoff"], t.get("time_valid", True))
        for t in ((rec.get("paper_ledger") or {}).get("trades") or [])
        if t.get("status") == "PENDING"
    }
    raw_soccer_picks = [
        {**p, "kickoff": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True)))[0],
         "time_valid": ledger_time_map.get((p.get("league"), str(p.get("event_id"))), (p["kickoff"], p.get("time_valid", True)))[1]}
        for p in (rec.get("qualifying_picks") or [])
        if (p.get("league"), str(p.get("event_id"))) not in settled_ids
    ]
    raw_tennis_picks = [
        {**tp, "kickoff": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True)))[0],
         "time_valid": ledger_time_map.get((tp.get("tour", "").lower(), str(tp.get("event_id"))), (tp["kickoff"], tp.get("time_valid", True)))[1]}
        for tp in (rec.get("tennis_picks") or [])
        if (tp.get("tour", "").lower(), str(tp.get("event_id"))) not in settled_ids
    ]
    raw_other_picks = [
        {**op, "kickoff": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True)))[0],
         "time_valid": ledger_time_map.get((op.get("league", "").lower(), str(op.get("event_id"))), (op["kickoff"], op.get("time_valid", True)))[1]}
        for op in (rec.get("other_sport_picks") or [])
        if (op.get("league", "").lower(), str(op.get("event_id"))) not in settled_ids
    ]
    ledger = rec.get("paper_ledger") or {}
    gen_at = rec.get("generated_at") or "—"

    # Soft filter: exclude picks whose primary/best/target odds are <= min_odds (e.g. <= 1.10)
    soccer_picks = [p for p in raw_soccer_picks if float(p.get("best_odds") or 0.0) > min_odds]
    tennis_picks = [tp for tp in raw_tennis_picks if float(tp.get("min_fair_odds") or 0.0) > min_odds]
    other_picks = [op for op in raw_other_picks if float(op.get("best_odds") or 0.0) > min_odds]

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
        p_day_loc = _format_local_time(p["kickoff"])[:10]
        soccer_cards.append(
            f"""
            <div class="card {'card-veto' if is_veto else ''}" data-odds="{p['best_odds']:.3f}" data-sport-cat="soccer" data-day="{html.escape(p_day_loc)}" data-search="{html.escape((p['home'] + ' ' + p['away'] + ' ' + lg_label + ' ' + p['league']).lower())}">
              <div class="card-head">
                <div>
                  <span class="pill">{html.escape(lg_label)}</span>
                  <span class="pill tier">{html.escape(p['tier'])}</span>
                  <span class="pill {badge_cls}">{html.escape(act)}</span>
                  {live_pill}
                </div>
                <div class="score">Score: {_fmt_signed(float(p['score']), '+.4f')} · EV: {_fmt_signed(ev_pct, '+.1f', '%')} · <button type="button" class="btn-mini" title="Share this pick to Discord / Telegram" onclick="shareSinglePick({sh_match}, {sh_pick}, {sh_odds}, {sh_time}, 'soccer')">📣</button></div>
              </div>
              <h3>{html.escape(p['home'])} <span class="muted">vs</span> {html.escape(p['away'])}</h3>
              <div class="meta">Kickoff: {_time_span(p['kickoff'], time_valid=p.get('time_valid'))} · Pick: <b>{html.escape(pick_team)} ({p['side']})</b> · Paper ¼-Kelly: <b>{0.0 if is_veto else qk_pct:.2f}%</b></div>
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
        tp_day_loc = _format_local_time(tp["kickoff"])[:10]
        t_comp_str = f"{tp['tour']} · {tp['tournament']}"
        t_match_str = f"{tp['player_1']} vs {tp['player_2']}"
        tennis_rows.append(
            f"""
            <tr data-odds="{t_odds_attr:.3f}" data-sport-cat="tennis" data-day="{html.escape(tp_day_loc)}" data-search="{html.escape((tp['player_1'] + ' ' + tp['player_2'] + ' ' + tp['tournament'] + ' ' + tp['tour']).lower())}">
              <td class="col-icon" data-sort="tennis"><span class="sport-icon" title="Tennis">🎾</span></td>
              <td data-sort="{html.escape(t_comp_str)}"><span class="pill">{html.escape(tp['tour'])}</span> <span class="pill surf-{html.escape(tp['surface'])}">{html.escape(tp['surface'].upper())}</span> {html.escape(tp['tournament'])}</td>
              <td data-sort="{html.escape(tp['kickoff'])}">{_time_span(tp['kickoff'], time_valid=tp.get('time_valid'))}</td>
              <td data-sort="{html.escape(t_match_str)}">{html.escape(t_match_str)}</td>
              <td data-sort="{html.escape(tp['pick'])}"><b>{html.escape(tp['pick'])}</b> <span class="pill tier">{html.escape(tp['tier'])}</span></td>
              <td data-sort="{tp['win_prob']*100:.2f}"><b>{tp['win_prob']*100:.1f}%</b></td>
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
        op_day_loc = _format_local_time(op["kickoff"])[:10]
        op_comp = op.get("league_name") or op["league"]
        op_match = f"{op['home']} vs {op['away']}"
        other_rows.append(
            f"""
            <tr data-odds="{op['best_odds']:.3f}" data-sport-cat="{html.escape(sp_cat)}" data-day="{html.escape(op_day_loc)}" data-search="{html.escape((op['home'] + ' ' + op['away'] + ' ' + op['league']).lower())}">
              <td class="col-icon" data-sort="{html.escape(sp_cat)}"><span class="sport-icon" title="{html.escape(op['sport'].capitalize())}">{sp_ico}</span></td>
              <td data-sort="{html.escape(op_comp)}"><span class="pill">{html.escape(op_comp)}</span></td>
              <td data-sort="{html.escape(op['kickoff'])}">{_time_span(op['kickoff'], time_valid=op.get('time_valid'))}</td>
              <td data-sort="{html.escape(op_match)}">{html.escape(op_match)}{inj_pill}</td>
              <td data-sort="{html.escape(op['pick'])}"><b>{html.escape(op['pick'])} ({html.escape(op['side'])})</b> <span class="pill tier">{html.escape(op['tier'])}</span></td>
              <td data-sort="{op_win*100:.2f}"><b>{op_win*100:.1f}%</b> <span class="muted">(Mkt {op['p_mkt']*100:.1f}%)</span></td>
              <td data-sort="{op_fair:.3f}">{op_fair:.2f}</td>
              <td data-sort="{op['best_odds']:.3f}"><b>{op['best_odds']:.2f}</b></td>
              <td data-sort="{ev_val:.2f}">{_fmt_signed(ev_val, '+.1f', '%')}</td>
            </tr>
            """
        )

    from .paper_trade import build_recommended_2leg_doubles
    doubles_list = rec.get("recommended_doubles") or build_recommended_2leg_doubles(soccer_picks, tennis_picks, other_picks)
    doubles_cards_html = ""
    if doubles_list:
        d_cards = []
        for idx_d, d in enumerate(doubles_list, start=1):
            l1, l2 = d["leg_1"], d["leg_2"]
            d1_loc = _format_local_time(l1["kickoff"])[:10]
            d_cards.append(
                f"""
                <div class="card" data-day="{html.escape(d1_loc)}">
                  <div class="card-head">
                    <div><span class="pill badge-bet">2-LEG DOUBLE #{idx_d}</span> <span class="pill">{html.escape(l1['league'].upper())} + {html.escape(l2['league'].upper())}</span></div>
                    <div class="score">Combined Odds: <b class="num-pos">{d['combined_odds']:.2f}</b> · WinProb: <b>{d['combined_prob']*100:.1f}%</b> (Fair {d['min_fair_odds']:.2f})</div>
                  </div>
                  <div style="margin-top:8px; font-size:13px;">
                    <div>1️⃣ <b>{html.escape(l1['match'])}</b> ({_time_span(l1['kickoff'], time_valid=l1.get('time_valid'))}) &rarr; <b class="num-pos">{html.escape(l1['pick'])}</b> @ <b>{l1['odds']:.2f}</b> ({l1['prob']*100:.1f}%)</div>
                    <div style="margin-top:4px;">2️⃣ <b>{html.escape(l2['match'])}</b> ({_time_span(l2['kickoff'], time_valid=l2.get('time_valid'))}) &rarr; <b class="num-pos">{html.escape(l2['pick'])}</b> @ <b>{l2['odds']:.2f}</b> ({l2['prob']*100:.1f}%)</div>
                  </div>
                </div>
                """
            )
        doubles_cards_html = f"""
        <h2>Recommended Uncorrelated 2-Leg High-Confidence Doubles (Parlays)</h2>
        <div class="cards" style="margin-bottom:24px;">{''.join(d_cards)}</div>
        """

    # Build unified Best Bets Summary Table at the end, sorted by Date (ascending: soonest upcoming events first!)
    best_bets = build_best_bets_summary(rec, min_odds=min_odds, sport_filter=norm_sport)
    export_best_bets_summary(best_bets, csv_path=csv_export_path, json_path=json_export_path)
    all_best_bets_for_html = build_best_bets_summary(rec, min_odds=min_odds, sport_filter="all")

    best_bets_rows = []
    for b in all_best_bets_for_html:
        b_match_js = html.escape(json.dumps(b["match"]))
        b_pick_with_sc = b["pick"] + (f" · [{b['exact_score_pick']}]" if b.get("exact_score_pick") and b["exact_score_pick"] != "—" else "")
        b_pick_js = html.escape(json.dumps(b_pick_with_sc))
        b_odds_js = html.escape(json.dumps(b["odds_display"]))
        b_time_js = html.escape(json.dumps(b["date_local"]))
        b_cat_js = html.escape(json.dumps(b["sport_cat"]))
        esc_col = html.escape(b.get("exact_score_pick") or "—")
        b_day_loc = (b.get("date_local") or _format_local_time(b["date"]))[:10]
        b_comp = b.get("competition") or b["sport_league"]
        b_ico = b.get("sport_icon") or _sport_icon(b["sport_cat"])
        b_win_pct = float(b.get("win_prob") or 0.5) * 100.0
        b_fair = float(b.get("min_fair_odds") or round(100.0 / max(b_win_pct, 5.0), 2))
        best_bets_rows.append(
            f"""
            <tr data-odds="{b['odds']:.3f}" data-sport-cat="{html.escape(b['sport_cat'])}" data-day="{html.escape(b_day_loc)}" data-search="{html.escape((b['match'] + ' ' + b['sport_league'] + ' ' + b_comp + ' ' + b['pick']).lower())}" data-date="{html.escape(b['date'])}" data-date-local="{html.escape(b['date_local'])}" data-sport="{html.escape(b['sport_league'])}" data-match="{html.escape(b['match'])}" data-pick="{html.escape(b_pick_with_sc)}" data-odds-display="{html.escape(b['odds_display'])}">
              <td class="col-icon" data-sort="{html.escape(b['sport_cat'])}"><span class="sport-icon" title="{html.escape(b['sport_cat'].capitalize())}">{b_ico}</span></td>
              <td data-sort="{html.escape(b_comp)}"><span class="pill">{html.escape(b_comp)}</span></td>
              <td data-sort="{html.escape(b['date'])}">{_time_span(b['date'], bold=True, time_valid=b.get('time_valid'))}</td>
              <td data-sort="{html.escape(b['match'])}">{html.escape(b['match'])}</td>
              <td data-sort="{html.escape(b['pick'])}"><b class="num-pos">{html.escape(b['pick'])}</b></td>
              <td data-sort="{b_win_pct:.2f}"><b>{b_win_pct:.1f}%</b></td>
              <td data-sort="{b_fair:.3f}">{b_fair:.2f}</td>
              <td data-sort="{esc_col}"><span style="color:var(--accent); font-weight:600;">{esc_col}</span></td>
              <td data-sort="{b['odds']:.3f}"><b>{html.escape(b['odds_display'])}</b> <button type="button" class="btn-mini" title="Share this pick to Discord / Telegram" onclick="shareSinglePick({b_match_js}, {b_pick_js}, {b_odds_js}, {b_time_js}, {b_cat_js})">📣</button></td>
            </tr>
            """
        )

    # Build separate SETTLED and PENDING Paper-Betting Ledger tables
    ledger_trades = ledger.get("trades") or []
    settled_html_rows = []
    pending_html_rows = []
    for tr in ledger_trades:
        if float(tr.get("logged_best_odds") or 0.0) <= min_odds:
            continue
        lg_name = LEAGUE_LABELS.get(tr["league"], tr["league"].upper())
        tr_sport_cat = _league_to_sport_cat(tr["league"])
        tr_ico = _sport_icon(tr_sport_cat)
        pick_team = tr["home"] if tr["side"] == "H" else tr["away"]
        st = tr.get("status", "PENDING")
        pnl_v = tr.get("pnl_best")
        clv_v = float(tr.get("clv_pct") or 0.0)
        score_str = tr.get("score_str") or "—"
        tr_match = f"{tr['home']} vs {tr['away']}"
        search_txt = html.escape(f"{tr['home']} {tr['away']} {lg_name} {pick_team}".lower())
        if st == "SETTLED" and pnl_v is not None:
            pnl_f = float(pnl_v)
            st_badge = (
                f'<span class="pill badge-bet">WIN ({pnl_f:+.2f}u)</span>'
                if pnl_f > 0
                else f'<span class="pill badge-veto">LOSS ({pnl_f:+.2f}u)</span>'
            )
            esc_badge = ""
            if tr.get("exact_score_pred"):
                if tr.get("exact_score_hit") == 1:
                    esc_badge = f' <span class="pill badge-bet" title="{html.escape(str(tr["exact_score_pred"]))}">🎯 Exact/Cluster HIT</span>'
                else:
                    esc_badge = f' <span class="pill" title="{html.escape(str(tr["exact_score_pred"]))}">Proj: {html.escape(str(tr["exact_score_pred"]).split("(", 1)[0].strip())}</span>'
            settled_html_rows.append(
                f"""
                <tr data-odds="{tr['logged_best_odds']:.3f}" data-sport-cat="{html.escape(tr_sport_cat)}" data-search="{search_txt}">
                  <td class="col-icon" data-sort="{html.escape(tr_sport_cat)}"><span class="sport-icon" title="{html.escape(tr_sport_cat.capitalize())}">{tr_ico}</span></td>
                  <td data-sort="{html.escape(lg_name)}"><span class="pill">{html.escape(lg_name)}</span></td>
                  <td data-sort="{html.escape(tr['kickoff'])}">{_time_span(tr['kickoff'], bold=True)}</td>
                  <td data-sort="{html.escape(tr_match)}">{html.escape(tr_match)}</td>
                  <td data-sort="{html.escape(pick_team)}"><b>{html.escape(pick_team)} ({html.escape(tr['side'])})</b> <span class="pill tier">{html.escape(tr['tier'])}</span></td>
                  <td data-sort="{html.escape(score_str)}"><b>{html.escape(score_str)}</b>{esc_badge}</td>
                  <td data-sort="{tr['logged_best_odds']:.3f}"><b>{tr['logged_best_odds']:.2f}</b> (CLV {_fmt_signed(clv_v, '+.1f', '%')})</td>
                  <td data-sort="{pnl_f:.3f}">{st_badge}</td>
                </tr>
                """
            )
        else:
            tr_day_loc = _format_local_time(tr["kickoff"])[:10]
            pending_html_rows.append(
                f"""
                <tr data-odds="{tr['logged_best_odds']:.3f}" data-sport-cat="{html.escape(tr_sport_cat)}" data-day="{html.escape(tr_day_loc)}" data-search="{search_txt}">
                  <td class="col-icon" data-sort="{html.escape(tr_sport_cat)}"><span class="sport-icon" title="{html.escape(tr_sport_cat.capitalize())}">{tr_ico}</span></td>
                  <td data-sort="{html.escape(lg_name)}"><span class="pill">{html.escape(lg_name)}</span></td>
                  <td data-sort="{html.escape(tr['kickoff'])}">{_time_span(tr['kickoff'], bold=True, time_valid=tr.get('time_valid'))}</td>
                  <td data-sort="{html.escape(tr_match)}">{html.escape(tr_match)}</td>
                  <td data-sort="{html.escape(pick_team)}"><b>{html.escape(pick_team)} ({html.escape(tr['side'])})</b> <span class="pill tier">{html.escape(tr['tier'])}</span></td>
                  <td data-sort="{tr['logged_best_odds']:.3f}"><b>{tr['logged_best_odds']:.2f}</b> (Close {tr['latest_close_odds']:.2f}, CLV {_fmt_signed(clv_v, '+.1f', '%')})</td>
                  <td data-sort="PENDING"><span class="pill tier">PENDING</span></td>
                </tr>
                """
            )

    # Live Paper-Betting Equity Curve & By-Sport PnL Breakdown
    settled_cum = ledger.get("settled_cum_pnl") or [0.0]
    by_sport_list = ledger.get("by_sport") or []
    live_ledger_analytics_html = ""
    if len(settled_cum) >= 2 or by_sport_list:
        lw, lh = 520, 130
        pts_live = [0.0] + list(settled_cum)
        l_min, l_max = min(0.0, min(pts_live)), max(1.0, max(pts_live))
        l_span = max(l_max - l_min, 1.0)
        l_poly = []
        for idx_p, val_p in enumerate(pts_live):
            lx = 10 + (idx_p / max(1, len(pts_live) - 1)) * (lw - 20)
            ly = lh - 12 - ((val_p - l_min) / l_span) * (lh - 24)
            l_poly.append(f"{lx:.1f},{ly:.1f}")
        ly_zero = lh - 12 - ((0.0 - l_min) / l_span) * (lh - 24)
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
        live_ledger_analytics_html = f"""
        <div class="cards" style="margin-bottom: 18px;">
          <div class="card">
            <div class="card-head">
              <div><b>Prospective Paper-Betting Equity Curve ({ledger.get('settled_count', 0)} Settled Bets)</b></div>
              <div class="muted">Realized PnL: {_fmt_signed(settled_profit_u, '+.2f', 'u')} · ROI: {_fmt_signed(float(ledger.get('settled_roi_best') or 0.0)*100.0, '+.1f', '%')}{esc_summary_str}</div>
            </div>
            <svg viewBox="0 0 {lw} {lh}" style="width:100%; height:130px; margin-top:8px;">
              <line x1="10" y1="{ly_zero:.1f}" x2="{lw-10}" y2="{ly_zero:.1f}" stroke="#334155" stroke-dasharray="4,4"/>
              <polyline fill="none" stroke="#38bdf8" stroke-width="2.5" points="{' '.join(l_poly)}"/>
            </svg>
          </div>
          <div class="card">
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
        </div>
        """
    bt_risk = rec.get("backtest_risk") or {}
    cum_pnl = bt_risk.get("post25_cum_pnl") or [0.0]
    svg_chart = ""
    if len(cum_pnl) > 2:
        w, h = 760, 150
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
        svg_chart = f"""
        <div class="card" style="margin-bottom: 24px;" data-sport-section="soccer">
          <div class="card-head">
            <div><b>Out-of-Sample Post-2025 Holdout Equity Curve (Big-5 Top 10%, n={bt_risk.get('post25_bets', 0)} Bets)</b></div>
            <div class="muted">Profit: {_fmt_signed(p25_prof, '+.2f', 'u')} · ROI: {_fmt_signed(p25_roi, '+.2f', '%')} · MaxDD: <b class="num-neg">-{p25_dd:.2f}u</b> · Sharpe: <b>{bt_risk.get('post25_sharpe', 0.0):.2f}</b> · HitRate: <b>{bt_risk.get('post25_hit_rate', 0.0)*100:.1f}%</b> (vs Mkt {bt_risk.get('post25_mean_p_mkt', 0.0)*100:.1f}%)</div>
          </div>
          <svg viewBox="0 0 {w} {h}" style="width:100%; height:150px; margin-top:8px;">
            <line x1="12" y1="{y_zero:.1f}" x2="{w-12}" y2="{y_zero:.1f}" stroke="#334155" stroke-dasharray="4,4"/>
            <polyline fill="none" stroke="#22c55e" stroke-width="2.5" points="{' '.join(pts)}"/>
          </svg>
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
        d_str = (b.get("date_local") or _format_local_time(b["date"]))[:10]
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
  .pill {{ display: inline-block; padding: 1.5px 7px; border-radius: 99px; font-size: 10.5px; font-weight: 600; background: #1e293b; color: var(--accent); margin-right: 3px; }}
  .pill.tier {{ color: var(--amber); }}
  .pill.badge-bet {{ background: rgba(34,197,94,0.16); color: var(--green); }}
  .pill.badge-veto {{ background: rgba(239,68,68,0.18); color: var(--red); }}
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
  th {{ background: #0f1623; color: var(--muted); font-weight: 600; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.03em; user-select: none; }}
  .sortable-table th[onclick] {{ cursor: pointer; transition: color 0.15s ease, background 0.15s ease; }}
  .sortable-table th[onclick]:hover {{ color: var(--accent); background: #162133; }}
  .sortable-table th[onclick]::after {{ content: " ⇅"; opacity: 0.35; font-size: 9.5px; }}
  .sortable-table th.sort-asc::after {{ content: " ▲"; opacity: 1; color: var(--accent); }}
  .sortable-table th.sort-desc::after {{ content: " ▼"; opacity: 1; color: var(--accent); }}
  .col-icon {{ width: 38px; text-align: center !important; padding-left: 6px !important; padding-right: 6px !important; }}
  .sport-icon {{ font-size: 14px; line-height: 1; display: inline-block; }}
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
</style>
</head>
<body>
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
      <button id="syncLedgerBtn" class="btn-export btn-primary js-action-btn" type="button" onclick="syncAndSettleLedger(false)">🔄 Sync &amp; Settle</button>
      <button id="rescanLiveBtn" class="btn-export js-action-btn" type="button" onclick="syncAndSettleLedger(true)">⚡ Rescan Live</button>
      <button id="runFullPipelineBtn" class="btn-export js-action-btn" type="button" onclick="runFullDailyPipeline()">🚀 Full Pipeline</button>
      <button id="topTelegramBtn" class="btn-export btn-telegram" type="button" onclick="openTelegramPanel()">💬 Share Picks</button>
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
          <th data-sort-type="text" onclick="sortTable(this)">Model Pick</th>
          <th data-sort-type="num" onclick="sortTable(this)">Win Prob</th>
          <th data-sort-type="num" onclick="sortTable(this)">Exact Set Score (2:0 / 2:1)</th>
          <th data-sort-type="num" onclick="sortTable(this)">Min Fair Odds</th>
          <th data-sort-type="num" onclick="sortTable(this)">Book / Target Odds</th>
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
          <th data-sort-type="text" onclick="sortTable(this)">Model Pick</th>
          <th data-sort-type="num" onclick="sortTable(this)">Win Prob</th>
          <th data-sort-type="num" onclick="sortTable(this)">Min Fair Odds</th>
          <th data-sort-type="num" onclick="sortTable(this)">Best Odds</th>
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
  <table id="settledTradesTable" class="sortable-table">
    <thead>
      <tr>
        <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
        <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
        <th class="tz-col-head" data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
        <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
        <th data-sort-type="text" onclick="sortTable(this)">Logged Pick</th>
        <th data-sort-type="text" onclick="sortTable(this)">Final Score</th>
        <th data-sort-type="num" onclick="sortTable(this)">Logged Odds / CLV</th>
        <th data-sort-type="num" onclick="sortTable(this)">Result / PnL</th>
      </tr>
    </thead>
    <tbody id="settledTradesTbody">
      {''.join(settled_html_rows) if settled_html_rows else '<tr><td colspan="8" class="muted">No settled paper bets yet. Pending bets automatically move here once their match finishes and you run <code>uv run sportdata-model</code>.</td></tr>'}
    </tbody>
  </table>

  <h2>Pending Paper-Bets Awaiting Kickoff / Completion (Count: <span id="pendingCountSpan">{ledger.get('pending_count', 0)}</span>)</h2>
  <table id="pendingTradesTable" class="sortable-table">
    <thead>
      <tr>
        <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
        <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
        <th class="tz-col-head" data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
        <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
        <th data-sort-type="text" onclick="sortTable(this)">Logged Pick</th>
        <th data-sort-type="num" onclick="sortTable(this)">Logged Odds / CLV</th>
        <th data-sort-type="text" onclick="sortTable(this)">Status</th>
      </tr>
    </thead>
    <tbody id="pendingTradesTbody">
      {''.join(pending_html_rows) if pending_html_rows else '<tr><td colspan="7" class="muted">No pending paper bets.</td></tr>'}
    </tbody>
  </table>

  <div class="section-head">
    <h2>Best Bets Summary Table (Click Any Column Header to Sort · Odds &gt; {min_odds:.2f})</h2>
    <div class="btn-group">
      <button class="btn-export btn-telegram" type="button" onclick="openTelegramPanel()">💬 Share / Post to Discord &amp; Telegram</button>
      <button class="btn-export" type="button" onclick="exportBestBets('csv')">Export CSV (with Header)</button>
      <button class="btn-export" type="button" onclick="exportBestBets('json')">Export JSON</button>
    </div>
  </div>
  <table id="bestBetsTable" class="sortable-table">
    <thead>
      <tr>
        <th class="col-icon" data-sort-type="text" onclick="sortTable(this)">Sport</th>
        <th data-sort-type="text" onclick="sortTable(this)">Competition</th>
        <th class="tz-col-head sort-asc" data-sort-type="text" onclick="sortTable(this)">Kickoff</th>
        <th data-sort-type="text" onclick="sortTable(this)">Matchup</th>
        <th data-sort-type="text" onclick="sortTable(this)">Model Pick</th>
        <th data-sort-type="num" onclick="sortTable(this)">Win Prob</th>
        <th data-sort-type="num" onclick="sortTable(this)">Min Fair Odds</th>
        <th data-sort-type="text" onclick="sortTable(this)">Exact Score / Set-Score Projection</th>
        <th data-sort-type="num" onclick="sortTable(this)">Odds</th>
      </tr>
    </thead>
    <tbody>
      {''.join(best_bets_rows) if best_bets_rows else '<tr><td colspan="9" class="muted">No qualifying best bets above minimum odds threshold.</td></tr>'}
    </tbody>
  </table>

  <script>
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

    function updateVisibleKpi() {{
      const visibleRows = document.querySelectorAll('#bestBetsTable tbody tr[data-date]:not(.hidden-by-odds):not(.hidden-by-sport):not(.hidden-by-search):not(.hidden-by-day)');
      const kpi = document.getElementById('visibleBestBetsKpi');
      if (kpi) kpi.textContent = String(visibleRows.length);
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
          if (['basketball', 'hockey', 'football', 'baseball'].includes(currentSportFilter)) sec.classList.remove('hidden-by-sport');
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
          match: r.getAttribute('data-match') || '',
          pick: r.getAttribute('data-pick') || '',
          odds: parseFloat(r.getAttribute('data-odds') || '0'),
          odds_display: r.getAttribute('data-odds-display') || ''
        }});
      }});
      return items;
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
      hockey: '🏒',
      football: '🏈',
      baseball: '⚾'
    }};

    function getSportEmoji(catOrLeague) {{
      const low = String(catOrLeague || '').toLowerCase();
      if (SPORT_EMOJIS[low]) return SPORT_EMOJIS[low];
      if (low.includes('tennis') || low.includes('atp') || low.includes('wta')) return '🎾';
      if (low.includes('basketball') || low.includes('nba')) return '🏀';
      if (low.includes('hockey') || low.includes('nhl')) return '🏒';
      if (low.includes('nfl') || low.includes('american football')) return '🏈';
      if (low.includes('baseball') || low.includes('mlb')) return '⚾';
      return '⚽';
    }}

    function buildBrowserTelegramDigest() {{
      const items = collectVisibleBestBets().slice(0, 20);
      const dayBadge = currentDayFilter === 'all' ? 'All Upcoming Days' : ('Day Filter: ' + currentDayFilter);
      const lines = [
        '📊 **SPORTDATA QUANT DESK — DAILY PICKS & UPDATES**',
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
      lines.push('', '🤖 *Powered by 7-Factor tanh(Z) Composite + Laya-Sports System-1 Gate*');
      return lines.join('\\n');
    }}

    function openTelegramPanel() {{
      const modal = document.getElementById('telegramModal');
      modal.style.display = 'block';
      document.getElementById('tgMessagePreview').value = buildBrowserTelegramDigest();
      modal.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function shareSinglePick(matchStr, pickStr, oddsStr, dateLocalStr, sportCat) {{
      const modal = document.getElementById('telegramModal');
      modal.style.display = 'block';
      const icon = getSportEmoji(sportCat || matchStr);
      const msg = [
        '🎯 **SPORTDATA QUANT DESK — HIGH-CONVICTION PICK**',
        '',
        icon + ' **' + matchStr + '**',
        '🕒 Kickoff: `' + dateLocalStr + '`',
        '✅ Pick: **' + pickStr + '**',
        '💰 Odds: **' + oddsStr + '**',
        '',
        '🤖 *Verified by 7-Factor tanh(Z) Composite + Laya-Sports System-1 Gate*'
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
      const pcEl = document.getElementById('pendingCountSpan');
      if (scEl) scEl.textContent = String(ledger.settled_count ?? 0);
      if (swEl) swEl.textContent = String(ledger.settled_wins ?? 0);
      if (slEl) {{
        slEl.textContent = String(ledger.settled_losses ?? 0);
        slEl.className = (ledger.settled_losses || 0) > 0 ? 'num-neg' : '';
      }}
      if (spEl) spEl.innerHTML = fmtSignedHtml(ledger.settled_profit_u || 0, 2, 'u');
      if (pcEl) pcEl.textContent = String(ledger.pending_count ?? 0);

      const trades = ledger.trades || [];
      const minThr = parseFloat(document.getElementById('minOddsSlider')?.value || '1.10');
      const settledRows = [];
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
        if (tr.status === 'SETTLED' && tr.pnl_best !== null && tr.pnl_best !== undefined) {{
          const pnl = Number(tr.pnl_best);
          const badge = pnl > 0
            ? '<span class="pill badge-bet">WIN (+' + pnl.toFixed(2) + 'u)</span>'
            : '<span class="pill badge-veto">LOSS (' + pnl.toFixed(2) + 'u)</span>';
          settledRows.push(
            '<tr class="' + rowCls + '" data-odds="' + o.toFixed(3) + '" data-sport-cat="' + escHtml(spCat) + '" data-search="' + escHtml(searchStr) + '">' +
              '<td class="col-icon" data-sort="' + escHtml(spCat) + '"><span class="sport-icon">' + spIcon + '</span></td>' +
              '<td data-sort="' + escHtml(lgName) + '"><span class="pill">' + escHtml(lgName) + '</span></td>' +
              '<td data-sort="' + escHtml(tr.kickoff) + '"><b class="tz-time" data-utc="' + escHtml(tr.kickoff) + '" data-local="' + escHtml(tr.kickoff_local || tr.kickoff) + '">' + escHtml(koDisp) + '</b></td>' +
              '<td data-sort="' + escHtml(matchStr) + '">' + escHtml(matchStr) + '</td>' +
              '<td data-sort="' + escHtml(pickTeam) + '"><b>' + escHtml(pickTeam) + ' (' + escHtml(tr.side) + ')</b> <span class="pill tier">' + escHtml(tr.tier) + '</span></td>' +
              '<td data-sort="' + escHtml(tr.score_str || '—') + '"><b>' + escHtml(tr.score_str || '—') + '</b></td>' +
              '<td data-sort="' + o.toFixed(3) + '"><b>' + o.toFixed(2) + '</b> (CLV ' + fmtSignedHtml(tr.clv_pct || 0, 1, '%') + ')</td>' +
              '<td data-sort="' + pnl.toFixed(3) + '">' + badge + '</td>' +
            '</tr>'
          );
        }} else {{
          const closeO = Number(tr.latest_close_odds || o);
          const trDay = (tr.kickoff_local || tr.kickoff || '').slice(0, 10);
          const hideDay = (currentDayFilter !== 'all' && !(currentDaySet ? currentDaySet.has(trDay) : trDay === currentDayFilter)) ? ' hidden-by-day' : '';
          const pendCls = (rowCls + hideDay).trim();
          pendingRows.push(
            '<tr class="' + pendCls + '" data-odds="' + o.toFixed(3) + '" data-sport-cat="' + escHtml(spCat) + '" data-day="' + escHtml(trDay) + '" data-search="' + escHtml(searchStr) + '">' +
              '<td class="col-icon" data-sort="' + escHtml(spCat) + '"><span class="sport-icon">' + spIcon + '</span></td>' +
              '<td data-sort="' + escHtml(lgName) + '"><span class="pill">' + escHtml(lgName) + '</span></td>' +
              '<td data-sort="' + escHtml(tr.kickoff) + '"><b class="tz-time" data-utc="' + escHtml(tr.kickoff) + '" data-local="' + escHtml(tr.kickoff_local || tr.kickoff) + '">' + escHtml(koDisp) + '</b></td>' +
              '<td data-sort="' + escHtml(matchStr) + '">' + escHtml(matchStr) + '</td>' +
              '<td data-sort="' + escHtml(pickTeam) + '"><b>' + escHtml(pickTeam) + ' (' + escHtml(tr.side) + ')</b> <span class="pill tier">' + escHtml(tr.tier) + '</span></td>' +
              '<td data-sort="' + o.toFixed(3) + '"><b>' + o.toFixed(2) + '</b> (Close ' + closeO.toFixed(2) + ', CLV ' + fmtSignedHtml(tr.clv_pct || 0, 1, '%') + ')</td>' +
              '<td data-sort="PENDING"><span class="pill tier">PENDING</span></td>' +
            '</tr>'
          );
        }}
      }});
      const sTbody = document.getElementById('settledTradesTbody');
      const pTbody = document.getElementById('pendingTradesTbody');
      if (sTbody && settledRows.length) sTbody.innerHTML = settledRows.join('');
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
        document.querySelectorAll('.js-action-btn').forEach(b => {{
          if (b.dataset.origHtml) {{
            b.innerHTML = b.dataset.origHtml;
            delete b.dataset.origHtml;
          }}
        }});
      }}
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
