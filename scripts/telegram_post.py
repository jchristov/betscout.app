"""CLI addon to format and publish high-conviction sports picks & settled paper-bet recaps
to a Telegram channel or group (`TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`).

Usage:
    # Preview the formatted Telegram post in terminal (dry-run)
    uv run python scripts/telegram_post.py --dry-run

    # Post live to a Telegram channel (e.g. @my_channel or -1001234567890)
    TELEGRAM_BOT_TOKEN="123456:AA..." TELEGRAM_CHAT_ID="@my_channel" uv run python scripts/telegram_post.py

    # Filter by sport and minimum odds
    uv run python scripts/telegram_post.py --sport soccer --min-odds 1.25 --max-picks 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from betscout.dashboard import DEFAULT_LOCAL_TZ  # noqa: E402
from betscout.telegram_bot import format_telegram_digest, send_telegram_message  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish BetScout Quant Desk digest to a Telegram channel.")
    parser.add_argument("--min-odds", type=float, default=1.15, help="Minimum odds threshold (default: 1.15)")
    parser.add_argument(
        "--sport",
        choices=("all", "soccer", "tennis", "basketball", "hockey", "football", "baseball"),
        default="all",
        help="Filter digest by sport (default: all)",
    )
    parser.add_argument(
        "--day",
        type=str,
        default="today",
        help="Day filter for picks: 'today' (default), 'tomorrow', 'next48h', 'all', or 'YYYY-MM-DD'",
    )
    parser.add_argument("--max-picks", type=int, default=12, help="Max upcoming picks in message (default: 12)")
    parser.add_argument("--tz", type=str, default=DEFAULT_LOCAL_TZ, help=f"Timezone for kickoff display (default: {DEFAULT_LOCAL_TZ})")
    parser.add_argument("--bot-token", type=str, default=None, help="Telegram Bot Token (overrides TELEGRAM_BOT_TOKEN)")
    parser.add_argument("--chat-id", type=str, default=None, help="Telegram Channel/Chat ID (overrides TELEGRAM_CHAT_ID)")
    parser.add_argument("--dry-run", action="store_true", help="Print formatted Telegram message without sending")
    args = parser.parse_args()

    rec_path = ROOT / "data" / "recommendations.json"
    db_path = ROOT / "data" / "betscout.db"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {}

    msg = format_telegram_digest(
        rec=rec,
        db_path=db_path,
        min_odds=args.min_odds,
        sport_filter=args.sport,
        day_filter=args.day,
        max_picks=args.max_picks,
        tz_name=args.tz,
    )
    res = send_telegram_message(
        text=msg,
        bot_token=args.bot_token,
        chat_id=args.chat_id,
        dry_run=args.dry_run,
    )
    if res.get("dry_run"):
        print("=== TELEGRAM CHANNEL DIGEST PREVIEW (HTML) ===")
        print(msg)
        print("==============================================")
        if not res.get("configured"):
            print("Note: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (or pass --bot-token / --chat-id) to post live.")
    else:
        print("Telegram API Response:", json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
