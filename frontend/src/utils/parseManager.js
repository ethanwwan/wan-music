/**
 * 解析管理
 * 提供搜索/解析音乐、歌单的逻辑与状态
 */

import { ref } from 'vue'
import { message, notification } from 'ant-design-vue'
import musicApi from '../services/musicApi.js'
import { allTracks, totalTracks, currentPage, updateDisplayTracks } from './paginationManager.js'

/** 接口版本标签 */
const getApiVersionLabel = () => ''  // 已废弃：不再显示接口版本

// ==================== 解析结果状态 ====================

export const musicUrl = ref('')
export const loading = ref(false)
export const musicInfo = ref(null)

export const playlistUrl = ref('')
export const playlistLoading = ref(false)
export const playlistInfo = ref(null)

export const albumUrl = ref('')
export const albumLoading = ref(false)
export const albumInfo = ref(null)

export const searchResults = ref([])
export const playlistSearchResults = ref([])
// 后端搜索返回的警告（如 'playlist_search_unsupported'，表示某平台不支持歌单搜索）
export const searchWarnings = ref([])

// ==================== 计时器 ====================

export const parseStartTime = ref(0)
export const elapsedTime = ref(0)
let timerInterval = null

const startTimer = () => {
  parseStartTime.value = Date.now()
  elapsedTime.value = 0
  timerInterval = setInterval(() => {
    elapsedTime.value = Math.floor((Date.now() - parseStartTime.value) / 1000)
  }, 100)
}

const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

export const cleanupTimer = () => stopTimer()

// ==================== 错误消息格式化 ====================

/**
 * 根据错误对象返回对应的友好提示信息
 * @returns {{ message: string, type: 'warning'|'error', duration: number }}
 */
const formatErrorMessage = (error) => {
  const msg = error?.message || ''
  if (msg.includes('API服务器暂时不可用')) {
    return {
      message: 'API服务器暂时不可用，请稍后重试。这可能是由于服务器维护或网络问题导致的。',
      type: 'warning',
      duration: 8000
    }
  }
  if (msg.includes('付费') || msg.includes('版权限制')) {
    return {
      message: '该歌曲为付费或受版权限制，暂无法获取播放链接',
      type: 'error',
      duration: 6000
    }
  }
  if (msg.includes('下架') || msg.includes('无法获取')) {
    return {
      message: '该歌曲已下架或者无法获取',
      type: 'error',
      duration: 6000
    }
  }
  if (msg.includes('网络连接失败') || msg.includes('网络请求失败')) {
    return { message: msg, type: 'error', duration: 6000 }
  }
  return { message: msg || '操作失败，请稍后重试', type: 'error', duration: 6000 }
}

/** 显示错误提示（统一入口） */
const showErrorToast = (error) => {
  const formatted = formatErrorMessage(error)
  // 注意：message.info/error/warning 接收的是字符串，不能直接传对象
  // ant-design-vue 在收到对象时会显示 "[object Object]"，必须取 message 字段
  const { message: text, type, duration } = formatted
  if (type === 'warning') {
    message.warning(text, duration)
  } else {
    message.error(text, duration)
  }
}

// ==================== 判断歌曲是否无版权 ====================

/**
 * 判断歌曲是否无版权
 * @param {Object} track 歌曲对象
 * @returns {Boolean} 是否无版权
 */
export const isTrackUnavailable = (track) => {
  if (!track) return true
  const privilege = track.privilege || {}
  const st = privilege.st !== undefined ? privilege.st : track.st
  const pl = privilege.pl !== undefined ? privilege.pl : track.pl
  // st === -200 表示明确无版权；pl === 0 表示播放级别 0（不可播放）
  return st === -200 || pl === 0
}

// ==================== 搜索/解析 ====================

/** 通知搜索结果 */
const notifySearchResult = (count, fromCache = false) => {
  notification.open({
    title: fromCache ? '读取缓存成功' : '搜索成功',
    message: `找到 ${count} 条结果${fromCache ? '（来自缓存）' : ''}`,
    type: 'success'
  })
}

/** 处理搜索模式的搜索逻辑 */
const handleSearchMode = async (sources, searchType = 0) => {
  loading.value = true
  try {
    const result = await musicApi.unifiedSearch(musicUrl.value, searchType, sources)
    const data = result.success ? result.data : { type: searchType, songs: [], playlists: [], warnings: [] }

    musicInfo.value = { name: musicUrl.value }
    searchWarnings.value = data.warnings || []

    // 根据后端返回的 type 字段决定展示
    if (data.type === 1) {
      // 只显示歌曲 tab
      searchResults.value = data.songs || []
      playlistSearchResults.value = []
    } else if (data.type === 2) {
      // 只显示歌单 tab
      searchResults.value = []
      playlistSearchResults.value = data.playlists || []
    } else {
      // 显示歌曲和歌单 tab
      searchResults.value = data.songs || []
      playlistSearchResults.value = data.playlists || []
    }

    const totalCount = (data.songs?.length || 0) + (data.playlists?.length || 0)
    if (totalCount > 0) {
      notifySearchResult(totalCount, result.fromCache)
    } else {
      // 如果是平台不支持歌单搜索，由 UI 展示专门提示，这里只 warn 一下
      if (searchType === 2 && searchWarnings.value.includes('playlist_search_unsupported')) {
        // UI 会展示专门提示，这里不再通用 warn
      } else {
        message.warning('未找到相关结果')
      }
    }
  } catch (error) {
    searchResults.value = []
    playlistSearchResults.value = []
    message.error('搜索失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/** 处理歌单模式的搜索/解析逻辑 */
const handlePlaylistMode = async (sources) => {
  // 有效歌单 URL 直接解析
  if (musicApi.validatePlaylistUrl(musicUrl.value)) {
    playlistUrl.value = musicUrl.value
    loading.value = true
    try {
      await parsePlaylist()
    } catch (error) {
      // 解析失败时回退到搜索
      await fallbackPlaylistSearch(sources)
    } finally {
      loading.value = false
    }
    return
  }
  // 否则作为关键词搜索歌单
  await searchPlaylistsByKeyword(sources)
}

/** 歌单解析失败后回退到关键词搜索 */
const fallbackPlaylistSearch = async (sources) => {
  playlistSearchResults.value = []
  try {
    const result = await musicApi.searchPlaylist(musicUrl.value, sources)
    if (result.success && result.data) {
      playlistSearchResults.value = result.data
      notification.open({
        title: '搜索成功',
        message: `找到 ${result.data.length || 0} 个歌单`,
        type: 'success'
      })
    } else {
      message.warning(result.error || '搜索结果为空')
    }
  } catch (error) {
    playlistSearchResults.value = []
    message.error('搜索失败，请稍后重试')
  }
}

/** 通过关键词搜索歌单 */
const searchPlaylistsByKeyword = async (sources) => {
  loading.value = true
  try {
    const result = await musicApi.searchPlaylist(musicUrl.value, sources)
    if (result.success && result.data) {
      playlistSearchResults.value = result.data
      playlistInfo.value = result
      notifySearchResult(result.data.length, result.fromCache)
    } else {
      playlistSearchResults.value = []
      message.warning(result.error || '搜索结果为空')
    }
  } catch (error) {
    playlistSearchResults.value = []
    message.error('搜索失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/** 通过 URL 直接解析歌曲 */
const parseMusicUrl = async (selectedQuality) => {
  loading.value = true
  try {
    const result = await musicApi.parseMusicFromUrl(musicUrl.value, selectedQuality)
    musicInfo.value = result
    notification.open({
      title: '解析成功',
      message: `成功解析歌曲：${result.name} (${result.qualityName})`,
      type: 'success'
    })
  } catch (error) {
    showErrorToast(error)
  } finally {
    loading.value = false
  }
}

/** 单曲关键词搜索 */
const searchMusicByKeyword = async () => {
  loading.value = true
  try {
    const result = await musicApi.searchMusic(musicUrl.value)
    if (result.success && result.data?.songs?.length > 0) {
      searchResults.value = result.data.songs
      notification.open({
        title: '搜索成功',
        message: `找到 ${result.data.songs.length} 首相关歌曲`,
        type: 'success'
      })
    } else {
      searchResults.value = []
      message.warning(result?.error || '搜索结果为空')
    }
  } catch (error) {
    searchResults.value = []
    message.error('搜索失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/**
 * 解析音乐信息
 * @param {string} selectedQuality 选择的音质
 * @param {string} mode 当前模式 ('search', 'music', 'playlist', 'album', 'artist', 'rank')
 * @param {Array} sources 数据源列表 ['netease', 'qq', ...]
 */
export const parseMusic = async (selectedQuality, mode = 'music', sources = ['netease'], searchType = 0) => {
  if (!musicUrl.value.trim()) {
    message.warning('请输入内容')
    return
  }

  switch (mode) {
    case 'search':
      return handleSearchMode(sources, searchType)
    case 'playlist':
      return handlePlaylistMode(sources)
    case 'album':
    case 'artist':
      // 专辑/歌手搜索功能暂未实现
      message.warning('该功能暂未实现')
      return
    case 'music':
    default:
      if (musicApi.validateMusicUrl(musicUrl.value)) {
        return parseMusicUrl(selectedQuality)
      }
      return searchMusicByKeyword()
  }
}

// ==================== 歌单解析 ====================

/** 应用歌单解析结果到全局状态 */
const applyPlaylistResult = (data) => {
  playlistInfo.value = data
  const tracks = (data.tracks || []).map(track => ({
    ...track,
    parsed: false,
    unavailable: isTrackUnavailable(track)
  }))
  allTracks.value = tracks
  totalTracks.value = tracks.length
  currentPage.value = 1
  updateDisplayTracks()
  return tracks
}

/** 构建歌单解析完成的通知消息 */
const buildPlaylistNotice = (tracks) => {
  const totalTime = Math.floor((Date.now() - parseStartTime.value) / 1000)
  const unavailableCount = tracks.filter(t => t.unavailable).length
  let msg = `共 ${tracks.length} 首歌曲，用时 ${totalTime} 秒 ${getApiVersionLabel()}`
  if (unavailableCount > 0) {
    msg += `（其中 ${unavailableCount} 首因版权问题无法播放）`
  }
  return msg
}

/**
 * 解析歌单
 */
export const parsePlaylist = async () => {
  if (!playlistUrl.value.trim()) {
    message.warning('请输入歌单链接')
    return
  }
  if (!musicApi.validatePlaylistUrl(playlistUrl.value)) {
    message.error('请输入有效的歌单链接')
    return
  }

  startTimer()
  playlistLoading.value = true

  try {
    const result = await musicApi.getPlaylistDetail(playlistUrl.value)
    if (!result.success) throw new Error(result.error)

    const tracks = applyPlaylistResult(result.data)
    notification.open({
      title: '歌单解析完成！',
      message: buildPlaylistNotice(tracks),
      type: 'success',
      duration: 5000
    })
  } catch (error) {
    playlistInfo.value = null
    allTracks.value = []
    totalTracks.value = 0
    showErrorToast(error)
  } finally {
    stopTimer()
    playlistLoading.value = false
  }
}

// ==================== 清空操作 ====================

export const clearMusicResult = () => {
  musicInfo.value = null
  musicUrl.value = ''
}

export const clearPlaylistResult = () => {
  playlistInfo.value = null
  playlistUrl.value = ''
  allTracks.value = []
  totalTracks.value = 0
  currentPage.value = 1
}

export const clearAlbumResult = () => {
  albumInfo.value = null
  albumUrl.value = ''
  allTracks.value = []
  totalTracks.value = 0
  currentPage.value = 1
}

// ==================== 设置示例链接 ====================

/**
 * 设置示例链接
 * @param {string} url 示例链接
 * @param {string} type 链接类型 ('music' | 'playlist' | 'album')
 */
export const setExampleUrl = (url, type) => {
  if (type === 'playlist') playlistUrl.value = url
  else if (type === 'album') albumUrl.value = url
  else musicUrl.value = url
}
