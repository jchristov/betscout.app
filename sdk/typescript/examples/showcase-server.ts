/**
 * Interactive Web Showcase Server for `@betscout/sdk`.
 * Serves `examples/showcase.html` and exposes live JSON endpoints backed by `BetScoutClient`.
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
  parsePrematchMarkets,
  parseVenueCoordinates,
  renderTeamJerseySvg,
} from '../src/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT ?? 8788);

const client = new BetScoutClient({
  defaultChannel: 'eu-retail',
  defaultTimezone: 'Europe:Berlin',
});

let cachedShowcasePayload: unknown = null;
let cachedAtMs = 0;

async function buildShowcasePayload() {
  const now = Date.now();
  if (cachedShowcasePayload && now - cachedAtMs < 120_000) {
    return cachedShowcasePayload;
  }

  const sampleMatchId = 71945344; // Udinese vs AC Milan
  const [
    sports,
    milanBundle,
    djokovicBundle,
    serieATable,
    seasonGoals,
    seasonOu,
    nbaTeamStats,
    serieAWinners,
    derbyVersus,
    sanSiroStats,
    squadFacts,
    maignanCareer,
    maignanMatches,
    matchInfo,
    matchMarketsPrimary,
    matchMarketsConsensus,
    matchInsights,
    matchCommentary,
    leagueSummary,
    uclBrackets,
    oddsFormats,
  ] = await Promise.all([
    client.listAllSports(SERVICE_PROFILES.GLOBAL_UNLIMITED, 0, 'global'),
    client.getTeamIntelligenceBundle(2692, {
      seasonId: 130971,
      lastMatchesLimit: 6,
      nextMatchesLimit: 4,
    }),
    client.getTennisPlayerIntelligenceBundle(14882, {
      lastMatchesLimit: 6,
      nextMatchesLimit: 3,
    }),
    client.getEnrichedLeagueTable(140782),
    client.getSeasonGoalsDistribution(140782),
    client.getSeasonOverUnder(140782),
    client.getSeasonUniqueTeamStats(142074), // NBA 26/27
    client.getTournamentSeasonsWinners(23), // Serie A
    client.getTeamVersus(2692, 2697, 6), // AC Milan vs Inter
    client.getVenueSeasonStats(647, 130971), // Stadio Giuseppe Meazza (San Siro)
    client.getTeamPlayerSeasonFacts(2692, 130971),
    client.getPlayerCareerStats(191210), // Mike Maignan
    client.getPlayerSeasonMatches(191210, 130971),
    client.getMatchInfo(sampleMatchId),
    client.getMatchMarkets(sampleMatchId, 'prematch', 'eu-retail'),
    client.getMatchMarkets(sampleMatchId, 'prematch', 'global'),
    client.getMatchInsights(sampleMatchId),
    client.getMatchCommentary(sampleMatchId),
    client.getSeasonLeagueSummary(130971),
    client.getCupBrackets(110232),
    client.getOddsFormatTable(),
  ]);

  const milanGoals = seasonGoals?.teams?.find((t) => t.team?.uid === 2692) ?? null;
  const milanOu = seasonOu?.stats?.['2692'] ?? null;
  const nbaTeams = Object.values(nbaTeamStats?.stats?.uniqueteams ?? {})
    .slice(0, 8)
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
      threePtPct: t.three_points?.percentage ?? null,
    }));

  const parsedPrimaryMarkets = parsePrematchMarkets(matchMarketsPrimary?.markets, false);
  const parsedConsensusMarkets = parsePrematchMarkets(matchMarketsConsensus?.markets, false);

  const payload = {
    generatedAtUtc: new Date().toISOString(),
    sdkVersion: '1.1.0',
    catalog: {
      sportsCount: sports.length,
      sports,
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
    clubIntelligence: {
      ...milanBundle,
      logoBigUrl: getTeamLogoUrl(2692, { size: 'big' }),
      countryFlagSvgUrl: getCountryFlagUrl('it', { format: 'svg', ratio: '4x3' }),
      homeJerseySvg: renderTeamJerseySvg(milanBundle.profile?.homejersey, {
        shirtNumber: 10,
        sizePx: 88,
      }),
      awayJerseySvg: renderTeamJerseySvg(milanBundle.profile?.awayjersey, {
        shirtNumber: 11,
        sizePx: 88,
      }),
      gkJerseySvg: renderTeamJerseySvg(milanBundle.profile?.gkjersey, {
        shirtNumber: 16,
        sizePx: 88,
      }),
    },
    tennisIntelligence: {
      ...djokovicBundle,
      countryFlagSvgUrl: getCountryFlagUrl('rs', { format: 'svg', ratio: '4x3' }),
    },
    playerSpotlight: {
      player: maignanCareer?.player ?? null,
      marketValueEur: squadFacts?.['191210']?.player?.marketvalue ?? null,
      shirtNumber: squadFacts?.['191210']?.player?.shirtnumber ?? null,
      memberSince: squadFacts?.['191210']?.player?.membersince?.date ?? null,
      seasonTotals: squadFacts?.['191210']?.stats?.total ?? null,
      clubs: Object.values(maignanCareer?.uniqueteams ?? {}),
      seasonMatchesCount: maignanMatches?.matches?.length ?? 0,
      recentMatches: (maignanMatches?.matches ?? []).slice(0, 6),
      flagSvgUrl: getCountryFlagUrl('fr', { format: 'svg', ratio: '4x3' }),
    },
    standingsAndForm: {
      ...serieATable,
      rows: serieATable.rows.map((r) => ({
        ...r,
        logoUrl: getTeamLogoUrl(r.team_uid, { size: 'small' }),
      })),
    },
    goalTimingAndOverUnder: {
      milanGoals,
      leagueTotals: seasonGoals?.totals ?? null,
      milanOverUnder: milanOu,
      leagueSummary,
    },
    multiSportAndTournaments: {
      nbaTeams,
      serieARollOfHonor: (serieAWinners?.seasons ?? []).slice(0, 10).map((s) => ({
        year: s.year,
        name: s.name,
        champion: s.champion?.mediumname ?? s.champion?.name ?? null,
        championId: s.champion?._id ?? null,
        championLogo: s.champion?._id ? getTeamLogoUrl(s.champion._id, { size: 'small' }) : null,
        runnerUp: s.runnerup?.mediumname ?? s.runnerup?.name ?? null,
      })),
      derbyVersus: {
        matches: (derbyVersus?.matches ?? []).slice(0, 5),
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
        matchId: sampleMatchId,
        home: matchInfo?.match?.teams?.home?.mediumname ?? matchInfo?.match?.teams?.home?.name,
        away: matchInfo?.match?.teams?.away?.mediumname ?? matchInfo?.match?.teams?.away?.name,
        result: matchInfo?.match?.result ?? null,
        funFacts: matchInsights?.funfacts ?? [],
        commentarySample: (matchCommentary?.phrases ?? []).slice(0, 8),
        primaryMarkets: parsedPrimaryMarkets,
        consensusMarkets: parsedConsensusMarkets,
        oddsFormatSample: (oddsFormats ?? []).slice(0, 6),
      },
    },
  };

  cachedShowcasePayload = payload;
  cachedAtMs = now;
  return payload;
}

const server = http.createServer(async (req, res) => {
  const urlObj = new URL(req.url ?? '/', `http://127.0.0.1:${PORT}`);

  if (urlObj.pathname === '/api/showcase') {
    try {
      const data = await buildShowcasePayload();
      res.writeHead(200, {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
      });
      res.end(JSON.stringify(data));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ ok: false, error: String(err) }));
    }
    return;
  }

  if (urlObj.pathname === '/' || urlObj.pathname === '/showcase.html') {
    const htmlPath = path.join(__dirname, 'showcase.html');
    const html = fs.readFileSync(htmlPath, 'utf8');
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Not Found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`@betscout/sdk Interactive Web Showcase running at http://127.0.0.1:${PORT}`);
});
