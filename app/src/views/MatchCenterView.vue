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

    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-40 bg-slate-950/85 backdrop-blur-xl border-b border-slate-400/15">
      <div class="w-full max-w-[1360px] mx-auto px-4 sm:px-6 min-h-[64px] py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-3">
          <router-link to="/app" class="flex items-center gap-2.5 text-white font-extrabold text-lg tracking-tight no-underline">
            <img
              src="/betscout-logo.svg?v=7.3"
              width="38"
              height="38"
              alt="BetScout Logo"
              class="rounded-xl shadow-[0_0_20px_rgba(56,189,248,0.28)] shrink-0"
            />
            <span>Bet<span class="text-emerald-400">Scout</span></span>
          </router-link>
          <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/45 font-mono tabular-nums">
            Match Center {{ dossier?.match_id ? `#${dossier.match_id}` : '' }}
          </span>
          <span
            class="hidden md:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-400/40"
          >
            <span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
            <span>Live Telemetry Active</span>
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <router-link
            to="/app"
            class="btn-press h-[34px] inline-flex items-center justify-center gap-1.5 px-3 rounded-lg text-xs font-bold leading-none bg-slate-900/90 text-slate-200 border border-slate-700 hover:border-sky-400 no-underline"
          >
            <Icon icon="fa6-solid:house" class="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span>&larr; Back to Quant Desk</span>
          </router-link>
          <div class="flex items-center gap-1.5">
            <input
              v-model="customMatchInput"
              type="text"
              placeholder="Match ID (e.g. 75837638)"
              class="w-36 h-[34px] bg-slate-950 text-white border border-slate-700 rounded-lg px-2.5 text-xs font-mono"
              @keyup.enter="jumpToMatchId"
            />
            <button
              type="button"
              class="btn-press h-[34px] inline-flex items-center justify-center px-3 rounded-lg text-xs font-bold leading-none bg-sky-500/20 text-sky-300 border border-sky-400/50"
              @click="jumpToMatchId"
            >
              Load
            </button>
            <button
              type="button"
              class="btn-press h-[34px] inline-flex items-center justify-center gap-1.5 px-3 rounded-lg text-xs font-bold leading-none bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
              @click="fetchDossier"
            >
              <Icon icon="fa6-solid:arrows-rotate" class="w-3.5 h-3.5 shrink-0" :class="{ 'animate-spin': loading }" />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <main class="flex-1 w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-5">
      <!-- Loading Indicator -->
      <div v-if="loading && !dossier" class="card-surface rounded-2xl p-10 flex flex-col items-center justify-center gap-3 text-slate-300">
        <div class="inline-flex items-center gap-2 text-sm font-bold text-sky-300">
          <Icon icon="fa6-solid:arrows-rotate" class="w-4 h-4 animate-spin text-sky-400" />
          <span>Loading Match Center Dossier, Live Markets &amp; Historical Splits...</span>
        </div>
        <div
          role="progressbar"
          aria-label="Loading Match Center"
          class="w-full max-w-[340px] h-1.5 rounded-full bg-slate-900 border border-slate-700 overflow-hidden"
        >
          <div class="modal-loading-bar"></div>
        </div>
      </div>

      <div v-else-if="errorMsg" class="card-surface rounded-2xl p-8 text-center space-y-3">
        <div class="text-rose-400 font-bold text-base">{{ errorMsg }}</div>
        <router-link
          to="/app"
          class="btn-press inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sky-500/20 text-sky-300 border border-sky-400/50 text-xs font-bold no-underline"
        >
          <span>Return to Live Quant Desk</span>
        </router-link>
      </div>

      <div v-else-if="dossier" class="space-y-5">
        <!-- HERO SCOREBOARD CARD -->
        <section class="card-surface rounded-2xl p-5 sm:p-6 border border-slate-700/80">
          <div class="flex flex-wrap justify-between items-center gap-2 pb-3 mb-4 border-b border-slate-800 text-xs text-slate-300">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="font-semibold text-sky-300">{{ dossier.sport_name || 'Sport' }}</span>
              <span v-if="realCategoryName">· {{ realCategoryName }}</span>
              <span>·</span>
              <img
                v-if="dossier.tournament_flag_url"
                :src="dossier.tournament_flag_url"
                width="18"
                height="13"
                alt=""
                class="inline-block rounded-[2px]"
              />
              <img
                v-if="dossier.tournament_crest_url"
                :src="dossier.tournament_crest_url"
                width="18"
                height="18"
                alt=""
                class="inline-block rounded"
              />
              <b class="text-white">{{ tournamentName }}</b>
              <span
                v-if="roundName"
                class="ml-1 px-2 py-0.5 rounded-full text-[10.5px] font-bold bg-slate-900 border border-slate-700 text-slate-300"
              >
                {{ roundName }}
              </span>
            </div>
            <div class="flex flex-wrap items-center gap-3 text-[11.5px] text-slate-400">
              <span v-if="groundName">Surface: <b class="text-slate-200">{{ groundName }}</b></span>
              <span v-if="stadiumName">Venue: <b class="text-slate-200">{{ stadiumName }}</b></span>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            <!-- Home Competitor -->
            <div class="lg:col-span-4 flex items-stretch gap-5">
              <div class="w-[96px] h-[96px] sm:w-[104px] sm:h-[104px] self-stretch rounded-2xl border-2 border-sky-400/50 bg-slate-900/90 shrink-0 overflow-hidden flex items-center justify-center">
                <img
                  v-if="dossier.home_headshot_url"
                  :src="dossier.home_headshot_url"
                  :alt="homeName"
                  class="w-full h-full"
                  :class="isClubMatch ? 'object-contain p-2' : 'object-cover object-top rounded-[14px]'"
                />
              </div>
              <div class="min-w-0 min-h-[96px] sm:min-h-[104px] flex flex-col justify-between py-0.5">
                <div>
                  <div class="flex flex-wrap items-center gap-1.5">
                    <span class="text-lg font-extrabold text-white leading-tight truncate">{{ homeName }}</span>
                    <span
                      v-if="homeSeed"
                      class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/45"
                    >
                      {{ homeSeed }}
                    </span>
                  </div>
                  <div class="text-xs text-slate-300 mt-1 flex flex-wrap items-center gap-1.5">
                    <span v-if="homeRankPrefix">{{ homeRankPrefix }}</span>
                    <span v-if="homeRankPrefix && (homeCountryName || dossier.home_flag_url)" class="text-slate-500">·</span>
                    <span v-if="homeCountryName || dossier.home_flag_url" class="inline-flex items-center gap-1.5">
                      <img
                        v-if="dossier.home_flag_url"
                        :src="dossier.home_flag_url"
                        alt=""
                        class="w-4 h-3 rounded-[2px] object-cover shrink-0 shadow-sm"
                      />
                      <span>{{ homeCountryName }}</span>
                    </span>
                  </div>
                </div>
                <!-- Form WDL Strip -->
                <div v-if="formWdlHome.length" class="flex items-center gap-1.5 mt-2">
                  <div
                    v-for="(seg, idx) in formWdlHome"
                    :key="idx"
                    class="flex flex-col items-center gap-0.5"
                    :title="seg.opponent_name ? `vs ${seg.opponent_name}` : ''"
                  >
                    <span
                      v-if="seg.wdl !== 'empty'"
                      class="w-[22px] h-[22px] rounded-[5px] inline-grid place-items-center text-[11px] font-bold border font-mono"
                      :class="getFormOutcomeSquareClass(seg.wdl)"
                    >
                      {{ seg.wdl }}
                    </span>
                    <span
                      v-if="seg.score_label"
                      class="text-[10px] font-mono font-bold leading-none"
                      :class="seg.wdl === 'W' ? 'text-emerald-300' : seg.wdl === 'L' ? 'text-rose-400' : 'text-amber-300'"
                    >
                      {{ seg.score_label }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Center Scoreboard -->
            <div class="lg:col-span-4 flex flex-col items-center justify-center text-center bg-slate-950/85 border border-slate-800 rounded-2xl p-3.5">
              <span class="px-2.5 py-0.5 rounded-full text-[10.5px] font-extrabold uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-400/45 mb-1">
                {{ matchStatusName }}
              </span>
              <div class="text-3xl font-black font-mono tabular-nums text-white tracking-tight my-1 flex items-center gap-2">
                <span v-if="isTennis && activeServer === '1'" class="text-base" title="Active Server">🎾</span>
                <span>{{ mainScoreHome }} - {{ mainScoreAway }}</span>
                <span v-if="isTennis && activeServer === '2'" class="text-base" title="Active Server">🎾</span>
              </div>
              <table v-if="periodKeys.length" class="w-full max-w-[280px] text-[11px] font-mono tabular-nums mt-1 border-t border-slate-800">
                <thead>
                  <tr class="text-slate-400">
                    <th class="py-1 text-left">{{ isTennis ? 'Player' : 'Team' }}</th>
                    <th v-for="(lbl, pIdx) in periodLabels" :key="pIdx" class="py-1 text-center">{{ lbl }}</th>
                    <th v-if="gameScoreObj" class="py-1 text-center text-sky-300">Pts</th>
                  </tr>
                </thead>
                <tbody>
                  <tr class="border-t border-slate-800/70">
                    <td class="py-1 text-left font-bold text-slate-200 truncate max-w-[90px]">{{ homeAbbr }}</td>
                    <td v-for="k in periodKeys" :key="`h-${k}`" class="py-1 text-center font-bold text-white">
                      {{ periodsObj[k]?.home ?? '—' }}
                    </td>
                    <td v-if="gameScoreObj" class="py-1 text-center font-extrabold text-sky-300">
                      {{ gameScoreObj.home ?? 0 }}
                    </td>
                  </tr>
                  <tr class="border-t border-slate-800/70">
                    <td class="py-1 text-left font-bold text-slate-200 truncate max-w-[90px]">{{ awayAbbr }}</td>
                    <td v-for="k in periodKeys" :key="`a-${k}`" class="py-1 text-center font-bold text-white">
                      {{ periodsObj[k]?.away ?? '—' }}
                    </td>
                    <td v-if="gameScoreObj" class="py-1 text-center font-extrabold text-amber-300">
                      {{ gameScoreObj.away ?? 0 }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Away Competitor -->
            <div class="lg:col-span-4 flex items-stretch lg:justify-end gap-5 lg:text-right">
              <div class="min-w-0 min-h-[96px] sm:min-h-[104px] flex flex-col justify-between py-0.5 order-2 lg:order-1">
                <div>
                  <div class="flex flex-wrap items-center lg:justify-end gap-1.5">
                    <span
                      v-if="awaySeed"
                      class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/45"
                    >
                      {{ awaySeed }}
                    </span>
                    <span class="text-lg font-extrabold text-white leading-tight truncate">{{ awayName }}</span>
                  </div>
                  <div class="text-xs text-slate-300 mt-1 flex flex-wrap items-center lg:justify-end gap-1.5">
                    <span v-if="awayRankPrefix">{{ awayRankPrefix }}</span>
                    <span v-if="awayRankPrefix && (awayCountryName || dossier.away_flag_url)" class="text-slate-500">·</span>
                    <span v-if="awayCountryName || dossier.away_flag_url" class="inline-flex items-center gap-1.5">
                      <img
                        v-if="dossier.away_flag_url"
                        :src="dossier.away_flag_url"
                        alt=""
                        class="w-4 h-3 rounded-[2px] object-cover shrink-0 shadow-sm"
                      />
                      <span>{{ awayCountryName }}</span>
                    </span>
                  </div>
                </div>
                <!-- Form WDL Strip -->
                <div v-if="formWdlAway.length" class="flex items-center lg:justify-end gap-1.5 mt-2">
                  <div
                    v-for="(seg, idx) in formWdlAway"
                    :key="idx"
                    class="flex flex-col items-center gap-0.5"
                    :title="seg.opponent_name ? `vs ${seg.opponent_name}` : ''"
                  >
                    <span
                      v-if="seg.wdl !== 'empty'"
                      class="w-[22px] h-[22px] rounded-[5px] inline-grid place-items-center text-[11px] font-bold border font-mono"
                      :class="getFormOutcomeSquareClass(seg.wdl)"
                    >
                      {{ seg.wdl }}
                    </span>
                    <span
                      v-if="seg.score_label"
                      class="text-[10px] font-mono font-bold leading-none"
                      :class="seg.wdl === 'W' ? 'text-emerald-300' : seg.wdl === 'L' ? 'text-rose-400' : 'text-amber-300'"
                    >
                      {{ seg.score_label }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="w-[96px] h-[96px] sm:w-[104px] sm:h-[104px] self-stretch rounded-2xl border-2 border-amber-400/50 bg-slate-900/90 shrink-0 overflow-hidden flex items-center justify-center order-1 lg:order-2">
                <img
                  v-if="dossier.away_headshot_url"
                  :src="dossier.away_headshot_url"
                  :alt="awayName"
                  class="w-full h-full"
                  :class="isClubMatch ? 'object-contain p-2' : 'object-cover object-top rounded-[14px]'"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- 3 FLUSH FOLDER-STYLE TABS -->
        <div class="workspace-shell">
          <div class="workspace-tablist" role="tablist" aria-label="Match Center Sections">
            <button
              type="button"
              role="tab"
              :aria-selected="activeTab === 'overview'"
              class="workspace-tab"
              :class="{ 'is-active': activeTab === 'overview' }"
              @click="activeTab = 'overview'"
            >
              <Icon icon="fa6-solid:chart-column" class="w-3.5 h-3.5 text-sky-400" />
              <span>1. Match Overview, Surface/Season Splits, H2H &amp; Info</span>
            </button>
            <button
              type="button"
              role="tab"
              :aria-selected="activeTab === 'statistics'"
              class="workspace-tab"
              :class="{ 'is-active': activeTab === 'statistics' }"
              @click="activeTab = 'statistics'"
            >
              <Icon icon="fa6-solid:chart-line" class="w-3.5 h-3.5 text-emerald-400" />
              <span>2. Match Boxscore Statistics</span>
            </button>
            <button
              type="button"
              role="tab"
              :aria-selected="activeTab === 'timeline'"
              class="workspace-tab"
              :class="{ 'is-active': activeTab === 'timeline' }"
              @click="activeTab = 'timeline'"
            >
              <Icon icon="fa6-solid:bolt" class="w-3.5 h-3.5 text-amber-400" />
              <span>3. Live Timeline &amp; All Bookmaker Markets</span>
            </button>
          </div>

          <div class="workspace-panel space-y-5">
            <!-- TAB 1: OVERVIEW -->
            <div v-if="activeTab === 'overview'" class="space-y-5">
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <!-- Win Probability & Pre-Match Markets -->
                <div class="card-surface rounded-2xl p-5">
                  <div class="flex justify-between items-center pb-2.5 mb-3 border-b border-slate-800">
                    <b class="text-sm text-white">Win Probability &amp; Pre-Match Markets</b>
                    <span class="text-[11px] font-mono text-sky-300 bg-slate-950 px-2 py-0.5 rounded border border-sky-400/30">
                      {{ winProbSummary.drawPct > 0.5 ? '3-Way (1X2)' : '2-Way (Moneyline)' }}
                    </span>
                  </div>

                  <!-- Seamless 0px-gap Win Probability Bar -->
                  <div class="my-3">
                    <div class="flex justify-between items-center text-xs font-bold font-mono tabular-nums mb-1.5">
                      <span class="text-sky-300">
                        {{ homeName }} — {{ winProbSummary.homePct }}%
                        <span v-if="winProbSummary.oddsHome" class="text-slate-400 font-normal">({{ winProbSummary.oddsHome }})</span>
                      </span>
                      <span v-if="winProbSummary.drawPct > 0.5" class="text-slate-300">
                        Draw — {{ winProbSummary.drawPct }}%
                        <span v-if="winProbSummary.oddsDraw" class="text-slate-400 font-normal">({{ winProbSummary.oddsDraw }})</span>
                      </span>
                      <span class="text-amber-300">
                        {{ awayName }} — {{ winProbSummary.awayPct }}%
                        <span v-if="winProbSummary.oddsAway" class="text-slate-400 font-normal">({{ winProbSummary.oddsAway }})</span>
                      </span>
                    </div>
                    <div class="h-3.5 rounded-full bg-slate-950 overflow-hidden flex gap-0">
                      <div
                        class="h-full bg-gradient-to-r from-sky-500 to-cyan-400"
                        :style="{ width: `${winProbSummary.homePct}%` }"
                      ></div>
                      <div
                        v-if="winProbSummary.drawPct > 0.5"
                        class="h-full bg-gradient-to-r from-slate-500 to-slate-400"
                        :style="{ width: `${winProbSummary.drawPct}%` }"
                      ></div>
                      <div
                        class="h-full bg-gradient-to-r from-amber-500 to-rose-500"
                        :style="{ width: `${winProbSummary.awayPct}%` }"
                      ></div>
                    </div>
                  </div>

                  <div class="table-surface rounded-xl overflow-x-auto mt-4">
                    <table class="w-full border-collapse text-xs">
                      <thead>
                        <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase border-b border-slate-800 text-left">
                          <th class="py-2 px-3">Market</th>
                          <th class="py-2 px-3">Outcomes &amp; Odds</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-800/80">
                        <tr v-for="(mk, mIdx) in overviewMarkets" :key="mIdx">
                          <td class="py-2 px-3 font-bold text-white">{{ mk.title }}</td>
                          <td class="py-2 px-3">
                            <div class="flex flex-wrap gap-1.5">
                              <span
                                v-for="(o, oIdx) in mk.outcomes.slice(0, 6)"
                                :key="oIdx"
                                class="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-mono text-[11px]"
                              >
                                {{ o.label }}: <b class="text-amber-300">{{ o.odds }}</b>
                              </span>
                            </div>
                          </td>
                        </tr>
                        <tr v-if="!overviewMarkets.length">
                          <td colspan="2" class="py-3 px-3 text-slate-400">Pre-match markets archived or settled.</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <!-- Surface Win Rate (Tennis) OR Season Statistics (Football / Team Sports) -->
                <div class="card-surface rounded-2xl p-5">
                  <div class="flex justify-between items-center pb-2.5 mb-3 border-b border-slate-800">
                    <b class="text-sm text-white">
                      {{ isTennis ? 'Surface Win Rate Comparison (All / Hard / Indoor / Clay / Grass)' : 'Season Statistics & Scoring Splits' }}
                    </b>
                  </div>
                  <div class="table-surface rounded-xl overflow-x-auto">
                    <table class="w-full border-collapse text-xs">
                      <thead>
                        <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase border-b border-slate-800 text-left">
                          <th class="py-2 px-3">{{ isTennis ? 'Court Surface' : 'Metric' }}</th>
                          <th class="py-2 px-3 text-sky-300">{{ homeName }}</th>
                          <th class="py-2 px-3 text-amber-300">{{ awayName }}</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-800/80 font-mono tabular-nums">
                        <tr v-for="(row, rIdx) in surfaceOrSeasonRows" :key="rIdx">
                          <td class="py-2 px-3 font-sans font-bold text-slate-200">{{ row.label }}</td>
                          <td class="py-2 px-3 font-bold text-white">{{ row.home }}</td>
                          <td class="py-2 px-3 font-bold text-white">{{ row.away }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- H2H Edge & Past Meetings + Last Completed Matches -->
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <!-- Head-to-Head Edge & Meetings -->
                <div class="card-surface rounded-2xl p-5">
                  <div class="flex justify-between items-center pb-2.5 mb-3 border-b border-slate-800">
                    <b class="text-sm text-white">Head-to-Head Edge &amp; Past Meetings ({{ h2hMeetings.length }})</b>
                  </div>

                  <div v-if="h2hEdge && h2hEdge.total_meetings > 0" class="mb-4">
                    <div class="flex justify-between items-center text-xs font-bold font-mono tabular-nums mb-1.5">
                      <span class="text-sky-300">{{ homeName }}: {{ h2hEdge.home_wins }}W ({{ h2hEdge.home_win_pct }}%)</span>
                      <span v-if="h2hEdge.draws > 0" class="text-slate-300">{{ h2hEdge.draws }}D ({{ h2hEdge.draw_pct }}%)</span>
                      <span class="text-amber-300">{{ awayName }}: {{ h2hEdge.away_wins }}W ({{ h2hEdge.away_win_pct }}%)</span>
                    </div>
                    <div class="h-3 rounded-full bg-slate-950 overflow-hidden flex gap-0">
                      <div
                        class="h-full bg-gradient-to-r from-sky-500 to-cyan-400"
                        :style="{ width: `${h2hEdge.home_win_pct}%` }"
                      ></div>
                      <div
                        v-if="h2hEdge.draw_pct > 0"
                        class="h-full bg-gradient-to-r from-slate-500 to-slate-400"
                        :style="{ width: `${h2hEdge.draw_pct}%` }"
                      ></div>
                      <div
                        class="h-full bg-gradient-to-r from-amber-500 to-rose-500"
                        :style="{ width: `${h2hEdge.away_win_pct}%` }"
                      ></div>
                    </div>
                  </div>

                  <div class="table-surface rounded-xl overflow-x-auto">
                    <table class="w-full border-collapse text-xs">
                      <thead>
                        <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase border-b border-slate-800 text-left">
                          <th class="py-2 px-3">Date</th>
                          <th class="py-2 px-3">Home</th>
                          <th class="py-2 px-3">Score</th>
                          <th class="py-2 px-3">Away</th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-800/80">
                        <tr v-for="(m, idx) in h2hMeetings" :key="idx">
                          <td class="py-2 px-3 font-mono text-slate-400">{{ m.date }}</td>
                          <td class="py-2 px-3">
                            <b v-if="m.winner === 'H'" class="text-white font-bold">{{ m.home }}</b>
                            <span v-else class="text-slate-300">{{ m.home }}</span>
                          </td>
                          <td class="py-2 px-3 font-mono tabular-nums">
                            <b class="text-emerald-300">{{ m.scoreMain }}</b>
                            <span v-if="m.scoreInterim" class="text-slate-400 ml-1 text-[11px]">{{ m.scoreInterim }}</span>
                          </td>
                          <td class="py-2 px-3">
                            <b v-if="m.winner === 'A'" class="text-white font-bold">{{ m.away }}</b>
                            <span v-else class="text-slate-300">{{ m.away }}</span>
                          </td>
                        </tr>
                        <tr v-if="!h2hMeetings.length">
                          <td colspan="4" class="py-3 px-3 text-slate-400">First career meeting.</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <!-- Missing / Injured Players OR Last Completed Matches -->
                <div class="card-surface rounded-2xl p-5 space-y-4">
                  <div v-if="homeMissing.length || awayMissing.length">
                    <b class="text-sm text-white block pb-2 mb-2.5 border-b border-slate-800">
                      Missing &amp; Injured Players
                    </b>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div>
                        <b class="text-sky-300 block mb-1">{{ homeName }} ({{ homeMissing.length }} Out)</b>
                        <div v-for="(p, i) in homeMissing.slice(0, 8)" :key="i" class="py-1 border-b border-slate-800/70 flex justify-between">
                          <span class="text-white font-semibold">{{ p.name }}</span>
                          <span class="text-rose-300 text-[11px]">{{ p.cause }}</span>
                        </div>
                      </div>
                      <div>
                        <b class="text-amber-300 block mb-1">{{ awayName }} ({{ awayMissing.length }} Out)</b>
                        <div v-for="(p, i) in awayMissing.slice(0, 8)" :key="i" class="py-1 border-b border-slate-800/70 flex justify-between">
                          <span class="text-white font-semibold">{{ p.name }}</span>
                          <span class="text-rose-300 text-[11px]">{{ p.cause }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <b class="text-sm text-white block pb-2 mb-2.5 border-b border-slate-800">
                      Last Completed Matches
                    </b>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
                      <div>
                        <b class="text-sky-300 block mb-1.5">{{ homeName }}</b>
                        <div
                          v-for="(lm, i) in homeLastMatches.slice(0, 6)"
                          :key="i"
                          class="py-1 border-b border-slate-800/70 flex justify-between font-mono tabular-nums"
                        >
                          <span class="font-sans truncate max-w-[165px]">
                            {{ lm.home }} <span class="text-slate-400">vs</span> {{ lm.away }}
                          </span>
                          <b class="text-white">{{ lm.score }}</b>
                        </div>
                      </div>
                      <div>
                        <b class="text-amber-300 block mb-1.5">{{ awayName }}</b>
                        <div
                          v-for="(lm, i) in awayLastMatches.slice(0, 6)"
                          :key="i"
                          class="py-1 border-b border-slate-800/70 flex justify-between font-mono tabular-nums"
                        >
                          <span class="font-sans truncate max-w-[165px]">
                            {{ lm.home }} <span class="text-slate-400">vs</span> {{ lm.away }}
                          </span>
                          <b class="text-white">{{ lm.score }}</b>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- TAB 2: MATCH BOXSCORE STATISTICS -->
            <div v-else-if="activeTab === 'statistics'" class="card-surface rounded-2xl p-5 space-y-4">
              <div class="flex flex-wrap justify-between items-center gap-2 pb-3 border-b border-slate-800">
                <b class="text-sm text-white">
                  {{ isTennis ? 'Live Tennis Serve & Return Statistics' : 'Live Football Boxscore & Attacking Statistics' }}
                </b>
                <div class="flex gap-1.5">
                  <button
                    type="button"
                    class="btn-press px-3 py-1 rounded-lg text-xs font-bold border"
                    :class="statPeriod === 'all' ? 'bg-sky-500/20 text-sky-300 border-sky-400' : 'bg-slate-900 text-slate-300 border-slate-700'"
                    @click="statPeriod = 'all'"
                  >
                    Match Total
                  </button>
                  <button
                    type="button"
                    class="btn-press px-3 py-1 rounded-lg text-xs font-bold border"
                    :class="statPeriod === 0 ? 'bg-sky-500/20 text-sky-300 border-sky-400' : 'bg-slate-900 text-slate-300 border-slate-700'"
                    @click="statPeriod = 0"
                  >
                    {{ isTennis ? '1st Set' : '1st Half' }}
                  </button>
                  <button
                    type="button"
                    class="btn-press px-3 py-1 rounded-lg text-xs font-bold border"
                    :class="statPeriod === 1 ? 'bg-sky-500/20 text-sky-300 border-sky-400' : 'bg-slate-900 text-slate-300 border-slate-700'"
                    @click="statPeriod = 1"
                  >
                    {{ isTennis ? '2nd Set' : '2nd Half' }}
                  </button>
                </div>
              </div>

              <div v-if="boxscoreStatRows.length" class="space-y-3">
                <div v-for="(st, idx) in boxscoreStatRows" :key="idx" class="space-y-1">
                  <div class="flex justify-between items-center text-xs font-mono tabular-nums">
                    <b class="text-sky-300">{{ st.homeDisplay }}</b>
                    <span class="font-sans font-semibold text-slate-300">{{ st.label }}</span>
                    <b class="text-amber-300">{{ st.awayDisplay }}</b>
                  </div>
                  <div class="h-2 rounded-full bg-slate-950 overflow-hidden flex gap-0">
                    <div
                      class="h-full bg-gradient-to-r from-sky-500 to-cyan-400"
                      :style="{ width: `${st.homePct}%` }"
                    ></div>
                    <div
                      class="h-full bg-gradient-to-r from-amber-500 to-rose-500"
                      :style="{ width: `${st.awayPct}%` }"
                    ></div>
                  </div>
                </div>
              </div>
              <div v-else class="py-6 text-center text-slate-400 text-xs">
                Detailed in-play boxscore statistics populate automatically once the match begins.
              </div>
            </div>

            <!-- TAB 3: TIMELINE & ALL BOOKMAKER MARKETS -->
            <div v-else-if="activeTab === 'timeline'" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div class="card-surface rounded-2xl p-5">
                <b class="text-sm text-white block pb-2.5 mb-3 border-b border-slate-800">
                  {{ isTennis ? 'Point-by-Point & Game Timeline' : 'Play-by-Play Match Timeline' }}
                </b>
                <div class="table-surface rounded-xl overflow-x-auto max-h-[520px] overflow-y-auto">
                  <table class="w-full border-collapse text-xs">
                    <thead>
                      <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase border-b border-slate-800 text-left">
                        <th class="py-2 px-3">Event</th>
                        <th class="py-2 px-3">Side</th>
                        <th class="py-2 px-3">Time / Set</th>
                        <th class="py-2 px-3">Score</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/80">
                      <tr v-for="(ev, idx) in timelineEvents" :key="idx">
                        <td class="py-2 px-3 font-bold text-white">{{ ev.name }}</td>
                        <td class="py-2 px-3 text-slate-300">{{ ev.side }}</td>
                        <td class="py-2 px-3 font-mono text-slate-400">{{ ev.timeStr }}</td>
                        <td class="py-2 px-3 font-mono font-bold text-emerald-300">{{ ev.scoreStr }}</td>
                      </tr>
                      <tr v-if="!timelineEvents.length">
                        <td colspan="4" class="py-4 px-3 text-slate-400">No play-by-play events recorded yet.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="card-surface rounded-2xl p-5">
                <b class="text-sm text-white block pb-2.5 mb-3 border-b border-slate-800">
                  All Bookmaker Markets ({{ allFormattedMarkets.length }})
                </b>
                <div class="table-surface rounded-xl overflow-x-auto max-h-[520px] overflow-y-auto">
                  <table class="w-full border-collapse text-xs">
                    <thead>
                      <tr class="bg-slate-900/90 text-slate-300 text-[11px] uppercase border-b border-slate-800 text-left">
                        <th class="py-2 px-3">ID</th>
                        <th class="py-2 px-3">Market</th>
                        <th class="py-2 px-3">Outcomes</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800/80">
                      <tr v-for="(mk, idx) in allFormattedMarkets" :key="idx">
                        <td class="py-2 px-3 font-mono text-sky-300">#{{ mk.marketId }}</td>
                        <td class="py-2 px-3 font-bold text-white">{{ mk.title }}</td>
                        <td class="py-2 px-3">
                          <div class="flex flex-wrap gap-1">
                            <span
                              v-for="(o, oIdx) in mk.outcomes"
                              :key="oIdx"
                              class="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 font-mono text-[11px]"
                            >
                              {{ o.label }}: <b class="text-amber-300">{{ o.odds }}</b>
                            </span>
                          </div>
                        </td>
                      </tr>
                      <tr v-if="!allFormattedMarkets.length">
                        <td colspan="3" class="py-4 px-3 text-slate-400">No raw markets available for this fixture.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Icon } from '@iconify/vue';
import { getFormOutcomeSquareClass, splitScoreAndInterim } from '../utils/formatters';
import { setupIconifyCollections } from '../utils/iconifySetup';

setupIconifyCollections();

const route = useRoute();
const router = useRouter();

const loading = ref<boolean>(true);
const errorMsg = ref<string>('');
const dossier = ref<Record<string, any> | null>(null);
const customMatchInput = ref<string>(String(route.params.id || ''));
const activeTab = ref<'overview' | 'statistics' | 'timeline'>('overview');
const statPeriod = ref<'all' | 0 | 1>('all');
let refreshTimer: ReturnType<typeof setInterval> | null = null;

function toOrdinal(n: string | number): string {
  const num = parseInt(String(n), 10);
  if (Number.isNaN(num)) return String(n);
  const rem100 = num % 100;
  if (rem100 >= 11 && rem100 <= 13) return `${num}th`;
  switch (num % 10) {
    case 1:
      return `${num}st`;
    case 2:
      return `${num}nd`;
    case 3:
      return `${num}rd`;
    default:
      return `${num}th`;
  }
}

function formatMarketText(
  rawText: string | undefined,
  hName: string,
  aName: string,
  specifiers?: Record<string, any>,
): string {
  let out = String(rawText || '');
  if (!out) return '';
  const spec = specifiers || {};
  out = out.replace(/\{!(\w+)\}/g, (_m, k) => (spec[k] !== undefined ? toOrdinal(spec[k]) : k));
  out = out.replace(/\{([+-])(\w+)\}/g, (_m, sign, k) => {
    if (spec[k] === undefined || spec[k] === null) return sign + k;
    const num = Number(spec[k]);
    if (Number.isNaN(num)) return String(spec[k]);
    const val = sign === '-' ? -num : num;
    return val > 0 ? `+${val}` : String(val);
  });
  out = out.replace(/\{\$competitor1\}/gi, hName || 'Home');
  out = out.replace(/\{\$competitor2\}/gi, aName || 'Away');
  out = out.replace(/\{(\w+)\}/g, (_m, k) => (spec[k] !== undefined ? String(spec[k]) : k));
  return out;
}

const isTennis = computed(() => Number(dossier.value?.sport_id) === 5);
const matchInfo = computed(() => dossier.value?.match_info || {});
const liveMatch = computed(
  () => dossier.value?.timeline_delta?.match || matchInfo.value?.match || {},
);
const homeTeam = computed(
  () => matchInfo.value?.match?.teams?.home || liveMatch.value?.teams?.home || {},
);
const awayTeam = computed(
  () => matchInfo.value?.match?.teams?.away || liveMatch.value?.teams?.away || {},
);
const isClubMatch = computed(
  () => Boolean(dossier.value?.home_is_club || homeTeam.value?.haslogo || !isTennis.value),
);

const homeName = computed(() => homeTeam.value?.name || dossier.value?.local_detail?.home || 'Home');
const awayName = computed(() => awayTeam.value?.name || dossier.value?.local_detail?.away || 'Away');
const homeAbbr = computed(() => homeTeam.value?.abbr || homeName.value);
const awayAbbr = computed(() => awayTeam.value?.abbr || awayName.value);

const tournamentName = computed(
  () => matchInfo.value?.season?.name || matchInfo.value?.tournament?.name || 'Tournament',
);
const realCategoryName = computed(() => matchInfo.value?.realcategory?.name || '');
const roundName = computed(
  () =>
    matchInfo.value?.match?.roundname?.name ||
    (matchInfo.value?.match?.round ? `Round ${matchInfo.value.match.round}` : ''),
);
const groundName = computed(() => matchInfo.value?.tournament?.ground?.name || '');
const stadiumName = computed(() => {
  const st = matchInfo.value?.stadium;
  return st ? `${st.name}${st.city ? ` (${st.city})` : ''}` : '';
});

const homeSeed = computed(() =>
  homeTeam.value?.seed?.seeding
    ? `Seed #${homeTeam.value.seed.seeding}`
    : homeTeam.value?.seed?.type_short || '',
);
const awaySeed = computed(() =>
  awayTeam.value?.seed?.seeding
    ? `Seed #${awayTeam.value.seed.seeding}`
    : awayTeam.value?.seed?.type_short || '',
);

const homeCountryName = computed(() => {
  const hp = dossier.value?.home_profile || {};
  return (
    homeTeam.value?.countrycode?.name ||
    homeTeam.value?.cc?.name ||
    hp.countrycode?.name ||
    hp.nationality ||
    matchInfo.value?.realcategory?.name ||
    ''
  );
});

const awayCountryName = computed(() => {
  const ap = dossier.value?.away_profile || {};
  return (
    awayTeam.value?.countrycode?.name ||
    awayTeam.value?.cc?.name ||
    ap.countrycode?.name ||
    ap.nationality ||
    matchInfo.value?.realcategory?.name ||
    ''
  );
});

const homeRankPrefix = computed(() => {
  const hp = dossier.value?.home_profile || {};
  if (isTennis.value) {
    const r = hp.singlesrank || dossier.value?.head2head?.rankings?.[homeTeam.value?._id]?.ranking;
    const pts = hp.ranking?.points ? ` (${hp.ranking.points} pts)` : '';
    return r ? `Rank #${r}${pts}` : '';
  }
  const tRows: any[] = dossier.value?.table_slice?.tablerows || [];
  const hRow = tRows.find(
    (r) => (r.team?.uid || r.team?._id) === (homeTeam.value?.uid || homeTeam.value?._id),
  );
  if (hRow?.pos) {
    return `League Pos #${hRow.pos}${hRow.pointsTotal !== undefined ? ` (${hRow.pointsTotal} pts)` : ''}`;
  }
  return homeAbbr.value;
});

const awayRankPrefix = computed(() => {
  const ap = dossier.value?.away_profile || {};
  if (isTennis.value) {
    const r = ap.singlesrank || dossier.value?.head2head?.rankings?.[awayTeam.value?._id]?.ranking;
    const pts = ap.ranking?.points ? ` (${ap.ranking.points} pts)` : '';
    return r ? `Rank #${r}${pts}` : '';
  }
  const tRows: any[] = dossier.value?.table_slice?.tablerows || [];
  const aRow = tRows.find(
    (r) => (r.team?.uid || r.team?._id) === (awayTeam.value?.uid || awayTeam.value?._id),
  );
  if (aRow?.pos) {
    return `League Pos #${aRow.pos}${aRow.pointsTotal !== undefined ? ` (${aRow.pointsTotal} pts)` : ''}`;
  }
  return awayAbbr.value;
});

const formWdlHome = computed(() => dossier.value?.form_wdl?.home || []);
const formWdlAway = computed(() => dossier.value?.form_wdl?.away || []);

const matchStatusName = computed(() => liveMatch.value?.status?.name || 'Scheduled');
const mainScoreHome = computed(() => liveMatch.value?.result?.home ?? 0);
const mainScoreAway = computed(() => liveMatch.value?.result?.away ?? 0);
const activeServer = computed(() => String(liveMatch.value?.gamescore?.service ?? ''));
const gameScoreObj = computed(() => liveMatch.value?.gamescore || null);
const periodsObj = computed(() => liveMatch.value?.periods || {});
const periodKeys = computed(() => {
  const p = periodsObj.value;
  return isTennis.value
    ? ['p1', 'p2', 'p3', 'p4', 'p5'].filter((k) => p[k])
    : ['p1', 'ft', 'ot', 'ap'].filter((k) => p[k]);
});
const periodLabels = computed(() =>
  periodKeys.value.map((k, idx) => {
    if (isTennis.value) return `S${idx + 1}`;
    if (k === 'p1') return 'HT';
    if (k === 'ft') return 'FT';
    return k.toUpperCase();
  }),
);

// Strictly 2-way (0% draw, home+away=100%) for Tennis/2-way sports, 3-way for Football when Draw exists
const winProbSummary = computed(() => {
  const d = dossier.value || {};
  if (d.win_prob_bar) {
    return {
      homePct: d.win_prob_bar.home_pct,
      drawPct: isTennis.value ? 0 : d.win_prob_bar.draw_pct || 0,
      awayPct: isTennis.value
        ? Number((100 - Number(d.win_prob_bar.home_pct || 50)).toFixed(1))
        : d.win_prob_bar.away_pct,
      oddsHome: d.win_prob_bar.odds_home,
      oddsDraw: isTennis.value ? null : d.win_prob_bar.odds_draw,
      oddsAway: d.win_prob_bar.odds_away,
    };
  }
  const mm = d.merged_markets || {};
  const rawM: any[] = d.raw_markets || [];
  const winM = rawM.find((x) => x._marketId === 1 || x._marketId === 186);
  let hProb = 50;
  let dProb = 0;
  let aProb = 50;
  if (winM && Array.isArray(winM.outcomes) && winM.outcomes.length >= 2) {
    const oHome = winM.outcomes[0];
    const oAway = winM.outcomes[winM.outcomes.length - 1];
    const oDraw = !isTennis.value && winM.outcomes.length >= 3 ? winM.outcomes[1] : null;
    if (oHome.odds && oAway.odds) {
      const inv1 = 1 / Number(oHome.odds);
      const invX = oDraw?.odds ? 1 / Number(oDraw.odds) : 0;
      const inv2 = 1 / Number(oAway.odds);
      const sumInv = inv1 + invX + inv2;
      hProb = Number(((inv1 / sumInv) * 100).toFixed(1));
      if (invX > 0) {
        aProb = Number(((inv2 / sumInv) * 100).toFixed(1));
        dProb = Number(Math.max(0, 100 - hProb - aProb).toFixed(1));
      } else {
        dProb = 0;
        aProb = Number(Math.max(0, 100 - hProb).toFixed(1));
      }
    }
  }
  return {
    homePct: hProb,
    drawPct: dProb,
    awayPct: aProb,
    oddsHome: mm.odds_home ?? null,
    oddsDraw: isTennis.value ? null : mm.odds_draw ?? null,
    oddsAway: mm.odds_away ?? null,
  };
});

const allFormattedMarkets = computed(() => {
  const rawM: any[] = dossier.value?.raw_markets || [];
  return rawM.map((mk) => ({
    marketId: mk._marketId,
    title: formatMarketText(mk.name || `Market #${mk._marketId}`, homeName.value, awayName.value, mk.specifiers),
    outcomes: (mk.outcomes || []).map((o: any) => ({
      label: formatMarketText(o.name, homeName.value, awayName.value, mk.specifiers),
      odds: o.odds,
    })),
  }));
});

const overviewMarkets = computed(() => allFormattedMarkets.value.slice(0, 6));

const surfaceOrSeasonRows = computed(() => {
  const d = dossier.value || {};
  if (isTennis.value) {
    const hGs: any[] = d.home_profile?.groundstats || [];
    const aGs: any[] = d.away_profile?.groundstats || [];
    const grounds = ['All surfaces', 'Hardcourt', 'Indoor', 'Clay', 'Grass'];
    return grounds.map((gName) => {
      const hg = hGs.find((x) => x.ground === gName) || { matcheswon: 0, matcheslost: 0, matcheswon_percent: 0 };
      const ag = aGs.find((x) => x.ground === gName) || { matcheswon: 0, matcheslost: 0, matcheswon_percent: 0 };
      return {
        label: gName,
        home: `${hg.matcheswon}-${hg.matcheslost} (${hg.matcheswon_percent}%)`,
        away: `${ag.matcheswon}-${ag.matcheslost} (${ag.matcheswon_percent}%)`,
      };
    });
  }
  const hSc = d.home_scoring_conceding?.stats || {};
  const aSc = d.away_scoring_conceding?.stats || {};
  return [
    { label: 'Matches Analysed', home: hSc.matches ?? '—', away: aSc.matches ?? '—' },
    { label: 'Goals Scored (Avg)', home: hSc.scoredsum ? `${hSc.scoredsum} (${hSc.scoredavg})` : '—', away: aSc.scoredsum ? `${aSc.scoredsum} (${aSc.scoredavg})` : '—' },
    { label: 'Goals Conceded (Avg)', home: hSc.concededsum ? `${hSc.concededsum} (${hSc.concededavg})` : '—', away: aSc.concededsum ? `${aSc.concededsum} (${aSc.concededavg})` : '—' },
    { label: 'Scored First (1-0)', home: hSc.firstgoal ?? '—', away: aSc.firstgoal ?? '—' },
    { label: 'Clean Sheets', home: hSc.cleansheets ?? '—', away: aSc.cleansheets ?? '—' },
  ];
});

const h2hEdge = computed(() => dossier.value?.h2h_edge || null);

const h2hMeetings = computed(() => {
  const vsMatches: any[] = dossier.value?.versus?.matches || [];
  if (vsMatches.length) {
    return vsMatches.map((vm) => {
      const hs = Number(vm.result?.home ?? 0);
      const as_ = Number(vm.result?.away ?? 0);
      const pList = ['p1', 'p2', 'p3'].filter((k) => vm.periods?.[k]).map((k) => `${vm.periods[k].home}-${vm.periods[k].away}`).join(', ');
      return {
        date: vm.time?.date || '—',
        home: vm.teams?.home?.name || homeName.value,
        away: vm.teams?.away?.name || awayName.value,
        scoreMain: `${hs}-${as_}`,
        scoreInterim: pList ? `(${pList})` : '',
        winner: vm.result?.winner === 'home' || hs > as_ ? 'H' : vm.result?.winner === 'away' || as_ > hs ? 'A' : 'D',
      };
    });
  }
  const localH2H: any[] = dossier.value?.local_detail?.h2h || [];
  return localH2H.map((m) => {
    const sp = splitScoreAndInterim(m.score);
    return {
      date: m.date,
      home: m.home,
      away: m.away,
      scoreMain: sp.main,
      scoreInterim: sp.interim,
      winner: m.outcome || 'D',
    };
  });
});

const homeMissing = computed(() => dossier.value?.home_missing_players || []);
const awayMissing = computed(() => dossier.value?.away_missing_players || []);

const homeLastMatches = computed(() =>
  (dossier.value?.home_last_matches || []).map((lm: any) => ({
    home: lm.teams?.home?.name || '',
    away: lm.teams?.away?.name || '',
    score: `${lm.result?.home ?? ''}-${lm.result?.away ?? ''}`,
  })),
);

const awayLastMatches = computed(() =>
  (dossier.value?.away_last_matches || []).map((lm: any) => ({
    home: lm.teams?.home?.name || '',
    away: lm.teams?.away?.name || '',
    score: `${lm.result?.home ?? ''}-${lm.result?.away ?? ''}`,
  })),
);

function parseLeadingNum(v: any): number {
  if (typeof v === 'number') return v;
  const m = String(v || '').match(/^(\d+(?:\.\d+)?)/);
  return m ? Number(m[1]) : 0;
}

const boxscoreStatRows = computed(() => {
  const values = dossier.value?.match_details?.values || {};
  const rowsDef = isTennis.value
    ? [
        { allKey: '130', setKey: '1518', label: 'Aces' },
        { allKey: '132', setKey: '1525', label: 'Double Faults' },
        { allKey: '1189', setKey: '1524', label: '1st Serve Successful' },
        { allKey: '137', setKey: '1529', label: '1st Serve Points Won' },
        { allKey: '138', setKey: '1530', label: '2nd Serve Points Won' },
        { allKey: '139', setKey: '1526', label: 'Break Points Won' },
        { allKey: '141', setKey: '1520', label: 'Service Points Won' },
        { allKey: '1410', setKey: '1522', label: 'Receiver Points Won' },
        { allKey: '136', setKey: '1523', label: 'Total Points Won' },
        { allKey: 'gameswon', setKey: 'gameswonperiod', label: 'Games Won' },
      ]
    : [
        { allKey: '110', setKey: '1199', label: 'Ball Possession (%)' },
        { allKey: 'goalattempts', setKey: 'goalattemptsperiod', label: 'Goal Attempts' },
        { allKey: '125', setKey: 'shotsonperiod', label: 'Shots on Target' },
        { allKey: '126', setKey: 'shotsoffperiod', label: 'Shots off Target' },
        { allKey: '124', setKey: '1634', label: 'Corner Kicks' },
        { allKey: '127', setKey: 'savesperiod', label: 'Goalkeeper Saves' },
        { allKey: '129', setKey: 'foulsperiod', label: 'Fouls' },
        { allKey: '40', setKey: '1627', label: 'Yellow Cards' },
        { allKey: '1029', setKey: 'dangerousperiod', label: 'Dangerous Attacks' },
      ];

  const out: Array<{ label: string; homeDisplay: string; awayDisplay: string; homePct: number; awayPct: number }> = [];
  for (const r of rowsDef) {
    let hVal: any;
    let aVal: any;
    if (statPeriod.value === 'all') {
      const item = values[r.allKey];
      if (!item) continue;
      hVal = item.value?.home ?? 0;
      aVal = item.value?.away ?? 0;
    } else {
      const idx = Number(statPeriod.value);
      const item = values[r.setKey];
      if (!item) continue;
      const hRaw = item.value?.home;
      const aRaw = item.value?.away;
      hVal = Array.isArray(hRaw) ? hRaw[idx] ?? '0' : String(hRaw || '').split('/')[idx] ?? '0';
      aVal = Array.isArray(aRaw) ? aRaw[idx] ?? '0' : String(aRaw || '').split('/')[idx] ?? '0';
    }
    const hNum = parseLeadingNum(hVal);
    const aNum = parseLeadingNum(aVal);
    const hasAny = hNum + aNum > 0;
    const tot = Math.max(1, hNum + aNum);
    const hPct = hasAny ? Math.round((hNum / tot) * 100) : 0;
    const aPct = hasAny ? 100 - hPct : 0;
    out.push({
      label: r.label,
      homeDisplay: String(hVal),
      awayDisplay: String(aVal),
      homePct: hPct,
      awayPct: aPct,
    });
  }
  return out;
});

const timelineEvents = computed(() => {
  const evs: any[] = dossier.value?.full_timeline?.events || [];
  return evs
    .filter((e) => ['score_change_tennis', 'periodscore', 'goal', 'card', 'substitution'].includes(e.type))
    .slice()
    .reverse()
    .slice(0, 60)
    .map((ev) => ({
      name: ev.name || ev.type,
      side:
        ev.service === '1' || ev.team === 'home'
          ? homeAbbr.value
          : ev.service === '2' || ev.team === 'away'
            ? awayAbbr.value
            : '—',
      timeStr:
        ev.time !== undefined && ev.time !== null && ev.time !== -1
          ? `${ev.time}'`
          : ev.set_score
            ? `${ev.set_score.home}-${ev.set_score.away}`
            : '—',
      scoreStr: ev.game_points
        ? `${ev.game_points.home}-${ev.game_points.away}`
        : ev.result && ev.result.home !== undefined
          ? `${ev.result.home}-${ev.result.away}`
          : '—',
    }));
});

async function fetchDossier() {
  loading.value = true;
  errorMsg.value = '';
  const idParam = String(route.params.id || '').trim();
  const homeQ = String(route.query.home || '').trim();
  const awayQ = String(route.query.away || '').trim();
  const lgQ = String(route.query.league || '').trim();

  const qs = new URLSearchParams();
  if (idParam && idParam !== 'lookup') qs.set('matchId', idParam);
  if (homeQ) qs.set('home', homeQ);
  if (awayQ) qs.set('away', awayQ);
  if (lgQ) qs.set('league', lgQ);

  try {
    const resp = await fetch(`/api/match-center?${qs.toString()}`);
    const data = await resp.json();
    if (data && data.ok !== false && (data.match_info || data.local_detail)) {
      dossier.value = data;
      if (data.match_id) customMatchInput.value = String(data.match_id);
    } else {
      errorMsg.value = data?.error || `Could not load Match Center for "${idParam}".`;
    }
  } catch (err) {
    errorMsg.value = `Network error loading Match Center: ${err}`;
  } finally {
    loading.value = false;
  }
}

function jumpToMatchId() {
  const val = customMatchInput.value.trim();
  if (!val) return;
  router.push(`/match/${encodeURIComponent(val)}`);
}

watch(
  () => [route.params.id, route.query.home, route.query.away],
  () => {
    fetchDossier();
  },
);

onMounted(() => {
  fetchDossier();
  refreshTimer = setInterval(fetchDossier, 15000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
