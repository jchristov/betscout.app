"""Independent-model totals test (Over/Under at each match's posted line).

Probability source: walk-forward Poisson model (team attack/defence rates, no look-ahead).
Price source: the bookmaker's own Over/Under prices, de-vigged.
Rule (fixed in advance): back a side when model probability x decimal price - 1 > threshold.
Evaluation: only the later half of matches (chronological), never used to choose the rule.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .goals import markets, score_grid
from .walkforward import _strength


@dataclass
class Row:
    p_over_model: float
    p_over_book: float
    odds_over: float
    odds_under: float
    over: bool
    league: str = ""
    year: str = ""


def build(db: Path) -> list[Row]:
    conn = sqlite3.connect(db)
    raw = conn.execute(
        "SELECT kickoff, league, home, away, home_score, away_score, line_total, odds_over, odds_under "
        "FROM matches WHERE sport='soccer' AND outcome IS NOT NULL AND home_score IS NOT NULL "
        "AND line_total IS NOT NULL AND odds_over IS NOT NULL AND odds_under IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()
    hist = defaultdict(lambda: [0.0, 0.0, 0])
    lg_goals = defaultdict(lambda: [0.0, 0])
    rows: list[Row] = []
    for kickoff, league, home, away, hs, as_, line, oo, ou in raw:
        hk, ak = (league, home), (league, away)
        mean = lg_goals[league][0] / lg_goals[league][1] if lg_goals[league][1] else 1.35
        if min(hist[hk][2], hist[ak][2]) >= 5:
            hgf, hga = _strength(hist, hk, mean)
            agf, aga = _strength(hist, ak, mean)
            grid = score_grid(hgf * aga / mean, agf * hga / mean)
            p_model = markets(grid, line)["over"]
            mo, mu = 1 / oo, 1 / ou
            rows.append(Row(p_model, mo / (mo + mu), oo, ou, (hs + as_) > line,
                            league, kickoff[:4]))
        hist[hk][0] += hs; hist[hk][1] += as_; hist[hk][2] += 1
        hist[ak][0] += as_; hist[ak][1] += hs; hist[ak][2] += 1
        lg_goals[league][0] += hs + as_; lg_goals[league][1] += 2
    return rows


def bets(rows: list[Row], side: str, threshold: float) -> list[tuple[bool, float]]:
    out = []
    for r in rows:
        if side == "over":
            p, price, won = r.p_over_model, r.odds_over, r.over
        else:
            p, price, won = 1 - r.p_over_model, r.odds_under, not r.over
        if p * price - 1 > threshold:
            out.append((won, price))
    return out


def ci(bs: list[tuple[bool, float]], seed: int = 0) -> tuple[float, float, float, int]:
    if not bs:
        return float("nan"), float("nan"), float("nan"), 0
    pnl = np.array([(p - 1) if w else -1.0 for w, p in bs])
    rng = np.random.default_rng(seed)
    boots = pnl[rng.integers(0, len(pnl), size=(2000, len(pnl)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(pnl.mean()), float(lo), float(hi), len(pnl)


def run(db: Path) -> None:
    rows = build(db)
    cut = len(rows) // 2
    test = rows[cut:]
    print(f"matches with model + totals prices: {len(rows)}; evaluated on later half: {len(test)}")
    mean_model = np.mean([r.p_over_model for r in test])
    mean_book = np.mean([r.p_over_book for r in test])
    realised = np.mean([r.over for r in test])
    print(f"test half: model P(over) {mean_model:.3f}  book P(over) {mean_book:.3f}  realised {realised:.3f}\n")
    for side in ("over", "under"):
        for t in (0.0, 0.02, 0.05):
            m, lo, hi, n = ci(bets(test, side, t))
            print(f"{side:<6} model EV > {t:.2f}: ROI {m:+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  bets={n}")
