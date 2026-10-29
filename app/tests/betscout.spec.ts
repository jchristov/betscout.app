import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { createMemoryHistory, createRouter } from 'vue-router';
import {
  type BestBetItem,
  SPORT_FA6_ICONIFY_NAMES,
  computeBankerBoosterCombos,
  computeEqualPayoutDutchSplit,
  formatHeaderTimestamp,
  formatLeagueBadgeLabel,
  getBadgeTooltipText,
  getCompetitionFlagIconify,
  getFormOutcomeSquareClass,
  getH2HScoreColorClass,
  getH2HWinnerSide,
  getSportBadgeTheme,
  getSportEmoji,
  getSportIconify,
  getTierBadgeClass,
  getWinProbBarColor,
  parseScorePredictionSegments,
  splitScoreAndInterim,
} from '../src/utils/formatters';
import { useBetscoutStore } from '../src/stores/betscoutStore';
import LandingView from '../src/views/LandingView.vue';
import DashboardView from '../src/views/DashboardView.vue';
import DocsView from '../src/views/DocsView.vue';
import MatchCenterView from '../src/views/MatchCenterView.vue';

function makeMockBet(overrides: Partial<BestBetItem> = {}): BestBetItem {
  return {
    sport_cat: 'soccer',
    sport_icon: '⚽',
    sport_league: 'ita.1',
    competition: 'Serie A',
    date: '2026-04-06 18:45 UTC',
    date_local: '2026-04-06 20:45 CEST',
    day_local: '2026-04-06',
    match: 'AS Roma vs Cagliari',
    home: 'AS Roma',
    away: 'Cagliari',
    pick: 'H',
    pick_name: 'AS Roma',
    tier: 'tier_1_93',
    win_prob: 0.785,
    min_fair_odds: 1.27,
    odds: 1.33,
    odds_display: '1.33',
    clv_pct: 2.1,
    exact_score_pick: '2:0 (16.4%)',
    score_cluster_items: [
      { label: '2:0', prob: 0.164, fair_odds: 6.1, book_odds: 6.5 },
      { label: '1:0', prob: 0.148, fair_odds: 6.75, book_odds: 7.0 },
      { label: '2:1', prob: 0.112, fair_odds: 8.9, book_odds: 8.5 },
    ],
    ...overrides,
  };
}

describe('BetScout Quantitative Formatters & Engines', () => {
  it('maps every sport category to its canonical emoji, multi-color vector icon, and preserved FA6 icon', () => {
    expect(getSportEmoji('soccer')).toBe('⚽');
    expect(getSportEmoji('tennis')).toBe('🎾');
    expect(getSportEmoji('basketball')).toBe('🏀');
    expect(getSportEmoji('hockey')).toBe('🏒');
    expect(getSportEmoji('table_tennis')).toBe('🏓');
    expect(getSportIconify('soccer')).toBe('betscout-sport:soccer');
    expect(getSportIconify('tennis')).toBe('betscout-sport:tennis');
    expect(getSportIconify('table_tennis')).toBe('betscout-sport:table_tennis');
    expect(SPORT_FA6_ICONIFY_NAMES.soccer).toBe('fa6-solid:futbol');
    expect(SPORT_FA6_ICONIFY_NAMES.tennis).toBe('fa6-solid:tennis-ball');
    expect(SPORT_FA6_ICONIFY_NAMES.table_tennis).toBe('fa6-solid:table-tennis-paddle-ball');
    expect(getSportBadgeTheme('soccer')).toContain('emerald');
    expect(getSportBadgeTheme('tennis')).toContain('lime');
    expect(getSportBadgeTheme('table_tennis')).toContain('fuchsia');
    expect(getCompetitionFlagIconify('Serie A', 'ita.1')).toBe('flag:it');
    expect(getCompetitionFlagIconify('Premier League', 'eng.1')).toBe('flag:gb-eng');
    expect(getCompetitionFlagIconify('Handball · Sweden · Handbollsligan')).toBe('flag:se');
    expect(getCompetitionFlagIconify('UEFA Champions League', 'uefa.champions')).toBe('flag:eu');
    expect(getCompetitionFlagIconify('NBA', 'nba')).toBe('flag:us');
    expect(formatLeagueBadgeLabel('HANDBALL', 'handball', 'Savehof', 'Amo')).toBe('Handball · Handbollsligan');
    expect(formatLeagueBadgeLabel('HANDBALL', 'handball', 'Porto', 'Veszprem')).toBe('EHF Champions League');
    expect(formatLeagueBadgeLabel('TABLE_TENNIS', 'table_tennis', 'Zelezik, Jacek', 'Pyrek, Dawid')).toBe(
      'Table Tennis · TT Elite Series',
    );
    expect(formatLeagueBadgeLabel('TABLE_TENNIS', 'table_tennis', 'Stach, Vojtech', 'Tkachenko, Andrii')).toBe(
      'Table Tennis · Czech Liga Pro',
    );
    expect(getCompetitionFlagIconify(formatLeagueBadgeLabel('HANDBALL', 'handball', 'Savehof', 'Amo'), 'handball Savehof Amo')).toBe('flag:se');
    expect(getCompetitionFlagIconify(formatLeagueBadgeLabel('TABLE_TENNIS', 'table_tennis', 'Zelezik, Jacek', 'Pyrek, Dawid'), 'table_tennis')).toBe('flag:pl');
    expect(getTierBadgeClass('top_8pct')).toContain('violet');
    expect(getTierBadgeClass('banker_70pct')).toContain('amber');
    expect(getTierBadgeClass('high_conf')).toContain('cyan');
    expect(getWinProbBarColor(0.85)).toContain('emerald');
  });

  it('returns detailed explanations for safety-gate tier and edge badges', () => {
    expect(getBadgeTooltipText('tier_0_96')).toContain('Tier 0 Ultra-Banker');
    expect(getBadgeTooltipText('BANKER_PROFIT_BOOSTER')).toContain('Banker Profitability Booster');
    expect(getBadgeTooltipText('EDGE +4.2pp')).toContain('Bookmaker Odds Mispricing');

    const segsHigh = parseScorePredictionSegments('Sets 2:0 (64.7%, Fair 1.55) / 2:1 (21.6%)');
    expect(segsHigh.length).toBe(2);
    expect(segsHigh[0].isOver60).toBe(true);
    expect(segsHigh[1].isOver60).toBe(false);

    const segsLow = parseScorePredictionSegments('0:1 (16.4%) · Cluster 0:1 / 0:2 / 1:2 (38.9%, Fair 2.57)');
    expect(segsLow.length).toBe(2);
    expect(segsLow[0].isOver60).toBe(false);
    expect(segsLow[1].isOver60).toBe(false);

    expect(getFormOutcomeSquareClass('W')).toContain('emerald');
    expect(getFormOutcomeSquareClass('L')).toContain('rose');
    expect(getFormOutcomeSquareClass('D')).toContain('amber');

    expect(splitScoreAndInterim('2-0 (6-2, 6-1)')).toEqual({
      main: '2-0',
      interim: '(6-2, 6-1)',
    });
    expect(splitScoreAndInterim('3-1')).toEqual({
      main: '3-1',
      interim: '',
    });

    expect(getH2HWinnerSide({ outcome: 'H', score: '2-0' })).toBe('H');
    expect(getH2HWinnerSide({ outcome: 'A', score: '1-2' })).toBe('A');
    expect(getH2HWinnerSide({ score: '0-2 (4-6, 2-6)' })).toBe('A');
    expect(getH2HWinnerSide({ score: '1-1' })).toBe('D');

    const romaCtx = {
      home: 'AS Roma',
      away: 'Cagliari',
      pick_detail: { side: 'H', pick: 'AS Roma' },
    };
    expect(
      getH2HScoreColorClass({ home: 'AS Roma', away: 'Cagliari', score: '4-2', outcome: 'H' }, romaCtx),
    ).toBe('text-emerald-300');
    expect(
      getH2HScoreColorClass({ home: 'Cagliari', away: 'AS Roma', score: '1-0', outcome: 'H' }, romaCtx),
    ).toBe('text-rose-400');
    expect(
      getH2HScoreColorClass({ home: 'Cagliari', away: 'AS Roma', score: '0-0', outcome: 'D' }, romaCtx),
    ).toBe('text-amber-300');

    expect(formatHeaderTimestamp('2026-10-29 11:02 CET', 'Europe/Vienna', 'local')).toBe('2026-10-29 11:02 CET');
    expect(formatHeaderTimestamp('2026-10-29T10:02:00Z', 'Europe/Vienna', 'local')).toBe('2026-10-29 11:02 CET');
    expect(formatHeaderTimestamp('2026-10-29T10:02:00Z', 'Europe/Vienna', 'utc')).toBe('2026-10-29 10:02 UTC');
  });

  it('builds 2-Leg and 3-Leg Banker Profitability Booster Combos when >=2 low-odds bankers exist', () => {
    const bets: BestBetItem[] = [
      makeMockBet({
        match: 'AS Roma vs Cagliari',
        pick_name: 'AS Roma',
        sport_league: 'ita.1',
        win_prob: 0.81,
        odds: 1.33,
      }),
      makeMockBet({
        sport_cat: 'tennis',
        sport_icon: '🎾',
        sport_league: 'atp',
        competition: 'ATP Tour',
        match: 'Jannik Sinner vs Alex de Minaur',
        pick_name: 'Jannik Sinner',
        win_prob: 0.86,
        odds: 1.22,
      }),
      makeMockBet({
        sport_cat: 'basketball',
        sport_icon: '🏀',
        sport_league: 'nba',
        competition: 'NBA',
        match: 'Boston Celtics vs Charlotte Hornets',
        pick_name: 'Boston Celtics',
        win_prob: 0.79,
        odds: 1.28,
      }),
    ];

    const boosters = computeBankerBoosterCombos(bets);
    expect(boosters.length).toBeGreaterThanOrEqual(2);
    expect(boosters[0].id).toBe('anchor-2leg');
    expect(boosters[0].combinedOdds).toBeCloseTo(1.22 * 1.33, 2);
    const treble = boosters.find((c) => c.id === 'treble-3leg');
    expect(treble).toBeDefined();
    expect(treble?.legs.length).toBe(3);
  });

  it('computes equal-payout Exact-Score Dutching splits accurately', () => {
    const split = computeEqualPayoutDutchSplit(
      [
        { label: '2:0', prob: 0.16, odds: 6.0 },
        { label: '2:1', prob: 0.12, odds: 9.0 },
      ],
      30,
    );
    expect(split).not.toBeNull();
    expect(split!.totalStake).toBeCloseTo(30, 2);
    // Equal payout means leg[0].payout === leg[1].payout
    expect(split!.legs[0].payout).toBeCloseTo(split!.legs[1].payout, 2);
    expect(split!.effectiveOdds).toBeCloseTo(3.6, 2);
  });
});

describe('BetScout Pinia Store & Reactive Filtering', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('filters active picks by sport, day, minOdds, and search query', () => {
    const store = useBetscoutStore();
    store.bestBets = [
      makeMockBet({
        sport_cat: 'soccer',
        match: 'AS Roma vs Cagliari',
        day_local: '2026-04-06',
        odds: 1.33,
      }),
      makeMockBet({
        sport_cat: 'tennis',
        sport_icon: '🎾',
        match: 'Ben Shelton vs Aleksandar Kovacevic',
        day_local: '2026-04-07',
        odds: 1.26,
      }),
    ];

    expect(store.visibleBestBets.length).toBe(2);
    expect(store.activeSportsBreakdown).toContain('⚽ 1');
    expect(store.activeSportsBreakdown).toContain('🎾 1');

    // Filter by sport
    store.sportFilter = 'tennis';
    expect(store.visibleBestBets.length).toBe(1);
    expect(store.visibleBestBets[0].match).toContain('Ben Shelton');

    // Reset sport, filter by minOdds
    store.sportFilter = 'all';
    store.minOdds = 1.30;
    expect(store.visibleBestBets.length).toBe(1);
    expect(store.visibleBestBets[0].match).toContain('AS Roma');

    // Custom selection toggle
    store.toggleCustomMatch('AS Roma vs Cagliari');
    expect(store.customSelectedMatches.has('AS Roma vs Cagliari')).toBe(true);
    store.clearCustomSelection();
    expect(store.customSelectedMatches.size).toBe(0);
  });
});

describe('Vue 3 Views (LandingView & DashboardView)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ ok: true }),
      }),
    );
  });

  it('renders LandingView with 3 pricing cards, verified KPIs, and interactive FAQ', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: LandingView },
        { path: '/app', component: DashboardView },
        { path: '/docs', component: DocsView },
      ],
    });
    const store = useBetscoutStore();
    store.bestBets = [makeMockBet()];

    const wrapper = mount(LandingView, {
      global: { plugins: [router] },
    });

    expect(wrapper.text()).toContain('96.5%');
    expect(wrapper.text()).toContain('+35.2%');
    expect(wrapper.find('footer').text()).toMatch(/v0\.5\.0 \([a-f0-9]+|dev\)/);
    expect(wrapper.text()).toContain('€39');
    expect(wrapper.text()).toContain('€79');
    expect(wrapper.text()).toContain('€199');
    expect(wrapper.text()).toContain('Bonus AI Agent MCP Server');
    expect(wrapper.text()).toContain('AS Roma vs Cagliari');
    expect(wrapper.text()).toContain('Pick');
    expect(wrapper.text()).toContain('Odds');
    expect(wrapper.text()).toContain('Result / PNL');
    expect(wrapper.text()).not.toContain('Model Pick');
    expect(wrapper.text()).not.toContain('Logged Odds');
    expect(wrapper.text()).toContain('API Documentation');
    expect(wrapper.text()).not.toContain('Interactive API Docs');
    expect(wrapper.text()).not.toContain('betscout.app');
    expect(wrapper.text()).not.toContain('/api/');
    expect(wrapper.text()).not.toContain('https://');
    expect(wrapper.html().toLowerCase()).not.toMatch(/espn|sportradar|sofascore/);
  });

  it('renders DashboardView with 4 workspace tabs, sortable table, and custom slip dock', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: LandingView },
        { path: '/app', component: DashboardView },
        { path: '/docs', component: DocsView },
      ],
    });
    const store = useBetscoutStore();
    store.bestBets = [
      makeMockBet({ match: 'AS Roma vs Cagliari', odds: 1.33, win_prob: 0.78 }),
      makeMockBet({
        sport_cat: 'tennis',
        match: 'Jannik Sinner vs Alex de Minaur',
        pick_name: 'Jannik Sinner',
        odds: 1.24,
        win_prob: 0.85,
      }),
    ];

    const wrapper = mount(DashboardView, {
      global: { plugins: [router] },
    });

    expect(wrapper.text()).toContain('Settled Win Rate');
    expect(wrapper.text()).toContain('Realized Profit / ROI');
    expect(wrapper.text()).toContain('AS Roma vs Cagliari');
    expect(wrapper.find('.live-dot-idle').exists()).toBe(true);
    expect(wrapper.find('.live-blink-dot').exists()).toBe(false);
    expect(wrapper.text()).toContain('High-Probability Banker Profitability Booster Combos');
    expect(wrapper.text()).not.toContain('Interactive API Docs');
    expect(wrapper.text()).not.toContain('betscout.app');
    expect(wrapper.text()).not.toContain('/api/');
    expect(wrapper.text()).not.toContain('https://');

    expect(wrapper.html().toLowerCase()).not.toMatch(/espn|sportradar|sofascore/);

    // Select a match to trigger floating custom slip dock
    store.toggleCustomMatch('AS Roma vs Cagliari');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('1 Selected');
  });

  it('renders DocsView (/docs) with all 5 documentation sections, 7 MCP tools, 4 prompts, and 4 resources', () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: LandingView },
        { path: '/app', component: DashboardView },
        { path: '/docs', component: DocsView },
      ],
    });
    const wrapper = mount(DocsView, {
      global: { plugins: [router] },
    });

    expect(wrapper.text()).toContain('BetScout Platform Manual');
    expect(wrapper.text()).toContain('get_daily_banker_picks');
    expect(wrapper.text()).toContain('get_banker_profit_boosters');
    expect(wrapper.text()).toContain('analyze_matchup');
    expect(wrapper.text()).toContain('calculate_exact_score_dutching');
    expect(wrapper.text()).toContain('get_match_center_dossier');
    expect(wrapper.text()).toContain('search_daily_fixtures');
    expect(wrapper.text()).toContain('get_paper_ledger_roi');
    expect(wrapper.text()).toContain('betscout://slate/today');
    expect(wrapper.text()).toContain('parlay-builder');
  });

  it('renders MatchCenterView (/match/:id) with 2-way 100% win probability bar (0% draw for Tennis)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ok: true,
          match_id: 75837638,
          sport_id: 5,
          sport_name: 'Tennis',
          match_info: {
            season: { name: 'ATP Vienna, Austria' },
            tournament: { ground: { name: 'Hardcourt indoor' } },
            match: {
              _id: 75837638,
              status: { name: 'Not started' },
              teams: {
                home: { name: 'Paul, Tommy', abbr: 'PAU' },
                away: { name: 'Darderi, Luciano', abbr: 'DAR' },
              },
            },
          },
          win_prob_bar: {
            home_pct: 76.9,
            draw_pct: 0.0,
            away_pct: 23.1,
            odds_home: 1.2,
            odds_draw: null,
            odds_away: 4.0,
          },
          h2h_edge: {
            total_meetings: 3,
            home_wins: 2,
            draws: 0,
            away_wins: 1,
            home_win_pct: 67,
            draw_pct: 0,
            away_win_pct: 33,
          },
        }),
      }),
    );

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: LandingView },
        { path: '/app', component: DashboardView },
        { path: '/docs', component: DocsView },
        { path: '/match/:id', component: MatchCenterView },
      ],
    });
    await router.push('/match/75837638');
    await router.isReady();

    const wrapper = mount(MatchCenterView, {
      global: { plugins: [router] },
    });
    await new Promise((r) => setTimeout(r, 10));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Match Center #75837638');
    expect(wrapper.text()).toContain('Paul, Tommy — 76.9%');
    expect(wrapper.text()).toContain('Darderi, Luciano — 23.1%');
    expect(wrapper.text()).not.toContain('Draw —');
    expect(wrapper.text()).toContain('2-Way (Moneyline)');
  });
});
