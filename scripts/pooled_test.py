"""Pooled one-test check for a single market side (more powerful than per-league slicing)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.sweep import pooled_test  # noqa: E402

if __name__ == "__main__":
    r = pooled_test(ROOT / "data" / "matches.sqlite", "UNDER")
    print(f"pooled UNDER: disc ROI {r['disc_roi']:+.4f} (n={r['disc_n']})  "
          f"conf ROI {r['conf_roi']:+.4f} (n={r['conf_n']})  one-sided p={r['p']:.4f}")
