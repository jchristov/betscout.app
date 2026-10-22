"""Run the multi-factor invariant soccer edge evaluation and enriched tennis surface/game model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.quant_edges import (  # noqa: E402
    ALL_SOCCER_LEAGUES,
    BIG5_LEAGUES,
    evaluate_invariant_soccer_composite,
    evaluate_tennis_surface_game_model,
    evaluate_us_major_sports_composite,
)

if __name__ == "__main__":
    db = ROOT / "data" / "matches.sqlite"
    print("=== 7-Factor Orthogonal Invariant Soccer Composite (Big-5 European Leagues) ===")
    res_b5 = evaluate_invariant_soccer_composite(db, leagues=BIG5_LEAGUES)
    for k, v in res_b5.items():
        lo, hi = v["post_ci"]
        print(
            f"  {k:<10} | Disc: {v['disc_roi']:+.4f} (n={v['disc_n']:<4}) | "
            f"Conf: {v['conf_roi']:+.4f} (n={v['conf_n']:<3}) | Fresh: {v['fresh_roi']:+.4f} (n={v['fresh_n']:<2}) | "
            f"Post25+(Best): {v['post_roi_best']:+.4f} [{lo:+.3f},{hi:+.3f}] p={v['post_p']:.4f} "
            f"(Primary: {v['post_roi_pri']:+.4f}) | All: {v['all_roi_best']:+.4f} (n={v['all_n']})"
        )

    print("\n=== 7-Factor Orthogonal Invariant Soccer Composite (All 6 Leagues incl. Austria) ===")
    res_all = evaluate_invariant_soccer_composite(db, leagues=ALL_SOCCER_LEAGUES)
    for k, v in res_all.items():
        lo, hi = v["post_ci"]
        print(
            f"  {k:<10} | Disc: {v['disc_roi']:+.4f} (n={v['disc_n']:<4}) | "
            f"Conf: {v['conf_roi']:+.4f} (n={v['conf_n']:<3}) | Fresh: {v['fresh_roi']:+.4f} (n={v['fresh_n']:<2}) | "
            f"Post25+(Best): {v['post_roi_best']:+.4f} [{lo:+.3f},{hi:+.3f}] p={v['post_p']:.4f} "
            f"(Primary: {v['post_roi_pri']:+.4f}) | All: {v['all_roi_best']:+.4f} (n={v['all_n']})"
        )

    print("\n=== Enriched Tennis Surface-Elo + Game-Dominance Model (Out-of-Sample) ===")
    res_tn = evaluate_tennis_surface_game_model(db)
    for tour, m in res_tn.items():
        print(
            f"  {tour.upper():<4} (n={int(m['n_test'])}) | Base Elo LL={m['base_log_loss']:.4f} (Acc={m['base_acc']:.2%}) -> "
            f"Rich 7-Feat LL={m['rich_log_loss']:.4f} (Acc={m['rich_acc']:.2%}, High-Conf >=70% Acc={m['high_conf_acc']:.2%} on n={int(m['high_conf_n'])})"
        )

    print("\n=== 7-Factor Boxscore + Rest/B2B + Rebound US Major Sports Composite (Top 15% Out-of-Sample) ===")
    res_us = evaluate_us_major_sports_composite(db)
    for lg, m in res_us.items():
        print(
            f"  {lg.upper():<6} (n={int(m['n_test_picks']):<3}) | ROI={m['roi_top15']:+.4f} | "
            f"HitRate={m['hit_rate']:.1%} vs MktImplied={m['mkt_implied']:.1%} ({m['hit_rate']-m['mkt_implied']:+.1%})"
        )
