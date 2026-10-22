"""Empirical-Bayes shrinkage edge search with a single fresh-window check."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.shrink import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "matches.sqlite")
