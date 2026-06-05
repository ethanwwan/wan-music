<template>
  <div :class="type !== 'search' ? 'detail-view' : 'search-result-panel'">
    <!-- 歌曲列表 -->
    <div v-if="totalTracks > 0" :class="type !== 'search' ? '' : 'tracks-section'">
      <!-- 歌单/专辑标题区域（只有在有详情数据时显示） -->
      <div v-if="playlistData" :class="type !== 'search' ? 'detail-header' : 'playlist-header'">
        <div class="header-left">
          <div v-if="playlistData.coverImgUrl" :class="type !== 'search' ? 'detail-cover-wrapper' : 'playlist-cover-wrapper'">
            <img :src="playlistData.coverImgUrl" :alt="playlistData.name" :class="type !== 'search' ? 'detail-cover' : 'playlist-cover'" />
          </div>
          <div :class="type !== 'search' ? 'detail-info' : 'playlist-info'">
            <h1 :class="type !== 'search' ? 'detail-name' : 'playlist-name'">{{ playlistData.name }}</h1>
            <div :class="type !== 'search' ? 'detail-meta' : 'playlist-meta'">
              <span class="meta-item">{{ creatorLabel }}：{{ playlistData.creator }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">共 {{ totalTracks }} 首歌曲</span>
            </div>
            <!-- 下载进度条 -->
            <div v-if="downloadProgress.isDownloading" class="download-progress-bar">
              <el-progress 
                :percentage="downloadProgress.percentage" 
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
          <el-button 
            type="primary" 
            @click="handleBatchDownload" 
            :disabled="downloadProgress.isDownloading"
            :loading="downloadProgress.isDownloading"
          >
            {{ downloadProgress.isDownloading ? '下载中...' : '批量打包下载' }}
          </el-button>
        </div>
      </div>

      <!-- 表格形式的歌曲列表 -->
      <div class="tracks-table-wrapper">
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
              v-for="(track, index) in currentPageTracks" 
              :key="track.id"
              class="track-row"
              :class="{ 
                'selected': selectedTrack && selectedTrack.id === track.id,
                'unavailable': track.unavailable
              }"
              @click="handleTrackClick(track)"
            >
              <td class="col-index">
                <span v-if="track.unavailable" class="unavailable-icon" title="无法播放">🚫</span>
                <span v-else>{{ (currentPage - 1) * pageSize + index + 1 }}</span>
              </td>
              <td class="col-cover">
                <img
                  :src="getCover(track)"
                  :alt="track.name"
                  class="track-cover"
                  :class="{ 'grayscale': track.unavailable }"
                  loading="lazy"
                  @error="onCoverError"
                />
              </td>
              <td class="col-name">
                <span class="track-name" :class="{ 'unavailable-text': track.unavailable }">{{ track.name }}</span>
                <span v-if="track.unavailable" class="unavailable-reason">无版权</span>
              </td>
              <td class="col-artist" :class="{ 'unavailable-text': track.unavailable }">{{ getArtist(track) }}</td>
              <td class="col-action">
                <button 
                  @click.stop="playTrack(track)"
                  :disabled="parsingTrackId === track.id && parsingType === 'play' || track.unavailable"
                  class="action-btn play-btn"
                  :class="{ 'is-loading': parsingTrackId === track.id && parsingType === 'play', 'disabled': track.unavailable }"
                  :title="track.unavailable ? '该歌曲无版权' : '播放'"
                >
                  <span v-if="parsingTrackId === track.id && parsingType === 'play'" class="loading-spinner"></span>
                  <span v-else class="btn-icon">▶</span>
                </button>
                <button 
                  @click.stop="downloadSingle(track)"
                  :disabled="parsingTrackId === track.id && parsingType === 'download' || track.unavailable"
                  class="action-btn download-btn"
                  :class="{ 'is-loading': parsingTrackId === track.id && parsingType === 'download', 'disabled': track.unavailable }"
                  :title="track.unavailable ? '该歌曲无版权' : '下载'"
                >
                  <span v-if="parsingTrackId === track.id && parsingType === 'download'" class="loading-spinner"></span>
                  <span v-else class="btn-icon">⬇</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <Pagination 
        :total-count="totalTracks"
        :page-size="pageSize"
        :model-value="currentPage"
        @update:model-value="handlePageChange"
      />
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <div class="loading-content">
        <el-icon class="is-loading"><Loading /></el-icon>
        <div class="loading-text">正在加载歌单信息...</div>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-if="error" class="error-container">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'
import { ElMessage, ElButton, ElIcon, ElProgress } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { batchDownloadMusic, parseMusicInfo } from '../services/musicApi.js'
import { settings } from '../utils/settingsManager.js'
import { saveBlob, sanitizeFilename } from '../utils/downloadHelper.js'
import { embedMetadata } from '../services/metadataWriter.js'
import Pagination from './Pagination.vue'

export default {
  name: 'SearchResultList',
  components: {
    ElButton,
    ElIcon,
    ElProgress,
    Loading,
    Pagination
  },
  props: {
    playlistInfo: {
      type: Object,
      required: false,
      default: null
    },
    displayTracks: {
      type: Array,
      default: () => []
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
    },
    settings: {
      type: Object,
      default: () => ({})
    },
    type: {
      type: String,
      default: 'search',
      validator: (value) => ['search', 'playlist', 'album'].includes(value)
    }
  },
  emits: ['track-selected', 'track-parsed', 'page-change'],
  setup(props, { emit }) {
    const playlistData = computed(() => props.playlistInfo)
    const creatorLabel = computed(() => (props.playlistInfo?.isAlbum ? '作者' : '创建者'))
    
    // 计算当前页应该显示的歌曲（分页处理）
    const currentPageTracks = computed(() => {
      const start = (props.currentPage - 1) * props.pageSize
      const end = start + props.pageSize
      return props.displayTracks.slice(start, end)
    })
    
    const loading = ref(false)
    const error = ref('')
    const selectedTrack = ref(null)
    const parsingTrackId = ref(null)
    const parsingType = ref(null) // 'play' | 'download'
    
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
    
    // 处理歌曲行点击
    const handleTrackClick = (track) => {
      if (track.unavailable) {
        ElMessage.warning(`《${track.name}》因版权问题暂时无法播放`)
        return
      }
      selectTrack(track)
    }

    // 获取封面地址（兼容多种字段）
    const getCover = (track) => {
      const coverUrl = track?.picUrl || track?.cover || track?.al?.picUrl || track?.album?.picUrl || playlistData.value?.picUrl || ''
      if (!coverUrl) return ''
      // HTTP地址需要通过代理访问
      if (coverUrl.startsWith('https')) return coverUrl
      return `/stream?url=${encodeURIComponent(coverUrl)}`
    }

    const onCoverError = (e) => {
      // 加载失败时使用一个透明占位，避免破图
      e.target.style.visibility = 'hidden'
    }

    // 获取歌手名称（兼容多种字段结构）
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

    // 获取专辑名称（兼容多种字段结构）
    const getAlbum = (track) => {
      return (
        track?.album ||
        track?.al?.name ||
        ''
      )
    }

    // 选择歌曲
    const selectTrack = (track) => {
      selectedTrack.value = track
      emit('track-selected', track)
    }

    // 播放歌曲（先解析再播放）
    const playTrack = async (track) => {
      // 版权检查
      if (track.unavailable) {
        ElMessage.warning(`《${track.name}》因版权问题暂时无法播放`)
        return
      }
      
      parsingTrackId.value = track.id
      parsingType.value = 'play'
      
      try {
        const qualityValue = typeof props.settings?.selectedQuality === 'string' ? props.settings.selectedQuality : 'lossless'
        const songUrl = `https://music.163.com/song?id=${track.id}`
        
        // 解析歌曲信息，获取播放链接
        const musicInfo = await parseMusicInfo(songUrl, qualityValue)
        
        if (!musicInfo?.url) {
          throw new Error('获取播放链接失败')
        }
        
        // 解析成功后触发播放，带上播放URL和完整的播放列表
        emit('track-parsed', { track, quality: qualityValue })
        emit('track-play', { ...track, url: musicInfo.url, lrc: musicInfo.lrc }, props.displayTracks)
        ElMessage.success(`开始播放：${track.name}`)
      } catch (error) {
        ElMessage.error(`播放失败：${error.message}`)
      } finally {
        parsingTrackId.value = null
        parsingType.value = null
      }
    }

    // 下载单曲
    const downloadSingle = async (track) => {
      // 版权检查
      if (track.unavailable) {
        ElMessage.warning(`《${track.name}》因版权问题暂时无法下载`)
        return
      }
      
      parsingTrackId.value = track.id
      parsingType.value = 'download'
      
      try {
        const qualityValue = typeof props.settings?.selectedQuality === 'string' ? props.settings.selectedQuality : 'lossless'
        const writeMetadata = props.settings?.writeMetadata !== false
        const filenameFormat = props.settings?.filenameFormat || 'song-artist'
        const songUrl = `https://music.163.com/song?id=${track.id}`
        
        // 解析歌曲信息
        const musicInfo = await parseMusicInfo(songUrl, qualityValue)
        
        if (!musicInfo?.url) {
          throw new Error('获取下载链接失败')
        }
        
        // 直接使用 musicInfo 中返回的文件扩展名（根据音质自动设置）
        const extension = musicInfo.fileExtension || '.mp3'
        
        // 下载并保存
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
          } catch {
            // 元数据写入失败，继续下载
          }
        }
        
        // 根据设置生成文件名
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
        
        // 根据扩展名获取 MIME 类型
        const mimeTypes = {
          '.mp3': 'audio/mpeg',
          '.flac': 'audio/flac',
          '.m4a': 'audio/mp4'
        }
        const mimeType = mimeTypes[extension] || 'audio/mpeg'
        
        const blob = new Blob([finalBuffer], { type: mimeType })
        saveBlob(blob, filename)
        
        ElMessage.success(`已下载：${track.name}`)
      } catch (error) {
        ElMessage.error(`下载失败：${error.message}`)
      } finally {
        parsingTrackId.value = null
        parsingType.value = null
      }
    }

    // 批量下载
    const handleBatchDownload = async () => {
      if (!props.displayTracks || props.displayTracks.length === 0) {
        ElMessage.warning('没有可下载的歌曲')
        return
      }

      try {
        // 过滤掉无版权的歌曲
        const availableTracks = props.displayTracks.filter(track => !track.unavailable)
        const unavailableCount = props.displayTracks.length - availableTracks.length
        
        if (availableTracks.length === 0) {
          ElMessage.warning('所有歌曲都因版权问题无法下载')
          return
        }
        
        // 重置进度状态
        downloadProgress.value = {
          isDownloading: true,
          percentage: 0,
          status: '',
          currentSong: '',
          total: availableTracks.length,
          completed: 0,
          failed: 0
        }

        let message = `开始批量下载 ${availableTracks.length} 首歌曲...`
        if (unavailableCount > 0) {
          message += `（${unavailableCount} 首因版权问题跳过）`
        }
        ElMessage.info(message)

        // 准备音乐列表，需要先解析每首歌的信息
        const musicList = []
        for (const track of availableTracks) {
          try {
            // 将歌曲ID转换为URL格式
            const songUrl = `https://music.163.com/song?id=${track.id}`
            
            // 解析歌曲信息
            const quality = props.settings?.selectedQuality || 'lossless'
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
            console.error(`解析歌曲失败: ${track.name}`, err)
          }
        }

        if (musicList.length === 0) {
          throw new Error('没有成功解析的歌曲')
        }

        // 执行批量下载
        const result = await batchDownloadMusic(
          musicList,
          playlistData.value?.name || '', // 传递歌单/专辑名称作为 ZIP 文件名
          {
            filenameFormat: props.settings?.filenameFormat || 'artist-song',
            writeMetadata: props.settings?.writeMetadata !== false,
            downloadLrcFile: props.settings?.downloadLrcFile !== false,
            selectedQuality: props.settings?.selectedQuality || 'lossless'
          },
          (progress) => {
            downloadProgress.value.percentage = progress.percentage
            downloadProgress.value.currentSong = progress.current
            downloadProgress.value.completed = progress.completed
            downloadProgress.value.failed = progress.failed
            downloadProgress.value.total = progress.total
          }
        )

        // 下载完成
        downloadProgress.value.isDownloading = false
        downloadProgress.value.status = result.failed === 0 ? 'success' : 'warning'
        downloadProgress.value.percentage = 100

        if (result.failed === 0) {
          ElMessage.success(`批量下载完成！共下载 ${result.completed} 首歌曲`)
        } else {
          ElMessage.warning(`下载完成！成功 ${result.completed} 首，失败 ${result.failed} 首`)
        }

      } catch (error) {
        downloadProgress.value.isDownloading = false
        downloadProgress.value.status = 'exception'
        ElMessage.error(`批量下载失败: ${error.message}`)
      }
    }

    // 解析歌曲
    const parseTrack = async (track) => {
      parsingTrackId.value = track.id
      
      try {
        // 确保传递正确的音质参数，避免事件对象污染
        const qualityValue = typeof props.settings?.selectedQuality === 'string' ? props.settings.selectedQuality : 'lossless'
        
        // 这里调用现有的解析逻辑，传递音质参数
        emit('track-parsed', { track, quality: qualityValue })
        ElMessage.success(`开始解析：${track.name}`)
      } catch {
        ElMessage.error('解析失败，请重试')
      } finally {
        parsingTrackId.value = null
      }
    }

    // 处理分页变化
    const handlePageChange = (page) => {
      console.log('SearchResultList: handlePageChange called with page:', page)
      emit('page-change', page)
    }


    // 格式化播放量
    const formatPlayCount = (count) => {
      if (count >= 100000000) {
        return Math.floor(count / 100000000) + '亿'
      } else if (count >= 10000) {
        return Math.floor(count / 10000) + '万'
      }
      return count.toString()
    }

    



    return {
      playlistData,
      creatorLabel,
      currentPageTracks,
      loading,
      error,
      selectedTrack,
      parsingTrackId,
      parsingType,
      downloadProgress,
      selectTrack,
      playTrack,
      downloadSingle,
      handleBatchDownload,
      handlePageChange,
      handleTrackClick,
      formatPlayCount,
      getCover,
      onCoverError,
      getArtist,
      getAlbum,
    }
  }
}
</script>

<style>
/* 操作按钮样式 */
.action-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  outline: none;
  outline-offset: 0;
  background: var(--color-surface-container-low);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
  flex-shrink: 0;
  line-height: 1;
  vertical-align: middle;
}

.action-btn:hover {
  background: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
  outline: none;
  border: none;
}

.action-btn:active {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.3);
  outline: none;
  border: none;
}

.action-btn:focus {
  outline: none;
  border: none;
}

.action-btn:focus-visible {
  outline: none;
  border: none;
}

.action-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
  outline: none;
  border: none;
}

.action-btn:disabled .btn-icon {
  color: var(--color-text-muted);
}

.action-btn.is-loading:disabled {
  opacity: 1;
  cursor: wait;
}

.play-btn,
.download-btn {
  color: var(--color-text-muted);
}

.action-btn:hover .btn-icon {
  color: white;
}

.btn-icon {
  font-size: 16px;
  line-height: 1;
  transition: color 0.25s ease;
  font-weight: 600;
}

/* Loading 旋转动画 */
.loading-spinner {
  width: 18px;
  height: 18px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: btn-spin 0.8s linear infinite;
}

@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 全局深色模式样式 - 不使用scoped以确保样式能够应用 */
.dark .tracks-section {
  background: var(--color-surface-white) !important;
  color: var(--color-on-surface) !important;
}

.dark .section-header h2 {
  color: var(--color-on-surface) !important;
}

.dark .track-total {
  color: var(--color-text-muted) !important;
}

.dark .track-item {
  background: var(--color-surface-container-low) !important;
  color: var(--color-on-surface) !important;
  border-color: var(--color-border-subtle) !important;
}

.dark .track-item:hover {
  background: var(--color-primary-light) !important;
}

.dark .track-item.selected {
  background: var(--color-primary-light) !important;
  border-color: var(--color-primary) !important;
}

.dark .playlist-info-bar {
  background-color: var(--color-surface-container) !important;
  color: var(--color-on-surface) !important;
}

.dark .info-item {
  color: var(--color-secondary) !important;
}

.dark .info-separator {
  color: var(--color-outline) !important;
}

.dark .section-header {
  border-bottom-color: var(--color-border-subtle) !important;
}

.dark .section-header h2 {
  color: var(--color-on-surface) !important;
}
</style>

<style scoped>
/* 搜索结果面板 */
.search-result-panel {
  width: 100%;
}

.tracks-section {
  background: var(--color-surface-white);
  padding: 0;
}

.playlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-border-subtle);
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-surface-white) 100%);
}

.playlist-cover-wrapper {
  flex-shrink: 0;
}

.playlist-cover {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-md);
  object-fit: cover;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.playlist-info {
  flex: 1;
  min-width: 0;
}

.playlist-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-on-surface);
  margin: 0 0 0.5rem 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 14px;
  color: var(--color-text-muted);
}

/* 二级页面模式 - 使用详情页样式 */
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

.track-cover {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  object-fit: cover;
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
  border-bottom: none !important;
  box-sizing: border-box;
  white-space: nowrap;
  vertical-align: middle;
}

.tracks-table td.col-action .action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0 6px;
  vertical-align: middle;
}

.track-row:hover {
  background: var(--color-surface-container-low);
}

.track-row.selected {
  background: var(--color-primary-light);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.section-header .header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--color-on-surface);
}

.track-total {
  color: var(--color-text-muted);
  font-size: 14px;
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
  font-size: 18px;
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

.action-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed !important;
}

.action-btn.disabled:hover {
  background: transparent !important;
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

.tracks-list {
  display: flex;
  flex-direction: column;
}

.track-item {
  display: flex;
  align-items: center;
  padding: var(--space-3) var(--space-2);
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.3s ease;
  margin-bottom: var(--space-2);
  min-height: 60px;
  box-sizing: border-box;
}

.track-item:hover {
  background: var(--color-primary-light);
  transform: translateY(-1px);
}

.track-item.selected {
  background: var(--color-primary-light);
  border: 1px solid var(--color-primary);
}


.track-info {
  flex: 1;
  min-width: 0;
}

.track-cover {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  margin-right: var(--space-2);
  background-color: var(--color-surface-variant);
}

.track-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}


.track-name, .track-artist {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-name {
  flex: 1 1 auto;
  min-width: 0;
}

.track-artist {
  color: var(--color-secondary);
  /* 限制歌手区域占比，避免撑开主列导致侧栏移位 */
  flex: 0 0 auto;
  max-width: 45%;
  min-width: 0;
}

.playlist-info-bar {
  background-color: var(--color-surface-container);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: 14px;
  flex-wrap: wrap;
}

.info-item {
  color: var(--color-secondary);
  white-space: nowrap;
}

.info-separator {
  color: var(--color-outline);
  font-weight: bold;
}

.track-name {
  font-weight: 600;
  font-size: 16px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-actions {
  margin-left: var(--space-2);
  flex-shrink: 0;
}

.track-actions .el-button {
  min-width: 60px;
  height: 32px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--color-text-muted);
  min-height: 200px;
  width: 100%;
}

.loading-container > .loading-content {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 24px !important;
  width: max-content !important;
  min-width: 250px;
  max-width: none !important;
  padding: 12px !important;
}

.loading-container .el-icon {
  font-size: 40px;
  color: var(--color-primary);
  flex-shrink: 0;
  margin-bottom: 6px !important;
}

.loading-container > .loading-content > .loading-text {
  font-size: 16px;
  font-weight: 500;
  text-align: center !important;
  white-space: nowrap !important;
  overflow: visible !important;
  width: auto !important;
  min-width: 200px !important;
  max-width: none !important;
  flex-shrink: 0;
  writing-mode: horizontal-tb !important;
  direction: ltr !important;
  word-break: normal !important;
  word-wrap: normal !important;
  overflow-wrap: normal !important;
  display: inline-block !important;
  line-height: 1.5;
  max-height: none !important;
}

.error-container {
  padding: 20px;
}

/* 循环解析模式样式 */

.dark .track-cover {
  background-color: var(--color-surface-variant);
}

.dark .track-artist {
  color: var(--color-secondary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }
  
  .header-left {
    width: 100%;
  }
  
  .header-right {
    width: 100%;
    justify-content: flex-start;
  }
  
  .track-item {
    padding: var(--space-2) var(--space-1);
    margin-bottom: var(--space-2);
  }
  .tracks-section {
    padding: var(--space-3);
  }
  .section-header {
    margin-bottom: var(--space-2);
  }
  .track-cover {
    margin-right: var(--space-1);
  }
  
  .playlist-info-bar {
    padding: var(--space-1) var(--space-2);
    margin-bottom: var(--space-2);
    font-size: 12px;
    gap: 6px;
  }
  
  .track-name {
    font-size: 14px;
  }
  
  /* Loading 响应式 */
  .loading-container {
    padding: 40px 16px;
    min-height: 150px;
  }
  
  .loading-container .el-icon {
    font-size: 32px;
  }
  
  .loading-text {
    font-size: 14px;
  }
}

/* 小屏幕设备优化 */
@media (max-width: 480px) {
  .loading-container {
    padding: 30px 12px;
    min-height: 120px;
  }
  
  .loading-container .el-icon {
    font-size: 28px;
  }
  
  .loading-text {
    font-size: 13px;
  }
}


</style>
