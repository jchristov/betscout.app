/**
 * BetScout Sports Data & Odds Client (`BetScoutClient`).
 * Provides unified access to 56 sports, multi-bookmaker pre-match & live markets (including 28-outcome Correct Score),
 * 3-second real-time timeline deltas, team & player profiles, historical performance, season statistics,
 * squad lineups, injuries, transfers, and tennis career surface matrices.
 */

import { SPORTS_CATALOG, resolveSportId } from './constants.js';
import {
  DEFAULT_UPSTREAM_BASE_URL,
  buildUpstreamFeedUrl,
  resolveUpstreamChannel,
} from './internal/transport.js';
import type {
  BetScoutBatchMarketsResponse,
  BetScoutCategoryTreeMini,
  BetScoutClientOptions,
  BetScoutCupBracketsResponse,
  BetScoutDailySportMatchesResponse,
  BetScoutDocument,
  BetScoutDynamicTableResponse,
  BetScoutEnvelope,
  BetScoutEventGetResponse,
  BetScoutFormTableMatchItem,
  BetScoutFormTableResponse,
  BetScoutJerseyColors,
  BetScoutLeagueTable,
  BetScoutMatchDetailsResponse,
  BetScoutMatchFormResponse,
  BetScoutMatchFunFactsResponse,
  BetScoutMatchHead2HeadResponse,
  BetScoutMatchInfoResponse,
  BetScoutMatchMarketsResponse,
  BetScoutMatchPhrasesResponse,
  BetScoutMatchSituationsResponse,
  BetScoutMatchSquadsResponse,
  BetScoutMatchStatsResponse,
  BetScoutMatchTimelineDeltaResponse,
  BetScoutMatchTimelineResponse,
  BetScoutOddsFormatEntry,
  BetScoutPlayerCareerStatsResponse,
  BetScoutPlayerFactsResponse,
  BetScoutPlayerSeasonMatchesResponse,
  BetScoutRefereeSeasonStatsResponse,
  BetScoutRequestOptions,
  BetScoutSeasonDescriptor,
  BetScoutSeasonGoalsResponse,
  BetScoutSeasonInjuryItem,
  BetScoutSeasonLeagueSummaryResponse,
  BetScoutSeasonMarketsResponse,
  BetScoutSeasonMetaResponse,
  BetScoutSeasonOverUnderResponse,
  BetScoutSeasonRefereesResponse,
  BetScoutSeasonTablesResponse,
  BetScoutSeasonTopListResponse,
  BetScoutSeasonUniqueTeamStatsResponse,
  BetScoutSeasonVenuesResponse,
  BetScoutSportConfigItem,
  BetScoutTeamMatchesResponse,
  BetScoutTeamPlayerFactsMap,
  BetScoutTeamPositionHistoryResponse,
  BetScoutTeamProfileResponse,
  BetScoutTeamScoringConcedingResponse,
  BetScoutTeamSeasonMatchesResponse,
  BetScoutTeamSeasonOfficialsResponse,
  BetScoutTeamSeasonStatsResponse,
  BetScoutTeamSeasonsResponse,
  BetScoutTeamSquadResponse,
  BetScoutTeamStreaksResponse,
  BetScoutTeamTournamentsResponse,
  BetScoutTeamTransfersResponse,
  BetScoutTeamUsualLineupResponse,
  BetScoutTeamVersusResponse,
  BetScoutTennisCalendarResponse,
  BetScoutTennisRankingResponse,
  BetScoutTennisSurfaceRecord,
  BetScoutTennisSurfaceStatsResponse,
  BetScoutTournamentSeasonsWinnersResponse,
  BetScoutUniqueTeamMarketsResponse,
  BetScoutUniqueTournament,
  BetScoutUniqueTournamentInfoResponse,
  BetScoutVenueStatsResponse,
  CountryFlagOptions,
  DailyMatchIndexEntry,
  DailyOddsLookupResult,
  EnrichedLeagueTableBundle,
  EnrichedStandingsRow,
  FeedLanguage,
  FeedTimezone,
  GoalIntervalBucketSummary,
  InjuryGateEvaluation,
  InsightsPushStreamOptions,
  InsightsStreamEvent,
  JerseySvgOptions,
  LiveMatchSituationsPressure,
  LiveTimelineDeltaSummary,
  MatchCenterDossier,
  MatchIntelligenceBundle,
  ParsedPrematchMarkets,
  ProviderChannel,
  SportCatalogItem,
  TeamGoalIntervalsSummary,
  TeamIntelligenceBundle,
  TeamLogoOptions,
  TeamMissingPlayerEntry,
  TennisPlayerIntelligenceBundle,
  TennisSurfaceSummary,
} from './types.js';
import {
  computeFormWdlSegments,
  computeH2HEdgeSummary,
  getAdaptiveRefetchIntervalMs,
  getCountryFlagUrl,
  getTeamLogoUrl,
  mergePrimaryAndConsensusMarkets,
  namesMatch,
  parsePrematchMarkets,
  renderTeamJerseySvg,
} from './utils.js';

interface CacheEntry<T = unknown> {
  expiresAtMs: number;
  value: T;
  doc?: BetScoutDocument<T>;
}

const DEFAULT_HEADERS: Readonly<Record<string, string>> = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
  Origin: 'https://statshub.sportradar.com',
  Referer: 'https://statshub.sportradar.com/tipico/en/',
  Accept: 'application/json',
};

function todayYmdUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function nextDayYmdUtc(ymd: string): string {
  const dt = new Date(`${ymd.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(dt.getTime())) return ymd;
  dt.setUTCDate(dt.getUTCDate() + 1);
  return dt.toISOString().slice(0, 10);
}

function formatUtcIsoMinutes(utsSeconds: number): string {
  return new Date(utsSeconds * 1000).toISOString().slice(0, 16) + 'Z';
}

export class BetScoutClient {
  private readonly baseUrl: string;
  private readonly defaultChannel: ProviderChannel;
  private readonly defaultLanguage: FeedLanguage;
  private readonly defaultTimezone: FeedTimezone;
  private readonly defaultTtlSec: number;
  private readonly timeoutMs: number;
  private readonly fetchFn: typeof fetch;
  private readonly cache = new Map<string, CacheEntry<any>>();

  constructor(options: BetScoutClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? DEFAULT_UPSTREAM_BASE_URL).replace(/\/+$/, '');
    this.defaultChannel = options.defaultChannel ?? 'eu-retail';
    this.defaultLanguage = options.defaultLanguage ?? 'en';
    this.defaultTimezone = options.defaultTimezone ?? 'Europe:Berlin';
    this.defaultTtlSec = options.defaultTtlSec ?? 300;
    this.timeoutMs = options.timeoutMs ?? 12000;
    this.fetchFn = options.fetchFn ?? globalThis.fetch.bind(globalThis);
  }

  /** Number of entries currently stored in the in-memory response cache. */
  public get cacheSize(): number {
    return this.cache.size;
  }

  /** Clear all cached responses. */
  public clearCache(): void {
    this.cache.clear();
  }

  /**
   * Build the relative transport path for a given feed endpoint and parameter string.
   */
  public buildRelativePath(
    endpoint: string,
    paramsPath = '',
    options: BetScoutRequestOptions = {},
  ): string {
    const channel = resolveUpstreamChannel(options.channel ?? this.defaultChannel);
    const language = options.language ?? this.defaultLanguage;
    const timezone = options.timezone ?? this.defaultTimezone;
    const cleanEndpoint = endpoint.replace(/^\/+|\/+$/g, '');
    const cleanParams = paramsPath.replace(/^\/+|\/+$/g, '');
    return cleanParams
      ? `${channel}/${language}/${timezone}/gismo/${cleanEndpoint}/${cleanParams}`
      : `${channel}/${language}/${timezone}/gismo/${cleanEndpoint}`;
  }

  /**
   * Low-level feed query returning the full `BetScoutDocument<T>` (`{ event, _dob, _maxage, data }`).
   */
  public async fetchDocument<T = unknown>(
    endpoint: string,
    paramsPath = '',
    options: BetScoutRequestOptions = {},
  ): Promise<BetScoutDocument<T> | null> {
    const channel = resolveUpstreamChannel(options.channel ?? this.defaultChannel);
    const ttlSec = options.ttlSec ?? this.defaultTtlSec;
    const cacheKey = `${channel}:${endpoint}:${paramsPath}`;
    const now = Date.now();

    if (!options.bypassCache && ttlSec > 0) {
      const hit = this.cache.get(cacheKey);
      if (hit && hit.expiresAtMs > now && hit.doc) {
        return hit.doc as BetScoutDocument<T>;
      }
    }

    const directUrl = buildUpstreamFeedUrl(
      this.baseUrl,
      channel,
      options.language ?? this.defaultLanguage,
      options.timezone ?? this.defaultTimezone,
      endpoint,
      paramsPath,
    );

    try {
      const resp = await this.fetchWithTimeout(directUrl, { headers: DEFAULT_HEADERS });
      if (resp.ok) {
        const payload = (await resp.json()) as BetScoutEnvelope<T>;
        const doc0 = payload?.doc?.[0];
        if (
          doc0 &&
          typeof doc0 === 'object' &&
          doc0.event !== 'exception' &&
          (doc0.data as Record<string, unknown> | undefined)?._doc !== 'exception'
        ) {
          this.cache.set(cacheKey, {
            expiresAtMs: now + ttlSec * 1000,
            value: doc0.data,
            doc: doc0,
          });
          return doc0;
        }
      }
    } catch {
      return null;
    }

    return null;
  }

  /**
   * Query a feed endpoint and return the inner `doc[0].data` payload (`T | null`).
   */
  public async fetchFeed<T = unknown>(
    endpoint: string,
    paramsPath = '',
    options: BetScoutRequestOptions = {},
  ): Promise<T | null> {
    const doc = await this.fetchDocument<T>(endpoint, paramsPath, options);
    return doc ? doc.data : null;
  }

  private async fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      return await this.fetchFn(url, { ...init, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }

  // ==========================================================================
  // A. Configuration & Sport / Tournament Discovery Endpoints
  // ==========================================================================

  /**
   * List all available sports supported by the data platform (`config_sports/{serviceId}/{configId}`).
   * Falls back to the built-in 56-sport `SPORTS_CATALOG` if offline.
   */
  public async listAllSports(
    serviceId = 69,
    configId = 0,
    channel: ProviderChannel = 'global',
  ): Promise<SportCatalogItem[]> {
    const data = await this.fetchFeed<BetScoutSportConfigItem[]>(
      'config_sports',
      `${serviceId}/${configId}`,
      { channel, timezone: 'Etc:UTC', ttlSec: 3600 },
    );
    if (Array.isArray(data) && data.length > 0) {
      return data
        .filter((s) => s && typeof s._id === 'number')
        .map((s) => ({ sportId: Number(s._id), name: String(s.name) }));
    }
    return Object.entries(SPORTS_CATALOG).map(([id, name]) => ({
      sportId: Number(id),
      name,
    }));
  }

  /** Query category & tournament hierarchy for a sport (`config_tree_mini/{serviceId}/{configId}/{sportId}/{rcId}`). */
  public async getCategoryTree(
    serviceId = 69,
    configId = 0,
    sportOrId: string | number = 1,
    rcId?: number,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutCategoryTreeMini | null> {
    const sportId = resolveSportId(sportOrId);
    const params =
      rcId !== undefined
        ? `${serviceId}/${configId}/${sportId}/${rcId}`
        : `${serviceId}/${configId}/${sportId}`;
    return this.fetchFeed<BetScoutCategoryTreeMini>('config_tree_mini', params, {
      channel: 'global',
      ttlSec: 3600,
      ...options,
    });
  }

  /** Query featured unique tournaments for a sport (`config_uniquetournaments/{serviceId}/{sportId}`). */
  public async getUniqueTournaments(
    serviceId = 69,
    sportOrId: string | number = 1,
    options?: BetScoutRequestOptions,
  ): Promise<Record<string, BetScoutUniqueTournament> | BetScoutUniqueTournament[] | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchFeed('config_uniquetournaments', `${serviceId}/${sportId}`, {
      channel: 'global',
      ttlSec: 3600,
      ...options,
    });
  }

  /** Query all unique tournaments for a sport (`config_uniquetournamentsall/0/{serviceId}/{sportId}`). */
  public async getAllUniqueTournaments(
    serviceId = 69,
    sportOrId: string | number = 1,
    options?: BetScoutRequestOptions,
  ): Promise<Record<string, BetScoutUniqueTournament> | BetScoutUniqueTournament[] | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchFeed('config_uniquetournamentsall', `0/${serviceId}/${sportId}`, {
      channel: 'global',
      ttlSec: 3600,
      ...options,
    });
  }

  /** Query the ATP/WTA/Challenger tournament calendar for a season year (`tennis_calendar/{seasonYear}`). */
  public async getTennisCalendar(
    seasonYear: number | string = new Date().getUTCFullYear(),
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTennisCalendarResponse | null> {
    return this.fetchFeed<BetScoutTennisCalendarResponse>('tennis_calendar', String(seasonYear), {
      channel: 'neutral',
      ttlSec: 3600,
      ...options,
    });
  }

  // ==========================================================================
  // B. Daily Match Schedules & Multi-Bookmaker Markets
  // ==========================================================================

  /**
   * Query all scheduled, live, and finished matches for a sport on `dateYmd` (`YYYY-MM-DD`).
   */
  public async getDailySportMatches(
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
    tzOffset = 0,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutDailySportMatchesResponse | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchFeed<BetScoutDailySportMatchesResponse>(
      'unified_sport_matches',
      `${sportId}/${dateYmd}/${tzOffset}`,
      { ttlSec: 600, ...options },
    );
  }

  /**
   * Query bulk daily pre-match markets for all matches on `dateYmd`
   * (`channel: 'eu-retail'` for Primary Retail `_bookmakerId: 176`, or `'global'` for Consensus `_bookmakerId: 0`).
   */
  public async getDailySportMarkets(
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
    channel: ProviderChannel = 'eu-retail',
    tzOffset = 0,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutBatchMarketsResponse | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchFeed<BetScoutBatchMarketsResponse>(
      'unified_sport_matches_markets',
      `${sportId}/${dateYmd}/${tzOffset}`,
      { channel, ttlSec: 600, ...options },
    );
  }

  /**
   * Query the full pre-match market suite of a single match
   * (1X2, Double Chance, Draw No Bet, Asian Handicap, Over/Under Totals, and 28-outcome Correct Score matrix).
   */
  public async getMatchMarkets(
    matchId: number | string,
    marketType: 'prematch' | 'live' | string = 'prematch',
    channel: ProviderChannel = 'eu-retail',
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchMarketsResponse | null> {
    return this.fetchFeed<BetScoutMatchMarketsResponse>(
      'match_markets',
      `${matchId}/${marketType}`,
      { channel, ttlSec: 600, ...options },
    );
  }

  /** Query tournament outright / winner futures odds for a season (`season_markets/{seasonId}`). */
  public async getSeasonMarkets(
    seasonId: number | string,
    channel: ProviderChannel = 'eu-retail',
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonMarketsResponse | null> {
    return this.fetchFeed<BetScoutSeasonMarketsResponse>('season_markets', String(seasonId), {
      channel,
      ttlSec: 1800,
      ...options,
    });
  }

  // ==========================================================================
  // C. Match Intelligence, Live 3s Delta Stream, Squads, Injuries, Form & H2H
  // ==========================================================================

  /**
   * Query real-time 3-second live scores (`_maxage: 3`), set/period breakdowns,
   * tennis game points & active server, and rolling event deltas for a match.
   */
  public async getMatchTimelineDelta(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchTimelineDeltaResponse | null> {
    return this.fetchFeed<BetScoutMatchTimelineDeltaResponse>(
      'match_timelinedelta',
      String(matchId),
      { channel: 'global', ttlSec: 3, ...options },
    );
  }

  /** Query the global 10-second live event feed across a sport (`_maxage: 10`). */
  public async getLiveEventsBySport(
    sportOrId: string | number = 'soccer',
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutEventGetResponse | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchFeed<BetScoutEventGetResponse>('event_get', String(sportId), {
      channel: 'global',
      ttlSec: 10,
      ...options,
    });
  }

  /** Query full match metadata, stadium, weather, managers & referee (`match_info_statshub/{matchId}`). */
  public async getMatchInfo(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchInfoResponse | null> {
    return this.fetchFeed<BetScoutMatchInfoResponse>('match_info_statshub', String(matchId), {
      channel: 'global',
      ttlSec: 60,
      ...options,
    });
  }

  /** Query confirmed starting XI (`startinglineup`), `substitutes`, and `manager` for a match (`match_squads/{matchId}`). */
  public async getMatchSquads(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchSquadsResponse | null> {
    return this.fetchFeed<BetScoutMatchSquadsResponse>('match_squads', String(matchId), {
      channel: 'global',
      ttlSec: 300,
      ...options,
    });
  }

  /** Query official league-wide injured, missing, and suspended players (`stats_season_injuries/{seasonId}`). */
  public async getSeasonInjuries(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonInjuryItem[] | null> {
    return this.fetchFeed<BetScoutSeasonInjuryItem[]>('stats_season_injuries', String(seasonId), {
      ttlSec: 1800,
      ...options,
    });
  }

  /** Query chronological W/D/L form sequences and current streaks for a match (`stats_match_form/{matchId}`). */
  public async getMatchForm(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchFormResponse | null> {
    return this.fetchFeed<BetScoutMatchFormResponse>('stats_match_form', String(matchId), {
      ttlSec: 1800,
      ...options,
    });
  }

  /** Query head-to-head confrontation history of a match pair (`stats_match_head2head/{matchId}`). */
  public async getMatchHead2Head(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchHead2HeadResponse | null> {
    return this.fetchFeed<BetScoutMatchHead2HeadResponse>(
      'stats_match_head2head',
      String(matchId),
      { ttlSec: 1800, ...options },
    );
  }

  /** Query direct H2H meetings between any two team or player IDs (`stats_h2h_versus/{minId}/{maxId}/{limit}`). */
  public async getHead2HeadVersus(
    teamIdA: number | string,
    teamIdB: number | string,
    limit = 10,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchHead2HeadResponse | null> {
    const aNum = Number(teamIdA);
    const bNum = Number(teamIdB);
    const minUid = Number.isFinite(aNum) && Number.isFinite(bNum) ? Math.min(aNum, bNum) : teamIdA;
    const maxUid = Number.isFinite(aNum) && Number.isFinite(bNum) ? Math.max(aNum, bNum) : teamIdB;
    return this.fetchFeed<BetScoutMatchHead2HeadResponse>(
      'stats_h2h_versus',
      `${minUid}/${maxUid}/${limit}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /** Query live pitch attack / dangerous-attack territorial coordinates (`match_situations/{matchId}`). */
  public async getMatchSituations(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchSituationsResponse | null> {
    return this.fetchFeed<BetScoutMatchSituationsResponse>('match_situations', String(matchId), {
      channel: 'neutral',
      ttlSec: 45,
      ...options,
    });
  }

  /** Query detailed match boxscore statistics (`stats_match_stats/{matchId}`). */
  public async getMatchStats(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchStatsResponse | null> {
    return this.fetchFeed<BetScoutMatchStatsResponse>('stats_match_stats', String(matchId), {
      ttlSec: 120,
      ...options,
    });
  }

  /**
   * Query detailed match statistics (`match_details/{matchId}`), including Tennis Aces, Double Faults,
   * 1st/2nd Serve %, Break Points Won, Service/Receiver Points Won, Max Points in a Row, and set durations.
   */
  public async getMatchDetails(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchDetailsResponse | null> {
    return this.fetchFeed<BetScoutMatchDetailsResponse>('match_details', String(matchId), {
      channel: 'global',
      ttlSec: 30,
      ...options,
    });
  }

  /**
   * Query extended period-by-period match statistics (`match_detailsextended/{matchId}`),
   * returning both full-match totals and set-by-set / period-by-period breakdowns (`1518`..`1746`, `gameswonperiod`).
   */
  public async getMatchDetailsExtended(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchDetailsResponse | null> {
    return this.fetchFeed<BetScoutMatchDetailsResponse>(
      'match_detailsextended',
      String(matchId),
      { channel: 'global', ttlSec: 30, ...options },
    );
  }

  // ==========================================================================
  // D. Team & Player Profiles, Historical Performance, Squads & Season Stats
  // ==========================================================================

  /**
   * Fetch the full profile of a team or individual competitor (`stats_team_info/{teamId}`).
   * - For clubs (e.g. `2692` AC Milan): returns `team`, `founded`, `homejersey`, `awayjersey`, `gkjersey`, `stadium`, `manager`, and `tournaments`.
   * - For tennis/individual players (e.g. `14882` Novak Djokovic): returns `turnedpro`, `dateofbirth`, `nationality`, `height`, `weight`, `plays`, `coachname`, `favouritesurface`, `singlesrank`, `doublesrank`, `highestranking`, `groundstats`, `ranking`, and `performance`.
   */
  public async getTeamProfile(
    teamId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamProfileResponse | null> {
    return this.fetchFeed<BetScoutTeamProfileResponse>('stats_team_info', String(teamId), {
      channel: 'global',
      ttlSec: 3600,
      ...options,
    });
  }

  /**
   * Fetch a team's or player's last `limit` completed historical matches (`stats_team_lastx/{teamId}/{limit}`).
   */
  public async getTeamLastMatches(
    teamId: number | string,
    limit = 20,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamMatchesResponse | null> {
    return this.fetchFeed<BetScoutTeamMatchesResponse>(
      'stats_team_lastx',
      `${teamId}/${limit}`,
      { channel: 'global', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch a team's or player's extended last `limit` matches with court surface (`ground`),
   * round metadata (`roundname`), and cup round context (`stats_team_lastxextended/{teamId}/{limit}`).
   */
  public async getTeamLastMatchesExtended(
    teamId: number | string,
    limit = 20,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamMatchesResponse | null> {
    return this.fetchFeed<BetScoutTeamMatchesResponse>(
      'stats_team_lastxextended',
      `${teamId}/${limit}`,
      { channel: 'global', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch a team's or player's next `limit` upcoming scheduled fixtures (`stats_team_nextx/{teamId}/{limit}`).
   */
  public async getTeamNextMatches(
    teamId: number | string,
    limit = 10,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamMatchesResponse | null> {
    return this.fetchFeed<BetScoutTeamMatchesResponse>(
      'stats_team_nextx',
      `${teamId}/${limit}`,
      { channel: 'global', ttlSec: 900, ...options },
    );
  }

  /**
   * Fetch active & historical team/player streaks, recent form sequence, and `nextmatches` difficulty ratings
   * (`stats_team_streaks/{teamId}`).
   */
  public async getTeamStreaks(
    teamId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamStreaksResponse | null> {
    return this.fetchFeed<BetScoutTeamStreaksResponse>('stats_team_streaks', String(teamId), {
      channel: 'neutral',
      ttlSec: 1800,
      ...options,
    });
  }

  /**
   * Fetch all historical and active domestic/international seasons for a team (`uniqueteam_seasons/{teamId}`).
   */
  public async getTeamSeasons(
    teamId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamSeasonsResponse | null> {
    return this.fetchFeed<BetScoutTeamSeasonsResponse>('uniqueteam_seasons', String(teamId), {
      channel: 'global',
      ttlSec: 3600,
      ...options,
    });
  }

  /**
   * Fetch per-game season statistics for a team in a specific season (`stats_team_seasonstats/{teamId}/{seasonId}`),
   * including `goal_attempts`, `shots_on_goal`, `ball_possession`, `corner_kicks`, `cards_given`, `freekicks`, `offside`, and `shots_blocked`.
   */
  public async getTeamSeasonStats(
    teamId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamSeasonStatsResponse | null> {
    return this.fetchFeed<BetScoutTeamSeasonStatsResponse>(
      'stats_team_seasonstats',
      `${teamId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch all matches played by a team in a specific season (`stats_team_seasonmatches/{teamId}/{seasonId}`).
   */
  public async getTeamSeasonMatches(
    teamId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamSeasonMatchesResponse | null> {
    return this.fetchFeed<BetScoutTeamSeasonMatchesResponse>(
      'stats_team_seasonmatches',
      `${teamId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch home/away/total scoring & conceding splits and 15-minute goal interval distributions
   * (`stats_season_teamscoringconceding/{seasonId}/{teamId}/{limit}`).
   */
  public async getTeamScoringConcedingSplits(
    seasonId: number | string,
    teamId: number | string,
    limit = 10,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamScoringConcedingResponse | null> {
    return this.fetchFeed<BetScoutTeamScoringConcedingResponse>(
      'stats_season_teamscoringconceding',
      `${seasonId}/${teamId}/${limit}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch round-by-round league table position history for a team (`stats_season_teampositionhistory/{seasonId}/{teamId}`).
   */
  public async getTeamPositionHistory(
    seasonId: number | string,
    teamId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamPositionHistoryResponse | null> {
    return this.fetchFeed<BetScoutTeamPositionHistoryResponse>(
      'stats_season_teampositionhistory',
      `${seasonId}/${teamId}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch the full active squad roster (`players`, `managers`, `roles`, `squadinfo`) for a club (`stats_team_squad/{teamId}`).
   */
  public async getTeamSquad(
    teamId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamSquadResponse | null> {
    return this.fetchFeed<BetScoutTeamSquadResponse>('stats_team_squad', String(teamId), {
      channel: 'global',
      ttlSec: 3600,
      ...options,
    });
  }

  /**
   * Fetch the season-specific squad roster, managers, and roles for a club (`stats_team_seasonsquad2/{teamId}/{seasonId}`).
   */
  public async getTeamSeasonSquad(
    teamId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamSquadResponse | null> {
    return this.fetchFeed<BetScoutTeamSquadResponse>(
      'stats_team_seasonsquad2',
      `${teamId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Fetch the preferred tactical formation (e.g. `"3-5-2"`) and usual starting XI players for a team in a season
   * (`stats_team_usuallineup/{teamId}/{seasonId}`).
   */
  public async getTeamUsualLineup(
    teamId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamUsualLineupResponse | null> {
    return this.fetchFeed<BetScoutTeamUsualLineupResponse>(
      'stats_team_usuallineup',
      `${teamId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Fetch historical player arrivals, departures, and loan transfers for a club (`stats_team_transfers/{teamId}`).
   */
  public async getTeamTransfers(
    teamId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamTransfersResponse | null> {
    return this.fetchFeed<BetScoutTeamTransfersResponse>('stats_team_transfers', String(teamId), {
      channel: 'global',
      ttlSec: 3600,
      ...options,
    });
  }

  /**
   * Fetch historical tournament participation and trophy records for a club (`stats_team_tournaments/{teamId}`).
   */
  public async getTeamTournaments(
    teamId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamTournamentsResponse | null> {
    return this.fetchFeed<BetScoutTeamTournamentsResponse>(
      'stats_team_tournaments',
      String(teamId),
      { channel: 'global', ttlSec: 3600, ...options },
    );
  }

  /**
   * Fetch referee assignment and card history for a team in a specific season (`stats_uniqueteam_seasonofficials/{teamId}/{seasonId}`).
   */
  public async getTeamSeasonOfficials(
    teamId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamSeasonOfficialsResponse | null> {
    return this.fetchFeed<BetScoutTeamSeasonOfficialsResponse>(
      'stats_uniqueteam_seasonofficials',
      `${teamId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Fetch an individual player's multi-season career statistics across all clubs & competitions (`stats_player_stats/{playerId}`).
   */
  public async getPlayerCareerStats(
    playerId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutPlayerCareerStatsResponse | null> {
    return this.fetchFeed<BetScoutPlayerCareerStatsResponse>(
      'stats_player_stats',
      String(playerId),
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Fetch an individual player's career facts, roles, clubs, and milestones (`stats_player_facts/{playerId}`).
   */
  public async getPlayerFacts(
    playerId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutPlayerFactsResponse | null> {
    return this.fetchFeed<BetScoutPlayerFactsResponse>('stats_player_facts', String(playerId), {
      channel: 'neutral',
      ttlSec: 3600,
      ...options,
    });
  }

  /**
   * Fetch every match played by an individual player in a given season (`player_seasonmatches/{playerId}/{seasonId}`).
   */
  public async getPlayerSeasonMatches(
    playerId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutPlayerSeasonMatchesResponse | null> {
    return this.fetchFeed<BetScoutPlayerSeasonMatchesResponse>(
      'player_seasonmatches',
      `${playerId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  // ==========================================================================
  // E. Tennis Career & Surface Analytics, Standings Tables & Referee Stats
  // ==========================================================================

  /**
   * Fetch multi-season ATP/WTA win-loss records broken down by year (`2004`–`2026`) and court surface
   * (`0`=All, `1`=Clay, `2`=Hard Outdoor, `3`=Indoor, `4`=Grass) (`tennis_team_surfacestats/{playerId}`).
   */
  public async getTennisPlayerSurfaceStats(
    playerId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTennisSurfaceStatsResponse | null> {
    return this.fetchFeed<BetScoutTennisSurfaceStatsResponse>(
      'tennis_team_surfacestats',
      String(playerId),
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /** Query official ATP/WTA rankings (`tennis_ranking/{type}/{year}/{week}`). */
  public async getTennisRanking(
    tourType: 'atp' | 'wta' | string,
    year: number | string,
    week: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTennisRankingResponse | null> {
    return this.fetchFeed<BetScoutTennisRankingResponse>(
      'tennis_ranking',
      `${tourType}/${year}/${week}`,
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Query league standings tables (`stats_season_tables/{seasonId}` or `stats_season_tables/{seasonId}/{tableType}/{round}` when optional parameters are provided).
   * Returns full `tablerows[]` with Total/Home/Away played, W/D/L, `goalsFor*`, `goalsAgainst*`, `goalDiff*`, `points*`, position changes (`changeTotal`/`changeHome`/`changeAway`), and `promotion` zones.
   */
  public async getSeasonTables(
    seasonId: number | string,
    tableType?: number | string,
    round?: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonTablesResponse | null> {
    const params = [seasonId, tableType, round]
      .filter((v): v is number | string => v !== undefined && v !== null && String(v).length > 0)
      .join('/');
    return this.fetchFeed<BetScoutSeasonTablesResponse>('stats_season_tables', params, {
      channel: 'neutral',
      ttlSec: 1800,
      ...options,
    });
  }

  /**
   * Query the real-time dynamic league table (`season_dynamictable/{seasonId}`), updating live during active matchdays.
   */
  public async getSeasonDynamicTable(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutDynamicTableResponse | null> {
    return this.fetchFeed<BetScoutDynamicTableResponse>('season_dynamictable', String(seasonId), {
      channel: 'neutral',
      ttlSec: 120,
      ...options,
    });
  }

  /**
   * Query the league **Form Table** (`stats_formtable/{seasonId}`), returning recent match-by-match `W`/`D`/`L` arrays
   * (`form.total`, `form.home`, `form.away` with `matchid` and `homematch`) plus rolling 6-match goal/point splits.
   */
  public async getSeasonFormTable(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutFormTableResponse | null> {
    return this.fetchFeed<BetScoutFormTableResponse>('stats_formtable', String(seasonId), {
      channel: 'neutral',
      ttlSec: 900,
      ...options,
    });
  }

  /**
   * Query the head-to-head league table slice for a specific match (`stats_match_tableslice/{matchId}`).
   */
  public async getMatchTableSlice(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutLeagueTable | null> {
    return this.fetchFeed<BetScoutLeagueTable>('stats_match_tableslice', String(matchId), {
      channel: 'neutral',
      ttlSec: 900,
      ...options,
    });
  }

  /**
   * Build a complete **Enriched League Standings & Form Table Bundle** for a `seasonId` (e.g. `140782` Serie A):
   * - Merges `stats_season_tables/{seasonId}` (or `season_dynamictable/{seasonId}`) with `stats_formtable/{seasonId}` in parallel.
   * - Returns every team's `pos` (`total`/`home`/`away`), round-over-round position delta (`change_total`, `change_home`, `change_away`),
   *   promotion/relegation zone (`promotion`: `"Champions League"`, `"Relegation"`, etc.), Total/Home/Away W-D-L,
   *   `goals_for`, `goals_against`, `goal_diff`, `points`, and chronological recent form (`form_total: ['W', 'W', 'D', ...]`).
   * - Supports optional `aroundTeamUid` + `sliceSize` (e.g. `5` rows centered on `2692` AC Milan) matching the platform's team-page table slice.
   */
  public async getEnrichedLeagueTable(
    seasonId: number | string,
    options: {
      aroundTeamUid?: number | string;
      sliceSize?: number;
      requestOptions?: BetScoutRequestOptions;
    } = {},
  ): Promise<EnrichedLeagueTableBundle> {
    const [tablesResp, formResp] = await Promise.all([
      this.getSeasonTables(seasonId, undefined, undefined, options.requestOptions),
      this.getSeasonFormTable(seasonId, options.requestOptions),
    ]);

    const mainTable = tablesResp?.tables?.[0];
    if (!mainTable || !Array.isArray(mainTable.tablerows)) {
      return {
        ok: false,
        season_id: seasonId,
        season_name: tablesResp?.name ?? null,
        current_round: null,
        max_rounds: null,
        tiebreak_rules: null,
        rows: [],
      };
    }

    const formByTeamId = new Map<
      number,
      {
        total: BetScoutFormTableMatchItem[];
        home: BetScoutFormTableMatchItem[];
        away: BetScoutFormTableMatchItem[];
      }
    >();

    for (const ftEntry of formResp?.teams ?? []) {
      const tid = ftEntry.team?.uid ?? ftEntry.team?._id;
      if (!tid) continue;
      formByTeamId.set(Number(tid), {
        total: Array.isArray(ftEntry.form?.total) ? [...ftEntry.form.total].reverse() : [],
        home: Array.isArray(ftEntry.form?.home) ? [...ftEntry.form.home].reverse() : [],
        away: Array.isArray(ftEntry.form?.away) ? [...ftEntry.form.away].reverse() : [],
      });
    }

    let rawRows = [...mainTable.tablerows].sort((a, b) => (a.pos ?? 0) - (b.pos ?? 0));

    if (options.aroundTeamUid !== undefined) {
      const limit = options.sliceSize ?? 5;
      if (rawRows.length > limit) {
        const targetUid = Number(options.aroundTeamUid);
        const idx = rawRows.findIndex(
          (r) => Number(r.team?.uid ?? r.team?._id) === targetUid,
        );
        if (idx >= 0) {
          const half = Math.floor((limit - 1) / 2);
          const start = Math.max(0, Math.min(rawRows.length - limit, idx - half));
          rawRows = rawRows.slice(start, start + limit);
        }
      }
    }

    const enrichedRows: EnrichedStandingsRow[] = rawRows.map((row) => {
      const uid = Number(row.team?.uid ?? row.team?._id ?? 0);
      const fObj = formByTeamId.get(uid) ?? { total: [], home: [], away: [] };
      return {
        pos: Number(row.pos ?? 0),
        pos_home: row.posHome ?? null,
        pos_away: row.posAway ?? null,
        change_total: Number(row.changeTotal ?? 0),
        change_home: Number(row.changeHome ?? 0),
        change_away: Number(row.changeAway ?? 0),
        team_id: Number(row.team?._id ?? uid),
        team_uid: uid,
        team_name: String(row.team?.mediumname ?? row.team?.name ?? ''),
        team_abbr: String(row.team?.abbr ?? ''),
        promotion: row.promotion?.name ?? null,
        promotion_short: row.promotion?.shortname ?? null,
        played: {
          total: Number(row.total ?? 0),
          home: Number(row.home ?? 0),
          away: Number(row.away ?? 0),
        },
        win: {
          total: Number(row.winTotal ?? 0),
          home: Number(row.winHome ?? 0),
          away: Number(row.winAway ?? 0),
        },
        draw: {
          total: Number(row.drawTotal ?? 0),
          home: Number(row.drawHome ?? 0),
          away: Number(row.drawAway ?? 0),
        },
        loss: {
          total: Number(row.lossTotal ?? 0),
          home: Number(row.lossHome ?? 0),
          away: Number(row.lossAway ?? 0),
        },
        goals_for: {
          total: Number(row.goalsForTotal ?? 0),
          home: Number(row.goalsForHome ?? 0),
          away: Number(row.goalsForAway ?? 0),
        },
        goals_against: {
          total: Number(row.goalsAgainstTotal ?? 0),
          home: Number(row.goalsAgainstHome ?? 0),
          away: Number(row.goalsAgainstAway ?? 0),
        },
        goal_diff: {
          total: Number(row.goalDiffTotal ?? 0),
          home: Number(row.goalDiffHome ?? 0),
          away: Number(row.goalDiffAway ?? 0),
        },
        points: {
          total: Number(row.pointsTotal ?? 0),
          home: Number(row.pointsHome ?? 0),
          away: Number(row.pointsAway ?? 0),
        },
        form_total: fObj.total.map((x) => String(x.value ?? x.typeid)),
        form_home: fObj.home.map((x) => String(x.value ?? x.typeid)),
        form_away: fObj.away.map((x) => String(x.value ?? x.typeid)),
        form_entries_total: fObj.total,
      };
    });

    return {
      ok: true,
      season_id: seasonId,
      season_name: mainTable.name ?? tablesResp?.name ?? null,
      current_round: mainTable.currentround ?? formResp?.currentround ?? null,
      max_rounds: mainTable.maxrounds ?? null,
      tiebreak_rules: mainTable.rules?.name ?? null,
      rows: enrichedRows,
    };
  }

  /**
   * Query league-wide and per-team Over/Under (`0.5`..`5.5`) and Half-by-Half (`ft`, `p1`, `p2`)
   * goal distributions, clean sheet rates, and win rates (`stats_season_overunder/{seasonId}`).
   */
  public async getSeasonOverUnder(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonOverUnderResponse | null> {
    return this.fetchFeed<BetScoutSeasonOverUnderResponse>(
      'stats_season_overunder',
      String(seasonId),
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Query league-wide **Season Goal Timing, First-to-Score & Penalty Analytics** (`stats_season_goals/{seasonId}`):
   * returns every team's 15-minute goal buckets (`0-15'`..`76-90'`), `firstgoal` count (matches where team scored 1-0),
   * `lastgoal` count, `average_time_first_goal` (e.g. `36.25` min), and `penalty_success_count`.
   */
  public async getSeasonGoalsDistribution(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonGoalsResponse | null> {
    return this.fetchFeed<BetScoutSeasonGoalsResponse>('stats_season_goals', String(seasonId), {
      channel: 'neutral',
      ttlSec: 1800,
      ...options,
    });
  }

  /**
   * Query **Multi-Sport Team Pace, Efficiency & Shooting Splits** (`stats_season_uniqueteamstats/{seasonId}`):
   * for NBA / Basketball, NHL, and UEFA competitions, returns per-team `possessions_per_game`, `points_per_possession`,
   * `points_scored`, `opponent_points_per_game`, `two_points`, `three_points`, `free_throws_attempts`, `rebounds`,
   * `offensive_rebounds`, `defensive_rebounds`, `assists`, `steals`, `blocks`, and `turnovers`.
   */
  public async getSeasonUniqueTeamStats(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonUniqueTeamStatsResponse | null> {
    return this.fetchFeed<BetScoutSeasonUniqueTeamStatsResponse>(
      'stats_season_uniqueteamstats',
      String(seasonId),
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Query rich **Head-to-Head Versus Dossier** between two clubs (`stats_team_versus/{teamIdA}/{teamIdB}/{limit}`),
   * including past H2H `matches` (with goal-minute & scorer `comment`), `upcomingmatches`, `currentmanagers`, and `jersey` maps.
   */
  public async getTeamVersus(
    teamIdA: number | string,
    teamIdB: number | string,
    limit = 10,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamVersusResponse | null> {
    return this.fetchFeed<BetScoutTeamVersusResponse>(
      'stats_team_versus',
      `${teamIdA}/${teamIdB}/${limit}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Query **Tournament Overview, Defending Champion & Current Leader** (`uniquetournament_info/{uniqueTournamentId}`).
   */
  public async getUniqueTournamentInfo(
    uniqueTournamentId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutUniqueTournamentInfoResponse | null> {
    return this.fetchFeed<BetScoutUniqueTournamentInfoResponse>(
      'uniquetournament_info',
      String(uniqueTournamentId),
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Query **Historical Season Champions & Runners-Up** across all editions of a competition
   * (`uniquetournament_seasonswinners/{uniqueTournamentId}`).
   */
  public async getTournamentSeasonsWinners(
    uniqueTournamentId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTournamentSeasonsWinnersResponse | null> {
    return this.fetchFeed<BetScoutTournamentSeasonsWinnersResponse>(
      'uniquetournament_seasonswinners',
      String(uniqueTournamentId),
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Query **Season Metadata, Coverage Matrix & Bracket IDs** (`stats_season_meta/{seasonId}`).
   * Returns `statscoverage` flags, `tableids`, `cupids`, and knockout `brackets` IDs.
   */
  public async getSeasonMeta(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonMetaResponse | null> {
    return this.fetchFeed<BetScoutSeasonMetaResponse>('stats_season_meta', String(seasonId), {
      channel: 'neutral',
      ttlSec: 3600,
      ...options,
    });
  }

  /**
   * Query **Playoff / Knockout Cup Brackets** (`stats_cup_brackets/{bracketId}`),
   * returning elimination `roundsets`, `cup` metadata, and `stadiums`.
   */
  public async getCupBrackets(
    bracketId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutCupBracketsResponse | null> {
    return this.fetchFeed<BetScoutCupBracketsResponse>('stats_cup_brackets', String(bracketId), {
      channel: 'neutral',
      ttlSec: 1800,
      ...options,
    });
  }

  /**
   * Query the **Full League Referee Pool** for a season (`stats_season_referees/{seasonId}`).
   */
  public async getSeasonReferees(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonRefereesResponse | null> {
    return this.fetchFeed<BetScoutSeasonRefereesResponse>(
      'stats_season_referees',
      String(seasonId),
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Query the **Complete Historical Match Event Timeline** (`match_timeline/{matchId}`),
   * returning all chronological goals, cards, substitutions, period scores, and point-by-point events.
   */
  public async getMatchFullTimeline(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchTimelineResponse | null> {
    return this.fetchFeed<BetScoutMatchTimelineResponse>('match_timeline', String(matchId), {
      channel: 'neutral',
      ttlSec: 60,
      ...options,
    });
  }

  /** Query referee cards, fouls, and penalties per match (`referee_seasonstats/{refereeId}/{seasonId}`). */
  public async getRefereeSeasonStats(
    refereeId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutRefereeSeasonStatsResponse | null> {
    return this.fetchFeed<BetScoutRefereeSeasonStatsResponse>(
      'referee_seasonstats',
      `${refereeId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  // ==========================================================================
  // F. Visual Assets (Team Logos, Country Flags & Player Jersey SVG Avatars)
  // ==========================================================================

  /**
   * Build the direct tokenless PNG logo URL for any club/team ID (`small` | `medium` | `big` or NCAA `ap250x188ut` | `ap500x375ut` | `ap1000x750ut`).
   * Example: `client.getTeamLogoUrl(2692, { size: 'big' })` for AC Milan.
   */
  public getTeamLogoUrl(teamId: number | string, options: TeamLogoOptions = {}): string {
    return getTeamLogoUrl(teamId, options);
  }

  /**
   * Build the direct tokenless SVG (`4x3` | `1x1`) or PNG (`small` | `medium` | `big`) country/federation flag URL.
   * Example: `client.getCountryFlagUrl('rs', { format: 'svg', ratio: '4x3' })` for Serbia.
   */
  public getCountryFlagUrl(countryIso2: string, options: CountryFlagOptions = {}): string {
    return getCountryFlagUrl(countryIso2, options);
  }

  /**
   * Render a standalone vector SVG player kit avatar from a team's `homejersey` / `awayjersey` / `gkjersey` colors
   * and optional player `shirtNumber`.
   */
  public renderTeamJerseySvg(
    jersey: BetScoutJerseyColors | null | undefined,
    options: JerseySvgOptions = {},
  ): string {
    return renderTeamJerseySvg(jersey, options);
  }

  // ==========================================================================
  // G. Insights, Editorial Commentary, Venues & Team/Futures Markets
  // ==========================================================================

  /**
   * Fetch automated pre-match & in-play **Match Insights / Fun Facts** (`match_funfacts/{matchId}`).
   * Returns natural-language streaks and head-to-head insights (`funfacts[]` and `facts[]`).
   */
  public async getMatchInsights(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchFunFactsResponse | null> {
    return this.fetchFeed<BetScoutMatchFunFactsResponse>('match_funfacts', String(matchId), {
      channel: 'neutral',
      ttlSec: 300,
      ...options,
    });
  }

  /**
   * Fetch full natural-language **Editorial Match Commentary** (`match_phrases/{matchId}`).
   */
  public async getMatchCommentary(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchPhrasesResponse | null> {
    return this.fetchFeed<BetScoutMatchPhrasesResponse>('match_phrases', String(matchId), {
      channel: 'neutral',
      ttlSec: 30,
      ...options,
    });
  }

  /**
   * Fetch rolling delta updates of **Editorial Match Commentary** (`match_phrasesdelta/{matchId}`).
   */
  public async getMatchCommentaryDelta(
    matchId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutMatchPhrasesResponse | null> {
    return this.fetchFeed<BetScoutMatchPhrasesResponse>('match_phrasesdelta', String(matchId), {
      channel: 'neutral',
      ttlSec: 5,
      ...options,
    });
  }

  /**
   * Fetch macro **Season League Summary Insights** (`stats_season_leaguesummary/{seasonId}`):
   * home/draw/away win percentages, goals per match, Over/Under (`0.5`..`5.5`) hit rates, clean sheet %, and BTTS %.
   */
  public async getSeasonLeagueSummary(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonLeagueSummaryResponse | null> {
    return this.fetchFeed<BetScoutSeasonLeagueSummaryResponse>(
      'stats_season_leaguesummary',
      String(seasonId),
      { channel: 'neutral', ttlSec: 3600, ...options },
    );
  }

  /**
   * Fetch per-player season facts, **market values (`marketvalue`)**, shirt numbers, and full season statistics
   * for all players on a team in a season (`stats_teamplayer_facts/{teamId}/{seasonId}`).
   */
  public async getTeamPlayerSeasonFacts(
    teamId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutTeamPlayerFactsMap | null> {
    return this.fetchFeed<BetScoutTeamPlayerFactsMap>(
      'stats_teamplayer_facts',
      `${teamId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch all stadiums/venues for a league season (`stats_season_venues/{seasonId}`),
   * including capacity, construction year, address, pitch dimensions (`pitchsize`), and `googlecoords`.
   */
  public async getSeasonVenues(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonVenuesResponse | null> {
    return this.fetchFeed<BetScoutSeasonVenuesResponse>('stats_season_venues', String(seasonId), {
      channel: 'neutral',
      ttlSec: 3600,
      ...options,
    });
  }

  /**
   * Fetch detailed **Venue / Stadium Season Statistics** (`stats_season_venuestats/{stadiumId}/{seasonId}`),
   * including stadium metadata (`capacity`, `googlecoords`, `pitchsize`) and venue-specific home/away goals,
   * corner kicks, yellow cards, 15-minute goal buckets, and top stadium goalscorers (`venue_top_scorer`).
   */
  public async getVenueSeasonStats(
    stadiumId: number | string,
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutVenueStatsResponse | null> {
    return this.fetchFeed<BetScoutVenueStatsResponse>(
      'stats_season_venuestats',
      `${stadiumId}/${seasonId}`,
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /** Fetch league-wide top goalscorers for a season (`stats_season_topgoals/{seasonId}`). */
  public async getSeasonTopScorers(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonTopListResponse | null> {
    return this.fetchFeed<BetScoutSeasonTopListResponse>(
      'stats_season_topgoals',
      String(seasonId),
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /** Fetch league-wide top assist providers for a season (`stats_season_topassists/{seasonId}`). */
  public async getSeasonTopAssists(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonTopListResponse | null> {
    return this.fetchFeed<BetScoutSeasonTopListResponse>(
      'stats_season_topassists',
      String(seasonId),
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /** Fetch league-wide disciplinary / card leaders for a season (`stats_season_topcards/{seasonId}`). */
  public async getSeasonTopCards(
    seasonId: number | string,
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutSeasonTopListResponse | null> {
    return this.fetchFeed<BetScoutSeasonTopListResponse>(
      'stats_season_topcards',
      String(seasonId),
      { channel: 'neutral', ttlSec: 1800, ...options },
    );
  }

  /**
   * Fetch all active & upcoming bookmaker markets (`1x2`, totals, handicaps, outrights) for a specific team
   * (`uniqueteam_markets/{teamId}`), including implied probabilities (`probability`).
   */
  public async getTeamMarkets(
    teamId: number | string,
    channel: ProviderChannel = 'eu-retail',
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutUniqueTeamMarketsResponse | null> {
    return this.fetchFeed<BetScoutUniqueTeamMarketsResponse>(
      'uniqueteam_markets',
      String(teamId),
      { channel, ttlSec: 900, ...options },
    );
  }

  /**
   * Fetch the complete 328-entry Decimal <-> UK Fractional & US Moneyline odds conversion table (`odds_ukformat`).
   */
  public async getOddsFormatTable(
    options?: BetScoutRequestOptions,
  ): Promise<BetScoutOddsFormatEntry[] | null> {
    return this.fetchFeed<BetScoutOddsFormatEntry[]>('odds_ukformat', '', {
      channel: 'neutral',
      language: 'agnostic',
      ttlSec: 86400,
      ...options,
    });
  }

  // ==========================================================================
  // High-Level Composite Intelligence Workflows
  // ==========================================================================

  /**
   * Fetch and flatten the daily match index for `sportOrId` on `dateYmd`, excluding
   * Simulated Reality League (`SRL`) / eSoccer entries and ordering main-draw competitions
   * ahead of youth/amateur fixtures.
   */
  public async getDailyMatchIndex(
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
  ): Promise<DailyMatchIndexEntry[]> {
    const uData = await this.getDailySportMatches(sportOrId, dateYmd, 0);
    const flat: DailyMatchIndexEntry[] = [];
    const youthOrAmateur: DailyMatchIndexEntry[] = [];

    for (const rc of uData?.sport?.realcategories ?? []) {
      const rcName = String(rc.name ?? '');
      const rcLow = rcName.toLowerCase();
      if (rcLow.includes('simulated reality') || rcLow.includes('esoccer')) continue;

      for (const t of rc.tournaments ?? []) {
        const tLabel = [rcName, t.name ?? ''].filter(Boolean).join(' · ');
        const tLow = tLabel.toLowerCase();
        if (tLow.includes(' srl') || tLow.includes('simulated reality')) continue;
        const isSubTier = ['amateur', 'u19', 'u20', 'u21', 'u18', 'u17', 'youth', 'reserve'].some(
          (w) => tLow.includes(w),
        );

        for (const m of t.matches ?? []) {
          const hNm = String(m.teams?.home?.name ?? '');
          const aNm = String(m.teams?.away?.name ?? '');
          if (hNm.endsWith(' SRL') || aNm.endsWith(' SRL')) continue;
          const entry: DailyMatchIndexEntry = {
            match_obj: m,
            tournament: tLabel,
            home: hNm,
            away: aNm,
          };
          if (isSubTier) youthOrAmateur.push(entry);
          else flat.push(entry);
        }
      }
    }

    return [...flat, ...youthOrAmateur];
  }

  /**
   * Fetch the bulk daily markets map for both Primary Retail (`eu-retail`) and
   * Global Consensus (`global`) channels in parallel.
   */
  public async getDailyMarketsMap(
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
  ): Promise<{
    primary: NonNullable<BetScoutBatchMarketsResponse['matches']>;
    consensus: NonNullable<BetScoutBatchMarketsResponse['matches']>;
  }> {
    const [primResp, consResp] = await Promise.all([
      this.getDailySportMarkets(sportOrId, dateYmd, 'eu-retail', 0),
      this.getDailySportMarkets(sportOrId, dateYmd, 'global', 0),
    ]);
    return {
      primary: primResp?.matches ?? {},
      consensus: consResp?.matches ?? {},
    };
  }

  /**
   * Fast pre-match odds & totals lookup from the daily multi-bookmaker feed.
   * Automatically checks `dateYmd` and `dateYmd + 1 day` and handles flipped home/away ordering.
   */
  public async lookupDailyOdds(
    home: string,
    away: string,
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
  ): Promise<DailyOddsLookupResult> {
    const dateCandidates = [dateYmd, nextDayYmdUtc(dateYmd)];
    let matchedEntry: DailyMatchIndexEntry | null = null;
    let matchedYmd = dateYmd;
    let flipped = false;

    for (const dCand of dateCandidates) {
      const flat = await this.getDailyMatchIndex(sportOrId, dCand);
      for (const entry of flat) {
        if (namesMatch(home, entry.home) && namesMatch(away, entry.away)) {
          matchedEntry = entry;
          matchedYmd = dCand;
          flipped = false;
          break;
        }
        if (namesMatch(home, entry.away) && namesMatch(away, entry.home)) {
          matchedEntry = entry;
          matchedYmd = dCand;
          flipped = true;
          break;
        }
      }
      if (matchedEntry) break;
    }

    if (!matchedEntry) return {};
    const matchedM = matchedEntry.match_obj;
    const mid = String(matchedM._id ?? '');
    if (!mid) return {};

    const { primary, consensus } = await this.getDailyMarketsMap(sportOrId, matchedYmd);
    const primRaw = primary[mid]?.markets ?? [];
    const consRaw = consensus[mid]?.markets ?? [];
    const pPrim = parsePrematchMarkets(primRaw, flipped);
    const pCons = parsePrematchMarkets(consRaw, flipped);
    const merged = mergePrimaryAndConsensusMarkets(pPrim, pCons);

    const dtUts = matchedM._dt?.uts ?? 0;
    const hTeamM = flipped ? matchedM.teams?.away : matchedM.teams?.home;
    const aTeamM = flipped ? matchedM.teams?.home : matchedM.teams?.away;

    return {
      match_id: mid,
      start_utc: dtUts ? formatUtcIsoMinutes(dtUts) : null,
      start_uts: dtUts || null,
      home_uid: hTeamM?.uid ?? hTeamM?._id ?? null,
      away_uid: aTeamM?.uid ?? aTeamM?._id ?? null,
      odds_home: merged.odds_home,
      odds_draw: merged.odds_draw,
      odds_away: merged.odds_away,
      line_total: merged.total_line,
      odds_over: merged.odds_over,
      odds_under: merged.odds_under,
      correct_score_odds: merged.correct_score_odds,
      odds_provider:
        primRaw.length > 0 && consRaw.length > 0
          ? 'combined'
          : primRaw.length > 0
            ? 'eu_retail'
            : 'consensus',
    };
  }

  /**
   * Compute 15-minute goal scoring/conceding rates (`0-15'`..`76-90'`), 1st-half scoring %, and BTTS %.
   */
  public async fetchTeamGoalIntervals(
    seasonId: number | string,
    teamId: number | string,
    limit = 10,
  ): Promise<TeamGoalIntervalsSummary> {
    const data = await this.getTeamScoringConcedingSplits(seasonId, teamId, limit);
    const st = data?.stats;
    if (!st) return {};

    const sc = st.scoring ?? {};
    const co = st.conceding ?? {};
    const scMins = sc.goalsbyminutes ?? {};
    const coMins = co.goalsbyminutes ?? {};
    const buckets = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90'] as const;
    const intervals: Record<string, GoalIntervalBucketSummary> = {};

    for (const bucket of buckets) {
      const sV = Number(scMins[bucket]?.total ?? 0);
      const cV = Number(coMins[bucket]?.total ?? 0);
      intervals[bucket] = {
        scored_per_match: Number(sV.toFixed(3)),
        conceded_per_match: Number(cV.toFixed(3)),
        combined_per_match: Number((sV + cV).toFixed(3)),
      };
    }

    const fhScored = Number(sc.goalsscoredfirsthalfaverage?.total ?? 0);
    const fhConceded = Number(co.goalsconcededfirsthalfaverage?.total ?? 0);
    const htScoreRate = Number(sc.scoringathalftimeaverage?.total ?? 0);
    const bttsRate = Number(sc.bothteamsscoredaverage?.total ?? 0);
    const lateScored = intervals['76-90']?.scored_per_match ?? 0;
    const lateConceded = intervals['76-90']?.conceded_per_match ?? 0;

    return {
      matches_sampled: Number(st.totalmatches?.total ?? 0),
      first_half_scored_avg: Number(fhScored.toFixed(2)),
      first_half_conceded_avg: Number(fhConceded.toFixed(2)),
      scoring_in_1h_pct: Number((htScoreRate * 100).toFixed(1)),
      btts_pct: Number((bttsRate * 100).toFixed(1)),
      late_76_90_scored_avg: Number(lateScored.toFixed(2)),
      late_76_90_conceded_avg: Number(lateConceded.toFixed(2)),
      late_76_90_total_avg: Number((lateScored + lateConceded).toFixed(2)),
      intervals,
    };
  }

  /**
   * Compute live attack & dangerous-attack territorial pressure share for a match.
   */
  public async fetchLiveMatchSituationsPressure(
    matchId: number | string,
  ): Promise<LiveMatchSituationsPressure> {
    const data = await this.getMatchSituations(matchId);
    const sits = data?.situations;
    if (!Array.isArray(sits) || sits.length === 0) return {};

    const cnt = {
      home: { attack: 0, dangerous_attack: 0, safe: 0 },
      away: { attack: 0, dangerous_attack: 0, safe: 0 },
    };

    for (const s of sits) {
      const tm = s.team;
      const stType = s.situation;
      if ((tm === 'home' || tm === 'away') && stType && stType in cnt[tm]) {
        cnt[tm][stType as 'attack' | 'dangerous_attack' | 'safe'] += 1;
      }
    }

    const hDa = cnt.home.dangerous_attack;
    const aDa = cnt.away.dangerous_attack;
    const totDa = Math.max(1, hDa + aDa);

    return {
      home_attacks: cnt.home.attack,
      away_attacks: cnt.away.attack,
      home_dangerous_attacks: hDa,
      away_dangerous_attacks: aDa,
      home_danger_share_pct: Number(((hDa / totDa) * 100).toFixed(1)),
      away_danger_share_pct: Number(((aDa / totDa) * 100).toFixed(1)),
    };
  }

  /**
   * Evaluate pre-match squad injuries for a Football match, counting missing forwards (`FWD`/`F`)
   * and goalkeepers (`GK`/`G`) and computing a net win-probability adjustment & veto recommendation.
   */
  public async evaluateInjuryGate(
    seasonId: number | string | null | undefined,
    backedUid: number | string | null | undefined,
    oppUid: number | string | null | undefined,
  ): Promise<InjuryGateEvaluation> {
    if (!seasonId || !backedUid) {
      return {
        status: 'NO_SEASON_DATA',
        backed_out: [],
        opp_out: [],
        prob_adjustment: 0,
        veto_recommended: false,
      };
    }

    const injList = await this.getSeasonInjuries(seasonId);
    if (!Array.isArray(injList)) {
      return {
        status: 'NO_INJURY_FEED',
        backed_out: [],
        opp_out: [],
        prob_adjustment: 0,
        veto_recommended: false,
      };
    }

    const backedOut: string[] = [];
    const oppOut: string[] = [];
    let backedFwdOut = 0;
    let backedGkOut = 0;
    let oppFwdOut = 0;

    for (const item of injList) {
      const utId = item.uniqueteam?._id;
      if (utId !== Number(backedUid) && utId !== Number(oppUid)) continue;
      const pNm = item.player?.name ?? '';
      if (!pNm) continue;
      const posS = item.player?.position?.shortname ?? '';
      const stNm = item.status?.name ?? item.status?.status ?? 'Out';
      const entry = posS ? `${pNm} (${posS}, ${stNm})` : `${pNm} (${stNm})`;

      if (utId === Number(backedUid)) {
        backedOut.push(entry);
        if (posS === 'FWD' || posS === 'F') backedFwdOut += 1;
        else if (posS === 'GK' || posS === 'G') backedGkOut += 1;
      } else if (utId === Number(oppUid)) {
        oppOut.push(entry);
        if (posS === 'FWD' || posS === 'F') oppFwdOut += 1;
      }
    }

    const netOutDiff = backedOut.length - oppOut.length;
    let probAdj = 0;
    if (backedFwdOut >= 2 || netOutDiff >= 3) {
      probAdj -= Math.min(0.06, 0.015 * backedFwdOut + 0.008 * Math.max(0, netOutDiff));
    } else if (oppFwdOut >= 2 || netOutDiff <= -3) {
      probAdj += Math.min(0.04, 0.012 * oppFwdOut + 0.006 * Math.max(0, -netOutDiff));
    }

    const vetoRec = Boolean(
      backedFwdOut >= 3 || (backedFwdOut >= 2 && backedGkOut >= 1) || netOutDiff >= 5,
    );
    const status = vetoRec
      ? `ALERT_DEPLETED_SQUAD (${backedOut.length} Out, ${backedFwdOut} FWD)`
      : backedOut.length > 0 || oppOut.length > 0
        ? `TRACKED (${backedOut.length} Out vs ${oppOut.length} Opp)`
        : 'CLEAN_SQUAD';

    return {
      status,
      backed_out: backedOut.slice(0, 8),
      opp_out: oppOut.slice(0, 8),
      backed_fwd_out: backedFwdOut,
      backed_gk_out: backedGkOut,
      prob_adjustment: Number(probAdj.toFixed(4)),
      veto_recommended: vetoRec,
    };
  }

  /**
   * Resolve a match by `(home, away)` and stream its 3-second real-time timeline delta state
   * (live sets/goals, period scores `p1`..`p5`, tennis game points & server `🎾`, and final `H`/`A`/`D` outcome).
   */
  public async fetchLiveMatchTimelineDelta(
    home: string,
    away: string,
    sportOrId: string | number = 'tennis',
    dateYmd: string = todayYmdUtc(),
  ): Promise<LiveTimelineDeltaSummary> {
    const sportId = resolveSportId(sportOrId);
    const isSoccer = sportId === 1;
    const dateCandidates = [dateYmd, nextDayYmdUtc(dateYmd)];
    let matchedEntry: DailyMatchIndexEntry | null = null;
    let flipped = false;

    for (const dCand of dateCandidates) {
      const flat = await this.getDailyMatchIndex(sportOrId, dCand);
      for (const entry of flat) {
        if (namesMatch(home, entry.home) && namesMatch(away, entry.away)) {
          matchedEntry = entry;
          flipped = false;
          break;
        }
        if (namesMatch(home, entry.away) && namesMatch(away, entry.home)) {
          matchedEntry = entry;
          flipped = true;
          break;
        }
      }
      if (matchedEntry) break;
    }

    if (!matchedEntry) return {};
    const matchedM = matchedEntry.match_obj;
    const mid = matchedM._id;
    if (!mid) return {};

    const td = await this.getMatchTimelineDelta(mid);
    const m = td?.match ?? matchedM;
    const stObj = m.status;
    const stId = Number(stObj?._id ?? 0);
    const stName = String(stObj?.name ?? stObj?.shortName ?? 'LIVE');
    const dtUtsM = m._dt?.uts ?? matchedM._dt?.uts ?? 0;
    const startUtcM = dtUtsM ? formatUtcIsoMinutes(dtUtsM) : null;

    if (stId === 70) return {}; // Cancelled
    if (stId === 0 || stId === 60 || stId === 61) {
      return {
        match_id: mid,
        season_id: matchedM._seasonid ?? null,
        status_id: stId,
        state: 'pre',
        status_desc: stName,
        start_utc: startUtcM,
        outcome: null,
      };
    }

    const finishedCodes = new Set([91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 110, 111, 120]);
    const isFinished = finishedCodes.has(stId);
    const resObj = m.result;
    const rawH = flipped ? resObj?.away : resObj?.home;
    const rawA = flipped ? resObj?.home : resObj?.away;

    if (stId === 22 && rawH == null && rawA == null && !m.periods) {
      return {
        match_id: mid,
        season_id: matchedM._seasonid ?? null,
        status_id: stId,
        state: 'pre',
        status_desc: stName,
        start_utc: startUtcM,
        outcome: null,
      };
    }

    const hMain = rawH != null ? Number(rawH) : 0;
    const aMain = rawA != null ? Number(rawA) : 0;

    const periods = m.periods ?? {};
    const periodStrs: string[] = [];
    for (const pk of ['p1', 'p2', 'p3', 'p4', 'p5', 'ft', 'ap'] as const) {
      const pVal = periods[pk];
      if (pVal && pVal.home != null && pVal.away != null) {
        if ((pk === 'ft' || pk === 'ap') && isSoccer) continue;
        const ph = Number(flipped ? pVal.away : pVal.home);
        const pa = Number(flipped ? pVal.home : pVal.away);
        periodStrs.push(`${ph}-${pa}`);
      }
    }

    const gs = m.gamescore;
    let ptStr = '';
    if (!isFinished && gs && (gs.home != null || gs.away != null)) {
      const gH = flipped ? (gs.away ?? 0) : (gs.home ?? 0);
      const gA = flipped ? (gs.home ?? 0) : (gs.away ?? 0);
      const srv = String(gs.service ?? '');
      const srvH = (srv === '1' && !flipped) || (srv === '2' && flipped) ? '🎾' : '';
      const srvA = (srv === '2' && !flipped) || (srv === '1' && flipped) ? '🎾' : '';
      if (String(gH) !== '0' || String(gA) !== '0' || srvH || srvA) {
        ptStr = ` · Pt ${srvH}${gH}-${gA}${srvA}`;
      }
    }

    const scoreStr =
      periodStrs.length > 0
        ? `${hMain}-${aMain} (${periodStrs.join(', ')}${ptStr})`
        : !isFinished
          ? `${hMain}-${aMain} (${stName})`
          : `${hMain}-${aMain}`;

    let outcome: 'H' | 'A' | 'D' | null = null;
    if (isFinished) {
      const winRaw = resObj?.winner;
      if (winRaw === 'home') outcome = flipped ? 'A' : 'H';
      else if (winRaw === 'away') outcome = flipped ? 'H' : 'A';
      else if (hMain !== aMain) outcome = hMain > aMain ? 'H' : 'A';
      else if (isSoccer) outcome = 'D';
    }

    const hTeam = flipped ? matchedM.teams?.away : matchedM.teams?.home;
    const aTeam = flipped ? matchedM.teams?.home : matchedM.teams?.away;

    return {
      match_id: mid,
      season_id: matchedM._seasonid ?? null,
      status_id: stId,
      home_uid: hTeam?.uid ?? null,
      away_uid: aTeam?.uid ?? null,
      state: isFinished ? 'post' : 'in',
      status_desc: stName,
      score_str: scoreStr,
      home_score: hMain,
      away_score: aMain,
      periods: periodStrs,
      point_score: ptStr.replace(/^ · /, ''),
      outcome,
    };
  }

  /**
   * Full Match Intelligence Lookup:
   * Finds `(home, away)` on `dateYmd` (or `dateYmd + 1 day`), merges Primary Retail (`_bookmakerId: 176`)
   * and Global Consensus (`_bookmakerId: 0`) pre-match markets (including the 28-outcome Correct Score grid),
   * and enriches with league injuries, team streaks, 15-minute goal intervals, live dangerous attacks,
   * or ATP/WTA surface win-loss records.
   */
  public async lookupMatchIntel(
    home: string,
    away: string,
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
  ): Promise<MatchIntelligenceBundle> {
    const sportId = resolveSportId(sportOrId);
    const dateCandidates = [dateYmd, nextDayYmdUtc(dateYmd)];
    let matchedEntry: DailyMatchIndexEntry | null = null;
    let flipped = false;

    for (const dCand of dateCandidates) {
      const flat = await this.getDailyMatchIndex(sportOrId, dCand);
      for (const entry of flat) {
        if (namesMatch(home, entry.home) && namesMatch(away, entry.away)) {
          matchedEntry = entry;
          flipped = false;
          break;
        }
        if (namesMatch(home, entry.away) && namesMatch(away, entry.home)) {
          matchedEntry = entry;
          flipped = true;
          break;
        }
      }
      if (matchedEntry) break;
    }

    if (!matchedEntry) {
      return { ok: true, found: false };
    }

    const matchedM = matchedEntry.match_obj;
    const mid = matchedM._id;
    const seasonId = matchedM._seasonid ?? null;
    const hTeam = flipped ? matchedM.teams?.away : matchedM.teams?.home;
    const aTeam = flipped ? matchedM.teams?.home : matchedM.teams?.away;
    const hUid = hTeam?.uid ?? hTeam?._id ?? null;
    const aUid = aTeam?.uid ?? aTeam?._id ?? null;

    const [mmPrimary, mmConsensus] = await Promise.all([
      this.getMatchMarkets(mid, 'prematch', 'eu-retail'),
      this.getMatchMarkets(mid, 'prematch', 'global'),
    ]);

    const primaryParsed = parsePrematchMarkets(mmPrimary?.markets, flipped);
    const consensusParsed = parsePrematchMarkets(mmConsensus?.markets, flipped);
    const marketsParsed: ParsedPrematchMarkets = mergePrimaryAndConsensusMarkets(
      primaryParsed,
      consensusParsed,
    );

    const homeInjuries: string[] = [];
    const awayInjuries: string[] = [];
    const tennisSurfaceRecords: { home?: TennisSurfaceSummary; away?: TennisSurfaceSummary } = {};

    if (sportId === 1 && seasonId) {
      const injList = (await this.getSeasonInjuries(seasonId)) ?? [];
      for (const item of injList) {
        const utId = item.uniqueteam?._id;
        const pNm = item.player?.name ?? '';
        if (!pNm) continue;
        const posS = item.player?.position?.shortname ?? '';
        const stNm = item.status?.name ?? item.status?.status ?? 'Out';
        const entryS = posS ? `${pNm} (${posS}, ${stNm})` : `${pNm} (${stNm})`;
        if (hUid && utId === hUid && homeInjuries.length < 8) homeInjuries.push(entryS);
        else if (aUid && utId === aUid && awayInjuries.length < 8) awayInjuries.push(entryS);
      }
    } else if (sportId === 5) {
      for (const [sideLbl, pUid] of [
        ['home', hUid],
        ['away', aUid],
      ] as const) {
        if (!pUid) continue;
        const sData = await this.getTennisPlayerSurfaceStats(pUid);
        const singlesYr = sData?.singles?.['2026'] ?? sData?.singles?.['2025'];
        if (singlesYr) {
          const allRec = (singlesYr['0'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
          const clayRec = (singlesYr['1'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
          const hardRec = (singlesYr['2'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
          const indoorRec = (singlesYr['3'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
          const grassRec = (singlesYr['4'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
          tennisSurfaceRecords[sideLbl] = {
            season_wl: `${allRec.wins ?? 0}-${allRec.losses ?? 0}`,
            hard_wl: `${hardRec.wins ?? 0}-${hardRec.losses ?? 0}`,
            clay_wl: `${clayRec.wins ?? 0}-${clayRec.losses ?? 0}`,
            indoor_wl: `${indoorRec.wins ?? 0}-${indoorRec.losses ?? 0}`,
            grass_wl: `${grassRec.wins ?? 0}-${grassRec.losses ?? 0}`,
          };
        }
      }
    }

    const streaksSummary: { home: string[]; away: string[] } = { home: [], away: [] };
    let goalIntervals: { home?: TeamGoalIntervalsSummary; away?: TeamGoalIntervalsSummary } = {};
    let livePressure: LiveMatchSituationsPressure = {};
    let injuryGate: InjuryGateEvaluation | Record<string, never> = {};

    if (sportId !== 5) {
      for (const [sideLbl, tUid] of [
        ['home', hUid],
        ['away', aUid],
      ] as const) {
        if (!tUid) continue;
        const stData = await this.getTeamStreaks(tUid);
        const stDict = stData?.streaks ?? {};
        for (const [stType, scopeObj] of Object.entries(stDict)) {
          const totV = scopeObj?.total?.value ?? scopeObj?.[sideLbl]?.value;
          if (totV && Number(totV) >= 3) {
            streaksSummary[sideLbl].push(`${stType}: ${totV} matches`);
          }
        }
      }

      if (sportId === 1 && seasonId && hUid && aUid) {
        const [giHome, giAway, injEval] = await Promise.all([
          this.fetchTeamGoalIntervals(seasonId, hUid, 10),
          this.fetchTeamGoalIntervals(seasonId, aUid, 10),
          this.evaluateInjuryGate(seasonId, hUid, aUid),
        ]);
        goalIntervals = { home: giHome, away: giAway };
        injuryGate = injEval;
        const stCode = Number(matchedM.status?._id ?? 0);
        if (stCode > 0 && stCode < 90) {
          livePressure = await this.fetchLiveMatchSituationsPressure(mid);
        }
      }
    }

    return {
      ok: true,
      found: true,
      match_id: mid,
      season_id: seasonId,
      home_uid: hUid,
      away_uid: aUid,
      tournament: matchedEntry.tournament,
      primary_markets: marketsParsed,
      consensus_markets: consensusParsed,
      home_injuries: homeInjuries,
      away_injuries: awayInjuries,
      injury_gate: injuryGate,
      goal_intervals: goalIntervals,
      live_pressure: livePressure,
      streaks: streaksSummary,
      tennis_surface_records: tennisSurfaceRecords,
    };
  }

  /**
   * Fetch all missing, injured, ill, doubtful, and suspended players for a specific team (`teamId`).
   * - If `options.seasonId` is omitted, automatically resolves the team's current domestic league season (`s.current === true` in `uniqueteam_seasons/{teamId}`).
   * - Filters out already-expired absences (`status.end.uts < referenceUts`) when `options.activeOnly` is `true` (default: `true`).
   */
  public async getTeamMissingPlayers(
    teamId: number | string,
    options: {
      seasonId?: number | string;
      activeOnly?: boolean;
      referenceUts?: number;
      requestOptions?: BetScoutRequestOptions;
    } = {},
  ): Promise<TeamMissingPlayerEntry[]> {
    const activeOnly = options.activeOnly ?? true;
    const refUts = options.referenceUts ?? Math.floor(Date.now() / 1000);
    let targetSeasonId: number | string | null = options.seasonId ?? null;

    if (!targetSeasonId) {
      const seasonsData = await this.getTeamSeasons(teamId, options.requestOptions);
      const seasonsList = Array.isArray(seasonsData?.seasons) ? seasonsData.seasons : [];
      const currentSeason =
        seasonsList.find((s) => s.current && s.containsdata) ??
        seasonsList.find((s) => s.current) ??
        seasonsList[0];
      targetSeasonId = currentSeason?._id ?? null;
    }

    if (!targetSeasonId) return [];

    const injList =
      (await this.getSeasonInjuries(targetSeasonId, options.requestOptions)) ?? [];
    if (!Array.isArray(injList)) return [];

    const numTeamId = Number(teamId);
    const out: TeamMissingPlayerEntry[] = [];

    for (const item of injList) {
      if (item.uniqueteam?._id !== numTeamId) continue;
      const p = item.player;
      const st = item.status;
      if (!p?.name || !st) continue;

      const startUts = typeof st.start?.uts === 'number' ? st.start.uts : null;
      const endUts = typeof st.end?.uts === 'number' ? st.end.uts : null;
      const isActive = endUts === null || endUts >= refUts;
      if (activeOnly && !isActive) continue;

      out.push({
        player_id: Number(p._id ?? item._playerid ?? 0),
        name: String(p.name),
        position: String(p.position?.shortname ?? p.position?.abbr ?? ''),
        shirt_number: p.shirtnumber ?? null,
        cause: String(st.name ?? 'Out'),
        status: String(st.status ?? 'Missing'),
        status_id: Number(st._id ?? 0),
        start_date: st.start?.date ?? null,
        end_date: st.end?.date ?? null,
        start_uts: startUts,
        end_uts: endUts,
        is_active: isActive,
      });
    }

    return out;
  }

  /**
   * Build a complete **Club / Team Historical & Season Intelligence Bundle** for any `teamId` (e.g. `2692` AC Milan):
   * - Club profile (`founded`, `stadium`, `manager`, `homejersey`, `awayjersey`, `tournaments`)
   * - All historical & active seasons (`uniqueteam_seasons`)
   * - Per-game season team statistics (`goal_attempts`, `shots_on_goal`, `ball_possession`, `corner_kicks`, etc.)
   * - Home/Away/Total scoring & conceding splits + 15-minute goal intervals
   * - Preferred tactical formation (`formation`, e.g. `"3-5-2"`) & usual starting XI
   * - Active 40+ player squad roster & currently **missing/injured/suspended players (`missing_players`)**
   * - Active streaks, upcoming match difficulty ratings, last $N$ completed matches, and next $N$ scheduled fixtures.
   */
  public async getTeamIntelligenceBundle(
    teamId: number | string,
    options: {
      seasonId?: number | string;
      injurySeasonId?: number | string;
      lastMatchesLimit?: number;
      nextMatchesLimit?: number;
    } = {},
  ): Promise<TeamIntelligenceBundle> {
    const lastLimit = options.lastMatchesLimit ?? 15;
    const nextLimit = options.nextMatchesLimit ?? 10;

    const [profile, seasonsData, streaksData, lastMatchesData, nextMatchesData, squadData] =
      await Promise.all([
        this.getTeamProfile(teamId),
        this.getTeamSeasons(teamId),
        this.getTeamStreaks(teamId),
        this.getTeamLastMatches(teamId, lastLimit),
        this.getTeamNextMatches(teamId, nextLimit),
        this.getTeamSquad(teamId),
      ]);

    const seasonsList: BetScoutSeasonDescriptor[] = Array.isArray(seasonsData?.seasons)
      ? seasonsData.seasons
      : [];

    let activeSeasonId: string | number | null = options.seasonId ?? null;
    if (!activeSeasonId && lastMatchesData?.matches?.length) {
      activeSeasonId = lastMatchesData.matches[0]?._seasonid ?? null;
    }
    if (!activeSeasonId && seasonsList.length > 0) {
      const currentWithData =
        seasonsList.find((s) => s.containsdata && s.year === '25/26') ??
        seasonsList.find((s) => s.containsdata) ??
        seasonsList[0];
      activeSeasonId = currentWithData?._id ?? null;
    }

    const currentInjurySeasonId =
      options.injurySeasonId ??
      seasonsList.find((s) => s.current && s.containsdata)?._id ??
      seasonsList.find((s) => s.current)?._id ??
      activeSeasonId;

    let seasonStats: Record<string, string | number> | null = null;
    let scoringSplits: BetScoutTeamScoringConcedingResponse | null = null;
    let goalIntervals: TeamGoalIntervalsSummary = {};
    let usualLineup: BetScoutTeamUsualLineupResponse | null = null;
    let missingPlayers: TeamMissingPlayerEntry[] = [];

    if (activeSeasonId) {
      const [sStats, sSplits, gIntervals, uLineup, mPlayers] = await Promise.all([
        this.getTeamSeasonStats(teamId, activeSeasonId),
        this.getTeamScoringConcedingSplits(activeSeasonId, teamId, 10),
        this.fetchTeamGoalIntervals(activeSeasonId, teamId, 10),
        this.getTeamUsualLineup(teamId, activeSeasonId),
        currentInjurySeasonId
          ? this.getTeamMissingPlayers(teamId, { seasonId: currentInjurySeasonId })
          : Promise.resolve([]),
      ]);
      seasonStats = sStats?.stats ?? null;
      scoringSplits = sSplits;
      goalIntervals = gIntervals;
      usualLineup = uLineup;
      missingPlayers = mPlayers;
    }

    const streakLabels: string[] = [];
    for (const [stType, scopeObj] of Object.entries(streaksData?.streaks ?? {})) {
      const totV = scopeObj?.total?.value;
      if (totV && Number(totV) >= 2) {
        streakLabels.push(`${stType}: ${totV}`);
      }
    }

    const squadPlayers = squadData?.players ?? [];

    return {
      ok: Boolean(profile || lastMatchesData),
      team_id: Number(teamId),
      profile,
      seasons: seasonsList,
      active_season_id: activeSeasonId,
      season_stats: seasonStats,
      scoring_conceding_splits: scoringSplits,
      goal_intervals: goalIntervals,
      usual_lineup: usualLineup,
      squad_count: squadPlayers.length,
      squad: squadPlayers,
      missing_players: missingPlayers,
      streaks: streakLabels,
      next_matches_difficulty: streaksData?.nextmatches ?? [],
      last_matches: lastMatchesData?.matches ?? [],
      next_matches: nextMatchesData?.matches ?? [],
    };
  }

  /**
   * Build a complete **Tennis Player Career & Surface Intelligence Bundle** for any `playerId` (e.g. `14882` Novak Djokovic):
   * - Biographical & career profile (`dateofbirth`, `turnedpro`, `height`, `weight`, `plays`, `coachname`, `favouritesurface`, `singlesrank`, `highestranking`, `groundstats`, `ranking`, `performance`)
   * - Multi-season (`2004`–`2026`) singles/doubles/mixed surface win-loss matrices (`All`, `Clay`, `Hard Outdoor`, `Indoor`, `Grass`)
   * - Current season surface summary
   * - Active streaks, last $N$ completed matches with set scores, and next $N$ scheduled matches.
   */
  public async getTennisPlayerIntelligenceBundle(
    playerId: number | string,
    options: { lastMatchesLimit?: number; nextMatchesLimit?: number } = {},
  ): Promise<TennisPlayerIntelligenceBundle> {
    const lastLimit = options.lastMatchesLimit ?? 15;
    const nextLimit = options.nextMatchesLimit ?? 5;

    const [profile, surfaceStats, streaksData, lastMatchesData, nextMatchesData] =
      await Promise.all([
        this.getTeamProfile(playerId),
        this.getTennisPlayerSurfaceStats(playerId),
        this.getTeamStreaks(playerId),
        this.getTeamLastMatchesExtended(playerId, lastLimit),
        this.getTeamNextMatches(playerId, nextLimit),
      ]);

    const singlesYr = surfaceStats?.singles?.['2026'] ?? surfaceStats?.singles?.['2025'] ?? {};
    const allRec = (singlesYr['0'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
    const clayRec = (singlesYr['1'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
    const hardRec = (singlesYr['2'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
    const indoorRec = (singlesYr['3'] as BetScoutTennisSurfaceRecord | undefined) ?? {};
    const grassRec = (singlesYr['4'] as BetScoutTennisSurfaceRecord | undefined) ?? {};

    const streakLabels: string[] = [];
    for (const [stType, scopeObj] of Object.entries(streaksData?.streaks ?? {})) {
      const totV = scopeObj?.total?.value;
      if (totV && Number(totV) >= 2) {
        streakLabels.push(`${stType}: ${totV}`);
      }
    }

    return {
      ok: Boolean(profile || surfaceStats),
      player_id: Number(playerId),
      profile,
      current_surface_summary: {
        season_wl: `${allRec.wins ?? 0}-${allRec.losses ?? 0}`,
        hard_wl: `${hardRec.wins ?? 0}-${hardRec.losses ?? 0}`,
        clay_wl: `${clayRec.wins ?? 0}-${clayRec.losses ?? 0}`,
        indoor_wl: `${indoorRec.wins ?? 0}-${indoorRec.losses ?? 0}`,
        grass_wl: `${grassRec.wins ?? 0}-${grassRec.losses ?? 0}`,
      },
      career_surface_stats: surfaceStats,
      streaks: streakLabels,
      last_matches: lastMatchesData?.matches ?? [],
      next_matches: nextMatchesData?.matches ?? [],
    };
  }

  /**
   * Build a complete **Match Center Dossier** (`getMatchCenterDossier(matchId)`) replicating every widget
   * on a full match page (such as `76034538` Taylor Fritz vs Rinky Hijikata or `71945344` Udinese vs AC Milan):
   * - Live scoreboard, set/period breakdown, game points & active server (`match_info_statshub` + `match_timelinedelta`)
   * - Full & set-by-set match statistics (`match_detailsextended` + `stats_match_stats`)
   * - Win probability & bookmaker odds (`match_markets` Primary Retail + Global Consensus)
   * - Competitor profiles, rankings, coach/bio info, and surface win-rate matrices (`stats_team_info` + `tennis_team_surfacestats`)
   * - Pre-match form, streaks, direct H2H meetings, last $N$ matches, and next $N$ matches for both competitors
   * - Point-by-point / play-by-play timeline (`match_timeline`), insights (`match_funfacts`), commentary (`match_phrases`), squads, and table slice.
   */
  public async getMatchCenterDossier(
    matchId: number | string,
    options: { lastMatchesLimit?: number } = {},
  ): Promise<MatchCenterDossier> {
    const lastLimit = options.lastMatchesLimit ?? 10;

    const [
      matchInfo,
      timelineDelta,
      fullTimeline,
      matchDetails,
      matchStats,
      matchForm,
      head2head,
      mmPrimary,
      mmConsensus,
      funFactsResp,
      phrasesResp,
      squads,
      tableSlice,
    ] = await Promise.all([
      this.getMatchInfo(matchId),
      this.getMatchTimelineDelta(matchId),
      this.getMatchFullTimeline(matchId),
      this.getMatchDetailsExtended(matchId),
      this.getMatchStats(matchId),
      this.getMatchForm(matchId),
      this.getMatchHead2Head(matchId),
      this.getMatchMarkets(matchId, 'prematch', 'eu-retail'),
      this.getMatchMarkets(matchId, 'prematch', 'global'),
      this.getMatchInsights(matchId),
      this.getMatchCommentary(matchId),
      this.getMatchSquads(matchId),
      this.getMatchTableSlice(matchId),
    ]);

    const m = timelineDelta?.match ?? matchInfo?.match;
    const sportId = Number(m?._sid ?? matchInfo?.match?._sid ?? 1);
    const sportName = SPORTS_CATALOG[sportId] ?? `Sport #${sportId}`;

    const hTeam = matchInfo?.match?.teams?.home ?? m?.teams?.home;
    const aTeam = matchInfo?.match?.teams?.away ?? m?.teams?.away;
    const hUid = hTeam?.uid ?? hTeam?._id ?? null;
    const aUid = aTeam?.uid ?? aTeam?._id ?? null;

    const [
      versus,
      homeProfile,
      awayProfile,
      homeSurface,
      awaySurface,
      homeStreaks,
      awayStreaks,
      homeLast,
      awayLast,
      homeNext,
      awayNext,
    ] = await Promise.all([
      hUid && aUid ? this.getTeamVersus(hUid, aUid, 10) : Promise.resolve(null),
      hUid ? this.getTeamProfile(hUid) : Promise.resolve(null),
      aUid ? this.getTeamProfile(aUid) : Promise.resolve(null),
      sportId === 5 && hUid ? this.getTennisPlayerSurfaceStats(hUid) : Promise.resolve(null),
      sportId === 5 && aUid ? this.getTennisPlayerSurfaceStats(aUid) : Promise.resolve(null),
      hUid ? this.getTeamStreaks(hUid) : Promise.resolve(null),
      aUid ? this.getTeamStreaks(aUid) : Promise.resolve(null),
      hUid ? this.getTeamLastMatchesExtended(hUid, lastLimit) : Promise.resolve(null),
      aUid ? this.getTeamLastMatchesExtended(aUid, lastLimit) : Promise.resolve(null),
      hUid ? this.getTeamNextMatches(hUid, 3) : Promise.resolve(null),
      aUid ? this.getTeamNextMatches(aUid, 3) : Promise.resolve(null),
    ]);

    const primaryParsed = parsePrematchMarkets(mmPrimary?.markets, false);
    const consensusParsed = parsePrematchMarkets(mmConsensus?.markets, false);
    const mergedMarkets = mergePrimaryAndConsensusMarkets(primaryParsed, consensusParsed);
    const rawMarkets =
      (mmConsensus?.markets?.length ? mmConsensus.markets : mmPrimary?.markets) ?? [];

    const homeLastList = homeLast?.matches ?? [];
    const awayLastList = awayLast?.matches ?? [];
    const homeFormWdl = computeFormWdlSegments(homeLastList, hUid, 5);
    const awayFormWdl = computeFormWdlSegments(awayLastList, aUid, 5);
    const h2hEdge = computeH2HEdgeSummary(versus?.matches, hUid, aUid);

    return {
      ok: Boolean(matchInfo || timelineDelta),
      match_id: Number(matchId),
      sport_id: sportId,
      sport_name: sportName,
      match_info: matchInfo,
      timeline_delta: timelineDelta,
      full_timeline: fullTimeline,
      match_details: matchDetails,
      match_stats: matchStats,
      match_form: matchForm,
      head2head,
      versus,
      primary_markets: primaryParsed,
      consensus_markets: consensusParsed,
      merged_markets: mergedMarkets,
      raw_markets: rawMarkets,
      home_profile: homeProfile,
      away_profile: awayProfile,
      home_surface_stats: homeSurface,
      away_surface_stats: awaySurface,
      home_streaks: homeStreaks,
      away_streaks: awayStreaks,
      home_last_matches: homeLastList,
      away_last_matches: awayLastList,
      home_next_matches: homeNext?.matches ?? [],
      away_next_matches: awayNext?.matches ?? [],
      fun_facts: funFactsResp?.funfacts ?? [],
      commentary_phrases: phrasesResp?.phrases ?? [],
      squads,
      table_slice: tableSlice,
      form_wdl: {
        home: homeFormWdl.segments,
        away: awayFormWdl.segments,
        home_form_pct: homeFormWdl.formPct,
        away_form_pct: awayFormWdl.formPct,
      },
      h2h_edge: h2hEdge,
    };
  }

  /**
   * Build the official Insights Push Stream URL (`https://api.sportradar.com/insights/production/stream/{league}/{provider}/subscribe?...`).
   */
  public buildInsightsPushUrl(options: InsightsPushStreamOptions = {}): string {
    const league = options.league ?? 'nba';
    const provider = options.provider ?? 'sportradar';
    const params = new URLSearchParams();
    if (options.insightType) params.set('insight_type', options.insightType);
    if (options.subjectType) params.set('subject_type', options.subjectType);
    if (options.gameId !== undefined) params.set('game_id', String(options.gameId));
    if (options.teamId !== undefined) params.set('team_id', String(options.teamId));
    if (options.playerId !== undefined) params.set('player_id', String(options.playerId));
    const qs = params.toString();
    return `https://api.sportradar.com/insights/production/stream/${league}/${provider}/subscribe${qs ? `?${qs}` : ''}`;
  }

  /**
   * Dual-Mode **Real-Time Insights & Live Delta Stream** (`streamInsights(options)`):
   * - **Commercial Push Mode (`options.apiKey` provided):** Opens a persistent chunked HTTP stream to
   *   `https://api.sportradar.com/insights/production/stream/{league}/{provider}/subscribe` with `x-api-key`,
   *   yielding real-time `scoring`, `milestones`, `player_betting_trends`, `lineup_changes`, and 5s `heartbeat` frames.
   * - **Tokenless Adaptive Delta Mode (`options.apiKey` omitted):** Automatically streams tokenless live deltas
   *   via `match_timelinedelta/{gameId}` (`_maxage: 3`), `match_phrasesdelta/{gameId}` (`_maxage: 5`),
   *   `match_funfacts/{gameId}`, and `event_get/{sportId}` (`_maxage: 10`), deduplicating events by ID.
   */
  public async *streamInsights(
    options: InsightsPushStreamOptions = {},
  ): AsyncGenerator<InsightsStreamEvent, void, unknown> {
    if (options.apiKey) {
      const url = this.buildInsightsPushUrl(options);
      const resp = await this.fetchFn(url, {
        headers: {
          'x-api-key': options.apiKey,
          Accept: 'application/json',
        },
        signal: options.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`Insights Push Stream HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (!options.signal?.aborted) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const parsed = JSON.parse(trimmed) as Record<string, unknown>;
            const isHeartbeat = 'heartbeat' in parsed || parsed.type === 'heartbeat';
            yield {
              mode: 'push_stream',
              event_type: isHeartbeat ? 'heartbeat' : 'raw_insight',
              timestamp_utc: new Date().toISOString(),
              match_id: (parsed.subject_id as string | undefined) ?? options.gameId ?? null,
              summary: (parsed.text as string | undefined) ?? null,
              payload: parsed,
            };
          } catch {
            // Partial JSON chunk
          }
        }
      }
      return;
    }

    // Tokenless Adaptive Delta Stream Mode
    const seenIds = new Set<string>();
    const numericMatchId =
      options.gameId !== undefined
        ? String(options.gameId).replace(/^sr:match:/i, '')
        : null;
    const sportId = resolveSportId(options.sportOrId ?? options.league ?? 'soccer');

    while (!options.signal?.aborted) {
      let sleepMs = 5000;

      if (numericMatchId) {
        const [deltaDoc, phrasesDelta, funFacts] = await Promise.all([
          this.fetchDocument('match_timelinedelta', numericMatchId, {
            channel: 'global',
            bypassCache: true,
          }),
          this.getMatchCommentaryDelta(numericMatchId, { bypassCache: true }),
          seenIds.size === 0 ? this.getMatchInsights(numericMatchId) : Promise.resolve(null),
        ]);

        sleepMs = getAdaptiveRefetchIntervalMs(deltaDoc);

        for (const fact of funFacts?.funfacts ?? []) {
          const fid = `fact:${fact}`;
          if (!seenIds.has(fid)) {
            seenIds.add(fid);
            yield {
              mode: 'tokenless_delta',
              event_type: 'funfact',
              timestamp_utc: new Date().toISOString(),
              match_id: numericMatchId,
              summary: fact,
              payload: { sentence: fact },
            };
          }
        }

        const deltaData = deltaDoc?.data as { events?: Array<Record<string, unknown>> } | undefined;
        for (const ev of deltaData?.events ?? []) {
          const eid = `ev:${ev._id ?? ev.uts ?? JSON.stringify(ev)}`;
          if (!seenIds.has(eid)) {
            seenIds.add(eid);
            yield {
              mode: 'tokenless_delta',
              event_type: 'scoring',
              timestamp_utc: new Date().toISOString(),
              match_id: numericMatchId,
              summary: String(ev.name ?? ev.type ?? 'score_change'),
              payload: ev,
            };
          }
        }

        for (const ph of phrasesDelta?.phrases ?? []) {
          const pid = `ph:${ph._id}`;
          if (!seenIds.has(pid)) {
            seenIds.add(pid);
            yield {
              mode: 'tokenless_delta',
              event_type: 'commentary',
              timestamp_utc: new Date().toISOString(),
              match_id: numericMatchId,
              summary: ph.text,
              payload: ph,
            };
          }
        }
      } else {
        const evDoc = await this.fetchDocument('event_get', String(sportId), {
          channel: 'global',
          bypassCache: true,
        });
        sleepMs = getAdaptiveRefetchIntervalMs(evDoc);
        const evData = evDoc?.data as { events?: Array<Record<string, unknown>> } | undefined;
        for (const ev of (evData?.events ?? []).slice(0, 15)) {
          const eid = `sp:${ev._id ?? ev.uts}`;
          if (!seenIds.has(eid)) {
            seenIds.add(eid);
            yield {
              mode: 'tokenless_delta',
              event_type: 'sport_event',
              timestamp_utc: new Date().toISOString(),
              match_id: (ev.matchid as number | undefined) ?? null,
              summary: String(ev.type ?? 'live_event'),
              payload: ev,
            };
          }
        }
      }

      yield {
        mode: 'tokenless_delta',
        event_type: 'heartbeat',
        timestamp_utc: new Date().toISOString(),
        match_id: numericMatchId,
        summary: `Heartbeat (next poll in ${sleepMs}ms)`,
        payload: { nextPollMs: sleepMs },
      };

      await new Promise((resolve) => setTimeout(resolve, sleepMs));
    }
  }
}
