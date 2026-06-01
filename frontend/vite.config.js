import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Proxy API requests to the FastAPI backend
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  // Enable environment variable loading from .env files
  envPrefix: 'VITE_'
});
