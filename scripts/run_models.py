"""Run out-of-sample Elo and market-calibration evaluation for soccer and tennis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sportdata_model.models import evaluate, fmt, soccer_samples, tennis_samples  # noqa: E402

DB = Path(__file__).resolve().parents[1] / "data" / "matches.sqlite"

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("soccer", "both"):
        print("SOCCER (1X2, all leagues, test = later half)")
        print(fmt(evaluate(soccer_samples(DB))))
    if which in ("tennis", "both"):
        print("\nTENNIS (win probability, test = later half)")
        print(fmt(evaluate(tennis_samples(DB))))
