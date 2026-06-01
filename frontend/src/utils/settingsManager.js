import { reactive } from 'vue'

// 默认设置
export const defaultSettings = {
  filenameFormat: 'song-artist', // song-artist, artist-song, song
  writeMetadata: true, // 是否写入元数据（默认开启）
  zipDownload: false, // 是否压缩下载（已移除，批量下载始终打包为ZIP）
  srtLyricsDownload: false, // 歌词格式（已移除，统一使用LRC）
  layoutMode: 'single-column', // 布局模式: dual-column, single-column
  // 播放链接缓存设置
  enableCache: true, // 是否启用缓存（默认开启）
  cacheTTLMinutes: 15, // 缓存时间（分钟） 
  // 音质设置
  selectedQuality: 'lossless', // 默认音质：无损
  // 极验验证码设置已移除
}

// 当前设置
export const settings = reactive({ ...defaultSettings })

/**
 * 加载设置
 */
export const loadSettings = () => {
  try {
    const savedSettings = localStorage.getItem('app-settings')
    console.log('[Settings] 加载设置, localStorage:', savedSettings)
    
    if (savedSettings) {
      const parsed = JSON.parse(savedSettings)
      console.log('[Settings] 解析后的设置:', parsed)
      
      // 合并默认值和保存的值
      Object.assign(settings, { ...defaultSettings, ...parsed })
      console.log('[Settings] 合并后的设置:', settings)
      
      // 迁移逻辑：根据新的产品需求，强制某些设置为默认值
      let hasChanges = false
      
      // writeMetadata 必须默认为 true（产品需求：自动写入元数据默认开启）
      if (settings.writeMetadata !== defaultSettings.writeMetadata) {
        console.log(`[Settings] 迁移: writeMetadata 从 ${settings.writeMetadata} 改为 ${defaultSettings.writeMetadata}`)
        settings.writeMetadata = defaultSettings.writeMetadata
        hasChanges = true
      }
      
      // enableCache 必须默认为 true
      if (settings.enableCache !== defaultSettings.enableCache) {
        console.log(`[Settings] 迁移: enableCache 从 ${settings.enableCache} 改为 ${defaultSettings.enableCache}`)
        settings.enableCache = defaultSettings.enableCache
        hasChanges = true
      }
      
      // selectedQuality 必须有值且有效
      if (!settings.selectedQuality || settings.selectedQuality !== defaultSettings.selectedQuality) {
        console.log(`[Settings] 迁移: selectedQuality 从 ${settings.selectedQuality} 改为 ${defaultSettings.selectedQuality}`)
        settings.selectedQuality = defaultSettings.selectedQuality
        hasChanges = true
      }
      
      // 清理已移除的旧字段
      const deprecatedKeys = ['enableUrlCache', 'urlCacheTTLMinutes']
      deprecatedKeys.forEach(key => {
        if (parsed[key] !== undefined) {
          delete settings[key]
          hasChanges = true
          console.log(`[Settings] 清理: 移除已废弃的设置项 ${key}`)
        }
      })
      
      // 如果有变更，立即保存
      if (hasChanges) {
        saveSettings()
        console.log('[Settings] 已保存迁移后的设置')
      }
    } else {
      // 没有保存的设置，使用默认值
      Object.assign(settings, defaultSettings)
      saveSettings()
      console.log('[Settings] 无保存的设置，使用默认值:', settings)
    }
  } catch (error) {
    console.error('[Settings] 加载设置失败:', error)
    Object.assign(settings, defaultSettings)
  }
}

/**
 * 保存设置
 */
export const saveSettings = () => {
  try {
    localStorage.setItem('app-settings', JSON.stringify(settings))
  } catch {
    void 0
  }
}

/**
 * 更新设置
 * @param {Object} newSettings 新的设置对象
 */
export const updateSettings = (newSettings) => {
  Object.assign(settings, newSettings)
  saveSettings()
}

/**
 * 重置设置为默认值
 */
export const resetSettings = () => {
  Object.assign(settings, defaultSettings)
  saveSettings()
}

/**
 * 获取设置值
 * @param {string} key 设置键名
 * @returns {any} 设置值
 */
export const getSetting = (key) => {
  return settings[key]
}

/**
 * 设置单个配置项
 * @param {string} key 设置键名
 * @param {any} value 设置值
 */
export const setSetting = (key, value) => {
  settings[key] = value
  saveSettings()
}
