"""Enrich the SQLite store from cached ESPN JSON files with boxscore stats, multi-book odds,
opening/closing line movements, and tennis surface/game scores."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .espn import ALL_LEAGUES, EspnClient
from .ingest import (
    _american_book_odds,
    _competitor,
    _line,
    _outcome,
    _parse_soccer_event,
    _parse_tennis_event,
    _score,
    _soccer_odds,
    _team_name,
    _tennis_sets,
    _valid_1x2,
    _valid_2way,
    _valid_totals,
    american_to_decimal,
    deduplicate_same_day,
    fractional_to_decimal,
    normalize_kickoff,
    open_store,
    upsert,
)

DETAILS_SCHEMA = """
CREATE TABLE IF NOT EXISTS match_details (
    league TEXT NOT NULL,
    event_id TEXT NOT NULL,
    sport TEXT NOT NULL,
    kickoff TEXT NOT NULL,
    open_home REAL,
    open_draw REAL,
    open_away REAL,
    close_home REAL,
    close_draw REAL,
    close_away REAL,
    best_home REAL,
    best_draw REAL,
    best_away REAL,
    cons_home REAL,
    cons_draw REAL,
    cons_away REAL,
    num_books INTEGER,
    open_line REAL,
    open_over REAL,
    open_under REAL,
    close_line REAL,
    close_over REAL,
    close_under REAL,
    best_over REAL,
    best_under REAL,
    cons_over REAL,
    home_sot REAL,
    away_sot REAL,
    home_shots REAL,
    away_shots REAL,
    home_corners REAL,
    away_corners REAL,
    home_poss REAL,
    away_poss REAL,
    home_fouls REAL,
    away_fouls REAL,
    home_yellow REAL,
    away_yellow REAL,
    home_red REAL,
    away_red REAL,
    home_pen_goals REAL,
    away_pen_goals REAL,
    ht_home REAL,
    ht_away REAL,
    surface TEXT,
    is_major INTEGER,
    round_name TEXT,
    home_games REAL,
    away_games REAL,
    PRIMARY KEY (league, event_id)
);
CREATE INDEX IF NOT EXISTS idx_details_kickoff ON match_details(sport, kickoff);
"""

CLAY_KEYWORDS = (
    "roland garros", "french open", "monte carlo", "monte-carlo", "madrid", "rome", "internazionali",
    "barcelona", "hamburg", "estoril", "geneva", "lyon", "bastad", "umag", "gstaad", "kitzbuhel",
    "kitzbühel", "bucharest", "munich", "münchen", "rio", "buenos aires", "santiago", "cordoba",
    "córdoba", "charleston", "bogota", "bogotá", "rabat", "palermo", "iasi", "iași", "lausanne",
    "budapest", "marrakech", "houston", "cagliari", "parma", "belgrade", "marbella", "oeiras",
)
GRASS_KEYWORDS = (
    "wimbledon", "halle", "queen's", "queens", "cinch", "stuttgart", "eastbourne", "mallorca",
    "hertogenbosch", "rosmalen", "newport", "berlin", "bad homburg", "nottingham", "birmingham",
    "ilkley", "surbiton",
)


def infer_surface(tournament_name: str) -> str:
    low = (tournament_name or "").lower()
    if any(k in low for k in CLAY_KEYWORDS):
        return "clay"
    if any(k in low for k in GRASS_KEYWORDS):
        return "grass"
    return "hard"


def _parse_node_dec(node: Any) -> float | None:
    if not isinstance(node, dict):
        return None
    if isinstance(node.get("decimal"), (int, float)) and node["decimal"] > 1.01:
        return float(node["decimal"])
    for key in ("odds", "american"):
        if node.get(key) is not None:
            d = american_to_decimal(node.get(key))
            if d and d > 1.01:
                return d
    if node.get("fraction"):
        d = fractional_to_decimal(str(node.get("fraction")))
        if d and d > 1.01:
            return d
    return None


def _extract_soccer_details(league: str, event_id: str, kickoff: str, summary: dict[str, Any]) -> tuple:
    # 1. Multi-book and open/close odds (strictly pre-match; filter out providers that overwrite current with live odds)
    PREMATCH_SAFE_PROVIDERS = {
        "Bet 365", "Bet365", "DraftKings", "DraftKings (old)", "ESPN BET",
        "Caesars Sportsbook (Colorado)", "Caesars Sportsbook (NJ)", "Caesars Sportsbook (Tennessee)",
        "SugarHouse", "PointsBet",
    }
    raw_books_1x2: list[tuple[float, float, float]] = []
    raw_books_ou: list[tuple[float, float, float]] = []
    anchor_prob: tuple[float, float, float] | None = None
    open_1x2: tuple[float, float, float] | None = None
    close_1x2: tuple[float, float, float] | None = None
    open_ou: tuple[float, float, float] | None = None
    close_ou: tuple[float, float, float] | None = None

    for o in summary.get("odds") or []:
        prov = (o.get("provider") or {}).get("name") or ""
        if "Live" in prov or prov not in PREMATCH_SAFE_PROVIDERS:
            continue
        tos = (o.get("bettingOdds") or {}).get("teamOdds") or {}
        if tos:
            bh = fractional_to_decimal((tos.get("preMatchFullTimeResultHome") or {}).get("value"))
            bd = fractional_to_decimal((tos.get("preMatchFullTimeResultDraw") or {}).get("value"))
            ba = fractional_to_decimal((tos.get("preMatchFullTimeResultAway") or {}).get("value"))
            if _valid_1x2(bh, bd, ba):
                raw_books_1x2.append((bh, bd, ba))
                if anchor_prob is None:
                    ih, idr, ia = 1.0 / bh, 1.0 / bd, 1.0 / ba
                    s = ih + idr + ia
                    anchor_prob = (ih / s, idr / s, ia / s)
            bline = _line(tos.get("preMatchOverUnderHandicap"))
            bover = fractional_to_decimal((tos.get("preMatchGoalLineOver") or {}).get("value"))
            bunder = fractional_to_decimal((tos.get("preMatchGoalLineUnder") or {}).get("value"))
            if _valid_totals(bline, bover, bunder):
                raw_books_ou.append((bline, bover, bunder))

        hto = o.get("homeTeamOdds") or {}
        ato = o.get("awayTeamOdds") or {}
        do = o.get("drawOdds") or {}
        ml = o.get("moneyline") or {}

        # Opening 1X2 for this book
        ho = _parse_node_dec((hto.get("open") or {}).get("moneyLine")) or _parse_node_dec((ml.get("home") or {}).get("open"))
        do_op = _parse_node_dec((o.get("open") or {}).get("draw")) or _parse_node_dec((ml.get("draw") or {}).get("open"))
        ao = _parse_node_dec((ato.get("open") or {}).get("moneyLine")) or _parse_node_dec((ml.get("away") or {}).get("open"))
        if _valid_1x2(ho, do_op, ao) and anchor_prob is None:
            ih, idr, ia = 1.0 / ho, 1.0 / do_op, 1.0 / ao
            s = ih + idr + ia
            anchor_prob = (ih / s, idr / s, ia / s)

        # Current / closing 1X2 for this book
        hc = _parse_node_dec((hto.get("current") or {}).get("moneyLine")) or _parse_node_dec((ml.get("home") or {}).get("close")) or american_to_decimal(hto.get("moneyLine"))
        dc = _parse_node_dec((o.get("current") or {}).get("draw")) or _parse_node_dec((ml.get("draw") or {}).get("close")) or american_to_decimal(do.get("moneyLine"))
        ac = _parse_node_dec((ato.get("current") or {}).get("moneyLine")) or _parse_node_dec((ml.get("away") or {}).get("close")) or american_to_decimal(ato.get("moneyLine"))
        if _valid_1x2(hc, dc, ac):
            raw_books_1x2.append((hc, dc, ac))
            if open_1x2 is None and _valid_1x2(ho, do_op, ao):
                # Verify close hasn't been overwritten by in-play odds (max 15pp move from open)
                ih_o, id_o, ia_o = 1.0 / ho, 1.0 / do_op, 1.0 / ao
                so = ih_o + id_o + ia_o
                ih_c, id_c, ia_c = 1.0 / hc, 1.0 / dc, 1.0 / ac
                sc = ih_c + id_c + ia_c
                if max(abs(ih_c / sc - ih_o / so), abs(ia_c / sc - ia_o / so)) <= 0.15:
                    open_1x2 = (ho, do_op, ao)
                    close_1x2 = (hc, dc, ac)

        # Totals open/close
        tot = o.get("total") or {}
        over_op_node = (o.get("open") or {}).get("over") or (tot.get("over") or {}).get("open") or {}
        under_op_node = (o.get("open") or {}).get("under") or (tot.get("under") or {}).get("open") or {}
        over_cl_node = (o.get("current") or {}).get("over") or (tot.get("over") or {}).get("close") or {}
        under_cl_node = (o.get("current") or {}).get("under") or (tot.get("under") or {}).get("close") or {}

        line_c = _line(o.get("overUnder"))
        if line_c is None and isinstance(over_cl_node, dict) and over_cl_node.get("line"):
            line_c = _line(str(over_cl_node.get("line")).lstrip("ouOU"))
        line_o = line_c
        if isinstance((o.get("open") or {}).get("total"), dict):
            line_o = _line(((o.get("open") or {}).get("total") or {}).get("alternateDisplayValue")) or line_c
        elif isinstance(over_op_node, dict) and over_op_node.get("line"):
            line_o = _line(str(over_op_node.get("line")).lstrip("ouOU")) or line_c

        oo = _parse_node_dec(over_op_node)
        uo = _parse_node_dec(under_op_node)
        oc = _parse_node_dec(over_cl_node) or american_to_decimal(o.get("overOdds"))
        uc = _parse_node_dec(under_cl_node) or american_to_decimal(o.get("underOdds"))
        if _valid_totals(line_c, oc, uc):
            raw_books_ou.append((line_c, oc, uc))
            if open_ou is None and _valid_totals(line_o, oo, uo) and line_o == line_c:
                po_ov = (1.0 / oo) / ((1.0 / oo) + (1.0 / uo))
                pc_ov = (1.0 / oc) / ((1.0 / oc) + (1.0 / uc))
                if abs(pc_ov - po_ov) <= 0.15:
                    open_ou = (line_o, oo, uo)
                    close_ou = (line_c, oc, uc)

    # Filter books_1x2 against anchor_prob (or median) so no stale/in-play book pollutes best_*
    books_1x2: list[tuple[float, float, float]] = []
    if raw_books_1x2:
        if anchor_prob is None:
            med_h = sorted(1.0 / b[0] for b in raw_books_1x2)[len(raw_books_1x2) // 2]
            med_d = sorted(1.0 / b[1] for b in raw_books_1x2)[len(raw_books_1x2) // 2]
            med_a = sorted(1.0 / b[2] for b in raw_books_1x2)[len(raw_books_1x2) // 2]
            s = med_h + med_d + med_a
            anchor_prob = (med_h / s, med_d / s, med_a / s)
        for bh, bd, ba in raw_books_1x2:
            ih, idr, ia = 1.0 / bh, 1.0 / bd, 1.0 / ba
            s = ih + idr + ia
            if max(abs(ih / s - anchor_prob[0]), abs(idr / s - anchor_prob[1]), abs(ia / s - anchor_prob[2])) <= 0.08:
                books_1x2.append((bh, bd, ba))

    books_ou = raw_books_ou

    best_h = max((b[0] for b in books_1x2), default=None)
    best_d = max((b[1] for b in books_1x2), default=None)
    best_a = max((b[2] for b in books_1x2), default=None)
    cons_h = cons_d = cons_a = None
    if books_1x2:
        probs = []
        for bh, bd, ba in books_1x2:
            ih, idr, ia = 1.0 / bh, 1.0 / bd, 1.0 / ba
            s = ih + idr + ia
            probs.append((ih / s, idr / s, ia / s))
        cons_h = sum(p[0] for p in probs) / len(probs)
        cons_d = sum(p[1] for p in probs) / len(probs)
        cons_a = sum(p[2] for p in probs) / len(probs)

    best_over = best_under = cons_over = None
    if books_ou:
        target_line = books_ou[0][0]
        same_line = [b for b in books_ou if b[0] == target_line]
        best_over = max(b[1] for b in same_line)
        best_under = max(b[2] for b in same_line)
        p_overs = [(1.0 / b[1]) / ((1.0 / b[1]) + (1.0 / b[2])) for b in same_line]
        cons_over = sum(p_overs) / len(p_overs)

    # 2. Boxscore team statistics
    stats_by_side: dict[str, dict[str, float]] = {"home": {}, "away": {}}
    hdr_comps = (summary.get("header") or {}).get("competitions") or []
    team_id_to_side: dict[str, str] = {}
    ht_scores: dict[str, float | None] = {"home": None, "away": None}
    if hdr_comps:
        for c in hdr_comps[0].get("competitors") or []:
            side = c.get("homeAway")
            tid = str((c.get("team") or {}).get("id") or c.get("id") or "")
            if side in ("home", "away") and tid:
                team_id_to_side[tid] = side
            ls = c.get("linescores") or []
            if side in ("home", "away") and ls:
                try:
                    ht_scores[side] = float(ls[0].get("displayValue") or ls[0].get("value"))
                except (TypeError, ValueError):
                    pass

    for t in (summary.get("boxscore") or {}).get("teams") or []:
        side = t.get("homeAway")
        if side not in ("home", "away"):
            tid = str((t.get("team") or {}).get("id") or "")
            side = team_id_to_side.get(tid)
        if side not in ("home", "away"):
            continue
        smap = {}
        for st in t.get("statistics") or []:
            name = st.get("name")
            val = st.get("displayValue")
            if name and val is not None:
                try:
                    smap[name] = float(str(val).replace("%", "").strip())
                except ValueError:
                    pass
        stats_by_side[side] = smap

    hs, as_ = stats_by_side["home"], stats_by_side["away"]
    return (
        league, event_id, "soccer", kickoff,
        open_1x2[0] if open_1x2 else None,
        open_1x2[1] if open_1x2 else None,
        open_1x2[2] if open_1x2 else None,
        close_1x2[0] if close_1x2 else None,
        close_1x2[1] if close_1x2 else None,
        close_1x2[2] if close_1x2 else None,
        best_h, best_d, best_a,
        cons_h, cons_d, cons_a,
        len(books_1x2),
        open_ou[0] if open_ou else None,
        open_ou[1] if open_ou else None,
        open_ou[2] if open_ou else None,
        close_ou[0] if close_ou else None,
        close_ou[1] if close_ou else None,
        close_ou[2] if close_ou else None,
        best_over, best_under, cons_over,
        hs.get("shotsOnTarget"), as_.get("shotsOnTarget"),
        hs.get("totalShots"), as_.get("totalShots"),
        hs.get("wonCorners"), as_.get("wonCorners"),
        hs.get("possessionPct"), as_.get("possessionPct"),
        hs.get("foulsCommitted"), as_.get("foulsCommitted"),
        hs.get("yellowCards"), as_.get("yellowCards"),
        hs.get("redCards"), as_.get("redCards"),
        hs.get("penaltyKickGoals"), as_.get("penaltyKickGoals"),
        ht_scores["home"], ht_scores["away"],
        None, None, None, None, None,
    )


def _extract_two_way_details(sport: str, league: str, event_id: str, kickoff: str, summary: dict[str, Any]) -> tuple:
    """Extract multi-book and opening/closing 2-way moneylines and totals for NBA, NHL, NFL, MLB."""
    books_2way: list[tuple[float, float]] = []
    books_ou: list[tuple[float, float, float]] = []
    open_2way: tuple[float, float] | None = None
    close_2way: tuple[float, float] | None = None
    open_ou: tuple[float, float, float] | None = None
    close_ou: tuple[float, float, float] | None = None

    odds_list = (summary.get("pickcenter") or []) + (summary.get("odds") or [])
    for o in odds_list:
        if not isinstance(o, dict):
            continue
        prov = (o.get("provider") or {}).get("name") or ""
        if "Live" in prov:
            continue
        hto = o.get("homeTeamOdds") or {}
        ato = o.get("awayTeamOdds") or {}
        ml = o.get("moneyline") or {}

        ho = _parse_node_dec((hto.get("open") or {}).get("moneyLine")) or _parse_node_dec((ml.get("home") or {}).get("open"))
        ao = _parse_node_dec((ato.get("open") or {}).get("moneyLine")) or _parse_node_dec((ml.get("away") or {}).get("open"))
        hc = _parse_node_dec((hto.get("current") or {}).get("moneyLine")) or _parse_node_dec((ml.get("home") or {}).get("close")) or american_to_decimal(hto.get("moneyLine"))
        ac = _parse_node_dec((ato.get("current") or {}).get("moneyLine")) or _parse_node_dec((ml.get("away") or {}).get("close")) or american_to_decimal(ato.get("moneyLine"))

        if _valid_2way(hc, ac):
            books_2way.append((hc, ac))
            if open_2way is None and _valid_2way(ho, ao):
                open_2way = (ho, ao)
                close_2way = (hc, ac)

        tot = o.get("total") or {}
        over_op_node = (o.get("open") or {}).get("over") or (tot.get("over") or {}).get("open") or {}
        under_op_node = (o.get("open") or {}).get("under") or (tot.get("under") or {}).get("open") or {}
        over_cl_node = (o.get("current") or {}).get("over") or (tot.get("over") or {}).get("close") or {}
        under_cl_node = (o.get("current") or {}).get("under") or (tot.get("under") or {}).get("close") or {}

        line_c = _line(o.get("overUnder"))
        if line_c is None and isinstance(over_cl_node, dict) and over_cl_node.get("line"):
            line_c = _line(str(over_cl_node.get("line")).lstrip("ouOU"))
        line_o = line_c
        if isinstance(over_op_node, dict) and over_op_node.get("line"):
            line_o = _line(str(over_op_node.get("line")).lstrip("ouOU")) or line_c

        oo = _parse_node_dec(over_op_node)
        uo = _parse_node_dec(under_op_node)
        oc = _parse_node_dec(over_cl_node) or american_to_decimal(o.get("overOdds"))
        uc = _parse_node_dec(under_cl_node) or american_to_decimal(o.get("underOdds"))
        if _valid_totals(line_c, oc, uc, sport=sport):
            books_ou.append((line_c, oc, uc))
            if open_ou is None and _valid_totals(line_o, oo, uo, sport=sport):
                open_ou = (line_o, oo, uo)
                close_ou = (line_c, oc, uc)

    best_h = max((b[0] for b in books_2way), default=None)
    best_a = max((b[1] for b in books_2way), default=None)
    cons_h = cons_a = None
    if books_2way:
        probs = [(1.0 / bh) / (1.0 / bh + 1.0 / ba) for bh, ba in books_2way]
        cons_h = sum(probs) / len(probs)
        cons_a = 1.0 - cons_h

    best_over = best_under = cons_over = None
    if books_ou:
        target_line = books_ou[0][0]
        same_line = [b for b in books_ou if b[0] == target_line]
        best_over = max(b[1] for b in same_line)
        best_under = max(b[2] for b in same_line)
        p_overs = [(1.0 / b[1]) / ((1.0 / b[1]) + (1.0 / b[2])) for b in same_line]
        cons_over = sum(p_overs) / len(p_overs)

    # Extract sport-specific boxscore efficiency, volume, creation, control & turnover metrics
    stats_by_side: dict[str, dict[str, float]] = {"home": {}, "away": {}}
    for t in (summary.get("boxscore") or {}).get("teams") or []:
        side = t.get("homeAway")
        if side not in ("home", "away"):
            continue
        smap: dict[str, float] = {}
        for st in t.get("statistics") or []:
            if isinstance(st.get("stats"), list):
                cat_name = st.get("name") or ""
                for inner in st.get("stats") or []:
                    iname = f"{cat_name}.{inner.get('name')}"
                    ival = inner.get("displayValue")
                    if ival is not None:
                        try:
                            smap[iname] = float(str(ival).replace("%", "").strip())
                        except ValueError:
                            pass
            else:
                name = st.get("name")
                val = st.get("displayValue")
                if name and val is not None:
                    try:
                        smap[name] = float(str(val).replace("%", "").strip())
                    except ValueError:
                        pass
        stats_by_side[side] = smap

    hs, as_ = stats_by_side["home"], stats_by_side["away"]
    if sport == "basketball":
        h_sot, a_sot = hs.get("fieldGoalPct"), as_.get("fieldGoalPct")
        h_sh, a_sh = hs.get("totalRebounds"), as_.get("totalRebounds")
        h_co, a_co = hs.get("assists"), as_.get("assists")
        h_po, a_po = hs.get("threePointFieldGoalPct"), as_.get("threePointFieldGoalPct")
        h_fo, a_fo = hs.get("totalTurnovers") or hs.get("turnovers"), as_.get("totalTurnovers") or as_.get("turnovers")
    elif sport == "hockey":
        h_sot, a_sot = hs.get("shotsTotal"), as_.get("shotsTotal")
        h_sh = (hs.get("shotsTotal", 0.0) + hs.get("blockedShots", 0.0)) if "shotsTotal" in hs else None
        a_sh = (as_.get("shotsTotal", 0.0) + as_.get("blockedShots", 0.0)) if "shotsTotal" in as_ else None
        h_co, a_co = hs.get("powerPlayOpportunities"), as_.get("powerPlayOpportunities")
        h_po, a_po = hs.get("faceoffPercent"), as_.get("faceoffPercent")
        h_fo = (hs.get("giveaways", 0.0) + hs.get("penalties", 0.0)) if ("giveaways" in hs or "penalties" in hs) else None
        a_fo = (as_.get("giveaways", 0.0) + as_.get("penalties", 0.0)) if ("giveaways" in as_ or "penalties" in as_) else None
    elif sport == "football":
        h_sot, a_sot = hs.get("yardsPerPlay"), as_.get("yardsPerPlay")
        h_sh, a_sh = hs.get("totalYards"), as_.get("totalYards")
        h_co, a_co = hs.get("firstDowns"), as_.get("firstDowns")
        h_po, a_po = hs.get("netPassingYards"), as_.get("netPassingYards")
        h_fo, a_fo = hs.get("turnovers") or hs.get("interceptions"), as_.get("turnovers") or as_.get("interceptions")
    else:  # baseball
        h_sot, a_sot = hs.get("batting.hits"), as_.get("batting.hits")
        h_sh, a_sh = hs.get("pitching.strikeouts"), as_.get("pitching.strikeouts")
        h_co, a_co = hs.get("batting.RBIs"), as_.get("batting.RBIs")
        h_po, a_po = None, None
        h_fo = (hs.get("batting.strikeouts", 0.0) + hs.get("fielding.errors", 0.0)) if "batting.hits" in hs else None
        a_fo = (as_.get("batting.strikeouts", 0.0) + as_.get("fielding.errors", 0.0)) if "batting.hits" in as_ else None

    return (
        league, event_id, sport, normalize_kickoff(kickoff),
        open_2way[0] if open_2way else None,
        None,
        open_2way[1] if open_2way else None,
        close_2way[0] if close_2way else None,
        None,
        close_2way[1] if close_2way else None,
        best_h, None, best_a,
        cons_h, None, cons_a,
        len(books_2way),
        open_ou[0] if open_ou else None,
        open_ou[1] if open_ou else None,
        open_ou[2] if open_ou else None,
        close_ou[0] if close_ou else None,
        close_ou[1] if close_ou else None,
        close_ou[2] if close_ou else None,
        best_over, best_under, cons_over,
        h_sot, a_sot,
        h_sh, a_sh,
        h_co, a_co,
        h_po, a_po,
        h_fo, a_fo,
        None, None, None, None, None, None, None, None,
        None, None, None, None, None,
    )


def sync_recent_completed_matches(
    db_path: Path,
    cache_dir: Path,
    lookback_days: int = 5,
    now_dt: datetime | None = None,
) -> dict[str, int]:
    """Incrementally fetch and enrich completed matches over the last `lookback_days` across all leagues."""
    client = EspnClient(cache_dir)
    conn = open_store(db_path)
    conn.executescript(DETAILS_SCHEMA)
    base_dt = now_dt or datetime.now(timezone.utc)
    days = [(base_dt - timedelta(days=d)).strftime("%Y%m%d") for d in range(1, lookback_days + 1)]

    added_counts: dict[str, int] = {}
    detail_rows: list[tuple] = []

    for lg in ALL_LEAGUES:
        matches = []
        for ymd in days:
            try:
                board = client.scoreboard(lg, ymd)
            except Exception:
                continue
            if lg.sport == "soccer":
                for ev in board.get("events") or []:
                    if not (ev.get("status") or {}).get("type", {}).get("completed"):
                        continue
                    eid = str(ev["id"])
                    try:
                        summary = client.summary(lg, eid)
                    except Exception:
                        continue
                    m = _parse_soccer_event(lg, ev, summary)
                    if m:
                        matches.append(m)
                        detail_rows.append(_extract_soccer_details(lg.key, eid, m.kickoff, summary))
            else:
                wanted = {"atp": "mens-singles", "wta": "womens-singles"}.get(lg.key)
                for tourn in board.get("events") or []:
                    surf = infer_surface(tourn.get("name") or "")
                    is_maj = 1 if tourn.get("major") else 0
                    for grp in tourn.get("groupings") or []:
                        if (grp.get("grouping") or {}).get("slug") != wanted:
                            continue
                        for comp in grp.get("competitions") or []:
                            m = _parse_tennis_event(lg, tourn, grp, comp)
                            if not m:
                                continue
                            matches.append(m)
                            p1, p2 = _competitor(comp, "home"), _competitor(comp, "away")
                            g1 = sum(float(x.get("value") or 0) for x in ((p1 or {}).get("linescores") or []) if x.get("value") is not None)
                            g2 = sum(float(x.get("value") or 0) for x in ((p2 or {}).get("linescores") or []) if x.get("value") is not None)
                            rnd = (comp.get("round") or {}).get("displayName")
                            detail_rows.append((
                                lg.key, m.event_id, "tennis", m.kickoff,
                                None, None, None, None, None, None, None, None, None, None, None, None, 0,
                                None, None, None, None, None, None, None, None, None,
                                None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
                                surf, is_maj, rnd, g1 if (g1 or g2) else None, g2 if (g1 or g2) else None,
                            ))
        if matches:
            upsert(conn, matches)
        added_counts[lg.key] = len(matches)

    if detail_rows:
        conn.executemany(
            "INSERT OR REPLACE INTO match_details VALUES (" + ",".join("?" * 49) + ")",
            detail_rows,
        )
        conn.execute(
            "DELETE FROM match_details WHERE (league, event_id) NOT IN (SELECT league, event_id FROM matches)"
        )
        conn.commit()
    conn.close()
    return added_counts


def refresh_soccer_details(db_path: Path, cache_dir: Path) -> int:
    """Fast refresh of soccer and 2-way team sport rows in match_details from cached summary JSONs."""
    conn = open_store(db_path)
    conn.executescript(DETAILS_SCHEMA)
    team_matches = conn.execute(
        "SELECT sport, league, event_id, kickoff FROM matches WHERE sport != 'tennis'"
    ).fetchall()
    detail_rows = []
    for sp, lg, eid, ko in team_matches:
        sum_file = cache_dir / f"sum_{lg}_{eid}.json"
        if not sum_file.exists():
            continue
        try:
            summary = json.loads(sum_file.read_text())
        except Exception:
            continue
        if sp == "soccer":
            detail_rows.append(_extract_soccer_details(lg, eid, ko, summary))
        else:
            detail_rows.append(_extract_two_way_details(sp, lg, eid, ko, summary))
    conn.execute("DELETE FROM match_details WHERE sport != 'tennis'")
    conn.executemany(
        "INSERT OR REPLACE INTO match_details VALUES (" + ",".join("?" * 49) + ")",
        detail_rows,
    )
    conn.commit()
    conn.close()
    return len(detail_rows)


def rebuild_all_from_cache(db_path: Path, cache_dir: Path) -> dict[str, int]:
    """Rebuild and enrich `matches` and `match_details` from cached scoreboard and summary JSONs."""
    conn = open_store(db_path)
    conn.executescript(DETAILS_SCHEMA)
    conn.execute("DELETE FROM matches")
    conn.execute("DELETE FROM match_details")

    match_rows: list[tuple] = []
    detail_rows: list[tuple] = []

    # 1. Process all cached scoreboards
    for sb_file in sorted(cache_dir.glob("sb_*.json")):
        parts = sb_file.stem.split("_")
        if len(parts) < 3:
            continue
        league_key = "_".join(parts[1:-1])
        try:
            board = json.loads(sb_file.read_text())
        except Exception:
            continue

        if league_key in ("atp", "wta"):
            wanted = {"atp": "mens-singles", "wta": "womens-singles"}[league_key]
            for tournament in board.get("events") or []:
                t_name = tournament.get("name") or ""
                surface = infer_surface(t_name)
                is_major = 1 if tournament.get("major") else 0
                for grouping in tournament.get("groupings") or []:
                    if (grouping.get("grouping") or {}).get("slug") != wanted:
                        continue
                    for comp in grouping.get("competitions") or []:
                        p1, p2 = _competitor(comp, "home"), _competitor(comp, "away")
                        if not p1 or not p2:
                            continue
                        completed = (comp.get("status") or {}).get("type", {}).get("completed")
                        if not completed or not (p1.get("winner") or p2.get("winner")):
                            continue
                        h_name, a_name = _team_name(p1).strip(), _team_name(p2).strip()
                        if not h_name or not a_name or h_name == a_name:
                            continue
                        outcome = "H" if p1.get("winner") else "A"
                        s1, s2 = _tennis_sets(p1), _tennis_sets(p2)
                        if s1 is not None and s2 is not None:
                            if (outcome == "H" and s1 <= s2) or (outcome == "A" and s2 <= s1):
                                s1, s2 = None, None
                        g1 = sum(float(x.get("value") or 0) for x in (p1.get("linescores") or []) if x.get("value") is not None)
                        g2 = sum(float(x.get("value") or 0) for x in (p2.get("linescores") or []) if x.get("value") is not None)
                        rnd = (comp.get("round") or {}).get("displayName")
                        eid = str(comp["id"])
                        ko = comp["date"]
                        match_rows.append((
                            eid, league_key, "tennis", ko, h_name, a_name, s1, s2, outcome,
                            None, None, None, None, None, None, None, None, None, None,
                        ))
                        detail_rows.append((
                            league_key, eid, "tennis", ko,
                            None, None, None, None, None, None, None, None, None, None, None, None, 0,
                            None, None, None, None, None, None, None, None, None,
                            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
                            surface, is_major, rnd, g1 if (g1 or g2) else None, g2 if (g1 or g2) else None,
                        ))
        else:
            for ev in board.get("events") or []:
                if not (ev.get("status") or {}).get("type", {}).get("completed"):
                    continue
                comp = (ev.get("competitions") or [{}])[0]
                home, away = _competitor(comp, "home"), _competitor(comp, "away")
                if not home or not away:
                    continue
                h_name, a_name = _team_name(home).strip(), _team_name(away).strip()
                if not h_name or not a_name or h_name == a_name:
                    continue
                hs, as_ = _score(home), _score(away)
                out = _outcome(hs, as_)
                if out is None:
                    continue
                eid = str(ev["id"])
                ko = ev["date"]
                sum_file = cache_dir / f"sum_{league_key}_{eid}.json"
                summary = {}
                if sum_file.exists():
                    try:
                        summary = json.loads(sum_file.read_text())
                    except Exception:
                        summary = {}
                prices = _soccer_odds(summary)
                match_rows.append((
                    eid, league_key, "soccer", ko, h_name, a_name, hs, as_, out,
                    prices["odds_home"], prices["odds_draw"], prices["odds_away"], prices["odds_provider"],
                    prices["odds_dc_1x"], prices["odds_dc_x2"], prices["odds_dc_12"],
                    prices["line_total"], prices["odds_over"], prices["odds_under"],
                ))
                if summary:
                    detail_rows.append(_extract_soccer_details(league_key, eid, ko, summary))

    conn.executemany(
        "INSERT OR REPLACE INTO matches VALUES (" + ",".join("?" * 19) + ")",
        match_rows,
    )
    deduplicate_same_day(conn)
    conn.executemany(
        "INSERT OR REPLACE INTO match_details VALUES (" + ",".join("?" * 49) + ")",
        detail_rows,
    )
    # Remove any orphan details from deduplicated matches
    conn.execute(
        "DELETE FROM match_details WHERE (league, event_id) NOT IN (SELECT league, event_id FROM matches)"
    )
    conn.commit()
    counts = dict(conn.execute("SELECT league, COUNT(*) FROM matches GROUP BY league").fetchall())
    conn.close()
    return counts
