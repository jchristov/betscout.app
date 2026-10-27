import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import {
  type BestBetItem,
  SPORT_EMOJIS,
  computeBankerBoosterCombos,
} from '../utils/formatters';

export const useBetscoutStore = defineStore('betscout', () => {
  const loading = ref<boolean>(true);
  const actionBusy = ref<boolean>(false);
  const actionProgressText = ref<string>('Syncing paper-betting ledger & live match scores...');
  const toastMessage = ref<string>('');
  const streamStatus = ref<'connecting' | 'online' | 'reconnecting'>('connecting');
  const serverTimeLocal = ref<string>('Ready');

  // Snapshot payload
  const totalMatches = ref<number>(59062);
  const vetoedBets = ref<number>(0);
  const generatedAt = ref<string>('');
  const generatedAtLocal = ref<string>('—');
  const timezone = ref<string>('Europe/Vienna');
  const role = ref<'admin' | 'pro' | 'free'>('admin');
  const isAdmin = ref<boolean>(true);
  const isPro = ref<boolean>(true);
  const userEmail = ref<string>('');
  const firebaseAuthCfg = ref<Record<string, any>>({ enabled: false });
  const monetizationCfg = ref<Record<string, any>>({ enabled: false, free_preview_picks_count: 0 });
  const discordEnv = ref<Record<string, any>>({ configured: false });
  const telegramEnv = ref<Record<string, any>>({ configured: false });
  const settings = ref<Record<string, any>>({});

  const bestBets = ref<BestBetItem[]>([]);
  const paperLedger = ref<Record<string, any>>({
    settled_count: 57,
    settled_wins: 55,
    settled_losses: 2,
    settled_profit_u: 20.07,
    settled_roi_best: 0.352,
    kelly_growth_pct: 27.25,
    mean_clv_pct: 0.0067,
    exact_score_graded: 35,
    exact_score_hits: 24,
    exact_score_hit_rate_pct: 68.6,
    live_count: 0,
    pending_count: 13,
    bets: [],
    combos: [],
    by_sport: [],
    by_tier: [],
    settled_cum_pnl: [],
    kelly_cum_pnl: [],
  });
  const recommendedDoubles = ref<any[]>([]);
  const qualifyingPicks = ref<any[]>([]);
  const tennisPicks = ref<any[]>([]);
  const otherSportPicks = ref<any[]>([]);
  const backtestRisk = ref<Record<string, any>>({});

  // Interactive UI Filters
  const sportFilter = ref<string>('all');
  const dayFilter = ref<string>('all');
  const minOdds = ref<number>(1.10);
  const searchQuery = ref<string>('');
  const tzMode = ref<'local' | 'utc'>('local');
  const disabledSports = ref<Set<string>>(new Set());
  const customSelectedMatches = ref<Set<string>>(new Set());

  // Auth Token state
  const firebaseIdToken = ref<string>('');
  const customApiKey = ref<string>(
    typeof localStorage !== 'undefined' ? localStorage.getItem('bs_api_key') || '' : '',
  );
  let firebaseAuthObj: any = null;
  let activeEventSource: EventSource | null = null;

  function showToast(msg: string) {
    toastMessage.value = msg;
    setTimeout(() => {
      if (toastMessage.value === msg) toastMessage.value = '';
    }, 5500);
  }

  function getAuthHeaders(includeJson = true): Record<string, string> {
    const h: Record<string, string> = {};
    if (includeJson) h['Content-Type'] = 'application/json';
    if (firebaseIdToken.value) {
      h['Authorization'] = `Bearer ${firebaseIdToken.value}`;
    }
    if (customApiKey.value) {
      h['X-API-Key'] = customApiKey.value;
    }
    return h;
  }

  function applySnapshot(snap: Record<string, any>) {
    if (!snap) return;
    if (snap.server_time_local) serverTimeLocal.value = `Live Sync: ${snap.server_time_local}`;
    if (snap.total_matches) totalMatches.value = Number(snap.total_matches);
    if (snap.vetoed_bets !== undefined) vetoedBets.value = Number(snap.vetoed_bets);
    if (snap.generated_at) generatedAt.value = String(snap.generated_at);
    if (snap.generated_at_local) generatedAtLocal.value = String(snap.generated_at_local);
    if (snap.timezone) timezone.value = String(snap.timezone);
    if (snap.role) {
      role.value = snap.role;
      isAdmin.value = snap.role === 'admin';
      isPro.value = snap.role === 'admin' || snap.role === 'pro';
    }
    if (snap.auth) {
      firebaseAuthCfg.value = snap.auth;
      isAdmin.value = Boolean(snap.auth.is_admin);
      isPro.value = Boolean(snap.auth.is_pro);
      if (snap.auth.role) role.value = snap.auth.role;
    }
    if (snap.monetization) monetizationCfg.value = snap.monetization;
    if (snap.discord_env) discordEnv.value = snap.discord_env;
    if (snap.telegram_env) telegramEnv.value = snap.telegram_env;
    if (snap.settings) {
      settings.value = snap.settings;
      if (Array.isArray(snap.settings.disabled_sports)) {
        disabledSports.value = new Set(snap.settings.disabled_sports.map((x: string) => String(x).toLowerCase()));
      }
    }
    if (Array.isArray(snap.best_bets)) bestBets.value = snap.best_bets;
    if (snap.paper_ledger) paperLedger.value = snap.paper_ledger;
    if (Array.isArray(snap.recommended_doubles)) recommendedDoubles.value = snap.recommended_doubles;
    if (Array.isArray(snap.qualifying_picks)) qualifyingPicks.value = snap.qualifying_picks;
    if (Array.isArray(snap.tennis_picks)) tennisPicks.value = snap.tennis_picks;
    if (Array.isArray(snap.other_sport_picks)) otherSportPicks.value = snap.other_sport_picks;
    if (snap.backtest_risk) backtestRisk.value = snap.backtest_risk;
  }

  async function fetchSnapshot() {
    try {
      const resp = await fetch('/api/snapshot?min_odds=1.05', {
        headers: getAuthHeaders(false),
        cache: 'no-store',
      });
      if (resp.ok) {
        const data = await resp.json();
        applySnapshot(data);
        if (data.auth?.enabled && data.auth?.api_key) {
          await initFirebaseClient(data.auth);
        }
      }
    } catch (_) {
      // ignore offline error
    } finally {
      loading.value = false;
    }
  }

  function connectLiveStream() {
    if (typeof window === 'undefined' || typeof EventSource === 'undefined') return;
    if (activeEventSource) {
      try {
        activeEventSource.close();
      } catch (_) {}
      activeEventSource = null;
    }
    const tok = firebaseIdToken.value || customApiKey.value;
    const qs = tok ? `?token=${encodeURIComponent(tok)}` : '';
    const es = new EventSource(`/api/stream${qs}`);
    activeEventSource = es;
    es.addEventListener('update', (ev: MessageEvent) => {
      streamStatus.value = 'online';
      try {
        const snap = JSON.parse(ev.data);
        if (snap.pipeline_status?.running && snap.pipeline_status?.step) {
          actionProgressText.value = snap.pipeline_status.step;
        }
        applySnapshot(snap);
      } catch (_) {}
    });
    es.onerror = () => {
      streamStatus.value = 'reconnecting';
    };
  }

  async function initFirebaseClient(authObj: Record<string, any>) {
    if (firebaseAuthObj || !authObj?.enabled || !authObj?.api_key) return;
    try {
      const { initializeApp } = await import('firebase/app');
      const { getAuth, onAuthStateChanged } = await import('firebase/auth');
      const fbApp = initializeApp({
        apiKey: authObj.api_key,
        authDomain: authObj.auth_domain || `${authObj.project_id}.firebaseapp.com`,
        projectId: authObj.project_id || undefined,
      });
      const auth = getAuth(fbApp);
      firebaseAuthObj = { auth };
      onAuthStateChanged(auth, async (user) => {
        if (user) {
          userEmail.value = user.email || '';
          firebaseIdToken.value = await user.getIdToken();
          document.cookie = `__session=${encodeURIComponent(firebaseIdToken.value)}; path=/; max-age=3600; SameSite=Lax`;
          await fetchSnapshot();
          connectLiveStream();
        } else {
          document.cookie = '__session=; path=/; max-age=0; SameSite=Lax';
          userEmail.value = '';
          firebaseIdToken.value = '';
          await fetchSnapshot();
          connectLiveStream();
        }
      });
    } catch (_) {}
  }

  async function triggerSignInOut() {
    if (!firebaseAuthObj) {
      if (firebaseAuthCfg.value?.enabled) {
        await initFirebaseClient(firebaseAuthCfg.value);
      }
      if (!firebaseAuthObj) {
        showToast('ℹ️ Local Admin mode is active — no Google Sign-In required.');
        return;
      }
    }
    const { GoogleAuthProvider, signInWithPopup, signOut } = await import('firebase/auth');
    if (userEmail.value) {
      await signOut(firebaseAuthObj.auth);
      showToast('👋 Signed out.');
    } else {
      try {
        const provider = new GoogleAuthProvider();
        const cred = await signInWithPopup(firebaseAuthObj.auth, provider);
        if (cred?.user) {
          showToast(`🔓 Signed in as ${cred.user.email}`);
        }
      } catch (err: any) {
        showToast(`❌ Sign-in cancelled or failed: ${err?.message || err}`);
      }
    }
  }

  function matchDayKey(b: BestBetItem): string {
    const loc = String(b.date_local || b.date || '');
    return loc.slice(0, 10);
  }

  const availableDays = computed(() => {
    const counts: Record<string, number> = {};
    for (const b of bestBets.value) {
      if (disabledSports.value.has(b.sport_cat)) continue;
      const d = matchDayKey(b);
      if (d.length === 10 && d[4] === '-') {
        counts[d] = (counts[d] || 0) + 1;
      }
    }
    return Object.keys(counts)
      .sort()
      .map((d) => ({ day: d, count: counts[d] }));
  });

  const activeBestBets = computed(() =>
    bestBets.value.filter((b) => !disabledSports.value.has(b.sport_cat)),
  );

  const visibleBestBets = computed(() => {
    const q = searchQuery.value.trim().toLowerCase();
    return activeBestBets.value.filter((b) => {
      if (Number(b.odds || 0) <= minOdds.value) return false;
      if (sportFilter.value !== 'all' && b.sport_cat !== sportFilter.value) return false;
      if (dayFilter.value !== 'all') {
        const d = matchDayKey(b);
        if (dayFilter.value === 'next48h') {
          const firstTwo = availableDays.value.slice(0, 2).map((x) => x.day);
          if (firstTwo.length && !firstTwo.includes(d)) return false;
        } else if (d !== dayFilter.value) {
          return false;
        }
      }
      if (q) {
        const hay = `${b.match} ${b.sport_league} ${b.competition || ''} ${b.pick}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  });

  const mispricedBets = computed(() =>
    visibleBestBets.value.filter((b) => Boolean(b.is_mispriced)),
  );

  const bankerBoosterCombos = computed(() => computeBankerBoosterCombos(visibleBestBets.value));

  const activeSportsBreakdown = computed(() => {
    const spOrder = [
      'soccer',
      'tennis',
      'basketball',
      'volleyball',
      'hockey',
      'football',
      'baseball',
      'handball',
      'darts',
      'table_tennis',
    ];
    const counts: Record<string, number> = {};
    for (const b of activeBestBets.value) {
      const sc = b.sport_cat || 'soccer';
      counts[sc] = (counts[sc] || 0) + 1;
    }
    const parts: string[] = [];
    for (const sc of spOrder) {
      if (counts[sc] > 0) parts.push(`${SPORT_EMOJIS[sc] || '🏅'} ${counts[sc]}`);
    }
    for (const sc of Object.keys(counts)) {
      if (!spOrder.includes(sc) && counts[sc] > 0) {
        parts.push(`${SPORT_EMOJIS[sc] || '🏅'} ${counts[sc]}`);
      }
    }
    return parts.length ? parts.join(' · ') : 'No active picks';
  });

  const settledBets = computed(() =>
    (paperLedger.value?.bets || []).filter((t: any) => t.status === 'SETTLED'),
  );

  const liveBets = computed(() =>
    (paperLedger.value?.bets || []).filter(
      (t: any) =>
        (t.is_live || t.status === 'LIVE') &&
        t.status !== 'SETTLED' &&
        (!disabledSports.value.has(t.sport_cat) || t.tier === 'tracked_live'),
    ),
  );

  const pendingBets = computed(() =>
    (paperLedger.value?.bets || []).filter(
      (t: any) =>
        t.status === 'PENDING' &&
        !t.is_live &&
        !disabledSports.value.has(t.sport_cat),
    ),
  );

  function toggleCustomMatch(matchName: string) {
    const next = new Set(customSelectedMatches.value);
    if (next.has(matchName)) next.delete(matchName);
    else next.add(matchName);
    customSelectedMatches.value = next;
  }

  function clearCustomSelection() {
    customSelectedMatches.value = new Set();
  }

  async function syncAndSettle(rescanLive = false) {
    if (actionBusy.value) return;
    actionBusy.value = true;
    actionProgressText.value = rescanLive
      ? 'Rescanning live & upcoming fixtures across all 10 sports...'
      : 'Syncing & grading paper-betting ledger against live scores...';
    try {
      const resp = await fetch('/api/sync', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ rescan: rescanLive, min_odds: minOdds.value }),
      });
      const data = await resp.json();
      if (data.ok) {
        applySnapshot(data);
        showToast(
          rescanLive
            ? `✅ Live matches rescanned & ledger synced (${data.paper_ledger?.settled_count || 0} settled)!`
            : `✅ Ledger synced (${data.newly_settled || 0} newly settled; ${data.paper_ledger?.settled_count || 0} total settled)!`,
        );
      } else {
        showToast(`❌ Sync error: ${data.error || 'Unauthorized'}`);
      }
    } catch (err) {
      showToast(`❌ Network error: ${err}`);
    } finally {
      actionBusy.value = false;
    }
  }

  async function runFullPipeline() {
    if (actionBusy.value) return;
    actionBusy.value = true;
    actionProgressText.value = 'Running full 4-stage ingestion, quality & model pipeline...';
    try {
      const resp = await fetch('/api/pipeline', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ full_pipeline: true, min_odds: minOdds.value }),
      });
      const data = await resp.json();
      if (data.ok) {
        applySnapshot(data);
        showToast(`✅ Full pipeline complete (${data.new_ingested_count || 0} new matches ingested)!`);
      } else {
        showToast(`❌ Pipeline error: ${data.error || 'Unauthorized'}`);
      }
    } catch (err) {
      showToast(`❌ Network error: ${err}`);
    } finally {
      actionBusy.value = false;
    }
  }

  async function trackLiveMatchup(query: string) {
    const q = query.trim();
    if (!q) return null;
    actionBusy.value = true;
    actionProgressText.value = `Analyzing & pinning "${q}" to Live In-Play tracker...`;
    try {
      const resp = await fetch('/api/track-live', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ query: q }),
      });
      const data = await resp.json();
      if (data.ok) {
        applySnapshot(data);
        showToast(`📌 Pinned "${q}" to Live In-Play Tracker!`);
        return data;
      }
      showToast(`❌ Could not track "${q}": ${data.error || 'Not found'}`);
      return null;
    } catch (err) {
      showToast(`❌ Failed to track match: ${err}`);
      return null;
    } finally {
      actionBusy.value = false;
    }
  }

  async function untrackLiveMatchup(league: string, eventId: string) {
    try {
      const resp = await fetch('/api/untrack-live', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ league, event_id: eventId }),
      });
      const data = await resp.json();
      if (data.ok) {
        applySnapshot(data);
        showToast('🗑️ Removed tracked match.');
      }
    } catch (_) {}
  }

  async function toggleSportEnabled(sportKey: string) {
    const next = new Set(disabledSports.value);
    if (next.has(sportKey)) next.delete(sportKey);
    else next.add(sportKey);
    disabledSports.value = next;
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ disabled_sports: Array.from(next) }),
      });
    } catch (_) {}
  }

  return {
    loading,
    actionBusy,
    actionProgressText,
    toastMessage,
    streamStatus,
    serverTimeLocal,
    totalMatches,
    vetoedBets,
    generatedAt,
    generatedAtLocal,
    timezone,
    role,
    isAdmin,
    isPro,
    userEmail,
    firebaseAuthCfg,
    monetizationCfg,
    discordEnv,
    telegramEnv,
    settings,
    bestBets,
    paperLedger,
    recommendedDoubles,
    qualifyingPicks,
    tennisPicks,
    otherSportPicks,
    backtestRisk,
    sportFilter,
    dayFilter,
    minOdds,
    searchQuery,
    tzMode,
    disabledSports,
    customSelectedMatches,
    customApiKey,
    availableDays,
    activeBestBets,
    visibleBestBets,
    mispricedBets,
    bankerBoosterCombos,
    activeSportsBreakdown,
    settledBets,
    liveBets,
    pendingBets,
    showToast,
    getAuthHeaders,
    applySnapshot,
    fetchSnapshot,
    connectLiveStream,
    triggerSignInOut,
    toggleCustomMatch,
    clearCustomSelection,
    syncAndSettle,
    runFullPipeline,
    trackLiveMatchup,
    untrackLiveMatchup,
    toggleSportEnabled,
  };
});
