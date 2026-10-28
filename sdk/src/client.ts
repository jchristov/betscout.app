/**
 * Sportradar StatsHub & Tipico Gismo Client (`SportradarGismoClient`).
 * Implements all 27 Gismo endpoints and high-level match intelligence workflows documented in `docs/SPORTRADAR_STATSHUB.md`.
 */

import {
  DIRECT_STATS_FN_BASE_URL,
  FISHNET_BASE_URL,
  SR_ALL_SPORTS_CATALOG,
  STATSHUB_TIPICO_URL,
  resolveSportId,
} from './constants.js';
import type {
  DailyMatchIndexEntry,
  DailyOddsLookupResult,
  GismoCategoryTreeMini,
  GismoClientAlias,
  GismoDocument,
  GismoEnvelope,
  GismoEventGetResponse,
  GismoLanguage,
  GismoMatchFormResponse,
  GismoMatchHead2HeadResponse,
  GismoMatchInfoStatshubResponse,
  GismoMatchMarketsResponse,
  GismoMatchSituationsResponse,
  GismoMatchSquadsResponse,
  GismoMatchStatsResponse,
  GismoMatchTimelineDeltaResponse,
  GismoRefereeSeasonStatsResponse,
  GismoRequestOptions,
  GismoSeasonInjuryItem,
  GismoSeasonMarketsResponse,
  GismoSeasonOverUnderResponse,
  GismoSeasonTablesResponse,
  GismoSportConfigItem,
  GismoTeamLastXResponse,
  GismoTeamScoringConcedingResponse,
  GismoTeamStreaksResponse,
  GismoTennisCalendarResponse,
  GismoTennisRankingResponse,
  GismoTennisSurfaceStatsResponse,
  GismoTimezone,
  GismoUnifiedMarketsResponse,
  GismoUnifiedSportMatchesResponse,
  GismoUniqueTournament,
  GoalIntervalBucketSummary,
  LiveMatchSituationsPressure,
  LiveTimelineDeltaSummary,
  ParsedPrematchMarkets,
  SportCatalogItem,
  SportradarGismoClientOptions,
  SportradarInjuryGateEvaluation,
  StatshubMatchIntelResult,
  TeamGoalIntervalsSummary,
  TennisSurfaceSummary,
} from './types.js';
import { mergeTipicoAndUofMarkets, namesMatch, parsePrematchMarkets } from './utils.js';

interface CacheEntry<T = unknown> {
  expiresAtMs: number;
  value: T;
  doc?: GismoDocument<T>;
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

export class SportradarGismoClient {
  private readonly baseUrl: string;
  private readonly fallbackBaseUrl: string;
  private readonly defaultClientAlias: GismoClientAlias;
  private readonly defaultLanguage: GismoLanguage;
  private readonly defaultTimezone: GismoTimezone;
  private readonly defaultTtlSec: number;
  private readonly timeoutMs: number;
  private readonly fetchFn: typeof fetch;
  private readonly cache = new Map<string, CacheEntry<any>>();
  private tokenCache: { token: string | null; fetchedAtMs: number } = {
    token: null,
    fetchedAtMs: 0,
  };

  constructor(options: SportradarGismoClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? DIRECT_STATS_FN_BASE_URL).replace(/\/+$/, '');
    this.fallbackBaseUrl = (options.fallbackBaseUrl ?? FISHNET_BASE_URL).replace(/\/+$/, '');
    this.defaultClientAlias = options.defaultClientAlias ?? 'tipico';
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

  /** Clear all cached Gismo responses and tokens. */
  public clearCache(): void {
    this.cache.clear();
    this.tokenCache = { token: null, fetchedAtMs: 0 };
  }

  /**
   * Build the relative Gismo path `{clientAlias}/{language}/{timezone}/gismo/{endpoint}/{paramsPath}`.
   */
  public buildRelativePath(
    endpoint: string,
    paramsPath = '',
    options: GismoRequestOptions = {},
  ): string {
    const clientAlias = options.clientAlias ?? this.defaultClientAlias;
    const language = options.language ?? this.defaultLanguage;
    const timezone = options.timezone ?? this.defaultTimezone;
    const cleanEndpoint = endpoint.replace(/^\/+|\/+$/g, '');
    const cleanParams = paramsPath.replace(/^\/+|\/+$/g, '');
    return cleanParams
      ? `${clientAlias}/${language}/${timezone}/gismo/${cleanEndpoint}/${cleanParams}`
      : `${clientAlias}/${language}/${timezone}/gismo/${cleanEndpoint}`;
  }

  /**
   * Extract the signed `fishnetToken` (`exp=...~acl=/*~hmac=...`) from `https://statshub.sportradar.com/tipico/en/`
   * when needed for the fallback `sh.fn.sportradar.com` cluster.
   */
  public async getStatshubToken(forceRefresh = false): Promise<string | null> {
    const now = Date.now();
    if (!forceRefresh && this.tokenCache.token && now - this.tokenCache.fetchedAtMs < 3600_000) {
      return this.tokenCache.token;
    }
    try {
      const resp = await this.fetchWithTimeout(STATSHUB_TIPICO_URL, {
        headers: { 'User-Agent': DEFAULT_HEADERS['User-Agent'] },
      });
      if (!resp.ok) return null;
      const html = await resp.text();
      const match = html.match(/(exp=\d+~acl=[^"\\]+~hmac=[a-fA-F0-9]+)/);
      if (match?.[1]) {
        this.tokenCache = { token: match[1], fetchedAtMs: now };
        return match[1];
      }
    } catch {
      return null;
    }
    return null;
  }

  /**
   * Low-level Gismo query returning the full `GismoDocument<T>` (`{ event, _dob, _maxage, data }`).
   * Queries the direct tokenless `stats.fn.sportradar.com` endpoint first and automatically falls back
   * to `sh.fn.sportradar.com?T={token}` if needed.
   */
  public async fetchGismoDocument<T = unknown>(
    endpoint: string,
    paramsPath = '',
    options: GismoRequestOptions = {},
  ): Promise<GismoDocument<T> | null> {
    const clientAlias = options.clientAlias ?? this.defaultClientAlias;
    const ttlSec = options.ttlSec ?? this.defaultTtlSec;
    const cacheKey = `${clientAlias}:${endpoint}:${paramsPath}`;
    const now = Date.now();

    if (!options.bypassCache && ttlSec > 0) {
      const hit = this.cache.get(cacheKey);
      if (hit && hit.expiresAtMs > now && hit.doc) {
        return hit.doc as GismoDocument<T>;
      }
    }

    const relPath = this.buildRelativePath(endpoint, paramsPath, options);
    const directUrl = `${this.baseUrl}/${relPath}`;

    // 1. Primary path: Direct tokenless JSON API via stats.fn.sportradar.com
    try {
      const resp = await this.fetchWithTimeout(directUrl, { headers: DEFAULT_HEADERS });
      if (resp.ok) {
        const payload = (await resp.json()) as GismoEnvelope<T>;
        const doc0 = payload?.doc?.[0];
        if (doc0 && typeof doc0 === 'object' && doc0.event !== 'exception') {
          this.cache.set(cacheKey, {
            expiresAtMs: now + ttlSec * 1000,
            value: doc0.data,
            doc: doc0,
          });
          return doc0;
        }
      }
    } catch {
      // Fall through to token-gated Fishnet fallback
    }

    // 2. Fallback: sh.fn.sportradar.com with token
    const tok = await this.getStatshubToken();
    if (!tok) return null;
    const fallbackUrl = `${this.fallbackBaseUrl}/${relPath}?T=${tok}`;
    try {
      const resp = await this.fetchWithTimeout(fallbackUrl, { headers: DEFAULT_HEADERS });
      if (resp.ok) {
        const payload = (await resp.json()) as GismoEnvelope<T>;
        const doc0 = payload?.doc?.[0];
        if (doc0 && typeof doc0 === 'object' && doc0.event !== 'exception') {
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
   * Query Sportradar's direct tokenless Gismo API (`https://stats.fn.sportradar.com/{client}/{lang}/{tz}/gismo/{endpoint}/{paramsPath}`)
   * and return `doc[0].data` directly.
   */
  public async fetchGismo<T = unknown>(
    endpoint: string,
    paramsPath = '',
    options: GismoRequestOptions = {},
  ): Promise<T | null> {
    const doc = await this.fetchGismoDocument<T>(endpoint, paramsPath, options);
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
   * Query `config_sports/{serviceId}/{configId}` directly (the API behind the "All Sports" modal).
   * Falls back to the built-in 56-sport `SR_ALL_SPORTS_CATALOG` if offline.
   */
  public async listAllSports(
    serviceId = 69,
    configId = 0,
    clientAlias: GismoClientAlias = 'sportradar',
  ): Promise<SportCatalogItem[]> {
    const data = await this.fetchGismo<GismoSportConfigItem[]>(
      'config_sports',
      `${serviceId}/${configId}`,
      { clientAlias, timezone: 'Etc:UTC', ttlSec: 3600 },
    );
    if (Array.isArray(data) && data.length > 0) {
      return data
        .filter((s) => s && typeof s._id === 'number')
        .map((s) => ({ sportId: Number(s._id), name: String(s.name) }));
    }
    return Object.entries(SR_ALL_SPORTS_CATALOG).map(([id, name]) => ({
      sportId: Number(id),
      name,
    }));
  }

  /** Query `config_tree_mini/{serviceId}/{configId}/{sportId}/{rcId}` for category & tournament discovery. */
  public async getConfigTreeMini(
    serviceId = 69,
    configId = 0,
    sportOrId: string | number = 1,
    rcId?: number,
    options?: GismoRequestOptions,
  ): Promise<GismoCategoryTreeMini | null> {
    const sportId = resolveSportId(sportOrId);
    const params =
      rcId !== undefined
        ? `${serviceId}/${configId}/${sportId}/${rcId}`
        : `${serviceId}/${configId}/${sportId}`;
    return this.fetchGismo<GismoCategoryTreeMini>('config_tree_mini', params, {
      clientAlias: 'sportradar',
      ttlSec: 3600,
      ...options,
    });
  }

  /** Query `config_uniquetournaments/{serviceId}/{sportId}` for top/featured unique tournaments. */
  public async getUniqueTournaments(
    serviceId = 69,
    sportOrId: string | number = 1,
    options?: GismoRequestOptions,
  ): Promise<Record<string, GismoUniqueTournament> | GismoUniqueTournament[] | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchGismo('config_uniquetournaments', `${serviceId}/${sportId}`, {
      clientAlias: 'sportradar',
      ttlSec: 3600,
      ...options,
    });
  }

  /** Query `config_uniquetournamentsall/0/{serviceId}/{sportId}` for all unique tournaments in a sport. */
  public async getAllUniqueTournaments(
    serviceId = 69,
    sportOrId: string | number = 1,
    options?: GismoRequestOptions,
  ): Promise<Record<string, GismoUniqueTournament> | GismoUniqueTournament[] | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchGismo('config_uniquetournamentsall', `0/${serviceId}/${sportId}`, {
      clientAlias: 'sportradar',
      ttlSec: 3600,
      ...options,
    });
  }

  /** Query `tennis_calendar/{seasonYear}` for the ATP/WTA/Challenger tournament calendar. */
  public async getTennisCalendar(
    seasonYear: number | string = new Date().getUTCFullYear(),
    options?: GismoRequestOptions,
  ): Promise<GismoTennisCalendarResponse | null> {
    return this.fetchGismo<GismoTennisCalendarResponse>('tennis_calendar', String(seasonYear), {
      clientAlias: 'common',
      ttlSec: 3600,
      ...options,
    });
  }

  // ==========================================================================
  // B. Daily Match Schedules & Bookmaker Markets (`_bookmakerId: 176` & `0`)
  // ==========================================================================

  /**
   * Query `unified_sport_matches/{sportId}/{dateYmd}/{tzOffset}` for all matches on `dateYmd`.
   */
  public async getUnifiedSportMatches(
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
    tzOffset = 0,
    options?: GismoRequestOptions,
  ): Promise<GismoUnifiedSportMatchesResponse | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchGismo<GismoUnifiedSportMatchesResponse>(
      'unified_sport_matches',
      `${sportId}/${dateYmd}/${tzOffset}`,
      { ttlSec: 600, ...options },
    );
  }

  /**
   * Query `unified_sport_matches_markets/{sportId}/{dateYmd}/{tzOffset}` for bulk daily odds
   * (`clientAlias: 'tipico'` for Tipico `_bookmakerId: 176`, or `'sportradar'` for UOF `_bookmakerId: 0`).
   */
  public async getUnifiedSportMatchesMarkets(
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
    clientAlias: GismoClientAlias = 'tipico',
    tzOffset = 0,
    options?: GismoRequestOptions,
  ): Promise<GismoUnifiedMarketsResponse | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchGismo<GismoUnifiedMarketsResponse>(
      'unified_sport_matches_markets',
      `${sportId}/${dateYmd}/${tzOffset}`,
      { clientAlias, ttlSec: 600, ...options },
    );
  }

  /**
   * Query `match_markets/{matchId}/{marketType}` for the full pre-match market suite of a single match
   * (1X2, Double Chance, Draw No Bet, Asian Handicap, Over/Under Totals, and 28-outcome Correct Score matrix).
   */
  public async getMatchMarkets(
    matchId: number | string,
    marketType: 'prematch' | 'live' | string = 'prematch',
    clientAlias: GismoClientAlias = 'tipico',
    options?: GismoRequestOptions,
  ): Promise<GismoMatchMarketsResponse | null> {
    return this.fetchGismo<GismoMatchMarketsResponse>(
      'match_markets',
      `${matchId}/${marketType}`,
      { clientAlias, ttlSec: 600, ...options },
    );
  }

  /** Query `season_markets/{seasonId}` for tournament outright / winner futures odds. */
  public async getSeasonMarkets(
    seasonId: number | string,
    clientAlias: GismoClientAlias = 'tipico',
    options?: GismoRequestOptions,
  ): Promise<GismoSeasonMarketsResponse | null> {
    return this.fetchGismo<GismoSeasonMarketsResponse>('season_markets', String(seasonId), {
      clientAlias,
      ttlSec: 1800,
      ...options,
    });
  }

  // ==========================================================================
  // C. Match Intelligence, Live 3s Delta Stream, Squads, Injuries, Form & H2H
  // ==========================================================================

  /**
   * Query `match_timelinedelta/{matchId}` (`_maxage: 3`) for real-time 3-second live scores,
   * set/period breakdowns, tennis game points & active server, and rolling event deltas.
   */
  public async getMatchTimelineDelta(
    matchId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchTimelineDeltaResponse | null> {
    return this.fetchGismo<GismoMatchTimelineDeltaResponse>(
      'match_timelinedelta',
      String(matchId),
      { clientAlias: 'sportradar', ttlSec: 3, ...options },
    );
  }

  /** Query `event_get/{sportId}` (`_maxage: 10`) for the global 10-second live event feed across a sport. */
  public async getLiveEventsBySport(
    sportOrId: string | number = 'soccer',
    options?: GismoRequestOptions,
  ): Promise<GismoEventGetResponse | null> {
    const sportId = resolveSportId(sportOrId);
    return this.fetchGismo<GismoEventGetResponse>('event_get', String(sportId), {
      clientAlias: 'sportradar',
      ttlSec: 10,
      ...options,
    });
  }

  /** Query `match_info_statshub/{matchId}` for full match metadata, stadium, weather, managers & referee. */
  public async getMatchInfo(
    matchId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchInfoStatshubResponse | null> {
    return this.fetchGismo<GismoMatchInfoStatshubResponse>(
      'match_info_statshub',
      String(matchId),
      { clientAlias: 'sportradar', ttlSec: 60, ...options },
    );
  }

  /** Query `match_squads/{matchId}` for confirmed starting XI (`startinglineup`), `substitutes`, and `manager`. */
  public async getMatchSquads(
    matchId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchSquadsResponse | null> {
    return this.fetchGismo<GismoMatchSquadsResponse>('match_squads', String(matchId), {
      clientAlias: 'sportradar',
      ttlSec: 300,
      ...options,
    });
  }

  /** Query `stats_season_injuries/{seasonId}` for official league-wide injured, missing, and suspended players. */
  public async getSeasonInjuries(
    seasonId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoSeasonInjuryItem[] | null> {
    return this.fetchGismo<GismoSeasonInjuryItem[]>('stats_season_injuries', String(seasonId), {
      ttlSec: 1800,
      ...options,
    });
  }

  /** Query `stats_match_form/{matchId}` for chronological W/D/L form sequences and current streaks. */
  public async getMatchForm(
    matchId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchFormResponse | null> {
    return this.fetchGismo<GismoMatchFormResponse>('stats_match_form', String(matchId), {
      ttlSec: 1800,
      ...options,
    });
  }

  /** Query `stats_team_streaks/{teamUid}` (`clientAlias: 'common'`) for active team streaks and `nextmatches` difficulty ratings. */
  public async getTeamStreaks(
    teamUid: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoTeamStreaksResponse | null> {
    return this.fetchGismo<GismoTeamStreaksResponse>('stats_team_streaks', String(teamUid), {
      clientAlias: 'common',
      ttlSec: 1800,
      ...options,
    });
  }

  /** Query `stats_match_head2head/{matchId}` for head-to-head confrontation history of a match pair. */
  public async getMatchHead2Head(
    matchId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchHead2HeadResponse | null> {
    return this.fetchGismo<GismoMatchHead2HeadResponse>('stats_match_head2head', String(matchId), {
      ttlSec: 1800,
      ...options,
    });
  }

  /** Query `stats_h2h_versus/{minTeamUid}/{maxTeamUid}/{limit}` for direct H2H meetings between two team UIDs. */
  public async getHead2HeadVersus(
    teamUidA: number | string,
    teamUidB: number | string,
    limit = 10,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchHead2HeadResponse | null> {
    const aNum = Number(teamUidA);
    const bNum = Number(teamUidB);
    const minUid = Number.isFinite(aNum) && Number.isFinite(bNum) ? Math.min(aNum, bNum) : teamUidA;
    const maxUid = Number.isFinite(aNum) && Number.isFinite(bNum) ? Math.max(aNum, bNum) : teamUidB;
    return this.fetchGismo<GismoMatchHead2HeadResponse>(
      'stats_h2h_versus',
      `${minUid}/${maxUid}/${limit}`,
      { clientAlias: 'common', ttlSec: 1800, ...options },
    );
  }

  /** Query `stats_team_lastx/{teamUid}/{limit}` for a team's or player's last `limit` completed matches. */
  public async getTeamLastX(
    teamUid: number | string,
    limit = 10,
    options?: GismoRequestOptions,
  ): Promise<GismoTeamLastXResponse | null> {
    return this.fetchGismo<GismoTeamLastXResponse>('stats_team_lastx', `${teamUid}/${limit}`, {
      ttlSec: 1800,
      ...options,
    });
  }

  /** Query `match_situations/{matchId}` (`clientAlias: 'common'`) for live pitch attack / dangerous-attack coordinates. */
  public async getMatchSituations(
    matchId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchSituationsResponse | null> {
    return this.fetchGismo<GismoMatchSituationsResponse>('match_situations', String(matchId), {
      clientAlias: 'common',
      ttlSec: 45,
      ...options,
    });
  }

  /** Query `stats_match_stats/{matchId}` for detailed match boxscore statistics. */
  public async getMatchStats(
    matchId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoMatchStatsResponse | null> {
    return this.fetchGismo<GismoMatchStatsResponse>('stats_match_stats', String(matchId), {
      ttlSec: 120,
      ...options,
    });
  }

  // ==========================================================================
  // D. Tennis & Player / Season Analytics Endpoints
  // ==========================================================================

  /**
   * Query `tennis_team_surfacestats/{playerUid}` (`clientAlias: 'common'`) for multi-season ATP/WTA
   * win-loss records broken down by surface (`0`=All, `1`=Clay, `2`=Hard Outdoor, `3`=Grass, `4`=Hard Indoor).
   */
  public async getTennisTeamSurfaceStats(
    playerUid: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoTennisSurfaceStatsResponse | null> {
    return this.fetchGismo<GismoTennisSurfaceStatsResponse>(
      'tennis_team_surfacestats',
      String(playerUid),
      { clientAlias: 'common', ttlSec: 3600, ...options },
    );
  }

  /** Query `tennis_ranking/{type}/{year}/{week}` for official ATP/WTA rankings. */
  public async getTennisRanking(
    tourType: 'atp' | 'wta' | string,
    year: number | string,
    week: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoTennisRankingResponse | null> {
    return this.fetchGismo<GismoTennisRankingResponse>(
      'tennis_ranking',
      `${tourType}/${year}/${week}`,
      { clientAlias: 'common', ttlSec: 3600, ...options },
    );
  }

  /** Query `stats_season_tables/{seasonId}/{tableType}/{round}` for league standings tables. */
  public async getSeasonTables(
    seasonId: number | string,
    tableType: number | string = 1,
    round: number | string = 0,
    options?: GismoRequestOptions,
  ): Promise<GismoSeasonTablesResponse | null> {
    return this.fetchGismo<GismoSeasonTablesResponse>(
      'stats_season_tables',
      `${seasonId}/${tableType}/${round}`,
      { clientAlias: 'common', ttlSec: 1800, ...options },
    );
  }

  /** Query `stats_season_overunder/{seasonId}` for league-wide Over/Under goals distributions. */
  public async getSeasonOverUnder(
    seasonId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoSeasonOverUnderResponse | null> {
    return this.fetchGismo<GismoSeasonOverUnderResponse>(
      'stats_season_overunder',
      String(seasonId),
      { clientAlias: 'common', ttlSec: 1800, ...options },
    );
  }

  /** Query `stats_season_teamscoringconceding/{seasonId}/{teamUid}/{limit}` for 15-minute goal interval distributions. */
  public async getTeamScoringConceding(
    seasonId: number | string,
    teamUid: number | string,
    limit = 10,
    options?: GismoRequestOptions,
  ): Promise<GismoTeamScoringConcedingResponse | null> {
    return this.fetchGismo<GismoTeamScoringConcedingResponse>(
      'stats_season_teamscoringconceding',
      `${seasonId}/${teamUid}/${limit}`,
      { clientAlias: 'common', ttlSec: 1800, ...options },
    );
  }

  /** Query `referee_seasonstats/{refereeId}/{seasonId}` for referee cards, fouls, and penalties per match. */
  public async getRefereeSeasonStats(
    refereeId: number | string,
    seasonId: number | string,
    options?: GismoRequestOptions,
  ): Promise<GismoRefereeSeasonStatsResponse | null> {
    return this.fetchGismo<GismoRefereeSeasonStatsResponse>(
      'referee_seasonstats',
      `${refereeId}/${seasonId}`,
      { clientAlias: 'common', ttlSec: 3600, ...options },
    );
  }

  // ==========================================================================
  // High-Level Composite Intelligence Workflows (Matching BetScout Engine)
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
    const uData = await this.getUnifiedSportMatches(sportOrId, dateYmd, 0);
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
   * Fetch the bulk daily markets map for both `tipico` (`_bookmakerId: 176`) and
   * `sportradar` (`_bookmakerId: 0`) in parallel.
   */
  public async getDailyMarketsMap(
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
  ): Promise<{
    tipico: NonNullable<GismoUnifiedMarketsResponse['matches']>;
    uof: NonNullable<GismoUnifiedMarketsResponse['matches']>;
  }> {
    const [tipResp, uofResp] = await Promise.all([
      this.getUnifiedSportMatchesMarkets(sportOrId, dateYmd, 'tipico', 0),
      this.getUnifiedSportMatchesMarkets(sportOrId, dateYmd, 'sportradar', 0),
    ]);
    return {
      tipico: tipResp?.matches ?? {},
      uof: uofResp?.matches ?? {},
    };
  }

  /**
   * Fast pre-match odds & totals lookup from Sportradar (`Tipico` + `UOF` bulk daily feed).
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
          flipped = TrueOrFalse(true);
          break;
        }
      }
      if (matchedEntry) break;
    }

    if (!matchedEntry) return {};
    const matchedM = matchedEntry.match_obj;
    const mid = String(matchedM._id ?? '');
    if (!mid) return {};

    const { tipico, uof } = await this.getDailyMarketsMap(sportOrId, matchedYmd);
    const tipRaw = tipico[mid]?.markets ?? [];
    const uofRaw = uof[mid]?.markets ?? [];
    const pTip = parsePrematchMarkets(tipRaw, flipped);
    const pUof = parsePrematchMarkets(uofRaw, flipped);
    const merged = mergeTipicoAndUofMarkets(pTip, pUof);

    const dtUts = matchedM._dt?.uts ?? 0;
    const hTeamM = flipped ? matchedM.teams?.away : matchedM.teams?.home;
    const aTeamM = flipped ? matchedM.teams?.home : matchedM.teams?.away;

    return {
      sr_match_id: mid,
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
        tipRaw.length > 0
          ? 'sportradar_tipico'
          : uofRaw.length > 0
            ? 'sportradar_uof'
            : 'sportradar',
    };
  }

  /**
   * Compute 15-minute goal scoring/conceding rates (`0-15'`..`76-90'`), 1st-half scoring %, and BTTS %
   * from `stats_season_teamscoringconceding/{seasonId}/{teamUid}/{limit}`.
   */
  public async fetchTeamGoalIntervals(
    seasonId: number | string,
    teamUid: number | string,
    limit = 10,
  ): Promise<TeamGoalIntervalsSummary> {
    const data = await this.getTeamScoringConceding(seasonId, teamUid, limit);
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
   * Compute live attack & dangerous-attack territorial pressure share from `match_situations/{matchId}`.
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
   * Evaluate pre-match `stats_season_injuries` for a Football match, counting missing forwards (`FWD`/`F`)
   * and goalkeepers (`GK`/`G`) and computing a net win-probability adjustment & veto recommendation.
   */
  public async evaluateInjuryGate(
    seasonId: number | string | null | undefined,
    backedUid: number | string | null | undefined,
    oppUid: number | string | null | undefined,
  ): Promise<SportradarInjuryGateEvaluation> {
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
   * Resolve a match by `(home, away)` and stream its 3-second real-time `match_timelinedelta/{matchId}` state
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
        sr_match_id: mid,
        sr_season_id: matchedM._seasonid ?? null,
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
        sr_match_id: mid,
        sr_season_id: matchedM._seasonid ?? null,
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
      sr_match_id: mid,
      sr_season_id: matchedM._seasonid ?? null,
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
   * Full Match Intelligence Lookup (`lookup_statshub_match_intel`):
   * Finds `(home, away)` on `dateYmd` (or `dateYmd + 1 day`), merges **Tipico (`_bookmakerId: 176`)**
   * and **Sportradar UOF (`_bookmakerId: 0`)** pre-match markets (including the 28-outcome Correct Score grid),
   * and enriches with league injuries (`stats_season_injuries`), team streaks (`stats_team_streaks`),
   * 15-minute goal intervals (`stats_season_teamscoringconceding`), live dangerous attacks (`match_situations`),
   * or ATP/WTA surface win-loss records (`tennis_team_surfacestats`).
   */
  public async lookupMatchIntel(
    home: string,
    away: string,
    sportOrId: string | number = 'soccer',
    dateYmd: string = todayYmdUtc(),
  ): Promise<StatshubMatchIntelResult> {
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

    const [mmTipico, mmSrMain] = await Promise.all([
      this.getMatchMarkets(mid, 'prematch', 'tipico'),
      this.getMatchMarkets(mid, 'prematch', 'sportradar'),
    ]);

    const tipicoParsed = parsePrematchMarkets(mmTipico?.markets, flipped);
    const srUofParsed = parsePrematchMarkets(mmSrMain?.markets, flipped);
    const marketsParsed: ParsedPrematchMarkets = mergeTipicoAndUofMarkets(
      tipicoParsed,
      srUofParsed,
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
        const sData = await this.getTennisTeamSurfaceStats(pUid);
        const singlesYr = sData?.singles?.['2026'] ?? sData?.singles?.['2025'];
        if (singlesYr) {
          const allRec = singlesYr['0'] ?? {};
          const clayRec = singlesYr['1'] ?? {};
          const hardRec = singlesYr['2'] ?? {};
          const indoorRec = singlesYr['4'] ?? {};
          tennisSurfaceRecords[sideLbl] = {
            season_wl: `${allRec.wins ?? 0}-${allRec.losses ?? 0}`,
            hard_wl: `${hardRec.wins ?? 0}-${hardRec.losses ?? 0}`,
            clay_wl: `${clayRec.wins ?? 0}-${clayRec.losses ?? 0}`,
            indoor_wl: `${indoorRec.wins ?? 0}-${indoorRec.losses ?? 0}`,
          };
        }
      }
    }

    const streaksSummary: { home: string[]; away: string[] } = { home: [], away: [] };
    let goalIntervals: { home?: TeamGoalIntervalsSummary; away?: TeamGoalIntervalsSummary } = {};
    let livePressure: LiveMatchSituationsPressure = {};
    let injuryGate: SportradarInjuryGateEvaluation | Record<string, never> = {};

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
      sr_match_id: mid,
      sr_season_id: seasonId,
      home_uid: hUid,
      away_uid: aUid,
      tournament: matchedEntry.tournament,
      primary_markets: marketsParsed,
      consensus_markets: srUofParsed,
      tipico_markets: marketsParsed,
      sportradar_uof_markets: srUofParsed,
      home_injuries: homeInjuries,
      away_injuries: awayInjuries,
      injury_gate: injuryGate,
      goal_intervals: goalIntervals,
      live_pressure: livePressure,
      streaks: streaksSummary,
      tennis_surface_records: tennisSurfaceRecords,
    };
  }
}

function TrueOrFalse(v: boolean): boolean {
  return v;
}
