/**
 * 网易云音乐 API 服务
 * 纯 JavaScript 实现，无需后端
 */

import { CryptoUtils, APIConstants } from './crypto.js'

class APIException extends Error {
  constructor(message) {
    super(message)
    this.name = 'APIException'
  }
}

export class NeteaseAPI {
  constructor() {
    this.cryptoUtils = CryptoUtils
  }

  /**
   * 生成随机请求 ID
   */
  generateRequestId() {
    return Math.floor(Math.random() * 10000000) + 20000000
  }

  /**
   * 发送 POST 请求
   * 使用相对路径，通过Vite代理转发到Express服务器
   */
  async postRequest(url, data = {}, headers = {}) {
    const defaultHeaders = {
      'User-Agent': APIConstants.USER_AGENT,
      'Referer': APIConstants.REFERER,
      'Content-Type': 'application/x-www-form-urlencoded'
    }

    try {
      // 使用相对路径，让Vite代理处理
      const fullUrl = url.startsWith('/') ? url : `/${url}`

      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: { ...defaultHeaders, ...headers },
        body: new URLSearchParams(data).toString(),
        credentials: 'include'
      })

      if (!response.ok) {
        throw new APIException(`HTTP Error: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof APIException) {
        throw error
      }
      throw new APIException(`Network Error: ${error.message}`)
    }
  }

  /**
   * 获取歌曲播放 URL
   */
  async getSongUrl(songId, quality = 'lossless', cookies = {}) {
    try {
      const config = { ...APIConstants.DEFAULT_CONFIG }
      config.requestId = String(this.generateRequestId())

      const payload = {
        ids: [songId],
        level: quality,
        encodeType: 'flac',
        header: JSON.stringify(config)
      }

      if (quality === 'sky') {
        payload.immerseType = 'c51'
      }

      const params = await this.cryptoUtils.encryptParams(
        APIConstants.SONG_URL_V1,
        payload
      )

      const result = await this.postRequest(
        APIConstants.SONG_URL_V1,
        { params },
        cookies
      )

      if (result.code !== 200) {
        throw new APIException(result.message || '获取歌曲URL失败')
      }

      return result
    } catch (error) {
      console.error('getSongUrl error:', error)
      throw error
    }
  }

  /**
   * 获取歌曲详情
   */
  async getSongDetail(songId) {
    try {
      const data = {
        c: JSON.stringify([{ id: songId, v: 0 }])
      }

      const result = await this.postRequest(
        APIConstants.SONG_DETAIL_V3,
        data
      )

      if (result.code !== 200) {
        throw new APIException(result.message || '获取歌曲详情失败')
      }

      return result
    } catch (error) {
      console.error('getSongDetail error:', error)
      throw error
    }
  }

  /**
   * 获取歌词
   */
  async getLyric(songId, cookies = {}, retryCount = 3) {
    let lastError = null
    
    for (let i = 0; i < retryCount; i++) {
      try {
        const data = {
          id: songId,
          cp: 'false',
          tv: '0',
          lv: '0',
          rv: '0',
          kv: '0',
          yv: '0',
          ytv: '0',
          yrv: '0'
        }

        const result = await this.postRequest(
          APIConstants.LYRIC_API,
          data,
          cookies
        )

        if (result.code !== 200) {
          throw new APIException(result.message || '获取歌词失败')
        }

        return result
      } catch (error) {
        lastError = error
        console.warn(`getLyric attempt ${i + 1} failed:`, error.message)
        
        if (i < retryCount - 1) {
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000))
        }
      }
    }
    
    console.error('getLyric error after retries:', lastError)
    throw lastError
  }

  /**
   * 搜索音乐
   */
  async searchMusic(keywords, cookies = {}, limit = 10) {
    try {
      const data = {
        s: keywords,
        type: 1,
        limit: limit
      }

      const result = await this.postRequest(
        APIConstants.SEARCH_API,
        data,
        cookies
      )

      if (result.code !== 200) {
        throw new APIException(result.message || '搜索失败')
      }

      const songs = []
      for (const item of result.result?.songs || []) {
        songs.push({
          id: item.id,
          name: item.name,
          artists: item.ar.map(a => a.name).join('/'),
          album: item.al.name,
          picUrl: item.al.picUrl
        })
      }

      return songs
    } catch (error) {
      console.error('searchMusic error:', error)
      throw error
    }
  }

  /**
   * 获取歌单详情
   */
  async getPlaylistDetail(playlistId, cookies = {}) {
    try {
      const data = { id: playlistId }

      const result = await this.postRequest(
        APIConstants.PLAYLIST_DETAIL_API,
        data,
        cookies
      )

      if (result.code !== 200) {
        throw new APIException(result.message || '获取歌单详情失败')
      }

      const playlist = result.playlist
      return {
        id: playlist.id,
        name: playlist.name,
        coverImgUrl: playlist.coverImgUrl,
        creator: playlist.creator?.nickname || '',
        trackCount: playlist.trackCount,
        playCount: playlist.playCount,
        tracks: playlist.tracks || []
      }
    } catch (error) {
      console.error('getPlaylistDetail error:', error)
      throw error
    }
  }

  /**
   * 获取专辑详情
   */
  async getAlbumDetail(albumId, cookies = {}) {
    try {
      const result = await this.postRequest(
        `${APIConstants.ALBUM_DETAIL_API}${albumId}`,
        {},
        cookies
      )

      if (result.code !== 200) {
        throw new APIException(result.message || '获取专辑详情失败')
      }

      return {
        id: result.album.id,
        name: result.album.name,
        artist: result.album.artist?.name || '',
        coverUrl: result.album.picUrl,
        publishTime: result.album.publishTime,
        tracks: result.songs || []
      }
    } catch (error) {
      console.error('getAlbumDetail error:', error)
      throw error
    }
  }

  /**
   * 获取单曲详情
   */
  async getSingleSongDetail(songId, cookies = {}) {
    try {
      const songDetail = await this.getSongDetail(songId)
      const detail = songDetail.songs?.[0]

      if (!detail) {
        throw new APIException('未找到歌曲详情')
      }

      return {
        id: detail.id,
        name: detail.name,
        artists: detail.ar?.map(a => a.name).join('/') || '',
        album: detail.al?.name || '',
        albumId: detail.al?.id,
        picUrl: detail.al?.picUrl || '',
        duration: detail.dt || 0,
        alias: detail.alia || []
      }
    } catch (error) {
      console.error('getSingleSongDetail error:', error)
      throw error
    }
  }
}

export default new NeteaseAPI()
