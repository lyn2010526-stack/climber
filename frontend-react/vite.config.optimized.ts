import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { ViteImageOptimizer } from 'vite-plugin-image-optimizer'
import { gzipSize } from 'vite-plugin-gzip'
import { visualizer } from 'rollup-plugin-visualizer'

const apiTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(), 
    tailwindcss(),
    // Enable gzip and brotli compression
    ViteImageOptimizer({
      png: { quality: 80 },
      jpeg: { quality: 80, progressive: true },
      webp: { quality: 75 },
      avif: { quality: 75 },
    }),
    gzipSize(),
    // Analyze bundle size
    visualizer({
      filename: 'dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
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
    chunkSizeWarningLimit: 1000,
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Split vendor chunks for better caching
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'react-vendor';
          }
          if (id.includes('node_modules/lucide-react') || id.includes('node_modules/@xyflow')) {
            return 'ui-vendor';
          }
          if (id.includes('node_modules/i18next')) {
            return 'i18n-vendor';
          }
          // Split large dependencies
          if (id.length > 1000 && id.includes('node_modules')) {
            return undefined; // Let Rollup decide
          }
        },
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]',
      },
    },
    // Generate manifest for CDN caching
    manifest: true,
    // Optimize for production
    cssCodeSplit: true,
    emptyOutDir: true,
    reportCompressedSize: true,
  },
  // CSS optimization
  css: {
    module: {
      localsConvention: 'camelCaseOnly',
    },
  },
  // Image preprocessing
  assetsInclude: ['**/*.svg', '**/*.png', '**/*.jpg', '**/*.webp'],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})
