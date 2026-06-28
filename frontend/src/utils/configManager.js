/** 统一配置管理
 *
 * 配置来源：后端 /config 接口（platforms / qualities / filename_formats / platform_quality_support）
 * 缓存策略：localStorage 缓存 24 小时
 * 加载状态：
 *   - config.value === null → 加载中
 *   - config.value === {...} → 加载成功
 *   - 加载失败：使用硬编码兜底配置
 */
import { ref } from 'vue'
import { getConfig } from '../services/musicApi.js'

const CACHE_KEY = 'wan-music-config-cache'
const CACHE_TTL_MS = 24 * 60 * 60 * 1000

// 响应式配置对象（应用启动后由 loadConfig 填充）
export const config = ref(null)

let _loadingPromise = null

// ==================== 硬编码兜底（后端不可用时使用） ====================
const FALLBACK = {
  version: '0.0.0-fallback',
  platforms: [
    { id: 'netease', name: '网易云音乐', color: '#e72d2c', description: '网易云音乐平台' },
    { id: 'qq', name: 'QQ音乐', color: '#31c27c', description: 'QQ音乐平台' },
    { id: 'kugou', name: '酷狗音乐', color: '#2a8eff', description: '酷狗音乐平台' },
    { id: 'kuwo', name: '酷我音乐', color: '#ff6600', description: '酷我音乐平台' },
  ],
  qualities: [
    { value: 'dolby', label: '杜比全景声', description: 'Dolby Atmos', priority: 1, format: 'Dolby Atmos' },
    { value: 'jymaster', label: '超清母带', description: 'FLAC 24bit/96kHz', priority: 2, format: 'FLAC 24bit/96kHz' },
    { value: 'jyeffect', label: '高清臻音', description: 'Spatial Audio', priority: 3, format: 'Spatial' },
    { value: 'sky', label: '沉浸环绕声', description: 'Surround Audio', priority: 4, format: 'Surround' },
    { value: 'hires', label: 'Hi-Res', description: 'FLAC 24bit', priority: 5, format: 'FLAC 24bit' },
    { value: 'lossless', label: '无损', description: 'FLAC', priority: 6, format: 'FLAC' },
    { value: 'exhigh', label: '极高', description: '320kbps', priority: 7, format: 'MP3/AAC' },
    { value: 'standard', label: '标准', description: '128kbps', priority: 8, format: 'MP3' },
  ],
  filename_formats: [
    { value: 'song-artist', label: '歌曲名 - 歌手名', example: '他不懂 - 张杰.flac' },
    { value: 'artist-song', label: '歌手名 - 歌曲名', example: '张杰 - 他不懂.flac' },
    { value: 'song-only', label: '仅歌曲名', example: '他不懂.flac' },
  ],
  platform_quality_support: {
    netease: { max_quality: 'hires', fallback_chain: ['hires', 'lossless', 'exhigh', 'standard'] },
    qq: { max_quality: 'exhigh', fallback_chain: ['exhigh', 'standard'] },
    kugou: { max_quality: 'lossless', fallback_chain: ['lossless', 'exhigh', 'standard'] },
    kuwo: { max_quality: 'lossless', fallback_chain: ['lossless', 'exhigh', 'standard'] },
  },
}

// ==================== 缓存读写 ====================
const loadFromStorage = () => {
  try {
    const stored = localStorage.getItem(CACHE_KEY)
    if (!stored) return null
    const { data, ts } = JSON.parse(stored)
    if (!data || Date.now() - ts > CACHE_TTL_MS) return null
    return data
  } catch {
    return null
  }
}

const saveToStorage = (data) => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ data, ts: Date.now() }))
  } catch { /* 写入失败静默 */ }
}

// ==================== 加载入口 ====================
export const loadConfig = () => {
  if (config.value !== null) return Promise.resolve(config.value)
  if (_loadingPromise) return _loadingPromise

  // 优先用 localStorage 缓存
  const cached = loadFromStorage()
  if (cached) {
    config.value = cached
    return Promise.resolve(cached)
  }

  _loadingPromise = getConfig()
    .then(data => {
      if (data && data.platforms && data.qualities) {
        config.value = data
        saveToStorage(data)
        return data
      }
      throw new Error('Invalid config response')
    })
    .catch(err => {
      console.warn('[configManager] 后端 /config 不可用，使用兜底配置:', err.message)
      config.value = FALLBACK
      return FALLBACK
    })
    .finally(() => {
      _loadingPromise = null
    })

  return _loadingPromise
}

// ==================== 查询辅助函数 ====================

/** 获取所有平台（兼容 config 尚未加载完成的情况） */
export const getPlatforms = () => {
  return config.value?.platforms || FALLBACK.platforms
}

/** 获取所有音质（按 priority 升序） */
export const getQualities = () => {
  return config.value?.qualities || FALLBACK.qualities
}

/** 获取所有文件命名格式 */
export const getFilenameFormats = () => {
  return config.value?.filename_formats || FALLBACK.filename_formats
}

/** 获取指定平台支持的音质降级链 */
export const getPlatformQualityChain = (platformId, requested = 'lossless') => {
  const support = config.value?.platform_quality_support?.[platformId]
    || FALLBACK.platform_quality_support[platformId]
  if (!support) return [requested]
  const chain = support.fallback_chain
  if (requested && chain.includes(requested)) {
    return chain.slice(chain.indexOf(requested))
  }
  return [...chain]
}

/** 获取指定 value 的音质对象 */
export const getQualityByValue = (value) => {
  const list = config.value?.qualities || FALLBACK.qualities
  return list.find(q => q.value === value) || null
}

/** 获取音质标签（label） */
export const getQualityLabel = (value) => {
  const q = getQualityByValue(value)
  return q ? q.label : value
}

/** 获取文件命名格式 label */
export const getFilenameFormatLabel = (value) => {
  const list = config.value?.filename_formats || FALLBACK.filename_formats
  const f = list.find(x => x.value === value)
  return f ? f.label : value
}

/** 获取文件命名格式示例 */
export const getFilenameFormatExample = (value) => {
  const list = config.value?.filename_formats || FALLBACK.filename_formats
  const f = list.find(x => x.value === value)
  return f ? f.example : ''
}
