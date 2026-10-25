"""Backfill finished ESPN events (result, pre-match 1X2 price, H2H) into a Parquet-free SQLite store."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from .espn import ALL_LEAGUES, LEAGUE_LABELS, EspnClient, League, resolve_league

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    event_id TEXT NOT NULL,
    league TEXT NOT NULL,
    sport TEXT NOT NULL,
    kickoff TEXT NOT NULL,
    home TEXT NOT NULL,
    away TEXT NOT NULL,
    home_score REAL,
    away_score REAL,
    outcome TEXT,
    odds_home REAL,
    odds_draw REAL,
    odds_away REAL,
    odds_provider TEXT,
    odds_dc_1x REAL,
    odds_dc_x2 REAL,
    odds_dc_12 REAL,
    line_total REAL,
    odds_over REAL,
    odds_under REAL,
    PRIMARY KEY (league, event_id)
);
CREATE INDEX IF NOT EXISTS idx_matches_kickoff ON matches(sport, kickoff);
"""


@dataclass(frozen=True)
class Match:
    event_id: str
    league: str
    sport: str
    kickoff: str
    home: str
    away: str
    home_score: float | None
    away_score: float | None
    outcome: str | None  # "H" | "D" | "A"
    odds_home: float | None  # decimal odds
    odds_draw: float | None
    odds_away: float | None
    odds_provider: str | None
    odds_dc_1x: float | None = None
    odds_dc_x2: float | None = None
    odds_dc_12: float | None = None
    line_total: float | None = None
    odds_over: float | None = None
    odds_under: float | None = None


def fractional_to_decimal(value: str | None) -> float | None:
    """ESPN prices are fractional ("8/5"); convert to decimal (2.6)."""
    if not value or "/" not in value:
        return None
    try:
        frac = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    return 1 + float(frac)


def _outcome(hs: float | None, as_: float | None) -> str | None:
    if hs is None or as_ is None:
        return None
    if hs > as_:
        return "H"
    if hs < as_:
        return "A"
    return "D"


def _competitor(comp: dict[str, Any], side: str) -> dict[str, Any] | None:
    for c in comp.get("competitors", []):
        if c.get("homeAway") == side:
            return c
    return None


def _team_name(c: dict[str, Any]) -> str:
    team = c.get("team") or c.get("athlete") or {}
    return team.get("displayName") or team.get("fullName") or ""


def _score(c: dict[str, Any]) -> float | None:
    s = c.get("score")
    if isinstance(s, dict):
        s = s.get("value")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def american_to_decimal(value: Any) -> float | None:
    """Convert American moneyline odds (e.g. -230, +400, '-150') to decimal odds."""
    if value is None or isinstance(value, bool):
        return None
    try:
        x = float(str(value).replace("+", "").strip())
    except (TypeError, ValueError):
        return None
    # Valid American odds are <= -100 or >= +100
    if -100.0 < x < 100.0:
        return None
    return (1.0 + x / 100.0) if x > 0 else (1.0 + 100.0 / (-x))


def _valid_1x2(h: float | None, d: float | None, a: float | None) -> bool:
    """Validate that 1X2 decimal odds are genuine pre-match prices (not 90th-minute in-play)."""
    if not (h and d and a):
        return False
    if min(h, d, a) <= 1.01 or d < 2.20 or max(h, d, a) > 100.0:
        return False
    overround = (1.0 / h) + (1.0 / d) + (1.0 / a)
    return 1.00 <= overround <= 1.20


def _valid_dc(dc_1x: float | None, dc_x2: float | None, dc_12: float | None,
              h: float | None = None, d: float | None = None, a: float | None = None) -> bool:
    """Validate double-chance decimal odds (sum of implied probs around 2.0)."""
    if not (dc_1x and dc_x2 and dc_12):
        return False
    if min(dc_1x, dc_x2, dc_12) <= 1.001:
        return False
    overround = ((1.0 / dc_1x) + (1.0 / dc_x2) + (1.0 / dc_12)) / 2.0
    if not (1.00 <= overround <= 1.25):
        return False
    if h and d and a:
        if dc_1x >= min(h, d) or dc_x2 >= min(d, a) or dc_12 >= min(h, a):
            return False
    return True


SPORT_TOTAL_BOUNDS: dict[str, tuple[float, float]] = {
    "soccer": (0.5, 6.5),
    "hockey": (3.0, 10.5),
    "baseball": (4.0, 16.5),
    "football": (24.0, 75.0),
    "basketball": (110.0, 285.0),
    "volleyball": (2.5, 5.5),
}


def normalize_kickoff(raw: str) -> str:
    """Normalize any ISO-8601 UTC timestamp to strict 17-char format YYYY-MM-DDTHH:MMZ."""
    s = (raw or "").strip()
    if len(s) == 17 and s[10] == "T" and s.endswith("Z"):
        return s
    dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%MZ")


def _valid_2way(h: float | None, a: float | None) -> bool:
    """Validate 2-way pre-match moneyline decimal odds (NBA, NHL, NFL, MLB)."""
    if not (h and a):
        return False
    if min(h, a) <= 1.01 or max(h, a) > 50.0:
        return False
    overround = (1.0 / h) + (1.0 / a)
    return 1.00 <= overround <= 1.18


def _valid_totals(line: float | None, over: float | None, under: float | None, sport: str = "soccer") -> bool:
    lo, hi = SPORT_TOTAL_BOUNDS.get(sport, (0.5, 300.0))
    if line is None or not (lo <= line <= hi) or not (over and under):
        return False
    if min(over, under) <= 1.01 or max(over, under) > 10.0:
        return False
    overround = (1.0 / over) + (1.0 / under)
    return 1.00 <= overround <= 1.20


def _price(tos: dict[str, Any], key: str) -> float | None:
    return fractional_to_decimal((tos.get(key) or {}).get("value"))


def _american_book_odds(summary: dict[str, Any]) -> dict[str, Any] | None:
    """Fallback pre-match 1X2 and O/U from American-format providers (DraftKings, ESPN BET, Unibet, etc.).
    Never reads Bet 365's top-level `homeTeamOdds.odds.value`, which is in-play closing-whistle odds."""
    for o in summary.get("odds") or []:
        prov = (o.get("provider") or {}).get("name") or ""
        if "Live" in prov:
            continue
        hto = o.get("homeTeamOdds") or {}
        ato = o.get("awayTeamOdds") or {}
        do = o.get("drawOdds") or {}
        ml = o.get("moneyline") or {}
        h = american_to_decimal(hto.get("moneyLine")) or american_to_decimal(((ml.get("home") or {}).get("close") or {}).get("odds"))
        d = american_to_decimal(do.get("moneyLine")) or american_to_decimal(((ml.get("draw") or {}).get("close") or {}).get("odds"))
        a = american_to_decimal(ato.get("moneyLine")) or american_to_decimal(((ml.get("away") or {}).get("close") or {}).get("odds"))
        if not _valid_1x2(h, d, a):
            continue
        line = _line(o.get("overUnder"))
        over = american_to_decimal(o.get("overOdds"))
        under = american_to_decimal(o.get("underOdds"))
        if not _valid_totals(line, over, under):
            tot = o.get("total") or {}
            over_c = ((tot.get("over") or {}).get("close") or {})
            under_c = ((tot.get("under") or {}).get("close") or {})
            line_str = str(over_c.get("line") or "").lstrip("ouOU")
            line = _line(line_str) if line_str else line
            over = american_to_decimal(over_c.get("odds"))
            under = american_to_decimal(under_c.get("odds"))
            if not _valid_totals(line, over, under):
                line, over, under = None, None, None
        return {
            "odds_home": h, "odds_draw": d, "odds_away": a,
            "odds_provider": prov or None,
            "odds_dc_1x": None, "odds_dc_x2": None, "odds_dc_12": None,
            "line_total": line, "odds_over": over, "odds_under": under,
        }
    return None


def _soccer_odds(summary: dict[str, Any]) -> dict[str, Any]:
    """Pre-match prices from the first bookmaker with a valid pre-match 1X2 line."""
    empty: dict[str, Any] = {k: None for k in ("odds_home", "odds_draw", "odds_away", "odds_provider",
                                                "odds_dc_1x", "odds_dc_x2", "odds_dc_12",
                                                "line_total", "odds_over", "odds_under")}
    for o in summary.get("odds") or []:
        tos = (o.get("bettingOdds") or {}).get("teamOdds") or {}
        h, d, a = (_price(tos, k) for k in ("preMatchFullTimeResultHome", "preMatchFullTimeResultDraw", "preMatchFullTimeResultAway"))
        if not _valid_1x2(h, d, a):
            continue
        dc_1x = _price(tos, "preMatchDoubleChanceHomeOrDraw")
        dc_x2 = _price(tos, "preMatchDoubleChanceDrawOrAway")
        dc_12 = _price(tos, "preMatchDoubleChanceHomeOrAway")
        if not _valid_dc(dc_1x, dc_x2, dc_12, h, d, a):
            dc_1x, dc_x2, dc_12 = None, None, None
        line = _line(tos.get("preMatchOverUnderHandicap"))
        over = _price(tos, "preMatchGoalLineOver")
        under = _price(tos, "preMatchGoalLineUnder")
        if not _valid_totals(line, over, under):
            line, over, under = None, None, None
        return {
            "odds_home": h, "odds_draw": d, "odds_away": a,
            "odds_provider": (o.get("provider") or {}).get("name"),
            "odds_dc_1x": dc_1x,
            "odds_dc_x2": dc_x2,
            "odds_dc_12": dc_12,
            "line_total": line,
            "odds_over": over,
            "odds_under": under,
        }
    fallback = _american_book_odds(summary)
    if fallback:
        return fallback
    return empty


def _line(v: Any) -> float | None:
    """Total-goals line as posted by ESPN, e.g. "2.5" (bare number, not fractional)."""
    try:
        return float(v.get("value")) if isinstance(v, dict) else float(v)
    except (TypeError, ValueError):
        return None


def _two_way_team_odds(summary: dict[str, Any], sport: str) -> dict[str, Any]:
    """Extract pre-match 2-way moneyline and totals from `pickcenter` or `odds` for NBA, NHL, NFL, MLB."""
    empty: dict[str, Any] = {
        k: None
        for k in (
            "odds_home", "odds_draw", "odds_away", "odds_provider",
            "odds_dc_1x", "odds_dc_x2", "odds_dc_12",
            "line_total", "odds_over", "odds_under",
        )
    }
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
        h = american_to_decimal(hto.get("moneyLine")) or american_to_decimal(((ml.get("home") or {}).get("close") or {}).get("odds"))
        a = american_to_decimal(ato.get("moneyLine")) or american_to_decimal(((ml.get("away") or {}).get("close") or {}).get("odds"))
        if not _valid_2way(h, a):
            continue
        line = _line(o.get("overUnder"))
        over = american_to_decimal(o.get("overOdds"))
        under = american_to_decimal(o.get("underOdds"))
        if not _valid_totals(line, over, under, sport=sport):
            tot = o.get("total") or {}
            over_c = (tot.get("over") or {}).get("close") or {}
            under_c = (tot.get("under") or {}).get("close") or {}
            line_str = str(over_c.get("line") or "").lstrip("ouOU")
            line = _line(line_str) if line_str else line
            over = american_to_decimal(over_c.get("odds"))
            under = american_to_decimal(under_c.get("odds"))
            if not _valid_totals(line, over, under, sport=sport):
                line, over, under = None, None, None
        return {
            **empty,
            "odds_home": h,
            "odds_away": a,
            "odds_provider": prov or None,
            "line_total": line,
            "odds_over": over,
            "odds_under": under,
        }
    return empty


def _parse_soccer_event(league: League, ev: dict[str, Any], summary: dict[str, Any]) -> Match | None:
    comp = (ev.get("competitions") or [{}])[0]
    home, away = _competitor(comp, "home"), _competitor(comp, "away")
    if not home or not away:
        return None
    h_name, a_name = _team_name(home).strip(), _team_name(away).strip()
    if not h_name or not a_name or h_name == a_name:
        return None
    completed = (ev.get("status") or {}).get("type", {}).get("completed")
    hs, as_ = (_score(home), _score(away)) if completed else (None, None)
    prices = _soccer_odds(summary) if league.sport == "soccer" else _two_way_team_odds(summary, league.sport)
    return Match(
        event_id=str(ev["id"]),
        league=league.key,
        sport=league.sport,
        kickoff=normalize_kickoff(ev["date"]),
        home=h_name,
        away=a_name,
        home_score=hs,
        away_score=as_,
        outcome=_outcome(hs, as_) if completed else None,
        **prices,
    )


def _tennis_sets(competitor: dict[str, Any]) -> float | None:
    """Count sets won from tennis linescores (only when completed set scores exist)."""
    ls = competitor.get("linescores") or []
    if not ls:
        return None
    won = sum(1 for s in ls if s.get("winner") is True)
    return float(won)


def _parse_tennis_event(league: League, tournament: dict[str, Any], grouping: dict[str, Any], comp: dict[str, Any]) -> Match | None:
    wanted = {"atp": "mens-singles", "wta": "womens-singles"}.get(league.key)
    if (grouping.get("grouping") or {}).get("slug") != wanted:
        return None
    p1, p2 = _competitor(comp, "home"), _competitor(comp, "away")
    if not p1 or not p2:
        return None
    completed = (comp.get("status") or {}).get("type", {}).get("completed")
    if not completed or not (p1.get("winner") or p2.get("winner")):
        return None
    home_name, away_name = _team_name(p1).strip(), _team_name(p2).strip()
    if not home_name or not away_name or home_name == away_name:
        return None
    outcome = "H" if p1.get("winner") else "A"
    s1, s2 = _tennis_sets(p1), _tennis_sets(p2)
    # Only store set scores if they agree with the winner flag (retirements can have fewer sets won by winner)
    if s1 is not None and s2 is not None:
        if (outcome == "H" and s1 <= s2) or (outcome == "A" and s2 <= s1):
            s1, s2 = None, None
    return Match(
        event_id=str(comp["id"]),
        league=league.key,
        sport=league.sport,
        kickoff=normalize_kickoff(comp["date"]),
        home=home_name,
        away=away_name,
        home_score=s1,
        away_score=s2,
        outcome=outcome,
        odds_home=None,
        odds_draw=None,
        odds_away=None,
        odds_provider=None,
    )


def parse_day(
    league: League,
    board: dict[str, Any],
    client: EspnClient,
    pool: ThreadPoolExecutor | None = None,
    skip_event_ids: set[str] | None = None,
) -> Iterable[Match]:
    skip = skip_event_ids or set()
    if league.sport != "tennis":
        finished = [
            ev
            for ev in board.get("events", [])
            if (ev.get("status") or {}).get("type", {}).get("completed") and str(ev.get("id")) not in skip
        ]
        fetch = lambda ev: client.summary(league, str(ev["id"]))  # noqa: E731
        summaries = list(pool.map(fetch, finished)) if pool else [fetch(ev) for ev in finished]
        for ev, summary in zip(finished, summaries):
            m = _parse_soccer_event(league, ev, summary)
            if m:
                yield m
    else:
        for tournament in board.get("events", []):
            for grouping in tournament.get("groupings", []):
                for comp in grouping.get("competitions", []):
                    if str(comp.get("id")) in skip:
                        continue
                    m = _parse_tennis_event(league, tournament, grouping, comp)
                    if m:
                        yield m


PROBE_DATES = ("0115", "0315", "0515", "0615", "0905", "0915", "1015")


def season_start(year: int) -> str:
    """Seasons labelled `year` begin around June of `year` (or Jan of `year` for calendar-year sports)."""
    return f"{year}0101"


def season_end(year: int) -> str:
    """... and end around June of `year + 1`."""
    return f"{year + 1}0601"


def calendar_days(client: EspnClient, league: League, year: int) -> list[str]:
    """Match days (YYYYMMDD) for a league in a season/year, supporting both flat day calendars
    and nested stage/week `entries` calendars (UEFA Champions/Europa/Conference, NFL)."""
    days: set[str] = set()
    today = datetime.now().strftime("%Y%m%d")
    for probe in PROBE_DATES:
        if f"{year}{probe}" > today:
            continue
        try:
            board = client.scoreboard(league, f"{year}{probe}")
        except Exception:
            continue
        for lg in board.get("leagues") or []:
            for cal in lg.get("calendar") or []:
                if isinstance(cal, str):
                    days.add(datetime.fromisoformat(cal.replace("Z", "+00:00")).strftime("%Y%m%d"))
                elif isinstance(cal, dict):
                    entries = cal.get("entries")
                    if isinstance(entries, list):
                        for ent in entries:
                            if isinstance(ent, str):
                                days.add(datetime.fromisoformat(ent.replace("Z", "+00:00")).strftime("%Y%m%d"))
                            elif isinstance(ent, dict) and ent.get("startDate") and ent.get("endDate"):
                                s_dt = datetime.fromisoformat(ent["startDate"].replace("Z", "+00:00")).date()
                                e_dt = datetime.fromisoformat(ent["endDate"].replace("Z", "+00:00")).date()
                                cur = s_dt
                                while cur <= e_dt:
                                    wd = cur.weekday()
                                    if league.key.startswith("uefa."):
                                        if wd in (1, 2, 3) or ("final" in (ent.get("label") or "").lower() and wd == 5):
                                            days.add(cur.strftime("%Y%m%d"))
                                    elif league.sport == "football":
                                        if wd in (0, 3, 5, 6):
                                            days.add(cur.strftime("%Y%m%d"))
                                    else:
                                        days.add(cur.strftime("%Y%m%d"))
                                    cur += timedelta(days=1)
                    elif cal.get("startDate"):
                        days.add(datetime.fromisoformat(cal["startDate"].replace("Z", "+00:00")).strftime("%Y%m%d"))
    return sorted(d for d in days if season_start(year) <= d <= min(season_end(year), today))


def open_store(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def deduplicate_same_day(conn: sqlite3.Connection) -> int:
    """Remove duplicate same-day fixtures between the same unordered pair of competitors."""
    cur = conn.execute(
        """
        DELETE FROM matches
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM matches
            GROUP BY sport, league, substr(kickoff, 1, 10),
                     CASE WHEN home < away THEN home ELSE away END,
                     CASE WHEN home < away THEN away ELSE home END
        )
        """
    )
    conn.commit()
    return cur.rowcount


def upsert(conn: sqlite3.Connection, matches: Iterable[Match]) -> int:
    n = 0
    for m in matches:
        conn.execute(
            "INSERT OR REPLACE INTO matches (event_id, league, sport, kickoff, home, away, home_score, away_score, "
            "outcome, odds_home, odds_draw, odds_away, odds_provider, odds_dc_1x, odds_dc_x2, odds_dc_12, "
            "line_total, odds_over, odds_under) VALUES (" + ",".join("?" * 19) + ")",
            (m.event_id, m.league, m.sport, m.kickoff, m.home.strip(), m.away.strip(), m.home_score, m.away_score,
             m.outcome, m.odds_home, m.odds_draw, m.odds_away, m.odds_provider, m.odds_dc_1x,
             m.odds_dc_x2, m.odds_dc_12, m.line_total, m.odds_over, m.odds_under),
        )
        n += 1
    deduplicate_same_day(conn)
    conn.commit()
    return n


def backfill(db: Path, cache: Path, years: list[int], leagues: list[League] | None = None,
             workers: int = 8) -> dict[str, int]:
    """Fetch finished events for each league and year, concurrently, into SQLite (idempotent)."""
    client = EspnClient(cache)
    conn = open_store(db)
    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for league in leagues or ALL_LEAGUES:
            days = sorted({d for y in years for d in calendar_days(client, league, y)})
            boards = list(pool.map(lambda d: client.scoreboard(league, d), days))
            matches = []
            for board in boards:
                matches.extend(parse_day(league, board, client, pool))
            upsert(conn, matches)
            counts[league.key] = conn.execute(
                "SELECT COUNT(*) FROM matches WHERE league = ?", (league.key,)
            ).fetchone()[0]
    conn.close()
    return counts
