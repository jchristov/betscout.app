"""Frozen-rule confirmation on 2026 matches, never seen when the Under rule was chosen.

Calibrator is fitted only on matches before 2026. Rule (fixed): bet Under when the calibrated
probability times the Under price exceeds 1 (EV > 0). Evaluated on 2026 kickoffs only.
"""

import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.models import logit  # noqa: E402
from betscout.totals_test import build, ci  # noqa: E402

rows = build(ROOT / "data" / "matches.sqlite")
train = [r for r in rows if r.year < "2026"]
test = [r for r in rows if r.year == "2026"]
print(f"fit on {len(train)} pre-2026 matches; frozen test on {len(test)} 2026 matches")

cal = LogisticRegression(C=1.0).fit(
    np.array([[logit(r.p_over_model)] for r in train]), np.array([r.over for r in train]))


def p_over(r) -> float:
    return cal.predict_proba([[logit(r.p_over_model)]])[0, 1]


for side in ("under", "over"):
    bs = []
    for r in test:
        p = p_over(r)
        q, price, won = (1 - p, r.odds_under, not r.over) if side == "under" else (p, r.odds_over, r.over)
        if q * price - 1 > 0:
            bs.append((won, price))
    m, lo, hi, n = ci(bs)
    print(f"{side:<5} EV>0: ROI {m:+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  bets={n}")

print(f"2026 realised over rate: {np.mean([r.over for r in test]):.3f}  book implied: {np.mean([r.p_over_book for r in test]):.3f}")
