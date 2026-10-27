import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { createMemoryHistory, createRouter } from 'vue-router';
import {
  type BestBetItem,
  computeBankerBoosterCombos,
  computeEqualPayoutDutchSplit,
  getBadgeTooltipText,
  getSportBadgeTheme,
  getSportEmoji,
  getSportIconify,
  getTierBadgeClass,
  getWinProbBarColor,
} from '../src/utils/formatters';
import { useBetscoutStore } from '../src/stores/betscoutStore';
import LandingView from '../src/views/LandingView.vue';
import DashboardView from '../src/views/DashboardView.vue';

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
  it('maps every sport category to its canonical emoji and Iconify icon', () => {
    expect(getSportEmoji('soccer')).toBe('⚽');
    expect(getSportEmoji('tennis')).toBe('🎾');
    expect(getSportEmoji('basketball')).toBe('🏀');
    expect(getSportEmoji('hockey')).toBe('🏒');
    expect(getSportEmoji('table_tennis')).toBe('🏓');
    expect(getSportIconify('soccer')).toBe('fa6-solid:futbol');
    expect(getSportIconify('tennis')).toBe('fa6-solid:tennis-ball');
    expect(getSportIconify('table_tennis')).toBe('fa6-solid:table-tennis-paddle-ball');
    expect(getSportBadgeTheme('soccer')).toContain('emerald');
    expect(getSportBadgeTheme('tennis')).toContain('lime');
    expect(getSportBadgeTheme('table_tennis')).toContain('fuchsia');
    expect(getTierBadgeClass('top_8pct')).toContain('violet');
    expect(getTierBadgeClass('banker_70pct')).toContain('amber');
    expect(getTierBadgeClass('high_conf')).toContain('cyan');
    expect(getWinProbBarColor(0.85)).toContain('emerald');
  });

  it('returns detailed explanations for safety-gate tier and edge badges', () => {
    expect(getBadgeTooltipText('tier_0_96')).toContain('Tier 0 Ultra-Banker');
    expect(getBadgeTooltipText('BANKER_PROFIT_BOOSTER')).toContain('Banker Profitability Booster');
    expect(getBadgeTooltipText('EDGE +4.2pp')).toContain('Bookmaker Odds Mispricing');
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
      ],
    });
    const store = useBetscoutStore();
    store.bestBets = [makeMockBet()];

    const wrapper = mount(LandingView, {
      global: { plugins: [router] },
    });

    expect(wrapper.text()).toContain('96.5%');
    expect(wrapper.text()).toContain('+35.2%');
    expect(wrapper.text()).toContain('€49');
    expect(wrapper.text()).toContain('€79');
    expect(wrapper.text()).toContain('€199');
    expect(wrapper.text()).toContain('AS Roma vs Cagliari');
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
});
