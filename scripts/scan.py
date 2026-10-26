"""Systematic candidate scan with discovery / confirmation / fresh windows."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.scan import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "betscout.db")
