import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const config = loadEnv(mode, process.cwd(), 'VITE_');
  const token = config.VITE_GRIDICS_PUBLISHABLE_TOKEN ?? '';
  if (token && !/^gpk_(test|live)_[A-Za-z0-9_-]+$/.test(token)) {
    throw new Error('Only a scoped gpk_test_... or gpk_live_... publishable token may enter a browser build.');
  }
  if (config.VITE_ZONING_PROXY_URL && !/^https?:\/\//.test(config.VITE_ZONING_PROXY_URL)) {
    throw new Error('VITE_ZONING_PROXY_URL must be an absolute HTTP(S) URL.');
  }
  return { resolve: { dedupe: ['react', 'react-dom'] }, test: { environment: 'jsdom' } };
});
