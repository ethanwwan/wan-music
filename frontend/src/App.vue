<template>
  <el-config-provider size="default">
    <el-container class="app-container" direction="vertical">
      <!-- 主要内容区域 -->
      <el-main class="app-main">
        <!-- Hero Header 组件 -->
        <HeroHeader 
          title="网易云音乐解析工具"
          subtitle="实时解析网易云音乐单曲、获取真实下载地址及封面信息。"
        />

        <!-- System Notice 组件 -->
        <SystemNotice 
          v-model="showNotice"
          title="系统公告"
          message="欢迎使用网易云音乐解析工具！如需反馈问题，请添加QQ群：1036593883"
          @close="handleNoticeClose"
        />

        <!-- Nav Tabs 组件 -->
        <NavTabs 
          v-model="currentView"
          :modes="modes"
          @change="handleViewChange"
        />

        <!-- Search Container 组件 -->
        <SearchContainer
          ref="searchContainerRef"
          :current-mode="currentView"
          :title="getCurrentMode().title"
          :description="getCurrentMode().desc"
          :placeholder="getCurrentMode().placeholder"
          :example-links="exampleLinks"
          :example-title="getCurrentExampleTitle()"
          :loading="loading"
          @parse="handleParse"
          @example-click="handleExampleClick"
          @chart-change="handleChartChange"
        />

        <!-- 搜索结果面板组件 -->
        <SearchResult 
          :songs="searchResults"
          :playlists="playlistSearchResults"
          :albums="albumSearchResults"
          :current-mode="currentView"
          @parse-song="handleParseSong"
          @parse-playlist="handleParsePlaylist"
          @parse-album="handleParseAlbum"
          @track-play="handlePlaySong"
        />

        <!-- 原有的其他内容保持不变 -->
        <!-- 单曲解析视图 -->
        <div class="view-container" v-show="currentView === 'music'">
          <!-- 音乐播放器组件 -->
          <MusicPlayer
            v-if="musicInfo"
            :music-info="musicInfo"
            :music-url="musicInfo.url"
            @track-parsed="handleTrackParsed"
          />
        </div>

        <!-- 歌单解析视图 -->
        <div class="view-container" v-show="currentView === 'playlist' && playlistInfo && displayTracks.length > 0">
          <SearchResultList
            :playlist-info="playlistInfo"
            :display-tracks="displayTracks"
            :current-page="currentPage"
            :page-size="20"
            :total-tracks="totalTracks"
            :settings="settings"
            @track-selected="handleTrackSelected"
            @track-parsed="handleTrackParsed"
            @track-play="handlePlaySong"
            @page-change="handlePageChange"
          />
        </div>

        <!-- 专辑解析视图 -->
        <div class="view-container" v-show="currentView === 'album'">
          <!-- 专辑详情组件 -->
        </div>
      </el-main>

      <!-- 底部组件 -->
      <Footer />

      <!-- 浮动操作按钮 -->
      <FloatingActions @open-settings="showSettingsDialog = true" />

      <!-- 设置对话框 -->
      <SettingsDialog v-model="showSettingsDialog" />

      <!-- 底部播放器 -->
      <BottomPlayer :playlist="playerPlaylist" :autoplay="true" :current-index="currentPlayIndex" />
    </el-container>
  </el-config-provider>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Moon, Sunny, Setting } from '@element-plus/icons-vue'

// 导入新创建的组件
import HeroHeader from './components/HeroHeader.vue'
import SystemNotice from './components/SystemNotice.vue'
import NavTabs from './components/NavTabs.vue'
import SearchContainer from './components/SearchContainer.vue'
import SearchResult from './components/SearchResult.vue'
import Footer from './components/Footer.vue'
import FloatingActions from './components/FloatingActions.vue'
import SettingsDialog from './components/SettingsDialog.vue'

// 导入原有组件
import MusicPlayer from './components/MusicPlayer.vue'
import SearchResultList from './components/SearchResultList.vue'
import BottomPlayer from './components/BottomPlayer.vue'

// 导入工具函数
import musicApi, { QUALITY_LEVELS } from './services/musicApi.js'
import { isDark, toggleTheme, initThemeFromLocalStorage } from './utils/themeManager.js'
import { settings, loadSettings, saveSettings } from './utils/settingsManager.js'
import {
    musicUrl, loading, musicInfo, playlistUrl, playlistLoading, playlistInfo, albumUrl, albumLoading, albumInfo, elapsedTime, parseMusic, parsePlaylist, parseAlbum, clearMusicResult, clearPlaylistResult, clearAlbumResult, setExampleUrl, cleanupTimer, searchResults, playlistSearchResults, albumSearchResults,
    currentParsingTrack, parsingProgress
  } from './utils/parseManager.js'
import { displayTracks, currentPage, totalTracks, updateDisplayTracks } from './utils/paginationManager.js'
import { isMobile, initDeviceDetection, cleanupDeviceDetection } from './utils/deviceDetector.js'
import { getCurrentExampleLinks, getExampleTitle } from './utils/exampleData.js'

// 响应式数据
const currentView = ref('search')
const showNotice = ref(true)
const showSettingsDialog = ref(false)
const searchContainerRef = ref(null)

// 播放列表
const playerPlaylist = ref([])

// 模式配置 - 按顺序：1 搜索，2 单曲，3 歌单，4 专辑，5 榜单
const modes = [
  { key: 'search', label: '搜索', title: '输入搜索关键词', desc: '支持搜索歌曲、歌手、专辑等', placeholder: '请输入搜索关键词' },
  { key: 'music', label: '单曲', title: '输入歌曲 URL 或 ID', desc: '支持单曲分享链接或直接输入数字ID', placeholder: '在此输入网易云音乐单曲链接或ID' },
  { key: 'playlist', label: '歌单', title: '输入歌单 URL 或 ID', desc: '支持歌单分享链接或直接输入数字ID', placeholder: '在此输入网易云音乐歌单链接或ID' },
  { key: 'album', label: '专辑', title: '输入专辑 URL 或 ID', desc: '支持专辑分享链接或直接输入数字ID', placeholder: '在此输入网易云音乐专辑链接或ID' },
  { key: 'rank', label: '榜单', title: '选择官方榜单', desc: '获取网易云官方实时排行榜数据', placeholder: '' }
]

// 示例链接 - 使用计算属性，随视图切换自动更新
const exampleLinks = computed(() => {
  return getCurrentExampleLinks(currentView.value)
})

// 方法
const getCurrentMode = () => {
  return modes.find(m => m.key === currentView.value) || modes[0]
}

const getCurrentExampleTitle = () => {
  return getExampleTitle(currentView.value)
}

const handleNoticeClose = () => {
  console.log('Notice closed')
}

const handleViewChange = (view) => {
  currentView.value = view
  // 切换模式时不清空搜索结果，保持每个模式的独立状态
  // 只清空其他模式的解析详情结果
  if (view === 'music') {
    clearPlaylistResult()
    clearAlbumResult()
  } else if (view === 'playlist') {
    clearMusicResult()
    clearAlbumResult()
  } else if (view === 'album') {
    clearMusicResult()
    clearPlaylistResult()
  }
}

const handleParse = async ({ url }) => {
  musicUrl.value = url
  // 从设置中读取音质
  const quality = settings.selectedQuality || 'lossless'
  await parseMusic(quality, currentView.value)
  
  // 解析成功后添加到历史记录
  if (searchContainerRef.value && url.trim()) {
    searchContainerRef.value.addHistoryRecord(url.trim())
  }
}

const handleExampleClick = (link) => {
  setExampleUrl(link.url, currentView.value)
}

const handleChartChange = (chartId) => {
  console.log('Chart changed:', chartId)
}

const handlePageChange = (page) => {
  console.log('App.vue handlePageChange called with page:', page)
  console.log('Before: currentPage =', currentPage.value, ', displayTracks.length =', displayTracks.value.length)
  currentPage.value = page
  updateDisplayTracks()
  console.log('After: currentPage =', currentPage.value, ', displayTracks.length =', displayTracks.value.length)
  console.log('Display tracks updated:', displayTracks.value.slice(0, 3))
}

const handleParseSong = (song) => {
  currentView.value = 'music'
  musicUrl.value = `https://music.163.com/song?id=${song.id}`
  const quality = settings.selectedQuality || 'lossless'
  parseMusic(quality, 'music')
}

// 当前播放索引
const currentPlayIndex = ref(0)

// 处理歌曲播放
const handlePlaySong = async (track) => {
  // 调试：打印原始 track 数据
  console.log('Original track data:', track)
  
  // 将当前列表添加到播放列表
  let tracks = []
  
  // 优先使用歌单的所有歌曲（不仅仅是当前页）
  if (playlistInfo.value?.tracks?.length > 0) {
    tracks = playlistInfo.value.tracks
  }
  // 其次使用当前显示的列表
  else if (displayTracks.value.length > 0) {
    tracks = displayTracks.value
  }
  // 如果都没有，就只播放当前这一首歌
  else {
    tracks = [track]
  }
  
  // 转换为播放器所需格式
  const newPlaylist = tracks.map(t => ({
    id: t.id,
    name: t.name,
    artist: t.artist || t.ar?.[0]?.name || (Array.isArray(t.artists) ? t.artists[0]?.name : t.artists) || '未知艺术家',
    album: t.album || t.al?.name || '未知专辑',
    cover: getCoverUrl(t),
    lrc: t.lrc || '',
    url: t.url || '' // 添加url字段
  }))
  
  // 调试：打印转换后的播放列表
  console.log('Converted playlist (first 3):', newPlaylist.slice(0, 3))
  
  // 找到当前歌曲索引
  const index = newPlaylist.findIndex(p => p.id === track.id)
  if (index >= 0) {
    // 如果找到了，更新当前歌曲的url和lrc（如果有新的）
    if (track.url) {
      newPlaylist[index].url = track.url
    }
    if (track.lrc) {
      newPlaylist[index].lrc = track.lrc
    }
    currentPlayIndex.value = index
  } else {
    // 如果没找到，就把这首歌加到播放列表开头
    newPlaylist.unshift({
      id: track.id,
      name: track.name,
      artist: track.artist || track.ar?.[0]?.name || (Array.isArray(track.artists) ? track.artists[0]?.name : track.artists) || '未知艺术家',
      album: track.album || track.al?.name || '未知专辑',
      cover: getCoverUrl(track),
      lrc: track.lrc || '',
      url: track.url || ''
    })
    currentPlayIndex.value = 0
  }
  
  // 更新播放列表（触发播放器监听）
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
    // data可能是 { name } 或 { track, quality }
    const name = data.name || data.track?.name
    if (name) {
      searchContainerRef.value.addHistoryRecord(name)
    }
  }
}

const handleTrackSelected = (track) => {
  console.log('Track selected:', track)
  // 这里可以添加选择歌曲后的逻辑，比如自动播放等
}

// 生命周期
onMounted(() => {
  loadSettings()
  initDeviceDetection()
  initThemeFromLocalStorage()
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
  display: flex;
  flex-direction: column;
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
</style>
