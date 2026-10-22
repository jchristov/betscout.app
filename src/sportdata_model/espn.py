"""Minimal, cached client for ESPN's public site API (undocumented; read-only)."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE = "https://site.api.espn.com/apis/site/v2/sports"


@dataclass(frozen=True)
class League:
    key: str
    sport: str
    league: str


SOCCER_LEAGUES = [
    League("eng.1", "soccer", "eng.1"),
    League("esp.1", "soccer", "esp.1"),
    League("ger.1", "soccer", "ger.1"),
    League("ita.1", "soccer", "ita.1"),
    League("fra.1", "soccer", "fra.1"),
    League("aut.1", "soccer", "aut.1"),
    League("ned.1", "soccer", "ned.1"),
    League("por.1", "soccer", "por.1"),
    League("eng.2", "soccer", "eng.2"),
    League("uefa.champions", "soccer", "uefa.champions"),
    League("uefa.europa", "soccer", "uefa.europa"),
    League("uefa.europa.conf", "soccer", "uefa.europa.conf"),
    League("uefa.super_cup", "soccer", "uefa.super_cup"),
    League("uefa.wchampions", "soccer", "uefa.wchampions"),
    League("uefa.euro", "soccer", "uefa.euro"),
    League("uefa.nations", "soccer", "uefa.nations"),
    League("fifa.world", "soccer", "fifa.world"),
]
TENNIS_LEAGUES = [League("atp", "tennis", "atp"), League("wta", "tennis", "wta")]
OTHER_LEAGUES = [
    League("nba", "basketball", "nba"),
    League("nhl", "hockey", "nhl"),
    League("nfl", "football", "nfl"),
    League("mlb", "baseball", "mlb"),
]
ALL_LEAGUES = SOCCER_LEAGUES + TENNIS_LEAGUES + OTHER_LEAGUES

LEAGUE_LABELS: dict[str, str] = {
    "eng.1": "Premier League",
    "esp.1": "La Liga",
    "ger.1": "Bundesliga",
    "ita.1": "Serie A",
    "fra.1": "Ligue 1",
    "aut.1": "Austrian Bundesliga",
    "ned.1": "Eredivisie",
    "por.1": "Primeira Liga",
    "eng.2": "English Championship",
    "uefa.champions": "UEFA Champions League",
    "uefa.europa": "UEFA Europa League",
    "uefa.europa.conf": "UEFA Conference League",
    "uefa.super_cup": "UEFA Super Cup",
    "uefa.wchampions": "UEFA Women's Champions League",
    "uefa.euro": "UEFA Euro",
    "uefa.nations": "UEFA Nations League",
    "fifa.world": "FIFA World Cup",
    "atp": "ATP Tour",
    "wta": "WTA Tour",
    "nba": "NBA",
    "nhl": "NHL",
    "nfl": "NFL",
    "mlb": "MLB",
}


def resolve_league(spec: str) -> League:
    """Resolve a league key ('uefa.champions', 'nba') or 'sport/league' ('soccer/ned.1') into a League object."""
    clean = spec.strip().lower()
    by_key = {lg.key: lg for lg in ALL_LEAGUES}
    if clean in by_key:
        return by_key[clean]
    if "/" in clean:
        sp, lg_slug = clean.split("/", 1)
        if lg_slug in by_key:
            return by_key[lg_slug]
        return League(lg_slug, sp, lg_slug)
    # Default to soccer if dot-separated slug (e.g. 'bel.1', 'tur.1', 'sco.1', 'usa.1')
    if "." in clean:
        return League(clean, "soccer", clean)
    raise ValueError(f"Unknown league '{spec}'. Use 'sport/league' (e.g. 'basketball/wnba') or a known key: {sorted(by_key)}")


class EspnClient:
    """Fetches JSON via curl (system Python has a broken CA bundle) and caches to disk."""

    def __init__(self, cache_dir: Path, timeout: int = 30) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def _get(self, url: str, cache_name: str) -> dict[str, Any]:
        path = self.cache_dir / f"{cache_name}.json"
        if path.exists():
            return json.loads(path.read_text())
        data = self._fetch(url)
        path.write_text(json.dumps(data))
        return data

    def _fetch(self, url: str, attempts: int = 4) -> dict[str, Any]:
        """curl with retry and exponential backoff; transient ESPN timeouts are common."""
        last = None
        for attempt in range(attempts):
            proc = subprocess.run(
                ["curl", "-s", "--compressed", "-f", "-m", str(self.timeout), url],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return json.loads(proc.stdout)
            last = proc.returncode
            time.sleep(2**attempt)
        raise RuntimeError(f"ESPN request failed after {attempts} attempts ({last}): {url}")

    def scoreboard(self, league: League, ymd: str) -> dict[str, Any]:
        url = f"{BASE}/{league.sport}/{league.league}/scoreboard?dates={ymd}&limit=1000"
        path = self.cache_dir / f"sb_{league.key}_{ymd}.json"
        # Days within the last 2 UTC days can have matches transitioning from 'pre'/'in' to 'post':
        # refresh if cached file is > 15 minutes old.
        cutoff_ymd = time.strftime("%Y%m%d", time.gmtime(time.time() - 2 * 86400))
        if ymd >= cutoff_ymd and path.exists():
            if (time.time() - path.stat().st_mtime) > 900:
                path.unlink(missing_ok=True)
        return self._get(url, f"sb_{league.key}_{ymd}")

    def summary(self, league: League, event_id: str) -> dict[str, Any]:
        url = f"{BASE}/{league.sport}/{league.league}/summary?event={event_id}"
        return self._get(url, f"sum_{league.key}_{event_id}")
