"""Backfill the 2025-26 season (ESPN label 2025) end to end: the fresh, unused window for confirmation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sportdata_model.espn import SOCCER_LEAGUES  # noqa: E402
from sportdata_model.ingest import backfill  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "data"

if __name__ == "__main__":
    print(backfill(ROOT / "matches.sqlite", ROOT / "cache", [2025], SOCCER_LEAGUES, workers=8), flush=True)
