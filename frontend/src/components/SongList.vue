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
          </div>
        </div>
        <div class="header-right">
          <a-button
            type="primary"
            @click="handleBatchDownload"
          >
            打包下载
          </a-button>
        </div>
      </div>



      <!-- 歌曲表格 -->
      <div v-if="paginatedTracks.length > 0" class="tracks-table-wrapper">
        <table class="tracks-table">
          <thead>
            <tr>
              <th v-if="isSelectMode" class="col-select">
                <a-checkbox 
                  :checked="isAllSelected"
                  :indeterminate="isPartiallySelected"
                  @change="handleSelectAll"
                />
              </th>
              <th class="col-index">
                <template v-if="isSelectMode">
                  已选 {{ (selectedTrackIds?.length || 0) }}/{{ (sortedTracks?.length || 0) }}
                </template>
                <template v-else>
                  序号
                </template>
              </th>
              <th class="col-cover"></th>
              <th class="col-name">歌名</th>
              <th class="col-artist">歌手</th>
              <th class="col-action">
                <template v-if="!isSelectMode">
                  <a-button size="small" @click="enterSelectMode">批量操作</a-button>
                </template>
                <template v-else>
                  <a-space :size="8">
                    <a-button size="small" type="primary" :disabled="(selectedTrackIds?.length || 0) === 0" @click="handleBatchDownloadSelected">下载选中</a-button>
                    <a-button size="small" @click="exitSelectMode">取消</a-button>
                  </a-space>
                </template>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="(track, index) in paginatedTracks" 
              :key="track.id"
              class="track-row"
              :class="{ 
                'selected': selectedTrack && selectedTrack.id === track.id,
                'unavailable': isTrackUnavailable(track),
                'selected-for-batch': isSelectMode && selectedTrackIds.value?.includes(track.id)
              }"
              @click="handleTrackClick(track)"
            >
              <td v-if="isSelectMode" class="col-select">
                <a-checkbox 
                  :checked="isTrackSelected(track)"
                  @change="() => toggleSelectTrack(track)"
                />
              </td>
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
              :style="{ backgroundColor: getSourceInfo(item.source)?.color, color: '#fff' }"
            >
              {{ getSourceInfo(item.source)?.name || item.source }}
            </span>
            <div :class="listType === 'playlist' ? 'playlist-overlay' : 'album-overlay'">
              <span class="track-count">
                <template v-if="item.trackCount && item.trackCount > 0">{{ item.trackCount }} 首</template>
                <template v-else>数量未知</template>
              </span>
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
import { parseMusicInfo } from '../services/musicApi.js'
import { settings } from '../utils/settingsManager.js'
import { useBatchDownload } from '../composables/useBatchDownload.js'
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
    default: 12
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

// 批量选择状态
const isSelectMode = ref(false)
const selectedTrackIds = ref([])

// 不可用歌曲ID集合（用于跟踪无版权歌曲）
const unavailableTrackIds = shallowRef(new Set())

// 是否全选
const isAllSelected = computed(() => {
  if (selectedTrackIds.value.length === 0 || sortedTracks.value.length === 0) return false
  return selectedTrackIds.value.length === sortedTracks.value.length
})

// 是否部分选择（用于 checkbox indeterminate 状态）
const isPartiallySelected = computed(() => {
  if (sortedTracks.value.length === 0) return false
  return selectedTrackIds.value.length > 0 && selectedTrackIds.value.length < sortedTracks.value.length
})

// 检查歌曲是否被选中
const isTrackSelected = (track) => {
  const ids = selectedTrackIds.value
  if (!ids || !Array.isArray(ids)) return false
  return ids.includes(track.id)
}

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
  
  // 如果在批量选择模式下，点击行切换选择状态
  if (isSelectMode.value) {
    toggleSelectTrack(track)
    return
  }
  
  selectedTrack.value = track
  emit('track-selected', track)
}

// 切换单首歌曲选择
const toggleSelectTrack = (track) => {
  const currentIds = selectedTrackIds.value
  if (currentIds.includes(track.id)) {
    // 取消选中
    selectedTrackIds.value = currentIds.filter(id => id !== track.id)
  } else {
    // 添加选中
    selectedTrackIds.value = [...currentIds, track.id]
    isSelectMode.value = true
  }
}

// 全选/取消全选
const handleSelectAll = (event) => {
  const checked = typeof event === 'boolean' ? event : (event?.target?.checked ?? false)
  if (checked) {
    // 全选：选中所有歌曲（跨分页）
    const allIds = sortedTracks.value.map(t => t.id)
    selectedTrackIds.value = [...allIds]
    isSelectMode.value = true
  } else {
    // 取消全选：只是清除选中状态，不退出选择模式
    selectedTrackIds.value = []
  }
}

// 下载选中的歌曲
const handleBatchDownloadSelected = async () => {
  if (selectedTrackIds.value.length === 0) {
    message.warning('请先选择要下载的歌曲')
    return
  }
  
  // 过滤出选中的歌曲
  const selectedTracks = sortedTracks.value.filter(t => selectedTrackIds.value.includes(t.id))
  const musicList = selectedTracks.map(track => ({
    id: track.id,
    name: track.name,
    artist: getArtist(track),
    album: getAlbum(track),
    source: track.source || ''
  }))
  
  try {
    const { startBatchDownload } = useBatchDownload()
    await startBatchDownload({
      playlistName: '批量下载',
      items: musicList,
      settings: {
        selectedQuality: settings.selectedQuality || 'lossless',
        filenameFormat: settings.filenameFormat || 'song-artist',
        writeMetadata: settings.writeMetadata !== false,
        downloadLrcFile: settings.downloadLrcFile === true
      }
    })
    // 下载后退出选择模式
    exitSelectMode()
  } catch (error) {
    const errorMsg = error?.message || String(error) || '未知错误'
    message.error(`下载失败：${errorMsg}`)
  }
}

// 进入批量选择模式
const enterSelectMode = () => {
  isSelectMode.value = true
}

// 退出批量选择模式
const exitSelectMode = () => {
  isSelectMode.value = false
  selectedTrackIds.value = []
}

/**
 * 播放单首歌曲
 *
 * 流程：
 *   1. 检查歌曲是否被标记为不可用
 *   2. 用 track.id 调后端 /song 接口获取播放信息
 *   3. 拿到 musicInfo 后触发播放事件
 *
 * @param {Object} track - 歌曲对象，必须包含 id、name、source
 */
const playTrack = async (track) => {
  // 1. 不可用检查
  if (isTrackUnavailable(track)) {
    message.warning(`《${track.name}》因版权问题暂时无法播放`)
    return
  }

  // 2. 校验 track.id
  if (!track?.id) {
    message.error(`《${track.name}》缺少歌曲ID，请重新搜索`)
    return
  }

  // 设置 loading 状态
  parsingTrackId.value = track.id
  parsingType.value = 'play'

  try {
    // 3. 用 id + source 调后端 /song 接口
    const qualityValue = settings.selectedQuality || 'lossless'
    const musicInfo = await parseMusicInfo(track.id, qualityValue, track.source)

    // 4. URL 无效时标记为不可用
    if (!musicInfo?.url) {
      markTrackUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法播放`)
      return
    }

    // 5. 触发播放
    emit('track-parsed', { track, quality: qualityValue })
    emit('track-play', { ...track, url: musicInfo.url, lrc: musicInfo.lrc })
    message.success(`开始播放：${track.name}`)
  } catch (error) {
    // 6. 统一错误处理
    const errorMsg = error?.message || String(error) || '未知错误'
    message.error(`播放失败：${errorMsg}`)
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

  if (!track.id) {
    message.error(`《${track.name}》缺少歌曲ID，请重新搜索`)
    return
  }

  parsingTrackId.value = track.id
  parsingType.value = 'download'

  try {
    const { startBatchDownload } = useBatchDownload()
    await startBatchDownload({
      playlistName: track.name,
      items: [{
        id: track.id,
        name: track.name,
        artist: getArtist(track),
        album: getAlbum(track),
        source: track.source || ''
      }],
      settings: {
        selectedQuality: settings.selectedQuality || 'lossless',
        filenameFormat: settings.filenameFormat || 'song-artist',
        writeMetadata: settings.writeMetadata !== false,
        downloadLrcFile: settings.downloadLrcFile === true
      }
    })
  } catch (error) {
    const errorMsg = error?.message || String(error) || '未知错误'
    if (errorMsg.includes('已下架') || errorMsg.includes('无法获取') || errorMsg.includes('未找到歌曲') || errorMsg.includes('版权')) {
      markTrackUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法下载`)
    } else {
      message.error(`下载失败：${errorMsg}`)
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

  // 不做过滤：所有歌曲都尝试，后端自动跳过无版权的
  const musicList = props.items
    .filter(t => t.id)
    .map(track => ({
      id: track.id,
      name: track.name,
      artist: getArtist(track),
      album: getAlbum(track),
      source: track.source || ''
    }))

  if (musicList.length === 0) {
    message.error('没有可下载的歌曲（缺少ID）')
    return
  }

  // 把任务加入下载队列（进度在 Drawer 中查看，不在此处阻塞）
  const { startBatchDownload } = useBatchDownload()
  try {
    await startBatchDownload({
      playlistName: props.detailInfo?.name || '歌单',
      items: musicList,
      settings: {
        selectedQuality: settings.selectedQuality || 'lossless',
        filenameFormat: settings.filenameFormat || 'song-artist',
        writeMetadata: settings.writeMetadata !== false,
        downloadLrcFile: settings.downloadLrcFile === true
      }
    })
  } catch (error) {
    const errorMsg = error?.message || String(error) || '未知错误'
    message.error(`加入下载队列失败: ${errorMsg}`)
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





/* 选择列 */
.col-select {
  width: 40px;
  text-align: center;
}

/* 选中状态样式 */
.track-row.selected-for-batch {
  background: var(--color-primary-light);
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
