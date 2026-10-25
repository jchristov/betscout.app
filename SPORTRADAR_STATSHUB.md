# 📡 Sportradar StatsHub & Tipico Direct API Reference (`SPORTRADAR_STATSHUB.md`)

> **Module:** [`src/betscout/sportradar_statshub.py`](./src/betscout/sportradar_statshub.py)  
> **Primary Bookmaker Feed:** **Tipico (`_bookmakerId: 176`, `clientAlias: "tipico"`)**  
> **Direct Tokenless API Host:** `https://stats.fn.sportradar.com` *(No HTML page parsing required!)*  
> **Secondary Token-Gated Host:** `https://sh.fn.sportradar.com`

---

## 1. Architecture Discovery: Direct JSON API vs. HTML Page Parsing

When you open `https://statshub.sportradar.com/tipico/en/` or `https://statshub.sportradar.com/sportradar/en/`, the Remix / React Router frontend loads `/assets/feeds-1NY2OSz0.js`, which constructs requests to Sportradar's **Fishnet (`fn`) Gismo JSON API** using the URL pattern:

```text
https://{host}/{clientAlias}/{language}/{timezone}/gismo/{endpoint}/{params}
```

### Key Discovery: Tokenless Direct API (`https://stats.fn.sportradar.com`) & Dual Odds Feeds (`Tipico` + `Sportradar Main UOF`)
While `https://sh.fn.sportradar.com` requires a signed `?T=exp=...~acl=/*~hmac=...` query parameter scraped from the HTML page, Sportradar's companion Fishnet cluster **`https://stats.fn.sportradar.com` serves the exact same Gismo JSON endpoints directly without any token or HTML page parsing!**

Even better, querying `stats.fn.sportradar.com` with `clientAlias="tipico"` vs `clientAlias="sportradar"` gives us **two complementary live bookmaker feeds** that [`lookup_statshub_match_intel()`](./src/betscout/sportradar_statshub.py) automatically merges:
1. **`clientAlias="tipico"` (`_bookmakerId: 176`, `source: "sr:crawler_odds:176"`):**
   - Genuine **Tipico retail bookmaker odds** (`616` Soccer matches/day, `11` markets per match including 1X2, Double Chance, Draw No Bet, 3-Way Handicap, Over/Under Totals, and the 28-outcome Correct Score matrix).
2. **`clientAlias="sportradar"` (`_bookmakerId: 0`, `source: "OS_SR:OP_SR:OF_3:OF_UOF"`):**
   - **Sportradar Main Site Unified Odds Feed (UOF)** (`980` Soccer matches/day, **`17` markets per match** — adding **2-Way Asian Handicap (`_marketId: 16`, e.g. `-1.5`)**, **Quarter-Goal Asian Totals (`3.25`)**, **Explicitly Named Correct Score (`_marketId: 45`)**, **2nd Half Handicaps (`_marketId: 87/88`)**, and **Tennis Set-by-Set Winner (`_marketId: 202`)**, plus full odds coverage for lower-tier leagues and Challenger matches not priced by Tipico).

`lookup_statshub_match_intel()` queries **both** `clientAlias="tipico"` and `clientAlias="sportradar"`: it prioritizes **Tipico (`_bookmakerId: 176`)** whenever available and automatically fills any missing markets or unpriced matches from **Sportradar Main UOF (`_bookmakerId: 0`)**!

| Parameter | Values | Description |
| :--- | :--- | :--- |
| **`{host}`** | `stats.fn.sportradar.com` | Direct tokenless JSON API host (Primary — zero HTML scraping) |
| **`{clientAlias}`** | `tipico` \| `sportradar` \| `common` | `tipico` unlocks **Tipico (`_bookmakerId: 176`)** odds; `sportradar` unlocks all 56 sports (`serviceId=69`); `common` is used for client-agnostic stats (`stats_team_streaks`, `tennis_team_surfacestats`) |
| **`{language}`** | `en` \| `de` \| `agnostic` | Localization language (`en` or `de`) |
| **`{timezone}`** | `Europe:Berlin` \| `Etc:UTC` | Timezone for date-bucketed match lists |
| **`serviceId`** | `67` (`statshub` / Tipico) \| `69` (`statshubUnlimited` / Sportradar) \| `41` (`statistics`) | Controls the sport/tournament tree returned by `config_sports/{serviceId}/{configId}` |

---

## 2. Complete Catalog of All 56 Sports Behind the "All Sports" Modal (`/sportradar/en/`)

Clicking **All Sports** on `https://statshub.sportradar.com/sportradar/en/` triggers the Gismo endpoint:
* **Sportradar Unlimited (`56` Sports):** `GET https://stats.fn.sportradar.com/sportradar/en/Etc:UTC/gismo/config_sports/69/0`
* **Tipico StatsHub (`53` Sports):** `GET https://stats.fn.sportradar.com/tipico/en/Etc:UTC/gismo/config_sports/67/0`

All 56 sports and their canonical Sportradar `_id` (`sportId`) are registered in `SR_ALL_SPORTS_CATALOG` and `SR_SPORT_IDS` inside [`sportradar_statshub.py`](./src/betscout/sportradar_statshub.py):

| # | `sportId` (`_id`) | Sport Name | Tipico (`67/0`) | Sportradar (`69/0`) | BetScout Mapped |
| :---: | :---: | :--- | :---: | :---: | :---: |
| 1 | **`1`** | **Soccer (Football)** | ✅ Yes | ✅ Yes | ✅ `soccer` |
| 2 | **`5`** | **Tennis** | ✅ Yes | ✅ Yes | ✅ `tennis` |
| 3 | **`4`** | **Ice Hockey** | ✅ Yes | ✅ Yes | ✅ `hockey` |
| 4 | **`2`** | **Basketball** | ✅ Yes | ✅ Yes | ✅ `basketball` |
| 5 | **`6`** | **Handball** | ✅ Yes | ✅ Yes | ✅ `handball` |
| 6 | **`23`** | **Volleyball** | ✅ Yes | ✅ Yes | ✅ `volleyball` |
| 7 | **`3`** | **Baseball** | ✅ Yes | ✅ Yes | ✅ `baseball` |
| 8 | **`7`** | **Floorball** | ✅ Yes | ✅ Yes | ✅ `floorball` |
| 9 | **`9`** | **Golf** | ✅ Yes | ✅ Yes | ✅ `golf` |
| 10 | **`12`** | **Rugby** | ✅ Yes | ✅ Yes | ✅ `rugby` |
| 11 | **`13`** | **Aussie Rules** | ✅ Yes | ✅ Yes | ✅ `aussie_rules` |
| 12 | **`15`** | **Bandy** | ✅ Yes | ✅ Yes | ✅ `bandy` |
| 13 | **`16`** | **American Football (NFL/NCAA)** | ✅ Yes | ✅ Yes | ✅ `football` |
| 14 | **`17`** | **Cycling** | ✅ Yes | ✅ Yes | ✅ `cycling` |
| 15 | **`18`** | **Specials** | ✅ Yes | ✅ Yes | ✅ `specials` |
| 16 | **`19`** | **Snooker** | ✅ Yes | ✅ Yes | ✅ `snooker` |
| 17 | **`20`** | **Table Tennis** | ✅ Yes | ✅ Yes | ✅ `table_tennis` |
| 18 | **`21`** | **Cricket** | ✅ Yes | ✅ Yes | ✅ `cricket` |
| 19 | **`22`** | **Darts** | ✅ Yes | ✅ Yes | ✅ `darts` |
| 20 | **`24`** | **Field hockey** | ✅ Yes | ✅ Yes | ✅ `field_hockey` |
| 21 | **`26`** | **Waterpolo** | ✅ Yes | ✅ Yes | ✅ `waterpolo` |
| 22 | **`28`** | **Curling** | ✅ Yes | ✅ Yes | ✅ `curling` |
| 23 | **`29`** | **Futsal** | ✅ Yes | ✅ Yes | ✅ `futsal` |
| 24 | **`31`** | **Badminton** | ✅ Yes | ✅ Yes | ✅ `badminton` |
| 25 | **`34`** | **Beach Volley** | ✅ Yes | ✅ Yes | ✅ `beach_volley` |
| 26 | **`36`** | **Athletics** | ✅ Yes | ✅ Yes | ✅ `athletics` |
| 27 | **`37`** | **Squash** | ✅ Yes | ✅ Yes | ✅ `squash` |
| 28 | **`40`** | **Formula 1** | ✅ Yes | ✅ Yes | ✅ `formula_1` |
| 29 | **`43`** | **Alpine Skiing** | ✅ Yes | ✅ Yes | ✅ `alpine_skiing` |
| 30 | **`44`** | **Biathlon** | ✅ Yes | ✅ Yes | ✅ `biathlon` |
| 31 | **`45`** | **Bobsleigh** | ✅ Yes | ✅ Yes | ✅ `bobsleigh` |
| 32 | **`46`** | **Cross-Country** | ✅ Yes | ✅ Yes | ✅ `cross_country` |
| 33 | **`47`** | **Nordic Combined** | ✅ Yes | ✅ Yes | ✅ `nordic_combined` |
| 34 | **`48`** | **Ski Jumping** | ✅ Yes | ✅ Yes | ✅ `ski_jumping` |
| 35 | **`49`** | **Snowboard** | ✅ Yes | ✅ Yes | ✅ `snowboard` |
| 36 | **`50`** | **Speed Skating** | ✅ Yes | ✅ Yes | ✅ `speed_skating` |
| 37 | **`51`** | **Luge** | ✅ Yes | ✅ Yes | ✅ `luge` |
| 38 | **`52`** | **Swimming** | ✅ Yes | ✅ Yes | ✅ `swimming` |
| 39 | **`54`** | **Softball** | ✅ Yes | ✅ Yes | ✅ `softball` |
| 40 | **`60`** | **Beach Soccer** | ✅ Yes | ✅ Yes | ✅ `beach_soccer` |
| 41 | **`61`** | **Pesapallo** | ✅ Yes | ✅ Yes | ✅ `pesapallo` |
| 42 | **`71`** | **Padel** | ✅ Yes | ✅ Yes | ✅ `padel` |
| 43 | **`101`** | **Rally** | ✅ Yes | ✅ Yes | ✅ `rally` |
| 44 | **`117`** | **MMA (UFC)** | ✅ Yes | ✅ Yes | ✅ `mma` |
| 45 | **`129`** | **Indy Racing** | ✅ Yes | ✅ Yes | ✅ `indy_racing` |
| 46 | **`131`** | **Speedway** | ✅ Yes | ✅ Yes | ✅ `speedway` |
| 47 | **`134`** | **ESport King of Glory** | ✅ Yes | ✅ Yes | ✅ `esport_king_of_glory` |
| 48 | **`135`** | **Gaelic Football** | ✅ Yes | ✅ Yes | ✅ `gaelic_football` |
| 49 | **`137`** | **eSoccer** | — | ✅ Yes (`69/0`) | ✅ `esoccer` |
| 50 | **`138`** | **Kabaddi** | ✅ Yes | ✅ Yes | ✅ `kabaddi` |
| 51 | **`153`** | **eBasketball** | — | ✅ Yes (`69/0`) | ✅ `ebasketball` |
| 52 | **`155`** | **Basketball 3x3** | ✅ Yes | ✅ Yes | ✅ `basketball_3x3` |
| 53 | **`188`** | **Touring Car Racing** | ✅ Yes | ✅ Yes | ✅ `touring_car_racing` |
| 54 | **`190`** | **Motorcycle Racing (MotoGP)** | ✅ Yes | ✅ Yes | ✅ `motorcycle_racing` |
| 55 | **`191`** | **Stock Car Racing (NASCAR)** | ✅ Yes | ✅ Yes | ✅ `stock_car_racing` |
| 56 | **`195`** | **eIce Hockey** | — | ✅ Yes (`69/0`) | ✅ `eice_hockey` |

---

## 3. Complete Gismo API Endpoint Reference (`feeds-1NY2OSz0.js`)

All endpoints below are callable directly via:
`https://stats.fn.sportradar.com/{clientAlias}/en/Europe:Berlin/gismo/{endpoint}/{params}`

### A. Configuration & Sport/Tournament Discovery
| Endpoint | Parameters | Description |
| :--- | :--- | :--- |
| **`config_sports`** | `{serviceId}/{configId}` (e.g. `69/0` or `67/0`) | Full list of enabled sports behind the "All Sports" modal |
| **`config_tree_mini`** | `{serviceId}/{configId}/{sportId}/{rcId}` | Category (country) and tournament tree for a sport |
| **`config_uniquetournaments`** | `{serviceId}/{sportId}` | Top/featured unique tournaments for a sport |
| **`config_uniquetournamentsall`** | `0/{serviceId}/{sportId}` | Complete list of all unique tournaments for a sport |
| **`tennis_calendar`** | `{seasonYear}` | Full ATP/WTA/Challenger tournament calendar |

### B. Daily Match Schedules & Tipico Bookmaker Markets (`_bookmakerId: 176`)
| Endpoint | Parameters | Description |
| :--- | :--- | :--- |
| **`unified_sport_matches`** | `{sportId}/{YYYY-MM-DD}/0` | All matches for `sportId` on `YYYY-MM-DD`, grouped by `realcategories` $\rightarrow$ `tournaments` $\rightarrow$ `matches` (includes `_id`, `_seasonid`, `teams.home.uid`, `teams.away.uid`, live scores, and status) |
| **`unified_sport_matches_markets`** | `{sportId}/{YYYY-MM-DD}/0` | Bulk Tipico primary market odds (`1x2`, `1st half - 1x2`, or `Winner`) for every match on `YYYY-MM-DD` |
| **`match_markets`** | `{matchId}/prematch` | **Full Tipico Pre-Match Market Suite** for a single match (`_bookmakerId: 176`):<br>• `_marketId: 1` — **1X2** (`{$competitor1}`, `draw`, `{$competitor2}`)<br>• `_marketId: 10` — **Double Chance** (`1X`, `12`, `X2`)<br>• `_marketId: 11` — **Draw No Bet (DNB)**<br>• `_marketId: 14` — **3-Way European Handicap** (`specifiers.hcp`)<br>• `_marketId: 18` — **Total Goals Over/Under** (`specifiers.total`)<br>• `_marketId: 41` — **28-Outcome Correct Score Matrix** (`sr:outcome:110`=`0:0` through `sr:outcome:166`=`0:6`)<br>• `_marketId: 60` / `65` / `68` — **1st Half 1X2, Handicap & Total**<br>• `_marketId: 186` / `189` — **Tennis Match Winner & Total Games O/U**<br>• `_marketId: 219` / `223` / `225` — **Basketball / NFL Winner, Point Spread & Total Points (incl. OT)**<br>• `_marketId: 406` — **Ice Hockey Winner (incl. OT & Penalties)** |
| **`season_markets`** | `{seasonId}` | Outright / tournament winner futures odds from Tipico |

### C. Match Intelligence, Lineups, Injuries, Form & Head-to-Head
| Endpoint | Parameters | Description |
| :--- | :--- | :--- |
| **`match_timelinedelta`** | `{matchId}` | **Real-Time 3-Second Live Score & Point-by-Point Delta Stream (`_maxage=3`):**<br>• `match.result` — Current sets/goals won (`home`, `away`, `winner`)<br>• `match.periods` — Set/period scores (`p1`..`p5`, `ft`)<br>• `match.gamescore` — Live tennis point score (`0`, `15`, `30`, `40`, `A`) and server (`service: "1" \| "2"`)<br>• `events` — Rolling delta array of the latest point/goal/card events (`score_change_tennis`, `service_taken`, `goal`) |
| **`event_get`** | `{sportId}` | Global 10-second live event feed across all ongoing matches in `sportId` (`_maxage=10`) |
| **`match_info_statshub`** | `{matchId}` | Full match metadata, stadium, attendance, managers, weather, and coverage flags (`_maxage=10`) |
| **`match_squads`** | `{matchId}` | Confirmed starting XI (`startinglineup`), `substitutes`, and `manager` for both teams |
| **`stats_season_injuries`** | `{seasonId}` | **Official League-Wide Missing / Injured / Suspended Players** (`player.name`, `player.position.shortname`, `status.name`, `status.start`, `status.end`, `uniqueteam._id`) |
| **`stats_match_form`** | `{matchId}` | Rolling W/D/L form sequence for both teams entering the match |
| **`stats_team_streaks`** | `{teamUid}` *(use `clientAlias="common"`)* | Active team streaks (`winning`, `losing`, `unbeaten`, `nowinning`, `goalsscored`, `morethan25goals`) + `nextmatches` with **`matchdifficultyrating` (`1–5`)** |
| **`stats_match_head2head`** | `{matchId}` | Head-to-head confrontation history for the match pair |
| **`stats_h2h_versus`** | `{minTeamUid}/{maxTeamUid}/{limit}` | Direct historical H2H meetings between two unique team IDs |
| **`match_situations`** | `{matchId}` *(use `clientAlias="common"`)* | Live pitch attack/danger-zone coordinate timeline (`x`, `y`, `situation: "attack" / "dangerous_attack" / "safe"`) |
| **`stats_match_stats`** | `{matchId}` | Detailed match boxscore statistics (xG, possession, shots on target, corners, cards, service points) |

### D. Tennis & Player / Season Analytics
| Endpoint | Parameters | Description |
| :--- | :--- | :--- |
| **`tennis_team_surfacestats`** | `{playerUid}` *(use `clientAlias="common"`)* | **Multi-Season ATP/WTA Win–Loss Records by Surface:**<br>• `groundid: 0` — All Surfaces total W–L<br>• `groundid: 1` — Clay W–L<br>• `groundid: 2` — Hard Outdoor W–L<br>• `groundid: 3` — Grass W–L<br>• `groundid: 4` — Hard Indoor W–L |
| **`tennis_ranking`** | `{type}/{year}/{week}` | Official ATP / WTA rankings table |
| **`stats_season_tables`** | `{seasonId}/{tableType}/{round}` | League standings table (overall, home, away, form table) |
| **`stats_season_overunder`** | `{seasonId}` | League-wide Over/Under goals distribution by team |
| **`stats_season_teamscoringconceding`** | `{seasonId}/{teamUid}` | 15-minute interval goal scoring & conceding distribution (`0-15'`, `16-30'`, ..., `76-90'`) |
| **`referee_seasonstats`** | `{refereeId}/{seasonId}` | Referee yellow/red cards, fouls, and penalties per match |

---

## 4. Correct Score (`_marketId: 41`) Outcome ID Mapping Table

In Tipico's `match_markets/{matchId}/prematch` payload, Market `41` (`Correct score [{score}]`) returns 28 outcomes keyed by `sr:outcome:{id}` with empty `name` strings. BetScout maps them via `SR_CORRECT_SCORE_OUTCOMES` in [`sportradar_statshub.py`](./src/betscout/sportradar_statshub.py):

| Outcome ID | Score (`H:A`) | Outcome ID | Score (`H:A`) | Outcome ID | Score (`H:A`) | Outcome ID | Score (`H:A`) |
| :--- | :---: | :--- | :---: | :--- | :---: | :--- | :---: |
| `sr:outcome:110` | **`0:0`** | `sr:outcome:126` | **`0:1`** | `sr:outcome:140` | **`1:2`** | `sr:outcome:154` | **`3:3`** |
| `sr:outcome:114` | **`1:0`** | `sr:outcome:128` | **`1:1`** | `sr:outcome:142` | **`2:2`** | `sr:outcome:156` | **`0:4`** |
| `sr:outcome:116` | **`2:0`** | `sr:outcome:130` | **`2:1`** | `sr:outcome:144` | **`3:2`** | `sr:outcome:158` | **`1:4`** |
| `sr:outcome:118` | **`3:0`** | `sr:outcome:132` | **`3:1`** | `sr:outcome:146` | **`4:2`** | `sr:outcome:160` | **`2:4`** |
| `sr:outcome:120` | **`4:0`** | `sr:outcome:134` | **`4:1`** | `sr:outcome:148` | **`0:3`** | `sr:outcome:162` | **`0:5`** |
| `sr:outcome:122` | **`5:0`** | `sr:outcome:136` | **`5:1`** | `sr:outcome:150` | **`1:3`** | `sr:outcome:164` | **`1:5`** |
| `sr:outcome:124` | **`6:0`** | `sr:outcome:138` | **`0:2`** | `sr:outcome:152` | **`2:3`** | `sr:outcome:166` | **`0:6`** |

---

## 5. Python Usage Examples in BetScout

```python
from betscout.sportradar_statshub import (
    fetch_statshub_gismo,
    list_all_sportradar_sports,
    lookup_statshub_match_intel,
)

# 1. List all 56 sports behind the "All Sports" modal on /sportradar/en/ (direct API, zero HTML parsing)
sports = list_all_sportradar_sports(service_id=69, client_alias="sportradar")

# 2. Fetch full Tipico odds (1X2, Double Chance, DNB, 28 Correct Scores), injuries & streaks for a Football match
intel_soccer = lookup_statshub_match_intel("Inter", "Fiorentina", sport="soccer", date_ymd="2026-10-25")

# 3. Fetch Tipico Winner/Totals odds + ATP Surface W-L records (All, Hard, Indoor, Clay) for a Tennis match
intel_tennis = lookup_statshub_match_intel("Daniil Medvedev", "Nikoloz Basilashvili", sport="tennis", date_ymd="2026-10-25")
```
