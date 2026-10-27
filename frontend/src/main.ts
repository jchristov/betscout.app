import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { setupIconifyCollections } from './utils/iconifySetup';
import './style.css';

setupIconifyCollections();

if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
