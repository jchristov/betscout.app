"""FunStats.fyi + Multi-Source External Stats & Consensus Adapter for BetScout.

Provides a unified 2-tier cached (L1 in-memory + L2 SQLite `funstats_http_cache`)
intelligence layer integrating:
1. **FunStats (`funstats.fyi`)**:
   - Arbitrary-pair Long-Term H2H (up to 20 meetings, 2012-2026) via `/api/fixture-expansion`
     even when teams are not scheduled to play each other (`fixture_id=1`).
   - 300+-field Team & Standings Statistical Splits via `/api/standings/{league_id}`
     and `/api/teams/{team_id}/stats` (9-cell HT/FT matrix, 1H/2H Over/Under & BTTS,
     Corners O/U 7.5-11.5, Cards O/U 2.5-6.5, Shots/SoT/Possession, Fav/Dog W/D/L splits,
     exact goals scored 0..5+).
   - 133,011-Match Empirical Market Calibration (`/api/odds/{id}/market-calibration`)
     and Historical Odds Twins (`/api/odds/{id}/similar-recent`).
   - Opening-to-Current 1X2 Odds Movement (`/api/odds/{id}/movement`) & Multi-Market Odds (`/api/odds/{id}`).
   - Active Team Streaks (`/api/teams/{id}/strikes`) + Streak vs Market Expectation
     with Wilson 95% Confidence Intervals (`/api/strikes/market-context`).
   - Season xG Regression (`/api/leagues/{id}/xg`), Empirical Scorelines (`/api/leagues/{id}/scorelines`),
     and Upset Index (`/api/leagues/{id}/upset-index`).
   - Injury-Adjusted Predicted Lineups, Continuity % & Curated Match Facts (`/api/matches/{id}/sections-dynamic`).
2. **OLBG Crowd Tipster Consensus (`olbg.com`)**:
   - Unflattens SvelteKit `devalue` payloads from `/betting-tips/Football/1/__data.json`
     and match-level `/__data.json?event_id={id}` across 12+ markets (`Full Time Result`,
     `Total Goals`, `Both Teams to Score`, `Result and BTTS`, `Asian Hcap`, `Correct Score`, etc.).
3. **SportyTrader Algorithmic & Expert Preview (`sportytrader.com`)**:
   - Extracts SportyTrader star algorithm 1X2 probabilities, expert pick, H2H/form Key Points,
     and Last-Minute opening-vs-current odds movement.
4. **FootyStats Official API (`api.football-data-api.com`)**:
   - Supports `FOOTYSTATS_API_KEY` (falling back to `"example"` demo key for league/sample inspection).
"""

from __future__ import annotations

import datetime as dt
import html
import json
import logging
import os
import re
import sqlite3
import ssl
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import unicodedata

_GENERIC_CLUB_TOKENS = {
    "fc", "cf", "sc", "ac", "afc", "ssc", "as", "cd", "ud", "rcd", "real", "club", "de", "the",
    "city", "united", "town", "rovers", "wanderers", "athletic", "county", "albion", "hotspur",
    "forest", "villa", "palace", "orient", "argyle", "wednesday", "north", "south", "west", "east",
    "sporting", "dynamo", "lokomotiv", "borussia", "eintracht", "olympique", "stade", "racing",
    "union", "inter", "atletico", "saint",
}


def _sdk_names_match(name_a: str, name_b: str) -> bool:
    """Strict club/player name matcher that prevents generic suffixes ('City', 'United', 'Rovers')
    from falsely matching unrelated clubs (e.g. 'Hull City' vs 'Manchester City')."""
    def _norm(s: str) -> str:
        s_ascii = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
        s_clean = re.sub(r"[^a-z0-9]+", " ", s_ascii.lower()).strip()
        stop = {"fc", "cf", "sc", "ac", "afc", "ssc", "as", "cd", "ud", "rcd", "club", "de", "the"}
        tokens = [t for t in s_clean.split() if t not in stop]
        return " ".join(tokens) or s_clean

    na, nb = _norm(name_a), _norm(name_b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = set(na.split()), set(nb.split())
    # Distinct tokens (excluding generic words like 'city', 'united', 'rovers')
    da = {t for t in ta if t not in _GENERIC_CLUB_TOKENS}
    db = {t for t in tb if t not in _GENERIC_CLUB_TOKENS}
    if da and db:
        if da == db or (da <= db and len(da) >= 1) or (db <= da and len(db) >= 1):
            # Prevent 'Manchester' matching both 'Manchester City' and 'Manchester United' when both have City/United specified
            if ("city" in ta and "united" in tb) or ("united" in ta and "city" in tb):
                return False
            return True
        overlap_d = da & db
        if any(len(tok) >= 4 for tok in overlap_d):
            if ("city" in ta and "united" in tb) or ("united" in ta and "city" in tb):
                return False
            return True
        return False
    return na in nb or nb in na

logger = logging.getLogger(__name__)

FUNSTATS_BASE_URL = "https://funstats.fyi"
OLBG_BASE_URL = "https://www.olbg.com"
SPORTYTRADER_BASE_URL = "https://www.sportytrader.com"
FOOTYSTATS_API_BASE_URL = "https://api.football-data-api.com"

DEFAULT_SEASON = 2026

# Map BetScout league codes / tournament names to FunStats (API-Football) league IDs
LEAGUE_CODE_TO_FUNSTATS_ID: dict[str, int] = {
    "ucl": 2,
    "champions_league": 2,
    "uefa_champions_league": 2,
    "uel": 3,
    "europa_league": 3,
    "uefa_europa_league": 3,
    "uecl": 848,
    "conference_league": 848,
    "uefa_europa_conference_league": 848,
    "epl": 39,
    "premier_league": 39,
    "eng1": 39,
    "championship": 40,
    "eng2": 40,
    "fa_cup": 45,
    "efl_cup": 48,
    "carabao_cup": 48,
    "laliga": 140,
    "la_liga": 140,
    "primera_division": 140,
    "esp1": 140,
    "segunda": 141,
    "la_liga_2": 141,
    "esp2": 141,
    "seriea": 135,
    "serie_a": 135,
    "ita1": 135,
    "serieb": 136,
    "serie_b": 136,
    "ita2": 136,
    "bundesliga": 78,
    "ger1": 78,
    "bundesliga2": 79,
    "2_bundesliga": 79,
    "ger2": 79,
    "dfb_pokal": 81,
    "ligue1": 61,
    "ligue_1": 61,
    "fra1": 61,
    "ligue2": 62,
    "ligue_2": 62,
    "fra2": 62,
    "eredivisie": 88,
    "ned1": 88,
    "primeira_liga": 94,
    "liga_portugal": 94,
    "por1": 94,
    "super_lig": 203,
    "tur1": 203,
    "scottish_premiership": 179,
    "sco1": 179,
    "belgian_pro_league": 144,
    "jupiler_pro_league": 144,
    "bel1": 144,
    "austrian_bundesliga": 218,
    "aut1": 218,
    "swiss_super_league": 207,
    "sui1": 207,
    "super_league_greece": 197,
    "gre1": 197,
    "mls": 253,
    "brasileirao": 71,
    "serie_a_brazil": 71,
    "argentina_primera": 128,
    "liga_profesional": 128,
    "saudi_pro_league": 307,
    "wc": 1,
    "world_cup": 1,
    "euro": 4,
    "nations_league": 5,
}

TOP_EUROPEAN_LEAGUE_IDS: tuple[int, ...] = (39, 140, 135, 78, 61, 2, 3, 848, 40, 88, 94)

SUPPORTED_MARKET_CONTEXT_STREAKS: frozenset[str] = frozenset(
    {
        "winning",
        "winning_home",
        "winning_away",
        "undefeated",
        "undefeated_home",
        "undefeated_away",
        "not_winning",
        "losing",
        "draw",
        "favorite_winning",
        "underdog_not_losing",
    }
)

# ---------------------------------------------------------------------------
# 2-Tier Cache (L1 Memory + L2 SQLite `funstats_http_cache`)
# ---------------------------------------------------------------------------
_L1_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()
_SQLITE_INIT_DONE = False

_CACHE_STATS: dict[str, int] = {
    "l1_hits": 0,
    "l2_hits": 0,
    "network_fetches": 0,
    "network_errors": 0,
}


def _get_sqlite_cache_db_path() -> Path:
    env_path = os.environ.get("BETSCOUT_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2] / "data" / "funstats_cache.db"


def _ensure_sqlite_table() -> sqlite3.Connection | None:
    global _SQLITE_INIT_DONE
    try:
        db_path = _get_sqlite_cache_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        if not _SQLITE_INIT_DONE:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS funstats_http_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    fetched_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_funstats_cache_expires ON funstats_http_cache(expires_at)"
            )
            conn.commit()
            _SQLITE_INIT_DONE = True
        return conn
    except Exception as exc:
        logger.debug("FunStats SQLite cache init skipped: %s", exc)
        return None


def _cache_get(cache_key: str) -> Any | None:
    now = time.time()
    with _CACHE_LOCK:
        entry = _L1_CACHE.get(cache_key)
        if entry is not None:
            expires_at, val = entry
            if expires_at > now:
                _CACHE_STATS["l1_hits"] += 1
                return val
            _L1_CACHE.pop(cache_key, None)

    conn = _ensure_sqlite_table()
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT payload_json, expires_at FROM funstats_http_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row is not None:
                payload_json, expires_at = row[0], float(row[1])
                if expires_at > now:
                    val = json.loads(payload_json)
                    with _CACHE_LOCK:
                        _L1_CACHE[cache_key] = (expires_at, val)
                        _CACHE_STATS["l2_hits"] += 1
                    return val
        except Exception as exc:
            logger.debug("FunStats SQLite read error for %s: %s", cache_key, exc)
        finally:
            conn.close()
    return None


def _cache_set(cache_key: str, value: Any, ttl_seconds: int) -> None:
    now = time.time()
    expires_at = now + max(30, ttl_seconds)
    with _CACHE_LOCK:
        _L1_CACHE[cache_key] = (expires_at, value)
    conn = _ensure_sqlite_table()
    if conn is not None:
        try:
            payload_json = json.dumps(value, ensure_ascii=False)
            conn.execute(
                """
                INSERT OR REPLACE INTO funstats_http_cache (cache_key, payload_json, fetched_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (cache_key, payload_json, now, expires_at),
            )
            conn.commit()
        except Exception as exc:
            logger.debug("FunStats SQLite write error for %s: %s", cache_key, exc)
        finally:
            conn.close()


def get_funstats_cache_stats() -> dict[str, Any]:
    """Return runtime cache hit/miss counters and L2 SQLite row count."""
    l2_rows = 0
    conn = _ensure_sqlite_table()
    if conn is not None:
        try:
            row = conn.execute("SELECT COUNT(*) FROM funstats_http_cache").fetchone()
            if row:
                l2_rows = int(row[0])
        except Exception:
            pass
        finally:
            conn.close()
    with _CACHE_LOCK:
        return {
            **_CACHE_STATS,
            "l1_entries": len(_L1_CACHE),
            "l2_rows": l2_rows,
        }


# ---------------------------------------------------------------------------
# HTTP Helpers
# ---------------------------------------------------------------------------
_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


_SSL_UNVERIFIED_CTX = ssl._create_unverified_context()


def _urlopen_with_ssl_fallback(req: urllib.request.Request, timeout: float):
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), ssl.SSLError):
            return urllib.request.urlopen(req, timeout=timeout, context=_SSL_UNVERIFIED_CTX)
        raise
    except ssl.SSLError:
        return urllib.request.urlopen(req, timeout=timeout, context=_SSL_UNVERIFIED_CTX)


def _http_get_json(
    url: str,
    *,
    cache_key: str | None = None,
    ttl_seconds: int = 900,
    timeout: float = 4.5,
    headers: dict[str, str] | None = None,
) -> Any | None:
    key = cache_key or f"json:{url}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    req_headers = {**_DEFAULT_HEADERS, "Referer": f"{FUNSTATS_BASE_URL}/"}
    if headers:
        req_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with _urlopen_with_ssl_fallback(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
        with _CACHE_LOCK:
            _CACHE_STATS["network_fetches"] += 1
        _cache_set(key, data, ttl_seconds)
        return data
    except Exception as exc:
        with _CACHE_LOCK:
            _CACHE_STATS["network_errors"] += 1
        logger.debug("HTTP JSON fetch failed for %s: %s", url, exc)
        return None


def _http_get_text(
    url: str,
    *,
    cache_key: str | None = None,
    ttl_seconds: int = 1200,
    timeout: float = 4.5,
    headers: dict[str, str] | None = None,
) -> str | None:
    key = cache_key or f"text:{url}"
    cached = _cache_get(key)
    if isinstance(cached, str):
        return cached
    req_headers = {
        **_DEFAULT_HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    if headers:
        req_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with _urlopen_with_ssl_fallback(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        with _CACHE_LOCK:
            _CACHE_STATS["network_fetches"] += 1
        _cache_set(key, text, ttl_seconds)
        return text
    except Exception as exc:
        with _CACHE_LOCK:
            _CACHE_STATS["network_errors"] += 1
        logger.debug("HTTP text fetch failed for %s: %s", url, exc)
        return None


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        if val is None or val == "":
            return default
        return int(float(val))
    except (TypeError, ValueError):
        return default


def _pct(numer: float, denom: float) -> float:
    if denom <= 0:
        return 0.0
    return round((numer / denom) * 100.0, 1)


def resolve_funstats_league_id(league_hint: str | int | None) -> int | None:
    """Resolve a BetScout league code, tournament name, or numeric string to a FunStats league_id."""
    if league_hint is None:
        return None
    if isinstance(league_hint, int):
        return league_hint if league_hint > 0 else None
    raw = str(league_hint).strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    slug = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    if slug in LEAGUE_CODE_TO_FUNSTATS_ID:
        return LEAGUE_CODE_TO_FUNSTATS_ID[slug]
    for key, lid in LEAGUE_CODE_TO_FUNSTATS_ID.items():
        if key in slug or slug in key:
            return lid
    return None


# ---------------------------------------------------------------------------
# FunStats Endpoint Wrappers
# ---------------------------------------------------------------------------
def _fetch_funstats_fixtures_today() -> list[dict[str, Any]]:
    data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/fixtures/today",
        cache_key="funstats:fixtures:today",
        ttl_seconds=600,
    )
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("fixtures"), list):
        return [x for x in data["fixtures"] if isinstance(x, dict)]
    leagues = data.get("leagues") or []
    flat: list[dict[str, Any]] = []
    for lg in leagues:
        if not isinstance(lg, dict):
            continue
        lid = _safe_int(lg.get("league_id") or lg.get("id"))
        lname = str(lg.get("league_name") or lg.get("name") or "")
        lcountry = str(lg.get("country") or "")
        for fx in lg.get("fixtures") or []:
            if isinstance(fx, dict):
                item = dict(fx)
                item.setdefault("league_id", lid)
                item.setdefault("league_name", lname)
                item.setdefault("league_country", lcountry)
                flat.append(item)
    return flat


def _fetch_funstats_fixtures_by_date(date_ymd: str) -> list[dict[str, Any]]:
    data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/fixtures/list?date={urllib.parse.quote(date_ymd)}",
        cache_key=f"funstats:fixtures:date:{date_ymd}",
        ttl_seconds=900,
    )
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("fixtures"), list):
            return [x for x in data["fixtures"] if isinstance(x, dict)]
        if isinstance(data.get("leagues"), list):
            out: list[dict[str, Any]] = []
            for lg in data["leagues"]:
                if isinstance(lg, dict):
                    for fx in lg.get("fixtures") or []:
                        if isinstance(fx, dict):
                            out.append(fx)
            return out
    return []


def _fetch_funstats_week_notable() -> list[dict[str, Any]]:
    data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/fixtures/week-notable",
        cache_key="funstats:fixtures:week-notable",
        ttl_seconds=1200,
    )
    if isinstance(data, dict) and isinstance(data.get("fixtures"), list):
        return [x for x in data["fixtures"] if isinstance(x, dict)]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def _search_funstats_team(team_name: str, league_id: int | None = None) -> dict[str, Any] | None:
    """Resolve a team name to `{id, name, logo, league_id, season}` via standings or `/api/search`."""
    clean = (team_name or "").strip()
    if not clean:
        return None

    # 1. If league_id is known, check the cached league standings first (also gives 300+ stats!)
    if league_id:
        standings = _fetch_funstats_standings(league_id)
        for row in standings:
            rname = str(row.get("team_name") or row.get("name") or "")
            if rname and _sdk_names_match(clean, rname):
                return {
                    "id": _safe_int(row.get("team_id") or row.get("id")),
                    "name": rname,
                    "logo": row.get("team_logo") or row.get("logo"),
                    "league_id": league_id,
                    "season": _safe_int(row.get("season"), DEFAULT_SEASON),
                    "standings_row": row,
                }

    # 2. Query `/api/search?q=`
    q_enc = urllib.parse.quote(clean)
    data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/search?q={q_enc}",
        cache_key=f"funstats:search:{clean.lower()}",
        ttl_seconds=86400,
    )
    teams = (data or {}).get("teams") if isinstance(data, dict) else None
    if not teams and isinstance(data, dict) and isinstance(data.get("results"), list):
        teams = [
            {
                "id": r.get("entityId") or r.get("id"),
                "name": r.get("name") or r.get("originalName"),
                "logo": (r.get("meta") or {}).get("logoUrl") or r.get("logo"),
                "country": (r.get("meta") or {}).get("country") or r.get("country"),
            }
            for r in data["results"]
            if isinstance(r, dict) and r.get("entityType") == "team"
        ]
    if isinstance(teams, list) and teams:
        for t in teams:
            if isinstance(t, dict) and _sdk_names_match(clean, str(t.get("name") or "")):
                return {
                    "id": _safe_int(t.get("id") or t.get("team_id")),
                    "name": str(t.get("name") or clean),
                    "logo": t.get("logo"),
                    "country": t.get("country"),
                    "league_id": _safe_int(t.get("league_id") or league_id or 0) or None,
                    "season": DEFAULT_SEASON,
                }
        first = teams[0]
        if isinstance(first, dict) and _safe_int(first.get("id")):
            return {
                "id": _safe_int(first.get("id")),
                "name": str(first.get("name") or clean),
                "logo": first.get("logo"),
                "country": first.get("country"),
                "league_id": _safe_int(first.get("league_id") or league_id or 0) or None,
                "season": DEFAULT_SEASON,
            }

    # 3. Scan top European league standings if search returned empty or short query
    for fallback_lid in TOP_EUROPEAN_LEAGUE_IDS[:6]:
        if fallback_lid == league_id:
            continue
        standings = _fetch_funstats_standings(fallback_lid)
        for row in standings:
            rname = str(row.get("team_name") or row.get("name") or "")
            if rname and _sdk_names_match(clean, rname):
                return {
                    "id": _safe_int(row.get("team_name_id") or row.get("team_id") or row.get("id")),
                    "name": rname,
                    "logo": row.get("team_logo") or row.get("logo"),
                    "league_id": fallback_lid,
                    "season": _safe_int(row.get("season"), DEFAULT_SEASON),
                    "standings_row": row,
                }
    return None


def _fetch_funstats_standings(league_id: int, season: int = DEFAULT_SEASON) -> list[dict[str, Any]]:
    data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/standings/{league_id}?season={season}&locale=en",
        cache_key=f"funstats:standings:{league_id}:{season}",
        ttl_seconds=3600,
    )
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for k in ("standings", "teams", "table", "data"):
            if isinstance(data.get(k), list):
                return [r for r in data[k] if isinstance(r, dict)]
    return []


def _fetch_funstats_fixture_expansion(
    *,
    fixture_id: int,
    home_team_id: int,
    away_team_id: int,
    league_id: int,
    season: int = DEFAULT_SEASON,
) -> dict[str, Any] | None:
    fid = fixture_id if fixture_id > 0 else 1
    lid = league_id if league_id > 0 else 39
    url = (
        f"{FUNSTATS_BASE_URL}/api/fixture-expansion"
        f"?fixture_id={fid}&home_team_id={home_team_id}&away_team_id={away_team_id}"
        f"&league_id={lid}&season={season}"
    )
    data = _http_get_json(
        url,
        cache_key=f"funstats:expansion:{fid}:{home_team_id}:{away_team_id}:{lid}:{season}",
        ttl_seconds=1800,
    )
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Long-Term H2H Analytics Builder (2012-2026, up to 20 meetings)
# ---------------------------------------------------------------------------
def build_long_term_h2h_analytics(
    h2h_matches: list[dict[str, Any]],
    *,
    home_team_name: str,
    away_team_name: str,
    home_team_id: int | None = None,
    away_team_id: int | None = None,
) -> dict[str, Any]:
    """Compute deep long-term H2H analytics from `funstats.fyi` `h2hMatches` (2012-2026).

    Correctly orients results to the queried `home_team_name` / `away_team_name`
    regardless of which club hosted each historical meeting, AND separately tracks
    same-venue meetings (`when_home_hosted`).
    """
    if not h2h_matches:
        return {
            "total_meetings": 0,
            "meetings": [],
            "insights": [],
        }

    home_wins = 0
    draws = 0
    away_wins = 0
    home_goals_total = 0
    away_goals_total = 0
    btts_count = 0
    over_15_count = 0
    over_25_count = 0
    over_35_count = 0
    home_clean_sheets = 0
    away_clean_sheets = 0

    venue_meetings = 0
    venue_home_wins = 0
    venue_draws = 0
    venue_away_wins = 0

    formatted_meetings: list[dict[str, Any]] = []
    years_seen: list[int] = []

    # Sort newest first
    sorted_matches = sorted(
        [m for m in h2h_matches if isinstance(m, dict)],
        key=lambda m: str(m.get("date") or ""),
        reverse=True,
    )

    for m in sorted_matches:
        ht = m.get("home_team") if isinstance(m.get("home_team"), dict) else {}
        at = m.get("away_team") if isinstance(m.get("away_team"), dict) else {}
        goals = m.get("goals") if isinstance(m.get("goals"), dict) else {}

        m_home_id = _safe_int(ht.get("id") or m.get("home_team_id"))
        m_away_id = _safe_int(at.get("id") or m.get("away_team_id"))
        m_home_name = str(ht.get("name") or m.get("home_team_name") or m.get("home") or "")
        m_away_name = str(at.get("name") or m.get("away_team_name") or m.get("away") or "")

        gh = goals.get("home") if "home" in goals else m.get("home_goals")
        ga = goals.get("away") if "away" in goals else m.get("away_goals")
        if gh is None or ga is None:
            continue
        gh_i = _safe_int(gh)
        ga_i = _safe_int(ga)

        # Determine whether the historical home team is the queried `home` team
        if home_team_id and m_home_id:
            queried_home_is_match_home = m_home_id == home_team_id
        elif away_team_id and m_home_id:
            queried_home_is_match_home = m_home_id != away_team_id
        else:
            queried_home_is_match_home = _sdk_names_match(home_team_name, m_home_name)

        if queried_home_is_match_home:
            q_home_goals = gh_i
            q_away_goals = ga_i
            venue_meetings += 1
            if gh_i > ga_i:
                venue_home_wins += 1
            elif gh_i == ga_i:
                venue_draws += 1
            else:
                venue_away_wins += 1
        else:
            q_home_goals = ga_i
            q_away_goals = gh_i

        home_goals_total += q_home_goals
        away_goals_total += q_away_goals

        if q_home_goals > q_away_goals:
            home_wins += 1
            winner_side = "home"
        elif q_home_goals == q_away_goals:
            draws += 1
            winner_side = "draw"
        else:
            away_wins += 1
            winner_side = "away"

        total_g = q_home_goals + q_away_goals
        if q_home_goals > 0 and q_away_goals > 0:
            btts_count += 1
        if total_g >= 2:
            over_15_count += 1
        if total_g >= 3:
            over_25_count += 1
        if total_g >= 4:
            over_35_count += 1
        if q_away_goals == 0:
            home_clean_sheets += 1
        if q_home_goals == 0:
            away_clean_sheets += 1

        raw_date = str(m.get("date") or "")[:10]
        if len(raw_date) >= 4 and raw_date[:4].isdigit():
            years_seen.append(int(raw_date[:4]))

        formatted_meetings.append(
            {
                "fixture_id": _safe_int(m.get("fixture_id") or m.get("id")),
                "date": raw_date,
                "home": m_home_name,
                "away": m_away_name,
                "home_goals": gh_i,
                "away_goals": ga_i,
                "score": f"{gh_i}:{ga_i}",
                "league": str(m.get("league_name") or m.get("league") or ""),
                "season": _safe_int(m.get("season")),
                "winner_for_matchup": winner_side,
                "same_venue": queried_home_is_match_home,
            }
        )

    n = len(formatted_meetings)
    if n == 0:
        return {"total_meetings": 0, "meetings": [], "insights": []}

    total_goals = home_goals_total + away_goals_total
    avg_total = round(total_goals / n, 2)
    home_avg = round(home_goals_total / n, 2)
    away_avg = round(away_goals_total / n, 2)
    btts_pct = _pct(btts_count, n)
    over_15_pct = _pct(over_15_count, n)
    over_25_pct = _pct(over_25_count, n)
    over_35_pct = _pct(over_35_count, n)

    # Compute active H2H streaks from newest to oldest
    home_unbeaten_streak = 0
    for fm in formatted_meetings:
        if fm["winner_for_matchup"] in ("home", "draw"):
            home_unbeaten_streak += 1
        else:
            break

    away_unbeaten_streak = 0
    for fm in formatted_meetings:
        if fm["winner_for_matchup"] in ("away", "draw"):
            away_unbeaten_streak += 1
        else:
            break

    btts_h2h_streak = 0
    for fm in formatted_meetings:
        if fm["home_goals"] > 0 and fm["away_goals"] > 0:
            btts_h2h_streak += 1
        else:
            break

    over25_h2h_streak = 0
    for fm in formatted_meetings:
        if (fm["home_goals"] + fm["away_goals"]) >= 3:
            over25_h2h_streak += 1
        else:
            break

    span_str = f"{min(years_seen)}-{max(years_seen)}" if years_seen else "Multi-Season"
    insights: list[str] = [
        f"{n} H2H meetings ({span_str}): {home_team_name} {home_wins}W - {draws}D - {away_wins}W {away_team_name} ({avg_total:.2f} goals/game)",
    ]
    if venue_meetings >= 2:
        insights.append(
            f"When {home_team_name} hosts ({venue_meetings} matches): {venue_home_wins}W - {venue_draws}D - {venue_away_wins}L"
        )
    if home_unbeaten_streak >= 3:
        insights.append(f"{home_team_name} is unbeaten in the last {home_unbeaten_streak} H2H meetings vs {away_team_name}")
    elif away_unbeaten_streak >= 3:
        insights.append(f"{away_team_name} is unbeaten in the last {away_unbeaten_streak} H2H meetings vs {home_team_name}")
    if btts_pct >= 65.0 and n >= 4:
        insights.append(f"High H2H BTTS tendency: {btts_count}/{n} meetings ({btts_pct:.0f}%) saw both teams score")
    if over_25_pct >= 65.0 and n >= 4:
        insights.append(f"High-scoring H2H series: {over_25_count}/{n} meetings ({over_25_pct:.0f}%) finished Over 2.5 Goals")
    elif over_25_pct <= 35.0 and n >= 4:
        insights.append(f"Tight low-scoring H2H series: {n - over_25_count}/{n} meetings ({100 - over_25_pct:.0f}%) stayed Under 2.5 Goals")

    return {
        "total_meetings": n,
        "span_years": span_str,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "home_win_pct": _pct(home_wins, n),
        "draw_pct": _pct(draws, n),
        "away_win_pct": _pct(away_wins, n),
        "home_goals_total": home_goals_total,
        "away_goals_total": away_goals_total,
        "avg_total_goals": avg_total,
        "home_goals_avg": home_avg,
        "away_goals_avg": away_avg,
        "btts_count": btts_count,
        "btts_pct": btts_pct,
        "over_15_pct": over_15_pct,
        "over_25_pct": over_25_pct,
        "over_35_pct": over_35_pct,
        "home_clean_sheets": home_clean_sheets,
        "away_clean_sheets": away_clean_sheets,
        "home_clean_sheet_pct": _pct(home_clean_sheets, n),
        "away_clean_sheet_pct": _pct(away_clean_sheets, n),
        "when_home_hosted": {
            "meetings": venue_meetings,
            "home_wins": venue_home_wins,
            "draws": venue_draws,
            "away_wins": venue_away_wins,
        },
        "active_h2h_streaks": {
            "home_unbeaten": home_unbeaten_streak,
            "away_unbeaten": away_unbeaten_streak,
            "btts_consecutive": btts_h2h_streak,
            "over_25_consecutive": over25_h2h_streak,
        },
        "insights": insights,
        "meetings": formatted_meetings,
    }


# ---------------------------------------------------------------------------
# 300+-Field Team Statistical Splits Extractor (`/api/standings/{id}`)
# ---------------------------------------------------------------------------
def extract_team_deep_splits(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Condense a 300+-column FunStats standings/team-stats row into structured quant splits."""
    if not isinstance(row, dict) or not row:
        return None
    played = max(1, _safe_int(row.get("played") or row.get("matches_played") or 1))
    home_played = max(1, _safe_int(row.get("home_played") or (played // 2) or 1))
    away_played = max(1, _safe_int(row.get("away_played") or (played // 2) or 1))

    def _rate(field: str, denom: int = played) -> float:
        val = row.get(field)
        if val is None:
            return 0.0
        fval = _safe_float(val)
        # In FunStats standings, counts (e.g. over_25 = 19 out of 31 played) are integers <= played
        if fval <= denom and field not in ("avg_possession", "shots_per_game", "sot_per_game", "corners_per_game", "cards_per_game", "fouls_per_game"):
            return _pct(fval, denom)
        return round(fval, 1)

    fav_w = _safe_int(row.get("odds_fav_wins"))
    fav_d = _safe_int(row.get("odds_fav_draws"))
    fav_l = _safe_int(row.get("odds_fav_losses"))
    fav_total = fav_w + fav_d + fav_l

    dog_w = _safe_int(row.get("odds_dog_wins"))
    dog_d = _safe_int(row.get("odds_dog_draws"))
    dog_l = _safe_int(row.get("odds_dog_losses"))
    dog_total = dog_w + dog_d + dog_l

    return {
        "team_id": _safe_int(row.get("team_id") or row.get("id")),
        "team_name": str(row.get("team_name") or row.get("name") or ""),
        "rank": _safe_int(row.get("rank") or row.get("position")),
        "played": _safe_int(row.get("played")),
        "points": _safe_int(row.get("points")),
        "form": str(row.get("form") or ""),
        "goals_for": _safe_int(row.get("goals_for")),
        "goals_against": _safe_int(row.get("goals_against")),
        "goals_Toggle": {
            "over_05_pct": _rate("over_05"),
            "over_15_pct": _rate("over_15"),
            "over_25_pct": _rate("over_25"),
            "over_35_pct": _rate("over_35"),
            "over_45_pct": _rate("over_45"),
            "btts_pct": _rate("btts"),
            "clean_sheets_pct": _rate("clean_sheets"),
            "failed_to_score_pct": _rate("failed_to_score"),
            "home_over_25_pct": _rate("home_over_25", home_played),
            "away_over_25_pct": _rate("away_over_25", away_played),
            "home_btts_pct": _rate("home_btts", home_played),
            "away_btts_pct": _rate("away_btts", away_played),
        },
        "half_splits": {
            "ht_over_05_pct": _rate("ht_over_05"),
            "ht_over_15_pct": _rate("ht_over_15"),
            "ht_btts_pct": _rate("ht_btts"),
            "ht_clean_sheets_pct": _rate("ht_clean_sheets"),
            "sh_over_05_pct": _rate("second_half_over_05"),
            "sh_over_15_pct": _rate("second_half_over_15"),
            "sh_btts_pct": _rate("second_half_btts"),
        },
        "htft_matrix": {
            "WW": _safe_int(row.get("htft_ww")),
            "WD": _safe_int(row.get("htft_wd")),
            "WL": _safe_int(row.get("htft_wl")),
            "DW": _safe_int(row.get("htft_dw")),
            "DD": _safe_int(row.get("htft_dd")),
            "DL": _safe_int(row.get("htft_dl")),
            "LW": _safe_int(row.get("htft_lw")),
            "LD": _safe_int(row.get("htft_ld")),
            "LL": _safe_int(row.get("htft_ll")),
        },
        "corners_and_cards": {
            "corners_per_game": round(_safe_float(row.get("corners_per_game") or row.get("avg_corners")), 2),
            "corners_for_avg": round(_safe_float(row.get("corners_for_avg") or row.get("avg_corners_for")), 2),
            "corners_against_avg": round(_safe_float(row.get("corners_against_avg") or row.get("avg_corners_against")), 2),
            "corners_over_85_pct": _rate("corners_over_85"),
            "corners_over_95_pct": _rate("corners_over_95"),
            "corners_over_105_pct": _rate("corners_over_105"),
            "cards_per_game": round(_safe_float(row.get("cards_per_game") or row.get("avg_cards")), 2),
            "cards_over_35_pct": _rate("cards_over_35"),
            "cards_over_45_pct": _rate("cards_over_45"),
        },
        "match_dominance": {
            "avg_possession": round(_safe_float(row.get("avg_possession")), 1),
            "shots_per_game": round(_safe_float(row.get("shots_per_game")), 1),
            "shots_against_per_game": round(_safe_float(row.get("shots_against_per_game")), 1),
            "sot_per_game": round(_safe_float(row.get("sot_per_game")), 1),
            "sot_against_per_game": round(_safe_float(row.get("sot_against_per_game")), 1),
        },
        "market_role_record": {
            "as_favorite": {
                "matches": fav_total,
                "wins": fav_w,
                "draws": fav_d,
                "losses": fav_l,
                "win_pct": _pct(fav_w, fav_total),
            },
            "as_underdog": {
                "matches": dog_total,
                "wins": dog_w,
                "draws": dog_d,
                "losses": dog_l,
                "unbeaten_pct": _pct(dog_w + dog_d, dog_total),
            },
        },
    }


# ---------------------------------------------------------------------------
# OLBG Crowd Tipster Consensus Adapter (SvelteKit `/__data.json` devalue)
# ---------------------------------------------------------------------------
def _unflatten_devalue(arr: list[Any], idx: int = 0, _depth: int = 0) -> Any:
    if not isinstance(arr, list) or idx < 0 or idx >= len(arr) or _depth > 22:
        return None
    val = arr[idx]
    if isinstance(val, (int, float, str, bool)) or val is None:
        return val
    if isinstance(val, list):
        if len(val) == 2 and isinstance(val[0], str) and val[0] in ("Date", "Set", "Map", "BigInt"):
            return val[1]
        return [_unflatten_devalue(arr, i, _depth + 1) if isinstance(i, int) else i for i in val]
    if isinstance(val, dict):
        return {
            k: (_unflatten_devalue(arr, v, _depth + 1) if isinstance(v, int) else v)
            for k, v in val.items()
        }
    return val


def lookup_olbg_match_consensus(home: str, away: str) -> dict[str, Any] | None:
    """Fetch OLBG crowd tipster consensus for `home` vs `away` via SvelteKit `/__data.json`."""
    if not home or not away:
        return None
    cache_key = f"olbg:match:{home.strip().lower()}:{away.strip().lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached if cached else None

    index_data = _http_get_json(
        f"{OLBG_BASE_URL}/betting-tips/Football/1/__data.json",
        cache_key="olbg:football:index",
        ttl_seconds=900,
        timeout=4.0,
    )
    if not isinstance(index_data, dict):
        return None
    nodes = index_data.get("nodes")
    if not isinstance(nodes, list) or len(nodes) < 3:
        return None
    node2 = nodes[2] if isinstance(nodes[2], dict) else {}
    raw_arr = node2.get("data")
    if not isinstance(raw_arr, list) or not raw_arr:
        return None

    root = _unflatten_devalue(raw_arr, 0)
    if not isinstance(root, dict):
        return None

    rows = root.get("MatchRowData") or []
    matched_row: dict[str, Any] | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        alias = str(row.get("event_name_alias") or row.get("event_name") or "")
        if " v " in alias:
            parts = alias.split(" v ", 1)
        elif " vs " in alias:
            parts = alias.split(" vs ", 1)
        else:
            continue
        if _sdk_names_match(home, parts[0]) and _sdk_names_match(away, parts[1]):
            matched_row = row
            break

    if matched_row is None:
        return None

    result: dict[str, Any] = {
        "provider": "crowd_tipsters",
        "event_id": matched_row.get("event_id"),
        "event_name": matched_row.get("event_name_alias"),
        "competition": matched_row.get("competition_name"),
        "total_event_tips": _safe_int(matched_row.get("total_markets_tips")),
        "top_tip": {
            "selection": matched_row.get("selection_name"),
            "market": matched_row.get("market_type"),
            "confidence_pct": _safe_float(matched_row.get("percentage_Confidence")),
            "selection_tips": _safe_int(matched_row.get("total_selection_tips")),
            "market_tips": _safe_int(matched_row.get("total_market_tips")),
            "decimal_odds": _safe_float(matched_row.get("odds_decimal")),
            "value_rating_stars": _safe_int(matched_row.get("value_rating")),
        },
        "markets": {},
        "summary": None,
    }

    # Optionally fetch deep match-level `__data.json` if `eventUrl` is present
    event_url = str(matched_row.get("eventUrl") or "")
    if event_url.startswith("http"):
        parsed = urllib.parse.urlparse(event_url)
        data_url = f"{OLBG_BASE_URL}{parsed.path.rstrip('/')}/__data.json"
        if parsed.query:
            data_url = f"{data_url}?{parsed.query}"
        detail_json = _http_get_json(
            data_url,
            cache_key=f"olbg:event:{matched_row.get('event_id')}",
            ttl_seconds=1200,
            timeout=4.0,
        )
        if isinstance(detail_json, dict) and isinstance(detail_json.get("nodes"), list) and len(detail_json["nodes"]) >= 3:
            dnode = detail_json["nodes"][2]
            if isinstance(dnode, dict) and isinstance(dnode.get("data"), list):
                droot = _unflatten_devalue(dnode["data"], 0)
                if isinstance(droot, dict):
                    result["summary"] = droot.get("summary")
                    mdata = droot.get("marketData")
                    if isinstance(mdata, dict):
                        markets_summary: dict[str, list[dict[str, Any]]] = {}
                        for mkt_name, items in mdata.items():
                            if not isinstance(items, list):
                                continue
                            top_sels: list[dict[str, Any]] = []
                            for it in items[:4]:
                                if isinstance(it, dict):
                                    top_sels.append(
                                        {
                                            "selection": it.get("selection_name"),
                                            "tips": _safe_int(it.get("total_selection_tips")),
                                            "market_tips": _safe_int(it.get("total_market_tips")),
                                            "confidence_pct": _safe_float(it.get("percentage_Confidence")),
                                            "odds": _safe_float(it.get("odds_decimal")),
                                            "comments_count": len(it.get("comment") or []) if isinstance(it.get("comment"), list) else 0,
                                        }
                                    )
                            if top_sels:
                                markets_summary[str(mkt_name)] = top_sels
                        result["markets"] = markets_summary

    _cache_set(cache_key, result, 1200)
    return result


# ---------------------------------------------------------------------------
# SportyTrader Algorithmic & Expert Preview Adapter
# ---------------------------------------------------------------------------
def lookup_sportytrader_match_intel(home: str, away: str) -> dict[str, Any] | None:
    """Discover and parse SportyTrader's match prediction, ⭐ algorithm probabilities, and key points."""
    if not home or not away:
        return None
    cache_key = f"sportytrader:match:{home.strip().lower()}:{away.strip().lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached if cached else None

    index_html = _http_get_text(
        f"{SPORTYTRADER_BASE_URL}/en/betting-tips/football/",
        cache_key="sportytrader:football:index",
        ttl_seconds=1200,
        timeout=4.0,
    )
    if not index_html:
        return None

    links = list(dict.fromkeys(re.findall(r'href="(/en/betting-tips/[a-z0-9-]+-\d+/)"', index_html)))
    home_tokens = [t for t in re.sub(r"[^a-z0-9]+", " ", home.lower()).split() if len(t) >= 3]
    away_tokens = [t for t in re.sub(r"[^a-z0-9]+", " ", away.lower()).split() if len(t) >= 3]

    matched_path: str | None = None
    for path in links:
        slug = path.lower()
        if any(ht in slug for ht in home_tokens) and any(at in slug for at in away_tokens):
            matched_path = path
            break

    if not matched_path:
        return None

    page_html = _http_get_text(
        f"{SPORTYTRADER_BASE_URL}{matched_path}",
        cache_key=f"sportytrader:page:{matched_path}",
        ttl_seconds=1800,
        timeout=4.0,
    )
    if not page_html:
        return None

    text_clean = html.unescape(re.sub(r"<[^>]+>", " ", page_html))
    text_clean = re.sub(r"\s+", " ", text_clean)

    # Extract SportyTrader ⭐ algorithm probabilities
    algo_probs: dict[str, float] = {}
    algo_match = re.search(
        r"algorithm estimates a\s+([\d.]+)%\s+chance of[^\d]+([\d.]+)%\s+chance of[^\d]+([\d.]+)%\s+chance",
        text_clean,
        re.IGNORECASE,
    )
    if algo_match:
        algo_probs = {
            "outcome_1_pct": _safe_float(algo_match.group(1)),
            "outcome_2_pct": _safe_float(algo_match.group(2)),
            "outcome_3_pct": _safe_float(algo_match.group(3)),
        }

    # Extract headline pick
    pick_match = re.search(
        r"prediction(?:\s+for[^:]+)?\s+is:\s*([^.!]+)",
        text_clean,
        re.IGNORECASE,
    )
    prediction_pick = pick_match.group(1).strip() if pick_match else None

    # Extract Key Points bullets
    key_points: list[str] = []
    kp_section = re.search(r"Key Points(.*?)(?:Our\s+[^<]+prediction|What are the best odds)", page_html, re.DOTALL | re.IGNORECASE)
    if kp_section:
        lis = re.findall(r"<li[^>]*>(.*?)</li>", kp_section.group(1), re.DOTALL | re.IGNORECASE)
        for li in lis[:6]:
            cleaned_li = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", li))).strip()
            if len(cleaned_li) >= 15:
                key_points.append(cleaned_li)

    out = {
        "provider": "expert_algorithm",
        "prediction_pick": prediction_pick,
        "algo_probabilities": algo_probs,
        "key_points": key_points,
    }
    _cache_set(cache_key, out, 1800)
    return out


# ---------------------------------------------------------------------------
# Extended League Analytics Feed Status
# ---------------------------------------------------------------------------
def lookup_footystats_intel() -> dict[str, Any]:
    """Return extended league analytics feed connectivity & key mode."""
    api_key = os.environ.get("FOOTYSTATS_API_KEY", "").strip() or "example"
    return {
        "provider": "extended_league_stats",
        "configured_key_mode": "licensed" if api_key != "example" else "demo_mode",
    }


# ---------------------------------------------------------------------------
# Primary Entrypoints: `lookup_funstats_team_intel` & `lookup_funstats_match_intel`
# ---------------------------------------------------------------------------
def lookup_funstats_team_intel(
    team_name: str,
    *,
    league_hint: str | int | None = None,
    season: int = DEFAULT_SEASON,
) -> dict[str, Any] | None:
    """Look up a single football club on `funstats.fyi` and return its 300+-field splits, streaks & xG."""
    if not team_name or not team_name.strip():
        return None
    lid = resolve_funstats_league_id(league_hint)
    resolved = _search_funstats_team(team_name, league_id=lid)
    if not resolved or not resolved.get("id"):
        return None

    team_id = int(resolved["id"])
    effective_lid = _safe_int(resolved.get("league_id") or lid or 39)
    standings_row = resolved.get("standings_row")
    if not standings_row and effective_lid:
        for r in _fetch_funstats_standings(effective_lid, season=season):
            if _safe_int(r.get("team_id") or r.get("id")) == team_id or _sdk_names_match(
                team_name, str(r.get("team_name") or "")
            ):
                standings_row = r
                break

    splits = extract_team_deep_splits(standings_row)

    # Fetch team active strikes
    strikes_raw = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/teams/{team_id}/strikes?league_id={effective_lid}&season={season}",
        cache_key=f"funstats:team_strikes:{team_id}:{effective_lid}:{season}",
        ttl_seconds=1800,
    )
    strikes_list = (
        strikes_raw.get("strikes")
        if isinstance(strikes_raw, dict) and isinstance(strikes_raw.get("strikes"), list)
        else (strikes_raw if isinstance(strikes_raw, list) else [])
    )

    # Fetch league xG table to find this team's xG regression
    xg_entry: dict[str, Any] | None = None
    xg_data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/leagues/{effective_lid}/xg?season={season}",
        cache_key=f"funstats:league_xg:{effective_lid}:{season}",
        ttl_seconds=3600,
    )
    xg_teams = (xg_data or {}).get("teams") if isinstance(xg_data, dict) else None
    if isinstance(xg_teams, list):
        for xt in xg_teams:
            if isinstance(xt, dict) and (
                _safe_int(xt.get("team_id")) == team_id
                or _sdk_names_match(team_name, str(xt.get("team_name") or ""))
            ):
                xg_for = _safe_float(xt.get("xg_for"))
                xg_against = _safe_float(xt.get("xg_against"))
                goals_for = _safe_int(xt.get("goals_for"))
                goals_against = _safe_int(xt.get("goals_against"))
                xg_entry = {
                    "xg_for": round(xg_for, 2),
                    "xg_against": round(xg_against, 2),
                    "goals_for": goals_for,
                    "goals_against": goals_against,
                    "goals_minus_xg": round(goals_for - xg_for, 2),
                    "ga_minus_xga": round(goals_against - xg_against, 2),
                }
                break

    return {
        "engine": "betscout_deep_stats",
        "team_id": team_id,
        "team_name": resolved.get("name") or team_name,
        "team_logo": resolved.get("logo"),
        "league_id": effective_lid,
        "season": season,
        "splits": splits,
        "active_streaks": strikes_list[:8],
        "xg_profile": xg_entry,
    }


def lookup_funstats_match_intel(
    home: str,
    away: str,
    *,
    league_hint: str | int | None = None,
    date_ymd: str | None = None,
    season: int = DEFAULT_SEASON,
    include_external_consensus: bool = True,
) -> dict[str, Any] | None:
    """Comprehensive FunStats.fyi + OLBG + SportyTrader intelligence lookup for ANY two football teams.

    Works both for scheduled fixtures (enriching with live 1X2/AH/OU odds, opening-to-current
    odds movement, 133,011-match empirical market calibration, historical odds twins, and
    injury-adjusted predicted lineups) AND for arbitrary unscheduled team pairs (using
    `/api/fixture-expansion?fixture_id=1` to pull 20 long-term H2H meetings, recent form,
    active streaks, and 300+-field standings splits).
    """
    home_clean = (home or "").strip()
    away_clean = (away or "").strip()
    if not home_clean or not away_clean:
        return None

    lid_hint = resolve_funstats_league_id(league_hint)
    cache_key = f"funstats:match_intel:v3:{home_clean.lower()}:{away_clean.lower()}:{lid_hint or 0}:{date_ymd or ''}"
    cached = _cache_get(cache_key)
    if isinstance(cached, dict):
        return cached

    # Step 1: Discover if `home` vs `away` is an active/scheduled fixture on FunStats
    matched_fixture: dict[str, Any] | None = None
    candidates: list[dict[str, Any]] = []
    candidates.extend(_fetch_funstats_fixtures_today())
    if date_ymd:
        candidates.extend(_fetch_funstats_fixtures_by_date(date_ymd))
    else:
        # Also check tomorrow in UTC
        tomorrow_ymd = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).strftime("%Y-%m-%d")
        candidates.extend(_fetch_funstats_fixtures_by_date(tomorrow_ymd))
    candidates.extend(_fetch_funstats_week_notable())

    for fx in candidates:
        ht = fx.get("home_team") if isinstance(fx.get("home_team"), dict) else {}
        at = fx.get("away_team") if isinstance(fx.get("away_team"), dict) else {}
        h_name = str(ht.get("name") or fx.get("home_team_name") or fx.get("home_name") or "")
        a_name = str(at.get("name") or fx.get("away_team_name") or fx.get("away_name") or "")
        if h_name and a_name and _sdk_names_match(home_clean, h_name) and _sdk_names_match(away_clean, a_name):
            matched_fixture = fx
            break

    fixture_id = 0
    home_team_id = 0
    away_team_id = 0
    league_id = lid_hint or 0
    home_resolved_name = home_clean
    away_resolved_name = away_clean
    home_logo: str | None = None
    away_logo: str | None = None

    if matched_fixture:
        fixture_id = _safe_int(matched_fixture.get("fixture_id") or matched_fixture.get("id"))
        ht = matched_fixture.get("home_team") if isinstance(matched_fixture.get("home_team"), dict) else {}
        at = matched_fixture.get("away_team") if isinstance(matched_fixture.get("away_team"), dict) else {}
        home_team_id = _safe_int(ht.get("id") or matched_fixture.get("home_team_id"))
        away_team_id = _safe_int(at.get("id") or matched_fixture.get("away_team_id"))
        home_resolved_name = str(ht.get("name") or matched_fixture.get("home_team_name") or home_clean)
        away_resolved_name = str(at.get("name") or matched_fixture.get("away_team_name") or away_clean)
        home_logo = ht.get("logo") or matched_fixture.get("home_team_logo")
        away_logo = at.get("logo") or matched_fixture.get("away_team_logo")
        league_id = _safe_int(matched_fixture.get("league_id") or lid_hint or 0)
        season = _safe_int(matched_fixture.get("season") or season, DEFAULT_SEASON)

    # Step 2: Resolve team IDs if not found in today's/week's fixtures
    home_info = _search_funstats_team(home_clean, league_id=league_id or None) if not home_team_id else None
    away_info = _search_funstats_team(away_clean, league_id=league_id or None) if not away_team_id else None

    if home_info and not home_team_id:
        home_team_id = _safe_int(home_info.get("id"))
        home_resolved_name = str(home_info.get("name") or home_clean)
        home_logo = home_info.get("logo")
        if not league_id and home_info.get("league_id"):
            league_id = _safe_int(home_info.get("league_id"))

    if away_info and not away_team_id:
        away_team_id = _safe_int(away_info.get("id"))
        away_resolved_name = str(away_info.get("name") or away_clean)
        away_logo = away_info.get("logo")
        if not league_id and away_info.get("league_id"):
            league_id = _safe_int(away_info.get("league_id"))

    if not home_team_id and not away_team_id and not fixture_id:
        return None

    effective_lid = league_id or 39

    # Step 3: Call `/api/fixture-expansion` (works with real `fixture_id` OR `fixture_id=1` for any pair!)
    expansion: dict[str, Any] | None = None
    if home_team_id and away_team_id:
        expansion = _fetch_funstats_fixture_expansion(
            fixture_id=fixture_id or 1,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            league_id=effective_lid,
            season=season,
        )

    raw_h2h = (expansion or {}).get("h2hMatches") if isinstance(expansion, dict) else None
    h2h_long_term = build_long_term_h2h_analytics(
        raw_h2h if isinstance(raw_h2h, list) else [],
        home_team_name=home_resolved_name,
        away_team_name=away_resolved_name,
        home_team_id=home_team_id or None,
        away_team_id=away_team_id or None,
    )

    # Step 4: Extract 300+-field standings splits for both teams
    standings_rows = _fetch_funstats_standings(effective_lid, season=season) if effective_lid else []
    home_st_row = (home_info or {}).get("standings_row")
    away_st_row = (away_info or {}).get("standings_row")
    for r in standings_rows:
        rid = _safe_int(r.get("team_id") or r.get("id"))
        rname = str(r.get("team_name") or r.get("name") or "")
        if not home_st_row and ((home_team_id and rid == home_team_id) or _sdk_names_match(home_clean, rname)):
            home_st_row = r
        if not away_st_row and ((away_team_id and rid == away_team_id) or _sdk_names_match(away_clean, rname)):
            away_st_row = r

    home_splits = extract_team_deep_splits(home_st_row)
    away_splits = extract_team_deep_splits(away_st_row)

    # Step 5: Extract active streaks + enrich top streaks with `/api/strikes/market-context`
    home_strikes_raw = (expansion or {}).get("homeTeamStrikesAll") or (expansion or {}).get("homeTeamStrikes") or []
    away_strikes_raw = (expansion or {}).get("awayTeamStrikesAll") or (expansion or {}).get("awayTeamStrikes") or []

    def _enrich_streaks(raw_list: Any, side_label: str, team_label: str) -> list[dict[str, Any]]:
        if not isinstance(raw_list, list):
            return []
        enriched: list[dict[str, Any]] = []
        for st in raw_list[:6]:
            if not isinstance(st, dict):
                continue
            stype = str(st.get("strike_type") or st.get("type") or "")
            length = _safe_int(st.get("strike_length") or st.get("length") or st.get("count"))
            item: dict[str, Any] = {
                "side": side_label,
                "team": team_label,
                "strike_type": stype,
                "length": length,
                "scope": st.get("scope") or ("home_away" if "_home" in stype or "_away" in stype else "overall"),
            }
            if stype in SUPPORTED_MARKET_CONTEXT_STREAKS and length >= 3 and len(enriched) < 2:
                mc = _http_get_json(
                    f"{FUNSTATS_BASE_URL}/api/strikes/market-context?league_id={effective_lid}&strike_type={urllib.parse.quote(stype)}&run_len={length}&fixture_id={fixture_id or 1}",
                    cache_key=f"funstats:strike_mc:{effective_lid}:{stype}:{length}",
                    ttl_seconds=86400,
                )
                if isinstance(mc, dict) and (mc.get("supported") or mc.get("n") or mc.get("sample_size")):
                    n_s = _safe_int(mc.get("sample_size") or mc.get("n"))
                    act_p = _safe_float(mc.get("actual_pct"))
                    exp_p = _safe_float(mc.get("market_expected_pct"))
                    item["market_context"] = {
                        "sample_size": n_s,
                        "continued_count": _safe_int(mc.get("continued_count") or mc.get("continued")),
                        "actual_pct": act_p,
                        "market_expected_pct": exp_p,
                        "edge_vs_market_pp": _safe_float(mc.get("edge_vs_market_pp")) or round(act_p - exp_p, 1),
                        "wilson_low_pct": _safe_float(mc.get("wilson_low_pct")),
                        "wilson_high_pct": _safe_float(mc.get("wilson_high_pct")),
                    }
            enriched.append(item)
        return enriched

    streaks = {
        "home": _enrich_streaks(home_strikes_raw, "home", home_resolved_name),
        "away": _enrich_streaks(away_strikes_raw, "away", away_resolved_name),
    }

    # Step 6: Season xG regression & League Empirical Scorelines
    xg_comparison: dict[str, Any] = {}
    xg_data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/leagues/{effective_lid}/xg?season={season}",
        cache_key=f"funstats:league_xg:{effective_lid}:{season}",
        ttl_seconds=3600,
    )
    if isinstance(xg_data, dict) and isinstance(xg_data.get("teams"), list):
        for xt in xg_data["teams"]:
            if not isinstance(xt, dict):
                continue
            tid = _safe_int(xt.get("team_id"))
            tname = str(xt.get("team_name") or "")
            entry = {
                "team_name": tname,
                "played": _safe_int(xt.get("played")),
                "goals_for": _safe_int(xt.get("goals_for")),
                "xg_for": round(_safe_float(xt.get("xg_for")), 2),
                "goals_minus_xg": round(_safe_int(xt.get("goals_for")) - _safe_float(xt.get("xg_for")), 2),
                "goals_against": _safe_int(xt.get("goals_against")),
                "xg_against": round(_safe_float(xt.get("xg_against")), 2),
            }
            if (home_team_id and tid == home_team_id) or _sdk_names_match(home_clean, tname):
                xg_comparison["home"] = entry
            elif (away_team_id and tid == away_team_id) or _sdk_names_match(away_clean, tname):
                xg_comparison["away"] = entry

    scorelines_top: list[dict[str, Any]] = []
    sl_data = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/leagues/{effective_lid}/scorelines?season={season}",
        cache_key=f"funstats:scorelines:{effective_lid}:{season}",
        ttl_seconds=7200,
    )
    sl_rows = (
        sl_data.get("scorelines") or sl_data.get("cells")
        if isinstance(sl_data, dict)
        else None
    )
    if isinstance(sl_rows, list):
        for sl in sl_rows[:6]:
            if isinstance(sl, dict):
                hg_sl = _safe_int(sl.get("home_goals") if "home_goals" in sl else sl.get("home"))
                ag_sl = _safe_int(sl.get("away_goals") if "away_goals" in sl else sl.get("away"))
                scorelines_top.append(
                    {
                        "score": f"{hg_sl}:{ag_sl}",
                        "count": _safe_int(sl.get("count")),
                        "pct": _safe_float(sl.get("pct") or sl.get("percentage") or sl.get("percent")),
                    }
                )

    # League macro rates (`/api/leagues/{lid}/per-season-stats`) & Upset Index (`/api/leagues/{lid}/upset-index`)
    league_macro_stats: dict[str, Any] | None = None
    pss_raw = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/leagues/{effective_lid}/per-season-stats?seasons={season},{season - 1}",
        cache_key=f"funstats:per_season_stats:{effective_lid}:{season}",
        ttl_seconds=7200,
    )
    if isinstance(pss_raw, list) and pss_raw:
        first_ps = pss_raw[0] if isinstance(pss_raw[0], dict) else {}
        st_ps = first_ps.get("stats") if isinstance(first_ps.get("stats"), dict) else first_ps
        if st_ps:
            league_macro_stats = {
                "season": _safe_int(first_ps.get("season"), season),
                "avg_goals_per_match": _safe_float(st_ps.get("avgGoalsPerMatch")),
                "home_win_rate_pct": _safe_float(st_ps.get("homeWinRate")),
                "draw_rate_pct": _safe_float(st_ps.get("drawRate")),
                "away_win_rate_pct": _safe_float(st_ps.get("awayWinRate")),
                "over_25_rate_pct": _safe_float(st_ps.get("over25Rate")),
                "btts_rate_pct": _safe_float(st_ps.get("bttsRate")),
                "avg_cards_per_match": _safe_float(st_ps.get("avgTotalCardsPerMatch")),
                "avg_corners_per_match": _safe_float(st_ps.get("avgTotalCornersPerMatch")),
            }

    recent_upsets: list[dict[str, Any]] = []
    up_raw = _http_get_json(
        f"{FUNSTATS_BASE_URL}/api/leagues/{effective_lid}/upset-index?season={season}&locale=en",
        cache_key=f"funstats:upset_index:{effective_lid}:{season}",
        ttl_seconds=7200,
    )
    up_list = up_raw.get("finished_upsets") or up_raw.get("upsets") if isinstance(up_raw, dict) else None
    if isinstance(up_list, list):
        for u in up_list[:4]:
            if isinstance(u, dict):
                recent_upsets.append(
                    {
                        "date": str(u.get("date") or "")[:10],
                        "home": u.get("home_team_name") or (u.get("home_team") or {}).get("name"),
                        "away": u.get("away_team_name") or (u.get("away_team") or {}).get("name"),
                        "score": f"{_safe_int(u.get('home_goals'))}:{_safe_int(u.get('away_goals'))}",
                        "winner_odd": _safe_float(u.get("winner_odd") or u.get("upset_odd")),
                    }
                )

    # Team profile narrative flags (`dual_life`, `giant_killer`, `blown_leads`, `handicap_minus1_rate`)
    team_profiles: dict[str, Any] = {}
    for side_k, tid_val in (("home", home_team_id), ("away", away_team_id)):
        if tid_val > 0:
            tp_raw = _http_get_json(
                f"{FUNSTATS_BASE_URL}/api/teams/{tid_val}/stats?locale=en",
                cache_key=f"funstats:team_stats:{tid_val}",
                ttl_seconds=3600,
            )
            if isinstance(tp_raw, dict) and tp_raw.get("id"):
                team_profiles[side_k] = {
                    "over25_last10_pct": _safe_float(tp_raw.get("over25_last10")),
                    "btts_last10_pct": _safe_float(tp_raw.get("btts10")),
                    "first_half_winrate_pct": _safe_float(tp_raw.get("first_half_winrate")),
                    "handicap_minus1_rate_pct": _safe_float(tp_raw.get("handicap_minus1_rate")),
                    "handicap_plus1_rate_pct": _safe_float(tp_raw.get("handicap_plus1_rate")),
                    "traits": tp_raw.get("funstats") if isinstance(tp_raw.get("funstats"), dict) else None,
                }

    # Step 7: Fixture-specific endpoints when `fixture_id > 0`
    market_calibration: dict[str, Any] | None = None
    odds_movement: dict[str, Any] | None = None
    similar_matches: list[dict[str, Any]] = []
    lineups_and_injuries: dict[str, Any] | None = None

    if fixture_id > 0:
        mc_raw = _http_get_json(
            f"{FUNSTATS_BASE_URL}/api/odds/{fixture_id}/market-calibration",
            cache_key=f"funstats:calibration:{fixture_id}",
            ttl_seconds=900,
        )
        if isinstance(mc_raw, dict) and (mc_raw.get("available") or mc_raw.get("league_bucket") or mc_raw.get("market_home_pct")):
            outcomes_out: list[dict[str, Any]] = []
            if isinstance(mc_raw.get("outcomes"), list) and mc_raw["outcomes"]:
                for oc in mc_raw["outcomes"]:
                    if not isinstance(oc, dict):
                        continue
                    market_pct = _safe_float(oc.get("market_pct"))
                    lg_bucket = oc.get("league") if isinstance(oc.get("league"), dict) else {}
                    all_bucket = oc.get("all_leagues") if isinstance(oc.get("all_leagues"), dict) else {}
                    lg_actual = _safe_float(lg_bucket.get("actual_pct"))
                    all_actual = _safe_float(all_bucket.get("actual_pct"))
                    outcomes_out.append(
                        {
                            "outcome": oc.get("outcome"),
                            "odd": _safe_float(oc.get("odd")),
                            "market_pct": market_pct,
                            "bucket_label": lg_bucket.get("bucket_label") or all_bucket.get("bucket_label"),
                            "league_actual_pct": lg_actual,
                            "league_sample": _safe_int(lg_bucket.get("sample")),
                            "league_delta_pp": round(lg_actual - market_pct, 1) if lg_bucket.get("sample") else 0.0,
                            "global_actual_pct": all_actual,
                            "global_sample": _safe_int(all_bucket.get("sample")),
                            "global_delta_pp": round(all_actual - market_pct, 1) if all_bucket.get("sample") else 0.0,
                        }
                    )
            else:
                # Current flat schema (`league_bucket`, `global_favorites`, `market_home_pct`..)
                lb = mc_raw.get("league_bucket") if isinstance(mc_raw.get("league_bucket"), dict) else {}
                gf = mc_raw.get("global_favorites") if isinstance(mc_raw.get("global_favorites"), dict) else {}
                b_lbl = f"{mc_raw.get('bucket_lower_pct', '')}-{mc_raw.get('bucket_upper_pct', '')}%"
                lg_n = _safe_int(lb.get("sample_size"))
                gl_n = _safe_int(gf.get("sample_size"))
                for oc_key, m_field, a_field in (
                    ("Home", "market_home_pct", "actual_home_pct"),
                    ("Draw", "market_draw_pct", "actual_draw_pct"),
                    ("Away", "market_away_pct", "actual_away_pct"),
                ):
                    m_p = _safe_float(lb.get(m_field) or mc_raw.get(m_field))
                    a_p = _safe_float(lb.get(a_field))
                    outcomes_out.append(
                        {
                            "outcome": oc_key,
                            "market_pct": m_p,
                            "bucket_label": b_lbl,
                            "league_actual_pct": a_p,
                            "league_sample": lg_n,
                            "league_delta_pp": round(a_p - m_p, 1) if lg_n else 0.0,
                            "global_sample": gl_n,
                        }
                    )
            market_calibration = {
                "outcomes": outcomes_out,
                "league_favorites": mc_raw.get("league_favorites"),
                "global_favorites": mc_raw.get("global_favorites"),
            }

        mov_raw = _http_get_json(
            f"{FUNSTATS_BASE_URL}/api/odds/{fixture_id}/movement",
            cache_key=f"funstats:movement:{fixture_id}",
            ttl_seconds=600,
        )
        if isinstance(mov_raw, dict) and (mov_raw.get("available") or mov_raw.get("opening") or mov_raw.get("open_1x2")):
            raw_open = mov_raw.get("open_1x2") or mov_raw.get("opening") or {}
            raw_curr = mov_raw.get("current_1x2") or mov_raw.get("current") or {}
            open_1x2 = {k.lower(): _safe_float(v) for k, v in raw_open.items()} if isinstance(raw_open, dict) else {}
            curr_1x2 = {k.lower(): _safe_float(v) for k, v in raw_curr.items()} if isinstance(raw_curr, dict) else {}
            deltas: dict[str, float] = {}
            for k in ("home", "draw", "away"):
                o_val = _safe_float(open_1x2.get(k))
                c_val = _safe_float(curr_1x2.get(k))
                if o_val > 0 and c_val > 0:
                    deltas[k] = round(c_val - o_val, 3)
            pts = mov_raw.get("points") if isinstance(mov_raw.get("points"), list) else []
            odds_movement = {
                "open_1x2": open_1x2,
                "current_1x2": curr_1x2,
                "delta_1x2": deltas,
                "change_points": _safe_int(mov_raw.get("change_points"), len(pts)),
                "first_seen_at": mov_raw.get("first_seen_at") or (pts[0].get("recorded_at") if pts else None),
                "updated_at": mov_raw.get("updated_at") or (pts[-1].get("recorded_at") if pts else None),
            }

        sim_raw = _http_get_json(
            f"{FUNSTATS_BASE_URL}/api/odds/{fixture_id}/similar-recent?locale=en",
            cache_key=f"funstats:similar:{fixture_id}",
            ttl_seconds=1800,
        )
        if isinstance(sim_raw, dict) and isinstance(sim_raw.get("matches"), list):
            for sm in sim_raw["matches"][:5]:
                if isinstance(sm, dict):
                    similar_matches.append(
                        {
                            "date": str(sm.get("date") or "")[:10],
                            "home": sm.get("home_team_name") or sm.get("home"),
                            "away": sm.get("away_team_name") or sm.get("away"),
                            "score": f"{_safe_int(sm.get('home_goals'))}:{_safe_int(sm.get('away_goals'))}",
                            "outcome": sm.get("outcome"),
                            "market_home_pct": _safe_float(sm.get("market_home_pct")),
                        }
                    )

        sec_raw = _http_get_json(
            f"{FUNSTATS_BASE_URL}/api/matches/{fixture_id}/sections-dynamic?locale=en",
            cache_key=f"funstats:sections_dynamic:{fixture_id}",
            ttl_seconds=900,
        )
        if isinstance(sec_raw, dict):
            inj_outer = sec_raw.get("injuries") if isinstance(sec_raw.get("injuries"), dict) else {}
            inj = inj_outer.get("data") if isinstance(inj_outer.get("data"), dict) else inj_outer
            pred_outer = sec_raw.get("predictedLineup") if isinstance(sec_raw.get("predictedLineup"), dict) else {}
            pred = pred_outer.get("data") if isinstance(pred_outer.get("data"), dict) else pred_outer
            cont_outer = sec_raw.get("lineupContinuity") if isinstance(sec_raw.get("lineupContinuity"), dict) else {}
            cont = cont_outer.get("data") if isinstance(cont_outer.get("data"), dict) else cont_outer
            facts = sec_raw.get("funstatsFacts") if isinstance(sec_raw.get("funstatsFacts"), list) else []
            lineups_and_injuries = {
                "injuries": {
                    "home": (inj.get("home") or [])[:8] if isinstance(inj.get("home"), list) else [],
                    "away": (inj.get("away") or [])[:8] if isinstance(inj.get("away"), list) else [],
                },
                "injuries_applied": pred.get("injuriesApplied") if isinstance(pred.get("injuriesApplied"), dict) else None,
                "predicted_lineup": {
                    "home_formation": (pred.get("home") or {}).get("formation") if isinstance(pred.get("home"), dict) else None,
                    "away_formation": (pred.get("away") or {}).get("formation") if isinstance(pred.get("away"), dict) else None,
                    "home_starters": [
                        {
                            "name": p.get("name"),
                            "position": p.get("pos") or p.get("position"),
                            "is_fill_in": bool(p.get("isFillIn")),
                            "doubtful": bool(p.get("doubtful")),
                        }
                        for p in (((pred.get("home") or {}).get("players") or (pred.get("home") or {}).get("starters")) or [])[:11]
                        if isinstance(p, dict)
                    ],
                    "away_starters": [
                        {
                            "name": p.get("name"),
                            "position": p.get("pos") or p.get("position"),
                            "is_fill_in": bool(p.get("isFillIn")),
                            "doubtful": bool(p.get("doubtful")),
                        }
                        for p in (((pred.get("away") or {}).get("players") or (pred.get("away") or {}).get("starters")) or [])[:11]
                        if isinstance(p, dict)
                    ],
                },
                "lineup_continuity": cont,
                "curated_facts": [str(f.get("text") or f) if isinstance(f, dict) else str(f) for f in facts[:8]],
            }

    # Step 8: Multi-source External Consensus (OLBG + SportyTrader + FootyStats)
    olbg_consensus = lookup_olbg_match_consensus(home_clean, away_clean) if include_external_consensus else None
    sportytrader_intel = lookup_sportytrader_match_intel(home_clean, away_clean) if include_external_consensus else None

    # Step 9: Synthesize high-conviction quantitative key insights across all sources
    key_insights: list[str] = []
    key_insights.extend(h2h_long_term.get("insights") or [])

    if market_calibration and isinstance(market_calibration.get("outcomes"), list):
        for oc in market_calibration["outcomes"]:
            delta = _safe_float(oc.get("global_delta_pp") or oc.get("league_delta_pp"))
            sample_n = _safe_int(oc.get("global_sample") or oc.get("league_sample"))
            actual_v = _safe_float(oc.get("global_actual_pct") or oc.get("league_actual_pct"))
            if abs(delta) >= 3.0 and sample_n >= 20:
                direction = "outperformed" if delta > 0 else "underperformed"
                key_insights.append(
                    f"Historical Odds Calibration ({oc.get('outcome')}, bucket {oc.get('bucket_label')}): "
                    f"actual {actual_v:.1f}% vs market {oc.get('market_pct'):.1f}% "
                    f"({delta:+.1f}pp {direction} across {sample_n} matches)"
                )

    for side_key in ("home", "away"):
        for st in streaks.get(side_key) or []:
            mc = st.get("market_context")
            if isinstance(mc, dict) and abs(_safe_float(mc.get("edge_vs_market_pp"))) >= 2.5:
                key_insights.append(
                    f"Active Streak ({st.get('team')} {st.get('strike_type')} = {st.get('length')}): "
                    f"continues {mc.get('actual_pct'):.1f}% historically vs {mc.get('market_expected_pct'):.1f}% priced "
                    f"({mc.get('edge_vs_market_pp'):+.1f}pp edge, 95% Wilson CI [{mc.get('wilson_low_pct'):.1f}%, {mc.get('wilson_high_pct'):.1f}%])"
                )

    for side_key, label in (("home", home_resolved_name), ("away", away_resolved_name)):
        xg_row = xg_comparison.get(side_key)
        if isinstance(xg_row, dict):
            diff = _safe_float(xg_row.get("goals_minus_xg"))
            if abs(diff) >= 3.5:
                status = "overperforming xG (negative regression watch)" if diff > 0 else "underperforming xG (positive regression candidate)"
                key_insights.append(
                    f"xG Regression ({label}): {xg_row.get('goals_for')}G vs {xg_row.get('xg_for')} xG ({diff:+.2f}G, {status})"
                )

    if olbg_consensus and isinstance(olbg_consensus.get("top_tip"), dict):
        tt = olbg_consensus["top_tip"]
        if tt.get("selection") and _safe_float(tt.get("confidence_pct")) > 0:
            key_insights.append(
                f"Crowd Tipster Consensus: {tt.get('confidence_pct'):.0f}% on '{tt.get('selection')}' "
                f"({tt.get('selection_tips')}/{tt.get('market_tips')} tips in {tt.get('market')} @ {tt.get('decimal_odds')})"
            )

    if sportytrader_intel and sportytrader_intel.get("prediction_pick"):
        key_insights.append(f"Algorithmic Expert Pick: {sportytrader_intel.get('prediction_pick')}")

    payload: dict[str, Any] = {
        "available": True,
        "engine": "betscout_deep_stats",
        "fixture_id": fixture_id or None,
        "league_id": effective_lid,
        "season": season,
        "home_team": {
            "id": home_team_id or None,
            "name": home_resolved_name,
            "logo": home_logo,
        },
        "away_team": {
            "id": away_team_id or None,
            "name": away_resolved_name,
            "logo": away_logo,
        },
        "h2h_long_term": h2h_long_term,
        "team_splits": {
            "home": home_splits,
            "away": away_splits,
        },
        "streaks": streaks,
        "xg_comparison": xg_comparison,
        "league_top_scorelines": scorelines_top,
        "league_macro_stats": league_macro_stats,
        "recent_league_upsets": recent_upsets,
        "team_profiles": team_profiles,
        "market_calibration": market_calibration,
        "odds_movement": odds_movement,
        "similar_odds_matches": similar_matches,
        "lineups_and_injuries": lineups_and_injuries,
        "external_consensus": {
            "crowd_consensus": olbg_consensus,
            "expert_preview": sportytrader_intel,
            "extended_stats": lookup_footystats_intel(),
        },
        "key_insights": key_insights[:12],
    }

    _cache_set(cache_key, payload, 1200)
    return payload
