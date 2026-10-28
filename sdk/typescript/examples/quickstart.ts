/**
 * Quickstart Example for `@betscout/sdk`
 * Run with: `npm run example` (from `sdk/typescript/`)
 */

import { BetScoutClient, SERVICE_PROFILES } from '../src/index.js';

async function main() {
  const client = new BetScoutClient({
    defaultChannel: 'eu-retail',
    defaultTimezone: 'Europe:Berlin',
  });

  console.log('=== 1. Sports Catalog (56 Sports) ===');
  const sports = await client.listAllSports(SERVICE_PROFILES.GLOBAL_UNLIMITED, 0, 'global');
  console.log(`Loaded ${sports.length} sports. Top 8:`, sports.slice(0, 8));

  console.log('\n=== 2. Tennis Player Profile & Historical Surface Matrix (ID: 14882 — Novak Djokovic) ===');
  const djokovic = await client.getTennisPlayerIntelligenceBundle(14882, {
    lastMatchesLimit: 5,
    nextMatchesLimit: 3,
  });
  console.log({
    name: djokovic.profile?.team?.name,
    nationality: djokovic.profile?.nationality,
    turnedPro: djokovic.profile?.turnedpro,
    plays: djokovic.profile?.plays,
    favouriteSurface: djokovic.profile?.favouritesurface,
    currentRank: djokovic.profile?.singlesrank,
    highestRank: djokovic.profile?.highestranking?.singles,
    atpPoints: djokovic.profile?.ranking?.points,
    currentSeasonSurfaceSummary: djokovic.current_surface_summary,
    recentMatchesSampled: djokovic.last_matches.length,
    latestMatch: djokovic.last_matches[0]
      ? `${djokovic.last_matches[0].teams?.home?.name} vs ${djokovic.last_matches[0].teams?.away?.name} (${djokovic.last_matches[0].result?.home}-${djokovic.last_matches[0].result?.away})`
      : null,
  });

  console.log('\n=== 3. Club Profile, Season Stats, Scoring Splits & Squad (ID: 2692 — AC Milan) ===');
  const milan = await client.getTeamIntelligenceBundle(2692, {
    seasonId: 130971, // Serie A 25/26
    lastMatchesLimit: 5,
    nextMatchesLimit: 3,
  });
  console.log({
    club: milan.profile?.team?.mediumname,
    founded: milan.profile?.team?.founded,
    activeSeasonId: milan.active_season_id,
    usualFormation: milan.usual_lineup?.formation,
    squadSize: milan.squad_count,
    seasonAverages: milan.season_stats,
    goalIntervals10MatchWindow: {
      matchesSampled: milan.goal_intervals.matches_sampled,
      firstHalfScoredAvg: milan.goal_intervals.first_half_scored_avg,
      scoringIn1hPct: milan.goal_intervals.scoring_in_1h_pct,
      bttsPct: milan.goal_intervals.btts_pct,
      late76To90Avg: milan.goal_intervals.late_76_90_total_avg,
    },
    streaks: milan.streaks,
    recentMatchesSampled: milan.last_matches.length,
  });

  console.log('\n=== 4. Individual Squad Player Career & Season Log (ID: 191210 — Mike Maignan) ===');
  const maignanCareer = await client.getPlayerCareerStats(191210);
  const maignanMatches = await client.getPlayerSeasonMatches(191210, 130971);
  console.log({
    player: maignanCareer?.player?.fullname,
    clubCount: Object.keys(maignanCareer?.uniqueteams ?? {}).length,
    serieA2526MatchesLogged: maignanMatches?.matches?.length ?? 0,
  });
}

main().catch((err) => {
  console.error('Quickstart failed:', err);
  process.exitCode = 1;
});
