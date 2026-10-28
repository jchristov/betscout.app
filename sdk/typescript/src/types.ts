/**
 * Complete TypeScript Data Interfaces for the BetScout Sports Data & Odds SDK (`@betscout/sdk`).
 * Covers:
 *   A. Configuration & Sport/Tournament Discovery
 *   B. Daily Match Schedules & Multi-Bookmaker Markets (Primary Retail + Global Consensus)
 *   C. Match Intelligence, 3s Live Delta Stream, Squads, Injuries, Form & H2H
 *   D. Team & Player Profiles, Historical Performance, Season Statistics, Squads, Lineups & Transfers
 *   E. Tennis Career & Surface Analytics, Standings Tables, Goal Intervals & Referee Stats
 */

export type ProviderChannel = 'global' | 'eu-retail' | 'neutral' | (string & {});
export type FeedLanguage = 'en' | 'de' | 'agnostic' | (string & {});
export type FeedTimezone = 'Europe:Berlin' | 'Etc:UTC' | 'Europe:Vienna' | (string & {});

/**
 * Top-level JSON response envelope returned by the BetScout Data transport layer.
 */
export interface BetScoutEnvelope<TData = unknown> {
  queryUrl?: string;
  doc: BetScoutDocument<TData>[];
}

export interface BetScoutDocument<TData = unknown> {
  event: string;
  /** UNIX timestamp (seconds) when the document was generated */
  _dob?: number;
  /** Recommended client cache/polling TTL in seconds (e.g. `3` for live timeline deltas) */
  _maxage?: number;
  data: TData;
}

export interface BetScoutClientOptions {
  /** Custom data gateway base URL (optional override) */
  baseUrl?: string;
  /** Default provider channel (`'global'`, `'eu-retail'`, or `'neutral'`; default: `'eu-retail'`) */
  defaultChannel?: ProviderChannel;
  /** Default localization language (default: `'en'`) */
  defaultLanguage?: FeedLanguage;
  /** Default timezone for date-bucketed queries (default: `'Europe:Berlin'`) */
  defaultTimezone?: FeedTimezone;
  /** Default in-memory cache TTL in seconds (default: `300`) */
  defaultTtlSec?: number;
  /** Request timeout in milliseconds (default: `12000`) */
  timeoutMs?: number;
  /** Custom `fetch` implementation (for testing, proxies, or custom runtimes) */
  fetchFn?: typeof fetch;
}

export interface BetScoutRequestOptions {
  channel?: ProviderChannel;
  language?: FeedLanguage;
  timezone?: FeedTimezone;
  ttlSec?: number;
  bypassCache?: boolean;
}

// ============================================================================
// A. Configuration & Sport / Tournament Discovery Interfaces
// ============================================================================

export interface BetScoutSportConfigItem {
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

export interface BetScoutCountryCode {
  _doc?: 'countrycode';
  _id?: number;
  a2?: string;
  a3?: string;
  name?: string;
  ioc?: string;
  continentid?: number;
  continent?: string;
  population?: number;
}

export interface BetScoutCategoryTreeMini {
  _doc?: string;
  realcategories?: BetScoutRealCategorySummary[];
}

export interface BetScoutRealCategorySummary {
  _doc?: 'realcategory';
  _id: number;
  _sid?: number;
  name: string;
  cc?: BetScoutCountryCode;
  tournaments?: BetScoutUniqueTournament[];
}

export interface BetScoutUniqueTournament {
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

export interface BetScoutTennisCalendarTournament {
  _id: number;
  name: string;
  utid?: number;
  ground?: string;
  prize?: string | number;
  currency?: string;
  start?: { uts?: number; date?: string };
  end?: { uts?: number; date?: string };
}

export interface BetScoutTennisCalendarResponse {
  seasonYear?: number | string;
  tournaments?: BetScoutTennisCalendarTournament[];
  [key: string]: unknown;
}

// ============================================================================
// B. Daily Match Schedules & Multi-Bookmaker Markets
// ============================================================================

export interface BetScoutTeamRef {
  _doc?: 'team' | 'uniqueteam';
  _id: number;
  _sid?: number;
  _rcid?: number;
  uid?: number;
  virtual?: boolean;
  name: string;
  mediumname?: string;
  abbr?: string;
  nickname?: string | null;
  iscountry?: boolean;
  haslogo?: boolean;
  founded?: string | null;
  website?: string | null;
  surname?: string;
  sex?: 'm' | 'f' | string;
  cc?: BetScoutCountryCode | string | null;
  tennisteamid?: number;
}

export interface BetScoutMatchStatus {
  _doc?: 'status';
  /**
   * Canonical match status codes:
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

export interface BetScoutDateTime {
  _doc?: 'time';
  time?: string;
  date?: string;
  tz?: string;
  tzoffset?: number;
  /** UNIX epoch timestamp in seconds */
  uts: number;
}

export interface BetScoutMatchResult {
  home: number | null;
  away: number | null;
  period?: string;
  winner?: 'home' | 'away' | 'draw' | null;
}

export interface BetScoutPeriodScore {
  home: number | null;
  away: number | null;
}

export interface BetScoutPeriodScoreMap {
  p1?: BetScoutPeriodScore;
  p2?: BetScoutPeriodScore;
  p3?: BetScoutPeriodScore;
  p4?: BetScoutPeriodScore;
  p5?: BetScoutPeriodScore;
  ft?: BetScoutPeriodScore;
  ap?: BetScoutPeriodScore;
  [periodKey: string]: BetScoutPeriodScore | undefined;
}

export interface BetScoutGameScore {
  home: number | string;
  away: number | string;
  /** Active server in Tennis/Table Tennis: `'1'` = home, `'2'` = away */
  service?: '1' | '2' | string | null;
}

export interface BetScoutMatchSummary {
  _doc?: 'match';
  _id: number;
  _sid?: number;
  _seasonid?: number;
  _rcid?: number;
  _tid?: number;
  _utid?: number;
  _dt?: BetScoutDateTime;
  time?: BetScoutDateTime;
  updated_uts?: number;
  round?: number;
  roundname?: { _id?: number; name?: string | number };
  status?: BetScoutMatchStatus;
  teams?: {
    home?: BetScoutTeamRef;
    away?: BetScoutTeamRef;
  };
  result?: BetScoutMatchResult;
  periods?: BetScoutPeriodScoreMap | null;
  gamescore?: BetScoutGameScore | null;
  ground?: { _id?: number; name?: string } | string | null;
  neutralground?: boolean;
  walkover?: boolean;
  retired?: boolean;
  bestof?: number;
}

export interface BetScoutTournamentGroup {
  _doc?: 'tournament';
  _id: number;
  _sid?: number;
  _rcid?: number;
  _utid?: number;
  _seasonid?: number;
  name: string;
  abbr?: string;
  ground?: string | null;
  matches?: BetScoutMatchSummary[];
}

export interface BetScoutRealCategory {
  _doc?: 'realcategory';
  _id: number;
  _sid?: number;
  name: string;
  tournaments?: BetScoutTournamentGroup[];
}

export interface BetScoutDailySportMatchesResponse {
  sport?: {
    _doc?: 'sport';
    _id: number;
    name: string;
    realcategories?: BetScoutRealCategory[];
  };
}

export interface BetScoutMarketOutcome {
  _id: string | number;
  name: string;
  odds: number;
  probability?: number;
  active?: boolean;
}

export interface BetScoutMarket {
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
  outcomes?: BetScoutMarketOutcome[];
}

export interface BetScoutBatchMarketsResponse {
  matches?: Record<
    string,
    {
      _id?: number;
      markets?: BetScoutMarket[];
    }
  >;
}

export interface BetScoutMatchMarketsResponse {
  _id?: number;
  markets?: BetScoutMarket[];
}

export interface BetScoutSeasonMarketsResponse {
  _id?: number;
  markets?: BetScoutMarket[];
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
  match_obj: BetScoutMatchSummary;
  tournament: string;
  home: string;
  away: string;
}

export interface DailyOddsLookupResult {
  match_id?: string;
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
  odds_provider?: 'eu_retail' | 'consensus' | 'combined';
}

// ============================================================================
// C. Match Intelligence, Live Delta Stream, Squads, Injuries, Form & H2H
// ============================================================================

export interface BetScoutTimelineDeltaEvent {
  _doc?: 'event';
  _id?: number | string;
  _doctype?: string;
  type: string;
  matchid?: number;
  uts?: number;
  time?: number;
  period?: string;
  team?: 'home' | 'away' | string;
  result?: BetScoutPeriodScore;
  set_score?: { home: string | number; away: string | number };
  game_score?: { home: string | number; away: string | number };
  game_points?: { home: string | number; away: string | number };
  service?: '1' | '2' | string;
  player?: { _id?: number; name?: string };
}

export interface BetScoutMatchTimelineDeltaResponse {
  match?: BetScoutMatchSummary;
  events?: BetScoutTimelineDeltaEvent[];
}

export interface BetScoutEventGetResponse {
  events?: BetScoutTimelineDeltaEvent[];
  matches?: Record<string, BetScoutMatchSummary>;
  [key: string]: unknown;
}

export interface BetScoutMatchInfoResponse {
  match?: BetScoutMatchSummary & {
    stadium?: { _id?: number; name?: string; city?: string; capacity?: number };
    weather?: { pitch?: string; temperature?: number; wind?: string };
    referee?: { _id?: number; name?: string; nationality?: string };
    manager?: {
      home?: { _id?: number; name?: string };
      away?: { _id?: number; name?: string };
    };
  };
  tournament?: BetScoutUniqueTournament;
  realcategory?: BetScoutRealCategorySummary;
  [key: string]: unknown;
}

export interface BetScoutSquadPlayer {
  player?: {
    _id: number;
    name: string;
    shirtnumber?: number;
    position?: { _id?: number | string; name?: string; shortname?: string };
  };
  shirtnumber?: number;
  position?: { _id?: number | string; name?: string; shortname?: string };
}

export interface BetScoutMatchSquadsResponse {
  home?: {
    startinglineup?: { players?: BetScoutSquadPlayer[] };
    substitutes?: { players?: BetScoutSquadPlayer[] };
    manager?: { _id?: number; name?: string };
    formation?: string;
  };
  away?: {
    startinglineup?: { players?: BetScoutSquadPlayer[] };
    substitutes?: { players?: BetScoutSquadPlayer[] };
    manager?: { _id?: number; name?: string };
    formation?: string;
  };
  [key: string]: unknown;
}

export interface BetScoutSeasonInjuryItem {
  _doc?: 'playerstatus';
  _id?: number;
  _tid?: number;
  _playerid?: number;
  uniqueteam?: {
    _id: number;
    name?: string;
    mediumname?: string;
    abbr?: string;
  };
  player?: {
    _id: number;
    name: string;
    shirtnumber?: number | string;
    nationality?: BetScoutCountryCode;
    position?: {
      _id?: number | string;
      _type?: string;
      name?: string;
      shortname?: string;
      abbr?: string;
    };
  };
  status?: {
    /** See `PLAYER_STATUS_TYPES` (`0`=Other, `1`=Injured, `2`=Illness, `11`=Yellow Card Suspension, `12`=Yellow-Red Suspension, `13`=Red Card Suspension) */
    _id?: number;
    _statusid?: number;
    name?: string;
    status?: 'Missing' | 'Doubtful' | string;
    comment?: string;
    missing?: number;
    doubtful?: number;
    start?: BetScoutDateTime;
    end?: BetScoutDateTime | null;
  };
}

export interface TeamMissingPlayerEntry {
  player_id: number;
  name: string;
  position: string;
  shirt_number: string | number | null;
  /** Specific cause (`"Injured"`, `"Ill"`, `"Suspended"`, `"Other"`) */
  cause: string;
  /** Availability status (`"Missing"`, `"Doubtful"`) */
  status: string;
  status_id: number;
  start_date: string | null;
  end_date: string | null;
  start_uts: number | null;
  end_uts: number | null;
  /** `true` if `end_uts` is null or `>= referenceUts` */
  is_active: boolean;
}

export interface BetScoutTeamFormEntry {
  type: 'W' | 'D' | 'L' | string;
  matchid?: number;
  tournament?: { _id?: number; name?: string };
}

export interface BetScoutTeamStreak {
  type: 'W' | 'D' | 'L' | string;
  value: number;
}

export interface BetScoutMatchFormResponse {
  teams?: {
    home?: {
      team?: BetScoutTeamRef;
      streak?: BetScoutTeamStreak;
      form?: BetScoutTeamFormEntry[];
    };
    away?: {
      team?: BetScoutTeamRef;
      streak?: BetScoutTeamStreak;
      form?: BetScoutTeamFormEntry[];
    };
  };
}

export interface BetScoutNextMatchDifficulty {
  matchid?: number;
  opponent?: BetScoutTeamRef;
  homeAway?: 'home' | 'away';
  matchdifficultyrating?: number;
}

export interface BetScoutTeamStreaksResponse {
  team?: BetScoutTeamRef;
  lastmatchesform?: string[] | BetScoutTeamFormEntry[];
  streaks?: Record<
    string,
    {
      total?: { value?: number };
      home?: { value?: number };
      away?: { value?: number };
    }
  >;
  nextmatches?: BetScoutNextMatchDifficulty[];
  [key: string]: unknown;
}

export interface BetScoutHistoricalMatchItem {
  _id: number;
  _sid?: number;
  _rcid?: number;
  _tid?: number;
  _utid?: number;
  _seasonid?: number;
  _dt?: BetScoutDateTime;
  time?: BetScoutDateTime;
  round?: number;
  roundname?: { _id?: number; name?: string | number };
  teams?: {
    home?: BetScoutTeamRef;
    away?: BetScoutTeamRef;
  };
  result?: BetScoutMatchResult;
  periods?: BetScoutPeriodScoreMap;
  status?: BetScoutMatchStatus;
  ground?: { _id?: number; name?: string } | string | null;
  bestof?: number;
  walkover?: boolean;
  retired?: boolean;
}

export interface BetScoutMatchHead2HeadResponse {
  matches?: BetScoutHistoricalMatchItem[];
  [key: string]: unknown;
}

export interface BetScoutTeamMatchesResponse {
  team?: BetScoutTeamRef;
  matches?: BetScoutHistoricalMatchItem[];
  tournaments?: Record<string, BetScoutUniqueTournament>;
  uniquetournaments?: Record<string, BetScoutUniqueTournament>;
  realcategories?: Record<string, BetScoutRealCategorySummary>;
}

export interface BetScoutMatchSituationItem {
  time?: number;
  injurytime?: number;
  team?: 'home' | 'away';
  situation?: 'attack' | 'dangerous_attack' | 'safe' | string;
  x?: number;
  y?: number;
}

export interface BetScoutMatchSituationsResponse {
  _id?: number;
  situations?: BetScoutMatchSituationItem[];
}

export interface BetScoutMatchStatsResponse {
  match?: BetScoutMatchSummary;
  stats?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface LiveTimelineDeltaSummary {
  match_id?: number | string;
  season_id?: number | null;
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

export interface InjuryGateEvaluation {
  status: string;
  backed_out: string[];
  opp_out: string[];
  backed_fwd_out?: number;
  backed_gk_out?: number;
  prob_adjustment: number;
  veto_recommended: boolean;
}

// ============================================================================
// D. Team & Player Profiles, Season Stats, Squads, Lineups & Transfers
// ============================================================================

export interface BetScoutJerseyColors {
  base?: string;
  sleeve?: string;
  number?: string;
  stripes?: string;
  type?: string;
  sleevelong?: string;
  real?: boolean;
}

export interface BetScoutTennisGroundStatItem {
  _id?: number;
  groundid: number;
  ground: string;
  total: number;
  matcheswon: number;
  matcheswon_percent: number;
  matcheslost: number;
  matcheslost_percent: number;
}

export interface BetScoutTennisRankingSnapshot {
  _doc?: 'ranking';
  teamid?: number;
  rankingtype?: number;
  gender?: 'men' | 'women' | string;
  ranking: number;
  points: number;
}

/**
 * Unified Team or Individual Player Profile (`getTeamProfile(teamId)`).
 * - For team sports (e.g. `2692` AC Milan): includes `founded`, `homejersey`, `awayjersey`, `gkjersey`, `stadium`, `manager`, and `tournaments`.
 * - For individual sports (e.g. `14882` Novak Djokovic in Tennis): includes `turnedpro`, `dateofbirth`, `nationality`, `height`, `weight`, `plays`, `coachname`, `favouritesurface`, `singlesrank`, `doublesrank`, `highestranking`, `groundstats`, `ranking`, and `performance`.
 */
export interface BetScoutTeamProfileResponse {
  team?: BetScoutTeamRef;
  countrycode?: BetScoutCountryCode;
  twitter?: string | null;
  hashtag?: string | null;
  matchup?: string | null;
  // Team-sport club attributes (e.g. Soccer team `2692` AC Milan)
  homejersey?: BetScoutJerseyColors;
  awayjersey?: BetScoutJerseyColors;
  awayjersey2?: BetScoutJerseyColors;
  gkjersey?: BetScoutJerseyColors;
  stadium?: {
    _id?: number;
    name?: string;
    city?: string;
    capacity?: number;
    country?: string;
    googlecoords?: string;
  };
  manager?: {
    _id?: number;
    name?: string;
    birthdate?: BetScoutDateTime;
    nationality?: BetScoutCountryCode;
  };
  tournaments?: BetScoutUniqueTournament[];
  // Individual player attributes (e.g. Tennis player `14882` Novak Djokovic)
  turnedpro?: string | number | null;
  dateofbirth?: string | null;
  nationality?: string | null;
  cc?: string | BetScoutCountryCode | null;
  ioc?: string | null;
  height?: string | number | null;
  weight?: string | number | null;
  /** Handedness (`'Right'` | `'Left'`) */
  plays?: string | null;
  agestarted?: number | null;
  ageturnedpro?: number | null;
  singlesrank?: number | null;
  doublesrank?: number | null;
  coachname?: string | null;
  favouritesurface?: string | null;
  highestranking?: {
    singles?: { date?: string; ranking?: number };
    doubles?: { date?: string; ranking?: number };
  };
  groundstats?: BetScoutTennisGroundStatItem[];
  ranking?: BetScoutTennisRankingSnapshot;
  doublesranking?: BetScoutTennisRankingSnapshot;
  performance?: Array<{
    _doc?: string;
    _typeid?: number;
    typename?: string;
    value?: number;
  }>;
  [key: string]: unknown;
}

export interface BetScoutSeasonDescriptor {
  _id: string | number;
  _doc?: 'season';
  _utid?: number;
  _sid?: number;
  name: string;
  abbr?: string;
  year?: string;
  current?: boolean;
  currentseasonid?: number;
  containsdata?: boolean;
  start?: BetScoutDateTime;
  end?: BetScoutDateTime;
}

export interface BetScoutTeamSeasonsResponse {
  seasons?: BetScoutSeasonDescriptor[];
  tournaments?: Record<string, BetScoutUniqueTournament> | BetScoutUniqueTournament[];
  [key: string]: unknown;
}

export interface BetScoutTeamSeasonStatsResponse {
  uniqueteam?: BetScoutTeamRef;
  season?: BetScoutSeasonDescriptor;
  /** Per-game season team averages (`goal_attempts`, `shots_on_goal`, `ball_possession`, `corner_kicks`, `cards_given`, `freekicks`, `offside`, `shots_blocked`, etc.) */
  stats?: Record<string, string | number>;
}

export interface BetScoutTeamSeasonMatchesResponse {
  season?: BetScoutSeasonDescriptor;
  matches?: BetScoutHistoricalMatchItem[];
}

export interface BetScoutTeamPositionHistoryResponse {
  season?: BetScoutSeasonDescriptor;
  teamcount?: number;
  roundcount?: number;
  teams?: Record<string, BetScoutTeamRef>;
  positiondata?: Record<string, number[] | Record<string, unknown>>;
  [key: string]: unknown;
}

export interface BetScoutExtendedPlayer {
  _doc?: 'extendedplayer' | 'player';
  _id: number;
  name: string;
  fullname?: string;
  birthdate?: BetScoutDateTime;
  nationality?: BetScoutCountryCode;
  position?: {
    _id?: string | number;
    _type?: string;
    name?: string;
    shortname?: string;
    abbr?: string;
  };
  primaryposition?: {
    _id?: string | number;
    name?: string;
    shortname?: string;
    abbr?: string;
  };
  shirtnumber?: number | string;
  height?: number;
  weight?: number;
  foot?: 'Right' | 'Left' | 'Both' | string;
  birthplace?: string;
  birthcountry?: BetScoutCountryCode;
  marketvalue?: number | string;
  [key: string]: unknown;
}

export interface BetScoutTeamSquadResponse {
  team?: BetScoutTeamRef;
  players?: BetScoutExtendedPlayer[];
  managers?: BetScoutExtendedPlayer[];
  roles?: unknown[];
  squadinfo?: Record<string, unknown>;
  seasons?: Record<string, BetScoutSeasonDescriptor>;
}

export interface BetScoutTeamUsualLineupResponse {
  formation?: string;
  players?: BetScoutExtendedPlayer[];
}

export interface BetScoutTeamTransfersResponse {
  team?: BetScoutTeamRef;
  transfers?: Record<string, unknown> | unknown[];
  uniqueteams?: Record<string, BetScoutTeamRef>;
}

export interface BetScoutTeamTournamentsResponse {
  uniqueteam?: BetScoutTeamRef;
  seasons?: Record<string, BetScoutSeasonDescriptor>;
  stats?: Record<string, unknown>;
  players?: Record<string, unknown>;
}

export interface BetScoutTeamSeasonOfficialsResponse {
  season?: BetScoutSeasonDescriptor;
  officials?: Array<{
    referee?: { _id?: number; name?: string; nationality?: BetScoutCountryCode };
    matches?: number;
    yellowcards?: number;
    redcards?: number;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
}

export interface BetScoutPlayerCareerStatsResponse {
  player?: BetScoutExtendedPlayer;
  seasons?: Record<string, unknown> | unknown[];
  uniqueteams?: Record<string, BetScoutTeamRef>;
  translations?: Record<string, string>;
  [key: string]: unknown;
}

export interface BetScoutPlayerFactsResponse {
  player?: BetScoutExtendedPlayer;
  roles?: unknown[];
  stats?: Record<string, unknown>;
  teams?: Record<string, BetScoutTeamRef>;
  seasons?: Record<string, BetScoutSeasonDescriptor>;
  uniquetournaments?: Record<string, BetScoutUniqueTournament>;
  [key: string]: unknown;
}

export interface BetScoutPlayerSeasonMatchesResponse {
  player?: BetScoutExtendedPlayer;
  season?: BetScoutSeasonDescriptor;
  matches?: BetScoutHistoricalMatchItem[];
  total?: Record<string, unknown>;
  [key: string]: unknown;
}

// ============================================================================
// E. Tennis Career & Surface Analytics, Standings Tables & Goal Intervals
// ============================================================================

export interface BetScoutTennisSurfaceRecord {
  groundid?: number | string;
  wins?: number;
  losses?: number;
  tournaments?: number;
  titles?: number;
}

export interface BetScoutTennisSurfaceStatsResponse {
  player?: BetScoutTeamRef;
  /** Keyed by season year (`"2026"`, `"2025"`, ..., `"2004"`), then by `groundId` (`"0"`=All, `"1"`=Clay, `"2"`=Hard Outdoor, `"3"`=Indoor, `"4"`=Grass) plus optional `"ranking"` */
  singles?: Record<string, Record<string, BetScoutTennisSurfaceRecord | number>>;
  doubles?: Record<string, Record<string, BetScoutTennisSurfaceRecord | number>>;
  mixed?: Record<string, Record<string, BetScoutTennisSurfaceRecord | number>>;
}

export interface TennisSurfaceSummary {
  season_wl: string;
  hard_wl: string;
  clay_wl: string;
  indoor_wl: string;
  grass_wl?: string;
}

export interface BetScoutTennisRankingResponse {
  type?: string;
  year?: number;
  week?: number;
  rankings?: Array<{
    rank: number;
    points: number;
    team?: BetScoutTeamRef;
  }>;
  [key: string]: unknown;
}

export interface BetScoutTablePromotion {
  _doc?: 'promotion';
  _id: number;
  name: string;
  shortname?: string;
  cssclass?: string;
  position?: number;
}

export interface BetScoutSeasonTableRow {
  _doc?: 'tablerow';
  _id?: number;
  pos: number;
  posHome?: number;
  posAway?: number;
  sortPositionTotal?: number;
  sortPositionHome?: number;
  sortPositionAway?: number;
  /** Rank change since previous matchday (`+1`, `-2`, `0`) */
  changeTotal?: number;
  changeHome?: number;
  changeAway?: number;
  team: BetScoutTeamRef;
  promotion?: BetScoutTablePromotion | null;
  /** Matches played (Total / Home / Away) */
  total?: number;
  home?: number;
  away?: number;
  winTotal?: number;
  winHome?: number;
  winAway?: number;
  drawTotal?: number;
  drawHome?: number;
  drawAway?: number;
  lossTotal?: number;
  lossHome?: number;
  lossAway?: number;
  goalsForTotal?: number;
  goalsForHome?: number;
  goalsForAway?: number;
  goalsAgainstTotal?: number;
  goalsAgainstHome?: number;
  goalsAgainstAway?: number;
  goalDiffTotal?: number;
  goalDiffHome?: number;
  goalDiffAway?: number;
  pointsTotal?: number;
  pointsHome?: number;
  pointsAway?: number;
  [key: string]: unknown;
}

export interface BetScoutLeagueTable {
  _doc?: 'statistics_leaguetable';
  _id?: string | number;
  seasonid?: string | number;
  name?: string;
  abbr?: string;
  groupname?: string | null;
  maxrounds?: number;
  currentround?: number;
  totalrows?: number;
  tournament?: BetScoutUniqueTournament;
  realcategory?: BetScoutRealCategorySummary;
  rules?: {
    _doc?: 'tiebreakrule';
    _id?: number;
    name?: string;
  };
  tablerows?: BetScoutSeasonTableRow[];
  [key: string]: unknown;
}

export interface BetScoutSeasonTablesResponse {
  _id?: string | number;
  name?: string;
  abbr?: string;
  year?: string;
  tables?: BetScoutLeagueTable[];
  [key: string]: unknown;
}

export interface BetScoutDynamicTableResponse {
  season?: BetScoutSeasonTablesResponse;
  [key: string]: unknown;
}

export interface BetScoutFormTableMatchItem {
  typeid: 'W' | 'D' | 'L' | string;
  value: 'W' | 'D' | 'L' | string;
  homematch?: boolean;
  neutralground?: boolean;
  matchid?: number;
}

export interface BetScoutFormTableTeamEntry {
  team: BetScoutTeamRef;
  position?: { total?: number; home?: number; away?: number };
  played?: { total?: number; totalhome?: number; totalaway?: number; home?: number; away?: number };
  win?: { total?: number; totalhome?: number; totalaway?: number; home?: number; away?: number };
  draw?: { total?: number; totalhome?: number; totalaway?: number; home?: number; away?: number };
  loss?: { total?: number; totalhome?: number; totalaway?: number; home?: number; away?: number };
  goalsfor?: { total?: number; totalhome?: number; totalaway?: number; home?: number; away?: number };
  goalsagainst?: {
    total?: number;
    totalhome?: number;
    totalaway?: number;
    home?: number;
    away?: number;
  };
  goaldifference?: {
    total?: number;
    totalhome?: number;
    totalaway?: number;
    home?: number;
    away?: number;
  };
  points?: { total?: number; totalhome?: number; totalaway?: number; home?: number; away?: number };
  form?: {
    total?: BetScoutFormTableMatchItem[];
    home?: BetScoutFormTableMatchItem[];
    away?: BetScoutFormTableMatchItem[];
  };
}

export interface BetScoutFormTableResponse {
  season?: BetScoutSeasonDescriptor;
  winpoints?: number;
  losspoints?: number;
  currentround?: number;
  teams?: BetScoutFormTableTeamEntry[];
  [key: string]: unknown;
}

export interface EnrichedStandingsRow {
  pos: number;
  pos_home: number | null;
  pos_away: number | null;
  /** Position delta vs previous round (`+1` = moved up 1 spot, `-2` = dropped 2 spots, `0` = unchanged) */
  change_total: number;
  change_home: number;
  change_away: number;
  team_id: number;
  team_uid: number;
  team_name: string;
  team_abbr: string;
  promotion: string | null;
  promotion_short: string | null;
  played: { total: number; home: number; away: number };
  win: { total: number; home: number; away: number };
  draw: { total: number; home: number; away: number };
  loss: { total: number; home: number; away: number };
  goals_for: { total: number; home: number; away: number };
  goals_against: { total: number; home: number; away: number };
  goal_diff: { total: number; home: number; away: number };
  points: { total: number; home: number; away: number };
  /** Chronological recent form array (`['W', 'W', 'D', 'W', 'L']`) */
  form_total: string[];
  form_home: string[];
  form_away: string[];
  form_entries_total: BetScoutFormTableMatchItem[];
}

export interface EnrichedLeagueTableBundle {
  ok: boolean;
  season_id: string | number;
  season_name: string | null;
  current_round: number | null;
  max_rounds: number | null;
  tiebreak_rules: string | null;
  rows: EnrichedStandingsRow[];
}

export interface BetScoutSeasonOverUnderResponse {
  teams?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BetScoutGoalMinuteBucket {
  total?: number;
  home?: number;
  away?: number;
  percentage?: number;
}

export interface BetScoutSplitMetric {
  total?: number;
  home?: number;
  away?: number;
}

export interface BetScoutTeamScoringConcedingResponse {
  team?: BetScoutTeamRef;
  stats?: {
    totalmatches?: BetScoutSplitMetric;
    totalwins?: BetScoutSplitMetric;
    totaldraws?: BetScoutSplitMetric;
    totallosses?: BetScoutSplitMetric;
    scoring?: {
      goalsscored?: BetScoutSplitMetric;
      atleastonegoal?: BetScoutSplitMetric;
      failedtoscore?: BetScoutSplitMetric;
      scoringathalftime?: BetScoutSplitMetric;
      scoringatfulltime?: BetScoutSplitMetric;
      bothteamsscored?: BetScoutSplitMetric;
      goalsscoredfirsthalf?: BetScoutSplitMetric;
      goalsscoredaverage?: BetScoutSplitMetric;
      goalsscoredfirsthalfaverage?: BetScoutSplitMetric;
      scoringathalftimeaverage?: BetScoutSplitMetric;
      bothteamsscoredaverage?: BetScoutSplitMetric;
      goalsbyminutes?: Record<string, BetScoutGoalMinuteBucket>;
    };
    conceding?: {
      goalsconceded?: BetScoutSplitMetric;
      cleansheets?: BetScoutSplitMetric;
      goalsconcededfirsthalf?: BetScoutSplitMetric;
      goalsconcededaverage?: BetScoutSplitMetric;
      goalsconcededfirsthalfaverage?: BetScoutSplitMetric;
      goalsbyminutes?: Record<string, BetScoutGoalMinuteBucket>;
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

export interface BetScoutRefereeSeasonStatsResponse {
  referee?: { _id?: number; name?: string; nationality?: string };
  stats?: {
    matches?: number;
    yellowcards?: number;
    redcards?: number;
    penalties?: number;
  };
  [key: string]: unknown;
}

export interface MatchIntelligenceBundle {
  ok: boolean;
  found: boolean;
  match_id?: number | string;
  season_id?: number | null;
  home_uid?: number | null;
  away_uid?: number | null;
  tournament?: string;
  primary_markets?: ParsedPrematchMarkets;
  consensus_markets?: ParsedPrematchMarkets;
  home_injuries?: string[];
  away_injuries?: string[];
  injury_gate?: InjuryGateEvaluation | Record<string, never>;
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

export interface TeamIntelligenceBundle {
  ok: boolean;
  team_id: number;
  profile: BetScoutTeamProfileResponse | null;
  seasons: BetScoutSeasonDescriptor[];
  active_season_id: string | number | null;
  season_stats: Record<string, string | number> | null;
  scoring_conceding_splits: BetScoutTeamScoringConcedingResponse | null;
  goal_intervals: TeamGoalIntervalsSummary;
  usual_lineup: BetScoutTeamUsualLineupResponse | null;
  squad_count: number;
  squad: BetScoutExtendedPlayer[];
  missing_players: TeamMissingPlayerEntry[];
  streaks: string[];
  next_matches_difficulty: BetScoutNextMatchDifficulty[];
  last_matches: BetScoutHistoricalMatchItem[];
  next_matches: BetScoutHistoricalMatchItem[];
}

export interface TennisPlayerIntelligenceBundle {
  ok: boolean;
  player_id: number;
  profile: BetScoutTeamProfileResponse | null;
  current_surface_summary: TennisSurfaceSummary;
  career_surface_stats: BetScoutTennisSurfaceStatsResponse | null;
  streaks: string[];
  last_matches: BetScoutHistoricalMatchItem[];
  next_matches: BetScoutHistoricalMatchItem[];
}

// ============================================================================
// F. Visual Assets (Team Logos, Country Flags, Player Kit SVG & Venue Coordinates)
// ============================================================================

export type TeamLogoSize = 'small' | 'medium' | 'big';
export type NcaaLogoSize = 'ap250x188ut' | 'ap500x375ut' | 'ap1000x750ut';

export interface TeamLogoOptions {
  /** Standard crest size (`'small'` | `'medium'` | `'big'`, default: `'big'`) */
  size?: TeamLogoSize;
  /** Set `true` for US College / NCAA teams using the `teams/{ncaaSize}/{teamId}.png` path */
  ncaa?: boolean;
  /** NCAA emblem resolution (`'ap250x188ut'` | `'ap500x375ut'` | `'ap1000x750ut'`) */
  ncaaSize?: NcaaLogoSize;
  /** Optional custom image CDN origin */
  imageBaseUrl?: string;
}

export interface CountryFlagOptions {
  /** Output image format (`'svg'` vector or `'png'` raster, default: `'svg'`) */
  format?: 'svg' | 'png';
  /** Aspect ratio when `format === 'svg'` (`'4x3'` | `'1x1'`, default: `'4x3'`) */
  ratio?: '4x3' | '1x1';
  /** Size when `format === 'png'` (`'small'` | `'medium'` | `'big'`, default: `'medium'`) */
  size?: TeamLogoSize;
  /** Optional custom image CDN origin */
  imageBaseUrl?: string;
}

export interface JerseySvgOptions {
  /** Optional player shirt number rendered on the jersey (`"16"`, `10`, etc.) */
  shirtNumber?: number | string | null;
  /** Rendered SVG width/height in pixels (default: `96`) */
  sizePx?: number;
}

// ============================================================================
// G. Insights, Editorial Commentary, Venues & Futures Markets
// ============================================================================

export interface BetScoutMatchFunFactItem {
  _id: number;
  _typeid?: number;
  sentence: string;
}

export interface BetScoutMatchFunFactsResponse {
  _id: number;
  funfacts?: string[];
  facts?: BetScoutMatchFunFactItem[];
}

export interface BetScoutMatchPhraseItem {
  _doc?: 'phrase';
  _id: string | number;
  uts?: number;
  typeid?: number | null;
  funfactid?: number;
  text: string;
  sentence?: string;
  time?: number;
  injurytime?: number;
  event?: Record<string, unknown>;
}

export interface BetScoutMatchPhrasesResponse {
  match?: BetScoutMatchSummary;
  owncommentary?: boolean;
  phrases?: BetScoutMatchPhraseItem[];
}

export interface BetScoutSeasonLeagueSummaryResponse {
  _doc?: 'summary';
  matches?: {
    played?: number;
    home_wins?: number;
    draws?: number;
    away_wins?: number;
  };
  goals?: {
    total?: number;
    pr_match?: number;
    pr_match_home?: number;
    pr_match_away?: number;
  };
  overunder?: Record<string, number>;
  clean_sheet?: {
    total?: number;
    pr_match?: number;
  };
  both_teams_to_score?: {
    total?: number;
    pr_match?: number;
  };
  [key: string]: unknown;
}

export interface BetScoutTeamPlayerFactEntry {
  player?: BetScoutExtendedPlayer & {
    marketvalue?: number;
    shirtnumber?: string | number;
    membersince?: BetScoutDateTime;
    twitter?: string;
  };
  stats?: {
    _doc?: 'toplistentry';
    _id?: number;
    playerid?: number;
    teams?: Record<
      string,
      {
        seasons?: Record<
          string,
          {
            active?: boolean;
            lastevent?: string;
            started?: number;
            matches?: number;
            minutes_played?: number;
            substituted_in?: number;
            substituted_out?: number;
            goals?: number;
            assists?: number;
            yellow_cards?: number;
            red_cards?: number;
            team_scored?: number;
            team_conceded?: number;
            matches_won?: number;
            matches_drawn?: number;
            matches_lost?: number;
            [key: string]: unknown;
          }
        >;
      }
    >;
    total?: Record<string, number>;
  };
}

export type BetScoutTeamPlayerFactsMap = Record<string, BetScoutTeamPlayerFactEntry>;

export interface BetScoutStadiumInfo {
  _doc?: 'stadium';
  _id: string | number;
  name: string;
  description?: string;
  city?: string;
  country?: string;
  state?: string | null;
  cc?: BetScoutCountryCode;
  capacity?: string | number;
  constryear?: string | number;
  address?: string;
  phone?: string;
  url?: string;
  /** Latitude,Longitude string (e.g. `"45.478025,9.124206"` for Stadio Giuseppe Meazza / San Siro) */
  googlecoords?: string;
  pitchsize?: {
    x?: number;
    y?: number;
  };
  hometeams?: BetScoutTeamRef[];
}

export interface BetScoutSeasonVenuesResponse {
  season?: BetScoutSeasonDescriptor;
  stadiums?: BetScoutStadiumInfo[];
}

export interface BetScoutVenueStatsResponse {
  stadium?: BetScoutStadiumInfo;
  season?: BetScoutSeasonDescriptor;
  statistics?: {
    venue_home_goals?: string | number;
    venue_away_goals?: string | number;
    venue_home_wins?: string | number;
    venue_away_wins?: string | number;
    venue_draws?: string | number;
    venue_home_corner_kicks?: string | number;
    venue_away_corner_kicks?: string | number;
    venue_yellow_cards?: string | number;
    venue_red_cards?: string | number;
    venue_goals_0_15?: string | number;
    venue_goals_16_30?: string | number;
    venue_goals_31_45?: string | number;
    venue_goals_46_60?: string | number;
    venue_goals_61_75?: string | number;
    venue_goals_76_90?: string | number;
    venue_top_scorer?: BetScoutExtendedPlayer[];
    [key: string]: unknown;
  };
  lastmatches?: BetScoutHistoricalMatchItem[];
  nextmatches?: BetScoutHistoricalMatchItem[];
  [key: string]: unknown;
}

export interface BetScoutSeasonTopListResponse {
  season?: BetScoutSeasonDescriptor;
  players?: Array<{
    player?: BetScoutExtendedPlayer;
    team?: BetScoutTeamRef;
    goals?: string | number;
    assists?: string | number;
    cards?: string | number;
    yellow_cards?: string | number;
    red_cards?: string | number;
    matches?: string | number;
    [key: string]: unknown;
  }>;
  teams?: Record<string, BetScoutTeamRef>;
}

export interface BetScoutUniqueTeamMarketsResponse {
  matches?: Record<
    string,
    {
      _id?: number;
      markets?: BetScoutMarket[];
    }
  >;
}

export interface BetScoutOddsFormatEntry {
  _doc?: string;
  decimal?: string | number;
  uk?: string;
  us?: string | number;
  [key: string]: unknown;
}

