"""Favourite head-to-head test: discovery vs confirmation split."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.favourites import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "matches.sqlite")
