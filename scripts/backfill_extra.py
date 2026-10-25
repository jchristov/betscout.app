"""Backfill additional soccer leagues (Austrian Bundesliga) into data/matches.sqlite."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from betscout.espn import SOCCER_LEAGUES  # noqa: E402
from betscout.ingest import backfill  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "data"
WANTED = {"aut.1", "ger.1", "ita.1"}
YEARS = [2022, 2023, 2024, 2025]

if __name__ == "__main__":
    leagues = [lg for lg in SOCCER_LEAGUES if lg.key in WANTED]
    print(backfill(ROOT / "matches.sqlite", ROOT / "cache", YEARS, leagues, workers=8), flush=True)
