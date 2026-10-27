<template>
  <div class="min-h-screen flex flex-col">
    <!-- Global Toast Notification -->
    <div
      v-if="store.toastMessage"
      class="fixed bottom-5 right-5 z-50 flex items-center gap-3 bg-navy-800/95 border border-sky-400/50 text-slate-100 px-4 py-3 rounded-xl shadow-2xl backdrop-blur-md text-xs font-semibold"
    >
      <span>{{ store.toastMessage }}</span>
      <button
        type="button"
        class="text-slate-400 hover:text-white px-1.5 py-0.5 rounded border border-slate-700"
        @click="store.toastMessage = ''"
      >
        ✕
      </button>
    </div>

    <router-view />
    <div id="bsFloatingTooltip" ref="tooltipEl"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useBetscoutStore } from './stores/betscoutStore';
import { getBadgeTooltipText } from './utils/formatters';

const store = useBetscoutStore();
const tooltipEl = ref<HTMLElement | null>(null);

function onMouseOver(e: MouseEvent) {
  const tipEl = tooltipEl.value;
  if (!tipEl) return;
  const rawTarget = e.target as HTMLElement | null;
  if (!rawTarget || typeof rawTarget.closest !== 'function') {
    tipEl.style.display = 'none';
    return;
  }
  const target = rawTarget.closest('[data-tip], [title], .pill-tip') as HTMLElement | null;
  if (!target) {
    tipEl.style.display = 'none';
    return;
  }
  let msg = target.getAttribute('data-tip') || '';
  if (!msg && target.hasAttribute('title')) {
    msg = target.getAttribute('title') || '';
    if (msg) {
      target.setAttribute('data-tip', msg);
      target.removeAttribute('title');
    }
  }
  if (!msg && target.classList.contains('pill-tip')) {
    msg = getBadgeTooltipText(target.textContent);
    if (msg) target.setAttribute('data-tip', msg);
  }
  if (!msg) {
    tipEl.style.display = 'none';
    return;
  }
  tipEl.textContent = msg;
  tipEl.style.display = 'block';
  const rect = target.getBoundingClientRect();
  const tipRect = tipEl.getBoundingClientRect();
  let top = rect.top - tipRect.height - 8;
  if (top < 8) top = rect.bottom + 8;
  let left = rect.left + rect.width / 2 - tipRect.width / 2;
  left = Math.max(8, Math.min(window.innerWidth - tipRect.width - 8, left));
  tipEl.style.top = `${Math.round(top)}px`;
  tipEl.style.left = `${Math.round(left)}px`;
}

function onMouseOut(e: MouseEvent) {
  const tipEl = tooltipEl.value;
  if (!tipEl) return;
  const related = e.relatedTarget as HTMLElement | null;
  if (!related || typeof related.closest !== 'function' || !related.closest('[data-tip], [title], .pill-tip')) {
    tipEl.style.display = 'none';
  }
}

function onScroll() {
  if (tooltipEl.value) tooltipEl.value.style.display = 'none';
}

onMounted(async () => {
  document.addEventListener('mouseover', onMouseOver);
  document.addEventListener('mouseout', onMouseOut);
  window.addEventListener('scroll', onScroll, { passive: true });
  await store.fetchSnapshot();
  store.connectLiveStream();
});

onUnmounted(() => {
  document.removeEventListener('mouseover', onMouseOver);
  document.removeEventListener('mouseout', onMouseOut);
  window.removeEventListener('scroll', onScroll);
});
</script>
