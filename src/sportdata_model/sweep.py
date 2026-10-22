"""Pre-registered sweep of structural market biases (no model, flat stakes at the book's price).

Every hypothesis is a fixed (market side, grouping) pair. A group is a candidate edge only if its
flat ROI at the posted price is positive in DISCOVERY (kickoff < 2025-07-01) AND in CONFIRMATION
(kickoff >= 2025-07-01), with a one-sided bootstrap p-value on confirmation. Adjustment across the
family is Benjamini-Hochberg FDR at 10% by default (Holm is available via method="holm").

Per-group tests are underpowered at this sample size, so `pooled_test` gives a single pre-specified
test over all bets of one side, which can detect edges per-group tests miss.

Because betting at the book price always carries the overround, a candidate must beat the margin.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np

from .edges import holm

CONFIRM_FROM = "2025-07-01"


def bh(pvals: dict[str, float]) -> dict[str, float]:
    """Benjamini-Hochberg adjusted p-values (controls the false discovery rate, not family-wise error)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 1.0
    for rank in range(m, 0, -1):
        k, p = items[rank - 1]
        running = min(running, p * m / rank)
        adj[k] = running
    return adj


def adjust(pvals: dict[str, float], method: str = "bh") -> dict[str, float]:
    return bh(pvals) if method == "bh" else holm(pvals)


def load(db: Path) -> list[dict]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM matches WHERE sport='soccer' AND outcome IS NOT NULL AND home_score IS NOT NULL "
        "AND odds_home IS NOT NULL AND odds_draw IS NOT NULL AND odds_away IS NOT NULL ORDER BY kickoff")]
    conn.close()
    for r in rows:
        dt = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00"))
        r["weekday"] = dt.strftime("%a")
        r["hour"] = dt.hour
        r["month"] = dt.month
    return rows


def sides(r: dict):
    """Yield (name, price, won) for every single selection with a posted price."""
    yield "H", r["odds_home"], r["outcome"] == "H"
    yield "D", r["odds_draw"], r["outcome"] == "D"
    yield "A", r["odds_away"], r["outcome"] == "A"
    if r["odds_over"] and r["odds_under"] and r["line_total"] is not None:
        over = (r["home_score"] + r["away_score"]) > r["line_total"]
        yield "OVER", r["odds_over"], over
        yield "UNDER", r["odds_under"], not over


def pnl_of(sel: list[tuple[float, bool]]) -> np.ndarray:
    return np.array([(p - 1) if w else -1.0 for p, w in sel])


def boot_p(pnl: np.ndarray, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    means = pnl[rng.integers(0, len(pnl), size=(4000, len(pnl)))].mean(axis=1)
    return float((means <= 0).mean())


def family(rows: list[dict]):
    """Hypothesis = (side, dimension, value). Dimensions: league, weekday, hour, month."""
    keys = {}
    for r in rows:
        for side, price, won in sides(r):
            for dim in ("league", "weekday", "hour", "month"):
                val = r[dim]
                keys.setdefault((side, dim, val), []).append((price, won, r["kickoff"]))
    return keys


def run(db: Path, min_n: int = 150, method: str = "bh", alpha: float = 0.10) -> None:
    rows = load(db)
    fam = family(rows)
    tests = []
    for (side, dim, val), items in fam.items():
        disc = [(p, w) for p, w, k in items if k < CONFIRM_FROM]
        conf = [(p, w) for p, w, k in items if k >= CONFIRM_FROM]
        if len(disc) < min_n or len(conf) < min_n:
            continue
        d = pnl_of(disc)
        c = pnl_of(conf)
        tests.append({"key": f"{side}|{dim}={val}", "d_roi": d.mean(), "c_roi": c.mean(),
                      "c_n": len(c), "p": boot_p(c), "d_n": len(d)})

    print(f"hypotheses with enough data in both windows: {len(tests)}")
    adj = adjust({t["key"]: t["p"] for t in tests}, method)
    for t in tests:
        t["holm"] = adj[t["key"]]
    tests.sort(key=lambda t: t["holm"])
    print(f"\n{'hypothesis':<26}{'disc ROI':>10}{'conf ROI':>10}{'n_c':>7}{'p':>8}{'holm':>8}  both>0")
    for t in tests[:25]:
        both = t["d_roi"] > 0 and t["c_roi"] > 0
        print(f"{t['key']:<26}{t['d_roi']:>+10.4f}{t['c_roi']:>+10.4f}{t['c_n']:>7}{t['p']:>8.3f}{t['holm']:>8.3f}  {both}")
    survivors = [t for t in tests if t["holm"] < alpha and t["d_roi"] > 0]
    print(f"correction: {method}, threshold {alpha}")
    print(f"\nsurvivors (adjusted p < {alpha} and discovery ROI > 0): {len(survivors)}")
    for t in survivors:
        print(f"  {t['key']}: conf ROI {t['c_roi']:+.4f}, n={t['c_n']}, adj p {t['holm']:.3f}")


if __name__ == "__main__":
    import sys
    run(Path(sys.argv[1] if len(sys.argv) > 1 else "data/matches.sqlite"))


def pooled_test(db: Path, side: str = "UNDER") -> dict[str, float]:
    """One pre-specified test over every bet on `side`, split by kickoff window."""
    rows = load(db)
    disc, conf = [], []
    for r in rows:
        for s, price, won in sides(r):
            if s == side:
                (disc if r["kickoff"] < CONFIRM_FROM else conf).append((price, won))
    pd_, pc_ = pnl_of(disc), pnl_of(conf)
    return {"disc_roi": float(pd_.mean()), "disc_n": len(disc), "conf_roi": float(pc_.mean()),
            "conf_n": len(conf), "p": boot_p(pc_)}
