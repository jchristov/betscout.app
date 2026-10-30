<template>
  <div class="min-h-screen px-3 sm:px-6 py-4 sm:py-5 pb-6 text-xs text-slate-100 max-w-[1600px] mx-auto w-full relative overflow-x-hidden">
    <!-- Ambient Background Glow Orbs for Frosted Glass Refraction -->
    <div
      class="pointer-events-none fixed -top-28 left-1/5 w-[480px] h-[300px] rounded-full bg-sky-500/14 blur-[130px] -z-10"
    ></div>
    <div
      class="pointer-events-none fixed top-56 right-1/6 w-[440px] h-[280px] rounded-full bg-emerald-500/12 blur-[130px] -z-10"
    ></div>
    <div
      class="pointer-events-none fixed bottom-16 left-1/3 w-[440px] h-[280px] rounded-full bg-violet-500/10 blur-[140px] -z-10"
    ></div>

    <!-- Top Indeterminate Progress Bar -->
    <div v-if="store.loading || store.actionBusy" class="fixed top-0 left-0 right-0 h-1 z-50 bg-sky-500/20 overflow-hidden">
      <div class="h-full w-1/3 bg-gradient-to-r from-sky-400 via-emerald-400 to-sky-400 animate-pulse"></div>
    </div>

    <!-- Offline / Pending Sync Banner (PWA Offline Support) -->
    <div
      v-if="store.isOffline || store.pendingOfflineQueueCount > 0"
      class="card-surface flex flex-wrap items-center justify-between gap-2 rounded-xl px-4 py-2.5 mb-3 border border-amber-400/50"
    >
      <div class="flex items-center gap-2 text-amber-200">
        <Icon icon="fa6-solid:wifi" class="w-4 h-4 text-amber-400 shrink-0" />
        <span>
          <b v-if="store.isOffline">Offline PWA Mode Active:</b>
          <b v-else>Local Storage Queue Ready:</b>
          Showing locally cached snapshot ({{ store.lastLocalCacheTime || 'Saved' }}).
          <template v-if="store.pendingOfflineQueueCount > 0">
            <b>{{ store.pendingOfflineQueueCount }}</b> action(s) queued for automatic sync.
          </template>
        </span>
      </div>
      <button
        v-if="!store.isOffline && store.pendingOfflineQueueCount > 0"
        type="button"
        class="btn-press inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
        @click="store.flushOfflineQueue()"
      >
        <Icon icon="fa6-solid:arrows-rotate" class="w-3.5 h-3.5" />
        <span>Sync Queued Changes Now</span>
      </button>
    </div>

    <!-- Main Dashboard Header -->
    <header class="card-surface flex items-start gap-3 sm:gap-3.5 rounded-2xl px-3.5 sm:px-4 py-3.5 mb-3.5">
      <router-link
        to="/"
        class="w-[40px] h-[40px] sm:w-[42px] sm:h-[42px] flex items-center justify-center shrink-0 mt-0.5 rounded-xl ring-1 ring-white/15 shadow-[0_0_16px_rgba(56,189,248,0.22)] hover:scale-105 transition-transform"
        title="Back to BetScout Home & Membership Plans"
      >
        <img src="/betscout-logo.svg?v=7.3" width="42" height="42" alt="BetScout" />
      </router-link>

      <div class="flex-1 min-w-0 flex flex-col gap-2.5">
        <!-- Top Row -->
        <div class="flex flex-wrap justify-between items-start gap-2.5">
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-2">
              <h1 class="m-0 text-lg sm:text-xl font-extrabold tracking-tight leading-none whitespace-nowrap">
                <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
              </h1>
              <span
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 whitespace-nowrap"
              >
                <Icon icon="fa6-solid:bolt" class="w-3 h-3 text-emerald-400" />
                <span>LIVE AI</span>
              </span>
            </div>
            <span class="text-xs text-slate-300 font-medium">
              Sports Edge, Exact-Score &amp; Paper-Betting Intelligence
            </span>
          </div>

          <div class="flex flex-wrap items-center justify-end gap-1.5 text-[11px] text-slate-300 ml-auto self-start tabular-nums">
            <span class="inline-flex items-center gap-1.5 bg-slate-900/80 border border-slate-700/80 rounded-lg px-2.5 py-0.5">
              <Icon icon="fa6-solid:clock" class="w-3 h-3 text-sky-400" />
              <span>Updated: <b class="text-white">{{ store.generatedAtLocal }}</b></span>
            </span>
            <span class="hidden md:inline-flex items-center gap-1.5 bg-slate-900/80 border border-slate-700/80 rounded-lg px-2.5 py-0.5">
              <Icon icon="fa6-solid:circle-check" class="w-3 h-3 text-emerald-400" />
              <span><b class="text-white">{{ store.totalMatches.toLocaleString() }}</b> Verified Matches</span>
            </span>
            <span
              v-if="store.lastLocalCacheTime"
              class="hidden lg:inline-flex items-center gap-1.5 bg-slate-900/80 border border-slate-700/80 rounded-lg px-2.5 py-0.5"
              title="Snapshot & filter preferences are automatically persisted in browser LocalStorage for instant offline PWA access."
            >
              <Icon icon="fa6-solid:database" class="w-3 h-3 text-cyan-400" />
              <span>Local Cache: <b class="text-cyan-300">{{ store.lastLocalCacheTime }}</b></span>
            </span>
            <span
              class="inline-flex items-center gap-1.5 bg-slate-900/90 border border-slate-700/80 rounded-full px-2.5 py-0.5 text-[11px]"
            >
              <span
                class="w-2 h-2 rounded-full"
                :class="
                  store.streamStatus === 'online'
                    ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
                    : store.streamStatus === 'offline'
                      ? 'bg-rose-400'
                      : 'bg-amber-400'
                "
              ></span>
              <span>
                {{
                  store.streamStatus === 'online'
                    ? 'Connected'
                    : store.streamStatus === 'offline'
                      ? 'Offline Cached'
                      : 'Reconnecting...'
                }}
              </span>
            </span>
          </div>
        </div>

        <!-- Bottom Action Row -->
        <div class="flex flex-wrap justify-between items-center gap-2 w-full">
          <!-- Admin Action Buttons -->
          <div v-if="store.isAdmin" class="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              :disabled="store.actionBusy"
              class="btn-press inline-flex items-center gap-1.5 min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50 hover:bg-sky-500/30 disabled:opacity-50"
              @click="store.syncAndSettle(false)"
            >
              <Icon icon="fa6-solid:arrows-rotate" class="w-3.5 h-3.5" :class="store.actionBusy ? 'animate-spin' : ''" />
              <span>Sync &amp; Settle</span>
            </button>
            <button
              type="button"
              :disabled="store.actionBusy"
              class="btn-press inline-flex items-center gap-1.5 min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-bold bg-amber-500/15 text-amber-300 border border-amber-400/45 hover:bg-amber-500/25 disabled:opacity-50"
              @click="store.syncAndSettle(true)"
            >
              <Icon icon="fa6-solid:bolt" class="w-3.5 h-3.5 text-amber-400" />
              <span>Rescan Live</span>
            </button>
            <button
              type="button"
              :disabled="store.actionBusy"
              class="btn-press inline-flex items-center gap-1.5 min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-400/45 hover:bg-emerald-500/25 disabled:opacity-50"
              @click="store.runFullPipeline()"
            >
              <Icon icon="fa6-solid:rocket" class="w-3.5 h-3.5 text-emerald-400" />
              <span>Full Pipeline</span>
            </button>
          </div>

          <!-- Guest / Pro Banner when not Admin -->
          <div
            v-else
            class="inline-flex flex-wrap items-center gap-2 bg-sky-500/15 border border-sky-400/40 rounded-xl px-3 py-1 text-[11.5px]"
          >
            <span
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold"
              :class="
                store.isPro
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/50'
                  : 'bg-amber-500/20 text-amber-300 border border-amber-400/50'
              "
            >
              <Icon :icon="store.isPro ? 'fa6-solid:lock-open' : 'fa6-solid:lock'" class="w-3 h-3" />
              <span>{{ store.isPro ? 'PRO READ-ONLY' : 'GUEST PREVIEW' }}</span>
            </span>
            <span v-if="store.isPro" class="text-slate-200">
              Signed in as <b>{{ store.userEmail || 'Pro Member' }}</b> · Real-time picks, exact-score targets &amp; SSE
              feed active.
            </span>
            <span v-else class="text-slate-200">
              Active picks, exact-score targets &amp; 2-leg combos are reserved for <b>BetScout Pro</b> members.
            </span>
            <button
              v-if="!store.userEmail"
              type="button"
              class="text-sky-300 font-bold hover:underline"
              @click="store.triggerSignInOut()"
            >
              Sign In
            </button>
            <span class="text-slate-500">·</span>
            <router-link to="/#pricing" class="inline-flex items-center gap-1 text-emerald-300 font-bold hover:underline">
              <span>Membership Plans</span>
              <Icon icon="fa6-solid:arrow-right" class="w-3 h-3" />
            </router-link>
          </div>

          <!-- Right Controls -->
          <div class="flex flex-wrap items-center gap-1.5 ml-auto">
            <button
              v-if="store.canInstallPwa"
              type="button"
              class="btn-press min-h-[34px] inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11.5px] font-bold bg-violet-500/20 text-violet-200 border border-violet-400/50"
              @click="store.promptPwaInstall()"
            >
              <Icon icon="fa6-solid:mobile-screen-button" class="w-3.5 h-3.5 text-violet-300" />
              <span>Install App</span>
            </button>
            <router-link
              to="/"
              class="btn-press min-h-[34px] inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-slate-900/90 text-slate-200 border border-slate-700 hover:border-sky-400 no-underline"
            >
              <Icon icon="fa6-solid:house" class="w-3.5 h-3.5 text-sky-400" />
              <span>Home &amp; Plans</span>
            </router-link>
            <button
              v-if="store.firebaseAuthCfg?.enabled"
              type="button"
              class="btn-press inline-flex items-center gap-1.5 min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold border"
              :class="
                store.userEmail
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/50'
                  : 'bg-sky-500/20 text-sky-300 border-sky-400/50'
              "
              @click="store.triggerSignInOut()"
            >
              <Icon :icon="store.userEmail ? 'fa6-solid:lock-open' : 'fa6-solid:lock'" class="w-3.5 h-3.5" />
              <span>
                {{
                  store.userEmail
                    ? `${store.userEmail.split('@')[0]} (${store.isAdmin ? 'Admin' : 'Pro'})`
                    : 'Sign In'
                }}
              </span>
            </button>
            <button
              v-if="store.isAdmin"
              type="button"
              class="btn-press inline-flex items-center gap-1.5 min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 hover:bg-emerald-500/30"
              @click="openShareSlateModal()"
            >
              <Icon icon="fa6-solid:share-nodes" class="w-3.5 h-3.5" />
              <span>Share Picks</span>
            </button>
            <button
              type="button"
              class="btn-press inline-flex items-center gap-1.5 min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-slate-900/90 text-slate-200 border border-slate-700 hover:border-sky-400"
              @click="settingsModalOpen = true"
            >
              <Icon icon="fa6-solid:gear" class="w-3.5 h-3.5 text-slate-300" />
              <span>Settings</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Action Progress Banner -->
    <div
      v-if="store.actionBusy"
      class="card-surface flex items-center gap-3 border border-sky-400/55 rounded-xl px-4 py-2.5 mb-3.5"
    >
      <span class="w-3.5 h-3.5 rounded-full border-2 border-sky-400 border-t-transparent animate-spin"></span>
      <b class="text-sky-300">{{ store.actionProgressText }}</b>
    </div>

    <!-- 5-Tile KPI Bento Strip (Color-Coded Top Accents + Frosted Glass) -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-3.5">
      <div
        class="card-surface border-t-2 border-t-emerald-400 rounded-xl px-3.5 py-3"
        title="Settled Win Rate & Exact-Score Accuracy across all graded paper-bets in the prospective ledger."
      >
        <span class="inline-flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-wider text-emerald-300">
          <Icon icon="fa6-solid:trophy" class="w-3.5 h-3.5 text-emerald-400" />
          <span>Settled Win Rate</span>
        </span>
        <b class="block text-lg font-mono tabular-nums mt-0.5 whitespace-nowrap">
          <span class="text-emerald-400">{{ settledWins }}W</span> –
          <span class="text-rose-400">{{ settledLosses }}L</span>
          (<span class="text-emerald-300">{{ winRatePct.toFixed(1) }}%</span>)
        </b>
        <small class="block text-[10.5px] text-slate-300 mt-1 truncate tabular-nums">
          {{ settledCount }} Graded ·
          <span
            class="cursor-help text-sky-300"
            title="Exact Score / Cluster Hit Rate: Share of graded matches where the final score landed inside BetScout's pre-match projected exact-score or set-score cluster."
          >
            Score Hits: {{ store.paperLedger?.exact_score_hits || 0 }}/{{ store.paperLedger?.exact_score_graded || 0 }}
            ({{ Number(store.paperLedger?.exact_score_hit_rate_pct || 0).toFixed(0) }}%)
          </span>
        </small>
      </div>

      <div
        class="card-surface border-t-2 border-t-cyan-400 rounded-xl px-3.5 py-3"
        title="Realized Flat-Unit Profit (1.00u per pick) and Return on Investment (ROI%) across all settled bets."
      >
        <span class="inline-flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-wider text-cyan-300">
          <Icon icon="fa6-solid:chart-line" class="w-3.5 h-3.5 text-cyan-400" />
          <span>Realized Profit / ROI</span>
        </span>
        <b
          class="block text-lg font-mono tabular-nums mt-0.5 whitespace-nowrap"
          :class="profitU >= 0 ? 'text-cyan-300' : 'text-rose-400'"
        >
          {{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(2) }}u ({{ roiPct >= 0 ? '+' : '' }}{{ roiPct.toFixed(1) }}%)
        </b>
        <small class="block text-[10.5px] text-slate-300 mt-1 truncate tabular-nums">
          <span
            class="cursor-help"
            title="Quarter-Kelly Bankroll Growth (¼-Kelly): Compounded percentage bankroll growth using optimal ¼-Kelly fractional staking."
          >
            ¼-Kelly:
            <b class="text-emerald-300">+{{ Number(store.paperLedger?.kelly_growth_pct || 0).toFixed(2) }}%</b>
          </span>
          ·
          <span class="cursor-help" :title="CLV_TOOLTIP">
            CLV:
            <b :class="meanClv >= 0 ? 'text-emerald-300' : 'text-rose-400'">
              {{ meanClv >= 0 ? '+' : '' }}{{ meanClv.toFixed(2) }}%
            </b>
          </span>
        </small>
      </div>

      <div
        class="card-surface border-t-2 border-t-sky-400 rounded-xl px-3.5 py-3"
        title="Total Upcoming & Live Qualifying Picks passing all sport-specific safety gates."
      >
        <span class="inline-flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-wider text-sky-300">
          <Icon icon="fa6-solid:layer-group" class="w-3.5 h-3.5 text-sky-400" />
          <span>Total Active Picks</span>
        </span>
        <b class="block text-lg font-mono tabular-nums text-white mt-0.5 whitespace-nowrap">
          {{ store.activeBestBets.length }} Picks
        </b>
        <div
          class="flex flex-wrap items-center gap-1 text-[10.5px] mt-1 font-mono tabular-nums"
          :title="store.activeSportsBreakdown"
        >
          <template v-if="store.activeSportsCounts.length">
            <span
              v-for="sp in store.activeSportsCounts"
              :key="sp.cat"
              class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-bold"
              :class="getSportBadgeTheme(sp.cat)"
            >
              <Icon :icon="sp.icon" class="w-3 h-3" />
              <span>{{ sp.count }}</span>
            </span>
          </template>
          <span v-else class="text-slate-300">{{ store.activeSportsBreakdown }}</span>
        </div>
      </div>

      <div
        class="card-surface border-t-2 border-t-rose-400 rounded-xl px-3.5 py-3"
        title="Currently in-play matches (streaming every 6s via live match telemetry) and pending pre-match bets in the ledger."
      >
        <span class="inline-flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-wider text-rose-300">
          <Icon icon="fa6-solid:tower-broadcast" class="w-3.5 h-3.5 text-rose-400" />
          <span>Live &amp; Pending Ledger</span>
        </span>
        <b class="flex items-center gap-2 text-lg font-mono tabular-nums mt-0.5 whitespace-nowrap">
          <span
            class="inline-flex items-center gap-2"
            :class="store.liveBets.length > 0 ? 'text-emerald-300' : 'text-slate-200'"
          >
            <span :class="store.liveBets.length > 0 ? 'live-blink-dot' : 'live-dot-idle'"></span>
            <span>{{ store.liveBets.length }} Live</span>
          </span>
          <span class="text-slate-500">·</span>
          <span class="inline-flex items-center gap-1 text-amber-300">
            <Icon icon="fa6-solid:clock" class="w-3.5 h-3.5 text-amber-400" />
            <span>{{ store.pendingBets.length }}</span>
          </span>
        </b>
        <small class="flex items-center gap-2 text-[10.5px] text-slate-300 mt-1 truncate tabular-nums">
          <span class="inline-flex items-center gap-1 text-sky-300">
            <Icon icon="fa6-solid:link" class="w-3 h-3 text-sky-400" />
            <span>{{ store.recommendedDoubles.length }} Combos</span>
          </span>
          <span>·</span>
          <span class="inline-flex items-center gap-1" :class="store.vetoedBets > 0 ? 'text-rose-400 font-bold' : ''">
            <Icon icon="fa6-solid:shield-halved" class="w-3 h-3" />
            <span>{{ store.vetoedBets }} Vetoes</span>
          </span>
        </small>
      </div>

      <div
        class="card-surface border-t-2 border-t-violet-400 rounded-xl px-3.5 py-3"
        title="Number of picks currently visible after applying your Sport, Day, Min Odds, and Search filters."
      >
        <span class="inline-flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-wider text-violet-300">
          <Icon icon="fa6-solid:wand-magic-sparkles" class="w-3.5 h-3.5 text-violet-400" />
          <span>Filtered Best Bets (&gt;{{ store.minOdds.toFixed(2) }})</span>
        </span>
        <b class="block text-lg font-mono tabular-nums text-violet-200 mt-0.5 whitespace-nowrap">
          {{ store.visibleBestBets.length }} Visible
        </b>
        <small class="flex items-center gap-1.5 text-[10.5px] text-slate-300 mt-1 truncate tabular-nums">
          <span class="text-emerald-300 font-bold">{{ store.mispricedBets.length }} Mispriced</span>
          <span>·</span>
          <span>{{ store.totalMatches.toLocaleString() }} Matches</span>
        </small>
      </div>
    </section>

    <!-- Color-Coded Filter Bar -->
    <div class="card-surface flex flex-col gap-2.5 rounded-xl px-3.5 py-2.5 mb-3 text-[11.5px]">
      <!-- Row 1: Sport Filters -->
      <div class="flex flex-wrap items-center gap-2">
        <b class="text-slate-200">Sport:</b>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="(label, key) in SPORT_CLEAN_LABELS"
            :key="key"
            type="button"
            class="btn-press inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border whitespace-nowrap"
            :class="
              store.sportFilter === key
                ? getSportBadgeTheme(key) + ' shadow-[0_0_12px_rgba(56,189,248,0.2)]'
                : 'bg-slate-900/80 border-slate-700/80 text-slate-300 hover:text-white hover:border-slate-500'
            "
            @click="store.sportFilter = key"
          >
            <Icon
              :icon="SPORT_ICONIFY_NAMES[key] || 'fa6-solid:globe'"
              class="w-3.5 h-3.5 shrink-0"
              :class="store.sportFilter === key ? '' : getSportIconColor(key)"
            />
            <span>{{ label }}</span>
          </button>
        </div>
      </div>

      <!-- Row 2: Day Filters + Min Odds, Search & Analyze Match -->
      <div class="flex flex-wrap items-center gap-2.5 pt-2 border-t border-slate-800/70">
        <b class="text-slate-200">Day:</b>
        <div class="flex flex-wrap gap-1.5">
          <button
            type="button"
            class="btn-press px-2.5 py-1 rounded-full text-[11px] font-bold border tabular-nums"
            :class="
              store.dayFilter === 'all'
                ? 'bg-sky-500/20 border-sky-400 text-sky-300'
                : 'bg-slate-900/80 border-slate-700/80 text-slate-300'
            "
            @click="store.dayFilter = 'all'"
          >
            All Days ({{ store.activeBestBets.length }})
          </button>
          <button
            v-for="dObj in store.availableDays"
            :key="dObj.day"
            type="button"
            class="btn-press px-2.5 py-1 rounded-full text-[11px] font-bold border tabular-nums"
            :class="
              store.dayFilter === dObj.day
                ? 'bg-sky-500/20 border-sky-400 text-sky-300'
                : 'bg-slate-900/80 border-slate-700/80 text-slate-300'
            "
            @click="store.dayFilter = dObj.day"
          >
            {{ dObj.day }} ({{ dObj.count }})
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-2 ml-auto w-full sm:w-auto pt-1 sm:pt-0">
          <b class="text-slate-200">Min Odds:</b>
          <input
            v-model.number="store.minOdds"
            type="range"
            min="1.05"
            max="2.00"
            step="0.05"
            class="w-24 sm:w-28 accent-sky-400 cursor-pointer"
          />
          <span class="font-mono tabular-nums text-amber-300">
            &gt;<b>{{ store.minOdds.toFixed(2) }}</b> (+{{ Math.round((store.minOdds - 1) * 100) }}%)
          </span>
          <input
            v-model="store.searchQuery"
            type="search"
            placeholder="Search team, player, league..."
            class="bg-slate-900/90 text-white border border-slate-700 rounded-lg px-2.5 py-1 text-[11.5px] flex-1 sm:min-w-[180px]"
          />
          <button
            type="button"
            class="btn-press inline-flex items-center gap-1.5 min-h-[32px] px-3 py-1 rounded-lg text-[11.5px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 hover:bg-emerald-500/30"
            @click="analyzerModalOpen = true"
          >
            <Icon icon="fa6-solid:magnifying-glass" class="w-3.5 h-3.5" />
            <span>Analyze Match</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Connected Folder-Style Tab Bar & Content -->
    <div class="mb-2">
      <nav class="workspace-tablist" role="tablist" aria-label="BetScout Workspace Sections">
        <button
          v-for="tab in workspaceTabs"
          :key="tab.id"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.id"
          :title="tab.label"
          class="workspace-tab whitespace-nowrap"
          :class="
            activeTab === tab.id
              ? 'workspace-tab-active flex-1 min-w-0'
              : 'workspace-tab-inactive shrink-0 lg:flex-1 px-3 lg:px-4'
          "
          @click="activeTab = tab.id"
        >
          <Icon :icon="tab.icon" class="w-4 h-4 shrink-0" :class="tab.iconColor" />
          <span
            class="truncate"
            :class="activeTab === tab.id ? 'inline' : 'hidden lg:inline'"
          >
            {{ tab.label }}
          </span>
          <span
            class="items-center whitespace-nowrap px-2 py-0.5 rounded-full text-[10px] font-bold tabular-nums border"
            :class="[
              tab.badgeClass,
              activeTab === tab.id ? 'hidden sm:inline-flex' : 'hidden xl:inline-flex',
            ]"
          >
            <template v-if="tab.id === 'ledger'">
              <span class="text-emerald-300">{{ settledWins }}W</span>
              <span class="text-slate-400 mx-0.5">–</span>
              <span class="text-rose-400">{{ settledLosses }}L</span>
              <span class="ml-1 text-amber-200">({{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(1)}}{{ 'u)' }}</span>
            </template>
            <template v-else>{{ tab.badge }}</template>
          </span>
        </button>
      </nav>

      <div class="workspace-tabpanel" role="tabpanel">
        <!-- TAB 1: PICKS & LIVE IN-PLAY -->
        <div v-if="activeTab === 'picks'">
      <!-- Live In-Play Header -->
      <div class="flex flex-wrap justify-between items-center gap-2 mb-2">
        <h2 class="inline-flex items-center gap-2 text-sm font-bold text-rose-300 m-0">
          <span :class="store.liveBets.length > 0 ? 'live-blink-dot' : 'live-dot-idle'"></span>
          <span>Live In-Play Paper-Bets &amp; Tracked Events (Ongoing: {{ store.liveBets.length }})</span>
        </h2>
        <div v-if="store.isAdmin" class="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
          <input
            v-model="trackQuickInput"
            type="search"
            placeholder="+ Track any live/upcoming match (e.g. Shelton vs Kovacevic)..."
            class="flex-1 sm:min-w-[280px] bg-slate-900/90 text-white border border-slate-700 rounded-lg px-2.5 py-1 text-[11.5px]"
            @keydown.enter="onTrackLiveQuick"
          />
          <button
            type="button"
            class="btn-press inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11.5px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50"
            @click="onTrackLiveQuick"
          >
            <Icon icon="fa6-solid:thumbtack" class="w-3.5 h-3.5" />
            <span>Track &amp; Analyze Live</span>
          </button>
        </div>
      </div>

      <!-- Mobile Live In-Play Cards (<768px) -->
      <div class="md:hidden space-y-2.5 mb-5">
        <div v-if="!store.liveBets.length" class="card-surface rounded-xl p-3.5 text-slate-300">
          No logged paper bets are currently in-play. Active matches move here automatically during kickoff!
        </div>
        <div
          v-for="tr in store.liveBets"
          :key="`mob-live-${tr.league}:${tr.event_id}`"
          class="card-surface rounded-xl p-3.5 border-l-2 border-l-rose-400"
        >
          <div class="flex justify-between items-center gap-2 mb-1.5">
            <span
              class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10.5px] font-bold border"
              :class="getSportBadgeTheme(tr.sport_cat)"
            >
              <Icon
                v-if="getCompetitionFlagIconify(formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away), `${tr.league} ${tr.home} ${tr.away}`)"
                :icon="getCompetitionFlagIconify(formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away), `${tr.league} ${tr.home} ${tr.away}`)!"
                class="w-3.5 h-2.5 rounded-[2px] shrink-0"
              />
              <Icon v-else :icon="getSportIconify(tr.sport_cat)" class="w-3.5 h-3.5 shrink-0" />
              <span>{{ formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away) }}</span>
            </span>
            <span class="font-mono tabular-nums text-[11px] text-slate-300">{{ tr.kickoff_local || tr.kickoff }}</span>
          </div>
          <button
            type="button"
            class="font-extrabold text-sm text-white hover:text-sky-300 text-left block mb-1.5"
            @click="openMatchupModal(tr.home, tr.away, tr.league)"
          >
            {{ tr.home }} <span class="text-slate-400 font-normal">vs</span> {{ tr.away }}
          </button>
          <div class="flex flex-wrap justify-between items-center gap-2">
            <div class="flex items-center gap-1.5">
              <b class="text-emerald-300">{{ tr.side === 'H' ? tr.home : tr.away }} ({{ tr.side }})</b>
              <span
                class="px-1.5 py-0.5 rounded text-[10px] font-bold border"
                :class="getTierBadgeClass(tr.tier)"
              >
                {{ tr.tier }}
              </span>
            </div>
            <div class="font-mono tabular-nums font-bold text-white">
              <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 mr-1 animate-ping"></span>
              {{ tr.live_score || tr.score_str || '0-0 (LIVE)' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Desktop Live In-Play Table (>=768px) -->
      <div class="hidden md:block table-surface rounded-2xl overflow-x-auto mb-5">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase tracking-wider border-b border-slate-700/70 text-left">
              <th class="py-2.5 px-2.5 w-11 text-center">Sport</th>
              <th class="py-2.5 px-2.5">Competition</th>
              <th class="py-2.5 px-2.5">Kickoff</th>
              <th class="py-2.5 px-2.5">Matchup</th>
              <th class="py-2.5 px-2.5">Pick</th>
              <th class="py-2.5 px-2.5">Live Score</th>
              <th class="py-2.5 px-2.5">Odds / CLV</th>
              <th class="py-2.5 px-2.5">Live Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!store.liveBets.length">
              <td colspan="8" class="py-3.5 px-3 text-slate-300">
                No logged paper bets are currently in-play. Active matches move here automatically during kickoff!
              </td>
            </tr>
            <tr
              v-for="tr in store.liveBets"
              :key="`${tr.league}:${tr.event_id}`"
              class="border-b border-slate-800/80 last:border-none hover:bg-slate-800/45"
            >
              <td class="py-2.5 px-2.5 text-center">
                <Icon
                  :icon="getSportIconify(tr.sport_cat)"
                  class="w-4 h-4 mx-auto"
                  :class="getSportIconColor(tr.sport_cat)"
                />
              </td>
              <td class="py-2.5 px-2.5">
                <span
                  class="inline-flex items-center gap-1.5 whitespace-nowrap px-2.5 py-0.5 rounded-md text-[10.5px] font-bold border"
                  :class="getSportBadgeTheme(tr.sport_cat || tr.league)"
                >
                  <Icon
                    v-if="getCompetitionFlagIconify(formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away), `${tr.league} ${tr.home} ${tr.away}`)"
                    :icon="getCompetitionFlagIconify(formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away), `${tr.league} ${tr.home} ${tr.away}`)!"
                    class="w-3.5 h-2.5 rounded-[2px] shrink-0"
                  />
                  <Icon v-else :icon="getSportIconify(tr.sport_cat || tr.league)" class="w-3.5 h-3.5 shrink-0" />
                  <span>{{ formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away) }}</span>
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums whitespace-nowrap text-slate-400">
                {{ tr.kickoff_local || tr.kickoff }}
              </td>
              <td class="py-2.5 px-2.5">
                <button
                  type="button"
                  class="font-bold text-white hover:text-sky-300 text-left transition-colors"
                  @click="openMatchupModal(tr.home, tr.away, tr.league)"
                >
                  {{ tr.home }} <span class="text-slate-400 font-normal">vs</span> {{ tr.away }}
                </button>
              </td>
              <td class="py-2.5 px-2.5">
                <div class="flex flex-wrap items-center gap-1.5">
                  <b class="text-emerald-300">{{ tr.side === 'H' ? tr.home : tr.away }} ({{ tr.side }})</b>
                  <span
                    class="pill-tip inline-flex items-center whitespace-nowrap px-1.5 py-0.5 rounded text-[10px] font-bold border cursor-help"
                    :class="getTierBadgeClass(tr.tier)"
                    :title="getBadgeTooltipText(tr.tier)"
                  >
                    {{ tr.tier }}
                  </span>
                </div>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums font-bold text-white whitespace-nowrap">
                <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 mr-1.5 animate-ping"></span>
                {{ tr.live_score || tr.score_str || '0-0 (LIVE)' }}
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums whitespace-nowrap">
                <b class="text-amber-300">{{ Number(tr.logged_best_odds || 1.3).toFixed(2) }}</b>
                <span class="text-slate-300 ml-1">
                  (Close {{ Number(tr.latest_close_odds || tr.logged_best_odds || 1.3).toFixed(2) }})
                </span>
              </td>
              <td class="py-2.5 px-2.5 whitespace-nowrap">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-[10.5px] font-bold border"
                  :class="
                    Number(tr.live_pnl || 0) > 0
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/50'
                      : Number(tr.live_pnl || 0) < 0
                        ? 'bg-rose-500/20 text-rose-300 border-rose-400/50'
                        : 'bg-amber-500/20 text-amber-300 border-amber-400/50'
                  "
                >
                  {{
                    Number(tr.live_pnl || 0) > 0
                      ? 'LIVE · LEADING'
                      : Number(tr.live_pnl || 0) < 0
                        ? 'LIVE · TRAILING'
                        : 'LIVE · LEVEL'
                  }}
                </span>
                <button
                  v-if="tr.tier === 'tracked_live' && store.isAdmin"
                  type="button"
                  class="btn-press ml-1.5 inline-flex items-center p-1 rounded border border-rose-500/50 text-rose-400"
                  @click="store.untrackLiveMatchup(tr.league, tr.event_id)"
                >
                  <Icon icon="fa6-solid:xmark" class="w-3 h-3" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Best Bets Summary Header -->
      <div class="flex flex-wrap justify-between items-center gap-2 mb-2">
        <h2 class="text-sm font-bold text-sky-300 m-0">
          Best Bets Summary Table (Click Any Header to Sort · Click Matchup for H2H · Select Rows for Custom Slip)
        </h2>
        <div class="flex flex-wrap items-center gap-1.5">
          <button
            v-if="store.customSelectedMatches.size > 0"
            type="button"
            class="btn-press inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/50"
            @click="store.clearCustomSelection()"
          >
            <Icon icon="fa6-solid:xmark" class="w-3 h-3" />
            <span>Clear Custom Selection ({{ store.customSelectedMatches.size }})</span>
          </button>
          <button
            type="button"
            class="btn-press inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50"
            @click="activeTab = 'studio'"
          >
            <Icon icon="fa6-solid:calculator" class="w-3.5 h-3.5" />
            <span>Open in Bet Slip &amp; Dutching Studio</span>
          </button>
        </div>
      </div>

      <!-- Responsive Mobile Best Bets Cards (<768px) -->
      <div class="md:hidden space-y-3 mb-5">
        <div v-if="!sortedBestBets.length" class="card-surface rounded-xl p-4 text-slate-300">
          No qualifying best bets match the current filter criteria.
        </div>
        <div
          v-for="b in sortedBestBets"
          :key="`mob-bet-${b.date}:${b.match}`"
          class="card-surface rounded-xl p-3.5"
          :class="store.customSelectedMatches.has(b.match) ? 'border-emerald-400/70' : ''"
        >
          <div class="flex justify-between items-center gap-2 mb-2">
            <label class="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                :checked="store.customSelectedMatches.has(b.match)"
                class="accent-emerald-400 w-4 h-4"
                @change="store.toggleCustomMatch(b.match)"
              />
              <span
                class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10.5px] font-bold border"
                :class="getSportBadgeTheme(b.sport_cat)"
              >
                <Icon
                  v-if="getCompetitionFlagIconify(b.competition, b.sport_league)"
                  :icon="getCompetitionFlagIconify(b.competition, b.sport_league)!"
                  class="w-3.5 h-2.5 rounded-[2px] shrink-0"
                />
                <Icon v-else :icon="getSportIconify(b.sport_cat)" class="w-3.5 h-3.5 shrink-0" />
                <span>{{ b.competition || b.sport_league }}</span>
              </span>
            </label>
            <span class="font-mono tabular-nums text-[11px] text-slate-300">
              {{ store.tzMode === 'utc' ? b.date : b.date_local }}
            </span>
          </div>

          <button
            type="button"
            class="font-extrabold text-sm text-white hover:text-sky-300 text-left block mb-2"
            @click="openMatchupModal(b.home, b.away, b.sport_league)"
          >
            <template v-if="b.home && b.away && !String(b.match || '').includes('🔒')">
              {{ b.home }} <span class="text-slate-400 font-normal">vs</span> {{ b.away }}
            </template>
            <template v-else>{{ b.match }}</template>
          </button>

          <div class="flex flex-wrap items-center gap-1.5 mb-2.5">
            <b class="text-emerald-300 text-xs">{{ b.pick_name || b.pick }}</b>
            <span
              v-if="b.tier"
              class="px-1.5 py-0.5 rounded text-[10px] font-bold border"
              :class="getTierBadgeClass(b.tier)"
            >
              {{ b.tier }}
            </span>
            <span
              v-if="b.is_mispriced"
              class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
            >
              <Icon icon="fa6-solid:wand-magic-sparkles" class="w-2.5 h-2.5" />
              <span>EDGE +{{ Number(b.edge_pp || 0).toFixed(1) }}pp</span>
            </span>
          </div>

          <div class="grid grid-cols-3 gap-2 pt-2 border-t border-slate-700/60 font-mono tabular-nums text-[11px]">
            <div>
              <span class="text-slate-400 block text-[10px]">WIN PROB</span>
              <b class="text-emerald-300">{{ (Number(b.win_prob || 0.5) * 100).toFixed(1) }}%</b>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px]">FAIR ODDS</span>
              <b class="text-slate-200">{{ Number(b.min_fair_odds || 1.35).toFixed(2) }}</b>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px]">MARKET ODDS</span>
              <b class="text-amber-300">{{ Number(b.odds || 1.3).toFixed(2) }}</b>
            </div>
          </div>
        </div>
      </div>

      <!-- Desktop Best Bets Table (>=768px) -->
      <div class="hidden md:block table-surface rounded-2xl overflow-x-auto mb-5">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr
              class="bg-slate-900/90 text-slate-300 text-[11px] uppercase tracking-wider border-b border-slate-700/70 text-left select-none"
            >
              <th class="py-2.5 px-2 w-9 text-center">Slip</th>
              <th class="py-2.5 px-2 w-11 text-center">Sport</th>
              <th class="py-2.5 px-2.5 cursor-pointer hover:text-white" @click="setBestBetsSort('comp')">
                Competition {{ sortInd('comp') }}
              </th>
              <th class="py-2.5 px-2.5 cursor-pointer hover:text-white" @click="setBestBetsSort('date')">
                Kickoff {{ sortInd('date') }}
              </th>
              <th class="py-2.5 px-2.5 cursor-pointer hover:text-white" @click="setBestBetsSort('match')">
                Matchup {{ sortInd('match') }}
              </th>
              <th class="py-2.5 px-2.5">Recommended Pick</th>
              <th class="py-2.5 px-2.5 cursor-pointer hover:text-white" @click="setBestBetsSort('win_prob')">
                Win Prob {{ sortInd('win_prob') }}
              </th>
              <th class="py-2.5 px-2.5 cursor-pointer hover:text-white" @click="setBestBetsSort('fair')">
                Fair Odds {{ sortInd('fair') }}
              </th>
              <th class="py-2.5 px-2.5">Score Projection</th>
              <th class="py-2.5 px-2.5 cursor-pointer hover:text-white" @click="setBestBetsSort('odds')">
                Odds / CLV &amp; Kelly {{ sortInd('odds') }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!sortedBestBets.length">
              <td colspan="10" class="py-4 px-3 text-slate-300">
                No qualifying best bets match the current filter criteria.
              </td>
            </tr>
            <tr
              v-for="b in sortedBestBets"
              :key="`${b.date}:${b.match}`"
              class="border-b border-slate-800/80 last:border-none hover:bg-slate-800/45 transition-colors"
              :class="store.customSelectedMatches.has(b.match) ? 'bg-sky-500/15' : ''"
            >
              <td class="py-2.5 px-2 text-center">
                <input
                  type="checkbox"
                  :checked="store.customSelectedMatches.has(b.match)"
                  class="accent-emerald-400 cursor-pointer w-3.5 h-3.5"
                  @change="store.toggleCustomMatch(b.match)"
                />
              </td>
              <td class="py-2.5 px-2 text-center">
                <Icon
                  :icon="getSportIconify(b.sport_cat)"
                  class="w-4 h-4 mx-auto"
                  :class="getSportIconColor(b.sport_cat)"
                />
              </td>
              <td class="py-2.5 px-2.5">
                <span
                  class="inline-flex items-center gap-1.5 whitespace-nowrap px-2.5 py-0.5 rounded-md text-[10.5px] font-bold border"
                  :class="getSportBadgeTheme(b.sport_cat)"
                >
                  <Icon
                    v-if="getCompetitionFlagIconify(b.competition, b.sport_league)"
                    :icon="getCompetitionFlagIconify(b.competition, b.sport_league)!"
                    class="w-3.5 h-2.5 rounded-[2px] shrink-0"
                  />
                  <Icon v-else :icon="getSportIconify(b.sport_cat)" class="w-3.5 h-3.5 shrink-0" />
                  <span>{{ b.competition || b.sport_league }}</span>
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums text-slate-400 whitespace-nowrap">
                {{ store.tzMode === 'utc' ? b.date : b.date_local }}
              </td>
              <td class="py-2.5 px-2.5">
                <button
                  type="button"
                  class="font-bold text-white hover:text-sky-300 text-left transition-colors"
                  @click="openMatchupModal(b.home, b.away, b.sport_league)"
                >
                  <template v-if="b.home && b.away && !String(b.match || '').includes('🔒')">
                    {{ b.home }} <span class="text-slate-400 font-normal">vs</span> {{ b.away }}
                  </template>
                  <template v-else>{{ b.match }}</template>
                </button>
              </td>
              <td class="py-2.5 px-2.5">
                <div class="flex flex-wrap items-center gap-1.5">
                  <b class="text-emerald-300">{{ b.pick_name || b.pick }}</b>
                  <span
                    v-if="b.tier"
                    class="pill-tip inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded-md text-[10px] font-bold border cursor-help"
                    :class="getTierBadgeClass(b.tier)"
                    :title="getBadgeTooltipText(b.tier)"
                  >
                    {{ b.tier }}
                  </span>
                  <span
                    v-if="b.is_mispriced"
                    class="pill-tip inline-flex items-center gap-1 whitespace-nowrap px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/55 cursor-help shadow-[0_0_10px_rgba(16,185,129,0.2)]"
                    :title="`Bookmaker Odds Mispricing: +${Number(b.edge_pp || 0).toFixed(1)}pp probability edge (${b.mispricing_drivers || 'Model Edge'})`"
                  >
                    <Icon icon="fa6-solid:wand-magic-sparkles" class="w-2.5 h-2.5" />
                    <span>EDGE +{{ Number(b.edge_pp || 0).toFixed(1) }}pp</span>
                  </span>
                </div>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums whitespace-nowrap">
                <div class="font-bold text-emerald-300">{{ (Number(b.win_prob || 0.5) * 100).toFixed(1) }}%</div>
                <div class="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden mt-1">
                  <div
                    class="h-full rounded-full"
                    :class="getWinProbBarColor(b.win_prob)"
                    :style="{ width: `${Math.min(100, Math.max(15, Number(b.win_prob || 0.5) * 100))}%` }"
                  ></div>
                </div>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums text-slate-200 whitespace-nowrap">
                {{ Number(b.min_fair_odds || 1.35).toFixed(2) }}
              </td>
              <td class="py-2.5 px-2.5">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-sky-300">
                    <template
                      v-for="(seg, sIdx) in parseScorePredictionSegments(b.exact_score_pick)"
                      :key="sIdx"
                    >
                      <span v-if="seg.separatorBefore" class="text-slate-400 font-normal">{{ seg.separatorBefore }}</span>
                      <b v-if="seg.isOver60" class="font-extrabold text-white">{{ seg.text }}</b>
                      <span v-else class="font-normal">{{ seg.text }}</span>
                    </template>
                  </span>
                  <button
                    v-if="b.score_cluster_items?.length"
                    type="button"
                    class="btn-press inline-flex items-center gap-1 whitespace-nowrap px-2 py-0.5 rounded-md text-[10px] font-bold bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-400/50 hover:bg-fuchsia-500/30"
                    @click="selectMatchForDutching(b.match)"
                  >
                    <Icon icon="fa6-solid:dice" class="w-3 h-3" />
                    <span>Split €</span>
                  </button>
                </div>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">
                <div class="flex flex-wrap items-center gap-1.5">
                  <b class="text-amber-300">{{ b.odds_display }}</b>
                  <span
                    class="whitespace-nowrap text-slate-300 cursor-help"
                    :title="CLV_TOOLTIP"
                  >
                    (CLV
                    <b :class="Number(b.clv_pct || 0) >= 0 ? 'text-emerald-300' : 'text-rose-400'">
                      {{ Number(b.clv_pct || 0) >= 0 ? '+' : '' }}{{ Number(b.clv_pct || 0).toFixed(1) }}%
                    </b>)
                  </span>
                  <span
                    v-if="Number(b.clv_pct || 0) >= 3.0"
                    class="pill-tip inline-flex items-center gap-1 whitespace-nowrap px-2 py-0.5 rounded-md text-[10px] font-bold bg-orange-500/20 text-orange-300 border border-orange-400/55 cursor-help"
                    :title="`Sharp Closing-Line Steam Move (+${Number(b.clv_pct || 0).toFixed(1)}% CLV)`"
                  >
                    <Icon icon="fa6-solid:fire" class="w-3 h-3" />
                    <span>STEAM +{{ Number(b.clv_pct || 0).toFixed(1) }}%</span>
                  </span>
                  <button
                    type="button"
                    class="btn-press inline-flex items-center p-1 rounded-md bg-slate-900 border border-slate-700 hover:border-sky-400 text-sky-300"
                    title="Share this pick + Notification Card to Discord / Telegram"
                    @click="openShareSinglePickModal(b)"
                  >
                    <Icon icon="fa6-solid:bullhorn" class="w-3 h-3" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- High-Probability Banker Profitability Booster Combos -->
      <section
        v-if="store.bankerBoosterCombos.length > 0"
        class="card-surface border border-emerald-400/50 rounded-2xl p-4 sm:p-5 mb-1"
      >
        <div class="flex flex-wrap justify-between items-center gap-2 mb-3.5">
          <div class="flex flex-wrap items-center gap-2">
            <Icon icon="fa6-solid:rocket" class="w-4 h-4 text-emerald-400" />
            <b class="text-sm text-emerald-300">High-Probability Banker Profitability Booster Combos</b>
            <span class="text-slate-300">
              Combines multiple high-win-probability (&ge;72%), lower-odds bankers into higher-yielding 2-Leg &amp;
              3-Leg multipliers
            </span>
          </div>
          <button
            type="button"
            class="btn-press inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold bg-slate-900 text-sky-300 border border-sky-400/50"
            @click="activeTab = 'studio'"
          >
            <Icon icon="fa6-solid:calculator" class="w-3.5 h-3.5" />
            <span>Customize Stake in Studio</span>
            <Icon icon="fa6-solid:arrow-right" class="w-3 h-3" />
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <div
            v-for="combo in store.bankerBoosterCombos"
            :key="combo.id"
            class="card-surface rounded-xl p-4 flex flex-col justify-between border-t-2 border-t-emerald-400"
          >
            <div>
              <div class="flex justify-between items-center gap-2 mb-1">
                <b class="text-white">{{ combo.title }}</b>
                <div class="flex items-center gap-1.5">
                  <span
                    class="inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded-md text-[10px] font-bold font-mono tabular-nums bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
                  >
                    +{{ combo.netYieldPct }}% PROFIT BOOST
                  </span>
                  <button
                    type="button"
                    class="btn-press inline-flex items-center p-1 rounded bg-slate-900 border border-slate-700 hover:border-sky-400 text-sky-300"
                    @click="openShareBoosterModal(combo)"
                  >
                    <Icon icon="fa6-solid:bullhorn" class="w-3 h-3" />
                  </button>
                </div>
              </div>
              <div class="text-slate-300 text-[11px] mb-2">{{ combo.description }}</div>
              <div class="divide-y divide-slate-800">
                <div
                  v-for="(leg, lIdx) in combo.legs"
                  :key="lIdx"
                  class="py-1 flex justify-between items-center text-[11.5px]"
                >
                  <span class="inline-flex items-center gap-1.5">
                    <span>{{ lIdx + 1 }}.</span>
                    <Icon
                      :icon="getSportIconify(leg.sport_cat)"
                      class="w-3.5 h-3.5 shrink-0"
                      :class="getSportIconColor(leg.sport_cat)"
                    />
                    <b class="text-white">{{ leg.pick_name || leg.pick }}</b>
                    <span class="text-slate-300">({{ leg.match }})</span>
                  </span>
                  <span class="font-mono tabular-nums whitespace-nowrap">
                    <b class="text-amber-300">{{ leg.odds.toFixed(2) }}</b>
                    <span class="text-emerald-300 ml-1">({{ (leg.win_prob * 100).toFixed(1) }}%)</span>
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-2.5 pt-2 border-t border-slate-700/60 flex justify-between items-center text-xs font-mono tabular-nums">
              <span>
                Combined Odds: <b class="text-amber-300">{{ combo.combinedOdds.toFixed(2) }}x</b>
                (Fair {{ combo.fairOdds.toFixed(2) }})
              </span>
              <span>
                Hit Prob: <b class="text-emerald-300">{{ (combo.combinedProb * 100).toFixed(1) }}%</b> · €100 &rarr;
                <b class="text-emerald-300">€{{ (100 * combo.combinedOdds).toFixed(2) }}</b>
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- TAB 2: BET SLIP, DUTCHING & COMBOS -->
    <div v-else-if="activeTab === 'studio'">
      <!-- Smart Bet Slip & Stake Allocation Optimizer -->
      <section class="card-surface rounded-2xl p-4 sm:p-5 mb-5">
        <div class="flex flex-wrap justify-between items-center gap-3 mb-3.5">
          <div class="flex flex-wrap items-center gap-2">
            <Icon icon="fa6-solid:calculator" class="w-4 h-4 text-sky-400" />
            <b class="text-sm text-sky-300">Smart Bet Slip &amp; Stake Allocation Optimizer</b>
            <span class="text-slate-300">
              Enter the exact amount (€) you want to bet — compares Safe Combos vs. Kelly-Weighted Singles vs. Hybrid
              65/35 Split
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <b>Ready to Bet (€):</b>
            <input
              v-model.number="betBudget"
              type="number"
              min="5"
              max="100000"
              step="5"
              class="w-24 bg-slate-950 text-emerald-300 border border-sky-400 rounded-lg px-2.5 py-1 text-xs font-extrabold font-mono tabular-nums"
            />
            <div class="flex gap-1">
              <button
                v-for="amt in [25, 50, 100, 250, 500]"
                :key="amt"
                type="button"
                class="btn-press px-2.5 py-1 rounded-full text-[11px] font-bold border tabular-nums"
                :class="
                  betBudget === amt
                    ? 'bg-sky-500/20 border-sky-400 text-sky-300'
                    : 'bg-slate-900 border-slate-700 text-slate-300'
                "
                @click="betBudget = amt"
              >
                €{{ amt }}
              </button>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <!-- Option A: Safe 2-Leg Combo -->
          <div class="card-surface border-t-2 border-t-emerald-400 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-1">
                <b>Option A · Safe {{ slipComboLegs.length }}-Leg Multiplier Combo</b>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tabular-nums bg-emerald-500/20 text-emerald-300 border border-emerald-400/50">
                  {{ (slipComboOdds || 1).toFixed(2) }}x
                </span>
              </div>
              <div class="text-slate-300 text-[11px] mb-2">
                Uncorrelated cross-league parlay maximizing total return on a single ticket
              </div>
              <div class="divide-y divide-slate-800">
                <div
                  v-for="(l, idx) in slipComboLegs"
                  :key="idx"
                  class="py-1 flex justify-between items-center text-[11.5px]"
                >
                  <span class="inline-flex items-center gap-1.5">
                    <span>{{ idx + 1 }}.</span>
                    <Icon
                      :icon="getSportIconify(l.sport_cat)"
                      class="w-3.5 h-3.5 shrink-0"
                      :class="getSportIconColor(l.sport_cat)"
                    />
                    <b>{{ l.pick_name || l.pick }}</b>
                    <span class="text-slate-300">({{ l.match }})</span>
                  </span>
                  <b class="font-mono tabular-nums text-amber-300">{{ l.odds.toFixed(2) }}</b>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-2 border-t border-slate-700/60 flex justify-between text-xs font-mono tabular-nums">
              <span>
                Stake: <b>€{{ betBudget.toFixed(2) }}</b> ({{ (slipComboProb * 100).toFixed(1) }}% Hit)
              </span>
              <span class="text-emerald-300 font-bold">
                Return: €{{ (betBudget * slipComboOdds).toFixed(2) }} (+€{{
                  (betBudget * (slipComboOdds - 1)).toFixed(2)
                }})
              </span>
            </div>
          </div>

          <!-- Option B: Kelly Singles Portfolio -->
          <div class="card-surface border-t-2 border-t-sky-400 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-1">
                <b>Option B · {{ slipSinglesAlloc.length }} Separate Individual Bets (Kelly Portfolio)</b>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50">
                  LOWEST VARIANCE
                </span>
              </div>
              <div class="text-slate-300 text-[11px] mb-2">
                Splits €{{ betBudget.toFixed(2) }} across {{ slipSinglesAlloc.length }} independent singles — one upset
                never wipes out your stake
              </div>
              <div class="divide-y divide-slate-800">
                <div
                  v-for="(s, idx) in slipSinglesAlloc"
                  :key="idx"
                  class="py-1 flex justify-between items-center text-[11.5px]"
                >
                  <span class="inline-flex items-center gap-1.5">
                    <Icon
                      :icon="getSportIconify(s.item.sport_cat)"
                      class="w-3.5 h-3.5 shrink-0"
                      :class="getSportIconColor(s.item.sport_cat)"
                    />
                    <b>{{ s.item.pick_name || s.item.pick }}</b>
                    <span class="text-slate-300">({{ s.item.odds.toFixed(2) }})</span>
                  </span>
                  <span class="font-mono tabular-nums">
                    Stake <b class="text-sky-300">€{{ s.stake.toFixed(2) }}</b> &rarr;
                    <b class="text-emerald-300">€{{ s.ret.toFixed(2) }}</b>
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-2 border-t border-slate-700/60 flex justify-between text-xs font-mono tabular-nums">
              <span>Total Budget: <b>€{{ betBudget.toFixed(2) }}</b></span>
              <span class="text-emerald-300 font-bold">
                All-Hit Return: €{{ slipSinglesTotalReturn.toFixed(2) }} (+€{{
                  (slipSinglesTotalReturn - betBudget).toFixed(2)
                }})
              </span>
            </div>
          </div>

          <!-- Option C: 65/35 Hybrid Split -->
          <div class="card-surface border-t-2 border-t-amber-400 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-1">
                <b>Option C · 65/35 Core Singles + Combo Booster</b>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/50">
                  OPTIMAL SHARPE
                </span>
              </div>
              <div class="text-slate-300 text-[11px] mb-2">
                65% (€{{ (betBudget * 0.65).toFixed(2) }}) on Top 2 Singles protects your floor + 35% (€{{
                  (betBudget * 0.35).toFixed(2)
                }}) on 2-Leg Combo for upside
              </div>
              <div class="space-y-1 text-[11.5px]">
                <div class="flex justify-between py-1 border-b border-slate-800">
                  <span>Core Single #1: <b>{{ slipComboLegs[0]?.pick_name || '—' }}</b></span>
                  <span class="font-mono tabular-nums">
                    €{{ (betBudget * 0.325).toFixed(2) }} &rarr;
                    <b class="text-emerald-300">
                      €{{ (betBudget * 0.325 * (slipComboLegs[0]?.odds || 1)).toFixed(2) }}
                    </b>
                  </span>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-800">
                  <span>Core Single #2: <b>{{ slipComboLegs[1]?.pick_name || '—' }}</b></span>
                  <span class="font-mono tabular-nums">
                    €{{ (betBudget * 0.325).toFixed(2) }} &rarr;
                    <b class="text-emerald-300">
                      €{{ (betBudget * 0.325 * (slipComboLegs[1]?.odds || 1)).toFixed(2) }}
                    </b>
                  </span>
                </div>
                <div class="flex justify-between py-1">
                  <span>2-Leg Combo Booster ({{ slipComboOdds.toFixed(2) }}x)</span>
                  <span class="font-mono tabular-nums">
                    €{{ (betBudget * 0.35).toFixed(2) }} &rarr;
                    <b class="text-emerald-300">€{{ (betBudget * 0.35 * slipComboOdds).toFixed(2) }}</b>
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-2 border-t border-slate-700/60 flex justify-between text-xs font-mono tabular-nums">
              <span>Floor Protection: <b>65% Core</b></span>
              <span class="text-emerald-300 font-bold">
                Full Sweep: €{{ slipHybridMaxReturn.toFixed(2) }} (+€{{ (slipHybridMaxReturn - betBudget).toFixed(2) }})
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Exact-Score & Set-Score Dutching Splitter -->
      <section class="card-surface rounded-2xl p-4 sm:p-5 mb-5">
        <div class="flex flex-wrap justify-between items-center gap-3 mb-3.5">
          <div class="flex flex-wrap items-center gap-2">
            <Icon icon="fa6-solid:dice" class="w-4 h-4 text-fuchsia-400" />
            <b class="text-sm text-fuchsia-300">Exact-Score &amp; Set-Score Dutching Investment Splitter</b>
            <span class="text-slate-300">
              Pick any high-conviction match and enter your investment (€) — generates 2-Score &amp; 3-Score
              equal-payout splits
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <b>Match:</b>
            <select
              v-model="selectedDutchMatch"
              class="max-w-[300px] bg-slate-950 text-white border border-slate-700 rounded-lg px-2.5 py-1 text-xs font-semibold"
            >
              <option v-for="m in dutchEligibleMatches" :key="m.match" :value="m.match">
                {{ m.match }} ({{ m.pick_name || m.pick }})
              </option>
            </select>
            <b>Investment (€):</b>
            <input
              v-model.number="dutchStake"
              type="number"
              min="5"
              max="100000"
              step="5"
              class="w-20 bg-slate-950 text-emerald-300 border border-fuchsia-400 rounded-lg px-2.5 py-1 text-xs font-extrabold font-mono tabular-nums"
            />
          </div>
        </div>

        <div v-if="dutchSplit2 && dutchSplit3" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="card-surface border-t-2 border-t-sky-400 rounded-xl p-4">
            <div class="flex justify-between items-center mb-2">
              <b>Option 1 · 2-Score Equal-Payout Dutching Split</b>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50 font-mono tabular-nums">
                {{ dutchSplit2.effectiveOdds.toFixed(2) }}x Effective Odds
              </span>
            </div>
            <div class="divide-y divide-slate-800">
              <div
                v-for="(leg, idx) in dutchSplit2.legs"
                :key="idx"
                class="py-1.5 flex justify-between items-center text-xs font-mono tabular-nums"
              >
                <span>
                  Score #{{ idx + 1 }}: <b>{{ leg.label }}</b> ({{ leg.odds.toFixed(2) }})
                </span>
                <span>
                  Place <b class="text-emerald-300">€{{ leg.stake.toFixed(2) }}</b> &rarr; Payout
                  <b>€{{ leg.payout.toFixed(2) }}</b>
                </span>
              </div>
            </div>
            <div class="mt-2.5 pt-2 border-t border-slate-700/60 flex justify-between text-xs font-mono tabular-nums">
              <span>Total Stake: <b>€{{ dutchSplit2.totalStake.toFixed(2) }}</b></span>
              <span class="text-emerald-300 font-bold">
                Equal Payout: €{{ dutchSplit2.totalPayout.toFixed(2) }} (+€{{ dutchSplit2.netProfit.toFixed(2) }})
              </span>
            </div>
          </div>

          <div class="card-surface border-t-2 border-t-fuchsia-400 rounded-xl p-4">
            <div class="flex justify-between items-center mb-2">
              <b>Option 2 · 3-Score Cluster Dutching Shield</b>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-400/50 font-mono tabular-nums">
                {{ dutchSplit3.effectiveOdds.toFixed(2) }}x Effective Odds
              </span>
            </div>
            <div class="divide-y divide-slate-800">
              <div
                v-for="(leg, idx) in dutchSplit3.legs"
                :key="idx"
                class="py-1.5 flex justify-between items-center text-xs font-mono tabular-nums"
              >
                <span>
                  Score #{{ idx + 1 }}: <b>{{ leg.label }}</b> ({{ leg.odds.toFixed(2) }})
                </span>
                <span>
                  Place <b class="text-emerald-300">€{{ leg.stake.toFixed(2) }}</b> &rarr; Payout
                  <b>€{{ leg.payout.toFixed(2) }}</b>
                </span>
              </div>
            </div>
            <div class="mt-2.5 pt-2 border-t border-slate-700/60 flex justify-between text-xs font-mono tabular-nums">
              <span>Total Stake: <b>€{{ dutchSplit3.totalStake.toFixed(2) }}</b></span>
              <span class="text-emerald-300 font-bold">
                Equal Payout: €{{ dutchSplit3.totalPayout.toFixed(2) }} (+€{{ dutchSplit3.netProfit.toFixed(2) }})
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Recommended 2-Leg High-Probability Combos -->
      <section v-if="store.recommendedDoubles.length">
        <h2 class="inline-flex items-center gap-2 text-sm font-bold text-sky-300 mb-2.5">
          <Icon icon="fa6-solid:link" class="w-4 h-4" />
          <span>Recommended 2-Leg High-Probability Combos &amp; Parlays ({{ store.recommendedDoubles.length }} Variations)</span>
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 mb-6">
          <div
            v-for="(d, idx) in store.recommendedDoubles"
            :key="idx"
            class="card-surface rounded-xl p-4 border-t-2 border-t-cyan-400"
          >
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50">
                  COMBO #{{ idx + 1 }}
                </span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/50">
                  {{ d.combo_label }}
                </span>
              </div>
              <div class="font-mono tabular-nums text-xs">
                Odds: <b class="text-amber-300">{{ Number(d.combined_odds).toFixed(2) }}</b> · WinProb:
                <b class="text-emerald-300">{{ (Number(d.combined_prob) * 100).toFixed(1) }}%</b>
              </div>
            </div>
            <div class="space-y-1 text-xs">
              <div class="inline-flex items-center gap-1.5 w-full">
                <span>1.</span>
                <Icon
                  :icon="getSportIconify(d.leg_1?.sport_cat || d.leg_1?.league)"
                  class="w-3.5 h-3.5 shrink-0"
                  :class="getSportIconColor(d.leg_1?.sport_cat || d.leg_1?.league)"
                />
                <b>{{ d.leg_1?.match }}</b> &rarr;
                <b class="text-emerald-300">{{ d.leg_1?.pick }}</b>
                <b class="font-mono tabular-nums text-amber-300">{{ Number(d.leg_1?.odds || 1).toFixed(2) }}</b>
              </div>
              <div class="inline-flex items-center gap-1.5 w-full">
                <span>2.</span>
                <Icon
                  :icon="getSportIconify(d.leg_2?.sport_cat || d.leg_2?.league)"
                  class="w-3.5 h-3.5 shrink-0"
                  :class="getSportIconColor(d.leg_2?.sport_cat || d.leg_2?.league)"
                />
                <b>{{ d.leg_2?.match }}</b> &rarr;
                <b class="text-emerald-300">{{ d.leg_2?.pick }}</b>
                <b class="font-mono tabular-nums text-amber-300">{{ Number(d.leg_2?.odds || 1).toFixed(2) }}</b>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- TAB 3: PAPER-BET LEDGER & ROI -->
    <div v-else-if="activeTab === 'ledger'">
      <h2 class="text-sm font-bold text-sky-300 mb-2">
        Settled Paper-Bets (Completed Results: <b class="text-white">{{ settledCount }}</b> · Wins:
        <b class="text-emerald-300">{{ settledWins }}W</b> · Losses:
        <b class="text-rose-400">{{ settledLosses }}L</b> · Realized Profit:
        <b class="text-emerald-300">{{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(2) }}u</b>)
      </h2>

      <div class="table-surface rounded-2xl overflow-x-auto mb-1">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase tracking-wider border-b border-slate-700/70 text-left">
              <th class="py-2.5 px-2.5 w-11 text-center">Sport</th>
              <th class="py-2.5 px-2.5">League</th>
              <th class="py-2.5 px-2.5">Kickoff</th>
              <th class="py-2.5 px-2.5">Matchup</th>
              <th class="py-2.5 px-2.5">Pick</th>
              <th class="py-2.5 px-2.5">Final Score</th>
              <th class="py-2.5 px-2.5">Odds</th>
              <th class="py-2.5 px-2.5">Result / PNL</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="tr in store.settledBets"
              :key="`${tr.league}:${tr.event_id}`"
              class="border-b border-slate-800/80 last:border-none hover:bg-slate-800/45"
            >
              <td class="py-2.5 px-2.5 text-center">
                <Icon
                  :icon="getSportIconify(tr.sport_cat)"
                  class="w-4 h-4 mx-auto"
                  :class="getSportIconColor(tr.sport_cat)"
                />
              </td>
              <td class="py-2.5 px-2.5">
                <span
                  class="inline-flex items-center gap-1.5 whitespace-nowrap px-2.5 py-0.5 rounded-md text-[10.5px] font-bold border"
                  :class="getSportBadgeTheme(tr.sport_cat || tr.league)"
                >
                  <Icon
                    v-if="getCompetitionFlagIconify(formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away), `${tr.league} ${tr.home} ${tr.away}`)"
                    :icon="getCompetitionFlagIconify(formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away), `${tr.league} ${tr.home} ${tr.away}`)!"
                    class="w-3.5 h-2.5 rounded-[2px] shrink-0"
                  />
                  <Icon v-else :icon="getSportIconify(tr.sport_cat || tr.league)" class="w-3.5 h-3.5 shrink-0" />
                  <span>{{ formatLeagueBadgeLabel(tr.league_label, tr.league, tr.home, tr.away) }}</span>
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums text-slate-400">{{ tr.kickoff_local || tr.kickoff }}</td>
              <td class="py-2.5 px-2.5">
                <button
                  type="button"
                  class="font-bold text-white hover:text-sky-300 text-left transition-colors cursor-pointer"
                  title="Click to inspect Match Details, H2H, Last-6 Form &amp; Score Matrix"
                  @click="openMatchupModal(tr.home, tr.away, tr.league)"
                >
                  {{ tr.home }} <span class="text-slate-400 font-normal">vs</span> {{ tr.away }}
                </button>
              </td>
              <td class="py-2.5 px-2.5">
                <b class="text-emerald-300">{{ tr.side === 'H' ? tr.home : tr.away }} ({{ tr.side }})</b>
                <span
                  class="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold border"
                  :class="getTierBadgeClass(tr.tier)"
                >
                  {{ tr.tier }}
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">
                <b class="text-white font-bold">{{ splitScoreAndInterim(tr.score_str || tr.settled_score || '—').main }}</b>
                <span
                  v-if="splitScoreAndInterim(tr.score_str || tr.settled_score || '').interim"
                  class="text-slate-400 font-normal ml-1 text-[11px]"
                >{{ splitScoreAndInterim(tr.score_str || tr.settled_score || '').interim }}</span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">
                <b class="text-amber-300">{{ Number(tr.logged_best_odds || 1.3).toFixed(2) }}</b>
              </td>
              <td class="py-2.5 px-2.5">
                <span
                  class="px-2 py-0.5 rounded text-[10.5px] font-bold border font-mono tabular-nums whitespace-nowrap"
                  :class="
                    Number(tr.pnl_best || 0) > 0
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/50'
                      : 'bg-rose-500/20 text-rose-300 border-rose-400/50'
                  "
                >
                  {{
                    Number(tr.pnl_best || 0) > 0
                      ? `WIN (+${Number(tr.pnl_best).toFixed(2)}u)`
                      : `LOSS (${Number(tr.pnl_best).toFixed(2)}u)`
                  }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 4: MODEL AUDIT & BACKTEST -->
    <div v-else-if="activeTab === 'audit'">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-1">
        <div class="card-surface rounded-2xl p-4 border-t-2 border-t-emerald-400">
          <b class="inline-flex items-center gap-1.5 text-sm text-emerald-300 mb-2">
            <Icon icon="fa6-solid:chart-line" class="w-4 h-4" />
            <span>By-Sport Settled Attribution</span>
          </b>
          <table class="w-full border-collapse text-xs">
            <thead>
              <tr class="text-left text-[11px] uppercase text-slate-300 border-b border-slate-700">
                <th class="py-2">Sport Group</th>
                <th class="py-2">Settled (W–L)</th>
                <th class="py-2">Win Rate</th>
                <th class="py-2">Profit (u)</th>
                <th class="py-2">ROI%</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="s in store.paperLedger?.by_sport || []"
                :key="s.sport"
                class="border-b border-slate-800 last:border-none"
              >
                <td class="py-2 font-bold text-white">{{ s.sport }}</td>
                <td class="py-2 font-mono tabular-nums">
                  {{ s.settled }} (<b class="text-emerald-300">{{ s.wins }}W</b> –
                  <b class="text-rose-400">{{ s.losses }}L</b>)
                </td>
                <td class="py-2 font-mono tabular-nums font-bold">{{ Number(s.win_rate_pct || 0).toFixed(1) }}%</td>
                <td
                  class="py-2 font-mono tabular-nums font-bold"
                  :class="Number(s.profit_u || 0) >= 0 ? 'text-emerald-300' : 'text-rose-400'"
                >
                  {{ Number(s.profit_u || 0) >= 0 ? '+' : '' }}{{ Number(s.profit_u || 0).toFixed(2) }}u
                </td>
                <td
                  class="py-2 font-mono tabular-nums font-bold"
                  :class="Number(s.roi_pct || 0) >= 0 ? 'text-cyan-300' : 'text-rose-400'"
                >
                  {{ Number(s.roi_pct || 0) >= 0 ? '+' : '' }}{{ Number(s.roi_pct || 0).toFixed(1) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card-surface rounded-2xl p-4 border-t-2 border-t-violet-400">
          <b class="inline-flex items-center gap-1.5 text-sm text-violet-300 mb-2">
            <Icon icon="fa6-solid:microscope" class="w-4 h-4" />
            <span>Calibration &amp; Tier Attribution</span>
          </b>
          <table class="w-full border-collapse text-xs">
            <thead>
              <tr class="text-left text-[11px] uppercase text-slate-300 border-b border-slate-700">
                <th class="py-2">Tier</th>
                <th class="py-2">Settled (W–L)</th>
                <th class="py-2">Exp Win%</th>
                <th class="py-2">Realized Win%</th>
                <th class="py-2">ROI%</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="t in store.paperLedger?.by_tier || []"
                :key="t.tier"
                class="border-b border-slate-800 last:border-none"
              >
                <td class="py-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold border" :class="getTierBadgeClass(t.tier)">
                    {{ t.tier }}
                  </span>
                </td>
                <td class="py-2 font-mono tabular-nums">
                  {{ t.settled }} (<b class="text-emerald-300">{{ t.wins }}W</b> –
                  <b class="text-rose-400">{{ t.losses }}L</b>)
                </td>
                <td class="py-2 font-mono tabular-nums">{{ Number(t.expected_win_pct || 0).toFixed(1) }}%</td>
                <td class="py-2 font-mono tabular-nums font-bold text-emerald-300">
                  {{ Number(t.realized_win_pct || 0).toFixed(1) }}%
                </td>
                <td
                  class="py-2 font-mono tabular-nums font-bold"
                  :class="Number(t.roi_pct || 0) >= 0 ? 'text-cyan-300' : 'text-rose-400'"
                >
                  {{ Number(t.roi_pct || 0) >= 0 ? '+' : '' }}{{ Number(t.roi_pct || 0).toFixed(1) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
      </div>
    </div>

    <!-- App Footer -->
    <footer class="border-t border-slate-700/45 pt-4 mt-4 text-[11.5px] text-slate-400 flex flex-wrap justify-between items-center gap-3">
      <div class="flex items-center gap-2">
        <img src="/betscout-logo.svg?v=7.3" width="18" height="18" alt="BetScout" class="rounded" />
        <span>
          &copy; {{ currentYear }} <strong class="text-slate-200">BetScout</strong> · Quantitative Sports Edge &amp;
          Score Intelligence. All rights reserved.
        </span>
      </div>
      <div class="font-mono text-[11px] text-slate-400/95 bg-slate-900/65 border border-slate-700/50 px-2.5 py-0.5 rounded-full">
        v{{ appVersion }} ({{ commitHash }})
      </div>
      <div class="flex flex-wrap gap-4">
        <router-link to="/" class="hover:text-white">Home &amp; Membership Plans</router-link>
        <router-link to="/docs" class="hover:text-white text-sky-300 font-semibold">User Guide</router-link>
        <a href="/api/docs" target="_blank" class="hover:text-white">API Documentation</a>
      </div>
    </footer>

    <!-- FLOATING CUSTOM SLIP DOCK (Appears when >=1 matches checked) -->
    <div
      v-if="store.customSelectedMatches.size > 0"
      class="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex flex-wrap items-center gap-4 bg-slate-950/95 border border-emerald-400/70 rounded-2xl px-5 py-3 shadow-2xl backdrop-blur-xl"
    >
      <div class="flex items-center gap-2">
        <span
          class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-emerald-500/20 text-emerald-300 tabular-nums"
        >
          <Icon icon="fa6-solid:square-check" class="w-3.5 h-3.5" />
          <span>{{ store.customSelectedMatches.size }} Selected</span>
        </span>
        <span class="text-xs text-slate-200 font-mono tabular-nums">
          Combined Odds: <b class="text-amber-300">{{ customSlipCombinedOdds.toFixed(2) }}x</b>
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="btn-press inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-extrabold bg-gradient-to-r from-emerald-400 to-teal-300 text-slate-950"
          @click="activeTab = 'studio'"
        >
          <Icon icon="fa6-solid:calculator" class="w-3.5 h-3.5" />
          <span>Optimize in Bet Slip Studio</span>
          <Icon icon="fa6-solid:arrow-right" class="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          class="btn-press inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 text-slate-200 border border-slate-700"
          @click="store.clearCustomSelection()"
        >
          <Icon icon="fa6-solid:xmark" class="w-3.5 h-3.5" />
          <span>Clear</span>
        </button>
      </div>
    </div>

    <!-- MODAL 1: MATCHUP DRILL-DOWN INSPECTOR -->
    <div
      v-if="inspectorModalOpen"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="inspectorModalOpen = false"
    >
      <div class="card-surface rounded-2xl max-w-[680px] w-full max-h-[78vh] flex flex-col p-5">
        <div class="flex justify-between items-center gap-2 mb-3 pb-2.5 border-b border-slate-700 shrink-0">
          <b class="inline-flex items-center gap-1.5 text-sm text-sky-300">
            <Icon icon="fa6-solid:magnifying-glass" class="w-4 h-4 shrink-0" />
            <span class=" whitespace-nowrap">{{ inspectorTitle }}</span>
          </b>
          <div class="flex items-center gap-2 shrink-0">
            <router-link
              v-if="inspectorData && !inspectorLockedPro"
              :to="
                inspectorData.sr_match_id
                  ? `/match/${inspectorData.sr_match_id}`
                  : `/match/lookup?home=${encodeURIComponent(inspectorData.home || '')}&away=${encodeURIComponent(inspectorData.away || '')}&league=${encodeURIComponent(inspectorData.league || '')}`
              "
              class="btn-press h-8 px-3 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-400/50 text-xs font-semibold leading-none inline-flex items-center justify-center gap-1.5 no-underline whitespace-nowrap"
              @click="inspectorModalOpen = false"
            >
              <span>Full Match Center</span>
              <Icon icon="fa6-solid:arrow-right" class="w-3.5 h-3.5 shrink-0" />
            </router-link>
            <button
              type="button"
              class="btn-press h-8 px-3 rounded-lg bg-slate-900 text-slate-200 border border-slate-700 text-xs font-semibold leading-none inline-flex items-center justify-center gap-1.5 whitespace-nowrap"
              @click="inspectorModalOpen = false"
            >
              <span>Close</span>
              <Icon icon="fa6-solid:xmark" class="w-3.5 h-3.5 shrink-0" />
            </button>
          </div>
        </div>
        <div class="relative flex-1 min-h-0 flex">
          <div
            ref="inspectorScrollRef"
            class="custom-scrollbar flex-1 min-h-0 pr-3"
            @scroll="updateInspectorScrollbar"
          >
        <div v-if="inspectorLoading" class="py-8 px-4 flex flex-col items-center justify-center gap-3 text-slate-300">
          <div class="inline-flex items-center gap-2 text-xs font-semibold text-sky-300">
            <Icon icon="fa6-solid:arrows-rotate" class="w-3.5 h-3.5 animate-spin text-sky-400" />
            <span>Loading H2H, Last-6 Form &amp; Score Matrix...</span>
          </div>
          <div
            role="progressbar"
            aria-label="Loading match details"
            class="w-full max-w-[300px] h-1.5 rounded-full bg-slate-900/95 border border-slate-700/80 overflow-hidden"
          >
            <div class="modal-loading-bar"></div>
          </div>
        </div>
        <div v-else-if="inspectorLockedPro" class="p-4 bg-slate-900 border border-sky-400/40 rounded-xl text-center">
          <div class="inline-flex items-center gap-1.5 text-base font-extrabold text-white mb-1.5">
            <Icon icon="fa6-solid:lock" class="w-4 h-4 text-amber-400" />
            <span>BetScout Pro Subscriber Pick</span>
          </div>
          <div class="text-slate-300 mb-4">
            Full matchup names, H2H history, Dixon-Coles exact-score matrices &amp; 2-leg combos are reserved for
            active <b>BetScout Pro</b> members.
          </div>
          <div class="flex justify-center gap-3">
            <button
              type="button"
              class="btn-press inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-400/50 font-bold"
              @click="
                inspectorModalOpen = false;
                store.triggerSignInOut();
              "
            >
              <Icon icon="fa6-solid:lock" class="w-3.5 h-3.5" />
              <span>Sign In with Google</span>
            </button>
            <router-link
              to="/#pricing"
              class="btn-press inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 font-bold no-underline"
              @click="inspectorModalOpen = false"
            >
              <Icon icon="fa6-solid:rocket" class="w-3.5 h-3.5" />
              <span>View Membership Plans</span>
              <Icon icon="fa6-solid:arrow-right" class="w-3.5 h-3.5" />
            </router-link>
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

          <!-- Seamless 2-Way / 3-Way Win Probability Bar -->
          <div
            v-if="inspectorData.win_prob_bar"
            class="p-3 rounded-xl bg-slate-900/75 border border-slate-800"
          >
            <div class="flex justify-between items-center text-[11.5px] font-bold font-mono tabular-nums mb-1.5">
              <span class="text-sky-300">
                {{ inspectorData.home }} — {{ inspectorData.win_prob_bar.home_pct }}%<span v-if="inspectorData.win_prob_bar.odds_home" class="text-slate-400 font-normal ml-1">({{ Number(inspectorData.win_prob_bar.odds_home).toFixed(2) }})</span>
              </span>
              <span v-if="Number(inspectorData.win_prob_bar.draw_pct || 0) > 0.5" class="text-slate-300">
                Draw — {{ inspectorData.win_prob_bar.draw_pct }}%<span v-if="inspectorData.win_prob_bar.odds_draw" class="text-slate-400 font-normal ml-1">({{ Number(inspectorData.win_prob_bar.odds_draw).toFixed(2) }})</span>
              </span>
              <span class="text-amber-300">
                {{ inspectorData.away }} — {{ inspectorData.win_prob_bar.away_pct }}%<span v-if="inspectorData.win_prob_bar.odds_away" class="text-slate-400 font-normal ml-1">({{ Number(inspectorData.win_prob_bar.odds_away).toFixed(2) }})</span>
              </span>
            </div>
            <div class="h-2.5 rounded-full bg-slate-950 overflow-hidden flex gap-0">
              <div
                class="h-full bg-gradient-to-r from-sky-500 to-cyan-400"
                :style="{ width: `${inspectorData.win_prob_bar.home_pct}%` }"
              ></div>
              <div
                v-if="Number(inspectorData.win_prob_bar.draw_pct || 0) > 0.5"
                class="h-full bg-gradient-to-r from-slate-500 to-slate-400"
                :style="{ width: `${inspectorData.win_prob_bar.draw_pct}%` }"
              ></div>
              <div
                class="h-full bg-gradient-to-r from-amber-500 to-rose-500"
                :style="{ width: `${inspectorData.win_prob_bar.away_pct}%` }"
              ></div>
            </div>
          </div>

          <!-- Surface Splits or Missing/Injured Players Telemetry -->
          <div
            v-if="
              inspectorData.live_intel?.tennis_surface_records?.home ||
              inspectorData.live_intel?.home_injuries?.length ||
              inspectorData.live_intel?.away_injuries?.length
            "
            class="p-3 rounded-xl bg-slate-900/75 border border-slate-800 space-y-1.5 text-[11.5px]"
          >
            <div
              v-if="inspectorData.live_intel?.tennis_surface_records?.home || inspectorData.live_intel?.tennis_surface_records?.away"
              class="flex flex-wrap justify-between gap-2 font-mono tabular-nums"
            >
              <span v-if="inspectorData.live_intel.tennis_surface_records.home" class="text-slate-300">
                <b class="text-sky-300">{{ inspectorData.home }}:</b>
                Season <b class="text-white">{{ inspectorData.live_intel.tennis_surface_records.home.season_wl }}</b>
                (Hard {{ inspectorData.live_intel.tennis_surface_records.home.hard_wl }} · Indoor {{ inspectorData.live_intel.tennis_surface_records.home.indoor_wl }} · Clay {{ inspectorData.live_intel.tennis_surface_records.home.clay_wl }})
              </span>
              <span v-if="inspectorData.live_intel.tennis_surface_records.away" class="text-slate-300">
                <b class="text-amber-300">{{ inspectorData.away }}:</b>
                Season <b class="text-white">{{ inspectorData.live_intel.tennis_surface_records.away.season_wl }}</b>
                (Hard {{ inspectorData.live_intel.tennis_surface_records.away.hard_wl }} · Indoor {{ inspectorData.live_intel.tennis_surface_records.away.indoor_wl }} · Clay {{ inspectorData.live_intel.tennis_surface_records.away.clay_wl }})
              </span>
            </div>
            <div v-if="inspectorData.live_intel?.home_injuries?.length" class="text-slate-300">
              <b class="text-rose-300">{{ inspectorData.home }} Missing ({{ inspectorData.live_intel.home_injuries.length }}):</b>
              <span class="ml-1 text-slate-400">{{ inspectorData.live_intel.home_injuries.slice(0, 6).join(', ') }}</span>
            </div>
            <div v-if="inspectorData.live_intel?.away_injuries?.length" class="text-slate-300">
              <b class="text-rose-300">{{ inspectorData.away }} Missing ({{ inspectorData.live_intel.away_injuries.length }}):</b>
              <span class="ml-1 text-slate-400">{{ inspectorData.live_intel.away_injuries.slice(0, 6).join(', ') }}</span>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <div class="flex items-center gap-2.5 mb-2">
                <div
                  v-if="inspectorData.home_headshot_url"
                  class="w-9 h-9 rounded-xl border-2 border-sky-400/50 bg-slate-900/90 shrink-0 overflow-hidden flex items-center justify-center"
                >
                  <img
                    :src="inspectorData.home_headshot_url"
                    :alt="inspectorData.home"
                    class="w-full h-full"
                    :class="inspectorData.home_is_club ? 'object-contain p-1' : 'object-cover object-top rounded-[9px]'"
                  />
                </div>
                <b class="text-white">{{ inspectorData.home }} — Last 6</b>
              </div>
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
              <div class="flex items-center gap-2.5 mb-2">
                <div
                  v-if="inspectorData.away_headshot_url"
                  class="w-9 h-9 rounded-xl border-2 border-amber-400/50 bg-slate-900/90 shrink-0 overflow-hidden flex items-center justify-center"
                >
                  <img
                    :src="inspectorData.away_headshot_url"
                    :alt="inspectorData.away"
                    class="w-full h-full"
                    :class="inspectorData.away_is_club ? 'object-contain p-1' : 'object-cover object-top rounded-[9px]'"
                  />
                </div>
                <b class="text-white">{{ inspectorData.away }} — Last 6</b>
              </div>
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
            <div
              v-if="inspectorData.h2h_edge && inspectorData.h2h_edge.total_meetings > 0"
              class="mb-2.5 p-2.5 rounded-xl bg-slate-900/75 border border-slate-800"
            >
              <div class="flex justify-between items-center text-[11px] font-bold font-mono tabular-nums mb-1.5">
                <span class="text-sky-300">
                  {{ inspectorData.home }}: {{ inspectorData.h2h_edge.home_wins }}W ({{ inspectorData.h2h_edge.home_win_pct }}%)
                </span>
                <span v-if="inspectorData.h2h_edge.draws > 0" class="text-slate-300">
                  {{ inspectorData.h2h_edge.draws }}D ({{ inspectorData.h2h_edge.draw_pct }}%)
                </span>
                <span class="text-amber-300">
                  {{ inspectorData.away }}: {{ inspectorData.h2h_edge.away_wins }}W ({{ inspectorData.h2h_edge.away_win_pct }}%)
                </span>
              </div>
              <div class="h-2 rounded-full bg-slate-950 overflow-hidden flex gap-0">
                <div
                  class="h-full bg-gradient-to-r from-sky-500 to-cyan-400"
                  :style="{ width: `${inspectorData.h2h_edge.home_win_pct}%` }"
                ></div>
                <div
                  v-if="inspectorData.h2h_edge.draw_pct > 0"
                  class="h-full bg-gradient-to-r from-slate-500 to-slate-400"
                  :style="{ width: `${inspectorData.h2h_edge.draw_pct}%` }"
                ></div>
                <div
                  class="h-full bg-gradient-to-r from-amber-500 to-rose-500"
                  :style="{ width: `${inspectorData.h2h_edge.away_win_pct}%` }"
                ></div>
              </div>
            </div>
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
          <!-- Always-Visible Styled Vertical Scrollbar Rail (macOS overlay-proof) -->
          <div
            class="w-2.5 rounded-full bg-slate-950/95 border border-sky-400/35 relative shrink-0 ml-1.5 my-0.5 overflow-hidden cursor-pointer select-none"
            aria-hidden="true"
            @mousedown="onInspectorRailMouseDown"
          >
            <div
              class="w-full rounded-full bg-gradient-to-b from-sky-400 to-emerald-400 shadow-[0_0_10px_rgba(56,189,248,0.55)] transition-[top,height] duration-75"
              :style="{
                position: 'absolute',
                left: '0',
                top: `${inspectorThumbTopPct}%`,
                height: `${inspectorThumbHeightPct}%`,
              }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL 2: ON-DEMAND LIVE MATCHUP ANALYZER -->
    <div
      v-if="analyzerModalOpen"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="analyzerModalOpen = false"
    >
      <div class="card-surface rounded-2xl max-w-[740px] w-full max-h-[85vh] overflow-y-auto p-5">
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-slate-700">
          <div>
            <b class="inline-flex items-center gap-1.5 text-sm text-emerald-300">
              <Icon icon="fa6-solid:magnifying-glass" class="w-4 h-4" />
              <span>On-Demand Any-Matchup Live Analyzer</span>
            </b>
            <div class="text-slate-300 text-[11px]">
              Analyze any Tennis or Football matchup — checks live bookmaker odds, Last-5 form, H2H &amp; turnaround
            </div>
          </div>
          <button
            type="button"
            class="btn-press h-8 px-3 rounded-lg bg-slate-900 text-slate-200 border border-slate-700 text-xs font-semibold leading-none inline-flex items-center justify-center gap-1.5"
            @click="analyzerModalOpen = false"
          >
            <span>Close</span>
            <Icon icon="fa6-solid:xmark" class="w-3.5 h-3.5 shrink-0" />
          </button>
        </div>

        <div class="flex gap-2 mb-3">
          <input
            v-model="analyzerQuery"
            type="search"
            placeholder="e.g. Shelton vs Kovacevic, Roma vs Cagliari..."
            class="flex-1 h-8 bg-slate-950 text-white border border-slate-700 rounded-lg px-3 text-xs"
            @keydown.enter="runLiveAnalyzer"
          />
          <button
            type="button"
            class="btn-press h-8 px-3.5 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-400/50 text-xs font-semibold leading-none inline-flex items-center justify-center gap-1.5"
            @click="runLiveAnalyzer"
          >
            <Icon icon="fa6-solid:bolt" class="w-3.5 h-3.5 shrink-0" />
            <span>Analyze Matchup</span>
          </button>
        </div>

        <div v-if="analyzerLoading" class="py-4 text-slate-300">Running live multi-market analysis...</div>
        <div v-else-if="analyzerResult" class="p-3.5 bg-slate-950 border border-slate-700 rounded-xl space-y-2">
          <div class="text-sm font-bold text-white">
            {{ analyzerResult.home }} vs {{ analyzerResult.away }}
            <span class="text-sky-300 ml-2">({{ analyzerResult.verdict || analyzerResult.sport || 'Analyzed' }})</span>
          </div>
          <div v-if="analyzerResult.summary" class="text-slate-200">{{ analyzerResult.summary }}</div>
          <pre v-else class="text-[11px] font-mono text-slate-200 whitespace-pre-wrap">{{
            JSON.stringify(analyzerResult, null, 2)
          }}</pre>
        </div>
      </div>
    </div>

    <!-- MODAL 3: SHARE PICK & NOTIFICATION CARD GENERATOR -->
    <div
      v-if="shareModalOpen"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="shareModalOpen = false"
    >
      <div class="card-surface custom-scrollbar rounded-2xl max-w-[720px] w-full max-h-[90vh] overflow-y-auto p-5">
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-slate-700">
          <b class="inline-flex items-center gap-1.5 text-sm text-emerald-300">
            <Icon icon="fa6-solid:share-nodes" class="w-4 h-4" />
            <span>Share Pick &amp; High-Res Notification Card Publisher</span>
          </b>
          <button
            type="button"
            class="btn-press h-8 px-3 rounded-lg bg-slate-900 text-slate-200 border border-slate-700 text-xs font-semibold leading-none inline-flex items-center justify-center gap-1.5"
            @click="shareModalOpen = false"
          >
            <span>Close</span>
            <Icon icon="fa6-solid:xmark" class="w-3.5 h-3.5 shrink-0" />
          </button>
        </div>

        <div class="bg-slate-950 border border-slate-700 rounded-xl p-2.5 mb-3">
          <div class="flex justify-between items-center mb-1.5">
            <span class="text-[11px] font-bold text-sky-300">Generated Notification Card (1080×560)</span>
            <button
              type="button"
              class="btn-press h-7 inline-flex items-center justify-center gap-1.5 px-2.5 rounded-lg bg-slate-900 border border-slate-700 text-[11px] font-semibold leading-none"
              @click="downloadCanvasPng"
            >
              <Icon icon="fa6-solid:download" class="w-3 h-3 text-sky-400 shrink-0" />
              <span>Download Notification Card</span>
            </button>
          </div>
          <canvas
            ref="pickCardCanvasRef"
            width="1080"
            height="560"
            class="w-full h-auto rounded-lg border border-slate-700 block"
          ></canvas>
        </div>

        <textarea
          v-model="shareMessageText"
          rows="6"
          class="w-full bg-slate-950 text-slate-100 border border-slate-700 rounded-xl p-2.5 font-mono text-xs mb-3"
        ></textarea>

        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="btn-press h-8 inline-flex items-center justify-center gap-1.5 px-3 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold leading-none"
            @click="copyShareMessage"
          >
            <Icon icon="fa6-solid:copy" class="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span>Copy Text</span>
          </button>
          <button
            type="button"
            class="btn-press h-8 inline-flex items-center justify-center gap-1.5 px-3.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 text-xs font-semibold leading-none"
            @click="postShareToDiscord"
          >
            <Icon icon="fa6-solid:rocket" class="w-3.5 h-3.5 shrink-0" />
            <span>Send to Discord</span>
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL 4: SETTINGS MODAL -->
    <div
      v-if="settingsModalOpen"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="settingsModalOpen = false"
    >
      <div class="card-surface custom-scrollbar rounded-2xl max-w-[640px] w-full max-h-[85vh] overflow-y-auto p-5">
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-slate-700">
          <b class="inline-flex items-center gap-1.5 text-sm text-sky-300">
            <Icon icon="fa6-solid:gear" class="w-4 h-4" />
            <span>BetScout Settings, PWA Cache &amp; Sport Toggles</span>
          </b>
          <button
            type="button"
            class="btn-press h-8 px-3 rounded-lg bg-slate-900 text-slate-200 border border-slate-700 text-xs font-semibold leading-none inline-flex items-center justify-center gap-1.5"
            @click="settingsModalOpen = false"
          >
            <span>Close</span>
            <Icon icon="fa6-solid:xmark" class="w-3.5 h-3.5 shrink-0" />
          </button>
        </div>

        <div class="space-y-4">
          <div class="p-3.5 bg-slate-950/90 border border-slate-700 rounded-xl">
            <b class="block text-emerald-300 mb-2">Active Sports On/Off Filter</b>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <label
                v-for="(lbl, spKey) in sportToggleItems"
                :key="spKey"
                class="flex items-center gap-2 cursor-pointer text-xs"
              >
                <input
                  type="checkbox"
                  :checked="!store.disabledSports.has(spKey)"
                  class="accent-emerald-400"
                  @change="store.toggleSportEnabled(spKey)"
                />
                <Icon
                  :icon="SPORT_ICONIFY_NAMES[spKey] || 'fa6-solid:award'"
                  class="w-3.5 h-3.5"
                  :class="getSportIconColor(spKey)"
                />
                <span>{{ lbl }}</span>
              </label>
            </div>
          </div>

          <div class="p-3.5 bg-slate-950/90 border border-slate-700 rounded-xl flex justify-between items-center">
            <span>Display Timezone:</span>
            <div class="flex gap-1.5">
              <button
                type="button"
                class="btn-press px-2.5 py-1 rounded-lg text-xs font-semibold border"
                :class="
                  store.tzMode === 'local'
                    ? 'bg-sky-500/20 border-sky-400 text-sky-300'
                    : 'bg-slate-900 border-slate-700 text-slate-300'
                "
                @click="store.tzMode = 'local'"
              >
                Local ({{ store.timezone }})
              </button>
              <button
                type="button"
                class="btn-press px-2.5 py-1 rounded-lg text-xs font-semibold border"
                :class="
                  store.tzMode === 'utc'
                    ? 'bg-sky-500/20 border-sky-400 text-sky-300'
                    : 'bg-slate-900 border-slate-700 text-slate-300'
                "
                @click="store.tzMode = 'utc'"
              >
                UTC
              </button>
            </div>
          </div>

          <div class="p-3.5 bg-slate-950/90 border border-slate-700 rounded-xl flex flex-wrap justify-between items-center gap-2">
            <div>
              <b class="text-cyan-300 block">Local Cache &amp; Multi-Tier Data Cache</b>
              <span class="text-[11px] text-slate-300">
                Last cached snapshot: {{ store.lastLocalCacheTime || 'Active' }}
                <template v-if="store.gismoCache?.hit_rate_pct !== undefined">
                  · Cache Hit Rate: <b class="text-emerald-300">{{ store.gismoCache.hit_rate_pct }}%</b>
                  (L1: {{ store.gismoCache.l1_memory_entries || 0 }}, L2 Persistent: {{ store.gismoCache.l2_sqlite_entries || 0 }})
                </template>
              </span>
            </div>
            <button
              type="button"
              class="btn-press inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50"
              @click="store.fetchSnapshot()"
            >
              <Icon icon="fa6-solid:arrows-rotate" class="w-3.5 h-3.5" />
              <span>Force Refresh Snapshot</span>
            </button>
          </div>

          <!-- Quant API Key & Remote MCP Connection Panel -->
          <div class="p-3.5 bg-slate-950/90 border border-sky-500/40 rounded-xl space-y-2.5 text-xs">
            <div class="flex flex-wrap justify-between items-center gap-2">
              <b class="text-sky-300 inline-flex items-center gap-1.5">
                <Icon icon="fa6-solid:lock" class="w-3.5 h-3.5 text-amber-300" />
                <span>Tier 3 Quant API Key &amp; Remote MCP (`https://betscout.app/mcp`)</span>
              </b>
              <router-link
                to="/docs#mcp"
                class="text-[11px] font-bold text-emerald-300 hover:underline no-underline"
                @click="settingsModalOpen = false"
              >
                Full MCP &amp; User Guide &rarr;
              </router-link>
            </div>
            <div class="flex gap-2">
              <input
                v-model="apiKeyInput"
                type="text"
                placeholder="Paste your bs_live_... API key"
                class="flex-1 h-8 bg-slate-900 text-white border border-slate-700 rounded-lg px-2.5 font-mono text-xs"
              />
              <button
                type="button"
                class="btn-press h-8 px-3 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 text-xs font-semibold leading-none inline-flex items-center justify-center"
                @click="store.setCustomApiKey(apiKeyInput)"
              >
                Save Key
              </button>
              <button
                type="button"
                class="btn-press h-8 px-3 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-400/50 text-xs font-semibold leading-none inline-flex items-center justify-center"
                @click="copyRemoteMcpConfig"
              >
                Copy MCP Config
              </button>
            </div>
          </div>

          <!-- Admin API Keys & Subscribers Provisioning Panel -->
          <div
            v-if="store.isAdmin"
            class="p-3.5 bg-slate-950/90 border border-amber-500/40 rounded-xl space-y-3 text-xs"
          >
            <div class="flex justify-between items-center">
              <b class="text-amber-300 inline-flex items-center gap-1.5">
                <Icon icon="fa6-solid:shield-halved" class="w-3.5 h-3.5" />
                <span>Admin · Issued API Keys ({{ store.monetizationCfg?.api_keys?.length || 0 }}) &amp; Subscribers</span>
              </b>
            </div>

            <div class="flex flex-wrap gap-2 items-center">
              <input
                v-model="newKeyEmail"
                type="email"
                placeholder="owner@email.com"
                class="flex-1 min-w-[160px] bg-slate-900 text-white border border-slate-700 rounded-lg px-2.5 py-1 text-xs"
              />
              <select
                v-model="newKeyTier"
                class="bg-slate-900 text-white border border-slate-700 rounded-lg px-2 py-1 text-xs font-semibold"
              >
                <option value="starter">starter (500/d)</option>
                <option value="pro">pro (5,000/d)</option>
                <option value="enterprise">enterprise (50,000/d)</option>
              </select>
              <input
                v-model="newKeyLabel"
                type="text"
                placeholder="Label (optional)"
                class="w-32 bg-slate-900 text-white border border-slate-700 rounded-lg px-2.5 py-1 text-xs"
              />
              <button
                type="button"
                class="btn-press px-3 py-1 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-400/50 font-bold"
                @click="handleIssueAdminKey"
              >
                + Issue Key
              </button>
            </div>

            <div
              v-if="newlyIssuedPlainKey"
              class="p-2.5 rounded-lg bg-emerald-500/15 border border-emerald-400/50 flex justify-between items-center gap-2 font-mono text-[11px]"
            >
              <span class="text-emerald-200 break-all">
                New Key (copy now): <b class="text-white">{{ newlyIssuedPlainKey }}</b>
              </span>
              <button
                type="button"
                class="btn-press px-2.5 py-1 rounded bg-emerald-500/30 text-white font-bold shrink-0"
                @click="copyPlainKey(newlyIssuedPlainKey)"
              >
                Copy
              </button>
            </div>

            <div v-if="store.monetizationCfg?.api_keys?.length" class="max-h-36 overflow-y-auto divide-y divide-slate-800">
              <div
                v-for="k in store.monetizationCfg.api_keys"
                :key="k.key_id"
                class="py-1.5 flex justify-between items-center gap-2 font-mono text-[11px]"
              >
                <div>
                  <b class="text-sky-300">{{ k.key_prefix }}</b>
                  <span class="text-slate-300 ml-1.5">{{ k.owner_email }}</span>
                  <span class="ml-1.5 px-1.5 py-0.5 rounded bg-slate-800 text-amber-300 text-[10px]">{{ k.plan_tier }}</span>
                  <span class="text-slate-400 ml-1.5">{{ k.calls_today || 0 }} / {{ k.daily_limit }} today</span>
                </div>
                <button
                  v-if="k.active"
                  type="button"
                  class="btn-press px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-400/40 text-[10px] font-bold"
                  @click="store.revokeAdminApiKey(k.key_id)"
                >
                  Revoke
                </button>
                <span v-else class="text-rose-400 text-[10px] font-bold">REVOKED</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { Icon } from '@iconify/vue';
import { useBetscoutStore } from '../stores/betscoutStore';
import {
  type BankerBoosterCombo,
  type BestBetItem,
  CLV_TOOLTIP,
  SPORT_CLEAN_LABELS,
  SPORT_ICONIFY_NAMES,
  computeEqualPayoutDutchSplit,
  formatLeagueBadgeLabel,
  getBadgeTooltipText,
  getCompetitionFlagIconify,
  getFormOutcomeSquareClass,
  getH2HScoreColorClass,
  getH2HWinnerSide,
  getSportBadgeTheme,
  getSportEmoji,
  getSportIconColor,
  getSportIconify,
  getTierBadgeClass,
  getWinProbBarColor,
  parseScorePredictionSegments,
  splitScoreAndInterim,
} from '../utils/formatters';
import { setupIconifyCollections } from '../utils/iconifySetup';
import { type PickCardMeta, renderCanvasPickCard } from '../utils/canvasCard';

setupIconifyCollections();

const store = useBetscoutStore();
const currentYear = new Date().getFullYear();
const appVersion = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.5.0';
const commitHash = typeof __COMMIT_HASH__ !== 'undefined' ? __COMMIT_HASH__ : 'dev';
const activeTab = ref<'picks' | 'studio' | 'ledger' | 'audit'>('picks');
const trackQuickInput = ref<string>('');
const betBudget = ref<number>(100);
const selectedDutchMatch = ref<string>('');
const dutchStake = ref<number>(25);

// Sorting state for Best Bets Table
const sortKey = ref<'date' | 'comp' | 'match' | 'win_prob' | 'fair' | 'odds'>('date');
const sortDir = ref<'asc' | 'desc'>('asc');

function setBestBetsSort(key: 'date' | 'comp' | 'match' | 'win_prob' | 'fair' | 'odds') {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortKey.value = key;
    sortDir.value = key === 'win_prob' ? 'desc' : 'asc';
  }
}

function sortInd(key: string): string {
  if (sortKey.value !== key) return '';
  return sortDir.value === 'asc' ? '▲' : '▼';
}

const sortedBestBets = computed(() => {
  const arr = [...store.visibleBestBets];
  const sgn = sortDir.value === 'asc' ? 1 : -1;
  arr.sort((a, b) => {
    if (sortKey.value === 'win_prob') return sgn * (Number(a.win_prob || 0) - Number(b.win_prob || 0));
    if (sortKey.value === 'fair') return sgn * (Number(a.min_fair_odds || 0) - Number(b.min_fair_odds || 0));
    if (sortKey.value === 'odds') return sgn * (Number(a.odds || 0) - Number(b.odds || 0));
    if (sortKey.value === 'comp')
      return sgn * String(a.competition || a.sport_league).localeCompare(String(b.competition || b.sport_league));
    if (sortKey.value === 'match') return sgn * String(a.match).localeCompare(String(b.match));
    return sgn * String(a.date).localeCompare(String(b.date));
  });
  return arr;
});

const customSlipCombinedOdds = computed(() => {
  const selected = store.visibleBestBets.filter((b) => store.customSelectedMatches.has(b.match));
  if (!selected.length) return 1.0;
  return selected.reduce((acc, b) => acc * Number(b.odds || 1), 1.0);
});

// Modals state
const inspectorModalOpen = ref<boolean>(false);
const inspectorLoading = ref<boolean>(false);
const inspectorLockedPro = ref<boolean>(false);
const inspectorTitle = ref<string>('');
const inspectorData = ref<Record<string, any> | null>(null);
const inspectorScrollRef = ref<HTMLElement | null>(null);
const inspectorScrollShow = ref<boolean>(false);
const inspectorThumbTopPct = ref<number>(0);
const inspectorThumbHeightPct = ref<number>(35);

function updateInspectorScrollbar() {
  const el = inspectorScrollRef.value;
  if (!el) return;
  const sh = el.scrollHeight;
  const ch = el.clientHeight;
  if (sh <= ch + 2) {
    inspectorScrollShow.value = true;
    inspectorThumbHeightPct.value = 100;
    inspectorThumbTopPct.value = 0;
    return;
  }
  inspectorScrollShow.value = true;
  const ratio = Math.max(0.18, Math.min(0.92, ch / sh));
  const maxScroll = Math.max(1, sh - ch);
  const progress = Math.max(0, Math.min(1, el.scrollTop / maxScroll));
  inspectorThumbHeightPct.value = ratio * 100;
  inspectorThumbTopPct.value = progress * (100 - ratio * 100);
}

function onInspectorRailMouseDown(ev: MouseEvent) {
  const rail = ev.currentTarget as HTMLElement | null;
  const el = inspectorScrollRef.value;
  if (!rail || !el) return;
  const applyFromClientY = (clientY: number) => {
    const rect = rail.getBoundingClientRect();
    const rel = Math.max(0, Math.min(1, (clientY - rect.top) / Math.max(1, rect.height)));
    el.scrollTop = rel * Math.max(0, el.scrollHeight - el.clientHeight);
    updateInspectorScrollbar();
  };
  applyFromClientY(ev.clientY);
  const onMove = (mEv: MouseEvent) => applyFromClientY(mEv.clientY);
  const onUp = () => {
    window.removeEventListener('mousemove', onMove);
    window.removeEventListener('mouseup', onUp);
  };
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
}

const analyzerModalOpen = ref<boolean>(false);
const analyzerQuery = ref<string>('');
const analyzerLoading = ref<boolean>(false);
const analyzerResult = ref<Record<string, any> | null>(null);

const shareModalOpen = ref<boolean>(false);
const shareMessageText = ref<string>('');
const currentShareCardMeta = ref<PickCardMeta | null>(null);
const pickCardCanvasRef = ref<HTMLCanvasElement | null>(null);

const settingsModalOpen = ref<boolean>(false);
const apiKeyInput = ref<string>(store.customApiKey || '');
const newKeyEmail = ref<string>('support@betscout.app');
const newKeyTier = ref<string>('enterprise');
const newKeyLabel = ref<string>('');
const newlyIssuedPlainKey = ref<string>('');

async function handleIssueAdminKey() {
  if (!newKeyEmail.value.trim()) {
    store.showToast('Enter an owner email address to issue an API key.');
    return;
  }
  const plain = await store.createAdminApiKey({
    email: newKeyEmail.value.trim(),
    tier: newKeyTier.value,
    label: newKeyLabel.value.trim(),
  });
  if (plain) {
    newlyIssuedPlainKey.value = plain;
  }
}

function copyPlainKey(val: string) {
  navigator.clipboard?.writeText(val);
  store.showToast('Copied API Key to clipboard!');
}

function copyRemoteMcpConfig() {
  const token = apiKeyInput.value.trim() || store.customApiKey || 'bs_live_YOUR_API_KEY';
  const snippet = JSON.stringify(
    {
      mcpServers: {
        betscout: {
          type: 'http',
          url: 'https://betscout.app/mcp',
          headers: {
            'X-API-Key': token,
          },
        },
      },
    },
    null,
    2,
  );
  navigator.clipboard?.writeText(snippet);
  store.showToast('Copied Remote MCP (.mcp.json) configuration to clipboard!');
}

onMounted(async () => {
  if (typeof window === 'undefined') return;
  const params = new URLSearchParams(window.location.search || '');
  const sid = params.get('session_id');
  if (sid && sid.startsWith('cs_')) {
    try {
      const resp = await fetch(`/api/billing/verify-session?session_id=${encodeURIComponent(sid)}`);
      const data = await resp.json();
      if (data?.ok) {
        if (data.api_key) {
          apiKeyInput.value = data.api_key;
          newlyIssuedPlainKey.value = data.api_key;
          store.setCustomApiKey(data.api_key);
          settingsModalOpen.value = true;
          store.showToast(`Stripe Checkout complete! Provisioned ${data.plan_tier} API & MCP Key for ${data.email}.`);
        } else {
          store.showToast(`Stripe Checkout complete! Activated ${data.plan_tier} membership for ${data.email}.`);
        }
        await store.fetchSnapshot();
      }
    } catch (_) {}
  }
});

const sportToggleItems: Record<string, string> = {
  soccer: 'Football',
  tennis: 'Tennis',
  basketball: 'Basketball',
  hockey: 'Hockey',
  football: 'NFL',
  baseball: 'Baseball',
  volleyball: 'Volleyball',
  handball: 'Handball',
  darts: 'Darts',
  table_tennis: 'Table Tennis',
};

const settledCount = computed(() => Number(store.paperLedger?.settled_count || 57));
const settledWins = computed(() => Number(store.paperLedger?.settled_wins || 55));
const settledLosses = computed(() => Number(store.paperLedger?.settled_losses || 2));
const winRatePct = computed(() => (settledWins.value / Math.max(1, settledCount.value)) * 100);
const profitU = computed(() => Number(store.paperLedger?.settled_profit_u ?? 20.07));
const roiPct = computed(() => Number(store.paperLedger?.settled_roi_best ?? 0.352) * 100);
const meanClv = computed(() => Number(store.paperLedger?.mean_clv_pct ?? 0.0067) * 100);

const workspaceTabs = computed(() => [
  {
    id: 'picks' as const,
    icon: 'fa6-solid:bolt',
    iconColor: 'text-emerald-400',
    label: 'Picks & Live In-Play',
    badge: `${store.visibleBestBets.length}`,
    badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/50',
  },
  {
    id: 'studio' as const,
    icon: 'fa6-solid:calculator',
    iconColor: 'text-sky-400',
    label: 'Bet Slip, Dutching & Combos',
    badge: `${store.recommendedDoubles.length} Combos · ${store.mispricedBets.length} Edge`,
    badgeClass: 'bg-sky-500/20 text-sky-300 border-sky-400/50',
  },
  {
    id: 'ledger' as const,
    icon: 'fa6-solid:chart-line',
    iconColor: 'text-amber-400',
    label: 'Paper-Bet Ledger & ROI',
    badge: `${settledWins.value}W–${settledLosses.value}L (${profitU.value >= 0 ? '+' : ''}${profitU.value.toFixed(1)}u)`,
    badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-400/50',
  },
  {
    id: 'audit' as const,
    icon: 'fa6-solid:microscope',
    iconColor: 'text-violet-400',
    label: 'Model Audit & Backtest',
    badge: '+18.9% ROI',
    badgeClass: 'bg-violet-500/20 text-violet-300 border-violet-400/50',
  },
]);

// Smart Bet Slip calculations
const slipPool = computed(() => {
  const unlocked = store.visibleBestBets.filter((b) => !String(b.match || '').includes('🔒'));
  if (store.customSelectedMatches.size > 0) {
    const custom = unlocked.filter((b) => store.customSelectedMatches.has(b.match));
    if (custom.length) return custom;
  }
  return unlocked;
});

const slipComboLegs = computed(() => slipPool.value.slice(0, 2));
const slipComboOdds = computed(() =>
  slipComboLegs.value.reduce((acc, l) => acc * Number(l.odds || 1), 1.0),
);
const slipComboProb = computed(() =>
  slipComboLegs.value.reduce((acc, l) => acc * Number(l.win_prob || 0.7), 1.0),
);

const slipSinglesAlloc = computed(() => {
  const top = slipPool.value.slice(0, 4);
  if (!top.length) return [];
  const weights = top.map((it) => Math.max(0.05, Number(it.win_prob || 0.7) * Number(it.odds || 1.3) - 0.9));
  const wSum = weights.reduce((a, b) => a + b, 0) || 1;
  return top.map((item, idx) => {
    const stake = betBudget.value * (weights[idx] / wSum);
    return {
      item,
      stake,
      ret: stake * item.odds,
    };
  });
});

const slipSinglesTotalReturn = computed(() =>
  slipSinglesAlloc.value.reduce((acc, s) => acc + s.ret, 0),
);

const slipHybridMaxReturn = computed(() => {
  const s1 = betBudget.value * 0.325 * (slipComboLegs.value[0]?.odds || 1);
  const s2 = betBudget.value * 0.325 * (slipComboLegs.value[1]?.odds || 1);
  const cb = betBudget.value * 0.35 * slipComboOdds.value;
  return s1 + s2 + cb;
});

// Dutching calculations
const dutchEligibleMatches = computed(() =>
  store.visibleBestBets.filter((b) => b.score_cluster_items && b.score_cluster_items.length >= 2),
);

watch(
  dutchEligibleMatches,
  (list) => {
    if (list.length && !list.some((x) => x.match === selectedDutchMatch.value)) {
      selectedDutchMatch.value = list[0].match;
    }
  },
  { immediate: true },
);

const currentDutchMatchObj = computed(() =>
  dutchEligibleMatches.value.find((m) => m.match === selectedDutchMatch.value) || dutchEligibleMatches.value[0] || null,
);

const dutchSplit2 = computed(() => {
  const items = (currentDutchMatchObj.value?.score_cluster_items || []).slice(0, 2).map((x) => ({
    label: x.label,
    prob: x.prob,
    odds: Number(x.book_odds || x.fair_odds || 6.0),
  }));
  return computeEqualPayoutDutchSplit(items, dutchStake.value);
});

const dutchSplit3 = computed(() => {
  const items = (currentDutchMatchObj.value?.score_cluster_items || []).slice(0, 3).map((x) => ({
    label: x.label,
    prob: x.prob,
    odds: Number(x.book_odds || x.fair_odds || 6.5),
  }));
  return computeEqualPayoutDutchSplit(items, dutchStake.value);
});

function selectMatchForDutching(matchName: string) {
  selectedDutchMatch.value = matchName;
  activeTab.value = 'studio';
}

async function onTrackLiveQuick() {
  if (!trackQuickInput.value.trim()) return;
  const q = trackQuickInput.value;
  trackQuickInput.value = '';
  await store.trackLiveMatchup(q);
}

async function openMatchupModal(home: string, away: string, league = '') {
  inspectorTitle.value = `${home} vs ${away}`;
  inspectorModalOpen.value = true;
  if (String(home).includes('🔒') || String(away).includes('🔒')) {
    inspectorLockedPro.value = true;
    inspectorLoading.value = false;
    return;
  }
  inspectorLockedPro.value = false;
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
    await nextTick();
    updateInspectorScrollbar();
    setTimeout(updateInspectorScrollbar, 80);
  }
}

async function runLiveAnalyzer() {
  if (!analyzerQuery.value.trim()) return;
  analyzerLoading.value = true;
  try {
    const qs = new URLSearchParams({ q: analyzerQuery.value.trim() });
    const r = await fetch(`/api/analyze-live?${qs.toString()}`);
    analyzerResult.value = await r.json();
  } catch (_) {
    analyzerResult.value = null;
  } finally {
    analyzerLoading.value = false;
  }
}

async function openShareSinglePickModal(b: BestBetItem) {
  const meta: PickCardMeta = {
    sport_cat: b.sport_cat,
    comp: b.competition || b.sport_league,
    match: b.match,
    pick: b.pick_name || b.pick,
    odds_display: b.odds_display,
    win_prob_str: `${(Number(b.win_prob || 0.75) * 100).toFixed(1)}%`,
    fair_str: `@ ${Number(b.min_fair_odds || 1.33).toFixed(2)}`,
    exact_score: b.exact_score_pick || 'Moneyline Edge',
    announced_at_local: b.announced_at_local || store.generatedAtLocal,
    date_local: b.date_local || b.date,
    tier: b.tier,
    badge: String(b.tier || 'HIGH-CONVICTION').toUpperCase(),
  };
  currentShareCardMeta.value = meta;
  const ico = getSportEmoji(b.sport_cat);
  shareMessageText.value = [
    '🎯 **BETSCOUT — HIGH-CONVICTION PICK**',
    '',
    `${ico} **${b.match}**`,
    `🕒 Match Start: \`${b.date_local || b.date}\``,
    `✅ Pick: **${b.pick_name || b.pick}**`,
    `💰 Odds: **${b.odds_display}**${b.exact_score_pick ? ` · 🎲 Score Proj: **${b.exact_score_pick}**` : ''}`,
    '',
    '⚡ *BetScout · Sports Edge & Score Intelligence*',
  ].join('\n');
  shareModalOpen.value = true;
  await nextTick();
  renderCanvasPickCard(pickCardCanvasRef.value, meta);
}

async function openShareBoosterModal(combo: BankerBoosterCombo) {
  const meta: PickCardMeta = {
    sport_cat: combo.legs[0]?.sport_cat || 'all',
    comp: 'BANKER PROFITABILITY BOOSTER',
    match: combo.title,
    pick: `${combo.legs.map((l) => l.pick_name || l.pick).join(' + ')}`,
    odds_display: `${combo.combinedOdds.toFixed(2)}x (+${combo.netYieldPct}% Profit)`,
    win_prob_str: `${(combo.combinedProb * 100).toFixed(1)}%`,
    fair_str: `@ ${combo.fairOdds.toFixed(2)}`,
    exact_score: `${combo.legs.length}-Leg Banker Multiplier`,
    date_local: combo.legs[0]?.date_local || 'Today',
    tier: 'BANKER BOOSTER',
    badge: `+${combo.netYieldPct}% PROFIT BOOST`,
  };
  currentShareCardMeta.value = meta;
  shareMessageText.value = [
    `🚀 **BETSCOUT — ${combo.title.toUpperCase()}**`,
    `💰 *Combined Odds: ${combo.combinedOdds.toFixed(2)}x (+${combo.netYieldPct}% Profit) · Hit Prob: ${(combo.combinedProb * 100).toFixed(1)}%*`,
    '',
    ...combo.legs.map(
      (l, i) =>
        `${i + 1}. ${getSportEmoji(l.sport_cat)} **${l.pick_name || l.pick}** (${l.match}) @ **${l.odds.toFixed(2)}**`,
    ),
    '',
    '⚡ *BetScout · Sports Edge & Score Intelligence*',
  ].join('\n');
  shareModalOpen.value = true;
  await nextTick();
  renderCanvasPickCard(pickCardCanvasRef.value, meta);
}

async function openShareSlateModal() {
  const items = store.visibleBestBets.slice(0, 12);
  const top = items[0];
  const meta: PickCardMeta = {
    sport_cat: top?.sport_cat || 'soccer',
    comp: 'DAILY HIGH-CONVICTION SLATE',
    match: top ? `${top.match}${items.length > 1 ? ` (+${items.length - 1} More)` : ''}` : 'Daily Slate',
    pick: top ? top.pick_name || top.pick : `${items.length} Qualifying Picks`,
    odds_display: top?.odds_display || '—',
    win_prob_str: top ? `${(top.win_prob * 100).toFixed(1)}%` : `${items.length} Picks`,
    fair_str: top ? `@ ${top.min_fair_odds.toFixed(2)}` : 'Calibrated',
    exact_score: top?.exact_score_pick || 'Multi-Sport Slate',
    date_local: top?.date_local || 'Today',
    badge: `${items.length} ACTIVE PICKS`,
  };
  currentShareCardMeta.value = meta;
  shareMessageText.value = [
    '⚡ **BETSCOUT — DAILY PICKS & UPDATES**',
    '',
    ...items.map(
      (it, idx) =>
        `${idx + 1}. ${getSportEmoji(it.sport_cat)} **${it.match}**\n   🕒 \`${it.date_local}\` · 🎯 Pick: **${it.pick_name || it.pick}** · 💰 **${it.odds_display}**`,
    ),
    '',
    '⚡ *BetScout · Sports Edge & Score Intelligence*',
  ].join('\n');
  shareModalOpen.value = true;
  await nextTick();
  renderCanvasPickCard(pickCardCanvasRef.value, meta);
}

function downloadCanvasPng() {
  const cv = pickCardCanvasRef.value;
  if (!cv) return;
  const a = document.createElement('a');
  const slug = String(currentShareCardMeta.value?.match || 'betscout_pick')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
  a.download = `${slug}.png`;
  a.href = cv.toDataURL('image/png');
  a.click();
}

function copyShareMessage() {
  navigator.clipboard?.writeText(shareMessageText.value);
  store.showToast('Copied formatted message to clipboard!');
}

async function postShareToDiscord() {
  try {
    const resp = await fetch('/api/discord', {
      method: 'POST',
      headers: store.getAuthHeaders(),
      body: JSON.stringify({
        text: shareMessageText.value,
        sport: store.sportFilter,
        pick_card: currentShareCardMeta.value,
        include_image: true,
      }),
    });
    const d = await resp.json();
    if (d.ok) {
      store.showToast('Posted pick & Notification Card to Discord!');
      shareModalOpen.value = false;
    } else {
      store.showToast(`Discord error: ${d.error || 'Failed'}`);
    }
  } catch (err) {
    store.showToast(`Network error: ${err}`);
  }
}
</script>
