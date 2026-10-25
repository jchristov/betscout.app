"""Run out-of-sample market-residual experiments for soccer 1X2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from betscout.experiments import run  # noqa: E402

DB = Path(__file__).resolve().parents[1] / "data" / "matches.sqlite"

if __name__ == "__main__":
    run(DB)
