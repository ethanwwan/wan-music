<template>
  <div class="player-container">
    <!-- Mini 悬浮播放按钮 -->
    <div 
      v-if="playlist.length > 0" 
      class="mini-player"
      :class="{ 'playing': isPlaying }"
      @click="togglePlay"
    >
      <!-- 圆形进度条边框 -->
      <svg class="progress-ring" viewBox="0 0 60 60">
        <!-- 背景圆 -->
        <circle
          class="progress-ring-bg"
          cx="30"
          cy="30"
          r="28"
          fill="none"
          stroke-width="3"
        />
        <!-- 进度圆 -->
        <circle
          class="progress-ring-bar"
          cx="30"
          cy="30"
          r="28"
          fill="none"
          stroke-width="3"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="progressOffset"
        />
      </svg>
      
      <!-- 封面/图标 -->
      <div class="mini-player-content">
        <img 
          v-if="currentTrack?.cover && !showIcon" 
          :src="currentTrack.cover" 
          :alt="currentTrack.name"
          class="mini-cover"
          :class="{ 'rotating': isPlaying }"
          @error="handleCoverError"
        />
        <div v-else class="mini-icon">
          <PlayCircleOutlined v-if="!isPlaying" />
          <PauseCircleOutlined v-else />
        </div>
      </div>
      
      <!-- 悬停提示 -->
      <div class="mini-player-tooltip">
        <div class="tooltip-title">{{ currentTrack?.name || '未播放' }}</div>
        <div class="tooltip-artist">{{ currentTrack?.artist || '未知艺术家' }}</div>
        <div class="tooltip-time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</div>
      </div>
    </div>
    
    <!-- 播放列表弹窗 -->
    <div v-if="showPlaylistModal" class="playlist-modal-mask" @click="togglePlaylist">
      <div class="playlist-modal" @click.stop>
        <div class="modal-header">
          <span class="modal-title">播放列表 ({{ playlist.length }})</span>
          <button class="close-btn" @click="togglePlaylist">
            <CloseOutlined />
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
          <a-space>
            <a-button type="text" size="small" @click="playPrev" :disabled="!hasPrev">
              <template #icon><SkipBackOutlined /></template>
              上一首
            </a-button>
            <a-button type="text" size="small" @click="playNext" :disabled="!hasNext">
              下一首
              <template #icon><SkipForwardOutlined /></template>
            </a-button>
            <a-button type="text" size="small" danger @click="clearPlaylist">
              <template #icon><DeleteOutlined /></template>
              清空
            </a-button>
          </a-space>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined,
  CloseOutlined,
  SkipBackOutlined,
  SkipForwardOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue'

const props = defineProps({
  playlist: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['play', 'pause', 'end', 'download', 'play-error'])

const audioRef = ref(null)
const currentIndex = ref(0)
const isPlaying = ref(false)
const showPlaylistModal = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const showIcon = ref(false)

// 圆形进度条参数
const circumference = 2 * Math.PI * 28 // 2πr

const currentTrack = computed(() => props.playlist[currentIndex.value])

const hasPrev = computed(() => currentIndex.value > 0)

const hasNext = computed(() => currentIndex.value < props.playlist.length - 1)

const progressPercent = computed(() => {
  if (duration.value === 0) return 0
  return (currentTime.value / duration.value) * 100
})

// 计算进度条的偏移量
const progressOffset = computed(() => {
  return circumference - (progressPercent.value / 100) * circumference
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
  const current = props.playlist[currentIndex.value]
  
  if (current) {
    emit('play-error', current)
  }
  
  if (hasNext.value) {
    playTrack(currentIndex.value + 1)
  }
}

const handleCoverError = () => {
  showIcon.value = true
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

const togglePlaylist = () => {
  showPlaylistModal.value = !showPlaylistModal.value
}

const clearPlaylist = () => {
  audioRef.value?.pause()
  currentIndex.value = 0
  isPlaying.value = false
  currentTime.value = 0
  duration.value = 0
  showPlaylistModal.value = false
}

// 右键点击显示播放列表
const handleContextMenu = (event) => {
  event.preventDefault()
  togglePlaylist()
}

watch(() => props.playlist, (newPlaylist) => {
  if (newPlaylist.length === 0) {
    isPlaying.value = false
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
  left: 24px;
  bottom: 24px;
  z-index: 9999;
}

/* Mini 悬浮播放器 */
.mini-player {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.mini-player:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.mini-player:active {
  transform: scale(1.05);
}

.mini-player.playing {
  box-shadow: 0 4px 16px rgba(var(--color-primary-rgb, 0, 87, 194), 0.4);
}

/* 圆形进度条 */
.progress-ring {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-ring-bg {
  stroke: var(--color-surface-container-high);
}

.progress-ring-bar {
  stroke: var(--color-primary);
  stroke-linecap: round;
  transition: stroke-dashoffset 0.1s linear;
}

/* 内容区域 */
.mini-player-content {
  position: absolute;
  top: 6px;
  left: 6px;
  right: 6px;
  bottom: 6px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-container);
}

.mini-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.mini-cover.rotating {
  animation: rotate 8s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.mini-icon {
  font-size: 24px;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 悬停提示 */
.mini-player-tooltip {
  position: absolute;
  left: 70px;
  top: 50%;
  transform: translateY(-50%);
  background: var(--color-surface-white);
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
  pointer-events: none;
  min-width: 180px;
}

.mini-player:hover .mini-player-tooltip {
  opacity: 1;
  visibility: visible;
}

.tooltip-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.tooltip-artist {
  font-size: 12px;
  color: var(--color-on-surface-variant);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.tooltip-time {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 6px;
}

/* 播放列表弹窗 */
.playlist-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.playlist-modal {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 480px;
  max-height: 600px;
  background: var(--color-surface-white);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-outline);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-on-surface);
}

.close-btn {
  background: none;
  border: none;
  color: var(--color-on-surface-variant);
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  font-size: 16px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--color-surface-container-high);
  color: var(--color-on-surface);
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
  padding: 12px 16px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.playlist-item:hover:not(.unavailable) {
  background: var(--color-surface-container-low);
}

.playlist-item.active {
  background: var(--color-primary-light);
}

.playlist-item.unavailable {
  opacity: 0.5;
  cursor: not-allowed;
}

.track-index {
  width: 28px;
  font-size: 14px;
  color: var(--color-on-surface-variant);
  text-align: center;
}

.track-info {
  flex: 1;
  min-width: 0;
}

.track-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface);
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
  color: var(--color-on-surface-variant);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
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
  color: var(--color-on-surface-variant);
  font-size: 14px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--color-outline);
  display: flex;
  justify-content: center;
}

/* 深色模式 */
.dark .mini-player {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.dark .mini-player-content {
  background: var(--color-surface-container);
}

.dark .mini-player-tooltip {
  background: var(--color-surface-container);
}

.dark .playlist-modal {
  background: var(--color-surface);
}
</style>
