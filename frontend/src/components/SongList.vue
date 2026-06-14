<template>
  <div :class="listContainerClass">
    <!-- 单曲列表样式 -->
    <template v-if="listType === 'song'">
      <!-- 详情头部（歌单/专辑/歌手信息） -->
      <div v-if="detailInfo" class="detail-header">
        <div class="header-left">
          <div class="detail-cover-wrapper">
            <img 
              v-if="detailInfo.coverImgUrl"
              :src="detailInfo.coverImgUrl" 
              :alt="detailInfo.name" 
              class="detail-cover"
              @error="handleCoverError($event)"
            />
            <div v-else class="cover-placeholder"></div>
          </div>
          <div class="detail-info">
            <h1 class="detail-name">{{ detailInfo.name }}</h1>
            <div class="detail-meta">
              <span class="meta-item">{{ creatorLabel }}：{{ detailInfo.creator }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">共 {{ totalTracks }} 首歌曲</span>
            </div>
            <!-- 下载进度条 -->
            <div v-if="downloadProgress.isDownloading" class="download-progress-bar">
              <a-progress 
                :percent="downloadProgress.percentage" 
                :status="downloadProgress.status"
                :stroke-width="6"
                :show-text="false"
              />
              <div class="progress-info">
                <span class="current-song">正在下载：{{ downloadProgress.currentSong || '准备中...' }}</span>
                <span class="progress-text">{{ downloadProgress.completed }}/{{ downloadProgress.total }} ({{ downloadProgress.percentage }}%)</span>
              </div>
            </div>
          </div>
        </div>
        <div class="header-right">
          <a-button 
            type="primary" 
            @click="handleBatchDownload" 
            :disabled="downloadProgress.isDownloading"
            :loading="downloadProgress.isDownloading"
          >
            {{ downloadProgress.isDownloading ? '下载中...' : '批量打包下载' }}
          </a-button>
        </div>
      </div>

      <!-- 歌曲表格 -->
      <div v-if="paginatedTracks.length > 0" class="tracks-table-wrapper">
        <table class="tracks-table">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th class="col-cover"></th>
              <th class="col-name">歌名</th>
              <th class="col-artist">歌手</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="(track, index) in paginatedTracks" 
              :key="track.id"
              class="track-row"
              :class="{ 
                'selected': selectedTrack && selectedTrack.id === track.id,
                'unavailable': isTrackUnavailable(track)
              }"
              @click="handleTrackClick(track)"
            >
              <td class="col-index">
                <span>{{ (currentPage - 1) * pageSize + index + 1 }}</span>
              </td>
              <td class="col-cover">
                <div class="track-cover-wrapper">
                  <img
                    v-if="getCover(track)"
                    :src="getCover(track)"
                    :alt="track.name"
                    class="track-cover"
                    :class="{ 'grayscale': isTrackUnavailable(track) }"
                    loading="lazy"
                    @error="handleTrackCoverError($event)"
                  />
                  <div v-else class="track-cover-placeholder"></div>
                </div>
              </td>
              <td class="col-name">
                <span class="track-name" :class="{ 'unavailable-text': isTrackUnavailable(track) }">{{ track.name }}</span>
                <span v-if="isTrackUnavailable(track)" class="unavailable-reason">无版权</span>
                <span 
                  v-if="track.source" 
                  class="source-tag"
                  :style="{ backgroundColor: getSourceInfo(track.source)?.color + '20', color: getSourceInfo(track.source)?.color }"
                >
                  {{ getSourceInfo(track.source)?.name || track.source }}
                </span>
              </td>
              <td class="col-artist" :class="{ 'unavailable-text': isTrackUnavailable(track) }">{{ getArtist(track) }}</td>
              <td class="col-action">
                <a-button 
                  type="text"
                  :disabled="parsingTrackId === track.id && parsingType === 'play' || isTrackUnavailable(track)"
                  :loading="parsingTrackId === track.id && parsingType === 'play'"
                  :title="isTrackUnavailable(track) ? '该歌曲无版权' : '播放'"
                  @click.stop="playTrack(track)"
                >
                  <template #icon><PlayCircleOutlined /></template>
                </a-button>
                <a-button 
                  type="text"
                  :disabled="parsingTrackId === track.id && parsingType === 'download' || isTrackUnavailable(track)"
                  :loading="parsingTrackId === track.id && parsingType === 'download'"
                  :title="isTrackUnavailable(track) ? '该歌曲无版权' : '下载'"
                  @click.stop="downloadSingle(track)"
                >
                  <template #icon><ArrowDownOutlined /></template>
                </a-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 - 只有超过1页时才显示 -->
      <Pagination 
        v-if="Math.ceil(sortedTracks.length / pageSize) > 1"
        :total-count="sortedTracks.length"
        :page-size="pageSize"
        :model-value="currentPage"
        @update:model-value="handlePageChange"
      />
    </template>

    <!-- 歌手列表样式 -->
    <template v-else-if="listType === 'artist'">
      <div class="artist-grid">
        <div 
          v-for="artist in items" 
          :key="artist.id" 
          class="artist-card"
        >
          <div class="artist-cover-wrapper">
            <img 
              v-if="artist.avatarUrl"
              :src="artist.avatarUrl" 
              :alt="artist.name" 
              class="artist-cover"
              loading="lazy"
              @error="handleImageError($event, 'artist')"
            />
            <div v-else class="artist-cover-placeholder"></div>
          </div>
          <div class="artist-info">
            <h4 class="artist-name">{{ artist.name }}</h4>
            <p class="artist-music-count">{{ artist.musicCount }} 首歌曲</p>
          </div>
          <div class="artist-action">
            <a-button size="middle" type="primary" @click.stop="handleItemClick(artist, 'artist')">
              解析歌手
            </a-button>
          </div>
        </div>
      </div>
    </template>

    <!-- 歌单/专辑列表样式 -->
    <template v-else-if="listType === 'playlist' || listType === 'album'">
      <div :class="listType === 'playlist' ? 'playlist-grid' : 'album-grid'">
        <div 
          v-for="item in items" 
          :key="item.id" 
          :class="listType === 'playlist' ? 'playlist-card' : 'album-card'"
          @click="handleItemClick(item, 'select')"
        >
          <div :class="listType === 'playlist' ? 'playlist-cover-wrapper' : 'album-cover-wrapper'">
            <img 
              v-if="item.coverImgUrl"
              :src="item.coverImgUrl" 
              :alt="item.name" 
              :class="listType === 'playlist' ? 'playlist-cover' : 'album-cover'"
              loading="lazy"
              @error="handleImageError($event, listType)"
            />
            <div v-else :class="listType === 'playlist' ? 'playlist-cover-placeholder' : 'album-cover-placeholder'"></div>
            <span 
              v-if="item.source" 
              :class="listType === 'playlist' ? 'playlist-source-tag' : 'album-source-tag'"
            >
              {{ getSourceInfo(item.source)?.name || item.source }}
            </span>
            <div :class="listType === 'playlist' ? 'playlist-overlay' : 'album-overlay'">
              <span class="track-count">{{ item.trackCount }} 首</span>
            </div>
          </div>
          <div :class="listType === 'playlist' ? 'playlist-info' : 'album-info'">
            <h4 :class="listType === 'playlist' ? 'playlist-name' : 'album-name'">{{ item.name }}</h4>
            <p :class="listType === 'playlist' ? 'playlist-creator' : 'album-artist'">
              {{ listType === 'playlist' ? (typeof item.creator === 'object' ? item.creator.name : item.creator) : (typeof item.artist === 'object' ? item.artist.name : item.artist) }}
            </p>
          </div>
          <div :class="listType === 'playlist' ? 'playlist-action' : 'album-action'">
            <a-button size="middle" type="primary" @click.stop="handleItemClick(item, listType)">
              解析{{ listType === 'playlist' ? '歌单' : '专辑' }}
            </a-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, shallowRef } from 'vue'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, ArrowDownOutlined } from '@ant-design/icons-vue'
import { batchDownloadMusic, parseMusicInfo } from '../services/musicApi.js'
import { settings } from '../utils/settingsManager.js'
import { saveBlob, sanitizeFilename } from '../utils/downloadHelper.js'
import { embedMetadata } from '../services/metadataWriter.js'
import Pagination from './Pagination.vue'
import { dataSources } from '../utils/dataSourceConfig.js'

const props = defineProps({
  // 列表类型：song / artist / playlist / album
  type: {
    type: String,
    default: 'song',
    validator: (value) => ['song', 'artist', 'playlist', 'album'].includes(value)
  },
  // 列表数据
  items: {
    type: Array,
    default: () => []
  },
  // 单曲列表相关
  detailInfo: {
    type: Object,
    default: null
  },
  currentPage: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 20
  },
  totalTracks: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits([
  'track-selected',
  'track-parsed',
  'track-play',
  'page-change',
  'item-click',
  'select',
  'track-unavailable'
])

// 计算列表类型
const listType = computed(() => props.type)

// 计算容器类名
const listContainerClass = computed(() => {
  if (props.type === 'song' && props.detailInfo) {
    return 'detail-view'
  }
  return 'song-list-panel'
})

// 创建者标签
const creatorLabel = computed(() => {
  if (props.detailInfo?.isAlbum) return '作者'
  if (props.detailInfo?.isArtist) return '歌手'
  return '创建者'
})

// 歌曲列表（保持原顺序，不排序）
const sortedTracks = computed(() => {
  return [...props.items]
})

// 分页后的歌曲列表
const paginatedTracks = computed(() => {
  if (props.totalTracks > 0) {
    const start = (props.currentPage - 1) * props.pageSize
    const end = start + props.pageSize
    return sortedTracks.value.slice(start, end)
  }
  return sortedTracks.value
})

// 状态
const selectedTrack = ref(null)
const parsingTrackId = ref(null)
const parsingType = ref(null)

// 不可用歌曲ID集合（用于跟踪无版权歌曲）
const unavailableTrackIds = shallowRef(new Set())

// 标记歌曲为不可用（无版权）
const markTrackUnavailable = (track) => {
  // 添加到不可用集合
  const newSet = new Set(unavailableTrackIds.value)
  newSet.add(track.id)
  unavailableTrackIds.value = newSet
  
  // 直接设置歌曲的 unavailable 属性
  track.unavailable = true
  
  // 通知父组件更新歌曲数据
  emit('track-unavailable', track)
}

// 判断歌曲是否不可用
const isTrackUnavailable = (track) => {
  return track.unavailable || unavailableTrackIds.value.has(track.id)
}

// 下载进度状态
const downloadProgress = ref({
  isDownloading: false,
  percentage: 0,
  status: '',
  currentSong: '',
  total: 0,
  completed: 0,
  failed: 0
})

// 工具方法

const getCover = (track) => {
  const coverUrl = track?.picUrl || track?.cover || track?.al?.picUrl || track?.album?.picUrl || props.detailInfo?.coverImgUrl || ''
  return coverUrl
}

const getArtist = (track) => {
  return (
    track?.artist ||
    track?.singer ||
    (typeof track?.artists === 'string' ? track.artists : null) ||
    (Array.isArray(track?.artists) && track.artists[0]?.name) ||
    (Array.isArray(track?.ar) && track.ar[0]?.name) ||
    ''
  )
}

const getSourceInfo = (sourceId) => {
  return dataSources.find(s => s.id === sourceId) || null
}

const getAlbum = (track) => {
  return track?.album || track?.al?.name || ''
}

// 图片错误处理
const handleCoverError = (event) => {
  const target = event.target
  target.style.display = 'none'
  const placeholder = target.parentElement.querySelector('.cover-placeholder')
  if (placeholder) {
    placeholder.style.display = 'flex'
  }
}

const handleTrackCoverError = (event) => {
  const target = event.target
  target.style.display = 'none'
  const placeholder = target.parentElement.querySelector('.track-cover-placeholder')
  if (placeholder) {
    placeholder.style.display = 'flex'
  }
}

const handleImageError = (event, type) => {
  const target = event.target
  target.style.display = 'none'
  const placeholderClass = type === 'artist' ? '.artist-cover-placeholder' : 
                           type === 'playlist' ? '.playlist-cover-placeholder' : '.album-cover-placeholder'
  const placeholder = target.parentElement.querySelector(placeholderClass)
  if (placeholder) {
    placeholder.style.display = 'flex'
  }
}

// 歌曲操作
const handleTrackClick = (track) => {
  if (isTrackUnavailable(track)) {
    message.warning(`《${track.name}》因版权问题暂时无法播放`)
    return
  }
  selectedTrack.value = track
  emit('track-selected', track)
}

const playTrack = async (track) => {
  if (isTrackUnavailable(track)) {
    message.warning(`《${track.name}》因版权问题暂时无法播放`)
    return
  }
  
  parsingTrackId.value = track.id
  parsingType.value = 'play'
  
  try {
    const qualityValue = settings.selectedQuality || 'lossless'
    const songUrl = `https://music.163.com/song?id=${track.id}`
    
    const musicInfo = await parseMusicInfo(songUrl, qualityValue)
    
    if (!musicInfo?.url) {
      // 标记为不可用
      markTrackUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法播放`)
      return
    }
    
    emit('track-parsed', { track, quality: qualityValue })
    // 只传递当前歌曲信息，不传递列表
    emit('track-play', { ...track, url: musicInfo.url, lrc: musicInfo.lrc })
    message.success(`开始播放：${track.name}`)
  } catch (error) {
    // 如果是版权相关错误，标记为不可用
    if (error.message?.includes('已下架') || error.message?.includes('无法获取')) {
      markTrackUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法播放`)
    } else {
      message.error(`播放失败：${error.message}`)
    }
  } finally {
    parsingTrackId.value = null
    parsingType.value = null
  }
}

const downloadSingle = async (track) => {
  if (isTrackUnavailable(track)) {
    message.warning(`《${track.name}》因版权问题暂时无法下载`)
    return
  }
  
  parsingTrackId.value = track.id
  parsingType.value = 'download'
  
  try {
    const qualityValue = settings.selectedQuality || 'lossless'
    const writeMetadata = settings.writeMetadata !== false
    const filenameFormat = settings.filenameFormat || 'song-artist'
    const songUrl = `https://music.163.com/song?id=${track.id}`
    
    const musicInfo = await parseMusicInfo(songUrl, qualityValue)
    
    if (!musicInfo?.url) {
      // 标记为不可用
      markTrackUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法下载`)
      return
    }
    
    const extension = musicInfo.fileExtension || '.mp3'
    
    const response = await fetch(musicInfo.url)
    if (!response.ok) {
      throw new Error('下载失败')
    }
    
    const audioBuffer = await response.arrayBuffer()
    
    let finalBuffer = audioBuffer
    if (writeMetadata && (extension === '.mp3' || extension === '.flac')) {
      const metadata = {
        name: track.name,
        artist: getArtist(track),
        album: getAlbum(track),
        lyrics: musicInfo.lrc || '',
        cover: getCover(track)
      }
      try {
        finalBuffer = await embedMetadata(audioBuffer, metadata, extension)
      } catch {}
    }
    
    const artist = getArtist(track)
    const trackName = track.name
    let filename
    if (filenameFormat === 'artist-song') {
      filename = sanitizeFilename(`${artist} - ${trackName}${extension}`)
    } else if (filenameFormat === 'song') {
      filename = sanitizeFilename(`${trackName}${extension}`)
    } else {
      filename = sanitizeFilename(`${trackName} - ${artist}${extension}`)
    }
    
    const mimeTypes = {
      '.mp3': 'audio/mpeg',
      '.flac': 'audio/flac',
      '.m4a': 'audio/mp4'
    }
    const mimeType = mimeTypes[extension] || 'audio/mpeg'
    
    const blob = new Blob([finalBuffer], { type: mimeType })
    saveBlob(blob, filename)
    
    message.success(`已下载：${track.name}`)
  } catch (error) {
    // 如果是版权相关错误，标记为不可用
    if (error.message?.includes('已下架') || error.message?.includes('无法获取')) {
      markTrackUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法下载`)
    } else {
      message.error(`下载失败：${error.message}`)
    }
  } finally {
    parsingTrackId.value = null
    parsingType.value = null
  }
}

// 批量下载
const handleBatchDownload = async () => {
  if (!props.items || props.items.length === 0) {
    message.warning('没有可下载的歌曲')
    return
  }

  try {
    const availableTracks = props.items.filter(track => !track.unavailable)
    const unavailableCount = props.items.length - availableTracks.length
    
    if (availableTracks.length === 0) {
      message.warning('所有歌曲都因版权问题无法下载')
      return
    }
    
    downloadProgress.value = {
      isDownloading: true,
      percentage: 0,
      status: '',
      currentSong: '',
      total: availableTracks.length,
      completed: 0,
      failed: 0
    }

    let messageText = `开始批量下载 ${availableTracks.length} 首歌曲...`
    if (unavailableCount > 0) {
      messageText += `（${unavailableCount} 首因版权问题跳过）`
    }
    message.info(messageText)

    const musicList = []
    for (const track of availableTracks) {
      try {
        const songUrl = `https://music.163.com/song?id=${track.id}`
        
        const quality = settings.selectedQuality || 'lossless'
        const musicInfo = await parseMusicInfo(songUrl, quality)
        if (musicInfo && musicInfo.url) {
          musicList.push({
            id: track.id,
            name: track.name,
            artist: getArtist(track),
            album: getAlbum(track),
            url: musicInfo.url,
            cover: getCover(track),
            lrc: musicInfo.lrc || '',
            fileExtension: musicInfo.fileExtension || '.mp3'
          })
        }
      } catch (err) {
        console.error(`解析歌曲失败: ${track.name} - ${getArtist(track)}`, err)
      }
    }

    if (musicList.length === 0) {
      throw new Error('没有成功解析的歌曲')
    }

    const result = await batchDownloadMusic(
      musicList,
      props.detailInfo?.name || '',
      {
        filenameFormat: settings.filenameFormat || 'artist-song',
        writeMetadata: settings.writeMetadata !== false,
        downloadLrcFile: settings.downloadLrcFile !== false,
        selectedQuality: settings.selectedQuality || 'lossless'
      },
      (progress) => {
        downloadProgress.value.percentage = progress.percentage
        downloadProgress.value.currentSong = progress.current
        downloadProgress.value.completed = progress.completed
        downloadProgress.value.failed = progress.failed
        downloadProgress.value.total = progress.total
      }
    )

    downloadProgress.value.isDownloading = false
    downloadProgress.value.status = result.failed === 0 ? 'success' : 'warning'
    downloadProgress.value.percentage = 100

    if (result.failed === 0) {
      message.success(`批量下载完成！共下载 ${result.completed} 首歌曲`)
    } else {
      message.warning(`下载完成！成功 ${result.completed} 首，失败 ${result.failed} 首`)
    }

  } catch (error) {
    downloadProgress.value.isDownloading = false
    downloadProgress.value.status = 'exception'
    message.error(`批量下载失败: ${error.message}`)
  }
}

// 分页变化
const handlePageChange = (page) => {
  emit('page-change', page)
}

// 列表项点击
const handleItemClick = (item, action) => {
  if (action === 'select') {
    emit('select', item)
  } else {
    emit('item-click', { item, action })
  }
}
</script>

<style>
</style>

<style scoped>
/* 歌曲列表面板 */
.song-list-panel {
  width: 100%;
  margin-top: 0 !important;
  padding-top: 0 !important;
}

/* 详情页面模式 */
.detail-view {
  padding: 0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-border-subtle);
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-surface-white) 100%);
}

.detail-cover-wrapper {
  flex-shrink: 0;
}

.detail-cover {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-md);
  object-fit: cover;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.cover-placeholder {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, color-mix(in srgb, var(--color-primary) 15%, var(--color-surface-container)) 50%, var(--color-primary-light) 100%);
  border-radius: var(--radius-md);
}

.detail-info {
  flex: 1;
  min-width: 0;
  padding-left: 1rem;
}

.detail-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-on-surface);
  margin: 0 0 0.5rem 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 14px;
  color: var(--color-text-muted);
}

.meta-item {
  white-space: nowrap;
}

.meta-separator {
  color: var(--color-outline);
}

.header-right {
  flex-shrink: 0;
}

/* 下载进度条 */
.download-progress-bar {
  margin-top: 1rem;
  width: 100%;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.35rem;
  font-size: 13px;
  width: 100%;
}

.current-song {
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
  margin-right: 1rem;
}

.progress-text {
  color: var(--color-primary);
  font-weight: 600;
  flex-shrink: 0;
  text-align: right;
}

/* 表格容器 */
.tracks-table-wrapper {
  overflow-x: auto;
}

.tracks-table {
  width: 100%;
  border-collapse: collapse;
}

.tracks-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-surface-container-low);
  white-space: nowrap;
  border-radius: 0 !important;
}

.tracks-table td {
  padding: 12px 16px;
  vertical-align: middle;
}

.col-index {
  width: 40px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 14px;
}

.col-cover {
  width: 32px;
  padding: 8px 8px;
}

.track-cover-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.track-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.track-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, color-mix(in srgb, var(--color-primary) 15%, var(--color-surface-container)) 50%, var(--color-primary-light) 100%);
}

.col-name {
  min-width: 200px;
}

.track-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface);
}

.col-artist,
.col-album {
  font-size: 14px;
  color: var(--color-text-muted);
  min-width: 150px;
}

.tracks-table td.col-action {
  min-width: 88px;
  text-align: center;
  padding: 6px 8px;
  margin: 0;
  box-sizing: border-box;
  white-space: nowrap;
  vertical-align: middle;
}

.tracks-table td.col-action :deep(.ant-btn) {
  margin: 0 4px;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.tracks-table td.col-action :deep(.anticon) {
  font-size: 16px;
  line-height: 1;
  color: var(--color-on-surface);
}

.tracks-table td.col-action :deep(.ant-btn-loading .anticon) {
  color: var(--color-on-surface);
}

.tracks-table td.col-action :deep(.ant-btn[disabled] .anticon) {
  color: var(--color-text-muted);
}

.track-row:hover {
  background: var(--color-primary-light);
}

.track-row.selected {
  background: var(--color-primary-light);
}

/* 无版权歌曲样式 */
.track-row.unavailable {
  background-color: #f5f5f5 !important;
  cursor: not-allowed;
  opacity: 0.7;
}

.track-row.unavailable:hover {
  background-color: #e8e8e8 !important;
}

.track-row.unavailable .track-name,
.track-row.unavailable .col-artist {
  color: #999 !important;
}

.track-cover.grayscale {
  filter: grayscale(100%);
  opacity: 0.5;
}

.unavailable-icon {
  color: #ff4d4f;
  font-size: 14px;
}

.unavailable-reason {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 6px;
  font-size: 10px;
  color: #ff4d4f;
  background: #fff1f0;
  border-radius: 3px;
  vertical-align: middle;
}

.source-tag {
  display: inline-block;
  margin-left: 8px;
  padding: 4px;
  font-size: 10px;
  border-radius: 4px;
  vertical-align: middle;
  font-weight: 500;
}

/* 暗色模式 */
.dark .track-row.unavailable {
  background-color: #2a2a2a !important;
}

.dark .track-row.unavailable:hover {
  background-color: #333 !important;
}

.dark .track-row.unavailable .track-name,
.dark .track-row.unavailable .col-artist {
  color: #666 !important;
}

.dark .track-cover.grayscale {
  filter: grayscale(100%);
  opacity: 0.3;
}

.dark .unavailable-reason {
  color: #ff7875;
  background: #2a1a1a;
}

/* ========== 歌手列表样式 ========== */
.artist-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  padding: 0 1.5rem 1.5rem 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

@media (min-width: 640px) {
  .artist-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 768px) {
  .artist-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (min-width: 1024px) {
  .artist-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.artist-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  transition: all 0.3s ease;
  cursor: pointer;
}

.artist-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.artist-cover-wrapper {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  margin-bottom: 0.75rem;
}

.artist-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.artist-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, color-mix(in srgb, var(--color-primary) 15%, var(--color-surface-container)) 50%, var(--color-primary-light) 100%);
}

.artist-info {
  text-align: center;
}

.artist-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.artist-music-count {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
}

.artist-action {
  padding: 0.75rem 1rem 0;
  width: 100%;
}

.artist-action :deep(.ant-btn) {
  width: 100%;
}

/* ========== 歌单列表样式 ========== */
.playlist-grid,
.album-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.5rem;
  padding: 0 1.5rem 1.5rem 1.5rem;
}

@media (min-width: 640px) {
  .playlist-grid,
  .album-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .playlist-grid,
  .album-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1280px) {
  .playlist-grid,
  .album-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.playlist-card,
.album-card {
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
}

.playlist-card:hover,
.album-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.playlist-cover-wrapper,
.album-cover-wrapper {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
}

.playlist-cover,
.album-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.playlist-cover-placeholder,
.album-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, color-mix(in srgb, var(--color-primary) 15%, var(--color-surface-container)) 50%, var(--color-primary-light) 100%);
}

.playlist-card:hover .playlist-cover,
.album-card:hover .album-cover {
  transform: scale(1.05);
}

.playlist-overlay,
.album-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.5rem;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  display: flex;
  justify-content: flex-end;
}

.track-count {
  font-size: 12px;
  color: #fff;
  background: rgba(0, 0, 0, 0.5);
  padding: 4px;
  border-radius: 4px;
}

.playlist-source-tag,
.album-source-tag {
  position: absolute;
  bottom: 0.5rem;
  left: 0.5rem;
  font-size: 11px;
  color: #fff;
  background: rgba(0, 0, 0, 0.5);
  padding: 4px;
  border-radius: 4px;
  font-weight: 500;
  z-index: 1;
}

.playlist-info,
.album-info {
  padding: 1rem;
}

.playlist-name,
.album-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-creator,
.album-artist {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-action,
.album-action {
  padding: 0 1rem 1rem;
}

.playlist-action :deep(.ant-btn),
.album-action :deep(.ant-btn) {
  width: 100%;
}
</style>
