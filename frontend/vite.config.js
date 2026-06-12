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
      // 后端API代理配置
      '/search': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/song': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/playlist': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:5002',
        changeOrigin: true
      }
    }
  }
})