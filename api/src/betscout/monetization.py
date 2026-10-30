"""Commercial Monetization Engine (`src/betscout/monetization.py`).

Implements the 3 monetization streams for BetScout (`betscout.app`):
  1. **Paid B2B & Developer REST API (`/api/v1/*`):**
     - API Key provisioning (`bs_live_<32_hex>`), SHA-256 hashed storage (`api_keys`),
       daily quota enforcement (`api_usage_daily`), and `X-RateLimit-*` response headers.
     - Tiered access (`starter`, `pro`, `enterprise`) and OpenAPI 3.1 specification (`/api/v1/openapi.json`).
  2. **Paid Read-Only WebApp Subscriptions (`subscribers`):**
     - 3-tier role resolution (`admin` | `pro` | `free`).
     - Server-side pick redaction (`redact_snapshot_for_free_tier` & `redact_recommendations_for_free_tier`)
       so free/anonymous visitors see 100% of the verified settled ledger + `FREE_PREVIEW_PICKS_COUNT` (default 2)
       unlocked daily picks while premium picks, combos, and exact-score clusters are redacted server-side.
     - Stripe Checkout & Webhook subscription synchronization (`handle_stripe_webhook_event`).
  3. **Paid VIP & B2B Syndication Webhooks (`subscriber_webhooks`):**
     - Multi-tenant Discord Webhook / Telegram Chat ID registry for B2B syndicate customers,
       plus Free Public Teaser vs. VIP Full-Slate dual-channel broadcasting.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import load_dotenv

MONETIZATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    owner_email TEXT NOT NULL,
    label TEXT DEFAULT '',
    plan_tier TEXT NOT NULL DEFAULT 'starter',
    daily_limit INTEGER NOT NULL DEFAULT 500,
    rate_limit_per_min INTEGER NOT NULL DEFAULT 20,
    allowed_sports TEXT NOT NULL DEFAULT 'all',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS api_usage_daily (
    key_id TEXT NOT NULL,
    date_ymd TEXT NOT NULL,
    calls_count INTEGER NOT NULL DEFAULT 0,
    last_called_at TEXT,
    PRIMARY KEY (key_id, date_ymd)
);

CREATE TABLE IF NOT EXISTS subscribers (
    email TEXT PRIMARY KEY,
    firebase_uid TEXT,
    plan_tier TEXT NOT NULL DEFAULT 'pro',
    status TEXT NOT NULL DEFAULT 'active',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS subscriber_webhooks (
    webhook_id TEXT PRIMARY KEY,
    owner_email TEXT NOT NULL,
    channel_type TEXT NOT NULL DEFAULT 'discord',
    target_url_or_chat TEXT NOT NULL,
    sports_filter TEXT NOT NULL DEFAULT 'all',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
"""

API_TIER_DEFAULTS: dict[str, dict[str, int]] = {
    "starter": {"daily_limit": 500, "rate_limit_per_min": 15},
    "pro": {"daily_limit": 5000, "rate_limit_per_min": 60},
    "enterprise": {"daily_limit": 50000, "rate_limit_per_min": 300},
}


def ensure_monetization_tables(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(MONETIZATION_SCHEMA)
    conn.commit()
    conn.close()


def get_monetization_config(data_dir: Path | None = None) -> dict[str, Any]:
    """Return current monetization settings from environment variables and `webapp_settings.json`."""
    load_dotenv(override=False)
    env_enabled = (os.environ.get("MONETIZATION_ENABLED") or "").strip().lower() in ("1", "true", "yes", "on")
    free_preview_n = int((os.environ.get("FREE_PREVIEW_PICKS_COUNT") or "2").strip() or "2")
    stripe_Monthly_url = (os.environ.get("STRIPE_CHECKOUT_URL_PRO") or "https://betscout.app/#pricing").strip()
    stripe_api_url = (os.environ.get("STRIPE_CHECKOUT_URL_API") or "https://betscout.app/#pricing").strip()
    free_discord_wh = (os.environ.get("DISCORD_WEBHOOK_URL_FREE_TEASER") or "").strip()

    if data_dir and (data_dir / "webapp_settings.json").exists():
        try:
            s = json.loads((data_dir / "webapp_settings.json").read_text(encoding="utf-8"))
            if "monetization_enabled" in s and s["monetization_enabled"] is not None:
                env_enabled = bool(s["monetization_enabled"])
            if "free_preview_picks_count" in s and s["free_preview_picks_count"] is not None:
                free_preview_n = max(0, int(s["free_preview_picks_count"]))
            if s.get("stripe_checkout_url_pro"):
                stripe_Monthly_url = str(s["stripe_checkout_url_pro"]).strip()
            if s.get("stripe_checkout_url_api"):
                stripe_api_url = str(s["stripe_checkout_url_api"]).strip()
        except Exception:
            pass

    stripe_sk = (os.environ.get("STRIPE_SECRET_KEY") or "").strip()
    stripe_pk = (os.environ.get("VITE_STRIPE_PUBLISHABLE_KEY") or os.environ.get("STRIPE_PUBLISHABLE_KEY") or "").strip()

    return {
        "enabled": env_enabled,
        "free_preview_picks_count": free_preview_n,
        "stripe_checkout_url_pro": stripe_Monthly_url,
        "stripe_checkout_url_api": stripe_api_url,
        "stripe_configured": bool(stripe_sk.startswith("sk_")),
        "stripe_publishable_key": stripe_pk,
        "has_free_teaser_webhook": bool(free_discord_wh.startswith("https://discord")),
    }


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def create_api_key(
    db_path: Path,
    owner_email: str,
    plan_tier: str = "pro",
    label: str = "",
    daily_limit: int | None = None,
    allowed_sports: str = "all",
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Generate a new `bs_live_<32_hex>` API key, store only its SHA-256 hash in `betscout.db`,
    and return the plaintext `api_key` once to the caller."""
    ensure_monetization_tables(db_path)
    tier = plan_tier.lower().strip() if plan_tier else "pro"
    if tier not in API_TIER_DEFAULTS:
        tier = "pro"
    defaults = API_TIER_DEFAULTS[tier]
    d_limit = int(daily_limit) if daily_limit is not None else defaults["daily_limit"]
    r_limit = defaults["rate_limit_per_min"]

    raw_token = f"bs_live_{secrets.token_hex(16)}"
    key_id = f"key_{secrets.token_hex(6)}"
    key_hash = _hash_api_key(raw_token)
    key_prefix = f"{raw_token[:14]}...{raw_token[-4:]}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = sqlite3.connect(db_path, timeout=20.0)
    conn.execute(
        """
        INSERT INTO api_keys
        (key_id, key_hash, key_prefix, owner_email, label, plan_tier, daily_limit, rate_limit_per_min, allowed_sports, active, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (key_id, key_hash, key_prefix, owner_email.strip().lower(), label.strip(), tier, d_limit, r_limit, allowed_sports, now_iso, expires_at),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "key_id": key_id,
        "api_key": raw_token,
        "key_prefix": key_prefix,
        "owner_email": owner_email.strip().lower(),
        "label": label.strip(),
        "plan_tier": tier,
        "daily_limit": d_limit,
        "rate_limit_per_min": r_limit,
        "allowed_sports": allowed_sports,
        "created_at": now_iso,
        "expires_at": expires_at,
    }


def list_api_keys(db_path: Path) -> list[dict[str, Any]]:
    ensure_monetization_tables(db_path)
    today_ymd = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    rows = [
        dict(r)
        for r in conn.execute(
            """
            SELECT k.key_id, k.key_prefix, k.owner_email, k.label, k.plan_tier, k.daily_limit,
                   k.rate_limit_per_min, k.allowed_sports, k.active, k.created_at, k.expires_at,
                   COALESCE(u.calls_count, 0) AS calls_today, u.last_called_at
            FROM api_keys k
            LEFT JOIN api_usage_daily u ON k.key_id = u.key_id AND u.date_ymd = ?
            ORDER BY k.created_at DESC
            """,
            (today_ymd,),
        ).fetchall()
    ]
    conn.close()
    return rows


def revoke_api_key(db_path: Path, key_id: str) -> bool:
    ensure_monetization_tables(db_path)
    conn = sqlite3.connect(db_path, timeout=15.0)
    cur = conn.execute("UPDATE api_keys SET active = 0 WHERE key_id = ?", (key_id.strip(),))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def validate_and_meter_api_key(
    db_path: Path,
    raw_key: str | None,
    required_tier: str = "starter",
) -> tuple[bool, dict[str, Any], dict[str, str], int]:
    """Validate an incoming `X-API-Key` (or `Bearer bs_live_...`), increment `api_usage_daily`,
    and return `(ok, key_info_or_err, rate_limit_headers, http_status)`."""
    if not raw_key or not raw_key.strip():
        return (
            False,
            {"ok": False, "error": "Missing API key. Pass 'X-API-Key: bs_live_...' or 'Authorization: Bearer bs_live_...'."},
            {},
            401,
        )
    ensure_monetization_tables(db_path)
    k_hash = _hash_api_key(raw_key.strip())
    today_ymd = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reset_iso = f"{today_ymd}T23:59:59Z"

    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM api_keys WHERE key_hash = ?", (k_hash,)).fetchone()
    if not row or not int(row["active"]):
        conn.close()
        return False, {"ok": False, "error": "Invalid or revoked API key."}, {}, 401

    if row["expires_at"] and str(row["expires_at"]) < now_iso:
        conn.close()
        return False, {"ok": False, "error": "API key has expired. Please renew your subscription."}, {}, 403

    tier_rank = {"starter": 1, "pro": 2, "enterprise": 3}
    key_tier = str(row["plan_tier"] or "starter").lower()
    if tier_rank.get(key_tier, 1) < tier_rank.get(required_tier.lower(), 1):
        conn.close()
        return (
            False,
            {
                "ok": False,
                "error": f"Endpoint requires '{required_tier}' API plan or higher (current plan: '{key_tier}').",
            },
            {},
            403,
        )

    u_row = conn.execute(
        "SELECT calls_count FROM api_usage_daily WHERE key_id = ? AND date_ymd = ?",
        (row["key_id"], today_ymd),
    ).fetchone()
    used = int(u_row["calls_count"]) if u_row else 0
    limit = int(row["daily_limit"] or 500)
    if used >= limit:
        conn.close()
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": reset_iso,
        }
        return (
            False,
            {"ok": False, "error": f"Daily API quota exceeded ({limit} requests/day). Upgrade tier or wait until {reset_iso}."},
            headers,
            429,
        )

    new_used = used + 1
    conn.execute(
        """
        INSERT INTO api_usage_daily (key_id, date_ymd, calls_count, last_called_at)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(key_id, date_ymd) DO UPDATE SET calls_count = calls_count + 1, last_called_at = excluded.last_called_at
        """,
        (row["key_id"], today_ymd, now_iso),
    )
    conn.commit()
    conn.close()

    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, limit - new_used)),
        "X-RateLimit-Reset": reset_iso,
        "X-BetScout-Plan": key_tier,
    }
    return True, dict(row), headers, 200


def upsert_subscriber(
    db_path: Path,
    email: str,
    plan_tier: str = "pro",
    status: str = "active",
    expires_at: str | None = None,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> dict[str, Any]:
    """Create or update a paid WebApp subscriber (`pro` or `vip`) in `betscout.db`."""
    ensure_monetization_tables(db_path)
    norm_email = email.strip().lower()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.execute(
        """
        INSERT INTO subscribers (email, plan_tier, status, stripe_customer_id, stripe_subscription_id, created_at, updated_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            plan_tier = excluded.plan_tier,
            status = excluded.status,
            stripe_customer_id = COALESCE(excluded.stripe_customer_id, subscribers.stripe_customer_id),
            stripe_subscription_id = COALESCE(excluded.stripe_subscription_id, subscribers.stripe_subscription_id),
            updated_at = excluded.updated_at,
            expires_at = excluded.expires_at
        """,
        (norm_email, plan_tier.lower().strip(), status.lower().strip(), stripe_customer_id, stripe_subscription_id, now_iso, now_iso, expires_at),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "email": norm_email,
        "plan_tier": plan_tier.lower().strip(),
        "status": status.lower().strip(),
        "expires_at": expires_at,
        "updated_at": now_iso,
    }


def list_subscribers(db_path: Path) -> list[dict[str, Any]]:
    ensure_monetization_tables(db_path)
    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM subscribers ORDER BY updated_at DESC").fetchall()]
    conn.close()
    return rows


def check_is_active_subscriber(db_path: Path, email: str | None) -> tuple[bool, str]:
    """Check if `email` is an active paying subscriber (`status == 'active'` and not expired) or listed in `BETSCOUT_PRO_EMAILS`."""
    if not email:
        return False, "free"
    norm_email = email.strip().lower()
    raw_pro_env = (os.environ.get("BETSCOUT_PRO_EMAILS") or "").strip()
    if raw_pro_env:
        pro_emails = {x.strip().lower() for x in raw_pro_env.split(",") if x.strip()}
        if norm_email in pro_emails:
            return True, "pro"
    if not db_path.exists():
        return False, "free"
    ensure_monetization_tables(db_path)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT plan_tier, status, expires_at FROM subscribers WHERE email = ?", (norm_email,)).fetchone()
    conn.close()
    if not row or str(row["status"]).lower() != "active":
        return False, "free"
    if row["expires_at"] and str(row["expires_at"]) < now_iso:
        return False, "free"
    return True, str(row["plan_tier"] or "pro").lower()


def add_subscriber_webhook(
    db_path: Path,
    owner_email: str,
    channel_type: str,
    target_url_or_chat: str,
    sports_filter: str = "all",
) -> dict[str, Any]:
    """Register a B2B customer's Discord Webhook URL or Telegram Chat ID for automated pick syndication."""
    ensure_monetization_tables(db_path)
    wid = f"wh_{secrets.token_hex(5)}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.execute(
        """
        INSERT INTO subscriber_webhooks (webhook_id, owner_email, channel_type, target_url_or_chat, sports_filter, active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
        (wid, owner_email.strip().lower(), channel_type.lower().strip(), target_url_or_chat.strip(), sports_filter.lower().strip(), now_iso),
    )
    conn.commit()
    conn.close()
    return {
        "ok": True,
        "webhook_id": wid,
        "owner_email": owner_email.strip().lower(),
        "channel_type": channel_type.lower().strip(),
        "sports_filter": sports_filter.lower().strip(),
    }


def list_subscriber_webhooks(db_path: Path, active_only: bool = True) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    ensure_monetization_tables(db_path)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM subscriber_webhooks WHERE active = 1 ORDER BY created_at DESC" if active_only else "SELECT * FROM subscriber_webhooks ORDER BY created_at DESC"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    conn.close()
    return rows


def redact_recommendations_for_free_tier(
    rec: dict[str, Any],
    free_preview_count: int = 2,
) -> dict[str, Any]:
    """Produce a server-side redacted copy of `recommendations.json` for `free` (unsubscribed) visitors when
    `monetization_enabled=True`:
      - 100% of `SETTLED` paper_ledger rows and equity curves remain visible (proving track record).
      - The first `free_preview_count` upcoming picks remain unlocked as a free daily sample.
      - All remaining upcoming picks, 2-leg combos, and pending/live ledger rows have their team/pick names
        replaced on the server with `'🔒 Pro Subscriber Pick'` so DevTools inspection cannot leak paid picks."""
    out = copy.deepcopy(rec)
    unlocked_matches: set[str] = set()

    # Collect earliest `free_preview_count` picks across soccer/tennis/other to keep unlocked
    all_upcoming: list[tuple[str, str]] = []
    for p in out.get("qualifying_picks") or []:
        if p.get("action") == "PAPER_BET":
            all_upcoming.append((str(p.get("kickoff") or "9999"), f"{p.get('home')} vs {p.get('away')}"))
    for tp in out.get("tennis_picks") or []:
        all_upcoming.append((str(tp.get("kickoff") or "9999"), f"{tp.get('player_1')} vs {tp.get('player_2')}"))
    for op in out.get("other_sport_picks") or []:
        all_upcoming.append((str(op.get("kickoff") or "9999"), f"{op.get('home')} vs {op.get('away')}"))
    all_upcoming.sort(key=lambda x: x[0])
    for _, m_name in all_upcoming[: max(0, free_preview_count)]:
        unlocked_matches.add(m_name)

    for p in out.get("qualifying_picks") or []:
        m_str = f"{p.get('home')} vs {p.get('away')}"
        if m_str not in unlocked_matches:
            p["home"] = "🔒 Pro Matchup"
            p["away"] = f"(Unlock @{float(p.get('best_odds') or 1.5):.2f})"
            p["home_logo"] = None
            p["away_logo"] = None
            p["exact_score_prediction"] = {}
            p["locked_pro"] = True

    for tp in out.get("tennis_picks") or []:
        m_str = f"{tp.get('player_1')} vs {tp.get('player_2')}"
        if m_str not in unlocked_matches:
            tp["player_1"] = "🔒 Pro Tennis Banker"
            tp["player_2"] = f"(Win {float(tp.get('win_prob') or 0.75)*100:.0f}%)"
            tp["pick"] = "🔒 Unlock Pro Pick"
            tp["home_logo"] = None
            tp["away_logo"] = None
            tp["home_flag"] = None
            tp["away_flag"] = None
            tp["set_score_prediction"] = {}
            tp["locked_pro"] = True

    for op in out.get("other_sport_picks") or []:
        m_str = f"{op.get('home')} vs {op.get('away')}"
        if m_str not in unlocked_matches:
            op["home"] = "🔒 Pro Major League Pick"
            op["away"] = f"(@{float(op.get('best_odds') or 1.5):.2f})"
            op["pick"] = "🔒 Unlock Pro Pick"
            op["home_logo"] = None
            op["away_logo"] = None
            op["locked_pro"] = True

    for d in out.get("recommended_doubles") or []:
        for lk in ("leg_1", "leg_2"):
            if isinstance(d.get(lk), dict):
                d[lk]["match"] = "🔒 Pro 2-Leg Combo Leg"
                d[lk]["pick"] = "🔒 Unlock Pro Parlay"

    ledger = out.get("paper_ledger")
    if isinstance(ledger, dict):
        for tr in ledger.get("bets") or []:
            if tr.get("status") != "SETTLED":
                m_str = f"{tr.get('home')} vs {tr.get('away')}"
                if m_str not in unlocked_matches:
                    tr["home"] = "🔒 Pro Active Pick"
                    tr["away"] = f"(@{float(tr.get('logged_best_odds') or 1.5):.2f})"
                    tr["home_logo"] = None
                    tr["away_logo"] = None
                    tr["exact_score_pred"] = "🔒 Pro Score Target"
                    tr["locked_pro"] = True
        for cb in ledger.get("combos") or []:
            if cb.get("status") != "SETTLED":
                for lk in ("leg_1", "leg_2"):
                    if isinstance(cb.get(lk), dict):
                        cb[lk]["match"] = "🔒 Pro Combo Leg"
                        cb[lk]["pick"] = "🔒 Unlock Pro"

    return out


def handle_stripe_webhook_event(
    db_path: Path,
    raw_body: bytes,
    sig_header: str | None = None,
) -> dict[str, Any]:
    """Process a Stripe `checkout.session.completed` or `customer.subscription.deleted` webhook event
    and automatically provision/revoke the subscriber and/or API key in `betscout.db`."""
    secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if secret and sig_header:
        # Verify Stripe-Signature `t=...,v1=...`
        parts = dict(item.split("=", 1) for item in sig_header.split(",") if "=" in item)
        ts = parts.get("t", "")
        v1 = parts.get("v1", "")
        signed_payload = f"{ts}.{raw_body.decode('utf-8', errors='replace')}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, v1):
            return {"ok": False, "error": "Invalid Stripe webhook signature"}

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"Invalid JSON: {exc}"}

    ev_type = str(event.get("type") or "")
    obj = ((event.get("data") or {}).get("object")) or {}
    email = str(
        obj.get("customer_email")
        or ((obj.get("customer_details") or {}).get("email"))
        or ((obj.get("metadata") or {}).get("email"))
        or ""
    ).strip().lower()

    if ev_type in ("checkout.session.completed", "customer.subscription.created", "customer.subscription.updated"):
        if not email:
            return {"ok": False, "error": "No customer email in Stripe event"}
        plan = str((obj.get("metadata") or {}).get("plan_tier") or "pro").lower()
        sub_res = upsert_subscriber(
            db_path=db_path,
            email=email,
            plan_tier=plan,
            status="active",
            stripe_customer_id=str(obj.get("customer") or ""),
            stripe_subscription_id=str(obj.get("subscription") or obj.get("id") or ""),
        )
        api_key_res = None
        if plan in ("api_starter", "api_pro", "api_enterprise", "enterprise"):
            clean_t = plan.replace("api_", "")
            api_key_res = create_api_key(db_path, owner_email=email, plan_tier=clean_t, label="Stripe Auto-Provisioned")
        return {"ok": True, "action": "provisioned", "subscriber": sub_res, "api_key": api_key_res}

    if ev_type == "customer.subscription.deleted" and email:
        upsert_subscriber(db_path=db_path, email=email, status="cancelled")
        return {"ok": True, "action": "cancelled", "email": email}

    return {"ok": True, "action": "ignored", "type": ev_type}


STRIPE_PLANS_SPEC: dict[str, dict[str, Any]] = {
    "tier1": {
        "meta_key": "tier_1_vip",
        "plan_tier": "vip",
        "name": "BetScout Tier 1 — VIP Notifications Only (Discord & Telegram)",
        "description": "Private VIP Discord & Telegram channels, high-res PNG Pick Cards, 2-Leg/3-Leg Banker Boosters & Live In-Play Alerts.",
        "monthly_cents": 3900,
        "annual_cents": 31900,
    },
    "tier2": {
        "meta_key": "tier_2_pro",
        "plan_tier": "pro",
        "name": "BetScout Tier 2 — Pro WebApp + VIP Notifications",
        "description": "100% Unlocked Pro WebApp Desk, Smart Bet Slip & ¼-Kelly Optimizer, Exact-Score/Set-Score Dutching + Tier 1 VIP Alerts.",
        "monthly_cents": 7900,
        "annual_cents": 64900,
    },
    "tier3": {
        "meta_key": "tier_3_api",
        "plan_tier": "enterprise",
        "name": "BetScout Tier 3 — Quant API + Bonus MCP Server",
        "description": "Dedicated Quant REST API Key (50,000 req/day), Remote AI Agent MCP Server (https://betscout.app/mcp), SDKs + Tier 2 Pro WebApp.",
        "monthly_cents": 19900,
        "annual_cents": 178800,
    },
}


def _stripe_api_call(method: str, endpoint: str, form_fields: list[tuple[str, str]] | None = None) -> dict[str, Any]:
    import subprocess
    from urllib.parse import urlencode

    load_dotenv(override=False)
    sk = (os.environ.get("STRIPE_SECRET_KEY") or "").strip()
    if not sk:
        return {"error": {"message": "STRIPE_SECRET_KEY is not configured in environment."}}
    cmd = ["curl", "-sS", "-X", method.upper(), f"https://api.stripe.com/v1/{endpoint.lstrip('/')}", "-u", f"{sk}:"]
    if form_fields:
        cmd.extend(["-d", urlencode(form_fields)])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15)
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"error": {"message": proc.stderr or proc.stdout or "Stripe API request failed"}}


def ensure_stripe_catalog_and_webhook(webhook_url: str = "https://betscout.app/api/billing/webhook") -> dict[str, Any]:
    """Idempotently provision the 3 BetScout products, 6 EUR recurring prices (monthly + annual),
    and the Stripe webhook endpoint using `STRIPE_SECRET_KEY`."""
    prods_resp = _stripe_api_call("GET", "products?limit=100")
    existing_prods = {
        (p.get("metadata") or {}).get("betscout_tier"): p
        for p in (prods_resp.get("data") or [])
        if isinstance(p, dict) and (p.get("metadata") or {}).get("betscout_tier")
    }
    prices_resp = _stripe_api_call("GET", "prices?limit=100")
    existing_prices = {
        (pr.get("metadata") or {}).get("betscout_price_key"): pr
        for pr in (prices_resp.get("data") or [])
        if isinstance(pr, dict) and (pr.get("metadata") or {}).get("betscout_price_key") and pr.get("active")
    }

    catalog_out: dict[str, Any] = {}
    for tier_k, spec in STRIPE_PLANS_SPEC.items():
        m_key = spec["meta_key"]
        prod = existing_prods.get(m_key)
        if not prod:
            prod = _stripe_api_call(
                "POST",
                "products",
                [
                    ("name", spec["name"]),
                    ("description", spec["description"]),
                    ("metadata[betscout_tier]", m_key),
                    ("metadata[plan_tier]", spec["plan_tier"]),
                ],
            )
        prod_id = prod.get("id")
        if not prod_id:
            continue

        tier_prices: dict[str, str] = {}
        for cyc, interval, cents in (
            ("monthly", "month", spec["monthly_cents"]),
            ("annual", "year", spec["annual_cents"]),
        ):
            p_key = f"{tier_k}_{cyc}"
            pr = existing_prices.get(p_key)
            if not pr or int(pr.get("unit_amount") or 0) != cents:
                pr = _stripe_api_call(
                    "POST",
                    "prices",
                    [
                        ("product", str(prod_id)),
                        ("currency", "eur"),
                        ("unit_amount", str(cents)),
                        ("recurring[interval]", interval),
                        ("nickname", f"{spec['name']} ({cyc.capitalize()})"),
                        ("metadata[betscout_price_key]", p_key),
                        ("metadata[plan_tier]", spec["plan_tier"]),
                        ("metadata[billing_cycle]", cyc),
                    ],
                )
            if pr.get("id"):
                tier_prices[cyc] = str(pr["id"])

        catalog_out[tier_k] = {
            "product_id": prod_id,
            "name": spec["name"],
            "plan_tier": spec["plan_tier"],
            "prices": tier_prices,
        }

    # Ensure webhook endpoint is registered
    wh_resp = _stripe_api_call("GET", "webhook_endpoints?limit=50")
    existing_wh = next(
        (w for w in (wh_resp.get("data") or []) if isinstance(w, dict) and w.get("url") == webhook_url),
        None,
    )
    if not existing_wh and webhook_url.startswith("https://"):
        existing_wh = _stripe_api_call(
            "POST",
            "webhook_endpoints",
            [
                ("url", webhook_url),
                ("description", "BetScout Cloud Run Subscription & API Key Provisioning Webhook"),
                ("enabled_events[0]", "checkout.session.completed"),
                ("enabled_events[1]", "customer.subscription.created"),
                ("enabled_events[2]", "customer.subscription.updated"),
                ("enabled_events[3]", "customer.subscription.deleted"),
            ],
        )

    return {
        "ok": True,
        "catalog": catalog_out,
        "webhook_id": (existing_wh or {}).get("id"),
        "webhook_url": webhook_url,
    }


def create_stripe_checkout_session(
    tier: str = "tier2",
    cycle: str = "monthly",
    customer_email: str | None = None,
    origin: str = "https://betscout.app",
) -> dict[str, Any]:
    """Create a live Stripe Checkout Session for Tier 1, Tier 2, or Tier 3 (`monthly` or `annual`)
    and return `{ok, checkout_url, session_id}`."""
    norm_t = str(tier or "tier2").lower().strip()
    if norm_t in ("1", "vip", "tier_1", "tier1"):
        t_key = "tier1"
    elif norm_t in ("3", "api", "enterprise", "tier_3", "tier3"):
        t_key = "tier3"
    else:
        t_key = "tier2"

    norm_c = "annual" if str(cycle or "").lower().strip() in ("annual", "yearly", "year") else "monthly"
    spec = STRIPE_PLANS_SPEC[t_key]
    cents = spec["annual_cents"] if norm_c == "annual" else spec["monthly_cents"]
    interval = "year" if norm_c == "annual" else "month"
    clean_origin = (origin or "https://betscout.app").rstrip("/")

    fields: list[tuple[str, str]] = [
        ("mode", "subscription"),
        ("success_url", f"{clean_origin}/app?checkout=success&tier={t_key}&session_id={{CHECKOUT_SESSION_ID}}"),
        ("cancel_url", f"{clean_origin}/#pricing"),
        ("allow_promotion_codes", "true"),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", "eur"),
        ("line_items[0][price_data][unit_amount]", str(cents)),
        ("line_items[0][price_data][recurring][interval]", interval),
        ("line_items[0][price_data][product_data][name]", spec["name"]),
        ("line_items[0][price_data][product_data][description]", spec["description"]),
        ("metadata[plan_tier]", spec["plan_tier"]),
        ("metadata[tier_key]", t_key),
        ("metadata[billing_cycle]", norm_c),
        ("subscription_data[metadata][plan_tier]", spec["plan_tier"]),
        ("subscription_data[metadata][tier_key]", t_key),
    ]
    if customer_email and "@" in customer_email:
        fields.append(("customer_email", customer_email.strip()))
        fields.append(("metadata[email]", customer_email.strip().lower()))

    sess = _stripe_api_call("POST", "checkout/sessions", fields)
    if sess.get("url"):
        return {
            "ok": True,
            "session_id": sess.get("id"),
            "checkout_url": sess.get("url"),
            "tier": t_key,
            "plan_tier": spec["plan_tier"],
            "cycle": norm_c,
        }
    return {
        "ok": False,
        "error": (sess.get("error") or {}).get("message") or "Could not create Stripe Checkout session.",
    }


def verify_and_provision_stripe_session(db_path: Path, session_id: str) -> dict[str, Any]:
    """Verify a completed Stripe Checkout `session_id` via the Stripe API, activate the subscriber in `subscribers`,
    and auto-provision a `bs_live_...` API key in `api_keys` when Tier 3 (`enterprise` / `api`) was purchased."""
    sid = str(session_id or "").strip()
    if not sid.startswith("cs_"):
        return {"ok": False, "error": "Invalid Stripe Checkout session_id."}

    sess = _stripe_api_call("GET", f"checkout/sessions/{sid}")
    if sess.get("error"):
        return {"ok": False, "error": (sess["error"] or {}).get("message") or "Stripe session lookup failed."}

    status = str(sess.get("status") or "").lower()
    pay_status = str(sess.get("payment_status") or "").lower()
    if status != "complete" and pay_status != "paid":
        return {"ok": False, "error": f"Checkout session is not completed yet (status={status}, payment_status={pay_status})."}

    email = str(
        ((sess.get("customer_details") or {}).get("email"))
        or sess.get("customer_email")
        or ((sess.get("metadata") or {}).get("email"))
        or "subscriber@betscout.app"
    ).strip().lower()
    plan_tier = str((sess.get("metadata") or {}).get("plan_tier") or "pro").lower()
    sub = upsert_subscriber(
        db_path=db_path,
        email=email,
        plan_tier=plan_tier,
        status="active",
        stripe_customer_id=str(sess.get("customer") or ""),
        stripe_subscription_id=str(sess.get("subscription") or sid),
    )

    issued_key: dict[str, Any] | None = None
    if plan_tier in ("enterprise", "api_pro", "api_starter"):
        lbl = f"Stripe Session {sid[:20]}"
        existing = [k for k in list_api_keys(db_path) if k.get("label") == lbl and k.get("active")]
        if not existing:
            issued_key = create_api_key(
                db_path,
                owner_email=email,
                plan_tier="enterprise" if plan_tier == "enterprise" else "pro",
                label=lbl,
            )

    return {
        "ok": True,
        "session_id": sid,
        "email": email,
        "plan_tier": plan_tier,
        "subscriber": sub,
        "api_key": (issued_key or {}).get("api_key"),
        "key_prefix": (issued_key or {}).get("key_prefix"),
    }


def build_openapi_v1_spec() -> dict[str, Any]:
    """Return the complete OpenAPI 3.1.0 specification for BetScout's Backend & Paid Developer API."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "BetScout Quantitative Sports Edge & Score Intelligence API",
            "version": "1.0.0",
            "description": (
                "Official OpenAPI 3.1 specification for BetScout's quantitative prediction, "
                "Dixon-Coles 28-score & tennis set-score dutching matrices, high-probability banker combos, "
                "bookmaker mispricing dislocations, real-time in-play SSE streams, and audited paper-betting ledger."
            ),
        },
        "tags": [
            {"name": "Model Context Protocol (MCP) Server", "description": "Remote Streamable HTTP JSON-RPC 2.0 MCP endpoint (https://betscout.app/mcp) exposing 7 quantitative tools for Claude, GitHub Copilot, Cursor & Windsurf"},
            {"name": "Quant Desk & Live Feed", "description": "Endpoints powering the BetScout WebApp Desk & real-time SSE stream"},
            {"name": "Commercial Syndicate API (v1)", "description": "Metered B2B REST endpoints authenticated via X-API-Key or Bearer token"},
            {"name": "Admin & Pipeline Operations", "description": "Protected settlement, rescan, and Discord/Telegram publishing endpoints"},
        ],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                "BearerAuth": {"type": "http", "scheme": "bearer"},
            }
        },
        "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
        "paths": {
            "/mcp": {
                "get": {
                    "tags": ["Model Context Protocol (MCP) Server"],
                    "summary": "Discover BetScout MCP Server metadata, protocol version (2024-11-05) & all 7 registered tools",
                    "responses": {"200": {"description": "MCP server capabilities & 7 tool JSON schemas"}},
                },
                "post": {
                    "tags": ["Model Context Protocol (MCP) Server"],
                    "summary": "Execute MCP JSON-RPC 2.0 requests (initialize, ping, tools/list, tools/call)",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "jsonrpc": {"type": "string", "default": "2.0"},
                                        "id": {"type": "integer", "default": 1},
                                        "method": {
                                            "type": "string",
                                            "enum": ["initialize", "ping", "tools/list", "tools/call"],
                                            "default": "tools/call",
                                        },
                                        "params": {
                                            "type": "object",
                                            "example": {
                                                "name": "analyze_matchup",
                                                "arguments": {"query": "Tommy Paul vs Luciano Darderi"},
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "JSON-RPC 2.0 MCP response"}},
                },
            },
            "/api/cache-stats": {
                "get": {
                    "tags": ["Quant Desk & Live Feed"],
                    "summary": "Inspect multi-tier L1 In-Memory + L2 Persistent Cache hit/miss & negative-cache telemetry",
                    "responses": {"200": {"description": "Cache telemetry and hit rate %"}},
                }
            },
            "/api/snapshot": {
                "get": {
                    "tags": ["Quant Desk & Live Feed"],
                    "summary": "Get complete role-aware Quant Desk snapshot (Picks, Ledger, Combos, Backtest & Auth config)",
                    "parameters": [
                        {"name": "sport", "in": "query", "schema": {"type": "string", "default": "all"}},
                        {"name": "min_odds", "in": "query", "schema": {"type": "number", "default": 1.10}},
                    ],
                    "responses": {"200": {"description": "Role-aware live snapshot JSON"}},
                }
            },
            "/api/matchup": {
                "get": {
                    "tags": ["Quant Desk & Live Feed"],
                    "summary": "Inspect historical H2H meetings and Last-6 form for a specific matchup",
                    "parameters": [
                        {"name": "home", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "away", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "league", "in": "query", "required": False, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "H2H and rolling form breakdown"}},
                }
            },
            "/api/analyze-live": {
                "get": {
                    "tags": ["Quant Desk & Live Feed"],
                    "summary": "Run on-demand multi-market quantitative analysis for any live or upcoming matchup",
                    "parameters": [
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string", "example": "Roma vs Cagliari"}},
                    ],
                    "responses": {"200": {"description": "Live matchup evaluation & fair odds"}},
                }
            },
            "/api/stream": {
                "get": {
                    "tags": ["Quant Desk & Live Feed"],
                    "summary": "Subscribe to 6-second real-time Server-Sent Events (SSE) for in-play scores & settlements",
                    "responses": {"200": {"description": "text/event-stream SSE feed"}},
                }
            },
            "/api/version": {
                "get": {
                    "tags": ["Quant Desk & Live Feed"],
                    "summary": "Get current BetScout engine version and latest recommendation snapshot timestamp",
                    "responses": {"200": {"description": "Version metadata"}},
                }
            },
            "/api/v1/picks": {
                "get": {
                    "tags": ["Commercial Syndicate API (v1)"],
                    "summary": "List upcoming high-conviction picks across all 10 sports (Starter+)",
                    "parameters": [
                        {"name": "sport", "in": "query", "schema": {"type": "string", "default": "all"}},
                        {"name": "min_odds", "in": "query", "schema": {"type": "number", "default": 1.15}},
                    ],
                    "responses": {"200": {"description": "Calibrated upcoming picks"}},
                }
            },
            "/api/v1/ledger": {
                "get": {
                    "tags": ["Commercial Syndicate API (v1)"],
                    "summary": "Get verified settled paper-betting ledger, ROI, CLV & sport/tier attribution (Starter+)",
                    "responses": {"200": {"description": "Prospective paper-bet ledger summary"}},
                }
            },
            "/api/v1/dutching": {
                "get": {
                    "tags": ["Commercial Syndicate API (v1)"],
                    "summary": "Get 28-score Dixon-Coles & tennis set-score equal-payout dutching matrices (Pro+)",
                    "parameters": [
                        {"name": "stake", "in": "query", "schema": {"type": "number", "default": 25.0}},
                    ],
                    "responses": {"200": {"description": "Exact-score & set-score dutching splits"}},
                }
            },
            "/api/v1/combos": {
                "get": {
                    "tags": ["Commercial Syndicate API (v1)"],
                    "summary": "Get recommended 2-leg high-probability combos & parlays across 4 archetypes (Pro+)",
                    "responses": {"200": {"description": "Recommended 2-leg & banker booster combos"}},
                }
            },
            "/api/v1/mispriced": {
                "get": {
                    "tags": ["Commercial Syndicate API (v1)"],
                    "summary": "Get confirmed bookmaker odds mispricings (>= +2.0pp edge & >= +2.0% EV) (Pro+)",
                    "responses": {"200": {"description": "Mispriced bookmaker lines"}},
                }
            },
            "/api/v1/analyze": {
                "get": {
                    "tags": ["Commercial Syndicate API (v1)"],
                    "summary": "Run on-demand live matchup analysis for any Tennis or Football pair (Pro+)",
                    "parameters": [
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Quantitative matchup analysis"}},
                }
            },
            "/api/sync": {
                "post": {
                    "tags": ["Admin & Pipeline Operations"],
                    "summary": "Settle finished paper-bets against official match results and optionally rescan live odds (Admin/Cron)",
                    "responses": {"200": {"description": "Sync & settlement result"}},
                }
            },
            "/api/daily-digest": {
                "post": {
                    "tags": ["Admin & Pipeline Operations"],
                    "summary": "Run morning rescan and publish Daily High-Conviction Slate + Free Teaser to Discord/Telegram",
                    "responses": {"200": {"description": "Daily digest dispatch result"}},
                }
            },
        },
    }


def build_swagger_ui_html() -> str:
    """Return a themed interactive Swagger UI + Remote MCP Server Documentation page for `/api/docs` and `/mcp/docs`."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BetScout — Quant API &amp; Remote MCP Server Documentation</title>
  <link rel="icon" type="image/svg+xml" href="/betscout-logo.svg" />
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css" />
  <style>
    body { margin: 0; background: #070b12; color: #f1f5f9; font-family: system-ui, -apple-system, sans-serif; }
    .bs-topbar {
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 24px; background: #0d1422; border-bottom: 1px solid #1e293b;
    }
    .bs-brand { display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 16px; color: #f8fafc; text-decoration: none; }
    .bs-links { display: flex; gap: 12px; }
    .bs-btn {
      padding: 7px 14px; border-radius: 8px; font-size: 12.5px; font-weight: 600;
      text-decoration: none; color: #e2e8f0; background: #131c2e; border: 1px solid #334155;
    }
    .bs-btn:hover { border-color: #38bdf8; color: #38bdf8; }
    .mcp-banner {
      max-width: 1280px; margin: 18px auto 0; padding: 20px 24px;
      background: linear-gradient(145deg, rgba(30,43,68,0.85), rgba(14,21,36,0.92));
      border: 1px solid rgba(56,189,248,0.35); border-radius: 14px; box-sizing: border-box;
    }
    .mcp-banner h2 { margin: 0 0 8px; font-size: 18px; color: #38bdf8; }
    .mcp-banner p { margin: 0 0 12px; font-size: 13.5px; color: #cbd5e1; line-height: 1.5; }
    .mcp-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; margin-top: 12px; align-items: stretch; }
    .mcp-box { background: #090e1a; border: 1px solid #1e293b; border-radius: 10px; padding: 14px; font-size: 12.5px; display: flex; flex-direction: column; }
    .mcp-box pre { margin: 8px 0 0; padding: 12px; background: #050811; border: 1px solid #162033; border-radius: 8px; overflow-x: auto; color: #34d399; font-size: 11.5px; line-height: 1.5; flex: 1; }
    .mcp-tools-list { margin: 8px 0 0; padding-left: 18px; color: #e2e8f0; line-height: 1.72; }
    .mcp-tools-list code { color: #fde047; font-weight: 700; }
    .mcp-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .mcp-tab-btn {
      padding: 5px 11px; border-radius: 7px; font-size: 11.5px; font-weight: 700; cursor: pointer;
      background: #111a2e; color: #94a3b8; border: 1px solid #263552; transition: border-color 0.15s, color 0.15s, background-color 0.15s;
    }
    .mcp-tab-btn:hover { color: #e2e8f0; border-color: #38bdf8; }
    .mcp-tab-btn.active { background: rgba(56,189,248,0.18); color: #38bdf8; border-color: #38bdf8; }
    .mcp-cfg-pane { display: none; flex-direction: column; flex: 1; }
    .mcp-cfg-pane.active { display: flex; }
    .mcp-cfg-hint { font-size: 11.5px; color: #94a3b8; margin-top: 8px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .mcp-cfg-hint code { color: #7dd3fc; }
    .mcp-copy-btn {
      padding: 3px 9px; border-radius: 5px; font-size: 11px; font-weight: 600; cursor: pointer;
      background: #132038; color: #7dd3fc; border: 1px solid rgba(56,189,248,0.4);
    }
    .mcp-copy-btn:hover { background: rgba(56,189,248,0.2); }
    #swagger-ui { max-width: 1280px; margin: 18px auto 32px; padding: 16px; background: #f8fafc; border-radius: 14px; box-sizing: border-box; }
    .swagger-ui .topbar { display: none; }
  </style>
</head>
<body>
  <header class="bs-topbar">
    <a href="/" class="bs-brand">
      <img src="/betscout-logo.svg" width="28" height="28" alt="BetScout" />
      <span>BetScout · Quant REST API &amp; Remote MCP Server Documentation</span>
    </a>
    <nav class="bs-links">
      <a href="/mcp" class="bs-btn">Remote MCP Discovery (/mcp)</a>
      <a href="/" class="bs-btn">Home &amp; Membership Plans</a>
      <a href="/app" class="bs-btn">Open Live Quant Desk</a>
    </nav>
  </header>
  <section class="mcp-banner">
    <h2>🤖 Tier 3 Remote MCP Server (<code>https://betscout.app/mcp</code>)</h2>
    <p>
      Connect <strong>Claude</strong>, <strong>VS Code GitHub Copilot</strong>, <strong>Cursor</strong>, <strong>Windsurf</strong>, or any MCP-compatible AI agent directly to BetScout's hosted quantitative engine over <strong>Streamable HTTP JSON-RPC 2.0</strong> at <code>https://betscout.app/mcp</code> using your Tier 3 Quant API key.
    </p>
    <div class="mcp-grid">
      <div class="mcp-box">
        <strong>7 Registered Model-Oriented MCP Tools:</strong>
        <ul class="mcp-tools-list">
          <li><code>get_daily_banker_picks</code> — Active multi-sport banker slate &amp; mispriced edges (cursor paginated)</li>
          <li><code>get_banker_profit_boosters</code> — 2-leg &amp; 3-leg high-prob (&ge;72%) combo tickets &amp; ¼-Kelly stakes</li>
          <li><code>analyze_matchup</code> — On-demand live Football / Tennis Elo + set-score &amp; turnaround analysis</li>
          <li><code>calculate_exact_score_dutching</code> — Equal-payout EUR stake split across top Exact Scores / Set Scores</li>
          <li><code>get_match_center_dossier</code> — Full 56-sport Match Center dossier (Win Prob, 28 Correct Scores, H2H, Injuries)</li>
          <li><code>search_daily_fixtures</code> — Search daily schedules &amp; match IDs across 56 sports (cursor paginated)</li>
          <li><code>get_paper_ledger_roi</code> — Audited Paper-Betting Ledger (75W–1L, ROI%, CLV%, by-sport breakdown)</li>
        </ul>
      </div>
      <div class="mcp-box">
        <strong>Remote MCP Quick Configuration:</strong>
        <div class="mcp-tabs" role="tablist" aria-label="Agentic Tool MCP Configurations">
          <button type="button" class="mcp-tab-btn active" onclick="switchMcpTab('claude', this)">Claude</button>
          <button type="button" class="mcp-tab-btn" onclick="switchMcpTab('copilot', this)">VS Code Copilot</button>
          <button type="button" class="mcp-tab-btn" onclick="switchMcpTab('cursor', this)">Cursor</button>
          <button type="button" class="mcp-tab-btn" onclick="switchMcpTab('windsurf', this)">Windsurf / Cline</button>
          <button type="button" class="mcp-tab-btn" onclick="switchMcpTab('curl', this)">cURL / HTTP</button>
        </div>

        <div id="mcp-pane-claude" class="mcp-cfg-pane active">
          <div class="mcp-cfg-hint">
            <span>Claude Code CLI or <code>.mcp.json</code></span>
            <button type="button" class="mcp-copy-btn" onclick="copyMcpSnippet('mcp-code-claude', this)">Copy</button>
          </div>
          <pre id="mcp-code-claude"># Option 1 — Claude Code CLI:
claude mcp add --transport http betscout https://betscout.app/mcp \\
  --header "Authorization: Bearer bs_live_YOUR_API_KEY"

# Option 2 — .mcp.json:
{
  "mcpServers": {
    "betscout": {
      "type": "http",
      "url": "https://betscout.app/mcp",
      "headers": {
        "Authorization": "Bearer bs_live_YOUR_API_KEY"
      }
    }
  }
}</pre>
        </div>

        <div id="mcp-pane-copilot" class="mcp-cfg-pane">
          <div class="mcp-cfg-hint">
            <span>VS Code <code>.vscode/mcp.json</code> or User Settings</span>
            <button type="button" class="mcp-copy-btn" onclick="copyMcpSnippet('mcp-code-copilot', this)">Copy</button>
          </div>
          <pre id="mcp-code-copilot">{
  "servers": {
    "betscout": {
      "type": "http",
      "url": "https://betscout.app/mcp",
      "headers": {
        "Authorization": "Bearer bs_live_YOUR_API_KEY"
      }
    }
  }
}</pre>
        </div>

        <div id="mcp-pane-cursor" class="mcp-cfg-pane">
          <div class="mcp-cfg-hint">
            <span>Cursor <code>.cursor/mcp.json</code> or Global MCP Settings</span>
            <button type="button" class="mcp-copy-btn" onclick="copyMcpSnippet('mcp-code-cursor', this)">Copy</button>
          </div>
          <pre id="mcp-code-cursor">{
  "mcpServers": {
    "betscout": {
      "url": "https://betscout.app/mcp",
      "headers": {
        "Authorization": "Bearer bs_live_YOUR_API_KEY"
      }
    }
  }
}</pre>
        </div>

        <div id="mcp-pane-windsurf" class="mcp-cfg-pane">
          <div class="mcp-cfg-hint">
            <span>Windsurf / Cline <code>mcp_config.json</code></span>
            <button type="button" class="mcp-copy-btn" onclick="copyMcpSnippet('mcp-code-windsurf', this)">Copy</button>
          </div>
          <pre id="mcp-code-windsurf">{
  "mcpServers": {
    "betscout": {
      "serverUrl": "https://betscout.app/mcp",
      "headers": {
        "X-API-Key": "bs_live_YOUR_API_KEY"
      }
    }
  }
}</pre>
        </div>

        <div id="mcp-pane-curl" class="mcp-cfg-pane">
          <div class="mcp-cfg-hint">
            <span>Direct JSON-RPC 2.0 <code>POST https://betscout.app/mcp</code></span>
            <button type="button" class="mcp-copy-btn" onclick="copyMcpSnippet('mcp-code-curl', this)">Copy</button>
          </div>
          <pre id="mcp-code-curl">curl -X POST https://betscout.app/mcp \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer bs_live_YOUR_API_KEY" \\
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_daily_banker_picks",
      "arguments": { "sport": "all", "min_win_prob": 0.70 }
    }
  }'</pre>
        </div>
      </div>
    </div>
  </section>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script>
    function switchMcpTab(tabId, btnEl) {
      document.querySelectorAll('.mcp-tab-btn').forEach(function(b) { b.classList.remove('active'); });
      document.querySelectorAll('.mcp-cfg-pane').forEach(function(p) { p.classList.remove('active'); });
      if (btnEl) btnEl.classList.add('active');
      var pane = document.getElementById('mcp-pane-' + tabId);
      if (pane) pane.classList.add('active');
    }
    function copyMcpSnippet(preId, btnEl) {
      var el = document.getElementById(preId);
      if (!el || !navigator.clipboard) return;
      navigator.clipboard.writeText(el.innerText).then(function() {
        var orig = btnEl.textContent;
        btnEl.textContent = 'Copied!';
        setTimeout(function() { btnEl.textContent = orig; }, 1600);
      });
    }
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: '/api/v1/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        docExpansion: 'list',
        persistAuthorization: true
      });
    };
  </script>
</body>
</html>
"""
