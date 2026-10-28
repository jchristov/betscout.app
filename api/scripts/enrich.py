"""Rebuild or refresh enriched match_details (and optionally matches) from cached ESPN JSON payloads.

Usage:
    uv run python scripts/enrich.py            # Fast refresh of soccer match_details + summary report
    uv run python scripts/enrich.py --full     # Full rebuild of matches + match_details (soccer & tennis)
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "data").exists() else Path(__file__).resolve().parents[1]

from betscout.enrich import rebuild_all_from_cache, refresh_soccer_details  # noqa: E402
from betscout.quality import install_view  # noqa: E402


def print_enrichment_summary(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT sport,
               COUNT(*) AS rows,
               SUM(open_home IS NOT NULL) AS open_1x2,
               SUM(num_books >= 2) AS multi_book,
               SUM(home_sot IS NOT NULL) AS boxscore,
               SUM(surface IS NOT NULL) AS surface,
               SUM(home_games IS NOT NULL) AS games
        FROM match_details
        GROUP BY sport
        ORDER BY sport
        """
    ).fetchall()
    conn.close()
    print(f"{'sport':<8}{'rows':>8}{'open_1x2':>10}{'multi_book':>12}{'boxscore':>10}{'surface':>10}{'games':>8}")
    for sp, n, oc, mb, bx, sf, gm in rows:
        print(f"{sp:<8}{n:>8}{oc or 0:>10}{mb or 0:>12}{bx or 0:>10}{sf or 0:>10}{gm or 0:>8}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild or refresh enriched match_details from cached ESPN payloads.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Rebuild both `matches` and `match_details` across all cached soccer and tennis scoreboards/summaries.",
    )
    args = parser.parse_args()

    db_path = ROOT / "data" / "betscout.db"
    cache_dir = ROOT / "data" / "cache"

    if args.full:
        counts = rebuild_all_from_cache(db_path, cache_dir)
        install_view(db_path)
        print(f"Full rebuild complete across {len(counts)} leagues ({sum(counts.values())} matches).")
    else:
        n = refresh_soccer_details(db_path, cache_dir)
        install_view(db_path)
        print(f"Refreshed {n} soccer rows in match_details.")

    print_enrichment_summary(db_path)


if __name__ == "__main__":
    main()
