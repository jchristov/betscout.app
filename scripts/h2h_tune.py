"""Tune the favourite H2H lead on discovery data; report one confirmation run."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.h2h_tune import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "matches.sqlite")
