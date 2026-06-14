/**
 * 音乐API服务
 * 通过后端API实现多平台音乐搜索和解析
 */

import { embedMetadata } from './metadataWriter.js'
import { saveBlob, ensureBlobType, getMimeByExtension, sanitizeFilename } from '../utils/downloadHelper.js'
import { settings } from '../utils/settingsManager.js'
import { getQualityLabel } from '../config/qualityLevels.js'

// 从 localStorage 加载缓存
const loadCacheFromStorage = (type) => {
  const stored = localStorage.getItem(`wan-music-search-${type}`)
  if (stored) {
    try {
      return new Map(JSON.parse(stored))
    } catch {
      return new Map()
    }
  }
  return new Map()
}

// 保存缓存到 localStorage
const saveCacheToStorage = (type, cache) => {
  localStorage.setItem(`wan-music-search-${type}`, JSON.stringify(Array.from(cache.entries())))
}

// 搜索缓存（从 localStorage 加载，持久化存储）
const searchCache = {
  music: loadCacheFromStorage('music'),
  playlist: loadCacheFromStorage('playlist'),
  album: loadCacheFromStorage('album')
}

// 检查缓存是否有效（长期有效，不过期）
const isCacheValid = (cacheEntry) => {
  if (!cacheEntry) return false
  // 检查数据是否有效（有歌曲数据）
  const dataLength = cacheEntry.data?.songs?.length || 0
  return dataLength > 0
}

// 获取缓存数据
const getCachedSearchResult = (type, keyword) => {
  if (!settings.enableCache) {
    console.log(`缓存已禁用，跳过缓存查询`)
    return null
  }
  
  const cache = searchCache[type]
  if (!cache) {
    console.log(`缓存类型 ${type} 不存在`)
    return null
  }
  
  const cached = cache.get(keyword)
  if (isCacheValid(cached)) {
    const dataLength = cached.data?.songs?.length || Object.keys(cached.data || {}).length
    console.log(`使用缓存的${type}搜索结果: ${keyword}, 数据长度: ${dataLength}`)
    return cached.data
  }
  
  if (cached) {
    cache.delete(keyword)
    saveCacheToStorage(type, cache)
  }
  return null
}

// 设置缓存数据
const setCachedSearchResult = (type, keyword, data) => {
  if (!settings.enableCache) return
  
  const cache = searchCache[type]
  if (!cache) return
  
  cache.set(keyword, {
    data,
    timestamp: Date.now()
  })
  saveCacheToStorage(type, cache)
}

/**
 * @typedef {Object} MusicInfo
 * @property {string} id - 歌曲ID
 * @property {string} name - 歌曲名称
 * @property {string} artist - 歌手名称
 * @property {string} album - 专辑名称
 * @property {string} cover - 封面图片URL
 * @property {number} duration - 歌曲时长(毫秒)
 * @property {string} url - 音频文件URL
 * @property {string} [lrc] - 歌词内容
 */

// 从文本中提取URL
const extractUrlFromText = (text) => {
  if (!text) return text
  if (typeof text !== 'string') {
    text = String(text)
  }
  const urlRegex = /(https?:\/\/[^\s"<>]+)/
  const match = text.match(urlRegex)
  return match ? match[0] : text
}

// 统一的ID提取函数 - 支持多平台
export const extractIdFromUrl = async (text) => {
  try {
    if (!text) return null
    if (typeof text !== 'string') {
      text = String(text)
    }
    
    const url = extractUrlFromText(text)
    if (!url) return null
    
    // 网易云音乐 - 短链接模式
    if (/https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/.test(url)) {
      return url
    }

    // 网易云音乐 - 歌曲链接模式
    const neteaseMusicPatterns = [
      /https?:\/\/music\.163\.com\/song\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/song\?id=(\d+)/
    ]
    
    // 网易云音乐 - 歌单链接模式
    const neteasePlaylistPatterns = [
      /https?:\/\/music\.163\.com\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\/(\d+)/,
      /https?:\/\/music\.163\.com\/#\/playlist\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/discover\/toplist\?id=(\d+)/
    ]

    // 网易云音乐 - 专辑链接模式
    const neteaseAlbumPatterns = [
      /https?:\/\/music\.163\.com\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/album\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\/(\d+)/
    ]
    
    // QQ音乐 - 歌曲链接模式
    const qqMusicPatterns = [
      /https?:\/\/y\.qq\.com\/n\/ryqq\/songDetail\/([a-zA-Z0-9]+)/,
      /https?:\/\/i\.y\.qq\.com\/n2\/m\/share\/details\/song\.html\?.*songid=(\d+)/,
      /https?:\/\/c\.y\.qq\.com\/base\/cgi-bin\/u\.cgi\?.*url=.*songDetail\/([a-zA-Z0-9]+)/
    ]
    
    // QQ音乐 - 歌单链接模式
    const qqPlaylistPatterns = [
      /https?:\/\/y\.qq\.com\/n\/ryqq\/playlist\/(\d+)/,
      /https?:\/\/i\.y\.qq\.com\/n2\/m\/share\/details\/taoge\.html\?.*id=(\d+)/
    ]
    
    // 酷狗音乐 - 歌曲链接模式
    const kugouMusicPatterns = [
      /https?:\/\/www\.kugou\.com\/song\/#hash=([a-zA-Z0-9]+)/,
      /https?:\/\/www\.kugou\.com\/mixsong\/([a-zA-Z0-9]+)/,
      /https?:\/\/m\.kugou\.com\/app\/i\/getSongInfo\.php\?.*hash=([a-zA-Z0-9]+)/
    ]
    
    // 酷狗音乐 - 歌单链接模式
    const kugouPlaylistPatterns = [
      /https?:\/\/www\.kugou\.com\/yy\/special\/single\/(\d+)\.html/,
      /https?:\/\/m\.kugou\.com\/plist\/list\/index\.php\?.*id=(\d+)/
    ]
    
    // 波点音乐 - 歌曲链接模式
    const bodianMusicPatterns = [
      /https?:\/\/bodian\.kuwo\.cn\/song\/([a-zA-Z0-9]+)/,
      /https?:\/\/www\.bodianmusic\.com\/song\/([a-zA-Z0-9]+)/
    ]
    
    // 波点音乐 - 歌单链接模式
    const bodianPlaylistPatterns = [
      /https?:\/\/bodian\.kuwo\.cn\/playlist\/([a-zA-Z0-9]+)/,
      /https?:\/\/www\.bodianmusic\.com\/playlist\/([a-zA-Z0-9]+)/
    ]
    
    // 合并所有模式
    const allPatterns = [
      ...neteaseMusicPatterns,
      ...neteasePlaylistPatterns,
      ...neteaseAlbumPatterns,
      ...qqMusicPatterns,
      ...qqPlaylistPatterns,
      ...kugouMusicPatterns,
      ...kugouPlaylistPatterns,
      ...bodianMusicPatterns,
      ...bodianPlaylistPatterns
    ]
    
    for (const pattern of allPatterns) {
      const match = url.match(pattern)
      if (match) {
        return match[1]
      }
    }
    
    // 如果是URL格式但未匹配到特定模式，返回整个URL让后端处理
    if (/^https?:\/\//.test(url)) {
      return url
    }
    
    return null
  } catch {
    return null
  }
}

// 验证链接格式 - 支持多平台
export const validateUrl = (url) => {
  try {
    if (!url || typeof url !== 'string') {
      return false
    }
    
    // 检查是否是URL格式
    if (/^https?:\/\//.test(url)) {
      return true
    }
    
    return false
  } catch {
    return false
  }
}

// 验证音乐链接格式 - 支持多平台
export const validateMusicUrl = (url) => {
  try {
    if (!url || typeof url !== 'string') {
      return false
    }
    
    // 网易云音乐
    const neteasePatterns = [
      /https?:\/\/music\.163\.com\/song\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/song\?id=(\d+)/,
      /https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/
    ]
    
    // QQ音乐
    const qqPatterns = [
      /https?:\/\/y\.qq\.com\/n\/ryqq\/songDetail\/([a-zA-Z0-9]+)/,
      /https?:\/\/i\.y\.qq\.com\/n2\/m\/share\/details\/song\.html\?.*songid=(\d+)/
    ]
    
    // 酷狗音乐
    const kugouPatterns = [
      /https?:\/\/www\.kugou\.com\/song\/#hash=([a-zA-Z0-9]+)/,
      /https?:\/\/www\.kugou\.com\/mixsong\/([a-zA-Z0-9]+)/,
      /https?:\/\/m\.kugou\.com\/app\/i\/getSongInfo\.php\?.*hash=([a-zA-Z0-9]+)/
    ]
    
    // 波点音乐
    const bodianPatterns = [
      /https?:\/\/bodian\.kuwo\.cn\/song\/([a-zA-Z0-9]+)/,
      /https?:\/\/www\.bodianmusic\.com\/song\/([a-zA-Z0-9]+)/
    ]
    
    const allPatterns = [...neteasePatterns, ...qqPatterns, ...kugouPatterns, ...bodianPatterns]
    return allPatterns.some(pattern => pattern.test(url))
  } catch {
    return false
  }
}

// 验证歌单链接格式 - 支持多平台
export const validatePlaylistUrl = (url) => {
  try {
    if (!url || typeof url !== 'string') {
      return false
    }
    
    // 网易云音乐
    const neteasePatterns = [
      /https?:\/\/music\.163\.com\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\/(\d+)/,
      /https?:\/\/music\.163\.com\/#\/playlist\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/discover\/toplist\?id=(\d+)/,
      /https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/
    ]
    
    // QQ音乐
    const qqPatterns = [
      /https?:\/\/y\.qq\.com\/n\/ryqq\/playlist\/(\d+)/,
      /https?:\/\/i\.y\.qq\.com\/n2\/m\/share\/details\/taoge\.html\?.*id=(\d+)/
    ]
    
    // 酷狗音乐
    const kugouPatterns = [
      /https?:\/\/www\.kugou\.com\/yy\/special\/single\/(\d+)\.html/,
      /https?:\/\/m\.kugou\.com\/plist\/list\/index\.php\?.*id=(\d+)/
    ]
    
    // 波点音乐
    const bodianPatterns = [
      /https?:\/\/bodian\.kuwo\.cn\/playlist\/([a-zA-Z0-9]+)/,
      /https?:\/\/www\.bodianmusic\.com\/playlist\/([a-zA-Z0-9]+)/
    ]
    
    const allPatterns = [...neteasePatterns, ...qqPatterns, ...kugouPatterns, ...bodianPatterns]
    return allPatterns.some(pattern => pattern.test(url))
  } catch {
    return false
  }
}

// 验证专辑链接格式
export const validateAlbumUrl = (url) => {
  try {
    if (!url || typeof url !== 'string') {
      return false
    }
    
    // 网易云音乐
    const neteasePatterns = [
      /https?:\/\/music\.163\.com\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/album\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\/(\d+)/,
      /https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/
    ]
    
    return neteasePatterns.some(pattern => pattern.test(url))
  } catch {
    return false
  }
}

export const getMusicIdFromUrl = extractIdFromUrl
export const extractPlaylistId = extractIdFromUrl
export const extractAlbumId = extractIdFromUrl

// 播放链接内存缓存
const urlCache = new Map()
const getUrlCacheKey = (id, quality) => `${id}|${quality}`
const getCachedUrlData = (id, quality) => {
  try {
    const key = getUrlCacheKey(id, quality)
    const entry = urlCache.get(key)
    if (!entry) return null
    const ttlMin = Number(settings?.urlCacheTTLMinutes) || 15
    const ttlMs = ttlMin * 60 * 1000
    if (Date.now() - entry.fetchedAt > ttlMs) {
      urlCache.delete(key)
      return null
    }
    return entry.data
  } catch {
    return null
  }
}
const setCachedUrlData = (id, quality, data) => {
  urlCache.set(getUrlCacheKey(id, quality), { data, fetchedAt: Date.now() })
}

// 获取音乐播放链接
export const getMusicUrl = async (musicId, quality = 'lossless', options = {}) => {
  const { bypassCache = false, updateCache = true } = options
  
  if (settings?.enableUrlCache && !bypassCache) {
    const cached = getCachedUrlData(musicId, quality)
    if (cached && cached.url) {
      return cached
    }
  }

  try {
    // 使用后端 /song 接口而不是直接调用 EAPI
    // 数据源自动切换，无需前端指定
    const response = await fetch('/song', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `ids=${musicId}&level=${quality}&type=url`
    })
    
    const result = await response.json()
    
    if (!result.success) {
      throw new Error(result.message || '获取音乐链接失败')
    }

    const urlData = result.data
    if (!urlData || !urlData.url) {
      throw new Error('该音质的音乐链接不可用')
    }

    if (settings?.enableUrlCache && updateCache) {
      setCachedUrlData(musicId, quality, urlData)
    }

    return urlData
  } catch (error) {
    throw new Error(error.message || '获取音乐链接失败')
  }
}

// 解析音乐信息 - 使用后端API
export const parseMusicInfo = async (url, quality = 'lossless') => {
  try {
    const musicId = await extractIdFromUrl(url)
    if (!musicId) {
      throw new Error('无法从链接中提取歌曲ID')
    }

    // 使用后端 /song 接口获取完整歌曲信息
    const response = await fetch('/song', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `ids=${musicId}&level=${quality}&type=json`
    })
    
    const result = await response.json()
    
    if (!result.success) {
      throw new Error(result.message || '获取歌曲信息失败')
    }

    const songData = result.data
    if (!songData) {
      throw new Error('未找到歌曲详情')
    }

    // 构造返回的音乐信息
    const musicInfo = {
      id: songData.id?.toString() || musicId,
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
    }

    return musicInfo

  } catch (error) {
    throw new Error(error.message || '解析失败，请检查链接是否正确或稍后重试')
  }
}

// 获取歌词 - 使用后端API
export const getLyrics = async (musicId) => {
  try {
    if (typeof musicId !== 'string') {
      if (musicId === null || musicId === undefined) {
        throw new Error('歌曲ID不能为空')
      }
      musicId = String(musicId)
    }
    
    // 使用后端 /song 接口获取歌词
    const response = await fetch('/song', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `ids=${musicId}&type=lyric`
    })
    
    const result = await response.json()
    
    if (!result.success) {
      throw new Error(result.message || '获取歌词失败')
    }

    return {
      lrc: result.data?.lyric || '',
      tlyric: result.data?.tlyric || '',
      romalrc: result.data?.romalrc || '',
      klyric: result.data?.klyric || ''
    }
  } catch {
    return { 
      lrc: '',
      tlyric: '',
      romalrc: '',
      klyric: ''
    }
  }
}



// 流式下载文件并返回Blob
const streamDownload = async (url, onProgress = null) => {
  const response = await fetch(url, { cache: 'no-store', mode: 'cors' })
  if (!response.ok) {
    throw new Error(`下载失败: ${response.statusText}`)
  }

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
      const speed = elapsed > 0 ? downloadedBytes / elapsed / 1024 : 0 // KB/s
      const remainingBytes = contentLength - downloadedBytes
      const eta = speed > 0 ? Math.ceil(remainingBytes / speed / 1024) : 0 // 秒

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

// 下载音乐
export const downloadMusic = async (musicInfo, settings = {}, onProgress = null) => {
  const {
    filenameFormat = 'song-artist',
    writeMetadata = false
  } = settings

  const extension = musicInfo.fileExtension || '.mp3'
  let filename
  if (filenameFormat === 'artist-song') {
    filename = `${musicInfo.artist} - ${musicInfo.name}${extension}`
  } else {
    filename = `${musicInfo.name} - ${musicInfo.artist}${extension}`
  }

  try {
    // 流式下载
    const audioBlob = await streamDownload(musicInfo.url, onProgress)
    let audioBuffer = await audioBlob.arrayBuffer()

    if (writeMetadata && (extension === '.mp3' || extension === '.flac')) {
      try {
        const metadata = {
          name: musicInfo.name,
          artist: musicInfo.artist,
          album: musicInfo.album,
          year: new Date().getFullYear().toString(),
          lyrics: musicInfo.lrc,
          cover: musicInfo.cover
        }
        audioBuffer = await embedMetadata(audioBuffer, metadata, extension)
      } catch {
        // 元数据写入失败，但下载继续
      }
    }

    const mime = audioBlob.type || getMimeByExtension(extension)
    const typedBlob = ensureBlobType(new Blob([audioBuffer], { type: mime }), mime)
    saveBlob(typedBlob, sanitizeFilename(filename))

    return true
  } catch (error) {
    throw new Error(`下载失败: ${error.message}`)
  }
}

// 获取歌单详情
export const getPlaylistDetail = async (url) => {
  try {
    const playlistId = await extractIdFromUrl(url)
    if (!playlistId) {
      throw new Error('无法从链接中提取歌单ID')
    }

    const response = await fetch('/playlist', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `id=${playlistId}&limit=100`
    })

    const result = await response.json()
    
    if (result.success && result.data) {
      const playlist = result.data.playlist || result.data
      // 后端返回的字段：id, name, cover, description, play_count, source, tracks[]
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
    } else {
      return {
        success: false,
        error: result.message || '获取歌单信息失败'
      }
    }
  } catch (error) {
    return {
      success: false,
      error: `网络请求失败: ${error.message || '未知错误'}`
    }
  }
}

// 获取专辑详情（后端暂未实现，返回空结果）
export const getAlbumDetail = async (url) => {
  console.warn('获取专辑详情功能暂未实现')
  return {
    success: false,
    error: '获取专辑详情功能暂未实现'
  }
}

// 搜索音乐（支持多数据源）
export const searchMusic = async (keyword, sources = ['netease']) => {
  try {
    console.log('searchMusic called with keyword:', keyword, 'sources:', sources)
    console.log('sources type:', typeof sources, 'isArray:', Array.isArray(sources))
    
    // 检查缓存
    const cacheKey = `${keyword}-${sources.join(',')}`
    console.log('cacheKey:', cacheKey)
    const cached = getCachedSearchResult('music', cacheKey)
    if (cached) {
      console.log('Using cached result, data:', cached)
      return { success: true, data: cached, fromCache: true }
    }
    console.log('No cache found, making API request')
    
    // 构建请求数据
    const requestData = { keyword, limit: 60 }
    
    // 如果不是全部数据源，指定source参数
    if (sources.length === 1) {
      requestData.source = sources[0]
      console.log('Setting source to:', sources[0])
    }
    
    console.log('Sending request:', JSON.stringify(requestData, null, 2))
    console.log('Request body:', JSON.stringify(requestData))

    const response = await fetch('/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)
    })
    
    const result = await response.json()
    console.log('API response:', result)
    console.log('API response data length:', result.data?.length)
    
    if (result.success && result.data) {
      // 后端返回的字段：id, name, artists, album, picUrl, duration, source
      const songs = result.data.map(song => ({
        id: song.id,
        name: song.name,
        artists: song.artists || song.artist_string || '',
        album: song.album || '',
        duration: song.duration || 0,
        picUrl: song.picUrl || '',
        source: song.source || 'netease'
      }))
      
      const searchData = { songs }
      
      // 缓存结果
      setCachedSearchResult('music', cacheKey, searchData)
      
      return {
        success: true,
        data: searchData
      }
    } else {
      console.log('API returned error:', result)
      return {
        success: false,
        error: result.message || '搜索失败'
      }
    }
  } catch (error) {
    console.log('API catch error:', error)
    return {
      success: false,
      error: error.message || '搜索失败'
    }
  }
}

// 搜索歌单（支持多数据源）
export const searchPlaylist = async (keyword, sources = ['netease']) => {
  try {
    // 检查缓存
    const cacheKey = `${keyword}-${sources.join(',')}`
    const cached = getCachedSearchResult('playlist', cacheKey)
    if (cached) {
      return { success: true, data: cached, fromCache: true }
    }

    // 构建请求数据
    const requestData = { keyword, limit: 20 }
    
    // 如果不是全部数据源，指定source参数
    if (sources.length === 1) {
      requestData.source = sources[0]
    }

    const response = await fetch('/search/playlist', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)
    })
    
    const result = await response.json()
    
    if (result.success && result.data) {
      // 后端返回的字段：id, name, cover, description, play_count, source
      const playlists = result.data.map(playlist => ({
        id: playlist.id,
        name: playlist.name,
        coverImgUrl: playlist.cover || playlist.coverImgUrl || '',
        description: playlist.description || '',
        playCount: playlist.play_count || playlist.playCount || 0,
        trackCount: playlist.track_count || playlist.trackCount || 0,
        source: playlist.source || 'netease'
      }))
      
      // 缓存结果
      setCachedSearchResult('playlist', cacheKey, playlists)
      
      return {
        success: true,
        data: playlists
      }
    } else {
      return {
        success: false,
        error: result.message || '搜索失败'
      }
    }
  } catch (error) {
    return {
      success: false,
      error: error.message || '搜索失败'
    }
  }
}

// 搜索专辑（后端暂未实现，返回空结果）
export const searchAlbum = async (keyword, sources = ['netease']) => {
  console.warn('搜索专辑功能暂未实现')
  return {
    success: true,
    data: []
  }
}

// 搜索歌手（后端暂未实现，返回空结果）
export const searchArtist = async (keyword) => {
  console.warn('搜索歌手功能暂未实现')
  return {
    success: true,
    data: []
  }
}

// 批量下载音乐（打包为ZIP）
export const batchDownloadMusic = async (musicList, playlistName = '', settings = {}, onProgress = null) => {
  const results = []
  const total = musicList.length
  let completed = 0
  let failed = 0
  let totalBytes = 0
  let downloadedBytes = 0
  const startTime = Date.now()
  const activeDownloads = new Map() // trackId -> { name, downloaded, total }

  try {
    // 导入 JSZip
    const JSZip = (await import('jszip')).default
    const zip = new JSZip()

    // 动态并发控制：根据文件大小和网络状况调整
    const maxConcurrency = 12 // 最多12个并发下载
    const getDynamicConcurrency = () => {
      const activeCount = activeDownloads.size
      // 如果网络不好或文件太大，减少并发
      if (activeCount >= maxConcurrency) return 0
      if (activeCount >= maxConcurrency - 3) return 1
      return Math.min(3, maxConcurrency - activeCount)
    }

    const sendProgress = () => {
      if (!onProgress) return
      
      const elapsed = (Date.now() - startTime) / 1000
      const speed = elapsed > 0 ? downloadedBytes / elapsed / 1024 : 0 // KB/s
      const remainingBytes = totalBytes - downloadedBytes
      const eta = speed > 0 ? Math.ceil(remainingBytes / speed / 1024) : 0 // 秒
      const overallPercentage = totalBytes > 0 
        ? Math.round((downloadedBytes / totalBytes) * 100) 
        : Math.round(((completed + failed) / total) * 100)

      onProgress({
        total,
        completed,
        failed,
        totalBytes,
        downloadedBytes,
        percentage: overallPercentage,
        speed: speed.toFixed(1),
        eta,
        activeDownloads: Array.from(activeDownloads.values())
      })
    }

    // 预获取文件大小
    const fetchSizes = async () => {
      const sizePromises = musicList.map(async (info) => {
        try {
          const headResponse = await fetch(info.url, { method: 'HEAD' })
          return parseInt(headResponse.headers.get('Content-Length') || '0', 10)
        } catch {
          return 0
        }
      })
      const sizes = await Promise.all(sizePromises)
      totalBytes = sizes.reduce((sum, s) => sum + s, 0)
    }

    await fetchSizes()
    sendProgress()

    // 并发下载队列
    const downloadQueue = []
    let queueIndex = 0

    const runDownload = async (musicInfo) => {
      const trackId = musicInfo.id
      activeDownloads.set(trackId, { 
        name: musicInfo.name, 
        downloaded: 0, 
        total: 0,
        status: 'downloading'
      })

      try {
        const extension = musicInfo.fileExtension || '.mp3'
        const sanitizedName = musicInfo.name.replace(/[<>:"/\\|?*]/g, '_')
        const sanitizedArtist = musicInfo.artist.replace(/[<>:"/\\|?*]/g, '_')
        
        let filename
        if (settings.filenameFormat === 'artist-song') {
          filename = `${sanitizedArtist} - ${sanitizedName}${extension}`
        } else {
          filename = `${sanitizedName} - ${sanitizedArtist}${extension}`
        }

        // 流式下载
        const response = await fetch(musicInfo.url, { cache: 'no-store', mode: 'cors' })
        if (!response.ok) {
          throw new Error(`下载失败: ${response.statusText}`)
        }

        const contentLength = parseInt(response.headers.get('Content-Length') || '0', 10)
        const reader = response.body.getReader()
        const chunks = []
        let localDownloaded = 0

        activeDownloads.set(trackId, { 
          name: musicInfo.name, 
          downloaded: 0, 
          total: contentLength,
          status: 'downloading'
        })

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          chunks.push(value)
          localDownloaded += value.length
          downloadedBytes += value.length

          activeDownloads.set(trackId, { 
            name: musicInfo.name, 
            downloaded: localDownloaded, 
            total: contentLength,
            status: 'downloading'
          })
          sendProgress()
        }

        const audioBlob = new Blob(chunks)
        let audioBuffer = await audioBlob.arrayBuffer()

        // 写入元数据（如果启用）
        if (settings.writeMetadata && (extension === '.mp3' || extension === '.flac')) {
          try {
            const metadata = {
              name: musicInfo.name,
              artist: musicInfo.artist,
              album: musicInfo.album,
              year: new Date().getFullYear().toString(),
              lyrics: musicInfo.lrc,
              cover: musicInfo.cover
            }
            audioBuffer = await embedMetadata(audioBuffer, metadata, extension)
          } catch (metaError) {
            console.warn(`元数据写入失败: ${musicInfo.name}`, metaError)
          }
        }

        // 添加到 ZIP
        zip.file(filename, audioBuffer)

        // 如果启用了独立LRC文件下载且有歌词，添加到 ZIP
        if (settings.downloadLrcFile !== false && musicInfo.lrc) {
          const lrcFilename = filename.replace(extension, '.lrc')
          zip.file(lrcFilename, musicInfo.lrc)
        }

        activeDownloads.set(trackId, { 
          name: musicInfo.name, 
          downloaded: contentLength, 
          total: contentLength,
          status: 'completed'
        })
        completed++
        sendProgress()

        return {
          success: true,
          name: musicInfo.name,
          id: musicInfo.id
        }
      } catch (error) {
        activeDownloads.set(trackId, { 
          name: musicInfo.name, 
          downloaded: 0, 
          total: 0,
          status: 'failed',
          error: error.message
        })
        failed++
        sendProgress()

        return {
          success: false,
          name: musicInfo.name,
          id: musicInfo.id,
          error: error.message
        }
      } finally {
        activeDownloads.delete(trackId)
      }
    }

    // 启动并发下载
    const processQueue = async () => {
      while (queueIndex < musicList.length) {
        // 控制并发数
        while (activeDownloads.size >= maxConcurrency && queueIndex < musicList.length) {
          await new Promise(resolve => setTimeout(resolve, 100))
        }

        if (queueIndex >= musicList.length) break

        const batchSize = getDynamicConcurrency()
        const batch = musicList.slice(queueIndex, queueIndex + batchSize)
        queueIndex += batchSize

        const batchPromises = batch.map(musicInfo => runDownload(musicInfo))
        const batchResults = await Promise.all(batchPromises)
        results.push(...batchResults)
      }
    }

    await processQueue()

    // 生成 ZIP 文件并下载
    if (completed > 0) {
      // 更新进度为打包中
      if (onProgress) {
        onProgress({
          ...(onProgress instanceof Function ? {} : onProgress),
          status: 'packing',
          message: '正在打包 ZIP 文件...'
        })
      }

      const content = await zip.generateAsync({ type: 'blob' })
      const zipFilename = playlistName 
        ? `${playlistName.replace(/[<>:"/\\|?*]/g, '_')}.zip`
        : `music_${new Date().getTime()}.zip`
      
      // 触发下载
      const url = URL.createObjectURL(content)
      const a = document.createElement('a')
      a.href = url
      a.download = zipFilename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    return {
      total,
      completed,
      failed,
      results
    }
  } catch (error) {
    throw new Error(`批量下载失败: ${error.message}`)
  }
}

export default {
  validateUrl,
  validateMusicUrl,
  validatePlaylistUrl,
  validateAlbumUrl,
  extractIdFromUrl,
  getMusicIdFromUrl,
  extractPlaylistId,
  extractAlbumId,
  parseMusicInfo,
  getLyrics,
  downloadMusic,
  batchDownloadMusic,
  getPlaylistDetail,
  getAlbumDetail,
  searchMusic,
  searchPlaylist,
  searchAlbum,
  searchArtist
}
