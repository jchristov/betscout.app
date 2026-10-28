# Laya Decision Model (`laya-sports` / `ms-decision-1`) — Out-of-Sample Ablation & Hypothesis Evaluation Report

**Date:** October 28, 2026  
**Preserved Feature Branch (with Laya ON):** [`feat/laya-decision-model`](https://github.com/jchristov/betscout.app/tree/feat/laya-decision-model)  
**Production Decision:** **Removed from active stack on `main`** (all player-availability protection is handled deterministically by the **Position-Specific T-60m Starting XI Confirmation Gate**, **Sportradar `stats_season_injuries`**, and **ESPN structured `injuries` roster counters**).

---

## 1. Executive Summary

We conducted an isolated, point-in-time ablation study and tested four alternative hypotheses to determine whether the unstructured news decision model (`Laya` / `laya_sports_ckpt`, distilled from `ms-decision-1`) improves out-of-sample betting accuracy or ROI when layered on top of BetScout's quantitative models and structured lineup/injury gates.

### Key Findings
1. **Out-of-Sample Big-5 Top-15% Ablation (`n = 207` Post-2025 Picks, `122` with Matched ESPN Articles):**
   - **Without Laya (`decision_backend="none"`)**: **`66.39%` Win Rate · `+9.63u` Flat-Unit Profit · `+7.89%` ROI**.
   - **With Laya Veto (`net_edge <= -0.50`)**: **`65.74%` Win Rate (`-0.65 pp`) · `+6.26u` Profit (`-3.37u`) · `+5.80%` ROI (`-2.09%` ROI)**.
   - The **`14` picks vetoed by Laya** actually went **`10W – 4L` (`71.4%` Win Rate, `+3.37u` Profit, `+24.07%` ROI)**!
2. **Negative Information Coefficient (`IC = -0.1727` with PnL):**
   - Across all `122` out-of-sample Post-2025 Big-5 Top-15% picks with matched ESPN articles, `corr(laya_net_edge, won) = -0.1388` and `corr(laya_net_edge, pnl) = -0.1727`.
   - Every tested threshold—whether used as a negative veto (`-0.80`, `-0.50`, `-0.35`, `-0.20`) or as a positive news booster (`> 0.0`, `> +0.20`, `> +0.50`)—**degraded out-of-sample ROI**.
3. **Prospective Live Ledger (`68` Settled Picks: `64W – 4L`, `94.1%` Win Rate, `+21.64u`, `+31.8%` ROI):**
   - `91` of `96` logged picks (`94.8%`) had zero Laya news articles (`Tennis`, `Table Tennis`, `Handball`, `Darts`, `NHL`, `NBA`, `NFL`, `MLB`).
   - All `5` settled football picks with non-zero Laya signals won (`5W – 0L`), while **none of the 4 prospective losses** in the ledger had any ESPN news articles.
   - On the live October 28, 2026 slate, Laya triggered a **false-positive veto (`net_edge = -0.7106`) on `Venezia vs Internazionale -> Inter (A) @ 1.33`** because ESPN attached an AC Milan article (*"Milan boss Ruben Amorim faces injury headache ahead of pre-derby Bologna game"*) whose body text mentioned *"Inter"* in passing.
4. **Structured Lineup & Injury Gates Already Provide Proven Alpha:**
   - Unlike unstructured ESPN league-roundup blurbs, the **Position-Specific T-60m Starting XI Confirmation Gate (`evaluate_starting_xi_gate`)** is proven across `1,258` Big-5 Top-15% matches to lift ROI from **`+3.03%` to `+3.66%`**, isolating `228` genuinely depleted lineups (`+0.16%` ROI).
   - Removing Laya eliminates an **`804 MB`** model checkpoint (`data/laya_sports_ckpt`), removes **`~150–200 ms/match`** of CPU subprocess latency, and prevents cross-team headline contamination while preserving 100% of BetScout's quantitative and structured-injury edge.

---

## 2. Architectural Scope: Where Laya Was Used vs. Not Used

| Subsystem / Sport | Quantitative Engine | Structured Injury / Lineup Gate | Unstructured Laya News Used? |
| :--- | :--- | :--- | :---: |
| **⚽ Football (`14` Leagues)** | 7-Factor Orthogonal `tanh(Z)` Composite + Logistic Calibrator + Dixon-Coles 28-Score Matrix | **T-60m Starting XI Gate** (`attack_share >= 50%`, `gk_starting`, `def_spine_share >= 50%`) + **Sportradar `stats_season_injuries`** | Yes (Post-filter veto `net_edge <= -0.50`) |
| **🎾 Tennis (`ATP / WTA`)** | 8-Feature Surface-Specific + Game-Dominance Logistic Regression + 75/25 Market Blend | SofaScore Rest/Turnaround (`<=38h` cross-city travel veto) & Adverse Line Drift Gate | **No** (`0%` coverage) |
| **🏒🏀🏈⚾ US Major Sports (`NHL, NBA, NFL, MLB`)** | 7-Factor Boxscore Efficiency + Rest/B2B + Rebound Composite + Elo | **ESPN Structured `summary["injuries"]`** (`Out` / `IR` / `Doubtful` player counter) | Post-filter veto only (`<5%` article coverage) |
| **🏓🤾🎯 European Sports (`Table Tennis, Handball, Darts`)** | Sportradar StatsHub Elo + Last-10 / Last-3 Form + Direct Last-H2H Gate | **3.5h Session Set Workload (`<13` sets)** + **5-Set Decider Hangover** + **48h Cold-Session Gate** | **No** (`0%` coverage) |

---

## 3. Out-of-Sample Post-2025 Big-5 Top-15% Ablation (`n = 207` Picks)

We evaluated all **`207` out-of-sample Post-2025 (`>= 2025-07-01`) Big-5 Top-15% Football picks** against their cached ESPN match summaries (`data/cache/sum_{league}_{event_id}.json`):
- `122` of the `207` matches had team-matched ESPN articles (`extract_team_news_text`).
- We scored all `122` matches using the fine-tuned **`laya-sports` (`data/laya_sports_ckpt`)** model and tested **four distinct hypotheses** for using `laya_net_edge` positively:

### Hypothesis Testing Across All `122` Out-of-Sample Matched-Article Picks

| Strategy / Hypothesis | Kept Picks (`n`) | Kept Win Rate | Kept Profit (`u`) | Kept ROI (`%`) | Vetoed Picks (`n`) | Vetoed Win Rate | Vetoed Profit (`u`) | Vetoed ROI (`%`) | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0. Baseline (`Laya OFF` — No News Filter)** | **`122`** | **`66.4%`** | **`+9.63u`** | **`+7.89%`** | `0` | — | `0.00u` | — | **Best Overall (`+9.63u`)** |
| **1. Production Veto (`net_edge > -0.50`)** | `108` | `65.7%` | `+6.26u` | `+5.80%` | `14` | **`71.4%`** | **`+3.37u`** | **`+24.07%`** | **Falsified (`-3.37u` lost)** |
| **2. Extreme Veto Only (`net_edge > -0.80`)** | `118` | `66.1%` | `+9.16u` | `+7.76%` | `4` | **`75.0%`** | **`+0.47u`** | **`+11.75%`** | **Falsified (`-0.47u` lost)** |
| **3. Moderate Veto (`net_edge > -0.20`)** | `106` | `66.0%` | `+6.81u` | `+6.42%` | `16` | **`68.8%`** | **`+2.82u`** | **`+17.62%`** | **Falsified (`-2.82u` lost)** |
| **4. Positive News Filter (`net_edge > 0.00`)** | `90` | `63.3%` | `+2.28u` | `+2.53%` | `32` | **`75.0%`** | **`+7.35u`** | **`+22.97%`** | **Falsified (`-7.35u` lost)** |
| **5. Positive News Booster (`net_edge > +0.20`)** | `55` | `58.2%` | `-3.74u` | `-6.80%` | `67` | **`73.1%`** | **`+13.37u`** | **`+19.96%`** | **Falsified (`-13.37u` lost)** |
| **6. Strong Hype Booster (`net_edge > +0.50`)** | `38` | `55.3%` | `-5.85u` | `-15.39%` | `84` | **`71.4%`** | **`+15.48u`** | **`+18.43%`** | **Falsified (`-15.48u` lost)** |

---

## 4. Root Causes of Why Unstructured News Fails to Add Alpha over Quantitative + Structured Gates

### Root Cause 1: League-Wide ESPN Article Contamination
ESPN's `summary["news"]["articles"]` endpoint does **not** return match-specific injury reports; it returns the latest 3–5 articles tagged to the league (e.g. Serie A, Bundesliga, Premier League). Whenever a rival club is mentioned in the article body, substring/alias matching attributes the rival club's crisis or boost to the current match:
- **Live Example (`2026-10-28`, `Venezia vs Internazionale`)**: ESPN attached *"Milan boss Ruben Amorim faces injury headache ahead of pre-derby Bologna game"*. Because the article body mentioned *"Inter"*, Laya scored `net_edge = -0.7106` and **falsely vetoed Internazionale (`@ 1.33`)**.
- **Historical Examples in `sum_{league}_{event_id}.json`**:
  - *"Bayern Munich coach Vincent Kompany doubtful for Arsenal game due to virus"* was attached to `Bayer Leverkusen vs TSG Hoffenheim`, `Bayer Leverkusen vs Borussia Mönchengladbach`, and `St. Pauli vs Bayer Leverkusen`.
  - *"Ruben Amorim still unbeaten in Serie A after Milan win"* was attached to `Parma vs Atalanta`, `Atalanta vs Lecce`, `Cremonese vs Atalanta`, and `Hellas Verona vs Atalanta`.

### Root Cause 2: Media Narrative Is Already Priced (and Over-Priced) by the Betting Market
- Matches with glowing positive media headlines (`laya_net_edge > +0.50`, `n = 38`) suffered a **`-15.39%` ROI (`55.3%` win rate)** because public recreational money chases positive media narratives, inflating bookmaker vig on hyped favorites (`Manchester United vs West Ham @ 1.42` L, `Manchester United vs Bournemouth @ 1.74` L, `Manchester United vs Wolves @ 1.38` L).
- Conversely, when a genuine top-tier statistical favorite has a negative media headline (`laya_net_edge <= -0.50`, `n = 14`, e.g., `Cagliari vs Internazionale @ 1.50` W `+0.50u`, `CSKA Sofia vs AS Monaco @ 1.47` W `+0.47u`), bookmaker odds lengthen slightly, creating **higher positive EV (`+24.07%` ROI across the 14 matches)**—provided the team's actual starting lineup passes our **T-60m Starting XI Gate (`attack_share >= 50%`, `def_spine_share >= 50%`)**.

### Root Cause 3: Structured Roster & Lineup Gates Are Strictly Superior
BetScout's three structured player-availability gates operate on exact athlete IDs and roster statuses rather than prose headlines:
1. **Position-Specific T-60m Starting XI Gate (`evaluate_starting_xi_gate`)**: Verifies from official starting lineups (`starter: True`) that `>= 50%` of the team's rolling 6-match attacking goal/assist/SoT output is starting and that the primary goalkeeper + defensive spine are intact (**`+3.66%` ROI on `1,030` kept picks vs `+0.16%` ROI on `228` vetoed picks**).
2. **Sportradar `stats_season_injuries` (`fetch_sportradar_Match_enrichment`)**: Structured player injury list with exact player roles and return dates.
3. **ESPN Structured `summary["injuries"]` Counter (`_evaluate_us_sport_injuries_and_news`)**: Exact count of `Out`, `Injured Reserve`, `Doubtful`, and `Suspension` athletes on each NBA/NHL/NFL/MLB roster.

---

## 5. Conclusion & Action Taken

1. **Preserved Laya on Dedicated Branch**: The complete Laya-enabled codebase (`decision_signal.py`, `distill_laya_sports.py`, `compare_decision_models.py`, `api/deploy/firebase_laya/`) is preserved on branch **`feat/laya-decision-model`**.
2. **Removed Laya from Active Production Stack (`main`)**: Removed the unstructured Laya decision model from the active `main` pipeline, eliminating false-positive headline vetoes, reducing scan latency, and freeing `804 MB` of checkpoint storage while retaining 100% of BetScout's quantitative and structured-lineup alpha.
