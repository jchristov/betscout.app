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


_BASE_POISSON_CACHE: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}


def _get_base_grid_tensors(max_goals: int = MAX_GOALS) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cached = _BASE_POISSON_CACHE.get(max_goals)
    if cached is not None:
        return cached
    lams = np.arange(0.2, 3.6, 0.1, dtype=np.float64)
    k = np.arange(max_goals + 1, dtype=np.float64)
    facts = np.array([math.factorial(int(x)) for x in k], dtype=np.float64)
    # P(X=k | lam) shape: (N_lam, max_goals+1)
    pmf = np.exp(-lams[:, None]) * (lams[:, None] ** k[None, :]) / facts[None, :]
    # Outer product across all (lam, mu) pairs -> shape (N_lam, N_mu, max_goals+1, max_goals+1)
    base_grids = pmf[:, None, :, None] * pmf[None, :, None, :]
    ii, jj = np.indices((max_goals + 1, max_goals + 1))
    res = (lams, base_grids, ii > jj, ii == jj, ii < jj)
    _BASE_POISSON_CACHE[max_goals] = res
    return res


def fit_rates(total_goals_line: float, home_p: float, away_p: float, draw_p: float,
              rho: float = -0.1) -> tuple[float, float]:
    """Solve (lambda, mu) so the grid's 1X2 best matches the blended market probabilities.

    Vectorised over the 34x34 (lambda, mu) grid (~100x faster than nested Python loops)."""
    lams, base_grids, mask_h, mask_d, mask_a = _get_base_grid_tensors(MAX_GOALS)
    grids = base_grids.copy()
    lam_grid = lams[:, None]
    mu_grid = lams[None, :]
    grids[:, :, 0, 0] *= (1.0 - lam_grid * mu_grid * rho)
    grids[:, :, 0, 1] *= (1.0 + lam_grid * rho)
    grids[:, :, 1, 0] *= (1.0 + mu_grid * rho)
    grids[:, :, 1, 1] *= (1.0 - rho)
    norm = grids.sum(axis=(2, 3), keepdims=True)
    grids /= norm

    ph = grids[:, :, mask_h].sum(axis=-1)
    pd = grids[:, :, mask_d].sum(axis=-1)
    pa = grids[:, :, mask_a].sum(axis=-1)

    err = (ph - home_p) ** 2 + (pd - draw_p) ** 2 + (pa - away_p) ** 2
    if total_goals_line is not None and total_goals_line > 0:
        err += 0.25 * ((lam_grid + mu_grid - total_goals_line) ** 2) / (total_goals_line ** 2)

    idx = int(np.argmin(err))
    i_best, j_best = divmod(idx, len(lams))
    return float(lams[i_best]), float(lams[j_best])
