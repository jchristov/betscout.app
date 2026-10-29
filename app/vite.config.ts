/// <reference types="vitest" />
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';
import { execSync } from 'child_process';
import { readFileSync } from 'fs';

const pkgJson = JSON.parse(readFileSync(resolve(__dirname, 'package.json'), 'utf-8')) as { version?: string };
const appVersion = process.env.VITE_APP_VERSION || pkgJson.version || '0.5.0';
let commitHash = process.env.VITE_COMMIT_HASH || '';
if (!commitHash) {
  try {
    commitHash = execSync('git rev-parse --short HEAD', { cwd: __dirname }).toString().trim();
  } catch {
    commitHash = 'dev';
  }
}

export default defineConfig({
  plugins: [vue()],
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __COMMIT_HASH__: JSON.stringify(commitHash),
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
      '/betscout-logo.svg': {
        target: 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
