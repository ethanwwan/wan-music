import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'

// ============================================================
// 从根目录 config.json 加载统一配置
// ============================================================
const rootDir = path.resolve(__dirname, '..')
const configPath = path.join(rootDir, 'config.json')
let appConfig = {}

if (fs.existsSync(configPath)) {
  try {
    const raw = JSON.parse(fs.readFileSync(configPath, 'utf-8'))
    // 去除 JSON 中带 _comment 的字段
    const stripComments = (obj) => {
      if (typeof obj !== 'object' || obj === null) return obj
      if (Array.isArray(obj)) return obj.map(stripComments)
      const result = {}
      for (const [k, v] of Object.entries(obj)) {
        if (k.startsWith('_')) continue
        result[k] = stripComments(v)
      }
      return result
    }
    appConfig = stripComments(raw)
  } catch (e) {
    console.warn(`[vite.config] 读取 config.json 失败: ${e.message}，将使用默认值`)
  }
}

const frontendCfg = appConfig.frontend || {}
const backendCfg = appConfig.backend || {}

// ============================================================
// Vite 配置
// ============================================================
export default defineConfig(({ mode }) => {
  // mode 可能是 'dev' / 'prod'（自定义）或 'development' / 'production'（vite 默认）
  const isProd = mode === 'prod' || mode === 'production'

  // 端口：config.json > 默认
  const defaultPort = isProd ? 6175 : 5175
  const vitePort = (isProd ? frontendCfg.prodPort : frontendCfg.devPort) || defaultPort

  // 后端代理：config.json > 默认
  const backendPort = isProd ? backendCfg.prodBackendPort : backendCfg.devBackendPort
  const proxyTarget = frontendCfg.apiProxyTarget
    || `http://localhost:${backendPort || 5005}`

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
      port: vitePort,
      proxy: {
        '/search': { target: proxyTarget, changeOrigin: true },
        '/song': { target: proxyTarget, changeOrigin: true },
        '/playlist': { target: proxyTarget, changeOrigin: true },
        '/download': { target: proxyTarget, changeOrigin: true },
        '/api': { target: proxyTarget, changeOrigin: true },
        '/health': { target: proxyTarget, changeOrigin: true }
      }
    },
    build: {
      // 把环境变量注入到前端（必须以 VITE_ 或 BACKEND_ 开头才能暴露给客户端）
      // VITE_API_BASE 在生产环境用作 API 基础路径（默认空 = 同源）
      envPrefix: ['VITE_', 'BACKEND_']
    }
  }
})
