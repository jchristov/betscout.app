"""Flat-stake betting check on the out-of-sample test set: bet where calibrated model beats market by a margin."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from betscout.models import TRAIN_FRAC, fit_calibrator, soccer_samples  # noqa: E402

DB = Path(__file__).resolve().parents[1] / "data" / "betscout.db"
OUT = {"H": 0, "D": 1, "A": 2}

samples = [s for s in soccer_samples(DB) if s.market]
cut = int(len(samples) * TRAIN_FRAC)
train, test = samples[:cut], samples[cut:]
predict = fit_calibrator(train, use_market=True)

for margin in (0.0, 0.03, 0.05, 0.08):
    stakes, profit = 0, 0.0
    for s in test:
        p = predict(s)
        for i, name in enumerate(("H", "D", "A")):
            ev = p[i] * s.odds[i] - 1
            if ev > margin:
                stakes += 1
                profit += (s.odds[i] - 1) if s.outcome == name else -1
    roi = profit / stakes if stakes else float("nan")
    print(f"margin>{margin:.2f}: bets={stakes:5d}  ROI={roi:+.4f}  profit={profit:+.1f} units")
