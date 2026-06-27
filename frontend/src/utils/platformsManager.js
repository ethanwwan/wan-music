/** 平台列表管理
 *
 * 平台元数据由后端维护（`/platforms` 接口），前端首次使用时拉取并缓存到 localStorage
 * - 加载中：platforms.value === null
 * - 成功：platforms.value === [{id, name, color, description}, ...]
 * - 失败：platforms.value === []，由调用方处理回退
 */
import { ref } from 'vue'
import { getPlatforms } from '../services/musicApi.js'

const CACHE_KEY = 'wan-music-platforms-cache'
/** 缓存 24 小时 */
const CACHE_TTL_MS = 24 * 60 * 60 * 1000

export const platforms = ref(null)

/** 模块级 Promise，保证并发调用复用同一次请求 */
let _loadingPromise = null

const loadFromStorage = () => {
  try {
    const stored = localStorage.getItem(CACHE_KEY)
    if (!stored) return null
    const { data, ts } = JSON.parse(stored)
    if (!Array.isArray(data) || Date.now() - ts > CACHE_TTL_MS) return null
    return data
  } catch {
    return null
  }
}

const saveToStorage = (data) => {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ data, ts: Date.now() }))
  } catch { /* localStorage 写入失败时静默 */ }
}

/** 拉取并缓存平台列表（已加载则直接返回） */
export const loadPlatforms = () => {
  if (platforms.value !== null) return Promise.resolve(platforms.value)
  if (_loadingPromise) return _loadingPromise

  // 优先使用 localStorage 缓存（静默加载，不提示）
  const cached = loadFromStorage()
  if (cached) {
    platforms.value = cached
    return Promise.resolve(cached)
  }

  _loadingPromise = getPlatforms()
    .then(list => {
      const normalized = Array.isArray(list) ? list : []
      platforms.value = normalized
      if (normalized.length > 0) saveToStorage(normalized)
      return platforms.value
    })
    .catch(err => {
      console.error('加载平台列表失败:', err)
      platforms.value = []
      return platforms.value
    })
    .finally(() => {
      _loadingPromise = null
    })

  return _loadingPromise
}

/** 按 id 查找平台（用于 UI 标签/颜色），未找到时返回 null */
export const getPlatformById = (id) => {
  if (!platforms.value) return null
  return platforms.value.find(p => p.id === id) || null
}
