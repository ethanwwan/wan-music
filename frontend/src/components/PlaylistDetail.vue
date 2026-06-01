<template>
  <div class="playlist-detail">


    <!-- 歌曲列表 -->
    <div v-if="playlistData && totalTracks > 0" class="tracks-section">
      <!-- 歌单标题区域 -->
      <div class="playlist-header">
        <div class="header-left">
          <div v-if="playlistData.coverImgUrl" class="playlist-cover-wrapper">
            <img :src="playlistData.coverImgUrl" :alt="playlistData.name" class="playlist-cover" />
          </div>
          <div class="playlist-info">
            <h1 class="playlist-name">{{ playlistData.name }}</h1>
            <div class="playlist-meta">
              <span class="meta-item">{{ creatorLabel }}：{{ playlistData.creator }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">共 {{ totalTracks }} 首歌曲</span>
            </div>
          </div>
        </div>
        <div class="header-right">
          <el-button type="primary" @click="handleBatchDownload" :disabled="!settings?.enableBatchDownload">
            批量打包下载
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
              <th class="col-album">专辑</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="(track, index) in displayTracks" 
              :key="track.id"
              class="track-row"
              :class="{ 'selected': selectedTrack && selectedTrack.id === track.id }"
              @click="selectTrack(track)"
            >
              <td class="col-index">{{ (currentPage - 1) * pageSize + index + 1 }}</td>
              <td class="col-cover">
                <img
                  :src="getCover(track)"
                  :alt="track.name"
                  class="track-cover"
                  loading="lazy"
                  @error="onCoverError"
                />
              </td>
              <td class="col-name">
                <span class="track-name">{{ track.name }}</span>
              </td>
              <td class="col-artist">{{ getArtist(track) }}</td>
              <td class="col-album">{{ getAlbum(track) }}</td>
              <td class="col-action">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click.stop="parseTrack(track)"
                  :loading="parsingTrackId === track.id"
                >
                  {{ parsingTrackId === track.id ? '解析中...' : '解析单曲' }}
                </el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- 分页：上一页 / 下一页 按钮 -->
      <div class="pagination-section">
        <el-button size="small" @click="goPrevPage" :disabled="currentPage <= 1">上一页</el-button>
        <span class="page-info">第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
        <el-button size="small" type="primary" @click="goNextPage" :disabled="currentPage >= totalPages">下一页</el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在加载歌单信息...</span>
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
import { ElMessage, ElButton, ElIcon } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

// 移除批量下载相关依赖

export default {
  name: 'PlaylistDetail',
  components: {
    ElButton,
    ElIcon,
    Loading
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
    selectedQuality: {
      type: String,
      default: 'lossless'
    },
    settings: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['track-selected', 'track-parsed', 'page-change'],
  setup(props, { emit }) {
    const playlistData = computed(() => props.playlistInfo)
    const creatorLabel = computed(() => (props.playlistInfo?.isAlbum ? '作者' : '创建者'))
    const loading = ref(false)
    const error = ref('')
    const selectedTrack = ref(null)
    const parsingTrackId = ref(null)
    // 移除批量下载相关状态与函数

    // 获取封面地址（兼容多种字段）
    const getCover = (track) => {
      return (
        track?.picUrl ||
        track?.cover ||
        track?.al?.picUrl ||
        track?.album?.picUrl ||
        playlistData.value?.picUrl ||
        ''
      )
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

    // 批量下载（占位函数）
    const handleBatchDownload = () => {
      ElMessage.info('批量下载功能开发中...')
    }

    // 解析歌曲
    const parseTrack = async (track) => {
      parsingTrackId.value = track.id
      
      try {
        // 确保传递正确的音质参数，避免事件对象污染
        const qualityValue = typeof props.selectedQuality === 'string' ? props.selectedQuality : 'lossless'
        
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

    // 计算总页数
    const totalPages = computed(() => {
      const size = Number(props.pageSize) || 1
      const total = Number(props.totalTracks) || 0
      return Math.max(1, Math.ceil(total / size))
    })

    // 上一页 / 下一页
    const goPrevPage = () => {
      if (props.currentPage > 1) {
        handlePageChange(props.currentPage - 1)
      }
    }
    const goNextPage = () => {
      if (props.currentPage < totalPages.value) {
        handlePageChange(props.currentPage + 1)
      }
    }



    return {
      playlistData,
      creatorLabel,
      loading,
      error,
      selectedTrack,
      parsingTrackId,
      selectTrack,
      parseTrack,
      handleBatchDownload,
      handlePageChange,
      formatPlayCount,
      getCover,
      onCoverError,
      getArtist,
      getAlbum,
      totalPages,
      goPrevPage,
      goNextPage,
    }
  }
}
</script>

<style>
/* 全局深色模式样式 - 不使用scoped以确保样式能够应用 */
.dark .tracks-section {
  background: var(--color-surface-white) !important;
  color: var(--color-on-surface) !important;
}

.dark .section-header h2 {
  color: var(--color-on-surface) !important;
}

.dark .page-info {
  color: var(--color-text-muted) !important;
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

.dark .pagination-section {
  border-top-color: var(--color-border-subtle) !important;
}

.dark .section-header {
  border-bottom-color: var(--color-border-subtle) !important;
}

.dark .section-header h2 {
  color: var(--color-on-surface) !important;
}
</style>

<style scoped>
.playlist-detail {
  width: 100%;
}

.tracks-section {
  background: var(--color-surface-white);
  border-radius: var(--radius-md);
  padding: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* 歌单头部 */
.playlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-border-subtle);
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-surface-white) 100%);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
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

.meta-item {
  white-space: nowrap;
}

.meta-separator {
  color: var(--color-outline);
}

.header-right {
  flex-shrink: 0;
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
}

.tracks-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  vertical-align: middle;
}

.col-index {
  width: 60px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 14px;
}

.col-cover {
  width: 50px;
  padding: 8px 16px;
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

.col-action {
  width: 100px;
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

.header-left {
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
}

.loading-container .el-icon {
  font-size: 32px;
  margin-bottom: 15px;
}

.error-container {
  padding: 20px;
}

.pagination-section {
  margin-top: var(--space-4);
  padding: var(--space-3) 0;
  border-top: 1px solid var(--color-border-subtle);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-2);
}

.page-info {
  color: var(--color-text-muted);
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
  
  .pagination-section {
    margin-top: var(--space-3);
    padding: var(--space-2) 0;
  }
  
  .pagination-section .el-pagination {
    font-size: 12px;
  }
}


</style>
