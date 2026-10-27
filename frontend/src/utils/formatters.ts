export const SPORT_EMOJIS: Record<string, string> = {
  soccer: '⚽',
  tennis: '🎾',
  basketball: '🏀',
  volleyball: '🏐',
  hockey: '🏒',
  football: '🏈',
  baseball: '⚾',
  handball: '🤾',
  darts: '🎯',
  table_tennis: '🏓',
};

export const SPORT_LABELS: Record<string, string> = {
  all: '🌐 All Sports',
  soccer: '⚽ Football',
  tennis: '🎾 Tennis',
  basketball: '🏀 Basketball',
  volleyball: '🏐 Volleyball',
  hockey: '🏒 Hockey',
  football: '🏈 NFL',
  baseball: '⚾ Baseball',
  handball: '🤾 Handball',
  darts: '🎯 Darts',
  table_tennis: '🏓 Table Tennis',
};

export const BADGE_TOOLTIPS: Record<string, string> = {
  tier_0_96:
    'Tier 0 Ultra-Banker (≥96% Calibration Confidence): Highest-conviction quantitative tier passing all sport-specific safety gates.',
  tier_1_93:
    'Tier 1 High-Conviction Edge (≥93% Calibration Confidence): Strong multi-factor quantitative alignment with positive EV.',
  tier_2_88:
    'Tier 2 Calibrated Edge (≥88% Calibration Confidence): Verified positive-EV edge passing pre-match safety gates.',
  banker_profit_booster:
    'Banker Profitability Booster: Combines 2 or 3 high-win-probability (≥72%), lower-odds (1.10–1.48) bankers into a higher-yielding 1.35x–2.15x multiplier ticket.',
  banker_70pct:
    'banker_70pct — High-Conviction Tennis / Euro-Sport Banker (≥70% Model Win Prob): Passes surface-specific Elo, 6-month Game-Win%, rest/turnaround, and closing-line steam gates.',
  top_8pct:
    'top_8pct — Elite Top 8% Football Quantitative Edge: Ranks in the top 8% of 7-factor composite scores across Big-5 & European leagues (>81% out-of-sample win rate, +18.9% ROI).',
  top_10pct:
    'top_10pct — Top 10% Football Quantitative Edge: High-conviction pick combining Market Prob, Low Vig, Shots-on-Target dominance, Discipline, H2H, Rebound Momentum & Low Draw rate.',
  top_15pct:
    'top_15pct — Top 15% Quantitative Edge: Strong multi-factor edge in Football or US Major Leagues (NBA/NFL/NHL) where Elo, box-score efficiency & market probability align.',
  top_25pct:
    'top_25pct — Top 25% Quantitative Edge: Upper-quartile model edge passing all sport-specific safety and positive-EV gates.',
  uefa_edge:
    'uefa_edge — UEFA Knockout / League-Phase Edge: Specialized European club tournament signal requiring positive Shots-on-Target dominance and rebound momentum.',
  high_conf:
    'high_conf — High-Confidence Multi-Sport Pick (≥68% Win Prob): Backed by Elo, rolling box-score efficiency (FG% / YPP / Save%), and session form.',
  solid:
    'solid — Solid Positive-EV Edge (≥58% Win Prob): Confirmed by goalie Save% & shot volume (NHL), yards-per-play (NFL), or shooting & possession security (NBA).',
  tracked_live:
    'tracked_live — User-Tracked Live Match: Ad-hoc live or upcoming match added manually via the Live Tracker input.',
};

export const FACTOR_TOOLTIPS: Record<string, string> = {
  p_mkt: 'p_mkt — Vig-Free Market Implied Probability z-score: Baseline bookmaker consensus strength stripped of overround.',
  vig_neg: 'vig_neg — Low Bookmaker Vig / Tight Market Spread: Higher values indicate sharper, lower-margin bookmaker pricing.',
  sot_d: 'sot_d — Rolling Shots-on-Target (SoT) Dominance Differential: Measures true on-target attacking creation vs. suppression.',
  discipline: 'discipline — Foul & Card Discipline Edge: Positive when the backed team commits fewer fouls/cards than the opponent.',
  h2h_adv: 'h2h_adv — Head-to-Head (H2H) Historical Dominance: Goal and win margin across prior meetings between these two clubs.',
  dom_rebound: 'dom_rebound — Dominance Rebound Signal: Positive when the team dominated shots-on-target in its previous match despite dropping points.',
  recent_draws: 'recent_draws — Anti-Stalemate / Low-Draw Propensity: Positive when both teams rarely settle for low-event draws.',
};

export const CLV_TOOLTIP =
  'Closing Line Value (CLV): Percentage edge between the bookmaker odds when BetScout logged the pick vs. the latest/closing market price (Logged Odds ÷ Close Odds − 1). Positive CLV proves you beat the closing market line.';

export function getSportEmoji(catOrLeague?: string | null): string {
  const low = String(catOrLeague || '').toLowerCase().trim();
  if (SPORT_EMOJIS[low]) return SPORT_EMOJIS[low];
  if (low.includes('table tennis') || low.includes('table_tennis')) return '🏓';
  if (low.includes('handball')) return '🤾';
  if (low.includes('darts')) return '🎯';
  if (low.includes('tennis') || low.includes('atp') || low.includes('wta')) return '🎾';
  if (low.includes('volleyball')) return '🏐';
  if (low.includes('basketball') || low.includes('nba') || low.includes('wnba') || low.includes('ncaa') || low.includes('nbl')) return '🏀';
  if (low.includes('hockey') || low.includes('nhl')) return '🏒';
  if (low.includes('nfl') || low.includes('american football')) return '🏈';
  if (low.includes('baseball') || low.includes('mlb')) return '⚾';
  return '⚽';
}

export function getBadgeTooltipText(rawLabel?: string | null): string {
  const s = String(rawLabel || '').trim();
  const low = s.toLowerCase();
  if (BADGE_TOOLTIPS[low]) return BADGE_TOOLTIPS[low];
  if (low.includes('steam'))
    return 'Sharp Closing-Line Steam Move (CLV ≥ +3.0%): Bookmaker odds have shortened significantly since BetScout logged this pick, confirming sharp money on our side.';
  if (low.includes('edge') || low.includes('mispriced'))
    return 'Bookmaker Odds Mispricing: BetScout calibrated win probability exceeds the bookmaker vig-free implied probability by ≥ +2.0pp with ≥ +2.0% Expected Value.';
  if (low.includes('rebound'))
    return 'Live In-Play Dominance Rebound Signal: Backed favorite is level or trailing despite dominating live Shots on Target (SoT) and ball possession.';
  if (low.includes('late goal') || low.includes('1h goal'))
    return 'Live Goal-Timing Window Alert: High historical 15-minute goal scoring/conceding rate combined with active in-play attacking pressure.';
  if (low.includes('banker profit booster'))
    return 'Banker Profit Booster: Combines 2 or 3 high-win-probability (≥72%), lower-odds (1.10–1.48) bankers into a higher-yielding 1.35x–2.15x multiplier ticket.';
  if (low.startsWith('vetoed')) return `${s} — Automatically filtered out by BetScout pre-match safety gates.`;
  if (low === 'paper_bet') return 'PAPER_BET — Verified pre-match model pick actively tracked in the Paper-Bet Ledger.';
  return '';
}

export interface BestBetItem {
  date: string;
  date_local: string;
  announced_at_local?: string;
  time_valid?: boolean;
  sport_cat: string;
  sport_icon?: string;
  sport_league: string;
  competition?: string;
  competition_logo?: string;
  match: string;
  home: string;
  away: string;
  home_logo?: string;
  away_logo?: string;
  home_flag?: string;
  away_flag?: string;
  pick: string;
  pick_name: string;
  pick_logo?: string;
  pick_flag?: string;
  tier: string;
  odds: number;
  odds_display: string;
  win_prob: number;
  min_fair_odds: number;
  p_mkt?: number;
  edge_pp?: number;
  ev_pct?: number;
  clv_pct?: number;
  is_mispriced?: boolean;
  mispricing_drivers?: string;
  exact_score_pick?: string;
  score_cluster_items?: Array<{ label: string; prob: number; fair_odds: number; book_odds?: number }>;
}

export interface BankerBoosterCombo {
  id: string;
  title: string;
  description: string;
  legs: BestBetItem[];
  combinedOdds: number;
  combinedProb: number;
  fairOdds: number;
  netYieldPct: number;
  avgSingleYieldPct: number;
}

export function computeBankerBoosterCombos(items: BestBetItem[]): BankerBoosterCombo[] {
  const unlocked = items.filter((it) => !String(it.match || '').includes('🔒'));
  const bankers = unlocked
    .filter((it) => Number(it.win_prob || 0) >= 0.72 && Number(it.odds || 0) >= 1.1 && Number(it.odds || 0) <= 1.48)
    .sort((a, b) => b.win_prob - a.win_prob || a.odds - b.odds);

  if (bankers.length < 2) return [];

  const avgSingleOdds = bankers.reduce((acc, x) => acc + x.odds, 0) / bankers.length;
  const avgSingleYieldPct = Math.round((avgSingleOdds - 1) * 100);

  const makeCombo = (id: string, title: string, description: string, legs: BestBetItem[]): BankerBoosterCombo => {
    const combinedOdds = Number(legs.reduce((acc, l) => acc * l.odds, 1.0).toFixed(2));
    const combinedProb = Number(legs.reduce((acc, l) => acc * l.win_prob, 1.0).toFixed(4));
    const fairOdds = Number((1.0 / Math.max(0.05, combinedProb)).toFixed(2));
    const netYieldPct = Math.round((combinedOdds - 1.0) * 100);
    return {
      id,
      title,
      description,
      legs,
      combinedOdds,
      combinedProb,
      fairOdds,
      netYieldPct,
      avgSingleYieldPct,
    };
  };

  const out: BankerBoosterCombo[] = [];
  out.push(
    makeCombo(
      'anchor-2leg',
      '⚡ 2-Leg Anchor Banker Double',
      'Pairs the 2 highest-probability bankers into a low-variance multiplier',
      [bankers[0], bankers[1]],
    ),
  );

  if (bankers.length >= 3) {
    const crossPartner = bankers.slice(1).find((x) => x.sport_cat !== bankers[0].sport_cat) || bankers[2];
    const partnerSecond = crossPartner === bankers[1] ? bankers[2] : crossPartner;
    out.push(
      makeCombo(
        'cross-2leg',
        '🌐 2-Leg Cross-League Banker Double',
        'Pairs top anchor banker with independent 2nd / cross-sport banker',
        [bankers[0], partnerSecond],
      ),
    );
    out.push(
      makeCombo(
        'treble-3leg',
        '🚀 3-Leg Banker Profit Treble',
        'Combines the top 3 bankers to multiply low-line singles into a high-yield ticket',
        [bankers[0], bankers[1], bankers[2]],
      ),
    );
  }

  return out;
}

export interface DutchSplitSet {
  legs: Array<{ label: string; prob: number; odds: number; stake: number; payout: number }>;
  totalStake: number;
  totalPayout: number;
  netProfit: number;
  effectiveOdds: number;
  combinedProb: number;
}

export function computeEqualPayoutDutchSplit(
  items: Array<{ label: string; prob: number; odds: number }>,
  totalStake: number,
): DutchSplitSet | null {
  if (!items.length || totalStake <= 0) return null;
  const invSum = items.reduce((acc, it) => acc + 1.0 / Math.max(1.05, it.odds), 0);
  if (invSum <= 0) return null;
  const effectiveOdds = 1.0 / invSum;
  const totalPayout = totalStake * effectiveOdds;
  const netProfit = totalPayout - totalStake;
  const combinedProb = items.reduce((acc, it) => acc + Number(it.prob || 0), 0);
  const legs = items.map((it) => {
    const w = 1.0 / Math.max(1.05, it.odds) / invSum;
    const st = totalStake * w;
    return {
      label: it.label,
      prob: it.prob,
      odds: it.odds,
      stake: Number(st.toFixed(2)),
      payout: Number((st * it.odds).toFixed(2)),
    };
  });
  return {
    legs,
    totalStake: Number(totalStake.toFixed(2)),
    totalPayout: Number(totalPayout.toFixed(2)),
    netProfit: Number(netProfit.toFixed(2)),
    effectiveOdds: Number(effectiveOdds.toFixed(2)),
    combinedProb: Number(combinedProb.toFixed(4)),
  };
}
