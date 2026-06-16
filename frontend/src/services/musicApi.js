/**
 * 音乐API服务
 * 通过后端API实现多平台音乐搜索和解析
 */

import { embedMetadata } from './metadataWriter.js'
import { saveBlob, ensureBlobType, sanitizeFilename } from '../utils/downloadHelper.js'
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

/** MIME 类型映射 */
const MIME_TYPES = {
  '.mp3': 'audio/mpeg',
  '.flac': 'audio/flac',
  '.m4a': 'audio/mp4'
}

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

const isCacheValid = (entry) => {
  return entry && entry.data?.songs?.length > 0
}

const getCachedSearchResult = (type, keyword) => {
  if (!settings.enableCache) return null
  const cache = searchCache[type]
  if (!cache) return null
  const cached = cache.get(keyword)
  if (isCacheValid(cached)) return cached.data
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

/** 流式下载文件并返回 Blob */
const streamDownload = async (url, onProgress = null) => {
  const response = await fetch(url, { cache: 'no-store', mode: 'cors' })
  if (!response.ok) throw new Error(`下载失败: ${response.statusText}`)

  const contentLength = parseInt(response.headers.get('Content-Length') || '0', 10)
  const reader = response.body.getReader()
  const chunks = []
  let downloadedBytes = 0
  const startTime = Date.now()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
    downloadedBytes += value.length

    if (onProgress && contentLength > 0) {
      const elapsed = (Date.now() - startTime) / 1000
      const speed = elapsed > 0 ? downloadedBytes / elapsed / 1024 : 0
      const remainingBytes = contentLength - downloadedBytes
      const eta = speed > 0 ? Math.ceil(remainingBytes / speed / 1024) : 0
      onProgress({
        downloadedBytes,
        totalBytes: contentLength,
        percentage: Math.round((downloadedBytes / contentLength) * 100),
        speed: speed.toFixed(1),
        eta
      })
    }
  }

  return new Blob(chunks, { type: response.headers.get('Content-Type') })
}

/** 生成下载文件名 */
const buildFilename = (musicInfo, filenameFormat, extension) => {
  if (filenameFormat === 'artist-song') {
    return `${musicInfo.artist} - ${musicInfo.name}${extension}`
  }
  if (filenameFormat === 'song') {
    return `${musicInfo.name}${extension}`
  }
  return `${musicInfo.name} - ${musicInfo.artist}${extension}`
}

/** 写入音频元数据（如果启用） */
const applyAudioMetadata = async (audioBuffer, musicInfo, extension, writeMetadata) => {
  if (!writeMetadata || (extension !== '.mp3' && extension !== '.flac')) {
    return audioBuffer
  }
  try {
    return await embedMetadata(audioBuffer, {
      name: musicInfo.name,
      artist: musicInfo.artist,
      album: musicInfo.album,
      year: new Date().getFullYear().toString(),
      lyrics: musicInfo.lrc,
      cover: musicInfo.cover
    }, extension)
  } catch {
    return audioBuffer
  }
}

/** 下载音乐 */
export const downloadMusic = async (musicInfo, downloadSettings = {}, onProgress = null) => {
  const { filenameFormat = 'song-artist', writeMetadata = false } = downloadSettings
  const extension = musicInfo.fileExtension || '.mp3'
  const filename = buildFilename(musicInfo, filenameFormat, extension)

  try {
    let audioBuffer = await (await streamDownload(musicInfo.url, onProgress)).arrayBuffer()
    audioBuffer = await applyAudioMetadata(audioBuffer, musicInfo, extension, writeMetadata)

    const mime = MIME_TYPES[extension] || 'audio/mpeg'
    const typedBlob = ensureBlobType(new Blob([audioBuffer], { type: mime }), mime)
    saveBlob(typedBlob, sanitizeFilename(filename))
    return true
  } catch (error) {
    throw new Error(`下载失败: ${error.message}`)
  }
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
          source: track.source || playlist.source || platform
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
  url: song.url || ''  // 后端返回的完整歌曲链接
}))

const mapSearchPlaylists = (playlists) => playlists.map(playlist => ({
  id: playlist.id,
  name: playlist.name,
  coverImgUrl: playlist.cover || playlist.coverImgUrl || '',
  description: playlist.description || '',
  playCount: playlist.play_count || playlist.playCount || 0,
  trackCount: playlist.track_count || playlist.trackCount || 0,
  source: playlist.source || 'netease',
  url: playlist.url || ''  // 后端返回的完整歌单链接
}))

/** 搜索音乐 */
export const searchMusic = async (keyword, sources = ['netease']) => {
  try {
    const cacheKey = `${keyword}-${sources.join(',')}`
    const cached = getCachedSearchResult('music', cacheKey)
    if (cached) return { success: true, data: cached, fromCache: true }

    const requestData = { keyword, limit: 60 }
    if (sources.length === 1) requestData.source = sources[0]

    const result = await postJson('/search', requestData)
    if (!result.success || !result.data) {
      return { success: false, error: result.message || '搜索失败' }
    }

    const searchData = { songs: mapSearchSongs(result.data) }
    setCachedSearchResult('music', cacheKey, searchData)
    return { success: true, data: searchData }
  } catch (error) {
    return { success: false, error: error.message || '搜索失败' }
  }
}

/** 搜索歌单 */
export const searchPlaylist = async (keyword, sources = ['netease']) => {
  try {
    const cacheKey = `${keyword}-${sources.join(',')}`
    const cached = getCachedSearchResult('playlist', cacheKey)
    if (cached) return { success: true, data: cached, fromCache: true }

    const requestData = { keyword, limit: 20 }
    if (sources.length === 1) requestData.source = sources[0]

    const result = await postJson('/search/playlist', requestData)
    if (!result.success || !result.data) {
      return { success: false, error: result.message || '搜索失败' }
    }

    const playlists = mapSearchPlaylists(result.data)
    setCachedSearchResult('playlist', cacheKey, playlists)
    return { success: true, data: playlists }
  } catch (error) {
    return { success: false, error: error.message || '搜索失败' }
  }
}

// ==================== 批量下载 ====================

/**
 * 批量下载音乐（打包为 ZIP）
 * @param {Array} musicList 歌曲列表（需含 url、name、artist 等）
 * @param {string} playlistName 歌单名称（用于 zip 文件名）
 * @param {Object} downloadSettings 下载设置 { filenameFormat, writeMetadata, downloadLrcFile }
 * @param {Function} onProgress 进度回调
 */
export const batchDownloadMusic = async (musicList, playlistName = '', downloadSettings = {}, onProgress = null) => {
  const results = []
  const total = musicList.length
  let completed = 0
  let failed = 0
  let totalBytes = 0
  let downloadedBytes = 0
  const startTime = Date.now()
  const activeDownloads = new Map()
  const maxConcurrency = 12

  /** 发送进度更新 */
  const sendProgress = () => {
    if (!onProgress) return
    const elapsed = (Date.now() - startTime) / 1000
    const speed = elapsed > 0 ? downloadedBytes / elapsed / 1024 : 0
    const remainingBytes = totalBytes - downloadedBytes
    const eta = speed > 0 ? Math.ceil(remainingBytes / speed / 1024) : 0
    onProgress({
      total,
      completed,
      failed,
      totalBytes,
      downloadedBytes,
      percentage: totalBytes > 0
        ? Math.round((downloadedBytes / totalBytes) * 100)
        : Math.round(((completed + failed) / total) * 100),
      speed: speed.toFixed(1),
      eta,
      activeDownloads: Array.from(activeDownloads.values())
    })
  }

  /** 预获取文件总大小 */
  const fetchTotalSize = async () => {
    const sizes = await Promise.all(musicList.map(async (info) => {
      try {
        const res = await fetch(info.url, { method: 'HEAD' })
        return parseInt(res.headers.get('Content-Length') || '0', 10)
      } catch {
        return 0
      }
    }))
    totalBytes = sizes.reduce((sum, s) => sum + s, 0)
  }

  /** 下载单首歌曲并加入 zip */
  const runDownload = async (musicInfo) => {
    const trackId = musicInfo.id
    activeDownloads.set(trackId, { name: musicInfo.name, downloaded: 0, total: 0, status: 'downloading' })

    try {
      const extension = musicInfo.fileExtension || '.mp3'
      const sanitizedName = musicInfo.name.replace(/[<>:"/\\|?*]/g, '_')
      const sanitizedArtist = musicInfo.artist.replace(/[<>:"/\\|?*]/g, '_')
      const filename = downloadSettings.filenameFormat === 'artist-song'
        ? `${sanitizedArtist} - ${sanitizedName}${extension}`
        : `${sanitizedName} - ${sanitizedArtist}${extension}`

      const response = await fetch(musicInfo.url, { cache: 'no-store', mode: 'cors' })
      if (!response.ok) throw new Error(`下载失败: ${response.statusText}`)

      const contentLength = parseInt(response.headers.get('Content-Length') || '0', 10)
      const reader = response.body.getReader()
      const chunks = []
      let localDownloaded = 0

      activeDownloads.set(trackId, { name: musicInfo.name, downloaded: 0, total: contentLength, status: 'downloading' })

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        chunks.push(value)
        localDownloaded += value.length
        downloadedBytes += value.length
        activeDownloads.set(trackId, { name: musicInfo.name, downloaded: localDownloaded, total: contentLength, status: 'downloading' })
        sendProgress()
      }

      let audioBuffer = await new Blob(chunks).arrayBuffer()
      audioBuffer = await applyAudioMetadata(audioBuffer, musicInfo, extension, downloadSettings.writeMetadata)

      zip.file(filename, audioBuffer)
      if (downloadSettings.downloadLrcFile !== false && musicInfo.lrc) {
        zip.file(filename.replace(extension, '.lrc'), musicInfo.lrc)
      }

      activeDownloads.set(trackId, { name: musicInfo.name, downloaded: contentLength, total: contentLength, status: 'completed' })
      completed++
      sendProgress()
      return { success: true, name: musicInfo.name, id: musicInfo.id }
    } catch (error) {
      activeDownloads.set(trackId, { name: musicInfo.name, downloaded: 0, total: 0, status: 'failed', error: error.message })
      failed++
      sendProgress()
      return { success: false, name: musicInfo.name, id: musicInfo.id, error: error.message }
    } finally {
      activeDownloads.delete(trackId)
    }
  }

  try {
    const JSZip = (await import('jszip')).default
    const zip = new JSZip()

    await fetchTotalSize()
    sendProgress()

    // 简单的并发控制
    const queue = [...musicList]
    const workers = Array.from({ length: maxConcurrency }, async () => {
      while (queue.length > 0) {
        const item = queue.shift()
        if (item) results.push(await runDownload(item))
      }
    })
    await Promise.all(workers)

    if (completed > 0) {
      onProgress?.({ status: 'packing', message: '正在打包 ZIP 文件...' })
      const content = await zip.generateAsync({ type: 'blob' })
      const zipFilename = playlistName
        ? `${playlistName.replace(/[<>:"/\\|?*]/g, '_')}.zip`
        : `music_${Date.now()}.zip`

      const a = document.createElement('a')
      a.href = URL.createObjectURL(content)
      a.download = zipFilename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(a.href)
    }

    return { total, completed, failed, results }
  } catch (error) {
    throw new Error(`批量下载失败: ${error.message}`)
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
  getMusicUrl
}
