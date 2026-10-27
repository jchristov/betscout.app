# BetScout Commercial Monetization Blueprint (`betscout.app`)

This document details the technical, product, and billing architecture to monetize **BetScout** across three independent, high-margin revenue streams on top of the **Option D (Firebase Hosting + Firebase Auth + Cloud Run + SQLite)** stack:

1. **Stream 1 — Paid B2B / Developer API (`api.betscout.app` / `/api/v1/*`):** Metered API keys (`X-API-Key: bs_live_...`), tiered rate limits, usage analytics, and OpenAPI/RapidAPI/Stripe distribution for 3rd-party apps, syndicates, and automated betting systems.
2. **Stream 2 — Paid SaaS WebApp / PWA (`betscout.app`):** Freemium + Pro subscription tiers using **Firebase Auth + Stripe Checkout**, where paying subscribers get full real-time read-only access (plus personal bankroll/slip tools), while free/anonymous visitors see the verified historical ledger + 1–2 unlocked daily preview picks (with `top_8pct` / `banker_70pct` / `💎 Mispriced` picks blurred behind a `🔒 Unlock Pro` paywall).
3. **Stream 3 — Paid VIP Discord & Telegram Channels:** Automated membership gating via **Whop / LaunchPass / Stripe Discord Role Sync** (or multi-tenant customer webhooks), plus Free Teaser vs. VIP Full-Slate dual-channel broadcasting.

---

## 1. Unified Architecture: How Billing, Auth & Delivery Fit Together

```
                          ┌────────────────────────────────────────┐
                          │         Stripe / Whop Billing          │
                          │ • Checkout Sessions & Customer Portal  │
                          │ • Webhooks (`POST /api/billing/webhook`)│
                          └───────────────────┬────────────────────┘
                                              │ Updates entitlements
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                  BetScout Cloud Run Service (`betscout.db` + Auth)               │
│  New SQLite Tables:                                                                 │
│   • `subscribers(uid, email, tier, stripe_customer_id, status, expires_at)`         │
│   • `api_keys(key_hash, key_prefix, owner_email, tier, daily_quota, calls_today)`   │
│   • `subscriber_webhooks(id, owner_email, channel_type, url_or_chat_id, sports)`    │
└───────────┬─────────────────────────────────┬───────────────────────────────────────┘
            │                                 │                                       │
            ▼ Stream 1                        ▼ Stream 2                              ▼ Stream 3
┌───────────────────────┐         ┌───────────────────────────┐           ┌───────────────────────────┐
│   1. Paid Developer   │         │  2. Paid Read-Only WebApp │           │  3. Paid VIP Discord &    │
│      REST API         │         │     (`betscout.app`)      │           │     Telegram Channels     │
│ • `X-API-Key` header  │         │ • Free: Ledger + 2 Picks  │           │ • VIP Channels: Full      │
│ • `/api/v1/picks`     │         │   (Top picks blurred 🔒)  │           │   Slate + 1080×580 PNGs   │
│ • `/api/v1/dutching`  │         │ • Pro (€29/m): All Picks, │           │ • Free Public Channel:    │
│ • `/api/v1/analyze`   │         │   3s Live Stream, H2H,    │           │   Settled Wins Recap +    │
│ • `/api/v1/ledger`    │         │   Dutching & Bet Slip     │           │   1 Free Pick of the Day  │
└───────────────────────┘         └───────────────────────────┘           └───────────────────────────┘
```

---

## 2. Stream 1: Paid Developer & 3rd-Party Integration API (`/api/v1/*`)

### A. Product Packaging & Pricing Tiers
Expose a clean, versioned `/api/v1/*` JSON surface (separate from the internal UI routes) authenticated via `X-API-Key: bs_live_<32_chars>` or `Authorization: Bearer bs_live_<32_chars>`:

| API Tier | Price | Quota | Included Endpoints |
|---|---|---|---|
| **Starter API** | **€49 / mo** | `500 req / day` (`10 req/min`) | `GET /api/v1/picks` (daily moneyline picks), `GET /api/v1/ledger` (verified track record) |
| **Pro Quant API** | **€149 / mo** | `5,000 req / day` (`60 req/min`) | Everything in Starter + `GET /api/v1/dutching` (Dixon-Coles 28-score & set-score matrices), `GET /api/v1/combos` (2-leg parlays), `GET /api/v1/mispriced` (`💎` edge dislocations), `GET /api/v1/analyze` (on-demand matchup analyzer) |
| **Enterprise / Syndicate** | **€399 / mo** | `50,000 req / day` + Webhook Push | Everything in Pro + real-time push webhooks whenever a new pick, `🔥 STEAM` move, or T-60m Starting XI veto triggers + PNG Pick Card binary endpoint (`GET /api/v1/pick-card.png`) |

### B. Technical Adjustments Required for Stream 1
1. **`api_keys` & `api_usage_daily` Tables in `betscout.db`:**
   ```sql
   CREATE TABLE IF NOT EXISTS api_keys (
       key_id TEXT PRIMARY KEY,
       key_hash TEXT NOT NULL UNIQUE,      -- SHA-256 hash of `bs_live_...` (never store raw key)
       key_prefix TEXT NOT NULL,           -- e.g. `bs_live_9f8a...` for display
       owner_email TEXT NOT NULL,
       plan_tier TEXT NOT NULL DEFAULT 'starter', -- 'starter' | 'pro' | 'enterprise'
       daily_limit INTEGER NOT NULL DEFAULT 500,
       rate_limit_per_min INTEGER NOT NULL DEFAULT 10,
       allowed_sports TEXT DEFAULT 'all',
       active INTEGER NOT NULL DEFAULT 1,
       created_at TEXT NOT NULL,
       expires_at TEXT
   );
   CREATE TABLE IF NOT EXISTS api_usage_daily (
       key_id TEXT NOT NULL,
       date_ymd TEXT NOT NULL,
       calls_count INTEGER NOT NULL DEFAULT 0,
       PRIMARY KEY (key_id, date_ymd)
   );
   ```
2. **Token-Bucket & Daily Quota Middleware in `webapp.py`:**
   - Validate `X-API-Key` by hashing with `hashlib.sha256`, checking `active == 1` and `calls_count < daily_limit`, and returning standard rate-limit headers:
     - `X-RateLimit-Limit: 5000`
     - `X-RateLimit-Remaining: 4812`
     - `X-RateLimit-Reset: 2026-10-27T00:00:00Z`
3. **OpenAPI 3.1 Spec (`GET /api/v1/openapi.json` + `/docs`):**
   - Auto-serve an interactive Swagger/Redoc API documentation page at `/api/docs` and publish the OpenAPI spec to **RapidAPI Hub** (which also handles global billing/invoicing automatically if you want a secondary B2B acquisition channel alongside Stripe).

---

## 3. Stream 2: Paid Read-Only WebApp Access (`betscout.app`)

### A. Freemium vs. Paid Pro Subscriber Experience
Instead of a hard login wall that blocks new visitors from seeing why BetScout is valuable, use a **"Proof-First Freemium Paywall"**:

| Role | What They Can See & Do in `betscout.app` | What Is Locked / Masked |
|---|---|---|
| **1. Anonymous / Free User** (`€0`) | • **100% of Settled Ledger (`44W – 2L`, `95.7%`, `+17.05u`)**, Equity Curves & Walk-Forward Audit (proves the model works!)<br>• **First 2 Upcoming Picks of the Day** (lowest tier / earliest kickoff) fully visible as a free sample | • All remaining upcoming picks, **💎 Mispriced Edges**, **2-Leg Combos**, **Exact-Score Dutching**, and **On-Demand Analyzer** have team/pick names masked (`🔒 Pro Pick · 79.4% WinProb · @1.44`) with a 1-click **`🚀 Unlock All Picks (€29/mo)`** button.<br>• All Admin buttons (`Sync`, `Rescan`, `Pipeline`, `Share`, global `Settings`) are hidden. |
| **2. Paying Subscriber (`Pro`)** (`€29/mo` or `€199/yr`) | • **Full Read-Only Access to All 10 Sports:** All Best Bets, Football Factor Cards, Tennis & Major League tables, 2-Leg Combos, `💎 Mispriced` Detector, and 3-second Live In-Play Stream.<br>• **Full Interactive Calculators:** Smart Bet Slip Optimizer, Exact-Score Dutching Splitter, H2H Drill-Down Modal, and On-Demand Matchup Analyzer.<br>• **Personal Local Preferences:** Can set their own Bankroll (€), toggle sports on/off locally, and export CSV/PDF slips. | • **Read-Only on Server State:** Cannot trigger server-wide `Full Pipeline`, modify global server settings/webhooks, or broadcast to your official Discord/Telegram channels. |
| **3. Admin (`You`)** | • Everything in Pro + full Admin control bar (`🔄 Sync & Settle`, `⚡ Rescan Live`, `🚀 Full Pipeline`, `📌 Track Live`, `💬 Share Picks` to official channels, `⚙️ Server Settings`). | — |

### B. Technical Adjustments Required for Stream 2
1. **Server-Side Payload Redaction (`_redact_snapshot_for_role` in `webapp.py` and `dashboard.py`):**
   - **Critical Security Rule:** Never rely on CSS blur alone (`filter: blur(5px)`) to hide paid picks—savvy users can inspect DOM elements in DevTools!
   - When a request to `/`, `/api/data`, or `/api/stream` does **not** carry a valid `pro` or `admin` token (and `MONETIZATION_ENABLED=true`):
     - Keep `settled` ledger rows 100% intact.
     - Keep the first `FREE_PREVIEW_PICKS_COUNT=2` lowest-edge picks intact.
     - Redact all remaining upcoming picks, combos, and mispriced rows **on the server before sending HTML/JSON** (`pick_name -> "🔒 Pro Subscriber Pick"`, `exact_score_pick -> "🔒 Pro Score Cluster"`, keeping only `kickoff`, `sport_icon`, `win_prob`, and `odds` visible to entice upgrades!).
2. **Stripe Checkout + Customer Portal Integration (`POST /api/billing/checkout` & `POST /api/billing/webhook`):**
   - User signs in with Google (`Firebase Auth`), clicks **`🚀 Upgrade to Pro`**, and is redirected to a Stripe Checkout session pre-filled with their `firebase_uid` and `email`.
   - When Stripe fires `checkout.session.completed` or `customer.subscription.Updated/Deleted` to `POST /api/billing/webhook`, `webapp.py` updates the `subscribers` table in `betscout.db` (and optionally sets a Firebase Custom Claim `{"role": "pro"}`).

---

## 4. Stream 3: Paid Telegram & Discord Channels (VIP Signals & B2B Feed Syndication)

You already have a multi-channel Discord publisher (`GLOBAL` + 8 dedicated per-sport webhooks) and a Telegram Bot publisher with 1080×580 PNG Pick Cards. Here is how to monetize those channels at scale:

### A. Two-Tier Channel Funnel (Free Teaser Channel $\rightarrow$ Paid VIP Channels)
1. **Free Public "Teaser & Results" Channel (Discord + Telegram):**
   - **Morning Post (`09:00 CET`):** Posts **1 Free Pick of the Day** (with PNG Pick Card) + a summary line: *"🔒 11 more High-Conviction Picks (`3 💎 Mispriced Edges`, `4 Combos`) posted in VIP today — Join VIP at betscout.app"*.
   - **Evening / Settlement Post (Automatic):** Posts the **full Settled Paper-Bet Recap** (`✅ WIN (+0.56u) Athletic Club`, `✅ WIN (+0.38u) Bayern Munich`, etc.) to the Free channel! Showing verified wins in real time in the free channel is the highest-converting marketing funnel for sports pick communities.
2. **Paid VIP Channels (Your 9 Per-Sport Discord Channels + VIP Telegram Group):**
   - Receives the **full daily slate**, **💎 Mispriced Edges**, **2-Leg Combos**, **Exact-Score Dutching cards**, and **T-60m Starting XI Veto alerts** immediately.

### B. How to Automate Paid Access to Discord & Telegram
You have two clean options (can use either or both):
- **Turnkey Option (Whop / LaunchPass / Stripe Discord App — Zero Custom Bot Code):**
  - Connect your Discord server and private Telegram channel to **Whop.com** or **LaunchPass** (or Stripe's official Discord integration).
  - When a customer pays **€29–€49/mo** (for All-Access VIP or a single-sport pass like *Tennis VIP* / *Football VIP*), Whop/LaunchPass automatically assigns them the `@VIP` or `@Tennis-VIP` Discord role (unlocking your existing per-sport webhook channels!) and kicks them automatically if their card declines or they cancel.
- **B2B "Bring Your Own Webhook" Syndication (`subscriber_webhooks` table):**
  - Community owners or betting groups who pay for the **Syndicate Plan (€149–€299/mo)** can paste their *own* Discord Webhook URL or Telegram Chat ID in their BetScout account settings (`subscriber_webhooks`), and your `send_discord_message` loop automatically fans out your PNG Pick Cards and digests to their channels!

---

## 5. Phased Implementation Roadmap

### Phase 1: Role-Based Access (`Admin` / `Pro` / `Free`) & Server-Side Pick Redaction
- Add `subscribers` and `api_keys` tables to `betscout.db`.
- Add `resolve_request_role(headers)` in `webapp.py` returning `"admin"`, `"pro"`, or `"free"` (defaulting to `"admin"` in local mode when `MONETIZATION_ENABLED` is unset so local development is never restricted).
- Add server-side pick redaction (`_redact_for_free_tier`) so `"free"` users see the full settled ledger + 2 preview picks while premium picks, combos, and exact-score clusters display `🔒 Pro Pick` badges and an upgrade CTA.

### Phase 2: Versioned Developer API (`/api/v1/*`) & API Key Management
- Add `/api/v1/picks`, `/api/v1/dutching`, `/api/v1/combos`, `/api/v1/mispriced`, `/api/v1/analyze`, and `/api/v1/ledger` protected by `X-API-Key` (`bs_live_...`) with daily quota tracking and `X-RateLimit-*` headers.
- Add CLI command `uv run betscout apikey [create|list|revoke]` and an Admin UI panel in `⚙️ Settings` to generate/revoke customer API keys and Pro subscriptions.

### Phase 3: Stripe Checkout & Free-Teaser vs. VIP Discord/Telegram Dual Broadcast
- Add `POST /api/billing/checkout` and `POST /api/billing/webhook` (verifying `Stripe-Signature` HMAC) to automate Pro WebApp & API Key provisioning.
- Add `DISCORD_WEBHOOK_URL_FREE_TEASER` / `TELEGRAM_FREE_CHAT_ID` support in `telegram_bot.py` so 1 free pick + settled win recaps post to your public teaser channel while full slates go to your VIP channels.
