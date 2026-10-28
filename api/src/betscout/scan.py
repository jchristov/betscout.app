"""Systematic candidate scan with a fixed three-window protocol.

Candidates: side (H, D, A, OVER, UNDER) x league x kickoff-hour band x price band. Price bands and
hour bands are fixed in advance. Each candidate's flat ROI at posted price is computed per window.

Windows (fixed):
  discovery    kickoff < 2025-07-01
  confirmation 2025-07-01 .. 2026-07-31
  fresh        kickoff >= 2026-08-01 (used once, for the final shortlist only)

Shortlist rule (fixed before running): discovery ROI > 0 AND discovery n >= 150 AND
confirmation ROI > 0. A candidate on the shortlist is then tested once on fresh data.
Reported with Benjamini-Hochberg across the full candidate family, so the penalty for scale is visible.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

from .shrink import FRESH_FROM  # noqa: F401  (same boundary)
from .sweep import boot_p, load, pnl_of, sides, CONFIRM_FROM, bh

CONF_TO = FRESH_FROM
PRICE_BANDS = [(1.0, 1.8), (1.8, 2.5), (2.5, 4.0), (4.0, 99.0)]
HOUR_BANDS = [(0, 15), (15, 18), (18, 24)]


def windows(kickoff: str) -> str:
    if kickoff < CONFIRM_FROM:
        return "disc"
    if kickoff < CONF_TO:
        return "conf"
    return "fresh"


def candidates(rows: list[dict]):
    cand: dict[tuple, dict[str, list]] = {}
    for r in rows:
        hour = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00")).hour
        hb = next(i for i, (lo, hi) in enumerate(HOUR_BANDS) if lo <= hour < hi)
        for side, price, won in sides(r):
            pb = next((i for i, (lo, hi) in enumerate(PRICE_BANDS) if lo <= price < hi), None)
            if pb is None:
                continue
            for key in ((side, r["league"], hb, pb), (side, "ALL", hb, pb)):
                cand.setdefault(key, {"disc": [], "conf": [], "fresh": []})[windows(r["kickoff"])].append(
                    ((price - 1) if won else -1.0))
    return cand


def run(db: Path) -> None:
    rows = load(db)
    cand = candidates(rows)
    shortlist, pvals = [], {}
    for key, w in cand.items():
        d, c = np.array(w["disc"]), np.array(w["conf"])
        if len(d) < 150 or len(c) < 50:
            continue
        pvals[key] = boot_p(c)
        if d.mean() > 0 and c.mean() > 0:
            shortlist.append(key)
    adj = bh(pvals) if pvals else {}
    print(f"candidates tested on confirmation: {len(pvals)}  shortlisted (disc>0, conf>0): {len(shortlist)}")
    print(f"{'candidate':<40}{'disc ROI':>10}{'conf ROI':>10}{'n_c':>6}{'p':>7}{'BH':>7}  fresh ROI (n)")
    for key in sorted(shortlist, key=lambda k: adj[k]):
        w = cand[key]
        d, c, f = np.array(w["disc"]), np.array(w["conf"]), np.array(w["fresh"])
        fr = f"{f.mean():+.3f} ({len(f)})" if len(f) else "no fresh bets"
        name = f"{key[0]}|{key[1]}|h{HOUR_BANDS[key[2]][0]}-{HOUR_BANDS[key[2]][1]}|p{PRICE_BANDS[key[3]][0]}-{PRICE_BANDS[key[3]][1]}"
        print(f"{name:<40}{d.mean():>+10.3f}{c.mean():>+10.3f}{len(c):>6}{pvals[key]:>7.3f}{adj[key]:>7.3f}  {fr}")


if __name__ == "__main__":
    import sys
    run(Path(sys.argv[1] if len(sys.argv) > 1 else "data/betscout.db"))
