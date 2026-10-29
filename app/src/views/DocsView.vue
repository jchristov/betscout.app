<template>
  <div class="min-h-screen flex flex-col relative overflow-x-hidden">
    <!-- Ambient Background Glows -->
    <div
      class="pointer-events-none fixed -top-32 left-1/4 w-[520px] h-[340px] rounded-full bg-sky-500/15 blur-[130px] -z-10"
      aria-hidden="true"
    ></div>
    <div
      class="pointer-events-none fixed top-64 right-1/5 w-[460px] h-[320px] rounded-full bg-emerald-500/12 blur-[130px] -z-10"
      aria-hidden="true"
    ></div>

    <!-- Sticky Top Navigation -->
    <header class="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-xl border-b border-slate-400/15">
      <div class="w-full max-w-[1280px] mx-auto px-4 sm:px-6 min-h-[66px] py-2.5 flex items-center justify-between gap-3">
        <router-link to="/" class="flex items-center gap-2.5 text-white font-extrabold text-lg tracking-tight shrink-0 no-underline">
          <img
            src="/betscout-logo.svg?v=7.3"
            width="38"
            height="38"
            alt="BetScout Logo"
            class="rounded-xl shadow-[0_0_20px_rgba(56,189,248,0.28)] shrink-0"
          />
          <span class="whitespace-nowrap">Bet<span class="text-emerald-400">Scout</span></span>
          <span
            class="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/45 whitespace-nowrap"
          >
            <Icon icon="fa6-solid:book-open" class="w-3 h-3 text-sky-300" />
            <span>USER GUIDE &amp; DOCS</span>
          </span>
        </router-link>

        <nav class="flex items-center gap-2 sm:gap-3 shrink-0" aria-label="Documentation Navigation">
          <router-link
            to="/"
            class="btn-press min-h-[36px] inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-900/80 border border-slate-700/80 no-underline"
          >
            <Icon icon="fa6-solid:house" class="w-3.5 h-3.5 text-sky-400" />
            <span class="hidden sm:inline">Home &amp; Plans</span>
          </router-link>
          <a
            href="/api/docs"
            class="btn-press min-h-[36px] inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-900/80 border border-slate-700/80 no-underline"
          >
            <Icon icon="fa6-solid:terminal" class="w-3.5 h-3.5 text-amber-400" />
            <span>Swagger &amp; OpenAPI</span>
          </a>
          <router-link
            to="/app"
            class="btn-press min-h-[36px] inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-extrabold text-slate-950 bg-gradient-to-r from-emerald-400 via-teal-300 to-sky-400 shadow-[0_6px_20px_rgba(16,185,129,0.28)] no-underline"
          >
            <Icon icon="fa6-solid:bolt" class="w-3.5 h-3.5" />
            <span>Open Live Quant Desk</span>
          </router-link>
        </nav>
      </div>
    </header>

    <!-- Main Documentation Layout (Sidebar + Content) -->
    <main class="flex-1 w-full max-w-[1280px] mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <!-- Hero Banner -->
      <div class="card-surface rounded-2xl p-6 sm:p-8 mb-6 border border-sky-400/35">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="max-w-3xl">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/45 mb-3">
              <Icon icon="fa6-solid:circle-check" class="w-3.5 h-3.5" />
              <span>v{{ appVersion }} ({{ commitHash }}) · 56 Sports · 2-Tier SQLite Cache · Remote MCP Server</span>
            </div>
            <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
              BetScout Platform Manual, Quantitative Methodology &amp; Remote MCP Guide
            </h1>
            <p class="text-sm text-slate-300 leading-relaxed">
              Complete guide to using the <strong class="text-white">4-Tab Live Quant Desk</strong>,
              <strong class="text-emerald-300">7-Factor Football &amp; 8-Feature Tennis Models</strong>,
              <strong class="text-sky-300">Dixon-Coles 28-Score &amp; Set-Score Dutching</strong>,
              <strong class="text-amber-300">2-Leg/3-Leg Banker Profit Boosters</strong>, and connecting AI agents
              (Claude, VS Code GitHub Copilot, Cursor, Windsurf) to <code class="text-sky-300">https://betscout.app/mcp</code>.
            </p>
          </div>
          <div class="flex flex-col gap-2 min-w-[210px]">
            <div class="p-3 rounded-xl bg-slate-950/85 border border-slate-700/80 font-mono tabular-nums text-xs">
              <span class="text-slate-400 block text-[10px] uppercase font-bold">Audited Settled Record</span>
              <b class="text-emerald-300 text-base">75W – 1L (98.7%)</b>
              <span class="block text-[11px] text-slate-300 mt-0.5">+29.34u Profit · +38.6% ROI</span>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <!-- Left Section Navigation -->
        <aside class="lg:col-span-3 lg:sticky lg:top-20 card-surface rounded-2xl p-3.5 space-y-1">
          <div class="px-2.5 py-1.5 text-[11px] font-extrabold uppercase tracking-wider text-slate-400">
            Documentation Sections
          </div>
          <button
            v-for="sec in sections"
            :key="sec.id"
            type="button"
            class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left text-xs font-bold transition-colors"
            :class="
              activeSection === sec.id
                ? 'bg-sky-500/20 text-sky-300 border border-sky-400/50'
                : 'text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent'
            "
            @click="activeSection = sec.id"
          >
            <Icon :icon="sec.icon" class="w-3.5 h-3.5 shrink-0" :class="sec.iconColor" />
            <span>{{ sec.title }}</span>
          </button>

          <div class="pt-3 mt-3 border-t border-slate-700/60 px-2 space-y-2 text-xs">
            <a
              href="/api/docs"
              class="btn-press w-full py-2 px-3 rounded-xl bg-slate-900/90 border border-slate-700 hover:border-sky-400 text-slate-200 font-semibold flex items-center justify-between no-underline"
            >
              <span>Interactive Swagger UI</span>
              <Icon icon="fa6-solid:arrow-right" class="w-3 h-3 text-sky-400" />
            </a>
            <a
              href="/docs/notification-cards.html"
              class="btn-press w-full py-2 px-3 rounded-xl bg-slate-900/90 border border-slate-700 hover:border-emerald-400 text-slate-200 font-semibold flex items-center justify-between no-underline"
            >
              <span>PNG Notification Cards</span>
              <Icon icon="fa6-solid:arrow-right" class="w-3 h-3 text-emerald-400" />
            </a>
          </div>
        </aside>

        <!-- Right Main Content Area -->
        <div class="lg:col-span-9 space-y-6">
          <!-- SECTION 1: QUICK START & PLATFORM WORKSPACE -->
          <section v-if="activeSection === 'overview' || activeSection === 'all'" class="card-surface rounded-2xl p-6 space-y-4">
            <div class="flex items-center gap-2.5 border-b border-slate-700/70 pb-3">
              <Icon icon="fa6-solid:rocket" class="w-5 h-5 text-emerald-400" />
              <h2 class="text-lg font-extrabold text-white">1. Quick Start &amp; 4-Tab Live Quant Desk Tour</h2>
            </div>
            <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">
              The BetScout WebApp (<router-link to="/app" class="text-sky-300 font-bold">/app</router-link>) is organized into four specialized operational tabs designed for fast daily execution and transparent out-of-sample auditing:
            </p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-1.5">
                <div class="flex items-center gap-2 font-bold text-emerald-300 text-sm">
                  <Icon icon="fa6-solid:bolt" class="w-4 h-4" />
                  <span>Tab 1 · Picks &amp; Live In-Play</span>
                </div>
                <p class="text-slate-300 leading-relaxed">
                  Displays the live 3-second in-play tracker at the top, followed by all qualifying pre-match picks across 10+ sports, filterable by <b class="text-white">Sport</b>, <b class="text-white">Day (`Today`, `Tomorrow`, `Next 48h`)</b>, and <b class="text-white">Min Odds (`1.10`–`1.65`)</b>. Click any matchup name to open the <b class="text-sky-300">Match Details &amp; H2H Modal</b>.
                </p>
              </div>
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-1.5">
                <div class="flex items-center gap-2 font-bold text-sky-300 text-sm">
                  <Icon icon="fa6-solid:calculator" class="w-4 h-4" />
                  <span>Tab 2 · Bet Slip, Dutching &amp; Combos</span>
                </div>
                <p class="text-slate-300 leading-relaxed">
                  Enter your exact EUR bankroll budget to compare <b class="text-white">Option A (Safe 2-Leg Multiplier)</b>, <b class="text-white">Option B (¼-Kelly Singles Portfolio)</b>, and <b class="text-white">Option C (65/35 Core + Combo Hybrid)</b>, or split a stake across 2 or 3 Exact Scores / Set Scores for an equal EUR payout.
                </p>
              </div>
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-1.5">
                <div class="flex items-center gap-2 font-bold text-amber-300 text-sm">
                  <Icon icon="fa6-solid:chart-line" class="w-4 h-4" />
                  <span>Tab 3 · Paper-Bet Ledger &amp; ROI</span>
                </div>
                <p class="text-slate-300 leading-relaxed">
                  Immutable, newest-first prospective ledger showing every settled match, logged odds, final score (with muted half-time or per-set scores), and realized unit PnL. Clicking any historical row opens its full H2H and form breakdown.
                </p>
              </div>
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-1.5">
                <div class="flex items-center gap-2 font-bold text-violet-300 text-sm">
                  <Icon icon="fa6-solid:microscope" class="w-4 h-4" />
                  <span>Tab 4 · Model Audit &amp; Backtest</span>
                </div>
                <p class="text-slate-300 leading-relaxed">
                  Breaks down settled attribution by <b class="text-white">Sport Group</b> (`SOCCER`, `TENNIS`, `HANDBALL`, `TABLE_TENNIS`, `NBA`, `NHL`, `NFL`) and <b class="text-white">Confidence Tier</b> (`top_8pct`, `top_10pct`, `banker_70pct`, `high_conf`) comparing expected vs. realized win rates.
                </p>
              </div>
            </div>
          </section>

          <!-- SECTION 2: QUANTITATIVE MODELS & SAFETY GATES -->
          <section v-if="activeSection === 'models' || activeSection === 'all'" class="card-surface rounded-2xl p-6 space-y-4">
            <div class="flex items-center gap-2.5 border-b border-slate-700/70 pb-3">
              <Icon icon="fa6-solid:shield-halved" class="w-5 h-5 text-sky-400" />
              <h2 class="text-lg font-extrabold text-white">2. Quantitative Models, Safety Gates &amp; Veto Rules</h2>
            </div>
            <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Every candidate fixture is scored by a sport-specific composite model and must pass strict pre-match safety gates before entering the active slate:
            </p>
            <div class="space-y-3 text-xs">
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80">
                <b class="text-emerald-300 text-sm block mb-1">⚽ Football · 7-Factor Orthogonal Composite + Dixon-Coles 28-Score Matrix</b>
                <p class="text-slate-300 leading-relaxed mb-2">
                  Combines standardized <code class="text-sky-300">tanh(Z)</code> factors:
                  <b>1. <code>p_mkt</code></b> (de-vigged market implied prob),
                  <b>2. <code>vig_neg</code></b> (low bookmaker overround),
                  <b>3. <code>sot_d</code></b> (rolling Shots-on-Target creation vs. suppression),
                  <b>4. <code>discipline</code></b> (foul/card differential),
                  <b>5. <code>h2h_adv</code></b> (shrunk head-to-head dominance),
                  <b>6. <code>dom_rebound</code></b> (unlucky SoT dominance rebound), and
                  <b>7. <code>recent_draws</code></b> (anti-stalemate propensity).
                </p>
                <div class="text-slate-400">
                  <b class="text-amber-300">Pre-Match Safety Gates:</b> Vetoes stalemate-prone favorites (<code class="text-slate-200">p_mkt &lt; 0.65</code> with high draw rate), weak-SoT favorites (<code class="text-slate-200">sot_d &lt; 0.35</code>), and severe squad depletion (<code class="text-slate-200">evaluate_sportradar_injury_gate</code> when missing players exceed the threshold or T-60m Starting XI drops key spine starters).
                </div>
              </div>

              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80">
                <b class="text-lime-300 text-sm block mb-1">🎾 Tennis · 8-Feature Surface Elo + Calibrated Markov Set-Score Engine</b>
                <p class="text-slate-300 leading-relaxed mb-2">
                  Maintains separate Elo ratings for <code class="text-sky-300">All Surfaces</code>, <code class="text-sky-300">Outdoor Hard</code>, <code class="text-sky-300">Indoor Hard</code>, <code class="text-sky-300">Clay</code>, and <code class="text-sky-300">Grass</code> alongside <code class="text-sky-300">Game-Win Elo</code>, rolling 6-month win%, 3-set decider win rate, current-tournament court acclimatization, and H2H.
                </p>
                <div class="text-slate-400">
                  <b class="text-amber-300">Set-Score &amp; Turnaround Gates:</b> Computes exact Markov probabilities for <code class="text-slate-200">2:0</code> / <code class="text-slate-200">0:2</code> straight sets, <code class="text-slate-200">2:1</code> / <code class="text-slate-200">1:2</code> deciders, and <code class="text-slate-200">+1.5 Sets</code> shields. Automatically flags or vetoes players with <code class="text-rose-300">&le;24h–38h</code> short turnaround or negative all-level (ATP/WTA/Challenger) Last-5 form divergence.
                </div>
              </div>

              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80">
                <b class="text-indigo-300 text-sm block mb-1">🤾🏓🎯🏀🏒 European &amp; US Major Sports Gates (Handball, Table Tennis, Darts, NBA, NHL, NFL)</b>
                <p class="text-slate-300 leading-relaxed">
                  Requires multi-factor alignment between Elo, rolling efficiency (FG%, Goalie Save% &amp; Shot Volume, Yards-per-Play), Last-5 form, and direct H2H history (vetoing Darts/Table Tennis favorites who lost their most recent H2H meeting or exceed the sport-specific odds ceiling).
                </p>
              </div>
            </div>
          </section>

          <!-- SECTION 3: SMART BET SLIP, DUTCHING & COMBOS -->
          <section v-if="activeSection === 'dutching' || activeSection === 'all'" class="card-surface rounded-2xl p-6 space-y-4">
            <div class="flex items-center gap-2.5 border-b border-slate-700/70 pb-3">
              <Icon icon="fa6-solid:dice" class="w-5 h-5 text-fuchsia-400" />
              <h2 class="text-lg font-extrabold text-white">3. Smart Bet Slip, ¼-Kelly Sizing &amp; Exact-Score Dutching</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-2">
                <b class="text-emerald-300 text-sm block">🚀 Banker Profitability Boosters (2-Leg &amp; 3-Leg)</b>
                <p class="text-slate-300 leading-relaxed">
                  Single bankers priced at <code class="text-amber-300">1.15–1.35</code> have high hit rates (&ge;72%–89%) but low standalone yield. BetScout pairs uncorrelated cross-league bankers into <b class="text-white">1.44x–1.85x</b> 2-leg and 3-leg tickets and sizes each ticket using <b class="text-sky-300">Quarter-Kelly weighting</b>:
                </p>
                <pre class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-emerald-300 font-mono text-[11px] overflow-x-auto">f_quarter = 0.25 * max(0, (p_comb * O_comb - 1) / (O_comb - 1))</pre>
              </div>
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-2">
                <b class="text-fuchsia-300 text-sm block">🎲 Equal-Payout Exact-Score &amp; Set-Score Dutching</b>
                <p class="text-slate-300 leading-relaxed">
                  Instead of guessing a single exact score, Dutching divides your total stake $S$ across the top 2 or 3 scores ($1:0, 2:0, 2:1$ in Football, or $2:0 + 2:1$ in Tennis) inversely proportional to their decimal odds $O_i$:
                </p>
                <pre class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sky-300 font-mono text-[11px] overflow-x-auto">Stake_i = S * (1 / O_i) / sum_j(1 / O_j)
Equal Payout = Stake_i * O_i (identical if any leg hits)</pre>
              </div>
            </div>
          </section>

          <!-- SECTION 4: REMOTE MCP SERVER & QUANT API -->
          <section id="mcp" v-if="activeSection === 'mcp' || activeSection === 'all'" class="card-surface rounded-2xl p-6 space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/70 pb-3">
              <div class="flex items-center gap-2.5">
                <Icon icon="fa6-solid:terminal" class="w-5 h-5 text-amber-400" />
                <h2 class="text-lg font-extrabold text-white">4. Remote MCP Server (<code class="text-sky-300">https://betscout.app/mcp</code>) &amp; Quant API</h2>
              </div>
              <a
                href="/api/docs"
                class="btn-press px-3 py-1 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-400/50 text-xs font-bold no-underline"
              >
                Open Interactive Swagger UI &rarr;
              </a>
            </div>

            <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Connect <b class="text-white">Claude</b>, <b class="text-white">VS Code GitHub Copilot</b>, <b class="text-white">Cursor</b>, or <b class="text-white">Windsurf</b> directly to BetScout's hosted quantitative engine over Streamable HTTP JSON-RPC 2.0 at <code class="text-emerald-300">https://betscout.app/mcp</code>.
            </p>

            <!-- Interactive Agent Config Tabs -->
            <div class="p-4 rounded-xl bg-slate-900/90 border border-sky-500/40 space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="t in mcpClientTabs"
                    :key="t.id"
                    type="button"
                    class="btn-press px-3 py-1.5 rounded-lg text-xs font-bold border"
                    :class="
                      activeMcpClient === t.id
                        ? 'bg-sky-500/20 text-sky-300 border-sky-400'
                        : 'bg-slate-950 text-slate-300 border-slate-700 hover:border-slate-500'
                    "
                    @click="activeMcpClient = t.id"
                  >
                    {{ t.label }}
                  </button>
                </div>
                <button
                  type="button"
                  class="btn-press inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
                  @click="copyActiveMcpSnippet"
                >
                  <Icon icon="fa6-solid:copy" class="w-3.5 h-3.5" />
                  <span>{{ copyFeedback || 'Copy Config' }}</span>
                </button>
              </div>
              <div class="text-[11px] text-slate-400 font-mono">{{ currentMcpTab.fileHint }}</div>
              <pre class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-emerald-300 font-mono text-xs overflow-x-auto leading-relaxed">{{ currentMcpTab.code }}</pre>
            </div>

            <!-- 7 Tools + 4 Prompts + 4 Resources Table -->
            <div class="space-y-3 text-xs">
              <b class="text-white text-sm block">7 Registered MCP Tools (<code class="text-sky-300">tools/list</code> &amp; <code class="text-sky-300">tools/call</code>)</b>
              <div class="table-surface rounded-xl overflow-x-auto">
                <table class="w-full border-collapse text-xs">
                  <thead>
                    <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase border-b border-slate-700/70 text-left">
                      <th class="py-2.5 px-3">Tool Name</th>
                      <th class="py-2.5 px-3">Key Arguments</th>
                      <th class="py-2.5 px-3">What It Returns</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-800/80">
                    <tr>
                      <td class="py-2.5 px-3 font-mono font-bold text-amber-300">get_daily_banker_picks</td>
                      <td class="py-2.5 px-3 font-mono text-slate-300">sport, min_odds, min_win_prob, mispriced_only, limit, cursor</td>
                      <td class="py-2.5 px-3 text-slate-300">Active pre-match &amp; live high-conviction picks with exact-score/set-score targets and opaque cursor pagination.</td>
                    </tr>
                    <tr>
                      <td class="py-2.5 px-3 font-mono font-bold text-amber-300">get_banker_profit_boosters</td>
                      <td class="py-2.5 px-3 font-mono text-slate-300">budget_eur, max_combos</td>
                      <td class="py-2.5 px-3 text-slate-300">2-leg &amp; 3-leg high-probability (&ge;72%) combo tickets with full leg details and Quarter-Kelly EUR stake allocations.</td>
                    </tr>
                    <tr>
                      <td class="py-2.5 px-3 font-mono font-bold text-amber-300">analyze_matchup</td>
                      <td class="py-2.5 px-3 font-mono text-slate-300">query ("Home vs Away")</td>
                      <td class="py-2.5 px-3 text-slate-300">On-demand live 7-Factor Football / 8-Feature Tennis Elo + Markov set-score distribution, H2H, Last-6 form &amp; turnaround warnings.</td>
                    </tr>
                    <tr>
                      <td class="py-2.5 px-3 font-mono font-bold text-amber-300">calculate_exact_score_dutching</td>
                      <td class="py-2.5 px-3 font-mono text-slate-300">query, stake_eur</td>
                      <td class="py-2.5 px-3 text-slate-300">Equal-payout EUR stake split across top Football exact scores (1:0/2:0/2:1) or Tennis set scores (2:0+2:1).</td>
                    </tr>
                    <tr>
                      <td class="py-2.5 px-3 font-mono font-bold text-amber-300">get_match_center_dossier</td>
                      <td class="py-2.5 px-3 font-mono text-slate-300">match_id OR (home, away, sport)</td>
                      <td class="py-2.5 px-3 text-slate-300">Complete 56-sport Match Center dossier: 2-way/3-way win probs, 28 Correct Scores, H2H edge, W/D/L form, surface splits &amp; missing players.</td>
                    </tr>
                    <tr>
                      <td class="py-2.5 px-3 font-mono font-bold text-amber-300">search_daily_fixtures</td>
                      <td class="py-2.5 px-3 font-mono text-slate-300">sport, date_ymd, query, limit, cursor</td>
                      <td class="py-2.5 px-3 text-slate-300">Search scheduled, live, and finished fixtures across 56 sports to discover numeric <code class="text-sky-300">match_id</code> values and pre-match odds.</td>
                    </tr>
                    <tr>
                      <td class="py-2.5 px-3 font-mono font-bold text-amber-300">get_paper_ledger_roi</td>
                      <td class="py-2.5 px-3 font-mono text-slate-300">status, sport, limit, cursor</td>
                      <td class="py-2.5 px-3 text-slate-300">Audited out-of-sample Paper-Betting Ledger summary (75W–1L, +29.34u, +38.6% ROI, CLV%) and paginated match history.</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 pt-2">
                <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80">
                  <b class="text-sky-300 block mb-1.5">4 Built-In MCP Prompts (<code>prompts/list</code>)</b>
                  <ul class="space-y-1 text-slate-300 list-disc pl-4">
                    <li><code class="text-amber-300 font-bold">daily-bankers</code> — Ranked multi-sport banker slate table</li>
                    <li><code class="text-amber-300 font-bold">parlay-builder</code> — Quarter-Kelly 2-leg &amp; 3-leg combo builder</li>
                    <li><code class="text-amber-300 font-bold">set-score-audit</code> — Tennis 2:0 / 0:2 fixed-set &amp; +1.5 Sets audit</li>
                    <li><code class="text-amber-300 font-bold">match-deep-dive</code> — Full Match Center + Exact-Score Dutching report</li>
                  </ul>
                </div>
                <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80">
                  <b class="text-emerald-300 block mb-1.5">4 Direct MCP Resources (<code>resources/list</code>)</b>
                  <ul class="space-y-1 text-slate-300 list-disc pl-4">
                    <li><code class="text-sky-300 font-bold">betscout://slate/today</code> — Active picks &amp; mispriced edges JSON</li>
                    <li><code class="text-sky-300 font-bold">betscout://ledger/summary</code> — Verified 75W–1L ledger &amp; sport ROI</li>
                    <li><code class="text-sky-300 font-bold">betscout://boosters/today</code> — Today's 2-leg &amp; 3-leg profit boosters</li>
                    <li><code class="text-sky-300 font-bold">betscout://cache/telemetry</code> — 2-tier L1/L2 SQLite Gismo cache stats</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          <!-- SECTION 5: CACHING, LEDGER & VERIFICATION -->
          <section v-if="activeSection === 'ledger' || activeSection === 'all'" class="card-surface rounded-2xl p-6 space-y-4">
            <div class="flex items-center gap-2.5 border-b border-slate-700/70 pb-3">
              <Icon icon="fa6-solid:database" class="w-5 h-5 text-cyan-400" />
              <h2 class="text-lg font-extrabold text-white">5. Paper-Betting Ledger, CLV &amp; 2-Tier SQLite Caching</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-1.5">
                <b class="text-amber-300 text-sm block">Prospective Ledger &amp; Closing Line Value (CLV)</b>
                <p class="text-slate-300 leading-relaxed">
                  Every qualifying pick is logged to <code class="text-sky-300">paper_bets</code> before kickoff with its opening odds, logged best odds, and exact-score projection. As kickoff approaches, closing odds are tracked to compute <b class="text-white">CLV% (`Logged Odds / Close Odds - 1`)</b>. After full time, official scores and interim period/set scores are graded automatically every 20 minutes via Cloud Scheduler.
                </p>
              </div>
              <div class="p-4 rounded-xl bg-slate-900/85 border border-slate-700/80 space-y-1.5">
                <b class="text-cyan-300 text-sm block">2-Tier L1 In-Memory + L2 Persistent SQLite Cache</b>
                <p class="text-slate-300 leading-relaxed">
                  Upstream Gismo lookups pass through an L1 LRU cache plus a persistent SQLite table (<code class="text-sky-300">gismo_http_cache</code>) with smart endpoint TTLs (<code class="text-emerald-300">3,600s</code> static/career, <code class="text-emerald-300">1,200s</code> season/form, <code class="text-emerald-300">600s</code> pre-match odds, and <code class="text-emerald-300">120s</code> negative caching for missing feeds), cutting cold-start latency to &lt;1.3s.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-400/15 py-6 mt-10 text-xs text-slate-400">
      <div class="max-w-[1280px] mx-auto px-4 sm:px-6 flex flex-wrap justify-between items-center gap-4">
        <div class="flex items-center gap-2">
          <img src="/betscout-logo.svg?v=7.3" width="20" height="20" alt="BetScout" class="rounded" />
          <span>&copy; {{ currentYear }} <strong class="text-slate-200">BetScout</strong> · Quantitative Sports Edge &amp; Score Intelligence.</span>
        </div>
        <div class="font-mono text-[11px] text-slate-400/95 bg-slate-900/65 border border-slate-700/50 px-2.5 py-0.5 rounded-full">
          v{{ appVersion }} ({{ commitHash }})
        </div>
        <div class="flex flex-wrap gap-4">
          <router-link to="/" class="hover:text-white">Home &amp; Plans</router-link>
          <router-link to="/app" class="hover:text-white">Live Quant Desk</router-link>
          <a href="/api/docs" class="hover:text-white">Swagger &amp; OpenAPI</a>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Icon } from '@iconify/vue';
import { setupIconifyCollections } from '../utils/iconifySetup';

setupIconifyCollections();

const currentYear = new Date().getFullYear();
const appVersion = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.5.0';
const commitHash = typeof __COMMIT_HASH__ !== 'undefined' ? __APP_HASH_FALLBACK() : 'dev';

function __APP_HASH_FALLBACK() {
  return typeof __COMMIT_HASH__ !== 'undefined' ? __COMMIT_HASH__ : 'dev';
}

const activeSection = ref<'all' | 'overview' | 'models' | 'dutching' | 'mcp' | 'ledger'>('all');

const sections = [
  { id: 'all' as const, title: 'All Documentation Sections', icon: 'fa6-solid:book-open', iconColor: 'text-sky-400' },
  { id: 'overview' as const, title: '1. Quick Start & 4-Tab Desk', icon: 'fa6-solid:rocket', iconColor: 'text-emerald-400' },
  { id: 'models' as const, title: '2. Quant Models & Safety Gates', icon: 'fa6-solid:shield-halved', iconColor: 'text-sky-400' },
  { id: 'dutching' as const, title: '3. Bet Slip, ¼-Kelly & Dutching', icon: 'fa6-solid:dice', iconColor: 'text-fuchsia-400' },
  { id: 'mcp' as const, title: '4. Remote MCP & Quant API', icon: 'fa6-solid:terminal', iconColor: 'text-amber-400' },
  { id: 'ledger' as const, title: '5. Ledger, CLV & SQLite Cache', icon: 'fa6-solid:database', iconColor: 'text-cyan-400' },
];

const activeMcpClient = ref<'copilot' | 'claude' | 'cursor' | 'windsurf' | 'curl'>('copilot');
const copyFeedback = ref<string>('');

const mcpClientTabs = [
  {
    id: 'copilot' as const,
    label: 'VS Code Copilot',
    fileHint: 'Add to .vscode/mcp.json or global .mcp.json:',
    code: `{
  "mcpServers": {
    "betscout": {
      "type": "http",
      "url": "https://betscout.app/mcp",
      "headers": {
        "X-API-Key": "bs_live_YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    id: 'claude' as const,
    label: 'Claude Code / Desktop',
    fileHint: 'Run in terminal with Claude Code CLI or add to .mcp.json:',
    code: `claude mcp add --transport http betscout https://betscout.app/mcp \\
  --header "X-API-Key: bs_live_YOUR_API_KEY"`,
  },
  {
    id: 'cursor' as const,
    label: 'Cursor',
    fileHint: 'Add to .cursor/mcp.json:',
    code: `{
  "mcpServers": {
    "betscout": {
      "url": "https://betscout.app/mcp",
      "headers": {
        "X-API-Key": "bs_live_YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    id: 'windsurf' as const,
    label: 'Windsurf / Cline',
    fileHint: 'Add to mcp_config.json:',
    code: `{
  "mcpServers": {
    "betscout": {
      "serverUrl": "https://betscout.app/mcp",
      "headers": {
        "X-API-Key": "bs_live_YOUR_API_KEY"
      }
    }
  }
}`,
  },
  {
    id: 'curl' as const,
    label: 'cURL / HTTP JSON-RPC',
    fileHint: 'Direct Streamable HTTP JSON-RPC 2.0 call to POST https://betscout.app/mcp:',
    code: `curl -X POST https://betscout.app/mcp \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: bs_live_YOUR_API_KEY" \\
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_banker_profit_boosters",
      "arguments": { "budget_eur": 100, "max_combos": 6 }
    }
  }'`,
  },
];

const currentMcpTab = computed(
  () => mcpClientTabs.find((x) => x.id === activeMcpClient.value) || mcpClientTabs[0]!,
);

function copyActiveMcpSnippet() {
  navigator.clipboard?.writeText(currentMcpTab.value.code);
  copyFeedback.value = 'Copied!';
  setTimeout(() => {
    copyFeedback.value = '';
  }, 1600);
}
</script>
