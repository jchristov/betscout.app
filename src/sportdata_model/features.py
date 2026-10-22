"""Point-in-time feature engineering for soccer, across leagues.

Every feature for a match uses only matches with kickoff strictly before it (no look-ahead):
  elo_diff        Elo(home) - Elo(away), before the match
  form5_diff      points per game, last 5 (home) - (away)
  gf5_diff        goals scored per game, last 5 (home) - (away)
  ga5_diff        goals conceded per game, last 5 (home) - (away)
  rest_diff       days since last match (home) - (away), capped at 14
  h2h_pts         points the home side earned in prior meetings (shrunk toward 1.0 per game)
  mkt_home_logit  logit of de-vigged market home probability (price information, not a model input here)

Target: home result (H/D/A). Market probabilities are kept so each feature can be tested as a
residual over the price, which is the only comparison that matters for betting.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import numpy as np

from .elo import Elo

FORM_N = 5
FEATURES = ("elo_diff", "form5_diff", "gf5_diff", "ga5_diff", "rest_diff", "h2h_pts")


@dataclass
class Feat:
    kickoff: str
    league: str
    outcome: str
    elo_diff: float
    form5_diff: float
    gf5_diff: float
    ga5_diff: float
    rest_diff: float
    h2h_pts: float
    mkt_home: float | None
    mkt_draw: float | None
    mkt_away: float | None


def _state(hist: deque, when: datetime) -> tuple[float, float, float, float]:
    if not hist:
        return 14.0, 1.5, 1.4, 1.4
    rest = min((when - hist[-1][0]).days, 14)
    rec = list(hist)[-FORM_N:]
    n = len(rec)
    return float(rest), sum(p for _, p, _, _ in rec) / n, sum(g for _, _, g, _ in rec) / n, sum(c for _, _, _, c in rec) / n


def build(db: Path) -> list[Feat]:
    conn = sqlite3.connect(db)
    raw = conn.execute(
        "SELECT kickoff, league, home, away, outcome, home_score, away_score, odds_home, odds_draw, odds_away "
        "FROM matches WHERE sport='soccer' AND outcome IS NOT NULL AND home_score IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()
    elo: dict[str, Elo] = {}
    hist: dict[tuple, deque] = defaultdict(lambda: deque(maxlen=FORM_N))
    h2h: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0])
    out: list[Feat] = []
    for kickoff, league, home, away, outcome, hs, as_, oh, od, oa in raw:
        when = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).replace(tzinfo=None)
        model = elo.setdefault(league, Elo(k=20, home_adv=60))
        hk, ak = (league, home), (league, away)
        hr, hf, hg, hc = _state(hist[hk], when)
        ar, af, ag, ac = _state(hist[ak], when)
        pts = h2h[(league, home, away)]
        h2h_rate = (pts[0] + 1.0) / (pts[1] + 2.0)  # shrunk toward an even split
        mkt = (None, None, None)
        if oh and od and oa:
            inv = np.array([1 / oh, 1 / od, 1 / oa])
            mkt = tuple(float(x) for x in inv / inv.sum())
        out.append(Feat(
            kickoff=kickoff, league=league, outcome=outcome,
            elo_diff=model.ratings[home] - model.ratings[away],
            form5_diff=hf - af, gf5_diff=hg - ag, ga5_diff=hc - ac,
            rest_diff=hr - ar, h2h_pts=h2h_rate,
            mkt_home=mkt[0], mkt_draw=mkt[1], mkt_away=mkt[2],
        ))
        # update state after recording
        pts_h = {"H": 3, "D": 1, "A": 0}[outcome]
        pts_a = {"H": 0, "D": 1, "A": 3}[outcome]
        hist[hk].append((when, pts_h, hs, as_))
        hist[ak].append((when, pts_a, as_, hs))
        h2h[(league, home, away)][0] += {"H": 1.0, "D": 0.5, "A": 0.0}[outcome]; h2h[(league, home, away)][1] += 1
        h2h[(league, away, home)][0] += {"H": 0.0, "D": 0.5, "A": 1.0}[outcome]; h2h[(league, away, home)][1] += 1
        model.update(home, away, {"H": 1.0, "D": 0.5, "A": 0.0}[outcome])
    return out
