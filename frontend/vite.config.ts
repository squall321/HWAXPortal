import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Dev proxy makes the SPA same-origin with the API (localhost:5283 -> :8723),
// so httpOnly session cookies and the SAML redirect chain behave like prod.
// Ports are deliberately uncommon (8723 / 5283) to avoid collisions on shared dev boxes.
const API = 'http://localhost:8723';

export default defineConfig({
  plugins: [react()],
  // Force a single React instance — guards against the dev optimizer pre-bundling
  // two copies (causes "Invalid hook call / more than one copy of React").
  resolve: { dedupe: ['react', 'react-dom'] },
  optimizeDeps: { include: ['react', 'react-dom', 'react-router-dom'] },
  server: {
    port: 5283,
    proxy: {
      '/api': { target: API, changeOrigin: true },
      '/auth': { target: API, changeOrigin: true },
      '/systems': { target: API, changeOrigin: true },
      '/mail': { target: API, changeOrigin: true },
      '/health': { target: API, changeOrigin: true },
      '/.well-known': { target: API, changeOrigin: true },
    },
  },
});
