<template>
  <div class="player-container">
    <!-- Mini 悬浮播放按钮 -->
    <div
      v-if="currentSong"
      class="mini-player"
      :class="{ playing: isPlaying }"
      @click="togglePlay"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      <!-- 圆形进度条边框 -->
      <svg class="progress-ring" viewBox="0 0 60 60">
        <circle
          class="progress-ring-bg"
          cx="30"
          cy="30"
          r="28"
          fill="none"
          stroke-width="3"
        />
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
          v-if="currentSong?.cover && !showIcon"
          :src="currentSong.cover"
          :alt="currentSong.name"
          class="mini-cover"
          :class="{ rotating: isPlaying }"
          @error="handleCoverError"
        />
        <div v-else class="mini-icon">
          <PlayCircleOutlined v-if="!isPlaying" />
          <PauseOutlined v-else />
        </div>
      </div>

      <!-- 悬停面板：歌曲信息 + 歌词（歌词随 /song 响应一并返回，无需再请求） -->
      <div class="mini-player-panel">
        <div class="panel-header">
          <div class="panel-title">{{ currentSong?.name || '未播放' }}</div>
          <div class="panel-artist">{{ currentSong?.artist || '未知艺术家' }}</div>
          <div class="panel-time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</div>
        </div>

        <div class="panel-divider" />

        <div class="panel-lyric">
          <div v-if="!lyricLines.length" class="lyric-status">暂无歌词</div>
          <ul v-else class="lyric-list" ref="lyricListRef">
            <li
              v-for="(line, idx) in lyricLines"
              :key="idx"
              :class="{ active: idx === currentLyricIndex }"
            >{{ line.text }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { PlayCircleOutlined, PauseOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  currentSong: {
    type: Object,
    default: null
  },
  autoplay: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['play', 'pause', 'end', 'download', 'play-error'])

const audioRef = ref(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const showIcon = ref(false)
const isHovered = ref(false)

// ==================== 歌词（随 /song 响应一并返回，无需单独请求） ====================

/** LRC 解析后的行：{ time: 秒, text: 字符串 } */
const lyricLines = ref([])
const lyricListRef = ref(null)

const circumference = 2 * Math.PI * 28

const progressPercent = computed(() =>
  duration.value === 0 ? 0 : (currentTime.value / duration.value) * 100
)
const progressOffset = computed(() =>
  circumference - (progressPercent.value / 100) * circumference
)

/** 找到 currentTime 所在歌词行（二分查找 O(log n)） */
const currentLyricIndex = computed(() => {
  const lines = lyricLines.value
  if (!lines.length) return -1
  const t = currentTime.value
  let lo = 0, hi = lines.length - 1, ans = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (lines[mid].time <= t) { ans = mid; lo = mid + 1 } else { hi = mid - 1 }
  }
  return ans
})

const formatTime = (time) => {
  const m = Math.floor(time / 60)
  const s = Math.floor(time % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/** 解析 LRC 文本为 {time, text} 数组 */
const parseLrc = (lrc) => {
  if (!lrc) return []
  const result = []
  const timeRe = /\[(\d+):(\d+(?:\.\d+)?)\]/g
  for (const line of lrc.split(/\r?\n/)) {
    const matches = []
    let m
    while ((m = timeRe.exec(line)) !== null) {
      matches.push({ time: parseInt(m[1]) * 60 + parseFloat(m[2]), index: m.index })
    }
    if (!matches.length) continue
    for (let i = 0; i < matches.length; i++) {
      const afterTag = line.indexOf(']', matches[i].index) + 1
      const nextAfter = i + 1 < matches.length ? matches[i + 1].index : line.length
      const text = line.slice(afterTag, nextAfter).trim()
      if (text) result.push({ time: matches[i].time, text })
    }
  }
  return result.sort((a, b) => a.time - b.time)
}

// 切换播放
const togglePlay = async () => {
  if (!audioRef.value) initAudio()
  if (isPlaying.value) {
    audioRef.value.pause()
    isPlaying.value = false
    emit('pause')
  } else {
    try {
      if (currentTime.value >= duration.value && duration.value > 0) {
        audioRef.value.currentTime = 0
      }
      await audioRef.value.play()
      isPlaying.value = true
      emit('play')
    } catch (error) {
      if (error.name !== 'AbortError') {
        isPlaying.value = false
      }
    }
  }
}

const handleTimeUpdate = () => {
  if (audioRef.value) currentTime.value = audioRef.value.currentTime
}
const handleLoadedMetadata = () => {
  if (audioRef.value) duration.value = audioRef.value.duration
}
const handleEnded = () => {
  isPlaying.value = false
  emit('end')
}
const handleError = (event) => {
  if (event.target.error?.code === 1) return
  isPlaying.value = false
  if (props.currentSong) emit('play-error', props.currentSong)
}
const handleCoverError = () => { showIcon.value = true }

const initAudio = () => {
  if (!audioRef.value) {
    audioRef.value = new Audio()
    audioRef.value.addEventListener('timeupdate', handleTimeUpdate)
    audioRef.value.addEventListener('loadedmetadata', handleLoadedMetadata)
    audioRef.value.addEventListener('ended', handleEnded)
    audioRef.value.addEventListener('error', handleError)
  }
  audioRef.value.src = props.currentSong?.url || ''
}

// 切歌时重置 + 重新解析歌词
watch(() => props.currentSong, (newSong) => {
  if (newSong) {
    lyricLines.value = parseLrc(newSong.lrc)
    currentTime.value = 0
  } else {
    lyricLines.value = []
  }
}, { immediate: true, deep: true })

// 当前歌词行变化时，自动滚动到可视区
watch(currentLyricIndex, async (idx) => {
  if (idx < 0) return
  await nextTick()
  const list = lyricListRef.value
  if (!list) return
  const active = list.children[idx]
  if (active) {
    const listRect = list.getBoundingClientRect()
    const itemRect = active.getBoundingClientRect()
    const offset = itemRect.top - listRect.top - listRect.height / 2 + itemRect.height / 2
    list.scrollBy({ top: offset, behavior: 'smooth' })
  }
})

onMounted(() => {
  if (props.currentSong) initAudio()
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
  transform: scale(1.05);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.mini-player.playing {
  box-shadow: 0 4px 16px rgba(0, 87, 194, 0.4);
}

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
  object-fit: cover;
  border-radius: 50%;
}

.mini-cover.rotating {
  animation: rotate 8s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.mini-icon {
  font-size: 24px;
  color: var(--color-primary);
}

/* 悬停面板：信息 + 歌词 */
.mini-player-panel {
  position: absolute;
  left: 70px;
  bottom: 0;
  width: 280px;
  max-height: 320px;
  background: var(--color-surface-white);
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
  opacity: 0;
  visibility: hidden;
  transform: translateY(10px);
  transition: all 0.2s ease;
  pointer-events: none;
  display: flex;
  flex-direction: column;
}

.mini-player:hover .mini-player-panel {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.panel-header {
  flex-shrink: 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-artist {
  font-size: 12px;
  color: var(--color-on-surface-variant);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-time {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.panel-divider {
  height: 1px;
  background: var(--color-border-subtle);
  margin: 10px 0;
}

.panel-lyric {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.lyric-status {
  font-size: 12px;
  color: var(--color-text-muted);
  text-align: center;
  padding: 12px 0;
}

.lyric-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
  scroll-behavior: smooth;
  mask-image: linear-gradient(to bottom, transparent 0, #000 24px, #000 calc(100% - 24px), transparent 100%);
}

.lyric-list li {
  font-size: 13px;
  line-height: 1.8;
  color: var(--color-text-muted);
  text-align: center;
  transition: all 0.25s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lyric-list li.active {
  color: var(--color-primary);
  font-weight: 600;
  font-size: 14px;
}

/* 深色模式 */
.dark .mini-player {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.dark .mini-player-content {
  background: var(--color-surface-container);
}

.dark .mini-player-panel {
  background: var(--color-surface-container);
}
</style>
