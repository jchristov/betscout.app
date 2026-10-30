/**
 * 7 Model-Oriented Tools for `@betscout/mcp-server`:
 *   1. `get_daily_banker_picks`
 *   2. `get_banker_profit_boosters`
 *   3. `analyze_matchup`
 *   4. `calculate_exact_score_dutching`
 *   5. `get_match_center_dossier`
 *   6. `search_daily_fixtures`
 *   7. `get_paper_ledger_roi`
 */

import type { BetScoutMcpBackendClient } from '../client.js';
import { BetScoutMcpError, formatMcpToolError } from '../errors.js';
import { paginateItems } from '../pagination.js';

export interface McpToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
}

export interface McpToolCallResult {
  content: Array<{ type: 'text'; text: string }>;
  isError?: boolean;
}

export const MCP_TOOLS_CATALOG: readonly McpToolDefinition[] = [
  {
    name: 'get_daily_banker_picks',
    description:
      "Retrieve BetScout's active pre-match and live high-conviction picks across Football, Tennis, Basketball (NBA), Ice Hockey (NHL), American Football (NFL), Handball, Table Tennis, and Darts. Use this tool when the user asks for today's best bets, high-probability banker recommendations, mispriced bookmaker edges, or sport-specific slates. Do NOT use this tool to analyze an arbitrary unscheduled matchup — use `analyze_matchup` for custom team/player matchups instead.",
    inputSchema: {
      type: 'object',
      properties: {
        sport: {
          type: 'string',
          description:
            "Filter by sport category ('all', 'soccer', 'tennis', 'basketball', 'hockey', 'nfl', 'handball', 'table_tennis', 'darts'). Default: 'all'.",
          enum: [
            'all',
            'soccer',
            'tennis',
            'basketball',
            'hockey',
            'nfl',
            'handball',
            'table_tennis',
            'darts',
          ],
        },
        market_filter: {
          type: 'string',
          description:
            "Filter by market type ('all', 'moneyline', 'secondary', 'shield', 'totals'). 'shield' returns Double Chance (1X/X2), Draw No Bet (DNB), and Tennis +1.5 Sets shields; 'totals' returns Over/Under Goals & Games; 'secondary' returns all non-moneyline opportunities. Default: 'all'.",
          enum: ['all', 'moneyline', 'secondary', 'shield', 'totals'],
        },
        min_odds: {
          type: 'number',
          description: 'Minimum decimal bookmaker odds threshold (e.g. 1.15, 1.25). Default: 1.10.',
        },
        min_win_prob: {
          type: 'number',
          description:
            'Minimum calibrated model win probability between 0.50 and 0.99 (e.g. 0.70 for >=70%). Default: 0.55.',
        },
        mispriced_only: {
          type: 'boolean',
          description:
            'When true, return only picks where model probability exceeds vig-free market probability by >=2.0pp with positive EV.',
        },
        limit: {
          type: 'integer',
          description: 'Maximum number of picks to return per call (1-50). Default: 15.',
        },
        cursor: {
          type: 'string',
          description: 'Opaque pagination cursor returned as `next_cursor` from a previous call.',
        },
      },
    },
  },
  {
    name: 'get_banker_profit_boosters',
    description:
      'Construct 2-leg and 3-leg high-probability (>=72% win prob, 1.10-1.48 decimal odds) Banker Profitability Booster combo tickets and quarter-Kelly stake allocations for a given bankroll budget in EUR. Use this tool when the user wants parlay/double/treble recommendations that combine low-odds favorites into higher-yielding 1.35x-2.15x tickets without same-match correlation. Do NOT use this tool for single-match exact-score dutching — use `calculate_exact_score_dutching` instead.',
    inputSchema: {
      type: 'object',
      properties: {
        budget_eur: {
          type: 'number',
          description:
            'Total bankroll/ticket budget in EUR to allocate across recommended combo tickets (e.g. 100). Default: 100.',
        },
        max_combos: {
          type: 'integer',
          description: 'Maximum number of combo tickets to return (1-10). Default: 6.',
        },
      },
    },
  },
  {
    name: 'analyze_matchup',
    description:
      "Run BetScout's live quantitative model (7-factor Football Composite + Dixon-Coles 28-score matrix, or 8-feature Tennis Surface Elo + Markov Set-Score engine) on ANY two teams or players (e.g. 'Medvedev vs Norrie', 'Tommy Paul vs Luciano Darderi', 'AS Roma vs Cagliari'). Use this tool when the user asks about a specific matchup's win probability, fixed set score ('2:0' / '0:2' / '2:1'), '+1.5 Sets' shield, total games/goals over/under, or safety-gate warnings. Do NOT use this tool if you only have a numeric match ID and want raw point-by-point boxscores — use `get_match_center_dossier` for match IDs.",
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description:
            "Matchup query formatted as 'Player1 vs Player2' or 'HomeTeam vs AwayTeam' (e.g. 'Daniil Medvedev vs Cameron Norrie', 'Tommy Paul vs Luciano Darderi').",
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'calculate_exact_score_dutching',
    description:
      'Compute an equal-payout Dutching stake split across the top Exact Scores (Football 1:0 / 2:0 / 2:1) or Set Scores (Tennis 2:0 + 2:1) for a specific matchup and total stake in EUR. Use this tool when the user wants to divide a stake across 2 or 3 exact scores or set results so every winning outcome returns the exact same EUR payout. Do NOT use this tool for multi-match parlays — use `get_banker_profit_boosters` instead.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description:
            "Matchup query formatted as 'Home vs Away' (e.g. 'AS Roma vs Cagliari', 'Valentin Vacherot vs Rafael Jodar').",
        },
        stake_eur: {
          type: 'number',
          description:
            'Total EUR stake to split across the exact score / set score cluster (e.g. 25, 50, 100). Default: 25.',
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_match_center_dossier',
    description:
      'Fetch the complete Match Center intelligence dossier for a specific match (by numeric `match_id` or `home` + `away` names), returning de-vigged 2-way/3-way win probabilities, bookmaker markets (1X2, Asian Handicap, Over/Under, 28 Correct Scores), direct Head-to-Head (H2H) history, Last-5 W/D/L form strips, surface or season scoring splits, missing/injured players, and live boxscore statistics. Use this tool for deep match inspection, H2H verification, injury audits, or live boxscores. Do NOT use this tool to browse a full day\'s schedule — call `search_daily_fixtures` first if you need to discover a `match_id`.',
    inputSchema: {
      type: 'object',
      properties: {
        match_id: {
          type: 'integer',
          description:
            'Numeric Sportradar match ID (e.g. 71945350 for Genoa vs Juventus, 75837638 for Paul vs Darderi). Provide `match_id` OR both `home` and `away`.',
        },
        home: {
          type: 'string',
          description:
            "Home team or Player 1 name when `match_id` is unknown (e.g. 'Genoa', 'Tommy Paul').",
        },
        away: {
          type: 'string',
          description:
            "Away team or Player 2 name when `match_id` is unknown (e.g. 'Juventus', 'Luciano Darderi').",
        },
        sport: {
          type: 'string',
          description:
            "Sport hint when looking up by team/player names ('soccer', 'tennis', 'basketball', 'hockey', 'handball', 'table_tennis', 'darts'). Default: 'soccer'.",
        },
      },
    },
  },
  {
    name: 'search_daily_fixtures',
    description:
      "Search and list scheduled, live, and finished fixtures across 56 sports for a given date (`YYYY-MM-DD`) and sport (e.g. 'soccer', 'tennis', 'basketball', 'hockey', 'handball', 'table_tennis', 'darts'), returning numeric `match_id` values, tournament names, kickoff times, scores, and pre-match odds. Use this tool to find a `match_id` or inspect a day's tournament slate before calling `get_match_center_dossier` or `analyze_matchup`. Supports text filtering via `query` and opaque `cursor` pagination.",
    inputSchema: {
      type: 'object',
      properties: {
        sport: {
          type: 'string',
          description:
            "Sport key ('soccer', 'tennis', 'basketball', 'hockey', 'nfl', 'handball', 'table_tennis', 'darts', 'volleyball', 'baseball'). Default: 'tennis'.",
        },
        date_ymd: {
          type: 'string',
          description: "Date in YYYY-MM-DD format (e.g. '2026-10-29'). Defaults to today in UTC.",
        },
        query: {
          type: 'string',
          description:
            "Optional substring filter matching team/player name or tournament (e.g. 'Vienna', 'Medvedev', 'Serie A').",
        },
        limit: {
          type: 'integer',
          description: 'Maximum number of fixtures to return (1-50). Default: 15.',
        },
        cursor: {
          type: 'string',
          description: 'Opaque pagination cursor returned as `next_cursor` from a previous call.',
        },
      },
    },
  },
  {
    name: 'get_paper_ledger_roi',
    description:
      "Query BetScout's verified out-of-sample Paper-Betting Ledger, returning overall Win-Loss record, net unit profit (+u), ROI%, Closing Line Value (CLV%), exact-score hit rate, by-sport attribution, and paginated settled/live/pending bet history (ordered newest resolved first). Use this tool when the user asks about historical model performance, win rate, ROI by sport, or recent settled results. Supports filtering by `status` ('all', 'settled', 'live', 'pending'), `sport`, and opaque `cursor` pagination.",
    inputSchema: {
      type: 'object',
      properties: {
        status: {
          type: 'string',
          description:
            "Filter ledger entries by status ('all', 'settled', 'live', 'pending'). Default: 'settled'.",
          enum: ['all', 'settled', 'live', 'pending'],
        },
        sport: {
          type: 'string',
          description:
            "Optional sport filter (e.g. 'soccer', 'tennis', 'basketball', 'hockey', 'nfl', 'handball', 'table_tennis', 'darts'). Default: 'all'.",
        },
        limit: {
          type: 'integer',
          description: 'Maximum number of ledger rows to return (1-50). Default: 15.',
        },
        cursor: {
          type: 'string',
          description: 'Opaque pagination cursor returned as `next_cursor` from a previous call.',
        },
      },
    },
  },
] as const;

export async function executeBetScoutMcpTool(
  client: BetScoutMcpBackendClient,
  toolName: string,
  args: Record<string, any> = {},
): Promise<McpToolCallResult> {
  try {
    if (toolName === 'get_daily_banker_picks') {
      const sport = String(args.sport ?? 'all').toLowerCase().trim();
      const marketFilter = String(args.market_filter ?? 'all').toLowerCase().trim();
      const minOdds = Number(args.min_odds ?? 1.1);
      const minWinProb = Number(args.min_win_prob ?? 0.55);
      const mispricedOnly = Boolean(args.mispriced_only ?? false);
      const limit = Number(args.limit ?? 15);
      const cursor = args.cursor as string | undefined;

      const snap = await client.getSnapshot(minOdds, sport);
      const rawBets: any[] = Array.isArray(snap.best_bets) ? snap.best_bets : [];
      const filtered = rawBets
        .filter((b) => {
          const wp = Number(b.win_prob ?? 0);
          if (wp < minWinProb) return false;
          if (mispricedOnly && !b.is_mispriced) return false;
          const mt = String(b.market_type ?? '').toUpperCase();
          const tr = String(b.tier ?? '').toLowerCase();
          const isSec = Boolean(mt) || ['dc_shield', 'dnb_shield', 'set_shield', 'totals_over', 'totals_under', 'straight_sets'].includes(tr);
          if (marketFilter === 'moneyline' && isSec) return false;
          if (marketFilter === 'secondary' && !isSec) return false;
          if (marketFilter === 'shield' && !(['dc_shield', 'dnb_shield', 'set_shield'].includes(tr) || mt.startsWith('DC_') || mt.startsWith('DNB_') || mt.startsWith('SET_HANDICAP'))) return false;
          if (marketFilter === 'totals' && !(['totals_over', 'totals_under', 'straight_sets'].includes(tr) || mt.startsWith('OVER_') || mt.startsWith('UNDER_') || mt.startsWith('SETS_'))) return false;
          return true;
        })
        .map((b) => ({
          match: b.match,
          home: b.home,
          away: b.away,
          sport: b.sport_cat,
          competition: b.competition,
          kickoff_local: b.date_local,
          pick: b.pick_name,
          side: b.pick,
          market_type: b.market_type ?? 'MONEYLINE',
          tier: b.tier,
          win_prob_pct: Number((Number(b.win_prob ?? 0) * 100).toFixed(1)),
          book_odds: b.odds,
          min_fair_odds: b.min_fair_odds,
          edge_pp: b.edge_pp,
          is_mispriced: Boolean(b.is_mispriced),
          exact_score_prediction: b.exact_score_pick,
          score_cluster: b.score_cluster_items ?? [],
          secondary_opportunities: b.secondary_opportunities ?? [],
        }));

      const paged = paginateItems(filtered, { cursor, limit });
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                generated_at: snap.generated_at_local ?? snap.generated_at,
                filters: {
                  sport,
                  market_filter: marketFilter,
                  min_odds: minOdds,
                  min_win_prob: minWinProb,
                  mispriced_only: mispricedOnly,
                },
                picks: paged.items,
                pagination: {
                  returned_count: paged.returned_count,
                  total_available: paged.total_available,
                  has_more: paged.has_more,
                  next_cursor: paged.next_cursor,
                  hint: paged.pagination_hint,
                },
              },
              null,
              2,
            ),
          },
        ],
        isError: false,
      };
    }

    if (toolName === 'get_banker_profit_boosters') {
      const budgetEur = Number(args.budget_eur ?? 100);
      if (!Number.isFinite(budgetEur) || budgetEur <= 0) {
        throw new BetScoutMcpError(
          `Invalid \`budget_eur\` value (${args.budget_eur}).`,
          'Pass a positive EUR amount such as `{"budget_eur": 100}`.',
        );
      }
      const maxCombos = Math.max(1, Math.min(Number(args.max_combos ?? 6), 10));
      const snap = await client.getSnapshot(1.08, 'all');
      const rawDoubles: any[] = Array.isArray(snap.recommended_doubles)
        ? snap.recommended_doubles.slice(0, maxCombos)
        : [];

      const normLeg = (rawL: any, prefix: string, parent: any) => {
        if (rawL && typeof rawL === 'object' && rawL.match) {
          return {
            match: rawL.match,
            sport: rawL.sport_cat ?? 'soccer',
            league: rawL.league,
            kickoff: rawL.kickoff ?? null,
            market: rawL.market ?? 'Moneyline',
            pick: rawL.pick,
            odds: Number(Number(rawL.odds ?? 1).toFixed(2)),
            win_prob_pct: Number((Number(rawL.prob ?? 0) * 100).toFixed(1)),
          };
        }
        if (parent?.[`${prefix}_match`] || parent?.[`${prefix}_pick`]) {
          return {
            match: parent[`${prefix}_match`],
            sport: parent[`${prefix}_sport`] ?? 'soccer',
            league: parent[`${prefix}_league`],
            kickoff: parent[`${prefix}_kickoff`] ?? null,
            market: parent[`${prefix}_market`] ?? 'Moneyline',
            pick: parent[`${prefix}_pick`],
            odds: Number(Number(parent[`${prefix}_odds`] ?? 1).toFixed(2)),
            win_prob_pct: Number((Number(parent[`${prefix}_prob`] ?? 0) * 100).toFixed(1)),
          };
        }
        return null;
      };

      const ticketsRaw: Array<{
        combo_type: string;
        combo_label: string;
        legs: any[];
        combined_odds: number;
        combined_prob: number;
        min_fair_odds: number;
        ev_pct: number;
      }> = [];

      for (const c of rawDoubles) {
        const l1 = normLeg(c.leg_1, 'leg_1', c);
        const l2 = normLeg(c.leg_2, 'leg_2', c);
        if (!l1 || !l2) continue;
        const legs = [l1, l2];
        const l3 = normLeg(c.leg_3, 'leg_3', c);
        if (l3) legs.push(l3);
        const combOdds = Number(c.combined_odds ?? 1.5);
        const combProb = Number(c.combined_prob ?? 0.5);
        const evPct =
          c.ev_pct !== undefined && c.ev_pct !== null
            ? Number(c.ev_pct)
            : Number(((combProb * combOdds - 1) * 100).toFixed(2));
        ticketsRaw.push({
          combo_type: c.combo_type ?? 'BANKER_PROFIT_BOOSTER',
          combo_label: c.combo_label ?? '2-Leg Banker Combo',
          legs,
          combined_odds: Number(combOdds.toFixed(2)),
          combined_prob: combProb,
          min_fair_odds: Number((1 / Math.max(combProb, 0.05)).toFixed(2)),
          ev_pct: Number(evPct.toFixed(2)),
        });
      }

      // Synthesize a 3-Leg Banker Profit Treble when >=3 high-prob (>=72%, 1.10-1.48) bankers exist
      const bankerSingles = (Array.isArray(snap.best_bets) ? snap.best_bets : [])
        .filter(
          (b: any) =>
            Number(b.win_prob ?? 0) >= 0.72 &&
            Number(b.odds ?? 0) >= 1.1 &&
            Number(b.odds ?? 0) <= 1.48 &&
            !String(b.match ?? '').includes('🔒'),
        )
        .sort((a: any, b: any) => Number(b.win_prob) - Number(a.win_prob) || Number(a.odds) - Number(b.odds));

      const distinct3: any[] = [];
      const seenMatches = new Set<string>();
      for (const b of bankerSingles) {
        const mName = String(b.match ?? '');
        if (mName && !seenMatches.has(mName)) {
          seenMatches.add(mName);
          distinct3.push(b);
        }
        if (distinct3.length === 3) break;
      }

      if (distinct3.length === 3) {
        const tLegs = distinct3.map((b) => ({
          match: b.match,
          sport: b.sport_cat,
          league: b.competition ?? b.sport_league,
          kickoff: b.date_local ?? b.date,
          market: 'Moneyline / 1X2',
          pick: b.pick_name ?? b.pick,
          odds: Number(Number(b.odds ?? 1).toFixed(2)),
          win_prob_pct: Number((Number(b.win_prob ?? 0) * 100).toFixed(1)),
        }));
        const tOdds = Number(
          (Number(distinct3[0].odds) * Number(distinct3[1].odds) * Number(distinct3[2].odds)).toFixed(2),
        );
        const tProb =
          Number(distinct3[0].win_prob) * Number(distinct3[1].win_prob) * Number(distinct3[2].win_prob);
        const trebleTicket = {
          combo_type: 'BANKER_PROFIT_TREBLE',
          combo_label: '3-Leg Banker Profit Treble',
          legs: tLegs,
          combined_odds: tOdds,
          combined_prob: tProb,
          min_fair_odds: Number((1 / Math.max(tProb, 0.05)).toFixed(2)),
          ev_pct: Number(((tProb * tOdds - 1) * 100).toFixed(2)),
        };
        if (ticketsRaw.length >= maxCombos) {
          ticketsRaw[ticketsRaw.length - 1] = trebleTicket;
        } else {
          ticketsRaw.push(trebleTicket);
        }
      }

      const finalTickets = ticketsRaw.slice(0, maxCombos);
      const qKellyFracs: number[] = [];
      const kellyWeights: number[] = [];

      for (const t of finalTickets) {
        const bNet = Math.max(0.05, t.combined_odds - 1);
        const fullKelly = Math.max(0, (t.combined_prob * t.combined_odds - 1) / bNet);
        const qKelly = 0.25 * fullKelly;
        qKellyFracs.push(qKelly);
        kellyWeights.push(qKelly + 0.015 * t.combined_prob);
      }

      const weightSum = kellyWeights.reduce((acc, w) => acc + w, 0) || 1;
      let allocatedSoFar = 0;

      const combos = finalTickets.map((t, idx) => {
        const qK = qKellyFracs[idx] ?? 0;
        let stakeEur: number;
        if (idx === finalTickets.length - 1) {
          stakeEur = Number(Math.max(0, budgetEur - allocatedSoFar).toFixed(2));
        } else {
          stakeEur = Number((budgetEur * ((kellyWeights[idx] ?? 0) / weightSum)).toFixed(2));
          allocatedSoFar += stakeEur;
        }

        const outObj: Record<string, any> = {
          ticket_rank: idx + 1,
          combo_type: t.combo_type,
          combo_label: t.combo_label,
          leg_count: t.legs.length,
          title: t.legs.map((lg) => lg.pick || lg.match).join(' + '),
          legs: t.legs,
          leg_1: t.legs[0],
          leg_2: t.legs[1],
        };
        if (t.legs[2]) outObj.leg_3 = t.legs[2];
        Object.assign(outObj, {
          combined_odds: t.combined_odds,
          min_fair_odds: t.min_fair_odds,
          combined_win_prob_pct: Number((t.combined_prob * 100).toFixed(1)),
          ev_pct: t.ev_pct,
          quarter_kelly_pct: Number((qK * 100).toFixed(2)),
          standalone_quarter_kelly_stake_eur: Number((budgetEur * qK).toFixed(2)),
          recommended_stake_eur: stakeEur,
          projected_return_eur: Number((stakeEur * t.combined_odds).toFixed(2)),
          projected_net_profit_eur: Number((stakeEur * (t.combined_odds - 1)).toFixed(2)),
        });
        return outObj;
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                budget_eur: budgetEur,
                allocation_method: 'quarter_kelly_weighted',
                combo_count: combos.length,
                combos,
              },
              null,
              2,
            ),
          },
        ],
        isError: false,
      };
    }

    if (toolName === 'analyze_matchup') {
      const query = String(args.query ?? '').trim();
      if (!query || (!query.toLowerCase().includes(' vs ') && !query.includes('-') && query.split(/\s+/).length < 2)) {
        throw new BetScoutMcpError(
          `Invalid matchup query "${query}".`,
          'Provide two team or player names separated by "vs", for example `{"query": "Daniil Medvedev vs Cameron Norrie"}` or `{"query": "AS Roma vs Cagliari"}`.',
        );
      }
      const analysis = await client.analyzeMatchup(query);
      if (!analysis?.ok) {
        throw new BetScoutMcpError(
          analysis?.error || `Could not analyze matchup "${query}".`,
          'Verify the spelling of both team/player names or use `search_daily_fixtures` to check exact competitor names.',
        );
      }

      const compact = {
        matchup: `${analysis.home} vs ${analysis.away}`,
        home: analysis.home,
        away: analysis.away,
        sport: analysis.sport,
        league: analysis.league,
        favorite: analysis.fav_name,
        model_win_prob_pct: analysis.fav_prob_pct,
        market_win_prob_pct: analysis.fav_mkt_prob_pct,
        edge_pp: analysis.fav_edge_pp,
        ev_pct: analysis.fav_ev_pct,
        fair_odds: analysis.fav_fair_odds,
        bookmaker_odds: {
          home: analysis.odds_home,
          away: analysis.odds_away,
          favorite: analysis.fav_book_odds,
        },
        elo_diff_home: analysis.elo_diff_home,
        h2h_summary: analysis.h2h_summary,
        h2h_recent: Array.isArray(analysis.h2h) ? analysis.h2h.slice(0, 6) : [],
        form_home_last6: Array.isArray(analysis.form_home) ? analysis.form_home.slice(0, 6) : [],
        form_away_last6: Array.isArray(analysis.form_away) ? analysis.form_away.slice(0, 6) : [],
        rest_hours: {
          home: analysis.p1_rest_hours,
          away: analysis.p2_rest_hours,
        },
        market_recommendations: analysis.market_recommendations,
        warnings: analysis.warnings ?? [],
        verdict: analysis.verdict,
        verdict_level: analysis.verdict_level,
        sportradar_match_id: analysis.live_intel?.sr_match_id ?? null,
      };

      return {
        content: [{ type: 'text', text: JSON.stringify(compact, null, 2) }],
        isError: false,
      };
    }

    if (toolName === 'calculate_exact_score_dutching') {
      const query = String(args.query ?? '').trim();
      const stakeEur = Number(args.stake_eur ?? 25);
      if (!query) {
        throw new BetScoutMcpError(
          'Missing required parameter `query`.',
          'Pass a matchup string such as `{"query": "AS Roma vs Cagliari", "stake_eur": 25}`.',
        );
      }
      if (!Number.isFinite(stakeEur) || stakeEur <= 0) {
        throw new BetScoutMcpError(
          `Invalid \`stake_eur\` (${args.stake_eur}).`,
          'Pass a positive stake amount in EUR (e.g. `25`).',
        );
      }

      const analysis = await client.analyzeMatchup(query);
      if (!analysis?.ok) {
        throw new BetScoutMcpError(
          analysis?.error || `Could not resolve matchup "${query}".`,
          'Pass two team or player names separated by "vs" (e.g. `"AS Roma vs Cagliari"`).',
        );
      }

      const pk = analysis.pick_detail ?? {};
      const esc = pk.exact_score_prediction ?? {};
      const bookCs = analysis.live_intel?.primary_markets?.correct_score_odds ?? {};
      const legsRaw: Array<{ score: string; prob: number; odds: number }> = [];

      if (Array.isArray(esc.top_3_breakdown) && esc.top_3_breakdown.length > 0) {
        for (const item of esc.top_3_breakdown.slice(0, 3)) {
          const sc = String(item.score);
          const prob = Number(item.prob ?? 0.12);
          const odds = Number(bookCs[sc] ?? item.fair_odds ?? Number((1 / Math.max(prob, 0.04)).toFixed(2)));
          legsRaw.push({ score: sc, prob, odds });
        }
      } else if (analysis.sport === 'tennis') {
        const wProb = Number(analysis.fav_prob_pct ?? 65) / 100;
        const favIsHome = analysis.fav_name === analysis.home;
        const straightScore = favIsHome ? '2:0' : '0:2';
        const deciderScore = favIsHome ? '2:1' : '1:2';
        const pStraight = Number((wProb * 0.63).toFixed(4));
        const pDecider = Number((wProb * 0.37).toFixed(4));
        legsRaw.push(
          {
            score: `Sets ${straightScore}`,
            prob: pStraight,
            odds: Number((1 / Math.max(pStraight, 0.08)).toFixed(2)),
          },
          {
            score: `Sets ${deciderScore}`,
            prob: pDecider,
            odds: Number((1 / Math.max(pDecider, 0.08)).toFixed(2)),
          },
        );
      } else {
        const favIsHome = analysis.fav_name === analysis.home;
        const defaultScores = favIsHome ? ['1:0', '2:0', '2:1'] : ['0:1', '0:2', '1:2'];
        const probs = [0.16, 0.14, 0.11];
        defaultScores.forEach((sc, i) => {
          const pr = probs[i]!;
          legsRaw.push({
            score: sc,
            prob: pr,
            odds: Number(bookCs[sc] ?? (1 / pr).toFixed(2)),
          });
        });
      }

      const invSum = legsRaw.reduce((acc, x) => acc + 1 / Math.max(x.odds, 1.01), 0);
      const effOdds = invSum > 0 ? 1 / invSum : 1;
      const combProb = legsRaw.reduce((acc, x) => acc + x.prob, 0);
      const legs = legsRaw.map((x) => {
        const st = stakeEur * ((1 / x.odds) / invSum);
        return {
          score: x.score,
          probability_pct: Number((x.prob * 100).toFixed(1)),
          decimal_odds: Number(x.odds.toFixed(2)),
          stake_eur: Number(st.toFixed(2)),
          equal_payout_return_eur: Number((st * x.odds).toFixed(2)),
        };
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                matchup: `${analysis.home} vs ${analysis.away}`,
                sport: analysis.sport,
                total_stake_eur: Number(stakeEur.toFixed(2)),
                combined_hit_prob_pct: Number((combProb * 100).toFixed(1)),
                effective_cluster_odds: Number(effOdds.toFixed(2)),
                equal_payout_return_eur: Number((stakeEur * effOdds).toFixed(2)),
                net_profit_if_hit_eur: Number((stakeEur * (effOdds - 1)).toFixed(2)),
                legs,
              },
              null,
              2,
            ),
          },
        ],
        isError: false,
      };
    }

    if (toolName === 'get_match_center_dossier') {
      let resolvedMatchId =
        args.match_id !== undefined && args.match_id !== null && Number.isFinite(Number(args.match_id))
          ? Number(args.match_id)
          : null;
      const home = String(args.home ?? '').trim();
      const away = String(args.away ?? '').trim();
      const sport = String(args.sport ?? 'soccer').trim().toLowerCase();

      let localDetail: any = null;
      if (home && away) {
        try {
          localDetail = await client.getMatchupDetail(home, away, sport);
          if (!resolvedMatchId && localDetail?.live_intel?.sr_match_id) {
            resolvedMatchId = Number(localDetail.live_intel.sr_match_id);
          }
        } catch {
          // Proceed with SDK lookup if match_id is known
        }
      }

      if (!resolvedMatchId) {
        throw new BetScoutMcpError(
          'Could not resolve a numeric `match_id` for the requested match.',
          'Provide a valid numeric `match_id` (discoverable via `search_daily_fixtures`) or pass both `home` and `away` team/player names for an active fixture.',
        );
      }

      const dossier = await client.sdk.getMatchCenterDossier(resolvedMatchId);
      const mi = dossier.match_info ?? ({} as any);
      const mObj = dossier.timeline_delta?.match ?? mi.match ?? ({} as any);
      const hTeam = mi.match?.teams?.home ?? mObj.teams?.home ?? ({} as any);
      const aTeam = mi.match?.teams?.away ?? mObj.teams?.away ?? ({} as any);

      if (!hTeam?.name && !aTeam?.name) {
        throw new BetScoutMcpError(
          `No match record found for match_id=${resolvedMatchId}.`,
          'Call `search_daily_fixtures` first to obtain valid numeric `match_id` values for the desired date and sport.',
        );
      }

      const dAny = dossier as any;
      const summary = {
        match_id: resolvedMatchId,
        sport_id: dossier.sport_id,
        sport_name: dossier.sport_name,
        tournament: mi.season?.name ?? mi.tournament?.name ?? null,
        surface: mi.tournament?.ground?.name ?? null,
        status: mObj.status?.name ?? null,
        home: {
          uid: hTeam.uid ?? hTeam._id ?? null,
          name: hTeam.name,
          logo_url: dAny.home_headshot_url ?? null,
          flag_url: dAny.home_flag_url ?? null,
        },
        away: {
          uid: aTeam.uid ?? aTeam._id ?? null,
          name: aTeam.name,
          logo_url: dAny.away_headshot_url ?? null,
          flag_url: dAny.away_flag_url ?? null,
        },
        score: mObj.result ?? null,
        periods: mObj.periods ?? null,
        merged_markets: dossier.merged_markets,
        form_wdl: dossier.form_wdl,
        h2h_edge: dossier.h2h_edge,
        missing_players: {
          home: (dossier.home_missing_players ?? []).slice(0, 10),
          away: (dossier.away_missing_players ?? []).slice(0, 10),
        },
        local_db_pick: localDetail?.pick_detail ?? null,
        cache_telemetry: client.getCacheTelemetry(),
      };

      return {
        content: [{ type: 'text', text: JSON.stringify(summary, null, 2) }],
        isError: false,
      };
    }

    if (toolName === 'search_daily_fixtures') {
      const sport = String(args.sport ?? 'tennis').trim().toLowerCase();
      const dateYmd = args.date_ymd ? String(args.date_ymd).trim() : undefined;
      const query = String(args.query ?? '').trim().toLowerCase();
      const limit = Number(args.limit ?? 15);
      const cursor = args.cursor as string | undefined;

      let fixtures = await client.sdk.getDailyMatchIndex(sport, dateYmd);
      if (query) {
        fixtures = fixtures.filter(
          (f) =>
            String(f.home ?? '').toLowerCase().includes(query) ||
            String(f.away ?? '').toLowerCase().includes(query) ||
            String(f.tournament ?? '').toLowerCase().includes(query),
        );
      }

      const paged = paginateItems(fixtures, { cursor, limit });
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                sport,
                date_ymd: dateYmd ?? 'today',
                query: query || null,
                fixtures: paged.items,
                pagination: {
                  returned_count: paged.returned_count,
                  total_available: paged.total_available,
                  has_more: paged.has_more,
                  next_cursor: paged.next_cursor,
                  hint: paged.pagination_hint,
                },
              },
              null,
              2,
            ),
          },
        ],
        isError: false,
      };
    }

    if (toolName === 'get_paper_ledger_roi') {
      const statusFilter = String(args.status ?? 'settled').trim().toLowerCase();
      const sportFilter = String(args.sport ?? 'all').trim().toLowerCase();
      const limit = Number(args.limit ?? 15);
      const cursor = args.cursor as string | undefined;

      const snap = await client.getSnapshot(1.05, 'all');
      const ledger = snap.paper_ledger ?? {};
      let bets: any[] = Array.isArray(ledger.bets) ? ledger.bets : [];

      if (statusFilter !== 'all') {
        bets = bets.filter((b) => String(b.status ?? '').toLowerCase() === statusFilter);
      }
      if (sportFilter !== 'all') {
        bets = bets.filter(
          (b) =>
            String(b.sport_cat ?? '').toLowerCase().includes(sportFilter) ||
            String(b.league ?? '').toLowerCase().includes(sportFilter),
        );
      }

      const rows = bets.map((b) => ({
        event_id: b.event_id,
        kickoff: b.kickoff,
        league: b.league_label ?? b.league,
        match: `${b.home} vs ${b.away}`,
        pick: b.side === 'H' ? b.home : b.away,
        side: b.side,
        tier: b.tier,
        odds: b.logged_best_odds,
        status: b.status,
        final_score: b.score_str ?? b.settled_score,
        pnl_u: b.pnl_best,
      }));

      const paged = paginateItems(rows, { cursor, limit });
      const settledCount = Number(ledger.settled_count ?? 0);
      const settledWins = Number(ledger.settled_wins ?? 0);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                summary: {
                  settled_count: settledCount,
                  wins: settledWins,
                  losses: Number(ledger.settled_losses ?? 0),
                  win_rate_pct: settledCount > 0 ? Number(((settledWins / settledCount) * 100).toFixed(1)) : 0,
                  net_profit_u: Number(Number(ledger.settled_profit_u ?? 0).toFixed(2)),
                  roi_pct: Number((Number(ledger.settled_roi_best ?? 0) * 100).toFixed(1)),
                  mean_clv_pct: Number((Number(ledger.mean_clv_pct ?? 0) * 100).toFixed(2)),
                  exact_score_hit_rate_pct: ledger.exact_score_hit_rate_pct,
                  live_count: ledger.live_count,
                  pending_count: ledger.pending_count,
                },
                by_sport: ledger.by_sport ?? [],
                rows: paged.items,
                pagination: {
                  returned_count: paged.returned_count,
                  total_available: paged.total_available,
                  has_more: paged.has_more,
                  next_cursor: paged.next_cursor,
                  hint: paged.pagination_hint,
                },
              },
              null,
              2,
            ),
          },
        ],
        isError: false,
      };
    }

    throw new BetScoutMcpError(
      `Unknown tool "${toolName}".`,
      `Use one of the 7 registered BetScout tools: ${MCP_TOOLS_CATALOG.map((t) => t.name).join(', ')}.`,
    );
  } catch (err) {
    return formatMcpToolError(toolName, err);
  }
}
