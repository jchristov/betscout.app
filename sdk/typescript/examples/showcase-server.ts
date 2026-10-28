/**
 * Interactive Web Showcase Server for `@betscout/sdk`.
 * Serves `examples/showcase.html`, `/betscout-logo.svg`, and exposes live dynamic JSON endpoints
 * backed by `BetScoutClient` for interactive cross-tab drill-down across all 56 sports, leagues, seasons,
 * teams, players, matches, venues, and multi-bookmaker odds.
 *
 * Run with: `npm run showcase` (from `sdk/typescript/`)
 */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  BOOKMAKER_IDS,
  BetScoutClient,
  CORRECT_SCORE_OUTCOMES,
  MARKET_IDS,
  PLAYER_STATUS_TYPES,
  SERVICE_PROFILES,
  SPORTS_CATALOG,
  TENNIS_SURFACE_IDS,
  getCountryFlagUrl,
  getTeamLogoUrl,
  mergePrimaryAndConsensusMarkets,
  parsePrematchMarkets,
  parseVenueCoordinates,
  renderMonogramCrestDataUri,
  renderTeamJerseySvg,
  resolveCompetitionCrestUrl,
  resolvePlayerHeadshotUrl,
} from '../src/index.js';
import type { BetScoutUniqueTournament } from '../src/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT ?? 8788);

const client = new BetScoutClient({
  defaultChannel: 'eu-retail',
  defaultTimezone: 'Europe:Berlin',
});

let cachedShowcasePayload: unknown = null;
let cachedAtMs = 0;

function normalizeTournamentArray(
  raw: Record<string, BetScoutUniqueTournament> | BetScoutUniqueTournament[] | null | undefined,
): Array<BetScoutUniqueTournament & { a2?: string; flagSvgUrl?: string | null }> {
  const list: Array<BetScoutUniqueTournament & { a2?: string }> = Array.isArray(raw)
    ? raw
    : raw && typeof raw === 'object'
      ? Object.values(raw)
      : [];
  return list
    .filter((t) => t && typeof t._id === 'number' && t.name)
    .map((t) => ({
      ...t,
      flagSvgUrl: t.a2 ? getCountryFlagUrl(String(t.a2), { format: 'svg', ratio: '4x3' }) : null,
    }));
}

async function buildSportLeaguesPayload(sportId: number) {
  const [featuredRaw, allRaw, treeMini] = await Promise.all([
    client.getUniqueTournaments(SERVICE_PROFILES.GLOBAL_UNLIMITED, sportId),
    client.getAllUniqueTournaments(SERVICE_PROFILES.GLOBAL_UNLIMITED, sportId),
    client.getCategoryTree(SERVICE_PROFILES.GLOBAL_UNLIMITED, 0, sportId),
  ]);

  const categoryById = new Map<number, { name: string; a2?: string }>();
  for (const rc of treeMini?.realcategories ?? []) {
    if (rc && typeof rc._id === 'number') {
      categoryById.set(rc._id, {
        name: rc.name,
        a2: rc.cc?.a2,
      });
    }
  }

  const featured = await Promise.all(
    normalizeTournamentArray(featuredRaw).map(async (t) => {
      const cat = t._rcid ? categoryById.get(t._rcid) : undefined;
      const iso = t.a2 ?? cat?.a2 ?? 'int';
      const crestUrl = await resolveCompetitionCrestUrl(t.name);
      return {
        ...t,
        categoryName: cat?.name ?? null,
        a2: iso,
        flagSvgUrl: getCountryFlagUrl(String(iso), { format: 'svg', ratio: '4x3' }),
        crestUrl,
      };
    }),
  );

  const allLeagues = normalizeTournamentArray(allRaw).map((t) => {
    const cat = t._rcid ? categoryById.get(t._rcid) : undefined;
    const iso = t.a2 ?? cat?.a2 ?? 'int';
    return {
      ...t,
      categoryName: cat?.name ?? null,
      a2: iso,
      flagSvgUrl: getCountryFlagUrl(String(iso), { format: 'svg', ratio: '4x3' }),
      crestUrl: renderMonogramCrestDataUri(t.name, 32),
    };
  });

  return {
    ok: true,
    sportId,
    sportName: SPORTS_CATALOG[sportId] ?? `Sport #${sportId}`,
    featuredCount: featured.length,
    totalLeaguesCount: allLeagues.length,
    featured,
    leagues: allLeagues,
  };
}

async function buildSeasonIntelPayload(
  seasonId: number | string,
  uniqueTournamentId?: number | string,
) {
  const [
    table,
    seasonGoals,
    seasonOu,
    leagueSummary,
    uniqueTeamStats,
    seasonVenues,
    topScorers,
    topAssists,
    topCards,
    seasonMeta,
    utInfo,
    utWinners,
  ] = await Promise.all([
    client.getEnrichedLeagueTable(seasonId),
    client.getSeasonGoalsDistribution(seasonId),
    client.getSeasonOverUnder(seasonId),
    client.getSeasonLeagueSummary(seasonId),
    client.getSeasonUniqueTeamStats(seasonId),
    client.getSeasonVenues(seasonId),
    client.getSeasonTopScorers(seasonId),
    client.getSeasonTopAssists(seasonId),
    client.getSeasonTopCards(seasonId),
    client.getSeasonMeta(seasonId),
    uniqueTournamentId ? client.getUniqueTournamentInfo(uniqueTournamentId) : Promise.resolve(null),
    uniqueTournamentId
      ? client.getTournamentSeasonsWinners(uniqueTournamentId)
      : Promise.resolve(null),
  ]);

  const rowsWithLogos = (table.rows ?? []).map((r) => ({
    ...r,
    logoUrl: getTeamLogoUrl(r.team_uid, { size: 'small' }),
  }));

  const multiSportTeams = Object.values(uniqueTeamStats?.stats?.uniqueteams ?? {})
    .slice(0, 12)
    .map((t) => ({
      id: t.uniqueteam?._id,
      name: t.uniqueteam?.mediumname ?? t.uniqueteam?.name,
      abbr: t.uniqueteam?.abbr,
      logoUrl: t.uniqueteam?._id ? getTeamLogoUrl(t.uniqueteam._id, { size: 'small' }) : null,
      ptsPerGame: t.points_scored?.average ?? null,
      oppPtsPerGame: t.opponent_points_per_game?.average ?? null,
      possessionsPerGame: t.possessions_per_game?.average ?? null,
      ptsPerPossession: t.points_per_possession?.average ?? null,
      reboundsPerGame: t.rebounds?.average ?? null,
      assistsPerGame: t.assists?.average ?? null,
    }));

  return {
    ok: true,
    seasonId,
    uniqueTournamentId: uniqueTournamentId ?? seasonMeta?.uniquetournament?._id ?? null,
    standingsAndForm: {
      ...table,
      rows: rowsWithLogos,
    },
    seasonGoals,
    seasonOverUnder: seasonOu,
    leagueSummary,
    multiSportTeams,
    venues: seasonVenues?.stadiums ?? [],
    topScorers: (topScorers?.players ?? []).slice(0, 10),
    topAssists: (topAssists?.players ?? []).slice(0, 10),
    topCards: (topCards?.players ?? []).slice(0, 10),
    defendingChampion: utInfo?.defendingchampion ?? null,
    currentLeader: utInfo?.currentleader ?? null,
    rollOfHonor: (utWinners?.seasons ?? []).slice(0, 12).map((s) => ({
      year: s.year,
      name: s.name,
      champion: s.champion?.mediumname ?? s.champion?.name ?? null,
      championId: s.champion?._id ?? null,
      championLogo: s.champion?._id ? getTeamLogoUrl(s.champion._id, { size: 'small' }) : null,
      runnerUp: s.runnerup?.mediumname ?? s.runnerup?.name ?? null,
      runnerUpId: s.runnerup?._id ?? null,
      runnerUpLogo: s.runnerup?._id ? getTeamLogoUrl(s.runnerup._id, { size: 'small' }) : null,
    })),
    leagueCrestUrl: await resolveCompetitionCrestUrl(
      utInfo?.uniquetournament?.name ?? table.season_name,
    ),
  };
}

async function buildTeamIntelPayload(teamId: number | string, seasonId?: number | string) {
  const profile = await client.getTeamProfile(teamId);
  const isTennisOrIndividual =
    profile?.team?._sid === 5 || Boolean(profile?.turnedpro || profile?.groundstats?.length);

  if (isTennisOrIndividual) {
    const tnBundle = await client.getTennisPlayerIntelligenceBundle(teamId, {
      lastMatchesLimit: 10,
      nextMatchesLimit: 5,
    });
    const ccIso =
      (typeof tnBundle.profile?.cc === 'string'
        ? tnBundle.profile.cc
        : tnBundle.profile?.countrycode?.a2) ?? 'rs';
    const headshotUrl = await resolvePlayerHeadshotUrl(tnBundle.profile?.team?.name);
    return {
      ok: true,
      kind: 'tennis_player' as const,
      tennisIntelligence: {
        ...tnBundle,
        headshotUrl,
        countryFlagSvgUrl: getCountryFlagUrl(ccIso, { format: 'svg', ratio: '4x3' }),
      },
    };
  }

  const clubBundle = await client.getTeamIntelligenceBundle(teamId, {
    seasonId,
    lastMatchesLimit: 8,
    nextMatchesLimit: 5,
  });

  const activeSid = clubBundle.active_season_id ?? seasonId ?? 130971;
  const [seasonGoals, seasonOu, squadFacts] = await Promise.all([
    client.getSeasonGoalsDistribution(activeSid),
    client.getSeasonOverUnder(activeSid),
    client.getTeamPlayerSeasonFacts(teamId, activeSid),
  ]);

  const teamGoals =
    seasonGoals?.teams?.find((t) => Number(t.team?.uid ?? t.team?._id) === Number(teamId)) ?? null;
  const teamOu = seasonOu?.stats?.[String(teamId)] ?? null;
  const ccIso =
    (typeof clubBundle.profile?.team?.cc === 'object' && clubBundle.profile?.team?.cc?.a2
      ? clubBundle.profile.team.cc.a2
      : clubBundle.profile?.countrycode?.a2) ?? 'it';

  const enrichedSquad = (clubBundle.squad ?? []).map((p) => {
    const f = squadFacts?.[String(p._id)];
    const natIso = p.nationality?.a2 ?? 'int';
    return {
      ...p,
      marketvalue: f?.player?.marketvalue ?? p.marketvalue ?? null,
      shirtnumber: f?.player?.shirtnumber ?? p.shirtnumber ?? null,
      seasonTotals: f?.stats?.total ?? null,
      flagSvgUrl: getCountryFlagUrl(natIso, { format: 'svg', ratio: '4x3' }),
      avatarUrl: renderMonogramCrestDataUri(p.fullname ?? p.name, 32),
    };
  });

  const enrichedMissing = await Promise.all(
    (clubBundle.missing_players ?? []).map(async (mp) => ({
      ...mp,
      headshotUrl: await resolvePlayerHeadshotUrl(mp.name),
    })),
  );

  return {
    ok: true,
    kind: 'club' as const,
    clubIntelligence: {
      ...clubBundle,
      squad: enrichedSquad,
      missing_players: enrichedMissing,
      logoBigUrl: getTeamLogoUrl(teamId, { size: 'big' }),
      countryFlagSvgUrl: getCountryFlagUrl(ccIso, { format: 'svg', ratio: '4x3' }),
      homeJerseySvg: renderTeamJerseySvg(clubBundle.profile?.homejersey, {
        shirtNumber: 10,
        sizePx: 88,
      }),
      awayJerseySvg: renderTeamJerseySvg(clubBundle.profile?.awayjersey, {
        shirtNumber: 11,
        sizePx: 88,
      }),
      gkJerseySvg: renderTeamJerseySvg(clubBundle.profile?.gkjersey, {
        shirtNumber: 1,
        sizePx: 88,
      }),
    },
    goalTimingAndOverUnder: {
      teamGoals,
      leagueTotals: seasonGoals?.totals ?? null,
      teamOverUnder: teamOu,
    },
  };
}

async function buildPlayerIntelPayload(
  playerId: number | string,
  teamId = 2692,
  seasonId = 130971,
) {
  const [career, facts, seasonMatches, squadFacts, teamProfile] = await Promise.all([
    client.getPlayerCareerStats(playerId),
    client.getPlayerFacts(playerId),
    client.getPlayerSeasonMatches(playerId, seasonId),
    client.getTeamPlayerSeasonFacts(teamId, seasonId),
    client.getTeamProfile(teamId),
  ]);

  const factEntry = squadFacts?.[String(playerId)];
  const playerObj = career?.player ?? facts?.player ?? factEntry?.player ?? null;
  const posShort = playerObj?.position?.shortname ?? playerObj?.primaryposition?.shortname ?? '';
  const jerseyColors =
    posShort === 'GK' || posShort === 'G'
      ? (teamProfile?.gkjersey ?? teamProfile?.homejersey)
      : teamProfile?.homejersey;
  const shirtNum = factEntry?.player?.shirtnumber ?? playerObj?.shirtnumber ?? 10;
  const ccIso = playerObj?.nationality?.a2 ?? 'fr';
  const headshotUrl = await resolvePlayerHeadshotUrl(playerObj?.fullname ?? playerObj?.name);

  return {
    ok: true,
    playerSpotlight: {
      player: playerObj,
      teamId,
      seasonId,
      headshotUrl,
      marketValueEur: factEntry?.player?.marketvalue ?? playerObj?.marketvalue ?? null,
      shirtNumber: shirtNum,
      memberSince: factEntry?.player?.membersince?.date ?? null,
      seasonTotals: factEntry?.stats?.total ?? seasonMatches?.total ?? null,
      clubs: Object.values(career?.uniqueteams ?? facts?.teams ?? {}).map((c) => ({
        ...c,
        logoUrl: c._id ? getTeamLogoUrl(c._id, { size: 'small' }) : null,
      })),
      seasonMatchesCount: seasonMatches?.matches?.length ?? 0,
      recentMatches: (seasonMatches?.matches ?? []).slice(0, 10),
      flagSvgUrl: getCountryFlagUrl(ccIso, { format: 'svg', ratio: '4x3' }),
      kitAvatarSvg: renderTeamJerseySvg(jerseyColors, { shirtNumber: shirtNum, sizePx: 88 }),
    },
  };
}

async function buildMatchIntelPayload(matchId: number | string) {
  const [
    matchInfo,
    matchMarketsPrimary,
    matchMarketsConsensus,
    matchInsights,
    matchCommentary,
    matchSquads,
    matchStats,
    livePressure,
    timelineDelta,
  ] = await Promise.all([
    client.getMatchInfo(matchId),
    client.getMatchMarkets(matchId, 'prematch', 'eu-retail'),
    client.getMatchMarkets(matchId, 'prematch', 'global'),
    client.getMatchInsights(matchId),
    client.getMatchCommentary(matchId),
    client.getMatchSquads(matchId),
    client.getMatchStats(matchId),
    client.fetchLiveMatchSituationsPressure(matchId),
    client.getMatchTimelineDelta(matchId),
  ]);

  const parsedPrimary = parsePrematchMarkets(matchMarketsPrimary?.markets, false);
  const parsedConsensus = parsePrematchMarkets(matchMarketsConsensus?.markets, false);
  const mergedMarkets = mergePrimaryAndConsensusMarkets(parsedPrimary, parsedConsensus);

  const stadiumId = matchInfo?.match?.stadium?._id;
  const seasonId = matchInfo?.match?._seasonid ?? 130971;
  const venueStats = stadiumId ? await client.getVenueSeasonStats(stadiumId, seasonId) : null;

  return {
    ok: true,
    match: {
      matchId,
      seasonId,
      home: matchInfo?.match?.teams?.home?.mediumname ?? matchInfo?.match?.teams?.home?.name,
      homeUid: matchInfo?.match?.teams?.home?.uid ?? matchInfo?.match?.teams?.home?._id,
      away: matchInfo?.match?.teams?.away?.mediumname ?? matchInfo?.match?.teams?.away?.name,
      awayUid: matchInfo?.match?.teams?.away?.uid ?? matchInfo?.match?.teams?.away?._id,
      result: matchInfo?.match?.result ?? timelineDelta?.match?.result ?? null,
      status: timelineDelta?.match?.status?.name ?? matchInfo?.match?.status?.name ?? null,
      homeFormation: matchSquads?.home?.formation ?? null,
      awayFormation: matchSquads?.away?.formation ?? null,
      funFacts: matchInsights?.funfacts ?? [],
      commentarySample: (matchCommentary?.phrases ?? []).slice(0, 12),
      primaryMarkets: parsedPrimary,
      consensusMarkets: parsedConsensus,
      mergedMarkets,
      livePressure,
      hasBoxscoreStats: Boolean(matchStats),
    },
    venue: venueStats
      ? {
          stadium: venueStats.stadium,
          coordinates: parseVenueCoordinates(venueStats.stadium?.googlecoords),
          statistics: venueStats.statistics,
        }
      : null,
  };
}

async function buildInitialShowcasePayload() {
  const now = Date.now();
  if (cachedShowcasePayload && now - cachedAtMs < 120_000) {
    return cachedShowcasePayload;
  }

  const sampleMatchId = 71945344; // Udinese vs AC Milan
  const [
    sports,
    soccerLeagues,
    milanPayload,
    djokovicPayload,
    maignanPayload,
    serieASeasonPayload,
    nbaTeamStats,
    derbyVersus,
    sanSiroStats,
    matchPayload,
    uclBrackets,
    oddsFormats,
  ] = await Promise.all([
    client.listAllSports(SERVICE_PROFILES.GLOBAL_UNLIMITED, 0, 'global'),
    buildSportLeaguesPayload(1),
    buildTeamIntelPayload(2692, 130971),
    buildTeamIntelPayload(14882),
    buildPlayerIntelPayload(191210, 2692, 130971),
    buildSeasonIntelPayload(140782, 23),
    client.getSeasonUniqueTeamStats(142074), // NBA 26/27
    client.getTeamVersus(2692, 2697, 6), // AC Milan vs Inter
    client.getVenueSeasonStats(647, 130971), // Stadio Giuseppe Meazza (San Siro)
    buildMatchIntelPayload(sampleMatchId),
    client.getCupBrackets(110232),
    client.getOddsFormatTable(),
  ]);

  const nbaTeams = Object.values(nbaTeamStats?.stats?.uniqueteams ?? {})
    .slice(0, 10)
    .map((t) => ({
      id: t.uniqueteam?._id,
      name: t.uniqueteam?.mediumname ?? t.uniqueteam?.name,
      abbr: t.uniqueteam?.abbr,
      logoUrl: t.uniqueteam?._id ? getTeamLogoUrl(t.uniqueteam._id, { size: 'medium' }) : null,
      ptsPerGame: t.points_scored?.average ?? null,
      oppPtsPerGame: t.opponent_points_per_game?.average ?? null,
      possessionsPerGame: t.possessions_per_game?.average ?? null,
      ptsPerPossession: t.points_per_possession?.average ?? null,
      reboundsPerGame: t.rebounds?.average ?? null,
      assistsPerGame: t.assists?.average ?? null,
    }));

  const payload = {
    generatedAtUtc: new Date().toISOString(),
    sdkVersion: '1.1.0',
    catalog: {
      sportsCount: sports.length,
      sports,
      initialSportLeagues: soccerLeagues,
      constants: {
        BOOKMAKER_IDS,
        SERVICE_PROFILES,
        MARKET_IDS,
        PLAYER_STATUS_TYPES,
        TENNIS_SURFACE_IDS,
        correctScoreOutcomesCount: Object.keys(CORRECT_SCORE_OUTCOMES).length,
        staticCatalogCount: Object.keys(SPORTS_CATALOG).length,
      },
    },
    clubIntelligence: milanPayload.kind === 'club' ? milanPayload.clubIntelligence : null,
    tennisIntelligence:
      djokovicPayload.kind === 'tennis_player' ? djokovicPayload.tennisIntelligence : null,
    playerSpotlight: maignanPayload.playerSpotlight,
    standingsAndForm: serieASeasonPayload.standingsAndForm,
    goalTimingAndOverUnder: {
      milanGoals:
        serieASeasonPayload.seasonGoals?.teams?.find((t) => t.team?.uid === 2692) ?? null,
      leagueTotals: serieASeasonPayload.seasonGoals?.totals ?? null,
      milanOverUnder: serieASeasonPayload.seasonOverUnder?.stats?.['2692'] ?? null,
      leagueSummary: serieASeasonPayload.leagueSummary,
    },
    multiSportAndTournaments: {
      nbaTeams,
      serieARollOfHonor: serieASeasonPayload.rollOfHonor,
      derbyVersus: {
        matches: (derbyVersus?.matches ?? []).slice(0, 6),
        managers: derbyVersus?.currentmanagers ?? {},
      },
      uclBracket: {
        cupName: uclBrackets?.cup?.name ?? null,
        bracketType: uclBrackets?.bracket?.type ?? null,
        seasonName: uclBrackets?.season?.name ?? null,
      },
    },
    venueAndInsights: {
      venue: {
        stadium: sanSiroStats?.stadium ?? null,
        coordinates: parseVenueCoordinates(sanSiroStats?.stadium?.googlecoords),
        statistics: sanSiroStats?.statistics ?? null,
      },
      match: {
        ...matchPayload.match,
        oddsFormatSample: (oddsFormats ?? []).slice(0, 6),
      },
    },
  };

  cachedShowcasePayload = payload;
  cachedAtMs = now;
  return payload;
}

function sendJson(res: http.ServerResponse, status: number, data: unknown) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  });
  res.end(JSON.stringify(data));
}

const server = http.createServer(async (req, res) => {
  const urlObj = new URL(req.url ?? '/', `http://127.0.0.1:${PORT}`);
  const p = urlObj.pathname;

  try {
    if (p === '/betscout-logo.svg') {
      const logoSvgPath = path.resolve(__dirname, '../../../app/public/betscout-logo.svg');
      if (fs.existsSync(logoSvgPath)) {
        res.writeHead(200, { 'Content-Type': 'image/svg+xml; charset=utf-8' });
        res.end(fs.readFileSync(logoSvgPath, 'utf8'));
        return;
      }
    }

    if (p === '/api/showcase') {
      return sendJson(res, 200, await buildInitialShowcasePayload());
    }

    if (p === '/api/sport-leagues') {
      const sportId = Number(urlObj.searchParams.get('sportId') ?? 1);
      return sendJson(res, 200, await buildSportLeaguesPayload(sportId));
    }

    if (p === '/api/season') {
      const seasonId = urlObj.searchParams.get('seasonId') ?? '140782';
      const utId = urlObj.searchParams.get('utId') ?? undefined;
      return sendJson(res, 200, await buildSeasonIntelPayload(seasonId, utId));
    }

    if (p === '/api/team') {
      const teamId = urlObj.searchParams.get('teamId') ?? '2692';
      const seasonId = urlObj.searchParams.get('seasonId') ?? undefined;
      return sendJson(res, 200, await buildTeamIntelPayload(teamId, seasonId));
    }

    if (p === '/api/player') {
      const playerId = urlObj.searchParams.get('playerId') ?? '191210';
      const teamId = Number(urlObj.searchParams.get('teamId') ?? 2692);
      const seasonId = Number(urlObj.searchParams.get('seasonId') ?? 130971);
      return sendJson(res, 200, await buildPlayerIntelPayload(playerId, teamId, seasonId));
    }

    if (p === '/api/match') {
      const matchId = urlObj.searchParams.get('matchId') ?? '71945344';
      return sendJson(res, 200, await buildMatchIntelPayload(matchId));
    }

    if (p === '/api/match-center') {
      const matchId = urlObj.searchParams.get('matchId') ?? '76034538';
      const dossier = await client.getMatchCenterDossier(matchId);
      const hTeam =
        dossier.match_info?.match?.teams?.home ?? dossier.timeline_delta?.match?.teams?.home;
      const aTeam =
        dossier.match_info?.match?.teams?.away ?? dossier.timeline_delta?.match?.teams?.away;
      const hUid = hTeam?.uid ?? hTeam?._id;
      const aUid = aTeam?.uid ?? aTeam?._id;
      const rcIso = dossier.match_info?.realcategory?.cc?.a2;
      const hIso =
        (typeof hTeam?.cc === 'object' && hTeam?.cc?.a2
          ? hTeam.cc.a2
          : hTeam?.countrycode?.a2 ?? dossier.home_profile?.countrycode?.a2 ?? rcIso) ?? 'int';
      const aIso =
        (typeof aTeam?.cc === 'object' && aTeam?.cc?.a2
          ? aTeam.cc.a2
          : aTeam?.countrycode?.a2 ?? dossier.away_profile?.countrycode?.a2 ?? rcIso) ?? 'int';
      const tourIso =
        (dossier.match_info?.tournament as { tennisinfo?: { a2?: string } } | undefined)?.tennisinfo
          ?.a2 ??
        rcIso ??
        'int';
      const seasonObj = dossier.match_info?.season as { name?: string } | undefined;

      const homeImagePromise =
        hTeam?.haslogo && hUid
          ? Promise.resolve(getTeamLogoUrl(hUid, { size: 'big' }))
          : resolvePlayerHeadshotUrl(hTeam?.name);
      const awayImagePromise =
        aTeam?.haslogo && aUid
          ? Promise.resolve(getTeamLogoUrl(aUid, { size: 'big' }))
          : resolvePlayerHeadshotUrl(aTeam?.name);

      const [homeAvatarUrl, awayAvatarUrl, tournamentCrestUrl] = await Promise.all([
        homeImagePromise,
        awayImagePromise,
        resolveCompetitionCrestUrl(seasonObj?.name ?? dossier.match_info?.tournament?.name),
      ]);
      return sendJson(res, 200, {
        ...dossier,
        home_is_club: Boolean(hTeam?.haslogo),
        away_is_club: Boolean(aTeam?.haslogo),
        home_flag_url: getCountryFlagUrl(hIso, { format: 'svg', ratio: '4x3' }),
        away_flag_url: getCountryFlagUrl(aIso, { format: 'svg', ratio: '4x3' }),
        home_headshot_url: homeAvatarUrl,
        away_headshot_url: awayAvatarUrl,
        tournament_flag_url: getCountryFlagUrl(tourIso, { format: 'svg', ratio: '4x3' }),
        tournament_crest_url: tournamentCrestUrl,
      });
    }

    if (p === '/match-center.html' || p.startsWith('/match/')) {
      const htmlPath = path.join(__dirname, 'match-center.html');
      const html = fs.readFileSync(htmlPath, 'utf8');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
      return;
    }

    if (p === '/api/daily-matches') {
      const sportId = urlObj.searchParams.get('sportId') ?? '1';
      const dateYmd = urlObj.searchParams.get('date') ?? new Date().toISOString().slice(0, 10);
      const entries = await client.getDailyMatchIndex(sportId, dateYmd);
      return sendJson(res, 200, {
        ok: true,
        sportId: Number(sportId),
        dateYmd,
        count: entries.length,
        matches: entries.slice(0, 60).map((e) => {
          const hTeam = e.match_obj.teams?.home;
          const aTeam = e.match_obj.teams?.away;
          const hUid = hTeam?.uid ?? hTeam?._id;
          const aUid = aTeam?.uid ?? aTeam?._id;
          const hIso = typeof hTeam?.cc === 'object' && hTeam?.cc?.a2 ? hTeam.cc.a2 : null;
          const aIso = typeof aTeam?.cc === 'object' && aTeam?.cc?.a2 ? aTeam.cc.a2 : null;
          return {
            matchId: e.match_obj._id,
            seasonId: e.match_obj._seasonid,
            utId: e.match_obj._utid,
            tournament: e.tournament,
            tournamentCrestUrl: renderMonogramCrestDataUri(e.tournament, 24),
            tournamentFlagUrl: getCountryFlagUrl(hIso ?? 'int', { format: 'svg', ratio: '4x3' }),
            home: e.home,
            homeUid: hUid,
            homeCrestUrl:
              hTeam?.haslogo && hUid
                ? getTeamLogoUrl(hUid, { size: 'small' })
                : hIso
                  ? getCountryFlagUrl(hIso, { format: 'svg', ratio: '4x3' })
                  : renderMonogramCrestDataUri(e.home, 24),
            away: e.away,
            awayUid: aUid,
            awayCrestUrl:
              aTeam?.haslogo && aUid
                ? getTeamLogoUrl(aUid, { size: 'small' })
                : aIso
                  ? getCountryFlagUrl(aIso, { format: 'svg', ratio: '4x3' })
                  : renderMonogramCrestDataUri(e.away, 24),
            status: e.match_obj.status?.name ?? 'Scheduled',
            score:
              e.match_obj.result?.home != null
                ? `${e.match_obj.result.home} - ${e.match_obj.result.away}`
                : 'vs',
          };
        }),
      });
    }

    if (p === '/' || p === '/showcase.html') {
      const htmlPath = path.join(__dirname, 'showcase.html');
      const html = fs.readFileSync(htmlPath, 'utf8');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
      return;
    }

    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Not Found');
  } catch (err) {
    sendJson(res, 500, { ok: false, error: String(err) });
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`@betscout/sdk Interactive Web Showcase running at http://127.0.0.1:${PORT}`);
});
