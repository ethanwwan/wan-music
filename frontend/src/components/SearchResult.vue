<template>
  <div v-if="hasResults || currentDetail || hasSearchResults" class="search-result-panel">
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

    <!-- 结果头部 -->
    <div v-if="!currentDetail" class="result-header">
      <div class="header-left">
        <h3 class="result-title">{{ title }}</h3>
      </div>
      <div class="header-right">
        <a-select 
          v-model:value="selectedDataSource" 
          placeholder="选择数据源" 
          size="small"
          style="width: 140px"
          @change="handleDataSourceChange"
        >
          <a-select-option value="all">全部</a-select-option>
          <a-select-option value="netease">网易云音乐</a-select-option>
          <a-select-option value="qq">QQ音乐</a-select-option>
          <a-select-option value="kugou">酷狗音乐</a-select-option>
          <a-select-option value="bodian">波点音乐</a-select-option>
        </a-select>
      </div>
    </div>

    <!-- 搜索类型Tab（搜索结果不为空时显示） -->
    <div v-if="hasSearchResults && !currentDetail" class="search-tabs">
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
      @track-parsed="handleTrackParse"
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
      @track-parsed="handleTrackParse"
      @track-play="handleTrackPlay"
      @track-unavailable="handleTrackUnavailable"
      @page-change="goToPage"
    />

    <!-- 一级页面：歌手列表 -->
    <SongList
      v-show="displayMode === 'artist' && !currentDetail"
      type="artist"
      :items="currentPageData"
      @item-click="handleItemClick"
      @select="handleSelect"
    />

    <!-- 一级页面：歌单列表 -->
    <SongList
      v-show="displayMode === 'playlist' && !currentDetail"
      type="playlist"
      :items="currentPageData"
      @item-click="handleItemClick"
      @select="handleSelect"
    />

    <!-- 一级页面：专辑列表 -->
    <SongList
      v-show="displayMode === 'album' && !currentDetail"
      type="album"
      :items="currentPageData"
      @item-click="handleItemClick"
      @select="handleSelect"
    />

    <!-- 分页组件（歌手、歌单和专辑搜索结果） -->
    <Pagination 
      v-if="(displayMode === 'playlist' || displayMode === 'album' || displayMode === 'artist') && !currentDetail && totalCount > 0"
      :total-count="totalCount"
      :page-size="getPageSize()"
      v-model="currentPage"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { message, notification } from 'ant-design-vue'
import { settings } from '../utils/settingsManager.js'
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
  albums: {
    type: Array,
    default: () => []
  },
  artists: {
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
  }
})

const emit = defineEmits(['parse-song', 'parse-playlist', 'parse-album', 'select', 'track-play', 'search-type-change'])

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
}
const currentSearchType = ref(getDefaultSearchType())

// 当前选择的数据源
const selectedDataSource = ref('all')

// 二级页面状态
const currentDetail = ref(null)
const detailTracks = ref([])

// 详情页分页配置
const currentDetailPage = ref(1)
const detailPageSize = ref(10)

// 从 localStorage 加载缓存
const loadDetailCache = () => {
  const storedPlaylist = localStorage.getItem('wan-music-playlist-cache')
  const storedAlbum = localStorage.getItem('wan-music-album-cache')
  const storedArtist = localStorage.getItem('wan-music-artist-cache')
  return {
    playlist: storedPlaylist ? JSON.parse(storedPlaylist) : {},
    album: storedAlbum ? JSON.parse(storedAlbum) : {},
    artist: storedArtist ? JSON.parse(storedArtist) : {}
  }
}

// 保存缓存到 localStorage
const saveDetailCache = (type, data) => {
  localStorage.setItem(`wan-music-${type}-cache`, JSON.stringify(data))
}

// 缓存存储（歌单和专辑，从 localStorage 加载）
const cache = ref(loadDetailCache())

// 分页配置 - 单曲每页10条
const currentPage = ref(1)
const pageSize = ref(10)

// 歌手分页配置 - 每页4行，移动端每行2个(8个)，大屏每行4个(16个)
const artistPageSize = ref(8)
const artistPageSizeLarge = ref(16)

// 歌单/专辑分页配置 - 每页3行
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
watch(() => props.searchType, (newType) => {
  currentSearchType.value = getDefaultSearchType()
})

// 获取各Tab的数据数量
const getTabCount = (tabKey) => {
  switch (tabKey) {
    case 'search':
      return props.songs.length
    case 'artist':
      return props.artists.length
    case 'playlist':
      return props.playlists.length
    case 'album':
      return props.albums.length
    default:
      return 0
  }
}

// 根据displayMode获取对应的pageSize
const getPageSize = () => {
  switch (displayMode.value) {
    case 'artist':
      // 歌手列表：每页4行，移动端每行2个(8个)，大屏每行4个(16个)
      return window.innerWidth >= 768 ? artistPageSizeLarge.value : artistPageSize.value
    case 'playlist':
    case 'album':
      // 歌单/专辑列表：每页3行，移动端每行2个(6个)，大屏每行4个(12个)
      return window.innerWidth >= 1280 ? playlistPageSizeLarge.value : playlistPageSize.value
    default:
      return pageSize.value
  }
}

// 是否有搜索结果
const hasSearchResults = computed(() => {
  return props.songs.length > 0 || props.artists.length > 0 || props.playlists.length > 0 || props.albums.length > 0
})

const displayMode = computed(() => {
  return currentSearchType.value
})

const title = computed(() => {
  const titles = {
    search: '单曲搜索结果',
    artist: '歌手搜索结果',
    playlist: '歌单搜索结果',
    album: '专辑搜索结果'
  }
  return titles[displayMode.value] || '搜索结果'
})

const totalCount = computed(() => {
  return getTabCount(currentSearchType.value)
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
    case 'album':
      return props.albums.slice(start, end)
    case 'artist':
      return props.artists.slice(start, end)
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

// 处理解析事件
const handleTrackParse = (data) => {
  if (data?.track) {
    emit('parse-song', data.track, data.quality)
  }
}

// 处理列表项点击（解析歌手/歌单/专辑）
const handleItemClick = async ({ item, action }) => {
  if (action === 'artist') {
    await handleParseArtist(item)
  } else if (action === 'playlist') {
    await handleParsePlaylist(item)
  } else if (action === 'album') {
    await handleParseAlbum(item)
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
    const response = await fetch('/playlist', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `id=${item.id}`
    })
    
    const result = await response.json()
    
    if (result.success && result.data && result.data.playlist) {
      const playlist = result.data.playlist
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
      message.error(result.message || '解析失败')
      currentDetail.value = null
    }
  } catch (error) {
    message.error('解析失败，请稍后重试')
    currentDetail.value = null
  }
}

// 解析专辑
const handleParseAlbum = async (item) => {
  resetDetailPagination()
  currentDetail.value = { ...item, loading: true, isAlbum: true }

  if (settings.enableCache && cache.value.album[item.id]) {
    const cached = cache.value.album[item.id]
    currentDetail.value = {
      id: cached.id,
      name: cached.name,
      coverImgUrl: cached.coverImgUrl,
      artist: cached.artist,
      creator: cached.artist,
      trackCount: cached.trackCount,
      loading: false,
      isAlbum: true
    }
    detailTracks.value = cached.tracks
    
    notification.success({
      message: '使用缓存数据',
      description: `找到 ${detailTracks.value.length} 首歌曲`,
    })
    return
  }
  
  try {
    const response = await fetch('/album', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `id=${item.id}`
    })
    
    const result = await response.json()
    
    if (result.success && result.data && result.data.album) {
      const album = result.data.album
      currentDetail.value = {
        id: album.id,
        name: album.name,
        coverImgUrl: album.coverImgUrl,
        artist: album.artist,
        creator: album.artist,
        trackCount: album.songs?.length || 0,
        loading: false,
        isAlbum: true
      }
      detailTracks.value = album.songs || []
      
      cache.value.album[item.id] = {
        id: album.id,
        name: album.name,
        coverImgUrl: album.coverImgUrl,
        artist: album.artist,
        trackCount: detailTracks.value.length,
        tracks: detailTracks.value
      }
      saveDetailCache('album', cache.value.album)
      
      if (detailTracks.value.length > 0) {
        notification.success({
          message: '解析成功',
          description: `找到 ${detailTracks.value.length} 首歌曲`,
        })
      }
    } else {
      message.error(result.message || '解析失败')
      currentDetail.value = null
    }
  } catch (error) {
    message.error('解析失败，请稍后重试')
    currentDetail.value = null
  }
}

// 解析歌手
const handleParseArtist = async (item) => {
  resetDetailPagination()

  // 直接使用卡片中的歌手信息，避免API返回错误的歌手信息
  currentDetail.value = {
    id: item.id,
    name: item.name,
    coverImgUrl: item.avatarUrl || item.coverImgUrl,
    artist: item.name,
    creator: item.name,
    trackCount: 0,
    loading: true,
    isArtist: true
  }
  
  if (settings.enableCache && cache.value.artist[item.id]) {
    const cached = cache.value.artist[item.id]
    currentDetail.value = {
      id: cached.id,
      name: cached.name,
      coverImgUrl: cached.avatarUrl || item.coverImgUrl,
      artist: cached.name,
      creator: cached.name,
      trackCount: cached.trackCount,
      loading: false,
      isArtist: true
    }
    detailTracks.value = cached.tracks
    
    notification.success({
      message: '使用缓存数据',
      description: `找到 ${detailTracks.value.length} 首歌曲`,
    })
    return
  }
  
  try {
    const response = await fetch('/artist', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: `id=${item.id}`
    })
    
    const result = await response.json()
    
    if (result.success && result.data) {
      const artistData = result.data.artist || result.data
      
      // 优先使用卡片中的歌手信息，避免API返回错误的歌手（如合唱歌曲的情况）
      currentDetail.value = {
        id: item.id,
        name: item.name,
        coverImgUrl: item.avatarUrl || item.coverImgUrl,
        artist: item.name,
        creator: item.name,
        trackCount: artistData.songs?.length || artistData.musicCount || 0,
        loading: false,
        isArtist: true
      }
      detailTracks.value = artistData.songs || []
      
      cache.value.artist = cache.value.artist || {}
      cache.value.artist[item.id] = {
        id: artistData.id,
        name: artistData.name || item.name,
        avatarUrl: artistData.avatarUrl || artistData.picUrl || '',
        trackCount: detailTracks.value.length,
        tracks: detailTracks.value
      }
      saveDetailCache('artist', cache.value.artist)
      
      if (detailTracks.value.length > 0) {
        notification.success({
          message: '解析成功',
          description: `找到 ${detailTracks.value.length} 首歌曲`,
        })
      }
    } else {
      message.error(result.message || '解析失败')
      currentDetail.value = null
    }
  } catch (error) {
    message.error('解析失败，请稍后重试')
    currentDetail.value = null
  }
}

const handleDataSourceChange = (value) => {
  selectedDataSource.value = value
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
