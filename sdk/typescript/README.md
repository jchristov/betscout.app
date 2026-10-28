# `@betscout/sdk` — TypeScript / Node.js Sports Data, Player/Team Analytics & Multi-Bookmaker Odds SDK

Standalone TypeScript/Node.js SDK (`@betscout/sdk` v1.1.0) providing typed access to **56 sports**, **multi-bookmaker pre-match & live odds** (Primary European Retail + Global Consensus, including the **28-outcome Correct Score matrix**), **3-second real-time timeline deltas**, **enriched league standings & form tables**, **visual assets (crests, flags, player kit SVG avatars)**, **venue analytics**, **automated match insights & editorial commentary**, and **complete Team, Club & Individual Player historical performance and season statistics**.

---

## Installation, Build & Examples

```bash
cd sdk/typescript
npm install
npm run typecheck   # Zero-error TypeScript strict check
npm test            # Run Vitest test suite (15/15 passing)
npm run build       # Compile ESM + .d.ts bundle to dist/
npm run example     # Run comprehensive CLI showcase (examples/quickstart.ts)
npm run showcase    # Launch interactive Web Showcase UI at http://127.0.0.1:8788
```

### Interactive Web Showcase (`examples/showcase.html` + `examples/showcase-server.ts`)
Run `npm run showcase` and open `http://127.0.0.1:8788` to explore an 8-tab interactive dashboard exercising every SDK domain against live data:
1. **Standings & Form Table** (`getEnrichedLeagueTable`, `getSeasonTables`, `getSeasonFormTable`)
2. **Club Intelligence & Missing Players** (`getTeamIntelligenceBundle`, `getTeamMissingPlayers`, `renderTeamJerseySvg`, `getTeamSeasonStats`)
3. **Tennis Player & Surface Matrix** (`getTennisPlayerIntelligenceBundle`, `getTennisPlayerSurfaceStats`)
4. **Squad Player & Kit Avatar SVG** (`getTeamPlayerSeasonFacts`, `getPlayerCareerStats`, `getPlayerSeasonMatches`)
5. **15-Min Goal Timing & Half Over/Under Splits** (`getSeasonGoalsDistribution`, `getSeasonOverUnder`)
6. **Multi-Sport NBA Pace, Derby H2H Versus & Roll of Honor** (`getSeasonUniqueTeamStats`, `getTeamVersus`, `getTournamentSeasonsWinners`)
7. **Venue Analytics, Match Insights, Commentary & 28-Outcome Correct Score** (`getVenueSeasonStats`, `getMatchInsights`, `getMatchCommentary`, `getMatchMarkets`)
8. **56-Sport Catalog & SDK Reference** (`listAllSports`, `SPORTS_CATALOG`)

---

## Complete API Reference (`BetScoutClient`)

### 1. Configuration, Sports Catalog & Tournament Discovery
| Method | Description |
| :--- | :--- |
| `listAllSports(serviceId?, configId?, channel?)` | Lists all 56 sports supported by the platform (`SportCatalogItem[]`), with automatic offline fallback to `SPORTS_CATALOG`. |
| `getCategoryTree(serviceId?, configId?, sportOrId?, rcId?)` | Fetches country/category & tournament hierarchy for a sport (`BetScoutCategoryTreeMini`). |
| `getUniqueTournaments(serviceId?, sportOrId?)` | Fetches featured unique tournaments for a sport. |
| `getAllUniqueTournaments(serviceId?, sportOrId?)` | Fetches all unique tournaments for a sport. |
| `getTennisCalendar(seasonYear?)` | Fetches the full ATP/WTA/Challenger tournament calendar for a season year. |
| `getUniqueTournamentInfo(uniqueTournamentId)` | Fetches tournament metadata, `currentseason`, `defendingchampion`, and `currentleader`. |
| `getTournamentSeasonsWinners(uniqueTournamentId)` | Fetches historical `champion` and `runnerup` Roll of Honor across all past editions. |
| `getSeasonMeta(seasonId)` | Fetches season `statscoverage` flags, `tableids`, `cupids`, and knockout `brackets` IDs. |
| `getCupBrackets(bracketId)` | Fetches playoff / knockout elimination cup bracket trees, `roundsets`, and `stadiums`. |

### 2. Daily Match Schedules & Multi-Bookmaker Markets
| Method | Description |
| :--- | :--- |
| `getDailySportMatches(sportOrId?, dateYmd?, tzOffset?)` | Fetches all scheduled, live, and finished matches for a sport on `dateYmd` (`YYYY-MM-DD`). |
| `getDailyMatchIndex(sportOrId?, dateYmd?)` | Flattens daily matches while filtering out Simulated Reality (`SRL`)/eSoccer and prioritizing main draws. |
| `getDailySportMarkets(sportOrId?, dateYmd?, channel?, tzOffset?)` | Bulk daily pre-match markets (`'eu-retail'` for Primary Retail `_bookmakerId: 176`, `'global'` for Consensus `_bookmakerId: 0`). |
| `getDailyMarketsMap(sportOrId?, dateYmd?)` | Fetches both `'eu-retail'` and `'global'` daily market maps in parallel. |
| `getMatchMarkets(matchId, marketType?, channel?)` | Full pre-match or live market suite for a match (1X2, 2-Way OT/SO, Double Chance, DNB, Asian Handicap, Over/Under, and 28-outcome Correct Score `marketId=41`). |
| `getTeamMarkets(teamId, channel?)` | All active & upcoming bookmaker markets and implied probabilities (`probability`) for a specific team. |
| `getSeasonMarkets(seasonId, channel?)` | Season-wide fixtures and tournament outright markets. |
| `getOddsFormatTable()` | Complete 328-entry Decimal $\leftrightarrow$ UK Fractional & US Moneyline conversion table. |
| `lookupDailyOdds(home, away, sportOrId?, dateYmd?)` | Fast pre-match odds, totals, and Correct Score lookup by team/player names with automatic home/away flip handling. |

### 3. Live 3-Second Timeline Delta Stream, Match Intelligence & In-Play Pressure
| Method | Description |
| :--- | :--- |
| `getMatchTimelineDelta(matchId)` | Real-time 3-second delta feed (`_maxage: 3`) with live scores, set/period breakdowns, tennis game points & server (`service`), and rolling events. |
| `fetchLiveMatchTimelineDelta(home, away, sportOrId?, dateYmd?)` | Resolves `(home, away)` and formats live score strings (`1-0 (6-4, 3-2 · Pt 🎾40-15)`) and final `H`/`A`/`D` outcomes. |
| `getMatchFullTimeline(matchId)` | Complete chronological match event timeline (goals, cards, substitutions, period scores). |
| `getLiveEventsBySport(sportOrId?)` | Global 10-second live event ticker across all in-play matches in a sport (`_maxage: 10`). |
| `getMatchInfo(matchId)` | Full match metadata, stadium, weather, pitch condition, managers, and referee. |
| `getMatchSquads(matchId)` | Confirmed starting XI (`startinglineup`), `substitutes`, `substitutions`, and `manager`. |
| `getMatchStats(matchId)` | Detailed match boxscore statistics (shots, possession, corners, cards, saves). |
| `getMatchSituations(matchId)` | Coordinate-level (`x`, `y`) timeline of `attack`, `dangerous_attack`, and `safe` possession events. |
| `fetchLiveMatchSituationsPressure(matchId)` | Computes live attack counts and dangerous-attack territorial share percentages (`home_danger_share_pct`, `away_danger_share_pct`). |
| `getMatchForm(matchId)` | Pre-match chronological W/D/L form sequences and streaks for both teams. |
| `getMatchHead2Head(matchId)` | Historical H2H meetings for a match ID. |
| `getHead2HeadVersus(teamIdA, teamIdB, limit?)` | Direct H2H confrontations between any two team/player IDs. |
| `getTeamVersus(teamIdA, teamIdB, limit?)` | Rich H2H dossier including goal-minute & scorer `comment` logs, `upcomingmatches`, `currentmanagers`, and `jersey` maps. |
| `lookupMatchIntel(home, away, sportOrId?, dateYmd?)` | One-call pre-match intelligence bundle combining Primary + Consensus markets, 28 Correct Scores, injuries, injury gate, streaks, 15-min goal intervals, or tennis surface records. |

### 4. Team, Club & Individual Player Profiles, Squads, Injuries & Historical Performance
| Method | Description |
| :--- | :--- |
| `getTeamProfile(teamId)` | Unified profile for clubs (`founded`, `stadium`, `manager`, `homejersey`, `awayjersey`, `gkjersey`, `tournaments`) and individual players (`turnedpro`, `dateofbirth`, `height`, `weight`, `plays`, `coachname`, `favouritesurface`, `singlesrank`, `highestranking`, `groundstats`, `ranking`, `performance`). |
| `getTeamLastMatches(teamId, limit?)` | Last `limit` completed matches across all competitions. |
| `getTeamLastMatchesExtended(teamId, limit?)` | Extended historical match log including court surface (`ground`), `roundname`, `bestof`, and `firstgoal`/`lastgoal`. |
| `getTeamNextMatches(teamId, limit?)` | Next `limit` scheduled fixtures. |
| `getTeamStreaks(teamId)` | Active & historical team/player streaks and `nextmatches` difficulty ratings (`matchdifficultyrating`). |
| `getTeamSeasons(teamId)` | All historical and active domestic/continental seasons (`uniqueteam_seasons`). |
| `getTeamSeasonStats(teamId, seasonId)` | Per-game season team averages (`goal_attempts`, `shots_on_goal`, `ball_possession`, `corner_kicks`, `cards_given`, `freekicks`, `offside`, `goals_scored`, `goals_conceded`, `attendance`). |
| `getTeamSeasonMatches(teamId, seasonId)` | All matches played by a team in a specific season. |
| `getTeamScoringConcedingSplits(seasonId, teamId, limit?)` | Home/Away/Total scoring & conceding splits and 15-minute goal buckets. |
| `fetchTeamGoalIntervals(seasonId, teamId, limit?)` | Computes per-match 15-minute scoring/conceding rates (`0-15'`..`76-90'`), 1H scoring %, and BTTS %. |
| `getTeamPositionHistory(seasonId, teamId)` | Round-by-round league table position trajectory across a season. |
| `getTeamSquad(teamId)` | Full active club squad (`players`, `managers`, `roles`, `squadinfo`). |
| `getTeamSeasonSquad(teamId, seasonId)` | Season-specific squad roster, managers, and roles. |
| `getTeamUsualLineup(teamId, seasonId)` | Preferred tactical formation (e.g. `"3-5-2"`) and usual starting XI players. |
| `getTeamTransfers(teamId)` | Historical player arrivals, departures, and loan transfers. |
| `getTeamTournaments(teamId)` | Historical cup/trophy records and season tournament summaries. |
| `getTeamSeasonOfficials(teamId, seasonId)` | Referee assignment and card history for a team in a season. |
| `getSeasonInjuries(seasonId)` | League-wide injured, ill, doubtful, and suspended players (`PLAYER_STATUS_TYPES`). |
| `getTeamMissingPlayers(teamId, options?)` | Resolves the team's active season and returns currently missing/injured/suspended players (`activeOnly: true`). |
| `evaluateInjuryGate(seasonId, backedUid, oppUid)` | Quantitative pre-match squad depletion gate counting missing `FWD`/`GK` players and recommending vetoes. |
| `getTeamPlayerSeasonFacts(teamId, seasonId)` | Full squad season facts including player **`marketvalue` (EUR)**, `shirtnumber`, `membersince`, `minutes_played`, and card splits. |
| `getPlayerCareerStats(playerId)` | Multi-season career statistics across all clubs & competitions. |
| `getPlayerFacts(playerId)` | Player career milestones, roles, clubs, and aggregate stats. |
| `getPlayerSeasonMatches(playerId, seasonId)` | Match-by-match season appearance log for an individual player. |
| `getTeamIntelligenceBundle(teamId, options?)` | Complete Club Historical & Season Intelligence Bundle (`profile`, `seasons`, `season_stats`, `scoring_conceding_splits`, `goal_intervals`, `usual_lineup`, `squad`, `missing_players`, `streaks`, `last_matches`, `next_matches`). |

### 5. Tennis Career & Surface Analytics
| Method | Description |
| :--- | :--- |
| `getTennisPlayerSurfaceStats(playerId)` | Multi-season (`2004`–`2026`) singles/doubles/mixed W–L records across `All` (`0`), `Clay` (`1`), `Hard Outdoor` (`2`), `Indoor` (`3`), and `Grass` (`4`) plus year-end rankings. |
| `getTennisRanking(tourType, year, week)` | Official ATP / WTA rankings table. |
| `getTennisPlayerIntelligenceBundle(playerId, options?)` | Complete Tennis Player Intelligence Bundle (`profile`, `current_surface_summary`, `career_surface_stats`, `streaks`, `last_matches`, `next_matches`). |

### 6. League Ranking Tables, Form Tables, Goal Timing & Multi-Sport Pace
| Method | Description |
| :--- | :--- |
| `getEnrichedLeagueTable(seasonId, options?)` | Merges `getSeasonTables` and `getSeasonFormTable` into `EnrichedStandingsRow[]` with Total/Home/Away W-D-L, `goals_for`, `goals_against`, `goal_diff`, `points`, round rank deltas (`change_total`), UEFA/relegation `promotion` badges, and chronological `form_total` (`['W','D','W',...]`). Supports `aroundTeamUid` + `sliceSize`. |
| `getSeasonTables(seasonId, tableType?, round?)` | Full league standings table (`BetScoutSeasonTablesResponse`). |
| `getSeasonDynamicTable(seasonId)` | Real-time live dynamic league standings table during active matchdays. |
| `getSeasonFormTable(seasonId)` | League form table with recent match-by-match `W`/`D`/`L` arrays and rolling 6-match splits. |
| `getMatchTableSlice(matchId)` | Head-to-head league standings slice for a specific match. |
| `getSeasonGoalsDistribution(seasonId)` | Per-team 15-minute goal buckets (`0-15'`..`76-90'`), `firstgoal` count (scored `1-0`), `lastgoal` count, `average_time_first_goal`, and `penalty_success_count`. |
| `getSeasonOverUnder(seasonId)` | Per-team Total/Home/Away Over/Under (`0.5`..`5.5`) hit matrices across Full Time (`ft`), 1st Half (`p1`), and 2nd Half (`p2`), plus half win rates and clean sheets. |
| `getSeasonUniqueTeamStats(seasonId)` | Multi-sport team pace & efficiency (`possessions_per_game`, `points_per_possession`, `points_scored`, `opponent_points_per_game`, 2PT/3PT/FT splits, rebounds, assists, steals, blocks, turnovers). |

### 7. Visual Assets, Venues, Insights, Commentary & Leaderboards
| Method / Utility | Description |
| :--- | :--- |
| `getTeamLogoUrl(teamId, options?)` | Direct tokenless PNG club/team crest URL (`size`: `'small'` \| `'medium'` \| `'big'`, or `ncaa: true` with `'ap250x188ut'` \| `'ap500x375ut'` \| `'ap1000x750ut'`). |
| `getCountryFlagUrl(countryIso2, options?)` | Direct tokenless SVG (`'4x3'` \| `'1x1'`) or PNG (`'small'` \| `'medium'` \| `'big'`) country/federation flag URL. |
| `renderTeamJerseySvg(jersey, options?)` | Generates a standalone vector SVG player kit avatar from `homejersey` / `awayjersey` / `gkjersey` hex colors and `shirtNumber`. |
| `parseVenueCoordinates(googlecoords)` | Parses stadium `"lat,lng"` strings into `{ lat, lng }`. |
| `getSeasonVenues(seasonId)` | All stadiums for a league season (`capacity`, `constryear`, `address`, `pitchsize`, `googlecoords`). |
| `getVenueSeasonStats(stadiumId, seasonId)` | Venue-specific season goals, corners, cards, 15-min goal intervals, and `venue_top_scorer`. |
| `getMatchInsights(matchId)` | Automated pre-match & live streak/form insights (`funfacts[]` and `facts[]`). |
| `getMatchCommentary(matchId)` & `getMatchCommentaryDelta(matchId)` | Natural-language play-by-play commentary sentences (`phrases[]`) with pitch `(X, Y)` coordinates. |
| `getSeasonLeagueSummary(seasonId)` | Macro league summary (1X2 win %, goals/match, Over/Under `0.5`..`5.5` %, clean sheet %, BTTS %). |
| `getSeasonTopScorers(seasonId)` / `getSeasonTopAssists(seasonId)` / `getSeasonTopCards(seasonId)` | League-wide player leaderboards for goals, assists, and cards. |
| `getSeasonReferees(seasonId)` & `getRefereeSeasonStats(refereeId, seasonId)` | League referee pool and per-referee card/foul/penalty averages. |

### 8. Insights Push Feeds, Betting Splits v3 & Retail vs. Consensus Sharp Divergence
| Method | Description |
| :--- | :--- |
| `buildInsightsPushUrl(options)` | Builds the commercial Insights Push Stream URL (`https://api.sportradar.com/insights/production/stream/{league}/{provider}/subscribe?...`). |
| `streamInsights(options)` | **Dual-Mode Real-Time Insights Generator:** Opens a persistent commercial push stream when `apiKey` is provided, or automatically falls back to **Tokenless Adaptive Delta Streaming** (`match_timelinedelta` `3s`, `match_phrasesdelta` `5s`, `match_funfacts`, and `event_get` `10s`) with event deduplication and heartbeat frames. |
| `buildBettingSplitsUrl(options)` | Builds the commercial Betting Splits v3 REST URL (`/betting-splits/v3/production/soccer/en/competition/{compId}/game/{gameId}` or `/betting-splits/v3/production/{product}/en/game/{gameId}`). |
| `buildBettingSplitsPushUrl(product)` | Builds the commercial Betting Splits Push Stream URL (`/betting-splits/production/stream/{product}/subscribe`). |
| `getBettingSplits(options)` | **Dual-Mode Betting Splits & Sharp Divergence Analyzer:** Queries commercial 150+ bookmaker betting splits when `apiKey` is supplied, or automatically computes **Tokenless Retail (`_bookmakerId: 176`) vs. Global Consensus (`_bookmakerId: 0` + Live `_bookmakerId: 6908`) Betting Splits**, returning `bets_percentage` (de-vigged retail implied %), `stake_percentage` (consensus fair probability %), `sharp_divergence_pct` (`stake_percentage - bets_percentage`), and `direction` (`'steam_toward'` \| `'fade_against'` \| `'neutral'`). |
| `getSeasonCompetitors(seasonId)` | Fetches all participating teams in a season (`stats_season_teams2/{seasonId}`). |
| `getSeasonSchedule(seasonId)` / `getSeasonLastMatches(seasonId, limit?)` / `getSeasonNextMatches(seasonId, limit?)` | Full season schedule (`stats_season_fixtures2`) and rolling season completed/upcoming fixtures. |
| `getCompetitionSeasons(uniqueTournamentId)` | Fetches all historical and active seasons for a competition (`uniquetournament_seasons/{utId}`). |
