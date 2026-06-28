<template>
  <div v-if="hasContent" class="search-result-panel">
    <div v-if="loading" class="loading-view">
      <div class="loading-spinner"></div>
      <span class="loading-text">正在加载中...</span>
    </div>

    <a-empty v-else-if="searched && songs.length === 0" description="未找到相关结果" />

    <div v-else-if="songs.length > 0" class="tracks-table-wrapper">
      <!-- 歌单详情头部：仅 playlist 模式展示 -->
      <div v-if="type === 'playlist' && detail" class="detail-header">
        <div class="header-left">
          <div class="detail-cover-wrapper">
            <img
              v-if="detail.cover"
              :src="proxyImg(detail.cover)"
              :alt="detail.name"
              class="detail-cover"
            />
            <div v-else class="cover-placeholder"></div>
          </div>
          <div class="detail-info">
            <h1 class="detail-name">{{ detail.name }}</h1>
            <div class="detail-meta">
              <template v-if="detail.creator">
                <span class="meta-item">创建者：{{ detail.creator }}</span>
                <span class="meta-separator">•</span>
              </template>
              <span class="meta-item">共 {{ detail.trackCount || songs.length }} 首歌曲</span>
            </div>
          </div>
        </div>
        <div class="header-right">
          <a-button type="primary" @click="downloadAllInPlaylist">全部下载</a-button>
        </div>
      </div>

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
              <template v-if="isSelectMode">已选 {{ selectedIds.length }}/{{ songs.length }}</template>
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
                  <a-button size="small" type="primary" :disabled="selectedIds.length === 0" @click="handleBatchDownloadSelected">下载</a-button>
                  <a-button size="small" @click="exitSelectMode">取消</a-button>
                </a-space>
              </template>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(track, index) in songs"
            :key="track.id"
            class="track-row"
            :class="{
              'unavailable': track.unavailable,
              'selected-for-batch': isSelectMode && selectedIds.includes(track.id)
            }"
          >
            <td v-if="isSelectMode" class="col-select" @click.stop>
              <a-checkbox
                :checked="selectedIds.includes(track.id)"
                @change="() => toggleSelect(track)"
              />
            </td>
            <td class="col-index">{{ index + 1 }}</td>
            <td class="col-cover">
              <div class="track-cover-wrapper">
                <img
                  v-if="track.picUrl && !track.picError"
                  :src="track.picUrl"
                  :alt="track.name"
                  class="track-cover"
                  :class="{ 'grayscale': track.unavailable }"
                  loading="lazy"
                  @error="track.picError = true"
                />
                <div v-else class="track-cover-placeholder"></div>
              </div>
            </td>
            <td class="col-name">
              <div class="track-name-row">
                <span class="track-name" :class="{ 'unavailable-text': track.unavailable }">{{ track.name }}</span>
                <span v-if="track.unavailable" class="unavailable-reason">无版权</span>
                <span
                  v-if="track.source"
                  class="source-tag"
                  :style="{ backgroundColor: getPlatformColor(track.source) + '20', color: getPlatformColor(track.source) }"
                >
                  {{ getPlatformName(track.source) }}
                </span>
              </div>
              <div class="track-artist" :class="{ 'unavailable-text': track.unavailable }">{{ track.artists }}</div>
            </td>
            <td class="col-album" :class="{ 'unavailable-text': track.unavailable }">{{ track.album || '-' }}</td>
            <td class="col-pay">
              <span
                v-if="track.pay || track.fee"
                class="pay-tag"
                :class="`pay-${getPayKey(track)}`"
                :title="getPayTitle(track)"
              >
                {{ getPayLabel(track) }}
              </span>
            </td>
            <td class="col-quality">
              <div v-if="track.bestQuality" class="quality-info">
                <span class="quality-label">{{ getQualityLabel(track.bestQuality) }}</span>
                <span v-if="getQualitySize(track)" class="quality-size">{{ getQualitySize(track) }}</span>
              </div>
            </td>
            <td class="col-action">
              <a-button
                type="text"
                :disabled="parsingId === track.id && parsingType === 'play' || track.unavailable"
                :loading="parsingId === track.id && parsingType === 'play'"
                :title="track.unavailable ? '该歌曲无版权' : '播放'"
                @click.stop="playTrack(track)"
              >
                <template #icon><PlayCircleOutlined /></template>
              </a-button>
              <a-button
                type="text"
                :disabled="parsingId === track.id && parsingType === 'download' || track.unavailable"
                :loading="parsingId === track.id && parsingType === 'download'"
                :title="track.unavailable ? '该歌曲无版权' : '下载'"
                @click.stop="downloadSingle(track)"
              >
                <template #icon><ArrowDownOutlined /></template>
              </a-button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, ArrowDownOutlined } from '@ant-design/icons-vue'
import { parseMusicInfo } from '../services/musicApi.js'
import { settings } from '../utils/settingsManager.js'
import { downloadQueueStore as queueStore } from '../stores/downloadQueue.js'
import { getPlatformById } from '../utils/platformsManager.js'

const props = defineProps({
  songs: { type: Array, default: () => [] },
  /** 搜索类型：'song'（单曲）| 'playlist'（歌单）| 'unknown' */
  type: { type: String, default: 'song' },
  /** 歌单详情：{ name, creator, cover, trackCount }（仅 playlist 模式有） */
  detail: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  searched: { type: Boolean, default: false }
})

const emit = defineEmits(['track-play', 'track-unavailable'])

const hasContent = computed(() => props.loading || props.searched || props.songs.length > 0)

const parsingId = ref(null)
const parsingType = ref(null)

const isSelectMode = ref(false)
const selectedIds = ref([])

const isAllSelected = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length === props.songs.length
)
const isPartiallySelected = computed(() => {
  const total = props.songs.length
  return total > 0 && selectedIds.value.length > 0 && selectedIds.value.length < total
})

const getPlatformName = (id) => getPlatformById(id)?.name || id
const getPlatformColor = (id) => getPlatformById(id)?.color || '#999'

const QUALITY_LABELS = {
  standard: '标准', exhigh: '极高', lossless: '无损', hires: 'Hi-Res',
  dolby: '杜比', sky: '环绕声', jymaster: '母带', jyeffect: '臻音',
}
const getQualityLabel = (key) => (key ? (QUALITY_LABELS[key] || key) : '')
const formatSize = (bytes) => {
  if (!bytes || bytes <= 0) return ''
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}
const getQualitySize = (track) => {
  const key = track.bestQuality
  return key ? formatSize(track.qualityMap?.[key]?.size) : ''
}

// 付费标签：fee=1 VIP / fee=4 专辑 / fee=8 部分试听
const getPayLabel = (track) => {
  const fee = track.fee
  if (fee === 1) return 'VIP'
  if (fee === 4) return '专辑'
  if (fee === 8 || fee === 16) return '试听'
  return track.pay ? '付费' : ''
}
// 付费类型 key：用于 CSS 样式分支
const getPayKey = (track) => {
  const fee = track.fee
  if (fee === 1) return 'vip'
  if (fee === 4) return 'album'
  if (fee === 8 || fee === 16) return 'preview'
  return track.pay ? 'paid' : ''
}
const getPayTitle = (track) => {
  const label = getPayLabel(track)
  return label ? `付费内容（${label}）` : ''
}

const toggleSelect = (track) => {
  const ids = selectedIds.value
  if (ids.includes(track.id)) {
    selectedIds.value = ids.filter(id => id !== track.id)
  } else {
    selectedIds.value = [...ids, track.id]
    isSelectMode.value = true
  }
}

const handleSelectAll = (e) => {
  const checked = typeof e === 'boolean' ? e : (e?.target?.checked ?? false)
  selectedIds.value = checked ? props.songs.map(t => t.id) : []
}

const enterSelectMode = () => { isSelectMode.value = true }
const exitSelectMode = () => {
  isSelectMode.value = false
  selectedIds.value = []
}

const markUnavailable = (track) => {
  track.unavailable = true
  emit('track-unavailable', track)
}

// 播放单首：调后端 /song 拿真实 URL + 歌词
const playTrack = async (track) => {
  if (track.unavailable) {
    message.warning(`《${track.name}》因版权问题暂时无法播放`)
    return
  }
  if (!track?.id) {
    message.error(`《${track.name}》缺少歌曲ID，请重新搜索`)
    return
  }

  parsingId.value = track.id
  parsingType.value = 'play'

  try {
    const quality = settings.selectedQuality || 'lossless'
    const info = await parseMusicInfo(track.id, quality, track.source)
    if (!info?.url || !info.available) {
      markUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法播放`)
      return
    }
    emit('track-play', {
      ...track,
      id: info.id,
      name: info.name,
      artist: info.artist,
      album: info.album,
      cover: info.cover,
      url: info.url,
      duration: info.duration,
      fileExtension: info.fileExtension,
      lrc: info.lyric || '',
    })
    message.success(`开始播放：${track.name}`)
  } catch (error) {
    message.error(`播放失败：${error?.message || error}`)
  } finally {
    parsingId.value = null
    parsingType.value = null
  }
}

const startDownload = (musicList, label) => queueStore.addTask(
  musicList,
  label,
  {
    selectedQuality: settings.selectedQuality || 'lossless',
    filenameFormat: settings.filenameFormat || 'song-artist',
    writeMetadata: settings.writeMetadata !== false,
  }
).then(() => {
  message.success(`已加入下载队列：${musicList.length} 首歌曲`)
  queueStore.openDrawer()
})

const buildDownloadItem = (track) => ({
  id: track.id,
  name: track.name,
  artist: track.artists,
  album: track.album,
  source: track.source || '',
  qualityMap: track.qualityMap || {},
})

const downloadSingle = async (track) => {
  if (track.unavailable) {
    message.warning(`《${track.name}》因版权问题暂时无法下载`)
    return
  }
  if (!track.id) {
    message.error(`《${track.name}》缺少歌曲ID，请重新搜索`)
    return
  }
  parsingId.value = track.id
  parsingType.value = 'download'
  try {
    await startDownload([buildDownloadItem(track)], track.name)
  } catch (error) {
    const msg = error?.message || String(error) || '未知错误'
    if (msg.includes('已下架') || msg.includes('无法获取') || msg.includes('未找到') || msg.includes('版权')) {
      markUnavailable(track)
      message.warning(`《${track.name}》因版权问题暂时无法下载`)
    } else {
      message.error(`下载失败：${msg}`)
    }
  } finally {
    parsingId.value = null
    parsingType.value = null
  }
}

const handleBatchDownloadSelected = async () => {
  if (selectedIds.value.length === 0) {
    message.warning('请先选择要下载的歌曲')
    return
  }
  const tracks = props.songs.filter(t => selectedIds.value.includes(t.id))
  const items = tracks.map(buildDownloadItem)
  const label = items.length > 1 ? `${items[0].name}等${items.length}首` : items[0].name
  try {
    await startDownload(items, label)
    exitSelectMode()
  } catch (error) {
    message.error(`下载失败：${error?.message || error}`)
  }
}

// 歌单模式：一键全部下载（跳过选择模式）
const downloadAllInPlaylist = async () => {
  if (props.songs.length === 0) return
  const items = props.songs.map(buildDownloadItem)
  const name = props.detail?.name || '歌单'
  const label = items.length > 1 ? `${name}（${items.length}首）` : items[0].name
  try {
    await startDownload(items, label)
  } catch (error) {
    message.error(`下载失败：${error?.message || error}`)
  }
}

// 包装图片 URL 走 /image 代理（避免跨域 ORB 阻断）
const proxyImg = (url) => {
  if (!url || typeof url !== 'string') return ''
  if (url.startsWith('/image') || url.startsWith('data:') || url.startsWith('blob:')) return url
  if (!/^https?:\/\//.test(url)) return url
  return `/image?url=${encodeURIComponent(url)}`
}
</script>

<style scoped>
.search-result-panel {
  margin-top: 2rem;
  background: var(--color-surface-white);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.loading-view {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  min-height: 300px;
  padding: 2rem;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-surface-container);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-text {
  font-size: 14px;
  color: var(--color-text-muted);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.select-hint {
  font-size: 13px;
  color: var(--color-text-muted);
  margin-right: 8px;
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
}

.tracks-table td {
  padding: 12px 16px;
  vertical-align: middle;
}

.track-row:hover {
  background: var(--color-primary-light);
}

.track-row.unavailable {
  background-color: #f5f5f5 !important;
  cursor: not-allowed;
  opacity: 0.7;
}

.track-row.selected-for-batch {
  background: var(--color-primary-light);
}

.col-select { width: 40px; text-align: center; }
.col-index { width: 40px; text-align: center; color: var(--color-text-muted); font-size: 14px; }
.col-cover { width: 56px; padding: 8px; }
.col-name { width: 280px; overflow: hidden; }
.col-album { font-size: 14px; color: var(--color-text-muted); width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-pay { width: 70px; text-align: center; }
.col-quality { width: 90px; text-align: center; }
.col-action { width: 130px; text-align: center; }

/* ==================== 歌单详情头部（toolbar）=================== */
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: var(--color-surface-container-low);
  border-bottom: 1px solid var(--color-border-subtle);
  gap: 20px;
}
.header-left { display: flex; align-items: center; gap: 16px; min-width: 0; }
.detail-cover-wrapper {
  width: 96px; height: 96px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface-container);
  flex-shrink: 0;
}
.detail-cover { width: 100%; height: 100%; object-fit: cover; }
.cover-placeholder { width: 100%; height: 100%; background: var(--color-surface-container); }
.detail-info { min-width: 0; }
.detail-name {
  font-size: 20px; font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--color-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.detail-meta { display: flex; align-items: center; gap: 8px; color: var(--color-text-muted); font-size: 13px; }
.meta-separator { color: var(--color-text-muted); opacity: 0.5; }

.track-cover-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
}
.track-cover { width: 100%; height: 100%; object-fit: cover; }
.track-cover-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, var(--color-primary-light) 0%, var(--color-surface-container) 100%);
}
.track-cover.grayscale { filter: grayscale(100%); opacity: 0.5; }

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
}
.track-artist {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.source-tag {
  display: inline-block;
  padding: 2px 6px;
  font-size: 10px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.pay-tag {
  display: inline-block;
  padding: 2px 8px;
  font-size: 10px;
  border-radius: 10px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}
/* 各付费类型配色 */
.pay-tag.pay-vip     { color: #d4380d; background: #fff1f0; border: 1px solid #ffa39e; }
.pay-tag.pay-album   { color: #d48806; background: #fffbe6; border: 1px solid #ffe58f; }
.pay-tag.pay-preview { color: #1d39c4; background: #f0f5ff; border: 1px solid #adc6ff; }
.pay-tag.pay-paid    { color: #d4380d; background: #fff7e6; border: 1px solid #ffd591; }

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

.unavailable-text { color: #999 !important; }

.quality-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}
.quality-label { font-size: 12px; font-weight: 500; color: var(--color-on-surface); }
.quality-size { font-size: 10px; color: var(--color-text-muted); }

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

.dark .track-row.unavailable { background-color: #2a2a2a !important; }
.dark .unavailable-reason { color: #ff7875; background: #2a1a1a; }
</style>
