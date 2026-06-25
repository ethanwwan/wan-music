/**
 * 音乐API服务
 * 通过后端API实现多平台音乐搜索和解析
 */

import { saveBlob, sanitizeFilename } from '../utils/downloadHelper.js'
import { settings } from '../utils/settingsManager.js'
import { getQualityLabel } from '../config/qualityLevels.js'

// ==================== 数据源 ====================

/** 当前选中的数据源在 localStorage 中的 key */
const STORAGE_KEY_DATA_SOURCE = 'wan-music-selected-data-source'

/** 搜索缓存的 localStorage key 前缀 */
const CACHE_KEY_PREFIX = 'wan-music-search-'

/** URL 模式正则（用于在 UI 中同步校验用户输入的链接） */
const URL_PATTERNS = {
  netease: {
    music: [
      /https?:\/\/music\.163\.com\/song\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/song\?id=(\d+)/
    ],
    playlist: [
      /https?:\/\/music\.163\.com\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\/(\d+)/,
      /https?:\/\/music\.163\.com\/#\/playlist\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/discover\/toplist\?id=(\d+)/
    ]
  },
  qq: {
    music: [
      /https?:\/\/y\.qq\.com\/n\/ryqq\/songDetail\/([a-zA-Z0-9]+)/,
      /https?:\/\/i\.y\.qq\.com\/n2\/m\/share\/details\/song\.html\?.*songid=(\d+)/,
      /https?:\/\/c\.y\.qq\.com\/base\/cgi-bin\/u\.cgi\?.*url=.*songDetail\/([a-zA-Z0-9]+)/
    ],
    playlist: [
      /https?:\/\/y\.qq\.com\/n\/ryqq\/playlist\/(\d+)/,
      /https?:\/\/i\.y\.qq\.com\/n2\/m\/share\/details\/taoge\.html\?.*id=(\d+)/
    ]
  },
  kugou: {
    music: [
      /https?:\/\/www\.kugou\.com\/song\/#hash=([a-zA-Z0-9]+)/,
      /https?:\/\/www\.kugou\.com\/mixsong\/([a-zA-Z0-9]+)/,
      /https?:\/\/m\.kugou\.com\/app\/i\/getSongInfo\.php\?.*hash=([a-zA-Z0-9]+)/
    ],
    playlist: [
      /https?:\/\/www\.kugou\.com\/yy\/special\/single\/(\d+)\.html/,
      /https?:\/\/m\.kugou\.com\/plist\/list\/index\.php\?.*id=(\d+)/
    ]
  },
  bodian: {
    music: [
      /https?:\/\/bodian\.kuwo\.cn\/song\/([a-zA-Z0-9]+)/,
      /https?:\/\/www\.bodianmusic\.com\/song\/([a-zA-Z0-9]+)/
    ],
    playlist: [
      /https?:\/\/bodian\.kuwo\.cn\/playlist\/([a-zA-Z0-9]+)/,
      /https?:\/\/www\.bodianmusic\.com\/playlist\/([a-zA-Z0-9]+)/
    ]
  }
}

/** 平台标识关键字（用于根据 URL 判断平台） */
const PLATFORM_KEYWORDS = [
  { platform: 'qq', keywords: ['y.qq.com', 'qq.com'] },
  { platform: 'kugou', keywords: ['kugou.com'] },
  { platform: 'bodian', keywords: ['bodian'] },
  { platform: 'netease', keywords: ['music.163.com'] }
]

// ==================== 工具函数 ====================

/** 从 localStorage 获取当前选中的数据源 */
const getCurrentDataSource = () => {
  try {
    return localStorage.getItem(STORAGE_KEY_DATA_SOURCE) || 'netease'
  } catch {
    return 'netease'
  }
}

/** 将字符串安全转为字符串 */
const toStr = (val) => {
  if (val === null || val === undefined) return ''
  return String(val)
}

/** 格式化表单请求体 */
const buildFormBody = (params) => {
  return Object.entries(params)
    .filter(([_, v]) => v !== '' && v !== null && v !== undefined)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join('&')
}

/** 根据 URL 推断平台 */
const detectPlatformFromUrl = (url) => {
  for (const { platform, keywords } of PLATFORM_KEYWORDS) {
    if (keywords.some(k => url.includes(k))) return platform
  }
  return ''
}

// ==================== 搜索缓存 ====================

const loadCacheFromStorage = (type) => {
  try {
    const stored = localStorage.getItem(CACHE_KEY_PREFIX + type)
    if (stored) return new Map(JSON.parse(stored))
  } catch {}
  return new Map()
}

const saveCacheToStorage = (type, cache) => {
  try {
    localStorage.setItem(CACHE_KEY_PREFIX + type, JSON.stringify(Array.from(cache.entries())))
  } catch {}
}

const searchCache = {
  music: loadCacheFromStorage('music'),
  playlist: loadCacheFromStorage('playlist'),
  album: loadCacheFromStorage('album')
}

// 判断缓存是否有效：songs 或 playlists 任意一个有数据就算有效
// 两者都为空视为"缓存数据为空"，调用方应该继续走网络接口
const isCacheValid = (entry) => {
  if (!entry || !entry.data) return false
  const { songs = [], playlists = [], albums = [], artists = [] } = entry.data
  return songs.length > 0 || playlists.length > 0 || albums.length > 0 || artists.length > 0
}

const getCachedSearchResult = (type, keyword) => {
  if (!settings.enableCache) return null
  const cache = searchCache[type]
  if (!cache) return null
  const cached = cache.get(keyword)
  if (isCacheValid(cached)) return cached.data
  // 缓存数据为空（songs 和 playlists 都为空）— 视为无效，强制走网络
  // 删掉空缓存，避免下次再走无意义的判断逻辑
  if (cached) {
    cache.delete(keyword)
    saveCacheToStorage(type, cache)
  }
  return null
}

const setCachedSearchResult = (type, keyword, data) => {
  if (!settings.enableCache) return
  const cache = searchCache[type]
  if (!cache) return
  cache.set(keyword, { data, timestamp: Date.now() })
  saveCacheToStorage(type, cache)
}

// ==================== URL 解析与校验 ====================

/** 获取所有歌单/专辑/音乐链接的匹配模式 */
const getAllPatterns = (type) => {
  const patterns = []
  for (const platformPatterns of Object.values(URL_PATTERNS)) {
    if (platformPatterns[type]) patterns.push(...platformPatterns[type])
    if (type === 'music' && platformPatterns.short) patterns.push(platformPatterns.short)
  }
  return patterns
}

/** 验证音乐链接 */
export const validateMusicUrl = (url) => {
  if (!url || typeof url !== 'string') return false
  return getAllPatterns('music').some(p => p.test(url))
}

/** 验证歌单链接 */
export const validatePlaylistUrl = (url) => {
  if (!url || typeof url !== 'string') return false
  return getAllPatterns('playlist').some(p => p.test(url))
}

/** 验证专辑链接 */
export const validateAlbumUrl = (url) => {
  if (!url || typeof url !== 'string') return false
  return getAllPatterns('album').some(p => p.test(url))
}

// ==================== URL 缓存 ====================

const urlCache = new Map()
const URL_CACHE_TTL_MIN = 15 // 播放链接缓存时间（分钟）
const getUrlCacheKey = (id, quality) => `${id}|${quality}`

const getCachedUrlData = (id, quality) => {
  const entry = urlCache.get(getUrlCacheKey(id, quality))
  if (!entry) return null
  if (Date.now() - entry.fetchedAt > URL_CACHE_TTL_MIN * 60 * 1000) {
    urlCache.delete(getUrlCacheKey(id, quality))
    return null
  }
  return entry.data
}

const setCachedUrlData = (id, quality, data) => {
  urlCache.set(getUrlCacheKey(id, quality), { data, fetchedAt: Date.now() })
}

// ==================== API 调用 ====================

/** 通用 POST 表单请求 */
const postForm = async (url, params) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: buildFormBody(params)
  })
  return response.json()
}

/** 通用 POST JSON 请求 */
const postJson = async (url, data) => {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return response.json()
}

/** 获取音乐播放链接 */
export const getMusicUrl = async (musicId, quality = 'lossless', options = {}) => {
  const { bypassCache = false, updateCache = true } = options
  const platform = getCurrentDataSource()

  if (!bypassCache) {
    const cached = getCachedUrlData(musicId, quality)
    if (cached?.url) return cached
  }

  try {
    const result = await postForm('/song', {
      ids: musicId,
      level: quality,
      type: 'url',
      source: platform
    })

    if (!result.success) throw new Error(result.message || '获取音乐链接失败')

    const urlData = result.data
    if (!urlData?.url) throw new Error('该音质的音乐链接不可用')

    if (updateCache) {
      setCachedUrlData(musicId, quality, urlData)
    }
    return urlData
  } catch (error) {
    throw new Error(error.message || '获取音乐链接失败')
  }
}

// ==================== 歌曲解析 ====================

/**
 * 映射后端 /song(type=json) 返回的字段为前端统一格式
 */
const mapSongData = (songData, musicId, quality) => ({
  id: toStr(songData.id) || toStr(musicId),
  name: songData.name || '',
  artist: songData.ar_name || songData.artist || '',
  album: songData.al_name || songData.album || '',
  cover: songData.pic || songData.cover || '',
  duration: songData.duration || 0,
  url: songData.url || '',
  quality: songData.level || quality,
  qualityName: getQualityLabel(songData.level || quality),
  fileSize: songData.size || 0,
  bitRate: songData.br || 0,
  lrc: songData.lyric || '',
  tlyric: songData.tlyric || '',
  fileExtension: `.${songData.fileType || 'mp3'}`
})

/**
 * 调用后端 /song 接口获取歌曲详情（id + source 模式）
 *
 * @param {string} musicId 歌曲 ID
 * @param {string} quality 音质
 * @param {string} source 平台，传空时使用当前数据源
 */
export const parseMusicInfo = async (musicId, quality = 'lossless', source = '') => {
  if (!musicId) {
    throw new Error('歌曲ID缺失，请重新搜索')
  }

  const platform = source || getCurrentDataSource()

  try {
    const resp = await fetch('/song', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: buildFormBody({
        ids: toStr(musicId),
        level: quality,
        type: 'json',
        source: platform
      })
    })
    const result = await resp.json()
    if (!result?.success) throw new Error(result?.message || '获取歌曲信息失败')
    const songData = result.data
    if (!songData) throw new Error('未找到歌曲详情')
    return mapSongData(songData, musicId, quality)
  } catch (error) {
    const msg = error?.message || String(error) || '未知错误'
    throw new Error(msg)
  }
}

/**
 * 通过 URL 解析歌曲信息
 * URL 解析交给后端处理，前端仅传入 URL 和音质
 * @param {string} url 完整歌曲链接
 * @param {string} quality 音质
 */
export const parseMusicFromUrl = async (url, quality = 'lossless') => {
  // 前置校验：URL 必须为合法的音乐链接，避免无效请求落到后端
  if (!url || typeof url !== 'string') {
    throw new Error('请提供有效的歌曲链接')
  }
  if (!validateMusicUrl(url)) {
    throw new Error('歌曲链接格式不正确，请检查后重试')
  }

  try {
    // URL 本身就是平台信息的可靠来源（QQ 链接、网易云链接等）
    // 如果 URL 无法识别，再回退到当前数据源
    const platform = detectPlatformFromUrl(url) || getCurrentDataSource()
    const result = await postForm('/song', {
      url,
      level: quality,
      type: 'json',
      source: platform
    })

    if (!result?.success) throw new Error(result?.message || '获取歌曲信息失败')
    const songData = result.data
    if (!songData) throw new Error('未找到歌曲详情')

    return mapSongData(songData, '', quality)
  } catch (error) {
    const msg = error?.message || String(error) || '解析失败，请检查链接是否正确或稍后重试'
    throw new Error(msg)
  }
}

/** 获取歌词 */
export const getLyrics = async (musicId) => {
  try {
    const result = await postForm('/song', {
      ids: toStr(musicId),
      type: 'lyric'
    })
    if (!result.success) throw new Error(result.message || '获取歌词失败')
    return {
      lrc: result.data?.lyric || '',
      tlyric: result.data?.tlyric || '',
      romalrc: result.data?.romalrc || '',
      klyric: result.data?.klyric || ''
    }
  } catch {
    return { lrc: '', tlyric: '', romalrc: '', klyric: '' }
  }
}

// ==================== 下载 ====================

/**
 * 下载音乐
 * 1. 调用后端 /download 路由（后端用 magic bytes 检测真实类型，返回正确的 Content-Disposition）
 * 2. 从 Content-Disposition 提取文件名
 * 3. 保存到本地
 *
 * @param {Object} musicInfo 歌曲信息（id/name/artist/album/source）
 * @param {Object} downloadSettings 保留兼容
 * @param {Function} onProgress 保留兼容
 */
export const downloadMusic = async (musicInfo, downloadSettings = {}, onProgress = null) => {
  const params = new URLSearchParams({
    id: String(musicInfo.id),
    quality: musicInfo.quality || 'lossless',
    source: musicInfo.source || '',
    name: musicInfo.name || 'song',
    artist: musicInfo.artist || musicInfo.artists || '',
    album: musicInfo.album || '',
    filenameFormat: downloadSettings?.filenameFormat || 'song-artist',
    writeMetadata: String(downloadSettings?.writeMetadata ?? false)
  })

  const response = await fetch(`/download?${params.toString()}`)
  if (!response.ok) {
    let errMsg = '下载失败'
    try {
      const err = await response.json()
      errMsg = err.message || errMsg
    } catch {}
    throw new Error(errMsg)
  }

  // 从 Content-Disposition 提取文件名（后端已用 magic bytes 检测正确类型）
  const cd = response.headers.get('Content-Disposition') || ''
  const utf8Match = cd.match(/filename\*=UTF-8''([^;]+)/i)
  const asciiMatch = cd.match(/filename="?([^";]+)"?/i)
  let filename = utf8Match ? decodeURIComponent(utf8Match[1])
              : asciiMatch ? asciiMatch[1]
              : `${musicInfo.name || 'song'}.mp3`

  const blob = await response.blob()
  saveBlob(blob, sanitizeFilename(filename))
  return true
}

// ==================== 歌单 ====================

/** 通过 ID 获取歌单详情 */
export const getPlaylistById = async (playlistId, source = '') => {
  try {
    const platform = source || getCurrentDataSource()
    const result = await postForm('/playlist', {
      id: playlistId,
      limit: 100,
      source: platform
    })

    if (!result.success || !result.data) {
      return { success: false, error: result.message || '获取歌单信息失败' }
    }

    const playlist = result.data.playlist || result.data

    // 后端可能返回带 __error__ 标记的"假数据"（如隐私歌单、歌单不存在等）
    if (playlist && playlist.__error__) {
      const errorMsg = playlist.__message__ || '该歌单无法获取'
      return {
        success: false,
        error: errorMsg,
        errorType: playlist.__error__  // 'privacy' | 'api_error' | 'empty'
      }
    }

    return {
      success: true,
      data: {
        id: playlist.id,
        name: playlist.name,
        coverImgUrl: playlist.cover || playlist.coverImgUrl || '',
        description: playlist.description || '',
        playCount: playlist.play_count || playlist.playCount || 0,
        trackCount: playlist.tracks?.length || 0,
        source: playlist.source || platform,
        tracks: (playlist.tracks || []).map(track => ({
          id: track.id,
          name: track.name,
          artists: track.artists || track.artist_string || '',
          album: track.album || '',
          picUrl: track.picUrl || track.cover || '',
          duration: track.duration || 0,
          source: track.source || playlist.source || platform,
          payInfo: track.payInfo || null,
          qualityMap: track.qualityMap || null,
          bestQuality: track.bestQuality || '',
        }))
      }
    }
  } catch (error) {
    return { success: false, error: `网络请求失败: ${error.message || '未知错误'}` }
  }
}

/** 通过 URL 获取歌单详情 */
export const getPlaylistDetail = async (url) => {
  try {
    // URL 解析由后端处理，前端不参与 URL 与平台的匹配
    // 兜底使用当前数据源，避免后端在某些情况下无法识别
    const result = await postForm('/playlist', {
      url,
      limit: 100,
      source: detectPlatformFromUrl(url) || getCurrentDataSource()
    })

    if (!result.success || !result.data) {
      return { success: false, error: result.message || '获取歌单信息失败' }
    }

    const playlist = result.data.playlist || result.data

    // 后端可能返回带 __error__ 标记的"假数据"（如隐私歌单）
    if (playlist && playlist.__error__) {
      return {
        success: false,
        error: playlist.__message__ || '该歌单无法获取',
        errorType: playlist.__error__  // 'privacy' | 'api_error' | 'empty'
      }
    }

    return {
      success: true,
      data: {
        id: playlist.id,
        name: playlist.name,
        coverImgUrl: playlist.cover || playlist.coverImgUrl || '',
        description: playlist.description || '',
        playCount: playlist.play_count || playlist.playCount || 0,
        trackCount: playlist.tracks?.length || 0,
        source: playlist.source || 'netease',
        tracks: (playlist.tracks || []).map(track => ({
          id: track.id,
          name: track.name,
          artists: track.artists || track.artist_string || '',
          album: track.album || '',
          picUrl: track.picUrl || track.cover || '',
          duration: track.duration || 0,
          source: track.source || playlist.source || 'netease'
        }))
      }
    }
  } catch (error) {
    return { success: false, error: `网络请求失败: ${error.message || '未知错误'}` }
  }
}

// ==================== 搜索 ====================

/** 映射后端搜索结果为前端使用的字段 */
const mapSearchSongs = (songs) => songs.map(song => ({
  id: song.id,
  name: song.name,
  artists: song.artists || song.artist_string || '',
  album: song.album || '',
  duration: song.duration || 0,
  picUrl: song.picUrl || '',
  source: song.source,
  // URL 解析模式下后端返回的歌曲详情（type=1 时的额外字段）
  url: song.url || '',
  lrc: song.lyric || '',
  fileExtension: song.fileType ? `.${song.fileType}` : '.mp3',
  // 类型标识（用于前端区分展示）
  _type: song._type || 'song',
  // 付费和音质信息
  payInfo: song.payInfo || null,
  qualityMap: song.qualityMap || null,
  bestQuality: song.bestQuality || '',
}))

const mapSearchPlaylists = (playlists) => playlists.map(playlist => ({
  id: playlist.id,
  name: playlist.name,
  coverImgUrl: playlist.cover || playlist.coverImgUrl || '',
  description: playlist.description || '',
  playCount: playlist.play_count || playlist.playCount || 0,
  trackCount: playlist.track_count || playlist.trackCount || 0,
  source: playlist.source || 'netease',
  _type: playlist._type || 'playlist'
}))

/**
 * 统一搜索接口
 * @param {string} keyword 搜索内容（关键词或 URL）
 * @param {number} type 搜索类型：0=全部 / 1=歌曲 / 2=歌单（仅当 keyword 不是 URL 时生效）
 * @param {Array<string>} sources 数据源列表
 *
 * 返回：{type: 0/1/2, songs: [...], playlists: [...]}，根据 type 分桶
 */
export const unifiedSearch = async (keyword, type = 0, sources = ['netease'], quality = 'lossless') => {
  try {
    const cacheKey = `${type}-${keyword}-${sources.join(',')}-${quality}`
    const cached = getCachedSearchResult('unified', cacheKey)
    if (cached) return { success: true, data: cached, fromCache: true }

    const requestData = { keyword, type, limit: 50, quality }
    if (sources.length === 1) requestData.source = sources[0]

    const result = await postJson('/search', requestData)
    if (!result.success || !result.data) {
      return { success: false, error: result.message || '搜索失败' }
    }

    // result.data = {type: 0/1/2, data: [...], warnings: [...]}，每项带 _type
    const { type: respType, data: items, warnings } = result.data
    const songs = []
    const playlists = []
    for (const item of items || []) {
      if (item._type === 'playlist') {
        playlists.push(mapSearchPlaylists([item])[0])
      } else {
        songs.push(mapSearchSongs([item])[0])
      }
    }

    const searchData = { type: respType, songs, playlists, warnings: warnings || [] }
    setCachedSearchResult('unified', cacheKey, searchData)
    return { success: true, data: searchData }
  } catch (error) {
    return { success: false, error: error.message || '搜索失败' }
  }
}

/** 搜索歌曲（兼容旧 API） */
export const searchMusic = async (keyword, sources = ['netease']) => {
  const result = await unifiedSearch(keyword, 1, sources)
  if (!result.success) return result
  return { ...result, data: { songs: result.data.songs } }
}

/** 搜索歌单（兼容旧 API） */
export const searchPlaylist = async (keyword, sources = ['netease']) => {
  const result = await unifiedSearch(keyword, 2, sources)
  if (!result.success) return result
  return { ...result, data: result.data.playlists }
}

// ==================== 批量下载 ====================

/**
 * 启动批量下载任务（异步，立即返回 task_id）
 * 后端会启动后台线程执行下载，前端通过 SSE 订阅进度
 *
 * @param {Array} items [{id, name, artist, album, source, quality}, ...]
 * @param {string} name 任务名（用于 zip 文件名）
 * @param {Object} settings {writeMetadata, filenameFormat}
 * @returns {Promise<{success, data: {task_id, total}, message}>}
 */
export const startBatchTask = async (items, name = 'playlist', settings = {}) => {
  const resp = await fetch('/download/batch/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, name, settings })
  })
  if (!resp.ok) {
    let errMsg = '启动批量下载失败'
    try {
      const err = await resp.json()
      errMsg = err.message || errMsg
    } catch {}
    throw new Error(errMsg)
  }
  return await resp.json()
}

/**
 * 列出所有批量下载任务（按创建时间倒序）
 * 用于刷新页面后恢复任务列表
 */
export const getBatchList = async () => {
  const resp = await fetch('/download/batch/list')
  if (!resp.ok) throw new Error('查询任务列表失败')
  return await resp.json()
}

/**
 * 查询单个任务信息（一次性查询，不订阅 SSE）
 */
export const getBatchInfo = async (taskId) => {
  const resp = await fetch(`/download/batch/info/${taskId}`)
  if (!resp.ok) throw new Error('查询任务失败')
  return await resp.json()
}

/**
 * 取消/删除批量下载任务
 * - 任务进行中：标记 cancelled，清理已下载文件
 * - 任务已完成：清理 zip 文件
 */
export const cancelBatchTask = async (taskId) => {
  const resp = await fetch(`/download/batch/${taskId}`, { method: 'DELETE' })
  if (!resp.ok) {
    let errMsg = '取消任务失败'
    try {
      const err = await resp.json()
      errMsg = err.message || errMsg
    } catch {}
    throw new Error(errMsg)
  }
  return await resp.json()
}

/**
 * 订阅批量下载进度（SSE）
 * 返回 unsubscribe 函数
 *
 * @param {string} taskId
 * @param {Object} callbacks { onProgress, onComplete, onError }
 * @returns {Function} unsubscribe
 */
export const subscribeBatchTask = (taskId, callbacks = {}) => {
  const { onProgress, onComplete, onError } = callbacks
  const es = new EventSource(`/download/batch/progress/${taskId}`)
  let closed = false

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.error) {
        onError?.(new Error(data.error))
        close()
        return
      }
      if (data.status === 'done' || data.status === 'error' || data.status === 'cancelled') {
        onComplete?.(data)
        close()
        return
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

/**
 * 下载已打包好的 zip 文件
 * @param {string} taskId
 * @returns {Promise<{blob, filename}>}
 */
export const downloadBatchFile = async (taskId) => {
  const resp = await fetch(`/download/batch/file/${taskId}`)
  if (!resp.ok) {
    let errMsg = '下载 zip 失败'
    try {
      const err = await resp.json()
      errMsg = err.message || errMsg
    } catch {}
    throw new Error(errMsg)
  }
  const blob = await resp.blob()
  // 从 Content-Disposition 提取文件名
  const disposition = resp.headers.get('Content-Disposition') || ''
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const asciiMatch = disposition.match(/filename="?([^";]+)"?/i)
  let filename = 'playlist.zip'
  if (utf8Match) {
    filename = decodeURIComponent(utf8Match[1])
  } else if (asciiMatch) {
    filename = asciiMatch[1]
  }
  return { blob, filename }
}

/**
 * 触发浏览器下载 zip（包装 downloadBatchFile + saveBlob）
 */
export const downloadBatchAsZip = async (taskId) => {
  const { blob, filename } = await downloadBatchFile(taskId)
  saveBlob(blob, filename)
  return filename
}

/**
 * 批量下载音乐（一体化便捷 API：启动 → 订阅 → 下载）
 * 简单场景使用（无队列管理）；复杂场景建议用 startBatchTask + subscribeBatchTask
 *
 * @param {Array} musicList 歌曲列表（需含 id, name, artist, album, source）
 * @param {string} playlistName 歌单名称（用于 zip 文件名）
 * @param {Object} downloadSettings { selectedQuality, filenameFormat, writeMetadata }
 * @param {Function} onProgress 进度回调
 */
export const batchDownloadMusic = async (musicList, playlistName = '', downloadSettings = {}, onProgress = null) => {
  const total = musicList.length
  const sendProgress = (state) => {
    onProgress?.({
      total,
      completed: state.completed,
      failed: state.failed,
      percentage: state.percentage,
      current: state.current
    })
  }

  if (total === 0) {
    return { total: 0, completed: 0, failed: 0, results: [] }
  }

  sendProgress({ completed: 0, failed: 0, percentage: 0, current: '启动任务...' })

  const quality = downloadSettings.selectedQuality || 'lossless'
  const items = musicList.map(m => ({
    id: m.id,
    name: m.name,
    artist: m.artist,
    album: m.album,
    source: m.source,
    quality
  }))
  const settings = {
    writeMetadata: downloadSettings.writeMetadata !== false,
    filenameFormat: downloadSettings.filenameFormat || 'song-artist',
  }

  // 1. 启动任务
  const startResult = await startBatchTask(items, playlistName || 'playlist', settings)
  const taskId = startResult.data.task_id

  sendProgress({ completed: 0, failed: 0, percentage: 5, current: '后端下载中...' })

  // 2. SSE 订阅进度
  const finalState = await new Promise((resolve, reject) => {
    const unsubscribe = subscribeBatchTask(taskId, {
      onProgress: (data) => {
        const percentage = data.total > 0
          ? Math.round((data.completed / data.total) * 90) + 5
          : 5
        sendProgress({
          completed: data.completed,
          failed: data.failed,
          percentage,
          current: data.current
        })
      },
      onComplete: (data) => {
        unsubscribe()
        resolve(data)
      },
      onError: (err) => {
        unsubscribe()
        reject(err)
      }
    })
  })

  if (finalState.status === 'error') {
    throw new Error(finalState.error || '任务执行失败')
  }

  // 3. 下载 zip
  sendProgress({ completed: total, failed: finalState.failed, percentage: 95, current: '下载中...' })
  const filename = await downloadBatchAsZip(taskId)
  sendProgress({ completed: total, failed: finalState.failed, percentage: 100, current: '完成' })

  return {
    total,
    completed: finalState.completed,
    failed: finalState.failed,
    errors: finalState.errors || [],
    filename
  }
}

export default {
  validateMusicUrl,
  validatePlaylistUrl,
  validateAlbumUrl,
  parseMusicInfo,
  parseMusicFromUrl,
  getLyrics,
  downloadMusic,
  batchDownloadMusic,
  getPlaylistDetail,
  getPlaylistById,
  searchMusic,
  searchPlaylist,
  unifiedSearch,
  getMusicUrl
}
