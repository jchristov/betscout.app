import { describe, expect, it, vi } from 'vitest';
import * as PublicSdk from '../src/index.js';
import {
  BOOKMAKER_IDS,
  BetScoutClient,
  CORRECT_SCORE_OUTCOMES,
  MARKET_IDS,
  SERVICE_PROFILES,
  SPORTS_CATALOG,
  getAdaptiveRefetchIntervalMs,
  getCountryFlagUrl,
  getTeamLogoUrl,
  mergeLatestMatchDelta,
  mergePrimaryAndConsensusMarkets,
  namesMatch,
  normalizeTeamName,
  parsePrematchMarkets,
  parseVenueCoordinates,
  renderTeamJerseySvg,
  resolveSportId,
} from '../src/index.js';
import type { BetScoutEnvelope, BetScoutMarket, BetScoutMatchSummary } from '../src/index.js';

function jsonResponse<T>(data: T, maxAge = 10, event = 'test_event'): Response {
  const env: BetScoutEnvelope<T> = {
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

describe('@betscout/sdk — White-Label Public API Surface & Catalogs', () => {
  it('exposes zero upstream vendor names in exported symbols', () => {
    const exportedKeys = Object.keys(PublicSdk);
    for (const key of exportedKeys) {
      const lower = key.toLowerCase();
      expect(lower).not.toContain('sportradar');
      expect(lower).not.toContain('gismo');
      expect(lower).not.toContain('tipico');
      expect(lower).not.toContain('fishnet');
    }
  });

  it('registers all 56 sports and resolves sport slugs and numeric IDs', () => {
    expect(Object.keys(SPORTS_CATALOG).length).toBe(56);
    expect(resolveSportId('soccer')).toBe(1);
    expect(resolveSportId('tennis')).toBe(5);
    expect(resolveSportId('wta')).toBe(5);
    expect(resolveSportId('nhl')).toBe(4);
    expect(resolveSportId('nfl')).toBe(16);
    expect(resolveSportId('table_tennis')).toBe(20);
    expect(resolveSportId('darts')).toBe(22);
    expect(resolveSportId('handball')).toBe(6);
    expect(resolveSportId(117)).toBe(117);
    expect(BOOKMAKER_IDS.EU_RETAIL).toBe(176);
    expect(BOOKMAKER_IDS.CONSENSUS).toBe(0);
    expect(SERVICE_PROFILES.GLOBAL_UNLIMITED).toBe(69);
    expect(Object.keys(CORRECT_SCORE_OUTCOMES).length).toBe(28);
  });

  it('normalizes diacritics, club prefixes, aliases, and Tennis "Lastname, Firstname" names', () => {
    expect(normalizeTeamName('FC Bayern München')).toBe('bayern munchen');
    expect(normalizeTeamName('Paris Saint-Germain')).toContain('psg');
    expect(namesMatch('Internazionale', 'Inter Milan')).toBe(true);
    expect(namesMatch('Jiri Lehecka', 'Lehečka, Jiří')).toBe(true);
    expect(namesMatch('Djokovic, Novak', 'Novak Djokovic')).toBe(true);
    expect(namesMatch('AC Milan', 'Milan')).toBe(true);
    expect(namesMatch('Real Madrid', 'Barcelona')).toBe(false);
  });
});

describe('@betscout/sdk — Market Parsing & Primary/Consensus Merging', () => {
  const samplePrimaryMarkets: BetScoutMarket[] = [
    {
      _marketId: MARKET_IDS.MATCH_1X2,
      _bookmakerId: 176,
      outcomes: [
        { _id: '1', name: '{$competitor1}', odds: 1.45 },
        { _id: '2', name: 'draw', odds: 4.3 },
        { _id: '3', name: '{$competitor2}', odds: 6.5 },
      ],
    },
    {
      _marketId: MARKET_IDS.DOUBLE_CHANCE,
      _bookmakerId: 176,
      outcomes: [
        { _id: '4', name: '{$competitor1} or draw', odds: 1.12 },
        { _id: '5', name: 'draw or {$competitor2}', odds: 2.55 },
      ],
    },
    {
      _marketId: MARKET_IDS.DRAW_NO_BET,
      _bookmakerId: 176,
      outcomes: [
        { _id: '6', name: '{$competitor1}', odds: 1.16 },
        { _id: '7', name: '{$competitor2}', odds: 4.8 },
      ],
    },
    {
      _marketId: MARKET_IDS.TOTAL_GOALS,
      _bookmakerId: 176,
      specifiers: { total: '2.5' },
      outcomes: [
        { _id: '8', name: 'Over 2.5', odds: 1.72 },
        { _id: '9', name: 'Under 2.5', odds: 2.05 },
      ],
    },
    {
      _marketId: MARKET_IDS.CORRECT_SCORE,
      _bookmakerId: 176,
      outcomes: [
        { _id: 'sr:outcome:114', name: '', odds: 6.5 }, // 1:0
        { _id: 'sr:outcome:116', name: '', odds: 6.8 }, // 2:0
        { _id: 'sr:outcome:130', name: '', odds: 8.0 }, // 2:1
        { _id: 'sr:outcome:126', name: '', odds: 14.0 }, // 0:1
      ],
    },
  ];

  it('parses 1X2, Double Chance, DNB, Totals, and 28-outcome Correct Score matrix', () => {
    const parsed = parsePrematchMarkets(samplePrimaryMarkets, false);
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
    const flipped = parsePrematchMarkets(samplePrimaryMarkets, true);
    expect(flipped.odds_home).toBe(6.5);
    expect(flipped.odds_away).toBe(1.45);
    expect(flipped.double_chance_1x).toBe(2.55);
    expect(flipped.double_chance_x2).toBe(1.12);
    expect(flipped.correct_score_odds['0:1']).toBe(6.5);
    expect(flipped.correct_score_odds['0:2']).toBe(6.8);
    expect(flipped.correct_score_odds['1:2']).toBe(8.0);
    expect(flipped.correct_score_odds['1:0']).toBe(14.0);
  });

  it('merges Primary Retail markets with Consensus Asian Handicap fallback', () => {
    const primary = parsePrematchMarkets(samplePrimaryMarkets, false);
    const consensus = parsePrematchMarkets(
      [
        {
          _marketId: MARKET_IDS.MATCH_1X2,
          _bookmakerId: 0,
          outcomes: [
            { _id: '1', name: '{$competitor1}', odds: 1.42 },
            { _id: '2', name: 'draw', odds: 4.2 },
            { _id: '3', name: '{$competitor2}', odds: 6.2 },
          ],
        },
        {
          _marketId: MARKET_IDS.ASIAN_HANDICAP_2WAY,
          _bookmakerId: 0,
          specifiers: { hcp: '-1.5' },
          outcomes: [
            { _id: '10', name: '{$competitor1}', odds: 2.15 },
            { _id: '11', name: '{$competitor2}', odds: 1.68 },
          ],
        },
      ],
      false,
    );

    const merged = mergePrimaryAndConsensusMarkets(primary, consensus);
    expect(merged.bookmaker).toBe('Primary + Consensus');
    expect(merged.odds_home).toBe(1.45);
    expect(merged.asian_handicap_line).toBe('-1.5');
    expect(merged.asian_handicap_home).toBe(2.15);
    expect(merged.asian_handicap_away).toBe(1.68);
  });
});

describe('@betscout/sdk — Team & Player Historical Analytics (AC Milan 2692 & Novak Djokovic 14882)', () => {
  it('builds a complete Tennis Player Intelligence Bundle for playerId=14882 (Novak Djokovic)', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('stats_team_info/14882')) {
        return jsonResponse({
          team: { _id: 14882, _sid: 5, name: 'Djokovic, Novak', abbr: 'DJO' },
          turnedpro: '2003',
          dateofbirth: '1987-05-22',
          nationality: 'Serbia',
          height: '188',
          weight: '77',
          plays: 'Right',
          singlesrank: 12,
          coachname: 'Goran Ivanisevic',
          favouritesurface: 'Hard',
          highestranking: { singles: { date: '07.2011', ranking: 1 } },
          groundstats: [
            {
              groundid: 0,
              ground: 'All surfaces',
              total: 28,
              matcheswon: 19,
              matcheswon_percent: 67.86,
              matcheslost: 9,
              matcheslost_percent: 32.14,
            },
          ],
          ranking: { ranking: 12, points: 3090 },
          performance: [
            { typename: 'serve_receiver_performance_percentage', value: 0.3598 },
          ],
        });
      }
      if (url.includes('tennis_team_surfacestats/14882')) {
        return jsonResponse({
          singles: {
            '2026': {
              '0': { groundid: 0, wins: 18, losses: 8 },
              '1': { groundid: 1, wins: 2, losses: 2 },
              '2': { groundid: 2, wins: 11, losses: 5 },
              '3': { groundid: 3, wins: 0, losses: 0 },
              '4': { groundid: 4, wins: 5, losses: 1 },
            },
          },
        });
      }
      if (url.includes('stats_team_streaks/14882')) {
        return jsonResponse({
          streaks: { Wins: { total: { value: 4 } } },
        });
      }
      if (url.includes('stats_team_lastxextended/14882')) {
        return jsonResponse({
          matches: [
            {
              _id: 71001,
              teams: {
                home: { _id: 14882, name: 'Djokovic, Novak' },
                away: { _id: 50002, name: 'Alcaraz, Carlos' },
              },
              result: { home: 2, away: 1, winner: 'home' },
              periods: { p1: { home: 6, away: 4 }, p2: { home: 4, away: 6 }, p3: { home: 6, away: 3 } },
            },
          ],
        });
      }
      if (url.includes('stats_team_nextx/14882')) {
        return jsonResponse({ matches: [] });
      }
      return new Response('Not Found', { status: 404 });
    });

    const client = new BetScoutClient({ fetchFn: mockFetch });
    const bundle = await client.getTennisPlayerIntelligenceBundle(14882);

    expect(bundle.ok).toBe(true);
    expect(bundle.player_id).toBe(14882);
    expect(bundle.profile?.team?.name).toBe('Djokovic, Novak');
    expect(bundle.profile?.turnedpro).toBe('2003');
    expect(bundle.profile?.singlesrank).toBe(12);
    expect(bundle.profile?.highestranking?.singles?.ranking).toBe(1);
    expect(bundle.profile?.ranking?.points).toBe(3090);
    expect(bundle.current_surface_summary).toEqual({
      season_wl: '18-8',
      hard_wl: '11-5',
      clay_wl: '2-2',
      indoor_wl: '0-0',
      grass_wl: '5-1',
    });
    expect(bundle.streaks).toEqual(['Wins: 4']);
    expect(bundle.last_matches.length).toBe(1);
    expect(bundle.last_matches[0]?.result?.home).toBe(2);
  });

  it('builds a complete Club Historical & Season Intelligence Bundle for teamId=2692 (AC Milan) and playerId=191210 (Mike Maignan)', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('stats_team_info/2692')) {
        return jsonResponse({
          team: { _id: 2692, _sid: 1, name: 'Milan', mediumname: 'AC Milan', abbr: 'ACM', founded: '1899' },
          twitter: 'acmilan',
          hashtag: '#ACMilan',
          stadium: { name: 'San Siro', city: 'Milan', capacity: 80018 },
        });
      }
      if (url.includes('uniqueteam_seasons/2692')) {
        return jsonResponse({
          seasons: [
            { _id: '130971', _utid: 23, name: 'Serie A 25/26', year: '25/26', containsdata: true },
          ],
        });
      }
      if (url.includes('stats_team_streaks/2692')) {
        return jsonResponse({
          streaks: { Unbeaten: { total: { value: 5 } } },
          nextmatches: [{ matchid: 88001, matchdifficultyrating: 3 }],
        });
      }
      if (url.includes('stats_team_lastx/2692')) {
        return jsonResponse({
          matches: [
            {
              _id: 76001,
              _seasonid: 130971,
              teams: {
                home: { _id: 2692, name: 'AC Milan' },
                away: { _id: 2697, name: 'Inter' },
              },
              result: { home: 2, away: 1, winner: 'home' },
            },
          ],
        });
      }
      if (url.includes('stats_team_nextx/2692')) {
        return jsonResponse({ matches: [] });
      }
      if (url.includes('stats_team_squad/2692')) {
        return jsonResponse({
          players: [
            {
              _id: 191210,
              name: 'Maignan, Mike',
              fullname: 'Maignan, Mike Peterson',
              height: 191,
              weight: 89,
              foot: 'Right',
              position: { shortname: 'GK', name: 'Goalkeeper' },
            },
          ],
        });
      }
      if (url.includes('stats_team_seasonstats/2692/130971')) {
        return jsonResponse({
          stats: {
            goal_attempts: '11.92',
            shots_on_goal: '4.16',
            ball_possession: '51.79',
            corner_kicks: '4.26',
          },
        });
      }
      if (url.includes('stats_season_teamscoringconceding/130971/2692')) {
        return jsonResponse({
          stats: {
            totalmatches: { total: 10, home: 5, away: 5 },
            totalwins: { total: 6, home: 4, away: 2 },
            scoring: {
              goalsscored: { total: 18, home: 11, away: 7 },
              goalsscoredfirsthalfaverage: { total: 0.9 },
              scoringathalftimeaverage: { total: 0.7 },
              bothteamsscoredaverage: { total: 0.6 },
              goalsbyminutes: {
                '0-15': { total: 0.3 },
                '76-90': { total: 0.5 },
              },
            },
            conceding: {
              goalsconceded: { total: 9, home: 4, away: 5 },
              goalsconcededfirsthalfaverage: { total: 0.4 },
              goalsbyminutes: {
                '0-15': { total: 0.1 },
                '76-90': { total: 0.2 },
              },
            },
          },
        });
      }
      if (url.includes('stats_team_usuallineup/2692/130971')) {
        return jsonResponse({
          formation: '3-5-2',
          players: [{ _id: 191210, name: 'Maignan, Mike' }],
        });
      }
      if (url.includes('stats_season_injuries/130971')) {
        return jsonResponse([
          {
            _playerid: 4001,
            uniqueteam: { _id: 2692, name: 'Milan' },
            player: { _id: 4001, name: 'Gabbia, Matteo', shirtnumber: '46', position: { shortname: 'DEF' } },
            status: {
              _id: 1,
              name: 'Injured',
              status: 'Missing',
              start: { date: '22/10/26', uts: 1792627200 },
              end: { date: '17/01/27', uts: 1899999999 },
            },
          },
          {
            _playerid: 4002,
            uniqueteam: { _id: 2692, name: 'Milan' },
            player: { _id: 4002, name: 'Fofana, Youssouf', shirtnumber: '29', position: { shortname: 'MID' } },
            status: {
              _id: 0,
              name: 'Other',
              status: 'Missing',
              start: { date: '28/08/26', uts: 1700000000 },
              end: { date: '06/09/26', uts: 1700500000 }, // Expired in the past
            },
          },
        ]);
      }
      if (url.includes('stats_player_stats/191210')) {
        return jsonResponse({
          player: { _id: 191210, name: 'Maignan, Mike' },
          seasons: { '130971': { matches_played: 28, clean_sheets: 12 } },
        });
      }
      if (url.includes('player_seasonmatches/191210/130971')) {
        return jsonResponse({
          player: { _id: 191210, name: 'Maignan, Mike' },
          matches: [{ _id: 76001, result: { home: 2, away: 1 } }],
        });
      }
      return new Response('Not Found', { status: 404 });
    });

    const client = new BetScoutClient({ fetchFn: mockFetch });
    const clubBundle = await client.getTeamIntelligenceBundle(2692);

    expect(clubBundle.ok).toBe(true);
    expect(clubBundle.team_id).toBe(2692);
    expect(clubBundle.profile?.team?.mediumname).toBe('AC Milan');
    expect(clubBundle.profile?.team?.founded).toBe('1899');
    expect(clubBundle.active_season_id).toBe(130971);
    expect(clubBundle.season_stats?.ball_possession).toBe('51.79');
    expect(clubBundle.usual_lineup?.formation).toBe('3-5-2');
    expect(clubBundle.squad_count).toBe(1);
    expect(clubBundle.squad[0]?.name).toBe('Maignan, Mike');
    expect(clubBundle.missing_players.length).toBe(1);
    expect(clubBundle.missing_players[0]?.name).toBe('Gabbia, Matteo');
    expect(clubBundle.missing_players[0]?.cause).toBe('Injured');
    expect(clubBundle.goal_intervals.btts_pct).toBe(60);
    expect(clubBundle.goal_intervals.late_76_90_total_avg).toBe(0.7);
    expect(clubBundle.streaks).toEqual(['Unbeaten: 5']);

    // Individual squad player career & season match logs
    const pCareer = await client.getPlayerCareerStats(191210);
    expect(pCareer?.player?.name).toBe('Maignan, Mike');
    const pMatches = await client.getPlayerSeasonMatches(191210, 130971);
    expect(pMatches?.matches?.length).toBe(1);
  });
});

describe('@betscout/sdk — 3s Live Timeline Delta Stream & Match Intelligence Workflows', () => {
  it('computes adaptive refetch intervals and merges match_timelinedelta updates', () => {
    expect(getAdaptiveRefetchIntervalMs({ event: 'match_timelinedelta', _maxage: 3, data: {} })).toBe(
      3000,
    );
    expect(getAdaptiveRefetchIntervalMs({ event: 'event_get', _maxage: 10, data: {} })).toBe(10000);

    const baseMatch: BetScoutMatchSummary = {
      _id: 70253720,
      updated_uts: 1000,
      result: { home: 0, away: 0 },
    };
    const merged = mergeLatestMatchDelta(baseMatch, {
      match: {
        _id: 70253720,
        updated_uts: 1005,
        result: { home: 1, away: 0 },
      },
    });
    expect(merged.result?.home).toBe(1);
  });

  it('formats live Tennis set scores, game points, and active server indicator (🎾)', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('unified_sport_matches/5/2026-04-20/0')) {
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
                    _id: 101,
                    name: 'ATP Barcelona, Spain',
                    matches: [
                      {
                        _id: 70253720,
                        _seasonid: 130001,
                        _dt: { uts: 1776686400 },
                        status: { _id: 9, name: '2nd set' },
                        teams: {
                          home: { _id: 1, uid: 1001, name: 'Lehecka, Jiri' },
                          away: { _id: 2, uid: 1002, name: 'Fils, Arthur' },
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
      if (url.includes('match_timelinedelta/70253720')) {
        return jsonResponse(
          {
            match: {
              _id: 70253720,
              _seasonid: 130001,
              status: { _id: 9, name: '2nd set' },
              result: { home: 1, away: 0 },
              periods: {
                p1: { home: 6, away: 4 },
                p2: { home: 3, away: 2 },
              },
              gamescore: { home: '40', away: '15', service: '1' },
            },
          },
          3,
        );
      }
      return new Response('Not Found', { status: 404 });
    });

    const client = new BetScoutClient({ fetchFn: mockFetch });
    const live = await client.fetchLiveMatchTimelineDelta(
      'Jiri Lehecka',
      'Arthur Fils',
      'tennis',
      '2026-04-20',
    );

    expect(live.state).toBe('in');
    expect(live.match_id).toBe(70253720);
    expect(live.score_str).toBe('1-0 (6-4, 3-2 · Pt 🎾40-15)');
    expect(live.point_score).toBe('Pt 🎾40-15');
  });

  it('evaluates pre-match injury gates and recommends veto on depleted squads', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse([
        {
          uniqueteam: { _id: 2672 },
          player: { _id: 10, name: 'Kane, Harry', position: { shortname: 'FWD' } },
          status: { name: 'Injured' },
        },
        {
          uniqueteam: { _id: 2672 },
          player: { _id: 11, name: 'Musiala, Jamal', position: { shortname: 'FWD' } },
          status: { name: 'Injured' },
        },
        {
          uniqueteam: { _id: 2672 },
          player: { _id: 12, name: 'Neuer, Manuel', position: { shortname: 'GK' } },
          status: { name: 'Injured' },
        },
      ]),
    );

    const client = new BetScoutClient({ fetchFn: mockFetch });
    const gate = await client.evaluateInjuryGate(118691, 2672, 2673);

    expect(gate.veto_recommended).toBe(true);
    expect(gate.backed_fwd_out).toBe(2);
    expect(gate.backed_gk_out).toBe(1);
    expect(gate.prob_adjustment).toBeLessThan(0);
    expect(gate.status).toContain('ALERT_DEPLETED_SQUAD');
  });
});

describe('@betscout/sdk — Visual Assets, Insights, Venues & Team Futures Markets', () => {
  it('builds tokenless team logo URLs, SVG/PNG country flags, jersey SVG avatars, and venue coordinates', () => {
    expect(getTeamLogoUrl(2692, { size: 'big' })).toMatch(/\/ls\/crest\/big\/2692\.png$/);
    expect(getTeamLogoUrl(2509, { ncaa: true, ncaaSize: 'ap250x188ut' })).toMatch(
      /\/ls\/teams\/ap250x188ut\/2509\.png$/,
    );
    expect(getCountryFlagUrl('rs', { format: 'svg', ratio: '4x3' })).toMatch(
      /\/ls\/crest\/4x3\/rs\.svg$/,
    );
    expect(getCountryFlagUrl('en', { format: 'svg', ratio: '4x3' })).toMatch(
      /\/ls\/crest\/4x3\/gb-eng\.svg$/,
    );
    expect(getCountryFlagUrl('it', { format: 'png', size: 'medium' })).toMatch(
      /\/ls\/crest\/medium\/it\.png$/,
    );

    const svg = renderTeamJerseySvg(
      { base: 'ff0000', sleeve: '121212', number: 'f8f6f6', stripes: '000000' },
      { shirtNumber: 16, sizePx: 96 },
    );
    expect(svg).toContain('<svg');
    expect(svg).toContain('#ff0000');
    expect(svg).toContain('>16</text>');

    expect(parseVenueCoordinates('45.478025,9.124206')).toEqual({
      lat: 45.478025,
      lng: 9.124206,
    });
  });

  it('fetches Match Insights, Editorial Commentary, Venue Stats (San Siro 647), Squad Market Values, and Team Markets', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('match_funfacts/71945344')) {
        return jsonResponse({
          _id: 71945344,
          funfacts: [
            "Udinese haven't won in their last 6 games.",
            "Milan's away record this season: 1-3-0.",
          ],
          facts: [{ _id: 1, _typeid: 1, sentence: "Udinese haven't won in their last 6 games." }],
        });
      }
      if (url.includes('match_phrases/71945344')) {
        return jsonResponse({
          owncommentary: true,
          phrases: [
            { _id: 'p1', time: 1, text: 'The whistle has gone to start the match.' },
          ],
        });
      }
      if (url.includes('stats_season_venuestats/647/130971')) {
        return jsonResponse({
          stadium: {
            _id: '647',
            name: 'Stadio Giuseppe Meazza',
            city: 'Milan',
            capacity: '80018',
            googlecoords: '45.478025,9.124206',
            pitchsize: { x: 105, y: 68 },
          },
          statistics: {
            venue_home_goals: '75',
            venue_away_goals: '37',
            venue_home_corner_kicks: '234',
            venue_yellow_cards: '133',
          },
        });
      }
      if (url.includes('stats_teamplayer_facts/2692/130971')) {
        return jsonResponse({
          '191210': {
            player: {
              _id: 191210,
              name: 'Maignan, Mike',
              marketvalue: 45000000,
              shirtnumber: '16',
            },
            stats: {
              total: { matches: 37, minutes_played: 3296, yellow_cards: 4 },
            },
          },
        });
      }
      if (url.includes('uniqueteam_markets/2692')) {
        return jsonResponse({
          matches: {
            '61061467': {
              markets: [
                {
                  _marketId: 1,
                  _bookmakerId: 176,
                  outcomes: [{ _id: 'sr:outcome:1', name: '{$competitor1}', odds: 1.85 }],
                },
              ],
            },
          },
        });
      }
      return new Response('Not Found', { status: 404 });
    });

    const client = new BetScoutClient({ fetchFn: mockFetch });

    const insights = await client.getMatchInsights(71945344);
    expect(insights?.funfacts?.length).toBe(2);

    const commentary = await client.getMatchCommentary(71945344);
    expect(commentary?.phrases?.[0]?.text).toContain('whistle');

    const sanSiro = await client.getVenueSeasonStats(647, 130971);
    expect(sanSiro?.stadium?.name).toBe('Stadio Giuseppe Meazza');
    expect(sanSiro?.stadium?.capacity).toBe('80018');
    expect(sanSiro?.statistics?.venue_home_goals).toBe('75');

    const squadFacts = await client.getTeamPlayerSeasonFacts(2692, 130971);
    expect(squadFacts?.['191210']?.player?.marketvalue).toBe(45000000);
    expect(squadFacts?.['191210']?.stats?.total?.minutes_played).toBe(3296);

    const teamMarkets = await client.getTeamMarkets(2692, 'eu-retail');
    expect(teamMarkets?.matches?.['61061467']?.markets?.[0]?.outcomes?.[0]?.odds).toBe(1.85);
  });

  it('merges League Standings (goal stats, rank changes, promotions) with Form Table into EnrichedLeagueTableBundle', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('stats_season_tables/140782')) {
        return jsonResponse({
          _id: '140782',
          name: 'Serie A 26/27',
          tables: [
            {
              _id: '108262',
              name: 'Serie A 26/27',
              currentround: 9,
              maxrounds: 38,
              rules: { name: '1. Head-to-head\n2. Goal difference' },
              tablerows: [
                {
                  pos: 1,
                  posHome: 3,
                  posAway: 1,
                  changeTotal: 1,
                  changeHome: 0,
                  changeAway: 2,
                  promotion: { _id: 1, name: 'Champions League', shortname: 'CL' },
                  team: { _id: 9267, uid: 2699, name: 'Lazio', mediumname: 'Lazio Rome', abbr: 'LAZ' },
                  total: 9,
                  home: 4,
                  away: 5,
                  winTotal: 8,
                  winHome: 3,
                  winAway: 5,
                  drawTotal: 1,
                  drawHome: 1,
                  drawAway: 0,
                  lossTotal: 0,
                  lossHome: 0,
                  lossAway: 0,
                  goalsForTotal: 22,
                  goalsForHome: 8,
                  goalsForAway: 14,
                  goalsAgainstTotal: 7,
                  goalsAgainstHome: 4,
                  goalsAgainstAway: 3,
                  goalDiffTotal: 15,
                  goalDiffHome: 4,
                  goalDiffAway: 11,
                  pointsTotal: 25,
                  pointsHome: 10,
                  pointsAway: 15,
                },
                {
                  pos: 2,
                  posHome: 1,
                  posAway: 4,
                  changeTotal: -1,
                  changeHome: 0,
                  changeAway: -1,
                  promotion: { _id: 1, name: 'Champions League', shortname: 'CL' },
                  team: { _id: 9246, uid: 2692, name: 'Milan', mediumname: 'AC Milan', abbr: 'ACM' },
                  total: 9,
                  home: 5,
                  away: 4,
                  winTotal: 6,
                  winHome: 4,
                  winAway: 2,
                  drawTotal: 2,
                  drawHome: 1,
                  drawAway: 1,
                  lossTotal: 1,
                  lossHome: 0,
                  lossAway: 1,
                  goalsForTotal: 18,
                  goalsForHome: 11,
                  goalsForAway: 7,
                  goalsAgainstTotal: 8,
                  goalsAgainstHome: 3,
                  goalsAgainstAway: 5,
                  goalDiffTotal: 10,
                  goalDiffHome: 8,
                  goalDiffAway: 2,
                  pointsTotal: 20,
                  pointsHome: 13,
                  pointsAway: 7,
                },
              ],
            },
          ],
        });
      }
      if (url.includes('stats_formtable/140782')) {
        return jsonResponse({
          currentround: 9,
          teams: [
            {
              team: { _id: 9267, uid: 2699, name: 'Lazio' },
              form: {
                // Raw feed stores newest first; getEnrichedLeagueTable reverses to chronological order
                total: [
                  { typeid: 'W', value: 'W', matchid: 103 },
                  { typeid: 'D', value: 'D', matchid: 102 },
                  { typeid: 'W', value: 'W', matchid: 101 },
                ],
                home: [{ typeid: 'W', value: 'W', matchid: 103 }],
                away: [{ typeid: 'D', value: 'D', matchid: 102 }],
              },
            },
            {
              team: { _id: 9246, uid: 2692, name: 'Milan' },
              form: {
                total: [
                  { typeid: 'W', value: 'W', matchid: 203 },
                  { typeid: 'L', value: 'L', matchid: 202 },
                  { typeid: 'D', value: 'D', matchid: 201 },
                ],
              },
            },
          ],
        });
      }
      return new Response('Not Found', { status: 404 });
    });

    const client = new BetScoutClient({ fetchFn: mockFetch });
    const table = await client.getEnrichedLeagueTable(140782);

    expect(table.ok).toBe(true);
    expect(table.season_name).toBe('Serie A 26/27');
    expect(table.current_round).toBe(9);
    expect(table.max_rounds).toBe(38);
    expect(table.rows.length).toBe(2);

    const row1 = table.rows[0]!;
    expect(row1.team_name).toBe('Lazio Rome');
    expect(row1.pos).toBe(1);
    expect(row1.change_total).toBe(1);
    expect(row1.promotion).toBe('Champions League');
    expect(row1.goals_for).toEqual({ total: 22, home: 8, away: 14 });
    expect(row1.goals_against).toEqual({ total: 7, home: 4, away: 3 });
    expect(row1.goal_diff).toEqual({ total: 15, home: 4, away: 11 });
    expect(row1.points).toEqual({ total: 25, home: 10, away: 15 });
    expect(row1.form_total).toEqual(['W', 'D', 'W']);

    const row2 = table.rows[1]!;
    expect(row2.team_name).toBe('AC Milan');
    expect(row2.change_total).toBe(-1);
    expect(row2.form_total).toEqual(['D', 'L', 'W']);
  });

  it('fetches Season Goal Timing (firstgoal/avg time), Over/Under Half Splits, NBA Pace/Efficiency, H2H Versus, and Cup Brackets', async () => {
    const mockFetch = vi.fn<typeof fetch>().mockImplementation(async (urlInput) => {
      const url = String(urlInput);
      if (url.includes('stats_season_goals/140782')) {
        return jsonResponse({
          teams: [
            {
              team: { _id: 9264, uid: 2697, name: 'Inter', mediumname: 'Inter Milano' },
              scored: { '0-15': 3, '76-90': 7 },
              scoredsum: 23,
              conceded: { '0-15': 3, '76-90': 1 },
              concededsum: 10,
              firstgoal: 6,
              lastgoal: 7,
              average_time_first_goal: 36.25,
              matches: 8,
              penalty_success_count: '2',
            },
          ],
          totals: { scoredsum: 259, average_time_first_goal: 31.45, matches: 83 },
        });
      }
      if (url.includes('stats_season_overunder/140782')) {
        return jsonResponse({
          values: { '1': '0.5', '2': '1.5', '3': '2.5' },
          stats: {
            '2692': {
              team: { _id: 2692, name: 'Milan' },
              matches: 8,
              winrate: {
                ft: { matches: 8, wins: 5, average: 0.63 },
                p1: { matches: 8, wins: 3, average: 0.38 },
                p2: { matches: 8, wins: 4, average: 0.5 },
              },
              total: {
                ft: { '2.5': { over: 4, under: 4 } },
                p1: { '0.5': { over: 4, under: 4 } },
                p2: { '0.5': { over: 8, under: 0 } },
              },
            },
          },
        });
      }
      if (url.includes('stats_season_uniqueteamstats/142074')) {
        return jsonResponse({
          stats: {
            uniqueteams: {
              '3433': {
                uniqueteam: { _id: 3433, name: 'Toronto', mediumname: 'Toronto Raptors' },
                points_scored: { average: 113.67, total: 341, matches: 3 },
                possessions_per_game: { average: 107.24, total: 321.72, matches: 3 },
                points_per_possession: { average: 1.06, matches: 3 },
              },
            },
          },
        });
      }
      if (url.includes('stats_team_versus/2692/2697/10')) {
        return jsonResponse({
          matches: [
            {
              _id: 71913828,
              comment: '0:1 (52.) F.Dimarco, 1:1 (83.) C.Nkunku',
              result: { home: 1, away: 1 },
            },
          ],
          currentmanagers: {
            '2692': [{ name: 'Allegri, Massimiliano' }],
          },
        });
      }
      if (url.includes('uniquetournament_seasonswinners/23')) {
        return jsonResponse({
          seasons: [
            {
              _id: '130971',
              name: 'Serie A 25/26',
              year: '25/26',
              champion: { _id: 2697, name: 'Inter', mediumname: 'Inter Milano' },
            },
          ],
        });
      }
      if (url.includes('stats_cup_brackets/110232')) {
        return jsonResponse({
          bracket: { _id: 110232, type: 'Single-elimination, dynamic' },
          cup: { _id: '198114', name: 'UEFA Champions League 26/27, Playoff Round' },
        });
      }
      return new Response('Not Found', { status: 404 });
    });

    const client = new BetScoutClient({ fetchFn: mockFetch });

    const goals = await client.getSeasonGoalsDistribution(140782);
    expect(goals?.teams?.[0]?.firstgoal).toBe(6);
    expect(goals?.teams?.[0]?.average_time_first_goal).toBe(36.25);

    const ou = await client.getSeasonOverUnder(140782);
    expect(ou?.stats?.['2692']?.total?.p2?.['0.5']?.over).toBe(8);
    expect(ou?.stats?.['2692']?.winrate?.p2?.average).toBe(0.5);

    const nbaStats = await client.getSeasonUniqueTeamStats(142074);
    expect(nbaStats?.stats?.uniqueteams?.['3433']?.points_scored?.average).toBe(113.67);
    expect(nbaStats?.stats?.uniqueteams?.['3433']?.possessions_per_game?.average).toBe(107.24);

    const versus = await client.getTeamVersus(2692, 2697, 10);
    expect(versus?.matches?.[0]?.comment).toContain('Dimarco');

    const winners = await client.getTournamentSeasonsWinners(23);
    expect(winners?.seasons?.[0]?.champion?.mediumname).toBe('Inter Milano');

    const brackets = await client.getCupBrackets(110232);
    expect(brackets?.cup?.name).toContain('Champions League');
  });
});
