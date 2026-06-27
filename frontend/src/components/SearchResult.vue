<template>
  <div v-if="hasResults || currentDetail || hasSearchResults || hasSearched" class="search-result-panel">
    <!-- 返回按钮（二级页面时显示） -->
    <div v-if="currentDetail" class="back-bar">
      <a-button type="link" @click="goBack" class="back-button">
        ← 返回搜索结果
      </a-button>
    </div>

    <!-- 搜索类型Tab（只要搜索过就显示，避免切歌单 tab 时 tabs 消失） -->
    <div v-if="hasSearched && !currentDetail" class="search-tabs">
      <a-button
        v-for="tab in searchTabs"
        :key="tab.key"
        type="text"
        :class="['search-tab', { active: currentSearchType === tab.key }]"
        @click="handleSearchTabClick(tab.key)"
      >
        {{ tab.label }}
      </a-button>
    </div>

    <!-- 加载中：tab 切换 或 详情加载 -->
    <div v-if="tabLoading || (currentDetail && currentDetail.loading)" class="loading-view">
      <div class="loading-spinner"></div>
      <span class="loading-text">正在加载中...</span>
    </div>

    <!-- 二级页面：歌单/专辑/歌手详情 -->
    <SongList
      v-if="currentDetail && !currentDetail.loading && detailTracks.length > 0"
      type="song"
      :items="detailTracks"
      :detail-info="currentDetail"
      @track-play="handleTrackPlay"
      @track-unavailable="handleTrackUnavailable"
    />

    <!-- 一级页面：单曲列表 -->
    <SongList
      v-show="displayMode === 'search' && !currentDetail && songs.length > 0"
      type="song"
      :items="songs"
      @track-play="handleTrackPlay"
      @track-unavailable="handleTrackUnavailable"
    />

    <!-- 一级页面：歌单列表 -->
    <SongList
      v-show="displayMode === 'playlist' && !currentDetail && playlists.length > 0"
      type="playlist"
      :items="playlists"
      @item-click="handleItemClick"
    />

    <!-- 当前 tab 搜索结果为空时显示提示（加载中时不展示空提示） -->
    <div v-if="!loading && !tabLoading && hasSearched && !currentDetail && isCurrentTabEmpty" class="empty-tab-hint">
      <a-empty
        v-if="displayMode === 'playlist' && isPlaylistSearchUnsupported"
        description="该平台不支持歌单搜索，请粘贴歌单链接进行解析（网易云/QQ 音乐支持歌单搜索）"
      >
        <template #image>
          <span style="font-size: 48px;">🚫</span>
        </template>
      </a-empty>
      <a-empty v-else :description="`未找到相关${emptyTabName}`" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { message, notification } from 'ant-design-vue'
import { settings } from '../utils/settingsManager.js'
import musicApi from '../services/musicApi.js'
import SongList from './SongList.vue'

const props = defineProps({
  songs: {
    type: Array,
    default: () => []
  },
  playlists: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  tabLoading: {
    type: Boolean,
    default: false
  },
  searchType: {
    type: String,
    default: 'keyword' // 'keyword' | 'music_link' | 'playlist_link'
  },
  warnings: {
    type: Array,
    default: () => [] // 后端搜索返回的警告列表，如 ['playlist_search_unsupported']
  }
})

const emit = defineEmits(['track-play', 'search-type-change'])

// 搜索类型Tab配置
const searchTabs = computed(() => {
  switch (props.searchType) {
    case 'music_link':
      return [{ key: 'search', label: '单曲' }]
    case 'playlist_link':
      return [{ key: 'playlist', label: '歌单' }]
    default:
      return [
        { key: 'search', label: '单曲' },
        { key: 'playlist', label: '歌单' }
      ]
  }
})

const getDefaultSearchType = () => {
  switch (props.searchType) {
    case 'music_link': return 'search'
    case 'playlist_link': return 'playlist'
    default: return 'search'
  }
}

const currentSearchType = ref(getDefaultSearchType())

// 是否已搜索过
const hasSearched = ref(false)
let prevLoading = false
watch(
  [() => props.songs, () => props.playlists, () => props.loading],
  ([songs, playlists, loading]) => {
    if (prevLoading && !loading) hasSearched.value = true
    prevLoading = loading
    if (songs.length > 0 || playlists.length > 0) hasSearched.value = true
  },
  { deep: true, immediate: true }
)

// 二级页面状态
const currentDetail = ref(null)
const detailTracks = ref([])

// 缓存
const PLAYLIST_CACHE_KEY = 'wan-music-playlist-cache'
/** 缓存 24 小时（与平台/搜索一致） */
const PLAYLIST_CACHE_TTL_MS = 24 * 60 * 60 * 1000
const cache = ref({ playlist: {} })

const loadCache = () => {
  try {
    const stored = localStorage.getItem(PLAYLIST_CACHE_KEY)
    if (!stored) return {}
    const parsed = JSON.parse(stored)
    if (!parsed.playlist) return {}
    // 过滤过期条目
    const now = Date.now()
    for (const id of Object.keys(parsed.playlist)) {
      const entry = parsed.playlist[id]
      if (!entry?._ts || now - entry._ts > PLAYLIST_CACHE_TTL_MS) {
        delete parsed.playlist[id]
      }
    }
    return parsed
  } catch { return {} }
}

const saveCache = (data) => {
  try { localStorage.setItem(PLAYLIST_CACHE_KEY, JSON.stringify(data)) } catch { /* 静默 */ }
}

cache.value.playlist = loadCache()

watch(() => props.searchType, () => {
  currentSearchType.value = getDefaultSearchType()
})

const handleSearchTabClick = (tabKey) => {
  currentSearchType.value = tabKey
  // 通知 App.vue 切换 tab 时重新拉取对应数据
  emit('search-type-change', tabKey)
}

const hasSearchResults = computed(() => props.songs.length > 0 || props.playlists.length > 0)

const isPlaylistSearchUnsupported = computed(() =>
  props.warnings?.includes('playlist_search_unsupported') || false
)

const displayMode = computed(() => currentSearchType.value)

const isCurrentTabEmpty = computed(() =>
  displayMode.value === 'search' ? props.songs.length === 0 : props.playlists.length === 0
)

const emptyTabName = computed(() => {
  const names = { search: '歌曲', playlist: '歌单' }
  return names[currentSearchType.value] || '结果'
})

const hasResults = computed(() => currentDetail.value || hasSearchResults.value)

const handleTrackPlay = (track) => emit('track-play', track)

const handleTrackUnavailable = (track) => {
  const songIndex = props.songs.findIndex(s => s.id === track.id)
  if (songIndex !== -1) props.songs[songIndex].unavailable = true

  const detailIndex = detailTracks.value.findIndex(t => t.id === track.id)
  if (detailIndex !== -1) detailTracks.value[detailIndex].unavailable = true
}

const handleItemClick = async ({ item, action }) => {
  if (action === 'playlist') await handleParsePlaylist(item)
}

const handleParsePlaylist = async (item) => {
  currentDetail.value = { ...item, loading: true }

  if (settings.enableCache && cache.value.playlist[item.id]) {
    const cached = cache.value.playlist[item.id]
    currentDetail.value = {
      id: cached.id,
      name: cached.name,
      coverImgUrl: cached.coverImgUrl,
      creator: cached.creator,
      trackCount: cached.trackCount,
      loading: false
    }
    detailTracks.value = cached.tracks
    notification.success({
      message: '读取缓存数据成功',
      description: `从缓存找到 ${detailTracks.value.length} 首歌曲`
    })
    return
  }

  try {
    const result = await musicApi.getPlaylistById(item.id, item.source || '')

    if (result.success && result.data) {
      const playlist = result.data
      currentDetail.value = {
        id: playlist.id,
        name: playlist.name,
        coverImgUrl: playlist.coverImgUrl,
        creator: playlist.creator,
        trackCount: playlist.trackCount,
        loading: false
      }
      detailTracks.value = playlist.tracks || []

      cache.value.playlist[item.id] = {
        _ts: Date.now(),
        id: playlist.id,
        name: playlist.name,
        coverImgUrl: playlist.coverImgUrl,
        creator: playlist.creator,
        trackCount: playlist.trackCount,
        tracks: detailTracks.value
      }
      saveCache(cache.value.playlist)

      if (detailTracks.value.length > 0) {
        notification.success({
          message: '解析歌单成功',
          description: `从网络获取 ${detailTracks.value.length} 首歌曲`
        })
      }
    } else {
      const errorMsg = result.error || result.message || '解析失败'
      if (result.errorType === 'privacy') {
        message.warning({ content: '该歌单已设置隐私保护，无法查看（QQ音乐官方限制）', duration: 4 })
      } else {
        message.error(errorMsg)
      }
      currentDetail.value = null
    }
  } catch {
    message.error('解析失败，请稍后重试')
    currentDetail.value = null
  }
}

const goBack = () => {
  currentDetail.value = null
  detailTracks.value = []
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
.empty-tab-hint {
  padding: 48px 16px;
  display: flex;
  justify-content: center;
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

.back-bar {
  padding: 1rem 1.5rem;
  background: var(--color-surface-container-low);
  border-bottom: 1px solid var(--color-border-subtle);
}

.back-button {
  font-size: 14px;
  color: var(--color-primary);
  padding: 0;
}

.back-button:hover {
  color: var(--color-primary-dark);
}

.search-tabs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
}

.search-tab {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 1rem;
  font-size: 14px;
  color: var(--color-on-surface);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}

.search-tab:deep(.ant-btn) {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0;
  height: auto;
  color: var(--color-on-surface);
  font-weight: 600;
}

.search-tab:hover {
  background: var(--color-surface-container-low);
  color: var(--color-primary);
}

.search-tab.active {
  background: var(--color-primary);
  color: #fff;
}
</style>
