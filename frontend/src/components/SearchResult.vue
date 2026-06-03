<template>
  <div v-if="hasResults || currentDetail" class="search-result-panel">
    <!-- 返回按钮（二级页面时显示） -->
    <div v-if="currentDetail" class="back-bar">
      <el-button 
        link
        @click="goBack"
        class="back-button"
      >
        ← 返回搜索结果
      </el-button>
    </div>

    <!-- 结果头部 -->
    <div v-if="!currentDetail" class="result-header">
      <div class="header-left">
        <h3 class="result-title">{{ title }}</h3>
        <span class="result-count">共 {{ totalCount }} 个结果</span>
      </div>
    </div>

    <!-- loading 状态 -->
    <div v-if="currentDetail && currentDetail.loading" class="loading-view">
      <div class="loading-spinner">
        <svg class="spinner" viewBox="0 0 50 50">
          <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="4"></circle>
        </svg>
        <p class="loading-text">正在加载...</p>
      </div>
    </div>

    <!-- 歌单详情页面（二级页面）- 使用 SearchResultList 组件 -->
    <SearchResultList 
      v-if="currentDetail && !currentDetail.loading && detailTracks.length > 0"
      :playlist-info="currentDetail"
      :display-tracks="currentDetailPageData"
      :current-page="currentDetailPage"
      :page-size="detailPageSize"
      :total-tracks="detailTracks.length"
      :settings="settings"
      :is-detail-page="true"
      @track-parsed="handleParse"
      @track-play="handleTrackPlay"
    />

    <!-- 歌单卡片展示 -->
    <div v-if="displayMode === 'playlist' && !currentDetail" class="playlist-grid">
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
          <el-button size="small" type="primary" @click.stop="handleParse(playlist, 'playlist')">
            解析歌单
          </el-button>
        </div>
      </div>
    </div>

    <!-- 专辑卡片展示 -->
    <div v-if="displayMode === 'album' && !currentDetail" class="album-grid">
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
          <el-button size="small" type="primary" @click.stop="handleParse(album, 'album')">
            解析专辑
          </el-button>
        </div>
      </div>
    </div>

    <!-- 分页组件（歌单和专辑搜索结果） -->
    <Pagination 
      v-if="(displayMode === 'playlist' || displayMode === 'album') && !currentDetail && totalCount > 0"
      :total-count="totalCount"
      :page-size="pageSize"
      v-model="currentPage"
    />

    <!-- 歌曲列表展示 -->
    <div v-if="displayMode === 'search' && !currentDetail" class="song-list-container">
      <div class="song-table-wrapper">
        <table class="song-table">
          <thead>
            <tr>
              <th class="col-index">序号</th>
              <th class="col-cover"></th>
              <th class="col-song">歌曲</th>
              <th class="col-artist">歌手</th>
              <th class="col-album">专辑</th>
              <th class="col-action">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(song, index) in songs" :key="song.id" class="song-row">
              <td class="col-index">{{ index + 1 }}</td>
              <td class="col-cover">
                <img 
                  v-if="song.picUrl" 
                  :src="song.picUrl" 
                  :alt="song.name" 
                  class="song-cover"
                  loading="lazy"
                />
              </td>
              <td class="col-song">
                <div class="song-info">
                  <span class="song-name">{{ song.name }}</span>
                </div>
              </td>
              <td class="col-artist">{{ song.artists }}</td>
              <td class="col-album">{{ song.album }}</td>
              <td class="col-action">
                <el-button size="small" @click="handleParse(song, 'song')">解析单曲</el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElButton, ElMessage, ElNotification, ElProgress } from 'element-plus'
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
  currentMode: {
    type: String,
    default: 'search'
  }
})

const emit = defineEmits(['parse-song', 'parse-playlist', 'parse-album', 'select', 'track-play'])

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
  return {
    playlist: storedPlaylist ? JSON.parse(storedPlaylist) : {},
    album: storedAlbum ? JSON.parse(storedAlbum) : {}
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
const pageSize = ref(12) // 4列 * 3行 = 12个卡片

// 监听模式变化，切换时重置分页和详情状态
watch(() => props.currentMode, () => {
  // 重置分页
  currentPage.value = 1
  currentDetailPage.value = 1
  
  // 清除详情页状态
  currentDetail.value = null
  detailTracks.value = []
})

const displayMode = computed(() => {
  // 严格根据当前模式显示对应类型的结果
  // 每个模式只显示自己的数据，不回退到其他模式
  if (props.currentMode === 'playlist') return 'playlist'
  if (props.currentMode === 'album') return 'album'
  if (props.currentMode === 'search' || props.currentMode === 'music' || props.currentMode === 'rank') return 'search'
  return null
})

const title = computed(() => {
  const titles = {
    search: '歌曲搜索结果',
    playlist: '歌单搜索结果',
    album: '专辑搜索结果'
  }
  return titles[displayMode.value] || '搜索结果'
})

const totalCount = computed(() => {
  // 只计算当前模式对应的数据数量
  if (props.currentMode === 'playlist') return props.playlists.length
  if (props.currentMode === 'album') return props.albums.length
  if (props.currentMode === 'search' || props.currentMode === 'music') return props.songs.length
  return 0
})

// 分页计算
const totalPages = computed(() => {
  return Math.ceil(totalCount.value / pageSize.value)
})

// 当前页的数据
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  
  // 只返回当前模式对应的数据
  if (props.currentMode === 'playlist') {
    return props.playlists.slice(start, end)
  }
  if (props.currentMode === 'album') {
    return props.albums.slice(start, end)
  }
  return []
})

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
  
  // 总页数 <= 7，显示所有页码
  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    // 总页数 > 7，显示当前页附近的页码
    if (current <= 3) {
      // 前面部分
      pages.push(1, 2, 3, 4, '...', total)
    } else if (current >= total - 2) {
      // 后面部分
      pages.push(1, '...', total - 3, total - 2, total - 1, total)
    } else {
      // 中间部分
      pages.push(1, '...', current - 1, current, current + 1, '...', total)
    }
  }
  
  return pages
})

const hasResults = computed(() => {
  if (currentDetail.value) return true
  
  switch (props.currentMode) {
    case 'search':
    case 'music':
      return props.songs.length > 0
    case 'playlist':
      return props.playlists.length > 0
    case 'album':
      return props.albums.length > 0
    default:
      return totalCount.value > 0
  }
})

const handleSelect = (item) => {
  emit('select', item)
}

// 处理播放事件
const handleTrackPlay = (track) => {
  emit('track-play', track)
}

const handleParse = async (item, type) => {
  if (type === 'song') {
    emit('parse-song', item)
  } else if (type === 'playlist') {
    // 重置详情页分页
    resetDetailPagination()
    // 显示加载状态
    currentDetail.value = { ...item, loading: true }
    
    // 检查缓存
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
      
      ElNotification({
        title: '使用缓存数据',
        message: `找到 ${detailTracks.value.length} 首歌曲`,
        type: 'success'
      })
      return
    }
    
    try {
      // 调用解析歌单接口
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
        
        // 缓存数据
        cache.value.playlist[item.id] = {
          id: playlist.id,
          name: playlist.name,
          coverImgUrl: playlist.coverImgUrl,
          creator: playlist.creator,
          trackCount: playlist.trackCount,
          tracks: detailTracks.value
        }
        // 持久化到 localStorage
        saveDetailCache('playlist', cache.value.playlist)
        
        if (detailTracks.value.length > 0) {
          ElNotification({
            title: '解析成功',
            message: `找到 ${detailTracks.value.length} 首歌曲`,
            type: 'success'
          })
        }
      } else {
        ElMessage.error(result.message || '解析失败')
        currentDetail.value = null
      }
    } catch (error) {
      ElMessage.error('解析失败，请稍后重试')
      currentDetail.value = null
    }
  } else if (type === 'album') {
    // 重置详情页分页
    resetDetailPagination()
    // 显示加载状态
    currentDetail.value = { ...item, loading: true }
    
    // 检查缓存
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
      
      ElNotification({
        title: '使用缓存数据',
        message: `找到 ${detailTracks.value.length} 首歌曲`,
        type: 'success'
      })
      return
    }
    
    try {
      // 调用解析专辑接口
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
        
        // 缓存数据
        cache.value.album[item.id] = {
          id: album.id,
          name: album.name,
          coverImgUrl: album.coverImgUrl,
          artist: album.artist,
          trackCount: detailTracks.value.length,
          tracks: detailTracks.value
        }
        // 持久化到 localStorage
        saveDetailCache('album', cache.value.album)
        
        if (detailTracks.value.length > 0) {
          ElNotification({
            title: '解析成功',
            message: `找到 ${detailTracks.value.length} 首歌曲`,
            type: 'success'
          })
        }
      } else {
        ElMessage.error(result.message || '解析失败')
        currentDetail.value = null
      }
    } catch (error) {
      ElMessage.error('解析失败，请稍后重试')
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
    ElMessage.warning('没有可下载的歌曲')
    return
  }

  try {
    // 重置进度状态
    downloadProgress.value = {
      isDownloading: true,
      percentage: 0,
      status: '',
      currentSong: '',
      total: detailTracks.value.length,
      completed: 0,
      failed: 0
    }

    ElMessage.info(`开始批量下载 ${detailTracks.value.length} 首歌曲...`)

    // 准备音乐列表，需要先解析每首歌的信息
    const musicList = []
    for (const track of detailTracks.value) {
      try {
        // 将歌曲ID转换为URL格式
        const songUrl = `https://music.163.com/song?id=${track.id}`
        
        // 解析歌曲信息
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

    // 执行批量下载
    const result = await batchDownloadMusic(
      musicList,
      currentDetail.value?.name || '', // 传递歌单/专辑名称作为 ZIP 文件名
      {
        filenameFormat: settings.filenameFormat || 'artist-song',
        writeMetadata: settings.writeMetadata !== false // 默认开启，除非明确设置为 false
      },
      (progress) => {
        downloadProgress.value.percentage = progress.percentage
        downloadProgress.value.currentSong = progress.current
        downloadProgress.value.completed = progress.completed
        downloadProgress.value.failed = progress.failed
      }
    )

    // 下载完成
    downloadProgress.value.isDownloading = false
    downloadProgress.value.status = result.failed === 0 ? 'success' : 'warning'

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

.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.spinner {
  width: 40px;
  height: 40px;
  animation: rotate 1s linear infinite;
}

.spinner .path {
  stroke: var(--color-primary);
  stroke-linecap: round;
  animation: dash 1.5s ease-in-out infinite;
}

@keyframes rotate {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 150;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -35;
  }
  100% {
    stroke-dasharray: 90, 150;
    stroke-dashoffset: -124;
  }
}

.loading-text {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 0;
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

.playlist-action :deep(.el-button) {
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

.album-action :deep(.el-button) {
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
  margin-top: 0.5rem;
  font-size: 13px;
}

.current-song {
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.progress-text {
  color: var(--color-primary);
  font-weight: 600;
  margin-left: 1rem;
  flex-shrink: 0;
}

/* 详情页面歌曲表格 */
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

.track-cover {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  object-fit: cover;
}

.track-row:hover {
  background: var(--color-surface-container-low);
}

/* 详情页分页组件样式 */
.detail-pagination-container {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 1.5rem;
  padding: 1.5rem;
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-surface-container-low);
}

@media (max-width: 768px) {
  .result-header {
    padding: 1rem;
  }
  
  .result-title {
    font-size: 16px;
  }
  
  .detail-header {
    padding: 1rem;
  }
  
  .detail-name {
    font-size: 20px;
  }
  
  .detail-cover {
    width: 60px;
    height: 60px;
  }
  
  .song-table th,
  .song-table td,
  .tracks-table th,
  .tracks-table td {
    padding: 10px 12px;
    font-size: 13px;
  }
  
  .col-album {
    display: none;
  }
  
  .col-action {
    width: 80px;
  }
}

</style>