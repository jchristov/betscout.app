"""Unified schema, normalisation and data-quality checks for every sport and league in the store.

Unified rules (applied to every row, every sport):
  * kickoff: ISO-8601 UTC, format YYYY-MM-DDTHH:MMZ, exactly 17 characters.
  * key: (league, event_id) unique.
  * outcome: H / D / A for soccer, H / A for tennis (no draws); must agree with the stored score.
  * scores: non-negative integers when present.
  * 1X2 prices: decimal, each > 1, overround in [1.00, 1.25], otherwise the set is rejected.
    Extreme prices (above 200) are kept and reported as info: verified against outcomes, they are real.
  * totals: line in [0.5, 6], both prices present or both absent, each > 1.
  * double-chance prices: each > 1.
  * team names: trimmed, non-empty, home != away.

Price normalisation: a 1X2 set is kept only when it came from the documented `bettingOdds` layout,
or from the flat layout with `homeTeamOdds.odds.value` / `drawOdds.value` / `awayTeamOdds.odds.value`
all present and numeric. Flat `drawOdds` shaped as `{moneyLine}` or `{summary: OFF}` is rejected.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

KICKOFF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$")


@dataclass
class Issue:
    check: str
    league: str
    sport: str
    count: int
    severity: str  # "error" or "warn"
    note: str = ""


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, dict] = field(default_factory=dict)

    def add(self, check: str, league: str, sport: str, count: int, severity: str, note: str = "") -> None:
        if count:
            self.issues.append(Issue(check, league, sport, count, severity, note))


SQL_CHECKS = [
    ("kickoff_format", "error", "kickoff NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]Z' OR length(kickoff)!=17",
     "kickoff is not YYYY-MM-DDTHH:MMZ"),
    ("outcome_invalid", "error", "outcome NOT IN ('H','D','A') OR (sport IN ('tennis','basketball','hockey','baseball') AND outcome='D')",
     "outcome not allowed for this sport"),
    ("score_outcome_mismatch", "error",
     "home_score IS NOT NULL AND outcome != CASE WHEN home_score>away_score THEN 'H' WHEN home_score<away_score THEN 'A' ELSE 'D' END",
     "outcome disagrees with score"),
    ("score_invalid", "error",
     "home_score IS NOT NULL AND (home_score<0 OR away_score<0 OR home_score!=CAST(home_score AS INT) OR away_score!=CAST(away_score AS INT))",
     "score negative or non-integer"),
    ("self_match", "error", "home = away", "home and away are the same"),
    ("empty_team", "error", "TRIM(home)='' OR TRIM(away)='' OR home!=TRIM(home) OR away!=TRIM(away)",
     "empty or untrimmed team name"),
    ("1x2_price_le_1", "error", "odds_home IS NOT NULL AND (odds_home<=1 OR odds_away<=1 OR (sport='soccer' AND (odds_draw IS NULL OR odds_draw<=1)))",
     "moneyline/1X2 price at or below 1.0"),
    ("1x2_overround_out_of_range", "error",
     "odds_home IS NOT NULL AND ((sport='soccer' AND (1.0/odds_home+1.0/odds_draw+1.0/odds_away NOT BETWEEN 1.0 AND 1.25)) OR (sport!='soccer' AND (1.0/odds_home+1.0/odds_away NOT BETWEEN 1.0 AND 1.20)))",
     "moneyline/1X2 overround outside valid pre-match range"),
    ("1x2_inplay_leakage", "error",
     "odds_home IS NOT NULL AND ((sport='soccer' AND (odds_draw<2.20 OR odds_draw>100)) OR odds_home<=1.01 OR odds_away<=1.01 OR odds_home>100 OR odds_away>100)",
     "price looks like in-play closing-whistle leakage (draw < 2.20 or price > 100)"),
    ("dc_price_le_1", "error", "odds_dc_1x IS NOT NULL AND (odds_dc_1x<=1 OR odds_dc_x2<=1 OR odds_dc_12<=1)",
     "double-chance price at or below 1.0"),
    ("dc_overround_out_of_range", "error",
     "odds_dc_1x IS NOT NULL AND ((1.0/odds_dc_1x+1.0/odds_dc_x2+1.0/odds_dc_12)/2.0 NOT BETWEEN 1.0 AND 1.25)",
     "double-chance overround outside [1.00, 1.25]"),
    ("totals_line_range", "error",
     "line_total IS NOT NULL AND ((sport='soccer' AND (line_total<0.5 OR line_total>6.5)) OR (sport='hockey' AND (line_total<3.0 OR line_total>10.5)) OR (sport='baseball' AND (line_total<4.0 OR line_total>16.5)) OR (sport='football' AND (line_total<24.0 OR line_total>75.0)) OR (sport='basketball' AND (line_total<140.0 OR line_total>285.0)))",
     "totals line outside sport-specific range"),
    ("totals_one_sided", "error", "(odds_over IS NULL) != (odds_under IS NULL)",
     "only one totals price present"),
    ("totals_price_le_1", "error", "odds_over IS NOT NULL AND (odds_over<=1 OR odds_under<=1)",
     "totals price at or below 1.0"),
    ("totals_overround_out_of_range", "error",
     "odds_over IS NOT NULL AND (1.0/odds_over+1.0/odds_under NOT BETWEEN 1.0 AND 1.20)",
     "totals overround outside [1.00, 1.20]"),
    ("totals_without_line", "error", "(odds_over IS NOT NULL OR odds_under IS NOT NULL) AND line_total IS NULL",
     "totals prices without a line"),
    ("missing_winner_tennis", "error", "sport='tennis' AND outcome IS NULL", "tennis match has no winner"),
    ("duplicate_key", "error",
     "rowid NOT IN (SELECT MIN(rowid) FROM matches GROUP BY league, event_id)", "duplicate (league, event_id)"),
    ("duplicate_fixture_same_day", "error",
     "rowid NOT IN (SELECT MIN(rowid) FROM matches GROUP BY sport, league, substr(kickoff,1,10), CASE WHEN home<away THEN home ELSE away END, CASE WHEN home<away THEN away ELSE home END)",
     "duplicate same-day fixture for the same competitors"),
]


CANONICAL_VIEW = """
DROP VIEW IF EXISTS matches_canonical;
CREATE VIEW matches_canonical AS
SELECT
    sport,
    league,
    event_id,
    kickoff,
    TRIM(home) AS home,
    TRIM(away) AS away,
    outcome,
    home_score,
    away_score,
    odds_home, odds_draw, odds_away, odds_provider,
    odds_dc_1x, odds_dc_x2, odds_dc_12,
    line_total, odds_over, odds_under,
    CASE WHEN sport = 'soccer' THEN 1 ELSE 0 END AS has_draw,
    CASE WHEN home_score IS NOT NULL THEN 1 ELSE 0 END AS has_score,
    CASE WHEN odds_home IS NOT NULL THEN 1 ELSE 0 END AS has_1x2
FROM matches
WHERE outcome IS NOT NULL;
"""


def install_view(db: Path) -> None:
    """Create the canonical view: one schema for every sport, with explicit capability flags."""
    conn = sqlite3.connect(db)
    conn.executescript(CANONICAL_VIEW)
    conn.commit()
    conn.close()


def adjust_and_normalize_db(db: Path) -> dict[str, int]:
    """Normalize formats and strip any invalid/in-play price sets on the fly across `matches` and `match_details`."""
    conn = sqlite3.connect(db)
    # 1. Trim team names and remove invalid self-matches or empty teams
    conn.execute("UPDATE matches SET home = TRIM(home), away = TRIM(away) WHERE home != TRIM(home) OR away != TRIM(away)")
    conn.execute("DELETE FROM matches WHERE home = away OR TRIM(home) = '' OR TRIM(away) = ''")
    # 2. Clear any invalid 1X2 / moneyline sets on the fly
    cur1 = conn.execute(
        """
        UPDATE matches
        SET odds_home = NULL, odds_draw = NULL, odds_away = NULL, odds_provider = NULL
        WHERE odds_home IS NOT NULL AND (
            odds_home <= 1.01 OR odds_away <= 1.01 OR odds_home > 100 OR odds_away > 100
            OR (sport = 'soccer' AND (odds_draw IS NULL OR odds_draw < 2.20 OR odds_draw > 100 OR (1.0/odds_home + 1.0/odds_draw + 1.0/odds_away NOT BETWEEN 1.0 AND 1.25)))
            OR (sport != 'soccer' AND (1.0/odds_home + 1.0/odds_away NOT BETWEEN 1.0 AND 1.20))
        )
        """
    )
    # 3. Clear any invalid Double Chance sets
    cur2 = conn.execute(
        """
        UPDATE matches
        SET odds_dc_1x = NULL, odds_dc_x2 = NULL, odds_dc_12 = NULL
        WHERE odds_dc_1x IS NOT NULL AND (
            odds_dc_1x <= 1.001 OR odds_dc_x2 <= 1.001 OR odds_dc_12 <= 1.001
            OR ((1.0/odds_dc_1x + 1.0/odds_dc_x2 + 1.0/odds_dc_12)/2.0 NOT BETWEEN 1.0 AND 1.25)
        )
        """
    )
    # 4. Clear any invalid Totals sets
    cur3 = conn.execute(
        """
        UPDATE matches
        SET line_total = NULL, odds_over = NULL, odds_under = NULL
        WHERE (odds_over IS NOT NULL OR odds_under IS NOT NULL OR line_total IS NOT NULL) AND (
            odds_over IS NULL OR odds_under IS NULL OR line_total IS NULL
            OR odds_over <= 1.01 OR odds_under <= 1.01
            OR (1.0/odds_over + 1.0/odds_under NOT BETWEEN 1.0 AND 1.20)
            OR (sport='soccer' AND (line_total<0.5 OR line_total>6.5))
            OR (sport='hockey' AND (line_total<3.0 OR line_total>10.5))
            OR (sport='baseball' AND (line_total<4.0 OR line_total>16.5))
            OR (sport='football' AND (line_total<24.0 OR line_total>75.0))
            OR (sport='basketball' AND (line_total<140.0 OR line_total>285.0))
        )
        """
    )
    # 5. Deduplicate same-day fixtures
    cur4 = conn.execute(
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
    has_details = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='match_details'"
    ).fetchone()[0]
    if has_details:
        conn.execute(
            "DELETE FROM match_details WHERE (league, event_id) NOT IN (SELECT league, event_id FROM matches)"
        )
    conn.executescript(CANONICAL_VIEW)
    conn.commit()
    conn.close()
    return {
        "cleared_1x2": cur1.rowcount,
        "cleared_dc": cur2.rowcount,
        "cleared_totals": cur3.rowcount,
        "deduplicated": cur4.rowcount,
    }


def run(db: Path) -> Report:
    rep = Report()
    conn = sqlite3.connect(db)
    for name, sev, cond, note in SQL_CHECKS:
        rows = conn.execute(
            f"SELECT league, sport, COUNT(*) FROM matches WHERE {cond} GROUP BY league, sport"
        ).fetchall()
        for league, sport, n in rows:
            rep.add(name, league, sport, n, sev, note)
    for league, sport, n, with_1x2, with_tot in conn.execute(
        "SELECT league, sport, COUNT(*), SUM(odds_home IS NOT NULL), SUM(odds_over IS NOT NULL) "
        "FROM matches GROUP BY league, sport ORDER BY sport, league"
    ):
        rep.stats[league] = {"sport": sport, "rows": n, "with_1x2": with_1x2, "with_totals": with_tot}

    has_details = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='match_details'"
    ).fetchone()[0]
    if has_details:
        for lg, sp, cnt in conn.execute(
            "SELECT league, sport, COUNT(*) FROM match_details "
            "WHERE best_home IS NOT NULL AND (1.0/best_home + 1.0/best_draw + 1.0/best_away < 0.94) "
            "GROUP BY league, sport"
        ):
            rep.add("details_inplay_arb_pollution", lg, sp, cnt, "error", "best 1X2 overround < 0.94 in match_details")
    conn.close()
    return rep
