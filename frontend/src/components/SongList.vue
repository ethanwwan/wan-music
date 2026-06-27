<template>
  <div :class="listContainerClass">
    <!-- 单曲列表（搜索结果 / 歌单详情共用） -->
    <template v-if="type === 'song'">
      <div v-if="detailInfo" class="detail-header">
        <div class="header-left">
          <div class="detail-cover-wrapper">
            <img
              v-if="detailInfo.coverImgUrl"
              :src="detailInfo.coverImgUrl"
              :alt="detailInfo.name"
              class="detail-cover"
              @error="handleCoverError"
            />
            <div v-else class="cover-placeholder"></div>
          </div>
          <div class="detail-info">
            <h1 class="detail-name">{{ detailInfo.name }}</h1>
            <div class="detail-meta">
              <span class="meta-item">{{ creatorLabel }}：{{ detailInfo.creator }}</span>
              <span class="meta-separator">•</span>
              <span class="meta-item">共 {{ items.length }} 首歌曲</span>
            </div>
          </div>
        </div>
        <div class="header-right">
          <a-button type="primary" @click="handleBatchDownload">打包下载</a-button>
        </div>
      </div>

      <div v-if="sortedTracks.length > 0" class="tracks-table-wrapper">
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
                <template v-if="isSelectMode">已选 {{ selectedTrackIds.length }}/{{ sortedTracks.length }}</template>
                <template v-else>序号</template>
              </th>
              <th class="col-cover"></th>
              <th class="col-name">歌名</th>
              <th class="col-album">专辑名</th>
              <th class="col-pay">付费</th>
              <th class="col-quality">音质</th>
              <th class="col-action">
                <template v-if="!isSelectMode">
                  <a-button size="small" @click="enterSelectMode">批量操作</a-button>
                </template>
                <template v-else>
                  <a-space :size="8">
                    <a-button size="small" type="primary" :disabled="selectedTrackIds.length === 0" @click="handleBatchDownloadSelected">下载选中</a-button>
                    <a-button size="small" @click="exitSelectMode">取消</a-button>
                  </a-space>
                </template>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(track, index) in sortedTracks"
              :key="track.id"
              class="track-row"
              :class="{
                'unavailable': isTrackUnavailable(track),
                'selected-for-batch': isSelectMode && selectedTrackIds.includes(track.id)
              }"
              @click="handleTrackClick(track)"
            >
              <td v-if="isSelectMode" class="col-select">
                <a-checkbox
                  :checked="isTrackSelected(track)"
                  @click.stop
                  @change="() => toggleSelectTrack(track)"
                />
              </td>
              <td class="col-index">
                <span>{{ index + 1 }}</span>
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
                    @error="handleTrackCoverError"
                  />
                  <div v-else class="track-cover-placeholder"></div>
                </div>
              </td>
              <td class="col-name">
                <div class="track-name-row">
                  <span class="track-name" :class="{ 'unavailable-text': isTrackUnavailable(track) }">{{ track.name }}</span>
                  <span v-if="isTrackUnavailable(track)" class="unavailable-reason">无版权</span>
                  <span
                    v-if="track.source"
                    class="source-tag"
                    :style="{ backgroundColor: getSourceInfo(track.source)?.color + '20', color: getSourceInfo(track.source)?.color }"
                  >
                    {{ getSourceInfo(track.source)?.name || track.source }}
                  </span>
                </div>
                <div class="track-artist" :class="{ 'unavailable-text': isTrackUnavailable(track) }">{{ getArtist(track) }}</div>
              </td>
              <td class="col-album" :class="{ 'unavailable-text': isTrackUnavailable(track) }">{{ getAlbum(track) }}</td>
              <td class="col-pay">
                <span v-if="track.payInfo" class="pay-tag" :class="{ 'pay-free': track.payInfo.free, 'pay-vip': track.payInfo.vipOnly }">
                  {{ track.payInfo.label }}
                </span>
              </td>
              <td class="col-quality">
                <div v-if="track.bestQuality" class="quality-info">
                  <span class="quality-label">{{ getBestQualityLabel(track) }}</span>
                  <span class="quality-size">{{ getBestQualitySize(track) }}</span>
                </div>
              </td>
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
    </template>

    <!-- 歌单列表 -->
    <template v-else-if="type === 'playlist'">
      <div class="playlist-grid">
        <div
          v-for="item in items"
          :key="item.id"
          class="playlist-card"
          @click="emit('item-click', { item, action: 'playlist' })"
        >
          <div class="playlist-cover-wrapper">
            <img
              v-if="item.coverImgUrl"
              :src="item.coverImgUrl"
              :alt="item.name"
              class="playlist-cover"
              loading="lazy"
            />
            <div v-else class="playlist-cover-placeholder"></div>
            <span
              v-if="item.source"
              class="playlist-source-tag"
              :style="{ backgroundColor: getSourceInfo(item.source)?.color, color: '#fff' }"
            >
              {{ getSourceInfo(item.source)?.name || item.source }}
            </span>
            <div class="playlist-overlay">
              <span class="track-count">
                <template v-if="item.trackCount && item.trackCount > 0">{{ item.trackCount }} 首</template>
                <template v-else>数量未知</template>
              </span>
            </div>
          </div>
          <div class="playlist-info">
            <h4 class="playlist-name">{{ item.name }}</h4>
            <p class="playlist-creator">
              {{ typeof item.creator === 'object' ? item.creator.name : item.creator }}
            </p>
          </div>
          <div class="playlist-action">
            <a-button size="middle" type="primary" @click.stop="emit('item-click', { item, action: 'playlist' })">
              解析歌单
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
import { downloadQueueStore as queueStore } from '../stores/downloadQueue.js'
import { getPlatformById } from '../utils/platformsManager.js'

const props = defineProps({
  /** 'song' | 'playlist' */
  type: {
    type: String,
    default: 'song',
    validator: (value) => ['song', 'playlist'].includes(value)
  },
  items: {
    type: Array,
    default: () => []
  },
  detailInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['track-parsed', 'track-play', 'item-click', 'track-unavailable'])

const listContainerClass = computed(() => {
  if (props.type === 'song' && props.detailInfo) return 'detail-view'
  return 'song-list-panel'
})

const creatorLabel = computed(() => {
  if (props.detailInfo?.isAlbum) return '作者'
  if (props.detailInfo?.isArtist) return '歌手'
  return '创建者'
})

const sortedTracks = computed(() => [...props.items])

// 状态
const parsingTrackId = ref(null)
const parsingType = ref(null)

// 批量选择
const isSelectMode = ref(false)
const selectedTrackIds = ref([])
const unavailableTrackIds = shallowRef(new Set())

const isAllSelected = computed(() =>
  selectedTrackIds.value.length > 0 && selectedTrackIds.value.length === sortedTracks.value.length
)

const isPartiallySelected = computed(() => {
  const total = sortedTracks.value.length
  return total > 0 && selectedTrackIds.value.length > 0 && selectedTrackIds.value.length < total
})

const isTrackSelected = (track) => Array.isArray(selectedTrackIds.value) && selectedTrackIds.value.includes(track.id)

const markTrackUnavailable = (track) => {
  const newSet = new Set(unavailableTrackIds.value)
  newSet.add(track.id)
  unavailableTrackIds.value = newSet
  track.unavailable = true
  emit('track-unavailable', track)
}

const isTrackUnavailable = (track) =>
  track.unavailable || unavailableTrackIds.value.has(track.id)

// 工具方法
const getCover = (track) =>
  track?.picUrl || track?.cover || track?.al?.picUrl || track?.album?.picUrl || props.detailInfo?.coverImgUrl || ''

const getArtist = (track) =>
  track?.artist || track?.singer ||
  (typeof track?.artists === 'string' ? track.artists : null) ||
  (Array.isArray(track?.artists) && track.artists[0]?.name) ||
  (Array.isArray(track?.ar) && track.ar[0]?.name) ||
  ''

const getSourceInfo = (sourceId) => getPlatformById(sourceId)

const getAlbum = (track) => track?.album || track?.al?.name || ''

const QUALITY_LABELS = {
  standard: '标准', exhigh: '极高', lossless: '无损', hires: 'Hi-Res',
  dolby: '杜比', sky: '环绕声', jymaster: '母带', jyeffect: '臻音',
}

const getBestQualityLabel = (track) => {
  const key = track.bestQuality
  return key ? (QUALITY_LABELS[key] || key) : ''
}

const formatFileSize = (bytes) => {
  if (!bytes || bytes <= 0) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

const getBestQualitySize = (track) => {
  const key = track.bestQuality
  const size = track.qualityMap?.[key]?.size
  return formatFileSize(size)
}

const handleCoverError = (e) => {
  e.target.style.display = 'none'
  const placeholder = e.target.parentElement.querySelector('.cover-placeholder')
  if (placeholder) placeholder.style.display = 'flex'
}

const handleTrackCoverError = (e) => {
  e.target.style.display = 'none'
  const placeholder = e.target.parentElement.querySelector('.track-cover-placeholder')
  if (placeholder) placeholder.style.display = 'flex'
}

// 行点击：批量选择模式切换；非选择模式触发播放
const handleTrackClick = (track) => {
  if (isTrackUnavailable(track)) {
    message.warning(`《${track.name}》因版权问题暂时无法播放`)
    return
  }
  if (isSelectMode.value) {
    toggleSelectTrack(track)
    return
  }
}

const toggleSelectTrack = (track) => {
  const currentIds = selectedTrackIds.value
  if (currentIds.includes(track.id)) {
    selectedTrackIds.value = currentIds.filter(id => id !== track.id)
  } else {
    selectedTrackIds.value = [...currentIds, track.id]
    isSelectMode.value = true
  }
}

const handleSelectAll = (event) => {
  const checked = typeof event === 'boolean' ? event : (event?.target?.checked ?? false)
  if (checked) {
    selectedTrackIds.value = sortedTracks.value.map(t => t.id)
    isSelectMode.value = true
  } else {
    selectedTrackIds.value = []
  }
}

// 下载
const startDownload = (musicList, playlistName) => queueStore.addTask(
  musicList,
  playlistName,
  {
    selectedQuality: settings.selectedQuality || 'lossless',
    filenameFormat: settings.filenameFormat || 'song-artist',
    writeMetadata: settings.writeMetadata !== false,
  }
).then(() => {
  message.success(`已加入下载队列：${musicList.length} 首歌曲`)
  queueStore.openDrawer()
})

const buildDownloadItems = (tracks) => tracks.map(track => ({
  id: track.id,
  name: track.name,
  artist: getArtist(track),
  album: getAlbum(track),
  source: track.source || '',
  qualityMap: track.qualityMap || {}
}))

const buildBatchName = (musicList) =>
  musicList.length > 1 ? `${musicList[0].name}等${musicList.length}首` : musicList[0].name

const handleBatchDownloadSelected = async () => {
  if (selectedTrackIds.value.length === 0) {
    message.warning('请先选择要下载的歌曲')
    return
  }
  const selectedTracks = sortedTracks.value.filter(t => selectedTrackIds.value.includes(t.id))
  const musicList = buildDownloadItems(selectedTracks)
  try {
    await startDownload(musicList, buildBatchName(musicList))
    exitSelectMode()
  } catch (error) {
    message.error(`下载失败：${error?.message || error}`)
  }
}

const enterSelectMode = () => { isSelectMode.value = true }
const exitSelectMode = () => {
  isSelectMode.value = false
  selectedTrackIds.value = []
}

// 播放单首：调后端 /song 获取真实 URL + 歌词，emit 给 App.vue
const playTrack = async (track) => {
  if (isTrackUnavailable(track)) {
    message.warning(`《${track.name}》因版权问题暂时无法播放`)
    return
  }
  if (!track?.id) {
    message.error(`《${track.name}》缺少歌曲ID，请重新搜索`)
    return
  }

  parsingTrackId.value = track.id
  parsingType.value = 'play'

  try {
    const qualityValue = settings.selectedQuality || 'lossless'
    const musicInfo = await parseMusicInfo(track.id, qualityValue, track.source)
    if (!musicInfo?.url || !musicInfo.available) {
      markTrackUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法播放`)
      return
    }
    emit('track-parsed', { track, quality: qualityValue })
    emit('track-play', {
      ...track,
      id: musicInfo.id,
      name: musicInfo.name,
      artist: musicInfo.artist,
      album: musicInfo.album,
      cover: musicInfo.cover,
      url: musicInfo.url,
      duration: musicInfo.duration,
      level: musicInfo.level,
      fileExtension: musicInfo.fileExtension,
      lrc: musicInfo.lyric || ''
    })
    message.success(`开始播放：${track.name}`)
  } catch (error) {
    message.error(`播放失败：${error?.message || error}`)
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
    await startDownload([{
      id: track.id,
      name: track.name,
      artist: getArtist(track),
      album: getAlbum(track),
      source: track.source || ''
    }], track.name)
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

const handleBatchDownload = async () => {
  if (!props.items || props.items.length === 0) {
    message.warning('没有可下载的歌曲')
    return
  }
  const musicList = buildDownloadItems(props.items.filter(t => t.id))
  if (musicList.length === 0) {
    message.error('没有可下载的歌曲（缺少ID）')
    return
  }
  try {
    await startDownload(musicList, props.detailInfo?.name || '歌单')
  } catch (error) {
    message.error(`加入下载队列失败: ${error?.message || error}`)
  }
}
</script>

<style scoped>
.song-list-panel {
  width: 100%;
  margin-top: 0 !important;
  padding-top: 0 !important;
}

.detail-view {
  padding: 0;
}

.col-select {
  width: 40px;
  text-align: center;
}

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
  justify-content: center;
  align-items: center;
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

.tracks-table-wrapper {
  overflow-x: auto;
}

.tracks-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
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
  width: 56px;
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
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, color-mix(in srgb, var(--color-primary) 15%, var(--color-surface-container)) 50%, var(--color-primary-light) 100%);
}

.col-name {
  width: 280px;
  overflow: hidden;
}

.track-name-row {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: nowrap;
  margin-bottom: 2px;
  max-width: 100%;
}

.track-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.track-artist {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.col-album {
  font-size: 14px;
  color: var(--color-text-muted);
  width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-pay {
  width: 60px;
  text-align: center;
  white-space: nowrap;
}

.pay-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.pay-free {
  color: #52c41a;
  background: #f6ffed;
}

.pay-vip {
  color: #faad14;
  background: #fffbe6;
}

.col-quality {
  width: 80px;
  text-align: center;
  white-space: nowrap;
}

.quality-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.quality-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-on-surface);
}

.quality-size {
  font-size: 10px;
  color: var(--color-text-muted);
}

.tracks-table td.col-action {
  width: 100px;
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

.track-row.unavailable {
  background-color: #f5f5f5 !important;
  cursor: not-allowed;
  opacity: 0.7;
}

.track-row.unavailable:hover {
  background-color: #e8e8e8 !important;
}

.track-row.unavailable .track-name,
.track-row.unavailable .track-artist,
.track-row.unavailable .col-album {
  color: #999 !important;
}

.track-cover.grayscale {
  filter: grayscale(100%);
  opacity: 0.5;
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
  margin-left: 0;
  padding: 2px 6px;
  font-size: 10px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.dark .track-row.unavailable {
  background-color: #2a2a2a !important;
}

.dark .track-row.unavailable:hover {
  background-color: #333 !important;
}

.dark .track-row.unavailable .track-name,
.dark .track-row.unavailable .track-artist,
.dark .track-row.unavailable .col-album {
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

.dark .pay-free {
  color: #73d13d;
  background: #162312;
}

.dark .pay-vip {
  color: #ffc53d;
  background: #2b2111;
}

.dark .quality-label {
  color: #e0e0e0;
}

.dark .quality-size {
  color: #888;
}

/* ========== 歌单列表样式 ========== */
.playlist-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.5rem;
  padding: 0 1.5rem 1.5rem 1.5rem;
}

@media (min-width: 640px) {
  .playlist-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .playlist-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1280px) {
  .playlist-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.playlist-card {
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
}

.playlist-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.playlist-cover-wrapper {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
}

.playlist-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.playlist-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, color-mix(in srgb, var(--color-primary) 15%, var(--color-surface-container)) 50%, var(--color-primary-light) 100%);
}

.playlist-card:hover .playlist-cover {
  transform: scale(1.05);
}

.playlist-overlay {
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

.playlist-source-tag {
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

.playlist-info {
  padding: 1rem;
}

.playlist-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-creator {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.playlist-action {
  padding: 0 1rem 1rem;
}

.playlist-action :deep(.ant-btn) {
  width: 100%;
}
</style>
