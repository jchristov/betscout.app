"""Out-of-sample experiments on soccer 1X2: does anything add information on top of the market?

Pre-match features per match use only results strictly before kickoff:
  elo_diff      Elo(home) - Elo(away) before the match
  rest_diff     days since last match (home) - (away), capped at 14
  form_diff     points per game over last 5 (home) - (away)
  gd_diff       goal difference per game over last 5 (home) - (away)
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
from .models import OUTCOMES, TRAIN_FRAC, devig, logit

FORM_N = 5


@dataclass
class Row:
    kickoff: datetime
    league: str
    outcome: str
    market: tuple[float, float, float]
    odds: tuple[float, float, float]
    elo_diff: float
    rest_diff: float
    form_diff: float
    gd_diff: float


def _team_feats(hist: deque, when: datetime) -> tuple[float, float, float]:
    """(rest_days, points_per_game, goal_diff_per_game) from the last FORM_N finished matches."""
    if not hist:
        return 14.0, 1.5, 0.0
    rest = min((when - hist[-1][0]).days, 14)
    recent = list(hist)[-FORM_N:]
    ppg = sum(p for _, p, _ in recent) / len(recent)
    gd = sum(g for _, _, g in recent) / len(recent)
    return float(rest), ppg, gd


def build_rows(db: Path) -> list[Row]:
    conn = sqlite3.connect(db)
    raw = conn.execute(
        "SELECT kickoff, league, home, away, outcome, home_score, away_score, odds_home, odds_draw, odds_away "
        "FROM matches WHERE sport='soccer' AND outcome IS NOT NULL AND home_score IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()

    elo: dict[str, Elo] = {}
    hist: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=FORM_N))
    rows: list[Row] = []
    for kickoff, league, home, away, outcome, hs, as_, oh, od, oa in raw:
        when = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).replace(tzinfo=None)
        model = elo.setdefault(league, Elo(k=20, home_adv=0))
        hk, ak = (league, home), (league, away)
        h_rest, h_ppg, h_gd = _team_feats(hist[hk], when)
        a_rest, a_ppg, a_gd = _team_feats(hist[ak], when)
        if oh and od and oa:
            rows.append(Row(
                kickoff=when, league=league, outcome=outcome,
                market=devig((oh, od, oa)), odds=(oh, od, oa),
                elo_diff=model.ratings[home] - model.ratings[away],
                rest_diff=h_rest - a_rest, form_diff=h_ppg - a_ppg, gd_diff=h_gd - a_gd,
            ))
        # update state after recording pre-match features
        model.update(home, away, {"H": 1.0, "D": 0.5, "A": 0.0}[outcome])
        pts_h = {"H": 3, "D": 1, "A": 0}[outcome]
        pts_a = {"H": 0, "D": 1, "A": 3}[outcome]
        hist[hk].append((when, pts_h, hs - as_))
        hist[ak].append((when, pts_a, as_ - hs))
    return rows


def _X(rows: list[Row], cols: tuple[str, ...]) -> np.ndarray:
    feats = []
    for r in rows:
        f = []
        for c in cols:
            if c == "mkt_h":
                f.append(logit(r.market[0]))
            elif c == "mkt_a":
                f.append(logit(r.market[2]))
            else:
                f.append(getattr(r, c) / (400 if c == "elo_diff" else 1))
        feats.append(f)
    return np.array(feats)


def _y(rows: list[Row]) -> np.ndarray:
    return np.array([OUTCOMES.index(r.outcome) for r in rows])


def fit_predict(train: list[Row], test: list[Row], cols: tuple[str, ...]) -> np.ndarray:
    clf = LogisticRegression(C=1.0, max_iter=2000)
    clf.fit(_X(train, cols), _y(train))
    return clf.predict_proba(_X(test, cols))


def per_match_logloss(probs: np.ndarray, rows: list[Row]) -> np.ndarray:
    y = _y(rows)
    return -np.log(np.clip(probs[np.arange(len(rows)), y], 1e-12, 1))


def run(db: Path, n_boot: int = 2000, seed: int = 0) -> None:
    rows = build_rows(db)
    cut = int(len(rows) * TRAIN_FRAC)
    train, test = rows[:cut], rows[cut:]
    print(f"rows={len(rows)}  train={len(train)}  test={len(test)}  test window {test[0].kickoff:%Y-%m-%d}..{test[-1].kickoff:%Y-%m-%d}")

    market = np.array([r.market for r in test])
    models = {
        "market (de-vig)": market,
        "market recalibrated": fit_predict(train, test, ("mkt_h", "mkt_a")),
        "market + elo": fit_predict(train, test, ("mkt_h", "mkt_a", "elo_diff")),
        "market + form": fit_predict(train, test, ("mkt_h", "mkt_a", "form_diff", "gd_diff")),
        "market + rest": fit_predict(train, test, ("mkt_h", "mkt_a", "rest_diff")),
        "market + all context": fit_predict(train, test, ("mkt_h", "mkt_a", "elo_diff", "rest_diff", "form_diff", "gd_diff")),
    }

    base = per_match_logloss(market, test)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(test), size=(n_boot, len(test)))
    print(f"\n{'model':<24}{'log_loss':>10}{'vs market':>11}{'95% CI (paired)':>22}")
    for name, probs in models.items():
        ll = per_match_logloss(probs, test)
        diff = ll - base
        boots = diff[idx].mean(axis=1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        print(f"{name:<24}{ll.mean():>10.4f}{diff.mean():>+11.4f}{f'[{lo:+.4f}, {hi:+.4f}]':>22}")
