import { createRouter, createWebHistory } from 'vue-router';
import LandingView from '../views/LandingView.vue';
import DashboardView from '../views/DashboardView.vue';
import DocsView from '../views/DocsView.vue';
import MatchCenterView from '../views/MatchCenterView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingView,
    },
    {
      path: '/landing',
      redirect: '/',
    },
    {
      path: '/pricing',
      redirect: '/#pricing',
    },
    {
      path: '/app',
      name: 'dashboard',
      component: DashboardView,
    },
    {
      path: '/docs',
      name: 'docs',
      component: DocsView,
    },
    {
      path: '/docs/notification-cards',
      name: 'docs-cards',
      component: DocsView,
    },
    {
      path: '/docs/notification-cards.html',
      name: 'docs-cards-html',
      component: DocsView,
    },
    {
      path: '/cards',
      name: 'cards-short',
      component: DocsView,
    },
    {
      path: '/match/:id',
      name: 'match-center',
      component: MatchCenterView,
    },
  ],
  scrollBehavior(to) {
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' };
    }
    return { top: 0 };
  },
});

export default router;
