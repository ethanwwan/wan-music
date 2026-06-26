import { reactive, watch } from 'vue'

const STORAGE_KEY = 'app-settings'

/** 默认设置（被旧版本使用过的 key 也会被 loadSettings 清理） */
export const defaultSettings = {
  filenameFormat: 'song-artist',     // song-artist | artist-song | song
  writeMetadata: true,               // 自动写入元数据（产品需求：默认开启）
  layoutMode: 'single-column',
  enableCache: true,                 // 搜索/歌单详情页缓存开关
  cacheTTLMinutes: 15,
  selectedQuality: 'lossless',       // 默认音质
}

export const settings = reactive({ ...defaultSettings })

/** 任意字段变化都自动持久化到 localStorage */
watch(settings, () => saveSettings(), { deep: true })

/** 启动时加载并迁移旧字段（writeMetadata 强制为 true 以满足产品需求） */
export const loadSettings = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      Object.assign(settings, { ...defaultSettings, ...parsed })

      // 旧版本 layoutMode 字段已废弃
      if (parsed.layoutMode !== undefined) {
        delete settings.layoutMode
      }
      // 旧版本强制 writeMetadata = true
      settings.writeMetadata = defaultSettings.writeMetadata
      // selectedQuality 兜底
      if (!settings.selectedQuality) settings.selectedQuality = defaultSettings.selectedQuality
    } else {
      Object.assign(settings, defaultSettings)
    }
    saveSettings()
  } catch {
    Object.assign(settings, defaultSettings)
  }
}

export const saveSettings = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch { /* localStorage 写入失败时静默 */ }
}
