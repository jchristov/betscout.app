"""Systematic soccer edge search with discovery/confirmation split and Holm correction."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.edges import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "matches.sqlite")
