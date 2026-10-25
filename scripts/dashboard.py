"""Generate the standalone HTML Quantitative Desk Dashboard (`data/dashboard.html`).

Usage:
    uv run python scripts/dashboard.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.dashboard import generate_dashboard_html  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the HTML Quantitative Desk Dashboard and export Best Bets summary as CSV/JSON.")
    parser.add_argument(
        "--min-odds",
        type=float,
        default=1.10,
        help="Soft filter threshold: exclude unattractive odds <= min_odds (default: 1.10 = 10%% profit or less)",
    )
    parser.add_argument(
        "--sport",
        choices=("all", "soccer", "tennis", "basketball", "hockey", "football", "baseball"),
        default="all",
        help="Default sport filter for dashboard and CSV/JSON exports (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=("both", "csv", "json", "none"),
        default="both",
        help="Export Best Bets summary table format (default: both -> data/best_bets.csv & data/best_bets.json)",
    )
    parser.add_argument("--export-csv", type=Path, default=None, help="Custom path for Best Bets CSV export (with header)")
    parser.add_argument("--export-json", type=Path, default=None, help="Custom path for Best Bets JSON export")
    args = parser.parse_args()

    rec_path = ROOT / "data" / "recommendations.json"
    db_path = ROOT / "data" / "matches.sqlite"
    out_path = ROOT / "data" / "dashboard.html"
    csv_path = args.export_csv or ((ROOT / "data" / "best_bets.csv") if args.format in ("both", "csv") else None)
    json_path = args.export_json or ((ROOT / "data" / "best_bets.json") if args.format in ("both", "json") else None)

    path = generate_dashboard_html(
        rec_path,
        db_path,
        out_path,
        min_odds=args.min_odds,
        sport_filter=args.sport,
        csv_export_path=csv_path,
        json_export_path=json_path,
    )
    print(f"Generated quantitative desk dashboard (min_odds > {args.min_odds:.2f}): {path} ({path.stat().st_size:,} bytes)")
    if csv_path:
        print(f"Exported Best Bets CSV (with header): {csv_path}")
    if json_path:
        print(f"Exported Best Bets JSON: {json_path}")


if __name__ == "__main__":
    main()
