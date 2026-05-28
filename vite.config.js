import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/wyapi2': {
        target: 'https://wyapi-2.toubiec.cn',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/wyapi2/, '')
      },
      '/wyapi': {
        target: 'https://wyapi-1.toubiec.cn',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/wyapi/, '')
      },
      '/netease': {
        target: 'https://netease-cloud-music-api-psi-six-56.vercel.app',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/netease/, '')
      }
    }
  }
})
