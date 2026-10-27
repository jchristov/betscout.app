import { createRouter, createWebHistory } from 'vue-router';
import LandingView from '../views/LandingView.vue';
import DashboardView from '../views/DashboardView.vue';
import LogoShowcaseView from '../views/LogoShowcaseView.vue';

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
      path: '/logos',
      name: 'logos',
      component: LogoShowcaseView,
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
