<template>
  <div class="player-container">
    <div 
      v-if="!isVisible && playlist.length > 0" 
      class="player-trigger-area"
      @mouseenter="handleMouseEnter"
    ></div>
    
    <div v-show="isVisible && playlist.length > 0" class="bottom-player" :class="{ 'expanded': showLyrics }">
      <div class="player-main">
        <div class="player-left">
          <div class="cover-wrapper" @click="toggleLyrics">
            <img 
              v-if="currentTrack?.cover" 
              :src="currentTrack.cover" 
              :alt="currentTrack.name" 
              class="cover"
              :class="{ 'playing': isPlaying }"
            />
            <div v-else class="cover-placeholder">
              <span class="music-icon">♪</span>
            </div>
          </div>
          
          <div class="song-info">
            <div class="song-name">{{ currentTrack?.name || '未播放' }}</div>
            <div class="artist-name">{{ currentTrack?.artist || '未知艺术家' }}</div>
          </div>
        </div>
        
        <div class="player-center">
          <div class="controls">
            <button class="control-btn" @click="playPrev" :disabled="!hasPrev">
              <span class="icon">❮❮</span>
            </button>
            <button class="play-btn" @click="togglePlay">
              <span class="icon">{{ isPlaying ? '❚❚' : '▶' }}</span>
            </button>
            <button class="control-btn" @click="playNext" :disabled="!hasNext">
              <span class="icon">❯❯</span>
            </button>
          </div>
          
          <div class="progress-area">
            <span class="time">{{ formatTime(currentTime) }}</span>
            <div class="progress-bar" @click="seekTo">
              <div class="progress-track" ref="progressTrack">
                <div class="progress-played" :style="{ width: progressPercent + '%' }"></div>
                <div class="progress-dot" :style="{ left: progressPercent + '%' }"></div>
              </div>
            </div>
            <span class="time">{{ formatTime(duration) }}</span>
          </div>
        </div>
        
        <div class="player-right">
          <div class="action-buttons">
            <button class="control-btn" @click="downloadCurrent" :disabled="isDownloading">
              <span v-if="isDownloading" class="loading-spinner"></span>
              <span v-else class="icon">⬇</span>
            </button>
            <button class="control-btn" @click="togglePlaylist">
              <span class="icon">☰</span>
            </button>
          </div>
        </div>
      </div>
      
      <div v-show="showLyrics" class="lyrics-panel">
        <div class="lyrics-header">
          <span class="lyrics-title">歌词</span>
          <button class="close-btn" @click="toggleLyrics">
            <span class="icon">✕</span>
          </button>
        </div>
        <div class="lyrics-content" ref="lyricsContainer">
          <div 
            v-for="(line, index) in parsedLyrics" 
            :key="index"
            :class="{ 'current': index === currentLyricIndex }"
            class="lyric-line"
          >
            {{ line.text }}
          </div>
          <div v-if="parsedLyrics.length === 0" class="no-lyrics">
            暂无歌词
          </div>
        </div>
      </div>
    </div>
  
    <div v-if="showPlaylistModal" class="playlist-modal-mask" @click="togglePlaylist">
      <div class="playlist-modal" @click.stop>
        <div class="modal-header">
          <span class="modal-title">播放列表</span>
          <button class="close-btn" @click="togglePlaylist">
            <span class="icon">✕</span>
          </button>
        </div>
        <div class="playlist-content">
          <div 
            v-for="(track, index) in playlist" 
            :key="track.id"
            :class="{ 'active': currentIndex === index, 'unavailable': track.unavailable }"
            class="playlist-item"
            @click="playTrack(index)"
          >
            <div class="track-index">{{ track.unavailable ? '🚫' : (index + 1) }}</div>
            <div class="track-info">
              <div class="track-name">{{ track.name }}<span v-if="track.unavailable" class="unavailable-badge">无版权</span></div>
              <div class="track-artist">{{ track.artist }}</div>
            </div>
            <div v-if="currentIndex === index && isPlaying" class="playing-indicator">
              <span class="playing-dot">●</span>
            </div>
          </div>
          <div v-if="playlist.length === 0" class="empty-playlist">
            播放列表为空
          </div>
        </div>
        <div class="modal-footer">
          <a-button type="text" @click="clearPlaylist">清空列表</a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'

const props = defineProps({
  playlist: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['play', 'pause', 'end', 'download'])

const audioRef = ref(null)
const currentIndex = ref(0)
const isPlaying = ref(false)
const isVisible = ref(true)
const showLyrics = ref(false)
const showPlaylistModal = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const isDownloading = ref(false)
const lyricsContainer = ref(null)
const progressTrack = ref(null)

const currentTrack = computed(() => props.playlist[currentIndex.value])

const hasPrev = computed(() => currentIndex.value > 0)

const hasNext = computed(() => currentIndex.value < props.playlist.length - 1)

const progressPercent = computed(() => {
  if (duration.value === 0) return 0
  return (currentTime.value / duration.value) * 100
})

const parsedLyrics = computed(() => {
  if (!currentTrack.value?.lyrics) return []
  const lines = currentTrack.value.lyrics.split('\n')
  return lines.map(line => {
    const match = line.match(/^\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)$/)
    if (match) {
      const minutes = parseInt(match[1])
      const seconds = parseInt(match[2])
      const milliseconds = parseInt(match[3])
      return {
        time: minutes * 60 + seconds + milliseconds / 1000,
        text: match[4] || ''
      }
    }
    return { time: 0, text: line }
  })
})

const currentLyricIndex = computed(() => {
  const current = currentTime.value
  for (let i = parsedLyrics.value.length - 1; i >= 0; i--) {
    if (current >= parsedLyrics.value[i].time) {
      return i
    }
  }
  return -1
})

const formatTime = (time) => {
  const minutes = Math.floor(time / 60)
  const seconds = Math.floor(time % 60)
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
}

const togglePlay = () => {
  if (!audioRef.value) {
    initAudio()
  }
  if (isPlaying.value) {
    audioRef.value.pause()
    isPlaying.value = false
    emit('pause')
  } else {
    audioRef.value.play()
    isPlaying.value = true
    emit('play')
  }
}

const playTrack = (index) => {
  if (props.playlist[index]?.unavailable) {
    message.warning('该歌曲无版权')
    return
  }
  currentIndex.value = index
  showPlaylistModal.value = false
  initAudio()
  audioRef.value.play()
  isPlaying.value = true
  emit('play')
}

const playPrev = () => {
  if (hasPrev.value) {
    playTrack(currentIndex.value - 1)
  }
}

const playNext = () => {
  if (hasNext.value) {
    playTrack(currentIndex.value + 1)
  }
}

const seekTo = (event) => {
  if (!audioRef.value || !progressTrack.value) return
  const rect = progressTrack.value.getBoundingClientRect()
  const percent = (event.clientX - rect.left) / rect.width
  audioRef.value.currentTime = percent * duration.value
}

const handleTimeUpdate = () => {
  if (audioRef.value) {
    currentTime.value = audioRef.value.currentTime
  }
}

const handleLoadedMetadata = () => {
  if (audioRef.value) {
    duration.value = audioRef.value.duration
  }
}

const handleEnded = () => {
  isPlaying.value = false
  if (hasNext.value) {
    playTrack(currentIndex.value + 1)
  } else {
    emit('end')
  }
}

const handleError = () => {
  isPlaying.value = false
  if (hasNext.value) {
    playTrack(currentIndex.value + 1)
  }
}

const initAudio = () => {
  if (!audioRef.value) {
    audioRef.value = new Audio()
    audioRef.value.addEventListener('timeupdate', handleTimeUpdate)
    audioRef.value.addEventListener('loadedmetadata', handleLoadedMetadata)
    audioRef.value.addEventListener('ended', handleEnded)
    audioRef.value.addEventListener('error', handleError)
  }
  audioRef.value.src = currentTrack.value?.url || ''
}

const downloadCurrent = async () => {
  if (!currentTrack.value || isDownloading.value) return
  isDownloading.value = true
  try {
    const response = await fetch(currentTrack.value.url)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentTrack.value.name}.mp3`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    message.success('下载成功')
    emit('download', currentTrack.value)
  } catch (error) {
    message.error('下载失败')
  } finally {
    isDownloading.value = false
  }
}

const toggleLyrics = () => {
  showLyrics.value = !showLyrics.value
}

const togglePlaylist = () => {
  showPlaylistModal.value = !showPlaylistModal.value
}

const clearPlaylist = () => {
  audioRef.value?.pause()
  currentIndex.value = 0
  isPlaying.value = false
  currentTime.value = 0
  duration.value = 0
  showLyrics.value = false
  showPlaylistModal.value = false
}

const handleMouseEnter = () => {
  isVisible.value = true
}

watch(currentLyricIndex, (newIndex) => {
  if (newIndex >= 0 && lyricsContainer.value) {
    const lyricLine = lyricsContainer.value.children[newIndex]
    if (lyricLine) {
      lyricLine.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
})

watch(() => props.playlist, (newPlaylist) => {
  if (newPlaylist.length === 0) {
    isVisible.value = false
    showLyrics.value = false
  }
}, { deep: true })

onMounted(() => {
  if (props.playlist.length > 0) {
    initAudio()
  }
})

onUnmounted(() => {
  audioRef.value?.pause()
  audioRef.value?.removeEventListener('timeupdate', handleTimeUpdate)
  audioRef.value?.removeEventListener('loadedmetadata', handleLoadedMetadata)
  audioRef.value?.removeEventListener('ended', handleEnded)
  audioRef.value?.removeEventListener('error', handleError)
})
</script>

<style scoped>
.player-container {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
}

.player-trigger-area {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 10px;
  cursor: pointer;
  z-index: 9998;
}

.bottom-player {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: var(--color-surface-container);
  border-top: 1px solid var(--color-outline);
  display: flex;
  flex-direction: column;
  padding: 0 24px;
  z-index: 9999;
  transition: height 0.3s ease;
}

.bottom-player.expanded {
  height: 320px;
}

.player-main {
  display: flex;
  align-items: center;
  width: 100%;
  height: 80px;
}

.player-left {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 280px;
  flex-shrink: 0;
}

.cover-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
}

.cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover.playing {
  animation: spin 8s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  background: var(--color-surface-container-high);
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-icon {
  font-size: 24px;
  color: var(--color-text-muted);
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artist-name {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 0 24px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 24px;
}

.control-btn {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.2s;
}

.control-btn:hover:not(:disabled) {
  background: var(--color-surface-container-high);
  color: var(--color-text-primary);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.control-btn .icon {
  font-size: 18px;
}

.play-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: var(--color-primary);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}

.play-btn:hover {
  transform: scale(1.05);
}

.play-btn .icon {
  font-size: 20px;
  margin-left: 2px;
}

.progress-area {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 600px;
}

.time {
  font-size: 12px;
  color: var(--color-text-muted);
  min-width: 40px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--color-surface-container-high);
  border-radius: 2px;
  cursor: pointer;
  position: relative;
}

.progress-track {
  width: 100%;
  height: 100%;
  position: relative;
}

.progress-played {
  height: 100%;
  background: var(--color-primary);
  border-radius: 2px;
  position: absolute;
  left: 0;
  top: 0;
}

.progress-dot {
  width: 12px;
  height: 12px;
  background: var(--color-primary);
  border-radius: 50%;
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.2s;
}

.progress-bar:hover .progress-dot {
  opacity: 1;
}

.player-right {
  width: 120px;
  display: flex;
  justify-content: flex-end;
}

.action-buttons {
  display: flex;
  gap: 16px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-text-muted);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.lyrics-panel {
  flex: 1;
  background: var(--color-surface-container);
  border-top: 1px solid var(--color-outline);
  display: flex;
  flex-direction: column;
}

.lyrics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  border-bottom: 1px solid var(--color-outline);
}

.lyrics-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.close-btn:hover {
  background: var(--color-surface-container-high);
  color: var(--color-text-primary);
}

.lyrics-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.lyric-line {
  font-size: 14px;
  color: var(--color-text-muted);
  transition: all 0.3s;
}

.lyric-line.current {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-primary);
}

.no-lyrics {
  color: var(--color-text-muted);
  font-size: 14px;
}

.playlist-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 10000;
}

.playlist-modal {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 480px;
  max-height: 600px;
  background: var(--color-surface-white);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--color-outline);
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.playlist-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.playlist-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.playlist-item:hover:not(.unavailable) {
  background: var(--color-surface-container-low);
}

.playlist-item.active {
  background: var(--color-primary-container);
}

.playlist-item.unavailable {
  opacity: 0.5;
  cursor: not-allowed;
}

.track-index {
  width: 24px;
  font-size: 14px;
  color: var(--color-text-muted);
  text-align: center;
}

.track-info {
  flex: 1;
  min-width: 0;
}

.track-name {
  font-size: 14px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 8px;
}

.unavailable-badge {
  font-size: 10px;
  color: var(--color-error);
  background: var(--color-error-container);
  padding: 2px 6px;
  border-radius: 4px;
}

.track-artist {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playing-indicator {
  width: 24px;
  display: flex;
  justify-content: center;
}

.playing-dot {
  color: var(--color-primary);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

.empty-playlist {
  text-align: center;
  padding: 48px;
  color: var(--color-text-muted);
  font-size: 14px;
}

.modal-footer {
  padding: 12px 24px;
  border-top: 1px solid var(--color-outline);
  display: flex;
  justify-content: flex-end;
}
</style>