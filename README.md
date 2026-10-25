# VektorPulse (`sportdata-model`) — Sports Edge, Exact-Score & Paper-Betting Intelligence

Isolated quantitative research, data-quality auditing, exact-score projection, and live paper-betting platform across **7 Sports & 27 Championships (`59,062` verified matches in `data/matches.sqlite`)**:
- **⚽ 14 Football Competitions (`11,582` matches):** `eng.1`, `esp.1`, `ger.1`, `ita.1`, `fra.1`, `aut.1`, `ned.1`, `por.1`, `eng.2`, `uefa.champions`, `uefa.europa`, `uefa.europa.conf`, `uefa.nations`, `fifa.world`
- **🎾 ATP & WTA Tennis (`43,168` matches):** `atp` (`18,392`), `wta` (`24,776`) across Outdoor Hard, Indoor Hard, Clay & Grass
- **🏐 Volleyball (`2,013` matches):** `wvolleyball` (NCAA Women's Volleyball, `1,537`), `mvolleyball` (NCAA Men's Volleyball, `476`)
- **🏀 Basketball (`986` matches across 6 leagues):** `nba` (`521`), `ncaaw` (`218`), `ncaam` (`152`), `fiba` (`36`), `nbl` (`34`), `wnba` (`25`)
- **🏒🏈⚾ Hockey, American Football & Baseball (`1,313` matches):** `nhl` (`678`), `nfl` (`479`), `mlb` (`156`)

See **[USER_MANUAL.md](./USER_MANUAL.md)** for the complete interactive WebApp & feature user guide, and **[FINDINGS.md](./FINDINGS.md)** for the complete technical report, discovered data anomalies, falsified hypotheses, verified out-of-sample edges, post-mortem model upgrades, and live prospective ledger performance.

## Quick Commands

```bash
# 0. Run the complete 4-stage daily pipeline (Config-driven incremental sync -> Quality check -> Multi-sport scanner -> HTML Dashboard)
uv run sportdata-model
# (or: uv run sportdata-model --days 5 --min-odds 1.10)

# 1. Universal Config-Driven Ingestion CLI (reads & updates ingestion_config.json automatically, prevents duplicate re-ingestion)
uv run sportdata-ingest                                            # Periodic incremental sync of all configured sources
uv run sportdata-ingest --leagues uefa.champions,nba,nhl --days 60 # Ingest specific/new leagues over last N days
uv run sportdata-ingest --leagues ned.1,por.1 --years 2025,2026    # Ingest specific seasons

# 2. Run database quality and anomaly checks (0 errors across 56,501 matches)
uv run sportdata-quality

# 3. Rebuild or refresh enriched match_details from cached ESPN JSON payloads
uv run sportdata-enrich           # Fast soccer match_details refresh
uv run sportdata-enrich --full    # Full rebuild of matches + match_details

# 4. Run the 7-Factor Orthogonal Soccer Composite, US Sports Composite & Tennis Game-Dominance evaluation
uv run sportdata-edges

# 5. Scan upcoming Soccer, Tennis & NBA/NHL/NFL/MLB fixtures, score 7-Factor Composite + News + Starting XI Gate & export JSON
uv run sportdata-bet --days 5

# 6. Generate standalone HTML Quantitative Desk Dashboard & export Best Bets Summary as CSV (with header) and JSON
uv run sportdata-dashboard --min-odds 1.10                       # Writes data/dashboard.html, data/best_bets.csv & data/best_bets.json
uv run sportdata-dashboard --min-odds 1.15 --format csv          # Export CSV only

# 7. View Settled & Pending Paper-Bets in the terminal and export data/settled_bets.csv
uv run sportdata-ledger                 # Shows Settled & Pending paper bets + realized PnL
uv run sportdata-ledger --settled-only  # Shows only completed/settled paper bets

# 8. Distill ms-decision-1 teacher labels into our local Laya sports checkpoint (data/laya_sports_ckpt)
uv run sportdata-distill --limit 160 --finetune --epochs 3

# 9. Benchmark ms-decision-1 vs Base Laya vs Sports-Fine-Tuned Laya (data/decision_model_comparison.json)
uv run sportdata-compare

# 10. Launch the Interactive Quant Desk Web App, SSE Live Stream & Social Publisher Addon
uv run sportdata-webapp --port 8090

# 11. Preview or Publish Daily Best Bets & Settled Recap to Discord (Primary) or Telegram (Optional)
uv run sportdata-discord --dry-run
uv run sportdata-discord --max-picks 12       # Reads DISCORD_WEBHOOK_URL from .env
uv run sportdata-telegram --dry-run

# 12. Evaluate Football Exact Score / Dutching Clusters & Tennis Set-Score (2:0 / 2:1) Models
uv run sportdata-exact-score

# 13. Run all unit tests
uv run pytest -q
```

## Project Structure

- `ingestion_config.json` — Descriptor of all 20 configured sports/leagues with automatic watermark & record-count tracking (`56,450` total matches)
- `deploy/firebase_laya/` — Ready-to-deploy Firebase Cloud Functions (2nd Gen Python 3.12) & GCP Cloud Functions package (`functions/main.py`, `firebase.json`, `.firebaserc`, `package_checkpoint.sh`, and `README.md`) for hosting the `804 MB` `laya_sports_ckpt` model
- `deploy/com.sportdata.model.daily.plist` — macOS `launchd` two-pass daily scheduler (`08:00` morning settlement & scan, `18:15` T-60m Starting XI confirmation pass)
- `src/sportdata_model/`
  - `espn.py` — Cached ESPN scoreboard & summary client (`curl --compressed` with retry/backoff and 15m live refresh for recent days)
  - `ingest.py` — Pre-match 3-way & 2-way odds validators (`_valid_1x2`, `_valid_2way`, `_valid_dc`, `_valid_totals`), American-odds fallback, and same-day deduplication
  - `universal_ingest.py` — Config-driven universal ingestion engine (`ingest_universal`) with watermark skipping and on-the-fly normalization
  - `enrich.py` — 49-column `match_details` builder (opening/closing odds, multi-book best/consensus prices, 25 soccer boxscore stats, NBA/NHL/NFL/MLB 2-way boxscore efficiency/volume/turnover metrics, tennis surface & game scores)
  - `quality.py` — 18 automated SQL & cross-table anomaly checks (`0 errors` across `56,450` matches), `adjust_and_normalize_db`, and `matches_canonical` view installer
  - `quant_edges.py` — 7-Factor Orthogonal Invariant Soccer Composite (`tanh(Z)`), 7-Factor US Major Sports Boxscore + Rest/B2B + Rebound Composite (`evaluate_us_major_sports_composite`), exact Asian totals settlement (`settle_asian_total`), and 7-Feature Tennis Surface + Game-Dominance model
  - `decision_signal.py` — System-1 pre-match injury/news veto gate defaulting to `laya` (`data/laya_sports_ckpt` via persistent warm worker or hosted `LAYA_REMOTE_URL` Firebase/GCP Function), with `ms-decision-1` teacher distillation (`record_distillation_pair`)
  - `paper_trade.py` — Multi-sport paper-betting scanner (15 Football competitions with cross-competition club history, ATP/WTA Tennis with Indoor vs Outdoor Hard surface split, Court-Acclimatization & Decider Resilience gates, diacritic-normalized SofaScore bookmaker odds & Market-Blend EV gate, NBA/NHL/NFL/MLB 7-Factor Composite with NHL Road Dual-Dominance & US Sports injury gates), 4-Archetype 2-Leg Combo / Parlay builder & auto-grader (`paper_combos`), retroactive pending re-validation, Quarter-Kelly compounding bankroll curve, Position-Specific T-60m Starting XI Gate (`attack_share`, `gk_starting`, `def_spine_share`), CLV tracker, live in-play tracking, and `recommendations.json` exporter
  - `dashboard.py` — Standalone dark-mode HTML/SVG **VektorPulse** Dashboard generator (`data/dashboard.html`) with custom hexagonal crest + pulse SVG logo, Per-Day (`Today`, `Tomorrow`, `Today + Tomorrow`, `All Days`) & Per-Sport filters, single-row sortable tables, ESPN Core v2 / CDN competition logos, team crests & player headshots, unified 8-column **Settled / Live In-Play / Pending** tables, **2-Leg Combo Ledger**, **Calibration & Tier Attribution** table, **Interactive Matchup Drill-Down Inspector** modal, and sorted Best Bets CSV/JSON exporter (`data/best_bets.csv`, `data/best_bets.json`)
  - `webapp.py` — Multi-threaded HTTP + SSE Live Stream server (`GET /api/stream`, `GET /api/matchup`, `POST /api/sync`, `POST /api/pipeline`, `POST /api/discord`, `POST /api/telegram`) with singleton 90s background auto-poller (live score sync, T-60m Starting XI auto-veto, and optional `DAILY_DIGEST_HOUR` morning digest scheduler)
  - `telegram_bot.py` — Discord (primary, Zscaler-compatible) & Telegram (optional) digest formatter (`day_filter='today'` default) and atomic settlement notifier (`notify_new_settlements_to_discord` with `BEGIN IMMEDIATE` + thread lock deduplication)
- `scripts/` — CLI entrypoints (`daily_pipeline.py`, `ingest.py`, `ledger.py`, `quality.py`, `enrich.py`, `quant_edges.py`, `paper_trade.py`, `dashboard.py`, `distill_laya_sports.py`, `compare_decision_models.py`, `exact_score_eval.py`)
- `tests/` — 16 unit tests covering ingestion, Asian settlement, quality checks, news signals, teacher distillation logging, Position-Specific XI gate (attack + GK/defensive spine), paper-bet CLV/settlement, and dashboard CSV/JSON exports

