/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const apiTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: false,
    allowedHosts: ['.monkeycode-ai.online', 'localhost', '127.0.0.1'],
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: apiTarget.replace('http', 'ws'),
        ws: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
      manualChunks: (id) => {
        if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
          return 'react-vendor';
        }
        if (id.includes('node_modules/lucide-react') || id.includes('node_modules/@xyflow/react')) {
          return 'ui-vendor';
        }
        if (id.includes('node_modules/@monaco-editor') || id.includes('node_modules/xterm')) {
          return 'editor-vendor';
        }
        if (id.includes('node_modules/react-markdown') || id.includes('node_modules/remark-gfm')) {
          return 'markdown-vendor';
        }
        return undefined;
      },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.{test,spec}.?(c|m)[jt]s?(x)'],
    exclude: ['e2e/', 'node_modules/', 'dist/'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'src/test-setup.ts',
        'e2e/',
        '**/*.config.*',
        'scripts/',
        'src/vite-env.d.ts',
      ],
      thresholds: {
        lines: 60,
        functions: 59,
        statements: 60,
        branches: 49,
      },
    },
  },
})
