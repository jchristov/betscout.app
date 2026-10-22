"""Point-in-time Elo ratings. Predict first, then update with the result."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


def expected(ra: float, rb: float, home_adv: float = 0.0) -> float:
    """Probability that A beats B (draws count as half) given ratings."""
    return 1.0 / (1.0 + 10 ** ((rb - ra - home_adv) / 400.0))


@dataclass
class Elo:
    k: float = 20.0
    base: float = 1500.0
    home_adv: float = 60.0
    ratings: dict = None

    def __post_init__(self) -> None:
        self.ratings = defaultdict(lambda: self.base)

    def p_home_win_or_draw_free(self, home: str, away: str) -> float:
        """P(home beats away) ignoring draws (draws count half)."""
        return expected(self.ratings[home], self.ratings[away], self.home_adv)

    def update(self, home: str, away: str, score_home: float) -> None:
        """score_home in {1 win, 0.5 draw, 0 loss} from the home side."""
        e = self.p_home_win_or_draw_free(home, away)
        delta = self.k * (score_home - e)
        self.ratings[home] += delta
        self.ratings[away] -= delta
