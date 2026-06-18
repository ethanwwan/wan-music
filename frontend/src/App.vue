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



        <!-- Search Container 组件 -->
        <SearchContainer
          ref="searchContainerRef"
          :title="searchConfig.title"
          :placeholder="searchConfig.placeholder"
          :loading="loading"
          @parse="handleParse"
          @open-settings="showSettingsDialog = true"
        />

        <!-- 搜索结果面板组件 -->
        <SearchResult
          :key="searchResultKey"
          :songs="searchResults"
          :playlists="playlistSearchResults"
          :loading="loading"
          :search-type="currentSearchType"
          :warnings="searchWarnings"
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
        <div class="view-container" v-show="currentView === 'album' && albumInfo">
          <SongList
            type="song"
            :items="albumInfo?.tracks || []"
            :detail-info="{
              ...albumInfo,
              coverImgUrl: albumInfo?.coverImgUrl || albumInfo?.picUrl,
              name: albumInfo?.name,
              creator: albumInfo?.artistName || albumInfo?.artist?.name,
              isAlbum: true
            }"
            :current-page="currentPage"
            :page-size="20"
            :total-tracks="totalTracks"
            :settings="settings"
            @track-selected="handleTrackSelected"
            @track-parsed="handleTrackParsed"
            @track-play="(track) => handlePlaySong(track)"
            @page-change="handlePageChange"
          />
        </div>
      </a-layout-content>

      <!-- 底部组件 -->
      <a-layout-footer>
        <Footer />
      </a-layout-footer>

      <!-- 浮动操作按钮 -->
      <FloatingActions @open-settings="showSettingsDialog = true" />

      <!-- 设置对话框 -->
      <SettingsDialog v-model:open="showSettingsDialog" />

      <!-- 底部播放器 -->
      <MusicPlayer :current-song="currentSong" :autoplay="true" @play-error="handlePlayError" />
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import { message } from 'ant-design-vue'

// 导入组件
import HeroHeader from './components/HeroHeader.vue'

import SearchContainer from './components/SearchContainer.vue'
import SearchResult from './components/SearchResult.vue'
import Footer from './components/Footer.vue'
import FloatingActions from './components/FloatingActions.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import MusicPlayer from './components/MusicPlayer.vue'
import SongList from './components/SongList.vue'

// 导入工具函数
import musicApi from './services/musicApi.js'
import { initThemeFromLocalStorage, DEFAULT_THEME_COLOR } from './utils/themeManager.js'
import { settings, loadSettings } from './utils/settingsManager.js'
import {
    musicUrl, loading, musicInfo, parseMusic, cleanupTimer, searchResults, playlistSearchResults, searchWarnings, playlistInfo
  } from './utils/parseManager.js'
import { displayTracks, currentPage, totalTracks, updateDisplayTracks } from './utils/paginationManager.js'
import { initDeviceDetection, cleanupDeviceDetection } from './utils/deviceDetector.js'


// 响应式数据
const currentView = ref('search')
const showSettingsDialog = ref(false)
const searchResultKey = ref(0)
const searchContainerRef = ref(null)
const currentSearchType = ref('keyword') // 'keyword' | 'music_link' | 'playlist_link'

// 播放列表（保留用于向后兼容）
const playerPlaylist = ref([])

// 当前播放的歌曲
const currentSong = ref(null)

// 搜索配置
const searchConfig = {
  title: '输入搜索关键词',
  description: '支持搜索歌曲、歌单、单曲分享链接或歌单分享链接',
  placeholder: '请输入歌曲名或歌单名'
}

// 主题配置 - 响应式主题token
const themeToken = reactive({
  colorPrimary: DEFAULT_THEME_COLOR,
})

// 判断输入类型 → 返回后端 type 参数
// 0=全部(不再使用) | 1=只搜歌曲 | 2=只搜歌单
const detectSearchType = (url) => {
  // 检查是否是歌曲链接
  if (musicApi.validateMusicUrl(url)) {
    return 1
  }
  // 检查是否是歌单链接
  if (musicApi.validatePlaylistUrl(url)) {
    return 2
  }
  // 关键字搜索：默认只搜歌曲（点击歌单 tab 时再搜歌单）
  return 1
}

// 判断输入类型（前端 UI 用）
const detectInputType = (url) => {
  // 检查是否是歌曲链接
  if (musicApi.validateMusicUrl(url)) {
    return 'music_link'
  }
  // 检查是否是歌单链接
  if (musicApi.validatePlaylistUrl(url)) {
    return 'playlist_link'
  }
  // 默认是keyword搜索
  return 'keyword'
}

// 当前选择的数据源（从localStorage读取）
const currentSources = ref([localStorage.getItem('wan-music-selected-data-source') || 'netease'])

const handleParse = async ({ url, sources = ['netease'] }) => {
  // 重新挂载 SearchResult 组件，重置所有状态
  searchResultKey.value++
  musicUrl.value = url

  // 保存当前选择的数据源
  currentSources.value = sources

  // 检测输入类型
  currentSearchType.value = detectInputType(url)
  const searchType = detectSearchType(url)

  const quality = settings.selectedQuality || 'lossless'
  await parseMusic(quality, 'search', sources, searchType)
  
  if (searchContainerRef.value && url.trim()) {
    searchContainerRef.value.addHistoryRecord(url.trim())
  }
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
  console.log('musicUrl.value at tab switch:', musicUrl.value)
  const quality = settings.selectedQuality || 'lossless'
  // 将 SearchResult 的 tab key 转成后端 type
  // 'search' → 1 (歌曲), 'playlist' → 2 (歌单)
  const backendType = searchType === 'playlist' ? 2 : 1
  await parseMusic(quality, 'search', currentSources.value, backendType)
}

// 处理歌曲播放 - 只播放当前点击的歌曲
// track.url 由 SongList 的 track-play 事件传递（实际值是后端 /song 响应的下载 URL）
// 同时设置 musicInfo.value，让 MusicPlayer 的 v-if 通过（无需第二次 /song URL 模式调用）
const handlePlaySong = async (track) => {
  const song = {
    id: track.id,
    name: track.name,
    artist: track.artist || track.ar?.[0]?.name || (Array.isArray(track.artists) ? track.artists[0]?.name : track.artists) || '未知艺术家',
    album: track.album || track.al?.name || '未知专辑',
    cover: getCoverUrl(track),
    lrc: track.lrc || '',
    url: track.url || '',
    fileExtension: track.fileExtension || '.mp3',
    unavailable: track.unavailable || false
  }
  currentSong.value = song
  musicInfo.value = song
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
  themeToken.colorPrimary = DEFAULT_THEME_COLOR
})

onUnmounted(() => {
  cleanupDeviceDetection()
  cleanupTimer()
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