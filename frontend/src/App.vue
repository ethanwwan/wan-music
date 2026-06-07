<template>
  <a-config-provider :theme="{ token: themeToken }">
    <a-layout class="app-container" style="min-height: 100vh;">
      <!-- 主要内容区域 -->
      <a-layout-content class="app-main">
        <!-- Hero Header 组件 -->
        <HeroHeader 
          title="网易云音乐解析工具"
          subtitle="实时解析网易云音乐单曲、获取真实下载地址及封面信息。"
        />

        <!-- System Notice 组件 -->
        <SystemNotice 
          v-model:visible="showNotice"
          title="系统公告"
          message="欢迎使用网易云音乐解析工具！如需反馈问题，请添加QQ群：1036593883"
          @close="handleNoticeClose"
        />

        <!-- Search Container 组件 -->
        <SearchContainer
          ref="searchContainerRef"
          :title="searchConfig.title"
          :description="searchConfig.description"
          :placeholder="searchConfig.placeholder"
          :example-links="exampleLinks"
          :example-title="exampleTitle"
          :loading="loading"
          @parse="handleParse"
          @example-click="handleExampleClick"
        />

        <!-- 搜索结果面板组件 -->
        <SearchResult 
          :key="searchResultKey"
          :songs="searchResults"
          :playlists="playlistSearchResults"
          :albums="albumSearchResults"
          :artists="artistSearchResults"
          :loading="loading"
          @parse-song="handleParseSong"
          @parse-playlist="handleParsePlaylist"
          @parse-album="handleParseAlbum"
          @track-play="handlePlaySong"
          @search-type-change="handleSearchTypeChange"
        />

        <!-- 单曲解析视图 -->
        <div class="view-container" v-show="currentView === 'music'">
          <!-- 音乐播放器组件 -->
          <MusicPlayer
            v-if="musicInfo"
            :playlist="[musicInfo]"
            :current-index="0"
          />
        </div>

        <!-- 歌单解析视图 -->
        <div class="view-container" v-show="currentView === 'playlist' && playlistInfo && displayTracks.length > 0">
          <SongList
            :playlist-info="playlistInfo"
            :display-tracks="playlistInfo?.tracks || displayTracks"
            :current-page="currentPage"
            :page-size="20"
            :total-tracks="totalTracks"
            :settings="settings"
            @track-selected="handleTrackSelected"
            @track-parsed="handleTrackParsed"
            @track-play="(track) => handlePlaySong(track, playlistInfo?.tracks || displayTracks)"
            @page-change="handlePageChange"
          />
        </div>

        <!-- 专辑解析视图 -->
        <div class="view-container" v-show="currentView === 'album'">
          <!-- 专辑详情组件 -->
        </div>
      </a-layout-content>

      <!-- 底部组件 -->
      <a-layout-footer>
        <Footer />
      </a-layout-footer>

      <!-- 浮动操作按钮 -->
      <FloatingActions @open-settings="showSettingsDialog = true" />

      <!-- 设置对话框 -->
      <SettingsDialog v-model:open="showSettingsDialog" @theme-color-change="handleThemeColorChange" />

      <!-- 底部播放器 -->
      <MusicPlayer :playlist="playerPlaylist" :autoplay="true" v-model:current-index="currentPlayIndex" @play-error="handlePlayError" />
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'

// 导入组件
import HeroHeader from './components/HeroHeader.vue'
import SystemNotice from './components/SystemNotice.vue'
import SearchContainer from './components/SearchContainer.vue'
import SearchResult from './components/SearchResult.vue'
import Footer from './components/Footer.vue'
import FloatingActions from './components/FloatingActions.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import MusicPlayer from './components/MusicPlayer.vue'
import SongList from './components/SongList.vue'

// 导入工具函数
import musicApi from './services/musicApi.js'
import { isDark, toggleTheme, initThemeFromLocalStorage, applyTheme } from './utils/themeManager.js'
import { settings, loadSettings, saveSettings } from './utils/settingsManager.js'
import {
    musicUrl, loading, musicInfo, playlistUrl, playlistLoading, playlistInfo, albumUrl, albumLoading, albumInfo, elapsedTime, parseMusic, parsePlaylist, parseAlbum, clearMusicResult, clearPlaylistResult, clearAlbumResult, setExampleUrl, cleanupTimer, searchResults, playlistSearchResults, albumSearchResults, artistSearchResults,
    currentParsingTrack, parsingProgress
  } from './utils/parseManager.js'
import { displayTracks, currentPage, totalTracks, updateDisplayTracks } from './utils/paginationManager.js'
import { isMobile, initDeviceDetection, cleanupDeviceDetection } from './utils/deviceDetector.js'
import { getExampleLinks, getExampleTitle } from './utils/exampleData.js'

// 响应式数据
const currentView = ref('search')
const showNotice = ref(true)
const showSettingsDialog = ref(false)
const searchResultKey = ref(0)
const searchContainerRef = ref(null)

// 播放列表
const playerPlaylist = ref([])

// 搜索配置
const searchConfig = {
  title: '输入搜索关键词',
  description: '支持搜索歌曲、歌手、歌单、专辑',
  placeholder: '请输入歌曲名、歌手名、专辑名或歌单名'
}

// 示例链接
const exampleLinks = getExampleLinks('search')
const exampleTitle = getExampleTitle('search')

// 主题配置 - 响应式主题token
const themeToken = reactive({
  colorPrimary: '#0057c2',
})

// 从localStorage读取保存的主题色
const getSavedThemeColor = () => {
  const saved = localStorage.getItem('themeColor')
  const themeColors = [
    { name: '默认蓝', value: 'blue', hex: '#0057c2' },
    { name: '活力红', value: 'red', hex: '#e53935' },
    { name: '优雅紫', value: 'purple', hex: '#722ed1' },
    { name: '清新绿', value: 'green', hex: '#13c2c2' },
    { name: '温暖橙', value: 'orange', hex: '#fa8c16' },
    { name: '浪漫粉', value: 'pink', hex: '#eb2f96' },
  ]
  if (saved) {
    const color = themeColors.find(c => c.value === saved)
    return color ? color.hex : '#0057c2'
  }
  return '#0057c2'
}

// 监听主题色变化
const handleStorageChange = (e) => {
  if (e.key === 'themeColor') {
    themeToken.colorPrimary = getSavedThemeColor()
  }
}

// 处理主题色变化（从设置对话框）
const handleThemeColorChange = (color) => {
  themeToken.colorPrimary = color
  applyTheme()
}

const handleNoticeClose = () => {
  console.log('Notice closed')
}

const handleParse = async ({ url }) => {
  // 重新挂载 SearchResult 组件，重置所有状态
  searchResultKey.value++
  musicUrl.value = url
  const quality = settings.selectedQuality || 'lossless'
  await parseMusic(quality, 'search')
  
  if (searchContainerRef.value && url.trim()) {
    searchContainerRef.value.addHistoryRecord(url.trim())
  }
}

const handleExampleClick = () => {
  // 示例tag点击只填充输入框，不自动解析
}

const handlePageChange = (page) => {
  console.log('App.vue handlePageChange called with page:', page)
  console.log('Before: currentPage =', currentPage.value, ', displayTracks.length =', displayTracks.value.length)
  currentPage.value = page
  updateDisplayTracks()
  console.log('After: currentPage =', currentPage.value, ', displayTracks.length =', displayTracks.value.length)
  console.log('Display tracks updated:', displayTracks.value.slice(0, 3))
}

const handleSearchTypeChange = async (searchType) => {
  console.log('Search type changed to:', searchType)
  console.log('musicUrl.value at artist tab switch:', musicUrl.value)
  const quality = settings.selectedQuality || 'lossless'
  await parseMusic(quality, searchType)
}

const handleParseSong = (song) => {
  musicUrl.value = `https://music.163.com/song?id=${song.id}`
  const quality = settings.selectedQuality || 'lossless'
  parseMusic(quality, 'music')
}

// 当前播放索引
const currentPlayIndex = ref(0)

// 保存当前播放列表的完整数据（用于点击播放时）
const currentFullPlaylist = ref([])

// 处理歌曲播放
const handlePlaySong = async (track, playlistData = null) => {
  console.log('Original track data:', track)
  
  let tracks = []
  
  if (playlistData && playlistData.length > 0) {
    tracks = playlistData
    console.log('Using provided playlist data:', playlistData.length, 'tracks')
  }
  else if (playlistInfo.value?.tracks?.length > 0) {
    tracks = playlistInfo.value.tracks
  }
  else if (displayTracks.value.length > 0) {
    tracks = displayTracks.value
  }
  else {
    tracks = [track]
  }
  
  const newPlaylist = tracks.map(t => ({
    id: t.id,
    name: t.name,
    artist: t.artist || t.ar?.[0]?.name || (Array.isArray(t.artists) ? t.artists[0]?.name : t.artists) || '未知艺术家',
    album: t.album || t.al?.name || '未知专辑',
    cover: getCoverUrl(t),
    lrc: t.lrc || '',
    url: t.url || '',
    unavailable: t.unavailable || false
  }))
  
  console.log('Converted playlist (first 3):', newPlaylist.slice(0, 3))
  
  const index = newPlaylist.findIndex(p => p.id === track.id)
  if (index >= 0) {
    if (track.url) {
      newPlaylist[index].url = track.url
    }
    if (track.lrc) {
      newPlaylist[index].lrc = track.lrc
    }
    currentPlayIndex.value = index
  } else {
    newPlaylist.unshift({
      id: track.id,
      name: track.name,
      artist: track.artist || track.ar?.[0]?.name || (Array.isArray(track.artists) ? track.artists[0]?.name : track.artists) || '未知艺术家',
      album: track.album || t.al?.name || '未知专辑',
      cover: getCoverUrl(track),
      lrc: track.lrc || '',
      url: track.url || '',
      unavailable: track.unavailable || false
    })
    currentPlayIndex.value = 0
  }
  
  playerPlaylist.value = [...newPlaylist]
}

// 获取封面URL
const getCoverUrl = (track) => {
  return (
    track.cover || 
    track.picUrl ||
    track.al?.picUrl || 
    track.album?.coverImgUrl ||
    track.album?.picUrl ||
    ''
  )
}

const handleParsePlaylist = (playlist) => {
  currentView.value = 'playlist'
  playlistUrl.value = `https://music.163.com/playlist?id=${playlist.id}`
  parsePlaylist()
}

const handleParseAlbum = (album) => {
  currentView.value = 'album'
  albumUrl.value = `https://music.163.com/album?id=${album.id}`
  parseAlbum()
}

const handleTrackParsed = async (data) => {
  console.log('Track parsed:', data)
  if (searchContainerRef.value && data) {
    const name = data.name || data.track?.name
    if (name) {
      searchContainerRef.value.addHistoryRecord(name)
    }
  }
}

const handleTrackSelected = (track) => {
  console.log('Track selected:', track)
}

// 处理歌曲播放失败（无版权）
const handlePlayError = (track) => {
  // 标记歌曲为不可用
  track.unavailable = true
  
  // 吐司提示
  message.warning(`《${track.name}》因版权问题暂时无法播放`)
  
  // 更新播放列表中的歌曲状态
  const index = playerPlaylist.value.findIndex(p => p.id === track.id)
  if (index !== -1) {
    playerPlaylist.value[index].unavailable = true
  }
}

// 生命周期
onMounted(() => {
  loadSettings()
  initDeviceDetection()
  initThemeFromLocalStorage()
  
  // 初始化主题色
  themeToken.colorPrimary = getSavedThemeColor()
  
  // 添加localStorage变化监听
  window.addEventListener('storage', handleStorageChange)
})

onUnmounted(() => {
  cleanupDeviceDetection()
  cleanupTimer()
  
  // 移除localStorage变化监听
  window.removeEventListener('storage', handleStorageChange)
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: var(--color-background);
}

.app-main {
  max-width: var(--max-width);
  width: 100%;
  margin: 0 auto;
  padding: var(--spacing-3xl) var(--padding-mobile);
  box-sizing: border-box;
}

@media (min-width: 768px) {
  .app-main {
    padding: var(--spacing-3xl);
  }
}

.view-container {
  margin-top: var(--spacing-2xl);
}

.custom-drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-on-surface);
}

.custom-drawer-title .anticon {
  font-size: 18px;
}

.custom-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-on-surface);
}

.close-icon {
  font-size: 20px;
  color: var(--color-on-surface-variant);
  cursor: pointer;
  transition: color 0.2s;
}

.close-icon:hover {
  color: var(--color-on-surface);
}
</style>