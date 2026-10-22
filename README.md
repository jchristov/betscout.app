# Sportdata Model (`sportdata-model`)

Isolated quantitative research, data-quality auditing, and point-in-time feature engineering pipeline for soccer (`eng.1`, `esp.1`, `ger.1`, `ita.1`, `fra.1`, `aut.1`) and tennis (`atp`, `wta`).

See **[FINDINGS.md](./FINDINGS.md)** for the complete technical report, discovered data anomalies, falsified hypotheses, verified out-of-sample edges, and next-step roadmap.

## Quick Commands

```bash
# 0. Run the complete 4-stage daily pipeline (Config-driven incremental sync -> Quality check -> Multi-sport scanner -> HTML Dashboard)
uv run sportdata-model
# (or: uv run python scripts/daily_pipeline.py --days 5 --min-odds 1.10)

# 1. Universal Config-Driven Ingestion CLI (reads & updates ingestion_config.json automatically, prevents duplicate re-ingestion)
uv run python scripts/ingest.py                                            # Periodic incremental sync of all configured sources
uv run python scripts/ingest.py --leagues uefa.champions,nba,nhl --days 60 # Ingest specific/new leagues over last N days
uv run python scripts/ingest.py --leagues ned.1,por.1 --years 2025,2026    # Ingest specific seasons

# 2. Run database quality and anomaly checks (0 errors across 55,212 matches)
uv run python scripts/quality.py

# 3. Rebuild or refresh enriched match_details from cached ESPN JSON payloads
uv run python scripts/enrich.py           # Fast soccer match_details refresh
uv run python scripts/enrich.py --full    # Full rebuild of matches + match_details

# 4. Run the 7-Factor Orthogonal Soccer Composite & Tennis Game-Dominance evaluation
uv run python scripts/quant_edges.py

# 5. Scan upcoming Soccer, Tennis & NBA/NHL/NFL/MLB fixtures, score 7-Factor Composite + News + Starting XI Gate & export JSON
uv run python scripts/paper_trade.py --days 5

# 6. Generate standalone HTML Quantitative Desk Dashboard & export Best Bets Summary as CSV (with header) and JSON
uv run python scripts/dashboard.py --min-odds 1.10                       # Writes data/dashboard.html, data/best_bets.csv & data/best_bets.json
uv run python scripts/dashboard.py --min-odds 1.15 --format csv          # Export CSV only

# 7. View Settled & Pending Paper-Trades in the terminal and export data/settled_trades.csv
uv run python scripts/ledger.py                 # Shows Settled & Pending paper trades + realized PnL
uv run python scripts/ledger.py --settled-only  # Shows only completed/settled paper trades

# 8. Distill ms-decision-1 teacher labels into our local Laya sports checkpoint (data/laya_sports_ckpt)
uv run python scripts/distill_laya_sports.py --limit 160 --finetune --epochs 3

# 9. Benchmark ms-decision-1 vs Base Laya vs Sports-Fine-Tuned Laya (data/decision_model_comparison.json)
uv run python scripts/compare_decision_models.py

# 10. Launch the Interactive Quant Desk Web App, SSE Live Stream & Social Publisher Addon
uv run python scripts/webapp.py --port 8090

# 11. Preview or Publish Daily Best Bets & Settled Recap to Discord (Primary) or Telegram (Optional)
uv run python scripts/discord_post.py --dry-run
uv run python scripts/discord_post.py --max-picks 12       # Reads DISCORD_WEBHOOK_URL from model/.env
uv run python scripts/telegram_post.py --dry-run

# 12. Evaluate Football Exact Score / Dutching Clusters & Tennis Set-Score (2:0 / 2:1) Models
uv run python scripts/exact_score_eval.py

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
  - `paper_trade.py` — Multi-sport scanner (12 Football leagues with cross-competition club history, ATP/WTA Tennis with live SofaScore bookmaker odds, NBA/NHL/NFL/MLB 7-Factor Composite), Discovery-calibrated win probability (`p_model`), capped Quarter-Kelly sizing, Position-Specific T-60m Starting XI Gate (`attack_share`, `gk_starting`, `def_spine_share`), CLV tracker, live settlement, and `recommendations.json` exporter
  - `dashboard.py` — Standalone dark-mode HTML/SVG Quantitative Desk Dashboard generator (`data/dashboard.html`) with soft minimum-odds filter, Settled & Pending Paper-Trades tables, and sorted Best Bets CSV/JSON exporter (`data/best_bets.csv`, `data/best_bets.json`)
- `scripts/` — CLI entrypoints (`daily_pipeline.py`, `ingest.py`, `ledger.py`, `quality.py`, `enrich.py`, `quant_edges.py`, `paper_trade.py`, `dashboard.py`, `distill_laya_sports.py`, `compare_decision_models.py`)
- `tests/` — 16 unit tests covering ingestion, Asian settlement, quality checks, news signals, teacher distillation logging, Position-Specific XI gate (attack + GK/defensive spine), paper-trade CLV/settlement, and dashboard CSV/JSON exports

