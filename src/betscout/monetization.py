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
    stripe_Monthly_url = (os.environ.get("STRIPE_CHECKOUT_URL_PRO") or "https://betscout.app/?upgrade=pro").strip()
    stripe_api_url = (os.environ.get("STRIPE_CHECKOUT_URL_API") or "https://betscout.app/?upgrade=api").strip()
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

    return {
        "enabled": env_enabled,
        "free_preview_picks_count": free_preview_n,
        "stripe_checkout_url_pro": stripe_Monthly_url,
        "stripe_checkout_url_api": stripe_api_url,
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
    """Check if `email` is an active paying subscriber (`status == 'active'` and not expired)."""
    if not email or not db_path.exists():
        return False, "free"
    ensure_monetization_tables(db_path)
    norm_email = email.strip().lower()
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


def build_openapi_v1_spec() -> dict[str, Any]:
    """Return the OpenAPI 3.1.0 specification for BetScout's Paid Developer API (`/api/v1/*`)."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "BetScout Quantitative Sports Edge & Score Intelligence API",
            "version": "1.0.0",
            "description": (
                "Commercial REST API providing calibrated multi-sport probabilities, Dixon-Coles exact-score & "
                "tennis set-score dutching matrices, 2-leg uncorrelated parlays, bookmaker mispricing dislocations, "
                "and verified paper-betting ledger attribution."
            ),
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                "BearerAuth": {"type": "http", "scheme": "bearer"},
            }
        },
        "security": [{"ApiKeyAuth": []}, {"BearerAuth": []}],
        "paths": {
            "/api/v1/picks": {
                "get": {
                    "summary": "List upcoming high-conviction picks across all 10 sports (Starter+)",
                    "parameters": [
                        {"name": "sport", "in": "query", "schema": {"type": "string", "default": "all"}},
                        {"name": "min_odds", "in": "query", "schema": {"type": "number", "default": 1.15}},
                    ],
                }
            },
            "/api/v1/ledger": {
                "get": {
                    "summary": "Get verified settled paper-betting ledger, ROI, CLV & sport/tier attribution (Starter+)",
                }
            },
            "/api/v1/dutching": {
                "get": {
                    "summary": "Get 28-score Dixon-Coles & tennis set-score equal-payout dutching matrices (Pro+)",
                    "parameters": [
                        {"name": "stake", "in": "query", "schema": {"type": "number", "default": 25.0}},
                    ],
                }
            },
            "/api/v1/combos": {
                "get": {
                    "summary": "Get recommended 2-leg high-probability combos & parlays across 4 archetypes (Pro+)",
                }
            },
            "/api/v1/mispriced": {
                "get": {
                    "summary": "Get confirmed bookmaker odds mispricings (>= +2.0pp edge & >= +2.0% EV) (Pro+)",
                }
            },
            "/api/v1/analyze": {
                "get": {
                    "summary": "Run on-demand live matchup analysis for any Tennis or Football pair (Pro+)",
                    "parameters": [
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                }
            },
        },
    }
