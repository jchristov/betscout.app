/**
 * Complete TypeScript Data Interfaces for Sportradar StatsHub & Tipico Gismo JSON APIs.
 * Covers all 4 endpoint families documented in `docs/SPORTRADAR_STATSHUB.md`:
 *   A. Configuration & Sport/Tournament Discovery
 *   B. Daily Match Schedules & Tipico / UOF Bookmaker Markets
 *   C. Match Intelligence, 3s Live Delta Stream (`match_timelinedelta`), Squads, Injuries, Form & H2H
 *   D. Tennis Surface Analytics, Standings Tables, Goal Intervals & Referee Stats
 */

export type GismoClientAlias = 'tipico' | 'sportradar' | 'common' | (string & {});
export type GismoLanguage = 'en' | 'de' | 'agnostic' | (string & {});
export type GismoTimezone = 'Europe:Berlin' | 'Etc:UTC' | 'Europe:Vienna' | (string & {});

/**
 * Top-level Gismo JSON response envelope returned by `stats.fn.sportradar.com` and `sh.fn.sportradar.com`.
 */
export interface GismoEnvelope<TData = unknown> {
  queryUrl?: string;
  doc: GismoDocument<TData>[];
}

export interface GismoDocument<TData = unknown> {
  event: string;
  /** UNIX timestamp (seconds) when the document was generated */
  _dob?: number;
  /** Recommended client cache/polling TTL in seconds (e.g. `3` for `match_timelinedelta`) */
  _maxage?: number;
  data: TData;
}

export interface SportradarGismoClientOptions {
  /** Primary tokenless Gismo base URL (default: `https://stats.fn.sportradar.com`) */
  baseUrl?: string;
  /** Secondary token-gated Fishnet base URL (default: `https://sh.fn.sportradar.com`) */
  fallbackBaseUrl?: string;
  /** Default client alias (`'tipico'`, `'sportradar'`, or `'common'`; default: `'tipico'`) */
  defaultClientAlias?: GismoClientAlias;
  /** Default localization language (default: `'en'`) */
  defaultLanguage?: GismoLanguage;
  /** Default timezone for date-bucketed queries (default: `'Europe:Berlin'`) */
  defaultTimezone?: GismoTimezone;
  /** Default in-memory cache TTL in seconds (default: `300`) */
  defaultTtlSec?: number;
  /** Request timeout in milliseconds (default: `12000`) */
  timeoutMs?: number;
  /** Custom `fetch` implementation (for testing, proxies, or custom runtimes) */
  fetchFn?: typeof fetch;
}

export interface GismoRequestOptions {
  clientAlias?: GismoClientAlias;
  language?: GismoLanguage;
  timezone?: GismoTimezone;
  ttlSec?: number;
  bypassCache?: boolean;
}

// ============================================================================
// A. Configuration & Sport / Tournament Discovery Interfaces
// ============================================================================

export interface GismoSportConfigItem {
  _doc?: 'sport';
  _id: number;
  _sid?: number;
  name: string;
  hasLive?: boolean;
}

export interface SportCatalogItem {
  sportId: number;
  name: string;
}

export interface GismoCategoryTreeMini {
  _doc?: string;
  realcategories?: GismoRealCategorySummary[];
}

export interface GismoRealCategorySummary {
  _doc?: 'realcategory';
  _id: number;
  _sid?: number;
  name: string;
  cc?: {
    _id?: number;
    a2?: string;
    name?: string;
    continent?: string;
  };
  tournaments?: GismoUniqueTournament[];
}

export interface GismoUniqueTournament {
  _doc?: 'uniquetournament' | 'tournament';
  _id: number;
  _sid?: number;
  _rcid?: number;
  _utid?: number;
  _iskip?: boolean;
  name: string;
  abbr?: string;
  ground?: string | null;
  friendly?: boolean;
  currentseason?: number;
  seasonid?: number;
}

export interface GismoTennisCalendarTournament {
  _id: number;
  name: string;
  utid?: number;
  ground?: string;
  prize?: string | number;
   currency?: string;
  start?: { uts?: number; date?: string };
  end?: { uts?: number; date?: string };
}

export interface GismoTennisCalendarResponse {
  seasonYear?: number | string;
  tournaments?: GismoTennisCalendarTournament[];
  [key: string]: unknown;
}

// ============================================================================
// B. Daily Match Schedules & Bookmaker Markets (`_bookmakerId: 176` & `0`)
// ============================================================================

export interface GismoTeamRef {
  _doc?: 'team';
  _id: number;
  _sid?: number;
  uid: number;
  virtual?: boolean;
  name: string;
  mediumname?: string;
  abbr?: string;
  nickname?: string | null;
  iscountry?: boolean;
  haslogo?: boolean;
  surname?: string;
}

export interface GismoMatchStatus {
  _doc?: 'status';
  /**
   * Canonical Sportradar status codes:
   * - `0`: Not started (`NS`)
   * - `6`: 1st half (`1H`)
   * - `7`: 2nd half (`2H`)
   * - `8`: 1st set (`S1`), `9`: 2nd set (`S2`), `10`: 3rd set (`S3`), `11`: 4th set, `12`: 5th set
   * - `22`: About to start
   * - `31`: Halftime (`HT`)
   * - `60`: Postponed, `61`: Delayed, `70`: Cancelled
   * - `100`: Ended (`FT`), `110`: Ended after extra time (`AET`), `120`: Ended after penalties (`AP`)
   */
  _id: number;
  name: string;
  shortName?: string;
}

export interface GismoMatchDateTime {
  _doc?: 'time';
  time?: string;
  date?: string;
  tz?: string;
  tzoffset?: number;
  /** UNIX epoch timestamp in seconds */
  uts: number;
}

export interface GismoMatchResult {
  home: number | null;
  away: number | null;
  period?: string;
  winner?: 'home' | 'away' | 'draw' | null;
}

export interface GismoPeriodScore {
  home: number | null;
  away: number | null;
}

export interface GismoPeriodScoreMap {
  p1?: GismoPeriodScore;
  p2?: GismoPeriodScore;
  p3?: GismoPeriodScore;
  p4?: GismoPeriodScore;
  p5?: GismoPeriodScore;
  ft?: GismoPeriodScore;
  ap?: GismoPeriodScore;
  [periodKey: string]: GismoPeriodScore | undefined;
}

export interface GismoGameScore {
  home: number | string;
  away: number | string;
  /** Active server in Tennis/Table Tennis: `'1'` = home, `'2'` = away */
  service?: '1' | '2' | string | null;
}

export interface GismoMatchSummary {
  _doc?: 'match';
  _id: number;
  _sid?: number;
  _seasonid?: number;
  _rcid?: number;
  _tid?: number;
  _utid?: number;
  _dt?: GismoMatchDateTime;
  updated_uts?: number;
  round?: number;
  roundname?: { _id?: number; name?: string };
  status?: GismoMatchStatus;
  teams?: {
    home?: GismoTeamRef;
    away?: GismoTeamRef;
  };
  result?: GismoMatchResult;
  periods?: GismoPeriodScoreMap | null;
  gamescore?: GismoGameScore | null;
  neutralground?: boolean;
  walkover?: boolean;
  retired?: boolean;
}

export interface GismoTournamentGroup {
  _doc?: 'tournament';
  _id: number;
  _sid?: number;
  _rcid?: number;
  _utid?: number;
  _seasonid?: number;
  name: string;
  abbr?: string;
  ground?: string | null;
  matches?: GismoMatchSummary[];
}

export interface GismoRealCategory {
  _doc?: 'realcategory';
  _id: number;
  _sid?: number;
  name: string;
  tournaments?: GismoTournamentGroup[];
}

export interface GismoUnifiedSportMatchesResponse {
  sport?: {
    _doc?: 'sport';
    _id: number;
    name: string;
    realcategories?: GismoRealCategory[];
  };
}

export interface GismoMarketOutcome {
  _id: string | number;
  name: string;
  odds: number;
  probability?: number;
  active?: boolean;
}

export interface GismoMarket {
  _marketId: number;
  _bookmakerId?: number;
  name?: string;
  source?: string;
  specifiers?: {
    hcp?: string;
    total?: string;
    setnr?: string;
    [key: string]: string | undefined;
  };
  outcomes?: GismoMarketOutcome[];
}

export interface GismoUnifiedMarketsResponse {
  matches?: Record<
    string,
    {
      _id?: number;
      markets?: GismoMarket[];
    }
  >;
}

export interface GismoMatchMarketsResponse {
  _id?: number;
  markets?: GismoMarket[];
}

export interface GismoSeasonMarketsResponse {
  _id?: number;
  markets?: GismoMarket[];
  [key: string]: unknown;
}

export interface ParsedPrematchMarkets {
  bookmaker: 'Primary Bookmaker' | 'Market Consensus' | 'Primary + Consensus';
  odds_home: number | null;
  odds_draw: number | null;
  odds_away: number | null;
  double_chance_1x: number | null;
  double_chance_x2: number | null;
  draw_no_bet_home: number | null;
  draw_no_bet_away: number | null;
  asian_handicap_line: string | null;
  asian_handicap_home: number | null;
  asian_handicap_away: number | null;
  total_line: number | null;
  odds_over: number | null;
  odds_under: number | null;
  /** 28-outcome Correct Score matrix keyed by `"H:A"` (e.g. `{"1:0": 6.5, "2:0": 7.2, "2:1": 8.0}`) */
  correct_score_odds: Record<string, number>;
}

export interface DailyMatchIndexEntry {
  match_obj: GismoMatchSummary;
  tournament: string;
  home: string;
  away: string;
}

export interface DailyOddsLookupResult {
  sr_match_id?: string;
  start_utc?: string | null;
  start_uts?: number | null;
  home_uid?: number | null;
  away_uid?: number | null;
  odds_home?: number | null;
  odds_draw?: number | null;
  odds_away?: number | null;
  line_total?: number | null;
  odds_over?: number | null;
  odds_under?: number | null;
  correct_score_odds?: Record<string, number>;
  odds_provider?: 'sportradar_tipico' | 'sportradar_uof' | 'sportradar';
}

// ============================================================================
// C. Match Intelligence, Live Delta Stream, Squads, Injuries, Form & H2H
// ============================================================================

export interface GismoTimelineDeltaEvent {
  _doc?: 'event';
  _id?: number | string;
  _doctype?: string;
  type: string;
  matchid?: number;
  uts?: number;
  time?: number;
  period?: string;
  team?: 'home' | 'away' | string;
  result?: GismoPeriodScore;
  set_score?: { home: string | number; away: string | number };
  game_score?: { home: string | number; away: string | number };
  game_points?: { home: string | number; away: string | number };
  service?: '1' | '2' | string;
  player?: { _id?: number; name?: string };
}

export interface GismoMatchTimelineDeltaResponse {
  match?: GismoMatchSummary;
  events?: GismoTimelineDeltaEvent[];
}

export interface GismoEventGetResponse {
  events?: GismoTimelineDeltaEvent[];
  matches?: Record<string, GismoMatchSummary>;
  [key: string]: unknown;
}

export interface GismoMatchInfoStatshubResponse {
  match?: GismoMatchSummary & {
    stadium?: { _id?: number; name?: string; city?: string; capacity?: number };
    weather?: { pitch?: string; temperature?: number; wind?: string };
    referee?: { _id?: number; name?: string; nationality?: string };
    manager?: {
      home?: { _id?: number; name?: string };
      away?: { _id?: number; name?: string };
    };
  };
  tournament?: GismoUniqueTournament;
  realcategory?: GismoRealCategorySummary;
  [key: string]: unknown;
}

export interface GismoSquadPlayer {
  player?: {
    _id: number;
    name: string;
    shirtnumber?: number;
    position?: { _id?: number; name?: string; shortname?: string };
  };
  shirtnumber?: number;
  position?: { _id?: number; name?: string; shortname?: string };
}

export interface GismoMatchSquadsResponse {
  home?: {
    startinglineup?: { players?: GismoSquadPlayer[] };
    substitutes?: { players?: GismoSquadPlayer[] };
    manager?: { _id?: number; name?: string };
    formation?: string;
  };
  away?: {
    startinglineup?: { players?: GismoSquadPlayer[] };
    substitutes?: { players?: GismoSquadPlayer[] };
    manager?: { _id?: number; name?: string };
    formation?: string;
  };
  [key: string]: unknown;
}

export interface GismoSeasonInjuryItem {
  uniqueteam?: {
    _id: number;
    name?: string;
  };
  player?: {
    _id: number;
    name: string;
    shirtnumber?: number;
    position?: {
      _id?: number;
      name?: string;
      shortname?: string;
    };
  };
  status?: {
    _id?: number;
    name?: string;
    status?: string;
    start?: { uts?: number; date?: string };
    end?: { uts?: number; date?: string } | null;
  };
}

export interface GismoTeamFormEntry {
  type: 'W' | 'D' | 'L' | string;
  matchid?: number;
  tournament?: { _id?: number; name?: string };
}

export interface GismoTeamStreak {
  type: 'W' | 'D' | 'L' | string;
  value: number;
}

export interface GismoMatchFormResponse {
  teams?: {
    home?: {
      team?: GismoTeamRef;
      streak?: GismoTeamStreak;
      form?: GismoTeamFormEntry[];
    };
    away?: {
      team?: GismoTeamRef;
      streak?: GismoTeamStreak;
      form?: GismoTeamFormEntry[];
    };
  };
}

export interface GismoNextMatchDifficulty {
  matchid?: number;
  opponent?: GismoTeamRef;
  homeAway?: 'home' | 'away';
  matchdifficultyrating?: number;
}

export interface GismoTeamStreaksResponse {
  team?: GismoTeamRef;
  streaks?: Record<
    string,
    {
      total?: { value?: number };
      home?: { value?: number };
      away?: { value?: number };
    }
  >;
  nextmatches?: GismoNextMatchDifficulty[];
  [key: string]: unknown;
}

export interface GismoHistoricalMatchItem {
  _id: number;
  _dt?: GismoMatchDateTime;
  time?: GismoMatchDateTime;
  teams?: {
    home?: GismoTeamRef;
    away?: GismoTeamRef;
  };
  result?: GismoMatchResult;
  periods?: GismoPeriodScoreMap;
}

export interface GismoMatchHead2HeadResponse {
  matches?: GismoHistoricalMatchItem[];
  [key: string]: unknown;
}

export interface GismoTeamLastXResponse {
  team?: GismoTeamRef;
  matches?: GismoHistoricalMatchItem[];
}

export interface GismoMatchSituationItem {
  time?: number;
   injurytime?: number;
  team?: 'home' | 'away';
  situation?: 'attack' | 'dangerous_attack' | 'safe' | string;
  x?: number;
  y?: number;
}

export interface GismoMatchSituationsResponse {
  _id?: number;
  situations?: GismoMatchSituationItem[];
}

export interface GismoMatchStatsResponse {
  match?: GismoMatchSummary;
  stats?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface LiveTimelineDeltaSummary {
  sr_match_id?: number | string;
  sr_season_id?: number | null;
  status_id?: number;
  home_uid?: number | null;
  away_uid?: number | null;
  state?: 'pre' | 'in' | 'post';
  status_desc?: string;
  start_utc?: string | null;
  score_str?: string;
  home_score?: number;
  away_score?: number;
  periods?: string[];
  point_score?: string;
  outcome?: 'H' | 'A' | 'D' | null;
}

export interface LiveMatchSituationsPressure {
  home_attacks?: number;
  away_attacks?: number;
  home_dangerous_attacks?: number;
  away_dangerous_attacks?: number;
  home_danger_share_pct?: number;
  away_danger_share_pct?: number;
}

export interface SportradarInjuryGateEvaluation {
  status: string;
  backed_out: string[];
  opp_out: string[];
  backed_fwd_out?: number;
  backed_gk_out?: number;
  prob_adjustment: number;
  veto_recommended: boolean;
}

// ============================================================================
// D. Tennis & Player / Season Analytics Interfaces
// ============================================================================

export interface GismoTennisSurfaceRecord {
  wins?: number;
  losses?: number;
  tournaments?: number;
  titles?: number;
}

export interface GismoTennisSurfaceStatsResponse {
  player?: GismoTeamRef;
  /** Keyed by season year (`"2026"`, `"2025"`), then by `groundId` (`"0"`=All, `"1"`=Clay, `"2"`=Hard Outdoor, `"3"`=Grass, `"4"`=Hard Indoor) */
  singles?: Record<string, Record<string, GismoTennisSurfaceRecord>>;
  doubles?: Record<string, Record<string, GismoTennisSurfaceRecord>>;
}

export interface TennisSurfaceSummary {
  season_wl: string;
  hard_wl: string;
  clay_wl: string;
  indoor_wl: string;
}

export interface GismoTennisRankingResponse {
  type?: string;
  year?: number;
  week?: number;
  rankings?: Array<{
    rank: number;
    points: number;
    team?: GismoTeamRef;
  }>;
  [key: string]: unknown;
}

export interface GismoSeasonTableRow {
  pos: number;
  team: GismoTeamRef;
  played?: number;
  win?: number;
  draw?: number;
  loss?: number;
  goalsfor?: number;
  goalsagainst?: number;
  goaldiff?: number;
  points?: number;
}

export interface GismoSeasonTablesResponse {
  tables?: Array<{
    _id?: number;
    name?: string;
    tablerows?: GismoSeasonTableRow[];
  }>;
  [key: string]: unknown;
}

export interface GismoSeasonOverUnderResponse {
  teams?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface GismoGoalMinuteBucket {
  total?: number;
  home?: number;
  away?: number;
  percentage?: number;
}

export interface GismoTeamScoringConcedingResponse {
  stats?: {
    totalmatches?: { total?: number; home?: number; away?: number };
    scoring?: {
      goalsbyminutes?: Record<string, GismoGoalMinuteBucket>;
      goalsscoredfirsthalfaverage?: { total?: number };
      scoringathalftimeaverage?: { total?: number };
      bothteamsscoredaverage?: { total?: number };
    };
    conceding?: {
      goalsbyminutes?: Record<string, GismoGoalMinuteBucket>;
      goalsconcededfirsthalfaverage?: { total?: number };
    };
  };
}

export interface GoalIntervalBucketSummary {
  scored_per_match: number;
  conceded_per_match: number;
  combined_per_match: number;
}

export interface TeamGoalIntervalsSummary {
  matches_sampled?: number;
  first_half_scored_avg?: number;
  first_half_conceded_avg?: number;
  scoring_in_1h_pct?: number;
  btts_pct?: number;
  late_76_90_scored_avg?: number;
  late_76_90_conceded_avg?: number;
  late_76_90_total_avg?: number;
  intervals?: Record<string, GoalIntervalBucketSummary>;
}

export interface GismoRefereeSeasonStatsResponse {
  referee?: { _id?: number; name?: string; nationality?: string };
  stats?: {
    matches?: number;
    yellowcards?: number;
    redcards?: number;
    penalties?: number;
  };
  [key: string]: unknown;
}

export interface StatshubMatchIntelResult {
  ok: boolean;
  found: boolean;
  sr_match_id?: number | string;
  sr_season_id?: number | null;
  home_uid?: number | null;
  away_uid?: number | null;
  tournament?: string;
  primary_markets?: ParsedPrematchMarkets;
  consensus_markets?: ParsedPrematchMarkets;
  tipico_markets?: ParsedPrematchMarkets;
  sportradar_uof_markets?: ParsedPrematchMarkets;
  home_injuries?: string[];
  away_injuries?: string[];
  injury_gate?: SportradarInjuryGateEvaluation | Record<string, never>;
  goal_intervals?: {
    home?: TeamGoalIntervalsSummary;
    away?: TeamGoalIntervalsSummary;
  };
  live_pressure?: LiveMatchSituationsPressure;
  streaks?: {
    home: string[];
    away: string[];
  };
  tennis_surface_records?: {
    home?: TennisSurfaceSummary;
    away?: TennisSurfaceSummary;
  };
}
