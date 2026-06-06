import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5175,
    proxy: {
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/eapi': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/weapi': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/Song_V1': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/song': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/search': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/cloudsearch': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/playlist': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/album': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/artist': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/download': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/stream': {
        target: 'http://localhost:5002',
        changeOrigin: true
      }
    }
  }
})
