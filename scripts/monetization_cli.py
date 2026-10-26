"""CLI for managing BetScout Paid API Keys, Pro Subscribers, and B2B Webhooks (`uv run betscout apikey ...`)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from betscout.monetization import (
    add_subscriber_webhook,
    create_api_key,
    list_api_keys,
    list_subscriber_webhooks,
    list_subscribers,
    revoke_api_key,
    upsert_subscriber,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description="Manage BetScout Paid API Keys, Pro WebApp Subscribers & B2B Webhooks")
    p.add_argument("action", choices=["create-key", "list-keys", "revoke-key", "add-subscriber", "list-subscribers", "add-webhook", "list-webhooks"], nargs="?", default="list-keys")
    p.add_argument("--email", default="", help="Customer email address")
    p.add_argument("--tier", default="pro", help="Plan tier: starter | pro | enterprise")
    p.add_argument("--label", default="", help="Optional label for API key")
    p.add_argument("--limit", type=int, default=None, help="Custom daily request quota")
    p.add_argument("--key-id", default="", help="Key ID to revoke (for revoke-key)")
    p.add_argument("--status", default="active", help="Subscriber status: active | cancelled")
    p.add_argument("--channel", default="discord", help="Webhook channel: discord | telegram")
    p.add_argument("--target", default="", help="Discord Webhook URL or Telegram Chat ID")
    p.add_argument("--sports", default="all", help="Sports filter for B2B webhook")
    p.add_argument("--db", default=str(ROOT / "data" / "betscout.db"), help="Path to betscout.db")
    args = p.parse_args()

    db_path = Path(args.db)
    if args.action == "create-key":
        if not args.email:
            raise SystemExit("Error: --email is required for create-key")
        res = create_api_key(db_path, owner_email=args.email, plan_tier=args.tier, label=args.label, daily_limit=args.limit)
        print(json.dumps(res, indent=2))
    elif args.action == "list-keys":
        print(json.dumps(list_api_keys(db_path), indent=2))
    elif args.action == "revoke-key":
        if not args.key_id:
            raise SystemExit("Error: --key-id is required for revoke-key")
        ok = revoke_api_key(db_path, args.key_id)
        print(json.dumps({"ok": ok, "key_id": args.key_id}, indent=2))
    elif args.action == "add-subscriber":
        if not args.email:
            raise SystemExit("Error: --email is required for add-subscriber")
        res = upsert_subscriber(db_path, email=args.email, plan_tier=args.tier, status=args.status)
        print(json.dumps(res, indent=2))
    elif args.action == "list-subscribers":
        print(json.dumps(list_subscribers(db_path), indent=2))
    elif args.action == "add-webhook":
        if not args.email or not args.target:
            raise SystemExit("Error: --email and --target are required for add-webhook")
        res = add_subscriber_webhook(db_path, owner_email=args.email, channel_type=args.channel, target_url_or_chat=args.target, sports_filter=args.sports)
        print(json.dumps(res, indent=2))
    elif args.action == "list-webhooks":
        print(json.dumps(list_subscriber_webhooks(db_path, active_only=False), indent=2))


if __name__ == "__main__":
    main()
