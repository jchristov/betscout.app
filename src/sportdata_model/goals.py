"""Independent-Poisson goal model with Dixon-Coles low-score correction.

Produces a joint scoreline grid per match. Every market (1X2, double chance,
over/under, exact score) is derived from the same grid, so they stay consistent.
"""

from __future__ import annotations

import math

import numpy as np

MAX_GOALS = 10


def _tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    if x == 0 and y == 0:
        return 1 - lam * mu * rho
    if x == 0 and y == 1:
        return 1 + lam * rho
    if x == 1 and y == 0:
        return 1 + mu * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def score_grid(lam: float, mu: float, rho: float = -0.1, max_goals: int = MAX_GOALS) -> np.ndarray:
    """P(home=i, away=j) for i, j in [0, max_goals], normalised to sum to 1."""
    ph = np.array([math.exp(-lam) * lam**i / math.factorial(i) for i in range(max_goals + 1)])
    pa = np.array([math.exp(-mu) * mu**j / math.factorial(j) for j in range(max_goals + 1)])
    grid = np.outer(ph, pa)
    grid[0, 0] *= _tau(0, 0, lam, mu, rho)
    grid[0, 1] *= _tau(0, 1, lam, mu, rho)
    grid[1, 0] *= _tau(1, 0, lam, mu, rho)
    grid[1, 1] *= _tau(1, 1, lam, mu, rho)
    return grid / grid.sum()


def markets(grid: np.ndarray, line: float | None = None) -> dict[str, float]:
    """Derive market probabilities from a scoreline grid."""
    n = grid.shape[0]
    i, j = np.indices((n, n))
    total = i + j
    out = {
        "home": float(grid[i > j].sum()),
        "draw": float(grid[i == j].sum()),
        "away": float(grid[i < j].sum()),
        "dc_1x": float(grid[i >= j].sum()),
        "dc_x2": float(grid[i <= j].sum()),
        "dc_12": float(grid[i != j].sum()),
        "btts": float(grid[(i > 0) & (j > 0)].sum()),
    }
    if line is not None:
        out["over"] = float(grid[total > line].sum())
        out["under"] = float(grid[total < line].sum())
    return out


def exact_score(grid: np.ndarray, home: int, away: int) -> float:
    return float(grid[home, away]) if home < grid.shape[0] and away < grid.shape[0] else 0.0


def fit_rates(total_goals_line: float, home_p: float, away_p: float, draw_p: float,
              rho: float = -0.1) -> tuple[float, float]:
    """Solve (lambda, mu) so the grid's 1X2 best matches the blended market probabilities.

    Simple grid search over the implied expected goals (lambda, mu) minimising squared 1X2 error,
    with the total-goals line as a soft prior on lambda + mu."""
    best, best_err = (1.3, 1.1), float("inf")
    for lam in np.arange(0.2, 3.6, 0.1):
        for mu in np.arange(0.2, 3.6, 0.1):
            m = markets(score_grid(lam, mu, rho))
            err = (m["home"] - home_p) ** 2 + (m["draw"] - draw_p) ** 2 + (m["away"] - away_p) ** 2
            if total_goals_line is not None:
                err += 0.25 * (lam + mu - total_goals_line) ** 2 / (total_goals_line**2)
            if err < best_err:
                best, best_err = (float(lam), float(mu)), err
    return best
