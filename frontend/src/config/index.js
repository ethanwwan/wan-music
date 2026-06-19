/**
 * 配置管理模块
 * 统一管理应用配置
 */

export const APP_CONFIG = {
  appName: 'Wan Music',
  version: '2.0.0',
  author: 'Suxiaoqinx',

  api: {
    baseUrl: 'https://interface3.music.163.com',
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1000
  },

  download: {
    maxConcurrent: 3,
    chunkSize: 8192,
    enableMetadata: true,
    enableLyrics: true
  },

  quality: {
    default: 'lossless',
    options: [
      { value: 'standard', label: '标准', bitrate: '128kbps' },
      { value: 'exhigh', label: '极高', bitrate: '320kbps' },
      { value: 'lossless', label: '无损', bitrate: 'FLAC' },
      { value: 'hires', label: 'Hi-Res', bitrate: 'FLAC 24bit' },
      { value: 'sky', label: '沉浸', bitrate: 'Dolby Atmos' },
      { value: 'jyeffect', label: '环绕', bitrate: 'Sony 360RA' },
      { value: 'jymaster', label: '母带', bitrate: 'FLAC 24bit/96kHz' },
      { value: 'dolby', label: '杜比', bitrate: 'Dolby Atmos' }
    ]
  },

  ui: {
    theme: 'light',
    layout: 'single',
    showLyrics: false,
    autoPlay: false
  },

  storage: {
    cookieKey: 'netease_music_cookie',
    settingsKey: 'netease_music_settings',
    cacheKey: 'netease_music_cache'
  },

  userAgent: 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154',

  referer: 'https://music.163.com/'
}

export class ConfigManager {
  constructor() {
    this.config = { ...APP_CONFIG }
    this.loadSettings()
  }

  /**
   * 加载保存的设置
   */
  loadSettings() {
    try {
      const saved = localStorage.getItem(APP_CONFIG.storage.settingsKey)
      if (saved) {
        const settings = JSON.parse(saved)
        this.config = { ...this.config, ...settings }
      }
    } catch (error) {
      console.error('加载设置失败:', error)
    }
  }

  /**
   * 保存设置
   */
  saveSettings() {
    try {
      const settings = {
        quality: this.config.quality,
        ui: this.config.ui,
        download: this.config.download
      }
      localStorage.setItem(APP_CONFIG.storage.settingsKey, JSON.stringify(settings))
    } catch (error) {
      console.error('保存设置失败:', error)
    }
  }

  /**
   * 获取配置
   */
  get(key) {
    const keys = key.split('.')
    let value = this.config
    for (const k of keys) {
      value = value?.[k]
    }
    return value
  }

  /**
   * 设置配置
   */
  set(key, value) {
    const keys = key.split('.')
    let target = this.config
    for (let i = 0; i < keys.length - 1; i++) {
      if (!target[keys[i]]) {
        target[keys[i]] = {}
      }
      target = target[keys[i]]
    }
    target[keys[keys.length - 1]] = value
    this.saveSettings()
  }

  /**
   * 重置配置
   */
  reset() {
    this.config = { ...APP_CONFIG }
    this.saveSettings()
  }
}

export default new ConfigManager()
