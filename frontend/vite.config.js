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

  // 代理路径列表（server 和 preview 复用）
  const proxyPaths = ['/search', '/song', '/playlist', '/download', '/image', '/api', '/health', '/platforms']
  const buildProxy = () => {
    const opts = {
      target: proxyTarget,
      changeOrigin: true,
      // 关键：后端没启动时 ECONNREFUSED 静默处理
      // retry 必须 = 0：每次 retry 都会 close socket 一次，导致浏览器
      // 显示 ERR_EMPTY_RESPONSE（Chrome DevTools 网络层错误，JS 无法拦截）
      // 让前端 silentFetch 自己做 retry（应用层），vite 不再 retry
      retry: 0,                  // 关键：不重试，避免重复 ERR_EMPTY_RESPONSE
      timeout: 3000,
      proxyTimeout: 3000,
      // ECONNREFUSED 是后端未启动导致，频繁刷屏会干扰开发
      // 用 configure 钩子自定义错误处理
      configure: (proxy) => {
        proxy.on('error', (err, req, res) => {
          // ECONNREFUSED / ECONNRESET 不打 vite 的错误日志
          if (['ECONNREFUSED', 'ECONNRESET', 'ETIMEDOUT'].includes(err.code)) {
            // 给前端一个 503 + JSON，前端 store 自己决定如何 retry
            if (res && !res.headersSent) {
              res.statusCode = 503
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({
                code: 503,
                message: `后端服务未就绪 (${proxyTarget})，请稍后重试`,
                retry_after: 2,
              }))
            }
          } else {
            // 其他错误才打日志
            console.error(`[vite proxy] ${err.code} ${req.url} →`, err.message)
          }
        })
      },
    }
    return Object.fromEntries(proxyPaths.map(p => [p, opts]))
  }

  // 静默 vite 5 的 http proxy error 日志（v1.1.3 configure hook 之后 vite 还会打）
  // vite 5 源码 proxy.ts → proxy.on("error") → config.logger.error
  // 这条 console.error 在 configure 之后才注册，无法在 configure 里覆盖
  // 唯一办法：拦截 console.error，过滤 http proxy error + ECONNREFUSED/ECONNRESET/ETIMEDOUT
  const installConsoleErrorFilter = () => {
    const originalError = console.error
    console.error = function (...args) {
      const msg = args.map(a => (typeof a === 'string' ? a : (a && a.message) || String(a))).join(' ')
      if (msg.includes('http proxy error') &&
          /ECONNREFUSED|ECONNRESET|ETIMEDOUT/.test(msg)) {
        // 后端未就绪，silent 掉
        return
      }
      return originalError.apply(console, args)
    }
  }

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
      proxy: buildProxy(),
      // dev 启动时静默 vite 5 的 http proxy error
      configureServer(server) {
        installConsoleErrorFilter()
      }
    },
    preview: {
      host: '0.0.0.0',
      port: vitePort,
      proxy: buildProxy(),
      configurePreviewServer(server) {
        installConsoleErrorFilter()
      }
    },
    build: {
      // 把环境变量注入到前端（必须以 VITE_ 或 BACKEND_ 开头才能暴露给客户端）
      // VITE_API_BASE 在生产环境用作 API 基础路径（默认空 = 同源）
      envPrefix: ['VITE_', 'BACKEND_']
    }
  }
})
