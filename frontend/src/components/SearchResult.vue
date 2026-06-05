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
        <span class="result-count">共 {{ totalCount }} 个结果</span>
      </div>
    </div>

    <!-- 搜索类型Tab（搜索结果不为空时显示） -->
    <div v-if="hasSearchResults && !currentDetail" class="search-tabs">
      <a-button
        v-for="tab in searchTabs"
        :key="tab.key"
        :class="['search-tab', { active: currentSearchType === tab.key }]"
        @click="handleSearchTabClick(tab.key)"
      >
        {{ tab.label }}
      </a-button>
    </div>

    <!-- loading 状态 -->
    <div v-if="currentDetail && currentDetail.loading" class="loading-view">
      <div class="loading-content">
        <a-spin size="large" tip="正在加载..." />
      </div>
    </div>

    <!-- 歌单/专辑详情页面 - 使用 SearchResultList 组件 -->
    <SearchResultList 
      v-if="currentDetail && !currentDetail.loading && detailTracks.length > 0"
      :playlist-info="currentDetail"
      :display-tracks="detailTracks"
      :current-page="currentDetailPage"
      :page-size="detailPageSize"
      :total-tracks="detailTracks.length"
      :settings="settings"
      :type="currentDetail.isAlbum ? 'album' : 'playlist'"
      @track-parsed="handleParse"
      @track-play="handleTrackPlay"
      @page-change="goToDetailPage"
    />

    <!-- 歌单卡片展示 -->
    <div v-if="displayMode === 'playlist' && !currentDetail" class="playlist-grid">
      <!-- loading 状态 -->
      <div v-if="props.loading" class="loading-container">
        <a-spin size="large" tip="正在搜索..." />
      </div>
      <!-- 搜索结果 -->
      <div 
        v-for="playlist in currentPageData" 
        :key="playlist.id" 
        class="playlist-card"
        @click="handleSelect(playlist)"
      >
        <div class="playlist-cover-wrapper">
          <img 
            :src="playlist.coverImgUrl" 
            :alt="playlist.name" 
            class="playlist-cover"
            loading="lazy"
          />
          <div class="playlist-overlay">
            <span class="track-count">{{ playlist.trackCount }} 首</span>
          </div>
        </div>
        <div class="playlist-info">
          <h4 class="playlist-name">{{ playlist.name }}</h4>
          <p class="playlist-creator">{{ playlist.creator }}</p>
        </div>
        <div class="playlist-action">
          <a-button size="middle" type="primary" @click.stop="handleParse(playlist, 'playlist')">
            解析歌单
          </a-button>
        </div>
      </div>
    </div>

    <!-- 专辑卡片展示 -->
    <div v-if="displayMode === 'album' && !currentDetail" class="album-grid">
      <!-- loading 状态 -->
      <div v-if="props.loading" class="loading-container">
        <a-spin size="large" tip="正在搜索..." />
      </div>
      <!-- 搜索结果 -->
      <div 
        v-for="album in currentPageData" 
        :key="album.id" 
        class="album-card"
        @click="handleSelect(album)"
      >
        <div class="album-cover-wrapper">
          <img 
            :src="album.coverImgUrl" 
            :alt="album.name" 
            class="album-cover"
            loading="lazy"
          />
          <div class="album-overlay">
            <span class="track-count">{{ album.trackCount }} 首</span>
          </div>
        </div>
        <div class="album-info">
          <h4 class="album-name">{{ album.name }}</h4>
          <p class="album-artist">{{ album.artist }}</p>
        </div>
        <div class="album-action">
          <a-button size="middle" type="primary" @click.stop="handleParse(album, 'album')">
            解析专辑
          </a-button>
        </div>
      </div>
    </div>

    <!-- 歌曲列表展示（使用 SearchResultList 组件） -->
    <SearchResultList 
      v-if="displayMode === 'search' && !currentDetail && songs.length > 0"
      :display-tracks="songs"
      :current-page="currentPage"
      :page-size="pageSize"
      :total-tracks="songs.length"
      :settings="settings"
      :type="displayMode"
      @track-parsed="handleTrackParse"
      @track-play="handleTrackPlay"
      @page-change="goToPage"
    />

    <!-- 歌手卡片展示 -->
    <div v-if="displayMode === 'artist' && !currentDetail" class="artist-grid">
      <!-- loading 状态 -->
      <div v-if="props.loading" class="loading-container">
        <a-spin size="large" tip="正在搜索..." />
      </div>
      <!-- 搜索结果 -->
      <div 
        v-for="artist in currentPageData" 
        :key="artist.id" 
        class="artist-card"
      >
        <div class="artist-cover-wrapper">
          <img 
            :src="artist.avatarUrl" 
            :alt="artist.name" 
            class="artist-cover"
            loading="lazy"
          />
        </div>
        <div class="artist-info">
          <h4 class="artist-name">{{ artist.name }}</h4>
          <p class="artist-music-count">{{ artist.musicCount }} 首歌曲</p>
        </div>
        <div class="artist-action">
          <a-button size="middle" type="primary" @click.stop="handleParse(artist, 'artist')">
            解析歌手
          </a-button>
        </div>
      </div>
    </div>

    <!-- 分页组件（歌手、歌单和专辑搜索结果） -->
    <Pagination 
      v-if="(displayMode === 'playlist' || displayMode === 'album' || displayMode === 'artist') && !currentDetail && totalCount > 0"
      :total-count="totalCount"
      :page-size="pageSize"
      v-model="currentPage"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { message, notification } from 'ant-design-vue'
import { batchDownloadMusic, parseMusicInfo } from '../services/musicApi.js'
import { settings } from '../utils/settingsManager.js'
import SearchResultList from './SearchResultList.vue'
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
  }
})

const emit = defineEmits(['parse-song', 'parse-playlist', 'parse-album', 'select', 'track-play', 'search-type-change'])

// 搜索类型Tab配置
const searchTabs = [
  { key: 'search', label: '单曲' },
  { key: 'artist', label: '歌手' },
  { key: 'playlist', label: '歌单' },
  { key: 'album', label: '专辑' }
]

// 当前搜索类型
const currentSearchType = ref('search')

// 二级页面状态
const currentDetail = ref(null)
const detailTracks = ref([])

// 详情页分页配置
const currentDetailPage = ref(1)
const detailPageSize = ref(10)

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

// 分页配置
const currentPage = ref(1)
const pageSize = ref(12)

// 监听模式变化，切换时重置分页和详情状态
watch(() => props.currentMode, () => {
  currentPage.value = 1
  currentDetailPage.value = 1
  currentDetail.value = null
  detailTracks.value = []
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
  return Math.ceil(totalCount.value / pageSize.value)
})

// 当前页的数据
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  
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

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

// 重置分页（搜索结果变化时）
const resetPagination = () => {
  currentPage.value = 1
}

// 详情页分页计算
const detailTotalPages = computed(() => {
  return Math.ceil(detailTracks.value.length / detailPageSize.value)
})

const currentDetailPageData = computed(() => {
  const start = (currentDetailPage.value - 1) * detailPageSize.value
  const end = start + detailPageSize.value
  return detailTracks.value.slice(start, end)
})

const detailVisiblePages = computed(() => {
  const pages = []
  const total = detailTotalPages.value
  const current = currentDetailPage.value
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 3) {
      pages.push(1, 2, 3, 4, '...', total)
    } else if (current >= total - 2) {
      pages.push(1, '...', total - 3, total - 2, total - 1, total)
    } else {
      pages.push(1, '...', current - 1, current, current + 1, '...', total)
    }
  }
  
  return pages
})

const goToDetailPage = (page) => {
  if (page >= 1 && page <= detailTotalPages.value) {
    currentDetailPage.value = page
  }
}

const prevDetailPage = () => {
  if (currentDetailPage.value > 1) {
    currentDetailPage.value--
  }
}

const nextDetailPage = () => {
  if (currentDetailPage.value < detailTotalPages.value) {
    currentDetailPage.value++
  }
}

const resetDetailPagination = () => {
  currentDetailPage.value = 1
}

// 可见的分页页码（最多显示7个页码）
const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value
  
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 3) {
      pages.push(1, 2, 3, 4, '...', total)
    } else if (current >= total - 2) {
      pages.push(1, '...', total - 3, total - 2, total - 1, total)
    } else {
      pages.push(1, '...', current - 1, current, current + 1, '...', total)
    }
  }
  
  return pages
})

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

// 处理解析事件
const handleTrackParse = (data) => {
  if (data?.track) {
    emit('parse-song', data.track, data.quality)
  }
}

// 处理播放列表数据
const handlePlaylistData = (playlistData) => {
  emit('playlist-data', playlistData)
}

const handleParse = async (item, type) => {
  if (type === 'song') {
    emit('parse-song', item)
  } else if (type === 'playlist') {
    resetDetailPagination()
    currentDetail.value = { ...item, loading: true }
    
    if (cache.value.playlist[item.id]) {
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
  } else if (type === 'album') {
    resetDetailPagination()
    currentDetail.value = { ...item, loading: true }
    
    if (cache.value.album[item.id]) {
      const cached = cache.value.album[item.id]
      currentDetail.value = {
        id: cached.id,
        name: cached.name,
        coverImgUrl: cached.coverImgUrl,
        artist: cached.artist,
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
          trackCount: album.songs?.length || 0,
          loading: false
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
  } else if (type === 'artist') {
    resetDetailPagination()
    currentDetail.value = { ...item, loading: true }
    
    if (cache.value.artist[item.id]) {
      const cached = cache.value.artist[item.id]
      currentDetail.value = {
        id: cached.id,
        name: cached.name,
        coverImgUrl: cached.avatarUrl,
        artist: cached.name,
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
      const response = await fetch('/artist', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `id=${item.id}`
      })
      
      const result = await response.json()
      
      if (result.success && result.data) {
        const artist = result.data.artist || result.data
        currentDetail.value = {
          id: artist.id,
          name: artist.name,
          coverImgUrl: artist.avatarUrl,
          artist: artist.name,
          trackCount: artist.songs?.length || artist.musicCount || 0,
          loading: false
        }
        detailTracks.value = artist.songs || []
        
        cache.value.artist = cache.value.artist || {}
        cache.value.artist[item.id] = {
          id: artist.id,
          name: artist.name,
          avatarUrl: artist.avatarUrl,
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
}

const goBack = () => {
  currentDetail.value = null
  detailTracks.value = []
}

// 批量下载
const handleBatchDownload = async () => {
  if (!detailTracks.value || detailTracks.value.length === 0) {
    message.warning('没有可下载的歌曲')
    return
  }

  try {
    downloadProgress.value = {
      isDownloading: true,
      percentage: 0,
      status: '',
      currentSong: '',
      total: detailTracks.value.length,
      completed: 0,
      failed: 0
    }

    message.info(`开始批量下载 ${detailTracks.value.length} 首歌曲...`)

    const musicList = []
    for (const track of detailTracks.value) {
      try {
        const songUrl = `https://music.163.com/song?id=${track.id}`
        
        const musicInfo = await parseMusicInfo(songUrl, 'lossless')
        if (musicInfo && musicInfo.url) {
          musicList.push({
            id: track.id,
            name: track.name,
            artist: getArtist(track),
            album: getAlbum(track),
            url: musicInfo.url,
            cover: getTrackCover(track),
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

    const result = await batchDownloadMusic(
      musicList,
      currentDetail.value?.name || '',
      {
        filenameFormat: settings.filenameFormat || 'artist-song',
        writeMetadata: settings.writeMetadata !== false
      },
      (progress) => {
        downloadProgress.value.percentage = progress.percentage
        downloadProgress.value.currentSong = progress.current
        downloadProgress.value.completed = progress.completed
        downloadProgress.value.failed = progress.failed
      }
    )

    downloadProgress.value.isDownloading = false
    downloadProgress.value.status = result.failed === 0 ? 'success' : 'warning'

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

const getTrackCover = (track) => {
  return (
    track.picUrl ||
    track.cover ||
    track.al?.picUrl ||
    track.album?.picUrl ||
    currentDetail.value?.coverImgUrl ||
    ''
  )
}

const getArtist = (track) => {
  return (
    track.artist ||
    track.singer ||
    (typeof track.artists === 'string' ? track.artists : null) ||
    (Array.isArray(track.artists) && track.artists[0]?.name) ||
    (Array.isArray(track.ar) && track.ar[0]?.name) ||
    ''
  )
}

const getAlbum = (track) => {
  return (
    track.album ||
    track.al?.name ||
    ''
  )
}
</script>

<style scoped>
.search-result-panel {
  margin-top: 2rem;
  background: var(--color-surface-white);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

/* loading 状态 */
.loading-view {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  padding: 2rem;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-text {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 0;
  white-space: nowrap;
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

/* loading 容器 */
.loading-container {
  grid-column: 1 / -1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
}

/* 歌单卡片网格 */
.playlist-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.5rem;
  padding: 1.5rem;
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
  padding: 2px 8px;
  border-radius: 10px;
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
}

.playlist-action {
  padding: 0 1rem 1rem;
}

.playlist-action :deep(.ant-btn) {
  width: 100%;
}

/* 专辑卡片网格 */
.album-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1.5rem;
  padding: 1.5rem;
}

@media (min-width: 640px) {
  .album-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .album-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1280px) {
  .album-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.album-card {
  background: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
}

.album-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.album-cover-wrapper {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
}

.album-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.album-card:hover .album-cover {
  transform: scale(1.05);
}

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

.album-info {
  padding: 1rem;
}

.album-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-on-surface);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.album-artist {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
}

.album-action {
  padding: 0 1rem 1rem;
}

.album-action :deep(.ant-btn) {
  width: 100%;
}

/* 歌曲列表 */
.song-list-container {
  overflow: hidden;
}

.song-table-wrapper {
  overflow-x: auto;
}

.song-table {
  width: 100%;
  border-collapse: collapse;
}

.song-table th {
  text-align: left;
  padding: 14px 16px;
  font-size: 14px;
  color: var(--color-text-muted);
  font-weight: 600;
  background: var(--color-surface-container-low);
  white-space: nowrap;
  border-radius: 0;
}

.song-table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.col-index {
  width: 60px;
  color: var(--color-text-muted);
  font-size: 14px;
  text-align: center;
}

.col-cover {
  width: 50px;
  padding: 8px 16px;
}

.song-cover {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  object-fit: cover;
}

.col-song {
  min-width: 200px;
}

.song-info {
  display: flex;
  flex-direction: column;
}

.song-name {
  font-size: 14px;
  color: var(--color-on-surface);
  font-weight: 500;
}

.col-artist,
.col-album {
  font-size: 14px;
  color: var(--color-text-muted);
  min-width: 120px;
}

.song-table td.col-action {
  width: 100px;
  border-bottom: none !important;
}

.song-row:hover {
  background: var(--color-surface-container-low);
}

/* 详情页面样式 */
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

.meta-separator {
  color: var(--color-outline);
}

.detail-actions {
  flex-shrink: 0;
  display: flex;
  gap: 0.5rem;
}

.detail-action-btn {
  min-width: 100px;
}

/* 歌手卡片网格 */
.artist-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  padding: 1.5rem;
}

@media (min-width: 640px) {
  .artist-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (min-width: 1024px) {
  .artist-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

@media (min-width: 1280px) {
  .artist-grid {
    grid-template-columns: repeat(8, 1fr);
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

/* 搜索Tab */
.search-tabs {
  display: flex;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border-subtle);
  margin-bottom: 0;
}

.search-tab {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 1rem;
  font-size: 14px;
  color: var(--color-text-muted);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.search-tab:hover {
  background: var(--color-surface-container-low);
  color: var(--color-on-surface);
}

.search-tab.active {
  background: var(--color-primary);
  color: #fff;
}

/* 下载进度弹窗 */
.download-modal-content {
  padding: 1.5rem;
}

.download-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.download-progress-title {
  font-size: 16px;
  font-weight: 600;
}

.download-progress-info {
  font-size: 14px;
  color: var(--color-text-muted);
  margin-bottom: 0.5rem;
}

.download-progress-bar {
  margin-bottom: 1rem;
}

.download-progress-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>