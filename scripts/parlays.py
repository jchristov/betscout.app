"""Accumulator (combo) test on soccer legs: discovery-tuned, confirmation-run-once."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.parlays import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "betscout.db")
