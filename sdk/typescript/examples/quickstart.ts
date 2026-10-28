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
    missingPlayers: milan.missing_players.map(
      (p) => `${p.name} (${p.position}, ${p.cause} until ${p.end_date ?? 'TBD'})`,
    ),
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
  const squadFacts = await client.getTeamPlayerSeasonFacts(2692, 130971);
  console.log({
    player: maignanCareer?.player?.fullname,
    marketValueEur: squadFacts?.['191210']?.player?.marketvalue,
    shirtNumber: squadFacts?.['191210']?.player?.shirtnumber,
    clubCount: Object.keys(maignanCareer?.uniqueteams ?? {}).length,
    serieA2526MatchesLogged: maignanMatches?.matches?.length ?? 0,
    serieA2526MinutesPlayed: squadFacts?.['191210']?.stats?.total?.minutes_played,
  });

  console.log('\n=== 5. Visual Assets (Team Crest, Country Flag, Kit Avatar SVG & San Siro Venue Stats) ===');
  const sanSiro = await client.getVenueSeasonStats(647, 130971);
  const matchInsights = await client.getMatchInsights(71945344);
  console.log({
    acMilanLogoBigUrl: client.getTeamLogoUrl(2692, { size: 'big' }),
    serbiaFlagSvgUrl: client.getCountryFlagUrl('rs', { format: 'svg', ratio: '4x3' }),
    maignanGkJerseySvgLength: client.renderTeamJerseySvg(milan.profile?.gkjersey, {
      shirtNumber: 16,
    }).length,
    venue: {
      name: sanSiro?.stadium?.name,
      capacity: sanSiro?.stadium?.capacity,
      coords: sanSiro?.stadium?.googlecoords,
      pitchSize: sanSiro?.stadium?.pitchsize,
      homeGoals: sanSiro?.statistics?.venue_home_goals,
      awayGoals: sanSiro?.statistics?.venue_away_goals,
      homeCorners: sanSiro?.statistics?.venue_home_corner_kicks,
    },
    sampleMatchInsights: matchInsights?.funfacts ?? [],
  });

  console.log('\n=== 6. Enriched League Standings & Form Table (Serie A 26/27 — Season ID: 140782) ===');
  const serieATable = await client.getEnrichedLeagueTable(140782, {
    aroundTeamUid: 2692,
    sliceSize: 5,
  });
  console.log({
    season: serieATable.season_name,
    round: `${serieATable.current_round}/${serieATable.max_rounds}`,
    sliceAroundMilan: serieATable.rows.map((r) => ({
      pos: r.pos,
      change: r.change_total > 0 ? `+${r.change_total}` : String(r.change_total),
      team: r.team_name,
      promotion: r.promotion_short,
      played: r.played.total,
      wdl: `${r.win.total}-${r.draw.total}-${r.loss.total}`,
      goals: `${r.goals_for.total}:${r.goals_against.total} (${r.goal_diff.total >= 0 ? '+' : ''}${r.goal_diff.total})`,
      pts: r.points.total,
      form: r.form_total.join('-'),
    })),
  });

  console.log('\n=== 7. First-to-Score Timing, Half Over/Under Splits, NBA Pace & Roll of Honor ===');
  const [seasonGoals, seasonOu, nbaTeamStats, serieAWinners, derbyVersus] = await Promise.all([
    client.getSeasonGoalsDistribution(140782),
    client.getSeasonOverUnder(140782),
    client.getSeasonUniqueTeamStats(142074), // NBA 26/27
    client.getTournamentSeasonsWinners(23), // Serie A Roll of Honor
    client.getTeamVersus(2692, 2697, 5), // AC Milan vs Inter
  ]);
  const milanGoals = seasonGoals?.teams?.find((t) => t.team?.uid === 2692);
  const milanOu = seasonOu?.stats?.['2692'];
  const raptorsStats = nbaTeamStats?.stats?.uniqueteams?.['3433'];
  console.log({
    milanGoalTiming: {
      scoredSum: milanGoals?.scoredsum,
      firstGoalMatches: milanGoals?.firstgoal,
      lastGoalMatches: milanGoals?.lastgoal,
      avgMinuteFirstGoal: milanGoals?.average_time_first_goal,
      lateGoals76To90: milanGoals?.scored?.['76-90'],
    },
    milanOverUnderSplits: {
      ftWinRate: milanOu?.winrate?.ft?.average,
      p1WinRate: milanOu?.winrate?.p1?.average,
      p2WinRate: milanOu?.winrate?.p2?.average,
      ftOver2_5: milanOu?.total?.ft?.['2.5'],
      p1Over0_5: milanOu?.total?.p1?.['0.5'],
      p2Over0_5: milanOu?.total?.p2?.['0.5'],
    },
    nbaSampleTeamPace: {
      team: raptorsStats?.uniqueteam?.mediumname,
      ptsPerGame: raptorsStats?.points_scored?.average,
      possessionsPerGame: raptorsStats?.possessions_per_game?.average,
      ptsPerPossession: raptorsStats?.points_per_possession?.average,
    },
    recentSerieAChampions: (serieAWinners?.seasons ?? []).slice(0, 3).map((s) => ({
      year: s.year,
      champion: s.champion?.mediumname ?? s.champion?.name,
      runnerUp: s.runnerup?.mediumname ?? s.runnerup?.name,
    })),
    latestDerbyComment: derbyVersus?.matches?.[0]?.comment,
  });
}

main().catch((err) => {
  console.error('Quickstart failed:', err);
  process.exitCode = 1;
});
