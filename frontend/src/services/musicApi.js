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

const get = async (url) => {
  const response = await fetch(url, { method: 'GET' })
  return safeJson(response)
}

const postJson = async (url, data) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return safeJson(response)
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
 * 2. 内部从 track.qualityMap 提取（该字段在 search result 中已存在）
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
  const qualityMap = track.qualityMap || null

  const result = await postJson('/song', {
    id: String(musicId),
    level: quality,
    source: platform,
    qualityMap: qualityMap || undefined
  })
  if (!result?.success) throw new Error(result?.message || '获取歌曲信息失败')
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
  qualityMap: song.qualityMap || null,
  bestQuality: song.bestQuality || '',
  api_source: song.api_source || '',
})

/**
 * 统一搜索（仅搜歌曲）
 * @param {string} keyword 关键词或 URL
 * @param {Array<string>} sources 数据源列表（仅第一个生效）
 */
export const unifiedSearch = async (keyword, sources = [getCurrentDataSource()]) => {
  try {
    const source = sources[0] || getCurrentDataSource()
    const cached = getCachedSearch(keyword, source)
    if (cached) return { success: true, data: cached, fromCache: true }

    const result = await postJson('/search', { keyword, source, limit: 50 })
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
    body: JSON.stringify({ items, name, settings: opts })
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
export const subscribeBatchTask = (taskId, { onProgress, onComplete, onError } = {}) => {
  const es = new EventSource(`/download/batch/progress/${taskId}`)
  let closed = false

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.error) { onError?.(new Error(data.error)); return close() }
      if (['done', 'error', 'cancelled'].includes(data.status)) {
        onComplete?.(data)
        return close()
      }
      onProgress?.(data)
    } catch (err) {
      onError?.(err)
      close()
    }
  }

  es.onerror = () => {
    if (es.readyState === EventSource.CLOSED) {
      onError?.(new Error('SSE 连接已断开'))
      close()
    }
  }

  function close() {
    if (closed) return
    closed = true
    es.close()
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
