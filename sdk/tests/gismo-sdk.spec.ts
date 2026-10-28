import { describe, expect, it, vi } from 'vitest';
import {
  DIRECT_STATS_FN_BASE_URL,
  FISHNET_BASE_URL,
  SR_ALL_SPORTS_CATALOG,
  SR_BOOKMAKER_IDS,
  SR_CORRECT_SCORE_OUTCOMES,
  SR_MARKET_IDS,
  SR_SERVICE_IDS,
  SportradarGismoClient,
  getAdaptiveRefetchIntervalMs,
  mergeLatestMatchDelta,
  mergeTipicoAndUofMarkets,
  namesMatch,
  normalizeTeamName,
  parsePrematchMarkets,
  resolveSportId,
} from '../src/index.js';
import type { GismoEnvelope, GismoMarket, GismoMatchSummary } from '../src/index.js';

function jsonResponse<T>(data: T, maxAge = 10, event = 'test_event'): Response {
  const env: GismoEnvelope<T> = {
    queryUrl: event,
    doc: [
      {
        event,
        _dob: 1793200000,
        _maxage: maxAge,
        data,
      },
    ],
  };
  return new Response(JSON.stringify(env), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('@betscout/sportradar-gismo-sdk — Constants & Name Normalization', () => {
  it('registers all 56 sports and resolves sport slugs and numeric IDs', () => {
    expect(Object.keys(SR_ALL_SPORTS_CATALOG).length).toBe(56);
    expect(resolveSportId('soccer')).toBe(1);
    expect(resolveSportId('tennis')).toBe(5);
    expect(resolveSportId('wta')).toBe(5);
    expect(resolveSportId('nhl')).toBe(4);
    expect(resolveSportId('nfl')).toBe(16);
    expect(resolveSportId('table_tennis')).toBe(20);
    expect(resolveSportId('darts')).toBe(22);
    expect(resolveSportId('handball')).toBe(6);
    expect(resolveSportId(117)).toBe(117);
    expect(SR_BOOKMAKER_IDS.TIPICO).toBe(176);
    expect(SR_BOOKMAKER_IDS.SPORTRADAR_UOF).toBe(0);
    expect(SR_SERVICE_IDS.SPORTRADAR_UNLIMITED).toBe(69);
    expect(Object.keys(SR_CORRECT_SCORE_OUTCOMES).length).toBe(28);
  });

  it('normalizes diacritics, club prefixes, aliases, and Tennis "Lastname, Firstname" names', () => {
    expect(normalizeTeamName('FC Bayern München')).toBe('bayern munchen');
    expect(normalizeTeamName('Paris Saint-Germain')).toContain('psg');
    expect(namesMatch('Internazionale', 'Inter Milan')).toBe(true);
    expect(namesMatch('Jiri Lehecka', 'Lehečka, Jiří')).toBe(true);
    expect(namesMatch('Machelski, Michal', 'Michal Machelski')).toBe(true);
    expect(namesMatch('Real Madrid', 'Barcelona')).toBe(false);
  });
});

describe('@betscout/sportradar-gismo-sdk — Market Parsing & Tipico/UOF Merging', () => {
  const sampleTipicoMarkets: GismoMarket[] = [
    {
      _marketId: SR_MARKET_IDS.MATCH_1X2,
      _bookmakerId: 176,
      outcomes: [
        { _id: '1', name: '{$competitor1}', odds: 1.45 },
        { _id: '2', name: 'draw', odds: 4.3 },
        { _id: '3', name: '{$competitor2}', odds: 6.5 },
      ],
    },
    {
      _marketId: SR_MARKET_IDS.DOUBLE_CHANCE,
      _bookmakerId: 176,
      outcomes: [
        { _id: '4', name: '{$competitor1} or draw', odds: 1.12 },
        { _id: '5', name: 'draw or {$competitor2}', odds: 2.55 },
      ],
    },
    {
      _marketId: SR_MARKET_IDS.DRAW_NO_BET,
      _bookmakerId: 176,
      outcomes: [
        { _id: '6', name: '{$competitor1}', odds: 1.16 },
        { _id: '7', name: '{$competitor2}', odds: 4.8 },
      ],
    },
    {
      _marketId: SR_MARKET_IDS.TOTAL_GOALS,
      _bookmakerId: 176,
      specifiers: { total: '2.5' },
      outcomes: [
        { _id: '8', name: 'Over 2.5', odds: 1.72 },
        { _id: '9', name: 'Under 2.5', odds: 2.05 },
      ],
    },
    {
      _marketId: SR_MARKET_IDS.CORRECT_SCORE,
      _bookmakerId: 176,
      outcomes: [
        { _id: 'sr:outcome:114', name: '', odds: 6.5 }, // 1:0
        { _id: 'sr:outcome:116', name: '', odds: 6.8 }, // 2:0
        { _id: 'sr:outcome:130', name: '', odds: 8.0 }, // 2:1
        { _id: 'sr:outcome:126', name: '', odds: 14.0 }, // 0:1
      ],
    },
  ];

  it('parses Tipico 1X2, Double Chance, DNB, Totals, and 28-outcome Correct Score matrix', () => {
    const parsed = parsePrematchMarkets(sampleTipicoMarkets, false);
    expect(parsed.bookmaker).toBe('Primary Bookmaker');
    expect(parsed.odds_home).toBe(1.45);
    expect(parsed.odds_draw).toBe(4.3);
    expect(parsed.odds_away).toBe(6.5);
    expect(parsed.double_chance_1x).toBe(1.12);
    expect(parsed.double_chance_x2).toBe(2.55);
    expect(parsed.draw_no_bet_home).toBe(1.16);
    expect(parsed.draw_no_bet_away).toBe(4.8);
    expect(parsed.total_line).toBe(2.5);
    expect(parsed.odds_over).toBe(1.72);
    expect(parsed.odds_under).toBe(2.05);
    expect(parsed.correct_score_odds).toEqual({
      '1:0': 6.5,
      '2:0': 6.8,
      '2:1': 8.0,
      '0:1': 14.0,
    });
  });

  it('correctly flips home/away odds and Correct Score keys when flipped=true', () => {
    const flipped = parsePrematchMarkets(sampleTipicoMarkets, true);
    expect(flipped.odds_home).toBe(6.5);
    expect(flipped.odds_away).toBe(1.45);
    expect(flipped.double_chance_1x).toBe(2.55);
    expect(flipped.double_chance_x2).toBe(1.12);
    expect(flipped.correct_score_odds['0:1']).toBe(6.5);
    expect(flipped.correct_score_odds['0:2']).toBe(6.8);
    expect(flipped.correct_score_odds['1:2']).toBe(8.0);
    expect(flipped.correct_score_odds['1:0']).toBe(14.0);
  });

  it('merges Tipico primary markets with Sportradar UOF Asian Handicap fallback', () => {
    const tipico = parsePrematchMarkets(sampleTipicoMarkets, false);
    const uof = parsePrematchMarkets(
      [
        {
          _marketId: SR_MARKET_IDS.MATCH_1X2,
          _bookmakerId: 0,
          source: 'OS_SR:OP_SR:OF_3:OF_UOF',
          outcomes: [
            { _id: '1', name: '{$competitor1}', odds: 1.42 },
            { _id: '2', name: 'draw', odds: 4.2 },
            { _id: '3', name: '{$competitor2}', odds: 6.2 },
          ],
        },
        {
          _marketId: SR_MARKET_IDS.ASIAN_HANDICAP_2WAY,
          _bookmakerId: 0,
          source: 'OS_SR:OP_SR:OF_3:OF_UOF',
          specifiers: { hcp: '-1.5' },
          outcomes: [
            { _id: '10', name: '{$competitor1}', odds: 2.15 },
            { _id: '11', name: '{$competitor2}', odds: 1.68 },
          ],
        },
      ],
      false,
    );

    const merged = mergeTipicoAndUofMarkets(tipico, uof);
    expect(merged.bookmaker).toBe('Primary + Consensus');
    // Preserves Tipico 1X2 (1.45) over UOF (1.42)
    expect(merged.odds_home).toBe(1.45);
    // Fills missing Asian Handicap from UOF
    expect(merged.asian_handicap_line).toBe('-1.5');
    expect(merged.asian_handicap_home).toBe(2.15);
    expect(merged.asian_handicap_away).toBe(1.68);
  });
});

describe('@betscout/sportradar-gismo-sdk — Client Transport, Caching & Fallback', () => {
  it('queries direct stats.fn.sportradar.com and caches responses within TTL', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse([
        { _id: 1, name: 'Soccer' },
        { _id: 5, name: 'Tennis' },
      ]),
    );

    const client = new SportradarGismoClient({ fetchFn: mockFetch });
    const sports1 = await client.listAllSports(69, 0, 'sportradar');
    const sports2 = await client.listAllSports(69, 0, 'sportradar');

    expect(sports1).toEqual([
      { sportId: 1, name: 'Soccer' },
      { sportId: 5, name: 'Tennis' },
    ]);
    expect(sports2).toEqual(sports1);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch.mock.calls[0]?.[0]).toBe(
      `${DIRECT_STATS_FN_BASE_URL}/sportradar/en/Etc:UTC/gismo/config_sports/69/0`,
    );
    expect(client.cacheSize).toBe(1);
  });

  it('automatically falls back to sh.fn.sportradar.com?T=token when direct endpoint fails', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.startsWith(DIRECT_STATS_FN_BASE_URL)) {
        return new Response('Service Unavailable', { status: 503 });
      }
      if (url.includes('statshub.sportradar.com/tipico/en/')) {
        return new Response(
          '<html><script>window.__TOKEN="exp=1999999999~acl=/*~hmac=abcdef0123456789";</script></html>',
          { status: 200 },
        );
      }
      if (url.startsWith(FISHNET_BASE_URL)) {
        return jsonResponse([{ _id: 1, name: 'Soccer (Fallback)' }]);
      }
      return new Response('Not Found', { status: 404 });
    });

    const client = new SportradarGismoClient({ fetchFn: mockFetch });
    const sports = await client.listAllSports(69, 0, 'sportradar');
    expect(sports).toEqual([{ sportId: 1, name: 'Soccer (Fallback)' }]);
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(String(mockFetch.mock.calls[2]?.[0])).toContain(
      `${FISHNET_BASE_URL}/sportradar/en/Etc:UTC/gismo/config_sports/69/0?T=exp=1999999999~acl=/*~hmac=abcdef0123456789`,
    );
  });
});

describe('@betscout/sportradar-gismo-sdk — Composite Intelligence & Live 3s Delta Stream', () => {
  it('formats live Tennis match_timelinedelta with set scores, point score & server indicator', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('unified_sport_matches/5/2026-10-28/0')) {
        return jsonResponse({
          sport: {
            _id: 5,
            name: 'Tennis',
            realcategories: [
              {
                _id: 3,
                name: 'ATP',
                tournaments: [
                  {
                    _id: 400,
                    name: 'Vienna, Austria',
                    matches: [
                      {
                        _id: 75992888,
                        _seasonid: 120001,
                        _dt: { uts: 1793200000 },
                        status: { _id: 8, name: '1st set', shortName: 'S1' },
                        teams: {
                          home: { _id: 10, uid: 1001, name: 'Mpetshi Perricard, Giovanni' },
                          away: { _id: 20, uid: 1002, name: 'Kovacevic, Aleksandar' },
                        },
                      },
                    ],
                  },
                ],
              },
            ],
          },
        });
      }
      if (url.includes('match_timelinedelta/75992888')) {
        return jsonResponse(
          {
            match: {
              _id: 75992888,
              updated_uts: 1793201234,
              status: { _id: 8, name: '1st set', shortName: 'S1' },
              result: { home: 0, away: 0, winner: null },
              periods: { p1: { home: 6, away: 5 } },
              gamescore: { home: 0, away: 15, service: '2' },
            },
            events: [{ type: 'score_change_tennis', matchid: 75992888, uts: 1793201234 }],
          },
          3,
          'match_timelinedelta',
        );
      }
      return jsonResponse({});
    });

    const client = new SportradarGismoClient({ fetchFn: mockFetch });
    const delta = await client.fetchLiveMatchTimelineDelta(
      'Giovanni Mpetshi Perricard',
      'Aleksandar Kovacevic',
      'tennis',
      '2026-10-28',
    );

    expect(delta.state).toBe('in');
    expect(delta.status_desc).toBe('1st set');
    expect(delta.score_str).toBe('0-0 (6-5 · Pt 0-15🎾)');
    expect(delta.point_score).toBe('Pt 0-15🎾');
    expect(getAdaptiveRefetchIntervalMs({ event: 'match_timelinedelta', _maxage: 3, data: {} })).toBe(
      3000,
    );

    const baseMatch: GismoMatchSummary = { _id: 75992888, updated_uts: 100 };
    const updatedMatch = mergeLatestMatchDelta(baseMatch, {
      match: { _id: 75992888, updated_uts: 200 },
    });
    expect(updatedMatch.updated_uts).toBe(200);
  });

  it('evaluates 15-minute goal intervals, live dangerous attacks, and pre-match injury gates in lookupMatchIntel', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('unified_sport_matches/1/2026-10-28/0')) {
        return jsonResponse({
          sport: {
            _id: 1,
            name: 'Soccer',
            realcategories: [
              {
                _id: 31,
                name: 'Italy',
                tournaments: [
                  {
                    _id: 23,
                    name: 'Serie A',
                    matches: [
                      {
                        _id: 401874993,
                        _seasonid: 118500,
                        _dt: { uts: 1793220600 },
                        status: { _id: 6, name: '1st half' },
                        teams: {
                          home: { _id: 2692, uid: 2692, name: 'AC Milan' },
                          away: { _id: 2685, uid: 2685, name: 'Bologna' },
                        },
                      },
                    ],
                  },
                ],
              },
            ],
          },
        });
      }
      if (url.includes('match_markets/401874993/prematch')) {
        return jsonResponse({
          markets: [
            {
              _marketId: 1,
              _bookmakerId: 176,
              outcomes: [
                { _id: '1', name: '{$competitor1}', odds: 1.65 },
                { _id: '2', name: 'draw', odds: 3.8 },
                { _id: '3', name: '{$competitor2}', odds: 5.2 },
              ],
            },
          ],
        });
      }
      if (url.includes('stats_season_injuries/118500')) {
        return jsonResponse([
          {
            uniqueteam: { _id: 2692, name: 'AC Milan' },
            player: { _id: 91, name: 'Ismael Bennacer', position: { shortname: 'MID' } },
            status: { name: 'Calf Injury' },
          },
        ]);
      }
      if (url.includes('stats_team_streaks/2692')) {
        return jsonResponse({
          streaks: { winning: { total: { value: 4 } } },
        });
      }
      if (url.includes('stats_season_teamscoringconceding/118500/')) {
        return jsonResponse({
          stats: {
            totalmatches: { total: 10 },
            scoring: {
              goalsbyminutes: { '0-15': { total: 0.3 }, '76-90': { total: 0.55 } },
              goalsscoredfirsthalfaverage: { total: 0.9 },
              scoringathalftimeaverage: { total: 0.7 },
              bothteamsscoredaverage: { total: 0.6 },
            },
            conceding: {
              goalsbyminutes: { '0-15': { total: 0.1 }, '76-90': { total: 0.25 } },
              goalsconcededfirsthalfaverage: { total: 0.4 },
            },
          },
        });
      }
      if (url.includes('match_situations/401874993')) {
        return jsonResponse({
          situations: [
            { team: 'home', situation: 'dangerous_attack' },
            { team: 'home', situation: 'dangerous_attack' },
            { team: 'home', situation: ' dangerous_attack'.trim() },
            { team: 'away', situation: 'dangerous_attack' },
          ],
        });
      }
      return jsonResponse({});
    });

    const client = new SportradarGismoClient({ fetchFn: mockFetch });
    const intel = await client.lookupMatchIntel('AC Milan', 'Bologna', 'soccer', '2026-10-28');

    expect(intel.ok).toBe(true);
    expect(intel.found).toBe(true);
    expect(intel.tournament).toBe('Italy · Serie A');
    expect(intel.primary_markets?.odds_home).toBe(1.65);
    expect(intel.home_injuries).toEqual(['Ismael Bennacer (MID, Calf Injury)']);
    expect(intel.streaks?.home).toEqual(['winning: 4 matches']);
    expect(intel.goal_intervals?.home?.late_76_90_total_avg).toBe(0.8);
    expect(intel.live_pressure?.home_danger_share_pct).toBe(75);
  });
});
