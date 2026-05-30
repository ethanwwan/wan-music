/**
 * 统一API客户端
 * 所有前端API调用都通过这里，代理到Python后端服务器
 */

const API_BASE = '' // Vite代理会处理

export const frontendApi = {
  /**
   * 获取歌曲详情和URL（Python后端Song_V1）
   */
  async getSongInfo(id, quality = 'standard') {
    try {
      const response = await fetch(`${API_BASE}/Song_V1`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          ids: id,
          level: quality,
          type: 'json'
        })
      })
      const data = await response.json()
      return data
    } catch (error) {
      console.error('getSongInfo error:', error)
      throw error
    }
  },

  /**
   * 获取歌曲详情（从API）
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
   * 健康检查
   */
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE}/health`)
      const data = await response.json()
      return data
    } catch (error) {
      console.error('healthCheck error:', error)
      throw error
    }
  }
}

export default frontendApi
