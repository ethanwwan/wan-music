/**
 * Pinia Store - 音乐状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import musicApi from '../services/musicApi.js'

export const useMusicStore = defineStore('music', () => {
  // 状态
  const currentQuality = ref('lossless')
  const musicInfo = ref(null)
  const playlistInfo = ref(null)
  const albumInfo = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // 计算属性
  const hasMusic = computed(() => musicInfo.value !== null)
  const hasPlaylist = computed(() => playlistInfo.value !== null)
  const hasAlbum = computed(() => albumInfo.value !== null)
  const hasError = computed(() => error.value !== null)

  // Actions
  const setQuality = (quality) => {
    currentQuality.value = quality
  }

  const fetchMusicInfo = async (url, quality = 'lossless') => {
    isLoading.value = true
    error.value = null

    try {
      const info = await musicApi.getMusicInfo(url, quality)
      musicInfo.value = info
      return info
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchPlaylistInfo = async (url) => {
    isLoading.value = true
    error.value = null

    try {
      const info = await musicApi.parsePlaylistInfo(url)
      playlistInfo.value = info
      return info
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchAlbumInfo = async (url) => {
    isLoading.value = true
    error.value = null

    try {
      const info = await musicApi.parseAlbumInfo(url)
      albumInfo.value = info
      return info
    } catch (err) {
      error.value = err
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const clearMusic = () => {
    musicInfo.value = null
    error.value = null
  }

  const clearPlaylist = () => {
    playlistInfo.value = null
    error.value = null
  }

  const clearAlbum = () => {
    albumInfo.value = null
    error.value = null
  }

  const clearAll = () => {
    musicInfo.value = null
    playlistInfo.value = null
    albumInfo.value = null
    error.value = null
  }

  return {
    // 状态
    currentQuality,
    musicInfo,
    playlistInfo,
    albumInfo,
    isLoading,
    error,

    // 计算属性
    hasMusic,
    hasPlaylist,
    hasAlbum,
    hasError,

    // Actions
    setQuality,
    fetchMusicInfo,
    fetchPlaylistInfo,
    fetchAlbumInfo,
    clearMusic,
    clearPlaylist,
    clearAlbum,
    clearAll
  }
})
