"""Model Context Protocol (MCP) JSON-RPC 2.0 handler for the BetScout Quant API (`/mcp` & `/api/mcp`).

Exposes 7 deep, model-oriented tools backed by BetScout's quantitative models, SQLite paper-betting ledger,
and 2-tier cached Sportradar/Tipico SDK (`betscout_sdk`):
  1. `get_daily_banker_picks`
  2. `get_banker_profit_boosters`
  3. `analyze_matchup`
  4. `calculate_exact_score_dutching`
  5. `get_match_center_dossier`
  6. `search_daily_fixtures`
  7. `get_paper_ledger_roi`
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from .sportradar_statshub import (
    get_daily_tipico_match_index,
    get_gismo_cache_stats,
    get_sdk_client,
)

MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_INFO = {
    "name": "betscout-mcp-server",
    "version": "1.1.0",
}


def encode_cursor(offset: int) -> str:
    raw = json.dumps({"o": int(max(0, offset))}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor or not str(cursor).strip():
        return 0
    s = str(cursor).strip()
    pad = "=" * ((4 - len(s) % 4) % 4)
    try:
        raw = base64.urlsafe_b64decode((s + pad).encode("ascii"))
        obj = json.loads(raw.decode("utf-8"))
        val = int(obj.get("o", 0))
        if val < 0:
            raise ValueError("Negative offset")
        return val
    except Exception as exc:
        raise ValueError(
            f"Invalid pagination cursor '{cursor}'. Omit `cursor` to start from the first batch of results."
        ) from exc


def paginate_items(items: list[Any], cursor: str | None = None, limit: int = 15) -> dict[str, Any]:
    offset = decode_cursor(cursor)
    page_size = max(1, min(int(limit or 15), 50))
    sliced = items[offset : offset + page_size]
    next_offset = offset + page_size
    has_more = next_offset < len(items)
    next_cursor = encode_cursor(next_offset) if has_more else None
    return {
        "items": sliced,
        "returned_count": len(sliced),
        "total_available": len(items),
        "has_more": has_more,
        "next_cursor": next_cursor,
        "pagination_hint": (
            f"More results available. Pass `cursor: \"{next_cursor}\"` to retrieve the next batch."
            if next_cursor
            else "All matching results returned."
        ),
    }


MCP_TOOLS_CATALOG: list[dict[str, Any]] = [
    {
        "name": "get_daily_banker_picks",
        "description": (
            "Retrieve BetScout's active pre-match and live high-conviction picks across Football, Tennis, "
            "Basketball (NBA), Ice Hockey (NHL), American Football (NFL), Handball, Table Tennis, and Darts. "
            "Use this tool when the user asks for today's best bets, high-probability banker recommendations, "
            "mispriced bookmaker edges, or sport-specific slates. Do NOT use this tool to analyze an arbitrary "
            "unscheduled matchup — use `analyze_matchup` for custom team/player matchups instead."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sport": {
                    "type": "string",
                    "description": "Filter by sport category ('all', 'soccer', 'tennis', 'basketball', 'hockey', 'nfl', 'handball', 'table_tennis', 'darts'). Default: 'all'.",
                    "enum": [
                        "all",
                        "soccer",
                        "tennis",
                        "basketball",
                        "hockey",
                        "nfl",
                        "handball",
                        "table_tennis",
                        "darts",
                    ],
                },
                "market_filter": {
                    "type": "string",
                    "description": "Filter by market type ('all', 'moneyline', 'secondary', 'shield', 'totals'). 'shield' returns Double Chance (1X/X2), Draw No Bet (DNB), and Tennis +1.5 Sets shields; 'totals' returns Over/Under Goals & Games; 'secondary' returns all non-moneyline opportunities. Default: 'all'.",
                    "enum": ["all", "moneyline", "secondary", "shield", "totals"],
                },
                "min_odds": {
                    "type": "number",
                    "description": "Minimum decimal bookmaker odds threshold (e.g. 1.15, 1.25). Default: 1.10.",
                },
                "min_win_prob": {
                    "type": "number",
                    "description": "Minimum calibrated model win probability between 0.50 and 0.99 (e.g. 0.70 for >=70%). Default: 0.55.",
                },
                "mispriced_only": {
                    "type": "boolean",
                    "description": "When true, return only picks where model probability exceeds vig-free market probability by >=2.0pp with positive EV.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of picks to return per call (1-50). Default: 15.",
                },
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor returned as `next_cursor` from a previous call.",
                },
            },
        },
    },
    {
        "name": "get_banker_profit_boosters",
        "description": (
            "Construct 2-leg and 3-leg high-probability (>=72% win prob, 1.10-1.48 decimal odds) Banker Profitability "
            "Booster combo tickets and quarter-Kelly stake allocations for a given bankroll budget in EUR. "
            "Use this tool when the user wants parlay/double/treble recommendations that combine low-odds favorites "
            "into higher-yielding 1.35x-2.15x tickets without same-match correlation. Do NOT use this tool for "
            "single-match exact-score dutching — use `calculate_exact_score_dutching` instead."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "budget_eur": {
                    "type": "number",
                    "description": "Total bankroll/ticket budget in EUR to allocate across recommended combo tickets (e.g. 100). Default: 100.",
                },
                "max_combos": {
                    "type": "integer",
                    "description": "Maximum number of combo tickets to return (1-10). Default: 6.",
                },
            },
        },
    },
    {
        "name": "analyze_matchup",
        "description": (
            "Run BetScout's live quantitative model (7-factor Football Composite + Dixon-Coles 28-score matrix, or "
            "8-feature Tennis Surface Elo + Markov Set-Score engine) on ANY two teams or players (e.g. 'Medvedev vs Norrie', "
            "'Tommy Paul vs Luciano Darderi', 'AS Roma vs Cagliari'). Use this tool when the user asks about a specific "
            "matchup's win probability, fixed set score ('2:0' / '0:2' / '2:1'), '+1.5 Sets' shield, total games/goals "
            "over/under, or safety-gate warnings. Do NOT use this tool if you only have a numeric match ID and want "
            "raw point-by-point boxscores — use `get_match_center_dossier` for match IDs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Matchup query formatted as 'Player1 vs Player2' or 'HomeTeam vs AwayTeam' (e.g. 'Daniil Medvedev vs Cameron Norrie', 'Tommy Paul vs Luciano Darderi').",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculate_exact_score_dutching",
        "description": (
            "Compute an equal-payout Dutching stake split across the top Exact Scores (Football 1:0 / 2:0 / 2:1) or "
            "Set Scores (Tennis 2:0 + 2:1) for a specific matchup and total stake in EUR. Use this tool when the user "
            "wants to divide a stake across 2 or 3 exact scores or set results so every winning outcome returns the "
            "exact same EUR payout. Do NOT use this tool for multi-match parlays — use `get_banker_profit_boosters` instead."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Matchup query formatted as 'Home vs Away' (e.g. 'AS Roma vs Cagliari', 'Valentin Vacherot vs Rafael Jodar').",
                },
                "stake_eur": {
                    "type": "number",
                    "description": "Total EUR stake to split across the exact score / set score cluster (e.g. 25, 50, 100). Default: 25.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_match_center_dossier",
        "description": (
            "Fetch the complete Match Center intelligence dossier for a specific match (by numeric `match_id` or "
            "`home` + `away` names), returning de-vigged 2-way/3-way win probabilities, bookmaker markets (1X2, Asian "
            "Handicap, Over/Under, 28 Correct Scores), direct Head-to-Head (H2H) history, Last-5 W/D/L form strips, "
            "surface or season scoring splits, missing/injured players, and live boxscore statistics. Use this tool "
            "for deep match inspection, H2H verification, injury audits, or live boxscores. Do NOT use this tool to "
            "browse a full day's schedule — call `search_daily_fixtures` first if you need to discover a `match_id`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "match_id": {
                    "type": "integer",
                    "description": "Numeric Sportradar match ID (e.g. 71945350 for Genoa vs Juventus, 75837638 for Paul vs Darderi). Provide `match_id` OR both `home` and `away`.",
                },
                "home": {
                    "type": "string",
                    "description": "Home team or Player 1 name when `match_id` is unknown (e.g. 'Genoa', 'Tommy Paul').",
                },
                "away": {
                    "type": "string",
                    "description": "Away team or Player 2 name when `match_id` is unknown (e.g. 'Juventus', 'Luciano Darderi').",
                },
                "sport": {
                    "type": "string",
                    "description": "Sport hint when looking up by team/player names ('soccer', 'tennis', 'basketball', 'hockey', 'handball', 'table_tennis', 'darts'). Default: 'soccer'.",
                },
            },
        },
    },
    {
        "name": "search_daily_fixtures",
        "description": (
            "Search and list scheduled, live, and finished fixtures across 56 sports for a given date (`YYYY-MM-DD`) "
            "and sport (e.g. 'soccer', 'tennis', 'basketball', 'hockey', 'handball', 'table_tennis', 'darts'), "
            "returning numeric `match_id` values, tournament names, kickoff times, scores, and pre-match odds. "
            "Use this tool to find a `match_id` or inspect a day's tournament slate before calling `get_match_center_dossier` "
            "or `analyze_matchup`. Supports text filtering via `query` and opaque `cursor` pagination."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "sport": {
                    "type": "string",
                    "description": "Sport key ('soccer', 'tennis', 'basketball', 'hockey', 'nfl', 'handball', 'table_tennis', 'darts', 'volleyball', 'baseball'). Default: 'tennis'.",
                },
                "date_ymd": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (e.g. '2026-10-29'). Defaults to today in UTC.",
                },
                "query": {
                    "type": "string",
                    "description": "Optional substring filter matching team/player name or tournament (e.g. 'Vienna', 'Medvedev', 'Serie A').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of fixtures to return (1-50). Default: 15.",
                },
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor returned as `next_cursor` from a previous call.",
                },
            },
        },
    },
    {
        "name": "get_paper_ledger_roi",
        "description": (
            "Query BetScout's verified out-of-sample Paper-Betting Ledger, returning overall Win-Loss record, "
            "net unit profit (+u), ROI%, Closing Line Value (CLV%), exact-score hit rate, by-sport attribution, "
            "and paginated settled/live/pending bet history (ordered newest resolved first). Use this tool when "
            "the user asks about historical model performance, win rate, ROI by sport, or recent settled results. "
            "Supports filtering by `status` ('all', 'settled', 'live', 'pending'), `sport`, and opaque `cursor` pagination."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter ledger entries by status ('all', 'settled', 'live', 'pending'). Default: 'settled'.",
                    "enum": ["all", "settled", "live", "pending"],
                },
                "sport": {
                    "type": "string",
                    "description": "Optional sport filter (e.g. 'soccer', 'tennis', 'basketball', 'hockey', 'nfl', 'handball', 'table_tennis', 'darts'). Default: 'all'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of ledger rows to return (1-50). Default: 15.",
                },
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor returned as `next_cursor` from a previous call.",
                },
            },
        },
    },
]


def execute_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any] | None,
    *,
    db_path: Path,
    rec_path: Path,
) -> dict[str, Any]:
    """Execute one of the 7 BetScout MCP tools and return an MCP `CallToolResult` dict."""
    from .exact_score import predict_tennis_set_scores
    from .paper_bet import build_recommended_2leg_doubles
    from .webapp import _analyze_live_matchup, _build_live_snapshot, _lookup_matchup_detail

    args = arguments or {}
    try:
        if tool_name == "get_daily_banker_picks":
            sport = str(args.get("sport") or "all").strip().lower()
            market_filter = str(args.get("market_filter") or "all").strip().lower()
            min_odds = float(args.get("min_odds") or 1.10)
            min_win_prob = float(args.get("min_win_prob") or 0.55)
            mispriced_only = bool(args.get("mispriced_only", False))
            limit = int(args.get("limit") or 15)
            cursor = args.get("cursor")

            snap = _build_live_snapshot(
                rec_path, db_path, min_odds=min_odds, sport=sport, run_settle=False, role="pro"
            )

            def _matches_market_filter(b: dict[str, Any]) -> bool:
                mt = str(b.get("market_type") or "").upper()
                tr = str(b.get("tier") or "").lower()
                is_sec = bool(mt) or tr in ("dc_shield", "dnb_shield", "set_shield", "totals_over", "totals_under", "straight_sets")
                if market_filter == "moneyline":
                    return not is_sec
                if market_filter == "secondary":
                    return is_sec
                if market_filter == "shield":
                    return tr in ("dc_shield", "dnb_shield", "set_shield") or mt.startswith(("DC_", "DNB_", "SET_HANDICAP"))
                if market_filter == "totals":
                    return tr in ("totals_over", "totals_under", "straight_sets") or mt.startswith(("OVER_", "UNDER_", "SETS_"))
                return True

            picks = [
                {
                    "match": b.get("match"),
                    "home": b.get("home"),
                    "away": b.get("away"),
                    "sport": b.get("sport_cat"),
                    "competition": b.get("competition"),
                    "kickoff_local": b.get("date_local"),
                    "pick": b.get("pick_name"),
                    "side": b.get("pick"),
                    "market_type": b.get("market_type") or "MONEYLINE",
                    "tier": b.get("tier"),
                    "win_prob_pct": round(float(b.get("win_prob") or 0.0) * 100.0, 1),
                    "book_odds": b.get("odds"),
                    "min_fair_odds": b.get("min_fair_odds"),
                    "edge_pp": b.get("edge_pp"),
                    "is_mispriced": bool(b.get("is_mispriced")),
                    "exact_score_prediction": b.get("exact_score_pick"),
                    "score_cluster": b.get("score_cluster_items") or [],
                    "secondary_opportunities": b.get("secondary_opportunities") or [],
                }
                for b in (snap.get("best_bets") or [])
                if float(b.get("win_prob") or 0.0) >= min_win_prob
                and (not mispriced_only or bool(b.get("is_mispriced")))
                and _matches_market_filter(b)
            ]
            paged = paginate_items(picks, cursor=cursor, limit=limit)
            result_obj = {
                "generated_at": snap.get("generated_at_local") or snap.get("generated_at"),
                "filters": {
                    "sport": sport,
                    "market_filter": market_filter,
                    "min_odds": min_odds,
                    "min_win_prob": min_win_prob,
                    "mispriced_only": mispriced_only,
                },
                "picks": paged["items"],
                "pagination": {
                    "returned_count": paged["returned_count"],
                    "total_available": paged["total_available"],
                    "has_more": paged["has_more"],
                    "next_cursor": paged["next_cursor"],
                    "hint": paged["pagination_hint"],
                },
            }
            return {"content": [{"type": "text", "text": json.dumps(result_obj, indent=2)}], "isError": False}

        if tool_name == "get_banker_profit_boosters":
            from .espn import resolve_competition_label

            budget_eur = float(args.get("budget_eur") or 100.0)
            if budget_eur <= 0:
                return {
                    "content": [{"type": "text", "text": "Parameter `budget_eur` must be greater than 0 (e.g. 100)."}],
                    "isError": True,
                }
            max_combos = max(1, min(int(args.get("max_combos") or 6), 10))
            snap = _build_live_snapshot(
                rec_path, db_path, min_odds=1.08, sport="all", run_settle=False, role="pro"
            )
            raw_doubles = build_recommended_2leg_doubles(
                snap.get("qualifying_picks") or [],
                snap.get("tennis_picks") or [],
                snap.get("other_sport_picks") or [],
                max_doubles=max_combos,
            )

            def _norm_leg(raw_l: dict[str, Any], prefix: str, parent: dict[str, Any]) -> dict[str, Any] | None:
                if isinstance(raw_l, dict) and raw_l.get("match"):
                    m_str = str(raw_l.get("match") or "")
                    h_part, a_part = (m_str.split(" vs ", 1) + [""])[:2] if " vs " in m_str else ("", "")
                    lg_raw = str(raw_l.get("league") or "")
                    lg_clean = resolve_competition_label(lg_raw, h_part.strip(), a_part.strip()) if lg_raw else ""
                    return {
                        "match": m_str,
                        "sport": raw_l.get("sport_cat") or "soccer",
                        "league": lg_clean or lg_raw,
                        "kickoff": raw_l.get("kickoff"),
                        "market": raw_l.get("market") or "Moneyline",
                        "pick": raw_l.get("pick"),
                        "odds": round(float(raw_l.get("odds") or 1.0), 2),
                        "win_prob_pct": round(float(raw_l.get("prob") or 0.0) * 100.0, 1),
                    }
                if parent.get(f"{prefix}_match") or parent.get(f"{prefix}_pick"):
                    return {
                        "match": parent.get(f"{prefix}_match"),
                        "sport": parent.get(f"{prefix}_sport") or "soccer",
                        "league": parent.get(f"{prefix}_league"),
                        "kickoff": parent.get(f"{prefix}_kickoff"),
                        "market": parent.get(f"{prefix}_market") or "Moneyline",
                        "pick": parent.get(f"{prefix}_pick"),
                        "odds": round(float(parent.get(f"{prefix}_odds") or 1.0), 2),
                        "win_prob_pct": round(float(parent.get(f"{prefix}_prob") or 0.0) * 100.0, 1),
                    }
                return None

            tickets_raw: list[dict[str, Any]] = []
            for c in raw_doubles:
                l1 = _norm_leg(c.get("leg_1") or {}, "leg_1", c)
                l2 = _norm_leg(c.get("leg_2") or {}, "leg_2", c)
                if not l1 or not l2:
                    continue
                legs_list = [l1, l2]
                l3 = _norm_leg(c.get("leg_3") or {}, "leg_3", c)
                if l3:
                    legs_list.append(l3)
                comb_odds = float(c.get("combined_odds") or 1.5)
                comb_prob = float(c.get("combined_prob") or 0.5)
                ev_pct = float(c.get("ev_pct") if c.get("ev_pct") is not None else (comb_prob * comb_odds - 1.0) * 100.0)
                tickets_raw.append({
                    "combo_type": c.get("combo_type") or "BANKER_PROFIT_BOOSTER",
                    "combo_label": c.get("combo_label") or "2-Leg Banker Combo",
                    "legs": legs_list,
                    "combined_odds": round(comb_odds, 2),
                    "combined_prob": comb_prob,
                    "min_fair_odds": round(1.0 / max(comb_prob, 0.05), 2),
                    "ev_pct": round(ev_pct, 2),
                })

            # Also synthesize a 3-Leg Banker Profit Treble if >=3 high-prob (>=72%, 1.10-1.48) bankers exist
            banker_singles = sorted(
                [
                    b
                    for b in (snap.get("best_bets") or [])
                    if float(b.get("win_prob") or 0.0) >= 0.72
                    and 1.10 <= float(b.get("odds") or 0.0) <= 1.48
                    and not str(b.get("match") or "").startswith("🔒")
                ],
                key=lambda x: (-float(x.get("win_prob") or 0.0), float(x.get("odds") or 99.0)),
            )
            distinct_3: list[dict[str, Any]] = []
            seen_m3: set[str] = set()
            for b in banker_singles:
                m_name = str(b.get("match") or "")
                if m_name and m_name not in seen_m3:
                    seen_m3.add(m_name)
                    distinct_3.append(b)
                if len(distinct_3) == 3:
                    break
            if len(distinct_3) == 3:
                t_legs = [
                    {
                        "match": b.get("match"),
                        "sport": b.get("sport_cat"),
                        "league": b.get("competition") or b.get("sport_league"),
                        "kickoff": b.get("date_local") or b.get("date"),
                        "market": "Moneyline / 1X2",
                        "pick": b.get("pick_name") or b.get("pick"),
                        "odds": round(float(b.get("odds") or 1.0), 2),
                        "win_prob_pct": round(float(b.get("win_prob") or 0.0) * 100.0, 1),
                    }
                    for b in distinct_3
                ]
                t_odds = round(float(distinct_3[0]["odds"]) * float(distinct_3[1]["odds"]) * float(distinct_3[2]["odds"]), 2)
                t_prob = float(distinct_3[0]["win_prob"]) * float(distinct_3[1]["win_prob"]) * float(distinct_3[2]["win_prob"])
                t_ev = round((t_prob * t_odds - 1.0) * 100.0, 2)
                treble_ticket = {
                    "combo_type": "BANKER_PROFIT_TREBLE",
                    "combo_label": "3-Leg Banker Profit Treble",
                    "legs": t_legs,
                    "combined_odds": t_odds,
                    "combined_prob": t_prob,
                    "min_fair_odds": round(1.0 / max(t_prob, 0.05), 2),
                    "ev_pct": t_ev,
                }
                if len(tickets_raw) >= max_combos:
                    tickets_raw[-1] = treble_ticket
                else:
                    tickets_raw.append(treble_ticket)

            tickets_raw = tickets_raw[:max_combos]

            # Quarter-Kelly stake sizing across recommended combo tickets
            kelly_weights: list[float] = []
            q_kelly_fracs: list[float] = []
            for t in tickets_raw:
                b_net = max(0.05, float(t["combined_odds"]) - 1.0)
                p_c = float(t["combined_prob"])
                full_kelly = max(0.0, (p_c * float(t["combined_odds"]) - 1.0) / b_net)
                q_kelly = 0.25 * full_kelly
                q_kelly_fracs.append(q_kelly)
                # Weight by Quarter-Kelly edge + small win-prob baseline so higher-edge combos get larger stakes
                kelly_weights.append(q_kelly + 0.015 * p_c)

            weight_sum = sum(kelly_weights) or 1.0
            enriched = []
            allocated_so_far = 0.0
            for idx, t in enumerate(tickets_raw):
                comb_odds = float(t["combined_odds"])
                comb_prob = float(t["combined_prob"])
                q_k = q_kelly_fracs[idx]
                if idx == len(tickets_raw) - 1:
                    stake_eur = round(max(0.0, budget_eur - allocated_so_far), 2)
                else:
                    stake_eur = round(budget_eur * (kelly_weights[idx] / weight_sum), 2)
                    allocated_so_far += stake_eur

                legs = t["legs"]
                title_str = " + ".join(str(lg.get("pick") or lg.get("match")) for lg in legs)
                ticket_obj: dict[str, Any] = {
                    "ticket_rank": idx + 1,
                    "combo_type": t["combo_type"],
                    "combo_label": t["combo_label"],
                    "leg_count": len(legs),
                    "title": title_str,
                    "legs": legs,
                    "leg_1": legs[0],
                    "leg_2": legs[1],
                }
                if len(legs) >= 3:
                    ticket_obj["leg_3"] = legs[2]
                ticket_obj.update({
                    "combined_odds": round(comb_odds, 2),
                    "min_fair_odds": t["min_fair_odds"],
                    "combined_win_prob_pct": round(comb_prob * 100.0, 1),
                    "ev_pct": t["ev_pct"],
                    "quarter_kelly_pct": round(q_k * 100.0, 2),
                    "standalone_quarter_kelly_stake_eur": round(budget_eur * q_k, 2),
                    "recommended_stake_eur": stake_eur,
                    "projected_return_eur": round(stake_eur * comb_odds, 2),
                    "projected_net_profit_eur": round(stake_eur * (comb_odds - 1.0), 2),
                })
                enriched.append(ticket_obj)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "budget_eur": budget_eur,
                                "allocation_method": "quarter_kelly_weighted",
                                "combo_count": len(enriched),
                                "combos": enriched,
                            },
                            indent=2,
                        ),
                    }
                ],
                "isError": False,
            }

        if tool_name == "analyze_matchup":
            query = str(args.get("query") or "").strip()
            if not query or (" vs " not in query.lower() and "-" not in query and len(query.split()) < 2):
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Invalid matchup query. Provide two team or player names separated by 'vs', "
                                "for example: `{\"query\": \"Daniil Medvedev vs Cameron Norrie\"}` or "
                                "`{\"query\": \"AS Roma vs Cagliari\"}`."
                            ),
                        }
                    ],
                    "isError": True,
                }
            analysis = _analyze_live_matchup(db_path, rec_path, query)
            if not analysis.get("ok"):
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": str(analysis.get("error") or f"Could not analyze matchup '{query}'."),
                        }
                    ],
                    "isError": True,
                }
            # Add explicit Tennis Set-Score distribution when sport is tennis
            set_distribution = None
            if analysis.get("sport") == "tennis" and analysis.get("fav_prob_pct"):
                fav_side = "H" if analysis.get("fav_name") == analysis.get("home") else "A"
                w_prob = float(analysis["fav_prob_pct"]) / 100.0
                g_diff = abs(float(analysis.get("game_share_diff_home") or 0.04))
                f_diff = abs(float(analysis.get("p1_last5_pct") or 50.0) - float(analysis.get("p2_last5_pct") or 50.0)) / 100.0
                set_distribution = predict_tennis_set_scores(
                    win_prob=w_prob,
                    side=fav_side,
                    game_win_pct_diff=g_diff,
                    form_6m_diff=f_diff,
                    best_of=3,
                    tour=str(analysis.get("league") or "atp"),
                )
            compact = {
                "matchup": f"{analysis.get('home')} vs {analysis.get('away')}",
                "home": analysis.get("home"),
                "away": analysis.get("away"),
                "sport": analysis.get("sport"),
                "league": analysis.get("league"),
                "favorite": analysis.get("fav_name"),
                "model_win_prob_pct": analysis.get("fav_prob_pct"),
                "market_win_prob_pct": analysis.get("fav_mkt_prob_pct"),
                "edge_pp": analysis.get("fav_edge_pp"),
                "ev_pct": analysis.get("fav_ev_pct"),
                "fair_odds": analysis.get("fav_fair_odds"),
                "bookmaker_odds": {
                    "home": analysis.get("odds_home"),
                    "away": analysis.get("odds_away"),
                    "favorite": analysis.get("fav_book_odds"),
                },
                "elo_diff_home": analysis.get("elo_diff_home"),
                "h2h_summary": analysis.get("h2h_summary"),
                "h2h_recent": (analysis.get("h2h") or [])[:6],
                "form_home_last6": (analysis.get("form_home") or [])[:6],
                "form_away_last6": (analysis.get("form_away") or [])[:6],
                "rest_hours": {
                    "home": analysis.get("p1_rest_hours"),
                    "away": analysis.get("p2_rest_hours"),
                },
                "set_score_distribution": set_distribution,
                "market_recommendations": analysis.get("market_recommendations"),
                "warnings": analysis.get("warnings") or [],
                "verdict": analysis.get("verdict"),
                "verdict_level": analysis.get("verdict_level"),
                "sportradar_match_id": (analysis.get("live_intel") or {}).get("sr_match_id"),
            }
            return {"content": [{"type": "text", "text": json.dumps(compact, indent=2, default=str)}], "isError": False}

        if tool_name == "calculate_exact_score_dutching":
            query = str(args.get("query") or "").strip()
            stake_eur = float(args.get("stake_eur") or 25.0)
            if stake_eur <= 0:
                return {
                    "content": [{"type": "text", "text": "Parameter `stake_eur` must be greater than 0 (e.g. 25)."}],
                    "isError": True,
                }
            analysis = _analyze_live_matchup(db_path, rec_path, query)
            if not analysis.get("ok"):
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Could not resolve matchup '{query}'. Pass 'Home vs Away' (e.g. 'AS Roma vs Cagliari').",
                        }
                    ],
                    "isError": True,
                }
            legs_raw: list[dict[str, Any]] = []
            pk = analysis.get("pick_detail") or {}
            esc = pk.get("exact_score_prediction") or {}
            book_cs = (((analysis.get("live_intel") or {}).get("primary_markets") or {}).get("correct_score_odds")) or {}
            if esc.get("top_3_breakdown"):
                for item in esc["top_3_breakdown"][:3]:
                    sc = str(item.get("score"))
                    prob = float(item.get("prob") or 0.12)
                    odds = float(book_cs.get(sc) or item.get("fair_odds") or round(1.0 / max(prob, 0.04), 2))
                    legs_raw.append({"score": sc, "prob": prob, "odds": odds})
            elif analysis.get("sport") == "tennis":
                fav_side = "H" if analysis.get("fav_name") == analysis.get("home") else "A"
                w_prob = float(analysis.get("fav_prob_pct") or 65.0) / 100.0
                g_diff = abs(float(analysis.get("game_share_diff_home") or 0.04))
                f_diff = abs(float(analysis.get("p1_last5_pct") or 50.0) - float(analysis.get("p2_last5_pct") or 50.0)) / 100.0
                sp = predict_tennis_set_scores(
                    win_prob=w_prob,
                    side=fav_side,
                    game_win_pct_diff=g_diff,
                    form_6m_diff=f_diff,
                    best_of=3,
                    tour=str(analysis.get("league") or "atp"),
                )
                legs_raw = [
                    {
                        "score": f"Sets {sp['straight_sets_score']}",
                        "prob": float(sp["straight_sets_prob"]),
                        "odds": float(sp["straight_sets_fair_odds"]),
                    },
                    {
                        "score": f"Sets {sp['decider_sets_score']}",
                        "prob": float(sp["decider_sets_prob"]),
                        "odds": float(sp["decider_sets_fair_odds"]),
                    },
                ]
            else:
                from .exact_score import predict_soccer_exact_scores

                fav_side = "H" if analysis.get("fav_name") == analysis.get("home") else "A"
                w_prob = float(analysis.get("fav_prob_pct") or 65.0) / 100.0
                dc = predict_soccer_exact_scores(win_prob=w_prob, side=fav_side)
                for item in dc.get("top_3_breakdown", [])[:3]:
                    sc = str(item["score"])
                    prob = float(item["prob"])
                    odds = float(book_cs.get(sc) or item["fair_odds"])
                    legs_raw.append({"score": sc, "prob": prob, "odds": odds})

            inv_sum = sum(1.0 / max(x["odds"], 1.01) for x in legs_raw)
            eff_odds = 1.0 / inv_sum if inv_sum > 0 else 1.0
            comb_prob = sum(x["prob"] for x in legs_raw)
            dutch_legs = []
            for x in legs_raw:
                st = stake_eur * ((1.0 / x["odds"]) / inv_sum)
                dutch_legs.append({
                    "score": x["score"],
                    "probability_pct": round(x["prob"] * 100.0, 1),
                    "decimal_odds": round(x["odds"], 2),
                    "stake_eur": round(st, 2),
                    "equal_payout_return_eur": round(st * x["odds"], 2),
                })
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "matchup": f"{analysis.get('home')} vs {analysis.get('away')}",
                                "sport": analysis.get("sport"),
                                "total_stake_eur": round(stake_eur, 2),
                                "combined_hit_prob_pct": round(comb_prob * 100.0, 1),
                                "effective_cluster_odds": round(eff_odds, 2),
                                "equal_payout_return_eur": round(stake_eur * eff_odds, 2),
                                "net_profit_if_hit_eur": round(stake_eur * (eff_odds - 1.0), 2),
                                "legs": dutch_legs,
                            },
                            indent=2,
                        ),
                    }
                ],
                "isError": False,
            }

        if tool_name == "get_match_center_dossier":
            mid = args.get("match_id")
            home = str(args.get("home") or "").strip()
            away = str(args.get("away") or "").strip()
            sport = str(args.get("sport") or "soccer").strip().lower()

            resolved_mid: int | None = int(mid) if mid is not None and str(mid).isdigit() else None
            local_detail: dict[str, Any] = {}
            if home and away:
                local_detail = _lookup_matchup_detail(db_path, rec_path, home, away, sport)
                if not resolved_mid:
                    sr_id = (local_detail.get("live_intel") or {}).get("sr_match_id")
                    if sr_id:
                        resolved_mid = int(sr_id)

            if not resolved_mid:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Could not resolve a numeric `match_id`. Provide either a valid Sportradar `match_id` "
                                "(discoverable via `search_daily_fixtures`) or both `home` and `away` team/player names "
                                "for a scheduled fixture."
                            ),
                        }
                    ],
                    "isError": True,
                }

            sdk = get_sdk_client()
            dossier = sdk.get_match_center_dossier(resolved_mid)
            mi = dossier.get("match_info") or {}
            m_obj = (dossier.get("timeline_delta") or {}).get("match") or mi.get("match") or {}
            teams = m_obj.get("teams") or (mi.get("match") or {}).get("teams") or {}
            h_team = teams.get("home") or {}
            a_team = teams.get("away") or {}
            if not h_team.get("name") and not a_team.get("name"):
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"No match found for match_id={resolved_mid}. Use `search_daily_fixtures` to look up "
                                "valid match IDs for the target date and sport."
                            ),
                        }
                    ],
                    "isError": True,
                }

            summary = {
                "match_id": resolved_mid,
                "sport_id": dossier.get("sport_id"),
                "sport_name": dossier.get("sport_name"),
                "tournament": (mi.get("season") or {}).get("name") or (mi.get("tournament") or {}).get("name"),
                "surface": ((mi.get("tournament") or {}).get("ground") or {}).get("name"),
                "status": (m_obj.get("status") or {}).get("name"),
                "home": {
                    "uid": h_team.get("uid") or h_team.get("_id"),
                    "name": h_team.get("name"),
                    "logo_url": dossier.get("home_headshot_url"),
                    "flag_url": dossier.get("home_flag_url"),
                },
                "away": {
                    "uid": a_team.get("uid") or a_team.get("_id"),
                    "name": a_team.get("name"),
                    "logo_url": dossier.get("away_headshot_url"),
                    "flag_url": dossier.get("away_flag_url"),
                },
                "score": m_obj.get("result"),
                "periods": m_obj.get("periods"),
                "merged_markets": dossier.get("merged_markets"),
                "form_wdl": dossier.get("form_wdl"),
                "h2h_edge": dossier.get("h2h_edge"),
                "missing_players": {
                    "home": (dossier.get("home_missing_players") or [])[:10],
                    "away": (dossier.get("away_missing_players") or [])[:10],
                },
                "local_db_pick": local_detail.get("pick_detail") if local_detail else None,
                "cache_stats": get_gismo_cache_stats(),
            }
            return {"content": [{"type": "text", "text": json.dumps(summary, indent=2, default=str)}], "isError": False}

        if tool_name == "search_daily_fixtures":
            sport = str(args.get("sport") or "tennis").strip().lower()
            date_ymd = str(args.get("date_ymd") or "").strip() or None
            query = str(args.get("query") or "").strip().lower()
            limit = int(args.get("limit") or 15)
            cursor = args.get("cursor")

            fixtures = get_daily_tipico_match_index(sport=sport, date_ymd=date_ymd)
            if query:
                fixtures = [
                    f
                    for f in fixtures
                    if query in str(f.get("home") or "").lower()
                    or query in str(f.get("away") or "").lower()
                    or query in str(f.get("tournament") or "").lower()
                ]
            paged = paginate_items(fixtures, cursor=cursor, limit=limit)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "sport": sport,
                                "date_ymd": date_ymd or "today",
                                "query": query or None,
                                "fixtures": paged["items"],
                                "pagination": {
                                    "returned_count": paged["returned_count"],
                                    "total_available": paged["total_available"],
                                    "has_more": paged["has_more"],
                                    "next_cursor": paged["next_cursor"],
                                    "hint": paged["pagination_hint"],
                                },
                            },
                            indent=2,
                            default=str,
                        ),
                    }
                ],
                "isError": False,
            }

        if tool_name == "get_paper_ledger_roi":
            status_filter = str(args.get("status") or "settled").strip().lower()
            sport_filter = str(args.get("sport") or "all").strip().lower()
            limit = int(args.get("limit") or 15)
            cursor = args.get("cursor")

            snap = _build_live_snapshot(
                rec_path, db_path, min_odds=1.05, sport="all", run_settle=False, role="pro"
            )
            ledger = snap.get("paper_ledger") or {}
            bets = list(ledger.get("bets") or [])
            if status_filter != "all":
                bets = [b for b in bets if str(b.get("status") or "").lower() == status_filter]
            if sport_filter != "all":
                bets = [
                    b
                    for b in bets
                    if sport_filter in str(b.get("sport_cat") or "").lower()
                    or sport_filter in str(b.get("league") or "").lower()
                ]
            compact_rows = [
                {
                    "event_id": b.get("event_id"),
                    "kickoff": b.get("kickoff"),
                    "league": b.get("league_label") or b.get("league"),
                    "match": f"{b.get('home')} vs {b.get('away')}",
                    "pick": b.get("home") if b.get("side") == "H" else b.get("away"),
                    "side": b.get("side"),
                    "tier": b.get("tier"),
                    "odds": b.get("logged_best_odds"),
                    "status": b.get("status"),
                    "final_score": b.get("score_str") or b.get("settled_score"),
                    "pnl_u": b.get("pnl_best"),
                }
                for b in bets
            ]
            paged = paginate_items(compact_rows, cursor=cursor, limit=limit)
            payload = {
                "summary": {
                    "settled_count": ledger.get("settled_count"),
                    "wins": ledger.get("settled_wins"),
                    "losses": ledger.get("settled_losses"),
                    "win_rate_pct": round(
                        (
                            float(ledger.get("settled_wins") or 0)
                            / max(1, int(ledger.get("settled_count") or 1))
                        )
                        * 100.0,
                        1,
                    ),
                    "net_profit_u": round(float(ledger.get("settled_profit_u") or 0.0), 2),
                    "roi_pct": round(float(ledger.get("settled_roi_best") or 0.0) * 100.0, 1),
                    "mean_clv_pct": round(float(ledger.get("mean_clv_pct") or 0.0) * 100.0, 2),
                    "exact_score_hit_rate_pct": ledger.get("exact_score_hit_rate_pct"),
                    "live_count": ledger.get("live_count"),
                    "pending_count": ledger.get("pending_count"),
                },
                "by_sport": ledger.get("by_sport") or [],
                "rows": paged["items"],
                "pagination": {
                    "returned_count": paged["returned_count"],
                    "total_available": paged["total_available"],
                    "has_more": paged["has_more"],
                    "next_cursor": paged["next_cursor"],
                    "hint": paged["pagination_hint"],
                },
            }
            return {"content": [{"type": "text", "text": json.dumps(payload, indent=2, default=str)}], "isError": False}

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Unknown tool '{tool_name}'. Available tools: "
                        + ", ".join(t["name"] for t in MCP_TOOLS_CATALOG)
                    ),
                }
            ],
            "isError": True,
        }
    except ValueError as ve:
        return {"content": [{"type": "text", "text": str(ve)}], "isError": True}
    except Exception as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Tool execution error in `{tool_name}`: {exc}. Verify your input parameters and retry.",
                }
            ],
            "isError": True,
        }


MCP_PROMPTS_CATALOG: list[dict[str, Any]] = [
    {
        "name": "daily-bankers",
        "description": "Retrieve today's highest-conviction BetScout picks across all sports and present a ranked summary table with model probabilities, bookmaker odds, and exact-score/set-score targets.",
        "arguments": [
            {
                "name": "sport",
                "description": "Optional sport category filter ('all', 'soccer', 'tennis', 'basketball', 'hockey', 'handball', 'table_tennis', 'darts'). Default: 'all'.",
                "required": False,
            },
            {
                "name": "min_win_prob",
                "description": "Minimum calibrated win probability threshold (e.g. '0.70' for >=70%). Default: '0.70'.",
                "required": False,
            },
        ],
    },
    {
        "name": "parlay-builder",
        "description": "Build 2-leg and 3-leg Banker Profitability Booster combo tickets with Quarter-Kelly EUR stake allocations for a specified bankroll budget.",
        "arguments": [
            {
                "name": "budget_eur",
                "description": "Total EUR budget to allocate across combo tickets (e.g. '100'). Default: '100'.",
                "required": False,
            },
        ],
    },
    {
        "name": "set-score-audit",
        "description": "Analyze one or more Tennis matchups for fixed straight-sets (2:0 / 0:2) probability, +1.5 Sets shield, turnaround warnings, and equal-payout set-score dutching.",
        "arguments": [
            {
                "name": "matchups",
                "description": "Comma-separated tennis matchups (e.g. 'Tommy Paul vs Luciano Darderi, Daniil Medvedev vs Cameron Norrie').",
                "required": True,
            },
        ],
    },
    {
        "name": "match-deep-dive",
        "description": "Run a full quantitative + Match Center inspection on a specific Football or Tennis matchup, including H2H history, Last-6 form, missing players, and equal-payout exact-score dutching.",
        "arguments": [
            {
                "name": "matchup",
                "description": "Matchup formatted as 'Home vs Away' (e.g. 'AS Roma vs Cagliari', 'Genoa vs Juventus').",
                "required": True,
            },
            {
                "name": "stake_eur",
                "description": "Optional EUR stake for exact-score dutching split (default: '25').",
                "required": False,
            },
        ],
    },
]

MCP_RESOURCES_CATALOG: list[dict[str, Any]] = [
    {
        "uri": "betscout://slate/today",
        "name": "Today's Active High-Conviction Picks Slate",
        "description": "Live JSON snapshot of BetScout's active multi-sport picks, model win probabilities, fair odds, and mispriced bookmaker edges.",
        "mimeType": "application/json",
    },
    {
        "uri": "betscout://ledger/summary",
        "name": "Verified Out-of-Sample Paper-Betting Ledger Summary",
        "description": "Audited Win-Loss record, net unit profit (+u), ROI%, Closing Line Value (CLV%), by-sport breakdown, and recent resolved bets.",
        "mimeType": "application/json",
    },
    {
        "uri": "betscout://boosters/today",
        "name": "Recommended 2-Leg & 3-Leg Banker Profit Boosters",
        "description": "High-probability (>=72%) 2-leg and 3-leg combo tickets with Quarter-Kelly stake allocations for a €100 reference budget.",
        "mimeType": "application/json",
    },
    {
        "uri": "betscout://cache/telemetry",
        "name": "2-Tier Gismo L1/L2 SQLite Cache Telemetry",
        "description": "Real-time hit/miss, negative-cache, and L2 SQLite persistence metrics for the Sportradar/Tipico Gismo data layer.",
        "mimeType": "application/json",
    },
]


def get_mcp_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    if name == "daily-bankers":
        sport = str(args.get("sport") or "all")
        min_wp = str(args.get("min_win_prob") or "0.70")
        return {
            "description": f"Daily BetScout banker picks (sport={sport}, min_win_prob={min_wp})",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Call `get_daily_banker_picks` with `sport=\"{sport}\"` and `min_win_prob={min_wp}`. "
                            "Present the returned picks ranked by model win probability in a clean markdown table "
                            "showing Matchup, League, Pick, Model Win%, Book Odds, Fair Odds, Edge (pp), and Exact Score / Set Score target."
                        ),
                    },
                }
            ],
        }
    if name == "parlay-builder":
        budget = str(args.get("budget_eur") or "100")
        return {
            "description": f"Build Quarter-Kelly Banker Profit Booster parlays for €{budget}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Call `get_banker_profit_boosters` with `budget_eur={budget}` and `max_combos=6`. "
                            "Present each 2-leg and 3-leg ticket with its full leg breakdown (match, league, pick, odds, win%), "
                            "combined odds, combined win%, EV%, Quarter-Kelly %, recommended EUR stake, and projected return."
                        ),
                    },
                }
            ],
        }
    if name == "set-score-audit":
        matchups = str(args.get("matchups") or "Tommy Paul vs Luciano Darderi, Daniil Medvedev vs Cameron Norrie")
        return {
            "description": f"Tennis fixed set-score (2:0 / 0:2) and +1.5 Sets shield audit for: {matchups}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"For each of the following tennis matchups ({matchups}), call `analyze_matchup` and `calculate_exact_score_dutching` (with `stake_eur=25`). "
                            "Compare their straight-sets (2:0 / 0:2) probability, 3-set decider (2:1 / 1:2) probability, +1.5 Sets shield, H2H history, and rest/turnaround warnings, "
                            "and rank them from highest to lowest confidence for a fixed set result."
                        ),
                    },
                }
            ],
        }
    if name == "match-deep-dive":
        matchup = str(args.get("matchup") or "AS Roma vs Cagliari")
        stake = str(args.get("stake_eur") or "25")
        return {
            "description": f"Full Match Center + Exact-Score Dutching deep dive for {matchup}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Inspect `{matchup}` by calling `analyze_matchup(query=\"{matchup}\")`, "
                            f"`calculate_exact_score_dutching(query=\"{matchup}\", stake_eur={stake})`, and "
                            "`get_match_center_dossier` (using the `sportradar_match_id` or `home`/`away` names). "
                            "Synthesize the model win probability, H2H edge, Last-6 form, missing/injured players, and exact-score dutching split."
                        ),
                    },
                }
            ],
        }
    raise ValueError(
        f"Unknown prompt '{name}'. Available prompts: " + ", ".join(p["name"] for p in MCP_PROMPTS_CATALOG)
    )


def read_mcp_resource(uri: str, *, db_path: Path, rec_path: Path) -> dict[str, Any]:
    u = str(uri or "").strip()
    if u == "betscout://slate/today":
        res = execute_mcp_tool(
            "get_daily_banker_picks", {"sport": "all", "min_win_prob": 0.55, "limit": 30}, db_path=db_path, rec_path=rec_path
        )
        return {
            "contents": [
                {
                    "uri": u,
                    "mimeType": "application/json",
                    "text": res["content"][0]["text"],
                }
            ]
        }
    if u == "betscout://ledger/summary":
        res = execute_mcp_tool(
            "get_paper_ledger_roi", {"status": "settled", "limit": 20}, db_path=db_path, rec_path=rec_path
        )
        return {
            "contents": [
                {
                    "uri": u,
                    "mimeType": "application/json",
                    "text": res["content"][0]["text"],
                }
            ]
        }
    if u == "betscout://boosters/today":
        res = execute_mcp_tool(
            "get_banker_profit_boosters", {"budget_eur": 100, "max_combos": 6}, db_path=db_path, rec_path=rec_path
        )
        return {
            "contents": [
                {
                    "uri": u,
                    "mimeType": "application/json",
                    "text": res["content"][0]["text"],
                }
            ]
        }
    if u == "betscout://cache/telemetry":
        return {
            "contents": [
                {
                    "uri": u,
                    "mimeType": "application/json",
                    "text": json.dumps(get_gismo_cache_stats(), indent=2),
                }
            ]
        }
    raise ValueError(
        f"Unknown resource URI '{u}'. Available resources: " + ", ".join(r["uri"] for r in MCP_RESOURCES_CATALOG)
    )


def handle_mcp_jsonrpc_request(
    rpc_body: dict[str, Any] | list[Any],
    *,
    db_path: Path,
    rec_path: Path,
    api_key: str | None = None,
    auth_header: str | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Process a JSON-RPC 2.0 MCP request (or batch) and return the JSON-RPC response."""
    if isinstance(rpc_body, list):
        responses = [
            r
            for item in rpc_body
            if (
                r := handle_mcp_jsonrpc_request(
                    item, db_path=db_path, rec_path=rec_path, api_key=api_key, auth_header=auth_header
                )
            )
            is not None
        ]
        return responses

    if not isinstance(rpc_body, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid JSON-RPC 2.0 request object."},
        }

    req_id = rpc_body.get("id")
    method = str(rpc_body.get("method") or "")
    params = rpc_body.get("params") or {}

    # JSON-RPC notifications (no id)
    if req_id is None and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "prompts": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": MCP_SERVER_INFO,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS_CATALOG},
        }

    if method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"prompts": MCP_PROMPTS_CATALOG},
        }

    if method == "prompts/get":
        p_name = str(params.get("name") or "")
        p_args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        try:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": get_mcp_prompt(p_name, p_args),
            }
        except ValueError as ve:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": str(ve)},
            }

    if method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": MCP_RESOURCES_CATALOG},
        }

    # Meter API key if provided (or enforce when monetization is enabled) for tools/call and resources/read
    if method in ("tools/call", "resources/read"):
        from .monetization import get_monetization_config, validate_and_meter_api_key

        raw_k = (api_key or "").strip()
        if not raw_k and auth_header:
            ah = auth_header.strip()
            if ah.lower().startswith("bearer "):
                raw_k = ah[7:].strip()
            elif ah.startswith("bs_live_"):
                raw_k = ah
        if raw_k.startswith("bs_live_"):
            ok_k, k_info, _rl_h, _st = validate_and_meter_api_key(db_path, raw_k, required_tier="starter")
            if not ok_k:
                err_msg = str(k_info.get("error") or "Invalid or expired BetScout API key.")
                if method == "tools/call":
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": err_msg}],
                            "isError": True,
                        },
                    }
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32001, "message": err_msg},
                }
        else:
            mon_cfg = get_monetization_config(db_path.parent if db_path else None)
            if mon_cfg.get("enabled"):
                from .webapp import resolve_request_role

                role_m, _act_m, _err_m = resolve_request_role(db_path, auth_header=auth_header, api_key_header=api_key)
                if role_m == "free":
                    msg_auth = (
                        "Authentication required for BetScout Remote MCP Server (`https://betscout.app/mcp`). "
                        "Pass `X-API-Key: bs_live_...` or `Authorization: Bearer bs_live_...` in your MCP client headers."
                    )
                    if method == "tools/call":
                        return {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"content": [{"type": "text", "text": msg_auth}], "isError": True},
                        }
                    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32001, "message": msg_auth}}

    if method == "resources/read":
        r_uri = str(params.get("uri") or "")
        try:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": read_mcp_resource(r_uri, db_path=db_path, rec_path=rec_path),
            }
        except ValueError as ve:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": str(ve)},
            }

    if method == "tools/call":
        t_name = str(params.get("name") or "")
        t_args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        tool_res = execute_mcp_tool(t_name, t_args, db_path=db_path, rec_path=rec_path)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": tool_res,
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method '{method}' not found. Supported MCP methods: initialize, ping, tools/list, tools/call, prompts/list, prompts/get, resources/list, resources/read.",
        },
    }
