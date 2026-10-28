# `@betscout/sdk` — TypeScript / Node.js Sports Data, Player/Team Analytics & Multi-Bookmaker Odds SDK

Standalone TypeScript/Node.js SDK (`@betscout/sdk`) providing typed access to **56 sports**, **multi-bookmaker pre-match & live odds** (Primary European Retail + Global Consensus, including the **28-outcome Correct Score matrix**), **3-second real-time timeline deltas**, and **complete Team, Club & Individual Player historical performance and season statistics**.

---

## Key Capabilities

1. **56-Sport Catalog & Tournament Discovery**
   - Full sport registry (`SPORTS_CATALOG`, `SPORT_IDS`, `resolveSportId`), category trees (`getCategoryTree`), tournament catalogs (`getUniqueTournaments`, `getAllUniqueTournaments`), and ATP/WTA calendars (`getTennisCalendar`).
2. **Multi-Bookmaker Pre-Match & Outright Markets**
   - Primary European Retail (`BOOKMAKER_IDS.EU_RETAIL = 176`) + Global Market Consensus (`BOOKMAKER_IDS.CONSENSUS = 0`).
   - Automatic parsing and merging of **1X2**, **2-Way Moneyline (incl. OT/SO)**, **Double Chance (`1X`/`X2`)**, **Draw No Bet**, **2-Way Asian Handicap**, **Over/Under Totals**, and the **28-outcome Correct Score grid (`marketId=41`)**.
3. **Team, Club & Player Historical Performance & Season Analytics**
   - **Club / Team Profiles (`getTeamProfile`, `getTeamIntelligenceBundle`)**: Club founding year, jerseys, stadium, manager, active & historical seasons (`getTeamSeasons`), per-game season statistics (`getTeamSeasonStats` — shots, possession, corners, cards, offsides), home/away/total scoring & conceding splits (`getTeamScoringConcedingSplits`), 15-minute goal interval distributions (`fetchTeamGoalIntervals`), round-by-round league position trajectories (`getTeamPositionHistory`), 40+ man squad rosters (`getTeamSquad`, `getTeamSeasonSquad`), preferred formation & usual starting XI (`getTeamUsualLineup`), transfer history (`getTeamTransfers`), trophy/tournament history (`getTeamTournaments`), and referee assignment stats (`getTeamSeasonOfficials`).
   - **Tennis Player Profiles & Multi-Year Surface Matrices (`getTeamProfile`, `getTennisPlayerSurfaceStats`, `getTennisPlayerIntelligenceBundle`)**: Biographical profile (`turnedpro`, `dateofbirth`, `height`, `weight`, `plays`, `coachname`, `favouritesurface`, `singlesrank`, `highestranking`, `groundstats`, `ranking`, `performance`) plus year-by-year (`2004`–`2026`) singles/doubles/mixed W–L records across all court surfaces (`All`, `Clay`, `Hard Outdoor`, `Indoor`, `Grass`).
   - **Individual Squad Player Career & Season Logs (`getPlayerCareerStats`, `getPlayerFacts`, `getPlayerSeasonMatches`)**: Multi-season career stats across all clubs, career milestones, and match-by-match season appearances.
4. **3-Second Live Timeline Delta Streaming & In-Play Pressure**
   - `getMatchTimelineDelta` (`_maxage: 3`), `fetchLiveMatchTimelineDelta` (live sets/periods, tennis point scores & active server `🎾`), and `fetchLiveMatchSituationsPressure` (live attack & dangerous-attack territorial share).

---

## Installation & Build

```bash
cd sdk/typescript
npm install
npm run typecheck
npm test
npm run build
```

---

## Quickstart Usage

```ts
import { BetScoutClient } from '@betscout/sdk';

const client = new BetScoutClient({
  defaultChannel: 'eu-retail',
  defaultTimezone: 'Europe:Berlin',
});

// 1. Tennis Player Profile & Multi-Season Surface Matrix (e.g. playerId = 14882, Novak Djokovic)
const tennisBundle = await client.getTennisPlayerIntelligenceBundle(14882);
console.log(tennisBundle.profile?.team?.name, tennisBundle.current_surface_summary);

// 2. Club Profile, Season Averages, Scoring Splits, Usual Lineup & Squad (e.g. teamId = 2692, AC Milan)
const clubBundle = await client.getTeamIntelligenceBundle(2692, { seasonId: 130971 });
console.log(clubBundle.usual_lineup?.formation, clubBundle.season_stats);

// 3. Individual Squad Player Career & Season Match Log (e.g. playerId = 191210, Mike Maignan)
const playerCareer = await client.getPlayerCareerStats(191210);
const playerSeasonMatches = await client.getPlayerSeasonMatches(191210, 130971);

// 4. Full Pre-Match Odds, 28-Outcome Correct Score & Injury Gate Lookup
const matchIntel = await client.lookupMatchIntel('AC Milan', 'Inter', 'soccer', '2026-04-20');
console.log(matchIntel.primary_markets?.correct_score_odds);
```
