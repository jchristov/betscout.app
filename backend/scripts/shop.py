"""Cross-bookmaker line-shopping test on cached ESPN odds (no network)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "data").exists() else Path(__file__).resolve().parents[1]

from betscout.shop import run  # noqa: E402

if __name__ == "__main__":
    run(ROOT / "data" / "betscout.db", ROOT / "data" / "cache")
