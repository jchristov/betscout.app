"""Honest out-of-sample evaluation of Elo-based models against the bookmaker market.

Protocol (no look-ahead):
  1. Elo ratings are updated sequentially in kickoff order. Each prediction uses only earlier results.
  2. The matches are split chronologically: the first TRAIN_FRAC fit calibration parameters;
     the remaining matches are the untouched test set used for all reported numbers.
  3. Calibration is a logistic regression (one-vs-rest) on logit probabilities, fitted on the train set.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from .elo import Elo

TRAIN_FRAC = 0.5
OUTCOMES = ("H", "D", "A")


def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def devig(prices: tuple[float, ...]) -> tuple[float, ...]:
    inv = [1 / x for x in prices]
    s = sum(inv)
    return tuple(v / s for v in inv)


@dataclass
class Sample:
    kickoff: str
    league: str
    outcome: str  # H, D, A
    elo: tuple[float, float, float]  # model P(H), P(D), P(A) from Elo
    market: tuple[float, float, float] | None  # de-vigged market P(H), P(D), P(A)
    odds: tuple[float, float, float] | None  # decimal prices, for betting simulation


def soccer_samples(db: Path) -> list[Sample]:
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT kickoff, league, home, away, outcome, odds_home, odds_draw, odds_away "
        "FROM matches WHERE sport='soccer' AND outcome IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()
    elo: dict[str, Elo] = {}
    out: list[Sample] = []
    draw_rate = 0.26  # soccer draw frequency; kept fixed (not fitted) to avoid leakage
    for kickoff, league, home, away, outcome, oh, od, oa in rows:
        model = elo.setdefault(league, Elo(k=20, home_adv=60))
        ph = model.p_home_win_or_draw_free(home, away)
        pd_ = draw_rate
        probs = (max(ph - pd_ / 2, 0.01), pd_, max(1 - ph - pd_ / 2, 0.01))
        s = sum(probs)
        probs = tuple(p / s for p in probs)
        has_odds = oh and od and oa
        out.append(Sample(kickoff, league, outcome, probs,
                          devig((oh, od, oa)) if has_odds else None,
                          (oh, od, oa) if has_odds else None))
        score = {"H": 1.0, "D": 0.5, "A": 0.0}[outcome]
        model.update(home, away, score)
    return out


def tennis_samples(db: Path) -> list[Sample]:
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT kickoff, league, home, away, outcome FROM matches WHERE sport='tennis' "
        "AND outcome IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()
    elo: dict[str, Elo] = {}
    out: list[Sample] = []
    for kickoff, league, home, away, outcome in rows:
        model = elo.setdefault(league, Elo(k=32, home_adv=0.0))
        ph = model.p_home_win_or_draw_free(home, away)
        out.append(Sample(kickoff, league, outcome, (ph, 0.0, 1 - ph), None, None))
        model.update(home, away, 1.0 if outcome == "H" else 0.0)
    return out


def _features(s: Sample, use_market: bool) -> list[float]:
    f = [logit(s.elo[0]), logit(s.elo[2])]
    if use_market:
        f += [logit(s.market[0]), logit(s.market[2])]
    return f


def fit_calibrator(train: list[Sample], use_market: bool):
    """One-vs-rest logistic per outcome on logit features; returns predict(sample) -> (pH, pD, pA)."""
    X = np.array([_features(s, use_market) for s in train])
    models = {}
    for o in OUTCOMES:
        y = np.array([1 if s.outcome == o else 0 for s in train])
        models[o] = LogisticRegression(C=1.0, max_iter=1000).fit(X, y)

    def predict(s: Sample) -> tuple[float, float, float]:
        x = np.array([_features(s, use_market)])
        raw = [models[o].predict_proba(x)[0, 1] for o in OUTCOMES]
        tot = sum(raw)
        return tuple(r / tot for r in raw)

    return predict


def log_loss(probs: list[tuple[float, float, float]], outcomes: list[str]) -> float:
    idx = {"H": 0, "D": 1, "A": 2}
    return -float(np.mean([math.log(max(p[idx[o]], 1e-12)) for p, o in zip(probs, outcomes)]))


def brier(probs: list[tuple[float, float, float]], outcomes: list[str]) -> float:
    idx = {"H": 0, "D": 1, "A": 2}
    total = 0.0
    for p, o in zip(probs, outcomes):
        for i, name in enumerate(OUTCOMES):
            total += (p[i] - (1.0 if name == o else 0.0)) ** 2
    return total / len(probs)


def ece(probs: list[tuple[float, float, float]], outcomes: list[str], bins: int = 10) -> float:
    """Expected calibration error over all (outcome, probability) pairs."""
    pairs = [(p[i], 1.0 if name == o else 0.0) for p, o in zip(probs, outcomes) for i, name in enumerate(OUTCOMES)]
    conf = np.array([a for a, _ in pairs])
    hit = np.array([b for _, b in pairs])
    err = 0.0
    edges = np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf >= lo) & (conf < hi + (1e-9 if hi == 1 else 0))
        if m.any():
            err += m.mean() * abs(conf[m].mean() - hit[m].mean())
    return float(err)


@dataclass
class Result:
    name: str
    n: int
    log_loss: float
    brier: float
    ece: float
    extras: dict = field(default_factory=dict)


def evaluate(samples: list[Sample]) -> list[Result]:
    cut = int(len(samples) * TRAIN_FRAC)
    train, test = samples[:cut], samples[cut:]
    outcomes = [s.outcome for s in test]
    results: list[Result] = []

    def add(name: str, probs: list[tuple[float, float, float]]) -> None:
        results.append(Result(name, len(probs), log_loss(probs, outcomes), brier(probs, outcomes), ece(probs, outcomes)))

    has_mkt = [s for s in test if s.market]
    if has_mkt:
        mo = [s.outcome for s in has_mkt]
        add_market = lambda name, pr: results.append(Result(name, len(pr), log_loss(pr, mo), brier(pr, mo), ece(pr, mo)))  # noqa: E731
        add_market("market (de-vig)", [s.market for s in has_mkt])
        add_market("elo (raw)", [s.elo for s in has_mkt])
        cal_m = fit_calibrator([s for s in train if s.market], use_market=True)
        add_market("calibrated elo+market", [cal_m(s) for s in has_mkt])
        cal_e = fit_calibrator([s for s in train if s.market], use_market=False)
        add_market("calibrated elo only", [cal_e(s) for s in has_mkt])
    else:
        add("elo (raw)", [s.elo for s in test])
    return results


def fmt(results: list[Result]) -> str:
    lines = [f"{'model':<26}{'n':>7}{'log_loss':>10}{'brier':>9}{'ECE':>8}"]
    for r in results:
        lines.append(f"{r.name:<26}{r.n:>7}{r.log_loss:>10.4f}{r.brier:>9.4f}{r.ece:>8.4f}")
    return "\n".join(lines)
