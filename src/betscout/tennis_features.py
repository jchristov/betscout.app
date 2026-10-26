"""Point-in-time features for tennis singles (no prices in this source; calibration only).

For each match, features use only earlier matches:
  elo_diff      Elo(home) - Elo(away) before the match (per tour, K=32)
  form10_diff   win rate over last 10 matches (home) - (away)
  rest_diff     days since last match (home) - (away), capped at 14
  h2h_rate      shrunk head-to-head win rate of home over away
Target: home win (outcome == 'H'). Evaluated out-of-sample with log loss against a 0.5 baseline.
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from .elo import Elo

FEATS = ("elo_diff", "form10_diff", "rest_diff", "h2h_rate")


@dataclass
class TRow:
    kickoff: str
    league: str
    y: int
    elo_diff: float
    form10_diff: float
    rest_diff: float
    h2h_rate: float


def build(db: Path) -> list[TRow]:
    conn = sqlite3.connect(db)
    raw = conn.execute(
        "SELECT kickoff, league, home, away, outcome FROM matches WHERE sport='tennis' "
        "AND outcome IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()
    elo: dict[str, Elo] = {}
    hist: dict[tuple, deque] = defaultdict(lambda: deque(maxlen=10))
    last: dict[tuple, datetime] = {}
    h2h: dict[tuple, list[float]] = defaultdict(lambda: [0.0, 0])
    out: list[TRow] = []
    for kickoff, league, home, away, outcome in raw:
        when = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).replace(tzinfo=None)
        model = elo.setdefault(league, Elo(k=32, home_adv=0))
        hk, ak = (league, home), (league, away)

        def form(k):
            h = hist[k]
            return sum(h) / len(h) if h else 0.5

        def rest(k):
            return min((when - last[k]).days, 14) if k in last else 14

        pts = h2h[(league, home, away)]
        out.append(TRow(
            kickoff=kickoff, league=league, y=1 if outcome == "H" else 0,
            elo_diff=(model.ratings[home] - model.ratings[away]) / 400.0,
            form10_diff=form(hk) - form(ak),
            rest_diff=float(rest(hk) - rest(ak)),
            h2h_rate=(pts[0] + 1.0) / (pts[1] + 2.0) - 0.5,
        ))
        won_h = 1 if outcome == "H" else 0
        hist[hk].append(won_h); hist[ak].append(1 - won_h)
        last[hk] = last[ak] = when
        h2h[(league, home, away)][0] += won_h; h2h[(league, home, away)][1] += 1
        h2h[(league, away, home)][0] += 1 - won_h; h2h[(league, away, home)][1] += 1
        model.update(home, away, float(won_h))
    return out


def evaluate(rows: list[TRow]) -> dict[str, float]:
    """Out-of-sample log loss, fitted on the earlier half, scored on the later half, per tour."""
    res = {}
    for tour in sorted({r.league for r in rows}):
        sub = sorted([r for r in rows if r.league == tour], key=lambda r: r.kickoff)
        cut = len(sub) // 2
        tr, te = sub[:cut], sub[cut:]
        ytr = np.array([r.y for r in tr]); yte = np.array([r.y for r in te])
        base = -np.mean(yte * math.log(0.5) + (1 - yte) * math.log(0.5))
        res[f"{tour}|baseline"] = base
        for name, cols in (("elo", ("elo_diff",)), ("all", FEATS)):
            X = np.array([[getattr(r, c) for c in cols] for r in tr])
            clf = LogisticRegression(C=1.0, max_iter=2000).fit(X, ytr)
            p = clf.predict_proba(np.array([[getattr(r, c) for c in cols] for r in te]))[:, 1]
            p = np.clip(p, 1e-9, 1 - 1e-9)
            res[f"{tour}|{name}"] = float(-np.mean(yte * np.log(p) + (1 - yte) * np.log(1 - p)))
        res[f"{tour}|n_test"] = len(te)
    return res


if __name__ == "__main__":
    import sys
    rows = build(Path(sys.argv[1] if len(sys.argv) > 1 else "data/betscout.db"))
    for k, v in evaluate(rows).items():
        print(f"{k:<20}{v:>10.4f}" if "n_test" not in k else f"{k:<20}{v:>10.0f}")
