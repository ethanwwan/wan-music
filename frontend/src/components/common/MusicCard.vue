<template>
  <div 
    class="music-card" 
    :class="{ 'unavailable': track.unavailable }"
    @click="handleCardClick"
  >
    <div class="card-cover">
      <img 
        v-if="track.picUrl || track.cover" 
        :src="track.picUrl || track.cover" 
        :alt="track.name"
        loading="lazy"
        :class="{ 'grayscale': track.unavailable }"
      />
      <div v-else class="cover-placeholder">
        <el-icon :size="40"><Microphone /></el-icon>
      </div>
      <div class="card-overlay">
        <el-button 
          :icon="isPlaying ? VideoPlay : VideoPlay" 
          circle
          size="large"
          :disabled="track.unavailable"
          @click.stop="handlePlay"
          :title="track.unavailable ? '该歌曲无版权' : '播放'"
        />
      </div>
    </div>
    <div class="card-content">
      <div class="track-title-line">
        <h3 class="track-name" :title="track.name">{{ track.name || '未知歌曲' }}</h3>
        <span v-if="track.unavailable" class="unavailable-tag">无版权</span>
      </div>
      <p class="track-artist" :title="track.artist">{{ track.artist || '未知艺术家' }}</p>
      <div class="track-meta">
        <el-tag v-if="track.album" size="small" :title="track.album">
          {{ track.album }}
        </el-tag>
        <span v-if="track.duration" class="duration">
          {{ formatDuration(track.duration) }}
        </span>
      </div>
    </div>
    <div class="card-actions">
      <el-button 
        :icon="Download" 
        size="small"
        :disabled="track.unavailable"
        @click.stop="handleDownload"
        :title="track.unavailable ? '该歌曲无版权' : '下载'"
      >
        下载
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Microphone, VideoPlay, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  track: {
    type: Object,
    required: true,
    default: () => ({
      id: null,
      name: '',
      artist: '',
      album: '',
      picUrl: '',
      cover: '',
      duration: 0,
      unavailable: false
    })
  },
  isPlaying: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click', 'play', 'download'])

const formatDuration = (ms) => {
  if (!ms) return '--:--'
  const seconds = Math.floor(ms / 1000)
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const handleCardClick = () => {
  if (props.track.unavailable) {
    ElMessage.warning(`《${props.track.name}》因版权问题暂时无法播放`)
    return
  }
  emit('click', props.track)
}

const handlePlay = () => {
  if (props.track.unavailable) {
    ElMessage.warning(`《${props.track.name}》因版权问题暂时无法播放`)
    return
  }
  emit('play', props.track)
}

const handleDownload = () => {
  if (props.track.unavailable) {
    ElMessage.warning(`《${props.track.name}》因版权问题暂时无法下载`)
    return
  }
  emit('download', props.track)
}
</script>

<style scoped>
.music-card {
  background: var(--el-bg-color);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
  border: 1px solid var(--el-border-color);
}

.music-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  background: var(--el-fill-color-light);
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.music-card:hover .card-cover img {
  transform: scale(1.05);
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
}

.card-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.music-card:hover .card-overlay {
  opacity: 1;
}

.card-content {
  padding: 12px;
}

.track-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-artist {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 0 0 8px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}

.duration {
  margin-left: auto;
}

.card-actions {
  padding: 8px 12px;
  border-top: 1px solid var(--el-border-color);
  display: flex;
  justify-content: flex-end;
}

.track-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.unavailable-tag {
  font-size: 10px;
  color: #ff4d4f;
  background: #fff1f0;
  padding: 2px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}

.music-card.unavailable {
  opacity: 0.7;
  cursor: not-allowed;
}

.music-card.unavailable:hover {
  transform: none;
  box-shadow: none;
}

.music-card.unavailable .card-cover img.grayscale {
  filter: grayscale(100%);
}

.music-card.unavailable .track-name,
.music-card.unavailable .track-artist {
  color: #999;
}

.music-card.unavailable .card-overlay {
  opacity: 1;
  background: rgba(0, 0, 0, 0.3);
}

.music-card.unavailable :deep(.el-button) {
  opacity: 0.5;
}
</style>
