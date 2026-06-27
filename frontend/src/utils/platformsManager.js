/** 平台列表管理
 *
 * 平台元数据由后端维护（`/platforms` 接口），前端首次使用时拉取并缓存到内存
 * - 加载中：platforms.value === null
 * - 成功：platforms.value === [{id, name, color, description}, ...]
 * - 失败：platforms.value === []，由调用方处理回退
 */
import { ref } from 'vue'
import { getPlatforms } from '../services/musicApi.js'

export const platforms = ref(null)

/** 模块级 Promise，保证并发调用复用同一次请求 */
let _loadingPromise = null

/** 拉取并缓存平台列表（已加载则直接返回） */
export const loadPlatforms = () => {
  if (platforms.value !== null) return Promise.resolve(platforms.value)
  if (_loadingPromise) return _loadingPromise

  _loadingPromise = getPlatforms()
    .then(list => {
      platforms.value = Array.isArray(list) ? list : []
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
