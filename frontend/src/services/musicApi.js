/**
 * 音乐API服务
 * 使用纯JavaScript实现的网易云音乐API，无需后端
 */

import { embedMetadata } from './metadataWriter.js'
import { saveBlob, ensureBlobType, getMimeByExtension, sanitizeFilename } from '../utils/downloadHelper.js'
import { settings } from '../utils/settingsManager.js'
import { NeteaseAPI } from './neteaseApi.js'

const neteaseApi = new NeteaseAPI()

// 搜索缓存
const searchCache = {
  music: new Map(),
  playlist: new Map(),
  album: new Map()
}

// 检查缓存是否有效
const isCacheValid = (cacheEntry, ttlMinutes) => {
  if (!cacheEntry) return false
  const now = Date.now()
  const cacheTime = cacheEntry.timestamp
  return (now - cacheTime) < (ttlMinutes * 60 * 1000)
}

// 获取缓存数据
const getCachedSearchResult = (type, keyword) => {
  if (!settings.enableCache) return null
  
  const cache = searchCache[type]
  if (!cache) return null
  
  const cached = cache.get(keyword)
  if (isCacheValid(cached, settings.cacheTTLMinutes || 15)) {
    console.log(`使用缓存的${type}搜索结果: ${keyword}`)
    return cached.data
  }
  
  // 缓存过期，删除
  if (cached) {
    cache.delete(keyword)
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

// 统一的ID提取函数
export const extractIdFromUrl = async (text) => {
  try {
    if (!text) return null
    if (typeof text !== 'string') {
      text = String(text)
    }
    
    const url = extractUrlFromText(text)
    if (!url) return null
    
    // 短链接模式
    if (/https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/.test(url)) {
      return url
    }

    // 音乐链接模式
    const musicPatterns = [
      /https?:\/\/music\.163\.com\/song\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/song\?id=(\d+)/
    ]
    
    // 歌单链接模式
    const playlistPatterns = [
      /https?:\/\/music\.163\.com\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\/(\d+)/,
      /https?:\/\/music\.163\.com\/#\/playlist\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/discover\/toplist\?id=(\d+)/
    ]

    // 专辑链接模式
    const albumPatterns = [
      /https?:\/\/music\.163\.com\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/album\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\/(\d+)/
    ]
    
    for (const pattern of [...musicPatterns, ...playlistPatterns, ...albumPatterns]) {
      const match = url.match(pattern)
      if (match) {
        return match[1]
      }
    }
    
    return null
  } catch {
    return null
  }
}

// 验证链接格式
export const validateUrl = (url) => {
  try {
    if (!url || typeof url !== 'string') {
      return false
    }
    
    const patterns = [
      /https?:\/\/music\.163\.com\/song\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/song\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\/(\d+)/,
      /https?:\/\/music\.163\.com\/#\/playlist\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/discover\/toplist\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/album\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\/(\d+)/,
      /https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/
    ]
    
    return patterns.some(pattern => pattern.test(url))
  } catch {
    return false
  }
}

export const validateMusicUrl = (url) => {
  try {
    const patterns = [
      /https?:\/\/music\.163\.com\/song\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/song\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/song\?id=(\d+)/,
      /https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/
    ]
    return patterns.some(p => p.test(url))
  } catch {
    return false
  }
}

export const validatePlaylistUrl = (url) => {
  try {
    const patterns = [
      /https?:\/\/music\.163\.com\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/playlist\/(\d+)/,
      /https?:\/\/music\.163\.com\/#\/playlist\?id=(\d+)/,
      /https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/
    ]
    return patterns.some(p => p.test(url))
  } catch {
    return false
  }
}

export const validateAlbumUrl = (url) => {
  try {
    const patterns = [
      /https?:\/\/music\.163\.com\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/album\/(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/album\?id=(\d+)/,
      /https?:\/\/y\.music\.163\.com\/m\/album\/(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\?id=(\d+)/,
      /https?:\/\/music\.163\.com\/#\/album\/(\d+)/,
      /https?:\/\/163cn\.tv\/([a-zA-Z0-9]+)/
    ]
    return patterns.some(p => p.test(url))
  } catch {
    return false
  }
}

export const getMusicIdFromUrl = extractIdFromUrl
export const extractPlaylistId = extractIdFromUrl
export const extractAlbumId = extractIdFromUrl

// 音质等级映射
export const QUALITY_LEVELS = {
  'jymaster': '超清母带(Master)',
  'dolby': '杜比全景声(Dolby Atmos)',
  'sky': '沉浸环绕声(Surround Audio)',
  'jyeffect': '高清臻音(Spatial Audio)',
  'hires': '高清晰度无损(Hi-Res)',
  'lossless': '无损(SQ)',
  'exhigh': '极高(HQ)',
  'standard': '标准(128k)'
}

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

// 解析音乐信息
export const parseMusicInfo = async (url, quality = 'lossless') => {
  try {
    const musicId = await extractIdFromUrl(url)
    if (!musicId) {
      throw new Error('无法从链接中提取歌曲ID')
    }

    // 获取歌曲基本信息
    const detailResult = await neteaseApi.getSongDetail(musicId)
    
    if (detailResult.code !== 200) {
      throw new Error(detailResult.message || '获取歌曲信息失败')
    }

    const songData = detailResult.songs?.[0]
    if (!songData) {
      throw new Error('未找到歌曲详情')
    }

    // 获取音乐播放链接
    let musicUrl = null
    let actualQuality = quality
    let fileSize = 0
    let bitRate = 0
    let fileType = 'mp3'

    try {
      const urlData = await getMusicUrl(musicId, quality)
      if (urlData && urlData.url) {
        musicUrl = urlData.url
        actualQuality = urlData.level || quality
        fileSize = urlData.size || 0
        bitRate = urlData.br || 0
        
        if (urlData.type) {
          fileType = urlData.type.toLowerCase()
        } else {
          const urlExtensionMatch = musicUrl.match(/\.([a-zA-Z0-9]+)(?=\?|$)/)
          if (urlExtensionMatch && urlExtensionMatch[1]) {
            fileType = urlExtensionMatch[1].toLowerCase()
          } else if (['lossless', 'hires', 'jymaster', 'sky', 'jyeffect'].includes(actualQuality)) {
            fileType = 'flac'
          }
        }
      } else {
        throw new Error('该歌曲已下架或者无法获取')
      }
    } catch {
      throw new Error('该歌曲已下架或者无法获取')
    }

    // 构造返回的音乐信息
    const musicInfo = {
      id: songData.id.toString(),
      name: songData.name,
      artist: songData.ar?.map(a => a.name).join('/') || '',
      album: songData.al?.name || '',
      cover: songData.al?.picUrl || '',
      duration: songData.dt || 0,
      url: musicUrl,
      quality: actualQuality,
      qualityName: QUALITY_LEVELS[actualQuality] || actualQuality,
      fileSize: fileSize,
      bitRate: bitRate,
      lrc: '',
      fileExtension: `.${fileType.toLowerCase()}`
    }

    // 尝试获取歌词
    try {
      const lyricsResult = await neteaseApi.getLyric(musicId)
      if (lyricsResult.code === 200 && lyricsResult.lrc) {
        // 确保 lrc 是字符串格式
        musicInfo.lrc = typeof lyricsResult.lrc === 'string' 
          ? lyricsResult.lrc 
          : (lyricsResult.lrc.lyric || '')
        
        // 确保 tlyric 是字符串格式
        musicInfo.tlyric = typeof lyricsResult.tlyric === 'string'
          ? lyricsResult.tlyric
          : (lyricsResult.tlyric?.lyric || '')
        
        // 其他歌词类型也做同样处理
        musicInfo.romalrc = typeof lyricsResult.romalrc === 'string'
          ? lyricsResult.romalrc
          : (lyricsResult.romalrc?.lyric || '')
        
        musicInfo.klyric = typeof lyricsResult.klyric === 'string'
          ? lyricsResult.klyric
          : (lyricsResult.klyric?.lyric || '')
      }
    } catch {
      // 歌词获取失败不影响主功能
    }

    return musicInfo

  } catch (error) {
    throw new Error(error.message || '解析失败，请检查链接是否正确或稍后重试')
  }
}

// 获取歌词
export const getLyrics = async (musicId) => {
  try {
    if (typeof musicId !== 'string') {
      if (musicId === null || musicId === undefined) {
        throw new Error('歌曲ID不能为空')
      }
      musicId = String(musicId)
    }
    
    const result = await neteaseApi.getLyric(musicId)
    
    if (result.code !== 200) {
      throw new Error(result.message || '获取歌词失败')
    }

    return {
      lrc: result.lrc || '',
      tlyric: result.tlyric || '',
      romalrc: result.romalrc || '',
      klyric: result.klyric || ''
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

// 下载音乐
export const downloadMusic = async (musicInfo, settings = {}) => {
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
    const response = await fetch(musicInfo.url, { cache: 'no-store', mode: 'cors' })
    if (!response.ok) {
      throw new Error(`下载音频文件失败: ${response.statusText}`)
    }
    let audioBuffer = await response.arrayBuffer()

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

    const mime = response.headers.get('Content-Type') || getMimeByExtension(extension)
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
      body: `id=${playlistId}`
    })

    const result = await response.json()
    
    if (result.success) {
      return {
        success: true,
        data: result.data.playlist
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

// 获取专辑详情
export const getAlbumDetail = async (url) => {
  try {
    const albumId = await extractIdFromUrl(url)
    if (!albumId) {
      throw new Error('无法从链接中提取专辑ID')
    }

    const response = await fetch('/album', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `id=${albumId}`
    })

    const result = await response.json()
    
    if (result.success) {
      return {
        success: true,
        data: result.data.album
      }
    } else {
      return {
        success: false,
        error: result.message || '获取专辑信息失败'
      }
    }
  } catch (error) {
    return {
      success: false,
      error: `网络请求失败: ${error.message || '未知错误'}`
    }
  }
}

// 搜索音乐
export const searchMusic = async (keyword) => {
  try {
    // 检查缓存
    const cached = getCachedSearchResult('music', keyword)
    if (cached) {
      return { success: true, data: cached }
    }

    const response = await fetch('/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ keyword })
    })
    
    const result = await response.json()
    
    if (result.success && result.data) {
      const searchData = {
        songs: result.data.map(song => ({
          id: song.id,
          name: song.name,
          artists: song.artists || [],
          album: song.album || {},
          duration: song.duration || 0
        }))
      }
      
      // 缓存结果
      setCachedSearchResult('music', keyword, searchData)
      
      return {
        success: true,
        data: searchData
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

// 搜索歌单
export const searchPlaylist = async (keyword) => {
  try {
    // 检查缓存
    const cached = getCachedSearchResult('playlist', keyword)
    if (cached) {
      return { success: true, data: cached }
    }

    const response = await fetch('/search/playlist', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ keyword })
    })
    
    const result = await response.json()
    
    if (result.success && result.data) {
      const searchData = result.data.map(playlist => ({
        id: playlist.id,
        name: playlist.name,
        creator: playlist.creator || '',
        coverImgUrl: playlist.coverImgUrl || '',
        trackCount: playlist.trackCount || 0
      }))
      
      // 缓存结果
      setCachedSearchResult('playlist', keyword, searchData)
      
      return {
        success: true,
        data: searchData
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

// 搜索专辑
export const searchAlbum = async (keyword) => {
  try {
    // 检查缓存
    const cached = getCachedSearchResult('album', keyword)
    if (cached) {
      return { success: true, data: cached }
    }

    const response = await fetch('/search/album', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ keyword })
    })
    
    const result = await response.json()
    
    if (result.success && result.data) {
      const searchData = result.data.map(album => ({
        id: album.id,
        name: album.name,
        artist: album.artist || '',
        coverImgUrl: album.coverImgUrl || '',
        trackCount: album.trackCount || 0
      }))
      
      // 缓存结果
      setCachedSearchResult('album', keyword, searchData)
      
      return {
        success: true,
        data: searchData
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

// 批量下载音乐（打包为ZIP）
export const batchDownloadMusic = async (musicList, playlistName = '', settings = {}, onProgress = null) => {
  const results = []
  const total = musicList.length
  let completed = 0
  let failed = 0

  try {
    // 导入 JSZip
    const JSZip = (await import('jszip')).default
    const zip = new JSZip()

    // 并发控制，最多同时下载3个
    const concurrency = 3
    
    for (let i = 0; i < musicList.length; i += concurrency) {
      const batch = musicList.slice(i, i + concurrency)
      
      const batchResults = await Promise.allSettled(
        batch.map(async (musicInfo) => {
          try {
            // 下载音频文件
            const response = await fetch(musicInfo.url, { cache: 'no-store', mode: 'cors' })
            if (!response.ok) {
              throw new Error(`下载音频文件失败: ${response.statusText}`)
            }
            let audioBuffer = await response.arrayBuffer()

            // 写入元数据（如果启用）
            const extension = musicInfo.fileExtension || '.mp3'
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
                const { embedMetadata } = await import('./metadataWriter.js')
                audioBuffer = await embedMetadata(audioBuffer, metadata, extension)
              } catch (metaError) {
                console.warn(`元数据写入失败: ${musicInfo.name}`, metaError)
              }
            }

            // 生成文件名
            let filename
            const sanitizedName = musicInfo.name.replace(/[<>:"/\\|?*]/g, '_')
            const sanitizedArtist = musicInfo.artist.replace(/[<>:"/\\|?*]/g, '_')
            if (settings.filenameFormat === 'artist-song') {
              filename = `${sanitizedArtist} - ${sanitizedName}${extension}`
            } else {
              filename = `${sanitizedName} - ${sanitizedArtist}${extension}`
            }

            // 添加到 ZIP
            zip.file(filename, audioBuffer)

            // 如果有歌词，也添加到 ZIP
            if (musicInfo.lrc) {
              const lrcFilename = filename.replace(extension, '.lrc')
              zip.file(lrcFilename, musicInfo.lrc)
            }

            completed++
            if (onProgress) {
              onProgress({
                total,
                completed,
                failed,
                current: musicInfo.name,
                percentage: Math.round((completed + failed) / total * 100)
              })
            }
            return {
              success: true,
              name: musicInfo.name,
              id: musicInfo.id
            }
          } catch (error) {
            failed++
            if (onProgress) {
              onProgress({
                total,
                completed,
                failed,
                current: musicInfo.name,
                percentage: Math.round((completed + failed) / total * 100),
                error: error.message
              })
            }
            return {
              success: false,
              name: musicInfo.name,
              id: musicInfo.id,
              error: error.message
            }
          }
        })
      )
      
      // 收集结果
      batchResults.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          results.push(result.value)
        } else {
          results.push({
            success: false,
            name: batch[index]?.name || '未知歌曲',
            error: result.reason?.message || '下载失败'
          })
        }
      })
    }

    // 生成 ZIP 文件并下载
    if (completed > 0) {
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
  searchAlbum
}
