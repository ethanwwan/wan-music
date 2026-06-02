<template>
  <transition name="slide-up">
    <div v-show="isVisible" class="bottom-player" :class="{ 'expanded': showLyrics }">
      <!-- 主播放器区域 -->
      <div class="player-main">
        <div class="player-left">
          <!-- 封面图片 -->
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
          
          <!-- 歌曲信息 -->
          <div class="song-info">
            <div class="song-name">{{ currentTrack?.name || '未播放' }}</div>
            <div class="artist-name">{{ currentTrack?.artist || '未知艺术家' }}</div>
          </div>
        </div>
        
        <!-- 播放控制 -->
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
          
          <!-- 进度条 -->
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
        
        <!-- 右侧控制 -->
        <div class="player-right">
          <!-- 音量控制 -->
          <div class="volume-control">
            <button class="control-btn" @click="toggleMute">
              <span class="icon">{{ getVolumeIcon() }}</span>
            </button>
            <div class="volume-bar" @click="setVolume">
              <div class="volume-track">
                <div class="volume-played" :style="{ width: volume + '%' }"></div>
              </div>
            </div>
          </div>
          
          <!-- 功能按钮 -->
          <div class="action-buttons">
            <button class="control-btn" @click="downloadCurrent">
              <span class="icon">⬇</span>
            </button>
            <button class="control-btn" @click="togglePlaylist">
              <span class="icon">☰</span>
            </button>
          </div>
        </div>
      </div>
      
      <!-- 歌词区域 -->
      <transition name="fade">
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
      </transition>
    </div>
  </transition>
  
  <!-- 播放列表弹窗 -->
  <transition name="slide-right">
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
            :class="{ 'active': currentIndex === index }"
            class="playlist-item"
            @click="playTrack(index)"
          >
            <div class="track-index">{{ index + 1 }}</div>
            <div class="track-info">
              <div class="track-name">{{ track.name }}</div>
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
          <el-button type="text" @click="clearPlaylist">清空列表</el-button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { settings } from '../utils/settingsManager.js'
import { saveBlob, sanitizeFilename } from '../utils/downloadHelper.js'
import { embedMetadata } from '../services/metadataWriter.js'
import musicApi from '../services/musicApi.js'

const props = defineProps({
  playlist: {
    type: Array,
    default: () => []
  },
  autoplay: {
    type: Boolean,
    default: false
  },
  currentIndex: {
    type: Number,
    default: 0
  }
})

const audio = ref(null)
const isPlaying = ref(false)
const isVisible = ref(false)
const showLyrics = ref(false)
const showPlaylistModal = ref(false)
const currentIndex = ref(0)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(80)
const isMuted = ref(false)
const lyricsContainer = ref(null)
const progressTrack = ref(null)

const currentTrack = computed(() => {
  return props.playlist[currentIndex.value] || null
})

const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value < props.playlist.length - 1)

const progressPercent = computed(() => {
  if (duration.value === 0) return 0
  return Math.round((currentTime.value / duration.value) * 100)
})

const parsedLyrics = computed(() => {
  if (!currentTrack.value?.lrc) return []
  const lyrics = []
  const lines = currentTrack.value.lrc.split('\n')
  lines.forEach(line => {
    const matches = line.match(/\[(\d{2}):(\d{2})\.(\d{2,3})\](.+)/)
    if (matches) {
      const time = parseInt(matches[1]) * 60 + parseInt(matches[2]) + parseInt(matches[3]) / 100
      lyrics.push({ time, text: matches[4].trim() })
    }
  })
  return lyrics
})

const currentLyricIndex = computed(() => {
  if (parsedLyrics.value.length === 0) return -1
  const time = currentTime.value / 1000
  for (let i = parsedLyrics.value.length - 1; i >= 0; i--) {
    if (parsedLyrics.value[i].time <= time) {
      return i
    }
  }
  return -1
})

const getVolumeIcon = () => {
  if (isMuted.value || volume.value === 0) return '🔇'
  if (volume.value < 50) return '🔉'
  return '🔊'
}

const formatTime = (ms) => {
  const seconds = Math.floor(ms / 1000)
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const initAudio = () => {
  if (audio.value) {
    audio.value.pause()
    audio.value = null
  }
  audio.value = new Audio()
  audio.value.volume = volume.value / 100
  audio.value.addEventListener('timeupdate', onTimeUpdate)
  audio.value.addEventListener('loadedmetadata', onLoadedMetadata)
  audio.value.addEventListener('ended', onEnded)
  audio.value.addEventListener('error', onError)
}

const onTimeUpdate = () => {
  if (audio.value) {
    currentTime.value = audio.value.currentTime * 1000
    scrollToCurrentLyric()
  }
}

const onLoadedMetadata = () => {
  if (audio.value) {
    duration.value = audio.value.duration * 1000
  }
}

const onEnded = () => {
  if (hasNext.value) {
    playNext()
  } else {
    isPlaying.value = false
  }
}

const onError = (e) => {
  ElMessage.error(`播放失败: ${e.target.error?.message || '未知错误'}`)
  isPlaying.value = false
}

const playTrack = async (index) => {
  if (index < 0 || index >= props.playlist.length) return
  
  currentIndex.value = index
  const track = props.playlist[index]
  
  if (!track?.url) {
    try {
      const result = await musicApi.getMusicUrl(track.id, settings.selectedQuality || 'lossless')
      if (result?.url) {
        track.url = result.url
      }
    } catch (error) {
      ElMessage.error(`获取播放链接失败: ${error.message}`)
      return
    }
  }
  
  if (!audio.value) {
    initAudio()
  }
  
  audio.value.src = track.url
  audio.value.play().then(() => {
    isPlaying.value = true
    isVisible.value = true
  }).catch((err) => {
    ElMessage.error(`播放失败: ${err.message}`)
  })
}

const togglePlay = () => {
  if (!audio.value) {
    if (props.playlist.length > 0) {
      playTrack(currentIndex.value)
    }
    return
  }
  
  if (isPlaying.value) {
    audio.value.pause()
    isPlaying.value = false
  } else {
    audio.value.play()
    isPlaying.value = true
  }
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

const seekTo = (e) => {
  if (!audio.value || !progressTrack.value) return
  const rect = progressTrack.value.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  audio.value.currentTime = (percent * duration.value) / 1000
}

const setVolume = (e) => {
  if (!audio.value) return
  const target = e.currentTarget
  const rect = target.getBoundingClientRect()
  const percent = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100))
  volume.value = Math.round(percent)
  audio.value.volume = volume.value / 100
  isMuted.value = volume.value === 0
}

const toggleMute = () => {
  if (!audio.value) return
  
  if (isMuted.value) {
    audio.value.volume = volume.value / 100
    isMuted.value = false
  } else {
    audio.value.volume = 0
    isMuted.value = true
  }
}

const toggleLyrics = () => {
  showLyrics.value = !showLyrics.value
}

const togglePlaylist = () => {
  showPlaylistModal.value = !showPlaylistModal.value
}

const clearPlaylist = () => {
  if (audio.value) {
    audio.value.pause()
  }
  isPlaying.value = false
  isVisible.value = false
  currentIndex.value = 0
  currentTime.value = 0
  duration.value = 0
}

const downloadCurrent = async () => {
  if (!currentTrack.value?.url) {
    ElMessage.warning('当前没有可下载的歌曲')
    return
  }
  
  try {
    const response = await fetch(currentTrack.value.url)
    if (!response.ok) {
      throw new Error('下载失败')
    }
    
    const audioBuffer = await response.arrayBuffer()
    const contentType = response.headers.get('Content-Type') || ''
    
    let extension = '.mp3'
    if (contentType.includes('flac')) extension = '.flac'
    else if (contentType.includes('mp4')) extension = '.m4a'
    
    let finalBuffer = audioBuffer
    if (settings.writeMetadata && (extension === '.mp3' || extension === '.flac')) {
      const metadata = {
        name: currentTrack.value.name,
        artist: currentTrack.value.artist,
        album: currentTrack.value.album,
        lyrics: currentTrack.value.lrc,
        cover: currentTrack.value.cover
      }
      try {
        finalBuffer = await embedMetadata(audioBuffer, metadata, extension)
      } catch {
        // 元数据写入失败，继续下载
      }
    }
    
    const filename = sanitizeFilename(`${currentTrack.value.name} - ${currentTrack.value.artist}${extension}`)
    const blob = new Blob([finalBuffer], { type: contentType })
    saveBlob(blob, filename)
    ElMessage.success(`已下载: ${currentTrack.value.name}`)
  } catch (error) {
    ElMessage.error(`下载失败: ${error.message}`)
  }
}

const scrollToCurrentLyric = () => {
  if (!lyricsContainer.value || currentLyricIndex.value < 0) return
  
  const currentLine = lyricsContainer.value.children[currentLyricIndex.value]
  if (currentLine) {
    const containerTop = lyricsContainer.value.scrollTop
    const lineTop = currentLine.offsetTop
    const containerHeight = lyricsContainer.value.clientHeight
    const lineHeight = currentLine.offsetHeight
    const targetScroll = lineTop - containerHeight / 2 + lineHeight / 2
    lyricsContainer.value.scrollTo({
      top: Math.max(0, targetScroll),
      behavior: 'smooth'
    })
  }
}

watch(() => props.playlist, (newPlaylist) => {
  if (newPlaylist.length > 0 && props.autoplay && !isPlaying.value) {
    const index = props.currentIndex >= 0 && props.currentIndex < newPlaylist.length 
      ? props.currentIndex 
      : 0
    playTrack(index)
  }
}, { immediate: true })

watch(isPlaying, (playing) => {
  if (!playing && currentTime.value >= duration.value - 1000) {
    setTimeout(() => {
      if (!isPlaying.value) {
        isVisible.value = false
      }
    }, 3000)
  }
})

onMounted(() => {
  initAudio()
})

onUnmounted(() => {
  if (audio.value) {
    audio.value.pause()
    audio.value.removeEventListener('timeupdate', onTimeUpdate)
    audio.value.removeEventListener('loadedmetadata', onLoadedMetadata)
    audio.value.removeEventListener('ended', onEnded)
    audio.value.removeEventListener('error', onError)
    audio.value = null
  }
})
</script>

<style scoped>
.bottom-player {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding: 12px 24px;
  z-index: 1000;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.bottom-player.expanded {
  height: 400px;
}

.player-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.player-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 0 0 280px;
}

.cover-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: transform 0.3s ease;
}

.cover-wrapper:hover {
  transform: scale(1.05);
}

.cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover.playing {
  animation: rotate 8s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.music-icon {
  font-size: 24px;
  color: white;
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-name {
  font-size: 15px;
  font-weight: 600;
  color: white;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artist-name {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 2px;
}

.player-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  min-width: 300px;
}

.controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.control-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.control-btn .icon {
  font-size: 16px;
}

.play-btn {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
}

.play-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5);
}

.play-btn .icon {
  font-size: 20px;
  padding-left: 2px;
}

.progress-area {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 500px;
}

.time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  width: 48px;
  text-align: center;
}

.progress-bar {
  flex: 1;
  cursor: pointer;
}

.progress-track {
  position: relative;
  height: 6px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  overflow: visible;
}

.progress-played {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 3px;
  transition: width 0.1s linear;
}

.progress-dot {
  position: absolute;
  top: 50%;
  width: 14px;
  height: 14px;
  background: white;
  border: 3px solid #667eea;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: left 0.1s linear;
  opacity: 0;
}

.progress-bar:hover .progress-dot {
  opacity: 1;
}

.player-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 0 0 200px;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.volume-bar {
  width: 80px;
  cursor: pointer;
}

.volume-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.volume-played {
  height: 100%;
  background: #667eea;
  border-radius: 2px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.lyrics-panel {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
  border-top-left-radius: 20px;
  border-top-right-radius: 20px;
  padding: 24px;
  height: calc(100% - 80px);
  display: flex;
  flex-direction: column;
}

.lyrics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.lyrics-title {
  font-size: 16px;
  font-weight: 600;
  color: white;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.close-btn .icon {
  font-size: 14px;
}

.lyrics-content {
  flex: 1;
  overflow-y: auto;
  text-align: center;
  padding: 20px 0;
}

.lyric-line {
  padding: 12px 0;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.6);
  transition: all 0.3s ease;
}

.lyric-line.current {
  color: #667eea;
  font-size: 18px;
  font-weight: 500;
}

.no-lyrics {
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px;
  padding: 40px 0;
}

.playlist-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 1001;
  display: flex;
  justify-content: flex-end;
}

.playlist-modal {
  width: 400px;
  height: 100%;
  background: #1e1e2e;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.playlist-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 0;
}

.playlist-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.playlist-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.playlist-item.active {
  background: rgba(102, 126, 234, 0.2);
}

.track-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
}

.playlist-item.active .track-index {
  background: #667eea;
  color: white;
}

.track-info {
  flex: 1;
  min-width: 0;
}

.track-name {
  font-size: 14px;
  font-weight: 500;
  color: white;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-artist {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 2px;
}

.playing-indicator {
  color: #667eea;
}

.playing-dot {
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.empty-playlist {
  text-align: center;
  padding: 60px 20px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: flex-end;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: opacity 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .bottom-player {
    padding: 10px 16px;
  }
  
  .player-main {
    gap: 12px;
  }
  
  .player-left {
    flex: 0 0 auto;
    gap: 12px;
  }
  
  .cover-wrapper {
    width: 48px;
    height: 48px;
  }
  
  .song-name {
    font-size: 13px;
  }
  
  .artist-name {
    font-size: 11px;
  }
  
  .player-center {
    min-width: auto;
    flex: 1;
  }
  
  .controls {
    gap: 12px;
  }
  
  .control-btn {
    width: 36px;
    height: 36px;
  }
  
  .play-btn {
    width: 48px;
    height: 48px;
  }
  
  .progress-area {
    gap: 8px;
  }
  
  .time {
    font-size: 11px;
    width: 40px;
  }
  
  .player-right {
    flex: 0 0 auto;
    gap: 12px;
  }
  
  .volume-bar {
    width: 60px;
  }
  
  .playlist-modal {
    width: 100%;
  }
}
</style>