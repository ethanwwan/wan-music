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
          :quality-options="qualityOptions"
          :example-links="exampleLinks"
          :example-title="getCurrentExampleTitle()"
          :loading="loading"
          @parse="handleParse"
          @quality-change="handleQualityChange"
          @example-click="handleExampleClick"
          @chart-change="handleChartChange"
        />

        <!-- 搜索结果面板组件 -->
        <SearchResultPanel 
          :songs="searchResults"
          :playlists="playlistSearchResults"
          :albums="albumSearchResults"
          :current-mode="currentView"
          @parse-song="handleParseSong"
          @parse-playlist="handleParsePlaylist"
          @parse-album="handleParseAlbum"
        />

        <!-- 原有的其他内容保持不变 -->
        <!-- 单曲解析视图 -->
        <div class="view-container" v-show="currentView === 'music'">
          <!-- 音乐播放器组件 -->
          <MusicPlayer
            v-if="musicInfo"
            :music-info="musicInfo"
            :music-url="musicInfo.url"
            :selected-quality="selectedQuality"
            @track-parsed="handleTrackParsed"
          />
        </div>

        <!-- 歌单解析视图 -->
        <div class="view-container" v-show="currentView === 'playlist' && playlistInfo && displayTracks.length > 0">
          <PlaylistDetail
            :playlist-info="playlistInfo"
            :display-tracks="displayTracks"
            :current-page="currentPage"
            :page-size="20"
            :total-tracks="totalTracks"
            :selected-quality="selectedQuality"
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
import SearchResultPanel from './components/SearchResultPanel.vue'
import Footer from './components/Footer.vue'
import FloatingActions from './components/FloatingActions.vue'
import SettingsDialog from './components/SettingsDialog.vue'

// 导入原有组件
import MusicPlayer from './components/MusicPlayer.vue'
import PlaylistDetail from './components/PlaylistDetail.vue'

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
const selectedQuality = ref('lossless')
const searchContainerRef = ref(null)

// 模式配置 - 按顺序：1 搜索，2 单曲，3 歌单，4 专辑，5 榜单
const modes = [
  { key: 'search', label: '搜索', title: '输入搜索关键词', desc: '支持搜索歌曲、歌手、专辑等', placeholder: '请输入搜索关键词' },
  { key: 'music', label: '单曲', title: '输入歌曲 URL 或 ID', desc: '支持单曲分享链接或直接输入数字ID', placeholder: '在此输入网易云音乐单曲链接或ID' },
  { key: 'playlist', label: '歌单', title: '输入歌单 URL 或 ID', desc: '支持歌单分享链接或直接输入数字ID', placeholder: '在此输入网易云音乐歌单链接或ID' },
  { key: 'album', label: '专辑', title: '输入专辑 URL 或 ID', desc: '支持专辑分享链接或直接输入数字ID', placeholder: '在此输入网易云音乐专辑链接或ID' },
  { key: 'rank', label: '榜单', title: '选择官方榜单', desc: '获取网易云官方实时排行榜数据', placeholder: '' }
]

// 音质选项
const qualityOptions = Object.entries(QUALITY_LEVELS).map(([value, label]) => ({
  value,
  label
}))

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
  // 清空结果
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

const handleParse = async ({ url, quality }) => {
  musicUrl.value = url
  selectedQuality.value = quality
  await parseMusic(quality, currentView.value)
}

const handleQualityChange = (quality) => {
  selectedQuality.value = quality
}

const handleExampleClick = (link) => {
  setExampleUrl(link.url, currentView.value)
}

const handleChartChange = (chartId) => {
  console.log('Chart changed:', chartId)
}

const handlePageChange = (page) => {
  currentPage.value = page
  updateDisplayTracks()
}

const handleParseSong = (song) => {
  currentView.value = 'music'
  musicUrl.value = `https://music.163.com/song?id=${song.id}`
  parseMusic(selectedQuality.value, 'music')
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
  if (searchContainerRef.value && data && data.name) {
    searchContainerRef.value.addHistoryRecord(data.name)
  }
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
