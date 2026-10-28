/**
 * Sportradar StatsHub & Tipico Gismo API Constants, Catalogs & Outcome Mappings.
 * Reference: `docs/SPORTRADAR_STATSHUB.md`
 */

export const STATSHUB_TIPICO_URL = 'https://statshub.sportradar.com/tipico/en/';
export const STATSHUB_SPORTRADAR_URL = 'https://statshub.sportradar.com/sportradar/en/';
export const DIRECT_STATS_FN_BASE_URL = 'https://stats.fn.sportradar.com';
export const FISHNET_BASE_URL = 'https://sh.fn.sportradar.com';

export const SR_BOOKMAKER_IDS = {
  /** Sportradar Main Unified Odds Feed (UOF consensus, 17+ markets/match) */
  SPORTRADAR_UOF: 0,
  /** Tipico retail bookmaker feed (`sr:crawler_odds:176`, 11+ markets/match) */
  TIPICO: 176,
} as const;

export const SR_SERVICE_IDS = {
  /** General statistics tree */
  STATISTICS: 41,
  /** Tipico StatsHub (`53` sports) */
  TIPICO_STATSHUB: 67,
  /** Sportradar Unlimited StatsHub (`56` sports) */
  SPORTRADAR_UNLIMITED: 69,
} as const;

export const SR_MARKET_IDS = {
  /** 3-Way 1X2 (`{$competitor1}`, `draw`, `{$competitor2}`) */
  MATCH_1X2: 1,
  /** Double Chance (`1X`, `12`, `X2`) */
  DOUBLE_CHANCE: 10,
  /** Draw No Bet (DNB) */
  DRAW_NO_BET: 11,
  /** 3-Way European Handicap (`specifiers.hcp`) */
  EUROPEAN_HANDICAP_3WAY: 14,
  /** 2-Way Asian Handicap (`specifiers.hcp`) */
  ASIAN_HANDICAP_2WAY: 16,
  /** Total Goals Over/Under (`specifiers.total`) */
  TOTAL_GOALS: 18,
  /** 28-Outcome Correct Score Matrix (`sr:outcome:110` .. `sr:outcome:166`) */
  CORRECT_SCORE: 41,
  /** Named Correct Score (`1:0`, `2:1`, etc.) */
  CORRECT_SCORE_NAMED: 45,
  /** 1st Half 1X2 */
  FIRST_HALF_1X2: 60,
  /** 1st Half Handicap */
  FIRST_HALF_HANDICAP: 65,
  /** 1st Half Total Goals */
  FIRST_HALF_TOTAL: 68,
  /** 2nd Half Handicap */
  SECOND_HALF_HANDICAP: 87,
  /** Tennis / Table Tennis / Darts 2-Way Match Winner */
  TENNIS_MATCH_WINNER: 186,
  /** Tennis Total Games Over/Under (`specifiers.total`) */
  TENNIS_TOTAL_GAMES: 189,
  /** Tennis Set-by-Set Winner */
  TENNIS_SET_WINNER: 202,
  /** Basketball / NFL 2-Way Winner (incl. Overtime) */
  US_SPORTS_WINNER_OT: 219,
  /** Basketball / NFL Point Spread (incl. Overtime) */
  US_SPORTS_SPREAD_OT: 223,
  /** Basketball / NFL Total Points Over/Under (incl. Overtime) */
  US_SPORTS_TOTAL_OT: 225,
  /** Ice Hockey 2-Way Winner (incl. Overtime & Penalties) */
  HOCKEY_WINNER_OT_SO: 406,
} as const;

export const SR_TENNIS_GROUND_IDS = {
  ALL_SURFACES: 0,
  CLAY: 1,
  HARD_OUTDOOR: 2,
  GRASS: 3,
  HARD_INDOOR: 4,
} as const;

/**
 * Complete 56-Sport Catalog from Sportradar StatsHub (`config_sports/69/0` & `config_sports/67/0`).
 */
export const SR_ALL_SPORTS_CATALOG: Readonly<Record<number, string>> = {
  1: 'Soccer',
  5: 'Tennis',
  4: 'Ice Hockey',
  2: 'Basketball',
  6: 'Handball',
  23: 'Volleyball',
  3: 'Baseball',
  7: 'Floorball',
  9: 'Golf',
  12: 'Rugby',
  13: 'Aussie Rules',
  15: 'Bandy',
  16: 'American Football',
  17: 'Cycling',
  18: 'Specials',
  19: 'Snooker',
  20: 'Table Tennis',
  21: 'Cricket',
  22: 'Darts',
  24: 'Field hockey',
  26: 'Waterpolo',
  28: 'Curling',
  29: 'Futsal',
  31: 'Badminton',
  34: 'Beach Volley',
  36: 'Athletics',
  37: 'Squash',
  40: 'Formula 1',
  43: 'Alpine Skiing',
  44: 'Biathlon',
  45: 'Bobsleigh',
  46: 'Cross-Country',
  47: 'Nordic Combined',
  48: 'Ski Jumping',
  49: 'Snowboard',
  50: 'Speed Skating',
  51: 'Luge',
  52: 'Swimming',
  54: 'Softball',
  60: 'Beach Soccer',
  61: 'Pesapallo',
  71: 'Padel',
  101: 'Rally',
  117: 'MMA',
  129: 'Indy Racing',
  131: 'Speedway',
  134: 'ESport King of Glory',
  135: 'Gaelic Football',
  137: 'eSoccer',
  138: 'Kabaddi',
  153: 'eBasketball',
  155: 'Basketball 3x3',
  188: 'Touring Car Racing',
  190: 'Motorcycle Racing',
  191: 'Stock Car Racing',
  195: 'eIce Hockey',
};

/**
 * Sportradar `sportId` mapping by slug/alias.
 */
export const SR_SPORT_IDS: Readonly<Record<string, number>> = {
  soccer: 1,
  football_soccer: 1,
  basketball: 2,
  nba: 2,
  wnba: 2,
  baseball: 3,
  mlb: 3,
  hockey: 4,
  ice_hockey: 4,
  nhl: 4,
  tennis: 5,
  atp: 5,
  wta: 5,
  handball: 6,
  floorball: 7,
  golf: 9,
  rugby: 12,
  aussie_rules: 13,
  bandy: 15,
  football: 16,
  american_football: 16,
  nfl: 16,
  cycling: 17,
  specials: 18,
  snooker: 19,
  table_tennis: 20,
  cricket: 21,
  darts: 22,
  volleyball: 23,
  field_hockey: 24,
  waterpolo: 26,
  curling: 28,
  futsal: 29,
  badminton: 31,
  beach_volley: 34,
  athletics: 36,
  squash: 37,
  formula_1: 40,
  f1: 40,
  alpine_skiing: 43,
  biathlon: 44,
  bobsleigh: 45,
  cross_country: 46,
  nordic_combined: 47,
  ski_jumping: 48,
  snowboard: 49,
  speed_skating: 50,
  luge: 51,
  swimming: 52,
  softball: 54,
  beach_soccer: 60,
  pesapallo: 61,
  padel: 71,
  rally: 101,
  mma: 117,
  ufc: 117,
  indy_racing: 129,
  speedway: 131,
  esport_king_of_glory: 134,
  gaelic_football: 135,
  esoccer: 137,
  kabaddi: 138,
  ebasketball: 153,
  basketball_3x3: 155,
  touring_car_racing: 188,
  motorcycle_racing: 190,
  motogp: 190,
  stock_car_racing: 191,
  nascar: 191,
  eice_hockey: 195,
};

/**
 * Sportradar OddsAPI `marketId=41` (Correct Score) standard outcome ID -> `"H:A"` score mapping (28 outcomes).
 */
export const SR_CORRECT_SCORE_OUTCOMES: Readonly<Record<string, string>> = {
  'sr:outcome:110': '0:0',
  'sr:outcome:114': '1:0',
  'sr:outcome:116': '2:0',
  'sr:outcome:118': '3:0',
  'sr:outcome:120': '4:0',
  'sr:outcome:122': '5:0',
  'sr:outcome:124': '6:0',
  'sr:outcome:126': '0:1',
  'sr:outcome:128': '1:1',
  'sr:outcome:130': '2:1',
  'sr:outcome:132': '3:1',
  'sr:outcome:134': '4:1',
  'sr:outcome:136': '5:1',
  'sr:outcome:138': '0:2',
  'sr:outcome:140': '1:2',
  'sr:outcome:142': '2:2',
  'sr:outcome:144': '3:2',
  'sr:outcome:146': '4:2',
  'sr:outcome:148': '0:3',
  'sr:outcome:150': '1:3',
  'sr:outcome:152': '2:3',
  'sr:outcome:154': '3:3',
  'sr:outcome:156': '0:4',
  'sr:outcome:158': '1:4',
  'sr:outcome:160': '2:4',
  'sr:outcome:162': '0:5',
  'sr:outcome:164': '1:5',
  'sr:outcome:166': '0:6',
};

/**
 * Resolve a sport slug (`'soccer'`, `'tennis'`, `'nhl'`) or numeric ID (`1`, `5`) to a canonical Sportradar `sportId`.
 */
export function resolveSportId(sportOrId: string | number): number {
  if (typeof sportOrId === 'number' && Number.isFinite(sportOrId)) {
    return sportOrId;
  }
  const clean = String(sportOrId || '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_');
  const parsedInt = Number.parseInt(clean, 10);
  if (!Number.isNaN(parsedInt) && String(parsedInt) === clean) {
    return parsedInt;
  }
  return SR_SPORT_IDS[clean] ?? 1;
}
