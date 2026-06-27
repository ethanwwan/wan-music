/**
 * 音乐 API 服务
 * 通过相对路径（同源 / vite 代理）访问后端接口，
 * 由 SearchContainer / SearchResult / SongList 等组件直接调用。
 */

import { saveBlob } from '../utils/downloadHelper.js'
import { settings } from '../utils/settingsManager.js'
import { getQualityLabel } from '../config/qualityLevels.js'

// ==================== 数据源 ====================

const STORAGE_KEY_DATA_SOURCE = 'wan-music-selected-data-source'

// ==================== 工具函数 ====================

const getCurrentDataSource = () => {
  try { return localStorage.getItem(STORAGE_KEY_DATA_SOURCE) || 'netease' }
  catch { return 'netease' }
}

const buildFormBody = (params) =>
  Object.entries(params)
    .filter(([, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')

/** 从 Content-Disposition 提取文件名（兼容 RFC 5987 UTF-8 与 ASCII fallback） */
const parseContentDispositionFilename = (cd, fallback) => {
  if (!cd) return fallback
  const utf8 = cd.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8) return decodeURIComponent(utf8[1])
  const ascii = cd.match(/filename="?([^";]+)"?/i)
  return ascii ? ascii[1] : fallback
}

// ==================== URL 校验 ====================

/** 仅做"是不是 http(s) URL"的轻量校验，平台/类型由后端识别 */
export const isHttpUrl = (url) =>
  typeof url === 'string' && /^https?:\/\/\S+$/i.test(url.trim())

// ==================== 搜索缓存 ====================

const CACHE_KEY_PREFIX = 'wan-music-search-'
const searchCache = { music: new Map(), playlist: new Map(), album: new Map(), unified: new Map() }

const loadCacheFromStorage = (type) => {
  try {
    const stored = localStorage.getItem(CACHE_KEY_PREFIX + type)
    if (stored) return new Map(JSON.parse(stored))
  } catch { /* localStorage 解析失败时返回空缓存 */ }
  return new Map()
}

const saveCacheToStorage = (type, cache) => {
  try { localStorage.setItem(CACHE_KEY_PREFIX + type, JSON.stringify(Array.from(cache.entries()))) }
  catch { /* localStorage 写入失败时静默 */ }
}

for (const k of Object.keys(searchCache)) searchCache[k] = loadCacheFromStorage(k)

const isCacheValid = (entry) => {
  if (!entry?.data || !entry.timestamp) return false
  // 校验 TTL（settings.cacheTTLMinutes 单位：分钟）
  const ttlMs = (settings.cacheTTLMinutes || 24 * 60) * 60 * 1000
  if (Date.now() - entry.timestamp > ttlMs) return false
  const { songs = [], playlists = [], albums = [], artists = [] } = entry.data
  return songs.length || playlists.length || albums.length || artists.length
}

const getCachedSearchResult = (type, keyword) => {
  if (!settings.enableCache) return null
  const cache = searchCache[type]
  const cached = cache?.get(keyword)
  if (isCacheValid(cached)) return cached.data
  // 空缓存/过期缓存视为无效，避免下次再走无意义判断
  if (cached) { cache.delete(keyword); saveCacheToStorage(type, cache) }
  return null
}

const setCachedSearchResult = (type, keyword, data) => {
  if (!settings.enableCache) return
  const cache = searchCache[type]
  if (!cache) return
  cache.set(keyword, { data, timestamp: Date.now() })
  saveCacheToStorage(type, cache)
}

// ==================== 通用请求 ====================

/** GET 请求 */
const get = async (url) => {
  const response = await fetch(url, { method: 'GET' })
  return response.json()
}

/** POST application/x-www-form-urlencoded */
const postForm = async (url, params) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: buildFormBody(params)
  })
  return response.json()
}

/** POST application/json */
const postJson = async (url, data) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return response.json()
}

// ==================== /platforms 平台列表 ====================

/** GET /platforms（从后端拉取支持的平台元数据，避免前端硬编码） */
export const getPlatforms = async () => {
  const r = await get('/platforms')
  return r?.data || []
}

// ==================== /song 单曲接口 ====================

/**
 * 调用后端 /song 接口获取歌曲完整信息：基本信息 + 播放/下载地址 + 歌词
 * 播放、下载、歌词展示都基于此接口的返回数据，无需额外请求
 * @param {string} musicId 歌曲 ID
 * @param {string} quality 音质
 * @param {string} source 平台（不传时使用当前数据源）
 */
export const parseMusicInfo = async (musicId, quality = 'lossless', source = '') => {
  if (!musicId) throw new Error('歌曲ID缺失，请重新搜索')

  try {
    const platform = source || getCurrentDataSource()
    const result = await postJson('/song', {
      id: String(musicId),
      level: quality,
      source: platform
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
      fileType: s.fileType || 'mp3',
      fileExtension: `.${s.fileType || 'mp3'}`,
      source: s.source || platform,
      available: !!s.available,
      lyric: s.lyric || ''
    }
  } catch (error) {
    throw new Error(error?.message || String(error) || '未知错误')
  }
}

// ==================== /playlist 歌单 ====================

/** 把后端歌单数据规整为前端使用的 track 列表 */
const normalizePlaylistTracks = (tracks, defaultSource) =>
  (tracks || []).map(track => ({
    id: track.id,
    name: track.name,
    artists: track.artists || track.artist_string || '',
    album: track.album || '',
    picUrl: track.picUrl || track.cover || '',
    duration: track.duration || 0,
    source: track.source || defaultSource,
    payInfo: track.payInfo || null,
    qualityMap: track.qualityMap || null,
    bestQuality: track.bestQuality || ''
  }))

/**
 * 统一歌单接口
 * - 传 url: 后端解析 URL 拿 id
 * - 传 id:  直接请求对应歌单
 * 后端可能返回带 __error__ 标记的"假数据"（隐私歌单、不存在等），需要识别
 */
const fetchPlaylist = async (params) => {
  try {
    const result = await postForm('/playlist', { limit: 100, ...params })
    if (!result.success || !result.data) {
      return { success: false, error: result.message || '获取歌单信息失败' }
    }
    const playlist = result.data.playlist || result.data
    if (playlist?.__error__) {
      return {
        success: false,
        error: playlist.__message__ || '该歌单无法获取',
        errorType: playlist.__error__  // privacy | api_error | empty
      }
    }
    return { success: true, playlist }
  } catch (error) {
    return { success: false, error: `网络请求失败: ${error.message || '未知错误'}` }
  }
}

/** 通过歌单 ID 获取详情（SearchResult.vue 点击歌单卡片使用） */
export const getPlaylistById = async (playlistId, source = '') => {
  const platform = source || getCurrentDataSource()
  const r = await fetchPlaylist({ id: playlistId, source: platform })
  if (!r.success) return r

  const { id, name, cover, coverImgUrl, description, play_count, playCount, tracks, source: src } = r.playlist
  return {
    success: true,
    data: {
      id,
      name,
      coverImgUrl: cover || coverImgUrl || '',
      description: description || '',
      playCount: play_count || playCount || 0,
      trackCount: tracks?.length || 0,
      source: src || platform,
      tracks: normalizePlaylistTracks(tracks, src || platform)
    }
  }
}

// ==================== /search 统一搜索 ====================

/** 把后端搜索结果中的单曲/歌单条目映射为前端统一结构 */
const mapSearchSong = (song) => ({
  id: song.id,
  name: song.name,
  artists: song.artists || song.artist_string || '',
  album: song.album || '',
  duration: song.duration || 0,
  picUrl: song.picUrl || '',
  source: song.source,
  url: song.url || '',
  lrc: song.lyric || '',
  fileExtension: song.fileType ? `.${song.fileType}` : '.mp3',
  _type: song._type || 'song',
  payInfo: song.payInfo || null,
  qualityMap: song.qualityMap || null,
  bestQuality: song.bestQuality || '',
})

const mapSearchPlaylist = (playlist) => ({
  id: playlist.id,
  name: playlist.name,
  coverImgUrl: playlist.cover || playlist.coverImgUrl || '',
  description: playlist.description || '',
  playCount: playlist.play_count || playlist.playCount || 0,
  trackCount: playlist.track_count || playlist.trackCount || 0,
  source: playlist.source || 'netease',
  _type: playlist._type || 'playlist'
})

/**
 * 统一搜索接口
 * @param {string} keyword 搜索内容（关键词或 URL）
 * @param {number} type 0=全部 / 1=歌曲 / 2=歌单（仅 keyword 不是 URL 时生效）
 * @param {Array<string>} sources 数据源列表
 * @param {string} quality 音质
 * 返回：{ type, songs, playlists, warnings }，warnings 用于前端友好提示
 * 歌曲 limit 50，歌单 limit 20（通过两次请求实现，无需后端支持多种 limit）
 */
const SONG_SEARCH_LIMIT = 50
const PLAYLIST_SEARCH_LIMIT = 20

const _doSearch = async (keyword, type, sources, quality, limit) => {
  const requestData = { keyword, type, limit, quality }
  if (sources.length === 1) requestData.source = sources[0]
  return postJson('/search', requestData)
}

export const unifiedSearch = async (keyword, type = 0, sources = ['netease'], quality = 'lossless') => {
  try {
    const cacheKey = `${type}-${keyword}-${sources.join(',')}-${quality}`
    const cached = getCachedSearchResult('unified', cacheKey)
    if (cached) return { success: true, data: cached, fromCache: true }

    let respType = type
    let items = []
    let warnings = []

    if (type === 0) {
      // 全部：分两次请求（歌曲 50 / 歌单 20）
      const [songResult, playlistResult] = await Promise.all([
        _doSearch(keyword, 1, sources, quality, SONG_SEARCH_LIMIT),
        _doSearch(keyword, 2, sources, quality, PLAYLIST_SEARCH_LIMIT),
      ])
      if (!songResult.success || !playlistResult.success) {
        return { success: false, error: (songResult.message || playlistResult.message || '搜索失败') }
      }
      const songData = songResult.data?.data || []
      const playlistData = playlistResult.data?.data || []
      items = [...songData, ...playlistData]
      warnings = [
        ...(songResult.data?.warnings || []),
        ...(playlistResult.data?.warnings || []),
      ]
      respType = 0
    } else {
      // 单类型：单次请求
      const limit = type === 2 ? PLAYLIST_SEARCH_LIMIT : SONG_SEARCH_LIMIT
      const result = await _doSearch(keyword, type, sources, quality, limit)
      if (!result.success || !result.data) {
        return { success: false, error: result.message || '搜索失败' }
      }
      items = result.data.data || []
      warnings = result.data.warnings || []
    }

    const songs = []
    const playlists = []
    for (const item of items) {
      if (item._type === 'playlist') playlists.push(mapSearchPlaylist(item))
      else songs.push(mapSearchSong(item))
    }

    const searchData = { type: respType, songs, playlists, warnings: warnings || [] }
    setCachedSearchResult('unified', cacheKey, searchData)
    return { success: true, data: searchData }
  } catch (error) {
    return { success: false, error: error.message || '搜索失败' }
  }
}

// ==================== 批量下载（异步 + SSE） ====================

/**
 * 启动批量下载任务（异步，立即返回 task_id）
 * 后端会启动后台线程执行下载，前端通过 SSE 订阅进度
 */
export const startBatchTask = async (items, name = 'playlist', settings = {}) => {
  const resp = await fetch('/download/batch/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, name, settings })
  })
  if (!resp.ok) {
    let msg = '启动批量下载失败'
    try { const err = await resp.json(); msg = err.message || msg } catch { /* 非 JSON 错误响应 */ }
    throw new Error(msg)
  }
  return resp.json()
}

/** 列出所有批量下载任务（启动时同步用） */
export const getBatchList = async () => {
  const resp = await fetch('/download/batch/list')
  if (!resp.ok) throw new Error('查询任务列表失败')
  return resp.json()
}

/** 取消/删除批量下载任务（运行中标记 cancelled 并清理，已完成清理 zip） */
export const cancelBatchTask = async (taskId) => {
  const resp = await fetch(`/download/batch/${taskId}`, { method: 'DELETE' })
  if (!resp.ok) {
    let msg = '取消任务失败'
    try { const err = await resp.json(); msg = err.message || msg } catch { /* 非 JSON 错误响应 */ }
    throw new Error(msg)
  }
  return resp.json()
}

/**
 * 订阅批量下载进度（SSE），返回 unsubscribe 函数
 * - onProgress(data): 进行中
 * - onComplete(data): status 是 done/error/cancelled
 * - onError(err): SSE 断流等异常
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
    // SSE 错误不一定是真错（可能正在重连），但已断流则报错
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

/** 下载已完成任务的 zip 包（前端触发浏览器下载） */
export const downloadBatchAsZip = async (taskId) => {
  const resp = await fetch(`/download/batch/file/${taskId}`)
  if (!resp.ok) {
    let msg = '下载 zip 失败'
    try { const err = await resp.json(); msg = err.message || msg } catch { /* 非 JSON 错误响应 */ }
    throw new Error(msg)
  }
  const blob = await resp.blob()
  const filename = parseContentDispositionFilename(
    resp.headers.get('Content-Disposition'),
    'playlist.zip'
  )
  saveBlob(blob, filename)
  return filename
}

export default {
  isHttpUrl,
  parseMusicInfo,
  getPlaylistById,
  unifiedSearch,
  getPlatforms,
  startBatchTask,
  getBatchList,
  cancelBatchTask,
  subscribeBatchTask,
  downloadBatchAsZip
}
