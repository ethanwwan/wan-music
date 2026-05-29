/**
 * 音乐API服务
 * 使用纯JavaScript实现的网易云音乐API，无需后端
 */

import { embedMetadata } from './metadataWriter.js'
import { saveBlob, ensureBlobType, getMimeByExtension, sanitizeFilename } from '../utils/downloadHelper.js'
import { settings } from '../utils/settingsManager.js'
import { NeteaseAPI } from './neteaseApi.js'

const neteaseApi = new NeteaseAPI()

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
    const result = await neteaseApi.getSongUrl(musicId, quality)
    
    if (result.code !== 200) {
      throw new Error(result.message || '获取音乐链接失败')
    }

    const urlData = result.data?.[0]
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
        musicInfo.lrc = lyricsResult.lrc
        musicInfo.tlyric = lyricsResult.tlyric || ''
        musicInfo.romalrc = lyricsResult.romalrc || ''
        musicInfo.klyric = lyricsResult.klyric || ''
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

    const result = await neteaseApi.getPlaylistDetail(playlistId)
    
    if (result.code === 200) {
      return {
        success: true,
        data: result.playlist
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
    
    const result = await neteaseApi.getAlbumDetail(albumId)
    
    if (result.code === 200) {
      return {
        success: true,
        data: result
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
    const songs = await neteaseApi.searchMusic(keyword)
    
    if (songs && songs.length > 0) {
      return {
        success: true,
        data: {
          songs: songs.map(song => ({
            id: song.id,
            name: song.name,
            artists: song.artists || [],
            album: song.album || {},
            duration: song.duration || 0
          }))
        }
      }
    } else {
      return {
        success: false,
        error: '搜索结果为空'
      }
    }
  } catch (error) {
    return {
      success: false,
      error: error.message || '搜索失败'
    }
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
  getPlaylistDetail,
  getAlbumDetail,
  searchMusic
}
