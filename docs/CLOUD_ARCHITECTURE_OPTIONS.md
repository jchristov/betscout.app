# BetScout 24/7 Cloud Architecture Options (`Option A` – `Option E`)

This document catalogs the architectural options for running **BetScout (`betscout.app`)** in the cloud so that:
1. **Your MacBook does NOT need to run 24/7** (the PWA, live 3-second score streaming, on-demand matchup analysis, scheduled scans, settlements, and Discord notifications work even when your MacBook is turned off).
2. **Zero Cloud Functions are required** (no serverless function cold starts, timeouts, or per-invocation billing).
3. **Latency is ultra-low (`<30–80ms`)** (edge CDN delivery, 3-second real-time scores, and sub-50ms analytical queries).
4. **Security is strict** (Discord webhooks and bot tokens never leave server-side secrets; administrative mutations require authenticated Admin credentials while shared viewers get safe read-only access + personal settings).

---

## 1. Why a Pure 100% Firestore Rewrite of the Historical Database Is Avoided

Every pre-match scan (`scan_upcoming_and_log_paper_trades`) and walk-forward calibration reads **26,200+ historical matches** (`matches` + `match_details`) to compute chronological Elo ratings, rolling 6-match boxscore z-scores (`StandardScaler`), and H2H matrices:
- In **SQLite**, scanning 26,200 rows takes **~40ms and costs $0**.
- In **Cloud Firestore**, storing 26,200 historical matches as individual NoSQL documents and reading them on every scan would consume **500,000+ document reads/day** (exceeding the 50,000/day free Spark tier in 2 scans) and add network latency.

Therefore, all options below **keep `matches.sqlite` in native SQLite** for analytical modeling while using edge/cloud primitives for 24/7 delivery and real-time synchronization.

---

## 2. Full Catalog of Architectural Options (`Option A` – `Option E`)

### Option A: Firebase Hosting + Cloud Firestore + Two-Way Sync Bridge *(Zero Cloud Functions)*

**Firebase is used purely as a serverless real-time state & command bus (`Firebase Hosting + Cloud Firestore + Firebase Auth`)**, while the Python quantitative engine (`uv run betscout`) stays 100% in Python/SQLite and syncs outbound over HTTPS.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                Browsers & Mobile Devices (Installed PWA)                │
│  • Served 24/7 from Firebase Hosting (`https://betscout.app`)           │
│  • Subscribes to `state/live_snapshot` via Firestore `onSnapshot()`     │
│  • Sends actions (`Analyze`, `Track Live`, `Sync`) to `commands/{id}`   │
└───────────────────▲─────────────────────────────────────┬───────────────┘
                    │                                     │
   1. Real-Time Push│(WebSocket `onSnapshot`)             │ 2. Write Command Doc
      (<150ms)      │                                     ▼    (`status: "pending"`)
┌───────────────────┴─────────────────────────────────────┴───────────────┐
│                         Google Cloud Firestore                          │
│  • `state/live_snapshot`   (~35 KB: Ledger + Best Bets + Live Scores)   │
│  • `state/picks_catalog`   (~45 KB: Football Cards + Tennis + US Sports)│
│  • `matchups/{pair_slug}`  (~3 KB/doc: On-demand H2H, Form & 28 Scores) │
│  • `commands/{cmd_id}`     (~1 KB/doc: Remote RPC Queue for Admin)      │
│  • `users/{uid}/settings`  (~1 KB/doc: Per-User Bankroll & Sport Prefs) │
└───────────────────▲─────────────────────────────────────┬───────────────┘
                    │                                     │
   4. Diff-Hashed   │(HTTPS REST / gRPC)                  │ 3. Watch `commands`
      Upsert        │                                     ▼    (`status == "pending"`)
┌───────────────────┴─────────────────────────────────────┴───────────────┐
│        Python Quant Engine (GitHub Actions Cloud Worker or Local)       │
│  • Keeps `data/matches.sqlite` (26,227 matches) & 40ms SQL queries      │
│  • Pushes diff-hashed (`sha256`) snapshots to Firestore                 │
│  • Executes `commands/{id}` (On-Demand Analyze, Track Live, Discord)    │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Firestore Data Model (4 Compact Collections — Respects 1 MiB Document Limit)
| Collection / Document Path | Size | Purpose & Sync Frequency |
|---|---|---|
| `state/live_snapshot` | ~35 KB | Compact payload containing `paper_ledger` (settled, live, pending rows, equity curves, KPIs), `best_bets`, `recommended_doubles`, `server_time_local`, and `pipeline_status`. Updated only when a score, odds, or settlement actually changes (diff-hashed). |
| `state/picks_catalog` | ~45 KB | Full `qualifying_picks` (Football factor bars), `tennis_picks`, and `other_sport_picks` for detailed breakdowns. Updated only on `scan` / `pipeline` runs. |
| `matchups/{pair_slug}` | ~3 KB each (~80 docs) | Precomputed H2H, Last-6 Form, squad availability, 15-min goal intervals, and 28-score Correct Score odds (`EMBEDDED_MATCHUP_DETAILS`). Loaded on demand (1 doc read) when a user clicks any match to open `#matchupInspectorModal`. |
| `commands/{cmd_id}` | ~1 KB | Two-way RPC queue for remote actions (`sync`, `rescan`, `pipeline`, `analyze_live`, `track_live`, `untrack_live`, `post_discord`). |
| `users/{uid}/settings` | ~1 KB | Per-user preferences (`bankroll_eur`, `disabled_sports`, `default_sort`, `custom_matches`) synced across all of that user's devices. |

#### Firestore Security Rules (`firestore.rules`) for Multi-User Sharing
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    function isAdmin() {
      return request.auth != null && request.auth.token.email in ["YOUR_ADMIN_EMAIL@gmail.com"];
    }
    // Public or authenticated viewers can read live picks, ledger, and matchup H2H details
    match /state/{docId} {
      allow read: if true;
      allow write: if isAdmin();
    }
    match /matchups/{slug} {
      allow read: if true;
      allow write: if isAdmin();
    }
    match /tracked_live/{eventId} {
      allow read: if true;
      allow write: if isAdmin();
    }
    // Each user can read/write their own personal settings (bankroll, toggled sports, custom slip)
    match /users/{userId}/settings/{docId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    // Only Admin can dispatch remote commands
    match /commands/{cmdId} {
      allow read, create, update, delete: if isAdmin();
    }
  }
}
```

---

### Option B: Distributed Cloud SQLite (`Turso / libSQL` or `Supabase`) + Static Edge PWA

Instead of translating relational SQL into NoSQL documents (Firestore), **keep the relational SQLite schema natively in the cloud** using **Turso (managed libSQL / distributed SQLite)** with embedded replicas:

```
┌─────────────────────────────────────────────────────────────────────────┐
│             Browsers & Mobile PWA (`Firebase Hosting / Pages`)          │
│  • Queries read-only HTTP SQL/JSON API or Turso Read-Only Token         │
│  • Reads `paper_trades` & `recommendations_kv` from nearest edge node   │
└───────────────────────────────────▲─────────────────────────────────────┘
                                    │ HTTPS (30+ Global Edge Replicas <25ms)
┌───────────────────────────────────┴─────────────────────────────────────┐
│                Turso Cloud (libSQL — Managed Cloud SQLite)              │
│  • Exact same tables: `matches`, `match_details`, `paper_trades`,       │
│    `paper_combos`, plus `kv_store(key, json_value, updated_at)`         │
│  • Free Tier: 9 GB storage, 500M rows read/month, 10M rows written/mo   │
└───────────────────────────────────▲─────────────────────────────────────┘
                                    │ `libsql.connect("matches.sqlite", sync_url=...)`
┌───────────────────────────────────┴─────────────────────────────────────┐
│                     Python Quant Engine (`betscout`)                    │
│  • Uses local embedded SQLite file (`40ms` full-history Elo/7-factor)   │
│  • Calls `conn.sync()` after scans/settlements to replicate diffs       │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Pros:** Zero NoSQL translation; 500 million free row reads/month and 9 GB storage; `<25ms` edge SQL reads globally.
- **Cons:** Does not include Firestore's native browser WebSocket `onSnapshot()` push or built-in Google Auth out of the box (unless paired with HTTP conditional `ETag` polling or Supabase Realtime).

---

### Option C: Thick-Client Edge Streaming (`Browser Direct to Sportradar Gismo` + Scheduled GitHub Actions)

Leverages our discovery that `https://stats.fn.sportradar.com` is a direct, tokenless, CORS-enabled JSON API so **the user's browser streams live scores directly without needing any 24/7 polling server**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  Installed PWA in User's Browser / Phone                │
│  1. Loads pre-match `recommendations.json` + compact `elo_state.json`   │
│     from Firebase Hosting / Cloudflare Pages CDN (<25ms)                │
│  2. Browser JS directly polls `stats.fn.sportradar.com/.../gismo/       │
│     match_timelinedelta/{sr_match_id}` every 5s for active live rows!   │
│  3. Computes live PnL, point scores (`15-30🎾`), 1H/76-90m goal edges,   │
│     and On-Demand Matchup Analysis directly in browser JS!              │
└───────────────────────────────────▲─────────────────────────────────────┘
                                    │ Static Deploy (4x/day via GitHub Actions)
┌───────────────────────────────────┴─────────────────────────────────────┐
│          Scheduled Cloud Batch Pipeline (GitHub Actions Cron)           │
│  • Runs `uv run betscout pipeline` in GitHub's cloud (MacBook 100% OFF) │
│  • Caches `data/matches.sqlite` in GitHub Actions Cache                 │
│  • Publishes updated static JSON + sends Discord PNG Pick Card alerts   │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Pros:** **100% serverless 24/7 operation with MacBook completely off**; zero database write quota used for live score ticks; true 3-second live scores directly in the browser.
- **Cons:** Needs Option A (Firestore) if you also want real-time cross-device sync of custom tracked matches (`tracked_live`) and per-user settings.

---

### Option D: Single Always-On Hardened Container (`Fly.io` / `Google Cloud Run` / `Hetzner`) + Persistent NVMe SQLite + Litestream

Run the **exact current `betscout` Python WebApp (`webapp.py` + `matches.sqlite`) 24/7 in a single container** with an attached NVMe SSD volume and **Litestream** continuous WAL backup:

```
┌─────────────────────────────────────────────────────────────────────────┐
│             Users (Desktop & Mobile PWA — `https://betscout.app`)       │
│  • Firebase Hosting CDN + Firebase Auth (Google Sign-In JWT)            │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS + Native `/api/stream` SSE
                                    ▼ (Admin POSTs verified via Firebase JWT)
┌─────────────────────────────────────────────────────────────────────────┐
│         Single Always-On Container (Fly.io / Cloud Run / Hetzner)       │
│  • Runs `uv run betscout --host 0.0.0.0 --port 8090` 24/7               │
│  • Local NVMe SSD Volume `/data/matches.sqlite` (`0.1ms` SQL latency!)  │
│  • Built-in 6s SSE `/api/stream` + 90s auto-poller + Discord PNG cards  │
│  • Litestream sidecar continuously replicates SQLite WAL to GCS / S3    │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Pros:** **Zero code rewrite**; fastest possible SQLite latency (`0.1ms` local NVMe); continuous 90-second background settlement, T-60m Starting XI vetoes, and Pillow PNG Pick Cards run 24/7 without your MacBook.
- **Cons:** Costs **~$3.50–$5.00/month** for an always-on instance (whereas Options A, B, and C are $0/month).

---

### Option E: Zero-Cloud Private Mesh (`Local Machine / Home Mini-PC + Cloudflare Zero-Trust Tunnel`)

Map `https://betscout.app` to `http://127.0.0.1:8090` using `cloudflared tunnel run` protected by **Cloudflare Access** (Google OTP/OAuth login at the edge).
- **Pros:** 5-minute setup, $0 cost, zero code changes.
- **Cons:** **Does NOT satisfy the "MacBook Off" requirement** unless run on a dedicated $100 Raspberry Pi / home mini-PC that stays on 24/7.

---

## 3. Recommended Solutions for **"MacBook Off 24/7 + Low Latency + High Security + No Cloud Functions"**

When your MacBook is turned off, **two architectures** stand out depending on whether you want **$0/month serverless** or **~$4/month dedicated container**:

### 🏆 Recommendation 1 ($0/Month Serverless): **The `Option A + Option C` Hybrid**
Combine **Option A** (`Firebase Hosting + Cloud Firestore + Firebase Auth`) with **Option C** (`Browser-Direct Sportradar 3s Streaming + GitHub Actions Quant Worker`):
1. **MacBook 100% Off:**
   - **UI & State (`<30ms`):** Served from **Firebase Hosting** and synced in real time via **Cloud Firestore** (`onSnapshot`).
   - **Live 3-Second In-Play Scores (`~50ms`):** Browser JS directly queries Sportradar's tokenless `match_timelinedelta/{sr_match_id}` endpoint for ongoing matches in `#liveTradesTable` — works 24/7 with **zero backend server and zero Firestore writes**!
   - **On-Demand Analyzer & `📌 Track Live` (`<15ms`):** Browser JS uses a compact synced `state/elo_team_state` (~120 KB) + live Sportradar `match_markets` to analyze any matchup client-side and saves pinned live matches directly to Firestore `tracked_live/{id}`.
   - **Unattended Scans & Discord Notifications:** A scheduled **GitHub Actions workflow** runs `uv run betscout pipeline --sync-firestore` in GitHub's cloud (with `matches.sqlite` cached in GitHub Actions Cache and `DISCORD_WEBHOOK_URL_*` stored in encrypted GitHub Secrets).
2. **Security:** Firebase Auth + `firestore.rules` lock all global writes to your Google email, while Discord webhooks never leave GitHub Encrypted Secrets.

### 🏆 Recommendation 2 (~$4/Month Dedicated): **`Option D` (Single Container on Fly.io / Cloud Run + Firebase Hosting/Auth)**
If you prefer continuous 90-second server-side background polling (rather than scheduled GitHub Actions crons) with zero client-side logic changes:
- Deploy the repo as a single Docker container on **Fly.io** (or **Cloud Run**) with a 1 GB persistent NVMe volume for `data/matches.sqlite` and put **Firebase Hosting + Firebase Auth** in front of it.

---

## 4. Side-by-Side Comparison Matrix

| Criterion | **Hybrid `Option A + C` (Firebase + Browser Stream + GH Actions)** | **Option D (24/7 Container on Fly.io + NVMe SQLite + Firebase Auth)** | **Option B (Turso Cloud SQLite + Edge PWA)** | **Option A Alone (Firestore + Local Mac Sync)** | **Option E (Local Mac + Cloudflare Tunnel)** |
|---|---|---|---|---|---|
| **Works with MacBook 100% Off?** | ✅ **Yes (24/7)** | ✅ **Yes (24/7)** | ✅ **Yes (24/7)** | ❌ Only static/cached when Mac is off | ❌ No (Mac must stay on) |
| **Uses Cloud Functions?** | ❌ **No** | ❌ **No** | ❌ **No** | ❌ **No** | ❌ **No** |
| **Page & Query Latency** | ⚡ **`<30ms`** (Firebase CDN + local JS) | ⚡ **`<40ms`** (Container NVMe SQLite) | ⚡ **`<30ms`** (Turso Edge Replicas) | ⚡ **`<40ms`** (Firestore cache) | ⚠️ `~60–120ms` (Home uplink) |
| **Live 3s Score Stream** | ⚡ **Browser direct to Sportradar** | ⚡ **Native `/api/stream` SSE** | ⚡ **Browser direct to Sportradar** | ⚠️ Only while Mac pushes diffs | ⚡ Native `/api/stream` SSE |
| **Security & Multi-User Auth** | 🔒 **Firebase Auth + `firestore.rules` + GH Secrets** | 🔒 **Firebase Auth JWT + Container Secrets** | 🔒 **Turso Read-Only Token + GH Secrets** | 🔒 **Firebase Auth + `firestore.rules`** | 🔒 **Cloudflare Access** |
| **Unattended Discord Alerts** | ✅ **Yes (GitHub Actions Cron)** | ✅ **Yes (Continuous 90s thread)** | ✅ **Yes (GitHub Actions Cron)** | ❌ Only while Mac is on | ❌ Only while Mac is on |
| **Monthly Cost** | 💰 **$0.00 / mo** | 💰 **~$4.00 / mo** | 💰 **$0.00 / mo** | 💰 **$0.00 / mo** | 💰 **$0.00 / mo** |
