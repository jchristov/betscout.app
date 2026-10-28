/**
 * Name Normalization, Market Parsing & Delta-Stream Utilities for the BetScout Data SDK.
 */

import { CORRECT_SCORE_OUTCOMES, MARKET_IDS } from './constants.js';
import {
  buildUpstreamCountryFlagUrl,
  buildUpstreamTeamLogoUrl,
} from './internal/transport.js';
import type {
  BetScoutDocument,
  BetScoutHistoricalMatchItem,
  BetScoutJerseyColors,
  BetScoutMarket,
  BetScoutMatchSummary,
  BetScoutMatchTimelineDeltaResponse,
  CountryFlagOptions,
  FormWdlSegment,
  H2HEdgeSummary,
  JerseySvgOptions,
  ParsedPrematchMarkets,
  TeamLogoOptions,
} from './types.js';

const CLUB_ALIASES: Readonly<Record<string, string>> = {
  'paris saint germain': 'psg paris saint germain',
  psg: 'psg paris saint germain',
  internazionale: 'inter internazionale milano',
  'inter milan': 'inter internazionale milano',
};

/**
 * Strip Unicode diacritics, remove common football club prefixes (`fc`, `sc`, `ac`, etc.),
 * and expand known club aliases.
 */
export function normalizeTeamName(name?: string | null): string {
  const raw = String(name ?? '');
  const stripped = raw
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
  const withoutPrefixes = stripped.replace(
    /\b(fc|sc|cf|ac|afc|sv|vfb|vfl|tsg|rb|ud|cd|rcd|fk|sk|bk)\b/g,
    ' ',
  );
  const clean = withoutPrefixes.replace(/[^a-z0-9]+/g, ' ').trim();
  return CLUB_ALIASES[clean] ?? clean;
}

/**
 * Extract significant (`>= 3` char) normalized tokens from a team or player name.
 */
export function teamTokens(name?: string | null): Set<string> {
  const norm = normalizeTeamName(name);
  if (!norm) return new Set();
  return new Set(norm.split(/\s+/).filter((t) => t.length >= 3));
}

/**
 * Fuzzy team / player name matcher handling diacritics, club prefixes, and
 * `"Lastname, Firstname"` vs `"Firstname Lastname"` ordering in Tennis/Table Tennis/Darts.
 */
export function namesMatch(a?: string | null, b?: string | null): boolean {
  const na = normalizeTeamName(a);
  const nb = normalizeTeamName(b);
  if (!na || !nb) return false;
  if (na === nb || na.includes(nb) || nb.includes(na)) {
    return true;
  }
  const ta = teamTokens(a);
  const tb = teamTokens(b);
  for (const tok of ta) {
    if (tb.has(tok)) return true;
  }
  return false;
}

/**
 * Parse pre-match markets from Primary Retail (`_bookmakerId: 176`) or Global Consensus (`_bookmakerId: 0`).
 * Automatically flips home/away outcomes and Correct Score (`"H:A"` -> `"A:H"`) when `flipped = true`.
 */
export function parsePrematchMarkets(
  markets: BetScoutMarket[] | undefined | null,
  flipped = false,
): ParsedPrematchMarkets {
  const list = Array.isArray(markets) ? markets : [];
  let bkLabel: ParsedPrematchMarkets['bookmaker'] = 'Primary Bookmaker';
  if (list.length > 0 && list[0]) {
    if (list[0]._bookmakerId === 0 || String(list[0].source ?? '').includes('UOF')) {
      bkLabel = 'Market Consensus';
    }
  }

  const out: ParsedPrematchMarkets = {
    bookmaker: bkLabel,
    odds_home: null,
    odds_draw: null,
    odds_away: null,
    double_chance_1x: null,
    double_chance_x2: null,
    draw_no_bet_home: null,
    draw_no_bet_away: null,
    asian_handicap_line: null,
    asian_handicap_home: null,
    asian_handicap_away: null,
    total_line: null,
    odds_over: null,
    odds_under: null,
    correct_score_odds: {},
  };

  for (const mk of list) {
    const mid = mk._marketId;
    const outcomes = mk.outcomes ?? [];
    const spec = mk.specifiers ?? {};

    if (
      mid === MARKET_IDS.MATCH_1X2 ||
      mid === MARKET_IDS.TENNIS_MATCH_WINNER ||
      mid === MARKET_IDS.US_SPORTS_WINNER_OT ||
      mid === MARKET_IDS.HOCKEY_WINNER_OT_SO
    ) {
      for (const o of outcomes) {
        const nm = String(o.name ?? '').toLowerCase();
        const val = o.odds ? Number(o.odds) : null;
        if (!val || !Number.isFinite(val)) continue;
        if (nm.includes('competitor1')) {
          if (flipped) out.odds_away = val;
          else out.odds_home = val;
        } else if (nm.includes('competitor2')) {
          if (flipped) out.odds_home = val;
          else out.odds_away = val;
        } else if (nm === 'draw') {
          out.odds_draw = val;
        }
      }
    } else if (mid === MARKET_IDS.DOUBLE_CHANCE) {
      for (const o of outcomes) {
        const nm = String(o.name ?? '').toLowerCase();
        const val = o.odds ? Number(o.odds) : null;
        if (!val || !Number.isFinite(val)) continue;
        if (nm.includes('competitor1') && nm.includes('draw')) {
          if (flipped) out.double_chance_x2 = val;
          else out.double_chance_1x = val;
        } else if (nm.includes('competitor2') && nm.includes('draw')) {
          if (flipped) out.double_chance_1x = val;
          else out.double_chance_x2 = val;
        }
      }
    } else if (mid === MARKET_IDS.DRAW_NO_BET) {
      for (const o of outcomes) {
        const nm = String(o.name ?? '').toLowerCase();
        const val = o.odds ? Number(o.odds) : null;
        if (!val || !Number.isFinite(val)) continue;
        if (nm.includes('competitor1')) {
          if (flipped) out.draw_no_bet_away = val;
          else out.draw_no_bet_home = val;
        } else if (nm.includes('competitor2')) {
          if (flipped) out.draw_no_bet_home = val;
          else out.draw_no_bet_away = val;
        }
      }
    } else if (
      mid === MARKET_IDS.ASIAN_HANDICAP_2WAY ||
      mid === MARKET_IDS.US_SPORTS_SPREAD_OT
    ) {
      out.asian_handicap_line = spec.hcp ?? null;
      for (const o of outcomes) {
        const nm = String(o.name ?? '').toLowerCase();
        const val = o.odds ? Number(o.odds) : null;
        if (!val || !Number.isFinite(val)) continue;
        if (nm.includes('competitor1')) {
          if (flipped) out.asian_handicap_away = val;
          else out.asian_handicap_home = val;
        } else if (nm.includes('competitor2')) {
          if (flipped) out.asian_handicap_home = val;
          else out.asian_handicap_away = val;
        }
      }
    } else if (
      mid === MARKET_IDS.TOTAL_GOALS ||
      mid === MARKET_IDS.TENNIS_TOTAL_GAMES ||
      mid === MARKET_IDS.US_SPORTS_TOTAL_OT
    ) {
      if (spec.total !== undefined) {
        const parsedLine = Number.parseFloat(spec.total);
        out.total_line = Number.isFinite(parsedLine) ? parsedLine : null;
      }
      for (const o of outcomes) {
        const nm = String(o.name ?? '').toLowerCase();
        const val = o.odds ? Number(o.odds) : null;
        if (!val || !Number.isFinite(val)) continue;
        if (nm.startsWith('over')) out.odds_over = val;
        else if (nm.startsWith('under')) out.odds_under = val;
      }
    } else if (
      mid === MARKET_IDS.CORRECT_SCORE ||
      mid === MARKET_IDS.CORRECT_SCORE_NAMED
    ) {
      if (
        Object.keys(out.correct_score_odds).length > 0 &&
        mid === MARKET_IDS.CORRECT_SCORE_NAMED
      ) {
        continue;
      }
      const csMap: Record<string, number> = {};
      for (const o of outcomes) {
        const oid = String(o._id ?? '');
        const nmSc = String(o.name ?? '').trim();
        const val = o.odds ? Number(o.odds) : null;
        if (!val || !Number.isFinite(val)) continue;
        let rawSc =
          nmSc.includes(':') && nmSc.length <= 5
            ? nmSc
            : (CORRECT_SCORE_OUTCOMES[oid] ?? '');
        if (rawSc && rawSc.includes(':')) {
          if (flipped) {
            const [ph, pa] = rawSc.split(':', 2);
            rawSc = `${pa}:${ph}`;
          }
          csMap[rawSc] = val;
        }
      }
      if (Object.keys(csMap).length > 0) {
        out.correct_score_odds = csMap;
      }
    }
  }

  return out;
}

/**
 * Merge Primary Retail (`_bookmakerId: 176`) and Global Consensus (`_bookmakerId: 0`) parsed markets:
 * prioritizes Primary Retail prices whenever present and fills missing markets from Global Consensus.
 */
export function mergePrimaryAndConsensusMarkets(
  primary: ParsedPrematchMarkets,
  consensus: ParsedPrematchMarkets,
): ParsedPrematchMarkets {
  const merged: ParsedPrematchMarkets = {
    ...primary,
    correct_score_odds:
      Object.keys(primary.correct_score_odds).length > 0
        ? { ...primary.correct_score_odds }
        : { ...consensus.correct_score_odds },
  };

  const scalarKeys: Array<keyof Omit<ParsedPrematchMarkets, 'bookmaker' | 'correct_score_odds'>> = [
    'odds_home',
    'odds_draw',
    'odds_away',
    'double_chance_1x',
    'double_chance_x2',
    'draw_no_bet_home',
    'draw_no_bet_away',
    'asian_handicap_line',
    'asian_handicap_home',
    'asian_handicap_away',
    'total_line',
    'odds_over',
    'odds_under',
  ];

  for (const key of scalarKeys) {
    if (merged[key] === null && consensus[key] !== null) {
      (merged as unknown as Record<string, unknown>)[key] = consensus[key];
    }
  }

  const hasPrimary = Boolean(
    primary.odds_home !== null || Object.keys(primary.correct_score_odds).length > 0,
  );
  const hasConsensus = Boolean(
    consensus.odds_home !== null || Object.keys(consensus.correct_score_odds).length > 0,
  );
  if (hasPrimary && hasConsensus) merged.bookmaker = 'Primary + Consensus';
  else if (hasPrimary) merged.bookmaker = 'Primary Bookmaker';
  else if (hasConsensus) merged.bookmaker = 'Market Consensus';

  return merged;
}

/**
 * Compute the adaptive polling interval in milliseconds from a feed document's `_maxage` metadata
 * (`Math.max((doc._maxage ?? 3) * 1000, 3000)`).
 */
export function getAdaptiveRefetchIntervalMs(doc?: BetScoutDocument<unknown> | null): number {
  const maxAgeSec = typeof doc?._maxage === 'number' && doc._maxage > 0 ? doc._maxage : 3;
  return Math.max(maxAgeSec * 1000, 3000);
}

/**
 * Merge a base `match` summary with a real-time `match_timelinedelta` response using `updated_uts`.
 */
export function mergeLatestMatchDelta(
  match: BetScoutMatchSummary,
  timelineDelta?: BetScoutMatchTimelineDeltaResponse | null,
): BetScoutMatchSummary {
  const deltaMatch = timelineDelta?.match;
  if (!deltaMatch) return match;
  if (
    typeof deltaMatch.updated_uts === 'number' &&
    (typeof match.updated_uts !== 'number' || deltaMatch.updated_uts > match.updated_uts)
  ) {
    return deltaMatch;
  }
  return deltaMatch;
}

/**
 * Build the direct tokenless PNG logo URL for any club/team ID (`small` | `medium` | `big` or NCAA `ap250x188ut` | `ap500x375ut` | `ap1000x750ut`).
 * Example: `getTeamLogoUrl(2692, { size: 'big' })` for AC Milan.
 */
export function getTeamLogoUrl(teamId: number | string, options: TeamLogoOptions = {}): string {
  return buildUpstreamTeamLogoUrl(teamId, options);
}

/**
 * Build the direct tokenless SVG (`4x3` | `1x1`) or PNG (`small` | `medium` | `big`) country/federation flag URL.
 * Automatically maps UK home-nation codes (`en` -> `gb-eng`, `s` -> `gb-sct`, `n` -> `gb-nir`, `w` -> `gb-wls`).
 */
export function getCountryFlagUrl(
  countryIso2: string,
  options: CountryFlagOptions = {},
): string {
  return buildUpstreamCountryFlagUrl(countryIso2, options);
}

/**
 * Render a standalone vector SVG player kit avatar from a team's `homejersey` / `awayjersey` / `gkjersey` colors
 * (`base`, `sleeve`, `number`, `stripes`) and optional player `shirtNumber`.
 */
export function renderTeamJerseySvg(
  jersey: BetScoutJerseyColors | null | undefined,
  options: JerseySvgOptions = {},
): string {
  const cleanHex = (c?: string, fallback = '1e293b') =>
    `#${String(c || fallback).replace(/^#+/, '')}`;
  const base = cleanHex(jersey?.base, 'dc2626');
  const sleeve = cleanHex(jersey?.sleeve, base.slice(1));
  const numberColor = cleanHex(jersey?.number, 'ffffff');
  const stripeColor = jersey?.stripes ? cleanHex(jersey.stripes) : null;
  const size = options.sizePx ?? 96;
  const numText =
    options.shirtNumber !== undefined && options.shirtNumber !== null
      ? String(options.shirtNumber).trim()
      : '';

  const stripesMarkup = stripeColor
    ? `<rect x="36" y="18" width="8" height="68" fill="${stripeColor}" opacity="0.9"/><rect x="52" y="18" width="8" height="68" fill="${stripeColor}" opacity="0.9"/>`
    : '';
  const numberMarkup = numText
    ? `<text x="48" y="60" text-anchor="middle" fill="${numberColor}" font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="24">${numText}</text>`
    : '';

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 96 96" role="img" aria-label="Player Jersey"><path d="M26 14 L38 14 C41 20 55 20 58 14 L70 14 L88 32 L76 44 L68 36 L68 86 L28 86 L28 36 L20 44 L8 32 Z" fill="${base}" stroke="rgba(255,255,255,0.22)" stroke-width="2"/><path d="M26 14 L8 32 L20 44 L28 36 L28 22 Z" fill="${sleeve}"/><path d="M70 14 L88 32 L76 44 L68 36 L68 22 Z" fill="${sleeve}"/>${stripesMarkup}${numberMarkup}</svg>`;
}

/**
 * Parse a stadium's `googlecoords` string (`"45.478025,9.124206"`) into `{ lat, lng }` coordinates.
 */
export function parseVenueCoordinates(
  googlecoords?: string | null,
): { lat: number; lng: number } | null {
  if (!googlecoords || !googlecoords.includes(',')) return null;
  const [latStr, lngStr] = googlecoords.split(',', 2);
  const lat = Number.parseFloat(String(latStr).trim());
  const lng = Number.parseFloat(String(lngStr).trim());
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
}

/**
 * Convert `"Lastname, Firstname"` (e.g. `"Djokovic, Novak"`, `"Maignan, Mike"`) to `"Firstname Lastname"`
 * for clean display and Wikipedia headshot resolution.
 */
export function formatPlayerFullName(rawName?: string | null): string {
  const s = String(rawName ?? '').trim();
  if (!s) return '';
  if (s.includes(',')) {
    const [last, first] = s.split(',', 2).map((p) => p.trim());
    if (first && last) return `${first} ${last}`;
  }
  return s;
}

/**
 * Generate a deterministic SVG monogram shield crest data URI (`data:image/svg+xml;utf8,...`)
 * for any competition, league, or player fallback.
 */
export function renderMonogramCrestDataUri(label?: string | null, sizePx = 36): string {
  const clean = String(label ?? 'BS').trim();
  const words = clean.replace(/[^a-zA-Z0-9\s]/g, ' ').trim().split(/\s+/).filter(Boolean);
  const initials =
    words.length >= 2
      ? `${words[0]![0] ?? ''}${words[1]![0] ?? ''}`.toUpperCase()
      : clean.slice(0, 2).toUpperCase() || 'BS';

  let hash = 0;
  for (let i = 0; i < clean.length; i += 1) {
    hash = (hash * 31 + clean.charCodeAt(i)) | 0;
  }
  const palettes = [
    ['#0ea5e9', '#10b981'],
    ['#6366f1', '#ec4899'],
    ['#f59e0b', '#ef4444'],
    ['#14b8a6', '#3b82f6'],
    ['#8b5cf6', '#06b6d4'],
  ] as const;
  const [c1, c2] = palettes[Math.abs(hash) % palettes.length]!;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${sizePx}" height="${sizePx}" viewBox="0 0 40 40"><defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="${c1}"/><stop offset="100%" stop-color="${c2}"/></linearGradient></defs><rect x="2" y="2" width="36" height="36" rx="10" fill="#0f172a" stroke="url(#g)" stroke-width="2.2"/><text x="20" y="25" text-anchor="middle" fill="#f8fafc" font-family="system-ui,-apple-system,sans-serif" font-weight="800" font-size="13">${initials}</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

const HEADSHOT_CACHE = new Map<string, string>();

const CURATED_COMPETITION_WIKI_TITLES: Readonly<Record<string, string>> = {
  'serie a': 'Serie_A',
  'premier league': 'Premier_League',
  'la liga': 'La_Liga',
  laliga: 'La_Liga',
  bundesliga: 'Bundesliga',
  'ligue 1': 'Ligue_1',
  'uefa champions league': 'UEFA_Champions_League',
  'champions league': 'UEFA_Champions_League',
  'uefa europa league': 'UEFA_Europa_League',
  'coppa italia': 'Coppa_Italia',
  'fa cup': 'FA_Cup',
  nba: 'National_Basketball_Association',
  nhl: 'National_Hockey_League',
  nfl: 'National_Football_League',
  mlb: 'Major_League_Baseball',
};

/**
 * Resolve an individual player's photographic headshot URL via Wikimedia Commons REST API,
 * falling back to a crisp monogram avatar data URI if no public portrait is found.
 */
export async function resolvePlayerHeadshotUrl(
  playerName?: string | null,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<string> {
  const fullName = formatPlayerFullName(playerName);
  if (!fullName) return renderMonogramCrestDataUri('PL', 64);

  const cached = HEADSHOT_CACHE.get(`player:${fullName.toLowerCase()}`);
  if (cached) return cached;

  const wikiTitle = encodeURIComponent(fullName.replace(/\s+/g, '_'));
  try {
    const resp = await fetchFn(`https://en.wikipedia.org/api/rest_v1/page/summary/${wikiTitle}`, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; BetScoutSDK/1.1)' },
    });
    if (resp.ok) {
      const data = (await resp.json()) as { thumbnail?: { source?: string } };
      if (data?.thumbnail?.source) {
        HEADSHOT_CACHE.set(`player:${fullName.toLowerCase()}`, data.thumbnail.source);
        return data.thumbnail.source;
      }
    }
  } catch {
    // Fallback to monogram avatar
  }

  const fallback = renderMonogramCrestDataUri(fullName, 64);
  HEADSHOT_CACHE.set(`player:${fullName.toLowerCase()}`, fallback);
  return fallback;
}

/**
 * Resolve a league / competition crest image URL (official emblem for major leagues via Wikimedia,
 * or a deterministic shield monogram crest data URI).
 */
export async function resolveCompetitionCrestUrl(
  competitionName?: string | null,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<string> {
  const clean = String(competitionName ?? '').trim();
  if (!clean) return renderMonogramCrestDataUri('LG', 36);

  const key = clean.toLowerCase();
  const cached = HEADSHOT_CACHE.get(`comp:${key}`);
  if (cached) return cached;

  const wikiTitle = CURATED_COMPETITION_WIKI_TITLES[key];
  if (wikiTitle) {
    try {
      const resp = await fetchFn(
        `https://en.wikipedia.org/api/rest_v1/page/summary/${wikiTitle}`,
        { headers: { 'User-Agent': 'Mozilla/5.0 (compatible; BetScoutSDK/1.1)' } },
      );
      if (resp.ok) {
        const data = (await resp.json()) as { thumbnail?: { source?: string } };
        if (data?.thumbnail?.source) {
          HEADSHOT_CACHE.set(`comp:${key}`, data.thumbnail.source);
          return data.thumbnail.source;
        }
      }
    } catch {
      // Fallback to monogram shield
    }
  }

  const fallback = renderMonogramCrestDataUri(clean, 36);
  HEADSHOT_CACHE.set(`comp:${key}`, fallback);
  return fallback;
}

function toOrdinal(n: number | string): string {
  const num = Number.parseInt(String(n), 10);
  if (Number.isNaN(num)) return String(n);
  const rem100 = num % 100;
  if (rem100 >= 11 && rem100 <= 13) return `${num}th`;
  switch (num % 10) {
    case 1:
      return `${num}st`;
    case 2:
      return `${num}nd`;
    case 3:
      return `${num}rd`;
    default:
      return `${num}th`;
  }
}

/**
 * Interpolate raw market/outcome template placeholders (`{!setnr}`, `{total}`, `{hcp}`,
 * `{$competitor1}`, `{$competitor2}`) into human-readable market & outcome names.
 */
export function formatMarketPlaceholders(
  rawText?: string | null,
  context: {
    homeName?: string | null;
    awayName?: string | null;
    specifiers?: Record<string, string | undefined> | null;
  } = {},
): string {
  let out = String(rawText ?? '');
  if (!out) return '';

  const spec = context.specifiers ?? {};
  // Replace {!key} with ordinal (e.g. {!setnr} -> 2nd)
  out = out.replace(/\{!(\w+)\}/g, (_m, key: string) => {
    const val = spec[key];
    return val !== undefined ? toOrdinal(val) : key;
  });
  // Replace {+hcp} / {-hcp} with signed specifier value
  out = out.replace(/\{([+-])(\w+)\}/g, (_m, sign: string, key: string) => {
    const rawVal = spec[key];
    if (rawVal === undefined || rawVal === null) return `${sign}${key}`;
    const num = Number(rawVal);
    if (Number.isNaN(num)) return String(rawVal);
    const val = sign === '-' ? -num : num;
    return val > 0 ? `+${val}` : String(val);
  });
  // Replace {$competitor1} and {$competitor2}
  out = out.replace(/\{\$competitor1\}/gi, context.homeName || 'Home');
  out = out.replace(/\{\$competitor2\}/gi, context.awayName || 'Away');
  // Replace {total}, {hcp}, {setnr}, etc.
  out = out.replace(/\{(\w+)\}/g, (_m, key: string) => {
    const val = spec[key];
    return val !== undefined ? String(val) : key;
  });

  return out;
}

/**
 * Extract the last `limit` (default `5`) completed match W/D/L segments with exact score labels
 * (`"2:0"`, `"1:2"`, etc.) and compute the overall `0`–`100` Form Index (`home_form_pct` / `away_form_pct`).
 */
export function computeFormWdlSegments(
  matches: BetScoutHistoricalMatchItem[] | undefined | null,
  teamUid: number | string | undefined | null,
  limit = 5,
): { segments: FormWdlSegment[]; formPct: number } {
  const list = Array.isArray(matches) ? matches : [];
  const targetUid = Number(teamUid ?? 0);
  const completed: FormWdlSegment[] = [];

  for (const m of list) {
    const res = m.result;
    if (!res || res.home == null || res.away == null) continue;
    if ((m.walkover || m.retired) && !res.winner) continue;

    const hTeam = m.teams?.home;
    const aTeam = m.teams?.away;
    const hUid = Number(hTeam?.uid ?? hTeam?._id ?? 0);
    const isHome = hUid === targetUid;
    const myScore = Number(isHome ? res.home : res.away);
    const oppScore = Number(isHome ? res.away : res.home);
    const oppName = String((isHome ? aTeam?.name : hTeam?.name) ?? '');

    let wdl: 'W' | 'D' | 'L' = 'D';
    if (res.winner === 'home') wdl = isHome ? 'W' : 'L';
    else if (res.winner === 'away') wdl = isHome ? 'L' : 'W';
    else if (myScore > oppScore) wdl = 'W';
    else if (myScore < oppScore) wdl = 'L';

    completed.push({
      match_id: m._id ?? null,
      wdl,
      score_label: `${myScore}:${oppScore}`,
      opponent_name: oppName || null,
    });
    if (completed.length >= limit) break;
  }

  // Chronological order (oldest -> newest from left to right, matching Sportradar's reverse())
  const chronological = [...completed].reverse();
  let pointsEarned = 0;
  let maxPoints = 0;
  for (const seg of chronological) {
    maxPoints += 3;
    if (seg.wdl === 'W') pointsEarned += 3;
    else if (seg.wdl === 'D') pointsEarned += 1;
  }
  const formPct = maxPoints > 0 ? Math.round((pointsEarned / maxPoints) * 100) : 0;

  while (chronological.length < limit) {
    chronological.unshift({
      match_id: null,
      wdl: 'empty',
      score_label: null,
      opponent_name: null,
    });
  }

  return { segments: chronological, formPct };
}

/**
 * Compute the direct Head-to-Head win/draw/loss summary and color-coded progress bar percentages
 * between `homeUid` and `awayUid`.
 */
export function computeH2HEdgeSummary(
  matches: BetScoutHistoricalMatchItem[] | undefined | null,
  homeUid: number | string | undefined | null,
  awayUid: number | string | undefined | null,
): H2HEdgeSummary {
  const list = Array.isArray(matches) ? matches : [];
  const hTarget = Number(homeUid ?? 0);
  const aTarget = Number(awayUid ?? 0);
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;
  let oldestUts: number | null = null;

  for (const m of list) {
    const res = m.result;
    if (!res || res.home == null || res.away == null) continue;
    const uts = m.time?.uts ?? m._dt?.uts ?? null;
    if (typeof uts === 'number' && uts > 0 && (oldestUts === null || uts < oldestUts)) {
      oldestUts = uts;
    }

    const mHomeUid = Number(m.teams?.home?.uid ?? m.teams?.home?._id ?? 0);
    const mAwayUid = Number(m.teams?.away?.uid ?? m.teams?.away?._id ?? 0);
    const hScore = Number(res.home);
    const aScore = Number(res.away);

    let winnerUid = 0;
    if (res.winner === 'home' || hScore > aScore) winnerUid = mHomeUid;
    else if (res.winner === 'away' || aScore > hScore) winnerUid = mAwayUid;

    if (winnerUid === hTarget && hTarget > 0) homeWins += 1;
    else if (winnerUid === aTarget && aTarget > 0) awayWins += 1;
    else if (winnerUid === 0) draws += 1;
  }

  const total = homeWins + draws + awayWins;
  const sinceYear =
    oldestUts !== null ? String(new Date(oldestUts * 1000).getUTCFullYear()) : null;

  return {
    total_meetings: total,
    since_year: sinceYear,
    home_wins: homeWins,
    draws,
    away_wins: awayWins,
    home_win_pct: total > 0 ? Math.round((homeWins / total) * 100) : 0,
    draw_pct: total > 0 ? Math.round((draws / total) * 100) : 0,
    away_win_pct: total > 0 ? Math.round((awayWins / total) * 100) : 0,
  };
}
