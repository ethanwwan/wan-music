<template>
  <transition name="slide-up">
    <div v-show="isVisible && playlist.length > 0" class="bottom-player" :class="{ 'expanded': showLyrics }">
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
          <!-- 功能按钮 -->
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
import musicApi, { getMusicUrl, getLyrics } from '../services/musicApi.js'

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
const lyricsContainer = ref(null)
const progressTrack = ref(null)
const isDownloading = ref(false)
const isLoadingLyrics = ref(false)

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

const formatTime = (ms) => {
  const seconds = Math.floor(ms / 1000)
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const getProxyUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('https')) return url
  return `/stream?url=${encodeURIComponent(url)}`
}

const initAudio = () => {
  if (audio.value) {
    audio.value.pause()
    audio.value = null
  }
  audio.value = new Audio()
  audio.value.volume = 0.8
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
  
  const track = props.playlist[index]
  
  // 版权检查
  if (track?.unavailable) {
    ElMessage.warning(`《${track.name}》因版权问题暂时无法播放`)
    // 尝试播放下一首
    if (index + 1 < props.playlist.length) {
      setTimeout(() => playTrack(index + 1), 500)
    }
    return
  }
  
  // 停止当前播放（防止竞态条件）
  if (audio.value) {
    try {
      audio.value.pause()
      audio.value.currentTime = 0
    } catch (e) {
      console.warn('停止当前播放时出错:', e)
    }
  }
  
  currentIndex.value = index
  
  // 显示播放器
  isVisible.value = true
  
  // 获取播放URL（如果没有的话）
  if (!track?.url) {
    try {
      const result = await getMusicUrl(track.id, settings.selectedQuality || 'lossless')
      if (result?.url) {
        track.url = result.url
      }
    } catch (error) {
      ElMessage.error(`获取播放链接失败: ${error.message}`)
      return
    }
  }
  
  // 获取歌词（如果没有的话）
  if (!track?.lrc) {
    try {
      const lyricsResult = await getLyrics(track.id)
      if (lyricsResult?.lrc) {
        // 确保lrc是字符串格式
        track.lrc = typeof lyricsResult.lrc === 'string' 
          ? lyricsResult.lrc 
          : (lyricsResult.lrc?.lyric || '')
        track.tlyric = typeof lyricsResult.tlyric === 'string'
          ? lyricsResult.tlyric
          : (lyricsResult.tlyric?.lyric || '')
      }
    } catch {
      // 歌词获取失败，继续播放
    }
  }
  
  // 获取封面（如果没有的话）- 尝试多种字段名
  if (!track?.cover) {
    track.cover = (
      track?.cover || 
      track?.picUrl || 
      track?.al?.picUrl || 
      track?.album?.coverImgUrl ||
      track?.album?.picUrl ||
      ''
    )
  }
  
  if (!audio.value) {
    initAudio()
  }
  
  audio.value.src = getProxyUrl(track.url)
  audio.value.play().then(() => {
    isPlaying.value = true
  }).catch((err) => {
    // 处理播放错误
    if (err.name === 'AbortError') {
      console.warn('播放被中断，可能是快速切换歌曲:', err)
    } else {
      ElMessage.error(`播放失败: ${err.message}`)
    }
    isPlaying.value = false
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
  if (!audio.value) {
    console.warn('Audio not initialized')
    return
  }
  if (!progressTrack.value) {
    console.warn('Progress track not found')
    return
  }
  
  const rect = progressTrack.value.getBoundingClientRect()
  const clickX = e.clientX - rect.left
  const percent = Math.max(0, Math.min(1, clickX / rect.width))
  
  // 设置当前播放时间
  const newTime = percent * (duration.value / 1000)
  audio.value.currentTime = newTime
  
  // 立即更新 currentTime 显示
  currentTime.value = newTime * 1000
  
  console.log('Seek to:', {
    percent: (percent * 100).toFixed(2) + '%',
    newTime: newTime.toFixed(2) + 's',
    duration: (duration.value / 1000).toFixed(2) + 's'
  })
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
  if (isDownloading.value) return
  
  if (!currentTrack.value?.url) {
    ElMessage.warning('当前没有可下载的歌曲')
    return
  }
  
  isDownloading.value = true
  
  try {
    const response = await fetch(getProxyUrl(currentTrack.value.url))
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
  } finally {
    isDownloading.value = false
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

// 监听播放列表变化
watch(() => props.playlist, (newPlaylist, oldPlaylist) => {
  if (newPlaylist.length > 0) {
    const index = props.currentIndex >= 0 && props.currentIndex < newPlaylist.length 
      ? props.currentIndex 
      : 0
    
    // 检查是否切换了歌曲（通过对比当前歌曲ID）
    const oldTrackId = oldPlaylist?.[currentIndex.value]?.id
    const newTrackId = newPlaylist[index]?.id
    
    // 如果是同一首歌且正在播放，不做处理
    if (oldTrackId === newTrackId && isPlaying.value) {
      return
    }
    
    // 重置播放状态
    currentTime.value = 0
    duration.value = 0
    
    // 如果是自动播放或者切换了歌曲，重新播放
    if (props.autoplay || oldTrackId !== newTrackId) {
      playTrack(index)
    }
  }
}, { immediate: true })

// 监听当前索引变化
watch(() => props.currentIndex, (newIndex, oldIndex) => {
  if (newIndex !== oldIndex && props.playlist.length > 0) {
    // 重置播放状态
    currentTime.value = 0
    duration.value = 0
    isPlaying.value = false
    // 播放新歌曲
    if (props.autoplay) {
      playTrack(newIndex)
    }
  }
})

watch(isPlaying, (playing) => {
  // 播放时显示播放器，播放结束后不自动隐藏
  if (playing) {
    isVisible.value = true
    // 清除可能存在的自动隐藏定时器
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
  }
})

// 滚动监听相关
let lastScrollY = 0
let hideTimer = null
let showTimer = null

const handleScroll = () => {
  const currentScrollY = window.scrollY
  
  if (currentScrollY > lastScrollY && currentScrollY > 100) {
    // 向上滚动超过100px，隐藏播放器
    if (isVisible.value && isPlaying.value) {
      isVisible.value = false
    }
    // 清除显示定时器
    if (showTimer) {
      clearTimeout(showTimer)
      showTimer = null
    }
  } else if (currentScrollY < lastScrollY) {
    // 向下滚动，显示播放器
    if (!isVisible.value) {
      isVisible.value = true
    }
    // 清除之前的定时器
    if (hideTimer) {
      clearTimeout(hideTimer)
      hideTimer = null
    }
  }
  
  lastScrollY = currentScrollY
}

onMounted(() => {
  initAudio()
  window.addEventListener('scroll', handleScroll, { passive: true })
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
  window.removeEventListener('scroll', handleScroll)
  if (hideTimer) clearTimeout(hideTimer)
  if (showTimer) clearTimeout(showTimer)
})
</script>

<style scoped>
.bottom-player {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(30, 30, 46, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 12px 24px;
  z-index: 1000;
  box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.15);
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

/* Loading 旋转动画 */
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: btn-spin 0.8s linear infinite;
}

@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
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
  flex-shrink: 0;
}

.progress-bar {
  flex: 1;
  cursor: pointer;
  padding: 8px 0; /* 增加垂直点击区域 */
  margin: -8px 0; /* 抵消padding，保持布局不变 */
}

.progress-track {
  position: relative;
  height: 6px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  overflow: visible;
  transition: height 0.2s ease;
}

.progress-bar:hover .progress-track {
  height: 8px; /* 悬停时变高 */
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
  transition: left 0.1s linear, opacity 0.2s ease, transform 0.2s ease;
  opacity: 0;
  pointer-events: none;
}

.progress-bar:hover .progress-dot {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1.2);
}

.player-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 0 0 120px;
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

.playlist-item.unavailable {
  opacity: 0.6;
  cursor: not-allowed;
}

.playlist-item.unavailable:hover {
  background: transparent;
}

.playlist-item.unavailable .track-index {
  background: rgba(239, 68, 68, 0.3);
  color: #ff4d4f;
}

.playlist-item.unavailable .track-name,
.playlist-item.unavailable .track-artist {
  color: rgba(255, 255, 255, 0.4);
}

.unavailable-badge {
  font-size: 10px;
  color: #ff4d4f;
  background: rgba(239, 68, 68, 0.2);
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
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