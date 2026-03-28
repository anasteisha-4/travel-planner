import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

// https://vitejs.dev/config/
export default defineConfig(({ command }) => {
  const isDev = command === 'serve';

  return {
    envDir: path.resolve(__dirname, '..'),
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'apple-touch-icon.png'],
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
          runtimeCaching: [
            {
              urlPattern: /^\/api\/.*$/i,
              handler: 'NetworkFirst',
              method: 'GET',
              options: {
                cacheName: 'api-cache',
                cacheableResponse: {
                  statuses: [0, 200],
                },
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 60 * 24 * 7, // 7 days
                },
                networkTimeoutSeconds: 5,
              },
            },
            {
              urlPattern: /^\/api\/.*$/i,
              handler: 'NetworkOnly',
              method: 'POST',
            },
            {
              urlPattern: /^\/api\/.*$/i,
              handler: 'NetworkOnly',
              method: 'PUT',
            },
            {
              urlPattern: /^\/api\/.*$/i,
              handler: 'NetworkOnly',
              method: 'DELETE',
            },
          ],
        },
        manifest: {
          name: 'Triply',
          short_name: 'Triply',
          description: 'Triply — персональный планировщик поездок',
          theme_color: '#ffffff',
          background_color: '#ffffff',
          display: 'standalone',
          display_override: ['standalone', 'minimal-ui'],
          orientation: 'any',
          start_url: '/',
          scope: '/',
          id: '/',
          handle_links: 'preferred',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: isDev ? 5173 : 80,
      host: true,
      proxy: {
        '/api/trips': {
          target: isDev ? 'http://localhost:8002' : 'http://trip-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/expenses': {
          target: isDev ? 'http://localhost:8002' : 'http://trip-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/places': {
          target: isDev ? 'http://localhost:8002' : 'http://trip-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/exchange-rates': {
          target: isDev ? 'http://localhost:8002' : 'http://trip-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api': {
          target: isDev ? 'http://localhost:8001' : 'http://auth-service:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    preview: {
      port: 80,
      host: true,
    },
  };
});
