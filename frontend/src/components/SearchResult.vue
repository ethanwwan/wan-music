<template>
  <div v-if="hasResults || currentDetail || hasSearchResults || hasSearched" class="search-result-panel">
    <!-- 返回按钮（二级页面时显示） -->
    <div v-if="currentDetail" class="back-bar">
      <a-button 
        type="link"
        @click="goBack"
        class="back-button"
      >
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

    <!-- loading 状态 -->
    <div v-if="currentDetail && currentDetail.loading" class="loading-view">
      <div class="loading-spinner"></div>
      <span class="loading-text">正在加载中...</span>
    </div>

    <!-- 二级页面：歌单/专辑/歌手详情 - 使用 SongList 组件 -->
    <SongList 
      v-if="currentDetail && !currentDetail.loading && detailTracks.length > 0"
      type="song"
      :items="detailTracks"
      :detail-info="currentDetail"
      :current-page="currentDetailPage"
      :page-size="detailPageSize"
      :total-tracks="detailTracks.length"
      @track-play="handleTrackPlay"
      @track-unavailable="handleTrackUnavailable"
      @page-change="goToDetailPage"
    />

    <!-- 一级页面：单曲列表 -->
    <SongList
      v-show="displayMode === 'search' && !currentDetail && songs.length > 0"
      type="song"
      :items="songs"
      :current-page="currentPage"
      :page-size="pageSize"
      :total-tracks="songs.length"
      @track-play="handleTrackPlay"
      @track-unavailable="handleTrackUnavailable"
      @page-change="goToPage"
    />

    <!-- 一级页面：歌曲列表 -->
    <SongList
      v-show="displayMode === 'search' && songs.length > 0"
      type="search"
      :items="currentPageData"
      @select="handleSelect"
    />

    <!-- 一级页面：歌单列表 -->
    <SongList
      v-show="displayMode === 'playlist' && !currentDetail && playlists.length > 0"
      type="playlist"
      :items="currentPageData"
      @item-click="handleItemClick"
      @select="handleSelect"
    />

    <!-- 分页组件（歌单搜索结果） - 只有超过1页时才显示 -->
    <Pagination
      v-if="displayMode === 'playlist' && !currentDetail && totalPages > 1"
      :total-count="totalCount"
      :page-size="getPageSize()"
      v-model="currentPage"
    />

    <!-- 当前 tab 搜索结果为空时显示提示（避免页面空白白屏） -->
    <div v-if="!loading && hasSearched && !currentDetail && isCurrentTabEmpty" class="empty-tab-hint">
      <!-- 酷狗/波点歌单搜索：明确告知不支持 -->
      <a-empty
        v-if="displayMode === 'playlist' && isPlaylistSearchUnsupported"
        description="该平台不支持歌单搜索，请粘贴歌单链接进行解析（网易云/QQ 音乐支持歌单搜索）"
      >
        <template #image>
          <span style="font-size: 48px;">🚫</span>
        </template>
      </a-empty>
      <!-- 普通空结果 -->
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
import Pagination from './Pagination.vue'

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
  searchType: {
    type: String,
    default: 'keyword' // 'keyword' | 'music_link' | 'playlist_link'
  },
  warnings: {
    type: Array,
    default: () => [] // 后端搜索返回的警告列表，如 ['playlist_search_unsupported']
  }
})

const emit = defineEmits(['select', 'track-play', 'search-type-change'])

// 搜索类型Tab配置 - 根据搜索类型动态显示
const searchTabs = computed(() => {
  switch (props.searchType) {
    case 'music_link':
      // 歌曲链接，只显示单曲
      return [{ key: 'search', label: '单曲' }]
    case 'playlist_link':
      // 歌单链接，只显示歌单
      return [{ key: 'playlist', label: '歌单' }]
    default:
      // keyword搜索，显示单曲和歌单
      return [
        { key: 'search', label: '单曲' },
        { key: 'playlist', label: '歌单' }
      ]
  }
})

// 当前搜索类型 - 根据搜索类型设置默认值
const getDefaultSearchType = () => {
  switch (props.searchType) {
    case 'music_link':
      return 'search'
    case 'playlist_link':
      return 'playlist'
    default:
      return 'search'
  }
}// 当前搜索类型
const currentSearchType = ref(getDefaultSearchType())

// 是否已搜索过（用于控制空状态显示，避免页面完全空白）
const hasSearched = ref(false)
// 监听 props.songs / props.playlists 变化，搜索结束后置为 true
watch(
  [() => props.songs, () => props.playlists, () => props.loading],
  ([songs, playlists, loading]) => {
    // 只要 props.songs 或 props.playlists 数组长度>0，就说明搜过
    if (songs.length > 0 || playlists.length > 0) {
      hasSearched.value = true
    }
    // 搜索开始时（loading=true）也置为 true
    if (loading) {
      hasSearched.value = true
    }
  },
  { deep: true, immediate: true }
)

// 二级页面状态
const currentDetail = ref(null)
const detailTracks = ref([])

// 详情页分页配置
const currentDetailPage = ref(1)
const detailPageSize = ref(12)

// 从 localStorage 加载缓存
const loadDetailCache = () => {
  const storedPlaylist = localStorage.getItem('wan-music-playlist-cache')
  return {
    playlist: storedPlaylist ? JSON.parse(storedPlaylist) : {}
  }
}

// 保存缓存到 localStorage
const saveDetailCache = (type, data) => {
  localStorage.setItem(`wan-music-${type}-cache`, JSON.stringify(data))
}

// 缓存存储（歌单和专辑，从 localStorage 加载）
const cache = ref(loadDetailCache())

// 分页配置 - 单曲每页12条
const currentPage = ref(1)
const pageSize = ref(12)

// 歌单分页配置 - 每页3行
const playlistPageSize = ref(6)           // 移动端：3行 × 2列 = 6个
const playlistPageSizeLarge = ref(12)     // 大屏：3行 × 4列 = 12个

// 监听模式变化，切换时重置分页和详情状态
watch(() => props.currentMode, () => {
  currentPage.value = 1
  currentDetailPage.value = 1
  currentDetail.value = null
  detailTracks.value = []
})

// 监听单曲搜索结果变化，重新搜索时重置所有状态
watch(
  () => props.songs.length,
  (newLength, oldLength) => {
    // 只有当从无数据变为有数据时（初始搜索），才切换回单曲tab
    if (newLength > 0 && oldLength === 0) {
      // 切换回单曲tab
      currentSearchType.value = 'search'
      // 重置到第一页
      currentPage.value = 1
      // 清除详情状态
      currentDetail.value = null
      detailTracks.value = []
      currentDetailPage.value = 1
    }
  }
)

// 监听searchType变化，更新当前搜索类型
watch(() => props.searchType, () => {
  currentSearchType.value = getDefaultSearchType()
})

// 获取各Tab的数据数量
const getTabCount = (tabKey) => {
  switch (tabKey) {
    case 'search':
      return props.songs.length
    case 'playlist':
      return props.playlists.length
    default:
      return 0
  }
}

// 根据displayMode获取对应的pageSize
const getPageSize = () => {
  switch (displayMode.value) {
    case 'playlist':
      // 歌单列表：每页3行，移动端每行2个(6个)，大屏每行4个(12个)
      return window.innerWidth >= 1280 ? playlistPageSizeLarge.value : playlistPageSize.value
    default:
      return pageSize.value
  }
}

// 是否有搜索结果
const hasSearchResults = computed(() => {
  return props.songs.length > 0 || props.playlists.length > 0
})

// 后端是否标记当前请求的歌单搜索平台不支持
const isPlaylistSearchUnsupported = computed(() => {
  return props.warnings?.includes('playlist_search_unsupported') || false
})

const displayMode = computed(() => {
  return currentSearchType.value
})

const totalCount = computed(() => {
  return getTabCount(currentSearchType.value)
})

// 当前 tab 是否为空（避免页面空白白屏，给用户友好提示）
const isCurrentTabEmpty = computed(() => {
  return totalCount.value === 0
})

// 当前 tab 的名称（用于空状态文案）
const emptyTabName = computed(() => {
  const names = {
    search: '歌曲',
    playlist: '歌单'
  }
  return names[currentSearchType.value] || '结果'
})

// 分页计算
const totalPages = computed(() => {
  return Math.ceil(totalCount.value / getPageSize())
})

// 当前页的数据
const currentPageData = computed(() => {
  const currentPageSize = getPageSize()
  const start = (currentPage.value - 1) * currentPageSize
  const end = start + currentPageSize

  switch (currentSearchType.value) {
    case 'playlist':
      return props.playlists.slice(start, end)
    default:
      return []
  }
})

// Tab切换方法
const handleSearchTabClick = (tabKey) => {
  currentSearchType.value = tabKey
  currentPage.value = 1
  
  const currentDataCount = getTabCount(tabKey)
  if (currentDataCount === 0) {
    emit('search-type-change', tabKey)
  }
}

// 分页方法
const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

// 详情页分页计算
const detailTotalPages = computed(() => {
  return Math.ceil(detailTracks.value.length / detailPageSize.value)
})

const goToDetailPage = (page) => {
  if (page >= 1 && page <= detailTotalPages.value) {
    currentDetailPage.value = page
  }
}

const resetDetailPagination = () => {
  currentDetailPage.value = 1
}

const hasResults = computed(() => {
  if (currentDetail.value) return true
  return getTabCount(currentSearchType.value) > 0
})

const handleSelect = (item) => {
  emit('select', item)
}

// 处理播放事件
const handleTrackPlay = (track, playlist) => {
  emit('track-play', track, playlist)
}

// 处理歌曲无版权事件
const handleTrackUnavailable = (track) => {
  // 标记歌曲为不可用（props.songs 是数组引用，直接修改会影响原始数据）
  const songIndex = props.songs.findIndex(s => s.id === track.id)
  if (songIndex !== -1) {
    props.songs[songIndex].unavailable = true
  }
  
  // 更新详情列表中的歌曲状态
  const detailIndex = detailTracks.value.findIndex(t => t.id === track.id)
  if (detailIndex !== -1) {
    detailTracks.value[detailIndex].unavailable = true
  }
  
  // 吐司提示已在 SongList 中处理
}

// 处理列表项点击（目前只支持歌单）
const handleItemClick = async ({ item, action }) => {
  if (action === 'playlist') {
    await handleParsePlaylist(item)
  }
}

// 解析歌单
const handleParsePlaylist = async (item) => {
  resetDetailPagination()
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
      message: '使用缓存数据',
      description: `找到 ${detailTracks.value.length} 首歌曲`,
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
        id: playlist.id,
        name: playlist.name,
        coverImgUrl: playlist.coverImgUrl,
        creator: playlist.creator,
        trackCount: playlist.trackCount,
        tracks: detailTracks.value
      }
      saveDetailCache('playlist', cache.value.playlist)

      if (detailTracks.value.length > 0) {
        notification.success({
          message: '解析成功',
          description: `找到 ${detailTracks.value.length} 首歌曲`,
        })
      }
    } else {
      // 歌单加载失败：隐私歌单、歌单不存在、登录态失效等
      const errorMsg = result.error || result.message || '解析失败'
      if (result.errorType === 'privacy') {
        message.warning({
          content: `该歌单已设置隐私保护，无法查看（QQ音乐官方限制）`,
          duration: 4
        })
      } else {
        message.error(errorMsg)
      }
      currentDetail.value = null
    }
  } catch (error) {
    message.error('解析失败，请稍后重试')
    currentDetail.value = null
  }
}

const goBack = () => {
  currentDetail.value = null
  detailTracks.value = []
  currentDetailPage.value = 1
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

/* loading 状态 */
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

/* 返回按钮栏 */
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

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--color-border-subtle);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-right {
  display: flex;
  align-items: center;
}

.result-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-on-surface);
  margin: 0;
}

.result-count {
  font-size: 14px;
  color: var(--color-text-muted);
  padding: 4px 12px;
  background: var(--color-surface-container-low);
  border-radius: 20px;
}

/* 搜索Tab */
.search-tabs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem 1rem 1.5rem;
  margin-bottom: 0;
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

.search-tab:hover:deep(.ant-btn) {
  background: transparent;
  color: var(--color-primary);
}

.search-tab.active {
  background: var(--color-primary);
  color: #fff;
}

.search-tab.active:deep(.ant-btn) {
  background: transparent;
  color: #fff;
  font-weight: 600;
}
</style>
