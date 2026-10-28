# 📡 Sportradar StatsHub & Tipico Direct API Reference (`SPORTRADAR_STATSHUB.md`)

> **Module:** [`src/betscout/sportradar_statshub.py`](../src/betscout/sportradar_statshub.py)  
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

Even better, querying `stats.fn.sportradar.com` with `clientAlias="tipico"` vs `clientAlias="sportradar"` gives us **two complementary live bookmaker feeds** that [`lookup_statshub_match_intel()`](../src/betscout/sportradar_statshub.py) automatically merges:
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

All 56 sports and their canonical Sportradar `_id` (`sportId`) are registered in `SR_ALL_SPORTS_CATALOG` and `SR_SPORT_IDS` inside [`sportradar_statshub.py`](../src/betscout/sportradar_statshub.py):

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
| **`stats_season_teamscoringconceding`** | `{seasonId}/{teamUid}/{limit}` | 15-minute interval goal scoring & conceding distribution (`0-15'`, `16-30'`, ..., `76-90'`) + home/away/total scoring splits |
| **`referee_seasonstats`** | `{refereeId}/{seasonId}` | Referee yellow/red cards, fouls, and penalties per match |

### E. Team, Club & Individual Player Historical Performance & Season Analytics (`/sport/:sportId/team/:teamId`)
These endpoints power the team and competitor pages (such as `/sport/5/team/14882` for Novak Djokovic and `/sport/1/team/2692` for AC Milan):

| Endpoint | Parameters | Description & Returned Data |
| :--- | :--- | :--- |
| **`stats_team_info`** | `{teamUid}` | **Unified Competitor Profile:**<br>• **Clubs (`2692` AC Milan):** `founded` (`"1899"`), `homejersey`, `awayjersey`, `gkjersey`, `stadium`, `manager`, `twitter`, `hashtag`, active `tournaments`.<br>• **Tennis Players (`14882` Novak Djokovic):** `turnedpro` (`"2003"`), `dateofbirth` (`"1987-05-22"`), `nationality`, `height` (`"188"`), `weight` (`"77"`), `plays` (`"Right"`), `coachname`, `favouritesurface` (`"Hard"`), `singlesrank`, `doublesrank`, `highestranking` (`{singles: {date: "07.2011", ranking: 1}}`), `groundstats` (win-loss & win% across All/Clay/Hardcourt/Indoor/Grass), `ranking` (`{ranking, points}`), and `performance` (`serve_receiver_performance_percentage`). |
| **`stats_team_lastx`** | `{teamUid}/{limit}` | Last `limit` completed matches across all competitions with scores, half/set periods, and tournament lookup maps |
| **`stats_team_lastxextended`** | `{teamUid}/{limit}` | Extended historical match log including court surface (`ground`), round (`roundname`), `bestof`, and `firstgoal`/`lastgoal` |
| **`stats_team_nextx`** | `{teamUid}/{limit}` | Next `limit` upcoming scheduled fixtures for a club or player |
| **`uniqueteam_seasons`** | `{teamUid}` | Complete list of historical and active domestic/continental seasons (`Serie A`, `Coppa Italia`, `Champions League`, etc.) |
| **`stats_team_seasonstats`** | `{teamUid}/{seasonId}` | Per-game team season averages (`goal_attempts`, `shots_on_goal`, `shots_off_goal`, `ball_possession`, `corner_kicks`, `shots_blocked`, `cards_given`, `freekicks`, `offside`, `goals_by_foot`, `goals_by_head`, `attendance`, `goals_scored`, `goals_conceded`) |
| **`stats_team_seasonmatches`** | `{teamUid}/{seasonId}` | All matches played by a team in a specific season |
| **`stats_season_teampositionhistory`** | `{seasonId}/{teamUid}` | Round-by-round league table position trajectory across the season |
| **`stats_team_squad`** | `{teamUid}` | Full active club squad (`players` with `height`, `weight`, `foot`, `birthdate`, `nationality`, `position`, `shirtnumber`, plus `managers` and `roles`) |
| **`stats_team_seasonsquad2`** | `{teamUid}/{seasonId}` | Season-specific squad roster, managers, and roles |
| **`stats_team_usuallineup`** | `{teamUid}/{seasonId}` | Preferred tactical formation (e.g. `"3-5-2"`) and usual starting XI players |
| **`stats_team_transfers`** | `{teamUid}` | Historical player arrivals, departures, and loan transfers |
| **`stats_team_tournaments`** | `{teamUid}` | Historical cup/trophy records and season tournament summaries |
| **`stats_uniqueteam_seasonofficials`** | `{teamUid}/{seasonId}` | Referee assignment, card, and foul history for the team in that season |
| **`stats_player_stats`** | `{playerId}` | Individual squad player's multi-season career statistics across all clubs & leagues (e.g. `191210` Mike Maignan) |
| **`stats_player_facts`** | `{playerId}` | Individual player career milestones, roles, clubs, and aggregate stats |
| **`player_seasonmatches`** | `{playerId}/{seasonId}` | Match-by-match appearance and event log for an individual player in a season |
| **`stats_teamplayer_facts`** | `{teamUid}/{seasonId}` | Full squad season facts including player **`marketvalue` (EUR)**, `shirtnumber`, `membersince`, `minutes_played`, `started`, `team_scored`, `team_conceded`, and half-by-half card counts |

### F. Visual Assets (`img.sportradar.com`), Insights, Commentary, Venues & Futures Mapping
Mapping official Sportradar API families (`images-and-editorials`, `insights`, `oddscomparison-futures`) to tokenless Gismo & CDN endpoints:

| Official API Family | Tokenless Gismo / CDN Endpoint | Description & Capabilities |
| :--- | :--- | :--- |
| **Team / Club Logos** | `https://img.sportradar.com/ls/crest/{size}/{teamUid}.png` | Tokenless transparent PNG club crests across all sports (`size`: `small` \| `medium` \| `big`; e.g. `2692.png` AC Milan, `3427.png` Boston Celtics, `3688.png` NHL) when `team.haslogo === true`. |
| **US College / NCAA Logos** | `https://img.sportradar.com/ls/teams/{size}/{teamUid}.png` | Tokenless NCAA team logos (`size`: `ap250x188ut` \| `ap500x375ut` \| `ap1000x750ut`). |
| **Country & Federation Flags** | `https://img.sportradar.com/ls/crest/{ratio}/{a2}.svg`<br>`https://img.sportradar.com/ls/crest/{size}/{a2}.png` | Tokenless vector SVG (`ratio`: `4x3` \| `1x1`) and PNG (`small` \| `medium` \| `big`) flags (`en` $\rightarrow$ `gb-eng`, `s` $\rightarrow$ `gb-sct`, `n` $\rightarrow$ `gb-nir`, `w` $\rightarrow$ `gb-wls`). |
| **Player Avatars / Kits** | `stats_team_info/{teamUid}` + `stats_teamplayer_facts/{teamUid}/{seasonId}` | Photographic editorial headshots/action shots (`api.sportradar.com/images-images3/ap\|getty\|reuters/...`) require commercial wire-agency API keys (`player.haslogo` is `false` in Gismo). Instead, StatsHub renders vector **Player Kit Avatars** from `homejersey`/`awayjersey`/`gkjersey` hex colors + `shirtnumber` + `nationality.a2` flag badge (implemented via `renderTeamJerseySvg` in `@betscout/sdk`). |
| **Venues & Stadiums** | `stats_season_venues/{seasonId}`<br>`stats_season_venuestats/{stadiumId}/{seasonId}` | Full stadium metadata (`name`, `capacity`, `constryear`, `address`, `url`, **`googlecoords: "45.478025,9.124206"`** for map/satellite tiles, **`pitchsize: {x: 105, y: 68}`**) plus venue-specific goals, corners, cards, 15-min goal intervals, and `venue_top_scorer`. |
| **Insights & Commentary** | `match_funfacts/{matchId}`<br>`match_phrases/{matchId}`<br>`match_phrasesdelta/{matchId}`<br>`stats_season_leaguesummary/{seasonId}` | Automated pre-match & in-play streak/form insights (`funfacts[]`, `facts[]`), real-time natural-language commentary sentences (`phrases[]` with pitch `X,Y` coordinates), and season-wide Over/Under, clean-sheet & BTTS rates. |
| **Odds Comparison & Futures** | `uniqueteam_markets/{teamUid}`<br>`season_markets/{seasonId}`<br>`odds_ukformat` | All active/upcoming bookmaker markets and implied probabilities (`probability`) for a specific team or season, plus the 328-entry Decimal $\leftrightarrow$ UK Fractional & US Moneyline conversion table. |

---

## 4. Correct Score (`_marketId: 41`) Outcome ID Mapping Table

In Tipico's `match_markets/{matchId}/prematch` payload, Market `41` (`Correct score [{score}]`) returns 28 outcomes keyed by `sr:outcome:{id}` with empty `name` strings. BetScout maps them via `SR_CORRECT_SCORE_OUTCOMES` in [`sportradar_statshub.py`](../src/betscout/sportradar_statshub.py):

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

## 5. Real-Time Live Streaming Architecture (`_maxage` Adaptive HTTP/2 Delta Stream)

### Why Sportradar StatsHub Uses `_maxage` Delta Streaming Instead of Stateful WebSockets
Inspecting an ongoing live match page (e.g. `https://statshub.sportradar.com/sportradar/en/match/75992888` — *Giovanni Mpetshi Perricard vs. Aleksandar Kovacevic*) and its client bundles (`/assets/query-Csf7PvLX.js`, `/assets/getLatestMatch-D9YBx4ON.js`, `/assets/matchRadarWrapper-BIfNZ5BR.js`) reveals how Sportradar delivers sub-3-second live updates at global scale:

1. **Server-Controlled `_maxage` & `_dob` Metadata (`doc[0]`):**
   Every Gismo JSON response includes `_maxage` (cache TTL in seconds) and `_dob` (UNIX timestamp of birth):
   ```json
   {
     "queryUrl": "match_timelinedelta/75992888",
     "doc": [
       {
         "event": "match_timelinedelta",
         "_dob": 1792936605,
         "_maxage": 3,
         "data": { ... }
       }
     ]
   }
   ```
2. **Adaptive `refetchInterval` in `useFeedQuery` (`query-Csf7PvLX.js`):**
   The frontend's React Query wrapper reads `data.meta.maxage` (in milliseconds) and schedules the next fetch at `Math.max(meta.maxage, 3000)`:
   * **`match_timelinedelta/{matchId}` (`_maxage: 3` $\rightarrow$ `3,000ms` tick):** Returns a lightweight (~2 KB) payload containing the current `match` header plus only the **rolling delta of events (`events[]`) from the last few seconds** (`score_change_tennis`, `service_taken`, `periodscore`, `goal`, `card`).
   * **`match_info_statshub/{matchId}` (`_maxage: 10` $\rightarrow$ `10,000ms` tick):** Full match header & period scores.
   * **`event_get/{sportId}` (`_maxage: 10` $\rightarrow$ `10,000ms` tick):** Global live event ticker across all in-play matches in `sportId` (`1`=Soccer, `5`=Tennis, etc.), used by `matchRadarWrapper-BIfNZ5BR.js` to fire live score/card toast notifications.
   * **`match_timeline/{matchId}` (`_maxage: 20` $\rightarrow$ `20,000ms` tick):** Full point-by-point / play-by-play historical event log for the match.
3. **Client Delta Merger (`getLatestMatch-D9YBx4ON.js`):**
   ```javascript
   function getLatestMatch({ match, timelineDelta }) {
     if (!(timelineDelta != null && timelineDelta.data.match)) return match;
     const s = timelineDelta.data.match;
     return typeof s.updated_uts == "number" &&
       (typeof match.updated_uts != "number" || s.updated_uts > match.updated_uts)
       ? s : match;
   }
   ```

### Live `match_timelinedelta/{matchId}` Payload Structure (Tennis Example: Match `75992888`)
Calling `GET https://stats.fn.sportradar.com/sportradar/en/Europe:Berlin/gismo/match_timelinedelta/75992888` during an active match returns:
* **`match.status`:** `{"_doc": "status", "_id": 8, "name": "1st set", "shortName": "S1"}` (`_id: 8/9/10` = 1st/2nd/3rd set; `_id: 6/7` = 1st/2nd half in Soccer; `_id: 100` = Ended)
* **`match.result`:** `{"home": 0, "away": 0, "winner": null}` (sets won in Tennis, or goals in Soccer)
* **`match.periods`:** `{"p1": {"home": 6, "away": 5}}` (games won in each set `p1`..`p5`)
* **`match.gamescore`:** `{"home": 0, "away": 15, "service": "2"}` (live current game points `0`, `15`, `30`, `40`, `A` and active server `"1"` = home, `"2"` = away)
* **`events` (Delta Array):**
  ```json
  [
    {
      "_doc": "event",
      "_doctype": "scorechangetennis",
      "type": "score_change_tennis",
      "matchid": 75992888,
      "uts": 1792936643,
      "team": "away",
      "set_score": {"home": "0", "away": "0"},
      "game_score": {"home": "6", "away": "5"},
      "game_points": {"home": "0", "away": "15"},
      "service": "2"
    }
  ]
  ```

### How BetScout Uses `match_timelinedelta`
* **`fetch_live_match_timelinedelta(home, away, sport, date_ymd)`** in [`src/betscout/sportradar_statshub.py`](../src/betscout/sportradar_statshub.py) resolves the active match and queries `match_timelinedelta/{matchId}` (`ttl_sec=3.0`), formatting the live score with set scores, current point score, and serving indicator (e.g. `0-0 (6-5 · Pt 0-15🎾)`).
* **`_refresh_inplay_timelinedelta(db_path)`** in [`src/betscout/webapp.py`](../src/betscout/webapp.py) runs on every 6-second SSE tick of `GET /api/stream`, pushing real-time point-by-point and goal-by-goal updates to all connected browsers in the **🔴 Live In-Play Paper-Bets** table.

---

## 6. Python Usage Examples in BetScout

```python
from betscout.sportradar_statshub import (
    fetch_live_match_timelinedelta,
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

# 4. Stream 3-second real-time point-by-point score & active server via match_timelinedelta
live_delta = fetch_live_match_timelinedelta("Giovanni Mpetshi Perricard", "Aleksandar Kovacevic", sport="tennis")
# -> {'state': 'in', 'status_desc': '1st set', 'score_str': '0-0 (6-5 · Pt 0-15🎾)', ...}
```
