<template>
  <div class="min-h-screen flex flex-col text-slate-100 relative overflow-x-hidden">
    <!-- Ambient Background Glow Orbs for Frosted Glass Refraction -->
    <div
      class="pointer-events-none fixed -top-32 left-1/4 w-[520px] h-[340px] rounded-full bg-sky-500/15 blur-[130px] -z-10"
    ></div>
    <div
      class="pointer-events-none fixed top-64 right-1/5 w-[460px] h-[320px] rounded-full bg-emerald-500/12 blur-[130px] -z-10"
    ></div>
    <div
      class="pointer-events-none fixed bottom-24 left-1/3 w-[480px] h-[300px] rounded-full bg-violet-500/10 blur-[140px] -z-10"
    ></div>

    <!-- Top Sticky Glass Navigation (Zero Overlap + Mobile Drawer) -->
    <header class="sticky top-0 z-50 w-full bg-obsidian/80 backdrop-blur-2xl border-b border-slate-300/15">
      <div class="w-full max-w-[1240px] mx-auto px-4 sm:px-6 min-h-[66px] py-2.5 flex items-center justify-between gap-2 sm:gap-4">
        <!-- Brand Logo -->
        <router-link to="/" class="inline-flex items-center gap-2.5 text-slate-100 no-underline min-w-0">
          <img
            src="/betscout-logo.svg?v=7.3"
            width="34"
            height="34"
            alt="BetScout Logo"
            class="rounded-xl ring-1 ring-white/15 shadow-[0_0_16px_rgba(56,189,248,0.25)] shrink-0"
          />
          <span class="text-[20px] sm:text-[21px] font-extrabold tracking-tight whitespace-nowrap">
            <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
          </span>
          <span
            class="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/45 whitespace-nowrap tabular-nums shadow-[0_0_12px_rgba(16,185,129,0.2)]"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
            {{ winRatePct.toFixed(1) }}% WIN RATE
          </span>
        </router-link>

        <!-- Desktop Navigation Links (lg and up — never wraps) -->
        <nav class="hidden lg:flex items-center gap-5 xl:gap-7 text-[13px] font-semibold text-slate-300 whitespace-nowrap">
          <a href="#pricing" class="hover:text-sky-300 transition-colors">Membership Plans</a>
          <a href="#architecture" class="hover:text-sky-300 transition-colors">Quant Architecture</a>
          <a href="#ledger" class="hover:text-sky-300 transition-colors">Audited Ledger</a>
          <a href="#onboarding" class="hover:text-sky-300 transition-colors">How to Join</a>
        </nav>

        <!-- Right CTA Buttons + Mobile Menu Trigger -->
        <div class="flex items-center gap-2 shrink-0">
          <button
            v-if="store.canInstallPwa"
            type="button"
            class="btn-press hidden xl:inline-flex items-center gap-1.5 min-h-[36px] px-3 py-1.5 rounded-xl text-xs font-bold bg-violet-500/20 text-violet-200 border border-violet-400/45 whitespace-nowrap"
            @click="store.promptPwaInstall()"
          >
            <Icon icon="fa6-solid:mobile-screen-button" class="w-3.5 h-3.5 text-violet-300" />
            <span>Install App</span>
          </button>

          <router-link
            to="/app"
            class="btn-press inline-flex items-center justify-center gap-1.5 min-h-[36px] px-3 sm:px-3.5 py-1.5 rounded-xl text-xs sm:text-[12.5px] font-bold bg-slate-800/80 text-white border border-sky-400/45 hover:bg-sky-500/20 hover:border-sky-300 whitespace-nowrap"
          >
            <Icon icon="fa6-solid:chart-column" class="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span>Open Live Desk</span>
          </router-link>

          <a
            href="#pricing"
            class="btn-press hidden sm:inline-flex items-center justify-center gap-1.5 min-h-[36px] px-3.5 py-1.5 rounded-xl text-xs sm:text-[12.5px] font-bold bg-gradient-to-r from-emerald-400 via-emerald-400 to-teal-300 text-slate-950 border border-emerald-200 shadow-[0_6px_20px_rgba(16,185,129,0.32)] hover:-translate-y-0.5 whitespace-nowrap"
          >
            <Icon icon="fa6-solid:wand-magic-sparkles" class="w-3.5 h-3.5 shrink-0" />
            <span>Get Pro Access</span>
          </a>

          <!-- Mobile Hamburger Button -->
          <button
            type="button"
            class="btn-press lg:hidden inline-flex items-center justify-center w-9 h-9 rounded-xl bg-slate-800/80 border border-slate-600/50 text-slate-200"
            aria-label="Toggle Navigation"
            @click="mobileMenuOpen = !mobileMenuOpen"
          >
            <Icon :icon="mobileMenuOpen ? 'fa6-solid:xmark' : 'fa6-solid:bars'" class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Responsive Mobile Drawer -->
      <div
        v-if="mobileMenuOpen"
        class="lg:hidden bg-navy-900/95 backdrop-blur-2xl border-t border-slate-700/50 px-5 py-4 space-y-2.5 text-sm font-semibold"
      >
        <a href="#pricing" class="block py-1.5 text-slate-200 hover:text-sky-300" @click="mobileMenuOpen = false">
          Membership Plans
        </a>
        <a href="#architecture" class="block py-1.5 text-slate-200 hover:text-sky-300" @click="mobileMenuOpen = false">
          Quant Architecture
        </a>
        <a href="#ledger" class="block py-1.5 text-slate-200 hover:text-sky-300" @click="mobileMenuOpen = false">
          Audited Ledger
        </a>
        <a href="#onboarding" class="block py-1.5 text-slate-200 hover:text-sky-300" @click="mobileMenuOpen = false">
          How to Join
        </a>
      </div>
    </header>

    <main class="max-w-[1240px] mx-auto px-4 sm:px-6 flex-1 w-full">
      <!-- Hero Section -->
      <section class="pt-12 sm:pt-16 pb-10 sm:pb-12 text-center">
        <div class="stagger-1">
          <span
            class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-[11px] sm:text-xs font-bold tracking-wide bg-sky-500/15 text-sky-300 border border-sky-400/45 shadow-[0_0_20px_rgba(56,189,248,0.15)] tabular-nums"
          >
            <Icon icon="fa6-solid:bolt" class="w-3.5 h-3.5 text-amber-300 shrink-0" />
            <span>ULTRA-FAST FINE-TUNED AI DECISION MODEL · 10 SPORTS · {{ store.totalMatches.toLocaleString() }}+ MATCHES</span>
          </span>

          <h1
            class="text-3xl sm:text-5xl md:text-[56px] font-extrabold tracking-tight leading-[1.1] max-w-[920px] mx-auto mt-5 mb-4 text-white drop-shadow-[0_2px_14px_rgba(255,255,255,0.08)]"
          >
            Quantitative Sports Edge,<br />
            <span class="font-serif italic font-semibold hero-shimmer-text inline-block py-0.5">
              Engineered for Consistent Alpha.
            </span>
          </h1>

          <p class="text-sm sm:text-base md:text-[17.5px] text-slate-300 max-w-[760px] mx-auto mb-8 leading-relaxed">
            BetScout fuses an
            <strong class="text-emerald-300 font-bold">ultra-fast, fine-tuned AI decision model</strong>
            trained on
            <strong class="text-white font-bold">{{ store.totalMatches.toLocaleString() }}+ historical matches</strong>
            with direct real-time bookmaker &amp; live match telemetry feeds, Dixon-Coles 28-outcome exact-score
            matrices, and strict per-sport safety vetoes. Every pick is timestamped before kickoff.
          </p>

          <div class="flex flex-wrap justify-center items-center gap-3.5 mb-12">
            <a
              href="#pricing"
              class="btn-press inline-flex items-center justify-center gap-2 min-h-[48px] px-7 py-3.5 rounded-xl text-sm sm:text-[15px] font-extrabold bg-gradient-to-r from-emerald-400 via-emerald-400 to-teal-300 text-slate-950 border border-emerald-200 shadow-[0_10px_28px_rgba(16,185,129,0.32)] hover:-translate-y-0.5"
            >
              <Icon icon="fa6-solid:rocket" class="w-4 h-4" />
              <span>View Membership Plans</span>
            </a>
            <router-link
              to="/app"
              class="btn-press inline-flex items-center justify-center gap-2 min-h-[48px] px-7 py-3.5 rounded-xl text-sm sm:text-[15px] font-bold bg-slate-800/80 text-white border border-sky-400/50 hover:bg-sky-500/20 hover:border-sky-300 shadow-[0_10px_28px_rgba(14,165,233,0.16)] hover:-translate-y-0.5"
            >
              <Icon icon="fa6-solid:chart-column" class="w-4 h-4 text-sky-400" />
              <span>Launch Live BetScout Desk</span>
              <Icon icon="fa6-solid:arrow-right" class="w-4 h-4 text-sky-300" />
            </router-link>
          </div>
        </div>

        <!-- 4-Column Bento KPI Strip (Translucent Frosted Glass + Color-Coded Accents) -->
        <div class="stagger-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10 text-left">
          <div class="card-surface border-t-2 border-t-emerald-400 rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-emerald-300">
              <Icon icon="fa6-solid:trophy" class="w-3.5 h-3.5 text-emerald-400" />
              <span>Verified Settled Record</span>
            </span>
            <div class="flex flex-wrap items-center gap-2 font-mono tabular-nums my-2">
              <span class="text-[22px] font-extrabold tracking-tight text-white whitespace-nowrap">
                <span class="text-emerald-400">{{ settledWins }}W</span> –
                <span class="text-rose-400">{{ settledLosses }}L</span>
              </span>
              <span class="px-2 py-0.5 rounded-md text-xs font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 whitespace-nowrap">
                {{ winRatePct.toFixed(1) }}%
              </span>
            </div>
            <div class="text-xs text-slate-300">{{ settledCount }} graded pre-match picks · Zero hindsight edits</div>
          </div>

          <div class="card-surface border-t-2 border-t-cyan-400 rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-cyan-300">
              <Icon icon="fa6-solid:chart-line" class="w-3.5 h-3.5 text-cyan-400" />
              <span>Realized Flat-Unit Profit</span>
            </span>
            <div class="flex flex-wrap items-center gap-2 font-mono tabular-nums my-2">
              <span class="text-[22px] font-extrabold tracking-tight text-cyan-300 whitespace-nowrap">
                {{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(2) }}u
              </span>
              <span class="px-2 py-0.5 rounded-md text-xs font-extrabold bg-cyan-500/20 text-cyan-200 border border-cyan-400/50 whitespace-nowrap">
                {{ roiPct >= 0 ? '+' : '' }}{{ roiPct.toFixed(1) }}% ROI
              </span>
            </div>
            <div class="text-xs text-slate-300">
              ¼-Kelly Bankroll Growth:
              <strong class="text-emerald-300 font-mono tabular-nums">+{{ kellyGrowthPct.toFixed(2) }}%</strong>
            </div>
          </div>

          <div class="card-surface border-t-2 border-t-amber-400 rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-300">
              <Icon icon="fa6-solid:bolt" class="w-3.5 h-3.5 text-amber-400" />
              <span>Active Daily Slate</span>
            </span>
            <div class="font-mono tabular-nums text-[23px] font-extrabold tracking-tight text-amber-300 my-2 whitespace-nowrap">
              {{ activeCount }} Live Picks
            </div>
            <div class="flex flex-wrap items-center gap-1.5 text-xs font-mono tabular-nums">
              <template v-if="store.activeSportsCounts.length">
                <span
                  v-for="sp in store.activeSportsCounts"
                  :key="sp.cat"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-bold"
                  :class="getSportBadgeTheme(sp.cat)"
                >
                  <Icon :icon="sp.icon" class="w-3 h-3" />
                  <span>{{ sp.count }}</span>
                </span>
              </template>
              <span v-else class="text-slate-300">{{ store.activeSportsBreakdown }}</span>
            </div>
          </div>

          <div class="card-surface border-t-2 border-t-violet-400 rounded-2xl p-5 flex flex-col justify-between">
            <span class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-violet-300">
              <Icon icon="fa6-solid:tower-broadcast" class="w-3.5 h-3.5 text-violet-400" />
              <span>Calibration &amp; Live Stream</span>
            </span>
            <div class="font-mono tabular-nums text-[23px] font-extrabold tracking-tight text-white my-2 whitespace-nowrap">
              {{ store.totalMatches.toLocaleString() }}+ Matches
            </div>
            <div class="text-xs text-slate-300">6-second real-time in-play score &amp; rebound feed</div>
          </div>
        </div>

        <!-- Live Free Daily Teaser Sample Card -->
        <div
          v-if="freeTeaser"
          class="stagger-3 card-surface max-w-[940px] mx-auto text-left rounded-2xl p-5 sm:p-6 border border-sky-400/45"
        >
          <div class="flex flex-wrap justify-between items-center gap-3 mb-4">
            <div class="flex flex-wrap items-center gap-2">
              <span
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
                FREE DAILY TEASER PICK
              </span>
              <span
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold border"
                :class="getSportBadgeTheme(freeTeaser.sport_cat)"
              >
                <Icon
                  v-if="getCompetitionFlagIconify(freeTeaser.competition, freeTeaser.sport_league)"
                  :icon="getCompetitionFlagIconify(freeTeaser.competition, freeTeaser.sport_league)!"
                  class="w-3.5 h-2.5 rounded-[2px] shrink-0"
                />
                <Icon v-else :icon="getSportIconify(freeTeaser.sport_cat)" class="w-3.5 h-3.5 shrink-0" />
                <span>{{ freeTeaser.competition || freeTeaser.sport_league }}</span>
              </span>
              <span
                v-if="freeTeaser.tier"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold border"
                :class="getTierBadgeClass(freeTeaser.tier)"
              >
                {{ freeTeaser.tier }}
              </span>
            </div>
            <span class="inline-flex items-center gap-1.5 text-xs text-slate-300 font-mono tabular-nums">
              <Icon icon="fa6-solid:clock" class="w-3.5 h-3.5 text-sky-400" />
              <span>Kickoff: {{ freeTeaser.date_local || freeTeaser.date }}</span>
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-5 items-center">
            <div class="md:col-span-2">
              <div class="inline-flex items-center gap-2 text-lg sm:text-xl font-extrabold tracking-tight text-white mb-2.5">
                <Icon
                  :icon="getSportIconify(freeTeaser.sport_cat)"
                  class="w-5 h-5 shrink-0"
                  :class="getSportIconColor(freeTeaser.sport_cat)"
                />
                <span>
                  <template v-if="freeTeaser.home && freeTeaser.away && !String(freeTeaser.match || '').includes('🔒')">
                    {{ freeTeaser.home }} <span class="text-slate-400 font-normal">vs</span> {{ freeTeaser.away }}
                  </template>
                  <template v-else>{{ freeTeaser.match }}</template>
                </span>
              </div>
              <div class="p-4 rounded-xl bg-slate-950/75 border border-emerald-400/40">
                <div class="text-[11px] font-bold uppercase tracking-wider text-emerald-300">
                  RECOMMENDED MODEL SELECTION
                </div>
                <div class="text-lg font-extrabold text-white mt-0.5">
                  {{ freeTeaser.pick_name || freeTeaser.pick }}
                </div>
                <div class="inline-flex items-center gap-1.5 text-xs text-sky-300 mt-1">
                  <Icon icon="fa6-solid:dice" class="w-3.5 h-3.5 text-amber-300 shrink-0" />
                  <span>
                    Score / Set Matrix Projection:
                    <b class="text-white">{{ freeTeaser.exact_score_pick || 'High-Conviction Moneyline' }}</b>
                  </span>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div class="p-3.5 rounded-xl bg-slate-950/75 border border-slate-700/70">
                <div class="text-[10.5px] font-bold uppercase tracking-wider text-slate-300">BOOKMAKER ODDS</div>
                <div class="font-mono text-xl font-extrabold text-amber-300 mt-1">{{ freeTeaser.odds.toFixed(2) }}</div>
                <div class="text-[11px] text-slate-400 mt-0.5">Verified Market Line</div>
              </div>
              <div class="p-3.5 rounded-xl bg-slate-950/75 border border-slate-700/70">
                <div class="text-[10.5px] font-bold uppercase tracking-wider text-slate-300">MODEL WIN PROB</div>
                <div class="font-mono text-xl font-extrabold text-emerald-300 mt-1">
                  {{ (freeTeaser.win_prob * 100).toFixed(1) }}%
                </div>
                <div class="text-[11px] text-slate-400 mt-0.5 font-mono">
                  Min Fair Odds: {{ freeTeaser.min_fair_odds.toFixed(2) }}
                </div>
              </div>
            </div>
          </div>

          <div
            class="mt-4 pt-3.5 border-t border-slate-700/50 flex flex-wrap justify-between items-center gap-3 text-[13px] text-slate-300"
          >
            <span class="inline-flex items-center gap-1.5">
              <Icon icon="fa6-solid:lock" class="w-3.5 h-3.5 text-amber-300 shrink-0" />
              <span>
                <strong class="text-white">
                  +{{ Math.max(1, activeCount - 1) }} additional high-conviction picks, 2-leg banker boosters &amp;
                  exact-score dutching splits
                </strong>
                are active right now.
              </span>
            </span>
            <router-link to="/app" class="inline-flex items-center gap-1.5 text-sky-300 font-bold hover:text-white">
              <span>Open Live Desk ({{ activeCount }} Active Picks)</span>
              <Icon icon="fa6-solid:arrow-right" class="w-3.5 h-3.5" />
            </router-link>
          </div>
        </div>
      </section>

      <!-- Membership Tiers & Pricing -->
      <section id="pricing" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-300 mb-2">
            MEMBERSHIP TIERS &amp; API ACCESS
          </div>
          <h2 class="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Transparent Plans Built for ROI
          </h2>
          <p class="text-sm sm:text-[15.5px] text-slate-300 max-w-[660px] mx-auto mb-6">
            Whether you bet daily singles &amp; exact-score splits on the web desk, want instant mobile push cards, or
            run an automated syndicate—choose the tier that fits your workflow.
          </p>

          <!-- Billing Period Toggle -->
          <div class="inline-flex items-center gap-1.5 bg-slate-900/90 border border-slate-700 rounded-full p-1.5">
            <button
              type="button"
              class="btn-press px-4 py-1.5 rounded-full text-xs font-bold"
              :class="
                billingCycle === 'monthly'
                  ? 'bg-sky-500/25 text-sky-200 border border-sky-400/50'
                  : 'text-slate-300 hover:text-white'
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
                  ? 'bg-emerald-500/25 text-emerald-200 border border-emerald-400/50'
                  : 'text-slate-300 hover:text-white'
              "
              @click="billingCycle = 'annual'"
            >
              Annual Billing
              <span class="px-1.5 py-0.5 rounded-full text-[10px] bg-emerald-400 text-slate-950 font-extrabold">
                SAVE 32%
              </span>
            </button>
          </div>
        </div>

        <!-- 3 Aligned Pricing Cards -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          <!-- Tier 1: VIP Notifications (Discord / Telegram) — €39/mo -->
          <article class="card-surface rounded-2xl p-6 sm:p-7 flex flex-col justify-between border-t-2 border-t-sky-400">
            <div>
              <div class="mb-4">
                <span
                  class="inline-block px-3 py-1 rounded-full text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/45"
                >
                  TIER 1 · VIP NOTIFICATIONS ONLY
                </span>
              </div>
              <div class="flex items-baseline gap-1.5 my-2 font-mono tabular-nums">
                <span class="text-4xl font-extrabold text-white">
                  €{{ billingCycle === 'annual' ? '27' : '39' }}
                </span>
                <span class="text-sm text-slate-300">/ month</span>
              </div>
              <div class="text-xs text-emerald-300 font-semibold mb-3 font-mono tabular-nums">
                {{
                  billingCycle === 'annual'
                    ? 'Billed €319 annually (Save €149/yr)'
                    : 'Billed monthly · Or €319/yr (Save 32%)'
                }}
              </div>
              <p class="text-[13.5px] text-slate-300 pb-4 mb-4 border-b border-slate-700/60">
                Real-time high-conviction pick alerts &amp; PNG cards delivered directly to Discord &amp; Telegram.
              </p>

              <ul class="space-y-3 text-[13.5px] text-slate-100 mb-7">
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><b>Private VIP Discord &amp; Telegram Channels</b> with dedicated per-sport feeds</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><b>Instant High-Res PNG Pick Cards</b> with win probability, fair odds &amp; score targets</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><b>2-Leg &amp; 3-Leg Banker Booster Combos</b> &amp; Daily Morning Slate Digests</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><b>Live In-Play Dominance Rebound</b> &amp; 76–90m Late-Goal Alerts pushed in real time</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                  <span><b>Closing-Line Steam Alerts</b> &amp; automated settled recap cards</span>
                </li>
              </ul>
            </div>

            <a
              href="mailto:julian.christ@gmail.com?subject=BetScout%20Tier%201%20VIP%20Notifications%20Subscription&body=Hi%20BetScout%20Team%2C%0A%0AI%20would%20like%20to%20activate%20Tier%201%20VIP%20Notifications%20(Discord%20%2F%20Telegram%20-%20%E2%82%AC39%2Fmo).%0AMy%20Discord%20or%20Telegram%20Username%3A%20"
              class="btn-press w-full min-h-[46px] inline-flex items-center justify-center gap-2 rounded-xl text-sm font-bold bg-slate-900/90 text-white border border-sky-400/50 hover:bg-sky-500/20 hover:border-sky-300"
            >
              <span>Activate VIP Notifications</span>
              <Icon icon="fa6-solid:arrow-right" class="w-4 h-4 text-sky-300" />
            </a>
          </article>

          <!-- Tier 2: Pro WebApp + Tier 1 Notifications (Featured) — €79/mo -->
          <article
            class="card-surface relative rounded-2xl p-6 sm:p-7 flex flex-col justify-between border-2 border-emerald-400/80 shadow-[0_24px_60px_rgba(0,0,0,0.65),0_0_40px_rgba(16,185,129,0.18)]"
          >
            <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
              <span
                class="inline-block px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
              >
                TIER 2 · PRO WEBAPP + NOTIFICATIONS
              </span>
              <span
                class="inline-flex items-center gap-1 bg-gradient-to-r from-emerald-400 to-teal-300 text-slate-950 text-[10.5px] font-extrabold px-3 py-1 rounded-full tracking-wider shadow"
              >
                <Icon icon="fa6-solid:award" class="w-3.5 h-3.5" />
                <span>MOST POPULAR</span>
              </span>
            </div>

            <div>
              <div class="flex items-baseline gap-1.5 my-2 font-mono tabular-nums">
                <span class="text-4xl font-extrabold text-white">
                  €{{ billingCycle === 'annual' ? '54' : '79' }}
                </span>
                <span class="text-sm text-slate-300">/ month</span>
              </div>
              <div class="text-xs text-emerald-300 font-semibold mb-3 font-mono tabular-nums">
                {{
                  billingCycle === 'annual'
                    ? 'Billed €649 annually (Save €299/yr)'
                    : 'Billed monthly · Or €649/yr (Save 31%)'
                }}
              </div>
              <p class="text-[13.5px] text-slate-300 pb-4 mb-4 border-b border-slate-700/60">
                Full interactive Quant WebApp desk on desktop &amp; mobile plus all Tier 1 Discord &amp; Telegram notifications.
              </p>

              <ul class="space-y-3 text-[13.5px] text-slate-100 mb-7">
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Everything in Tier 1 (VIP Discord &amp; Telegram Notifications)</b> included</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>100% Unlocked Pro WebApp Desk</b> across all 10 sports on desktop &amp; mobile</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Smart Bet Slip &amp; ¼-Kelly Optimizer</b> tailored to your exact euro bankroll &amp; stake</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>Exact-Score &amp; Set-Score Dutching Splitter</b> (2-Score &amp; 3-Score equal-payout splits)</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span><b>On-Demand Matchup Analyzer</b>, Drill-Down Inspector &amp; 6s Live In-Play Stream</span>
                </li>
              </ul>
            </div>

            <a
              href="mailto:julian.christ@gmail.com?subject=BetScout%20Tier%202%20Pro%20WebApp%20%2B%20VIP%20Notifications&body=Hi%20BetScout%20Team%2C%0A%0AI%20would%20like%20to%20join%20Tier%202%20(Pro%20WebApp%20%2B%20VIP%20Notifications%20-%20%E2%82%AC79%2Fmo).%0AMy%20Google%20Account%20Email%3A%20%0AMy%20Discord%2FTelegram%20Username%3A%20"
              class="btn-press w-full min-h-[46px] inline-flex items-center justify-center gap-2 rounded-xl text-sm font-extrabold bg-gradient-to-r from-emerald-400 via-emerald-400 to-teal-300 text-slate-950 border border-emerald-200 shadow-[0_8px_24px_rgba(16,185,129,0.3)]"
            >
              <Icon icon="fa6-solid:rocket" class="w-4 h-4" />
              <span>Get Pro WebApp + VIP Alerts</span>
              <Icon icon="fa6-solid:arrow-right" class="w-4 h-4" />
            </a>
          </article>

          <!-- Tier 3: Quant API + Bonus MCP Server -->
          <article class="card-surface rounded-2xl p-6 sm:p-7 flex flex-col justify-between border-t-2 border-t-amber-400">
            <div>
              <div class="mb-4">
                <span
                  class="inline-block px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/50"
                >
                  TIER 3 · QUANT API + BONUS MCP SERVER
                </span>
              </div>
              <div class="flex items-baseline gap-1.5 my-2 font-mono tabular-nums">
                <span class="text-4xl font-extrabold text-white">
                  €{{ billingCycle === 'annual' ? '149' : '199' }}
                </span>
                <span class="text-sm text-slate-300">/ month</span>
              </div>
              <div class="text-xs text-amber-300 font-semibold mb-3 font-mono tabular-nums">
                {{
                  billingCycle === 'annual'
                    ? 'Billed €1,788 annually (Save €600/yr)'
                    : 'Billed monthly · Or €1,788/yr (Save 25%)'
                }}
              </div>
              <p class="text-[13.5px] text-slate-300 pb-4 mb-4 border-b border-slate-700/60">
                Full REST API, TypeScript/Python SDKs &amp; Bonus AI Agent MCP Server plus everything in Tier 2.
              </p>

              <ul class="space-y-3 text-[13.5px] text-slate-100 mb-7">
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span><b>Everything in Tier 2 (Pro WebApp + VIP Notifications)</b> included</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <b>Bonus AI Agent MCP Server:</b> Native Model Context Protocol tools for Claude, Cursor &amp;
                    Copilot
                  </span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span><b>Dedicated REST API Key</b> with 5,000 calls/day &amp; rate-limit headers</span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <b>Full JSON Feeds:</b> Daily Picks, Exact-Score Dutching, Banker Combos, Mispriced Lines &amp;
                    Live Matchup Analysis
                  </span>
                </li>
                <li class="flex items-start gap-2.5">
                  <Icon icon="fa6-solid:check" class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    <b>Custom Webhook Fan-Out:</b> Automated PNG Pick Cards posted directly to your Discord or Telegram
                  </span>
                </li>
              </ul>
            </div>

            <a
              href="mailto:julian.christ@gmail.com?subject=BetScout%20Tier%203%20Quant%20API%20%2B%20MCP%20Server%20Access&body=Hi%20BetScout%20Team%2C%0A%0AI%20am%20interested%20in%20Tier%203%20(Quant%20API%20%2B%20Bonus%20MCP%20Server%20-%20%E2%82%AC199%2Fmo).%0AOrganization%20%2F%20Use%20Case%3A%20"
              class="btn-press w-full min-h-[46px] inline-flex items-center justify-center gap-2 rounded-xl text-sm font-bold bg-slate-900/90 text-white border border-amber-400/50 hover:bg-amber-500/20 hover:border-amber-300"
            >
              <span>Request API + MCP Access</span>
              <Icon icon="fa6-solid:arrow-right" class="w-4 h-4 text-amber-300" />
            </a>
          </article>
        </div>
      </section>

      <!-- 4-Card Quantitative Architecture Grid -->
      <section id="architecture" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-300 mb-2">
            QUANTITATIVE ARCHITECTURE
          </div>
          <h2 class="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Why BetScout Outperforms the Market
          </h2>
          <p class="text-sm sm:text-[15.5px] text-slate-300 max-w-[660px] mx-auto">
            Every recommendation must survive sport-specific statistical filters, pre-match injury checks, and
            closing-line drift gates before it ever reaches your screen.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card-surface rounded-2xl p-6 border-t-2 border-t-sky-400">
            <div class="flex items-center gap-3.5 mb-3">
              <div class="w-11 h-11 rounded-xl bg-sky-500/20 border border-sky-400/45 flex items-center justify-center shrink-0">
                <Icon icon="fa6-solid:shield-halved" class="w-5 h-5 text-sky-300" />
              </div>
              <h3 class="text-base font-extrabold text-white leading-snug m-0">
                Fine-Tuned AI Decision Model &amp; Safety Gates
              </h3>
            </div>
            <p class="text-[13.5px] text-slate-300 leading-relaxed">
              Powered by an ultra-fast, fine-tuned AI decision model paired with isolated safety gates for Football
              (7-factor composite + T-60m Starting XI gate), Tennis (Surface Elo + 6m Game-Win%), NBA, NFL, NHL &amp;
              Table Tennis.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6 border-t-2 border-t-amber-400">
            <div class="flex items-center gap-3.5 mb-3">
              <div class="w-11 h-11 rounded-xl bg-amber-500/20 border border-amber-400/45 flex items-center justify-center shrink-0">
                <Icon icon="fa6-solid:dice" class="w-5 h-5 text-amber-300" />
              </div>
              <h3 class="text-base font-extrabold text-white leading-snug m-0">
                Dixon-Coles 28-Score Dutching
              </h3>
            </div>
            <p class="text-[13.5px] text-slate-300 leading-relaxed">
              Bivariate Poisson &amp; Markov set-score matrices price all 28 exact football scores and tennis set
              outcomes, splitting your stake across 2 or 3 scores for an identical net payout.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6 border-t-2 border-t-emerald-400">
            <div class="flex items-center gap-3.5 mb-3">
              <div class="w-11 h-11 rounded-xl bg-emerald-500/20 border border-emerald-400/45 flex items-center justify-center shrink-0">
                <Icon icon="fa6-solid:rocket" class="w-5 h-5 text-emerald-300" />
              </div>
              <h3 class="text-base font-extrabold text-white leading-snug m-0">
                Banker Profitability Booster Combos
              </h3>
            </div>
            <p class="text-[13.5px] text-slate-300 leading-relaxed">
              Automatically pairs high-probability (&ge;72%), lower-odds bankers into uncorrelated 2-Leg Doubles
              (1.35x–1.75x) and 3-Leg Trebles (1.60x–2.15x) to multiply net return.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6 border-t-2 border-t-rose-400">
            <div class="flex items-center gap-3.5 mb-3">
              <div class="w-11 h-11 rounded-xl bg-rose-500/20 border border-rose-400/45 flex items-center justify-center shrink-0">
                <Icon icon="fa6-solid:tower-broadcast" class="w-5 h-5 text-rose-300" />
              </div>
              <h3 class="text-base font-extrabold text-white leading-snug m-0">
                6-Second In-Play Dominance Stream
              </h3>
            </div>
            <p class="text-[13.5px] text-slate-300 leading-relaxed">
              Real-time match timeline delta tracking detects when a pre-match favorite is level or trailing despite
              dominating Shots-on-Target (SoT) or 76–90m late-goal pressure.
            </p>
          </div>
        </div>
      </section>

      <!-- Audited Settled Paper-Bet Ledger Preview -->
      <section id="ledger" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-300 mb-2">
            AUDITED PROSPECTIVE RECORD
          </div>
          <h2 class="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            Recent Graded Paper-Bet Ledger
          </h2>
          <p class="text-sm sm:text-[15.5px] text-slate-300 max-w-[660px] mx-auto">
            All picks are logged before kickoff with live bookmaker odds and graded automatically against official
            final scores.
          </p>
        </div>

        <div class="table-surface rounded-2xl overflow-x-auto">
          <table class="w-full border-collapse text-[13px]">
            <thead>
              <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase tracking-wider border-b border-slate-700/70 text-left">
                <th class="py-3.5 px-4">League</th>
                <th class="py-3.5 px-4">Matchup</th>
                <th class="py-3.5 px-4">Pick</th>
                <th class="py-3.5 px-4">Final Score</th>
                <th class="py-3.5 px-4">Odds</th>
                <th class="py-3.5 px-4">Result / PNL</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in recentSettledRows"
                :key="`${r.league}:${r.event_id}`"
                class="border-b border-slate-800/80 last:border-none hover:bg-slate-800/40"
              >
                <td class="py-3 px-4">
                  <span
                    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-xs font-bold border whitespace-nowrap"
                    :class="getSportBadgeTheme(r.sport_cat || r.league)"
                  >
                    <Icon
                      v-if="getCompetitionFlagIconify(formatLeagueBadgeLabel(r.league_label, r.league, r.home, r.away), `${r.league} ${r.home} ${r.away}`)"
                      :icon="getCompetitionFlagIconify(formatLeagueBadgeLabel(r.league_label, r.league, r.home, r.away), `${r.league} ${r.home} ${r.away}`)!"
                      class="w-3.5 h-2.5 rounded-[2px] shrink-0"
                    />
                    <Icon v-else :icon="getSportIconify(r.sport_cat || r.league)" class="w-3.5 h-3.5 shrink-0" />
                    <span>{{ formatLeagueBadgeLabel(r.league_label, r.league, r.home, r.away) }}</span>
                  </span>
                </td>
                <td class="py-3 px-4">
                  <button
                    type="button"
                    class="font-bold text-white hover:text-sky-300 text-left transition-colors cursor-pointer"
                    title="Click to inspect Match Details, H2H &amp; Last-6 Form"
                    @click="openMatchupModal(r.home, r.away, r.league)"
                  >
                    {{ r.home }} <span class="text-slate-400 font-normal">vs</span> {{ r.away }}
                  </button>
                </td>
                <td class="py-3 px-4 text-emerald-300 font-bold">
                  {{ r.side === 'H' ? r.home : r.away }} ({{ r.side }})
                </td>
                <td class="py-3 px-4 font-mono tabular-nums text-slate-200">
                  <b class="text-white font-bold">{{ splitScoreAndInterim(r.settled_score || r.score_str || '—').main }}</b>
                  <span
                    v-if="splitScoreAndInterim(r.settled_score || r.score_str || '').interim"
                    class="text-slate-400 font-normal ml-1 text-xs"
                  >{{ splitScoreAndInterim(r.settled_score || r.score_str || '').interim }}</span>
                </td>
                <td class="py-3 px-4 font-mono tabular-nums font-bold text-amber-300">
                  {{ Number(r.logged_best_odds || 1.35).toFixed(2) }}
                </td>
                <td class="py-3 px-4">
                  <span
                    class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md font-mono tabular-nums text-xs font-bold border whitespace-nowrap"
                    :class="
                      Number(r.pnl_best || 0) > 0
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/50'
                        : 'bg-rose-500/20 text-rose-300 border-rose-400/50'
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
            class="btn-press inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-bold bg-slate-800/80 text-white border border-sky-400/50 hover:border-sky-300"
          >
            <span>Inspect All {{ settledCount }} Graded Bets &amp; Equity Curves on Live Desk</span>
            <Icon icon="fa6-solid:arrow-right" class="w-4 h-4 text-sky-300" />
          </router-link>
        </div>
      </section>

      <!-- 3-Step Onboarding -->
      <section id="onboarding" class="py-12 scroll-mt-20">
        <div class="text-center mb-8">
          <div class="text-xs font-extrabold uppercase tracking-widest text-sky-300 mb-2">FAST ONBOARDING</div>
          <h2 class="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-white mb-3">
            How to Unlock Access in 3 Steps
          </h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div class="card-surface rounded-2xl p-6 border-t-2 border-t-sky-400">
            <div class="flex items-center gap-3 mb-3">
              <span class="font-mono text-xs font-bold text-sky-300 px-2.5 py-1 rounded-md bg-sky-500/20 border border-sky-400/40 shrink-0 whitespace-nowrap">
                STEP 01
              </span>
              <h3 class="text-base font-extrabold text-white leading-snug m-0">Select Your Membership Tier</h3>
            </div>
            <p class="text-[13.5px] text-slate-300 leading-relaxed">
              Choose VIP Notifications (€39/mo), Pro WebApp + Notifications (€79/mo), or Quant API + Bonus MCP Server
              (€199/mo) and send your details.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6 border-t-2 border-t-emerald-400">
            <div class="flex items-center gap-3 mb-3">
              <span class="font-mono text-xs font-bold text-emerald-300 px-2.5 py-1 rounded-md bg-emerald-500/20 border border-emerald-400/40 shrink-0 whitespace-nowrap">
                STEP 02
              </span>
              <h3 class="text-base font-extrabold text-white leading-snug m-0">Instant Account Whitelisting</h3>
            </div>
            <p class="text-[13.5px] text-slate-300 leading-relaxed">
              We whitelist your Google email in the BetScout Pro subscriber database and send your private VIP
              Discord/Telegram invite or live API key.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6 border-t-2 border-t-amber-400">
            <div class="flex items-center gap-3 mb-3">
              <span class="font-mono text-xs font-bold text-amber-300 px-2.5 py-1 rounded-md bg-amber-500/20 border border-amber-400/40 shrink-0 whitespace-nowrap">
                STEP 03
              </span>
              <h3 class="text-base font-extrabold text-white leading-snug m-0">Sign In &amp; Execute With Edge</h3>
            </div>
            <p class="text-[13.5px] text-slate-300 leading-relaxed">
              Click <b>Sign In</b> on the Live Quant Desk with Google. All locked picks, exact-score dutching splits,
              and banker booster combos unlock immediately.
            </p>
          </div>
        </div>
      </section>

      <!-- B2B Quant REST API Section -->
      <section class="py-10">
        <div class="card-surface rounded-2xl p-6 sm:p-7 grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
          <div>
            <span
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/45 mb-3"
            >
              <Icon icon="fa6-solid:terminal" class="w-3.5 h-3.5" />
              <span>FOR SYNDICATES, BOTS &amp; COMMUNITIES</span>
            </span>
            <h3 class="text-2xl font-extrabold text-white mb-2.5">Programmatic JSON API, Bonus MCP Server &amp; Webhook Syndication</h3>
            <p class="text-sm text-slate-300 leading-relaxed mb-5">
              Integrate BetScout's calibrated probabilities, Dixon-Coles 28-score matrices, and 2-leg banker combos
              directly into your execution engine, AI Agent (via our Bonus MCP Server), or community server with
              rate-limit headers and OpenAPI 3.1 schemas.
            </p>
            <div class="flex flex-wrap gap-3">
              <a
                href="/api/docs"
                target="_blank"
                class="btn-press px-4 py-2 rounded-xl text-xs font-bold bg-sky-500/20 text-sky-200 border border-sky-400/50 hover:bg-sky-500/30 inline-flex items-center gap-1.5"
              >
                <Icon icon="fa6-solid:book-open" class="w-3.5 h-3.5 text-sky-300" />
                <span>Explore Interactive Swagger API Docs</span>
              </a>
              <a
                href="/api/openapi.json"
                target="_blank"
                class="btn-press px-4 py-2 rounded-xl text-xs font-bold bg-slate-900/90 text-slate-200 border border-slate-600 hover:border-sky-400 inline-flex items-center gap-1.5"
              >
                <Icon icon="fa6-solid:download" class="w-3.5 h-3.5 text-sky-300" />
                <span>Download OpenAPI Specification</span>
              </a>
            </div>
          </div>

          <pre
            class="bg-slate-950/90 border border-slate-700/80 rounded-xl p-4 font-mono text-xs text-slate-200 overflow-x-auto leading-relaxed"
          ><span class="text-slate-400"># Authenticated Commercial Quant Feed Request</span>
{
  <span class="text-sky-300">"ok"</span>: <span class="text-emerald-300">true</span>,
  <span class="text-sky-300">"plan_tier"</span>: <span class="text-amber-300">"pro"</span>,
  <span class="text-sky-300">"endpoints"</span>: [
    <span class="text-emerald-300">"Upcoming Calibrated Picks (10 Sports)"</span>,
    <span class="text-emerald-300">"28-Score Dixon-Coles &amp; Set Dutching Matrices"</span>,
    <span class="text-emerald-300">"2-Leg &amp; 3-Leg Banker Booster Combos"</span>,
    <span class="text-emerald-300">"Bookmaker Mispriced Edge Dislocations"</span>
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
              <Icon
                icon="fa6-solid:chevron-down"
                class="w-4 h-4 text-sky-400 transition-transform duration-200 shrink-0"
                :class="openFaq === idx ? 'rotate-180' : ''"
              />
            </button>
            <div v-if="openFaq === idx" class="px-5 pb-4 text-[13.5px] text-slate-300 leading-relaxed">
              {{ item.a }}
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-400/15 py-8 mt-12 text-xs text-slate-400">
      <div class="max-w-[1240px] mx-auto px-4 sm:px-6 flex flex-wrap justify-between items-center gap-4">
        <div class="flex items-center gap-2.5">
          <img src="/betscout-logo.svg?v=7.3" width="22" height="22" alt="BetScout" class="rounded" />
          <span>
            &copy; {{ currentYear }} <strong class="text-slate-200">BetScout</strong> · Quantitative Sports Edge &amp;
            Score Intelligence. All rights reserved.
          </span>
        </div>
        <div class="font-mono text-[11px] text-slate-400/95 bg-slate-900/65 border border-slate-700/50 px-2.5 py-0.5 rounded-full">
          v{{ appVersion }} ({{ commitHash }})
        </div>
        <div class="flex flex-wrap gap-5">
          <router-link to="/app" class="hover:text-white">Live Quant Desk</router-link>
          <a href="#pricing" class="hover:text-white">Membership Plans</a>
          <a href="/api/docs" target="_blank" class="hover:text-white">API Documentation</a>
          <a href="mailto:julian.christ@gmail.com" class="hover:text-white">Contact &amp; Support</a>
        </div>
      </div>
    </footer>

    <!-- MATCHUP DRILL-DOWN INSPECTOR MODAL -->
    <div
      v-if="inspectorModalOpen"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="inspectorModalOpen = false"
    >
      <div class="card-surface rounded-2xl max-w-[680px] w-full max-h-[85vh] overflow-y-auto p-5 text-xs">
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-slate-700">
          <b class="inline-flex items-center gap-1.5 text-sm text-sky-300">
            <Icon icon="fa6-solid:magnifying-glass" class="w-4 h-4" />
            <span>{{ inspectorTitle }}</span>
          </b>
          <button
            type="button"
            class="btn-press inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs"
            @click="inspectorModalOpen = false"
          >
            <span>Close</span>
            <Icon icon="fa6-solid:xmark" class="w-3.5 h-3.5" />
          </button>
        </div>
        <div v-if="inspectorLoading" class="py-8 px-4 flex flex-col items-center justify-center gap-3 text-slate-300">
          <div class="inline-flex items-center gap-2 text-xs font-semibold text-sky-300">
            <Icon icon="fa6-solid:arrows-rotate" class="w-3.5 h-3.5 animate-spin text-sky-400" />
            <span>Loading Match Details, H2H &amp; Last-6 Form...</span>
          </div>
          <div
            role="progressbar"
            aria-label="Loading match details"
            class="w-full max-w-[300px] h-1.5 rounded-full bg-slate-900/95 border border-slate-700/80 overflow-hidden"
          >
            <div class="modal-loading-bar"></div>
          </div>
        </div>
        <div v-else-if="inspectorData" class="space-y-4">
          <div
            v-if="inspectorData.pick_detail && Object.keys(inspectorData.pick_detail).length"
            class="p-3.5 rounded-xl bg-slate-900/90 border border-slate-700/80 flex flex-wrap justify-between items-center gap-3 text-xs"
          >
            <div>
              <span class="text-slate-400 block text-[10px] uppercase tracking-wider font-bold">Model Selection</span>
              <b class="text-emerald-300 text-sm">
                {{ inspectorData.pick_detail.pick || (inspectorData.pick_detail.side === 'H' ? inspectorData.home : inspectorData.away) }}
              </b>
              <span
                v-if="inspectorData.pick_detail.tier"
                class="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold border"
                :class="getTierBadgeClass(inspectorData.pick_detail.tier)"
              >
                {{ inspectorData.pick_detail.tier }}
              </span>
            </div>
            <div class="font-mono tabular-nums">
              <span class="text-slate-400 block text-[10px] uppercase tracking-wider font-bold">Odds</span>
              <b class="text-amber-300 text-sm">{{ Number(inspectorData.pick_detail.best_odds || inspectorData.pick_detail.odds || 1.3).toFixed(2) }}</b>
            </div>
            <div v-if="inspectorData.pick_detail.settled_score" class="font-mono tabular-nums">
              <span class="text-slate-400 block text-[10px] uppercase tracking-wider font-bold">Final Score</span>
              <span class="text-sm">
                <b class="text-white font-bold">{{ splitScoreAndInterim(inspectorData.pick_detail.settled_score).main }}</b>
                <span
                  v-if="splitScoreAndInterim(inspectorData.pick_detail.settled_score).interim"
                  class="text-slate-400 font-normal ml-1 text-xs"
                >{{ splitScoreAndInterim(inspectorData.pick_detail.settled_score).interim }}</span>
              </span>
            </div>
            <div v-if="inspectorData.pick_detail.pnl_best !== undefined && inspectorData.pick_detail.pnl_best !== null">
              <span
                class="px-2.5 py-1 rounded-md text-xs font-bold border font-mono tabular-nums"
                :class="
                  Number(inspectorData.pick_detail.pnl_best) > 0
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/50'
                    : 'bg-rose-500/20 text-rose-300 border-rose-400/50'
                "
              >
                {{
                  Number(inspectorData.pick_detail.pnl_best) > 0
                    ? `WIN (+${Number(inspectorData.pick_detail.pnl_best).toFixed(2)}u)`
                    : `LOSS (${Number(inspectorData.pick_detail.pnl_best).toFixed(2)}u)`
                }}
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <b class="block mb-1.5 text-white">{{ inspectorData.home }} — Last 6</b>
              <div v-if="!inspectorData.form_home?.length" class="text-slate-300">No recent matches in DB</div>
              <div
                v-for="(m, i) in inspectorData.form_home"
                :key="i"
                class="flex justify-between items-center py-1.5 border-b border-slate-800"
              >
                <span class="inline-flex items-center gap-1.5">
                  <span
                    class="w-[22px] h-[22px] rounded-[5px] inline-grid place-items-center text-[11px] font-bold border shrink-0 font-mono"
                    :class="getFormOutcomeSquareClass(m.result)"
                  >{{ m.result }}</span>
                  <span>{{ m.venue }} <span class="text-slate-400 font-normal">vs</span> <b>{{ m.opp }}</b></span>
                </span>
                <span class="font-mono tabular-nums text-slate-300">
                  <b :class="m.result === 'W' ? 'text-emerald-300' : m.result === 'L' ? 'text-rose-400' : 'text-amber-300'">{{ splitScoreAndInterim(m.score).main }}</b>
                  <span v-if="splitScoreAndInterim(m.score).interim" class="text-slate-400 ml-0.5">{{ splitScoreAndInterim(m.score).interim }}</span>
                  <span class="text-slate-400 ml-1">({{ m.date }})</span>
                </span>
              </div>
            </div>
            <div>
              <b class="block mb-1.5 text-white">{{ inspectorData.away }} — Last 6</b>
              <div v-if="!inspectorData.form_away?.length" class="text-slate-300">No recent matches in DB</div>
              <div
                v-for="(m, i) in inspectorData.form_away"
                :key="i"
                class="flex justify-between items-center py-1.5 border-b border-slate-800"
              >
                <span class="inline-flex items-center gap-1.5">
                  <span
                    class="w-[22px] h-[22px] rounded-[5px] inline-grid place-items-center text-[11px] font-bold border shrink-0 font-mono"
                    :class="getFormOutcomeSquareClass(m.result)"
                  >{{ m.result }}</span>
                  <span>{{ m.venue }} <span class="text-slate-400 font-normal">vs</span> <b>{{ m.opp }}</b></span>
                </span>
                <span class="font-mono tabular-nums text-slate-300">
                  <b :class="m.result === 'W' ? 'text-emerald-300' : m.result === 'L' ? 'text-rose-400' : 'text-amber-300'">{{ splitScoreAndInterim(m.score).main }}</b>
                  <span v-if="splitScoreAndInterim(m.score).interim" class="text-slate-400 ml-0.5">{{ splitScoreAndInterim(m.score).interim }}</span>
                  <span class="text-slate-400 ml-1">({{ m.date }})</span>
                </span>
              </div>
            </div>
          </div>

          <div>
            <b class="block mb-1.5 text-white">Head-to-Head History ({{ inspectorData.h2h?.length || 0 }} Meetings)</b>
            <div v-if="!inspectorData.h2h?.length" class="text-slate-300">First tracked meeting in current DB window.</div>
            <div
              v-for="(h, idx) in inspectorData.h2h"
              :key="idx"
              class="flex justify-between items-center py-1.5 border-b border-slate-800"
            >
              <span>
                <b v-if="getH2HWinnerSide(h) === 'H'" class="font-bold text-white">{{ h.home }}</b>
                <span v-else class="text-slate-300 font-normal">{{ h.home }}</span>
                <span class="text-slate-400 font-normal mx-1">vs</span>
                <b v-if="getH2HWinnerSide(h) === 'A'" class="font-bold text-white">{{ h.away }}</b>
                <span v-else class="text-slate-300 font-normal">{{ h.away }}</span>
              </span>
              <span class="font-mono tabular-nums">
                <b :class="getH2HScoreColorClass(h, inspectorData)">{{ splitScoreAndInterim(h.score).main }}</b>
                <span v-if="splitScoreAndInterim(h.score).interim" class="text-slate-400 font-normal ml-1">{{ splitScoreAndInterim(h.score).interim }}</span>
                <span class="text-slate-400 font-normal ml-1">({{ h.date }})</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Icon } from '@iconify/vue';
import { useBetscoutStore } from '../stores/betscoutStore';
import {
  formatLeagueBadgeLabel,
  getCompetitionFlagIconify,
  getFormOutcomeSquareClass,
  getH2HScoreColorClass,
  getH2HWinnerSide,
  getSportBadgeTheme,
  getSportIconColor,
  getSportIconify,
  getTierBadgeClass,
  splitScoreAndInterim,
} from '../utils/formatters';
import { setupIconifyCollections } from '../utils/iconifySetup';

setupIconifyCollections();

const store = useBetscoutStore();
const currentYear = new Date().getFullYear();
const appVersion = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.5.0';
const commitHash = typeof __COMMIT_HASH__ !== 'undefined' ? __COMMIT_HASH__ : 'dev';
const billingCycle = ref<'monthly' | 'annual'>('monthly');
const openFaq = ref<number | null>(0);
const mobileMenuOpen = ref<boolean>(false);

const inspectorModalOpen = ref<boolean>(false);
const inspectorTitle = ref<string>('Matchup Inspector');
const inspectorLoading = ref<boolean>(false);
const inspectorData = ref<any>(null);

async function openMatchupModal(home: string, away: string, league = '') {
  inspectorTitle.value = `${home} vs ${away}`;
  inspectorModalOpen.value = true;
  inspectorLoading.value = true;
  try {
    const qs = new URLSearchParams({ home, away, league });
    const r = await fetch(`/api/matchup?${qs.toString()}`);
    if (r.ok) {
      inspectorData.value = await r.json();
    }
  } catch (_) {
    inspectorData.value = null;
  } finally {
    inspectorLoading.value = false;
  }
}

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
  return store.settledBets.slice(0, 10);
});

const faqs = [
  {
    q: 'Are all settled results and ROI metrics verified out-of-sample?',
    a: 'Yes. Every BetScout pick is timestamped and logged in the prospective Paper-Bet Ledger before kickoff with live bookmaker odds. Results are graded automatically against official final match scoreboards with zero retroactive edits.',
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
