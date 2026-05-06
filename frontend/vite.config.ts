import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig, loadEnv, type Plugin } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

const envDir = path.resolve(__dirname, '..');

const escapeJsString = (value: string): string => value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');

const buildRuntimeEnvSource = (env: Record<string, string>): string => {
  const entries = Object.entries(env)
    .filter(([key]) => key.startsWith('VITE_'))
    .sort(([a], [b]) => a.localeCompare(b));

  const body = entries
    .map(([key, value]) => `  ${JSON.stringify(key)}: "${escapeJsString(value)}"`)
    .join(',\n');

  return `window.__TRIPLY_ENV__ = {\n${body}\n};\n`;
};

const runtimeEnvPlugin = (mode: string): Plugin => {
  const modeEnv = loadEnv(mode, envDir, 'VITE_');
  const runtimeEnv = { ...modeEnv };
  for (const [key, value] of Object.entries(process.env)) {
    if (key.startsWith('VITE_') && value !== undefined) {
      runtimeEnv[key] = value;
    }
  }

  return {
    name: 'triply-runtime-env',
    configureServer(server) {
      server.middlewares.use('/env.js', (_req, res) => {
        res.setHeader('Content-Type', 'application/javascript');
        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
        res.end(buildRuntimeEnvSource(runtimeEnv));
      });
    },
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'env.js',
        source: buildRuntimeEnvSource(runtimeEnv),
      });
    },
  };
};

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const isDev = command === 'serve';

  return {
    envDir,
    plugins: [
      react(),
      runtimeEnvPlugin(mode),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'apple-touch-icon.png'],
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
          globIgnores: ['**/env.js'],
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
        '/api/profile': {
          target: isDev ? 'http://localhost:8002' : 'http://trip-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/destinations': {
          target: isDev ? 'http://localhost:8003' : 'http://data-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/v1/events': {
          target: isDev ? 'http://localhost:8005' : 'http://analytics-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/v1/feedback': {
          target: isDev ? 'http://localhost:8005' : 'http://analytics-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/v1/users': {
          target: isDev ? 'http://localhost:8005' : 'http://analytics-service:8000',
          changeOrigin: true,
          secure: false,
        },
        '/api/v1': {
          target: isDev ? 'http://localhost:8004' : 'http://ml-service:8000',
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
