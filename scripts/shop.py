"""Cross-bookmaker line-shopping test on cached ESPN odds (no network)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.shop import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "matches.sqlite", ROOT / "data" / "cache")
