"""CLI addon to format and publish high-conviction sports picks & settled paper-trade recaps
to a Discord channel (`DISCORD_WEBHOOK_URL` or `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` in `model/.env`).

Usage:
    # Preview the formatted Discord Markdown post in terminal (dry-run)
    uv run python scripts/discord_post.py --dry-run

    # Post live to your Discord channel (reads DISCORD_WEBHOOK_URL from model/.env automatically)
    uv run python scripts/discord_post.py

    # Filter by sport and minimum odds
    uv run python scripts/discord_post.py --sport soccer --min-odds 1.25 --max-picks 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sportdata_model.dashboard import DEFAULT_LOCAL_TZ  # noqa: E402
from sportdata_model.telegram_bot import format_discord_digest, send_discord_message  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Sportdata Quant Desk digest to a Discord channel.")
    parser.add_argument("--min-odds", type=float, default=1.15, help="Minimum odds threshold (default: 1.15)")
    parser.add_argument(
        "--sport",
        choices=("all", "soccer", "tennis", "basketball", "hockey", "football", "baseball"),
        default="all",
        help="Filter digest by sport (default: all)",
    )
    parser.add_argument("--max-picks", type=int, default=12, help="Max upcoming picks in message (default: 12)")
    parser.add_argument("--tz", type=str, default=DEFAULT_LOCAL_TZ, help=f"Timezone for kickoff display (default: {DEFAULT_LOCAL_TZ})")
    parser.add_argument("--webhook-url", type=str, default=None, help="Discord Webhook URL (overrides DISCORD_WEBHOOK_URL in .env)")
    parser.add_argument("--bot-token", type=str, default=None, help="Discord Bot Token (overrides DISCORD_BOT_TOKEN in .env)")
    parser.add_argument("--channel-id", type=str, default=None, help="Discord Channel ID (overrides DISCORD_CHANNEL_ID in .env)")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted Discord Markdown message without sending")
    args = parser.parse_args()

    rec_path = ROOT / "data" / "recommendations.json"
    db_path = ROOT / "data" / "matches.sqlite"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}

    msg = format_discord_digest(
        rec=rec,
        db_path=db_path,
        min_odds=args.min_odds,
        sport_filter=args.sport,
        max_picks=args.max_picks,
        tz_name=args.tz,
    )
    res = send_discord_message(
        text=msg,
        webhook_url=args.webhook_url,
        bot_token=args.bot_token,
        channel_id=args.channel_id,
        dry_run=args.dry_run,
    )
    if res.get("dry_run"):
        print("=== DISCORD CHANNEL DIGEST PREVIEW (MARKDOWN) ===")
        print(msg)
        print("=================================================")
        if not res.get("configured"):
            print("Note: Set DISCORD_WEBHOOK_URL in model/.env (or pass --webhook-url) to post live.")
    else:
        print("Discord API Response:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
