"""Accumulator (combo) test: does combining legs raise profitability?

Legs: single soccer selections (1X2, double chance, Over/Under at the posted line) with a
walk-forward Poisson probability, recalibrated per side on DISCOVERY only (logistic on logit prob).
Accumulator: on each match day, take the k legs with the highest calibrated EV (one per match,
all from different matches, so no same-match correlation), combine them, stake 1.
Protocol: choose k and EV threshold on discovery (kickoff < 2025-07-01); evaluate once on 2025/26.
Baseline: same-size accumulators built from RANDOM sides at the book's prices. Its expected ROI
shows how much margin compounding costs before any model is involved.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from .edges import CONFIRM_FROM, Row, build, hit
from .models import logit

SIDES = ("H", "D", "A", "1X", "X2", "12", "OVER", "UNDER")


def calibrate(disc: list[Row]) -> dict[str, LogisticRegression]:
    cals = {}
    for s in SIDES:
        pts = [r for r in disc if s in r.model and s in r.price]
        if len(pts) < 200:
            continue
        X = np.array([[logit(r.model[s])] for r in pts])
        y = np.array([hit(s, r) for r in pts])
        cals[s] = LogisticRegression(C=1.0).fit(X, y)
    return cals


def legs_for(rows: list[Row], cals, thr: float) -> list[tuple[str, Row, float, float]]:
    """(day, row, ev, price) for the best calibrated side of each match above the EV threshold."""
    out = []
    for r in rows:
        best = None
        for s, cal in cals.items():
            if s not in r.model or s not in r.price:
                continue
            p = float(cal.predict_proba([[logit(r.model[s])]])[0, 1])
            ev = p * r.price[s] - 1
            if ev > thr and (best is None or ev > best[0]):
                best = (ev, s, r.price[s])
        if best:
            out.append((r.kickoff[:10], r, best, best[1]))
    return out


def accumulators(legs, k: int, rng=None):
    """Group legs by day; chunk each day's sorted legs into accumulators of size k (leftovers dropped)."""
    days = defaultdict(list)
    for day, r, (ev, s, price), _ in legs:
        days[day].append((ev, s, price, r))
    accs = []
    for day, items in days.items():
        items.sort(key=lambda x: -x[0])
        if rng is not None:
            rng.shuffle(items)
        for i in range(0, len(items) - k + 1, k):
            chunk = items[i:i + k]
            odds = np.prod([c[2] for c in chunk])
            won = all(hit(c[1], c[3]) for c in chunk)
            accs.append((odds - 1) if won else -1.0)
    return np.array(accs)


def random_accs(rows: list[Row], k: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    legs = []
    for r in rows:
        sides = [s for s in ("H", "D", "A") if s in r.price]
        if not sides:
            continue
        s = sides[rng.integers(len(sides))]
        legs.append((r.kickoff[:10], r, (0.0, s, r.price[s]), s))
    return accumulators(legs, k)


def ci(pnl: np.ndarray, seed: int = 0):
    if len(pnl) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    b = pnl[rng.integers(0, len(pnl), size=(2000, len(pnl)))].mean(axis=1)
    return float(pnl.mean()), *(float(x) for x in np.percentile(b, [2.5, 97.5]))


def run(db: Path) -> None:
    rows = build(db)
    disc = [r for r in rows if r.kickoff < CONFIRM_FROM]
    conf = [r for r in rows if r.kickoff >= CONFIRM_FROM]
    cals = calibrate(disc)
    print(f"discovery={len(disc)} confirmation={len(conf)} calibrated sides={sorted(cals)}\n")

    print("discovery: accumulator size k x EV threshold (mean ROI per accumulator, n)")
    best = None
    for k in (1, 2, 3):
        for thr in (0.0, 0.03, 0.06, 0.10):
            pnl = accumulators(legs_for(disc, cals, thr), k)
            if len(pnl) < 50:
                continue
            m, lo, hi = ci(pnl)
            print(f"  k={k} EV>{thr:.2f}: ROI {m:+.4f} CI [{lo:+.3f},{hi:+.3f}] n={len(pnl)}")
            if best is None or m > best[0]:
                best = (m, k, thr)
    print(f"\nselected on discovery: k={best[1]} EV>{best[2]:.2f} (discovery ROI {best[0]:+.4f})")

    k, thr = best[1], best[2]
    cpnl = accumulators(legs_for(conf, cals, thr), k)
    m, lo, hi = ci(cpnl)
    print(f"CONFIRMATION (run once): ROI {m:+.4f} CI [{lo:+.3f},{hi:+.3f}] n={len(cpnl)}")
    bpnl = random_accs(conf, k)
    m, lo, hi = ci(bpnl)
    print(f"baseline random {k}-leg accumulators, confirmation: ROI {m:+.4f} CI [{lo:+.3f},{hi:+.3f}] n={len(bpnl)}")


if __name__ == "__main__":
    import sys
    run(Path(sys.argv[1] if len(sys.argv) > 1 else "data/betscout.db"))
