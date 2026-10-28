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


def format_player_full_name(raw_name: str | None = None) -> str:
    """Convert 'Lastname, Firstname' (e.g. 'Djokovic, Novak') to 'Firstname Lastname'."""
    s = str(raw_name or "").strip()
    if not s:
        return ""
    if "," in s:
        parts = [p.strip() for p in s.split(",", 1)]
        if len(parts) == 2 and parts[0] and parts[1]:
            return f"{parts[1]} {parts[0]}"
    return s


def render_monogram_crest_data_uri(label: str | None = None, size_px: int = 36) -> str:
    """Generate a deterministic SVG monogram shield crest data URI."""
    from urllib.parse import quote

    clean = str(label or "BS").strip()
    words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", " ", clean).split() if w]
    if len(words) >= 2:
        initials = f"{words[0][0]}{words[1][0]}".upper()
    else:
        initials = (clean[:2] or "BS").upper()

    h = 0
    for ch in clean:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    palettes = [
        ("#0ea5e9", "#10b981"),
        ("#6366f1", "#ec4899"),
        ("#f59e0b", "#ef4444"),
        ("#14b8a6", "#3b82f6"),
        ("#8b5cf6", "#06b6d4"),
    ]
    c1, c2 = palettes[h % len(palettes)]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size_px}" height="{size_px}" viewBox="0 0 40 40">'
        f'<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/></linearGradient></defs>'
        f'<rect x="2" y="2" width="36" height="36" rx="10" fill="#0f172a" stroke="url(#g)" stroke-width="2.2"/>'
        f'<text x="20" y="25" text-anchor="middle" fill="#f8fafc" '
        f'font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="13">{initials}</text></svg>'
    )
    return f"data:image/svg+xml;utf8,{quote(svg)}"


_HEADSHOT_CACHE: dict[str, str] = {}

_CURATED_COMPETITION_WIKI_TITLES: dict[str, str] = {
    "serie a": "Serie_A",
    "premier league": "Premier_League",
    "la liga": "La_Liga",
    "laliga": "La_Liga",
    "bundesliga": "Bundesliga",
    "ligue 1": "Ligue_1",
    "uefa champions league": "UEFA_Champions_League",
    "champions league": "UEFA_Champions_League",
    "uefa europa league": "UEFA_Europa_League",
    "coppa italia": "Coppa_Italia",
    "fa cup": "FA_Cup",
    "nba": "National_Basketball_Association",
    "nhl": "National_Hockey_League",
    "nfl": "National_Football_League",
    "mlb": "Major_League_Baseball",
}


def resolve_player_headshot_url(player_name: str | None = None) -> str:
    """Resolve an individual player's photographic headshot URL via Wikimedia REST API with monogram fallback."""
    import json
    import ssl
    import urllib.request
    from urllib.parse import quote

    full_name = format_player_full_name(player_name)
    if not full_name:
        return render_monogram_crest_data_uri("PL", 64)

    cache_key = f"player:{full_name.lower()}"
    if cache_key in _HEADSHOT_CACHE:
        return _HEADSHOT_CACHE[cache_key]

    wiki_title = quote(full_name.replace(" ", "_"))
    try:
        ctx = ssl.create_default_context()
        if hasattr(ssl, "VERIFY_X509_STRICT"):
            ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        req = urllib.request.Request(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_title}",
            headers={"User-Agent": "Mozilla/5.0 (compatible; BetScoutSDK/1.1)"},
        )
        with urllib.request.urlopen(req, timeout=6.0, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            src = (data.get("thumbnail") or {}).get("source")
            if src:
                _HEADSHOT_CACHE[cache_key] = str(src)
                return str(src)
    except Exception:
        pass

    fallback = render_monogram_crest_data_uri(full_name, 64)
    _HEADSHOT_CACHE[cache_key] = fallback
    return fallback


def resolve_competition_crest_url(competition_name: str | None = None) -> str:
    """Resolve a league / competition crest image URL with monogram shield fallback."""
    import json
    import ssl
    import urllib.request

    clean = str(competition_name or "").strip()
    if not clean:
        return render_monogram_crest_data_uri("LG", 36)

    key = clean.lower()
    cache_key = f"comp:{key}"
    if cache_key in _HEADSHOT_CACHE:
        return _HEADSHOT_CACHE[cache_key]

    wiki_title = _CURATED_COMPETITION_WIKI_TITLES.get(key)
    if wiki_title:
        try:
            ctx = ssl.create_default_context()
            if hasattr(ssl, "VERIFY_X509_STRICT"):
                ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
            req = urllib.request.Request(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_title}",
                headers={"User-Agent": "Mozilla/5.0 (compatible; BetScoutSDK/1.1)"},
            )
            with urllib.request.urlopen(req, timeout=6.0, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
                src = (data.get("thumbnail") or {}).get("source")
                if src:
                    _HEADSHOT_CACHE[cache_key] = str(src)
                    return str(src)
        except Exception:
            pass

    fallback = render_monogram_crest_data_uri(clean, 36)
    _HEADSHOT_CACHE[cache_key] = fallback
    return fallback


def _to_ordinal(val: Any) -> str:
    try:
        num = int(val)
    except (ValueError, TypeError):
        return str(val)
    rem100 = num % 100
    if 11 <= rem100 <= 13:
        return f"{num}th"
    return f"{num}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th') }"


def format_market_placeholders(
    raw_text: str | None = None,
    *,
    home_name: str | None = None,
    away_name: str | None = None,
    specifiers: dict[str, Any] | None = None,
) -> str:
    """Interpolate {!setnr}, {total}, {hcp}, {$competitor1}, {$competitor2} into human-readable names."""
    out = str(raw_text or "")
    if not out:
        return ""
    spec = specifiers or {}
    out = re.sub(
        r"\{!(\w+)\}",
        lambda m: _to_ordinal(spec[m.group(1)]) if m.group(1) in spec else m.group(1),
        out,
    )
    out = re.sub(r"\{\$competitor1\}", home_name or "Home", out, flags=re.IGNORECASE)
    out = re.sub(r"\{\$competitor2\}", away_name or "Away", out, flags=re.IGNORECASE)
    out = re.sub(
        r"\{(\w+)\}",
        lambda m: str(spec[m.group(1)]) if m.group(1) in spec else m.group(1),
        out,
    )
    return out


def compute_form_wdl_segments(
    matches: list[dict[str, Any]] | None = None,
    team_uid: int | str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Extract last `limit` completed match W/D/L segments with exact score labels and 0-100 formPct."""
    items = matches if isinstance(matches, list) else []
    target_uid = int(team_uid or 0)
    completed: list[dict[str, Any]] = []

    for m in items:
        res = m.get("result") or {}
        if res.get("home") is None or res.get("away") is None:
            continue
        if (m.get("walkover") or m.get("retired")) and not res.get("winner"):
            continue
        teams = m.get("teams") or {}
        h_team = teams.get("home") or {}
        a_team = teams.get("away") or {}
        h_uid = int(h_team.get("uid") or h_team.get("_id") or 0)
        is_home = h_uid == target_uid
        my_score = int(res["home"] if is_home else res["away"])
        opp_score = int(res["away"] if is_home else res["home"])
        opp_name = str((a_team if is_home else h_team).get("name") or "")

        wdl = "D"
        if res.get("winner") == "home":
            wdl = "W" if is_home else "L"
        elif res.get("winner") == "away":
            wdl = "L" if is_home else "W"
        elif my_score > opp_score:
            wdl = "W"
        elif my_score < opp_score:
            wdl = "L"

        completed.append(
            {
                "match_id": m.get("_id"),
                "wdl": wdl,
                "score_label": f"{my_score}:{opp_score}",
                "opponent_name": opp_name or None,
            }
        )
        if len(completed) >= limit:
            break

    chronological = list(reversed(completed))
    pts = sum(3 if s["wdl"] == "W" else (1 if s["wdl"] == "D" else 0) for s in chronological)
    max_pts = len(chronological) * 3
    form_pct = round((pts / max_pts) * 100) if max_pts > 0 else 0

    while len(chronological) < limit:
        chronological.insert(
            0,
            {"match_id": None, "wdl": "empty", "score_label": None, "opponent_name": None},
        )
    return {"segments": chronological, "formPct": form_pct}


def compute_h2h_edge_summary(
    matches: list[dict[str, Any]] | None = None,
    home_uid: int | str | None = None,
    away_uid: int | str | None = None,
) -> dict[str, Any]:
    """Compute direct H2H win/draw/loss counts and color-coded progress bar percentages."""
    items = matches if isinstance(matches, list) else []
    h_target = int(home_uid or 0)
    a_target = int(away_uid or 0)
    home_wins = 0
    away_wins = 0
    draws = 0
    oldest_uts: int | None = None

    for m in items:
        res = m.get("result") or {}
        if res.get("home") is None or res.get("away") is None:
            continue
        uts = (m.get("time") or {}).get("uts") or (m.get("_dt") or {}).get("uts")
        if isinstance(uts, (int, float)) and uts > 0:
            if oldest_uts is None or int(uts) < oldest_uts:
                oldest_uts = int(uts)

        teams = m.get("teams") or {}
        mh = int((teams.get("home") or {}).get("uid") or (teams.get("home") or {}).get("_id") or 0)
        ma = int((teams.get("away") or {}).get("uid") or (teams.get("away") or {}).get("_id") or 0)
        hs, as_ = int(res["home"]), int(res["away"])

        winner_uid = 0
        if res.get("winner") == "home" or hs > as_:
            winner_uid = mh
        elif res.get("winner") == "away" or as_ > hs:
            winner_uid = ma

        if winner_uid == h_target and h_target > 0:
            home_wins += 1
        elif winner_uid == a_target and a_target > 0:
            away_wins += 1
        elif winner_uid == 0:
            draws += 1

    total = home_wins + draws + away_wins
    from datetime import datetime, timezone

    since_year = (
        str(datetime.fromtimestamp(oldest_uts, tz=timezone.utc).year)
        if oldest_uts is not None
        else None
    )
    return {
        "total_meetings": total,
        "since_year": since_year,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_pct": round((home_wins / total) * 100) if total > 0 else 0,
        "draw_pct": round((draws / total) * 100) if total > 0 else 0,
        "away_win_pct": round((away_wins / total) * 100) if total > 0 else 0,
    }


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
formatPlayerFullName = format_player_full_name
renderMonogramCrestDataUri = render_monogram_crest_data_uri
resolvePlayerHeadshotUrl = resolve_player_headshot_url
resolveCompetitionCrestUrl = resolve_competition_crest_url
formatMarketPlaceholders = format_market_placeholders
computeFormWdlSegments = compute_form_wdl_segments
computeH2HEdgeSummary = compute_h2h_edge_summary
