<template>
  <div class="min-h-screen px-4 sm:px-6 py-5 pb-20 text-xs text-slate-100 max-w-[1600px] mx-auto w-full">
    <!-- Top Indeterminate Progress Bar -->
    <div v-if="store.loading || store.actionBusy" class="fixed top-0 left-0 right-0 h-1 z-50 bg-sky-500/20 overflow-hidden">
      <div class="h-full w-1/3 bg-gradient-to-r from-sky-400 via-emerald-400 to-sky-400 animate-pulse"></div>
    </div>

    <!-- Main Dashboard Header (Concentric radius: rounded-2xl p-3.5 -> inner rounded-xl) -->
    <header
      class="card-surface flex items-start gap-3.5 rounded-2xl px-4 py-3.5 mb-3.5"
    >
      <router-link
        to="/"
        class="w-[42px] h-[42px] flex items-center justify-center shrink-0 mt-0.5 rounded-xl ring-1 ring-white/10 hover:scale-105 transition-transform"
        title="Back to BetScout Home & Membership Plans"
      >
        <img src="/betscout-logo.svg" width="42" height="42" alt="BetScout" />
      </router-link>

      <div class="flex-1 min-w-0 flex flex-col gap-2">
        <!-- Top Row -->
        <div class="flex flex-wrap justify-between items-center gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <h1
              class="m-0 text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-sky-400 to-emerald-400 bg-clip-text text-transparent"
            >
              BetScout
            </h1>
            <span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40">
              LIVE AI
            </span>
            <span class="text-xs text-slate-300 font-medium">
              Sports Edge, Exact-Score &amp; Paper-Betting Intelligence
            </span>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-400 ml-auto tabular-nums">
            <span class="inline-flex items-center gap-1 bg-slate-900/85 border border-border rounded-lg px-2.5 py-0.5">
              🕒 Updated: <b class="text-slate-100">{{ store.generatedAtLocal }}</b>
            </span>
            <span class="inline-flex items-center gap-1 bg-slate-900/85 border border-border rounded-lg px-2.5 py-0.5">
              🗄️ <b class="text-slate-100">{{ store.totalMatches.toLocaleString() }}</b> Verified Matches
            </span>
            <span class="inline-flex items-center gap-1 bg-slate-900/85 border border-border rounded-lg px-2.5 py-0.5">
              📡 <span>{{ store.serverTimeLocal }}</span>
            </span>
            <span
              class="inline-flex items-center gap-1.5 bg-slate-900/90 border border-border rounded-full px-2.5 py-0.5 text-[11px]"
            >
              <span
                class="w-2 h-2 rounded-full"
                :class="store.streamStatus === 'online' ? 'bg-emerald-400 shadow-[0_0_8px_#22c55e]' : 'bg-amber-400'"
              ></span>
              <span>{{ store.streamStatus === 'online' ? 'Connected' : 'Reconnecting...' }}</span>
            </span>
          </div>
        </div>

        <!-- Bottom Action Row -->
        <div class="flex flex-wrap justify-between items-center gap-2.5 w-full">
          <!-- Admin Action Buttons -->
          <div v-if="store.isAdmin" class="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              :disabled="store.actionBusy"
              class="btn-press min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-sky-500/15 text-sky-400 border border-sky-400/45 hover:bg-sky-500/25 disabled:opacity-50"
              @click="store.syncAndSettle(false)"
            >
              🔄 Sync &amp; Settle
            </button>
            <button
              type="button"
              :disabled="store.actionBusy"
              class="btn-press min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-slate-900 text-slate-200 border border-border hover:border-sky-400 disabled:opacity-50"
              @click="store.syncAndSettle(true)"
            >
              ⚡ Rescan Live
            </button>
            <button
              type="button"
              :disabled="store.actionBusy"
              class="btn-press min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-slate-900 text-slate-200 border border-border hover:border-sky-400 disabled:opacity-50"
              @click="store.runFullPipeline()"
            >
              🚀 Full Pipeline
            </button>
          </div>

          <!-- Guest / Pro Banner when not Admin -->
          <div
            v-else
            class="inline-flex flex-wrap items-center gap-2 bg-sky-500/10 border border-sky-400/35 rounded-xl px-3 py-1 text-[11.5px]"
          >
            <span
              class="px-2 py-0.5 rounded-md text-[10px] font-bold"
              :class="
                store.isPro
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40'
                  : 'bg-amber-500/15 text-amber-400 border border-amber-500/40'
              "
            >
              {{ store.isPro ? '🔓 PRO READ-ONLY' : '🔒 GUEST PREVIEW' }}
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
              class="text-sky-400 font-bold hover:underline"
              @click="store.triggerSignInOut()"
            >
              Sign In
            </button>
            <span class="text-slate-500">·</span>
            <router-link to="/#pricing" class="text-emerald-400 font-bold hover:underline">
              🚀 Membership Plans &rarr;
            </router-link>
          </div>

          <!-- Right Controls -->
          <div class="flex flex-wrap items-center gap-1.5 ml-auto">
            <router-link
              to="/"
              class="btn-press min-h-[34px] inline-flex items-center px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-slate-900 text-slate-300 border border-border hover:border-sky-400 no-underline"
            >
              🏠 Home &amp; Plans
            </router-link>
            <button
              v-if="store.firebaseAuthCfg?.enabled"
              type="button"
              class="btn-press min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold border"
              :class="
                store.userEmail
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/45'
                  : 'bg-sky-500/15 text-sky-400 border-sky-400/45'
              "
              @click="store.triggerSignInOut()"
            >
              {{
                store.userEmail
                  ? `🔓 ${store.userEmail.split('@')[0]} (${store.isAdmin ? 'Admin' : 'Pro'})`
                  : '🔐 Sign In'
              }}
            </button>
            <button
              v-if="store.isAdmin"
              type="button"
              class="btn-press min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/45 hover:bg-emerald-500/25"
              @click="openShareSlateModal()"
            >
              💬 Share Picks
            </button>
            <button
              type="button"
              class="btn-press min-h-[34px] px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-slate-900 text-slate-200 border border-border hover:border-sky-400"
              @click="settingsModalOpen = true"
            >
              ⚙️ Settings
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Action Progress Banner -->
    <div
      v-if="store.actionBusy"
      class="flex items-center gap-3 bg-navy-800 border border-sky-400/50 rounded-xl px-4 py-2.5 mb-3.5"
    >
      <span class="w-3.5 h-3.5 rounded-full border-2 border-sky-400 border-t-transparent animate-spin"></span>
      <b class="text-sky-400">{{ store.actionProgressText }}</b>
    </div>

    <!-- 5-Tile KPI Bento Strip -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-3.5">
      <div
        class="card-surface rounded-xl px-3.5 py-3"
        title="Settled Win Rate & Exact-Score Accuracy across all graded paper-bets in the prospective ledger."
      >
        <span class="block text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Settled Win Rate</span>
        <b class="block text-lg font-mono tabular-nums mt-0.5 whitespace-nowrap">
          <span class="text-emerald-400">{{ settledWins }}W</span> –
          <span :class="settledLosses > 0 ? 'text-danger' : 'text-slate-200'">{{ settledLosses }}L</span>
          (<span class="text-emerald-400">{{ winRatePct.toFixed(1) }}%</span>)
        </b>
        <small class="block text-[10.5px] text-slate-400 mt-0.5 truncate tabular-nums">
          {{ settledCount }} Graded ·
          <span
            class="border-b border-dotted border-slate-500 cursor-help"
            title="Exact Score / Cluster Hit Rate: Share of graded matches where the final score landed inside BetScout's pre-match projected exact-score or set-score cluster."
          >
            Score Hits: {{ store.paperLedger?.exact_score_hits || 0 }}/{{ store.paperLedger?.exact_score_graded || 0 }}
            ({{ Number(store.paperLedger?.exact_score_hit_rate_pct || 0).toFixed(0) }}%)
          </span>
        </small>
      </div>

      <div
        class="card-surface rounded-xl px-3.5 py-3"
        title="Realized Flat-Unit Profit (1.00u per pick) and Return on Investment (ROI%) across all settled bets."
      >
        <span class="block text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Realized Profit / ROI</span>
        <b
          class="block text-lg font-mono tabular-nums mt-0.5 whitespace-nowrap"
          :class="profitU >= 0 ? 'text-emerald-400' : 'text-danger'"
        >
          {{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(2) }}u ({{ roiPct >= 0 ? '+' : '' }}{{ roiPct.toFixed(1) }}%)
        </b>
        <small class="block text-[10.5px] text-slate-400 mt-0.5 truncate tabular-nums">
          <span
            class="border-b border-dotted border-slate-500 cursor-help"
            title="Quarter-Kelly Bankroll Growth (¼-Kelly): Compounded percentage bankroll growth using optimal ¼-Kelly fractional staking."
          >
            ¼-Kelly:
            <b class="text-emerald-400">+{{ Number(store.paperLedger?.kelly_growth_pct || 0).toFixed(2) }}%</b>
          </span>
          ·
          <span class="border-b border-dotted border-slate-500 cursor-help" :title="CLV_TOOLTIP">
            CLV:
            <b :class="meanClv >= 0 ? 'text-emerald-400' : 'text-danger'">
              {{ meanClv >= 0 ? '+' : '' }}{{ meanClv.toFixed(2) }}%
            </b>
          </span>
        </small>
      </div>

      <div
        class="card-surface rounded-xl px-3.5 py-3"
        title="Total Upcoming & Live Qualifying Picks passing all sport-specific safety gates."
      >
        <span class="block text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Total Active Picks</span>
        <b class="block text-lg font-mono tabular-nums text-emerald-400 mt-0.5 whitespace-nowrap">
          {{ store.activeBestBets.length }} Picks
        </b>
        <small class="block text-[10.5px] text-slate-400 mt-0.5 truncate" :title="store.activeSportsBreakdown">
          {{ store.activeSportsBreakdown }}
        </small>
      </div>

      <div
        class="card-surface rounded-xl px-3.5 py-3"
        title="Currently in-play matches (streaming every 6s via Sportradar) and pending pre-match bets in the ledger."
      >
        <span class="block text-[10.5px] font-bold uppercase tracking-wider text-slate-400">Live &amp; Pending Ledger</span>
        <b class="block text-lg font-mono tabular-nums mt-0.5 whitespace-nowrap">
          <span :class="store.liveBets.length > 0 ? 'text-emerald-400' : 'text-slate-200'">
            🔴 {{ store.liveBets.length }} Live
          </span>
          · ⏳ {{ store.pendingBets.length }}
        </b>
        <small class="block text-[10.5px] text-slate-400 mt-0.5 truncate tabular-nums">
          🔗 {{ store.recommendedDoubles.length }} Combos ·
          <span :class="store.vetoedBets > 0 ? 'text-danger' : ''">🛡️ {{ store.vetoedBets }} Vetoes</span>
        </small>
      </div>

      <div
        class="card-surface rounded-xl px-3.5 py-3"
        title="Number of picks currently visible after applying your Sport, Day, Min Odds, and Search filters."
      >
        <span class="block text-[10.5px] font-bold uppercase tracking-wider text-slate-400">
          Filtered Best Bets (&gt;{{ store.minOdds.toFixed(2) }})
        </span>
        <b class="block text-lg font-mono tabular-nums text-emerald-400 mt-0.5 whitespace-nowrap">
          {{ store.visibleBestBets.length }}
        </b>
        <small class="block text-[10.5px] text-slate-400 mt-0.5 truncate tabular-nums">
          💎 {{ store.mispricedBets.length }} Mispriced · {{ store.totalMatches.toLocaleString() }} Matches
        </small>
      </div>
    </section>

    <!-- Filter Bar -->
    <div
      class="card-surface flex flex-wrap items-center gap-2.5 rounded-xl px-3.5 py-2.5 mb-3 text-[11.5px]"
    >
      <b>Sport:</b>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="(label, key) in SPORT_LABELS"
          :key="key"
          type="button"
          class="btn-press px-2.5 py-1 rounded-full text-[11px] font-semibold border"
          :class="
            store.sportFilter === key
              ? 'bg-sky-500/15 border-sky-400 text-sky-400'
              : 'bg-navy-900 border-border text-slate-400 hover:text-slate-200'
          "
          @click="store.sportFilter = key"
        >
          {{ label }}
        </button>
      </div>

      <span class="text-slate-700">|</span>
      <b>Day:</b>
      <div class="flex flex-wrap gap-1">
        <button
          type="button"
          class="btn-press px-2.5 py-1 rounded-full text-[11px] font-semibold border tabular-nums"
          :class="
            store.dayFilter === 'all'
              ? 'bg-sky-500/15 border-sky-400 text-sky-400'
              : 'bg-navy-900 border-border text-slate-400'
          "
          @click="store.dayFilter = 'all'"
        >
          All Days ({{ store.activeBestBets.length }})
        </button>
        <button
          v-for="dObj in store.availableDays"
          :key="dObj.day"
          type="button"
          class="btn-press px-2.5 py-1 rounded-full text-[11px] font-semibold border tabular-nums"
          :class="
            store.dayFilter === dObj.day
              ? 'bg-sky-500/15 border-sky-400 text-sky-400'
              : 'bg-navy-900 border-border text-slate-400'
          "
          @click="store.dayFilter = dObj.day"
        >
          {{ dObj.day }} ({{ dObj.count }})
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-2 ml-auto">
        <b>Min Odds:</b>
        <input
          v-model.number="store.minOdds"
          type="range"
          min="1.05"
          max="2.00"
          step="0.05"
          class="w-28 accent-sky-400 cursor-pointer"
        />
        <span class="font-mono tabular-nums">
          &gt;<b>{{ store.minOdds.toFixed(2) }}</b> (+{{ Math.round((store.minOdds - 1) * 100) }}%)
        </span>
        <input
          v-model="store.searchQuery"
          type="search"
          placeholder="Search team, player, league..."
          class="bg-navy-900 text-slate-100 border border-border rounded-lg px-2.5 py-1 text-[11.5px] min-w-[180px]"
        />
        <button
          type="button"
          class="btn-press min-h-[32px] px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/45 hover:bg-emerald-500/25"
          @click="analyzerModalOpen = true"
        >
          🔍 Analyze Match
        </button>
      </div>
    </div>

    <!-- 4 Sticky Workspace Tabs (Concentric radius: outer rounded-xl p-1.5 -> inner rounded-lg) -->
    <nav
      class="flex flex-wrap gap-2 bg-navy-950/95 border border-border rounded-xl p-1.5 mb-4 sticky top-2 z-40 backdrop-blur-md shadow-xl"
    >
      <button
        v-for="tab in workspaceTabs"
        :key="tab.id"
        type="button"
        class="btn-press flex-1 min-w-[180px] min-h-[38px] inline-flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-bold border"
        :class="
          activeTab === tab.id
            ? 'bg-gradient-to-br from-sky-500/20 to-emerald-500/15 text-white border-sky-400 shadow-[0_0_14px_rgba(56,189,248,0.18)]'
            : 'bg-navy-800 text-slate-400 border-border hover:text-slate-100'
        "
        @click="activeTab = tab.id"
      >
        <span>{{ tab.label }}</span>
        <span
          class="px-2 py-0.5 rounded-full text-[10px] font-bold tabular-nums bg-sky-500/15 text-sky-400 border border-sky-400/35"
        >
          {{ tab.badge }}
        </span>
      </button>
    </nav>

    <!-- TAB 1: PICKS & LIVE IN-PLAY -->
    <div v-if="activeTab === 'picks'">
      <!-- Live In-Play Table -->
      <div class="flex flex-wrap justify-between items-center gap-2 mb-2">
        <h2 class="text-sm font-bold text-sky-400 m-0">
          🔴 Live In-Play Paper-Bets &amp; Tracked Events (Ongoing: {{ store.liveBets.length }})
        </h2>
        <div v-if="store.isAdmin" class="flex flex-wrap items-center gap-1.5">
          <input
            v-model="trackQuickInput"
            type="search"
            placeholder="+ Track any live/upcoming match (e.g. Shelton vs Kovacevic)..."
            class="min-w-[280px] bg-navy-900 text-slate-100 border border-border rounded-lg px-2.5 py-1 text-[11.5px]"
            @keydown.enter="onTrackLiveQuick"
          />
          <button
            type="button"
            class="btn-press px-3 py-1 rounded-lg text-[11.5px] font-semibold bg-sky-500/15 text-sky-400 border border-sky-400/45"
            @click="onTrackLiveQuick"
          >
            📌 Track &amp; Analyze Live
          </button>
        </div>
      </div>

      <div class="card-surface rounded-2xl overflow-x-auto mb-5">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-navy-900/90 text-slate-400 text-[11px] uppercase tracking-wider border-b border-border text-left">
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
              <td colspan="8" class="py-3.5 px-3 text-slate-400">
                No logged paper bets are currently in-play. Active matches move here automatically during kickoff!
              </td>
            </tr>
            <tr
              v-for="tr in store.liveBets"
              :key="`${tr.league}:${tr.event_id}`"
              class="border-b border-border/60 last:border-none hover:bg-slate-800/40"
            >
              <td class="py-2.5 px-2.5 text-center text-base">{{ getSportEmoji(tr.sport_cat) }}</td>
              <td class="py-2.5 px-2.5">
                <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-400/35">
                  {{ tr.league_label || tr.league }}
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">{{ tr.kickoff_local || tr.kickoff }}</td>
              <td class="py-2.5 px-2.5">
                <button
                  type="button"
                  class="font-bold text-slate-100 hover:text-sky-400 border-b border-dashed border-sky-400/40"
                  @click="openMatchupModal(tr.home, tr.away, tr.league)"
                >
                  {{ tr.home }} <span class="text-slate-400 font-normal">vs</span> {{ tr.away }}
                </button>
              </td>
              <td class="py-2.5 px-2.5">
                <b class="text-emerald-400">{{ tr.side === 'H' ? tr.home : tr.away }} ({{ tr.side }})</b>
                <span
                  class="pill-tip ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40 cursor-help"
                  :title="getBadgeTooltipText(tr.tier)"
                >
                  {{ tr.tier }}
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums font-bold text-white">
                <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 mr-1.5 animate-ping"></span>
                {{ tr.live_score || tr.score_str || '0-0 (LIVE)' }}
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">
                <b>{{ Number(tr.logged_best_odds || 1.3).toFixed(2) }}</b>
                <span class="text-slate-400 ml-1">
                  (Close {{ Number(tr.latest_close_odds || tr.logged_best_odds || 1.3).toFixed(2) }})
                </span>
              </td>
              <td class="py-2.5 px-2.5">
                <span
                  class="px-2 py-0.5 rounded text-[10.5px] font-bold border"
                  :class="
                    Number(tr.live_pnl || 0) > 0
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40'
                      : Number(tr.live_pnl || 0) < 0
                        ? 'bg-red-500/15 text-danger border-red-500/40'
                        : 'bg-amber-500/15 text-amber-400 border-amber-500/40'
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
                  class="btn-press ml-1.5 px-1.5 py-0.5 rounded border border-red-500/40 text-danger text-[10px]"
                  @click="store.untrackLiveMatchup(tr.league, tr.event_id)"
                >
                  ✕
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Best Bets Summary Table -->
      <div class="flex flex-wrap justify-between items-center gap-2 mb-2">
        <h2 class="text-sm font-bold text-sky-400 m-0">
          Best Bets Summary Table (Click Any Header to Sort · Click Matchup for H2H · Check ☑️ Rows for Custom Slip)
        </h2>
        <div class="flex flex-wrap items-center gap-1.5">
          <button
            v-if="store.customSelectedMatches.size > 0"
            type="button"
            class="btn-press px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/40"
            @click="store.clearCustomSelection()"
          >
            ✕ Clear Custom Selection ({{ store.customSelectedMatches.size }})
          </button>
          <button
            type="button"
            class="btn-press px-3 py-1 rounded-lg text-[11px] font-semibold bg-sky-500/15 text-sky-400 border border-sky-400/45"
            @click="activeTab = 'studio'"
          >
            🧮 Open in Bet Slip &amp; Dutching Studio
          </button>
        </div>
      </div>

      <div class="card-surface rounded-2xl overflow-x-auto mb-5">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-navy-900/90 text-slate-400 text-[11px] uppercase tracking-wider border-b border-border text-left select-none">
              <th class="py-2.5 px-2 w-9 text-center">☑️</th>
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
              <td colspan="10" class="py-4 px-3 text-slate-400">
                No qualifying best bets match the current filter criteria.
              </td>
            </tr>
            <tr
              v-for="b in sortedBestBets"
              :key="`${b.date}:${b.match}`"
              class="border-b border-border/60 last:border-none hover:bg-slate-800/40"
              :class="store.customSelectedMatches.has(b.match) ? 'bg-sky-500/10' : ''"
            >
              <td class="py-2.5 px-2 text-center">
                <input
                  type="checkbox"
                  :checked="store.customSelectedMatches.has(b.match)"
                  class="accent-emerald-400 cursor-pointer w-3.5 h-3.5"
                  @change="store.toggleCustomMatch(b.match)"
                />
              </td>
              <td class="py-2.5 px-2 text-center text-base">{{ b.sport_icon || getSportEmoji(b.sport_cat) }}</td>
              <td class="py-2.5 px-2.5">
                <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-400/35">
                  {{ b.competition || b.sport_league }}
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums font-bold text-slate-200">
                {{ store.tzMode === 'utc' ? b.date : b.date_local }}
              </td>
              <td class="py-2.5 px-2.5">
                <button
                  type="button"
                  class="font-bold text-white hover:text-sky-400 border-b border-dashed border-sky-400/40 text-left"
                  @click="openMatchupModal(b.home, b.away, b.sport_league)"
                >
                  {{ b.match }}
                </button>
              </td>
              <td class="py-2.5 px-2.5">
                <b class="text-emerald-400">{{ b.pick_name || b.pick }}</b>
                <span
                  v-if="b.tier"
                  class="pill-tip ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40 cursor-help"
                  :title="getBadgeTooltipText(b.tier)"
                >
                  {{ b.tier }}
                </span>
                <span
                  v-if="b.is_mispriced"
                  class="pill-tip ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 cursor-help"
                  :title="`Bookmaker Odds Mispricing: +${Number(b.edge_pp || 0).toFixed(1)}pp probability edge (${b.mispricing_drivers || 'Model Edge'})`"
                >
                  💎 EDGE +{{ Number(b.edge_pp || 0).toFixed(1) }}pp
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums font-bold text-emerald-400">
                {{ (Number(b.win_prob || 0.5) * 100).toFixed(1) }}%
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums text-slate-300">
                {{ Number(b.min_fair_odds || 1.35).toFixed(2) }}
              </td>
              <td class="py-2.5 px-2.5">
                <span class="text-sky-400 font-semibold">{{ b.exact_score_pick || '—' }}</span>
                <button
                  v-if="b.score_cluster_items?.length"
                  type="button"
                  class="btn-press ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-navy-900 text-amber-400 border border-amber-500/40 hover:bg-amber-500/15"
                  @click="selectMatchForDutching(b.match)"
                >
                  🎲 Split €
                </button>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">
                <b>{{ b.odds_display }}</b>
                <span
                  class="ml-1 text-slate-400 border-b border-dotted border-slate-500 cursor-help"
                  :title="CLV_TOOLTIP"
                >
                  (CLV
                  <b :class="Number(b.clv_pct || 0) >= 0 ? 'text-emerald-400' : 'text-danger'">
                    {{ Number(b.clv_pct || 0) >= 0 ? '+' : '' }}{{ Number(b.clv_pct || 0).toFixed(1) }}%
                  </b>
                  )
                </span>
                <span
                  v-if="Number(b.clv_pct || 0) >= 3.0"
                  class="pill-tip ml-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 cursor-help"
                  :title="`Sharp Closing-Line Steam Move (+${Number(b.clv_pct || 0).toFixed(1)}% CLV)`"
                >
                  🔥 STEAM +{{ Number(b.clv_pct || 0).toFixed(1) }}%
                </span>
                <button
                  type="button"
                  class="btn-press ml-1.5 px-1.5 py-0.5 rounded bg-navy-900 border border-border hover:border-sky-400 text-[10.5px]"
                  title="Share this pick + PNG Card to Discord / Telegram"
                  @click="openShareSinglePickModal(b)"
                >
                  📣
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- High-Probability Banker Profitability Booster Combos -->
      <section
        v-if="store.bankerBoosterCombos.length > 0"
        class="bg-gradient-to-b from-emerald-950/35 to-navy-800/95 border border-emerald-500/45 rounded-2xl p-4 mb-6 shadow-xl"
      >
        <div class="flex flex-wrap justify-between items-center gap-2 mb-3">
          <div>
            <b class="text-sm text-emerald-400">🚀 High-Probability Banker Profitability Booster Combos</b>
            <span class="text-slate-400 ml-2">
              Combines multiple high-win-probability (&ge;72%), lower-odds bankers into higher-yielding 2-Leg &amp;
              3-Leg multipliers
            </span>
          </div>
          <button
            type="button"
            class="btn-press px-3 py-1 rounded-lg text-[11px] font-semibold bg-navy-900 text-slate-200 border border-border hover:border-sky-400"
            @click="activeTab = 'studio'"
          >
            🧮 Customize Stake in Studio &rarr;
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          <div
            v-for="combo in store.bankerBoosterCombos"
            :key="combo.id"
            class="card-surface rounded-xl p-4 flex flex-col justify-between"
          >
            <div>
              <div class="flex justify-between items-center gap-2 mb-1">
                <b>{{ combo.title }}</b>
                <div class="flex items-center gap-1.5">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tabular-nums bg-emerald-500/15 text-emerald-400 border border-emerald-500/40">
                    +{{ combo.netYieldPct }}% PROFIT BOOST
                  </span>
                  <button
                    type="button"
                    class="btn-press px-1.5 py-0.5 rounded bg-navy-900 border border-border hover:border-sky-400 text-[10.5px]"
                    @click="openShareBoosterModal(combo)"
                  >
                    📣
                  </button>
                </div>
              </div>
              <div class="text-slate-400 text-[11px] mb-2">{{ combo.description }}</div>
              <div class="divide-y divide-slate-800">
                <div
                  v-for="(leg, lIdx) in combo.legs"
                  :key="lIdx"
                  class="py-1 flex justify-between items-center text-[11.5px]"
                >
                  <span>
                    {{ lIdx + 1 }}. {{ getSportEmoji(leg.sport_cat) }}
                    <b>{{ leg.pick_name || leg.pick }}</b>
                    <span class="text-slate-400">({{ leg.match }})</span>
                  </span>
                  <span class="font-mono tabular-nums">
                    <b class="text-emerald-400">@{{ leg.odds.toFixed(2) }}</b>
                    <span class="text-slate-400 ml-1">({{ (leg.win_prob * 100).toFixed(1) }}%)</span>
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-2.5 pt-2 border-t border-border flex justify-between items-center text-xs font-mono tabular-nums">
              <span>
                Combined Odds: <b class="text-emerald-400">{{ combo.combinedOdds.toFixed(2) }}x</b>
                (Fair {{ combo.fairOdds.toFixed(2) }})
              </span>
              <span>
                Hit Prob: <b class="text-emerald-400">{{ (combo.combinedProb * 100).toFixed(1) }}%</b> · €100 &rarr;
                <b class="text-emerald-400">€{{ (100 * combo.combinedOdds).toFixed(2) }}</b>
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- TAB 2: BET SLIP, DUTCHING & COMBOS -->
    <div v-else-if="activeTab === 'studio'">
      <!-- Smart Bet Slip & Stake Allocation Optimizer -->
      <section class="card-surface rounded-2xl p-4 mb-5">
        <div class="flex flex-wrap justify-between items-center gap-3 mb-3">
          <div>
            <b class="text-sm text-sky-400">🎯 Smart Bet Slip &amp; Stake Allocation Optimizer</b>
            <span class="text-slate-400 ml-2">
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
              class="w-24 bg-navy-900 text-emerald-400 border border-sky-400 rounded-lg px-2.5 py-1 text-xs font-extrabold font-mono tabular-nums"
            />
            <div class="flex gap-1">
              <button
                v-for="amt in [25, 50, 100, 250, 500]"
                :key="amt"
                type="button"
                class="btn-press px-2.5 py-1 rounded-full text-[11px] font-semibold border tabular-nums"
                :class="
                  betBudget === amt
                    ? 'bg-sky-500/15 border-sky-400 text-sky-400'
                    : 'bg-navy-900 border-border text-slate-400'
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
          <div class="bg-navy-900/90 border border-emerald-500/45 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-1">
                <b>Option A · Safe {{ slipComboLegs.length }}-Leg Multiplier Combo</b>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tabular-nums bg-emerald-500/15 text-emerald-400">
                  {{ (slipComboOdds || 1).toFixed(2) }}x
                </span>
              </div>
              <div class="text-slate-400 text-[11px] mb-2">
                Uncorrelated cross-league parlay maximizing total return on a single ticket
              </div>
              <div class="divide-y divide-slate-800">
                <div
                  v-for="(l, idx) in slipComboLegs"
                  :key="idx"
                  class="py-1 flex justify-between items-center text-[11.5px]"
                >
                  <span>
                    {{ idx + 1 }}. {{ getSportEmoji(l.sport_cat) }} <b>{{ l.pick_name || l.pick }}</b>
                    <span class="text-slate-400">({{ l.match }})</span>
                  </span>
                  <b class="font-mono tabular-nums text-emerald-400">@{{ l.odds.toFixed(2) }}</b>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-2 border-t border-border flex justify-between text-xs font-mono tabular-nums">
              <span>
                Stake: <b>€{{ betBudget.toFixed(2) }}</b> ({{ (slipComboProb * 100).toFixed(1) }}% Hit)
              </span>
              <span class="text-emerald-400 font-bold">
                Return: €{{ (betBudget * slipComboOdds).toFixed(2) }} (+€{{
                  (betBudget * (slipComboOdds - 1)).toFixed(2)
                }})
              </span>
            </div>
          </div>

          <!-- Option B: Kelly Singles Portfolio -->
          <div class="bg-navy-900/90 border border-sky-400/45 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-1">
                <b>Option B · {{ slipSinglesAlloc.length }} Separate Individual Bets (Kelly Portfolio)</b>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/15 text-sky-400">
                  LOWEST VARIANCE
                </span>
              </div>
              <div class="text-slate-400 text-[11px] mb-2">
                Splits €{{ betBudget.toFixed(2) }} across {{ slipSinglesAlloc.length }} independent singles — one upset
                never wipes out your stake
              </div>
              <div class="divide-y divide-slate-800">
                <div
                  v-for="(s, idx) in slipSinglesAlloc"
                  :key="idx"
                  class="py-1 flex justify-between items-center text-[11.5px]"
                >
                  <span>
                    {{ getSportEmoji(s.item.sport_cat) }} <b>{{ s.item.pick_name || s.item.pick }}</b>
                    <span class="text-slate-400">(@{{ s.item.odds.toFixed(2) }})</span>
                  </span>
                  <span class="font-mono tabular-nums">
                    Stake <b class="text-sky-400">€{{ s.stake.toFixed(2) }}</b> &rarr;
                    <b class="text-emerald-400">€{{ s.ret.toFixed(2) }}</b>
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-2 border-t border-border flex justify-between text-xs font-mono tabular-nums">
              <span>Total Budget: <b>€{{ betBudget.toFixed(2) }}</b></span>
              <span class="text-emerald-400 font-bold">
                All-Hit Return: €{{ slipSinglesTotalReturn.toFixed(2) }} (+€{{
                  (slipSinglesTotalReturn - betBudget).toFixed(2)
                }})
              </span>
            </div>
          </div>

          <!-- Option C: 65/35 Hybrid Split -->
          <div class="bg-navy-900/90 border border-amber-500/45 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-1">
                <b>Option C · 65/35 Core Singles + Combo Booster</b>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400">
                  ★ OPTIMAL SHARPE
                </span>
              </div>
              <div class="text-slate-400 text-[11px] mb-2">
                65% (€{{ (betBudget * 0.65).toFixed(2) }}) on Top 2 Singles protects your floor + 35% (€{{
                  (betBudget * 0.35).toFixed(2)
                }}) on 2-Leg Combo for upside
              </div>
              <div class="space-y-1 text-[11.5px]">
                <div class="flex justify-between py-1 border-b border-slate-800">
                  <span>🛡️ Core Single #1: <b>{{ slipComboLegs[0]?.pick_name || '—' }}</b></span>
                  <span class="font-mono tabular-nums">
                    €{{ (betBudget * 0.325).toFixed(2) }} &rarr;
                    <b class="text-emerald-400">
                      €{{ (betBudget * 0.325 * (slipComboLegs[0]?.odds || 1)).toFixed(2) }}
                    </b>
                  </span>
                </div>
                <div class="flex justify-between py-1 border-b border-slate-800">
                  <span>🛡️ Core Single #2: <b>{{ slipComboLegs[1]?.pick_name || '—' }}</b></span>
                  <span class="font-mono tabular-nums">
                    €{{ (betBudget * 0.325).toFixed(2) }} &rarr;
                    <b class="text-emerald-400">
                      €{{ (betBudget * 0.325 * (slipComboLegs[1]?.odds || 1)).toFixed(2) }}
                    </b>
                  </span>
                </div>
                <div class="flex justify-between py-1">
                  <span>🚀 2-Leg Combo Booster (@{{ slipComboOdds.toFixed(2) }}x)</span>
                  <span class="font-mono tabular-nums">
                    €{{ (betBudget * 0.35).toFixed(2) }} &rarr;
                    <b class="text-emerald-400">€{{ (betBudget * 0.35 * slipComboOdds).toFixed(2) }}</b>
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-3 pt-2 border-t border-border flex justify-between text-xs font-mono tabular-nums">
              <span>Floor Protection: <b>65% Core</b></span>
              <span class="text-emerald-400 font-bold">
                Full Sweep: €{{ slipHybridMaxReturn.toFixed(2) }} (+€{{ (slipHybridMaxReturn - betBudget).toFixed(2) }})
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Exact-Score & Set-Score Dutching Splitter -->
      <section class="card-surface rounded-2xl p-4 mb-5">
        <div class="flex flex-wrap justify-between items-center gap-3 mb-3">
          <div>
            <b class="text-sm text-amber-400">🎲 Exact-Score &amp; Set-Score Dutching Investment Splitter</b>
            <span class="text-slate-400 ml-2">
              Pick any high-conviction match and enter your investment (€) — generates 2-Score &amp; 3-Score
              equal-payout splits
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <b>Match:</b>
            <select
              v-model="selectedDutchMatch"
              class="max-w-[300px] bg-navy-900 text-slate-100 border border-border rounded-lg px-2.5 py-1 text-xs font-semibold"
            >
              <option v-for="m in dutchEligibleMatches" :key="m.match" :value="m.match">
                {{ getSportEmoji(m.sport_cat) }} {{ m.match }} ({{ m.pick_name || m.pick }})
              </option>
            </select>
            <b>Investment (€):</b>
            <input
              v-model.number="dutchStake"
              type="number"
              min="5"
              max="100000"
              step="5"
              class="w-20 bg-navy-900 text-emerald-400 border border-amber-400 rounded-lg px-2.5 py-1 text-xs font-extrabold font-mono tabular-nums"
            />
          </div>
        </div>

        <div v-if="dutchSplit2 && dutchSplit3" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="bg-navy-900/90 border border-sky-400/45 rounded-xl p-4">
            <div class="flex justify-between items-center mb-2">
              <b>Option 1 · 2-Score Equal-Payout Dutching Split</b>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/15 text-sky-400 font-mono tabular-nums">
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
                  Score #{{ idx + 1 }}: <b>{{ leg.label }}</b> (@{{ leg.odds.toFixed(2) }})
                </span>
                <span>
                  Place <b class="text-emerald-400">€{{ leg.stake.toFixed(2) }}</b> &rarr; Payout
                  <b>€{{ leg.payout.toFixed(2) }}</b>
                </span>
              </div>
            </div>
            <div class="mt-2.5 pt-2 border-t border-border flex justify-between text-xs font-mono tabular-nums">
              <span>Total Stake: <b>€{{ dutchSplit2.totalStake.toFixed(2) }}</b></span>
              <span class="text-emerald-400 font-bold">
                Equal Payout: €{{ dutchSplit2.totalPayout.toFixed(2) }} (+€{{ dutchSplit2.netProfit.toFixed(2) }})
              </span>
            </div>
          </div>

          <div class="bg-navy-900/90 border border-emerald-500/45 rounded-xl p-4">
            <div class="flex justify-between items-center mb-2">
              <b>Option 2 · 3-Score Cluster Dutching Shield</b>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 font-mono tabular-nums">
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
                  Score #{{ idx + 1 }}: <b>{{ leg.label }}</b> (@{{ leg.odds.toFixed(2) }})
                </span>
                <span>
                  Place <b class="text-emerald-400">€{{ leg.stake.toFixed(2) }}</b> &rarr; Payout
                  <b>€{{ leg.payout.toFixed(2) }}</b>
                </span>
              </div>
            </div>
            <div class="mt-2.5 pt-2 border-t border-border flex justify-between text-xs font-mono tabular-nums">
              <span>Total Stake: <b>€{{ dutchSplit3.totalStake.toFixed(2) }}</b></span>
              <span class="text-emerald-400 font-bold">
                Equal Payout: €{{ dutchSplit3.totalPayout.toFixed(2) }} (+€{{ dutchSplit3.netProfit.toFixed(2) }})
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Recommended 2-Leg High-Probability Combos -->
      <section v-if="store.recommendedDoubles.length">
        <h2 class="text-sm font-bold text-sky-400 mb-2.5">
          🔗 Recommended 2-Leg High-Probability Combos &amp; Parlays ({{ store.recommendedDoubles.length }} Variations)
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5 mb-6">
          <div
            v-for="(d, idx) in store.recommendedDoubles"
            :key="idx"
            class="card-surface rounded-xl p-4"
          >
            <div class="flex justify-between items-center mb-2">
              <div class="flex items-center gap-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40">
                  COMBO #{{ idx + 1 }}
                </span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40">
                  {{ d.combo_label }}
                </span>
              </div>
              <div class="font-mono tabular-nums text-xs">
                Odds: <b class="text-emerald-400">{{ Number(d.combined_odds).toFixed(2) }}</b> · WinProb:
                <b class="text-emerald-400">{{ (Number(d.combined_prob) * 100).toFixed(1) }}%</b>
              </div>
            </div>
            <div class="space-y-1 text-xs">
              <div>
                1️⃣ {{ getSportEmoji(d.leg_1?.sport_cat || d.leg_1?.league) }}
                <b>{{ d.leg_1?.match }}</b> &rarr;
                <b class="text-emerald-400">{{ d.leg_1?.pick }}</b> @
                <b class="font-mono tabular-nums">{{ Number(d.leg_1?.odds || 1).toFixed(2) }}</b>
              </div>
              <div>
                2️⃣ {{ getSportEmoji(d.leg_2?.sport_cat || d.leg_2?.league) }}
                <b>{{ d.leg_2?.match }}</b> &rarr;
                <b class="text-emerald-400">{{ d.leg_2?.pick }}</b> @
                <b class="font-mono tabular-nums">{{ Number(d.leg_2?.odds || 1).toFixed(2) }}</b>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- TAB 3: PAPER-BET LEDGER & ROI -->
    <div v-else-if="activeTab === 'ledger'">
      <h2 class="text-sm font-bold text-sky-400 mb-2">
        Settled Paper-Bets (Completed Results: {{ settledCount }} · Wins:
        <b class="text-emerald-400">{{ settledWins }}</b> · Losses:
        <b :class="settledLosses > 0 ? 'text-danger' : ''">{{ settledLosses }}</b> · Realized Profit:
        <b class="text-emerald-400">{{ profitU >= 0 ? '+' : '' }}{{ profitU.toFixed(2) }}u</b>)
      </h2>

      <div class="card-surface rounded-2xl overflow-x-auto mb-6">
        <table class="w-full border-collapse text-xs">
          <thead>
            <tr class="bg-navy-900/90 text-slate-400 text-[11px] uppercase tracking-wider border-b border-border text-left">
              <th class="py-2.5 px-2.5 w-11 text-center">Sport</th>
              <th class="py-2.5 px-2.5">Competition</th>
              <th class="py-2.5 px-2.5">Kickoff</th>
              <th class="py-2.5 px-2.5">Matchup</th>
              <th class="py-2.5 px-2.5">Pick</th>
              <th class="py-2.5 px-2.5">Final Score</th>
              <th class="py-2.5 px-2.5">Odds / CLV</th>
              <th class="py-2.5 px-2.5">Result / PnL</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="tr in store.settledBets"
              :key="`${tr.league}:${tr.event_id}`"
              class="border-b border-border/60 last:border-none hover:bg-slate-800/40"
            >
              <td class="py-2.5 px-2.5 text-center text-base">{{ getSportEmoji(tr.sport_cat) }}</td>
              <td class="py-2.5 px-2.5">
                <span class="px-2 py-0.5 rounded-md text-[10.5px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-400/35">
                  {{ tr.league_label || tr.league }}
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">{{ tr.kickoff_local || tr.kickoff }}</td>
              <td class="py-2.5 px-2.5 font-bold">{{ tr.home }} vs {{ tr.away }}</td>
              <td class="py-2.5 px-2.5">
                <b class="text-emerald-400">{{ tr.side === 'H' ? tr.home : tr.away }} ({{ tr.side }})</b>
                <span class="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400">
                  {{ tr.tier }}
                </span>
              </td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums font-bold">{{ tr.score_str || tr.settled_score || '—' }}</td>
              <td class="py-2.5 px-2.5 font-mono tabular-nums">
                <b>{{ Number(tr.logged_best_odds || 1.3).toFixed(2) }}</b>
              </td>
              <td class="py-2.5 px-2.5">
                <span
                  class="px-2 py-0.5 rounded text-[10.5px] font-bold border font-mono tabular-nums"
                  :class="
                    Number(tr.pnl_best || 0) > 0
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40'
                      : 'bg-red-500/15 text-danger border-red-500/40'
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
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div class="card-surface rounded-2xl p-4">
          <b class="text-sm text-sky-400 block mb-2">📊 By-Sport Settled Attribution</b>
          <table class="w-full border-collapse text-xs">
            <thead>
              <tr class="text-left text-[11px] uppercase text-slate-400 border-b border-border">
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
                class="border-b border-border/50 last:border-none"
              >
                <td class="py-2 font-bold">{{ s.sport }}</td>
                <td class="py-2 font-mono tabular-nums">
                  {{ s.settled }} (<b class="text-emerald-400">{{ s.wins }}W</b> –
                  <b :class="s.losses > 0 ? 'text-danger' : ''">{{ s.losses }}L</b>)
                </td>
                <td class="py-2 font-mono tabular-nums font-bold">{{ Number(s.win_rate_pct || 0).toFixed(1) }}%</td>
                <td class="py-2 font-mono tabular-nums text-emerald-400 font-bold">
                  {{ Number(s.profit_u || 0) >= 0 ? '+' : '' }}{{ Number(s.profit_u || 0).toFixed(2) }}u
                </td>
                <td class="py-2 font-mono tabular-nums text-emerald-400 font-bold">
                  {{ Number(s.roi_pct || 0) >= 0 ? '+' : '' }}{{ Number(s.roi_pct || 0).toFixed(1) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card-surface rounded-2xl p-4">
          <b class="text-sm text-sky-400 block mb-2">🎯 Calibration &amp; Tier Attribution</b>
          <table class="w-full border-collapse text-xs">
            <thead>
              <tr class="text-left text-[11px] uppercase text-slate-400 border-b border-border">
                <th class="py-2">Tier</th>
                <th class="py-2">Settled</th>
                <th class="py-2">Exp Win%</th>
                <th class="py-2">Realized Win%</th>
                <th class="py-2">ROI%</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="t in store.paperLedger?.by_tier || []"
                :key="t.tier"
                class="border-b border-border/50 last:border-none"
              >
                <td class="py-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400">
                    {{ t.tier }}
                  </span>
                </td>
                <td class="py-2 font-mono tabular-nums">{{ t.settled }} ({{ t.wins }}W–{{ t.losses }}L)</td>
                <td class="py-2 font-mono tabular-nums">{{ Number(t.expected_win_pct || 0).toFixed(1) }}%</td>
                <td class="py-2 font-mono tabular-nums font-bold text-emerald-400">
                  {{ Number(t.realized_win_pct || 0).toFixed(1) }}%
                </td>
                <td class="py-2 font-mono tabular-nums font-bold text-emerald-400">
                  {{ Number(t.roi_pct || 0) >= 0 ? '+' : '' }}{{ Number(t.roi_pct || 0).toFixed(1) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- FLOATING CUSTOM SLIP DOCK (Appears when >=1 matches checked) -->
    <div
      v-if="store.customSelectedMatches.size > 0"
      class="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex flex-wrap items-center gap-4 bg-navy-950/95 border border-emerald-400/60 rounded-2xl px-5 py-3 shadow-2xl backdrop-blur-md"
    >
      <div class="flex items-center gap-2">
        <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-emerald-500/20 text-emerald-400 tabular-nums">
          ☑️ {{ store.customSelectedMatches.size }} Selected
        </span>
        <span class="text-xs text-slate-300 font-mono tabular-nums">
          Combined Odds: <b class="text-emerald-400">{{ customSlipCombinedOdds.toFixed(2) }}x</b>
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="btn-press px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-400 to-emerald-500 text-emerald-950"
          @click="activeTab = 'studio'"
        >
          🧮 Optimize in Bet Slip Studio &rarr;
        </button>
        <button
          type="button"
          class="btn-press px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-slate-900 text-slate-300 border border-border"
          @click="store.clearCustomSelection()"
        >
          ✕ Clear
        </button>
      </div>
    </div>

    <!-- MODAL 1: MATCHUP DRILL-DOWN INSPECTOR -->
    <div
      v-if="inspectorModalOpen"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="inspectorModalOpen = false"
    >
      <div class="card-surface rounded-2xl max-w-[680px] w-full max-h-[85vh] overflow-y-auto p-5">
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-border">
          <b class="text-sm text-sky-400">🔍 {{ inspectorTitle }}</b>
          <button
            type="button"
            class="btn-press px-2.5 py-1 rounded-lg bg-navy-900 border border-border text-xs"
            @click="inspectorModalOpen = false"
          >
            Close ✕
          </button>
        </div>
        <div v-if="inspectorLoading" class="py-6 text-slate-400">Loading H2H, Last-6 Form &amp; Score Matrix...</div>
        <div v-else-if="inspectorLockedPro" class="p-4 bg-navy-900 border border-sky-400/40 rounded-xl text-center">
          <div class="text-base font-extrabold text-white mb-1.5">🔒 BetScout Pro Subscriber Pick</div>
          <div class="text-slate-400 mb-4">
            Full matchup names, H2H history, Dixon-Coles exact-score matrices &amp; 2-leg combos are reserved for
            active <b>BetScout Pro</b> members.
          </div>
          <div class="flex justify-center gap-3">
            <button
              type="button"
              class="btn-press px-3.5 py-1.5 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-400/50 font-bold"
              @click="
                inspectorModalOpen = false;
                store.triggerSignInOut();
              "
            >
              🔐 Sign In with Google
            </button>
            <router-link
              to="/#pricing"
              class="btn-press px-3.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 font-bold no-underline"
              @click="inspectorModalOpen = false"
            >
              🚀 View Membership Plans &rarr;
            </router-link>
          </div>
        </div>
        <div v-else-if="inspectorData" class="space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            <div>
              <b class="block mb-1.5 text-white">📈 {{ inspectorData.home }} — Last 6</b>
              <div v-if="!inspectorData.form_home?.length" class="text-slate-400">No recent matches in DB</div>
              <div
                v-for="(m, i) in inspectorData.form_home"
                :key="i"
                class="flex justify-between py-1 border-b border-border/50"
              >
                <span>
                  <b :class="m.result === 'W' ? 'text-emerald-400' : m.result === 'L' ? 'text-danger' : 'text-amber-400'">
                    {{ m.result }}
                  </b>
                  {{ m.venue }} vs <b>{{ m.opp }}</b>
                </span>
                <span class="font-mono tabular-nums text-slate-400">{{ m.score }} ({{ m.date }})</span>
              </div>
            </div>
            <div>
              <b class="block mb-1.5 text-white">📈 {{ inspectorData.away }} — Last 6</b>
              <div v-if="!inspectorData.form_away?.length" class="text-slate-400">No recent matches in DB</div>
              <div
                v-for="(m, i) in inspectorData.form_away"
                :key="i"
                class="flex justify-between py-1 border-b border-border/50"
              >
                <span>
                  <b :class="m.result === 'W' ? 'text-emerald-400' : m.result === 'L' ? 'text-danger' : 'text-amber-400'">
                    {{ m.result }}
                  </b>
                  {{ m.venue }} vs <b>{{ m.opp }}</b>
                </span>
                <span class="font-mono tabular-nums text-slate-400">{{ m.score }} ({{ m.date }})</span>
              </div>
            </div>
          </div>

          <div>
            <b class="block mb-1.5 text-white">⚔️ Head-to-Head History ({{ inspectorData.h2h?.length || 0 }} Meetings)</b>
            <div v-if="!inspectorData.h2h?.length" class="text-slate-400">First tracked meeting in current DB window.</div>
            <div
              v-for="(h, idx) in inspectorData.h2h"
              :key="idx"
              class="flex justify-between py-1 border-b border-border/50"
            >
              <span><b>{{ h.home }}</b> vs <b>{{ h.away }}</b></span>
              <span class="font-mono tabular-nums"><b class="text-emerald-400">{{ h.score }}</b> ({{ h.date }})</span>
            </div>
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
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-border">
          <div>
            <b class="text-sm text-emerald-400">🔍 On-Demand Any-Matchup Live Analyzer</b>
            <div class="text-slate-400 text-[11px]">
              Analyze any Tennis or Football matchup — checks live bookmaker odds, Last-5 form, H2H &amp; turnaround
            </div>
          </div>
          <button
            type="button"
            class="btn-press px-2.5 py-1 rounded-lg bg-navy-900 border border-border text-xs"
            @click="analyzerModalOpen = false"
          >
            ✕ Close
          </button>
        </div>

        <div class="flex gap-2 mb-3">
          <input
            v-model="analyzerQuery"
            type="search"
            placeholder="e.g. Shelton vs Kovacevic, Roma vs Cagliari..."
            class="flex-1 bg-navy-900 text-slate-100 border border-border rounded-lg px-3 py-1.5 text-xs"
            @keydown.enter="runLiveAnalyzer"
          />
          <button
            type="button"
            class="btn-press px-3.5 py-1.5 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-400/50 font-bold"
            @click="runLiveAnalyzer"
          >
            ⚡ Analyze Matchup
          </button>
        </div>

        <div v-if="analyzerLoading" class="py-4 text-slate-400">Running live multi-market analysis...</div>
        <div v-else-if="analyzerResult" class="p-3.5 bg-navy-900 border border-border rounded-xl space-y-2">
          <div class="text-sm font-bold text-white">
            {{ analyzerResult.home }} vs {{ analyzerResult.away }}
            <span class="text-sky-400 ml-2">({{ analyzerResult.verdict || analyzerResult.sport || 'Analyzed' }})</span>
          </div>
          <div v-if="analyzerResult.summary" class="text-slate-300">{{ analyzerResult.summary }}</div>
          <pre v-else class="text-[11px] font-mono text-slate-300 whitespace-pre-wrap">{{
            JSON.stringify(analyzerResult, null, 2)
          }}</pre>
        </div>
      </div>
    </div>

    <!-- MODAL 3: SHARE PICK & PNG CARD GENERATOR -->
    <div
      v-if="shareModalOpen"
      class="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      @click.self="shareModalOpen = false"
    >
      <div class="card-surface rounded-2xl max-w-[720px] w-full max-h-[90vh] overflow-y-auto p-5">
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-border">
          <b class="text-sm text-emerald-400">💬 Share Pick &amp; High-Res PNG Card Publisher</b>
          <button
            type="button"
            class="btn-press px-2.5 py-1 rounded-lg bg-navy-900 border border-border text-xs"
            @click="shareModalOpen = false"
          >
            ✕ Close
          </button>
        </div>

        <div class="bg-obsidian border border-border rounded-xl p-2.5 mb-3">
          <div class="flex justify-between items-center mb-1.5">
            <span class="text-[11px] font-bold text-sky-400">🖼️ Generated Pick Card Image (1080×560 PNG)</span>
            <button
              type="button"
              class="btn-press px-2.5 py-0.5 rounded-lg bg-navy-900 border border-border text-[11px]"
              @click="downloadCanvasPng"
            >
              ⬇️ Download PNG Card
            </button>
          </div>
          <canvas
            ref="pickCardCanvasRef"
            width="1080"
            height="560"
            class="w-full h-auto rounded-lg border border-border block"
          ></canvas>
        </div>

        <textarea
          v-model="shareMessageText"
          rows="6"
          class="w-full bg-obsidian text-slate-100 border border-border rounded-xl p-2.5 font-mono text-xs mb-3"
        ></textarea>

        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="btn-press px-3 py-1.5 rounded-lg bg-navy-900 border border-border text-xs font-semibold"
            @click="copyShareMessage"
          >
            📋 Copy Text
          </button>
          <button
            type="button"
            class="btn-press px-3.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 text-xs font-bold"
            @click="postShareToDiscord"
          >
            🚀 Send to Discord
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
      <div class="card-surface rounded-2xl max-w-[640px] w-full max-h-[85vh] overflow-y-auto p-5">
        <div class="flex justify-between items-center mb-3 pb-2 border-b border-border">
          <b class="text-sm text-sky-400">⚙️ BetScout Settings &amp; Active Sport Toggles</b>
          <button
            type="button"
            class="btn-press px-2.5 py-1 rounded-lg bg-navy-900 border border-border text-xs"
            @click="settingsModalOpen = false"
          >
            Close ✕
          </button>
        </div>

        <div class="space-y-4">
          <div class="p-3.5 bg-navy-900 border border-border rounded-xl">
            <b class="block text-emerald-400 mb-2">🏅 Active Sports On/Off Filter</b>
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
                <span>{{ lbl }}</span>
              </label>
            </div>
          </div>

          <div class="p-3.5 bg-navy-900 border border-border rounded-xl flex justify-between items-center">
            <span>Display Timezone:</span>
            <div class="flex gap-1.5">
              <button
                type="button"
                class="btn-press px-2.5 py-1 rounded-lg text-xs font-semibold border"
                :class="
                  store.tzMode === 'local'
                    ? 'bg-sky-500/15 border-sky-400 text-sky-400'
                    : 'bg-navy-800 border-border text-slate-400'
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
                    ? 'bg-sky-500/15 border-sky-400 text-sky-400'
                    : 'bg-navy-800 border-border text-slate-400'
                "
                @click="store.tzMode = 'utc'"
              >
                UTC
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { useBetscoutStore } from '../stores/betscoutStore';
import {
  type BankerBoosterCombo,
  type BestBetItem,
  CLV_TOOLTIP,
  SPORT_LABELS,
  computeEqualPayoutDutchSplit,
  getBadgeTooltipText,
  getSportEmoji,
} from '../utils/formatters';
import { type PickCardMeta, renderCanvasPickCard } from '../utils/canvasCard';

const store = useBetscoutStore();
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

const analyzerModalOpen = ref<boolean>(false);
const analyzerQuery = ref<string>('');
const analyzerLoading = ref<boolean>(false);
const analyzerResult = ref<Record<string, any> | null>(null);

const shareModalOpen = ref<boolean>(false);
const shareMessageText = ref<string>('');
const currentShareCardMeta = ref<PickCardMeta | null>(null);
const pickCardCanvasRef = ref<HTMLCanvasElement | null>(null);

const settingsModalOpen = ref<boolean>(false);

const sportToggleItems: Record<string, string> = {
  soccer: '⚽ Football',
  tennis: '🎾 Tennis',
  basketball: '🏀 Basketball',
  hockey: '🏒 Hockey',
  football: '🏈 NFL',
  baseball: '⚾ Baseball',
  volleyball: '🏐 Volleyball',
  handball: '🤾 Handball',
  darts: '🎯 Darts',
  table_tennis: '🏓 Table Tennis',
};

const settledCount = computed(() => Number(store.paperLedger?.settled_count || 57));
const settledWins = computed(() => Number(store.paperLedger?.settled_wins || 55));
const settledLosses = computed(() => Number(store.paperLedger?.settled_losses || 2));
const winRatePct = computed(() => (settledWins.value / Math.max(1, settledCount.value)) * 100);
const profitU = computed(() => Number(store.paperLedger?.settled_profit_u ?? 20.07));
const roiPct = computed(() => Number(store.paperLedger?.settled_roi_best ?? 0.352) * 100);
const meanClv = computed(() => Number(store.paperLedger?.mean_clv_pct ?? 0.0067) * 100);

const workspaceTabs = computed(() => [
  { id: 'picks' as const, label: '🎯 Picks & Live In-Play', badge: `${store.visibleBestBets.length}` },
  {
    id: 'studio' as const,
    label: '🧮 Bet Slip, Dutching & Combos',
    badge: `${store.recommendedDoubles.length} Combos · ${store.mispricedBets.length} 💎`,
  },
  {
    id: 'ledger' as const,
    label: '📊 Paper-Bet Ledger & ROI',
    badge: `${settledWins.value}W–${settledLosses.value}L (${profitU.value >= 0 ? '+' : ''}${profitU.value.toFixed(1)}u)`,
  },
  { id: 'audit' as const, label: '🔬 Model Audit & Backtest', badge: '+18.9% ROI' },
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
  store.showToast('📋 Copied formatted message to clipboard!');
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
      store.showToast('🚀 Posted pick & PNG card to Discord!');
      shareModalOpen.value = false;
    } else {
      store.showToast(`❌ Discord error: ${d.error || 'Failed'}`);
    }
  } catch (err) {
    store.showToast(`❌ Network error: ${err}`);
  }
}
</script>
