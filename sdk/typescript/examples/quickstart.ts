/**
 * Comprehensive CLI Showcase for `@betscout/sdk`
 * Exercises all 9 functional domains of `BetScoutClient` and utility functions.
 *
 * Run with: `npm run example` (from `sdk/typescript/`)
 */

import {
  BOOKMAKER_IDS,
  BetScoutClient,
  CORRECT_SCORE_OUTCOMES,
  MARKET_IDS,
  PLAYER_STATUS_TYPES,
  SERVICE_PROFILES,
  SPORTS_CATALOG,
  TENNIS_SURFACE_IDS,
  getAdaptiveRefetchIntervalMs,
  getCountryFlagUrl,
  getTeamLogoUrl,
  namesMatch,
  normalizeTeamName,
  parseVenueCoordinates,
  renderTeamJerseySvg,
  resolveSportId,
} from '../src/index.js';

async function main() {
  const client = new BetScoutClient({
    defaultChannel: 'eu-retail',
    defaultTimezone: 'Europe:Berlin',
  });

  // --------------------------------------------------------------------------
  // 1. Catalogs, Constants & Discovery (A)
  // --------------------------------------------------------------------------
  console.log('=== 1. Sports Catalog, Category Tree & Tournament Discovery ===');
  const [sports, soccerTree, topSoccerTournaments, tennisCalendar] = await Promise.all([
    client.listAllSports(SERVICE_PROFILES.GLOBAL_UNLIMITED, 0, 'global'),
    client.getCategoryTree(SERVICE_PROFILES.GLOBAL_UNLIMITED, 0, 'soccer', 31), // 31 = Italy
    client.getUniqueTournaments(SERVICE_PROFILES.GLOBAL_UNLIMITED, 'soccer'),
    client.getTennisCalendar(2026),
  ]);
  console.log({
    catalogSportsCount: Object.keys(SPORTS_CATALOG).length,
    liveSportsCount: sports.length,
    sampleConstants: {
      bookmakers: BOOKMAKER_IDS,
      market1X2: MARKET_IDS.MATCH_1X2,
      correctScoreOutcomesCount: Object.keys(CORRECT_SCORE_OUTCOMES).length,
      playerStatusTypes: PLAYER_STATUS_TYPES,
      tennisSurfaceIds: TENNIS_SURFACE_IDS,
    },
    italyCategoriesCount: soccerTree?.realcategories?.length ?? 0,
    featuredSoccerTournamentsLoaded: Boolean(topSoccerTournaments),
    tennisCalendarLoaded: Boolean(tennisCalendar),
    utilityChecks: {
      resolvedSoccerId: resolveSportId('soccer'),
      normalizedClub: normalizeTeamName('FC Bayern München'),
      fuzzyMatch: namesMatch('Djokovic, Novak', 'Novak Djokovic'),
      adaptiveIntervalMs: getAdaptiveRefetchIntervalMs({ event: 'match_timelinedelta', _maxage: 3, data: {} }),
    },
  });

  // --------------------------------------------------------------------------
  // 2. Daily Match Schedules, Multi-Bookmaker Markets & Odds Format Table (B)
  // --------------------------------------------------------------------------
  console.log('\n=== 2. Daily Match Schedules, Multi-Bookmaker Odds & 28-Outcome Correct Score ===');
  const sampleMatchId = 71945344; // Udinese vs AC Milan
  const [matchMarketsPrimary, matchMarketsConsensus, teamMarkets, seasonMarkets, oddsFormats] =
    await Promise.all([
      client.getMatchMarkets(sampleMatchId, 'prematch', 'eu-retail'),
      client.getMatchMarkets(sampleMatchId, 'prematch', 'global'),
      client.getTeamMarkets(2692, 'eu-retail'),
      client.getSeasonMarkets(130971, 'global'),
      client.getOddsFormatTable(),
    ]);
  console.log({
    sampleMatchId,
    primaryMarketCount: matchMarketsPrimary?.markets?.length ?? 0,
    consensusMarketCount: matchMarketsConsensus?.markets?.length ?? 0,
    acMilanActiveMarketMatchesCount: Object.keys(teamMarkets?.matches ?? {}).length,
    serieASeasonMarketMatchesCount: Object.keys(seasonMarkets?.matches ?? {}).length,
    oddsConversionTableRows: oddsFormats?.length ?? 0,
  });

  // --------------------------------------------------------------------------
  // 3. Match Intelligence, Live Delta Stream, Squads, Injuries, Form & H2H (C)
  // --------------------------------------------------------------------------
  console.log('\n=== 3. Match Info, Lineups, Form, H2H, Timeline, Situations & Injury Gate ===');
  const [
    matchInfo,
    matchSquads,
    matchForm,
    matchH2H,
    h2hVersus,
    matchStats,
    matchSituations,
    livePressure,
    matchTimelineDelta,
    matchFullTimeline,
    injuryGate,
  ] = await Promise.all([
    client.getMatchInfo(sampleMatchId),
    client.getMatchSquads(sampleMatchId),
    client.getMatchForm(sampleMatchId),
    client.getMatchHead2Head(sampleMatchId),
    client.getHead2HeadVersus(2692, 2697, 5), // AC Milan vs Inter
    client.getMatchStats(sampleMatchId),
    client.getMatchSituations(sampleMatchId),
    client.fetchLiveMatchSituationsPressure(sampleMatchId),
    client.getMatchTimelineDelta(sampleMatchId),
    client.getMatchFullTimeline(sampleMatchId),
    client.evaluateInjuryGate(140782, 2692, 2697),
  ]);
  console.log({
    matchTitle: `${matchInfo?.match?.teams?.home?.name} vs ${matchInfo?.match?.teams?.away?.name}`,
    finalScore: matchInfo?.match?.result,
    homeFormation: matchSquads?.home?.formation,
    awayFormation: matchSquads?.away?.formation,
    homeRecentFormStreak: matchForm?.teams?.home?.streak,
    awayRecentFormStreak: matchForm?.teams?.away?.streak,
    matchH2HCount: matchH2H?.matches?.length ?? 0,
    milanVsInterDirectH2HCount: h2hVersus?.matches?.length ?? 0,
    hasBoxscoreStats: Boolean(matchStats),
    situationsCount: matchSituations?.situations?.length ?? 0,
    livePressure,
    timelineDeltaStatus: matchTimelineDelta?.match?.status?.name,
    fullTimelineEventsCount: matchFullTimeline?.events?.length ?? 0,
    injuryGateEvaluation: injuryGate,
  });

  // --------------------------------------------------------------------------
  // 4. Tennis Player Career & Surface Matrix (D/E — ID: 14882 Novak Djokovic)
  // --------------------------------------------------------------------------
  console.log('\n=== 4. Tennis Player Profile & Multi-Season Surface Matrix (ID: 14882 — Novak Djokovic) ===');
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

  // --------------------------------------------------------------------------
  // 5. Club Profile, Season Stats, Scoring Splits, Missing Players & Squad (D — ID: 2692 AC Milan)
  // --------------------------------------------------------------------------
  console.log('\n=== 5. Club Profile, Season Stats, Scoring Splits, Missing Players & Squad (ID: 2692 — AC Milan) ===');
  const [milan, milanTransfers, milanTournaments, milanOfficials, milanPosHistory] =
    await Promise.all([
      client.getTeamIntelligenceBundle(2692, {
        seasonId: 130971, // Serie A 25/26
        lastMatchesLimit: 5,
        nextMatchesLimit: 3,
      }),
      client.getTeamTransfers(2692),
      client.getTeamTournaments(2692),
      client.getTeamSeasonOfficials(2692, 130971),
      client.getTeamPositionHistory(130971, 2692),
    ]);
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
    positionHistoryRoundsTracked: milanPosHistory?.roundcount,
    officialsTrackedCount: milanOfficials?.officials?.length ?? 0,
    historicalSeasonsInTournaments: Object.keys(milanTournaments?.seasons ?? {}).length,
    transfersLoaded: Boolean(milanTransfers),
  });

  // --------------------------------------------------------------------------
  // 6. Individual Squad Player Career, Facts, Market Value & Season Log (D — ID: 191210 Mike Maignan)
  // --------------------------------------------------------------------------
  console.log('\n=== 6. Individual Squad Player Career, Facts & Season Log (ID: 191210 — Mike Maignan) ===');
  const [maignanCareer, maignanFacts, maignanMatches, squadFacts] = await Promise.all([
    client.getPlayerCareerStats(191210),
    client.getPlayerFacts(191210),
    client.getPlayerSeasonMatches(191210, 130971),
    client.getTeamPlayerSeasonFacts(2692, 130971),
  ]);
  console.log({
    player: maignanCareer?.player?.fullname,
    marketValueEur: squadFacts?.['191210']?.player?.marketvalue,
    shirtNumber: squadFacts?.['191210']?.player?.shirtnumber,
    clubCount: Object.keys(maignanCareer?.uniqueteams ?? {}).length,
    rolesCount: maignanFacts?.roles?.length ?? 0,
    serieA2526MatchesLogged: maignanMatches?.matches?.length ?? 0,
    serieA2526MinutesPlayed: squadFacts?.['191210']?.stats?.total?.minutes_played,
  });

  // --------------------------------------------------------------------------
  // 7. Visual Assets, Insights, Editorial Commentary, Venues & Leaderboards (F & G)
  // --------------------------------------------------------------------------
  console.log('\n=== 7. Visual Assets, Match Insights, Commentary, San Siro Venue Stats & Leaderboards ===');
  const [sanSiro, seasonVenues, matchInsights, matchCommentary, leagueSummary, topScorers, topAssists, topCards] =
    await Promise.all([
      client.getVenueSeasonStats(647, 130971),
      client.getSeasonVenues(130971),
      client.getMatchInsights(sampleMatchId),
      client.getMatchCommentary(sampleMatchId),
      client.getSeasonLeagueSummary(130971),
      client.getSeasonTopScorers(130971),
      client.getSeasonTopAssists(130971),
      client.getSeasonTopCards(130971),
    ]);
  console.log({
    acMilanLogoBigUrl: getTeamLogoUrl(2692, { size: 'big' }),
    serbiaFlagSvgUrl: getCountryFlagUrl('rs', { format: 'svg', ratio: '4x3' }),
    maignanGkJerseySvgLength: renderTeamJerseySvg(milan.profile?.gkjersey, {
      shirtNumber: 16,
    }).length,
    venue: {
      name: sanSiro?.stadium?.name,
      capacity: sanSiro?.stadium?.capacity,
      coords: parseVenueCoordinates(sanSiro?.stadium?.googlecoords),
      pitchSize: sanSiro?.stadium?.pitchsize,
      homeGoals: sanSiro?.statistics?.venue_home_goals,
      awayGoals: sanSiro?.statistics?.venue_away_goals,
      homeCorners: sanSiro?.statistics?.venue_home_corner_kicks,
      serieAVenuesCount: seasonVenues?.stadiums?.length ?? 0,
    },
    sampleMatchInsights: matchInsights?.funfacts ?? [],
    commentaryPhrasesCount: matchCommentary?.phrases?.length ?? 0,
    leagueSummaryGoalsPerMatch: leagueSummary?.goals?.pr_match,
    leaderboardsLoaded: {
      topScorers: topScorers?.players?.length ?? 0,
      topAssists: topAssists?.players?.length ?? 0,
      topCards: topCards?.players?.length ?? 0,
    },
  });

  // --------------------------------------------------------------------------
  // 8. Enriched League Standings, Live Dynamic Table, Form Table & Table Slice (E)
  // --------------------------------------------------------------------------
  console.log('\n=== 8. Enriched League Standings & Form Table (Serie A 26/27 — Season ID: 140782) ===');
  const [serieATable, dynamicTable, matchSlice] = await Promise.all([
    client.getEnrichedLeagueTable(140782, {
      aroundTeamUid: 2692,
      sliceSize: 5,
    }),
    client.getSeasonDynamicTable(140782),
    client.getMatchTableSlice(sampleMatchId),
  ]);
  console.log({
    season: serieATable.season_name,
    round: `${serieATable.current_round}/${serieATable.max_rounds}`,
    dynamicTableRowsCount: dynamicTable?.season?.tables?.[0]?.tablerows?.length ?? 0,
    matchSliceRowsCount: matchSlice?.tablerows?.length ?? 0,
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

  // --------------------------------------------------------------------------
  // 9. First-to-Score Timing, Half Over/Under Splits, NBA Pace, Brackets & Roll of Honor (H)
  // --------------------------------------------------------------------------
  console.log('\n=== 9. First-to-Score Timing, Half Over/Under Splits, NBA Pace, Brackets & Roll of Honor ===');
  const [seasonGoals, seasonOu, nbaTeamStats, serieAInfo, serieAWinners, derbyVersus, uclMeta, uclBrackets, serieAReferees] =
    await Promise.all([
      client.getSeasonGoalsDistribution(140782),
      client.getSeasonOverUnder(140782),
      client.getSeasonUniqueTeamStats(142074), // NBA 26/27
      client.getUniqueTournamentInfo(23), // Serie A
      client.getTournamentSeasonsWinners(23), // Serie A Roll of Honor
      client.getTeamVersus(2692, 2697, 5), // AC Milan vs Inter
      client.getSeasonMeta(140786), // UEFA Champions League 26/27
      client.getCupBrackets(110232), // UCL Playoff Bracket
      client.getSeasonReferees(140782),
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
    serieADefendingChampion: serieAInfo?.defendingchampion?.mediumname,
    recentSerieAChampions: (serieAWinners?.seasons ?? []).slice(0, 3).map((s) => ({
      year: s.year,
      champion: s.champion?.mediumname ?? s.champion?.name,
      runnerUp: s.runnerup?.mediumname ?? s.runnerup?.name,
    })),
    uclBracketIds: uclMeta?.brackets,
    uclPlayoffBracketName: uclBrackets?.cup?.name,
    serieARefereePoolCount: Object.keys(serieAReferees?.referees ?? {}).length,
    latestDerbyComment: derbyVersus?.matches?.[0]?.comment,
  });
}

main().catch((err) => {
  console.error('Quickstart failed:', err);
  process.exitCode = 1;
});
