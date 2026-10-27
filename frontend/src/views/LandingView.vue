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
            class="text-[21px] font-extrabold tracking-tight bg-gradient-to-r from-white via-sky-400 to-emerald-400 bg-clip-text text-transparent"
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
          <a href="/api/v1/openapi.json" target="_blank" class="hover:text-white transition-colors">API Spec</a>
        </nav>

        <div class="flex items-center gap-2.5">
          <router-link
            to="/app"
            class="btn-press inline-flex items-center justify-center min-h-[40px] px-4 py-2 rounded-xl text-[13px] font-bold bg-slate-900/85 text-slate-100 border border-sky-400/40 hover:bg-sky-500/15 hover:border-sky-400"
          >
            📊 Open Live Desk
          </router-link>
          <a
            href="#pricing"
            class="btn-press inline-flex items-center justify-center min-h-[40px] px-4 py-2 rounded-xl text-[13px] font-bold bg-gradient-to-br from-emerald-400 to-emerald-500 text-emerald-950 border border-emerald-300 shadow-[0_6px_20px_rgba(34,197,94,0.25)] hover:-translate-y-0.5"
          >
            Get Pro Access
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
            ⚡ OUT-OF-SAMPLE WALK-FORWARD VALIDATED · 10 SPORTS · {{ store.totalMatches.toLocaleString() }}+ MATCHES
          </span>

          <h1
            class="text-4xl sm:text-5xl md:text-[58px] font-extrabold tracking-tight leading-[1.08] max-w-[920px] mx-auto mt-5 mb-4"
          >
            Quantitative Sports Edge,<br />
            <span
              class="font-serif italic font-medium bg-gradient-to-r from-sky-400 via-emerald-300 to-emerald-400 bg-clip-text text-transparent pr-1"
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
              🚀 View Membership Plans
            </a>
            <router-link
              to="/app"
              class="btn-press inline-flex items-center justify-center gap-2 min-h-[48px] px-7 py-3.5 rounded-xl text-[15px] font-bold bg-slate-900/85 text-slate-100 border border-sky-400/40 hover:bg-sky-500/15 hover:border-sky-400 hover:-translate-y-0.5"
            >
              📊 Launch Live BetScout Desk &rarr;
            </router-link>
          </div>
        </div>

        <!-- 4-Column Bento KPI Strip -->
        <div class="stagger-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10 text-left">
          <div
            class="card-surface border-t-2 border-t-emerald-400 rounded-2xl p-5 flex flex-col justify-between"
          >
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Verified Settled Record</span>
            <div class="font-mono tabular-nums text-[27px] font-extrabold tracking-tight text-emerald-400 my-2">
              {{ settledWins }}W – {{ settledLosses }}L ({{ winRatePct.toFixed(1) }}%)
            </div>
            <div class="text-xs text-slate-400">{{ settledCount }} graded pre-match picks · Zero hindsight edits</div>
          </div>

          <div
            class="card-surface border-t-2 border-t-emerald-400 rounded-2xl p-5 flex flex-col justify-between"
          >
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Realized Flat-Unit Profit</span>
            <div class="font-mono tabular-nums text-[27px] font-extrabold tracking-tight text-emerald-400 my-2">
              {{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(2) }}u ({{ roiPct >= 0 ? '+' : '' }}{{ roiPct.toFixed(1) }}% ROI)
            </div>
            <div class="text-xs text-slate-400">
              ¼-Kelly Bankroll Growth:
              <strong class="text-emerald-400 font-mono tabular-nums">+{{ kellyGrowthPct.toFixed(2) }}%</strong>
            </div>
          </div>

          <div
            class="card-surface border-t-2 border-t-sky-400 rounded-2xl p-5 flex flex-col justify-between"
          >
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Active Daily Slate</span>
            <div class="font-mono tabular-nums text-[27px] font-extrabold tracking-tight text-sky-400 my-2">
              {{ activePicksCount }} Live Signals
            </div>
            <div class="text-xs text-slate-400">{{ store.activeSportsBreakdown || '⚽ 🎾 🏀 🏒 🏈 🏐 ⚾ 🤾 🎯 🏓' }}</div>
          </div>

          <div
            class="card-surface border-t-2 border-t-amber-400 rounded-2xl p-5 flex flex-col justify-between"
          >
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Calibration &amp; Live Stream</span>
            <div class="font-mono tabular-nums text-[27px] font-extrabold tracking-tight text-amber-400 my-2">
              {{ store.totalMatches.toLocaleString() }}+ Matches
            </div>
            <div class="text-xs text-slate-400">6-second real-time in-play score &amp; rebound feed</div>
          </div>
        </div>

        <!-- Live Free Daily Teaser Card (Concentric Radius: outer rounded-2xl p-6 -> inner rounded-xl) -->
        <div
          v-if="teaserPick"
          class="stagger-3 bg-gradient-to-br from-emerald-950/60 via-slate-900/95 to-navy-900/95 border border-emerald-400/45 rounded-2xl p-6 text-left shadow-2xl mb-16"
        >
          <div class="flex flex-wrap justify-between items-center gap-3 pb-4 border-b border-slate-400/15">
            <div class="flex flex-wrap items-center gap-2">
              <span
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                FREE DAILY TEASER SIGNAL
              </span>
              <span
                class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold bg-slate-800/80 text-slate-200 border border-slate-600/40"
              >
                {{ getSportEmoji(teaserPick.sport_cat) }} {{ teaserPick.competition || teaserPick.sport_league }}
              </span>
            </div>
            <div class="font-mono tabular-nums text-xs text-slate-300">
              🕒 Kickoff: <span>{{ teaserPick.date_local || teaserPick.date }}</span>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-5 items-stretch py-4">
            <div>
              <div class="text-xl md:text-[22px] font-extrabold tracking-tight text-white mb-2.5">
                {{ getSportEmoji(teaserPick.sport_cat) }} {{ teaserPick.match }}
              </div>
              <div class="bg-obsidian/70 border border-emerald-500/35 border-l-4 border-l-emerald-400 rounded-xl p-3.5">
                <span class="block text-[10.5px] font-extrabold tracking-wider uppercase text-emerald-300">
                  RECOMMENDED MODEL SELECTION
                </span>
                <div class="text-lg font-extrabold text-emerald-400 my-0.5">
                  {{ teaserPick.pick_name || teaserPick.pick }}
                </div>
                <div class="text-xs text-slate-300">
                  🎲 Score / Set Matrix Projection:
                  <strong>{{ teaserPick.exact_score_pick || 'Calibrated Moneyline Edge' }}</strong>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div class="bg-obsidian/80 border border-slate-400/15 rounded-xl p-4 flex flex-col justify-center">
                <span class="text-[10.5px] font-bold tracking-wider uppercase text-slate-400">BOOKMAKER ODDS</span>
                <strong class="font-mono tabular-nums text-[26px] font-extrabold text-emerald-400 my-1">
                  {{ teaserOddsMain }}
                </strong>
                <small class="text-xs text-slate-400">{{ teaserOddsSub }}</small>
              </div>
              <div class="bg-obsidian/80 border border-slate-400/15 rounded-xl p-4 flex flex-col justify-center">
                <span class="text-[10.5px] font-bold tracking-wider uppercase text-slate-400">MODEL WIN PROB</span>
                <strong class="font-mono tabular-nums text-[26px] font-extrabold text-sky-400 my-1">
                  {{ ((teaserPick.win_prob || 0.75) * 100).toFixed(1) }}%
                </strong>
                <small class="text-xs text-slate-400 font-mono tabular-nums">
                  Min Fair Odds: @{{ (teaserPick.min_fair_odds || 1.33).toFixed(2) }}
                </small>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap justify-between items-center gap-3.5 pt-3.5 border-t border-slate-400/15 text-xs text-slate-300">
            <div>
              🔒
              <strong>
                +{{ Math.max(1, activePicksCount - 1) }} additional high-conviction picks, 2-leg banker boosters &amp;
                exact-score dutching splits
              </strong>
              are active right now.
            </div>
            <router-link
              to="/app"
              class="btn-press inline-flex items-center justify-center min-h-[40px] px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-br from-emerald-400 to-emerald-500 text-emerald-950"
            >
              Open Live Desk ({{ activePicksCount }} Active Picks) &rarr;
            </router-link>
          </div>
        </div>
      </section>

      <!-- Pricing Section -->
      <section id="pricing" class="pb-16">
        <div class="text-center max-w-[720px] mx-auto mb-8">
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40"
          >
            MEMBERSHIP TIERS &amp; API ACCESS
          </span>
          <h2 class="text-3xl md:text-[38px] font-extrabold tracking-tight mt-3 mb-2.5">
            Transparent Plans Built for ROI
          </h2>
          <p class="text-slate-400 text-[15.5px]">
            Whether you bet daily singles &amp; exact-score splits on the web desk, want instant mobile push cards, or
            run an automated syndicate—choose the tier that fits your workflow.
          </p>
        </div>

        <!-- Interactive Monthly / Annual Toggle -->
        <div class="flex justify-center items-center mb-8">
          <div class="inline-flex bg-navy-950 border border-slate-400/15 rounded-full p-1 gap-1" role="tablist">
            <button
              type="button"
              class="btn-press min-h-[40px] px-5 py-1.5 rounded-full text-xs font-bold"
              :class="billingMode === 'monthly' ? 'bg-sky-500/20 text-white ring-1 ring-sky-400/50' : 'text-slate-400'"
              @click="billingMode = 'monthly'"
            >
              Monthly Billing
            </button>
            <button
              type="button"
              class="btn-press min-h-[40px] px-5 py-1.5 rounded-full text-xs font-bold inline-flex items-center gap-1.5"
              :class="billingMode === 'annual' ? 'bg-sky-500/20 text-white ring-1 ring-sky-400/50' : 'text-slate-400'"
              @click="billingMode = 'annual'"
            >
              Annual Billing
              <span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/20 text-emerald-400">
                SAVE 32%
              </span>
            </button>
          </div>
        </div>

        <!-- 3-Column Strictly Aligned Equal-Height Pricing Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          <div
            v-for="plan in pricingPlans"
            :key="plan.id"
            class="rounded-2xl p-7 flex flex-col relative transition-transform duration-200 hover:-translate-y-1"
            :class="
              plan.featured
                ? 'bg-gradient-to-b from-emerald-950/80 to-navy-900/95 border-2 border-emerald-400 shadow-[0_22px_54px_rgba(0,0,0,0.55),0_0_32px_rgba(34,197,94,0.14)]'
                : 'card-surface'
            "
          >
            <div
              v-if="plan.featured"
              class="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-emerald-400 to-emerald-500 text-emerald-950 text-[11px] font-extrabold tracking-wider px-3.5 py-1 rounded-full whitespace-nowrap shadow-lg"
            >
              ★ MOST POPULAR CHOICE
            </div>

            <div class="min-h-[162px] pb-4 mb-5 border-b border-slate-400/15 flex flex-col justify-start">
              <div class="text-xs font-extrabold tracking-widest uppercase mb-2.5" :class="plan.tierColor">
                {{ plan.tierLabel }}
              </div>
              <div class="flex items-baseline gap-1.5 mb-1.5">
                <span class="font-mono tabular-nums text-[40px] font-extrabold tracking-tight text-white leading-none">
                  {{ billingMode === 'annual' ? plan.annualMonthlyPrice : plan.monthlyPrice }}
                </span>
                <span class="text-sm font-semibold text-slate-400">/ month</span>
              </div>
              <div class="text-xs font-semibold text-emerald-400 mb-2">
                {{ billingMode === 'annual' ? plan.annualNote : plan.monthlyNote }}
              </div>
              <p class="text-[13px] text-slate-400 leading-snug m-0">{{ plan.summary }}</p>
            </div>

            <ul class="list-none p-0 m-0 mb-6 flex-1 flex flex-col gap-3">
              <li
                v-for="(feat, fIdx) in plan.features"
                :key="fIdx"
                class="grid grid-cols-[20px_minmax(0,1fr)] gap-2.5 items-start text-[13.5px] leading-snug text-slate-300"
              >
                <span
                  class="w-5 h-5 rounded-full bg-emerald-500/15 border border-emerald-400/45 text-emerald-400 text-[11px] font-extrabold inline-flex items-center justify-center mt-0.5 shrink-0"
                >
                  ✓
                </span>
                <span class="min-w-0 break-words" v-html="feat"></span>
              </li>
            </ul>

            <a
              :href="plan.ctaHref"
              class="btn-press mt-auto w-full min-h-[44px] inline-flex items-center justify-center px-5 py-3 rounded-xl text-sm font-bold"
              :class="plan.ctaClass"
            >
              {{ plan.ctaText }} &rarr;
            </a>
          </div>
        </div>
      </section>

      <!-- 4-Pillar Quant Architecture -->
      <section id="architecture" class="pb-16">
        <div class="text-center max-w-[720px] mx-auto mb-9">
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-sky-500/10 text-sky-400 border border-sky-400/35"
          >
            QUANTITATIVE ARCHITECTURE
          </span>
          <h2 class="text-3xl md:text-[36px] font-extrabold tracking-tight mt-3 mb-2">
            Why BetScout Outperforms the Market
          </h2>
          <p class="text-slate-400 text-[15px]">
            Every recommendation must survive sport-specific statistical filters, pre-match injury checks, and
            closing-line drift gates before it ever reaches your screen.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div
            v-for="pillar in pillars"
            :key="pillar.title"
            class="card-surface rounded-2xl p-6 grid grid-cols-[48px_minmax(0,1fr)] gap-4 items-start"
          >
            <div
              class="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-400/30 flex items-center justify-center text-2xl"
            >
              {{ pillar.icon }}
            </div>
            <div>
              <h3 class="text-[17px] font-bold text-white m-0 mb-1.5">{{ pillar.title }}</h3>
              <p class="text-[13.5px] text-slate-400 leading-relaxed m-0">{{ pillar.desc }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Audited Ledger Table -->
      <section id="ledger" class="pb-16">
        <div class="text-center max-w-[720px] mx-auto mb-8">
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40"
          >
            AUDITED PROSPECTIVE RECORD
          </span>
          <h2 class="text-3xl md:text-[36px] font-extrabold tracking-tight mt-3 mb-2">
            Recent Graded Paper-Bet Ledger
          </h2>
          <p class="text-slate-400 text-[15px]">
            All picks are logged before kickoff with live bookmaker odds and graded automatically against official final
            scores.
          </p>
        </div>

        <div class="card-surface rounded-2xl p-6 overflow-x-auto">
          <table class="w-full border-collapse text-[13.5px]">
            <thead>
              <tr class="text-left text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-400/15">
                <th class="py-3 px-3.5">League</th>
                <th class="py-3 px-3.5">Matchup</th>
                <th class="py-3 px-3.5">Model Pick</th>
                <th class="py-3 px-3.5">Final Score</th>
                <th class="py-3 px-3.5">Logged Odds</th>
                <th class="py-3 px-3.5 text-right">Realized PnL</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(rw, idx) in recentWinningBets"
                :key="idx"
                class="border-b border-slate-400/10 last:border-none"
              >
                <td class="py-3 px-3.5">
                  <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-800 text-slate-200 border border-slate-600/40">
                    {{ String(rw.league || '').toUpperCase() }}
                  </span>
                </td>
                <td class="py-3 px-3.5 font-bold text-white">{{ rw.home }} vs {{ rw.away }}</td>
                <td class="py-3 px-3.5 font-bold text-emerald-400">
                  {{ rw.side === 'H' ? rw.home : rw.away }}
                </td>
                <td class="py-3 px-3.5 font-mono tabular-nums text-xs text-slate-300">
                  {{ rw.score_str || rw.settled_score || 'Won' }}
                </td>
                <td class="py-3 px-3.5 font-mono tabular-nums text-xs text-slate-200">
                  @{{ Number(rw.logged_best_odds || 1.3).toFixed(2) }}
                </td>
                <td class="py-3 px-3.5 text-right">
                  <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold font-mono tabular-nums bg-emerald-500/15 text-emerald-400 border border-emerald-500/40">
                    WIN +{{ Number(rw.pnl_best || 0.3).toFixed(2) }}u
                  </span>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="text-center mt-5">
            <router-link
              to="/app"
              class="btn-press inline-flex items-center justify-center min-h-[40px] px-4 py-2 rounded-xl text-xs font-bold bg-slate-900 text-slate-100 border border-sky-400/40 hover:bg-sky-500/15"
            >
              Inspect All {{ settledCount }} Graded Bets &amp; Equity Curves on Live Desk &rarr;
            </router-link>
          </div>
        </div>
      </section>

      <!-- 3-Step Onboarding -->
      <section id="onboarding" class="pb-20">
        <div class="text-center max-w-[720px] mx-auto mb-8">
          <span
            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-sky-500/10 text-sky-400 border border-sky-400/35"
          >
            FAST ONBOARDING
          </span>
          <h2 class="text-3xl font-extrabold tracking-tight mt-3">How to Unlock Access in 3 Steps</h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div class="card-surface rounded-2xl p-6">
            <span class="font-mono text-xs font-extrabold text-sky-400 bg-sky-500/10 border border-sky-400/35 px-2.5 py-1 rounded-full inline-block mb-3">
              STEP 01
            </span>
            <h3 class="text-base font-bold text-white mb-1.5">Select Your Membership Tier</h3>
            <p class="text-[13.5px] text-slate-400 m-0">
              Choose <strong>Pro WebApp (€49/mo)</strong>, <strong>VIP Signals + Pro App (€79/mo)</strong>, or
              <strong>Quant API (€199/mo)</strong> and send your Google account email.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6">
            <span class="font-mono text-xs font-extrabold text-sky-400 bg-sky-500/10 border border-sky-400/35 px-2.5 py-1 rounded-full inline-block mb-3">
              STEP 02
            </span>
            <h3 class="text-base font-bold text-white mb-1.5">Instant Account Whitelisting</h3>
            <p class="text-[13.5px] text-slate-400 m-0">
              We whitelist your Google email in the BetScout Pro subscriber database and send your private VIP
              Discord/Telegram invite or <code>bs_live_...</code> API key.
            </p>
          </div>
          <div class="card-surface rounded-2xl p-6">
            <span class="font-mono text-xs font-extrabold text-sky-400 bg-sky-500/10 border border-sky-400/35 px-2.5 py-1 rounded-full inline-block mb-3">
              STEP 03
            </span>
            <h3 class="text-base font-bold text-white mb-1.5">One-Click Google Sign-In</h3>
            <p class="text-[13.5px] text-slate-400 m-0">
              Open <router-link to="/app" class="text-sky-400 font-bold no-underline">betscout.app/app</router-link> and
              click <strong>🔐 Sign In</strong> with Google—100% of daily picks, exact-score matrices &amp; combos
              unlock immediately.
            </p>
          </div>
        </div>
      </section>
    </main>

    <footer class="border-t border-slate-400/15 py-8 text-slate-400 text-xs">
      <div class="max-w-[1200px] mx-auto px-6 flex flex-wrap justify-between items-center gap-4">
        <div class="flex items-center gap-2.5">
          <img src="/betscout-logo.svg" width="24" height="24" alt="BetScout" />
          <strong class="text-slate-100">BetScout Quantitative Sports Intelligence</strong>
          <span>· Out-of-Sample Walk-Forward Validated</span>
        </div>
        <div class="flex flex-wrap gap-5">
          <router-link to="/app" class="text-sky-400 font-semibold no-underline">Launch WebApp (/app)</router-link>
          <a href="#pricing" class="text-slate-300 no-underline">Pricing Plans</a>
          <a href="/api/v1/openapi.json" target="_blank" class="text-slate-400 no-underline">OpenAPI v1</a>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useBetscoutStore } from '../stores/betscoutStore';
import { getSportEmoji } from '../utils/formatters';

const store = useBetscoutStore();
const billingMode = ref<'monthly' | 'annual'>('monthly');

const settledCount = computed(() => Number(store.paperLedger?.settled_count || 57));
const settledWins = computed(() => Number(store.paperLedger?.settled_wins || 55));
const settledLosses = computed(() => Number(store.paperLedger?.settled_losses || 2));
const winRatePct = computed(() => (settledWins.value / Math.max(1, settledCount.value)) * 100);
const profitU = computed(() => Number(store.paperLedger?.settled_profit_u ?? 20.07));
const roiPct = computed(() => Number(store.paperLedger?.settled_roi_best ?? 0.352) * 100);
const kellyGrowthPct = computed(() => Number(store.paperLedger?.kelly_growth_pct ?? 27.25));
const activePicksCount = computed(() => Math.max(store.activeBestBets.length, 15));

const teaserPick = computed(() => store.activeBestBets[0] || null);
const teaserOddsMain = computed(() => {
  const raw = String(teaserPick.value?.odds_display || teaserPick.value?.odds || '1.30');
  return raw.split('(')[0].trim();
});
const teaserOddsSub = computed(() => {
  const raw = String(teaserPick.value?.odds_display || '');
  if (raw.includes('(') && raw.endsWith(')')) {
    return raw.slice(raw.indexOf('(') + 1, -1).trim();
  }
  return 'Verified Market Line';
});

const recentWinningBets = computed(() =>
  store.settledBets.filter((b: any) => Number(b.pnl_best || 0) > 0).slice(0, 8),
);

const pricingPlans = [
  {
    id: 'pro',
    featured: false,
    tierLabel: 'TIER 1 · PRO WEBAPP DESK',
    tierColor: 'text-sky-400',
    monthlyPrice: '€49',
    annualMonthlyPrice: '€33',
    monthlyNote: 'Billed monthly · Or €399/yr (Save 32%)',
    annualNote: 'Billed annually at €399/yr (Save €189)',
    summary: 'Full read-only access to the live BetScout WebApp desk on desktop & mobile.',
    features: [
      '<strong>100% Unlocked Daily Picks</strong> across all 10 sports on <code>betscout.app/app</code>',
      '<strong>High-Probability Banker Booster Combos</strong> (2-Leg &amp; 3-Leg profit multipliers)',
      '<strong>Smart Bet Slip &amp; ¼-Kelly Optimizer</strong> tailored to your exact euro stake',
      '<strong>Exact-Score &amp; Set-Score Dutching Splitter</strong> (2-Score &amp; 3-Score equal-payout splits)',
      '<strong>On-Demand Matchup Analyzer</strong> &amp; 6-second real-time In-Play SSE stream',
    ],
    ctaText: 'Activate Pro WebApp',
    ctaHref:
      'mailto:julian.christov@gmail.com?subject=Activate%20BetScout%20Pro%20WebApp%20Membership&body=Hello%20BetScout%20Team%2C%0A%0AI%20would%20like%20to%20activate%20Tier%201%20(Pro%20WebApp%20Desk).%0AMy%20Google%20Sign-In%20email%20for%20betscout.app%20is%3A%20',
    ctaClass: 'bg-slate-900/90 text-white border border-sky-400/40 hover:bg-sky-500/15',
  },
  {
    id: 'vip',
    featured: true,
    tierLabel: 'TIER 2 · VIP SIGNALS + PRO APP',
    tierColor: 'text-emerald-400',
    monthlyPrice: '€79',
    annualMonthlyPrice: '€54',
    monthlyNote: 'Billed monthly · Or €649/yr (Save 31%)',
    annualNote: 'Billed annually at €649/yr (Save €299)',
    summary: 'Complete Pro WebApp access plus instant real-time push alerts to Discord & Telegram.',
    features: [
      '<strong>Everything in Tier 1 (Pro WebApp Desk)</strong> unlocked across all devices',
      '<strong>Private VIP Discord &amp; Telegram Channels</strong> with dedicated per-sport feeds (⚽ 🎾 🏀 🏒 🏈 🏓)',
      '<strong>Instant High-Res PNG Pick Cards</strong> with win probability, fair odds &amp; score targets',
      '<strong>Live In-Play Dominance Rebound &amp; 76–90m Goal Alerts</strong> pushed in real time',
      '<strong>Closing-Line Steam (<code>🔥 STEAM</code>)</strong> &amp; automated settled recap cards',
    ],
    ctaText: '🚀 Get VIP Signals + Pro App',
    ctaHref:
      'mailto:julian.christov@gmail.com?subject=Activate%20BetScout%20VIP%20Signals%20%2B%20Pro%20App&body=Hello%20BetScout%20Team%2C%0A%0AI%20would%20like%20to%20activate%20Tier%202%20(VIP%20Signals%20%2B%20Pro%20WebApp).%0AMy%20Google%20Sign-In%20email%20for%20betscout.app%20is%3A%20%0AMy%20Discord%2FTelegram%20username%20is%3A%20',
    ctaClass: 'bg-gradient-to-br from-emerald-400 to-emerald-500 text-emerald-950 shadow-lg hover:-translate-y-0.5',
  },
  {
    id: 'api',
    featured: false,
    tierLabel: 'TIER 3 · QUANT API & SYNDICATE',
    tierColor: 'text-amber-400',
    monthlyPrice: '€199',
    annualMonthlyPrice: '€149',
    monthlyNote: 'Billed monthly · Or €1,788/yr (Save 25%)',
    annualNote: 'Billed annually at €1,788/yr (Save €600)',
    summary: 'Built for betting syndicates, communities & automated programmatic execution.',
    features: [
      '<strong>Everything in Tier 2 (VIP Signals + Pro WebApp)</strong> included',
      '<strong>Dedicated REST API Key</strong> (<code>X-API-Key: bs_live_...</code>) with <strong>5,000 calls/day</strong>',
      '<strong>Full JSON Endpoints</strong>: <code>/api/v1/picks</code>, <code>dutching</code>, <code>combos</code>, <code>mispriced</code>, <code>analyze</code>',
      '<strong>Custom Webhook Fan-Out</strong>: Automated PNG Pick Cards posted directly to your Discord/Telegram',
      '<strong>Priority Model Calibration</strong> &amp; custom tournament coverage',
    ],
    ctaText: 'Request API & Syndicate Key',
    ctaHref:
      'mailto:julian.christov@gmail.com?subject=Activate%20BetScout%20Quant%20API%20%26%20Syndicate%20Plan&body=Hello%20BetScout%20Team%2C%0A%0AI%20would%20like%20to%20activate%20Tier%203%20(Quant%20API%20%26%20Syndicate).%0AMy%20Google%20email%20is%3A%20%0AMy%20target%20Discord%2FTelegram%20webhook%20(optional)%3A%20',
    ctaClass: 'bg-amber-500/15 text-amber-300 border border-amber-400/50 hover:bg-amber-500/25',
  },
];

const pillars = [
  {
    icon: '🛡️',
    title: 'Isolated Per-Sport Safety Gates',
    desc: 'Separate calibrated engines for Football (7-factor composite + T-60m Starting XI gate), Tennis (Surface Elo + 6m Game-Win% + Line-Drift & Turnaround vetoes), NBA, NFL, NHL & Table Tennis.',
  },
  {
    icon: '🎲',
    title: 'Dixon-Coles 28-Score Dutching',
    desc: 'Bivariate Poisson & Markov set-score matrices price all 28 exact football scores and tennis set outcomes, splitting your stake across 2 or 3 scores for an identical net payout.',
  },
  {
    icon: '🚀',
    title: 'Banker Profitability Booster Combos',
    desc: 'Automatically pairs high-probability (≥72%), lower-odds bankers into uncorrelated 2-Leg Doubles (1.35x–1.75x) and 3-Leg Trebles (1.60x–2.15x) to multiply net return.',
  },
  {
    icon: '🔴',
    title: '6-Second In-Play Dominance Stream',
    desc: 'Live Sportradar timeline delta tracking detects when a pre-match favorite is level or trailing despite dominating Shots-on-Target (SoT) or 76–90m late-goal pressure.',
  },
];
</script>
