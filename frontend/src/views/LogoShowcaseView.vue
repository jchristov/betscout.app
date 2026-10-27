<template>
  <div class="min-h-screen px-4 sm:px-6 py-7 max-w-[1380px] mx-auto text-slate-100">
    <div class="flex flex-wrap justify-between items-center gap-4 mb-6">
      <div>
        <span class="px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50">
          NEWEST BATCH · 10 STADIUM &amp; FIELD VARIATIONS WITH 6.6 OVERSIZED COMPASS (8.1 – 8.10)
        </span>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-white mt-2">
          Stadium &amp; Field Behind the Oversized 6.6 Chiseled Compass (8.1 – 8.10)
        </h1>
        <p class="text-sm text-slate-300 mt-1">
          Uses <b>Option 6.6’s oversized chiseled compass needles</b> piercing past 10 stadium &amp; field variations
          (tilted stadium pitch oval, tilted rectangular soccer field, colosseum bowl, 3D isometric pitch, mowed turf
          field, yard-line gridiron, championship court, 6.6 ball+pitch hybrid, floodlit arena bowl, and +40° pitch).
          Option 6.6 and all previous batches are kept right below.
        </p>
      </div>
      <div class="flex gap-2">
        <router-link
          to="/"
          class="btn-press px-4 py-2 rounded-xl text-xs font-bold bg-slate-900 text-slate-200 border border-slate-700"
        >
          Landing Page
        </router-link>
        <router-link
          to="/app"
          class="btn-press px-4 py-2 rounded-xl text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50"
        >
          Live Quant Desk
        </router-link>
      </div>
    </div>

    <!-- BATCH 6 (NEWEST): 10 Stadium & Field Variations with 6.6 Oversized Compass (8.1 - 8.10) -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-10">
      <div
        v-for="opt in STADIUM_FIELD_66_VARIATIONS"
        :key="opt.id"
        class="card-surface rounded-2xl p-4 flex flex-col justify-between border-t-2 border-t-emerald-400"
      >
        <div>
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50">
              #{{ opt.id }}
            </span>
            <span class="text-[11px] font-semibold text-emerald-300 truncate">{{ opt.subtitle }}</span>
          </div>

          <div class="flex items-center justify-center py-3.5 bg-slate-950/75 rounded-xl border border-slate-800 mb-2.5">
            <div class="w-[76px] h-[76px]" v-html="opt.svg"></div>
          </div>

          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-obsidian/90 border border-slate-800 mb-2.5">
            <div class="w-[32px] h-[32px] shrink-0" v-html="opt.svg"></div>
            <span class="text-[17px] font-extrabold tracking-tight whitespace-nowrap">
              <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
            </span>
          </div>

          <h2 class="text-sm font-extrabold text-white mb-1">{{ opt.name }}</h2>
          <p class="text-xs text-slate-300 leading-relaxed">{{ opt.description }}</p>
        </div>
      </div>
    </div>

    <!-- BATCH 5 KEPT: 10 Variations of Option 5.6 (6.1 - 6.10, including 6.6) -->
    <div class="mb-4 pt-4 border-t border-slate-800">
      <span class="px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-400/50">
        BATCH 5 KEPT (INCLUDING #6.6) · 6.1 – 6.10
      </span>
      <h2 class="text-xl font-extrabold text-white mt-2">Option 5.6 Prolate Variations (6.1 – 6.10)</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-10">
      <div
        v-for="opt in PROLATE_56_VARIATIONS"
        :key="opt.id"
        class="card-surface rounded-2xl p-4 flex flex-col justify-between border-t-2 border-t-amber-400"
      >
        <div>
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-amber-500/20 text-amber-300 border border-amber-400/50">
              #{{ opt.id }}
            </span>
            <span class="text-[11px] font-semibold text-amber-300 truncate">{{ opt.subtitle }}</span>
          </div>

          <div class="flex items-center justify-center py-3.5 bg-slate-950/75 rounded-xl border border-slate-800 mb-2.5">
            <div class="w-[76px] h-[76px]" v-html="opt.svg"></div>
          </div>

          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-obsidian/90 border border-slate-800 mb-2.5">
            <div class="w-[32px] h-[32px] shrink-0" v-html="opt.svg"></div>
            <span class="text-[17px] font-extrabold tracking-tight whitespace-nowrap">
              <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
            </span>
          </div>

          <h2 class="text-sm font-extrabold text-white mb-1">{{ opt.name }}</h2>
          <p class="text-xs text-slate-300 leading-relaxed">{{ opt.description }}</p>
        </div>
      </div>
    </div>

    <!-- BATCH 4 KEPT: 5.1 - 5.10 -->
    <div class="mb-4 pt-4 border-t border-slate-800">
      <span class="px-3 py-1 rounded-full text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50">
        BATCH 4 KEPT · VARIOUS BALLS BEHIND THE COMPASS (5.1 – 5.10)
      </span>
      <h2 class="text-xl font-extrabold text-white mt-2">Various Sports Balls Behind the Compass (5.1 – 5.10)</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-10">
      <div
        v-for="opt in BALL_BEHIND_COMPASS_OPTIONS"
        :key="opt.id"
        class="card-surface rounded-2xl p-4 flex flex-col justify-between border-t-2 border-t-sky-400"
      >
        <div>
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-sky-500/20 text-sky-300 border border-sky-400/50">
              #{{ opt.id }}
            </span>
            <span class="text-[11px] font-semibold text-sky-300 truncate">{{ opt.subtitle }}</span>
          </div>

          <div class="flex items-center justify-center py-3.5 bg-slate-950/75 rounded-xl border border-slate-800 mb-2.5">
            <div class="w-[76px] h-[76px]" v-html="opt.svg"></div>
          </div>

          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-obsidian/90 border border-slate-800 mb-2.5">
            <div class="w-[32px] h-[32px] shrink-0" v-html="opt.svg"></div>
            <span class="text-[17px] font-extrabold tracking-tight whitespace-nowrap">
              <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
            </span>
          </div>

          <h2 class="text-sm font-extrabold text-white mb-1">{{ opt.name }}</h2>
          <p class="text-xs text-slate-300 leading-relaxed">{{ opt.description }}</p>
        </div>
      </div>
    </div>

    <!-- BATCH 3 KEPT: 4.1 - 4.10 -->
    <div class="mb-4 pt-4 border-t border-slate-800">
      <span class="px-3 py-1 rounded-full text-[11px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-400/50">
        BATCH 3 KEPT · PURE VERTEX VARIATIONS (4.1 – 4.10)
      </span>
      <h2 class="text-xl font-extrabold text-white mt-2">Pure Chiseled Vertex + Sports Variations 4.1 – 4.10</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-10">
      <div
        v-for="opt in PURE_VERTEX_SPORTS_OPTIONS"
        :key="opt.id"
        class="card-surface rounded-2xl p-4 flex flex-col justify-between border-t-2 border-t-cyan-400"
      >
        <div>
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-cyan-500/20 text-cyan-300 border border-cyan-400/50">
              #{{ opt.id }}
            </span>
            <span class="text-[11px] font-semibold text-cyan-300 truncate">{{ opt.subtitle }}</span>
          </div>

          <div class="flex items-center justify-center py-3.5 bg-slate-950/75 rounded-xl border border-slate-800 mb-2.5">
            <div class="w-[76px] h-[76px]" v-html="opt.svg"></div>
          </div>

          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-obsidian/90 border border-slate-800 mb-2.5">
            <div class="w-[32px] h-[32px] shrink-0" v-html="opt.svg"></div>
            <span class="text-[17px] font-extrabold tracking-tight whitespace-nowrap">
              <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
            </span>
          </div>

          <h2 class="text-sm font-extrabold text-white mb-1">{{ opt.name }}</h2>
          <p class="text-xs text-slate-300 leading-relaxed">{{ opt.description }}</p>
        </div>
      </div>
    </div>

    <!-- BATCH 2 KEPT: 3.1 - 3.10 -->
    <div class="mb-4 pt-4 border-t border-slate-800">
      <span class="px-3 py-1 rounded-full text-[11px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-400/50">
        BATCH 2 KEPT · 3.1 – 3.10
      </span>
      <h2 class="text-xl font-extrabold text-white mt-2">Sports-Fused Variations 3.1 – 3.10 (No Middle Dot)</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-10">
      <div
        v-for="opt in SPORTS_COMPASS_3_OPTIONS"
        :key="opt.id"
        class="card-surface rounded-2xl p-4 flex flex-col justify-between border-t-2 border-t-indigo-400"
      >
        <div>
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-indigo-500/20 text-indigo-300 border border-indigo-400/50">
              #{{ opt.id }}
            </span>
            <span class="text-[11px] font-semibold text-indigo-300 truncate">{{ opt.subtitle }}</span>
          </div>

          <div class="flex items-center justify-center py-3.5 bg-slate-950/75 rounded-xl border border-slate-800 mb-2.5">
            <div class="w-[76px] h-[76px]" v-html="opt.svg"></div>
          </div>

          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-obsidian/90 border border-slate-800 mb-2.5">
            <div class="w-[32px] h-[32px] shrink-0" v-html="opt.svg"></div>
            <span class="text-[17px] font-extrabold tracking-tight whitespace-nowrap">
              <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
            </span>
          </div>

          <h2 class="text-sm font-extrabold text-white mb-1">{{ opt.name }}</h2>
          <p class="text-xs text-slate-300 leading-relaxed">{{ opt.description }}</p>
        </div>
      </div>
    </div>

    <!-- BATCH 1 KEPT: 7.1 - 7.10 -->
    <div class="mb-4 pt-4 border-t border-slate-800">
      <span class="px-3 py-1 rounded-full text-[11px] font-bold bg-violet-500/20 text-violet-300 border border-violet-400/50">
        BATCH 1 KEPT · 7.1 – 7.10
      </span>
      <h2 class="text-xl font-extrabold text-white mt-2">Original Compass Rose Variations 7.1 – 7.10 (No Middle Dot)</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <div
        v-for="opt in LOGO_OPTIONS"
        :key="opt.id"
        class="card-surface rounded-2xl p-4 flex flex-col justify-between border-t-2 border-t-violet-400"
      >
        <div>
          <div class="flex items-center justify-between gap-2 mb-2.5">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-violet-500/20 text-violet-300 border border-violet-400/50">
              #7.{{ opt.id }}
            </span>
            <span class="text-[11px] font-semibold text-violet-300 truncate">{{ opt.subtitle }}</span>
          </div>

          <div class="flex items-center justify-center py-3.5 bg-slate-950/75 rounded-xl border border-slate-800 mb-2.5">
            <div class="w-[76px] h-[76px]" v-html="opt.svg"></div>
          </div>

          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-obsidian/90 border border-slate-800 mb-2.5">
            <div class="w-[32px] h-[32px] shrink-0" v-html="opt.svg"></div>
            <span class="text-[17px] font-extrabold tracking-tight whitespace-nowrap">
              <span class="text-white">Bet</span><span class="text-emerald-400">Scout</span>
            </span>
          </div>

          <h2 class="text-sm font-extrabold text-white mb-1">{{ opt.name }}</h2>
          <p class="text-xs text-slate-300 leading-relaxed">{{ opt.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  BALL_BEHIND_COMPASS_OPTIONS,
  LOGO_OPTIONS,
  PROLATE_56_VARIATIONS,
  PURE_VERTEX_SPORTS_OPTIONS,
  SPORTS_COMPASS_3_OPTIONS,
  STADIUM_FIELD_66_VARIATIONS,
} from '../utils/logoOptions';
</script>
