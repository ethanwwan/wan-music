/**
 * 播放器 Composable
 * 管理音乐播放状态和逻辑
 */

import { ref, computed } from 'vue'

export function usePlayer() {
  const player = ref(null)
  const isPlaying = ref(false)
  const currentTrack = ref(null)
  const volume = ref(0.8)
  const playlist = ref([])
  const currentIndex = ref(-1)
  const duration = ref(0)
  const currentTime = ref(0)

  const hasPlaylist = computed(() => playlist.value.length > 0)
  const hasTrack = computed(() => currentTrack.value !== null)

  const initPlayer = (container, options = {}) => {
    console.log('usePlayer: initPlayer called', { container, options })
  }

  const play = (track = null) => {
    if (track) {
      currentTrack.value = track
      if (!playlist.value.find(t => t.id === track.id)) {
        playlist.value.push(track)
      }
    }
    isPlaying.value = true
  }

  const pause = () => {
    isPlaying.value = false
  }

  const toggle = () => {
    isPlaying.value = !isPlaying.value
  }

  const setVolume = (vol) => {
    volume.value = Math.max(0, Math.min(1, vol))
  }

  const next = () => {
    if (!hasPlaylist.value) return

    const nextIndex = (currentIndex.value + 1) % playlist.value.length
    const nextTrack = playlist.value[nextIndex]

    if (nextTrack) {
      currentTrack.value = nextTrack
      currentIndex.value = nextIndex
    }
  }

  const prev = () => {
    if (!hasPlaylist.value) return

    const prevIndex = currentIndex.value - 1 < 0 
      ? playlist.value.length - 1 
      : currentIndex.value - 1
    const prevTrack = playlist.value[prevIndex]

    if (prevTrack) {
      currentTrack.value = prevTrack
      currentIndex.value = prevIndex
    }
  }

  const addToPlaylist = (track) => {
    if (!playlist.value.find(t => t.id === track.id)) {
      playlist.value.push(track)
    }
  }

  const clearPlaylist = () => {
    playlist.value = []
    currentIndex.value = -1
    currentTrack.value = null
  }

  const destroy = () => {
    player.value = null
    isPlaying.value = false
    currentTrack.value = null
    playlist.value = []
    currentIndex.value = -1
  }

  return {
    player,
    isPlaying,
    currentTrack,
    volume,
    playlist,
    currentIndex,
    duration,
    currentTime,
    hasPlaylist,
    hasTrack,
    initPlayer,
    play,
    pause,
    toggle,
    setVolume,
    next,
    prev,
    addToPlaylist,
    clearPlaylist,
    destroy
  }
}

export default usePlayer
