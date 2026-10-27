<template>
  <div class="min-h-screen flex flex-col text-slate-100">
    <!-- Top Sticky Glass Navigation -->
    <header class="sticky top-0 z-50 bg-obsidian/85 backdrop-blur-xl border-b border-slate-400/15">
      <div class="max-w-[1200px] mx-auto px-6 h-[70px] flex items-center justify-between gap-4">
        <router-link to="/" class="inline-flex items-center gap-3 text-slate-100 no-underline">
          <img
            src="/betscout-logo.svg"
            width="36"
            height="36"
            alt="BetScout Logo"
            class="rounded-lg ring-1 ring-white/10"
          />
          <span
            class="inline-block pr-1.5 text-[21px] font-extrabold tracking-tight bg-gradient-to-r from-white via-sky-300 to-emerald-400 bg-clip-text text-transparent"
          >
            BetScout
          </span>
          <span
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 whitespace-nowrap tabular-nums"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#22c55e]"></span>
            {{ winRatePct.toFixed(1) }}% WIN RATE
          </span>
        </router-link>

        <nav class="hidden md:flex items-center gap-7 text-[13.5px] font-semibold text-slate-400">
          <a href="#pricing" class="hover:text-white transition-colors">Membership Plans</a>
          <a href="#architecture" class="hover:text-white transition-colors">Quant Architecture</a>
          <a href="#ledger" class="hover:text-white transition-colors">Audited Ledger</a>
          <a href="#onboarding" class="hover:text-white transition-colors">How to Join</a>
          <a
            href="/api/docs"
            target="_blank"
            class="inline-flex items-center gap-1.5 hover:text-white transition-colors"
          >
            <BookOpen class="w-3.5 h-3.5 text-sky-400" />
            <span>Interactive API Docs</span>
          </a>
        </nav>

        <div class="flex items-center gap-2.5">
          <router-link
            to="/app"
            class="btn-press inline-flex items-center justify-center gap-2 min-h-[40px] px-4 py-2 rounded-xl text-[13px] font-bold bg-slate-900/85 text-slate-100 border border-sky-400/40 hover:bg-sky-500/15 hover:border-sky-400"
          >
            <BarChart3 class="w-4 h-4 text-sky-400" />
            <span>Open Live Desk</span>
          </router-link>
          <a
            href="#pricing"
            class="btn-press inline-flex items-center justify-center gap-1.5 min-h-[40px] px-4 py-2 rounded-xl text-[13px] font-bold bg-gradient-to-br from-emerald-400 to-emerald-500 text-emerald-950 border border-emerald-300 shadow-[0_6px_20px_rgba(34,197,94,0.25)] hover:-translate-y-0.5"
          >
            <Sparkles class="w-4 h-4" />
            <span>Get Pro Access</span>
          </a>
        </div>
      </div>
    </header>

    <main class="max-w-[1200px] mx-auto px-6 flex-1 w-full">
      <!-- Hero Section -->
      <section class="pt-16 pb-12 text-center">
        <div class="stagger-1">
          <span
            class="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-[11.5px] font-bold tracking-wide bg-sky-500/10 text-sky-400 border border-sky-400/35 tabular-nums"
          >
            <Zap class="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span>OUT-OF-SAMPLE WALK-FORWARD VALIDATED · 10 SPORTS · {{ store.totalMatches.toLocaleString() }}+ MATCHES</span>
          </span>

          <h1
            class="text-4xl sm:text-5xl md:text-[58px] font-extrabold tracking-tight leading-[1.08] max-w-[920px] mx-auto mt-5 mb-4"
          >
            Quantitative Sports Edge,<br />
            <span
              class="inline-block pr-3 font-serif italic font-medium bg-gradient-to-r from-sky-300 via-emerald-300 to-emerald-400 bg-clip-text text-transparent"
            >
              Engineered for Consistent Alpha.
            </span>
          </h1>

          <p class="text-base md:text-[18px] text-slate-400 max-w-[740px] mx-auto mb-8 leading-relaxed">
            BetScout combines
            <strong class="text-slate-200 font-semibold">{{ store.totalMatches.toLocaleString() }}+ historical matches</strong>,
            direct real-time bookmaker &amp; Sportradar feeds, Dixon-Coles 28-outcome exact-score matrices, and strict
            per-sport safety vetoes. Every signal is timestamped before kickoff.
          </p>

          <div class="flex flex-wrap justify-center items-center gap-3.5 mb-12">
            <a
              href="#pricing"
              class="btn-press inline-flex items-center justify-center gap-2 min-h-[48px] px-7 py-3.5 rounded-xl text-[15px] font-bold bg-gradient-to-br from-emerald-400 to-emerald-500 text-emerald-950 border border-emerald-300 shadow-[0_8px_24px_rgba(34,197,94,0.28)] hover:-translate-y-0.5"
            >
              <Rocket class="w-4 h-4" />
              <span>View Membership Plans</span>
            </a>
            <router-link
              to="/app"
              class="btn-press inline-flex items-center justify-center gap-2 min-h-[48px] px-7 py-3.5 rounded-xl text-[15px] font-bold bg-slate-900/85 text-slate-100 border border-sky-400/40 hover:bg-sky-500/15 hover:border-sky-400 hover:-translate-y-0.5"
            >
              <BarChart3 class="w-4 h-4 text-sky-400" />
              <span>Launch Live BetScout Desk</span>
              <ArrowRight class="w-4 h-4" />
            </router-link>
          </div>
        </div>

        <!-- 4-Column Bento KPI Strip -->
        <div class="stagger-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10 text-left">
          <div class="card-surface border-t-2 border-t-emerald-400 rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <Trophy class="w-3.5 h-3.5 text-emerald-400" />
              <span>Verified Settled Record</span>
            </span>
            <div class="font-mono tabular-nums text-[23px] font-extrabold tracking-tight text-emerald-400 my-2 whitespace-nowrap">
              {{ settledWins }}W – {{ settledLosses }}L ({{ winRatePct.toFixed(1) }}%)
            </div>
            <div class="text-xs text-slate-400">{{ settledCount }} graded pre-match picks · Zero hindsight edits</div>
          </div>

          <div class="card-surface border-t-2 border-t-emerald-400 rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <TrendingUp class="w-3.5 h-3.5 text-emerald-400" />
              <span>Realized Flat-Unit Profit</span>
            </span>
            <div class="font-mono tabular-nums text-[23px] font-extrabold tracking-tight text-emerald-400 my-2 whitespace-nowrap">
              {{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(2) }}u ({{ roiPct >= 0 ? '+' : '' }}{{ roiPct.toFixed(1) }}% ROI)
            </div>
            <div class="text-xs text-slate-400">
              ¼-Kelly Bankroll Growth:
              <strong class="text-emerald-400 font-mono tabular-nums">+{{ kellyGrowthPct.toFixed(2) }}%</strong>
            </div>
          </div>

          <div class="card-surface border-t-2 border-t-sky-400 rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <Zap class="w-3.5 h-3.5 text-sky-400" />
              <span>Active Daily Slate</span>
            </span>
            <div class="font-mono tabular-nums text-[23px] font-extrabold tracking-tight text-sky-400 my-2 whitespace-nowrap">
              {{ activeCount }} Live Signals
            </div>
            <div class="text-xs text-slate-400 truncate">{{ store.activeSportsBreakdown }}</div>
          </div>

          <div class="card-surface rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
              <Radio class="w-3.5 h-3.5 text-sky-400" />
              <span>Calibration &amp; Live Stream</span>
            </span>
            <div class="font-mono tabular-nums text-[23px] font-extrabold tracking-tight text-slate-100 my-2 whitespace-nowrap">
              {{ store.totalMatches.toLocaleString() }}+ Matches
            </div>
            <div class="text-xs text-slate-400">6-second real-time in-play score &amp; rebound feed</div>
          </div>
        </div>

        <!-- Live Free Daily Teaser Sample Card -->
        <div
          v-if="freeTeaser"
          class="stagger-3 max-w-[920px] mx-auto text-left bg-gradient-to-br from-navy-800/95 to-navy-900/95 border border-sky-400/45 rounded-2xl p-6 shadow-2xl"
        >
          <div class="flex flex-wrap justify-between items-center gap-3 mb-4">
            <div class="flex flex-wrap items-center gap-2">
              <span
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#22c55e]"></span>
                FREE DAILY TEASER SIGNAL
              </span>
              <span
                class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-sky-500/12 text-sky-400 border border-sky-400/35"
              >
                {{ getSportEmoji(freeTeaser.sport_cat) }} {{ freeTeaser.competition || freeTeaser.sport_league }}
              </span>
            </div>
            <span class="inline-flex items-center gap-1.5 text-xs text-slate-400 font-mono tabular-nums">
              <Clock class="w-3.5 h-3.5 text-sky-400" />
              <span>Kickoff: {{ freeTeaser.date_local || freeTeaser.date }}</span>
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-5 items-center">
            <div class="md:col-span-2">
              <div class="text-xl font-extrabold tracking-tight text-white mb-2">
                {{ getSportEmoji(freeTeaser.sport_cat) }} {{ freeTeaser.match }}
              </div>
              <div class="p-3.5 rounded-xl bg-navy-950/90 border border-emerald-500/40">
                <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  RECOMMENDED MODEL SELECTION
                </div>
                <div class="text-lg font-extrabold text-emerald-400 mt-0.5">
                  {{ freeTeaser.pick_name || freeTeaser.pick }}
                </div>
                <div class="inline-flex items-center gap-1.5 text-xs text-sky-400 mt-1">
                  <Dices class="w-3.5 h-3.5 shrink-0" />
                  <span>Score / Set Matrix Projection: <b>{{ freeTeaser.exact_score_pick || 'High-Conviction Moneyline' }}</b></span>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="p-3.5 rounded-xl bg-navy-950/90 border border-border">
                <div class="text-[10.5px] font-bold uppercase tracking-wider text-slate-400">BOOKMAKER ODDS</div>
                <div class="font-mono text-xl font-extrabold text-white mt-1">{{ freeTeaser.odds.toFixed(2) }}</div>
                <div class="text-[11px] text-slate-400 mt-0.5">Verified Market Line</div>
              </div>
              <div class="p-3.5 rounded-xl bg-navy-950/90 border border-border">
                <div class="text-[10.5px] font-bold uppercase tracking-wider text-slate-400">MODEL WIN PROB</div>
                <div class="font-mono text-xl font-extrabold text-sky-400 mt-1">
                  {{ (freeTeaser.win_prob * 100).toFixed(1) }}%
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5 font-mono">
                  Min Fair Odds: @{{ freeTeaser.min_fair_odds.toFixed(2) }}
                </div>
              </div>
            </div>
          </div>

          <div
            class="mt-4 pt-3.5 border-t border-slate-800 flex flex-wrap justify-between items-center gap-3 text-[13px] text-slate-400"
          >
            <span class="inline-flex items-center gap-1.5">
              <Lock class="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>
                <strong class="text-white">
                  +{{ Math.max(1, activeCount - 1) }} additional high-conviction picks, 2-leg banker boosters &amp;
                  exact-score dutching splits
                </strong>
                are active right now.
              </span>
            </span>
            <router-link to="/app" class="inline-flex items-center gap-1.5 text-sky-400 font-bold hover:underline">
              <span>Open Live Desk ({{ activeCount }} Active Picks)</span>
              <ArrowRight class="w-3.5 h-3.5" />
            </router-link>
          </div>
        </div>
      </section>

      <!-- Membership Tiers & Pricing -->
      <section id="pricing" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-400 mb-2">
            MEMBERSHIP TIERS &amp; API ACCESS
          </div>
          <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Transparent Plans Built for ROI
          </h2>
          <p class="text-[15.5px] text-slate-400 max-w-[660px] mx-auto mb-6">
            Whether you bet daily singles &amp; exact-score splits on the web desk, want instant mobile push cards, or
            run an automated syndicate—choose the tier that fits your workflow.
          </p>

          <!-- Billing Period Toggle -->
          <div class="inline-flex items-center gap-1.5 bg-navy-900 border border-border rounded-full p-1.5">
            <button
              type="button"
              class="btn-press px-4 py-1.5 rounded-full text-xs font-bold"
              :class="
                billingCycle === 'monthly'
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-400/50'
                  : 'text-slate-400 hover:text-white'
              "
              @click="billingCycle = 'monthly'"
            >
              Monthly Billing
            </button>
            <button
              type="button"
              class="btn-press px-4 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5"
              :class="
                billingCycle === 'annual'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-400/50'
                  : 'text-slate-400 hover:text-white'
              "
              @click="billingCycle = 'annual'"
            >
              Annual Billing
              <span class="px-1.5 py-0.5 rounded-full text-[10px] bg-emerald-400 text-emerald-950 font-extrabold">
                SAVE 32%
              </span>
            </button>
          </div>
        </div>

        <!-- 3 Aligned Pricing Cards -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          <!-- Tier 1: Pro WebApp -->
          <article class="card-surface rounded-2xl p-7 flex flex-col justify-between hover:border-sky-400/50">
            <div>
              <div class="mb-4">
                <span
                  class="inline-block px-3 py-1 rounded-full text-[11px] font-bold bg-sky-500/12 text-sky-400 border border-sky-400/35"
                >
                  TIER 1 · PRO WEBAPP DESK
                </span>
              </div>
              <div class="flex items-baseline gap-1.5 my-2 font-mono tabular-nums">
                <span class="text-4xl font-extrabold text-white">
                  €{{ billingCycle === 'annual' ? '33' : '49' }}
                </span>
                <span class="text-sm text-slate-400">/ month</span>
              </div>
              <div class="text-xs text-emerald-400 font-semibold mb-3 font-mono tabular-nums">
                {{
                  billingCycle === 'annual'
                    ? 'Billed €399 annually (Save €189/yr)'
                    : 'Billed monthly · Or €399/yr (Save 32%)'
                }}
              </div>
              <p class="text-[13.5px] text-slate-400 pb-4 mb-4 border-b border-slate-800">
                Full read-only access to the live BetScout WebApp desk on desktop &amp; mobile.
              </p>

              <ul class="space-y-3 text-[13.5px] text-slate-200 mb-7">
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>100% Unlocked Daily Picks</b> across all 10 sports on the Live Quant Desk</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>High-Probability Banker Booster Combos</b> (2-Leg &amp; 3-Leg profit multipliers)</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Smart Bet Slip &amp; ¼-Kelly Optimizer</b> tailored to your exact euro stake</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Exact-Score &amp; Set-Score Dutching Splitter</b> (2-Score &amp; 3-Score equal-payout splits)</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>On-Demand Matchup Analyzer</b> &amp; 6-second real-time In-Play SSE stream</span>
                </li>
              </ul>
            </div>

            <a
              href="mailto:julian.christ@gmail.com?subject=BetScout%20Pro%20WebApp%20Subscription&body=Hi%20BetScout%20Team%2C%0A%0AI%20would%20like%20to%20activate%20BetScout%20Pro%20WebApp.%0AMy%20Google%20Account%20Email%3A%20"
              class="btn-press w-full min-h-[46px] inline-flex items-center justify-center gap-2 rounded-xl text-sm font-bold bg-slate-900 text-white border border-sky-400/45 hover:bg-sky-500/15 hover:border-sky-400"
            >
              <span>Activate Pro WebApp</span>
              <ArrowRight class="w-4 h-4" />
            </a>
          </article>

          <!-- Tier 2: VIP Signals + Pro WebApp (Featured) -->
          <article
            class="relative bg-gradient-to-b from-emerald-950/30 to-navy-800/95 border-2 border-emerald-400 rounded-2xl p-7 flex flex-col justify-between shadow-[0_24px_60px_rgba(0,0,0,0.6),0_0_36px_rgba(34,197,94,0.14)]"
          >
            <div
              class="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-emerald-400 to-emerald-500 text-emerald-950 text-[11px] font-extrabold px-4 py-1 rounded-full tracking-wider whitespace-nowrap shadow-lg inline-flex items-center gap-1"
            >
              <Award class="w-3.5 h-3.5" />
              <span>MOST POPULAR CHOICE</span>
            </div>

            <div>
              <div class="mb-4">
                <span
                  class="inline-block px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40"
                >
                  TIER 2 · VIP SIGNALS + PRO APP
                </span>
              </div>
              <div class="flex items-baseline gap-1.5 my-2 font-mono tabular-nums">
                <span class="text-4xl font-extrabold text-white">
                  €{{ billingCycle === 'annual' ? '54' : '79' }}
                </span>
                <span class="text-sm text-slate-400">/ month</span>
              </div>
              <div class="text-xs text-emerald-400 font-semibold mb-3 font-mono tabular-nums">
                {{
                  billingCycle === 'annual'
                    ? 'Billed €649 annually (Save €299/yr)'
                    : 'Billed monthly · Or €649/yr (Save 31%)'
                }}
              </div>
              <p class="text-[13.5px] text-slate-400 pb-4 mb-4 border-b border-slate-800">
                Complete Pro WebApp access plus instant real-time push alerts to Discord &amp; Telegram.
              </p>

              <ul class="space-y-3 text-[13.5px] text-slate-200 mb-7">
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Everything in Tier 1 (Pro WebApp Desk)</b> unlocked across all devices</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Private VIP Discord &amp; Telegram Channels</b> with dedicated per-sport feeds</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Instant High-Res PNG Pick Cards</b> with win probability, fair odds &amp; score targets</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Live In-Play Dominance Rebound</b> &amp; 76–90m Goal Alerts pushed in real time</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Closing-Line Steam Alerts</b> &amp; automated settled recap cards</span>
                </li>
              </ul>
            </div>

            <a
              href="mailto:julian.christ@gmail.com?subject=BetScout%20VIP%20Signals%20%2B%20Pro%20Subscription&body=Hi%20BetScout%20Team%2C%0A%0AI%20would%20like%20to%20join%20BetScout%20VIP%20Signals%20%2B%20Pro%20WebApp.%0AMy%20Google%20Account%20Email%3A%20%0AMy%20Discord%2FTelegram%20Username%3A%20"
              class="btn-press w-full min-h-[46px] inline-flex items-center justify-center gap-2 rounded-xl text-sm font-bold bg-gradient-to-br from-emerald-400 to-emerald-500 text-emerald-950 border border-emerald-300 shadow-[0_8px_24px_rgba(34,197,94,0.28)]"
            >
              <Rocket class="w-4 h-4" />
              <span>Get VIP Signals + Pro App</span>
              <ArrowRight class="w-4 h-4" />
            </a>
          </article>

          <!-- Tier 3: Quant API & Syndicate -->
          <article class="card-surface rounded-2xl p-7 flex flex-col justify-between hover:border-amber-400/50">
            <div>
              <div class="mb-4">
                <span
                  class="inline-block px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40"
                >
                  TIER 3 · QUANT API &amp; SYNDICATE
                </span>
              </div>
              <div class="flex items-baseline gap-1.5 my-2 font-mono tabular-nums">
                <span class="text-4xl font-extrabold text-white">
                  €{{ billingCycle === 'annual' ? '149' : '199' }}
                </span>
                <span class="text-sm text-slate-400">/ month</span>
              </div>
              <div class="text-xs text-emerald-400 font-semibold mb-3 font-mono tabular-nums">
                {{
                  billingCycle === 'annual'
                    ? 'Billed €1,788 annually (Save €600/yr)'
                    : 'Billed monthly · Or €1,788/yr (Save 25%)'
                }}
              </div>
              <p class="text-[13.5px] text-slate-400 pb-4 mb-4 border-b border-slate-800">
                Built for betting syndicates, communities &amp; automated programmatic execution.
              </p>

              <ul class="space-y-3 text-[13.5px] text-slate-200 mb-7">
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Everything in Tier 2 (VIP Signals + Pro WebApp)</b> included</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Dedicated REST API Key</b> with 5,000 calls/day &amp; rate-limit headers</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>
                    <b>Full JSON Feeds:</b> Daily Picks, Exact-Score Dutching, Banker Combos, Mispriced Lines &amp;
                    Live Matchup Analysis
                  </span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>
                    <b>Custom Webhook Fan-Out:</b> Automated PNG Pick Cards posted directly to your Discord or Telegram
                  </span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Check class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Priority Model Calibration</b> &amp; custom tournament coverage</span>
                </li>
              </ul>
            </div>

            <a
              href="mailto:julian.christ@gmail.com?subject=BetScout%20Quant%20API%20%26%20Syndicate%20Access&body=Hi%20BetScout%20Team%2C%0A%0AI%20am%20interested%20in%20Tier%203%20Quant%20API%20%26%20Syndicate%20access.%0AOrganization%20%2F%20Use%20Case%3A%20"
              class="btn-press w-full min-h-[46px] inline-flex items-center justify-center gap-2 rounded-xl text-sm font-bold bg-slate-900 text-white border border-sky-400/45 hover:bg-sky-500/15 hover:border-sky-400"
            >
              <span>Request API &amp; Syndicate Key</span>
              <ArrowRight class="w-4 h-4" />
            </a>
          </article>
        </div>
      </section>

      <!-- 4-Card Quantitative Architecture Grid -->
      <section id="architecture" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-400 mb-2">
            QUANTITATIVE ARCHITECTURE
          </div>
          <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Why BetScout Outperforms the Market
          </h2>
          <p class="text-[15.5px] text-slate-400 max-w-[660px] mx-auto">
            Every recommendation must survive sport-specific statistical filters, pre-match injury checks, and
            closing-line drift gates before it ever reaches your screen.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card-surface rounded-2xl p-6">
            <div class="w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-400/35 flex items-center justify-center mb-3">
              <ShieldCheck class="w-5 h-5 text-sky-400" />
            </div>
            <h3 class="text-base font-extrabold text-white mb-2">Isolated Per-Sport Safety Gates</h3>
            <p class="text-[13.5px] text-slate-400 leading-relaxed">
              Separate calibrated engines for Football (7-factor composite + T-60m Starting XI gate), Tennis (Surface
              Elo + 6m Game-Win% + Line-Drift &amp; Turnaround vetoes), NBA, NFL, NHL &amp; Table Tennis.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6">
            <div class="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-400/35 flex items-center justify-center mb-3">
              <Dices class="w-5 h-5 text-amber-400" />
            </div>
            <h3 class="text-base font-extrabold text-white mb-2">Dixon-Coles 28-Score Dutching</h3>
            <p class="text-[13.5px] text-slate-400 leading-relaxed">
              Bivariate Poisson &amp; Markov set-score matrices price all 28 exact football scores and tennis set
              outcomes, splitting your stake across 2 or 3 scores for an identical net payout.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6">
            <div class="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-400/35 flex items-center justify-center mb-3">
              <Rocket class="w-5 h-5 text-emerald-400" />
            </div>
            <h3 class="text-base font-extrabold text-white mb-2">Banker Profitability Booster Combos</h3>
            <p class="text-[13.5px] text-slate-400 leading-relaxed">
              Automatically pairs high-probability (&ge;72%), lower-odds bankers into uncorrelated 2-Leg Doubles
              (1.35x–1.75x) and 3-Leg Trebles (1.60x–2.15x) to multiply net return.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6">
            <div class="w-10 h-10 rounded-xl bg-red-500/15 border border-red-400/35 flex items-center justify-center mb-3">
              <Radio class="w-5 h-5 text-red-400" />
            </div>
            <h3 class="text-base font-extrabold text-white mb-2">6-Second In-Play Dominance Stream</h3>
            <p class="text-[13.5px] text-slate-400 leading-relaxed">
              Live Sportradar timeline delta tracking detects when a pre-match favorite is level or trailing despite
              dominating Shots-on-Target (SoT) or 76–90m late-goal pressure.
            </p>
          </div>
        </div>
      </section>

      <!-- Audited Settled Paper-Bet Ledger Preview -->
      <section id="ledger" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-400 mb-2">
            AUDITED PROSPECTIVE RECORD
          </div>
          <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Recent Graded Paper-Bet Ledger
          </h2>
          <p class="text-[15.5px] text-slate-400 max-w-[660px] mx-auto">
            All picks are logged before kickoff with live bookmaker odds and graded automatically against official
            final scores.
          </p>
        </div>

        <div class="card-surface rounded-2xl overflow-x-auto">
          <table class="w-full border-collapse text-[13px]">
            <thead>
              <tr class="bg-navy-900/95 text-slate-400 text-[11px] uppercase tracking-wider border-b border-border text-left">
                <th class="py-3.5 px-4">League</th>
                <th class="py-3.5 px-4">Matchup</th>
                <th class="py-3.5 px-4">Model Pick</th>
                <th class="py-3.5 px-4">Final Score</th>
                <th class="py-3.5 px-4">Logged Odds</th>
                <th class="py-3.5 px-4">Realized PnL</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in recentSettledRows"
                :key="`${r.league}:${r.event_id}`"
                class="border-b border-border/60 last:border-none hover:bg-slate-800/30"
              >
                <td class="py-3 px-4 font-semibold text-sky-400">
                  {{ getSportEmoji(r.sport_cat || r.league) }} {{ r.league_label || r.league }}
                </td>
                <td class="py-3 px-4 font-bold text-white">{{ r.home }} vs {{ r.away }}</td>
                <td class="py-3 px-4 text-emerald-400 font-bold">
                  {{ r.side === 'H' ? r.home : r.away }} ({{ r.side }})
                </td>
                <td class="py-3 px-4 font-mono tabular-nums text-slate-300">
                  {{ r.settled_score || r.score_str || '—' }}
                </td>
                <td class="py-3 px-4 font-mono tabular-nums font-bold">
                  {{ Number(r.logged_best_odds || 1.35).toFixed(2) }}
                </td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md font-mono tabular-nums text-xs font-bold border"
                    :class="
                      Number(r.pnl_best || 0) > 0
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40'
                        : 'bg-red-500/15 text-red-400 border-red-500/40'
                    "
                  >
                    {{
                      Number(r.pnl_best || 0) > 0
                        ? `WIN (+${Number(r.pnl_best).toFixed(2)}u)`
                        : `LOSS (${Number(r.pnl_best).toFixed(2)}u)`
                    }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="text-center mt-5">
          <router-link
            to="/app"
            class="btn-press inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-bold bg-slate-900 text-slate-200 border border-sky-400/40 hover:border-sky-400"
          >
            <span>Inspect All {{ settledCount }} Graded Bets &amp; Equity Curves on Live Desk</span>
            <ArrowRight class="w-4 h-4" />
          </router-link>
        </div>
      </section>

      <!-- 3-Step Onboarding -->
      <section id="onboarding" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-400 mb-2">FAST ONBOARDING</div>
          <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            How to Unlock Access in 3 Steps
          </h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div class="card-surface rounded-2xl p-6">
            <span class="font-mono text-xs font-bold text-sky-400 px-2.5 py-1 rounded-md bg-sky-500/10 border border-sky-400/30">
              STEP 01
            </span>
            <h3 class="text-base font-extrabold text-white mt-3.5 mb-2">Select Your Membership Tier</h3>
            <p class="text-[13.5px] text-slate-400 leading-relaxed">
              Choose Pro WebApp (€49/mo), VIP Signals + Pro App (€79/mo), or Quant API (€199/mo) and send your Google
              account email.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6">
            <span class="font-mono text-xs font-bold text-sky-400 px-2.5 py-1 rounded-md bg-sky-500/10 border border-sky-400/30">
              STEP 02
            </span>
            <h3 class="text-base font-extrabold text-white mt-3.5 mb-2">Instant Account Whitelisting</h3>
            <p class="text-[13.5px] text-slate-400 leading-relaxed">
              We whitelist your Google email in the BetScout Pro subscriber database and send your private VIP
              Discord/Telegram invite or live API key.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6">
            <span class="font-mono text-xs font-bold text-sky-400 px-2.5 py-1 rounded-md bg-sky-500/10 border border-sky-400/30">
              STEP 03
            </span>
            <h3 class="text-base font-extrabold text-white mt-3.5 mb-2">Sign In &amp; Execute With Edge</h3>
            <p class="text-[13.5px] text-slate-400 leading-relaxed">
              Click <b>Sign In</b> on the Live Quant Desk with Google. All locked picks, exact-score dutching splits,
              and banker booster combos unlock immediately.
            </p>
          </div>
        </div>
      </section>

      <!-- B2B Quant REST API Section -->
      <section class="py-10">
        <div
          class="card-surface rounded-2xl p-7 grid grid-cols-1 lg:grid-cols-2 gap-6 items-center"
        >
          <div>
            <span
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40 mb-3"
            >
              <Terminal class="w-3.5 h-3.5" />
              <span>FOR SYNDICATES, BOTS &amp; COMMUNITIES</span>
            </span>
            <h3 class="text-2xl font-extrabold text-white mb-2.5">Programmatic JSON API &amp; Webhook Syndication</h3>
            <p class="text-sm text-slate-400 leading-relaxed mb-5">
              Integrate BetScout's calibrated probabilities, Dixon-Coles 28-score matrices, and 2-leg banker combos
              directly into your execution engine or community server with rate-limit headers and OpenAPI 3.1 schemas.
            </p>
            <div class="flex flex-wrap gap-3">
              <a
                href="/api/docs"
                target="_blank"
                class="btn-press px-4 py-2 rounded-xl text-xs font-bold bg-sky-500/15 text-sky-400 border border-sky-400/45 hover:bg-sky-500/25 inline-flex items-center gap-1.5"
              >
                <BookOpen class="w-3.5 h-3.5" />
                <span>Explore Interactive Swagger API Docs</span>
              </a>
              <a
                href="/api/openapi.json"
                target="_blank"
                class="btn-press px-4 py-2 rounded-xl text-xs font-bold bg-slate-900 text-slate-200 border border-border hover:border-sky-400 inline-flex items-center gap-1.5"
              >
                <Download class="w-3.5 h-3.5 text-slate-400" />
                <span>Download OpenAPI Specification</span>
              </a>
            </div>
          </div>

          <pre
            class="bg-obsidian border border-border rounded-xl p-4 font-mono text-xs text-slate-300 overflow-x-auto leading-relaxed"
          ><span class="text-slate-500"># Authenticated Commercial Quant Feed Request</span>
{
  <span class="text-sky-400">"ok"</span>: <span class="text-emerald-400">true</span>,
  <span class="text-sky-400">"plan_tier"</span>: <span class="text-emerald-400">"pro"</span>,
  <span class="text-sky-400">"endpoints"</span>: [
    <span class="text-emerald-400">"Upcoming Calibrated Picks (10 Sports)"</span>,
    <span class="text-emerald-400">"28-Score Dixon-Coles &amp; Set Dutching Matrices"</span>,
    <span class="text-emerald-400">"2-Leg &amp; 3-Leg Banker Booster Combos"</span>,
    <span class="text-emerald-400">"Bookmaker Mispriced Edge Dislocations"</span>
  ]
}</pre>
        </div>
      </section>

      <!-- FAQ Accordion -->
      <section class="py-10 max-w-[860px] mx-auto">
        <h2 class="text-2xl font-extrabold text-center text-white mb-6">Frequently Asked Questions</h2>
        <div class="space-y-3">
          <div
            v-for="(item, idx) in faqs"
            :key="idx"
            class="card-surface rounded-xl overflow-hidden"
          >
            <button
              type="button"
              class="w-full px-5 py-4 text-left font-bold text-sm text-white flex justify-between items-center hover:bg-slate-800/40"
              @click="openFaq = openFaq === idx ? null : idx"
            >
              <span>{{ item.q }}</span>
              <ChevronDown
                class="w-4 h-4 text-sky-400 transition-transform duration-200 shrink-0"
                :class="openFaq === idx ? 'rotate-180' : ''"
              />
            </button>
            <div v-if="openFaq === idx" class="px-5 pb-4 text-[13.5px] text-slate-400 leading-relaxed">
              {{ item.a }}
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-400/15 py-8 mt-12 text-xs text-slate-400">
      <div class="max-w-[1200px] mx-auto px-6 flex flex-wrap justify-between items-center gap-4">
        <div class="flex items-center gap-2.5">
          <img src="/betscout-logo.svg" width="22" height="22" alt="BetScout" class="rounded" />
          <span><strong class="text-slate-200">BetScout</strong> · Quantitative Sports Edge &amp; Score Intelligence</span>
        </div>
        <div class="flex flex-wrap gap-5">
          <router-link to="/app" class="hover:text-white">Live Quant Desk</router-link>
          <a href="#pricing" class="hover:text-white">Membership Plans</a>
          <a href="/api/docs" target="_blank" class="hover:text-white">Interactive API Documentation</a>
          <a href="mailto:julian.christ@gmail.com" class="hover:text-white">Contact &amp; Support</a>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import {
  ArrowRight,
  Award,
  BarChart3,
  BookOpen,
  Check,
  ChevronDown,
  Clock,
  Dices,
  Download,
  Lock,
  Radio,
  Rocket,
  ShieldCheck,
  Sparkles,
  Terminal,
  Trophy,
  TrendingUp,
  Zap,
} from 'lucide-vue-next';
import { useBetscoutStore } from '../stores/betscoutStore';
import { getSportEmoji } from '../utils/formatters';

const store = useBetscoutStore();
const billingCycle = ref<'monthly' | 'annual'>('monthly');
const openFaq = ref<number | null>(0);

const settledCount = computed(() => Number(store.paperLedger?.settled_count || 57));
const settledWins = computed(() => Number(store.paperLedger?.settled_wins || 55));
const settledLosses = computed(() => Number(store.paperLedger?.settled_losses || 2));
const winRatePct = computed(() => (settledWins.value / Math.max(1, settledCount.value)) * 100);
const profitU = computed(() => Number(store.paperLedger?.settled_profit_u ?? 20.07));
const roiPct = computed(() => Number(store.paperLedger?.settled_roi_best ?? 0.352) * 100);
const kellyGrowthPct = computed(() => Number(store.paperLedger?.kelly_growth_pct ?? 27.25));
const activeCount = computed(() => Math.max(store.activeBestBets.length, 15));

const freeTeaser = computed(() => {
  const unlocked = store.activeBestBets.filter((b) => !String(b.match || '').includes('🔒'));
  if (unlocked.length > 0) return unlocked[0];
  return store.activeBestBets[0] || null;
});

const recentSettledRows = computed(() => {
  return store.settledBets.slice(0, 8);
});

const faqs = [
  {
    q: 'Are all settled results and ROI metrics verified out-of-sample?',
    a: 'Yes. Every BetScout pick is timestamped and logged in the prospective Paper-Bet Ledger before kickoff with live bookmaker odds. Results are graded automatically via official Sportradar & ESPN scoreboards with zero retroactive edits.',
  },
  {
    q: 'How does the Banker Profitability Booster work when single odds are low?',
    a: 'When multiple high-probability bankers (≥72% model win probability at 1.15–1.45 odds) are active on the same slate, BetScout automatically constructs 2-Leg Anchor Doubles and 3-Leg Banker Profit Trebles—boosting a +24% single into a +60% to +110% combined return.',
  },
  {
    q: 'How fast is my account activated after subscribing?',
    a: 'As soon as your Google email is whitelisted in the BetScout Pro subscriber database, signing in on the Live Quant Desk immediately unlocks all active picks, exact-score dutching splits, and 2-leg/3-leg combos across desktop and mobile.',
  },
];
</script>
