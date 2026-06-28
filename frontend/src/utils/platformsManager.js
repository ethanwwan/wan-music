/** 平台列表管理（向后兼容层）
 *
 * 平台元数据统一在 configManager 中维护（来源：后端 /config）。
 * 这里保留旧的 `platforms` ref 和 `loadPlatforms` 入口，
 * 内部委托给 configManager。
 */
import { computed } from 'vue'
import { config, loadConfig } from './configManager.js'

/** 平台列表（reactive ref，兼容老代码） */
export const platforms = computed(() => {
  return config.value?.platforms || null
})

/** 加载平台列表（已废弃，请改用 loadConfig） */
export const loadPlatforms = () => {
  return loadConfig().then(() => platforms.value)
}

/** 按 id 查找平台 */
export const getPlatformById = (id) => {
  if (!platforms.value) return null
  return platforms.value.find(p => p.id === id) || null
}
