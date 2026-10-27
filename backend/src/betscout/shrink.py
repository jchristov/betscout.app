"""Empirical-Bayes shrinkage of ROI across market side x league groups.

Each group's discovery ROI is an noisy estimate. We estimate the between-group variance (tau^2) by
method of moments, then shrink each group toward the pooled mean by w = tau^2 / (tau^2 + se^2).
Groups are selected only by their SHRUNK posterior mean on discovery, and checked once on the
newest window (Aug-Oct 2026), which no earlier analysis used.

Single-bet ROI variance is approximated by Var(pnl) = E[pnl^2] - E[pnl]^2 per group.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from .sweep import load, sides

FRESH_FROM = "2026-08-01"
DISC_TO = "2025-07-01"


def pnl(price: float, won: bool) -> float:
    return (price - 1) if won else -1.0


def groups(rows: list[dict], window) -> dict[tuple[str, str], list[float]]:
    out: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        if not window(r["kickoff"]):
            continue
        for side, price, won in sides(r):
            out[(side, r["league"])].append(pnl(price, won))
    return out


def estimate(disc: dict) -> dict[tuple[str, str], tuple[float, float, int]]:
    """Return (mean, se^2, n) per group from discovery."""
    stats = {}
    for k, v in disc.items():
        a = np.array(v)
        if len(a) >= 30:
            stats[k] = (a.mean(), a.var(ddof=1) / len(a), len(a))
    return stats


def shrink(stats: dict) -> dict[tuple[str, str], float]:
    means = np.array([m for m, _, _ in stats.values()])
    ses = np.array([s for _, s, _ in stats.values()])
    grand = float(np.average(means, weights=1 / ses))
    tau2 = max(float(np.var(means, ddof=1) - np.mean(ses)), 1e-6)
    out = {}
    for k, (m, s2, _) in stats.items():
        w = tau2 / (tau2 + s2)
        out[k] = grand + w * (m - grand)
    return out, grand, tau2


def run(db: Path, top: int = 3, min_post: float = 0.02) -> None:
    rows = load(db)
    disc_rows = [r for r in rows if r["kickoff"] < DISC_TO]
    fresh_rows = [r for r in rows if r["kickoff"] >= FRESH_FROM]
    disc = groups(disc_rows, lambda k: True)
    stats = estimate(disc)
    post, grand, tau2 = shrink(stats)
    print(f"discovery groups: {len(stats)}  pooled mean ROI {grand:+.4f}  between-group tau {np.sqrt(tau2):.4f}")

    chosen = sorted(post, key=lambda k: -post[k])[:top]
    fresh = groups(fresh_rows, lambda k: True)
    print(f"\nselected on discovery (shrunk ROI), checked once on {FRESH_FROM}+:")
    for k in chosen:
        f = np.array(fresh.get(k, []))
        fr = f"{f.mean():+.4f} (n={len(f)})" if len(f) else "no fresh bets"
        print(f"  {k[0]:<6} {k[1]:<12} disc raw {stats[k][0]:+.4f} shrunk {post[k]:+.4f}  fresh {fr}")

    all_fresh = [x for k in stats for x in fresh.get(k, [])]
    if all_fresh:
        print(f"\nall groups pooled on fresh window: ROI {np.mean(all_fresh):+.4f} (n={len(all_fresh)})")


if __name__ == "__main__":
    import sys
    run(Path(sys.argv[1] if len(sys.argv) > 1 else "data/betscout.db"))
