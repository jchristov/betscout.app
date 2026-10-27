<template>
  <div class="min-h-screen px-4 sm:px-6 py-8 max-w-[1320px] mx-auto text-slate-100">
    <div class="flex flex-wrap justify-between items-center gap-4 mb-6">
      <div>
        <span class="px-3 py-1 rounded-full text-[11px] font-bold bg-sky-500/20 text-sky-300 border border-sky-400/50">
          BETSCOUT BRAND STUDIO · 10 VARIATIONS OF OPTION 7 (THE COMPASS ROSE)
        </span>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-white mt-2">
          Choose Your Compass Rose Variation (7.1 – 7.10)
        </h1>
        <p class="text-sm text-slate-300 mt-1">
          Every option is shown at both <b>App Icon size (76×76)</b> and <b>Live Header Lockup size (36×36)</b>. Tell me
          the number (1–10) you prefer and I will apply it across all SVG, PNG &amp; PWA icons!
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

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <div
        v-for="opt in LOGO_OPTIONS"
        :key="opt.id"
        class="card-surface rounded-2xl p-5 flex flex-col justify-between border-t-2 border-t-sky-400"
      >
        <div>
          <div class="flex items-center justify-between gap-2 mb-3">
            <span class="px-2.5 py-0.5 rounded-full text-[11px] font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-400/50">
              #{{ opt.id }}
            </span>
            <span class="text-[11px] font-semibold text-sky-300">{{ opt.subtitle }}</span>
          </div>

          <!-- Large 76x76 Emblem Preview -->
          <div class="flex items-center justify-center py-4 bg-slate-950/75 rounded-xl border border-slate-800 mb-3">
            <div class="w-[76px] h-[76px]" v-html="opt.svg"></div>
          </div>

          <!-- Header Lockup Preview (34x34 + BetScout Text) -->
          <div class="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-obsidian/90 border border-slate-800 mb-3">
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
import { LOGO_OPTIONS } from '../utils/logoOptions';
</script>
