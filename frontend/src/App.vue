<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElNotification, ElLoading } from 'element-plus'
import { Microphone, Moon, Sunny, Search, Link, VideoPlay, InfoFilled, Setting, User, Download, Document, Check, FolderOpened, Loading, List, Refresh, ElementPlus } from '@element-plus/icons-vue'
import { ElSkeleton, ElAside } from 'element-plus'
import MusicPlayer from './components/MusicPlayer.vue'
import PlaylistDetail from './components/PlaylistDetail.vue'
import musicApi, { QUALITY_LEVELS } from './services/musicApi.js'
import { setCookie, getCookie } from './utils/cookies.js'

import { isDark, toggleTheme, initThemeFromLocalStorage } from './utils/themeManager.js'
import { settings, loadSettings, saveSettings } from './utils/settingsManager.js'
import {
  musicUrl, loading, musicInfo, playlistUrl, playlistLoading, playlistInfo, albumUrl, albumLoading, albumInfo, elapsedTime, parseMusic, parsePlaylist, parseAlbum, clearMusicResult, clearPlaylistResult, clearAlbumResult, setExampleUrl, cleanupTimer,
  currentParsingTrack, parsingProgress
} from './utils/parseManager.js'
import {
  currentPage, pageSize, totalTracks, displayTracks,
  updateDisplayTracks, handlePageChange
} from './utils/paginationManager.js'
import { isMobile, initDeviceDetection, cleanupDeviceDetection } from './utils/deviceDetector.js'
import { getCurrentExampleLinks } from './utils/exampleData.js'

const selectedQuality = ref('lossless')
const showSettingsDialog = ref(false)
const showWelcomeDialog = ref(false)
const currentView = ref('music') // 'music', 'playlist', 'album', 'search', 'rank'

const qualityOptions = Object.entries(QUALITY_LEVELS).map(([value, label]) => ({
  value,
  label
}))

const isLocalEnv = computed(() => {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1' || host === '::1'
})

onUnmounted(() => {
  cleanupDeviceDetection()
  cleanupTimer()
})

onMounted(() => {
  loadSettings()
  initDeviceDetection()
  initThemeFromLocalStorage()
})

const toggleThemeWithLoading = () => {
  const bg = isDark.value ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.7)'
  const text = isDark.value ? '切换为浅色模式…' : '切换为深色模式…'
  const loading = ElLoading.service({
    fullscreen: true,
    lock: true,
    text,
    background: bg
  })
  requestAnimationFrame(() => {
    toggleTheme()
    setTimeout(() => {
      loading.close()
    }, 700)
  })
}

const switchView = (view) => {
  currentView.value = view
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

const useExampleLink = (link, name) => {
  if (currentView.value === 'playlist') {
    setExampleUrl(link, 'playlist')
    ElMessage.success(`已选择示例歌单: ${name}`)
  } else if (currentView.value === 'album') {
    setExampleUrl(link, 'album')
    ElMessage.success(`已选择示例专辑: ${name}`)
  } else {
    setExampleUrl(link, 'music')
    ElMessage.success(`已选择示例歌曲: ${name}`)
  }
}

const handleTrackParsed = async (data) => {
  try {
    const track = data.track || data
    const quality = data.quality || selectedQuality.value
    const qualityValue = typeof quality === 'string' ? quality : 'lossless'
    const musicUrlValue = `https://music.163.com/song?id=${track.id}`
    const result = await musicApi.parseMusicInfo(musicUrlValue, qualityValue)
    musicInfo.value = result
    ElNotification({
      title: '解析成功',
      message: `成功解析歌曲：${result.name} (${result.qualityName})`,
      type: 'success'
    })
  } catch (error) {
    ElMessage.error(error.message || '解析失败，请稍后重试')
  }
}

const handleTrackSelected = () => {}

const computedPlaylistInfo = computed(() => {
  if (currentView.value === 'playlist' && playlistInfo.value) {
    return playlistInfo.value;
  }
  if (currentView.value === 'album' && albumInfo.value) {
    return {
      name: albumInfo.value.name,
      creator: albumInfo.value.artist,
      time: albumInfo.value.publishTime,
      totalCount: albumInfo.value.trackCount,
      tracks: albumInfo.value.tracks,
      picUrl: albumInfo.value.picUrl,
      isAlbum: true,
    };
  }
  return null;
});

const exampleLinks = computed(() => {
  return getCurrentExampleLinks()
})

const viewTitles = {
  music: '单曲解析',
  playlist: '歌单解析',
  album: '专辑解析',
  search: '搜索',
  rank: '榜单'
}
</script>

<template>
  <el-config-provider size="default">
    <el-container class="app-container" direction="vertical">
      <!-- 顶部导航栏 -->
      <el-header class="app-header">
        <div class="header-content">
          <div class="header-left">
            <div class="logo">
              <img src="/favicon.svg" alt="Logo" class="logo-img" />
              <span class="logo-text">网易云音乐解析</span>
            </div>
          </div>

          <div class="header-center">
            <div class="nav-tabs">
              <el-button
                class="nav-btn"
                :class="{ active: currentView === 'music' }"
                @click="switchView('music')"
              >
                单曲
              </el-button>
              <el-button
                class="nav-btn"
                :class="{ active: currentView === 'album' }"
                @click="switchView('album')"
              >
                专辑
              </el-button>
              <el-button
                class="nav-btn"
                :class="{ active: currentView === 'playlist' }"
                @click="switchView('playlist')"
              >
                歌单
              </el-button>
              <el-button
                class="nav-btn"
                :class="{ active: currentView === 'search' }"
                @click="switchView('search')"
              >
                搜索
              </el-button>
              <el-button
                class="nav-btn"
                :class="{ active: currentView === 'rank' }"
                @click="switchView('rank')"
              >
                榜单
              </el-button>
            </div>
          </div>

          <div class="header-right">
            <el-button
              @click="toggleThemeWithLoading"
              class="theme-btn"
              :icon="isDark ? Sunny : Moon"
              circle
            />
            <el-button
              @click="showSettingsDialog = true"
              class="settings-btn"
              :icon="Setting"
              circle
            />
          </div>
        </div>
      </el-header>

      <!-- 主要内容区域 -->
      <el-main class="app-main">
        <!-- 页面标题卡片 -->
        <el-card class="page-header-card" shadow="hover">
          <div class="page-header">
            <h1 class="page-title">{{ viewTitles[currentView] }}</h1>
            <p class="page-description">永久免费的网易云音乐高品质解析</p>
          </div>
        </el-card>

        <!-- 示例歌曲 -->
        <el-card class="module-card" shadow="hover">
          <div class="module-title">
            <el-icon><VideoPlay /></el-icon>
            <span>示例歌曲</span>
          </div>
          <div class="example-tags">
            <el-tag
              v-for="link in exampleLinks"
              :key="link.name"
              class="example-tag"
              type="danger"
              @click="useExampleLink(link.url, link.name)"
            >
              {{ link.name }}
            </el-tag>
          </div>
        </el-card>

        <!-- 单曲解析视图 -->
        <div class="view-container" v-show="currentView === 'music'">
          <el-card class="module-card" shadow="hover">
            <div class="module-title">
              <el-icon><Link /></el-icon>
              <span>音乐链接解析</span>
            </div>
            <el-form :model="{ musicUrl, selectedQuality }" label-position="left">
              <el-form-item label="音乐链接">
                <el-input
                  v-model="musicUrl"
                  placeholder="请输入网易云音乐分享链接"
                  clearable
                  @keyup.enter="parseMusic"
                  size="large"
                >
                  <template #prefix>
                    <el-icon><Link /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <div class="form-row">
                <el-form-item label="音质选择" class="quality-item">
                  <el-select v-model="selectedQuality" size="large" style="width: 200px">
                    <el-option
                      v-for="option in qualityOptions"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    >
                      <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span>{{ option.label }}</span>
                        <el-tag v-if="option.value === 'jymaster'" type="danger" size="small">最高</el-tag>
                        <el-tag v-else-if="option.value === 'lossless'" type="success" size="small">推荐</el-tag>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </div>

              <el-form-item>
                <el-button
                  type="primary"
                  @click="() => parseMusic(selectedQuality)"
                  :loading="loading"
                  :disabled="!musicUrl.trim()"
                  :icon="Search"
                  size="large"
                  style="width: 100%"
                >
                  {{ loading ? '解析中...' : '开始解析' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 专辑解析视图 -->
        <div class="view-container" v-show="currentView === 'album'">
          <el-card class="module-card" shadow="hover">
            <div class="module-title">
              <el-icon><FolderOpened /></el-icon>
              <span>专辑链接解析</span>
            </div>
            <el-form :model="{ albumUrl }" label-position="left">
              <el-form-item label="专辑链接">
                <el-input
                  v-model="albumUrl"
                  placeholder="请输入网易云音乐专辑链接"
                  clearable
                  @keyup.enter="parseAlbum"
                  size="large"
                >
                  <template #prefix>
                    <el-icon><Link /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <div class="form-row">
                <el-form-item label="音质选择" class="quality-item">
                  <el-select v-model="selectedQuality" size="large" style="width: 200px">
                    <el-option
                      v-for="option in qualityOptions"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    >
                      <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span>{{ option.label }}</span>
                        <el-tag v-if="option.value === 'jymaster'" type="danger" size="small">最高</el-tag>
                        <el-tag v-else-if="option.value === 'lossless'" type="success" size="small">推荐</el-tag>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </div>

              <el-form-item>
                <el-button
                  type="primary"
                  @click="() => parseAlbum(updateDisplayTracks)"
                  :loading="albumLoading"
                  :disabled="!albumUrl.trim()"
                  :icon="Search"
                  size="large"
                  style="width: 100%"
                >
                  {{ albumLoading ? '解析中...' : '开始解析' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 歌单解析视图 -->
        <div class="view-container" v-show="currentView === 'playlist'">
          <el-card class="module-card" shadow="hover">
            <div class="module-title">
              <el-icon><Document /></el-icon>
              <span>歌单链接解析</span>
            </div>
            <el-form :model="{ playlistUrl }" label-position="left">
              <el-form-item label="歌单链接">
                <el-input
                  v-model="playlistUrl"
                  placeholder="请输入网易云音乐歌单链接"
                  clearable
                  @keyup.enter="parsePlaylist"
                  size="large"
                >
                  <template #prefix>
                    <el-icon><Link /></el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <div class="form-row">
                <el-form-item label="音质选择" class="quality-item">
                  <el-select v-model="selectedQuality" size="large" style="width: 200px">
                    <el-option
                      v-for="option in qualityOptions"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    >
                      <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span>{{ option.label }}</span>
                        <el-tag v-if="option.value === 'jymaster'" type="danger" size="small">最高</el-tag>
                        <el-tag v-else-if="option.value === 'lossless'" type="success" size="small">推荐</el-tag>
                      </div>
                    </el-option>
                  </el-select>
                </el-form-item>
              </div>

              <el-form-item>
                <el-button
                  type="primary"
                  @click="() => parsePlaylist(updateDisplayTracks)"
                  :loading="playlistLoading"
                  :disabled="!playlistUrl.trim()"
                  :icon="Search"
                  size="large"
                  style="width: 100%"
                >
                  {{ playlistLoading ? '解析中...' : '开始解析' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 搜索视图 -->
        <div class="view-container" v-show="currentView === 'search'">
          <el-card class="module-card" shadow="hover">
            <div class="module-title">
              <el-icon><Search /></el-icon>
              <span>搜索音乐</span>
            </div>
            <el-empty description="搜索功能开发中..." />
          </el-card>
        </div>

        <!-- 榜单视图 -->
        <div class="view-container" v-show="currentView === 'rank'">
          <el-card class="module-card" shadow="hover">
            <div class="module-title">
              <el-icon><List /></el-icon>
              <span>热门榜单</span>
            </div>
            <el-empty description="榜单功能开发中..." />
          </el-card>
        </div>

        <!-- 歌单/专辑详情组件 -->
        <div v-if="computedPlaylistInfo" class="playlist-section">
          <PlaylistDetail
            :playlist-info="computedPlaylistInfo"
            :display-tracks="displayTracks"
            :current-page="currentPage"
            :page-size="pageSize"
            :total-tracks="totalTracks"
            :selected-quality="selectedQuality"
            :settings="settings"
            @track-parsed="handleTrackParsed"
            @track-selected="handleTrackSelected"
            @page-change="handlePageChange"
          />
        </div>

        <!-- 播放器区域 -->
        <div v-if="musicInfo" class="player-section">
          <Suspense>
            <template #default>
              <MusicPlayer :music-info="musicInfo" :settings="settings" />
            </template>
            <template #fallback>
              <div class="loading-placeholder">
                <el-skeleton :rows="3" animated />
                <div class="loading-text">正在加载播放器...</div>
              </div>
            </template>
          </Suspense>
        </div>

        <!-- 作者信息 -->
        <el-card class="author-card" shadow="hover">
          <div class="author-info">
            <img src="https://p2.music.126.net/625-tE8OzdM-rWO37PgqlQ==/109951168111472442.jpg" alt="Author" class="author-avatar" />
            <div class="author-text">
              <div class="author-name">苏晓晴</div>
              <div class="author-desc">一个全栈开发菜鸟</div>
            </div>
          </div>
        </el-card>
      </el-main>

      <!-- 播放器底部固定 -->
      <el-footer class="app-footer">
        <!-- 播放器内容由 MusicPlayer 组件处理 -->
      </el-footer>
    </el-container>
  </el-config-provider>
</template>

<style scoped>
/* Header 样式 */
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: var(--app-max-width);
  margin: 0 auto;
  height: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.logo-img {
  width: 32px;
  height: 32px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--app-text-primary);
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-tabs {
  display: flex;
  gap: var(--space-1);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.theme-btn,
.settings-btn {
  border: none;
  background: transparent;
}

.theme-btn:hover,
.settings-btn:hover {
  background: rgba(194, 12, 12, 0.1);
}

/* 主内容布局 */
.app-main {
  padding-bottom: 100px;
}

.view-container {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 示例标签 */
.example-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

/* 表单样式 */
.form-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.quality-item {
  flex: 1;
}

/* 作者信息卡片 */
.author-card {
  margin-top: var(--space-5);
  background: linear-gradient(135deg, var(--app-bg) 0%, var(--app-card-bg) 100%);
}

.author-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
}

.author-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
}

.author-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.author-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--app-text-primary);
}

.author-desc {
  font-size: 13px;
  color: var(--app-text-secondary);
}

/* 播放器间距 */
.player-section {
  margin-top: var(--space-4);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-center {
    display: none;
  }

  .logo-text {
    font-size: 16px;
  }

  .nav-tabs {
    flex-wrap: wrap;
  }
}
</style>
