"""Favourites and head-to-head: does past H2H against the opponent add information beyond the price?

Definitions, fixed before testing:
  favourite      team with the shorter 1X2 price (de-vigged market probability > 0.5 for a win is not required)
  strong         team with Elo in its league's top 5 at kickoff (point-in-time Elo, no look-ahead)
  h2h_edge       shrunk H2H win rate of the favourite over this opponent, minus the market's
                 implied win probability for that side. Shrinkage: (wins + 2*0.5) / (games + 2).
Rule: back the favourite when h2h_edge > threshold AND the favourite is strong.
Protocol: discovery = before 2025-07-01, confirmation = 2025/26 onward. Threshold chosen on discovery only.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np

from .elo import Elo

CONFIRM_FROM = "2025-07-01"
THRESH = (0.0, 0.05, 0.10)


def load(db: Path):
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT kickoff, league, home, away, outcome, odds_home, odds_draw, odds_away FROM matches "
        "WHERE sport='soccer' AND outcome IS NOT NULL AND odds_home IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()
    return rows


def h2h_record(h2h, league: str, a: str, b: str) -> tuple[int, float]:
    """Games between a and b in this league, and how many of those a won (draws count 0.5)."""
    rec = h2h.get((league, a, b))
    if not rec:
        return 0, 0.0
    return rec[1], rec[0]


def h2h_update(h2h, league: str, home: str, away: str, outcome: str) -> None:
    """Record one match from both teams' perspectives under the ordered key (league, a, b)."""
    score_home = {"H": 1.0, "D": 0.5, "A": 0.0}[outcome]
    for key, pts in (((league, home, away), score_home), ((league, away, home), 1.0 - score_home)):
        h2h[key][0] += pts
        h2h[key][1] += 1


def run(db: Path) -> None:
    rows = load(db)
    elo: dict[str, Elo] = {}
    h2h: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0])  # (league, a, b) -> [a's points, games]
    recs = []
    for kickoff, league, home, away, outcome, oh, od, oa in rows:
        model = elo.setdefault(league, Elo(k=20, home_adv=60))
        ratings = model.ratings
        # market implied probs (de-vig)
        inv = np.array([1 / oh, 1 / od, 1 / oa])
        pm = inv / inv.sum()
        fav_is_home = pm[0] >= pm[2]
        fav, dog = (home, away) if fav_is_home else (away, home)
        p_fav = pm[0] if fav_is_home else pm[2]
        # strong: favourite is in the top 5 by Elo among teams in this league (point-in-time)
        league_teams = [t for (lg_, t) in [(league, x) for x in ratings] if True]
        ranked = sorted(ratings.keys(), key=lambda t: -ratings[t])
        strong = fav in ranked[:5] if len(ratings) >= 5 else False
        games, wins_fav = h2h_record(h2h, league, fav, dog)
        shrunk = (wins_fav + 1.0) / (games + 2.0)
        edge = shrunk - p_fav
        won_fav = outcome == ("H" if fav_is_home else "A")
        price = oh if fav_is_home else oa
        recs.append((kickoff, league, edge, p_fav, price, won_fav, games, strong))
        # update H2H (symmetric key, points from each side's view) and Elo after recording
        h2h_update(h2h, league, home, away, outcome)
        model.update(home, away, {"H": 1.0, "D": 0.5, "A": 0.0}[outcome])

    disc = [r for r in recs if r[0] < CONFIRM_FROM]
    conf = [r for r in recs if r[0] >= CONFIRM_FROM]
    print(f"records: discovery={len(disc)} confirmation={len(conf)}")
    for t in THRESH:
        for name, sub in (("discovery", disc), ("confirmation", conf)):
            pnl = np.array([(p - 1) if won else -1.0 for _, _, e, _, p, won, g, st in sub if e > t and g >= 3 and st])
            if len(pnl):
                print(f"strong fav, edge>{t:.2f} {name:<13} ROI {pnl.mean():+.4f}  n={len(pnl)}")
