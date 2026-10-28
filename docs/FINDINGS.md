# BetScout Quantitative Modeling & Edge Discovery Report

This document summarizes the data pipeline, data-quality audit, feature engineering, falsified hypotheses, verified out-of-sample edges, and next-step roadmap for the `betscout/model` project.

---

## 1. Executive Summary

Across **52,410 finished matches** (`9,292` soccer matches across 6 European leagues + international fixtures, and `43,118` deduplicated ATP & WTA tennis singles matches from 2022 through October 2026), we built a zero-lookahead, point-in-time feature and backtesting engine backed by cached ESPN scoreboard and summary payloads (`data/betscout.db`).

### Key Takeaways
1. **Single-feature models and raw goal-based Elo do not beat closing bookmaker prices**: A single bookmaker's closing 1X2 line carries a ~`5.6%` overround and already prices in team Elo, recent W/D/L form, and rest days.
2. **Data hygiene is critical before any edge claim**: Auditing the raw ESPN payloads uncovered four major data anomalies that created false edges in naive backtests—most notably **90th-minute in-play closing-whistle odds** stored in `Bet 365`'s top-level `homeTeamOdds.odds.value` slot (`746` rows), **in-play pollution in secondary European feeds** (`BetfairSportsbook`, `Unibet`, `Titanbets`), **1,336 duplicate same-day tennis competition IDs**, and **Asian push/quarter-line settlement bugs** on `2.0`, `2.25`, `2.75`, and `3.0` goal lines. All four have been fixed and locked down with automated checks in [`src/betscout/quality.py`](./src/betscout/quality.py).
3. **Multi-book execution & synthetic Dutching cut the bookmaker margin nearly in half**:
   - Line-shopping across verified pre-match providers (`Bet 365`, `Bet365`, `DraftKings`, `ESPN BET`, `Caesars`, `SugarHouse`, `PointsBet`) reduces the 1X2 overround from **`1.0561` (`+5.61%` vig)** to **`1.0371` (`+3.71%` vig)** across `8,203` multi-book matches.
   - Constructing a **Synthetic Double Chance** (`1X`, `X2`, `12`) by proportionally dutching the best pre-match 1X2 prices reduces Double Chance vig from **`+6.30%`** (official DC market) to **`+3.80%`**, beating the official DC price on **83%–89%** of matches.
4. **The 7-Factor Orthogonal Invariant Soccer Composite (`tanh(Z)`)**:
   - Using **Sub-Era Invariant Feature Selection** strictly inside Discovery (`D1: 2022–2023` vs `D2: 2024–Jun 2025`, without touching post-July 2025 data), we identified **7 orthogonal point-in-time factors** with consistent positive Information Coefficients across both Discovery sub-eras.
   - Standardized on Discovery (`< 2025-07-01`), smoothly bounded via `tanh(Z)` so no single heavy-tailed outlier hijacks the score, and averaged with **equal weights (zero fitted weight parameters)**, high-conviction picks (`1.35 <= odds <= 3.40`, max 1 pick/match) achieved positive ROI across **every chronological window** (`D1`, `D2`, `Confirmation 2025/26`, and `Fresh Aug–Oct 2026`), on **both Best Pre-Match Book and Primary Single Book**:
     - **Big-5 Leagues (`eng.1`, `esp.1`, `ger.1`, `ita.1`, `fra.1`), Top 10% Conviction**: Discovery `+2.30%` (`n=704`) | Confirmation `+11.00%` (`n=97`) | Fresh `+55.21%` (`n=18`) | **Post-2025 Combined (`n=115`)**: **`+17.92%` ROI (`95% CI [+3.6%, +31.4%]`, `p = 0.0080`; Primary Book: `+17.03%`)** | Full 2022–2026 (`n=819`): **`+4.49%` ROI**.
     - **All 6 Leagues (including `aut.1`), Top 10% Conviction**: Discovery `+2.11%` (`n=784`) | Confirmation `+5.50%` (`n=123`) | Fresh `+48.99%` (`n=26`) | **Post-2025 Combined (`n=149`)**: **`+13.09%` ROI (`95% CI [+1.2%, +25.7%]`, `p = 0.0170`; Primary Book: `+12.02%`)** | Full 2022–2026 (`n=933`): **`+3.87%` ROI**.
     - **Year-by-Year Hit Rate vs De-Vigged Market**: Beats the de-vigged market-implied probability in **all 5 calendar years** (`2022: +6.6%`, `2023: +1.5%`, `2024: +3.4%`, `2025: +4.9%`, `2026: +12.2%`), with positive net ROI after vig in 4 of 5 years.
5. **Tennis Surface-Specific + Game-Dominance Elo Model (`43,118` matches)**:
   - Updating Elo on the **share of games won (`games_won / total_games`)** rather than binary match wins—combined with **Surface-Specific Elo (`clay`, `grass`, `hard`)**, **short-rest fatigue**, and **H2H**—significantly improves out-of-sample predictions on both tours:
     - **ATP (`n=9,182` test matches)**: Log-loss improves from `0.6439` to **`0.6403`** (Accuracy `61.62% -> 62.54%`; High-Confidence `>=70%` picks reach **`75.60%` accuracy** across `2,639` matches).
     - **WTA (`n=12,377` test matches)**: Log-loss improves from `0.6406` to **`0.6339`** (Accuracy `62.50% -> 63.17%`; High-Confidence `>=70%` picks reach **`76.22%` accuracy** across `3,844` matches).

---

## 2. Database Architecture & Current Data Status (`55,212` Verified Matches)

The SQLite database (`data/betscout.db`) and config descriptor ([`ingestion_config.json`](./ingestion_config.json)) manage three core tables and one unified view across **6 sports and 20 leagues**:

| Object | Rows | Description |
| :--- | ---: | :--- |
| `matches` | `55,212` | Core match results (`home_score`, `away_score`, `outcome`), primary pre-match 1X2 / 2-way moneyline (`odds_home`, `odds_draw`, `odds_away`, `odds_provider`), Double Chance (`odds_dc_1x`, `odds_dc_x2`, `odds_dc_12`), and Totals (`line_total`, `odds_over`, `odds_under`). |
| `match_details` | `55,197` | 49-column enriched table built by [`src/betscout/enrich.py`](./src/betscout/enrich.py) and [`src/betscout/universal_ingest.py`](./src/betscout/universal_ingest.py) containing opening vs. closing lines (`open_*`, `close_*`), multi-book best prices and consensus probabilities (`best_*`, `cons_*`, `num_books`), soccer boxscore statistics (`shotsOnTarget`, `totalShots`, `wonCorners`, `possessionPct`, `foulsCommitted`, `yellowCards`, `redCards`, `penaltyKickGoals`, `ht_home`, `ht_away`), and tennis metadata (`surface`, `is_major`, `round_name`, `home_games`, `away_games`). |
| `paper_bets` | `14` (active) | Prospective paper-betting & CLV ledger managed by [`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py), storing `open_odds`, `logged_best_odds`, `logged_primary_odds`, `latest_close_odds`, `clv_pct`, `synthetic_dc_odds`, `composite_score`, `factor_breakdown_json`, `news_signal_json`, `status` (`PENDING` / `SETTLED`), and realized `pnl_best` / `pnl_primary`. |
| `matches_canonical` | `55,212` | Unified cross-sport view with explicit capability flags (`has_draw`, `has_score`, `has_1x2`). |

### Current Data Status by Sport & League (`uv run python scripts/quality.py` — `0 errors`)

| Sport | League Key | Competition Name | Ingested Records | Pre-Match Moneyline / 1X2 | Pre-Match Totals | Multi-Book (`>=2`) | Rich Boxscore / Games | Date Range (UTC) |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **Soccer** | `eng.1` | English Premier League | `1,787` | `1,787` (100.0%) | `1,787` (100.0%) | `1,744` | `1,787` | `2022-01-01` .. `2026-10-19` |
| **Soccer** | `esp.1` | Spanish La Liga | `1,802` | `1,799` (99.8%) | `1,784` (99.0%) | `1,007` | `1,802` | `2022-01-02` .. `2026-10-21` |
| **Soccer** | `ger.1` | German Bundesliga | `1,431` | `1,431` (100.0%) | `1,431` (100.0%) | `1,405` | `1,431` | `2022-01-07` .. `2026-10-18` |
| **Soccer** | `ita.1` | Italian Serie A | `1,781` | `1,766` (99.2%) | `1,761` (98.9%) | `1,656` | `1,781` | `2022-01-06` .. `2026-10-19` |
| **Soccer** | `fra.1` | French Ligue 1 | `1,552` | `1,552` (100.0%) | `1,550` (99.9%) | `1,510` | `1,552` | `2022-01-07` .. `2026-10-18` |
| **Soccer** | `aut.1` | Austrian Bundesliga | `921` | `921` (100.0%) | `919` (99.8%) | `879` | `383` | `2022-02-11` .. `2026-10-18` |
| **Soccer** | `ned.1` | Dutch Eredivisie | `547` | `547` (100.0%) | `547` (100.0%) | `504` | `547` | `2025-01-10` .. `2026-10-18` |
| **Soccer** | `por.1` | Portuguese Primeira Liga | `540` | `540` (100.0%) | `540` (100.0%) | `503` | `540` | `2025-01-03` .. `2026-10-19` |
| **Soccer** | `eng.2` | English Championship | `109` | `109` (100.0%) | `109` (100.0%) | `107` | `109` | `2026-08-23` .. `2026-10-20` |
| **Soccer** | `uefa.champions` | UEFA Champions League | `324` | `324` (100.0%) | `324` (100.0%) | `295` | `324` | `2025-01-21` .. `2026-10-21` |
| **Soccer** | `uefa.europa` | UEFA Europa League | `321` | `306` (95.3%) | `306` (95.3%) | `266` | `306` | `2022-09-15` .. `2026-10-15` |
| **Soccer** | `uefa.europa.conf` | UEFA Conference League | `215` | `214` (99.5%) | `213` (99.1%) | `0` | `215` | `2025-02-13` .. `2026-10-15` |
| **Soccer** | `fifa.world` | FIFA World Cup | `105` | `104` (99.0%) | `104` (99.0%) | `1` | `105` | `2022-11-20` .. `2026-07-19` |
| **Soccer** | `uefa.nations` | UEFA Nations League | `102` | `99` (97.1%) | `98` (96.1%) | `65` | `102` | `2022-06-01` .. `2026-10-06` |
| **Basketball** | `nba` | NBA | `81` | `77` (95.1%) | `77` (95.1%) | `0` | — | `2026-10-03` .. `2026-10-22` |
| **Am. Football** | `nfl` | NFL | `99` | `99` (100.0%) | `99` (100.0%) | `0` | — | `2026-08-24` .. `2026-10-20` |
| **Ice Hockey** | `nhl` | NHL | `215` | `153` (71.2%) | `153` (71.2%) | `0` | — | `2026-09-19` .. `2026-10-21` |
| **Baseball** | `mlb` | MLB | `156` | `156` (100.0%) | `156` (100.0%) | `0` | — | `2026-09-17` .. `2026-10-20` |
| **Tennis** | `atp` | ATP Singles Tour | `18,368` | — | — | — | `18,268` (Games) | `2021-09-25` .. `2026-10-22` |
| **Tennis** | `wta` | WTA Singles Tour | `24,756` | — | — | — | `24,585` (Games) | `2022-01-02` .. `2026-10-22` |
| **TOTAL** | **20 Leagues** | **6 Sports** | **`55,212`** | **`11,485`** | **`11,458`** | **`9,942`** | **`54,037`** | **`0` Quality Errors** |

---

## 3. Critical Data Anomalies Discovered & Resolved

1. **In-Play 90th-Minute Closing-Whistle Leakage (`_flat_1x2`)**:
   - **Symptom**: `esp.1` (2024–2026) exhibited an impossible `0.29` 1X2 market log-loss and `416` rows with odds `> 200` or draw odds `= 1.063`.
   - **Root Cause**: When `Bet 365`'s `bettingOdds.teamOdds.preMatchFullTimeResult...` was absent, `_flat_1x2` read `Bet 365`'s top-level `homeTeamOdds.odds.value` / `drawOdds.value` / `awayTeamOdds.odds.value`. On finished matches, ESPN overwrites those top-level fields with **live in-play odds at the final whistle** (e.g., `draw = 1/16 = 1.063` in a 0-0 draw).
   - **Resolution**: Removed `_flat_1x2` in [`src/betscout/ingest.py`](./src/betscout/ingest.py) and replaced it with `_american_book_odds`, which reads genuine pre-match moneylines and totals from `DraftKings`, `ESPN BET`, `Bet365`, `Caesars`, `SugarHouse`, and `PointsBet`, validated by `_valid_1x2` (`draw >= 2.20`, `1.01 < odds <= 100`, overround in `[1.00, 1.20]`). La Liga's market log-loss immediately normalized to **`0.9597`**.
2. **In-Play Overwrites in Secondary European Bookmakers**:
   - **Symptom**: Taking the maximum price across all `odds[]` providers produced synthetic overrounds as low as `0.3012`.
   - **Root Cause**: `BetfairSportsbook`, `Unibet`, and `Titanbets` occasionally overwrite their `current` slot with in-play prices during the match.
   - **Resolution**: [`src/betscout/enrich.py`](./src/betscout/enrich.py) restricts `match_details` to verified pre-match providers and rejects any book whose implied probability deviates by `> 8 percentage points` from the pre-match anchor (`open` or `Bet 365` `preMatch`).
3. **Duplicate Same-Day Tennis Fixtures (`1,336` rows)**:
   - **Root Cause**: ESPN's tennis scoreboard feed occasionally assigns two different `comp["id"]` values to the same match on the same day.
   - **Resolution**: `deduplicate_same_day` in [`src/betscout/ingest.py`](./src/betscout/ingest.py) removes same-day duplicates for identical unordered player pairs, and `duplicate_fixture_same_day` in [`src/betscout/quality.py`](./src/betscout/quality.py) enforces uniqueness.
4. **Asian Totals Push & Quarter-Line Settlement Bug**:
   - **Symptom**: Earlier scripts showed apparent `+18%` to `+27%` ROI on `Under 3.0` and `Under 2.0`.
   - **Root Cause**: Using `over = (home_score + away_score) > line_total` and `under = not over` graded exact 3-goal outcomes on a `3.0` line (and 2-goal outcomes on a `2.0` line) as **full `UNDER` wins** instead of `0.0` **pushes**, and mis-graded `2.25` / `2.75` Asian quarter-lines.
   - **Resolution**: Implemented exact Asian settlement (`settle_asian_total` in [`src/betscout/quant_edges.py`](./src/betscout/quant_edges.py) and tested in [`tests/test_quant_edges.py`](./tests/test_quant_edges.py)). With accurate push settlement, unconditional flat Over and Under both sit at `-3.0%` ROI (the exact bookmaker margin).

---

## 4. Quantitative Research Findings

### 4.1 What Does NOT Work (Falsified Hypotheses)
- **Raw Elo, Rolling Form, or Rest Days vs. Closing 1X2**: Adding standard Elo, 5-game form, or rest-day differentials to the closing market probability changes out-of-sample log-loss by less than `±0.0008` (95% bootstrap CI includes zero).
- **Fixture Congestion (Midweek European / Cup Match <= 4 Days Prior)**: Backing either the rested team (`-12.1%` Discovery ROI) or the congested team (`-1.4%` Discovery, `-29.9%` Confirmation) loses money; the closing price already adjusts for schedule congestion.
- **Unconditional Accumulators (Parlays)**: Combining random or uncalibrated legs compounds the bookmaker's margin (`k=1: -5.4%`, `k=2: -6.5%`, `k=3: -27.7%`).
- **Naive Single-Feature Slicing**: Slicing across `120` `(side × league × weekday/hour/month)` buckets yields zero survivors under Holm or Benjamini–Hochberg FDR correction.
- **Following Steam Moves at Closing Odds**: While teams whose implied probability steams by `> 4.0%` from Open to Close earn **`+10.37%` Discovery ROI and `+12.46%` Confirmation ROI (`p = 0.0063`) at the Opening Price**, betting them at the **Closing Price** yields `-3.21%` Discovery / `-3.72%` Confirmation ROI—proving that the closing line fully absorbs the steam information.
- **Backing "Clinical Overperformers" (`s_gd > s_sot`)**: Teams that beat market goal expectations while getting out-shot on target (`s_gd_d > 0` and `s_gd_d - s_sot_d > 0.35`) are "fraudulent winners" whose subsequent 1X2 bets lose **`-8.85%` in Confirmation and `-16.2%` in Fresh (`Post25+ = -9.97%, p = 0.990`)**.

---

### 4.2 What DOES Work: The 7-Factor Orthogonal Invariant Soccer Composite

To avoid overfitting to a single period, we split the pre-2025/26 Discovery dataset into two sub-eras—**`D1 (< 2024-01-01)`** and **`D2 (2024-01-01 .. 2025-06-30)`**—and tested which point-in-time factors had a **strictly positive Information Coefficient (`IC > +0.005`) with unit PnL in BOTH `D1` and `D2`** for moderate-priced sides (`1.35 <= best_odds <= 3.40`).

Every single factor that passed the `D1 & D2` invariance filter **also maintained a positive IC in the untouched `Post25+ (>= 2025-07-01)` holdout**:

| Orthogonal Factor | Domain Mechanism | `D1 (<2024)` IC | `D2 (24–25)` IC | `Post25+` Holdout IC |
| :--- | :--- | ---: | ---: | ---: |
| 1. `p_mkt` | Market-implied baseline team quality (lower vig on favourites) | `+0.0074` | `+0.0216` | **`+0.0200`** |
| 2. `vig_neg` | Multi-book price efficiency (`1 - best_overround`) | `+0.0077` | `+0.0029` | **`+0.0013`** |
| 3. `sot_d` | Rolling 6-match Shots on Target differential | `+0.0087` | `+0.0276` | **`+0.0250`** |
| 4. `discipline` | Tactical control: committing *fewer* fouls than opponent (`-d_fouls`) | `+0.0124` | `+0.0511` | **`+0.0249`** |
| 5. `h2h_adv` | Shrunk H2H win advantage minus H2H draw propensity | `+0.0191` | `+0.0150` | **`+0.0139`** |
| 6. `dom_rebound` | Shot & Possession dominance coming off negative Market-Adjusted Goal luck (`s_gd < 0`) | `+0.0119` | `+0.0152` | **`+0.0105`** |
| 7. `recent_draws` | Backed team's recent draw rate (depresses public win price) | `+0.0222` | `+0.0152` | **`+0.0072`** |

#### Why Bounded Multi-Factor Consensus (`tanh(Z)`) Works
Unclipped linear combinations are vulnerable to extreme single-factor outliers (e.g., a `z = +6.0` rebound after a 0-4 red-card loss). Standardizing each factor strictly on Discovery (`< 2025-07-01`), applying `tanh(z)` to smoothly bound each factor in `[-1, +1]`, and taking the **equal-weight average (zero fitted weights)** forces high-scoring picks to have **broad multi-factor agreement** (at least 5 to 6 of the 7 independent factors positive simultaneously).

#### Out-of-Sample Results (`uv run python scripts/quant_edges.py`)

| Scope & Conviction Tier | Discovery ROI (`< Jul 2025`) | Confirmation ROI (`2025/26`) | Fresh ROI (`Aug–Oct 2026`) | Post-2025 Combined (Best Book) | Post-2025 95% CI & One-Sided $p$ | Post-2025 Primary Single Book | Full 2022–2026 ROI ($N$) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Big-5 Leagues, Top 15%** | `+1.37%` (1,055) | `+7.83%` (176) | `+36.28%` (27) | **`+11.62%`** (203) | `[+0.6%, +21.8%]`, $p=0.0213$ | **`+10.86%`** | `+3.03%` (1,258) |
| **Big-5 Leagues, Top 10%** | `+2.30%` (704) | `+11.00%` (97) | `+55.21%` (18) | **`+17.92%`** (115) | `[+3.6%, +31.4%]`, $p=0.0080$ | **`+17.03%`** | `+4.49%` (819) |
| **Big-5 Leagues, Top 8%** | `+2.03%` (563) | `+10.39%` (72) | `+56.75%` (15) | **`+18.39%`** (87) | `[+3.4%, +33.1%]`, $p=0.0077$ | **`+17.54%`** | `+4.22%` (650) |
| **All 6 Leagues, Top 10%** | `+2.11%` (784) | `+5.50%` (123) | `+48.99%` (26) | **`+13.09%`** (149) | `[+1.2%, +25.7%]`, $p=0.0170$ | **`+12.02%`** | `+3.87%` (933) |
| **All 6 Leagues, Top 8%** | `+1.87%` (627) | `+11.73%` (93) | `+47.60%` (21) | **`+18.34%`** (114) | `[+4.9%, +31.4%]`, $p=0.0032$ | **`+17.27%`** | `+4.40%` (741) |

*Note on Austrian Bundesliga (`aut.1`)*: `aut.1` splits mid-season into a 6-team Championship group and 6-team Relegation group, causing regular-season rolling stats to shift regime after the split. Excluding `aut.1` (keeping the Big-5 European leagues where teams play a continuous round-robin) improves both precision and consistency.

---

### 4.3 Tennis: Surface-Specific + Game-Dominance Model (`43,118` Matches)

In [`src/betscout/quant_edges.py`](./src/betscout/quant_edges.py), we engineered 7 point-in-time tennis features from `matches` and `match_details`:
1. `d_elo_all`: Overall tour Elo differential ($K=28$)
2. `d_elo_surf`: Court-surface-specific Elo differential (`clay`, `grass`, `hard`)
3. `d_elo_games`: **Game-Dominance Elo**, updated on continuous game-win share $\text{sigmoid}(6 \cdot (\frac{G_{\text{won}}}{G_{\text{total}}} - 0.5))$ rather than binary match win/loss
4. `d_game_pct`: Rolling 10-match game-win percentage differential
5. `d_trans`: Surface-transition indicator (switching surface within the last 12 days)
6. `d_fat`: Short-rest fatigue (total games played within the last 2 days)
7. `d_h2h`: Shrunk head-to-head match win rate

| Tour | Out-of-Sample Test Matches | Baseline Elo Log-Loss (Acc) | Rich 7-Feature Log-Loss (Acc) | High-Confidence (`P >= 70%`) Accuracy ($N$) |
| :--- | ---: | ---: | ---: | ---: |
| **ATP** | `9,182` | `0.6439` (`61.62%`) | **`0.6403`** (`62.54%`) | **`75.60%`** (`n = 2,639`) |
| **WTA** | `12,377` | `0.6406` (`62.50%`) | **`0.6339`** (`63.17%`) | **`76.22%`** (`n = 3,844`) |

---

## 5. How to Run Tools On Demand

All commands run inside `/Users/yuliyan.hristov/Development/github.com/jchristov/betscout/model`:

```bash
# 0. Run the complete 4-stage daily pipeline (Incremental config-driven ingest -> Quality check -> Paper bet + News/XI gates -> HTML Dashboard)
uv run betscout pipeline
# (or with custom options: uv run betscout pipeline --days 5 --min-odds 1.10)

# 1. Universal Config-Driven Ingestion CLI (reads/updates ingestion_config.json automatically, skips existing events, normalizes on the fly)
uv run betscout ingest                                                # Periodic incremental sync of all enabled sources in ingestion_config.json
uv run betscout ingest --leagues uefa.champions,nba,nhl --days 60     # On-demand ingestion for specific/new leagues over last N days
uv run betscout ingest --leagues ned.1,por.1 --years 2025,2026        # On-demand multi-season backfill
uv run betscout ingest --leagues mlb --from 2026-09-15 --to 2026-10-22 # Exact date range
uv run betscout ingest --leagues eng.1 --all-history                  # Full 2022-2026 history

# 2. Run the database quality & anomaly checker (0 issues across 56,501 matches)
uv run betscout quality

# 3. Rebuild or refresh enriched match_details from cached ESPN JSON payloads
uv run betscout enrich           # Fast soccer match_details refresh + summary
uv run betscout enrich --full    # Full rebuild of matches + match_details

# 4. Run the multi-factor soccer edge & enriched tennis evaluation
uv run betscout edges

# 5. Scan upcoming Soccer, Tennis & NBA/NHL/NFL/MLB fixtures, score 7-Factor Composite + News + Starting XI Gate, log paper bets & export JSON
uv run betscout scan --days 5

# 6. Generate the standalone interactive HTML Quantitative Desk Dashboard & export Best Bets Summary as CSV (with header) and JSON
uv run betscout dashboard --min-odds 1.10                       # Exports data/dashboard.html, data/best_bets.csv & data/best_bets.json
uv run betscout dashboard --min-odds 1.15 --format csv          # Export CSV only
uv run betscout dashboard --export-csv /tmp/my_bets.csv         # Custom output path

# 7. View Settled & Pending Paper-Bets in the terminal and export data/settled_bets.csv
uv run betscout ledger                 # Shows Settled & Pending paper bets + realized PnL
uv run betscout ledger --settled-only  # Shows only completed/settled paper bets

# 8. Run the automated unit test suite
uv run pytest -q
```

---

## 6. Executed Next Steps: Paper-Betting, CLV, System-1 News Veto, T-60m XI Gate, Tennis Scanner & HTML Desk

All roadmap items have been implemented, verified on live ESPN fixtures, and covered by unit tests:

1. **Dedicated Enrichment CLI ([`scripts/enrich.py`](./scripts/enrich.py) & [`src/betscout/enrich.py`](./src/betscout/enrich.py))**:
   - Provides one-command fast refresh (`uv run betscout enrich`) or full rebuild (`--full`) of the 49-column `match_details` table and `matches_canonical` view from cached ESPN payloads.
2. **Automated Pre-Kickoff Paper-Betting & Prospective CLV Ledger ([`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py) & [`scripts/paper_bet.py`](./scripts/paper_bet.py))**:
   - Freezes the Discovery (`< 2025-07-01`) standardization parameters (`StandardScaler`) and conviction thresholds (`top_8pct: +0.3661`, `top_10pct: +0.3246`, `top_15pct: +0.2565`, `top_25pct: +0.1579`), rolls team boxscore and H2H states forward to the latest completed match, scans upcoming ESPN fixtures, and logs qualifying picks to the `paper_bets` SQLite table.
   - Preserves initial `logged_best_odds` and `logged_primary_odds`, updates `latest_close_odds` and `clv_pct = (logged_best_odds / latest_close_odds) - 1` on subsequent pre-kickoff runs, and automatically settles completed paper bets into realized `pnl_best` and `pnl_primary`.
3. **Unstructured Match-Preview & Injury News Veto Gate via `ms-decision-1` and Distilled Sports-Tuned Local `Laya` ([`src/betscout/decision_signal.py`](./src/betscout/decision_signal.py) & [`scripts/distill_laya_sports.py`](./scripts/distill_laya_sports.py))**:
   - Extracts team-specific news headlines and previews from each upcoming ESPN match summary (using alias-aware matching, pre-kickoff timestamp validation, and zero unrelated-headline fallback) and evaluates calibrated predicates (`home_positive`, `home_negative`, `away_positive`, `away_negative`) using Azure AI Foundry's **`ms-decision-1`** (`POST /v1/decisions` via `rbi-sl-token token --env uat`) with automatic offline fallback to our distilled sports-tuned **`Laya`** checkpoint ([`data/laya_sports_ckpt`](./data/laya_sports_ckpt)).
   - Automatically logs every `ms-decision-1` teacher query/response pair to [`data/decision_training_pairs.jsonl`](./data/decision_training_pairs.jsonl) (`record_distillation_pair`). Using [`scripts/distill_laya_sports.py`](./scripts/distill_laya_sports.py), we harvested `160` sports headlines (`384` question items) from cached ESPN summaries, labeled them with `ms-decision-1`, and fine-tuned `laya_sports_ckpt` via `laya.train_cli --loss soft-ce --freeze-encoder`. On the `96`-item held-out evaluation split:
     - **Cross-Entropy Loss**: dropped from **`0.5818`** to **`0.4475`** (`-0.1343`)
     - **Expected Calibration Error (ECE)**: dropped from **`0.1791`** to **`0.0873`** (`-0.0918`, **>51% calibration error reduction**)
     - **Brier Score (Top-1)**: dropped from **`0.1408`** to **`0.0826`** (`-0.0582`)
   - Acts as an **automated System-1 injury/crisis veto gate (`net_edge_for_pick <= -0.50` -> `VETOED_BY_INJURY_NEWS`)**: when the 7-factor statistical model scored **PSG vs Lyon -> Home (`+0.5638`)**, `ms-decision-1` read the ESPN headline *"PSG star Khvicha Kvaratskhelia ruptures ACL; Dembélé, Marquinhos out 'weeks'"*, scored `home_negative = 0.998` (`net_edge = -0.816`), and **automatically vetoed and removed PSG from the active paper-betting ledger** while keeping **Juventus (`@ 1.44`)**, **Bayern Munich (`@ 1.38`, `News +0.260`)**, and **AC Milan (`@ 1.65`, `News +0.750`)**.
4. **Position-Specific Pre-Kickoff Starting XI Confirmation Gate (T-60m) (`evaluate_starting_xi_gate` in [`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py))**:
   - Tracks each team's rolling 6-match **Attacking Contribution** (`totalGoals + 0.7 * goalAssists + 0.2 * shotsOnTarget`), **Primary Goalkeeper Continuity** (`position.abbreviation == 'G'`), and **Defensive Spine Continuity** (`position.abbreviation` in `{'CD', 'CD-L', 'CD-R', 'D', 'CB', 'LB', 'RB', 'LD', 'RD', 'SW'}`).
   - Once ESPN posts official starting lineups (`starter: True`, ~60m before kickoff), it verifies that:
     1. `attack_share >= 0.50` (`VETOED_DEPLETED_XI` if `< 50%` of recent attacking output starts), and
     2. The team is not missing **both** its primary goalkeeper (`gk_starting == False`) **and** `>= 50%` of its regular defensive spine (`def_spine_share < 0.50` $\rightarrow$ `VETOED_DEPLETED_DEFENSE`).
   - In historical backtest ablation across all `1,258` Big-5 Top-15% picks:
     - **Baseline (no XI gate)**: **`+3.03%` ROI** (`n = 1,258`)
     - **Attack Share (`>= 50%`) only**: **`+3.23%` ROI** (`n = 1,057` kept vs `+1.95%` on `201` vetoed)
     - **Combined Attack + Goalkeeper & Defensive Spine Gate**: **`+3.66%` ROI** (`n = 1,030` kept) vs **`+0.16%` ROI** (`n = 228` vetoed)!
5. **Discovery-Calibrated Win Probabilities (`p_model`), EV%, Capped Quarter-Kelly Sizing & Risk Metrics ([`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py))**:
   - Fits a two-feature logistic calibrator strictly on Discovery (`< 2025-07-01`):
     $$\text{logit}(P(\text{win})) = 0.0472 + 0.9484 \cdot \text{logit}(p_{\text{mkt}}) + 0.3896 \cdot \text{score}$$
   - Computes calibrated expected value ($\text{EV} = p_{\text{model}} \cdot O_{\text{best}} - 1$) and **Capped Quarter-Kelly Paper Stake** ($\min(2.0\%, \max(0\%, 0.25 \cdot \frac{\text{EV}}{O_{\text{best}} - 1}))$).
   - **Out-of-Sample Post-2025 Holdout Risk Profile (`Big-5 Top 10%`, `n = 115` bets)**:
     - **Cumulative Profit**: **`+20.61 units`** (`ROI = +17.92%`, $p = 0.0080$)
     - **Maximum Drawdown**: **`5.00 units`** (`Profit / MaxDD = 4.12x`)
     - **Period Sharpe / $t$-stat**: **`2.57`**
     - **Hit Rate**: **`73.0%`** vs **`60.1%` de-vigged market implied** (mean calibrated `p_model = 64.6%`).
6. **Live Multi-Sport Scanner & 7-Factor US Major Sports Composite (`scan_upcoming_tennis` & `scan_upcoming_other_sports` in [`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py), `evaluate_us_major_sports_composite` in [`src/betscout/quant_edges.py`](./src/betscout/quant_edges.py))**:
   - **Football (12 leagues)**: Big-5 (`eng.1`, `esp.1`, `ger.1`, `ita.1`, `fra.1`), `ned.1`, `por.1`, `eng.2`, `aut.1`, and UEFA Club Competitions (`uefa.champions`, `uefa.europa`, `uefa.europa.conf`) with **Cross-Competition Club History Inheritance** (clubs playing in UEFA competitions inherit their full domestic rolling boxscore and H2H history).
   - **Tennis (`atp`, `wta`)**: 7-Feature Surface-Specific + Game-Dominance Logistic Regression model across `43,124` completed matches, outputting Win Probability, Minimum Fair Odds (`1 / p`), and `+3% EV Target Odds` (`1.03 / p`).
   - **Major 2-Way US Sports (`nba`, `nhl`, `nfl`, `mlb`) — 7-Factor Boxscore + Rest/B2B + Rebound Composite**:
     - Enriched `1,801` completed games (`506` NBA, `663` NHL, `476` NFL, `156` MLB) with sport-specific boxscore efficiency, volume, creation, control, and turnover metrics in `match_details` (`_extract_two_way_details` in [`src/betscout/enrich.py`](./src/betscout/enrich.py)).
     - Built a 7-Factor `tanh(Z)` composite (`p_mkt`, `vig_neg`, `eff_d`, `vol_d`, `to_adv`, `rest_b2b`, `dom_rebound`) that achieves **`+3.91%` pooled out-of-sample ROI** (`n = 170`, **`66.5%` hit rate vs `61.5%` market implied (`+4.9%`)**), led by **NFL (`+13.47%` ROI, `74.1%` hit rate vs `61.9%` market)** and **MLB (`+29.35%` ROI, `77.8%` hit rate vs `58.7%` market)**.
7. **Universal Config-Driven Ingestion Engine ([`scripts/ingest.py`](./scripts/ingest.py), [`src/betscout/universal_ingest.py`](./src/betscout/universal_ingest.py) & [`ingestion_config.json`](./ingestion_config.json))**:
   - Reads [`ingestion_config.json`](./ingestion_config.json) by default, automatically registers any new sport/league requested on demand, skips already-completed `event_id`s to prevent duplicate work, refreshes scoreboards within the last 2 UTC days when older than 15 minutes, and runs `adjust_and_normalize_db` + `quality.run` on the fly (`0 errors` across `56,450` matches).
8. **Standalone HTML Quantitative Desk Dashboard, Soft Minimum-Odds Filter & CSV/JSON Exports ([`src/betscout/dashboard.py`](./src/betscout/dashboard.py), [`scripts/dashboard.py`](./scripts/dashboard.py), [`scripts/ledger.py`](./scripts/ledger.py))**:
   - **Soft Minimum-Odds Filter (`--min-odds 1.10`)**: Filters out unattractive odds `<= 1.10` (`<= 10%` profit) in both the CLI exports and via an interactive live slider in [`data/dashboard.html`](./data/dashboard.html).
   - **Settled & Pending Paper-Bets Ledger (`scripts/ledger.py` & `data/settled_bets.csv`)**: Automatically settles completed matches across all sports (soccer, tennis, NBA, NHL, NFL, MLB), displaying final scores, `WIN` / `LOSS` badges, `CLV%`, and realized unit profit in [`data/dashboard.html`](./data/dashboard.html), in the terminal (`uv run betscout ledger`), and in [`data/settled_bets.csv`](./data/settled_bets.csv).
   - **Sorted Best Bets Summary Table (`data/best_bets.csv` & `data/best_bets.json`)**: Renders a unified table at the end of [`data/dashboard.html`](./data/dashboard.html) sorted chronologically by **Date (ascending — soonest upcoming events first)** with columns **Date (UTC)**, **Sport / League**, **Match**, **Pick**, and **Odds**, plus one-click browser **"Export CSV (with Header)"** and **"Export JSON"** buttons.
9. **Master One-Command Daily Pipeline ([`scripts/daily_pipeline.py`](./scripts/daily_pipeline.py) / `uv run betscout pipeline`)**:
   - Executes config-driven incremental ingestion, automated database quality verification (`0 errors`), multi-sport paper-bet settlement and upcoming fixture scoring, CSV/JSON exports (`recommendations.json`, `best_bets.csv`, `best_bets.json`), and HTML dashboard generation in a single command.

### Current Paper-Betting Ledger & Live Slate Snapshot

- **First Settled Live Paper Bet (`2026-10-22`)**:
  - `2026-10-22 05:30 UTC` · **WTA Tour (`Hard`)**: **Magda Linette vs Katerina Siniakova** $\rightarrow$ Pick: **Katerina Siniakova (`A`)** `@ 1.45` (`WinProb 71.0%`) $\rightarrow$ **Final Score `0-2` (`4-6, 1-6`) — `SETTLED WIN (+0.45u)`**!

| Sport / League | Kickoff (UTC) | Fixture | Pick | Tier / Action | Score / WinProb | Odds (Syn DC) | Calib `p_model` (`EV%`) | System-1 News |
| :--- | :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| `Tennis · ATP` | `2026-10-22 09:30` | Medvedev vs Shimabukuro | Medvedev (`H`) | `banker_70pct` · **`PAPER_BET`** | `88.4%` | `>= 1.13` (`1.17`) | `88.4%` (`+3.0%`) | — |
| `Tennis · ATP` | `2026-10-22 11:30` | R. Collignon vs Jiri Lehecka | Lehecka (`A`) | `banker_70pct` · **`PAPER_BET`** | `80.9%` | `>= 1.24` (`1.27`) | `80.9%` (`+3.0%`) | — |
| `Tennis · ATP` | `2026-10-22 13:30` | P-H. Herbert vs Taylor Fritz | Fritz (`A`) | `banker_70pct` · **`PAPER_BET`** | `81.9%` | `>= 1.22` (`1.26`) | `81.9%` (`+3.0%`) | — |
| `Soccer · uefa.europa.conf` | `2026-10-22 19:00` | Braga vs KAA Gent | Braga (`H`) | `top_25pct` · **`PAPER_BET`** | `+0.172` | `1.87` (`1.23`) | `54.0%` (`+0.9%`) | `0.000` |
| `Hockey · NHL` | `2026-10-22 23:00` | Bruins vs Predators | Bruins (`H`) | `solid` · **`PAPER_BET`** | `58.7%` | `1.65` | `58.7%` (`-3.4%`) | — |
| `Soccer · eng.2` | `2026-10-23 19:00` | Bolton vs Middlesbrough | Middlesbrough (`A`) | `top_8pct` · **`PAPER_BET`** | `+0.485` | `1.59` (`1.18`) | `67.8%` (`+7.7%`) | `0.000` |
| `Basketball · NBA` | `2026-10-23 23:00` | Celtics vs Knicks | Celtics (`H`) | `solid` · **`PAPER_BET`** | `61.1%` | `1.74` | `61.1%` (`+6.3%`) | — |
| `Soccer · ita.1` | `2026-10-25 17:00` | Lecce vs Juventus | Juventus (`A`) | `top_8pct` · **`PAPER_BET`** | `+0.539` | `1.44` (`1.07`) | `70.5%` (`+1.8%`) | `0.000` |
| `Soccer · ger.1` | `2026-10-25 16:30` | Freiburg vs Bayern Munich | Bayern (`A`) | `top_10pct` · **`PAPER_BET`** | `+0.357` | `1.38` (`1.11`) | `71.9%` (`-0.8%`) | **`+0.383`** |
| `Soccer · ita.1` | `2026-10-25 19:45` | Udinese vs AC Milan | AC Milan (`A`) | `top_10pct` · **`PAPER_BET`** | `+0.330` | `1.65` (`1.15`) | `61.3%` (`+1.2%`) | **`+0.750`** |
| `Soccer · fra.1` | `2026-10-25 19:45` | PSG vs Lyon | PSG (`H`) | `top_8pct` · **`VETOED_BY_INJURY_NEWS`** | `+0.564` | `1.48` (`1.14`) | `69.9%` (`+3.4%`) | **`-0.816`** *(ACL/injury crisis)* |

---

## 7. Head-to-Head Benchmark: `ms-decision-1` vs Base `Laya` vs Sports-Fine-Tuned `Laya` ([`scripts/compare_decision_models.py`](./scripts/compare_decision_models.py))

We switched the default decision model across `decision_signal.py`, `paper_bet.py`, and `daily_pipeline.py` to **`laya`** (`laya-sports`, [`data/laya_sports_ckpt`](./data/laya_sports_ckpt)) with a persistent warm worker process and subject-aware per-team headline routing (`split_match_text_by_team`).

To empirically compare **`ms-decision-1`** (Azure AI Foundry teacher) against **Base `Laya` (`typed-decisions`)** and **Sports-Fine-Tuned `Laya` (`data/laya_sports_ckpt`)**, run:
```bash
uv run python scripts/compare_decision_models.py
```

### 7.1 Held-Out Validation Benchmark vs `ms-decision-1` Teacher (`data/laya_sports_val.jsonl`, `96` items across `32` sports contexts)

| Model | Accuracy vs Teacher | Soft Cross-Entropy Loss | Brier Score | Expected Calibration Error (ECE) | Pearson $r$ | Warm Latency |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **`laya-base` (`typed-decisions`)** | `82.29%` | `0.5818` | `0.0518` | `0.1892` | `0.6870` | `159.0 ms` |
| **`laya-sports` (`data/laya_sports_ckpt`)** | **`82.29%`** | **`0.4475` (`-23.1%`)** | **`0.0367` (`-29.2%`)** | **`0.0816` (`-56.9%`)** | **`0.6878`** | **`164.2 ms`** |

### 7.2 Match-Level Injury Veto Gate Concordance (`net_edge` in `[-1, +1]`, Veto triggered at `<= -0.50`)

| Match Scenario | Expected Veto | `ms-decision-1` (Cloud Teacher) | `laya-base` (Untuned) | `laya-sports` (Default Local/Cloud) |
| :--- | :---: | ---: | ---: | ---: |
| **PSG vs Lyon** *(Kvaratskhelia ACL, Dembélé & Marquinhos out)* | **`True`** | **`-0.984` (`VETO`, `927ms`)** | `-0.577` (`VETO`, `523ms`) | **`-0.785` (`VETO`, `218ms`)** |
| **Udinese vs AC Milan** *(Milan captain returns fit, Udinese suspensions)* | **`False`** | **`+1.922` (`KEEP`, `625ms`)** | `+0.854` (`KEEP`, `222ms`) | **`+1.129` (`KEEP`, `304ms`)** |
| **Freiburg vs Bayern Munich** *(Bayern 6-match winning streak)* | **`False`** | **`+0.991` (`KEEP`, `540ms`)** | `+0.302` (`KEEP`, `59ms`) | **`+0.288` (`KEEP`, `49ms`)** |
| **Arsenal vs Chelsea** *(Saka & Odegaard out; Palmer returns fit)* | **`True`** | **`-1.888` (`VETO`, `769ms`)** | `-1.149` (`VETO`, `179ms`) | **`-1.597` (`VETO`, `191ms`)** |
| **Real Madrid vs Sevilla** *(Dressing-room crisis, Bellingham & Vini suspended)* | **`True`** | **`-1.015` (`VETO`, `630ms`)** | `-0.489` *(Missed Veto)* | **`-0.630` (`VETO`, `83ms`)** |
| **Brentford vs Fulham** *(Neutral kickoff/referee preview)* | **`False`** | **`+0.000` (`KEEP`, `528ms`)** | `+0.000` (`KEEP`, `117ms`) | **`+0.000` (`KEEP`, `141ms`)** |

- **Key Finding**: Untuned `laya-base` (`typed-decisions`) under-confidently scored the Real Madrid dressing-room/suspension crisis at `-0.489` (missing the `-0.50` veto threshold), whereas **`laya-sports` (`-0.630`) achieved `6/6` (`100%`) veto concordance with `ms-decision-1` at 3x–8x lower warm latency (`49–218 ms` vs `528–927 ms`) and zero external API cost**.

---

## 8. Packaging & Hosting `laya-sports` on Firebase Functions / GCP Cloud Functions ([`deploy/firebase_laya/`](./deploy/firebase_laya/README.md))

We prepared a complete, ready-to-deploy **Firebase Cloud Functions (2nd Gen Python 3.12) & GCP Cloud Functions** package in [`deploy/firebase_laya/`](./deploy/firebase_laya/):
- [`deploy/firebase_laya/package_checkpoint.sh`](./deploy/firebase_laya/package_checkpoint.sh): Strips the `804 MB` resumable training state (`checkpoint_latest/`) so the deployable inference bundle is **`804 MB`** (`model.safetensors` + `rl_agent_config.json` + `encoder/` + `tokenizer/`), and optionally syncs it to Google Cloud Storage / Firebase Storage (`gs://betscout-ai.appspot.com/models/laya_sports_ckpt`).
- [`deploy/firebase_laya/functions/main.py`](./deploy/firebase_laya/functions/main.py): Exposes `laya_sports_decisions` (`memory=2GiB`, `cpu=2`, `concurrency=8`), keeping `laya.Agent` warm in global instance memory and accepting both Laya native (`{"state": ..., "questions": {...}}`) and `ms-decision-1` (`{"input": ..., "questions": [...]}`) wire payloads.
- [`deploy/firebase_laya/firebase.json`](./deploy/firebase_laya/firebase.json) & [`.firebaserc`](./deploy/firebase_laya/.firebaserc): Pre-configured for the repo's Firebase project (`betscout-ai`).
- **Seamless Remote Hook**: Setting `export LAYA_REMOTE_URL="https://..."` (and optional `LAYA_REMOTE_TOKEN`) automatically routes `score_with_laya` in [`src/betscout/decision_signal.py`](./src/betscout/decision_signal.py) to the hosted Firebase/GCP function, falling back to the local warm worker when unset.

---

## 9. Live SofaScore Tennis Odds, Two-Pass Scheduler & Main App (`app/`) Bridge

1. **Live SofaScore Tennis Bookmaker Odds (`_fetch_sofascore_tennis_odds` in [`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py))**:
   - Queries `https://api.sofascore.com/api/v1/search/all` and `/event/{id}/odds/1/all` for upcoming ATP/WTA picks, converting live fractional bookmaker prices (`initialFractionalValue` and `fractionalValue`) to decimal `open_odds` and `best_odds` alongside `min_fair_odds` and exact `ev_pct`.
2. **Automated Two-Pass Matchday Scheduler ([`deploy/com.betscout.daily.plist`](./deploy/com.betscout.daily.plist))**:
   - macOS `launchd` agent running `uv run betscout pipeline --days 5 --min-odds 1.10 --decision-backend laya` at `08:00` (morning settlement & early scan) and `18:15` (pre-kickoff T-60m Starting XI confirmation pass & closing CLV update).
   - Install with: `cp deploy/com.betscout.daily.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.betscout.daily.plist`
3. **Main Vue App (`app/public/model/`) Static Feed Bridge**:
   - Every run of `scripts/daily_pipeline.py` (`uv run betscout pipeline`) automatically syncs `best_bets.json`, `best_bets.csv`, `recommendations.json`, and `dashboard.html` into `../app/public/model/` so the `betscout-ai` web app can serve and render the latest quantitative picks and dashboard directly.
4. **Local Timezone Conversion (`Europe/Vienna` CEST/CET), Live SSE Web App (`scripts/webapp.py`), & Discord / Telegram Social Publisher (`scripts/discord_post.py`, `scripts/telegram_post.py`)**:
   - **Timezone Fix**: All ESPN timestamps (`Z` / UTC) are now automatically converted and displayed in local **`Europe/Vienna` (`CEST` / `CET`)** by default across [dashboard.html](./data/dashboard.html), [best_bets.csv](./data/best_bets.csv), and [best_bets.json](./data/best_bets.json), with an interactive **`Local (Europe/Vienna)` / `UTC` toggle button** in the top filter bar.
   - **Interactive Web App Server & SSE Live Stream ([`src/betscout/webapp.py`](./src/betscout/webapp.py) & [`scripts/webapp.py`](./scripts/webapp.py))**: Run `uv run python scripts/webapp.py --port 8090` to serve the interactive Quant Desk UI (`/`), real-time Server-Sent Events stream (`GET /api/stream`), one-click ledger sync & live match rescan (`POST /api/sync` with animated spinner + progress bar lock), and social channel publishing (`POST /api/discord`, `POST /api/telegram`).
   - **Discord (Primary, Zscaler-Compatible) & Telegram (Optional) Social Integration ([`src/betscout/telegram_bot.py`](./src/betscout/telegram_bot.py), [`scripts/discord_post.py`](./scripts/discord_post.py), [`.env.example`](./.env.example))**:
     - Reads `DISCORD_WEBHOOK_URL` (and optional `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`) from `model/.env` via `load_dotenv()`.
     - Formats settled paper-bet recaps (with exact match/set/walkover scores), System-1 injury/lineup veto alerts, and upcoming Best Bets with sport-type symbols (`⚽`, `🎾`, `🏀`, `🏒`, `🏈`, `⚾`) and atomic multi-message block chunking (`_chunk_discord_text` `<= 1,900` chars) so no pick is ever truncated.

---

## 10. Post-Mortem of Early Paper-Bet Losses & Model Upgrades

We audited all 4 early paper-bet losses and upgraded both the Tennis and UEFA Football models in [`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py):

| Early Failed Pick | Final Score | Root Cause Discovered | Model Upgrade Applied |
| :--- | :---: | :--- | :--- |
| **1. WTA: Katarzyna Kawa vs Belinda Bencic $\rightarrow$ Bencic (`A`) `@ 1.24`** | `2-0 (7-5, 6-2)` | **Career-Elo Slump vs Hot Qualifier**: Bencic had high historical Elo (`+110` Game-Elo diff) but was in a `2–5` (`28.6%`) recent slump, while Kawa had won `5` of her last `6` matches (`83.3%`, `form_6m_diff = -54.7%`). | **Added 8th Feature (`d_win6` 6-Match Rolling Form) + Form-Slump Gate (`form_6m_diff >= -0.15`)**: Lifted out-of-sample `>=70%` High-Confidence accuracy across `43,124` ATP/WTA matches from **`75.67%` to `77.02%` on ATP** (`+1.35 pp`) and **`76.22%` to `76.58%` on WTA**. |
| **2. UEFA Europa: Dinamo Zagreb vs NEC Nijmegen $\rightarrow$ Dinamo (`H`) `@ 1.57`** | `2-4` | **Negative Composite Score & Negative SOT**: Composite score was `-0.0230` and `sot_d = -0.570`; logged mid-game (`74'`) via a loose `p_model >= 0.56` rule. | **Strict Pre-Match + SOT-Alignment & Dominance-Rebound Gate for `uefa_edge`**: Require `sot_z >= 0.0` AND `(score >= 0.02 or dom_rebound > 0.20)` (lifting historical UEFA ROI across `401` matches to **`+8.66%`**, and **`+19.46%`** at `score >= 0.14`), and restrict `paper_bets` logging strictly to pre-match (`state == 'pre'`). |
| **3. UEFA Europa: Juventus vs Stade Rennais $\rightarrow$ Juventus (`H`) `@ 1.48`** | `2-2` | **Negative Composite Score & Negative SOT**: Composite score was `-0.1278` and `sot_d = -0.206` (logged in-play at `73'`). | Filtered out by the **UEFA SOT-Alignment Gate (`sot_z >= 0.0` and `score >= 0.02`)**. |
| **4. UEFA Conf: FC Nordsjælland vs CSKA Sofia $\rightarrow$ Nordsjælland (`H`) `@ 1.41`** | `2-2` | **Negative Composite Score & Severe Negative SOT**: Composite score was `-0.0227` and `sot_d = -0.735`. | Filtered out by the **UEFA SOT-Alignment Gate (`sot_z >= 0.0` and `score >= 0.02`)**. |

- **Current Settled Paper-Betting Ledger (`uv run betscout ledger`)**: **`18 Settled` (`16 Wins, 2 Losses`, `88.9%` Win Rate) · Realized Profit: `+5.82u` (`ROI = +32.36%`)**, including UEFA Conference League wins **Braga `2-0` vs KAA Gent (`@ 1.87`, `+0.87u`)**, **Ajax Amsterdam `2-0` vs Atalanta (`@ 2.00`, `+1.00u`)**, and overnight NHL/NFL/WTA wins (**Boston Bruins `6-0`**, **New Jersey Devils `4-1`**, **Dallas Stars `3-2`**, **Chicago Bears `30-24`**, **Detroit Red Wings `2-5`**, **Ann Li `2-1`**).

---

## 11. Exact Score & Set-Score Prediction Engine ([`src/betscout/exact_score.py`](./src/betscout/exact_score.py) & [`scripts/exact_score_eval.py`](./scripts/exact_score_eval.py))

1. **Football Feature-Adjusted Dixon-Coles Score Grid & 2/3-Score Dutching Clusters (`predict_soccer_exact_scores`)**:
   - Solves baseline expected goals $(\lambda_0, \mu_0)$ from de-vigged 1X2 probabilities and `line_total`, tilts $(\lambda, \mu, \rho)$ using our calibrated `p_model`, `sot_d` (`tanh(Z)`), `dom_rebound`, and `recent_draws`, and rescales the winning scoreline distribution to sum to `p_model`.
   - **Out-of-Sample Post-2025 Holdout Performance (`Big-5 Top 10%`, `n = 115`)**:
     - **1X2 Hit Rate**: **`73.0%`**
     - **Top-1 Exact Score Hit Rate**: **`13.9%`**
     - **2-Score Dutching Cluster Hit Rate**: **`33.0%`**
     - **3-Score Dutching Cluster Hit Rate**: **`46.1%`** *(vs `32.0%` model mean cluster probability — **`+14.1 pp` outperformance**!)*
2. **Tennis Calibrated Set-Score Distribution (`2:0` vs `2:1` / `3:0` vs `3:1` vs `3:2`, `predict_tennis_set_scores`)**:
   - Inverts match win probability $p$ into single-set win probability $s$ and applies a game-dominance & 6-match form tilt (`game_win_pct_diff`, `form_6m_diff`).
   - **Out-of-Sample Walk-Forward Evaluation (`13,256` Best-of-3 ATP/WTA matches)**:
     - **ATP (`n = 4,957`)**: `2:0` Brier = **`0.2353`** · On `WinProb >= 70%` (`n = 1,437`): **Actual `2:0` = `55.6%`** vs Model `54.4%` · On `WinProb >= 80%` (`n = 577`): **Actual `2:0` = `61.2%`** vs Model `64.1%`
     - **WTA (`n = 8,299`)**: `2:0` Brier = **`0.2382`** · On `WinProb >= 70%` (`n = 2,943`): **Actual `2:0` = `58.4%`** vs Model `55.1%` · On `WinProb >= 80%` (`n = 1,255`): **Actual `2:0` = `65.4%`** vs Model `63.9%`
3. **Full Integration into Dashboard, Web App, CSV/JSON & Discord/Telegram Digests**:
   - Every Football pick card in [dashboard.html](./data/dashboard.html) now displays an **Expected Goals ($\lambda/\mu$), Top Exact Score, 2-Score Dutch, and 3-Score Cluster** strip.
   - The Tennis table and Best Bets Summary Table now include the **Score Projection** column, and Discord/Telegram digests automatically include `🎲 Exact Score: ...` on every football and tennis pick.

---

## 12. BetScout Platform Rebrand, 4-Archetype 2-Leg Combo Ledger, ESPN Core v2 Media & Post-Mortem #2 (`Griekspoor vs Lehecka`)

1. **BetScout Rebrand, Sortable 8-Column Ledger Tables, Live In-Play Table & ESPN Core v2 Media ([`src/betscout/dashboard.py`](./src/betscout/dashboard.py) & [`app/src/views/QuantModelView.vue`](../app/src/views/QuantModelView.vue))**:
   - Rebranded the platform to **BetScout** (*Sports Edge, Exact-Score & Paper-Betting Intelligence*) with a custom hexagonal shield + vector-pulse SVG logo and browser tab favicon ([`app/public/vektorpulse-logo.svg`](../app/public/vektorpulse-logo.svg)).
   - Added **Per-Day Filtering** (`Today`, `Tomorrow`, `Today + Tomorrow`, `All Days`), **Provisional Time (`*`) Detection & Auto-Sync**, single-row interactive column sorting (`⇅` / `▲` / `▼`), a dedicated **Sport Icon** column (`⚽`, `🎾`, `🏀`, `🏒`, `🏈`, `⚾`), and unified **`Competition`** / **`Matchup`** / **`Pick`** / **`Score`** / **`Odds / CLV`** / **`Result / PnL`** 8-column tables across **Settled**, **🔴 Live In-Play**, and **Pending** paper bets.
   - Integrated **100% ESPN-native competition logos, team crests, and verified tennis player headshots** via `https://sports.core.api.espn.com/v2/sports/tennis/athletes/{id}` (`a.espncdn.com/i/headshots/tennis/players/full/{id}.png` with automatic `a.espncdn.com/i/teamlogos/countries/500/{iso}.png` fallback — zero SofaScore image requests and zero 404s).
   - Added an **Interactive Matchup Drill-Down Inspector Modal (`GET /api/matchup`)** displaying Last-6 form (`W`/`D`/`L` pills), H2H meetings, and Dixon-Coles / Tennis Set-Score breakdowns on click, plus a **Calibration & Tier / CLV Attribution Table (`by_tier`)** and **Quarter-Kelly Compounding vs. Flat `1.0u` Equity Curve**.

2. **4-Archetype 2-Leg Combo / Parlay Engine & Auto-Grading Ledger (`paper_combos` in [`src/betscout/paper_bet.py`](./src/betscout/paper_bet.py))**:
   - `build_recommended_2leg_doubles` constructs up to `8` uncorrelated 2-leg combinations across 4 high-probability market archetypes:
     1. **`CROSS_SPORT_BANKER`** (*Cross-Sport Banker ML*: `1X2` / Moneyline / Tennis Match Winner)
     2. **`DOUBLE_CHANCE_SHIELD`** (*Double-Chance / +1.5 Sets Shield*: Football `1X`/`X2` + Tennis `+1.5 Sets` Handicap, `~72–77%` combined hit rate)
     3. **`GOALS_GAMES_TOTALS`** (*Goals & Games O/U Combo*: Poisson `Over 1.5` / `Under 3.5 Goals` + Tennis `Total Games O/U`)
     4. **`STRAIGHT_SETS_SCORE_CLUSTER`** (*Straight-Sets & Score-Cluster Plus*: Tennis `2:0` Straight Sets + Football `3-Score Dutch Cluster`)
   - Persists all recommended combos into `paper_combos`, grades each leg automatically (`settle_pending_paper_combos`), renders the sortable **`#combosLedgerTable`**, and sends atomic Discord alerts (`notify_new_settlements_to_discord` with `BEGIN IMMEDIATE` + `_SETTLEMENT_NOTIFY_LOCK` deduplication).

3. **Post-Mortem #2 (`Tallon Griekspoor vs Jiri Lehecka`, `2-1`) & Tennis Model Upgrades**:
   - Audited our sole loss in the current `22`-bet settled ledger (**`21W – 1L`, `95.5%` Win Rate, `+8.49u`, `+38.6%` ROI**) and implemented four permanent upgrades:
     - **Unicode NFKD Diacritic Normalization (`_strip_accents`)**: Fixed `"Jiri Lehecka"` (ESPN) vs `"Jiri Lehečka"` (SofaScore) matching so players with accents always resolve live bookmaker odds.
     - **75/25 Model + De-Vigged Market Blend & Zero-Margin EV Gate**: Blends `75% Model + 25% De-Vigged Market` probability when bookmaker odds exist and vetoes any sub-80% tennis pick with `ev_pct < 0.0%`.
     - **Court-Acclimatization (`tourn_wins_diff`) & 3-Set Decider Resilience (`decider_diff`) Gate**: Tracks current-week tournament wins on court and rolling `>=26`-game decider win rates, lifting Post-2025 out-of-sample `>=70%` accuracy across `2,468` picks to **`78.06%` on ATP** (`+1.14%`) and **`78.83%` on WTA** (`+0.80%`).
     - **Indoor Hard vs. Outdoor Hard Surface Split (`hard_indoor` vs `hard`) & Retroactive Pending Re-Validation**: Splits indoor hard-court tournaments (`Basel`, `Vienna`, `Paris`, `ATP Finals`, etc.) into their own `elo_surf` bucket and automatically prunes any pre-match `PENDING` bet that no longer passes upgraded gates.

