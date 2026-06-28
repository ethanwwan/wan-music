<template>
  <a-config-provider :theme="{ token: themeToken }">
    <a-layout class="app-container" style="min-height: 100vh;">
      <a-layout-content class="app-main">
        <div class="hero-header">
          <h1 class="hero-title">Wan Music - 多平台音乐下载</h1>
          <p class="hero-subtitle">支持网易云 / QQ 音乐 / 酷狗 / 酷我，搜索歌曲，解析真实下载地址。</p>
        </div>

        <SearchContainer
          ref="searchContainerRef"
          title="输入搜索关键词"
          placeholder="请输入歌曲名或粘贴歌曲/歌单链接"
          :loading="loading"
          @parse="handleParse"
          @open-settings="showSettingsDialog = true"
        />

        <SearchResult
          :key="searchSession"
          :songs="searchResults"
          :type="searchType"
          :detail="searchDetail"
          :loading="loading"
          :searched="searched"
          @track-play="handlePlaySong"
          @track-unavailable="handleTrackUnavailable"
        />
      </a-layout-content>

      <a-layout-footer>
        <footer class="footer-container">
          <div class="footer-content">
            <p class="footer-text">© 2026 Wan Music. All rights reserved.</p>
            <p class="footer-text">开源项目 | 仅供学习</p>
            <p class="footer-text">Version 1.4.0 · 构建时间: 2026.6.28</p>
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

import { initThemeFromLocalStorage, DEFAULT_THEME_COLOR } from './utils/themeManager.js'
import { loadSettings } from './utils/settingsManager.js'
import { loading, searchResults, searchType, searchDetail, parseMusic } from './utils/parseManager.js'
import { downloadQueueStore as queueStore } from './stores/downloadQueue.js'

const showSettingsDialog = ref(false)
const searchContainerRef = ref(null)
const currentSong = ref(null)
const currentSource = ref(localStorage.getItem('wan-music-selected-data-source') || 'netease')
/** 是否已搜索过（用来控制空状态展示） */
const searched = ref(false)
/** 搜索会话计数器：每次搜索自增，作为 :key 强制 SearchResult 重新挂载 */
const searchSession = ref(0)

const themeToken = reactive({ colorPrimary: DEFAULT_THEME_COLOR })

const handleParse = async ({ url, sources = [currentSource.value] }) => {
  const source = sources[0] || currentSource.value
  currentSource.value = source
  // 注意：searchSession 必须在 parseMusic 成功之后再自增，
  // 否则失败/空结果时 SearchResult 会被强制重新挂载、清空旧数据。
  const result = await parseMusic(url, source)
  if (!result?.success) {
    // 搜索失败 → 保留旧数据，只在 toast 提示错误（parseMusic 内部已 message.error）
    return
  }
  // 成功后才推进会话计数（强制 SearchResult 重新挂载以重置分页/选择）
  searchSession.value++
  searched.value = true
  // 记录到历史
  if (searchContainerRef.value && url.trim()) {
    const isUrl = /^https?:\/\//i.test(url.trim())
    let displayName = url.trim()
    let type = isUrl ? 'song' : 'search'
    if (result.type === 'playlist' && result.detail?.name) {
      displayName = result.detail.name
      type = 'playlist'
    } else if (isUrl && result.type === 'song' && result.data?.[0]?.name) {
      // 歌曲 URL：取解析出的歌曲名
      displayName = result.data[0].name
    }
    searchContainerRef.value.addHistoryRecord({
      name: displayName,
      url: url.trim(),
      type,
    })
  }
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

/** 同步搜索结果列表里的 unavailable 标记 */
const handleTrackUnavailable = (track) => {
  const idx = searchResults.value.findIndex(s => s.id === track.id)
  if (idx !== -1) searchResults.value[idx].unavailable = true
}

const handlePlayError = (track) => {
  if (!track) return
  track.unavailable = true
  const idx = searchResults.value.findIndex(s => s.id === track.id)
  if (idx !== -1) searchResults.value[idx].unavailable = true
  message.warning(`《${track.name}》因版权问题暂时无法播放`)
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
