# <img src="./app/public/betscout-logo.svg" width="34" height="34" align="absmiddle" alt="BetScout Logo"/> BetScout (`betscout.app`) — Sports Edge, Exact-Score & Paper-Betting Intelligence

Out-of-sample validated multi-sport quantitative edge, exact-score dutching, 2-leg combo/parlay, and live paper-betting intelligence platform (`https://betscout.app`) across **7 Core Database Sports & 27 Championships (`59,062` verified matches in `data/betscout.db`)** plus **56 Live Sportradar StatsHub & Tipico Sports**:
- **⚽ 14 Football Competitions (`11,582` matches):** `eng.1`, `esp.1`, `ger.1`, `ita.1`, `fra.1`, `aut.1`, `ned.1`, `por.1`, `eng.2`, `uefa.champions`, `uefa.europa`, `uefa.europa.conf`, `uefa.nations`, `fifa.world`
- **🎾 ATP & WTA Tennis (`43,168` matches):** `atp` (`18,392`), `wta` (`24,776`) across Outdoor Hard, Indoor Hard, Clay & Grass
- **🏐 Volleyball (`2,013` matches):** `wvolleyball` (NCAA Women's Volleyball, `1,537`), `mvolleyball` (NCAA Men's Volleyball, `476`)
- **🏀 Basketball (`986` matches across 6 leagues):** `nba` (`521`), `ncaaw` (`218`), `ncaam` (`152`), `fiba` (`36`), `nbl` (`34`), `wnba` (`25`)
- **🏒🏈⚾ Hockey, American Football & Baseball (`1,313` matches):** `nhl` (`678`), `nfl` (`479`), `mlb` (`156`)
- **📡 Direct Sportradar StatsHub & Tipico API (`56` Sports):** Live **Tipico (`_bookmakerId: 176`)** + **Sportradar Main UOF (`_bookmakerId: 0`)** 1X2, 28-score Correct Score matrices, Asian Handicaps, Player Injuries (`stats_season_injuries`), 15-Minute Goal Intervals (`stats_season_teamscoringconceding`), and European High-Frequency Sports (**Handball, Darts, Table Tennis, Snooker, MMA**).

See **[docs/USER_MANUAL.md](./docs/USER_MANUAL.md)** for the complete interactive WebApp & feature user guide, **[docs/SPORTRADAR_STATSHUB.md](./docs/SPORTRADAR_STATSHUB.md)** for the direct Sportradar/Tipico API reference, **[docs/FINDINGS.md](./docs/FINDINGS.md)** for the complete technical report, verified out-of-sample walk-forward edges, and live prospective ledger performance, **[docs/LAYA_DECISION_MODEL_EVALUATION.md](./docs/LAYA_DECISION_MODEL_EVALUATION.md)** for the out-of-sample Laya decision model ablation study, **[docs/notification-cards.html](./docs/notification-cards.html)** for the 12 PNG Notification Card designs catalog, and **[docs/logo-studio.html](./docs/logo-studio.html)** for the 60-variation SVG Logo Design Studio archive.

## Quick Commands (`Makefile` & `uv`)

```bash
# Show all available Makefile targets
make help

# Build Vue 3 + Tailwind SPA (app/dist) and start local BetScout server on http://127.0.0.1:8090
make dev

# Run all app (Vitest), SDK (Vitest + Pytest), and api (Pytest) unit & component test suites
make test

# Regenerate Option 7.3 SVG & PNG logo assets in all sizes and PNG notification cards design catalog
make logos
make cards-gallery

# Test, build app/dist, and deploy to Google Cloud Run + Firebase Hosting
make deploy

# Launch the live BetScout WebApp, SSE Stream & Background Auto-Poller directly via uv (http://127.0.0.1:8090)
cd api && uv run betscout --port 8090

# 0. Run the complete 4-stage daily pipeline (Config-driven incremental sync -> Quality check -> Multi-sport scanner -> HTML Dashboard)
uv run betscout pipeline
# (or: uv run betscout pipeline --days 5 --min-odds 1.10)

# 1. Universal Config-Driven Ingestion CLI (reads & updates ingestion_config.json automatically, prevents duplicate re-ingestion)
uv run betscout ingest                                            # Periodic incremental sync of all configured sources
uv run betscout ingest --leagues uefa.champions,nba,nhl --days 60 # Ingest specific/new leagues over last N days
uv run betscout ingest --leagues ned.1,por.1 --years 2025,2026    # Ingest specific seasons

# 2. Run database quality and anomaly checks (0 errors across 56,501 matches)
uv run betscout quality

# 3. Rebuild or refresh enriched match_details from cached ESPN JSON payloads
uv run betscout enrich           # Fast soccer match_details refresh
uv run betscout enrich --full    # Full rebuild of matches + match_details

# 4. Run the 7-Factor Orthogonal Soccer Composite, US Sports Composite & Tennis Game-Dominance evaluation
uv run betscout edges

# 5. Scan upcoming Soccer, Tennis & NBA/NHL/NFL/MLB fixtures, score 7-Factor Composite + News + Starting XI Gate & export JSON
uv run betscout scan --days 5

# 6. Generate standalone HTML Quantitative Desk Dashboard & export Best Bets Summary as CSV (with header) and JSON
uv run betscout dashboard --min-odds 1.10                       # Writes data/dashboard.html, data/best_bets.csv & data/best_bets.json
uv run betscout dashboard --min-odds 1.15 --format csv          # Export CSV only

# 7. View Settled & Pending Paper-Bets in the terminal and export data/settled_bets.csv
uv run betscout ledger                 # Shows Settled & Pending paper bets + realized PnL
uv run betscout ledger --settled-only  # Shows only completed/settled paper bets

# 8. Launch the Interactive Quant Desk Web App, SSE Live Stream & Social Publisher Addon
uv run betscout --port 8090

# 9. Preview or Publish Daily Best Bets & Settled Recap to Discord (Primary) or Telegram (Optional)
uv run betscout discord --dry-run
uv run betscout discord --max-picks 12       # Reads DISCORD_WEBHOOK_URL from .env
uv run betscout telegram --dry-run

# 10. Evaluate Football Exact Score / Dutching Clusters & Tennis Set-Score (2:0 / 2:1) Models
uv run betscout exact-score

# 11. Run all unit tests
uv run pytest -q
```

## Project Structure

- `Makefile` — Root monorepo task runner (`make help`, `make install`, `make dev`, `make serve`, `make test`, `make logos`, `make cards-gallery`, `make sync`, `make rescan`, `make pipeline`, `make deploy`)
- `app/` — **Vue 3 + TypeScript + Tailwind CSS + Pinia + Vue Router + Vitest** single-domain SPA (`/` Landing Page, `/app` 4-Tab Quantitative Desk, `@iconify/vue` FontAwesome 6 Solid icons, PWA Service Worker & LocalStorage sync, and `canvasCard.ts` client-side PNG card preview)
- `sdk/typescript/` & `sdk/python/` — White-labeled **`@betscout/sdk` (TypeScript/Node.js)** and **`betscout-sdk` / `betscout_sdk` (Python)** SDKs with 1:1 parity across 56 sports, multi-bookmaker odds, betting splits, stage sports, and match center dossiers
- `mcp/` & `.mcp.json` — **`@betscout/mcp-server` (TypeScript)** & **`betscout-mcp` (Python stdio + `/mcp` HTTP)** Model Context Protocol server exposing 7 quantitative tools (`mcp/README.md`, `mcp/evals.xml`)
- `docs/` — Comprehensive documentation & design catalogs (`USER_MANUAL.md`, `FINDINGS.md`, `LAYA_DECISION_MODEL_EVALUATION.md`, `MONETIZATION_PLAN.md`, `CLOUD_ARCHITECTURE_OPTIONS.md`, `FIREBASE_CLOUD_RUN_SETUP.md`, `SPORTRADAR_STATSHUB.md`, `notification-cards.html`, and `logo-studio.html`)
- `api/ingestion_config.json` — Descriptor of all 20 configured sports/leagues with automatic watermark & record-count tracking (`56,450` total matches)
- `api/deploy/com.betscout.daily.plist` — macOS `launchd` two-pass daily scheduler (`08:00` morning settlement & scan, `18:15` T-60m Starting XI confirmation pass)
- `api/src/betscout/`
  - `espn.py` — Cached ESPN scoreboard & summary client (`curl --compressed` with retry/backoff and 15m live refresh for recent days)
  - `ingest.py` — Pre-match 3-way & 2-way odds validators (`_valid_1x2`, `_valid_2way`, `_valid_dc`, `_valid_totals`), American-odds fallback, and same-day deduplication
  - `universal_ingest.py` — Config-driven universal ingestion engine (`ingest_universal`) with watermark skipping and on-the-fly normalization
  - `enrich.py` — 49-column `match_details` builder (opening/closing odds, multi-book best/consensus prices, 25 soccer boxscore stats, NBA/NHL/NFL/MLB 2-way boxscore efficiency/volume/turnover metrics, tennis surface & game scores)
  - `quality.py` — 18 automated SQL & cross-table anomaly checks (`0 errors` across `56,450` matches), `adjust_and_normalize_db`, and `matches_canonical` view installer
  - `quant_edges.py` — 7-Factor Orthogonal Invariant Soccer Composite (`tanh(Z)`), 7-Factor US Major Sports Boxscore + Rest/B2B + Rebound Composite (`evaluate_us_major_sports_composite`), exact Asian totals settlement (`settle_asian_total`), and 7-Feature Tennis Surface + Game-Dominance model
  - `paper_bet.py` — Multi-sport paper-betting scanner (15 Football competitions with cross-competition club history, ATP/WTA Tennis with Indoor vs Outdoor Hard surface split, Court-Acclimatization & Decider Resilience gates, diacritic-normalized SofaScore bookmaker odds & Market-Blend EV gate, NBA/NHL/NFL/MLB 7-Factor Composite with NHL Road Dual-Dominance & US Sports injury gates), 4-Archetype 2-Leg Combo / Parlay builder & auto-grader (`paper_combos`), retroactive pending re-validation, Quarter-Kelly compounding bankroll curve, Position-Specific T-60m Starting XI Gate (`attack_share`, `gk_starting`, `def_spine_share`), CLV tracker, live in-play tracking, and `recommendations.json` exporter
  - `dashboard.py` — Standalone dark-mode HTML/SVG **BetScout** Dashboard generator (`data/dashboard.html`) with custom hexagonal crest + pulse SVG logo, Per-Day (`Today`, `Tomorrow`, `Today + Tomorrow`, `All Days`) & Per-Sport filters, single-row sortable tables, ESPN Core v2 / CDN competition logos, team crests & player headshots, unified 8-column **Settled / Live In-Play / Pending** tables, **2-Leg Combo Ledger**, **Calibration & Tier Attribution** table, **Interactive Matchup Drill-Down Inspector** modal, and sorted Best Bets CSV/JSON exporter (`data/best_bets.csv`, `data/best_bets.json`)
  - `webapp.py` — Multi-threaded HTTP + SSE Live Stream server (`GET /api/stream`, `GET /api/matchup`, `POST /api/sync`, `POST /api/pipeline`, `POST /api/discord`, `POST /api/telegram`) with singleton 90s background auto-poller (live score sync, T-60m Starting XI auto-veto, and optional `DAILY_DIGEST_HOUR` morning digest scheduler)
  - `telegram_bot.py` — Discord (primary, Zscaler-compatible) & Telegram (optional) digest formatter (`day_filter='today'` default) and atomic settlement notifier (`notify_new_settlements_to_discord` with `BEGIN IMMEDIATE` + thread lock deduplication)
- `scripts/` — CLI entrypoints (`daily_pipeline.py`, `ingest.py`, `ledger.py`, `quality.py`, `enrich.py`, `quant_edges.py`, `paper_bet.py`, `dashboard.py`, `distill_laya_sports.py`, `compare_decision_models.py`, `exact_score_eval.py`)
- `tests/` — 16 unit tests covering ingestion, Asian settlement, quality checks, news signals, teacher distillation logging, Position-Specific XI gate (attack + GK/defensive spine), paper-bet CLV/settlement, and dashboard CSV/JSON exports

