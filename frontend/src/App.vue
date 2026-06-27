<template>
  <a-config-provider :theme="{ token: themeToken }">
    <a-layout class="app-container" style="min-height: 100vh;">
      <a-layout-content class="app-main">
        <div class="hero-header">
          <h1 class="hero-title">Wan Music - 多平台音乐下载</h1>
          <p class="hero-subtitle">支持网易云 / QQ 音乐 / 酷狗 / 波点，搜索歌曲/歌单，解析真实下载地址。</p>
        </div>

        <SearchContainer
          ref="searchContainerRef"
          title="输入搜索关键词"
          placeholder="请输入歌曲名或歌单名"
          :loading="loading"
          @parse="handleParse"
          @open-settings="showSettingsDialog = true"
        />

        <SearchResult
          :key="searchSession"
          :songs="searchResults"
          :playlists="playlistSearchResults"
          :loading="loading"
          :tab-loading="tabLoading"
          :search-type="currentSearchType"
          :warnings="searchWarnings"
          @track-play="handlePlaySong"
          @search-type-change="handleSearchTypeChange"
        />
      </a-layout-content>

      <a-layout-footer>
        <footer class="footer-container">
          <div class="footer-content">
            <p class="footer-text">© 2026 Wan Music. All rights reserved.</p>
            <p class="footer-text">开源项目 | 仅供学习</p>
            <p class="footer-text">Version 1.3.6 · 构建时间: 2026.5.24</p>
          </div>
        </footer>
      </a-layout-footer>

      <SettingsDialog v-model:open="showSettingsDialog" />
      <DownloadDrawer />
      <MusicPlayer :current-song="currentSong" :autoplay="true" @play-error="handlePlayError" />
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { message } from 'ant-design-vue'

import SearchContainer from './components/SearchContainer.vue'
import SearchResult from './components/SearchResult.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import MusicPlayer from './components/MusicPlayer.vue'
import DownloadDrawer from './components/DownloadDrawer.vue'

import musicApi from './services/musicApi.js'
import { initThemeFromLocalStorage, DEFAULT_THEME_COLOR } from './utils/themeManager.js'
import { settings, loadSettings } from './utils/settingsManager.js'
import { loading, tabLoading, parseMusic, searchByTab, searchResults, playlistSearchResults, searchWarnings } from './utils/parseManager.js'
import { downloadQueueStore as queueStore } from './stores/downloadQueue.js'

const showSettingsDialog = ref(false)
const searchContainerRef = ref(null)
/** 'keyword' | 'music_link' | 'playlist_link' */
const currentSearchType = ref('keyword')
const currentSong = ref(null)
const currentSources = ref([localStorage.getItem('wan-music-selected-data-source') || 'netease'])
/** 当前输入（供 tab 切换时回传给后端） */
const currentInput = ref('')
/** 搜索会话计数器：每次点击搜索按钮自增，作为 :key 强制 SearchResult 重新挂载 */
const searchSession = ref(0)

const themeToken = reactive({ colorPrimary: DEFAULT_THEME_COLOR })

const handleParse = async ({ url, sources = ['netease'] }) => {
  searchSession.value++  // 每次搜索自增，驱动 SearchResult 重新挂载
  currentSources.value = sources
  currentInput.value = url
  // URL 解析交由后端，前端先按关键词的双 tab 占位；后端返回后再收窄为单 tab
  currentSearchType.value = 'keyword'
  await parseMusic(url, sources, musicApi.isHttpUrl(url) ? 0 : 1)

  if (musicApi.isHttpUrl(url)) {
    // URL 后端只会返回歌曲或歌单之一，按结果收窄为对应单 tab
    if (searchResults.value.length > 0) currentSearchType.value = 'music_link'
    else if (playlistSearchResults.value.length > 0) currentSearchType.value = 'playlist_link'
  }

  if (searchContainerRef.value && url.trim()) {
    searchContainerRef.value.addHistoryRecord(url.trim())
  }
}

const handleSearchTypeChange = async (searchType) => {
  const backendType = searchType === 'playlist' ? 2 : 1
  await searchByTab(currentInput.value, currentSources.value, backendType)
}

const handlePlaySong = (track) => {
  currentSong.value = {
    id: track.id,
    name: track.name,
    artist: track.artist || track.ar?.[0]?.name || (Array.isArray(track.artists) ? track.artists[0]?.name : track.artists) || '未知艺术家',
    album: track.album || track.al?.name || '未知专辑',
    cover: track.cover || track.picUrl || track.al?.picUrl || track.album?.coverImgUrl || track.album?.picUrl || '',
    lrc: track.lrc || '',
    url: track.url || '',
    fileExtension: track.fileExtension || '.mp3',
    source: track.source || '',
    unavailable: track.unavailable || false
  }
}

/** 播放失败（无版权）：标记 + 提示 */
const handlePlayError = (track) => {
  if (track) track.unavailable = true
  message.warning(`《${track?.name}》因版权问题暂时无法播放`)
}

onMounted(() => {
  loadSettings()
  initThemeFromLocalStorage()
  themeToken.colorPrimary = DEFAULT_THEME_COLOR
  queueStore.init()
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

.hero-header {
  text-align: center;
  margin-bottom: 40px;
}

.hero-title {
  font-size: var(--font-size-headline-lg);
  font-weight: 700;
  line-height: var(--line-height-headline-lg);
  margin-bottom: 8px;
  color: var(--color-on-surface);
  font-family: var(--font-family);
}

.hero-subtitle {
  font-size: var(--font-size-body-lg);
  line-height: var(--line-height-body-lg);
  font-weight: 400;
  color: var(--color-text-muted);
  margin: 0;
  font-family: var(--font-family);
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
  }
  .hero-subtitle {
    font-size: var(--font-size-body-md);
    line-height: var(--line-height-body-md);
  }
}

.footer-container {
  width: 100%;
  margin-top: auto;
  background: transparent;
}

.footer-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 var(--padding-desktop);
  text-align: center;
  padding-top: 3rem;
  padding-bottom: 3rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.footer-text {
  color: var(--color-text-muted);
  font-size: var(--font-size-body-sm);
  margin: 0;
}

@media (max-width: 768px) {
  .footer-content {
    padding: 0 var(--padding-mobile);
    padding-top: 2rem;
    padding-bottom: 2rem;
  }
}
</style>
