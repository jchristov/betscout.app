import { describe, expect, it, vi } from 'vitest';
import {
  BetScoutMcpServer,
  MCP_TOOLS_CATALOG,
  decodeCursor,
  encodeCursor,
  paginateItems,
} from '../src/index.js';

function createMockSnapshot() {
  return {
    ok: true,
    generated_at: '2026-10-29T10:02:00Z',
    generated_at_local: '2026-10-29 11:02 CET',
    best_bets: [
      {
        match: 'AS Roma vs Cagliari',
        home: 'AS Roma',
        away: 'Cagliari',
        sport_cat: 'soccer',
        competition: 'Serie A',
        date_local: '2026-10-29 20:45 CET',
        pick: 'H',
        pick_name: 'AS Roma',
        tier: 'top_8pct',
        win_prob: 0.812,
        odds: 1.36,
        min_fair_odds: 1.23,
        edge_pp: 4.5,
        is_mispriced: true,
        exact_score_pick: '2:0 (16.4%) · Cluster 2:0 / 1:0 / 2:1 (42.4%)',
        score_cluster_items: [
          { label: '2:0', prob: 0.164, fair_odds: 6.1, book_odds: 6.5 },
          { label: '1:0', prob: 0.148, fair_odds: 6.75, book_odds: 7.0 },
          { label: '2:1', prob: 0.112, fair_odds: 8.9, book_odds: 8.5 },
        ],
      },
      {
        match: 'Tommy Paul vs Luciano Darderi',
        home: 'Tommy Paul',
        away: 'Luciano Darderi',
        sport_cat: 'tennis',
        competition: 'ATP · Vienna, Austria',
        date_local: '2026-10-29 15:30 CET',
        pick: 'H',
        pick_name: 'Tommy Paul',
        tier: 'banker_70pct',
        win_prob: 0.745,
        odds: 1.22,
        min_fair_odds: 1.34,
        edge_pp: 1.2,
        is_mispriced: false,
        exact_score_pick: 'Sets 2:0 (51.8%, Fair 1.93) / 2:1 (26.2%)',
        score_cluster_items: [],
      },
    ],
    recommended_doubles: [
      {
        leg_1_match: 'AS Roma vs Cagliari',
        leg_1_league: 'Serie A',
        leg_1_pick: 'AS Roma',
        leg_1_odds: 1.36,
        leg_1_prob: 0.812,
        leg_2_match: 'Tommy Paul vs Luciano Darderi',
        leg_2_league: 'ATP Vienna',
        leg_2_pick: 'Tommy Paul',
        leg_2_odds: 1.22,
        leg_2_prob: 0.745,
        combined_odds: 1.66,
        combined_prob: 0.605,
        ev_pct: 4.2,
      },
    ],
    paper_ledger: {
      settled_count: 75,
      settled_wins: 74,
      settled_losses: 1,
      settled_profit_u: 29.16,
      settled_roi_best: 0.389,
      mean_clv_pct: 0.014,
      exact_score_hit_rate_pct: 68.6,
      live_count: 0,
      pending_count: 12,
      by_sport: [
        { sport: 'SOCCER', settled: 28, wins: 28, losses: 0, win_rate_pct: 100.0, profit_u: 11.4, roi_pct: 40.7 },
        { sport: 'TENNIS', settled: 22, wins: 22, losses: 0, win_rate_pct: 100.0, profit_u: 8.2, roi_pct: 37.3 },
      ],
      bets: [
        {
          event_id: '401874780',
          kickoff: '2026-10-27T19:45Z',
          league: 'ita.1',
          league_label: 'Serie A',
          sport_cat: 'soccer',
          home: 'AS Roma',
          away: 'Cagliari',
          side: 'H',
          tier: 'top_10pct',
          logged_best_odds: 1.36,
          status: 'SETTLED',
          score_str: '4-2 (2-1)',
          pnl_best: 0.36,
        },
        {
          event_id: '185106',
          kickoff: '2026-10-26T15:30Z',
          league: 'atp',
          league_label: 'ATP Tour',
          sport_cat: 'tennis',
          home: 'Taylor Fritz',
          away: 'Rinky Hijikata',
          side: 'H',
          tier: 'banker_70pct',
          logged_best_odds: 1.22,
          status: 'SETTLED',
          score_str: '2-0 (6-4, 7-6)',
          pnl_best: 0.22,
        },
      ],
    },
  };
}

function createMockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/api/snapshot')) {
      return new Response(JSON.stringify(createMockSnapshot()), { status: 200 });
    }
    if (url.includes('/api/analyze-live')) {
      return new Response(
        JSON.stringify({
          ok: true,
          sport: 'tennis',
          league: 'atp',
          home: 'Tommy Paul',
          away: 'Luciano Darderi',
          fav_name: 'Tommy Paul',
          fav_prob_pct: 69.5,
          fav_mkt_prob_pct: 76.9,
          fav_edge_pp: -7.4,
          fav_ev_pct: -16.6,
          fav_fair_odds: 1.44,
          fav_book_odds: 1.2,
          odds_home: 1.2,
          odds_away: 4.0,
          elo_diff_home: 147.0,
          h2h_summary: 'Tommy Paul 2 – 1 Luciano Darderi',
          h2h: [{ date: '2024-08-07', home: 'Tommy Paul', away: 'Luciano Darderi', score: '2-0', outcome: 'H' }],
          form_home: [{ date: '2026-10-27', opp: 'Andrey Rublev', venue: 'H', result: 'W', score: '2-0' }],
          form_away: [{ date: '2026-10-26', opp: 'Matteo Arnaldi', venue: 'H', result: 'W', score: '2-0' }],
          p1_rest_hours: 48.0,
          p2_rest_hours: 67.3,
          market_recommendations: {
            moneyline: 'Tommy Paul ML (69.5% WinProb, Fair @1.44, Book @1.20)',
            handicap_shield: 'Tommy Paul 2:0 Straight Sets (43.0%, Fair @2.33)',
            totals_cluster: 'Under 21.5 Total Games',
          },
          warnings: [],
          verdict: '⚖️ SOLID VALUE LEAN — Tommy Paul ML',
          verdict_level: 'lean_bet',
          live_intel: { sr_match_id: 75837638 },
        }),
        { status: 200 },
      );
    }
    if (url.includes('match_info_statshub/75837638')) {
      return new Response(
        JSON.stringify({
          doc: [
            {
              event: 'match_info',
              _maxage: 600,
              data: {
                sport: { _id: 5, name: 'Tennis' },
                tournament: { name: 'ATP Vienna', ground: { name: 'Hardcourt indoor' } },
                match: {
                  _id: 75837638,
                  status: { name: 'Not started' },
                  teams: {
                    home: { _id: 138546, uid: 138546, name: 'Paul, Tommy' },
                    away: { _id: 534043, uid: 534043, name: 'Darderi, Luciano' },
                  },
                },
              },
            },
          ],
        }),
        { status: 200 },
      );
    }
    return new Response(
      JSON.stringify({
        doc: [{ event: 'exception', data: { _doc: 'exception', message: 'Not found' } }],
      }),
      { status: 200 },
    );
  });
}

describe('@betscout/mcp-server', () => {
  it('registers all 7 model-oriented tools with rich descriptions and JSON schemas', async () => {
    const server = new BetScoutMcpServer({ fetchFn: createMockFetch() as any });
    const initResp = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
    })) as any;
    expect(initResp.result.protocolVersion).toBe('2024-11-05');
    expect(initResp.result.serverInfo.name).toBe('@betscout/mcp-server');

    const listResp = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
    })) as any;
    expect(listResp.result.tools).toHaveLength(7);
    for (const tool of MCP_TOOLS_CATALOG) {
      expect(tool.description.length).toBeGreaterThan(120);
      expect(tool.inputSchema.type).toBe('object');
    }
  });

  it('supports opaque cursor pagination without leaking page numbers', () => {
    const items = ['a', 'b', 'c', 'd', 'e'];
    const p1 = paginateItems(items, { limit: 2 });
    expect(p1.items).toEqual(['a', 'b']);
    expect(p1.has_more).toBe(true);
    expect(p1.next_cursor).toBeTruthy();

    const p2 = paginateItems(items, { limit: 2, cursor: p1.next_cursor });
    expect(p2.items).toEqual(['c', 'd']);
    expect(decodeCursor(encodeCursor(4))).toBe(4);
    expect(() => decodeCursor('invalid_cursor_$$$')).toThrow(/Invalid pagination cursor/);
  });

  it('executes get_daily_banker_picks, get_banker_profit_boosters, analyze_matchup, calculate_exact_score_dutching, and get_paper_ledger_roi with API caching', async () => {
    const mockFetch = createMockFetch();
    const server = new BetScoutMcpServer({ fetchFn: mockFetch as any });

    // 1. get_daily_banker_picks
    const picksResp = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 10,
      method: 'tools/call',
      params: {
        name: 'get_daily_banker_picks',
        arguments: { sport: 'all', min_win_prob: 0.7 },
      },
    })) as any;
    expect(picksResp.result.isError).toBe(false);
    const picksData = JSON.parse(picksResp.result.content[0].text);
    expect(picksData.picks.length).toBe(2);

    // 2. get_banker_profit_boosters
    const boostResp = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 11,
      method: 'tools/call',
      params: {
        name: 'get_banker_profit_boosters',
        arguments: { budget_eur: 80 },
      },
    })) as any;
    expect(boostResp.result.isError).toBe(false);
    const boostData = JSON.parse(boostResp.result.content[0].text);
    expect(boostData.combos[0].recommended_stake_eur).toBe(80);

    // 3. analyze_matchup + verify API cache hit on second call
    const anResp1 = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 12,
      method: 'tools/call',
      params: {
        name: 'analyze_matchup',
        arguments: { query: 'Tommy Paul vs Luciano Darderi' },
      },
    })) as any;
    expect(anResp1.result.isError).toBe(false);

    // 4. calculate_exact_score_dutching (reuses cached analyze_matchup response!)
    const dutchResp = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 13,
      method: 'tools/call',
      params: {
        name: 'calculate_exact_score_dutching',
        arguments: { query: 'Tommy Paul vs Luciano Darderi', stake_eur: 40 },
      },
    })) as any;
    expect(dutchResp.result.isError).toBe(false);
    const dutchData = JSON.parse(dutchResp.result.content[0].text);
    expect(dutchData.total_stake_eur).toBe(40);
    expect(dutchData.legs.length).toBe(2);
    expect(server.client.getCacheTelemetry().api_cache_hits).toBeGreaterThanOrEqual(1);

    // 5. get_paper_ledger_roi with cursor pagination
    const ledResp1 = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 14,
      method: 'tools/call',
      params: {
        name: 'get_paper_ledger_roi',
        arguments: { status: 'settled', limit: 1 },
      },
    })) as any;
    const ledData1 = JSON.parse(ledResp1.result.content[0].text);
    expect(ledData1.summary.wins).toBe(74);
    expect(ledData1.pagination.has_more).toBe(true);

    const ledResp2 = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 15,
      method: 'tools/call',
      params: {
        name: 'get_paper_ledger_roi',
        arguments: { status: 'settled', limit: 1, cursor: ledData1.pagination.next_cursor },
      },
    })) as any;
    const ledData2 = JSON.parse(ledResp2.result.content[0].text);
    expect(ledData2.rows[0].match).toBe('Taylor Fritz vs Rinky Hijikata');

    // 6. Actionable error recovery on invalid input
    const badCursorResp = (await server.handleJsonRpc({
      jsonrpc: '2.0',
      id: 16,
      method: 'tools/call',
      params: {
        name: 'get_paper_ledger_roi',
        arguments: { cursor: 'not-a-valid-cursor-!!!' },
      },
    })) as any;
    expect(badCursorResp.result.isError).toBe(true);
    expect(badCursorResp.result.content[0].text).toContain('Invalid pagination cursor');
  });
});
