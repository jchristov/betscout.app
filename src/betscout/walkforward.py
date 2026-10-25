"""Walk-forward soccer evaluation of 1X2 / double chance / over-under / exact score.

For each match the model is fitted only on matches strictly before its kickoff.
Team strengths are attack/defence rates estimated by a running average of
goals per game, shrunk toward the league mean (no look-ahead)."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from .evaluate import Report, devig_1x2
from .goals import markets, score_grid


def _strength(hist: dict, team: str, league_mean: float, k: float = 8.0) -> tuple[float, float]:
    """Shrunk goals-for and goals-against rates (per game) for a team."""
    gf, ga, n = hist[team]
    if n == 0:
        return league_mean, league_mean
    return (gf + k * league_mean) / (n + k), (ga + k * league_mean) / (n + k)


def run(db: Path, league: str | None = None, min_history: int = 5) -> Report:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM matches WHERE outcome IS NOT NULL AND sport='soccer'"
    args: tuple = ()
    if league:
        q += " AND league = ?"
        args = (league,)
    rows = list(conn.execute(q + " ORDER BY kickoff", args))
    conn.close()

    report = Report()
    hist: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    league_goals = [0.0, 0]
    seen_for_league: dict[str, int] = defaultdict(int)

    for r in rows:
        hs, as_ = r["home_score"], r["away_score"]
        if hs is None or as_ is None:
            continue
        lg_mean = league_goals[0] / league_goals[1] if league_goals[1] else 1.35
        h_key, a_key = (r["league"], r["home"]), (r["league"], r["away"])
        ready = min(hist[h_key][2], hist[a_key][2]) >= min_history and r["odds_home"]
        if ready:
            hgf, hga = _strength(hist, h_key, lg_mean)
            agf, aga = _strength(hist, a_key, lg_mean)
            lam = hgf * aga / lg_mean
            mu = agf * hga / lg_mean
            grid = score_grid(lam, mu)
            m = markets(grid, r["line_total"])
            ph, pd_, pa = devig_1x2(r["odds_home"], r["odds_draw"], r["odds_away"])
            outcome = r["outcome"]
            idx = {"H": 0, "D": 1, "A": 2}[outcome]
            report.add("market 1X2", (ph, pd_, pa)[idx])
            report.add("poisson 1X2", (m["home"], m["draw"], m["away"])[idx])
            blend = [0.5 * a + 0.5 * b for a, b in zip((ph, pd_, pa), (m["home"], m["draw"], m["away"]))]
            report.add("blend 1X2 (50/50)", blend[idx])
            if r["odds_dc_1x"] and r["odds_dc_x2"] and r["odds_dc_12"]:
                # Double-chance outcomes that contain the realised result.
                dc_hit = {"1X": outcome in ("H", "D"), "X2": outcome in ("D", "A"), "12": outcome in ("H", "A")}
                dc_odds = {"1X": r["odds_dc_1x"], "X2": r["odds_dc_x2"], "12": r["odds_dc_12"]}
                # Each double-chance event covers two of the three outcomes, so the fair
                # probabilities sum to 2, not 1: scale by 2 / overround to remove the margin.
                inv = {k: 1 / v for k, v in dc_odds.items()}
                scale = 2 / sum(inv.values())
                dc_model = {"1X": m["dc_1x"], "X2": m["dc_x2"], "12": m["dc_12"]}
                for k in ("1X", "X2", "12"):
                    p_m = dc_model[k]
                    p_k = inv[k] * scale
                    report.add("poisson double chance", p_m if dc_hit[k] else 1 - p_m)
                    report.add("market double chance", p_k if dc_hit[k] else 1 - p_k)
            if r["line_total"] is not None:
                total = int(hs + as_)
                over = total > r["line_total"]
                p_over = m["over"]
                report.add("poisson over/under", p_over if over else 1 - p_over)
                if r["odds_over"] and r["odds_under"]:
                    mo, mu_ = 1 / r["odds_over"], 1 / r["odds_under"]
                    p_mkt_over = mo / (mo + mu_)
                    report.add("market over/under", p_mkt_over if over else 1 - p_mkt_over)
            report.add("exact score", float(grid[min(int(hs), 10), min(int(as_), 10)]) if hs <= 10 and as_ <= 10 else 1e-6)

        # Update history after prediction (no look-ahead).
        hist[h_key][0] += hs; hist[h_key][1] += as_; hist[h_key][2] += 1
        hist[a_key][0] += as_; hist[a_key][1] += hs; hist[a_key][2] += 1
        league_goals[0] += hs + as_; league_goals[1] += 2
    conn.close()
    return report
