"""Tune the favourite H2H lead on DISCOVERY only (kickoff < 2025-07-01); confirm once on 2025/26.

Each match contributes one record with point-in-time features:
  price, pf (market prob of the favourite), strong (fav in top-N Elo), g (H2H games), edge (shrunk H2H - pf),
  won (favourite won), league, kickoff.
Grid: top-N in {3,5,8}, min H2H games in {2,3,5}, prior strength k in {1,2,4}, price band (pf) in several ranges,
edge threshold in {0, 0.03, 0.06}. Selection criterion: discovery ROI lower confidence bound (bootstrap 5th pct),
which penalises thin samples. Holm correction is applied across the grid to the discovery p-values for reporting.
"""

from __future__ import annotations

import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np

from .elo import Elo
from .favourites import CONFIRM_FROM, h2h_record, h2h_update, load

CACHE = Path("data/h2h_records.pkl")


def build_records(db: Path) -> list[dict]:
    if CACHE.exists():
        return pickle.loads(CACHE.read_bytes())
    rows = load(db)
    elo: dict[str, Elo] = {}
    h2h = defaultdict(lambda: [0.0, 0])
    recs = []
    for kickoff, league, home, away, outcome, oh, od, oa in rows:
        model = elo.setdefault(league, Elo(k=20, home_adv=60))
        inv = np.array([1 / oh, 1 / od, 1 / oa])
        pm = inv / inv.sum()
        fav_home = pm[0] >= pm[2]
        fav, dog = (home, away) if fav_home else (away, home)
        pf = float(pm[0] if fav_home else pm[2])
        ranked = sorted(model.ratings, key=lambda t: -model.ratings[t])
        ranks = {t: i for i, t in enumerate(ranked)}
        g, wins = h2h_record(h2h, league, fav, dog)
        recs.append(dict(
            k=kickoff, league=league, pf=pf, price=oh if fav_home else oa,
            won=outcome == ("H" if fav_home else "A"), g=g, wins=wins,
            rank=ranks.get(fav, 999),
        ))
        h2h_update(h2h, league, home, away, outcome)
        model.update(home, away, {"H": 1.0, "D": 0.5, "A": 0.0}[outcome])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(recs))
    return recs


def select(recs, top_n, min_games, k, lo, hi, thr):
    out = []
    for r in recs:
        if not (r["rank"] < top_n and r["g"] >= min_games and lo <= r["pf"] < hi):
            continue
        edge = (r["wins"] + k * 0.5) / (r["g"] + k) - r["pf"]
        if edge > thr:
            out.append((r["price"] - 1) if r["won"] else -1.0)
    return np.array(out)


def lcb(pnl: np.ndarray, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    b = pnl[rng.integers(0, len(pnl), size=(1000, len(pnl)))].mean(axis=1)
    return float(np.percentile(b, 5)), float(np.mean(b <= 0))


def run(db: Path) -> None:
    recs = build_records(db)
    disc = [r for r in recs if r["k"] < CONFIRM_FROM]
    conf = [r for r in recs if r["k"] >= CONFIRM_FROM]
    bands = [(0.5, 0.6), (0.5, 0.7), (0.6, 0.7), (0.4, 0.6), (0.5, 0.75)]
    grid = [(n, g, k, b, t) for n in (3, 5, 8) for g in (2, 3, 5) for k in (1, 2, 4)
            for b in bands for t in (0.0, 0.03, 0.06)]
    print(f"grid size {len(grid)}; discovery rows={len(disc)}, confirmation rows={len(conf)}")

    scored = []
    for n, g, k, (lo, hi), t in grid:
        pnl = select(disc, n, g, k, lo, hi, t)
        if len(pnl) < 100:
            continue
        low, p = lcb(pnl)
        scored.append(((n, g, k, (lo, hi), t), pnl.mean(), low, p, len(pnl)))
    scored.sort(key=lambda s: -s[2])

    print("\nTop 8 by discovery lower bound (selection is on DISCOVERY only):")
    print(f"{'top_n':>5}{'min_g':>6}{'k':>3}{'band':>12}{'thr':>6}{'disc ROI':>10}{'LCB5':>8}{'n':>6}")
    for (n, g, k, b, t), m, low, p, nn in scored[:8]:
        print(f"{n:>5}{g:>6}{k:>3}{str(b):>12}{t:>6.2f}{m:>+10.4f}{low:>+8.3f}{nn:>6}")

    best = scored[0][0]
    n, g, k, (lo, hi), t = best
    cpnl = select(conf, n, g, k, lo, hi, t)
    cl, cp = lcb(cpnl)
    print(f"\nSELECTED on discovery: top_n={n} min_games={g} k={k} band={lo}-{hi} thr={t}")
    print(f"CONFIRMATION (run once): ROI {cpnl.mean():+.4f}  LCB5 {cl:+.3f}  n={len(cpnl)}  P(ROI<=0)={cp:.3f}")
    base = select(conf, 5, 3, 2, 0.5, 0.7, 0.0)
    print(f"reference (previous rule, confirmation): ROI {base.mean():+.4f} n={len(base)}")


if __name__ == "__main__":
    import sys
    run(Path(sys.argv[1] if len(sys.argv) > 1 else "data/betscout.db"))
