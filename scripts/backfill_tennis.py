"""Backfill ATP and WTA singles results into data/matches.sqlite."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from betscout.espn import TENNIS_LEAGUES  # noqa: E402
from betscout.ingest import backfill  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "data"
YEARS = [2022, 2023, 2024, 2025]

if __name__ == "__main__":
    print(backfill(ROOT / "matches.sqlite", ROOT / "cache", YEARS, TENNIS_LEAGUES, workers=8), flush=True)
