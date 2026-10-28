"""Name Normalization, Market Parsing, Visual Asset URLs & Delta-Stream Utilities for `betscout_sdk`."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from ._internal.transport import (
    build_upstream_country_flag_url,
    build_upstream_team_logo_url,
)
from .constants import CORRECT_SCORE_OUTCOMES, MARKET_IDS

_CLUB_ALIASES: dict[str, str] = {
    "paris saint germain": "psg paris saint germain",
    "psg": "psg paris saint germain",
    "internazionale": "inter internazionale milano",
    "inter milan": "inter internazionale milano",
}


def normalize_team_name(name: str | None = None) -> str:
    """Strip Unicode diacritics, remove common football club prefixes, and expand known club aliases."""
    raw = str(name or "")
    normalized = unicodedata.normalize("NFKD", raw)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()
    without_prefixes = re.sub(
        r"\b(fc|sc|cf|ac|afc|sv|vfb|vfl|tsg|rb|ud|cd|rcd|fk|sk|bk)\b",
        " ",
        stripped,
    )
    clean = re.sub(r"[^a-z0-9]+", " ", without_prefixes).strip()
    return _CLUB_ALIASES.get(clean, clean)


def team_tokens(name: str | None = None) -> set[str]:
    """Extract significant (>= 3 char) normalized tokens from a team or player name."""
    norm = normalize_team_name(name)
    if not norm:
        return set()
    return {tok for tok in norm.split() if len(tok) >= 3}


def names_match(a: str | None = None, b: str | None = None) -> bool:
    """Fuzzy team / player name matcher handling diacritics, club prefixes, and 'Lastname, Firstname' ordering."""
    na = normalize_team_name(a)
    nb = normalize_team_name(b)
    if not na or not nb:
        return False
    if na == nb or nb in na or na in nb:
        return True
    ta = team_tokens(a)
    tb = team_tokens(b)
    return bool(ta & tb)


def parse_prematch_markets(
    markets: list[dict[str, Any]] | None = None,
    flipped: bool = False,
) -> dict[str, Any]:
    """Parse pre-match markets from Primary Retail (_bookmakerId: 176) or Global Consensus (_bookmakerId: 0)."""
    items = markets if isinstance(markets, list) else []
    bk_label = "Primary Bookmaker"
    if items and isinstance(items[0], dict):
        if items[0].get("_bookmakerId") == 0 or "UOF" in str(items[0].get("source") or ""):
            bk_label = "Market Consensus"

    out: dict[str, Any] = {
        "bookmaker": bk_label,
        "odds_home": None,
        "odds_draw": None,
        "odds_away": None,
        "double_chance_1x": None,
        "double_chance_x2": None,
        "draw_no_bet_home": None,
        "draw_no_bet_away": None,
        "asian_handicap_line": None,
        "asian_handicap_home": None,
        "asian_handicap_away": None,
        "total_line": None,
        "odds_over": None,
        "odds_under": None,
        "correct_score_odds": {},
    }

    for mk in items:
        if not isinstance(mk, dict):
            continue
        mid = mk.get("_marketId")
        outcomes = mk.get("outcomes") or []
        spec = mk.get("specifiers") or {}

        if mid in (
            MARKET_IDS["MATCH_1X2"],
            MARKET_IDS["TENNIS_MATCH_WINNER"],
            MARKET_IDS["US_SPORTS_WINNER_OT"],
            MARKET_IDS["HOCKEY_WINNER_OT_SO"],
        ):
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm:
                    if flipped:
                        out["odds_away"] = val
                    else:
                        out["odds_home"] = val
                elif "competitor2" in nm:
                    if flipped:
                        out["odds_home"] = val
                    else:
                        out["odds_away"] = val
                elif nm == "draw":
                    out["odds_draw"] = val

        elif mid == MARKET_IDS["DOUBLE_CHANCE"]:
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm and "draw" in nm:
                    if flipped:
                        out["double_chance_x2"] = val
                    else:
                        out["double_chance_1x"] = val
                elif "competitor2" in nm and "draw" in nm:
                    if flipped:
                        out["double_chance_1x"] = val
                    else:
                        out["double_chance_x2"] = val

        elif mid == MARKET_IDS["DRAW_NO_BET"]:
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm:
                    if flipped:
                        out["draw_no_bet_away"] = val
                    else:
                        out["draw_no_bet_home"] = val
                elif "competitor2" in nm:
                    if flipped:
                        out["draw_no_bet_home"] = val
                    else:
                        out["draw_no_bet_away"] = val

        elif mid in (MARKET_IDS["ASIAN_HANDICAP_2WAY"], MARKET_IDS["US_SPORTS_SPREAD_OT"]):
            out["asian_handicap_line"] = spec.get("hcp")
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if "competitor1" in nm:
                    if flipped:
                        out["asian_handicap_away"] = val
                    else:
                        out["asian_handicap_home"] = val
                elif "competitor2" in nm:
                    if flipped:
                        out["asian_handicap_home"] = val
                    else:
                        out["asian_handicap_away"] = val

        elif mid in (
            MARKET_IDS["TOTAL_GOALS"],
            MARKET_IDS["TENNIS_TOTAL_GAMES"],
            MARKET_IDS["US_SPORTS_TOTAL_OT"],
        ):
            if spec.get("total") is not None:
                try:
                    out["total_line"] = float(spec["total"])
                except (ValueError, TypeError):
                    out["total_line"] = None
            for o in outcomes:
                nm = str(o.get("name") or "").lower()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                if nm.startswith("over"):
                    out["odds_over"] = val
                elif nm.startswith("under"):
                    out["odds_under"] = val

        elif mid in (MARKET_IDS["CORRECT_SCORE"], MARKET_IDS["CORRECT_SCORE_NAMED"]):
            if out["correct_score_odds"] and mid == MARKET_IDS["CORRECT_SCORE_NAMED"]:
                continue
            cs_map: dict[str, float] = {}
            for o in outcomes:
                oid = str(o.get("_id") or "")
                nm_sc = str(o.get("name") or "").strip()
                val = float(o["odds"]) if o.get("odds") else None
                if not val:
                    continue
                raw_sc = (
                    nm_sc
                    if (":" in nm_sc and len(nm_sc) <= 5)
                    else CORRECT_SCORE_OUTCOMES.get(oid, "")
                )
                if raw_sc and ":" in raw_sc:
                    if flipped:
                        ph, pa = raw_sc.split(":", 1)
                        raw_sc = f"{pa}:{ph}"
                    cs_map[raw_sc] = val
            if cs_map:
                out["correct_score_odds"] = cs_map

    return out


def merge_primary_and_consensus_markets(
    primary: dict[str, Any],
    consensus: dict[str, Any],
) -> dict[str, Any]:
    """Merge Primary Retail (_bookmakerId: 176) and Global Consensus (_bookmakerId: 0) parsed markets."""
    merged: dict[str, Any] = {
        **primary,
        "correct_score_odds": dict(primary.get("correct_score_odds") or {})
        if primary.get("correct_score_odds")
        else dict(consensus.get("correct_score_odds") or {}),
    }

    scalar_keys = [
        "odds_home",
        "odds_draw",
        "odds_away",
        "double_chance_1x",
        "double_chance_x2",
        "draw_no_bet_home",
        "draw_no_bet_away",
        "asian_handicap_line",
        "asian_handicap_home",
        "asian_handicap_away",
        "total_line",
        "odds_over",
        "odds_under",
    ]
    for k in scalar_keys:
        if merged.get(k) is None and consensus.get(k) is not None:
            merged[k] = consensus[k]

    has_primary = bool(
        primary.get("odds_home") is not None
        or primary.get("asian_handicap_home") is not None
        or primary.get("odds_over") is not None
        or primary.get("correct_score_odds")
    )
    has_consensus = bool(
        consensus.get("odds_home") is not None
        or consensus.get("asian_handicap_home") is not None
        or consensus.get("odds_over") is not None
        or consensus.get("correct_score_odds")
    )
    if has_primary and has_consensus:
        merged["bookmaker"] = "Primary + Consensus"
    elif has_primary:
        merged["bookmaker"] = "Primary Bookmaker"
    elif has_consensus:
        merged["bookmaker"] = "Market Consensus"

    return merged


def get_adaptive_refetch_interval_ms(doc: dict[str, Any] | None = None) -> int:
    """Compute the adaptive polling interval in milliseconds from a document's _maxage metadata."""
    max_age_sec = doc.get("_maxage") if isinstance(doc, dict) else None
    sec = int(max_age_sec) if isinstance(max_age_sec, (int, float)) and max_age_sec > 0 else 3
    return max(sec * 1000, 3000)


def merge_latest_match_delta(
    match: dict[str, Any],
    timeline_delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge a base match summary with a real-time match_timelinedelta response using updated_uts."""
    delta_match = timeline_delta.get("match") if isinstance(timeline_delta, dict) else None
    if not isinstance(delta_match, dict):
        return match
    return delta_match


def get_team_logo_url(
    team_id: int | str,
    size: str = "big",
    ncaa: bool = False,
    ncaa_size: str = "ap250x188ut",
    image_base_url: str | None = None,
) -> str:
    """Build the direct tokenless PNG logo URL for any club/team ID."""
    return build_upstream_team_logo_url(
        team_id,
        size=size,
        ncaa=ncaa,
        ncaa_size=ncaa_size,
        image_base_url=image_base_url,
    )


def get_country_flag_url(
    country_iso2: str,
    fmt: str = "svg",
    ratio: str = "4x3",
    size: str = "medium",
    image_base_url: str | None = None,
) -> str:
    """Build the direct tokenless SVG (4x3 | 1x1) or PNG (small | medium | big) country flag URL."""
    return build_upstream_country_flag_url(
        country_iso2,
        fmt=fmt,
        ratio=ratio,
        size=size,
        image_base_url=image_base_url,
    )


def render_team_jersey_svg(
    jersey: dict[str, Any] | None = None,
    shirt_number: int | str | None = None,
    size_px: int = 96,
) -> str:
    """Render a standalone vector SVG player kit avatar from a team's jersey hex colors and shirt_number."""
    jersey = jersey or {}

    def clean_hex(c: Any, fallback: str = "1e293b") -> str:
        raw = str(c or fallback).lstrip("#")
        return f"#{raw}"

    base = clean_hex(jersey.get("base"), "dc2626")
    sleeve = clean_hex(jersey.get("sleeve"), base.lstrip("#"))
    number_color = clean_hex(jersey.get("number"), "ffffff")
    stripe_color = clean_hex(jersey["stripes"]) if jersey.get("stripes") else None
    num_text = str(shirt_number).strip() if shirt_number is not None else ""

    stripes_markup = (
        f'<rect x="36" y="18" width="8" height="68" fill="{stripe_color}" opacity="0.9"/>'
        f'<rect x="52" y="18" width="8" height="68" fill="{stripe_color}" opacity="0.9"/>'
        if stripe_color
        else ""
    )
    number_markup = (
        f'<text x="48" y="60" text-anchor="middle" fill="{number_color}" '
        f'font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="24">{num_text}</text>'
        if num_text
        else ""
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size_px}" height="{size_px}" '
        f'viewBox="0 0 96 96" role="img" aria-label="Player Jersey">'
        f'<path d="M26 14 L38 14 C41 20 55 20 58 14 L70 14 L88 32 L76 44 L68 36 L68 86 L28 86 L28 36 L20 44 L8 32 Z" '
        f'fill="{base}" stroke="rgba(255,255,255,0.22)" stroke-width="2"/>'
        f'<path d="M26 14 L8 32 L20 44 L28 36 L28 22 Z" fill="{sleeve}"/>'
        f'<path d="M70 14 L88 32 L76 44 L68 36 L68 22 Z" fill="{sleeve}"/>'
        f"{stripes_markup}{number_markup}</svg>"
    )


def parse_venue_coordinates(googlecoords: str | None = None) -> dict[str, float] | None:
    """Parse a stadium's googlecoords string ('45.478025,9.124206') into {'lat': ..., 'lng': ...}."""
    if not googlecoords or "," not in str(googlecoords):
        return None
    parts = str(googlecoords).split(",", 1)
    try:
        return {"lat": float(parts[0].strip()), "lng": float(parts[1].strip())}
    except (ValueError, TypeError):
        return None


# CamelCase aliases for 1:1 parity with TypeScript @betscout/sdk
normalizeTeamName = normalize_team_name
teamTokens = team_tokens
namesMatch = names_match
parsePrematchMarkets = parse_prematch_markets
mergePrimaryAndConsensusMarkets = merge_primary_and_consensus_markets
getAdaptiveRefetchIntervalMs = get_adaptive_refetch_interval_ms
mergeLatestMatchDelta = merge_latest_match_delta
getTeamLogoUrl = get_team_logo_url
getCountryFlagUrl = get_country_flag_url
renderTeamJerseySvg = render_team_jersey_svg
parseVenueCoordinates = parse_venue_coordinates
