"""Line-shopping from cached ESPN summaries: how much do bookmakers disagree, and would the best price have paid?

Only uses cached responses (no network). Each match contributes one row per bookmaker that posts a full 1X2.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

from .ingest import fractional_to_decimal


def book_prices(cache: Path, event_id: str, league: str) -> dict[str, tuple[float, float, float]]:
    f = cache / f"sum_{league}_{event_id}.json"
    if not f.exists():
        return {}
    out = {}
    for o in json.loads(f.read_text()).get("odds") or []:
        tos = (o.get("bettingOdds") or {}).get("teamOdds") or {}
        h = fractional_to_decimal((tos.get("preMatchFullTimeResultHome") or {}).get("value"))
        d = fractional_to_decimal((tos.get("preMatchFullTimeResultDraw") or {}).get("value"))
        a = fractional_to_decimal((tos.get("preMatchFullTimeResultAway") or {}).get("value"))
        if h and d and a:
            out[(o.get("provider") or {}).get("name", "?")] = (h, d, a)
    return out


def run(db: Path, cache: Path, min_books: int = 3) -> None:
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT event_id, league, outcome FROM matches WHERE sport='soccer' AND outcome IS NOT NULL"
    ).fetchall()
    conn.close()
    idx = {"H": 0, "D": 1, "A": 2}
    n_matches, pnl_best, pnl_avg, spreads, n_bets = 0, [], [], [], 0
    for event_id, league, outcome in rows:
        books = book_prices(cache, event_id, league)
        if len(books) < min_books:
            continue
        n_matches += 1
        mat = np.array(list(books.values()))  # books x outcomes, decimal
        inv = 1 / mat
        fair = inv / inv.sum(axis=1, keepdims=True)  # per-book de-vig
        consensus = fair.mean(axis=0)  # cross-book consensus probability
        best = mat.max(axis=0)  # best available price per outcome
        i = idx[outcome]
        # Bet the outcome whose best price beats consensus fair value by the most (rule fixed in advance)
        edge = best * consensus - 1
        k = int(np.argmax(edge))
        won = k == i
        pnl_best.append((best[k] - 1) if won else -1.0)
        spreads.append(float(np.max(mat[:, k]) / np.min(mat[:, k]) - 1))
        n_bets += 1
    if not pnl_best:
        print("no matches with enough cached books")
        return
    arr = np.array(pnl_best)
    rng = np.random.default_rng(0)
    boots = arr[rng.integers(0, len(arr), size=(2000, len(arr)))].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"matches with >= {min_books} cached books: {n_matches}")
    print(f"median best-vs-worst price spread on the bet: {np.median(spreads):.1%}")
    print(f"best-price flat-stake ROI on the consensus-edge pick: {arr.mean():+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  bets={n_bets}")
