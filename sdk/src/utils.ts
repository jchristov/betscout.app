/**
 * Name Normalization, Market Parsing & Delta-Stream Utilities for Sportradar Gismo SDK.
 */

import { SR_CORRECT_SCORE_OUTCOMES, SR_MARKET_IDS } from './constants.js';
import type {
  GismoDocument,
  GismoMarket,
  GismoMatchSummary,
  GismoMatchTimelineDeltaResponse,
  ParsedPrematchMarkets,
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
 * Parse pre-match markets from Tipico (`_bookmakerId: 176`) or Sportradar UOF (`_bookmakerId: 0`).
 * Automatically flips home/away outcomes and Correct Score (`"H:A"` -> `"A:H"`) when `flipped = true`.
 */
export function parsePrematchMarkets(
  markets: GismoMarket[] | undefined | null,
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
      mid === SR_MARKET_IDS.MATCH_1X2 ||
      mid === SR_MARKET_IDS.TENNIS_MATCH_WINNER ||
      mid === SR_MARKET_IDS.US_SPORTS_WINNER_OT ||
      mid === SR_MARKET_IDS.HOCKEY_WINNER_OT_SO
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
    } else if (mid === SR_MARKET_IDS.DOUBLE_CHANCE) {
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
    } else if (mid === SR_MARKET_IDS.DRAW_NO_BET) {
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
      mid === SR_MARKET_IDS.ASIAN_HANDICAP_2WAY ||
      mid === SR_MARKET_IDS.US_SPORTS_SPREAD_OT
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
      mid === SR_MARKET_IDS.TOTAL_GOALS ||
      mid === SR_MARKET_IDS.TENNIS_TOTAL_GAMES ||
      mid === SR_MARKET_IDS.US_SPORTS_TOTAL_OT
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
      mid === SR_MARKET_IDS.CORRECT_SCORE ||
      mid === SR_MARKET_IDS.CORRECT_SCORE_NAMED
    ) {
      if (
        Object.keys(out.correct_score_odds).length > 0 &&
        mid === SR_MARKET_IDS.CORRECT_SCORE_NAMED
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
            : (SR_CORRECT_SCORE_OUTCOMES[oid] ?? '');
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
 * Merge Tipico (`_bookmakerId: 176`) and Sportradar UOF (`_bookmakerId: 0`) parsed markets:
 * prioritizes Tipico retail prices whenever present and fills missing markets from UOF.
 */
export function mergeTipicoAndUofMarkets(
  tipico: ParsedPrematchMarkets,
  uof: ParsedPrematchMarkets,
): ParsedPrematchMarkets {
  const merged: ParsedPrematchMarkets = {
    ...tipico,
    correct_score_odds:
      Object.keys(tipico.correct_score_odds).length > 0
        ? { ...tipico.correct_score_odds }
        : { ...uof.correct_score_odds },
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
    if (merged[key] === null && uof[key] !== null) {
      (merged as unknown as Record<string, unknown>)[key] = uof[key];
    }
  }

  const hasTipico = Boolean(
    tipico.odds_home !== null || Object.keys(tipico.correct_score_odds).length > 0,
  );
  const hasUof = Boolean(
    uof.odds_home !== null || Object.keys(uof.correct_score_odds).length > 0,
  );
  if (hasTipico && hasUof) merged.bookmaker = 'Primary + Consensus';
  else if (hasTipico) merged.bookmaker = 'Primary Bookmaker';
  else if (hasUof) merged.bookmaker = 'Market Consensus';

  return merged;
}

/**
 * Compute the adaptive polling interval in milliseconds from a Gismo document's `_maxage` metadata,
 * matching Sportradar's `useFeedQuery` (`Math.max((doc._maxage ?? 3) * 1000, 3000)`).
 */
export function getAdaptiveRefetchIntervalMs(doc?: GismoDocument<unknown> | null): number {
  const maxAgeSec = typeof doc?._maxage === 'number' && doc._maxage > 0 ? doc._maxage : 3;
  return Math.max(maxAgeSec * 1000, 3000);
}

/**
 * Merge a base `match` summary with a real-time `match_timelinedelta` response using `updated_uts`,
 * matching Sportradar's client delta merger (`getLatestMatch-D9YBx4ON.js`).
 */
export function mergeLatestMatchDelta(
  match: GismoMatchSummary,
  timelineDelta?: GismoMatchTimelineDeltaResponse | null,
): GismoMatchSummary {
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
