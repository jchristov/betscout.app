# ⚡ VektorPulse — User Manual & Feature Reference Guide

**VektorPulse** (`sportdata-model` + WebApp + Vue 3 PWA) is an out-of-sample validated multi-sport prediction, exact-score projection, 2-leg combo/parlay, and prospective paper-betting intelligence platform covering:
- **⚽ 15 Football Competitions:** Big-5 European Leagues (`eng.1`, `esp.1`, `ger.1`, `ita.1`, `fra.1`), Secondary European Leagues (`ned.1`, `por.1`, `eng.2`, `aut.1`), UEFA Club Competitions (`uefa.champions`, `uefa.europa`, `uefa.europa.conf`, `uefa.super_cup`, `uefa.wchampions`), and `fifa.world`.
- **🎾 ATP & WTA Tennis:** Outdoor Hard (`hard`), Indoor Hard (`hard_indoor`), Clay (`clay`), and Grass (`grass`) across Grand Slams, Masters 1000, ATP/WTA 500 & 250 Main Draws and Qualifying rounds.
- **🏀🏒🏈⚾ US Major League Sports:** `NBA`, `NHL`, `NFL`, and `MLB`.

---

## 📑 Table of Contents
1. [Sports & Championships Covered in Database (`59,062` Matches)](#0-sports--championships-covered-in-database-59062-matches)
2. [Quick Start & Launching the WebApp](#1-quick-start--launching-the-webapp)
2. [Header Bar & Global Live Controls](#2-header-bar--global-live-controls)
3. [Day, Sport, Timezone, Bankroll & Min-Odds Filter Bar](#3-day-sport-timezone-bankroll--min-odds-filter-bar)
4. [🎯 Smart Bet Slip & Stake Allocation Optimizer](#4--smart-bet-slip--stake-allocation-optimizer)
5. [🎲 Exact-Score & Set-Score Dutching Investment Splitter](#5--exact-score--set-score-dutching-investment-splitter)
6. [🔍 On-Demand Any-Matchup Live Analyzer](#6--on-demand-any-matchup-live-analyzer)
7. [💎 Bookmaker Odds Mispricing & Unpriced Edge Detector](#7--bookmaker-odds-mispricing--unpriced-edge-detector)
8. [📈 Expanding-Window Monthly Forward-Walking Backtest Audit](#8--expanding-window-monthly-forward-walking-backtest-audit)
9. [Sport-Specific Recommendation Cards & Tables](#9-sport-specific-recommendation-cards--tables)
10. [🔗 2-Leg High-Probability Combos & Parlay Engine](#10--2-leg-high-probability-combos--parlay-engine)
11. [Prospective Paper-Betting Ledger (Settled, Live In-Play & Pending)](#11-prospective-paper-betting-ledger-settled-live-in-play--pending)
12. [Best Bets Summary Table & Custom Slip Checkboxes (`☑️`)](#12-best-bets-summary-table--custom-slip-checkboxes-️)
13. [Matchup Drill-Down Inspector Modal (`🔍`)](#13-matchup-drill-down-inspector-modal-)
14. [💬 Discord & Telegram Publishing & Automated Alerts](#14--discord--telegram-publishing--automated-alerts)
15. [Quantitative Model Gates & Safety Guardrails](#15-quantitative-model-gates--safety-guardrails)
16. [CLI Reference & Environment Configuration (`.env`)](#16-cli-reference--environment-configuration-env)

---

## 0. Sports & Championships Covered in Database (`59,062` Matches)

All historical and live records are stored in a single canonical SQLite database: **`model/data/matches.sqlite`** (`0` quality errors across `59,062` verified matches and `27` active championships across **7 sports**).

| Sport | League Key | ESPN Slug | Championship / Competition Name | Verified Matches | Date Range |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **⚽ Football (Soccer)** | `esp.1` | `esp.1` | **Spanish La Liga** | `1,803` | `2022-01` – Present |
| **⚽ Football (Soccer)** | `eng.1` | `eng.1` | **English Premier League** | `1,788` | `2022-01` – Present |
| **⚽ Football (Soccer)** | `ita.1` | `ita.1` | **Italian Serie A** | `1,782` | `2022-01` – Present |
| **⚽ Football (Soccer)** | `fra.1` | `fra.1` | **French Ligue 1** | `1,553` | `2022-01` – Present |
| **⚽ Football (Soccer)** | `ger.1` | `ger.1` | **German Bundesliga** | `1,432` | `2022-01` – Present |
| **⚽ Football (Soccer)** | `aut.1` | `aut.1` | **Austrian Bundesliga** | `922` | `2022-02` – Present |
| **⚽ Football (Soccer)** | `ned.1` | `ned.1` | **Dutch Eredivisie** | `548` | `2025-01` – Present |
| **⚽ Football (Soccer)** | `por.1` | `por.1` | **Portuguese Primeira Liga** | `541` | `2025-01` – Present |
| **⚽ Football (Soccer)** | `uefa.europa` | `uefa.europa` | **UEFA Europa League** | `339` | `2022-09` – Present |
| **⚽ Football (Soccer)** | `uefa.champions` | `uefa.champions` | **UEFA Champions League** | `324` | `2025-01` – Present |
| **⚽ Football (Soccer)** | `uefa.europa.conf` | `uefa.europa.conf` | **UEFA Conference League** | `233` | `2025-02` – Present |
| **⚽ Football (Soccer)** | `eng.2` | `eng.2` | **English Championship** | `110` | `2026-08` – Present |
| **⚽ Football (Soccer)** | `fifa.world` | `fifa.world` | **FIFA World Cup** | `105` | `2022-11` – `2026-07` |
| **⚽ Football (Soccer)** | `uefa.nations` | `uefa.nations` | **UEFA Nations League** | `102` | `2022-06` – Present |
| **🎾 Tennis** | `wta` | `wta` | **WTA Tour** (Grand Slams, WTA 1000/500/250 & Qualies) | `24,776` | `2022-01` – Present |
| **🎾 Tennis** | `atp` | `atp` | **ATP Tour** (Grand Slams, Masters 1000, 500/250 & Qualies) | `18,392` | `2021-09` – Present |
| **🏐 Volleyball** | `wvolleyball` | `womens-college-volleyball` | **NCAA Women's Volleyball** | `1,537` | `2026-09` – Present |
| **🏐 Volleyball** | `mvolleyball` | `mens-college-volleyball` | **NCAA Men's Volleyball** | `476` | `2026-03` – `2026-05` |
| **🏀 Basketball** | `nba` | `nba` | **NBA** (National Basketball Association) | `521` | `2026-03` – Present |
| **🏀 Basketball** | `ncaaw` | `womens-college-basketball` | **NCAA Women's Basketball** | `218` | `2026-03` – `2026-04` |
| **🏀 Basketball** | `ncaam` | `mens-college-basketball` | **NCAA Men's Basketball** | `152` | `2026-03` – `2026-04` |
| **🏀 Basketball** | `fiba` | `fiba` | **FIBA Basketball** (FIBA World Cup / Qualifiers) | `36` | `2026-09` – Present |
| **🏀 Basketball** | `nbl` | `nbl` | **NBL** (Australian National Basketball League) | `34` | `2026-09` – Present |
| **🏀 Basketball** | `wnba` | `wnba` | **WNBA** (Women's National Basketball Association) | `25` | `2026-09` – Present |
| **🏒 Ice Hockey** | `nhl` | `nhl` | **NHL** (National Hockey League) | `678` | `2026-03` – Present |
| **🏈 American Football**| `nfl` | `nfl` | **NFL** (National Football League) | `479` | `2025-01` – Present |
| **⚾ Baseball** | `mlb` | `mlb` | **MLB** (Major League Baseball) | `156` | `2026-09` – Present |
| **TOTAL (7 Sports)** | **27 Leagues** | — | **All Configured Championships** | **`59,062`** | **`0` Quality Errors** |

---

## 1. Quick Start & Launching the WebApp

### Launch the Interactive VektorPulse WebApp Server (Recommended)
```bash
cd model
uv run vektorpulse --port 8090
# (or: uv run sportdata-webapp --port 8090)
```
Then open **`http://127.0.0.1:8090`** in your browser.

Running the WebApp server enables:
- **Real-time Server-Sent Events (SSE) streaming** (`/api/stream`) every 15 seconds.
- **Singleton 90-second Background Auto-Poller** that automatically settles finished matches, updates live in-play scores, checks T-60m Starting XIs, and pushes settled bet notifications to Discord.
- **On-Demand Live Matchup Analyzer** (`/api/analyze-live`) and **Matchup Drill-Down Inspector** (`/api/matchup`).

### Generate Standalone Static HTML / CSV / JSON Feeds
```bash
cd model
uv run sportdata-model                     # Full 4-stage pipeline: Ingest -> Quality -> Scan -> Dashboard
uv run sportdata-dashboard --min-odds 1.10 # Regenerate data/dashboard.html, best_bets.csv & best_bets.json
```

---

## 2. Header Bar & Global Live Controls

At the top of the VektorPulse WebApp, the header displays system metadata and 5 global action buttons:

| Control | Description |
| :--- | :--- |
| **`📡 Live SSE Stream`** | Shows connection status (`Connected` with green pulse dot when connected to `uv run vektorpulse`, or `Static File Mode` when opened via `file://`). |
| **`🔕 Live Alerts: OFF` / `🔔 ON`** | **Global toggle** for automated Discord push alerts on Live In-Play Dominance Rebound (`⚽`) and Set-1 Deficit Rebound (`🎾`) edges. **Default is `OFF`** so your Discord channel is never spammed. Persists in `data/webapp_settings.json` and `localStorage`. |
| **`🔄 Sync & Settle`** | Immediately polls ESPN & SofaScore to grade completed bets, update live in-play scores, and refresh the ledger without rescanning all future fixtures (~2–4 seconds). |
| **`⚡ Rescan Live`** | Re-runs the full multi-sport upcoming scanner (`scan_upcoming_and_log_paper_trades`), updates live bookmaker odds and CLV, and refreshes all recommendations (~25–40 seconds). |
| **`🚀 Full Pipeline`** | Executes all 4 stages from the browser: `[1/4]` Incremental ingestion across all 20 leagues $\rightarrow$ `[2/4]` Quality check $\rightarrow$ `[3/4]` Multi-sport scan & settlement $\rightarrow$ `[4/4]` Dashboard rebuild. |
| **`💬 Share Picks`** | Opens the **Discord & Telegram Social Publisher** panel with a pre-formatted Markdown digest of your currently filtered picks. |

> **Note on Provisional Kickoff Times (`*`):** Any match whose official court/pitch time has not yet been confirmed by the tournament (`time_valid == False` or ESPN's `04:00Z` placeholder) is marked with an asterisk (`*`, e.g., `2026-10-26 05:00 CET* (TBD)`) and updates automatically as soon as the official Order of Play is released.

---

## 3. Day, Sport, Timezone, Bankroll & Min-Odds Filter Bar

Two filter bars let you slice the entire dashboard in real time:

1. **Filter by Day (`04:00 AM` Betting-Slate Cutoff):**
   - Buttons for **`All Days`**, **`Today + Tomorrow`**, **`Today`**, **`Tomorrow`**, and subsequent dates.
   - **Smart Late-Night US Slate Grouping:** VektorPulse uses a **`04:00 AM` local time cutoff** (`Europe/Vienna`). Late-night NHL/NBA/NFL/MLB games kicking off between `00:00` and `03:59 CEST` (e.g., `Boston Bruins vs San Jose Sharks` at `01:00 CEST`) remain grouped with **Today's evening slate** rather than disappearing into Tomorrow's calendar date.
2. **Filter by Sport:**
   - Switch between `All Sports`, `Football`, `Tennis`, `Basketball (NBA)`, `Hockey (NHL)`, `American Football (NFL)`, and `Baseball (MLB)`.
3. **Instant Search:**
   - Filter cards and table rows by team name, player name, tournament, or competition.
4. **Timezone Switcher (`Local (Europe/Vienna)` vs `UTC`):**
   - Converts every kickoff timestamp across all cards and tables between `CET`/`CEST` and `UTC` with a single click.
5. **Bankroll (`€`) Calculator:**
   - Enter your total bankroll (default **`€1,000`**, persisted in `localStorage`). Every Football card and Best Bets row dynamically displays its recommended **Quarter-Kelly stake in both `%` and `€`** (e.g., `1.25% (€12.50)`).
6. **Soft Min-Odds Slider (`1.05` – `2.00`):**
   - Dynamically hides heavy-juice favorites below your chosen minimum odds threshold (default `> 1.10`).

---

## 4. 🎯 Smart Bet Slip & Stake Allocation Optimizer

Located directly below the KPI row, the **Smart Bet Slip Optimizer** takes the exact amount you are ready to bet today and builds **3 side-by-side strategies** from the active Best Bets pool:

### Controls
- **`Ready to Bet (€)` Input & Presets:** Enter any amount or click **`€25`**, **`€50`**, **`€100`**, **`€250`**, **`€500`**.
- **Risk Mode Selector:**
  - `⚖️ Balanced (Safe 2-Leg + Top 4 Singles)`
  - `🛡️ Ultra-Safe Fortress (Max Hit Rate ≥72%)`
  - `🚀 Max Return Multiplier (3-Leg Booster + Value Singles)`
- **`🖨️ Print / PDF Slip` Button:** Opens a clean printer- and Save-as-PDF-ready ticket of your 3 strategy options.

### The 3 Generated Strategy Options
1. **Option A · Safe Uncorrelated Multiplier Combo (`2-Leg` or `3-Leg` Parlay):**
   - Selects the highest-safety, highest-EV picks across **different competitions/sports** (preventing single-competition correlation risk) to maximize total payout on a single ticket.
2. **Option B · Separate Individual Bets (Kelly-Weighted Singles Portfolio):**
   - Splits your `€` budget across **3 to 5 independent singles** weighted by Model Win Probability and Quarter-Kelly edge (rounded to `€0.50`). Protects your bankroll so a single upset never wipes out your stake (`>90%` probability that at least $N-1$ singles hit).
3. **Option C · 65/35 Core Singles Floor + Combo Booster (`★ Optimal Sharpe Split`):**
   - Allocates **65% of your budget** to the Top 2 Core Singles (whose return covers nearly your entire initial budget) and **35%** to the 2-Leg Multiplier Combo for upside.

---

## 5. 🎲 Exact-Score & Set-Score Dutching Investment Splitter

When you want to bet on **Exact Scores** (`1:0`, `2:0`, `2:1` in Football) or **Exact Set Scores** (`2:0`, `2:1` in Tennis) for a high-quality match, this tool calculates the exact `€` to place on each scoreline so your payout is identical regardless of which score hits:

1. **Select a Match:** Choose any high-conviction Football or Tennis match from the **`Match:`** dropdown — or click the **`🎲 Split €`** button on any Football card or Best Bets row to jump straight to that match.
2. **Set Your Investment (`€`):** Enter any amount or click **`€10`**, **`€20`**, **`€25`**, **`€50`**, **`€100`**.
3. **Edit Live Bookmaker Score Odds (`✏️`):**
   - Each projected score (`#1`, `#2`, `#3`) displays its Model Probability, Fair Odds, and an **editable Odds input box**.
   - Type the exact live odds from your sportsbook (for example, `1:0 @ 3.80` and `2:0 @ 5.50`) — the engine immediately recalculates the inverse-odds weights ($w_i = \frac{1/O_i}{\sum 1/O_k}$) and exact `€` stakes!
4. **Compare 3 Dutching Sets:**
   - **Set A · 2-Score Precision Dutch (`★ HIGHEST PAYOUT`):** Equal-payout split across the Top 2 exact scores (e.g. `€14.79` on `1:0 @ 3.80` + `€10.21` on `2:0 @ 5.50` = **`€56.18` payout / `2.25x` effective odds**).
   - **Set B · 3-Score Wide Shield (`★ 46% OOS HIT RATE`):** Equal-payout split across all Top 3 exact scores (`1:0 / 2:0 / 2:1`).
   - **Set C · 65/35 Winner Floor + Exact-Score Booster:** Places **65%** on the Main Pick Moneyline/1X2 (protecting any win such as `3:2` or `4:1`) + **35%** on the 2-Score Precision Dutch.

---

## 6. 🔍 On-Demand Any-Matchup Live Analyzer

Want to check a match that isn't in `best_bets.json` (for example, a 55/45 Tennis match or a derby that our model passed on)?

- Type **any two players or teams** separated by `vs` into the **🔍 On-Demand Any-Matchup Live Analyzer** bar (e.g., `Medvedev vs Bublik`, `Bernet vs Altmaier`, `Chelsea vs Tottenham`) and click **`⚡ Analyze Matchup`**.
- The server (`GET /api/analyze-live`) queries `matches.sqlite` + live SofaScore feeds on the fly to compute:
  - **Live Elo & Game-Share Elo Differential** (Tennis) or **Club Elo & 6-Match Rolling Shots-on-Target Differential** (Football),
  - **All-Level Last-5 Win Rate** (including ATP/WTA Challenger & ITF matches),
  - **Rest & Turnaround Hours** since each player's previous match (and previous tournament city),
  - **Color-Coded Verdict Badge**:
    - 🟢 **Green (`✅ STRONG BANKER`)**: WinProb $\ge 70\%$ with aligned form and rest.
    - 🟠 **Amber (`⚖️ SOLID VALUE LEAN`)**: WinProb $58\%–69.9\%$ with clean form/rest.
    - 🔴 **Red (`⛔ NO-BET / HIGH VARIANCE`)**: Sub-58% coin flip, severe form divergence (`1-4` vs `5-0`), or `<36h` cross-city turnaround warning.
  - **3 Side-by-Side Market Verdicts:**
    1. `1️⃣ Moneyline / 1X2`
    2. `2️⃣ Handicap / Shield` (`+1.5 Sets`, `2:0 Straight Sets`, or `1X / X2 Double Chance`)
    3. `3️⃣ Totals / Score Cluster` (`Over/Under Games` or `Over 1.5 Goals & 3-Score Dutch Cluster`)

---

## 7. 💎 Bookmaker Odds Mispricing & Unpriced Edge Detector

Whenever VektorPulse detects a match where our calibrated model probability exceeds the bookmaker's de-vigged implied probability by **$\ge +2.0\text{pp}$** AND Expected Value is **$\ge +2.0\%$**, the match is surfaced in the **💎 Bookmaker Odds Mispricing & Unpriced Edge Detector**:

- Shows **Model Prob vs. Market Implied Prob (`+Edge pp`)**, **Bookmaker Odds vs. Fair Model Odds**, **Expected Value (`EV %`)**, and the exact **Unpriced Edge Drivers** that bookmakers failed to price in (such as `sot_d=+0.95z, dom_rebound=+1.00z, h2h_adv=+0.93z` in Football, or `SurfElo +185, GameElo +120` in Tennis).
- Also attaches a **`💎 EDGE +X.Xpp (EV +Y.Y%)`** badge directly to those rows in the **Best Bets Summary Table**.

---

## 8. 📈 Expanding-Window Monthly Forward-Walking Backtest Audit

Click the collapsible **📈 Expanding-Window Monthly Forward-Walking Backtest Audit (`2025-07 -> 2026-10`)** bar to inspect our zero-lookahead out-of-sample validation across all `56,501` matches:
- At the start of every month $M$, scalers, quantile thresholds, and logistic probability calibrators are refit strictly on matches `< M` and tested on month $M$:
  - **⚽ Big-5 Football (`top_8pct`):** `99` bets · `73.7%` Win Rate · **`+18.76u` (`+18.95%` ROI · Sharpe `2.54`)**
  - **⚽ Big-5 Football (`top_10pct`):** `134` bets · `71.6%` Win Rate · **`+21.95u` (`+16.38%` ROI · `11/13` profitable months)**
  - **⚽ All 9 Domestic Leagues (`top_8pct`):** `174` bets · `72.4%` Win Rate · **`+27.37u` (`+15.73%` ROI · Sharpe `2.81`)**
  - **🎾 ATP Tennis (`>=70%` Banker):** `715` bets · **`79.16%` Accuracy** (`84.24%` at `>=80%`)
  - **🎾 WTA Tennis (`>=70%` Banker):** `1,305` bets · **`79.77%` Accuracy** (`83.51%` at `>=80%`)
  - **🏀🏒🏈⚾ US Major Sports (`top_15pct`):** `102` bets · **`68.6%` Hit Rate (`+8.4pp` over market · `+9.68%` ROI)**

---

## 9. Sport-Specific Recommendation Cards & Tables

1. **⚽ Upcoming Football Picks Cards:**
   - Displays competition logo, team crests, tier (`top_8pct`, `top_10pct`, `top_15pct`, `top_25pct`), action badge (`PAPER_BET` or `VETOED_BY_...`), Quarter-Kelly stake (`%` and `€`), Best 1X2 odds, Synthetic Dutch Double-Chance (`1X`/`X2`) odds, Dixon-Coles Expected Goals ($\lambda/\mu$), Top Exact Score, 2-Score & 3-Score Dutching Clusters, 7-Factor horizontal `tanh(Z)` bars, **System-1 `laya-sports` News Gate**, and **T-60m Starting XI Gate**.
2. **🎾 Upcoming Tennis Picks Table (ATP & WTA):**
   - Displays player studio headshots (via ESPN Core v2 API with automatic country-flag fallback), tournament surface pill (`HARD`, `HARD_INDOOR`, `CLAY`, `GRASS`), calibrated Win Probability, Straight-Sets (`2:0`/`0:2`) vs Decider (`2:1`/`1:2`) projections, Recommended Total Games Over/Under (`21.5`/`22.5`), Min Fair Odds, Live SofaScore Bookmaker Odds, and Game/Surface Elo differentials.
3. **🏀🏒🏈⚾ Upcoming Major League Picks Table (NBA · NHL · NFL · MLB):**
   - Displays team crests, injury availability pill (`Out: X vs Y`), calibrated Model vs Market Win Probability, Min Fair Odds, Bookmaker Odds, and EV%.

---

## 10. 🔗 2-Leg High-Probability Combos & Parlay Engine

VektorPulse automatically constructs up to **8 uncorrelated 2-leg parlays** across **4 strategic market archetypes** and tracks them prospectively in the `paper_combos` SQLite table:

1. **`CROSS_SPORT_BANKER` (Cross-Sport Banker ML):** Pairs two high-probability Moneyline/1X2 favorites (`1.18 – 1.75` per leg) from different sports or leagues.
2. **`DOUBLE_CHANCE_SHIELD` (Double-Chance / `+1.5 Sets` Shield):** Pairs Football Double Chance (`1X`/`X2`) with Tennis Set Handicap (`+1.5 Sets`, winning at least 1 set).
3. **`GOALS_GAMES_TOTALS` (Goals & Games Over/Under Totals):** Pairs Dixon-Coles `Over 1.5` / `Under 3.5 Goals` with Tennis `Under/Over Total Games`.
4. **`STRAIGHT_SETS_SCORE_CLUSTER` (Straight-Sets & 3-Score Cluster Plus):** Higher-payout combos pairing Tennis `2:0` Straight Sets with Football 3-Score Dutching Clusters.

All logged combos are graded automatically in the **🔗 Prospective 2-Leg Combo / Parlay Ledger** table (`✅ HIT` / `❌ MISS` per leg; if Leg 1 loses, the combo immediately settles as `LOST (-1.00u)`).

---

## 11. Prospective Paper-Betting Ledger (Settled, Live In-Play & Pending)

All three single-bet ledger tables share an identical, fixed-width **8-column sortable layout** (`Sport`, `Competition`, `Kickoff`, `Matchup`, `Pick`, `Score`, `Odds / CLV`, `Result / PnL`):

1. **Settled Paper-Bets Table & Analytics:**
   - **Standalone Full-Width Equity Curve Chart (`760×155` SVG):** Plots both the **Flat `1.0u` PnL curve** (blue) and the **Quarter-Kelly Compounding Bankroll curve** (green dashed).
   - **Performance by Sport Table** & **Calibration & Tier / CLV Attribution Table** (`Exp Win%` vs `Realized Win%` and `Mean CLV`).
   - Marks any settled bet whose final score matched our pre-match Top-1 Exact Score or 3-Score Cluster with **`🎯 Exact/Cluster HIT`**.
2. **🔴 Live In-Play Paper-Bets Table:**
   - Active matches automatically move here during play (`15s` SSE updates), showing live scores, current virtual PnL (`LEADING`, `LEVEL`, `TRAILING`), live Football boxscore telemetry (`SoT`, `Possession %`), **`🔥 REBOUND EDGE`** badges, and a **per-match `🔕` / `🔔` alert toggle button** right next to each row.
   - Includes automatic **SofaScore Live Tennis Scoreboard Fallback** for ATP/WTA Qualifying matches when ESPN leaves qualifying status in pre-match state.
3. **Pending Paper-Bets Awaiting Kickoff Table:**
   - Tracks opening vs latest closing odds and real-time **Closing Line Value (`CLV %`)** prior to kickoff.

---

## 12. Best Bets Summary Table & Custom Slip Checkboxes (`☑️`)

At the bottom of the dashboard, the **Best Bets Summary Table** consolidates all qualifying picks across all sports, sorted chronologically by kickoff:
- **Click any column header** (`Sport`, `Competition`, `Kickoff`, `Matchup`, `Pick`, `Win Prob`, `Min Fair Odds`, `Score Projection`, `Odds / CLV`) to sort ascending/descending (`▲` / `▼`).
- **`☑️` Custom Slip Checkboxes:** Check any 2–6 rows in the leftmost column to switch the **Smart Bet Slip Optimizer** at the top of the page into **`☑️ CUSTOM SLIP`** mode, calculating Option A (Combo), Option B (Kelly Singles), and Option C (65/35 Hybrid) **exclusively for your hand-picked matches**!
- **`🎲 Split €` Button:** Jumps straight to the **Exact-Score Investment Splitter** pre-loaded with that match.
- **`📣` Share Button:** Opens the Discord/Telegram modal pre-loaded with a single-pick spotlight post.
- **`Export CSV (with Header)` & `Export JSON` Buttons:** Download the currently filtered Best Bets table.

---

## 13. Matchup Drill-Down Inspector Modal (`🔍`)

Click on **any matchup name** in any table (or click **`🔍 Full H2H & Dutching`** inside the Live Analyzer) to open the **Matchup Drill-Down Inspector Modal**:
- **📈 Last-6 Form Side-by-Side:** Shows `W` / `D` / `L` badges, opponent, home/away venue, score, and date for both teams/players.
- **⚔️ Head-to-Head History:** Lists all prior meetings in the database with dates and scores.
- **🎲 Interactive Modal Dutching Calculator:** Displays the Dixon-Coles Score Projection or Tennis Set-Score distribution with a live `Dutching Stake (€)` input.

---

## 14. 💬 Discord & Telegram Publishing & Automated Alerts

Click **`💬 Share Picks`** in the header (or run `uv run sportdata-discord`) to publish formatted digests:
- **Automatic Smart Chunking:** Long digests are split cleanly at match boundaries (`<= 1,900` chars) so Discord never truncates a message.
- **Atomic Settlement Notifications (`notify_new_settlements_to_discord`):** Uses a thread lock + SQLite `BEGIN IMMEDIATE` transaction so each newly settled single bet or 2-leg combo is announced to Discord **at most once**.
- **Toggleable Live In-Play Rebound Alerts (`notify_inplay_rebound_edges_to_discord`):**
  - **Default: `OFF` globally.**
  - Can be toggled **globally** via the header button (`🔕 Live Alerts: OFF` / `🔔 ON`) or **individually per live match** via the `🔕` / `🔔` button on each row in the **🔴 Live In-Play** table.

---

## 15. Quantitative Model Gates & Safety Guardrails

Every pick in VektorPulse must pass a strict sequence of out-of-sample validated safety gates before entering the ledger:

1. **⚽ Football Gates:**
   - **7-Factor Orthogonal Composite (`tanh(Z)`):** Combines de-vigged `p_mkt`, `vig_neg`, opponent-adjusted `sot_d` (Shots on Target diff), `discipline` (fouls diff), `h2h_adv`, `dom_rebound` (unlucky dominance rebound), and `recent_draws`.
   - **Secondary Domestic League Gate (`ned.1, por.1, eng.2, aut.1`):** Requires positive rolling Shots-on-Target dominance (`sot_z > 0.20`), positive `dom_rebound`, and `EV >= +1.5%` for `top_15pct` picks (`+5.23%` OOS ROI).
   - **System-1 `laya-sports` News Gate:** Vetoes picks with severe negative injury/rotation news (`net_edge_for_pick <= -0.25`).
   - **Position-Specific T-60m Starting XI Gate:** Automatically checks official ESPN lineups within 60 minutes of kickoff and vetoes the bet if:
     - Starting XI attacking share (`G + 0.7A + 0.2SoT` over last 6 matches) drops below `< 50%` (or `< 60%` without the top scorer), OR
     - Both the primary Goalkeeper (`GK`) is missing AND `< 50%` of the regular defensive spine starts (`VETOED_DEPLETED_DEFENSE`).
2. **🎾 Tennis Gates:**
   - **8-Feature Surface + Indoor/Outdoor Hard + Game-Dominance Model:** Separate Elo ratings for `hard`, `hard_indoor`, `clay`, `grass`, plus `game_elo` and rolling 10-match game-win share.
   - **Form-Slump & Decider / Court-Acclimatization Gates:** Vetoes `<80%` favorites with worse 6-match form (`< -15pp`), worse 3-set decider record (`< -20pp`), or fewer current-week wins on court (`tourn_wins_diff <= -1`).
   - **Qualifying Game-Share & Form Alignment Gate:** In Qualifying rounds, vetoes `<82%` favorites with non-positive rolling game-share (`game_win_pct_diff <= 0`) or non-positive form (`form_6m_diff <= 0`).
   - **All-Level Challenger/ATP Last-5 Form & Market-Divergence Gate:** Queries SofaScore's all-level match history (`ATP + Challenger + ITF`) and vetoes any pick at `<= 25%` (`1-4`) facing an opponent at `>= 60%` (`3-2+`), or where model probability diverges `>= 15pp` above a sub-60% market line.
   - **Cross-Tournament `<38h` Turnaround Gate:** Vetoes `<80%` favorites playing within `<= 38h` of finishing a match in a different tournament city against a rested opponent.
   - **Automatic Draw-Change / Withdrawal Purge:** Automatically purges pending singles and combos if a player withdraws or ESPN redraws the competition slot.
3. **🏀🏒🏈⚾ US Major Sports Gates:**
   - **NBA Alignment Gate:** Requires Elo confirmation (`p_elo >= p_mkt - 0.02`), non-negative rest (`rest_adv >= 0`), and positive rolling FG% diff (`+14.49%` OOS ROI).
   - **NHL Alignment Gate:** Requires non-negative rest, positive Save% diff, and positive Shot-Volume diff (plus Dual-Dominance `>= 12.0` on road picks).

---

## 16. CLI Reference & Environment Configuration (`.env`)

### CLI Entrypoints (`model/pyproject.toml`)
| Command | Description |
| :--- | :--- |
| `uv run vektorpulse --port 8090` | Launch interactive VektorPulse WebApp + SSE stream + 90s auto-poller |
| `uv run sportdata-model` | Run full 4-stage daily pipeline (Ingest $\rightarrow$ Quality $\rightarrow$ Scan $\rightarrow$ Dashboard) |
| `uv run sportdata-bet --days 3` | Scan upcoming fixtures across all sports and update `paper_trades` & `paper_combos` |
| `uv run sportdata-dashboard` | Rebuild `data/dashboard.html`, `data/best_bets.csv`, and `data/best_bets.json` |
| `uv run sportdata-calibrate` | Run Post-Match Calibration, Brier Skill Score vs Market & Factor Attribution monitor |
| `uv run sportdata-edges` | Run multi-sport backtest & monthly expanding-window walk-forward evaluation |
| `uv run sportdata-exact-score` | Run Football Exact-Score / Cluster & Tennis Set-Score out-of-sample evaluation |
| `uv run sportdata-ledger` | Print Settled & Pending paper-betting ledger in terminal |
| `uv run sportdata-discord` | Publish daily picks & settled recap digest to Discord channel |

### Environment Variables (`model/.env`)
```ini
# Primary Social Publisher (Zscaler-compatible) — Global Fallback Webhook
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Optional: Per-Sport Dedicated Discord Webhooks (override DISCORD_WEBHOOK_URL for specific sports!)
# DISCORD_WEBHOOK_URL_SOCCER="https://discord.com/api/webhooks/..."
# DISCORD_WEBHOOK_URL_TENNIS="https://discord.com/api/webhooks/..."
# DISCORD_WEBHOOK_URL_HOCKEY="https://discord.com/api/webhooks/..."
# DISCORD_WEBHOOK_URL_BASKETBALL="https://discord.com/api/webhooks/..."
# DISCORD_WEBHOOK_URL_NFL="https://discord.com/api/webhooks/..."
# DISCORD_WEBHOOK_URL_BASEBALL="https://discord.com/api/webhooks/..."
# DISCORD_WEBHOOK_URL_US_SPORTS="https://discord.com/api/webhooks/..."

# Optional: Live In-Play Discord Alerts default (default is false / OFF)
INPLAY_ALERTS_ENABLED="false"

# Optional: Automated Morning Daily Digest Hour in Europe/Vienna time (e.g. 9 for 09:00 CEST)
# DAILY_DIGEST_HOUR="9"

# Optional: Remote Firebase / GCP Cloud Function URL for laya-sports checkpoint
# LAYA_REMOTE_URL="https://..."
```
