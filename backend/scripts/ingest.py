"""Universal on-demand & periodic ingestion CLI for any ESPN sport or league.

Reads `ingestion_config.json` by default. Automatically registers newly requested sports/leagues
into `ingestion_config.json`, skips already-ingested events to prevent duplication, normalizes
and enriches records on the fly (`matches` + `match_details`), and verifies database quality.

Examples:
    # 1. Periodic incremental run across all enabled sources in ingestion_config.json:
    uv run python scripts/ingest.py

    # 2. Ingest specific leagues or new sports over a recent window (and auto-add to ingestion_config.json):
    uv run python scripts/ingest.py --leagues uefa.champions,uefa.europa,uefa.europa.conf,ned.1,por.1,nba,nhl,nfl,mlb --days 60

    # 3. Ingest a specific season/year range or full history for selected leagues:
    uv run python scripts/ingest.py --leagues uefa.champions,uefa.europa --years 2025,2026
    uv run python scripts/ingest.py --leagues nba,nhl,nfl --from 2026-09-01 --to 2026-10-22
    uv run python scripts/ingest.py --leagues eng.1 --all-history
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[2] if (Path(__file__).resolve().parents[2] / "data").exists() else Path(__file__).resolve().parents[1]

from betscout.espn import LEAGUE_LABELS, resolve_league  # noqa: E402
from betscout.universal_ingest import ingest_universal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Universal config-driven sport & league ingestion with on-the-fly quality normalization.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "ingestion_config.json",
        help="Path to ingestion descriptor JSON (default: model/ingestion_config.json)",
    )
    parser.add_argument(
        "--leagues",
        type=str,
        default=None,
        help="Comma-separated league keys or 'sport/league' specs (e.g. 'uefa.champions,nba,soccer/ned.1'). Omit to run all enabled sources in config.",
    )
    parser.add_argument("--days", type=int, default=None, help="Ingest completed matches over the last N days")
    parser.add_argument("--from", dest="from_date", type=str, default=None, help="Start date YYYY-MM-DD (or YYYYMMDD)")
    parser.add_argument("--to", dest="to_date", type=str, default=None, help="End date YYYY-MM-DD (or YYYYMMDD)")
    parser.add_argument("--years", type=str, default=None, help="Comma-separated season years (e.g. '2025,2026')")
    parser.add_argument("--all-history", action="store_true", help="Ingest full 2022-2026 historical range")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent fetch workers (default: 8)")
    args = parser.parse_args()

    leagues = None
    if args.leagues:
        leagues = [resolve_league(x) for x in args.leagues.split(",") if x.strip()]

    mode = "incremental"
    years = None
    from_ymd = args.from_date.replace("-", "") if args.from_date else None
    to_ymd = args.to_date.replace("-", "") if args.to_date else None

    if args.all_history:
        mode = "all_history"
    elif args.years:
        mode = "years"
        years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    elif from_ymd:
        mode = "range"
    elif args.days:
        mode = "days"

    db_path = ROOT / "data" / "betscout.db"
    cache_dir = ROOT / "data" / "cache"

    res = ingest_universal(
        db_path=db_path,
        cache_dir=cache_dir,
        config_path=args.config,
        leagues=leagues,
        mode=mode,
        years=years,
        days_back=args.days,
        from_ymd=from_ymd,
        to_ymd=to_ymd,
        workers=args.workers,
    )

    print(f"Ingestion mode: {res['mode']} | Config updated: {args.config}")
    print(f"New matches ingested this run: {res['new_ingested']}")
    print(f"On-the-fly normalization: {res['normalization']}")
    print(f"Quality errors: {len(res['quality_errors'])}\n")

    print(f"{'League':<18}{'Name':<26}{'Sport':<12}{'Rows':>7}{'Priced':>8}{'Totals':>8}")
    print("-" * 79)
    for lg, st in sorted(res["stats"].items(), key=lambda kv: (kv[1]["sport"], kv[0])):
        label = LEAGUE_LABELS.get(lg, lg)
        print(f"{lg:<18}{label:<26}{st['sport']:<12}{st['rows']:>7}{st['with_1x2'] or 0:>8}{st['with_totals'] or 0:>8}")


if __name__ == "__main__":
    main()
