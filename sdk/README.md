# 📡 `@betscout/sportradar-gismo-sdk` — TypeScript / Node.js SDK for Sportradar StatsHub & Tipico Gismo APIs

A standalone, zero-runtime-dependency TypeScript/Node.js SDK wrapping **Sportradar's Fishnet (`fn`) Gismo JSON APIs** (`https://stats.fn.sportradar.com` and `https://sh.fn.sportradar.com`), including **Tipico retail bookmaker markets (`_bookmakerId: 176`)** and **Sportradar Unified Odds Feed (`_bookmakerId: 0`)**.

Built directly from the reverse-engineered specification in [`../docs/SPORTRADAR_STATSHUB.md`](../docs/SPORTRADAR_STATSHUB.md).

---

## ✨ Key Features

- **Zero HTML Scraping Required (`stats.fn.sportradar.com`)**: Queries Sportradar's direct tokenless Gismo cluster first, with automatic token extraction (`exp=...~acl=/*~hmac=...`) and fallback to `sh.fn.sportradar.com` if needed.
- **Complete 56-Sport Catalog (`SR_ALL_SPORTS_CATALOG` & `SR_SPORT_IDS`)**: Covers all 56 sports behind the `/sportradar/en/` "All Sports" modal (`config_sports/69/0`) and `/tipico/en/` (`config_sports/67/0`).
- **Dual Bookmaker Feed Merger (`Tipico 176` + `Sportradar UOF 0`)**: Automatically merges Tipico retail markets (1X2, Double Chance, Draw No Bet, Over/Under Totals, 28-outcome Correct Score grid) with Sportradar UOF Asian Handicaps and lower-tier coverage.
- **3-Second Real-Time Live Delta Stream (`match_timelinedelta`)**: Sub-3-second point-by-point and goal-by-goal streaming with `_maxage` adaptive polling and `updated_uts` delta merging.
- **27 Strongly-Typed Gismo Endpoints**: Complete TypeScript interfaces for configuration discovery, daily schedules, pre-match/outright markets, starting XIs (`match_squads`), injuries (`stats_season_injuries`), form (`stats_match_form`), streaks (`stats_team_streaks`), H2H (`stats_match_head2head`, `stats_h2h_versus`), live dangerous attacks (`match_situations`), 15-minute goal intervals (`stats_season_teamscoringconceding`), and ATP/WTA surface records (`tennis_team_surfacestats`).

---

## 🚀 Installation & Scripts

```bash
cd sdk
npm install

# Run Vitest unit & integration test suite
npm run test

# Type-check with strict TypeScript
npm run typecheck

# Build ESM + .d.ts bundle into dist/
npm run build

# Run live quickstart example
npm run example
```

---

## 💻 Usage Examples

### 1. Initialize Client & Discover All 56 Sports
```typescript
import { SportradarGismoClient, SR_SERVICE_IDS } from '@betscout/sportradar-gismo-sdk';

const client = new SportradarGismoClient({
  defaultClientAlias: 'tipico',
  defaultLanguage: 'en',
  defaultTimezone: 'Europe:Berlin',
});

// Query config_sports/69/0 (all 56 sports)
const sports = await client.listAllSports(SR_SERVICE_IDS.SPORTRADAR_UNLIMITED);
console.log(sports); // [{ sportId: 1, name: 'Soccer' }, { sportId: 5, name: 'Tennis' }, ...]
```

### 2. Full Match Intelligence (`lookupMatchIntel`) — Tipico + UOF Odds, 28 Correct Scores, Injuries & Streaks
```typescript
// Automatically resolves team aliases, diacritics & cross-day Europe:Berlin schedules
const intel = await client.lookupMatchIntel('AC Milan', 'Bologna', 'soccer', '2026-10-28');

if (intel.found) {
  console.log('Tournament:', intel.tournament);
  console.log('1X2 Odds:', intel.primary_markets?.odds_home, intel.primary_markets?.odds_draw, intel.primary_markets?.odds_away);
  console.log('28-Score Matrix:', intel.primary_markets?.correct_score_odds);
  console.log('Missing Players:', intel.home_injuries, intel.away_injuries);
  console.log('15m Goal Intervals:', intel.goal_intervals?.home?.intervals);
}
```

### 3. Tennis Surface Win–Loss Analytics (`getTennisTeamSurfaceStats`)
```typescript
const intelTennis = await client.lookupMatchIntel('Taylor Fritz', 'Rinky Hijikata', 'tennis', '2026-10-28');
console.log(intelTennis.tennis_surface_records);
// { home: { season_wl: '48-18', hard_wl: '31-10', clay_wl: '10-5', indoor_wl: '7-3' }, ... }
```

### 4. Real-Time 3-Second Point-by-Point Live Stream (`fetchLiveMatchTimelineDelta`)
```typescript
const liveDelta = await client.fetchLiveMatchTimelineDelta(
  'Giovanni Mpetshi Perricard',
  'Aleksandar Kovacevic',
  'tennis',
);
// -> { state: 'in', status_desc: '1st set', score_str: '0-0 (6-5 · Pt 0-15🎾)', point_score: 'Pt 0-15🎾', ... }
```

---

## 📚 Supported Gismo Endpoints & TypeScript Interfaces

| Category | Client Method | Gismo Endpoint | Return Interface |
| :--- | :--- | :--- | :--- |
| **Discovery** | `listAllSports()` | `config_sports/{serviceId}/{configId}` | `SportCatalogItem[]` |
| **Discovery** | `getConfigTreeMini()` | `config_tree_mini/{serviceId}/{configId}/{sportId}` | `GismoCategoryTreeMini` |
| **Discovery** | `getUniqueTournaments()` | `config_uniquetournaments/{serviceId}/{sportId}` | `Record<string, GismoUniqueTournament>` |
| **Discovery** | `getAllUniqueTournaments()` | `config_uniquetournamentsall/0/{serviceId}/{sportId}` | `Record<string, GismoUniqueTournament>` |
| **Discovery** | `getTennisCalendar()` | `tennis_calendar/{seasonYear}` | `GismoTennisCalendarResponse` |
| **Schedules & Odds** | `getUnifiedSportMatches()` | `unified_sport_matches/{sportId}/{YYYY-MM-DD}/0` | `GismoUnifiedSportMatchesResponse` |
| **Schedules & Odds** | `getUnifiedSportMatchesMarkets()` | `unified_sport_matches_markets/{sportId}/{YYYY-MM-DD}/0` | `GismoUnifiedMarketsResponse` |
| **Schedules & Odds** | `getMatchMarkets()` | `match_markets/{matchId}/prematch` | `GismoMatchMarketsResponse` |
| **Schedules & Odds** | `getSeasonMarkets()` | `season_markets/{seasonId}` | `GismoSeasonMarketsResponse` |
| **Live Stream** | `getMatchTimelineDelta()` | `match_timelinedelta/{matchId}` (`_maxage=3`) | `GismoMatchTimelineDeltaResponse` |
| **Live Stream** | `getLiveEventsBySport()` | `event_get/{sportId}` (`_maxage=10`) | `GismoEventGetResponse` |
| **Match Intel** | `getMatchInfo()` | `match_info_statshub/{matchId}` | `GismoMatchInfoStatshubResponse` |
| **Match Intel** | `getMatchSquads()` | `match_squads/{matchId}` | `GismoMatchSquadsResponse` |
| **Match Intel** | `getSeasonInjuries()` | `stats_season_injuries/{seasonId}` | `GismoSeasonInjuryItem[]` |
| **Match Intel** | `getMatchForm()` | `stats_match_form/{matchId}` | `GismoMatchFormResponse` |
| **Match Intel** | `getTeamStreaks()` | `stats_team_streaks/{teamUid}` | `GismoTeamStreaksResponse` |
| **Match Intel** | `getMatchHead2Head()` | `stats_match_head2head/{matchId}` | `GismoMatchHead2HeadResponse` |
| **Match Intel** | `getHead2HeadVersus()` | `stats_h2h_versus/{minUid}/{maxUid}/{limit}` | `GismoMatchHead2HeadResponse` |
| **Match Intel** | `getTeamLastX()` | `stats_team_lastx/{teamUid}/{limit}` | `GismoTeamLastXResponse` |
| **Match Intel** | `getMatchSituations()` | `match_situations/{matchId}` | `GismoMatchSituationsResponse` |
| **Match Intel** | `getMatchStats()` | `stats_match_stats/{matchId}` | `GismoMatchStatsResponse` |
| **Analytics** | `getTennisTeamSurfaceStats()` | `tennis_team_surfacestats/{playerUid}` | `GismoTennisSurfaceStatsResponse` |
| **Analytics** | `getTennisRanking()` | `tennis_ranking/{type}/{year}/{week}` | `GismoTennisRankingResponse` |
| **Analytics** | `getSeasonTables()` | `stats_season_tables/{seasonId}/{tableType}/{round}` | `GismoSeasonTablesResponse` |
| **Analytics** | `getSeasonOverUnder()` | `stats_season_overunder/{seasonId}` | `GismoSeasonOverUnderResponse` |
| **Analytics** | `getTeamScoringConceding()` | `stats_season_teamscoringconceding/{seasonId}/{teamUid}/{limit}` | `GismoTeamScoringConcedingResponse` |
| **Analytics** | `getRefereeSeasonStats()` | `referee_seasonstats/{refereeId}/{seasonId}` | `GismoRefereeSeasonStatsResponse` |
