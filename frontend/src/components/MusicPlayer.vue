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
          <PauseOutlined v-else />
        </div>
      </div>
      
      <!-- 悬停提示 -->
      <div class="mini-player-tooltip">
        <div class="tooltip-title">{{ currentTrack?.name || '未播放' }}</div>
        <div class="tooltip-artist">{{ currentTrack?.artist || '未知艺术家' }}</div>
        <div class="tooltip-time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, PauseOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  playlist: {
    type: Array,
    default: () => []
  },
  currentIndex: {
    type: Number,
    default: 0
  },
  autoplay: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['play', 'pause', 'end', 'download', 'play-error', 'update:currentIndex'])

const audioRef = ref(null)
const internalIndex = ref(0)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const showIcon = ref(false)

// 使用 prop 或内部索引
const currentIndex = computed({
  get: () => props.currentIndex ?? internalIndex.value,
  set: (val) => { internalIndex.value = val }
})

// 圆形进度条参数
const circumference = 2 * Math.PI * 28 // 2πr

const currentTrack = computed(() => props.playlist[currentIndex.value])

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
  internalIndex.value = index
  emit('update:currentIndex', index)
  initAudio()
  audioRef.value.play()
  isPlaying.value = true
  emit('play')
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
  const hasNext = currentIndex.value < props.playlist.length - 1
  if (hasNext) {
    playTrack(currentIndex.value + 1)
  } else {
    emit('end')
  }
}

const handleError = (event) => {
  // ERR_ABORTED (错误代码 1) 是正常的中止错误，通常发生在快速切换歌曲时
  if (event.target.error?.code === 1) {
    return
  }
  
  isPlaying.value = false
  const current = props.playlist[currentIndex.value]
  
  if (current) {
    emit('play-error', current)
  }
  
  const hasNext = currentIndex.value < props.playlist.length - 1
  if (hasNext) {
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

watch(() => props.playlist, (newPlaylist) => {
  if (newPlaylist.length === 0) {
    isPlaying.value = false
  }
}, { deep: true })

// 监听 currentIndex prop 变化，自动切换歌曲
watch(() => props.currentIndex, (newIndex, oldIndex) => {
  if (newIndex !== oldIndex && newIndex >= 0 && newIndex < props.playlist.length) {
    if (audioRef.value) {
      initAudio()
      if (props.autoplay || isPlaying.value) {
        audioRef.value.play()
        isPlaying.value = true
      }
    }
  }
})

// 监听 playlist 变化，自动播放第一首
watch(() => props.playlist, (newPlaylist, oldPlaylist) => {
  if (newPlaylist.length > 0 && oldPlaylist?.length === 0 && props.autoplay) {
    initAudio()
    audioRef.value?.play()
    isPlaying.value = true
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
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-container);
}

.mini-cover {
  width: 48px;
  height: 48px;
  max-width: 48px;
  max-height: 48px;
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
</style>
