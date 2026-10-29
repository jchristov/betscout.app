"""BetScout Sports Data & Odds Client (`BetScoutClient`) for Python.

Mirrors the TypeScript `@betscout/sdk` (`sdk/typescript`) with 1:1 method parity,
providing both Pythonic `snake_case` and TypeScript-compatible `camelCase` method aliases.
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from ._internal.transport import (
    DEFAULT_UPSTREAM_BASE_URL,
    build_upstream_feed_url,
    resolve_upstream_channel,
)
from .constants import SPORTS_CATALOG, resolve_sport_id
from .utils import (
    compute_form_wdl_segments,
    compute_h2h_edge_summary,
    format_market_placeholders,
    get_adaptive_refetch_interval_ms,
    get_country_flag_url,
    get_team_logo_url,
    merge_primary_and_consensus_markets,
    names_match,
    parse_prematch_markets,
    render_team_jersey_svg,
)

_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Origin": "https://statshub.sportradar.com",
    "Referer": "https://statshub.sportradar.com/tipico/en/",
    "Accept": "application/json",
}


def _today_ymd_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _next_day_ymd_utc(ymd: str) -> str:
    try:
        dt = datetime.strptime(ymd[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (dt + timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        return ymd


def _format_utc_iso_minutes(uts_seconds: int | float) -> str:
    return datetime.fromtimestamp(float(uts_seconds), tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%MZ"
    )


_STATIC_LONG_TTL_ENDPOINTS: set[str] = {
    "config_sports",
    "config_tree_mini",
    "config_uniquetournaments",
    "config_uniquetournamentsall",
    "tennis_calendar",
    "stats_team_info",
    "tennis_team_surfacestats",
    "stats_team_versus",
    "stats_h2h_versus",
    "stats_season_meta",
    "stats_season_venues",
    "stats_tournament_seasons_winners",
    "stats_uniquetournament_info",
}

_HISTORICAL_MEDIUM_TTL_ENDPOINTS: set[str] = {
    "stats_team_lastx",
    "stats_team_lastxextended",
    "stats_season_tables",
    "stats_season_goals",
    "stats_season_overunder",
    "stats_season_injuries",
    "stats_team_streaks",
    "stats_team_scoringconceding",
    "stats_team_squad",
    "stats_team_usuallineup",
    "stats_team_transfers",
    "stats_team_seasonstats",
    "stats_player_careerstats",
}

_LIVE_SHORT_TTL_ENDPOINTS: set[str] = {
    "match_timelinedelta",
    "match_detailsextended",
    "match_timeline",
    "match_situations",
    "match_phrases",
    "match_phrasesdelta",
}


def _resolve_smart_endpoint_ttl_sec(
    endpoint: str,
    params_path: str,
    explicit_ttl_sec: float | None,
    default_ttl_sec: float,
) -> float:
    if explicit_ttl_sec is not None:
        return explicit_ttl_sec
    ep = endpoint.strip("/").lower()
    if ep in _LIVE_SHORT_TTL_ENDPOINTS:
        return 5.0
    if ep == "match_markets" and str(params_path).lower().endswith("/live"):
        return 8.0
    if ep in _STATIC_LONG_TTL_ENDPOINTS:
        return 3600.0
    if ep in _HISTORICAL_MEDIUM_TTL_ENDPOINTS:
        return 1200.0
    if ep in ("unified_sport_matches", "match_info_statshub", "match_markets"):
        return 600.0
    return default_ttl_sec


class BetScoutClient:
    """Unified Sports Data, Live Scores, Player/Team Historical Analytics & Multi-Bookmaker Odds Client."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        default_channel: str = "eu-retail",
        default_language: str = "en",
        default_timezone: str = "Europe:Berlin",
        default_ttl_sec: float = 300.0,
        negative_ttl_sec: float = 120.0,
        max_cache_entries: int = 2000,
        timeout_sec: float = 12.0,
        fetch_fn: Callable[[str, dict[str, str], float], dict[str, Any] | None] | None = None,
    ) -> None:
        self.base_url = (base_url or DEFAULT_UPSTREAM_BASE_URL).rstrip("/")
        self.default_channel = default_channel
        self.default_language = default_language
        self.default_timezone = default_timezone
        self.default_ttl_sec = default_ttl_sec
        self.negative_ttl_sec = negative_ttl_sec
        self.max_cache_entries = max_cache_entries
        self.timeout_sec = timeout_sec
        self._fetch_fn = fetch_fn
        # cache_key -> (expires_at, data, doc0, is_negative)
        self._cache: dict[str, tuple[float, Any, dict[str, Any] | None, bool]] = {}
        self._hits = 0
        self._misses = 0
        self._negative_hits = 0
        self._stale_fallbacks = 0

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    @property
    def cacheSize(self) -> int:
        return len(self._cache)

    def get_cache_stats(self) -> dict[str, int]:
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "negativeHits": self._negative_hits,
            "staleFallbacks": self._stale_fallbacks,
        }

    getCacheStats = get_cache_stats

    def clear_cache(self) -> None:
        self._cache.clear()

    def _set_cache_entry(
        self,
        key: str,
        expires_at: float,
        data: Any,
        doc0: dict[str, Any] | None,
        is_negative: bool = False,
    ) -> None:
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self.max_cache_entries:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = (expires_at, data, doc0, is_negative)

    def build_relative_path(
        self,
        endpoint: str,
        params_path: str = "",
        *,
        channel: str | None = None,
        language: str | None = None,
        timezone_str: str | None = None,
    ) -> str:
        resolved_channel = resolve_upstream_channel(channel or self.default_channel)
        lang = language or self.default_language
        tz = timezone_str or self.default_timezone
        clean_ep = endpoint.strip("/")
        clean_params = str(params_path or "").strip("/")
        return (
            f"{resolved_channel}/{lang}/{tz}/gismo/{clean_ep}/{clean_params}"
            if clean_params
            else f"{resolved_channel}/{lang}/{tz}/gismo/{clean_ep}"
        )

    def fetch_document(
        self,
        endpoint: str,
        params_path: str = "",
        *,
        channel: str | None = None,
        language: str | None = None,
        timezone_str: str | None = None,
        ttl_sec: float | None = None,
        bypass_cache: bool = False,
    ) -> dict[str, Any] | None:
        resolved_channel = resolve_upstream_channel(channel or self.default_channel)
        ttl = _resolve_smart_endpoint_ttl_sec(
            endpoint, params_path, ttl_sec, self.default_ttl_sec
        )
        cache_key = f"{resolved_channel}:{endpoint}:{params_path}"
        now = time.time()
        existing = self._cache.get(cache_key)

        if not bypass_cache and ttl > 0 and existing and existing[0] > now:
            if existing[3]:
                self._negative_hits += 1
                return None
            if existing[2] is not None:
                self._hits += 1
                return existing[2]

        self._misses += 1
        url = build_upstream_feed_url(
            self.base_url,
            resolved_channel,
            language or self.default_language,
            timezone_str or self.default_timezone,
            endpoint,
            params_path,
        )

        try:
            if self._fetch_fn is not None:
                payload = self._fetch_fn(url, _DEFAULT_HEADERS, self.timeout_sec)
            else:
                req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
                ctx = ssl.create_default_context()
                if hasattr(ssl, "VERIFY_X509_STRICT"):
                    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
                with urllib.request.urlopen(req, timeout=self.timeout_sec, context=ctx) as resp:
                    payload = json.loads(resp.read().decode("utf-8", errors="replace"))

            doc0 = (payload or {}).get("doc", [None])[0] if isinstance(payload, dict) else None
            if isinstance(doc0, dict) and doc0.get("event") != "exception":
                data = doc0.get("data")
                if not (isinstance(data, dict) and data.get("_doc") == "exception"):
                    maxage = doc0.get("_maxage")
                    eff_ttl = (
                        ttl
                        if ttl_sec is not None
                        else (float(maxage) if isinstance(maxage, (int, float)) and maxage > ttl else ttl)
                    )
                    if eff_ttl > 0:
                        self._set_cache_entry(cache_key, now + eff_ttl, data, doc0, False)
                    return doc0

            if ttl > 0 and self.negative_ttl_sec > 0:
                self._set_cache_entry(
                    cache_key, now + min(ttl, self.negative_ttl_sec), None, None, True
                )
            return None
        except Exception:
            if existing and existing[2] is not None and not existing[3]:
                self._stale_fallbacks += 1
                return existing[2]
            return None

    def fetch_feed(
        self,
        endpoint: str,
        params_path: str = "",
        *,
        channel: str | None = None,
        language: str | None = None,
        timezone_str: str | None = None,
        ttl_sec: float | None = None,
        bypass_cache: bool = False,
    ) -> Any:
        doc = self.fetch_document(
            endpoint,
            params_path,
            channel=channel,
            language=language,
            timezone_str=timezone_str,
            ttl_sec=ttl_sec,
            bypass_cache=bypass_cache,
        )
        return doc.get("data") if isinstance(doc, dict) else None

    # ==========================================================================
    # A. Configuration & Sport / Tournament Discovery
    # ==========================================================================

    def list_all_sports(
        self,
        service_id: int = 69,
        config_id: int = 0,
        channel: str = "global",
    ) -> list[dict[str, Any]]:
        data = self.fetch_feed(
            "config_sports",
            f"{service_id}/{config_id}",
            channel=channel,
            timezone_str="Etc:UTC",
            ttl_sec=3600,
        )
        if isinstance(data, list) and data:
            return [
                {"sportId": int(s["_id"]), "name": str(s["name"])}
                for s in data
                if isinstance(s, dict) and isinstance(s.get("_id"), int)
            ]
        return [{"sportId": int(k), "name": v} for k, v in SPORTS_CATALOG.items()]

    def get_category_tree(
        self,
        service_id: int = 69,
        config_id: int = 0,
        sport_or_id: str | int = 1,
        rc_id: int | None = None,
    ) -> dict[str, Any] | None:
        sid = resolve_sport_id(sport_or_id)
        params = (
            f"{service_id}/{config_id}/{sid}/{rc_id}"
            if rc_id is not None
            else f"{service_id}/{config_id}/{sid}"
        )
        return self.fetch_feed("config_tree_mini", params, channel="global", ttl_sec=3600)

    def get_unique_tournaments(
        self,
        service_id: int = 69,
        sport_or_id: str | int = 1,
    ) -> Any:
        sid = resolve_sport_id(sport_or_id)
        return self.fetch_feed(
            "config_uniquetournaments", f"{service_id}/{sid}", channel="global", ttl_sec=3600
        )

    def get_all_unique_tournaments(
        self,
        service_id: int = 69,
        sport_or_id: str | int = 1,
    ) -> Any:
        sid = resolve_sport_id(sport_or_id)
        return self.fetch_feed(
            "config_uniquetournamentsall",
            f"0/{service_id}/{sid}",
            channel="global",
            ttl_sec=3600,
        )

    def get_tennis_calendar(self, season_year: int | str | None = None) -> dict[str, Any] | None:
        yr = season_year or datetime.now(timezone.utc).year
        return self.fetch_feed("tennis_calendar", str(yr), channel="neutral", ttl_sec=3600)

    # ==========================================================================
    # B. Daily Match Schedules & Multi-Bookmaker Markets
    # ==========================================================================

    def get_daily_sport_matches(
        self,
        sport_or_id: str | int = "soccer",
        date_ymd: str | None = None,
        tz_offset: int = 0,
    ) -> dict[str, Any] | None:
        sid = resolve_sport_id(sport_or_id)
        ymd = date_ymd or _today_ymd_utc()
        return self.fetch_feed("unified_sport_matches", f"{sid}/{ymd}/{tz_offset}", ttl_sec=600)

    def get_daily_sport_markets(
        self,
        sport_or_id: str | int = "soccer",
        date_ymd: str | None = None,
        channel: str = "eu-retail",
        tz_offset: int = 0,
    ) -> dict[str, Any] | None:
        sid = resolve_sport_id(sport_or_id)
        ymd = date_ymd or _today_ymd_utc()
        return self.fetch_feed(
            "unified_sport_matches_markets",
            f"{sid}/{ymd}/{tz_offset}",
            channel=channel,
            ttl_sec=600,
        )

    def get_match_markets(
        self,
        match_id: int | str,
        market_type: str = "prematch",
        channel: str = "eu-retail",
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "match_markets", f"{match_id}/{market_type}", channel=channel, ttl_sec=600
        )

    def get_season_markets(
        self,
        season_id: int | str,
        channel: str = "eu-retail",
    ) -> dict[str, Any] | None:
        return self.fetch_feed("season_markets", str(season_id), channel=channel, ttl_sec=1800)

    # ==========================================================================
    # C. Match Intelligence, Live 3s Delta Stream, Squads, Injuries, Form & H2H
    # ==========================================================================

    def get_match_timeline_delta(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "match_timelinedelta", str(match_id), channel="global", ttl_sec=3
        )

    def get_live_events_by_sport(self, sport_or_id: str | int = "soccer") -> dict[str, Any] | None:
        sid = resolve_sport_id(sport_or_id)
        return self.fetch_feed("event_get", str(sid), channel="global", ttl_sec=10)

    def get_match_info(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "match_info_statshub", str(match_id), channel="global", ttl_sec=60
        )

    def get_match_squads(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("match_squads", str(match_id), channel="global", ttl_sec=300)

    def get_season_injuries(self, season_id: int | str) -> list[dict[str, Any]] | None:
        res = self.fetch_feed("stats_season_injuries", str(season_id), ttl_sec=1800)
        return res if isinstance(res, list) else None

    def get_match_form(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("stats_match_form", str(match_id), ttl_sec=1800)

    def get_match_head2head(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("stats_match_head2head", str(match_id), ttl_sec=1800)

    def get_head2head_versus(
        self,
        team_id_a: int | str,
        team_id_b: int | str,
        limit: int = 10,
    ) -> dict[str, Any] | None:
        a_num, b_num = int(team_id_a), int(team_id_b)
        min_uid, max_uid = min(a_num, b_num), max(a_num, b_num)
        return self.fetch_feed(
            "stats_h2h_versus",
            f"{min_uid}/{max_uid}/{limit}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_match_situations(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("match_situations", str(match_id), channel="neutral", ttl_sec=45)

    def get_match_stats(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("stats_match_stats", str(match_id), ttl_sec=120)

    def get_match_details(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("match_details", str(match_id), channel="global", ttl_sec=30)

    def get_match_details_extended(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "match_detailsextended", str(match_id), channel="global", ttl_sec=30
        )

    # ==========================================================================
    # D. Team & Player Profiles, Historical Performance, Squads & Season Stats
    # ==========================================================================

    def get_team_profile(self, team_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("stats_team_info", str(team_id), channel="global", ttl_sec=3600)

    def get_team_last_matches(
        self, team_id: int | str, limit: int = 20
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_lastx", f"{team_id}/{limit}", channel="global", ttl_sec=1800
        )

    def get_team_last_matches_extended(
        self, team_id: int | str, limit: int = 20
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_lastxextended", f"{team_id}/{limit}", channel="global", ttl_sec=1800
        )

    def get_team_next_matches(
        self, team_id: int | str, limit: int = 10
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_nextx", f"{team_id}/{limit}", channel="global", ttl_sec=900
        )

    def get_team_streaks(self, team_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_streaks", str(team_id), channel="neutral", ttl_sec=1800
        )

    def get_team_seasons(self, team_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("uniqueteam_seasons", str(team_id), channel="global", ttl_sec=3600)

    def get_team_season_stats(
        self, team_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_seasonstats",
            f"{team_id}/{season_id}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_team_season_matches(
        self, team_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_seasonmatches",
            f"{team_id}/{season_id}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_team_scoring_conceding_splits(
        self, season_id: int | str, team_id: int | str, limit: int = 10
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_teamscoringconceding",
            f"{season_id}/{team_id}/{limit}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_team_position_history(
        self, season_id: int | str, team_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_teampositionhistory",
            f"{season_id}/{team_id}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_team_squad(self, team_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("stats_team_squad", str(team_id), channel="global", ttl_sec=3600)

    def get_team_season_squad(
        self, team_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_seasonsquad2",
            f"{team_id}/{season_id}",
            channel="neutral",
            ttl_sec=3600,
        )

    def get_team_usual_lineup(
        self, team_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_usuallineup",
            f"{team_id}/{season_id}",
            channel="neutral",
            ttl_sec=3600,
        )

    def get_team_transfers(self, team_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_transfers", str(team_id), channel="global", ttl_sec=3600
        )

    def get_team_tournaments(self, team_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_tournaments", str(team_id), channel="global", ttl_sec=3600
        )

    def get_team_season_officials(
        self, team_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_uniqueteam_seasonofficials",
            f"{team_id}/{season_id}",
            channel="neutral",
            ttl_sec=3600,
        )

    def get_player_career_stats(self, player_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_player_stats", str(player_id), channel="neutral", ttl_sec=3600
        )

    def get_player_facts(self, player_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_player_facts", str(player_id), channel="neutral", ttl_sec=3600
        )

    def get_player_season_matches(
        self, player_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "player_seasonmatches",
            f"{player_id}/{season_id}",
            channel="neutral",
            ttl_sec=1800,
        )

    # ==========================================================================
    # E. Tennis Career, League Ranking Tables, Form Tables & Goal/Pace Analytics
    # ==========================================================================

    def get_tennis_player_surface_stats(self, player_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "tennis_team_surfacestats", str(player_id), channel="neutral", ttl_sec=3600
        )

    def get_tennis_ranking(
        self, tour_type: str, year: int | str, week: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "tennis_ranking", f"{tour_type}/{year}/{week}", channel="neutral", ttl_sec=3600
        )

    def get_season_tables(
        self,
        season_id: int | str,
        table_type: int | str | None = None,
        round_num: int | str | None = None,
    ) -> dict[str, Any] | None:
        parts = [
            str(x)
            for x in (season_id, table_type, round_num)
            if x is not None and str(x) != ""
        ]
        return self.fetch_feed(
            "stats_season_tables", "/".join(parts), channel="neutral", ttl_sec=1800
        )

    def get_season_dynamic_table(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "season_dynamictable", str(season_id), channel="neutral", ttl_sec=120
        )

    def get_season_form_table(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("stats_formtable", str(season_id), channel="neutral", ttl_sec=900)

    def get_match_table_slice(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_match_tableslice", str(match_id), channel="neutral", ttl_sec=900
        )

    def get_enriched_league_table(
        self,
        season_id: int | str,
        *,
        around_team_uid: int | str | None = None,
        slice_size: int = 5,
    ) -> dict[str, Any]:
        tables_resp = self.get_season_tables(season_id)
        form_resp = self.get_season_form_table(season_id)

        tables = (tables_resp or {}).get("tables") or []
        main_table = tables[0] if tables else None
        if not isinstance(main_table, dict) or not isinstance(main_table.get("tablerows"), list):
            return {
                "ok": False,
                "season_id": season_id,
                "season_name": (tables_resp or {}).get("name"),
                "current_round": None,
                "max_rounds": None,
                "tiebreak_rules": None,
                "rows": [],
            }

        form_by_team_id: dict[int, dict[str, list[dict[str, Any]]]] = {}
        for ft_entry in (form_resp or {}).get("teams") or []:
            team_obj = ft_entry.get("team") or {}
            tid = team_obj.get("uid") or team_obj.get("_id")
            if not tid:
                continue
            f_dict = ft_entry.get("form") or {}
            form_by_team_id[int(tid)] = {
                "total": list(reversed(f_dict.get("total") or [])),
                "home": list(reversed(f_dict.get("home") or [])),
                "away": list(reversed(f_dict.get("away") or [])),
            }

        raw_rows = sorted(
            main_table["tablerows"],
            key=lambda r: int(r.get("pos") or 0),
        )

        if around_team_uid is not None and len(raw_rows) > slice_size:
            target_uid = int(around_team_uid)
            idx = next(
                (
                    i
                    for i, r in enumerate(raw_rows)
                    if int((r.get("team") or {}).get("uid") or (r.get("team") or {}).get("_id") or 0)
                    == target_uid
                ),
                -1,
            )
            if idx >= 0:
                half = (slice_size - 1) // 2
                start = max(0, min(len(raw_rows) - slice_size, idx - half))
                raw_rows = raw_rows[start : start + slice_size]

        enriched_rows: list[dict[str, Any]] = []
        for row in raw_rows:
            t_obj = row.get("team") or {}
            uid = int(t_obj.get("uid") or t_obj.get("_id") or 0)
            f_obj = form_by_team_id.get(uid, {"total": [], "home": [], "away": []})
            promo = row.get("promotion") or {}
            enriched_rows.append(
                {
                    "pos": int(row.get("pos") or 0),
                    "pos_home": row.get("posHome"),
                    "pos_away": row.get("posAway"),
                    "change_total": int(row.get("changeTotal") or 0),
                    "change_home": int(row.get("changeHome") or 0),
                    "change_away": int(row.get("changeAway") or 0),
                    "team_id": int(t_obj.get("_id") or uid),
                    "team_uid": uid,
                    "team_name": str(t_obj.get("mediumname") or t_obj.get("name") or ""),
                    "team_abbr": str(t_obj.get("abbr") or ""),
                    "promotion": promo.get("name"),
                    "promotion_short": promo.get("shortname"),
                    "played": {
                        "total": int(row.get("total") or 0),
                        "home": int(row.get("home") or 0),
                        "away": int(row.get("away") or 0),
                    },
                    "win": {
                        "total": int(row.get("winTotal") or 0),
                        "home": int(row.get("winHome") or 0),
                        "away": int(row.get("winAway") or 0),
                    },
                    "draw": {
                        "total": int(row.get("drawTotal") or 0),
                        "home": int(row.get("drawHome") or 0),
                        "away": int(row.get("drawAway") or 0),
                    },
                    "loss": {
                        "total": int(row.get("lossTotal") or 0),
                        "home": int(row.get("lossHome") or 0),
                        "away": int(row.get("lossAway") or 0),
                    },
                    "goals_for": {
                        "total": int(row.get("goalsForTotal") or 0),
                        "home": int(row.get("goalsForHome") or 0),
                        "away": int(row.get("goalsForAway") or 0),
                    },
                    "goals_against": {
                        "total": int(row.get("goalsAgainstTotal") or 0),
                        "home": int(row.get("goalsAgainstHome") or 0),
                        "away": int(row.get("goalsAgainstAway") or 0),
                    },
                    "goal_diff": {
                        "total": int(row.get("goalDiffTotal") or 0),
                        "home": int(row.get("goalDiffHome") or 0),
                        "away": int(row.get("goalDiffAway") or 0),
                    },
                    "points": {
                        "total": int(row.get("pointsTotal") or 0),
                        "home": int(row.get("pointsHome") or 0),
                        "away": int(row.get("pointsAway") or 0),
                    },
                    "form_total": [str(x.get("value") or x.get("typeid")) for x in f_obj["total"]],
                    "form_home": [str(x.get("value") or x.get("typeid")) for x in f_obj["home"]],
                    "form_away": [str(x.get("value") or x.get("typeid")) for x in f_obj["away"]],
                    "form_entries_total": f_obj["total"],
                }
            )

        return {
            "ok": True,
            "season_id": season_id,
            "season_name": main_table.get("name") or (tables_resp or {}).get("name"),
            "current_round": main_table.get("currentround")
            or (form_resp or {}).get("currentround"),
            "max_rounds": main_table.get("maxrounds"),
            "tiebreak_rules": (main_table.get("rules") or {}).get("name"),
            "rows": enriched_rows,
        }

    def get_season_over_under(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_overunder", str(season_id), channel="neutral", ttl_sec=1800
        )

    def get_season_goals_distribution(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_goals", str(season_id), channel="neutral", ttl_sec=1800
        )

    def get_season_unique_team_stats(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_uniqueteamstats", str(season_id), channel="neutral", ttl_sec=1800
        )

    def get_team_versus(
        self, team_id_a: int | str, team_id_b: int | str, limit: int = 10
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_team_versus",
            f"{team_id_a}/{team_id_b}/{limit}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_unique_tournament_info(
        self, unique_tournament_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "uniquetournament_info",
            str(unique_tournament_id),
            channel="neutral",
            ttl_sec=3600,
        )

    def get_tournament_seasons_winners(
        self, unique_tournament_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "uniquetournament_seasonswinners",
            str(unique_tournament_id),
            channel="neutral",
            ttl_sec=3600,
        )

    def get_season_meta(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_meta", str(season_id), channel="neutral", ttl_sec=3600
        )

    def get_cup_brackets(self, bracket_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_cup_brackets", str(bracket_id), channel="neutral", ttl_sec=1800
        )

    def get_season_referees(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_referees", str(season_id), channel="neutral", ttl_sec=3600
        )

    def get_season_competitors(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_teams2", str(season_id), channel="neutral", ttl_sec=3600
        )

    def get_season_schedule(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_fixtures2", str(season_id), channel="neutral", ttl_sec=1800
        )

    def get_season_last_matches(
        self, season_id: int | str, limit: int = 20
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_lastx", f"{season_id}/{limit}", channel="neutral", ttl_sec=900
        )

    def get_season_next_matches(
        self, season_id: int | str, limit: int = 20
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_nextx", f"{season_id}/{limit}", channel="neutral", ttl_sec=900
        )

    def get_competition_seasons(
        self, unique_tournament_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "uniquetournament_seasons",
            str(unique_tournament_id),
            channel="neutral",
            ttl_sec=3600,
        )

    # ==========================================================================
    # J. Stage Sports (Formula 1, MotoGP, NASCAR, IndyCar, Rally, Cycling, Winter Sports) & Cricket
    # ==========================================================================

    def get_stage_seasons(self, real_category_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stage_seasons", str(real_category_id), channel="global", ttl_sec=3600
        )

    def get_stage_season_summary(self, stage_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stage_seasonsummary", str(stage_id), channel="global", ttl_sec=1800
        )

    def get_stage_details(self, stage_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("stage_get", str(stage_id), channel="global", ttl_sec=900)

    def get_stage_calendar(self, stage_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_stage_calendar", str(stage_id), channel="global", ttl_sec=3600
        )

    def get_stage_day_events(
        self, sport_or_id: str | int = 40, date_ymd: str | None = None
    ) -> dict[str, Any] | None:
        sid = resolve_sport_id(sport_or_id)
        ymd = date_ymd or _today_ymd_utc()
        return self.fetch_feed("stage_day", f"{sid}/{ymd}", channel="global", ttl_sec=600)

    def get_cricket_events(self) -> dict[str, Any] | None:
        url = f"{self.base_url}/common/en/Etc:UTC/cricket/get_events"
        try:
            if self._fetch_fn is not None:
                payload = self._fetch_fn(url, _DEFAULT_HEADERS, self.timeout_sec)
            else:
                req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
                ctx = ssl.create_default_context()
                if hasattr(ssl, "VERIFY_X509_STRICT"):
                    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
                with urllib.request.urlopen(req, timeout=self.timeout_sec, context=ctx) as resp:
                    payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            doc0 = (payload or {}).get("doc", [None])[0] if isinstance(payload, dict) else None
            return doc0.get("data") if isinstance(doc0, dict) else None
        except Exception:
            return None

    def get_match_full_timeline(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("match_timeline", str(match_id), channel="neutral", ttl_sec=60)

    def get_referee_season_stats(
        self, referee_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "referee_seasonstats",
            f"{referee_id}/{season_id}",
            channel="neutral",
            ttl_sec=3600,
        )

    # ==========================================================================
    # F. Visual Assets (Team Logos, Country Flags & Player Jersey SVG Avatars)
    # ==========================================================================

    def get_team_logo_url(
        self,
        team_id: int | str,
        *,
        size: str = "big",
        ncaa: bool = False,
        ncaa_size: str = "ap250x188ut",
    ) -> str:
        return get_team_logo_url(team_id, size=size, ncaa=ncaa, ncaa_size=ncaa_size)

    def get_country_flag_url(
        self,
        country_iso2: str,
        *,
        fmt: str = "svg",
        ratio: str = "4x3",
        size: str = "medium",
    ) -> str:
        return get_country_flag_url(country_iso2, fmt=fmt, ratio=ratio, size=size)

    def render_team_jersey_svg(
        self,
        jersey: dict[str, Any] | None = None,
        *,
        shirt_number: int | str | None = None,
        size_px: int = 96,
    ) -> str:
        return render_team_jersey_svg(jersey, shirt_number=shirt_number, size_px=size_px)

    # ==========================================================================
    # G. Insights, Editorial Commentary, Venues & Team/Futures Markets
    # ==========================================================================

    def get_match_insights(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("match_funfacts", str(match_id), channel="neutral", ttl_sec=300)

    def get_match_commentary(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("match_phrases", str(match_id), channel="neutral", ttl_sec=30)

    def get_match_commentary_delta(self, match_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed("match_phrasesdelta", str(match_id), channel="neutral", ttl_sec=5)

    def get_season_league_summary(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_leaguesummary", str(season_id), channel="neutral", ttl_sec=3600
        )

    def get_team_player_season_facts(
        self, team_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_teamplayer_facts",
            f"{team_id}/{season_id}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_season_venues(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_venues", str(season_id), channel="neutral", ttl_sec=3600
        )

    def get_venue_season_stats(
        self, stadium_id: int | str, season_id: int | str
    ) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_venuestats",
            f"{stadium_id}/{season_id}",
            channel="neutral",
            ttl_sec=1800,
        )

    def get_season_top_scorers(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_topgoals", str(season_id), channel="neutral", ttl_sec=1800
        )

    def get_season_top_assists(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_topassists", str(season_id), channel="neutral", ttl_sec=1800
        )

    def get_season_top_cards(self, season_id: int | str) -> dict[str, Any] | None:
        return self.fetch_feed(
            "stats_season_topcards", str(season_id), channel="neutral", ttl_sec=1800
        )

    def get_team_markets(
        self, team_id: int | str, channel: str = "eu-retail"
    ) -> dict[str, Any] | None:
        return self.fetch_feed("uniqueteam_markets", str(team_id), channel=channel, ttl_sec=900)

    def get_odds_format_table(self) -> list[dict[str, Any]] | None:
        res = self.fetch_feed(
            "odds_ukformat", "", channel="neutral", language="agnostic", ttl_sec=86400
        )
        return res if isinstance(res, list) else None

    # ==========================================================================
    # High-Level Composite Intelligence Workflows
    # ==========================================================================

    def get_daily_match_index(
        self,
        sport_or_id: str | int = "soccer",
        date_ymd: str | None = None,
    ) -> list[dict[str, Any]]:
        u_data = self.get_daily_sport_matches(sport_or_id, date_ymd, 0) or {}
        flat: list[dict[str, Any]] = []
        youth_or_amateur: list[dict[str, Any]] = []

        for rc in (u_data.get("sport") or {}).get("realcategories") or []:
            rc_name = str(rc.get("name") or "")
            rc_low = rc_name.lower()
            if "simulated reality" in rc_low or "esoccer" in rc_low:
                continue
            for t in rc.get("tournaments") or []:
                t_label = " · ".join(x for x in (rc_name, t.get("name") or "") if x)
                t_low = t_label.lower()
                if " srl" in t_low or "simulated reality" in t_low:
                    continue
                is_sub = any(
                    w in t_low
                    for w in ("amateur", "u19", "u20", "u21", "u18", "u17", "youth", "reserve")
                )
                for m in t.get("matches") or []:
                    h_nm = str(((m.get("teams") or {}).get("home") or {}).get("name") or "")
                    a_nm = str(((m.get("teams") or {}).get("away") or {}).get("name") or "")
                    if h_nm.endswith(" SRL") or a_nm.endswith(" SRL"):
                        continue
                    entry = {
                        "match_obj": m,
                        "tournament": t_label,
                        "home": h_nm,
                        "away": a_nm,
                    }
                    if is_sub:
                        youth_or_amateur.append(entry)
                    else:
                        flat.append(entry)
        return flat + youth_or_amateur

    def fetch_team_goal_intervals(
        self, season_id: int | str, team_id: int | str, limit: int = 10
    ) -> dict[str, Any]:
        data = self.get_team_scoring_conceding_splits(season_id, team_id, limit) or {}
        st = data.get("stats")
        if not isinstance(st, dict):
            return {}

        sc = st.get("scoring") or {}
        co = st.get("conceding") or {}
        sc_mins = sc.get("goalsbyminutes") or {}
        co_mins = co.get("goalsbyminutes") or {}
        buckets = ("0-15", "16-30", "31-45", "46-60", "61-75", "76-90")
        intervals: dict[str, dict[str, float]] = {}

        for b in buckets:
            s_v = float((sc_mins.get(b) or {}).get("total") or 0.0)
            c_v = float((co_mins.get(b) or {}).get("total") or 0.0)
            intervals[b] = {
                "scored_per_match": round(s_v, 3),
                "conceded_per_match": round(c_v, 3),
                "combined_per_match": round(s_v + c_v, 3),
            }

        fh_scored = float((sc.get("goalsscoredfirsthalfaverage") or {}).get("total") or 0.0)
        fh_conceded = float((co.get("goalsconcededfirsthalfaverage") or {}).get("total") or 0.0)
        ht_rate = float((sc.get("scoringathalftimeaverage") or {}).get("total") or 0.0)
        btts_rate = float((sc.get("bothteamsscoredaverage") or {}).get("total") or 0.0)
        late_s = intervals["76-90"]["scored_per_match"]
        late_c = intervals["76-90"]["conceded_per_match"]

        return {
            "matches_sampled": int((st.get("totalmatches") or {}).get("total") or 0),
            "first_half_scored_avg": round(fh_scored, 2),
            "first_half_conceded_avg": round(fh_conceded, 2),
            "scoring_in_1h_pct": round(ht_rate * 100.0, 1),
            "btts_pct": round(btts_rate * 100.0, 1),
            "late_76_90_scored_avg": round(late_s, 2),
            "late_76_90_conceded_avg": round(late_c, 2),
            "late_76_90_total_avg": round(late_s + late_c, 2),
            "intervals": intervals,
        }

    def fetch_live_match_situations_pressure(self, match_id: int | str) -> dict[str, Any]:
        data = self.get_match_situations(match_id) or {}
        sits = data.get("situations")
        if not isinstance(sits, list) or not sits:
            return {}

        cnt = {
            "home": {"attack": 0, "dangerous_attack": 0, "safe": 0},
            "away": {"attack": 0, "dangerous_attack": 0, "safe": 0},
        }
        for s in sits:
            tm = s.get("team")
            st_type = s.get("situation")
            if tm in ("home", "away") and st_type in cnt[tm]:
                cnt[tm][st_type] += 1

        h_da = cnt["home"]["dangerous_attack"]
        a_da = cnt["away"]["dangerous_attack"]
        tot_da = max(1, h_da + a_da)
        return {
            "home_attacks": cnt["home"]["attack"],
            "away_attacks": cnt["away"]["attack"],
            "home_dangerous_attacks": h_da,
            "away_dangerous_attacks": a_da,
            "home_danger_share_pct": round((h_da / tot_da) * 100.0, 1),
            "away_danger_share_pct": round((a_da / tot_da) * 100.0, 1),
        }

    def evaluate_injury_gate(
        self,
        season_id: int | str | None,
        backed_uid: int | str | None,
        opp_uid: int | str | None,
    ) -> dict[str, Any]:
        if not season_id or not backed_uid:
            return {
                "status": "NO_SEASON_DATA",
                "backed_out": [],
                "opp_out": [],
                "prob_adjustment": 0.0,
                "veto_recommended": False,
            }

        inj_list = self.get_season_injuries(season_id)
        if not isinstance(inj_list, list):
            return {
                "status": "NO_INJURY_FEED",
                "backed_out": [],
                "opp_out": [],
                "prob_adjustment": 0.0,
                "veto_recommended": False,
            }

        backed_out: list[str] = []
        opp_out: list[str] = []
        backed_fwd_out = 0
        backed_gk_out = 0
        opp_fwd_out = 0

        for item in inj_list:
            ut_id = (item.get("uniqueteam") or {}).get("_id")
            if ut_id not in (int(backed_uid), int(opp_uid) if opp_uid else -1):
                continue
            p_obj = item.get("player") or {}
            p_nm = p_obj.get("name") or ""
            if not p_nm:
                continue
            pos_s = (p_obj.get("position") or {}).get("shortname") or ""
            st_obj = item.get("status") or {}
            st_nm = st_obj.get("name") or st_obj.get("status") or "Out"
            entry = f"{p_nm} ({pos_s}, {st_nm})" if pos_s else f"{p_nm} ({st_nm})"

            if ut_id == int(backed_uid):
                backed_out.append(entry)
                if pos_s in ("FWD", "F"):
                    backed_fwd_out += 1
                elif pos_s in ("GK", "G"):
                    backed_gk_out += 1
            elif opp_uid and ut_id == int(opp_uid):
                opp_out.append(entry)
                if pos_s in ("FWD", "F"):
                    opp_fwd_out += 1

        net_diff = len(backed_out) - len(opp_out)
        prob_adj = 0.0
        if backed_fwd_out >= 2 or net_diff >= 3:
            prob_adj -= min(0.06, 0.015 * backed_fwd_out + 0.008 * max(0, net_diff))
        elif opp_fwd_out >= 2 or net_diff <= -3:
            prob_adj += min(0.04, 0.012 * opp_fwd_out + 0.006 * max(0, -net_diff))

        veto_rec = bool(
            backed_fwd_out >= 3 or (backed_fwd_out >= 2 and backed_gk_out >= 1) or net_diff >= 5
        )
        status = (
            f"ALERT_DEPLETED_SQUAD ({len(backed_out)} Out, {backed_fwd_out} FWD)"
            if veto_rec
            else (
                f"TRACKED ({len(backed_out)} Out vs {len(opp_out)} Opp)"
                if (backed_out or opp_out)
                else "CLEAN_SQUAD"
            )
        )
        return {
            "status": status,
            "backed_out": backed_out[:8],
            "opp_out": opp_out[:8],
            "backed_fwd_out": backed_fwd_out,
            "backed_gk_out": backed_gk_out,
            "prob_adjustment": round(prob_adj, 4),
            "veto_recommended": veto_rec,
        }

    def get_team_missing_players(
        self,
        team_id: int | str,
        *,
        season_id: int | str | None = None,
        active_only: bool = True,
        reference_uts: int | None = None,
    ) -> list[dict[str, Any]]:
        ref_uts = reference_uts if reference_uts is not None else int(time.time())
        target_sid = season_id
        if not target_sid:
            seasons_data = self.get_team_seasons(team_id) or {}
            s_list = seasons_data.get("seasons") or []
            if isinstance(s_list, list) and s_list:
                curr = next(
                    (s for s in s_list if s.get("current") and s.get("containsdata")),
                    next((s for s in s_list if s.get("current")), s_list[0]),
                )
                target_sid = curr.get("_id")

        if not target_sid:
            return []

        inj_list = self.get_season_injuries(target_sid) or []
        num_tid = int(team_id)
        out: list[dict[str, Any]] = []

        for item in inj_list:
            if (item.get("uniqueteam") or {}).get("_id") != num_tid:
                continue
            p = item.get("player") or {}
            st = item.get("status") or {}
            if not p.get("name") or not st:
                continue
            start_uts = (st.get("start") or {}).get("uts")
            end_uts = (st.get("end") or {}).get("uts")
            is_active = end_uts is None or int(end_uts) >= ref_uts
            if active_only and not is_active:
                continue
            pos_obj = p.get("position") or {}
            out.append(
                {
                    "player_id": int(p.get("_id") or item.get("_playerid") or 0),
                    "name": str(p["name"]),
                    "position": str(pos_obj.get("shortname") or pos_obj.get("abbr") or ""),
                    "shirt_number": p.get("shirtnumber"),
                    "cause": str(st.get("name") or "Out"),
                    "status": str(st.get("status") or "Missing"),
                    "status_id": int(st.get("_id") or 0),
                    "start_date": (st.get("start") or {}).get("date"),
                    "end_date": (st.get("end") or {}).get("date"),
                    "start_uts": int(start_uts) if start_uts is not None else None,
                    "end_uts": int(end_uts) if end_uts is not None else None,
                    "is_active": is_active,
                }
            )
        return out

    def get_team_intelligence_bundle(
        self,
        team_id: int | str,
        *,
        season_id: int | str | None = None,
        injury_season_id: int | str | None = None,
        last_matches_limit: int = 15,
        next_matches_limit: int = 10,
    ) -> dict[str, Any]:
        profile = self.get_team_profile(team_id)
        seasons_data = self.get_team_seasons(team_id) or {}
        streaks_data = self.get_team_streaks(team_id) or {}
        last_matches_data = self.get_team_last_matches(team_id, last_matches_limit) or {}
        next_matches_data = self.get_team_next_matches(team_id, next_matches_limit) or {}
        squad_data = self.get_team_squad(team_id) or {}

        s_list = (
            seasons_data.get("seasons")
            if isinstance(seasons_data.get("seasons"), list)
            else []
        )

        active_sid = season_id
        if not active_sid and (last_matches_data.get("matches") or []):
            active_sid = last_matches_data["matches"][0].get("_seasonid")
        if not active_sid and s_list:
            cand = next(
                (s for s in s_list if s.get("containsdata") and s.get("year") == "25/26"),
                next((s for s in s_list if s.get("containsdata")), s_list[0]),
            )
            active_sid = cand.get("_id")

        curr_inj_sid = (
            injury_season_id
            or next(
                (s.get("_id") for s in s_list if s.get("current") and s.get("containsdata")),
                None,
            )
            or next((s.get("_id") for s in s_list if s.get("current")), None)
            or active_sid
        )

        season_stats = None
        scoring_splits = None
        goal_intervals: dict[str, Any] = {}
        usual_lineup = None
        missing_players: list[dict[str, Any]] = []

        if active_sid:
            s_stats = self.get_team_season_stats(team_id, active_sid) or {}
            season_stats = s_stats.get("stats")
            scoring_splits = self.get_team_scoring_conceding_splits(active_sid, team_id, 10)
            goal_intervals = self.fetch_team_goal_intervals(active_sid, team_id, 10)
            usual_lineup = self.get_team_usual_lineup(team_id, active_sid)
            if curr_inj_sid:
                missing_players = self.get_team_missing_players(team_id, season_id=curr_inj_sid)

        streak_labels: list[str] = []
        for st_type, scope_obj in (streaks_data.get("streaks") or {}).items():
            tot_v = ((scope_obj or {}).get("total") or {}).get("value")
            if tot_v and int(tot_v) >= 2:
                streak_labels.append(f"{st_type}: {tot_v}")

        squad_players = squad_data.get("players") or []
        return {
            "ok": bool(profile or last_matches_data),
            "team_id": int(team_id),
            "profile": profile,
            "seasons": s_list,
            "active_season_id": active_sid,
            "season_stats": season_stats,
            "scoring_conceding_splits": scoring_splits,
            "goal_intervals": goal_intervals,
            "usual_lineup": usual_lineup,
            "squad_count": len(squad_players),
            "squad": squad_players,
            "missing_players": missing_players,
            "streaks": streak_labels,
            "next_matches_difficulty": streaks_data.get("nextmatches") or [],
            "last_matches": last_matches_data.get("matches") or [],
            "next_matches": next_matches_data.get("matches") or [],
        }

    def get_tennis_player_intelligence_bundle(
        self,
        player_id: int | str,
        *,
        last_matches_limit: int = 15,
        next_matches_limit: int = 5,
    ) -> dict[str, Any]:
        profile = self.get_team_profile(player_id)
        surface_stats = self.get_tennis_player_surface_stats(player_id) or {}
        streaks_data = self.get_team_streaks(player_id) or {}
        last_matches_data = self.get_team_last_matches_extended(player_id, last_matches_limit) or {}
        next_matches_data = self.get_team_next_matches(player_id, next_matches_limit) or {}

        singles = surface_stats.get("singles") or {}
        singles_yr = singles.get("2026") or singles.get("2025") or {}
        all_rec = singles_yr.get("0") if isinstance(singles_yr.get("0"), dict) else {}
        clay_rec = singles_yr.get("1") if isinstance(singles_yr.get("1"), dict) else {}
        hard_rec = singles_yr.get("2") if isinstance(singles_yr.get("2"), dict) else {}
        indoor_rec = singles_yr.get("3") if isinstance(singles_yr.get("3"), dict) else {}
        grass_rec = singles_yr.get("4") if isinstance(singles_yr.get("4"), dict) else {}

        streak_labels: list[str] = []
        for st_type, scope_obj in (streaks_data.get("streaks") or {}).items():
            tot_v = ((scope_obj or {}).get("total") or {}).get("value")
            if tot_v and int(tot_v) >= 2:
                streak_labels.append(f"{st_type}: {tot_v}")

        return {
            "ok": bool(profile or surface_stats),
            "player_id": int(player_id),
            "profile": profile,
            "current_surface_summary": {
                "season_wl": f"{all_rec.get('wins', 0)}-{all_rec.get('losses', 0)}",
                "hard_wl": f"{hard_rec.get('wins', 0)}-{hard_rec.get('losses', 0)}",
                "clay_wl": f"{clay_rec.get('wins', 0)}-{clay_rec.get('losses', 0)}",
                "indoor_wl": f"{indoor_rec.get('wins', 0)}-{indoor_rec.get('losses', 0)}",
                "grass_wl": f"{grass_rec.get('wins', 0)}-{grass_rec.get('losses', 0)}",
            },
            "career_surface_stats": surface_stats,
            "streaks": streak_labels,
            "last_matches": last_matches_data.get("matches") or [],
            "next_matches": next_matches_data.get("matches") or [],
        }

    def get_match_center_dossier(
        self,
        match_id: int | str,
        *,
        last_matches_limit: int = 10,
    ) -> dict[str, Any]:
        """Build a complete Match Center Dossier (replicating /match/76034538 or /match/71945344)."""
        match_info = self.get_match_info(match_id)
        timeline_delta = self.get_match_timeline_delta(match_id)
        full_timeline = self.get_match_full_timeline(match_id)
        match_details = self.get_match_details_extended(match_id)
        match_stats = self.get_match_stats(match_id)
        match_form = self.get_match_form(match_id)
        head2head = self.get_match_head2head(match_id)
        mm_primary = self.get_match_markets(match_id, "prematch", "eu-retail")
        mm_consensus = self.get_match_markets(match_id, "prematch", "global")
        fun_facts_resp = self.get_match_insights(match_id)
        phrases_resp = self.get_match_commentary(match_id)
        squads = self.get_match_squads(match_id)
        table_slice = self.get_match_table_slice(match_id)

        m = (timeline_delta or {}).get("match") or (match_info or {}).get("match") or {}
        sport_id = int(m.get("_sid") or ((match_info or {}).get("match") or {}).get("_sid") or 1)
        sport_name = SPORTS_CATALOG.get(sport_id, f"Sport #{sport_id}")

        teams_obj = ((match_info or {}).get("match") or {}).get("teams") or m.get("teams") or {}
        h_team = teams_obj.get("home") or {}
        a_team = teams_obj.get("away") or {}
        h_uid = h_team.get("uid") or h_team.get("_id")
        a_uid = a_team.get("uid") or a_team.get("_id")
        season_id = (
            ((match_info or {}).get("season") or {}).get("_id")
            or m.get("_seasonid")
            or (((match_info or {}).get("match") or {}).get("_seasonid"))
        )

        versus = self.get_team_versus(h_uid, a_uid, 10) if (h_uid and a_uid) else None
        home_profile = self.get_team_profile(h_uid) if h_uid else None
        away_profile = self.get_team_profile(a_uid) if a_uid else None
        home_surface = (
            self.get_tennis_player_surface_stats(h_uid) if (sport_id == 5 and h_uid) else None
        )
        away_surface = (
            self.get_tennis_player_surface_stats(a_uid) if (sport_id == 5 and a_uid) else None
        )
        home_season_stats_resp = (
            self.get_team_season_stats(h_uid, season_id)
            if (sport_id != 5 and h_uid and season_id)
            else None
        )
        away_season_stats_resp = (
            self.get_team_season_stats(a_uid, season_id)
            if (sport_id != 5 and a_uid and season_id)
            else None
        )
        home_scoring_conceding = (
            self.get_team_scoring_conceding_splits(season_id, h_uid, 10)
            if (sport_id != 5 and h_uid and season_id)
            else None
        )
        away_scoring_conceding = (
            self.get_team_scoring_conceding_splits(season_id, a_uid, 10)
            if (sport_id != 5 and a_uid and season_id)
            else None
        )
        home_missing_players = (
            self.get_team_missing_players(h_uid, season_id=season_id)
            if (sport_id != 5 and h_uid and season_id)
            else []
        )
        away_missing_players = (
            self.get_team_missing_players(a_uid, season_id=season_id)
            if (sport_id != 5 and a_uid and season_id)
            else []
        )
        home_streaks = self.get_team_streaks(h_uid) if h_uid else None
        away_streaks = self.get_team_streaks(a_uid) if a_uid else None
        home_last = (
            self.get_team_last_matches_extended(h_uid, last_matches_limit) if h_uid else None
        )
        away_last = (
            self.get_team_last_matches_extended(a_uid, last_matches_limit) if a_uid else None
        )
        home_next = self.get_team_next_matches(h_uid, 3) if h_uid else None
        away_next = self.get_team_next_matches(a_uid, 3) if a_uid else None

        primary_parsed = parse_prematch_markets((mm_primary or {}).get("markets"), False)
        consensus_parsed = parse_prematch_markets((mm_consensus or {}).get("markets"), False)
        merged_markets = merge_primary_and_consensus_markets(primary_parsed, consensus_parsed)
        raw_markets = (
            (mm_consensus or {}).get("markets")
            if (mm_consensus or {}).get("markets")
            else ((mm_primary or {}).get("markets") or [])
        )

        home_last_list = (home_last or {}).get("matches") or []
        away_last_list = (away_last or {}).get("matches") or []
        home_form_wdl = compute_form_wdl_segments(home_last_list, h_uid, 5)
        away_form_wdl = compute_form_wdl_segments(away_last_list, a_uid, 5)
        h2h_edge = compute_h2h_edge_summary((versus or {}).get("matches"), h_uid, a_uid)

        return {
            "ok": bool(match_info or timeline_delta),
            "match_id": int(match_id),
            "sport_id": sport_id,
            "sport_name": sport_name,
            "match_info": match_info,
            "timeline_delta": timeline_delta,
            "full_timeline": full_timeline,
            "match_details": match_details,
            "match_stats": match_stats,
            "match_form": match_form,
            "head2head": head2head,
            "versus": versus,
            "primary_markets": primary_parsed,
            "consensus_markets": consensus_parsed,
            "merged_markets": merged_markets,
            "raw_markets": raw_markets,
            "home_profile": home_profile,
            "away_profile": away_profile,
            "home_surface_stats": home_surface,
            "away_surface_stats": away_surface,
            "home_season_stats": (home_season_stats_resp or {}).get("stats"),
            "away_season_stats": (away_season_stats_resp or {}).get("stats"),
            "home_scoring_conceding": home_scoring_conceding,
            "away_scoring_conceding": away_scoring_conceding,
            "home_missing_players": home_missing_players,
            "away_missing_players": away_missing_players,
            "home_streaks": home_streaks,
            "away_streaks": away_streaks,
            "home_last_matches": home_last_list,
            "away_last_matches": away_last_list,
            "home_next_matches": (home_next or {}).get("matches") or [],
            "away_next_matches": (away_next or {}).get("matches") or [],
            "fun_facts": (fun_facts_resp or {}).get("funfacts") or [],
            "commentary_phrases": (phrases_resp or {}).get("phrases") or [],
            "squads": squads,
            "table_slice": table_slice,
            "form_wdl": {
                "home": home_form_wdl["segments"],
                "away": away_form_wdl["segments"],
                "home_form_pct": home_form_wdl["formPct"],
                "away_form_pct": away_form_wdl["formPct"],
            },
            "h2h_edge": h2h_edge,
        }

    def build_insights_push_url(
        self,
        *,
        league: str = "nba",
        provider: str = "sportradar",
        insight_type: str | None = None,
        subject_type: str | None = None,
        game_id: str | int | None = None,
        team_id: str | int | None = None,
        player_id: str | int | None = None,
    ) -> str:
        from urllib.parse import urlencode

        q: dict[str, str] = {}
        if insight_type:
            q["insight_type"] = insight_type
        if subject_type:
            q["subject_type"] = subject_type
        if game_id is not None:
            q["game_id"] = str(game_id)
        if team_id is not None:
            q["team_id"] = str(team_id)
        if player_id is not None:
            q["player_id"] = str(player_id)
        qs = urlencode(q)
        return f"https://api.sportradar.com/insights/production/stream/{league}/{provider}/subscribe{f'?{qs}' if qs else ''}"

    def stream_insights(
        self,
        *,
        api_key: str | None = None,
        league: str = "nba",
        provider: str = "sportradar",
        insight_type: str | None = None,
        subject_type: str | None = None,
        game_id: str | int | None = None,
        team_id: str | int | None = None,
        player_id: str | int | None = None,
        sport_or_id: str | int | None = None,
        max_events: int | None = None,
    ):
        """Dual-Mode Real-Time Insights & Live Delta Stream generator."""
        emitted = 0
        if api_key:
            url = self.build_insights_push_url(
                league=league,
                provider=provider,
                insight_type=insight_type,
                subject_type=subject_type,
                game_id=game_id,
                team_id=team_id,
                player_id=player_id,
            )
            req = urllib.request.Request(
                url,
                headers={"x-api-key": api_key, "Accept": "application/json"},
            )
            ctx = ssl.create_default_context()
            if hasattr(ssl, "VERIFY_X509_STRICT"):
                ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
            with urllib.request.urlopen(req, timeout=30.0, context=ctx) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        is_hb = "heartbeat" in parsed or parsed.get("type") == "heartbeat"
                        yield {
                            "mode": "push_stream",
                            "event_type": "heartbeat" if is_hb else "raw_insight",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "match_id": parsed.get("subject_id") or game_id,
                            "summary": parsed.get("text"),
                            "payload": parsed,
                        }
                        emitted += 1
                        if max_events and emitted >= max_events:
                            return
                    except Exception:
                        continue
            return

        seen_ids: set[str] = set()
        numeric_mid = (
            str(game_id).replace("sr:match:", "") if game_id is not None else None
        )
        sid = resolve_sport_id(sport_or_id or league or "soccer")

        while True:
            sleep_ms = 5000
            if numeric_mid:
                delta_doc = self.fetch_document(
                    "match_timelinedelta", numeric_mid, channel="global", bypass_cache=True
                )
                phrases_delta = self.get_match_commentary_delta(numeric_mid)
                fun_facts = self.get_match_insights(numeric_mid) if not seen_ids else None
                sleep_ms = get_adaptive_refetch_interval_ms(delta_doc)

                for fact in (fun_facts or {}).get("funfacts") or []:
                    fid = f"fact:{fact}"
                    if fid not in seen_ids:
                        seen_ids.add(fid)
                        yield {
                            "mode": "tokenless_delta",
                            "event_type": "funfact",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "match_id": numeric_mid,
                            "summary": fact,
                            "payload": {"sentence": fact},
                        }
                        emitted += 1
                        if max_events and emitted >= max_events:
                            return

                delta_data = (delta_doc or {}).get("data") or {}
                for ev in delta_data.get("events") or []:
                    eid = f"ev:{ev.get('_id') or ev.get('uts')}"
                    if eid not in seen_ids:
                        seen_ids.add(eid)
                        yield {
                            "mode": "tokenless_delta",
                            "event_type": "scoring",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "match_id": numeric_mid,
                            "summary": str(ev.get("name") or ev.get("type") or "score_change"),
                            "payload": ev,
                        }
                        emitted += 1
                        if max_events and emitted >= max_events:
                            return

                for ph in (phrases_delta or {}).get("phrases") or []:
                    pid = f"ph:{ph.get('_id')}"
                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        yield {
                            "mode": "tokenless_delta",
                            "event_type": "commentary",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "match_id": numeric_mid,
                            "summary": ph.get("text"),
                            "payload": ph,
                        }
                        emitted += 1
                        if max_events and emitted >= max_events:
                            return
            else:
                ev_doc = self.fetch_document(
                    "event_get", str(sid), channel="global", bypass_cache=True
                )
                sleep_ms = get_adaptive_refetch_interval_ms(ev_doc)
                ev_data = (ev_doc or {}).get("data") or {}
                for ev in (ev_data.get("events") or [])[:15]:
                    eid = f"sp:{ev.get('_id') or ev.get('uts')}"
                    if eid not in seen_ids:
                        seen_ids.add(eid)
                        yield {
                            "mode": "tokenless_delta",
                            "event_type": "sport_event",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "match_id": ev.get("matchid"),
                            "summary": str(ev.get("type") or "live_event"),
                            "payload": ev,
                        }
                        emitted += 1
                        if max_events and emitted >= max_events:
                            return

            yield {
                "mode": "tokenless_delta",
                "event_type": "heartbeat",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "match_id": numeric_mid,
                "summary": f"Heartbeat (next poll in {sleep_ms}ms)",
                "payload": {"nextPollMs": sleep_ms},
            }
            emitted += 1
            if max_events and emitted >= max_events:
                return
            time.sleep(sleep_ms / 1000.0)

    # ==========================================================================
    # I. Betting Splits v3 (Commercial REST/Push + Tokenless Retail vs Consensus Divergence)
    # ==========================================================================

    def build_betting_splits_url(
        self,
        *,
        game_id: str | int,
        product: str = "nba",
        access_level: str = "production",
        language_code: str = "en",
        competition_id: str | int | None = None,
    ) -> str:
        from urllib.parse import quote

        gid = quote(str(game_id))
        if product == "soccer":
            raw_comp = competition_id if competition_id is not None else "sr:competition:17"
            comp_id = (
                str(raw_comp)
                if str(raw_comp).startswith("sr:competition:")
                else f"sr:competition:{raw_comp}"
            )
            return f"https://api.sportradar.com/betting-splits/v3/{access_level}/soccer/{language_code}/competition/{quote(comp_id)}/game/{gid}"
        return f"https://api.sportradar.com/betting-splits/v3/{access_level}/{product}/{language_code}/game/{gid}"

    def build_betting_splits_push_url(self, product: str = "nba") -> str:
        return f"https://api.sportradar.com/betting-splits/production/stream/{product}/subscribe"

    def get_betting_splits(
        self,
        *,
        game_id: str | int,
        product: str = "soccer",
        api_key: str | None = None,
        access_level: str = "production",
        language_code: str = "en",
        competition_id: str | int | None = None,
        home_name: str | None = None,
        away_name: str | None = None,
    ) -> dict[str, Any]:
        """Dual-Mode Betting Splits & Market Flow Analyzer."""
        if api_key:
            url = self.build_betting_splits_url(
                game_id=game_id,
                product=product,
                access_level=access_level,
                language_code=language_code,
                competition_id=competition_id,
            )
            req = urllib.request.Request(
                url,
                headers={"x-api-key": api_key, "Accept": "application/json"},
            )
            ctx = ssl.create_default_context()
            if hasattr(ssl, "VERIFY_X509_STRICT"):
                ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
            with urllib.request.urlopen(req, timeout=self.timeout_sec, context=ctx) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))
            return {
                "ok": True,
                "mode": "commercial_betting_splits_v3",
                "match_id": game_id,
                "product": product,
                "updated_utc": datetime.now(timezone.utc).isoformat(),
                "markets": [],
                "raw_commercial_payload": raw,
            }

        import re

        numeric_mid = re.sub(r"^sr:(?:sport_event|match):", "", str(game_id), flags=re.I)
        retail_resp = self.get_match_markets(numeric_mid, "prematch", "eu-retail") or {}
        consensus_resp = self.get_match_markets(numeric_mid, "prematch", "global") or {}
        live_resp = self.get_match_markets(numeric_mid, "live", "global") or {}

        retail_markets = retail_resp.get("markets") or []
        consensus_markets = consensus_resp.get("markets") or []
        live_markets = live_resp.get("markets") or []

        def spec_key(mk: dict[str, Any]) -> str:
            return f"{mk.get('_marketId')}:{json.dumps(mk.get('specifiers') or {}, sort_keys=True)}"

        r_map = {spec_key(m): m for m in retail_markets if isinstance(m, dict)}
        c_map = {spec_key(m): m for m in consensus_markets if isinstance(m, dict)}
        l_map = {spec_key(m): m for m in live_markets if isinstance(m, dict)}

        all_keys = list(dict.fromkeys(list(c_map.keys()) + list(r_map.keys())))
        split_markets: list[dict[str, Any]] = []

        for k in all_keys:
            c_mk = c_map.get(k)
            r_mk = r_map.get(k)
            l_mk = l_map.get(k)
            base_mk = c_mk or r_mk
            if not base_mk:
                continue

            r_outcomes = (r_mk or {}).get("outcomes") or []
            c_outcomes = (c_mk or {}).get("outcomes") or []
            l_outcomes = (l_mk or {}).get("outcomes") or []

            r_inv_sum = sum(
                1.0 / float(o["odds"])
                for o in r_outcomes
                if o.get("odds") and float(o["odds"]) > 1.0
            )
            c_inv_sum = sum(
                1.0 / float(o["odds"])
                for o in c_outcomes
                if o.get("odds") and float(o["odds"]) > 1.0
            )

            retail_overround = round((r_inv_sum - 1.0) * 100.0, 2) if r_inv_sum > 0 else None
            consensus_overround = round((c_inv_sum - 1.0) * 100.0, 2) if c_inv_sum > 0 else None

            base_outcomes = c_outcomes if c_outcomes else r_outcomes
            selections: list[dict[str, Any]] = []

            for bo in base_outcomes:
                oid = str(bo.get("_id") or "")
                r_out = next(
                    (x for x in r_outcomes if str(x.get("_id")) == oid or x.get("name") == bo.get("name")),
                    None,
                )
                c_out = next(
                    (x for x in c_outcomes if str(x.get("_id")) == oid or x.get("name") == bo.get("name")),
                    None,
                )
                l_out = next(
                    (x for x in l_outcomes if str(x.get("_id")) == oid or x.get("name") == bo.get("name")),
                    None,
                )

                r_odds = float(r_out["odds"]) if (r_out and r_out.get("odds")) else None
                c_odds = float(c_out["odds"]) if (c_out and c_out.get("odds")) else None
                l_odds = float(l_out["odds"]) if (l_out and l_out.get("odds")) else None

                if r_odds and r_inv_sum > 0:
                    retail_prob = ((1.0 / r_odds) / r_inv_sum) * 100.0
                elif c_odds and c_inv_sum > 0:
                    retail_prob = ((1.0 / c_odds) / c_inv_sum) * 100.0
                else:
                    retail_prob = 0.0

                if c_out and isinstance(c_out.get("probability"), (int, float)) and c_out["probability"] > 0:
                    consensus_prob = float(c_out["probability"]) * 100.0
                elif c_odds and c_inv_sum > 0:
                    consensus_prob = ((1.0 / c_odds) / c_inv_sum) * 100.0
                else:
                    consensus_prob = retail_prob

                bets_pct = round(retail_prob, 2)
                stake_pct = round(consensus_prob, 2)
                diff_pct = round(stake_pct - bets_pct, 2)

                raw_name = str(bo.get("name") or "")
                home_away = (
                    "home"
                    if "competitor1" in raw_name
                    else "away"
                    if "competitor2" in raw_name
                    else "draw"
                    if raw_name.lower() == "draw"
                    else None
                )

                selections.append(
                    {
                        "selection_id": oid,
                        "name": format_market_placeholders(
                            raw_name,
                            home_name=home_name,
                            away_name=away_name,
                            specifiers=base_mk.get("specifiers"),
                        ),
                        "home_away": home_away,
                        "retail_odds": r_odds,
                        "consensus_odds": c_odds,
                        "live_odds": l_odds,
                        "bets_percentage": bets_pct,
                        "stake_percentage": stake_pct,
                        "sharp_divergence_pct": diff_pct,
                        "direction": "steam_toward"
                        if diff_pct >= 0.4
                        else ("fade_against" if diff_pct <= -0.4 else "neutral"),
                    }
                )

            display_market = format_market_placeholders(
                str(base_mk.get("name") or f"Market #{base_mk.get('_marketId')}"),
                home_name=home_name,
                away_name=away_name,
                specifiers=base_mk.get("specifiers"),
            )

            split_markets.append(
                {
                    "market_id": base_mk.get("_marketId"),
                    "market_name": str(base_mk.get("name") or f"Market #{base_mk.get('_marketId')}"),
                    "display_market": display_market,
                    "specifiers": base_mk.get("specifiers"),
                    "retail_overround_pct": retail_overround,
                    "consensus_overround_pct": consensus_overround,
                    "selections": selections,
                }
            )

        return {
            "ok": len(split_markets) > 0,
            "mode": "tokenless_retail_vs_consensus",
            "match_id": numeric_mid,
            "product": product,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "markets": split_markets,
        }

    # CamelCase aliases for 1:1 parity with TypeScript BetScoutClient
    clearCache = clear_cache
    buildRelativePath = build_relative_path
    fetchDocument = fetch_document
    fetchFeed = fetch_feed
    listAllSports = list_all_sports
    getCategoryTree = get_category_tree
    getUniqueTournaments = get_unique_tournaments
    getAllUniqueTournaments = get_all_unique_tournaments
    getTennisCalendar = get_tennis_calendar
    getDailySportMatches = get_daily_sport_matches
    getDailySportMarkets = get_daily_sport_markets
    getMatchMarkets = get_match_markets
    getSeasonMarkets = get_season_markets
    getMatchTimelineDelta = get_match_timeline_delta
    getLiveEventsBySport = get_live_events_by_sport
    getMatchInfo = get_match_info
    getMatchSquads = get_match_squads
    getSeasonInjuries = get_season_injuries
    getMatchForm = get_match_form
    getMatchHead2Head = get_match_head2head
    getHead2HeadVersus = get_head2head_versus
    getMatchSituations = get_match_situations
    getMatchStats = get_match_stats
    getMatchDetails = get_match_details
    getMatchDetailsExtended = get_match_details_extended
    getTeamProfile = get_team_profile
    getTeamLastMatches = get_team_last_matches
    getTeamLastMatchesExtended = get_team_last_matches_extended
    getTeamNextMatches = get_team_next_matches
    getTeamStreaks = get_team_streaks
    getTeamSeasons = get_team_seasons
    getTeamSeasonStats = get_team_season_stats
    getTeamSeasonMatches = get_team_season_matches
    getTeamScoringConcedingSplits = get_team_scoring_conceding_splits
    getTeamPositionHistory = get_team_position_history
    getTeamSquad = get_team_squad
    getTeamSeasonSquad = get_team_season_squad
    getTeamUsualLineup = get_team_usual_lineup
    getTeamTransfers = get_team_transfers
    getTeamTournaments = get_team_tournaments
    getTeamSeasonOfficials = get_team_season_officials
    getPlayerCareerStats = get_player_career_stats
    getPlayerFacts = get_player_facts
    getPlayerSeasonMatches = get_player_season_matches
    getTennisPlayerSurfaceStats = get_tennis_player_surface_stats
    getTennisRanking = get_tennis_ranking
    getSeasonTables = get_season_tables
    getSeasonDynamicTable = get_season_dynamic_table
    getSeasonFormTable = get_season_form_table
    getMatchTableSlice = get_match_table_slice
    getEnrichedLeagueTable = get_enriched_league_table
    getSeasonOverUnder = get_season_over_under
    getSeasonGoalsDistribution = get_season_goals_distribution
    getSeasonUniqueTeamStats = get_season_unique_team_stats
    getTeamVersus = get_team_versus
    getUniqueTournamentInfo = get_unique_tournament_info
    getTournamentSeasonsWinners = get_tournament_seasons_winners
    getSeasonMeta = get_season_meta
    getCupBrackets = get_cup_brackets
    getSeasonReferees = get_season_referees
    getSeasonCompetitors = get_season_competitors
    getSeasonSchedule = get_season_schedule
    getSeasonLastMatches = get_season_last_matches
    getSeasonNextMatches = get_season_next_matches
    getCompetitionSeasons = get_competition_seasons
    getStageSeasons = get_stage_seasons
    getStageSeasonSummary = get_stage_season_summary
    getStageDetails = get_stage_details
    getStageCalendar = get_stage_calendar
    getStageDayEvents = get_stage_day_events
    getCricketEvents = get_cricket_events
    getMatchFullTimeline = get_match_full_timeline
    getRefereeSeasonStats = get_referee_season_stats
    getTeamLogoUrl = get_team_logo_url
    getCountryFlagUrl = get_country_flag_url
    renderTeamJerseySvg = render_team_jersey_svg
    getMatchInsights = get_match_insights
    getMatchCommentary = get_match_commentary
    getMatchCommentaryDelta = get_match_commentary_delta
    getSeasonLeagueSummary = get_season_league_summary
    getTeamPlayerSeasonFacts = get_team_player_season_facts
    getSeasonVenues = get_season_venues
    getVenueSeasonStats = get_venue_season_stats
    getSeasonTopScorers = get_season_top_scorers
    getSeasonTopAssists = get_season_top_assists
    getSeasonTopCards = get_season_top_cards
    getTeamMarkets = get_team_markets
    getOddsFormatTable = get_odds_format_table
    getDailyMatchIndex = get_daily_match_index
    fetchTeamGoalIntervals = fetch_team_goal_intervals
    fetchLiveMatchSituationsPressure = fetch_live_match_situations_pressure
    evaluateInjuryGate = evaluate_injury_gate
    getTeamMissingPlayers = get_team_missing_players
    getTeamIntelligenceBundle = get_team_intelligence_bundle
    getTennisPlayerIntelligenceBundle = get_tennis_player_intelligence_bundle
    getMatchCenterDossier = get_match_center_dossier
    buildInsightsPushUrl = build_insights_push_url
    streamInsights = stream_insights
    buildBettingSplitsUrl = build_betting_splits_url
    buildBettingSplitsPushUrl = build_betting_splits_push_url
    getBettingSplits = get_betting_splits
