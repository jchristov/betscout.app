"""Systematic edge search on soccer markets with a fixed discovery / confirmation protocol.

Model: walk-forward Poisson goals (no look-ahead), giving H/D/A, double chance and Over/Under
probabilities at each match's own posted line.
Protocol:
  discovery    kickoff < 2025-07-01  (seasons 2022/23 to 2024/25 start): calibrators are fitted here,
               and candidate (market side, league) pairs are kept only if flat ROI > 0 here.
  confirmation kickoff >= 2025-07-01 (season 2025/26): each kept candidate is tested once.
               Holm correction across all confirmation tests.
Calibration: logistic regression on logit(model prob), fitted per side on discovery rows only.
Bet rule (fixed): back a side when calibrated probability x decimal price - 1 > 0.
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from .goals import markets, score_grid
from .models import logit
from .walkforward import _strength

CONFIRM_FROM = "2025-07-01"
SIDES = ("H", "D", "A", "1X", "X2", "12", "OVER", "UNDER")


@dataclass
class Row:
    kickoff: str
    league: str
    outcome: str
    model: dict[str, float]
    price: dict[str, float]
    over_realised: bool | None


def build(db: Path) -> list[Row]:
    conn = sqlite3.connect(db)
    raw = conn.execute(
        "SELECT kickoff, league, home, away, outcome, home_score, away_score, odds_home, odds_draw, odds_away, "
        "odds_dc_1x, odds_dc_x2, odds_dc_12, line_total, odds_over, odds_under "
        "FROM matches WHERE sport='soccer' AND outcome IS NOT NULL AND home_score IS NOT NULL ORDER BY kickoff"
    ).fetchall()
    conn.close()
    hist = defaultdict(lambda: [0.0, 0.0, 0])
    lg = defaultdict(lambda: [0.0, 0])
    rows: list[Row] = []
    for (kickoff, league, home, away, outcome, hs, as_, oh, od, oa, d1x, dx2, d12,
         line, oo, ou) in raw:
        hk, ak = (league, home), (league, away)
        mean = lg[league][0] / lg[league][1] if lg[league][1] else 1.35
        if min(hist[hk][2], hist[ak][2]) >= 5 and oh and od and oa:
            hgf, hga = _strength(hist, hk, mean)
            agf, aga = _strength(hist, ak, mean)
            grid = score_grid(hgf * aga / mean, agf * hga / mean)
            m = markets(grid, line)
            model = {"H": m["home"], "D": m["draw"], "A": m["away"], "1X": m["dc_1x"],
                     "X2": m["dc_x2"], "12": m["dc_12"]}
            price = {"H": oh, "D": od, "A": oa}
            if d1x and dx2 and d12:
                price.update({"1X": d1x, "X2": dx2, "12": d12})
            over_real = None
            if line is not None and oo and ou:
                model["OVER"] = m["over"]
                model["UNDER"] = 1 - m["over"]
                price["OVER"], price["UNDER"] = oo, ou
                over_real = (hs + as_) > line
            rows.append(Row(kickoff, league, outcome, model, price, over_real))
        hist[hk][0] += hs; hist[hk][1] += as_; hist[hk][2] += 1
        hist[ak][0] += as_; hist[ak][1] += hs; hist[ak][2] += 1
        lg[league][0] += hs + as_; lg[league][1] += 2
    return rows


def hit(side: str, r: Row) -> bool:
    if side in ("H", "D", "A"):
        return r.outcome == side
    if side == "1X":
        return r.outcome in ("H", "D")
    if side == "X2":
        return r.outcome in ("D", "A")
    if side == "12":
        return r.outcome in ("H", "A")
    if side == "OVER":
        return bool(r.over_realised)
    return not r.over_realised


def roi_ci(pnl: np.ndarray, seed: int = 0) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    boots = pnl[rng.integers(0, len(pnl), size=(2000, len(pnl)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(pnl.mean()), float(lo), float(hi)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def pval_mean_positive(pnl: np.ndarray, seed: int = 0) -> float:
    """One-sided bootstrap p-value that mean ROI <= 0."""
    rng = np.random.default_rng(seed)
    means = pnl[rng.integers(0, len(pnl), size=(4000, len(pnl)))].mean(axis=1)
    return float((means <= 0).mean())


def run(db: Path) -> None:
    rows = build(db)
    disc = [r for r in rows if r.kickoff < CONFIRM_FROM]
    conf = [r for r in rows if r.kickoff >= CONFIRM_FROM]
    print(f"matches: discovery={len(disc)}  confirmation={len(conf)}")

    calibrators = {}
    for side in SIDES:
        pts = [r for r in disc if side in r.model and side in r.price]
        if len(pts) < 200:
            continue
        X = np.array([[logit(r.model[side])] for r in pts])
        y = np.array([hit(side, r) for r in pts])
        calibrators[side] = LogisticRegression(C=1.0).fit(X, y)

    def q(side: str, r: Row) -> float:
        return float(calibrators[side].predict_proba([[logit(r.model[side])]])[0, 1])

    def bets(side: str, rs: list[Row], league: str | None = None) -> np.ndarray:
        out = []
        for r in rs:
            if side not in r.model or side not in r.price or (league and r.league != league):
                continue
            if side not in calibrators:
                continue
            p = q(side, r)
            if p * r.price[side] - 1 > 0:
                out.append((r.price[side] - 1) if hit(side, r) else -1.0)
        return np.array(out)

    leagues = sorted({r.league for r in rows})
    candidates = []
    for side in calibrators:
        for lg in [None] + leagues:
            pnl_d = bets(side, disc, lg)
            if len(pnl_d) < 100 or pnl_d.mean() <= 0:
                continue
            candidates.append((side, lg, pnl_d))
    print(f"discovery candidates with positive ROI: {len(candidates)}")

    pvals, results = {}, {}
    for side, lg, _ in candidates:
        pnl_c = bets(side, conf, lg)
        key = f"{side}|{lg or 'ALL'}"
        if len(pnl_c) < 30:
            continue
        pvals[key] = pval_mean_positive(pnl_c)
        results[key] = (pnl_c, roi_ci(pnl_c))
    adj = holm(pvals)

    print(f"\n{'candidate':<18}{'disc ROI':>10}{'conf ROI':>10}{'95% CI':>22}{'n':>6}{'p':>8}{'holm':>8}")
    for side, lg, pnl_d in sorted(candidates, key=lambda c: -c[2].mean()):
        key = f"{side}|{lg or 'ALL'}"
        if key not in results:
            continue
        pnl_c, (m, lo, hi) = results[key]
        print(f"{key:<18}{pnl_d.mean():>+10.4f}{m:>+10.4f}{f'[{lo:+.3f},{hi:+.3f}]':>22}{len(pnl_c):>6}"
              f"{pvals[key]:>8.3f}{adj[key]:>8.3f}")


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1] if len(sys.argv) > 1 else "data/matches.sqlite"))
