/**
 * 网易云音乐API Node.js后端服务
 * 使用Express提供API接口，代理访问网易云音乐API
 * 支持Cookie认证
 */

import express from 'express'
import cors from 'cors'
import axios from 'axios'
import { NodeCrypto } from './server-crypto.js'
import cookieManager from './server-cookie.js'

const app = express()
const PORT = 3000
const BASE_URL = 'https://interface3.music.163.com'

const API_CONSTANTS = {
  USER_AGENT: 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154',
  REFERER: 'https://music.163.com/',
  SONG_URL_V1: '/eapi/song/enhance/player/url/v1',
  SONG_DETAIL_V3: '/api/v3/song/detail',
  LYRIC_API: '/api/song/lyric',
  SEARCH_API: '/api/cloudsearch/pc',
  PLAYLIST_DETAIL_API: '/api/v6/playlist/detail',
  ALBUM_DETAIL_API: '/api/v1/album/'
}

// 初始化Cookie
console.log('📋 Cookie管理器初始化...')
const cookieInfo = cookieManager.getCookieInfo()
if (cookieInfo.valid) {
  console.log(`✅ Cookie有效，包含 ${cookieInfo.cookieCount} 个字段`)
} else {
  console.warn(`⚠️ Cookie无效或缺失，可能无法获取VIP歌曲`)
  if (cookieInfo.missingCookies.length > 0) {
    console.warn(`缺少: ${cookieInfo.missingCookies.join(', ')}`)
  }
}

app.use(cors())
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

// 通用请求方法（支持Cookie）
async function neteaseRequest(endpoint, data, isEapi = false, useCookie = true) {
  const url = `${BASE_URL}${endpoint}`

  const headers = {
    'User-Agent': API_CONSTANTS.USER_AGENT,
    'Referer': API_CONSTANTS.REFERER,
    'Content-Type': 'application/x-www-form-urlencoded'
  }

  try {
    if (isEapi) {
      // EAPI加密
      const params = await NodeCrypto.encryptParams(url, data)
      const requestData = { params }

      // 添加Cookie
      if (useCookie) {
        const cookies = cookieManager.getCookies()
        if (Object.keys(cookies).length > 0) {
          requestData.cookies = cookies
          console.log(`📡 EAPI请求（带Cookie）: ${endpoint}`)
        } else {
          console.warn(`⚠️ EAPI请求（无Cookie）: ${endpoint}`)
        }
      }

      const response = await axios.post(url, requestData, { headers, timeout: 30000 })
      console.log('📊 EAPI响应类型:', typeof response.data, '内容:', response.data)
      return response.data
    } else {
      // 普通API
      const requestData = new URLSearchParams(data).toString()

      // 添加Cookie
      if (useCookie) {
        const cookies = cookieManager.getCookies()
        if (Object.keys(cookies).length > 0) {
          headers['Cookie'] = cookieManager.getCookieString()
          console.log(`📡 API请求（带Cookie）: ${endpoint}`)
        } else {
          console.warn(`⚠️ API请求（无Cookie）: ${endpoint}`)
        }
      }

      const response = await axios.post(url, requestData, { headers, timeout: 30000 })
      return response.data
    }
  } catch (error) {
    console.error(`❌ API请求失败 [${endpoint}]:`, error.message)
    throw error
  }
}

// 首页
app.get('/', (req, res) => {
  res.json({
    service: '网易云音乐API',
    status: 'running',
    version: '1.0.0',
    endpoints: [
      'GET /health - 健康检查',
      'POST /api/song - 获取歌曲信息',
      'POST /api/song/url - 获取歌曲播放URL',
      'POST /api/search - 搜索音乐',
      'POST /api/playlist - 获取歌单详情',
      'POST /api/album - 获取专辑详情',
      'POST /api/lyric - 获取歌词'
    ]
  })
})

// 健康检查
app.get('/health', (req, res) => {
  const cookieInfo = cookieManager.getCookieInfo()
  res.json({
    service: 'running',
    timestamp: Date.now(),
    status: 'ok',
    cookie: cookieInfo
  })
})

// 获取歌曲信息
app.post('/api/song', async (req, res) => {
  try {
    const { ids, id, level = 'lossless' } = req.body

    let songId = ids || id
    if (!songId) {
      return res.status(400).json({
        success: false,
        message: '缺少歌曲ID参数'
      })
    }

    // 如果是数组，取第一个
    if (Array.isArray(songId)) {
      songId = songId[0]
    }

    const result = await neteaseRequest(
      API_CONSTANTS.SONG_DETAIL_V3,
      { c: JSON.stringify([{ id: songId, v: 0 }]) }
    )

    res.json({
      success: true,
      data: result
    })
  } catch (error) {
    console.error('获取歌曲信息失败:', error)
    res.status(500).json({
      success: false,
      message: error.response?.data?.message || error.message || '获取歌曲信息失败'
    })
  }
})

// 获取歌曲URL
app.post('/api/song/url', async (req, res) => {
  try {
    const { ids, level = 'lossless' } = req.body

    if (!ids) {
      return res.status(400).json({
        success: false,
        message: '缺少歌曲ID参数'
      })
    }

    const songId = Array.isArray(ids) ? ids[0] : ids

    const config = {
      os: 'pc',
      appver: '',
      osver: '',
      deviceId: 'pyncm!',
      requestId: String(Math.floor(Math.random() * 10000000) + 20000000)
    }

    const payload = {
      ids: [songId],
      level: level,
      encodeType: 'flac',
      header: JSON.stringify(config)
    }

    const result = await neteaseRequest(
      API_CONSTANTS.SONG_URL_V1,
      payload,
      true // 使用EAPI加密
    )

    console.log('📊 EAPI响应:', JSON.stringify(result)?.substring(0, 200))

    res.json({
      success: true,
      data: result
    })
  } catch (error) {
    console.error('获取歌曲URL失败:', error)
    res.status(500).json({
      success: false,
      message: error.response?.data?.message || error.message || '获取歌曲URL失败'
    })
  }
})

// 搜索音乐
app.post('/api/search', async (req, res) => {
  try {
    const { keyword, keywords, limit = 10 } = req.body

    const query = keyword || keywords
    if (!query) {
      return res.status(400).json({
        success: false,
        message: '缺少搜索关键词'
      })
    }

    const result = await neteaseRequest(
      API_CONSTANTS.SEARCH_API,
      {
        s: query,
        type: 1,
        limit: limit,
        offset: 0,
        total: true
      }
    )

    res.json({
      success: true,
      data: result
    })
  } catch (error) {
    console.error('搜索失败:', error)
    res.status(500).json({
      success: false,
      message: error.response?.data?.message || error.message || '搜索失败'
    })
  }
})

// 获取歌单详情
app.post('/api/playlist', async (req, res) => {
  try {
    const { id } = req.body

    if (!id) {
      return res.status(400).json({
        success: false,
        message: '缺少歌单ID'
      })
    }

    const result = await neteaseRequest(
      API_CONSTANTS.PLAYLIST_DETAIL_API,
      { id: id, n: 1000000, s: 0 }
    )

    res.json({
      success: true,
      data: result
    })
  } catch (error) {
    console.error('获取歌单详情失败:', error)
    res.status(500).json({
      success: false,
      message: error.response?.data?.message || error.message || '获取歌单详情失败'
    })
  }
})

// 获取专辑详情
app.post('/api/album', async (req, res) => {
  try {
    const { id } = req.body

    if (!id) {
      return res.status(400).json({
        success: false,
        message: '缺少专辑ID'
      })
    }

    const result = await neteaseRequest(
      `${API_CONSTANTS.ALBUM_DETAIL_API}${id}`,
      {}
    )

    res.json({
      success: true,
      data: result
    })
  } catch (error) {
    console.error('获取专辑详情失败:', error)
    res.status(500).json({
      success: false,
      message: error.response?.data?.message || error.message || '获取专辑详情失败'
    })
  }
})

// 获取歌词
app.post('/api/lyric', async (req, res) => {
  try {
    const { id } = req.body

    if (!id) {
      return res.status(400).json({
        success: false,
        message: '缺少歌曲ID'
      })
    }

    const result = await neteaseRequest(
      API_CONSTANTS.LYRIC_API,
      {
        id: id,
        cp: 'false',
        tv: '0',
        lv: '0',
        rv: '0',
        kv: '0',
        yv: '0',
        ytv: '0',
        yrv: '0'
      }
    )

    res.json({
      success: true,
      data: result
    })
  } catch (error) {
    console.error('获取歌词失败:', error)
    res.status(500).json({
      success: false,
      message: error.response?.data?.message || error.message || '获取歌词失败'
    })
  }
})

// 通用的EAPI和API路由代理（处理前端直接调用）
// 使用中间件方式捕获所有请求
app.use('/eapi', express.json(), express.urlencoded({ extended: true }), async (req, res) => {
  try {
    const path = req.path
    const apiPath = `/eapi${path}`
    console.log(`代理EAPI请求: ${apiPath}`)

    const payload = req.body
    const result = await neteaseRequest(apiPath, payload, true)

    res.json(result)
  } catch (error) {
    console.error(`EAPI请求失败:`, error)
    res.status(500).json({
      success: false,
      message: error.message || 'API请求失败'
    })
  }
})

app.use('/api', express.json(), express.urlencoded({ extended: true }), async (req, res) => {
  try {
    const path = req.path
    const apiPath = `/api${path}`
    console.log(`代理API请求: ${apiPath}`)

    const payload = req.body
    const result = await neteaseRequest(apiPath, payload, false)

    res.json(result)
  } catch (error) {
    console.error(`API请求失败:`, error)
    res.status(500).json({
      success: false,
      message: error.message || 'API请求失败'
    })
  }
})

// 启动服务器
app.listen(PORT, '0.0.0.0', () => {
  console.log('🎵 网易云音乐API服务已启动')
  console.log(`📡 服务地址: http://localhost:${PORT}`)
  console.log(`📖 API文档: http://localhost:${PORT}/`)
})

export default app
