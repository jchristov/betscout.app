"""Walk-forward evaluation: each match is predicted using only results dated strictly before it."""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Row:
    kickoff: str
    league: str
    home: str
    away: str
    outcome: str
    odds_home: float | None
    odds_draw: float | None
    odds_away: float | None
    line_total: float | None
    odds_over: float | None
    odds_under: float | None
    odds_dc_1x: float | None
    odds_dc_x2: float | None
    odds_dc_12: float | None
    home_score: float | None
    away_score: float | None


def load(db: Path, sport: str | None = None) -> list[Row]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM matches WHERE outcome IS NOT NULL"
    args: tuple = ()
    if sport:
        q += " AND sport = ?"
        args = (sport,)
    rows = [Row(**{k: r[k] for k in Row.__dataclass_fields__}) for r in conn.execute(q + " ORDER BY kickoff", args)]
    conn.close()
    return rows


def devig_1x2(h: float, d: float, a: float) -> tuple[float, float, float]:
    """Proportional de-vig of decimal 1X2 prices."""
    ih, idr, ia = 1 / h, 1 / d, 1 / a
    s = ih + idr + ia
    return ih / s, idr / s, ia / s


def log_loss(p_outcome: float) -> float:
    return -math.log(max(min(p_outcome, 1 - 1e-12), 1e-12))


@dataclass
class Scores:
    n: int = 0
    total: float = 0.0

    def add(self, p: float) -> None:
        self.n += 1
        self.total += log_loss(p)

    @property
    def mean(self) -> float:
        return self.total / self.n if self.n else float("nan")


@dataclass
class Report:
    scores: dict[str, Scores] = field(default_factory=dict)

    def add(self, name: str, p: float) -> None:
        self.scores.setdefault(name, Scores()).add(p)

    def table(self) -> str:
        lines = [f"{'model':<28}{'n':>6}{'log_loss':>12}"]
        for k, s in sorted(self.scores.items(), key=lambda kv: kv[1].mean):
            lines.append(f"{k:<28}{s.n:>6}{s.mean:>12.4f}")
        return "\n".join(lines)
