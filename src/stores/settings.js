/**
 * Pinia Store - 设置状态管理
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  // 状态
  const theme = ref('light')
  const quality = ref('lossless')
  const autoPlay = ref(false)
  const showLyrics = ref(false)
  const layout = ref('single') // 'single' | 'double'
  const filenameTemplate = ref('{artist} - {name}')
  const embedMetadata = ref(true)
  const embedLyrics = ref(true)
  const useZipDownload = ref(true)

  // 加载保存的设置
  const loadSettings = () => {
    try {
      const saved = localStorage.getItem('wan-music-settings')
      if (saved) {
        const settings = JSON.parse(saved)
        
        if (settings.theme !== undefined) theme.value = settings.theme
        if (settings.quality !== undefined) quality.value = settings.quality
        if (settings.autoPlay !== undefined) autoPlay.value = settings.autoPlay
        if (settings.showLyrics !== undefined) showLyrics.value = settings.showLyrics
        if (settings.layout !== undefined) layout.value = settings.layout
        if (settings.filenameTemplate !== undefined) filenameTemplate.value = settings.filenameTemplate
        if (settings.embedMetadata !== undefined) embedMetadata.value = settings.embedMetadata
        if (settings.embedLyrics !== undefined) embedLyrics.value = settings.embedLyrics
        if (settings.useZipDownload !== undefined) useZipDownload.value = settings.useZipDownload
      }
    } catch (error) {
      console.error('加载设置失败:', error)
    }
  }

  // 保存设置
  const saveSettings = () => {
    try {
      const settings = {
        theme: theme.value,
        quality: quality.value,
        autoPlay: autoPlay.value,
        showLyrics: showLyrics.value,
        layout: layout.value,
        filenameTemplate: filenameTemplate.value,
        embedMetadata: embedMetadata.value,
        embedLyrics: embedLyrics.value,
        useZipDownload: useZipDownload.value
      }
      localStorage.setItem('wan-music-settings', JSON.stringify(settings))
    } catch (error) {
      console.error('保存设置失败:', error)
    }
  }

  // 自动保存
  watch(
    [theme, quality, autoPlay, showLyrics, layout, filenameTemplate, embedMetadata, embedLyrics, useZipDownload],
    () => {
      saveSettings()
    },
    { deep: true }
  )

  // Actions
  const setTheme = (newTheme) => {
    theme.value = newTheme
  }

  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  const setQuality = (newQuality) => {
    quality.value = newQuality
  }

  const setLayout = (newLayout) => {
    layout.value = newLayout
  }

  const reset = () => {
    theme.value = 'light'
    quality.value = 'lossless'
    autoPlay.value = false
    showLyrics.value = false
    layout.value = 'single'
    filenameTemplate.value = '{artist} - {name}'
    embedMetadata.value = true
    embedLyrics.value = true
    useZipDownload.value = true
  }

  return {
    // 状态
    theme,
    quality,
    autoPlay,
    showLyrics,
    layout,
    filenameTemplate,
    embedMetadata,
    embedLyrics,
    useZipDownload,

    // 方法
    loadSettings,
    saveSettings,
    setTheme,
    toggleTheme,
    setQuality,
    setLayout,
    reset
  }
})
