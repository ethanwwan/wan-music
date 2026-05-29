/**
 * 统一API客户端
 * 所有前端API调用都通过这里，代理到后端服务器
 */

const API_BASE = '' // Vite代理会处理

export const frontendApi = {
  /**
   * 获取歌曲详情
   */
  async getSongDetail(id) {
    try {
      const response = await fetch(`${API_BASE}/api/song`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('getSongDetail error:', error)
      throw error
    }
  },

  /**
   * 获取歌曲URL
   */
  async getSongUrl(id, quality = 'lossless') {
    try {
      const response = await fetch(`${API_BASE}/api/song/url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: [id], level: quality })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('getSongUrl error:', error)
      throw error
    }
  },

  /**
   * 获取歌词
   */
  async getLyric(id) {
    try {
      const response = await fetch(`${API_BASE}/api/lyric`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('getLyric error:', error)
      throw error
    }
  },

  /**
   * 搜索歌曲
   */
  async search(keyword, limit = 30) {
    try {
      const response = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword, limit })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('search error:', error)
      throw error
    }
  },

  /**
   * 获取歌单详情
   */
  async getPlaylist(id) {
    try {
      const response = await fetch(`${API_BASE}/api/playlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('getPlaylist error:', error)
      throw error
    }
  },

  /**
   * 获取专辑详情
   */
  async getAlbum(id) {
    try {
      const response = await fetch(`${API_BASE}/api/album`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('getAlbum error:', error)
      throw error
    }
  },

  /**
   * 健康检查
   */
  async health() {
    try {
      const response = await fetch(`${API_BASE}/health`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('health check error:', error)
      throw error
    }
  }
}

export default frontendApi
