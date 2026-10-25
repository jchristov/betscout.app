"""Historical tests of bookmaker market inconsistencies (no forward data needed).

Each test is a fixed, pre-specified rule evaluated on the full history with a paired
bootstrap CI for flat-stake ROI. Nothing is fitted, so there is no in-sample tuning.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

OUT = {"H": 0, "D": 1, "A": 2}


@dataclass
class Bet:
    won: bool
    odds: float


def load(db: Path) -> list[dict]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM matches WHERE sport='soccer' AND outcome IS NOT NULL AND odds_home IS NOT NULL "
        "AND odds_dc_1x IS NOT NULL ORDER BY kickoff")]
    conn.close()
    return rows


def roi_ci(bets: list[Bet], n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float, int]:
    if not bets:
        return float("nan"), float("nan"), float("nan"), 0
    pnl = np.array([(b.odds - 1) if b.won else -1.0 for b in bets])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(pnl), size=(n_boot, len(pnl)))
    boots = pnl[idx].mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(pnl.mean()), float(lo), float(hi), len(bets)


def cross_market(rows: list[dict]) -> list[Bet]:
    """Rule: if the double-chance price implies a higher probability than the 1X2 pair does,
    back the double chance. Compares the 1X2-implied probability of the double-chance pair
    with the double-chance price (both de-vigged)."""
    bets = []
    for r in rows:
        inv1 = {k: 1 / r[c] for k, c in (("H", "odds_home"), ("D", "odds_draw"), ("A", "odds_away"))}
        s1 = sum(inv1.values())
        p1 = {k: v / s1 for k, v in inv1.items()}
        dc = {"1X": ("H", "D", r["odds_dc_1x"]), "X2": ("D", "A", r["odds_dc_x2"]), "12": ("H", "A", r["odds_dc_12"])}
        inv_dc = {k: 1 / v[2] for k, v in dc.items()}
        scale = 2 / sum(inv_dc.values())
        for k, (a, b, price) in dc.items():
            p_1x2 = p1[a] + p1[b]
            p_dc = inv_dc[k] * scale
            if p_dc - p_1x2 > 0.02:  # double chance looks underpriced vs the 1X2 pair
                won = r["outcome"] in (a, b)
                bets.append(Bet(won, price))
    return bets


def draw_by_odds(rows: list[dict]) -> list[tuple[str, float, float, int]]:
    """Rule per bin: back the draw when its market probability is in the bin. Reports realised draw rate vs implied."""
    bins = [(0.0, 0.22), (0.22, 0.26), (0.26, 0.30), (0.30, 1.0)]
    out = []
    for lo, hi in bins:
        sel = []
        for r in rows:
            inv = [1 / r["odds_home"], 1 / r["odds_draw"], 1 / r["odds_away"]]
            s = sum(inv)
            pd_ = inv[1] / s
            if lo <= pd_ < hi:
                sel.append((pd_, r["outcome"] == "D"))
        if sel:
            implied = np.mean([p for p, _ in sel])
            real = np.mean([w for _, w in sel])
            out.append((f"[{lo:.2f},{hi:.2f})", implied, real, len(sel)))
    return out


def totals_by_league(rows: list[dict]) -> list[tuple[str, float, float, int]]:
    """Over realised rate vs implied, per league, at each match's own posted totals line."""
    out = {}
    for r in rows:
        if r["odds_over"] is None or r["line_total"] is None:
            continue
        mo, mu = 1 / r["odds_over"], 1 / r["odds_under"]
        p_over = mo / (mo + mu)
        over = (r["home_score"] + r["away_score"]) > r["line_total"]
        out.setdefault(r["league"], []).append((p_over, over))
    res = []
    for lg, pairs in sorted(out.items()):
        res.append((lg, float(np.mean([p for p, _ in pairs])), float(np.mean([o for _, o in pairs])), len(pairs)))
    return res


def totals_bet_rule(rows: list[dict], threshold: float = 0.0) -> list[Bet]:
    """Pre-specified rule: back Over at each match's own posted line whenever the Over price
    is more than `threshold` above fair (de-vigged) value."""
    bets = []
    for r in rows:
        if r["odds_over"] is None or r["line_total"] is None:
            continue
        mo, mu = 1 / r["odds_over"], 1 / r["odds_under"]
        p_over = mo / (mo + mu)
        over = (r["home_score"] + r["away_score"]) > r["line_total"]
        if p_over * r["odds_over"] - 1 > threshold:
            bets.append(Bet(over, r["odds_over"]))
    return bets


def run(db: Path) -> None:
    rows = load(db)
    print(f"soccer matches with full 1X2 + double-chance prices: {len(rows)}\n")

    m, lo, hi, n = roi_ci(cross_market(rows))
    print(f"[1] cross-market: back double chance when 1X2-implied probability is >2pp below its price")
    print(f"    ROI {m:+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  bets={n}\n")

    print("[2] draw calibration by market-implied draw probability (implied vs realised draw rate)")
    for label, imp, real, n in draw_by_odds(rows):
        print(f"    bin {label}: implied {imp:.3f}  realised {real:.3f}  diff {real - imp:+.3f}  n={n}")
    print()

    print("[3] over/under calibration by league (own posted line) (implied vs realised over rate)")
    for lg, imp, real, n in totals_by_league(rows):
        print(f"    {lg:<16} implied {imp:.3f}  realised {real:.3f}  diff {real - imp:+.3f}  n={n}")
    print()

    for t in (0.0, 0.03):
        m, lo, hi, n = roi_ci(totals_bet_rule(rows, t))
        print(f"[4] totals: back Over 2.5 when EV > {t:.2f}  ROI {m:+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  bets={n}")


def totals_side_rule(rows: list[dict], side: str, threshold: float = 0.0) -> list[Bet]:
    """Back `side` ('over' or 'under') at each match's posted line when its price's EV exceeds `threshold`."""
    bets = []
    for r in rows:
        if r["odds_over"] is None or r["line_total"] is None:
            continue
        mo, mu = 1 / r["odds_over"], 1 / r["odds_under"]
        p_over = mo / (mo + mu)
        over = (r["home_score"] + r["away_score"]) > r["line_total"]
        if side == "over":
            p, price, won = p_over, r["odds_over"], over
        else:
            p, price, won = 1 - p_over, r["odds_under"], not over
        if p * price - 1 > threshold:
            bets.append(Bet(won, price))
    return bets
