"""Tune the favourite H2H lead on discovery data; report one confirmation run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "data").exists() else Path(__file__).resolve().parents[1]

from betscout.h2h_tune import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "betscout.db")
