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

/**
 * Preserved FontAwesome 6 Solid (`fa6-solid:*`) monochrome sport icon mapping.
 * Kept intact so we can switch back to monochrome `fa6-solid:*` icons at any time in the future.
 */
export const SPORT_FA6_ICONIFY_NAMES: Record<string, string> = {
  all: 'fa6-solid:globe',
  soccer: 'fa6-solid:futbol',
  tennis: 'fa6-solid:tennis-ball',
  basketball: 'fa6-solid:basketball',
  volleyball: 'fa6-solid:volleyball',
  hockey: 'fa6-solid:hockey-puck',
  football: 'fa6-solid:football',
  baseball: 'fa6-solid:baseball-bat-ball',
  handball: 'fa6-solid:handball',
  darts: 'fa6-solid:bullseye',
  table_tennis: 'fa6-solid:table-tennis-paddle-ball',
};

/**
 * Active Multi-Color Vector Sport Iconify mapping (`betscout-sport:*`, registered in `iconifySetup.ts`),
 * matching the notification card sport icons across all platforms without OS-dependent emoji font glyphs.
 */
export const SPORT_ICONIFY_NAMES: Record<string, string> = {
  all: 'betscout-sport:all',
  soccer: 'betscout-sport:soccer',
  tennis: 'betscout-sport:tennis',
  basketball: 'betscout-sport:basketball',
  volleyball: 'betscout-sport:volleyball',
  hockey: 'betscout-sport:hockey',
  football: 'betscout-sport:football',
  baseball: 'betscout-sport:baseball',
  handball: 'betscout-sport:handball',
  darts: 'betscout-sport:darts',
  table_tennis: 'betscout-sport:table_tennis',
};

export const SPORT_CLEAN_LABELS: Record<string, string> = {
  all: 'All Sports',
  soccer: 'Football',
  tennis: 'Tennis',
  basketball: 'Basketball',
  volleyball: 'Volleyball',
  hockey: 'Hockey',
  football: 'NFL',
  baseball: 'Baseball',
  handball: 'Handball',
  darts: 'Darts',
  table_tennis: 'Table Tennis',
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

export function getSportIconify(catOrLeague?: string | null): string {
  const low = String(catOrLeague || '').toLowerCase().trim();
  if (SPORT_ICONIFY_NAMES[low]) return SPORT_ICONIFY_NAMES[low];
  if (low.includes('table tennis') || low.includes('table_tennis') || low.includes('wtt')) return 'betscout-sport:table_tennis';
  if (low.includes('handball')) return 'betscout-sport:handball';
  if (low.includes('darts')) return 'betscout-sport:darts';
  if (low.includes('tennis') || low.includes('atp') || low.includes('wta')) return 'betscout-sport:tennis';
  if (low.includes('volleyball')) return 'betscout-sport:volleyball';
  if (low.includes('basketball') || low.includes('nba') || low.includes('wnba') || low.includes('ncaa') || low.includes('nbl') || low.includes('fiba')) return 'betscout-sport:basketball';
  if (low.includes('hockey') || low.includes('nhl')) return 'betscout-sport:hockey';
  if (low.includes('nfl') || low.includes('american football')) return 'betscout-sport:football';
  if (low.includes('baseball') || low.includes('mlb')) return 'betscout-sport:baseball';
  return 'betscout-sport:soccer';
}

/**
 * Resolve a country / federation Flag Iconify name (`flag:*`) for a competition or league string
 * when a country/region can be identified. Returns `null` when international / tour-wide without a country.
 */
export function getCompetitionFlagIconify(compOrLeague?: string | null, secondaryHint?: string | null): string | null {
  const raw = `${compOrLeague || ''} ${secondaryHint || ''}`.toLowerCase().trim();
  if (!raw) return null;

  // Football / European domestic & continental leagues
  if (raw.includes('eng.1') || raw.includes('eng.2') || raw.includes('premier league') || raw.includes('english championship') || raw.includes('england')) {
    return 'flag:gb-eng';
  }
  if (raw.includes('esp.1') || raw.includes('laliga') || raw.includes('la liga') || raw.includes('copa del rey') || raw.includes('spain') || raw.includes('madrid') || raw.includes('barcelona')) {
    return 'flag:es';
  }
  if (raw.includes('ger.1') || (raw.includes('bundesliga') && !raw.includes('austria') && !raw.includes('aut.1')) || raw.includes('germany')) {
    return 'flag:de';
  }
  if (raw.includes('ita.1') || raw.includes('serie a') || raw.includes('italy') || raw.includes('vienna') === false && raw.includes('rome')) {
    return 'flag:it';
  }
  if (raw.includes('fra.1') || raw.includes('ligue 1') || raw.includes('france') || raw.includes('paris') || raw.includes('montpellier') || raw.includes('brest') || raw.includes('roland garros')) {
    return 'flag:fr';
  }
  if (raw.includes('aut.1') || raw.includes('austria') || raw.includes('hla meisterliga') || raw.includes('vienna')) {
    return 'flag:at';
  }
  if (raw.includes('ned.1') || raw.includes('eredivisie') || raw.includes('netherlands') || raw.includes('dutch')) {
    return 'flag:nl';
  }
  if (raw.includes('por.1') || raw.includes('primeira liga') || raw.includes('portugal')) {
    return 'flag:pt';
  }
  if (raw.includes('sweden') || raw.includes('handbollsligan') || raw.includes('allsvenskan')) {
    return 'flag:se';
  }
  if (raw.includes('switzerland') || raw.includes('basel') || raw.includes('swiss')) {
    return 'flag:ch';
  }
  if (raw.includes('poland') || raw.includes('tt elite') || raw.includes('superliga')) {
    return 'flag:pl';
  }
  if (raw.includes('czech') || raw.includes('tt star') || raw.includes('extraliga')) {
    return 'flag:cz';
  }
  if (raw.includes('denmark')) return 'flag:dk';
  if (raw.includes('norway')) return 'flag:no';
  if (raw.includes('modus') || raw.includes('pdc') || raw.includes('wimbledon') || raw.includes('united kingdom')) {
    return 'flag:gb';
  }
  if (
    raw.includes('uefa') ||
    raw.includes('champions league') ||
    raw.includes('europa league') ||
    raw.includes('conference league') ||
    raw.includes('nations league') ||
    raw.includes('ehf') ||
    raw.includes('euroleague')
  ) {
    return 'flag:eu';
  }

  // US & North American Major Sports + ATP/WTA Tour Stops
  if (
    raw.includes('nba') ||
    raw.includes('wnba') ||
    raw.includes('nfl') ||
    raw.includes('nhl') ||
    raw.includes('mlb') ||
    raw.includes('ncaa') ||
    raw.includes('wvolleyball') ||
    raw.includes('mvolleyball') ||
    raw.includes('us open') ||
    raw.includes('indian wells') ||
    raw.includes('miami') ||
    raw.includes('cincinnati')
  ) {
    return 'flag:us';
  }
  if (raw.includes('nbl') || raw.includes('australia') || raw.includes('australian open')) {
    return 'flag:au';
  }
  if (raw.includes('tokyo') || raw.includes('japan')) return 'flag:jp';
  if (raw.includes('hong kong')) return 'flag:hk';
  if (raw.includes('guangzhou') || raw.includes('jiujiang') || raw.includes('shanghai') || raw.includes('beijing') || raw.includes('wuhan') || raw.includes('china')) {
    return 'flag:cn';
  }
  if (raw.includes('tampico') || raw.includes('guadalajara') || raw.includes('acapulco') || raw.includes('monterrey') || raw.includes('mexico')) {
    return 'flag:mx';
  }
  if (raw.includes('florianopolis') || raw.includes('rio') || raw.includes('sao paulo') || raw.includes('brazil')) {
    return 'flag:br';
  }
  if (raw.includes('cali') || raw.includes('bogota') || raw.includes('colombia')) {
    return 'flag:co';
  }
  return null;
}

export function getSportIconColor(catOrLeague?: string | null): string {
  const low = String(catOrLeague || '').toLowerCase().trim();
  if (low.includes('table tennis') || low.includes('table_tennis')) return 'text-fuchsia-400';
  if (low.includes('tennis') || low.includes('atp') || low.includes('wta')) return 'text-lime-400';
  if (low.includes('basketball') || low.includes('nba')) return 'text-orange-400';
  if (low.includes('hockey') || low.includes('nhl')) return 'text-cyan-400';
  if (low.includes('nfl') || low.includes('football') && !low.includes('soccer')) return 'text-amber-400';
  if (low.includes('volleyball')) return 'text-yellow-400';
  if (low.includes('baseball') || low.includes('mlb')) return 'text-rose-400';
  if (low.includes('handball')) return 'text-indigo-400';
  if (low.includes('darts')) return 'text-red-400';
  if (low === 'all') return 'text-sky-400';
  return 'text-emerald-400';
}

export function getSportBadgeTheme(catOrLeague?: string | null): string {
  const low = String(catOrLeague || '').toLowerCase().trim();
  if (low.includes('table tennis') || low.includes('table_tennis'))
    return 'bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-400/40';
  if (low.includes('tennis') || low.includes('atp') || low.includes('wta'))
    return 'bg-lime-500/15 text-lime-300 border-lime-400/40';
  if (low.includes('basketball') || low.includes('nba'))
    return 'bg-orange-500/15 text-orange-300 border-orange-400/40';
  if (low.includes('hockey') || low.includes('nhl'))
    return 'bg-cyan-500/15 text-cyan-300 border-cyan-400/40';
  if (low.includes('nfl') || (low.includes('football') && !low.includes('soccer')))
    return 'bg-amber-500/15 text-amber-300 border-amber-400/40';
  if (low.includes('volleyball'))
    return 'bg-yellow-500/15 text-yellow-300 border-yellow-400/40';
  if (low.includes('baseball') || low.includes('mlb'))
    return 'bg-rose-500/15 text-rose-300 border-rose-400/40';
  if (low.includes('handball'))
    return 'bg-indigo-500/15 text-indigo-300 border-indigo-400/40';
  if (low.includes('darts'))
    return 'bg-red-500/15 text-red-300 border-red-400/40';
  return 'bg-emerald-500/15 text-emerald-300 border-emerald-400/40';
}

export function getTierBadgeClass(tier?: string | null): string {
  const low = String(tier || '').toLowerCase().trim();
  if (low.includes('tier_0') || low.includes('top_8pct')) {
    return 'bg-violet-500/20 text-violet-200 border-violet-400/55 shadow-[0_0_10px_rgba(139,92,246,0.22)]';
  }
  if (low.includes('banker') || low.includes('tier_1') || low.includes('top_10pct')) {
    return 'bg-amber-500/20 text-amber-300 border-amber-400/55 shadow-[0_0_10px_rgba(245,158,11,0.16)]';
  }
  if (low.includes('top_15pct') || low.includes('high_conf') || low.includes('uefa')) {
    return 'bg-cyan-500/20 text-cyan-300 border-cyan-400/50';
  }
  if (low.includes('tracked')) {
    return 'bg-rose-500/20 text-rose-300 border-rose-400/50';
  }
  return 'bg-indigo-500/20 text-indigo-300 border-indigo-400/50';
}

export function getWinProbBarColor(prob?: number): string {
  const p = Number(prob || 0);
  if (p >= 0.8) return 'bg-gradient-to-r from-emerald-400 to-teal-300';
  if (p >= 0.7) return 'bg-gradient-to-r from-sky-400 to-cyan-300';
  if (p >= 0.6) return 'bg-gradient-to-r from-amber-400 to-yellow-300';
  return 'bg-gradient-to-r from-indigo-400 to-violet-300';
}

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
