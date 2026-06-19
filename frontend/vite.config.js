import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  // 加载 .env.[mode] 文件（如 .env.development / .env.production）
  const env = loadEnv(mode, process.cwd(), '')

  const vitePort = parseInt(env.VITE_PORT) || 5175
  const proxyTarget = env.VITE_API_PROXY_TARGET || `http://localhost:${env.BACKEND_PORT || 5002}`

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    server: {
      host: '0.0.0.0',
      port: vitePort,
      proxy: {
        // 后端实际提供的 API 端点
        '/search': { target: proxyTarget, changeOrigin: true },
        '/song': { target: proxyTarget, changeOrigin: true },
        '/playlist': { target: proxyTarget, changeOrigin: true },
        '/download': { target: proxyTarget, changeOrigin: true },
        '/api': { target: proxyTarget, changeOrigin: true },
        '/health': { target: proxyTarget, changeOrigin: true }
      }
    },
    preview: {
      host: '0.0.0.0',
      port: vitePort
    },
    build: {
      // 把环境变量注入到前端（必须以 VITE_ 开头才能暴露给客户端）
      // VITE_API_BASE 在生产环境用作 API 基础路径（默认空 = 同源）
      envPrefix: ['VITE_', 'BACKEND_']
    }
  }
})
