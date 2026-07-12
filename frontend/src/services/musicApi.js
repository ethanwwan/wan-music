/**
 * 音乐 API 服务
 * 通过相对路径（同源 / vite 代理）访问后端接口
 */

import { saveBlob } from '../utils/downloadHelper.js'
import { settings } from '../utils/settingsManager.js'
import { getQualityLabel } from '../utils/configManager.js'

// ==================== 数据源 ====================

const STORAGE_KEY_DATA_SOURCE = 'wan-music-selected-data-source'
const getCurrentDataSource = () => {
  try { return localStorage.getItem(STORAGE_KEY_DATA_SOURCE) || 'netease' }
  catch { return 'netease' }
}

const buildFormBody = (params) =>
  Object.entries(params)
    .filter(([, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')

const parseContentDispositionFilename = (cd, fallback) => {
  if (!cd) return fallback
  const utf8 = cd.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8) return decodeURIComponent(utf8[1])
  const ascii = cd.match(/filename="?([^";]+)"?/i)
  return ascii ? ascii[1] : fallback
}

// ==================== URL 校验 ====================

export const isHttpUrl = (url) =>
  typeof url === 'string' && /^https?:\/\/\S+$/i.test(url.trim())

// ==================== 搜索缓存 ====================

const CACHE_KEY_PREFIX = 'wan-music-search-'
const searchCache = new Map()

const loadCacheFromStorage = () => {
  try {
    const stored = localStorage.getItem(CACHE_KEY_PREFIX)
    if (stored) return new Map(JSON.parse(stored))
  } catch { /* 解析失败返回空 */ }
  return new Map()
}

const saveCacheToStorage = (cache) => {
  try { localStorage.setItem(CACHE_KEY_PREFIX, JSON.stringify(Array.from(cache.entries()))) }
  catch { /* 静默 */ }
}

searchCache.value = loadCacheFromStorage()

const isCacheValid = (entry) => {
  if (!entry?.data || !entry.timestamp) return false
  const ttlMs = (settings.cacheTTLMinutes || 24 * 60) * 60 * 1000
  if (Date.now() - entry.timestamp > ttlMs) return false
  return Array.isArray(entry.data) && entry.data.length > 0
}

const getCachedSearch = (keyword, source) => {
  if (!settings.enableCache) return null
  const key = `${source}-${keyword}`
  const entry = searchCache.value.get(key)
  return isCacheValid(entry) ? entry.data : null
}

const setCachedSearch = (keyword, source, data) => {
  if (!settings.enableCache || !data?.length) return
  searchCache.value.set(`${source}-${keyword}`, { data, timestamp: Date.now() })
  saveCacheToStorage(searchCache.value)
}

// ==================== 通用请求 ====================

// ==================== 全局 fetch 超时（避免 ERR_EMPTY_RESPONSE 永久挂起）====================
//
// 后端 Flask dev server 是单线程的，搜索时试 30+ 数据源可能 hang 几十秒。
// 前端 fetch 默认无超时 → 5s+ 没响应 → socket 被关闭 → ERR_EMPTY_RESPONSE。
//
// AbortController 5s 超时后主动 abort，浏览器看到的是清晰的 AbortError，
// 我们的 try/catch 立即捕获，UI 显示友好提示，**不**再无限挂起。
//
// 关键：AbortController abort 后，Chrome DevTools 仍会显示"Failed to fetch"日志，
// 但这是**网络层**错误（fetch 主动取消），**不是**后端错误，用户理解成本更低。
// =====================================================================================

const DEFAULT_TIMEOUT_MS = 15000  // 15s：搜索/解析的最大合理等待时间（后端某些平台响应较慢）

const fetchWithTimeout = async (url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) => {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

const get = async (url) => {
  try {
    const response = await fetchWithTimeout(url, { method: 'GET' })
    return safeJson(response)
  } catch (e) {
    if (e.name === 'AbortError') {
      return { success: false, error: '请求超时（15s），后端可能较慢', message: 'timeout' }
    }
    const hint = e.message?.includes('Failed to fetch')
      ? '后端服务未启动或连接被重置，请检查后端是否运行'
      : `网络请求失败: ${e.message || '未知错误'}`
    return { success: false, error: hint, message: e.message || 'network error' }
  }
}

const postJson = async (url, data, timeoutMs = DEFAULT_TIMEOUT_MS) => {
  try {
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }, timeoutMs)
    return safeJson(response)
  } catch (e) {
    if (e.name === 'AbortError') {
      return { success: false, error: `请求超时（${timeoutMs / 1000}s），后端可能较慢`, message: 'timeout' }
    }
    // 捕获网络错误（ERR_EMPTY_RESPONSE / ECONNREFUSED / ECONNRESET 等）
    const hint = e.message?.includes('Failed to fetch')
      ? '后端服务未启动或连接被重置，请检查后端是否运行'
      : `网络请求失败: ${e.message || '未知错误'}`
    return { success: false, error: hint, message: e.message || 'network error' }
  }
}

// 安全 JSON 解析：空响应或非 JSON 时返回明确的错误对象
const safeJson = async (response) => {
  const text = await response.text()
  if (!text) {
    return {
      success: false,
      error: `请求失败 (HTTP ${response.status})：后端无响应，请检查后端服务是否启动`,
      message: `HTTP ${response.status}`,
    }
  }
  try {
    return JSON.parse(text)
  } catch (e) {
    return {
      success: false,
      error: `请求失败 (HTTP ${response.status})：返回非 JSON 数据`,
      message: text.slice(0, 200),
    }
  }
}

// ==================== /platforms ====================

export const getPlatforms = async () => {
  const r = await get('/platforms')
  return r?.data || []
}

// ==================== /config ====================

export const getConfig = async () => {
  const r = await get('/config')
  return r?.data || null
}

// ==================== /song ====================

/**
 * 调用后端 /song 接口获取歌曲完整信息：基本信息 + 播放 URL + 歌词
 * 播放、下载、歌词展示都基于此接口的返回数据
 *
 * 设计原则（按用户意图）：
 * 1. 调用方只传 (track, quality)，不直接传 qualityMap
 * 2. 内部从 track.matchQuality 构造 qualityMap
 * 3. qualityMap 让后端做精准降级：用户请求 lossless，歌曲只有 exhigh → 直接 exhigh
 *
 * @param {object} track  - 歌曲对象（来自 search result，含 id/source/qualityMap）
 * @param {string} quality - 用户请求的音质（如 lossless/jymaster/hires）
 */
export const parseMusicInfo = async (track, quality = 'lossless') => {
  if (!track) throw new Error('歌曲对象缺失')
  const musicId = track.id
  if (!musicId) throw new Error('歌曲ID缺失，请重新搜索')

  const platform = track.source || getCurrentDataSource()
  const qualityMap = track.qualityMap || (track.matchQuality
    ? { [track.matchQuality.quality]: { br: track.matchQuality.br, size: track.matchQuality.size } }
    : null)

  const result = await postJson('/song', {
    id: String(musicId),
    level: quality,
    source: platform,
    qualityMap: qualityMap || undefined,
    line: settings.musicLine ?? 0
  })
  if (!result?.success) throw new Error(result?.error || result?.message || '获取歌曲信息失败')
  if (!result.data) throw new Error('未找到歌曲详情')

  const s = result.data
  return {
    id: String(s.id || musicId),
    name: s.name || '',
    artist: s.artist || '',
    album: s.album || '',
    cover: s.cover || '',
    duration: s.duration || 0,
    url: s.url || '',
    level: s.level || quality,
    levelName: getQualityLabel(s.level || quality),
    requestedLevel: s.requested_level || quality,
    levelFallback: !!s.level_fallback,
    fileType: s.fileType || 'mp3',
    fileExtension: `.${s.fileType || 'mp3'}`,
    source: s.source || platform,
    available: !!s.available,
    lyric: s.lyric || ''
  }
}

// ==================== /search ====================

/**
 * 把外部图片 URL 包装成后端代理 URL（避免 Chrome ORB 阻断跨域图）
 * 已经是同源（/image 或 base64）则原样返回
 */
const proxyImage = (url) => {
  if (!url || typeof url !== 'string') return url
  if (url.startsWith('/image') || url.startsWith('data:') || url.startsWith('blob:')) return url
  if (!/^https?:\/\//.test(url)) return url
  return `/image?url=${encodeURIComponent(url)}`
}

/** 把后端搜索结果标准化为前端使用的 track 列表 */
const mapSearchSong = (song) => ({
  id: song.id,
  name: song.name || '',
  artists: song.artists || song.artist_string || '',
  album: song.album || '',
  duration: song.duration || 0,
  picUrl: proxyImage(song.picUrl || song.cover || ''),
  source: song.source,
  url: song.url || '',
  lrc: song.lyric || '',
  fileExtension: song.fileType ? `.${song.fileType}` : '.mp3',
  // 付费信息：后端字段是 pay (bool) + fee (int 0/1/4/8)
  pay: song.pay || false,
  fee: song.fee || 0,
  payInfo: song.pay ? { payed: false, fee: song.fee || 0, listenUrl: null } : null,
  matchQuality: song.matchQuality || null,
  api_source: song.api_source || '',
})

/**
 * SSE 流式搜索（线路二 musicdl 专用）
 * 通过 EventSource 逐条接收搜索结果，收集完成后 resolve
 */
const streamSearch = (keyword, source, timeout = 20, quality = 'lossless') => {
  return new Promise((resolve, reject) => {
    const url = `/search/sse?keyword=${encodeURIComponent(keyword)}&source=${encodeURIComponent(source)}&timeout=${timeout}&quality=${encodeURIComponent(quality)}`
    const es = new EventSource(url)
    const items = []

    es.addEventListener('result', (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.song) {
          items.push(mapSearchSong(data.song))
        }
      } catch { /* skip malformed */ }
    })

    es.addEventListener('done', (e) => {
      es.close()
      resolve({
        success: true,
        data: items,
        type: 'song',
        detail: null,
        error: '',
        fromCache: false,
      })
    })

    es.addEventListener('error', () => {
      es.close()
      // 区分后端未启动 vs 其他错误：探 /health 判断后端状态
      const ctrl = new AbortController()
      const timer = setTimeout(() => ctrl.abort(), 5000)
      fetch('/health', { method: 'GET', signal: ctrl.signal })
        .then(r => {
          clearTimeout(timer)
          reject(new Error(r.ok
            ? '流式搜索连接失败，后端服务异常'
            : '后端服务未就绪，请先启动音乐服务后刷新页面'))
        })
        .catch(() => {
          clearTimeout(timer)
          reject(new Error('后端服务未就绪，请先启动音乐服务后刷新页面'))
        })
    })

    // 安全兜底：timeout + 5s 后如果还没 done 就强制结束
    setTimeout(() => {
      es.close()
      resolve({
        success: true,
        data: items,
        type: 'song',
        detail: null,
        error: '',
        fromCache: false,
      })
    }, (timeout + 5) * 1000)
  })
}

/**
 * 统一搜索（仅搜歌曲）
 * @param {string} keyword 关键词或 URL
 * @param {Array<string>} sources 数据源列表（仅第一个生效）
 */
export const unifiedSearch = async (keyword, sources = [getCurrentDataSource()], quality) => {
  try {
    const source = sources[0] || getCurrentDataSource()
    const cached = getCachedSearch(keyword, source)
    if (cached) return { success: true, data: cached, fromCache: true }

    // line=1 走 SSE 流式搜索（musicdl），20s 超时
    const line = settings.musicLine ?? 0
    if (line === 1) {
      const q = quality || settings.selectedQuality || 'lossless'
      const result = await streamSearch(keyword, source, 20, q)
      if (result?.data?.length) {
        setCachedSearch(keyword, source, result.data)
      }
      return result
    }

    const q = quality || settings.selectedQuality || 'lossless'
    const result = await postJson('/search', { keyword, source, limit: 50, line, quality: q }, 120000)
    if (!result?.success) {
      return { success: false, error: result?.error || result?.message || '搜索失败' }
    }

    const inner = result.data || {}
    const items = (inner.data || []).map(mapSearchSong)
    setCachedSearch(keyword, source, items)
    return {
      success: true,
      data: items,
      type: inner.type || 'song',         // 'song' | 'playlist' | 'unknown'
      detail: inner.detail || null,        // 仅 type==='playlist' 时有
      error: inner.error || '',
    }
  } catch (error) {
    return { success: false, error: error.message || '搜索失败' }
  }
}

// ==================== 批量下载（异步 + SSE） ====================

export const startBatchTask = async (items, name = 'songs', opts = {}) => {
  const resp = await fetch('/download/batch/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, name, settings: opts, line: settings.musicLine ?? 0 })
  })
  if (!resp.ok) {
    let msg = '启动批量下载失败'
    try { const err = await resp.json(); msg = err.message || msg } catch { /* 非 JSON */ }
    throw new Error(msg)
  }
  return resp.json()
}

export const getBatchList = async () => {
  const resp = await fetch('/download/batch/list')
  if (!resp.ok) throw new Error('查询任务列表失败')
  return resp.json()
}

export const cancelBatchTask = async (taskId) => {
  const resp = await fetch(`/download/batch/${taskId}`, { method: 'DELETE' })
  if (!resp.ok) {
    let msg = '取消任务失败'
    try { const err = await resp.json(); msg = err.message || msg } catch { /* 非 JSON */ }
    throw new Error(msg)
  }
  return resp.json()
}

/**
 * 订阅批量下载进度（SSE），返回 unsubscribe 函数
 */
/**
 * 订阅批量任务进度
 * 改用轮询（setInterval）替代 SSE，原因：
 *   - Flask dev server 配 threaded=True 时，Response generator 第一次 yield 后
 *     立即设 Connection: close，导致浏览器报 ERR_INCOMPLETE_CHUNKED_ENCODING
 *   - SSE 在生产环境（gunicorn/eventlet）下才好用
 *   - 轮询方案：1s 一次，每次 ~10KB 数据，简单可靠
 * 优点：
 *   - 不受 Flask dev server Connection: close 影响
 *   - vite proxy 不需要特殊配置（普通 fetch）
 *   - 后端 /download/batch/list 接口已存在，无需新写 SSE 端点
 */
export const subscribeBatchTask = (taskId, { onProgress, onComplete, onError } = {}) => {
  let closed = false
  let timer = null
  let consecutiveErrors = 0
  // 智能轮询：状态/进度有变化时高频，无变化时降频
  let lastStatus = null
  let lastCompleted = -1
  let lastFailed = -1
  let slowMode = false

  const scheduleNext = (delay) => {
    if (closed) return
    if (timer) clearTimeout(timer)   // 取消上一次的延时
    timer = setTimeout(poll, delay)
  }

  const poll = async () => {
    if (closed) return
    try {
      // 显式接收 Response，然后转 JSON（之前用 fetchWithTimeout 直接当 data 用是错的，会拿到 Response 对象）
      const response = await fetchWithTimeout(`/download/batch/progress/${taskId}`, {}, 5000)
      if (!response.ok) {
        onError?.(new Error(`HTTP ${response.status}`))
        return close()
      }
      const wrapper = await safeJson(response)
      // 后端包装层：{ success, message, data: {status, total, ...} }
      // 任务不存在时后端返回 { success: false, message: '...', code: 404 }，data 为 undefined
      if (!wrapper?.success) {
        onError?.(new Error(wrapper?.message || '任务不存在'))
        return close()
      }
      const data = wrapper?.data || wrapper
      consecutiveErrors = 0   // 成功后重置错误计数
      if (data.error) { onError?.(new Error(data.error)); return close() }
      if (['done', 'error', 'cancelled'].includes(data.status)) {
        onComplete?.(data)
        return close()
      }

      // 智能调度：状态/计数有变化 → 1s 实时；无变化 → 3s 降频
      const changed = (
        data.status !== lastStatus ||
        data.completed !== lastCompleted ||
        data.failed !== lastFailed
      )
      lastStatus = data.status
      lastCompleted = data.completed
      lastFailed = data.failed

      onProgress?.(data)
      scheduleNext(changed || !slowMode ? 1000 : 3000)
      slowMode = !slowMode   // 简单实现：第一次 fast (1s)，之后 slow (3s)，有变化时重置
    } catch (err) {
      consecutiveErrors++
      // 连续 3 次失败才报错（容忍短暂网络抖动）
      if (consecutiveErrors >= 3) {
        onError?.(err)
        return close()
      }
      // 否则静默重试（2s 后）
      scheduleNext(2000)
    }
  }

  // 立即跑一次
  poll()

  function close() {
    if (closed) return
    closed = true
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  return close
}

export const downloadBatchAsZip = async (taskId) => {
  const resp = await fetch(`/download/batch/file/${taskId}`)
  if (!resp.ok) {
    let msg = '下载 zip 失败'
    try { const err = await resp.json(); msg = err.message || msg } catch { /* 非 JSON */ }
    throw new Error(msg)
  }
  const blob = await resp.blob()
  const filename = parseContentDispositionFilename(
    resp.headers.get('Content-Disposition'),
    'songs.zip'
  )
  saveBlob(blob, filename)
  return filename
}

export default {
  isHttpUrl,
  parseMusicInfo,
  unifiedSearch,
  getPlatforms,
  startBatchTask,
  getBatchList,
  cancelBatchTask,
  subscribeBatchTask,
  downloadBatchAsZip
}
