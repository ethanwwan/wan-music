import { ref } from 'vue'
import { message, notification } from 'ant-design-vue'
import musicApi from '../services/musicApi.js'
import { allTracks, totalTracks, currentPage, displayTracks, updateDisplayTracks } from './paginationManager.js'
import { settings } from './settingsManager.js'

/**
 * 判断歌曲是否无版权
 * @param {Object} track 歌曲对象
 * @returns {Boolean} 是否无版权
 */
export const isTrackUnavailable = (track) => {
  if (!track) return true
  
  // 检查 fee 字段：0=免费, 1=VIP, 4=购买专辑
  const fee = track.fee
  // 检查 privilege 字段
  const privilege = track.privilege || {}
  // 检查 st (status)
  const st = privilege.st !== undefined ? privilege.st : track.st
  // 检查 pl (play level)
  const pl = privilege.pl !== undefined ? privilege.pl : track.pl
  
  // 判断规则：
  // 1. st === -200 (明确无版权)
  // 2. pl === 0 (播放级别0表示不可播放)
  // 3. fee === 1 (VIP歌曲) 或者 fee === 4 (购买专辑)，这里先不处理，保持可播放
  
  if (st === -200 || pl === 0) {
    return true
  }
  
  // 如果没有明确的无版权标志，视为可播放
  return false
}

const getApiVersionLabel = () => {
  const v = settings?.apiVersion
  return v === 'API_V2' ? '接口2' : '接口1'
}
// 解析状态
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
export const albumSearchResults = ref([])
export const artistSearchResults = ref([])

// 移除循环解析模式相关状态

// 计时器相关
export const parseStartTime = ref(0)
export const elapsedTime = ref(0)
let timerInterval = null

/**
 * 启动计时器
 */
const startTimer = () => {
  parseStartTime.value = Date.now()
  elapsedTime.value = 0
  
  timerInterval = setInterval(() => {
    elapsedTime.value = Math.floor((Date.now() - parseStartTime.value) / 1000)
  }, 100)
}

/**
 * 停止计时器
 */
const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

/**
 * 清理计时器
 */
export const cleanupTimer = () => {
  stopTimer()
}

/**
 * 解析音乐信息
 * @param {string} selectedQuality 选择的音质
 * @param {string} mode 当前模式 ('search', 'music', 'playlist', 'album', 'rank')
 */
export const parseMusic = async (selectedQuality, mode = 'music') => {
  if (!musicUrl.value.trim()) {
    message.warning('请输入内容')
    return
  }

  // 搜索模式不需要验证URL格式，直接搜索
  if (mode === 'search') {
    loading.value = true
    try {
      // 只搜索单曲
      const songResult = await musicApi.searchMusic(musicUrl.value)

      musicInfo.value = { name: musicUrl.value }

      // 更新单曲搜索结果，清空其他类型结果
      searchResults.value = songResult.success ? (songResult.data.songs || []) : []
      artistSearchResults.value = []
      playlistSearchResults.value = []
      albumSearchResults.value = []

      if (searchResults.value.length > 0) {
        notification.open({
          title: songResult.fromCache ? '读取缓存成功' : '搜索成功',
          message: `找到 ${searchResults.value.length} 首歌曲${songResult.fromCache ? '（来自缓存）' : ''}`,
          type: 'success'
        })
      } else {
        message.warning('未找到相关结果')
      }
    } catch (error) {
      searchResults.value = []
      artistSearchResults.value = []
      playlistSearchResults.value = []
      albumSearchResults.value = []
      message.error('搜索失败，请稍后重试')
    } finally {
      loading.value = false
    }
    return
  }

  // 歌单模式 - 支持URL解析和名称搜索
  if (mode === 'playlist') {
    // 如果是有效的歌单URL，直接解析歌单详情
    if (musicApi.validatePlaylistUrl(musicUrl.value)) {
      playlistUrl.value = musicUrl.value
      loading.value = true
      try {
        await parsePlaylist()
      } finally {
        loading.value = false
      }
      return
    }
    // 如果不是URL，尝试搜索歌单
    loading.value = true
    try {
      const result = await musicApi.searchPlaylist(musicUrl.value)
      playlistInfo.value = result
      if (result.success && result.data) {
        playlistSearchResults.value = result.data
        notification.open({
          title: result.fromCache ? '读取缓存成功' : '搜索成功',
          message: `找到 ${result.data.length || 0} 个歌单${result.fromCache ? '（来自缓存）' : ''}`,
          type: 'success'
        })
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
    return
  }

  // 专辑模式 - 支持URL解析和名称搜索
  if (mode === 'album') {
    // 如果是有效的专辑URL，直接解析专辑详情
    if (musicApi.validateAlbumUrl(musicUrl.value)) {
      albumUrl.value = musicUrl.value
      loading.value = true
      try {
        await parseAlbum()
      } finally {
        loading.value = false
      }
      return
    }
    // 如果不是URL，尝试搜索专辑
    loading.value = true
    try {
      const result = await musicApi.searchAlbum(musicUrl.value)
      albumInfo.value = result
      if (result.success && result.data) {
        albumSearchResults.value = result.data
        notification.open({
          title: result.fromCache ? '读取缓存成功' : '搜索成功',
          message: `找到 ${result.data.length || 0} 张专辑${result.fromCache ? '（来自缓存）' : ''}`,
          type: 'success'
        })
      } else {
        albumSearchResults.value = []
        message.warning(result.error || '搜索结果为空')
      }
    } catch (error) {
      albumSearchResults.value = []
      message.error('搜索失败，请稍后重试')
    } finally {
      loading.value = false
    }
    return
  }

  // 歌手搜索模式
  if (mode === 'artist') {
    loading.value = true
    try {
      const result = await musicApi.searchArtist(musicUrl.value)
      if (result.success && result.data) {
        artistSearchResults.value = result.data
        notification.open({
          title: result.fromCache ? '读取缓存成功' : '搜索成功',
          message: `找到 ${result.data.length || 0} 位歌手${result.fromCache ? '（来自缓存）' : ''}`,
          type: 'success'
        })
      } else {
        artistSearchResults.value = []
        message.warning(result.error || '搜索结果为空')
      }
    } catch (error) {
      artistSearchResults.value = []
      message.error('搜索失败，请稍后重试')
    } finally {
      loading.value = false
    }
    return
  }

  // 单曲模式 - 支持URL解析和名称搜索
  // 如果是有效的单曲URL，直接解析
  if (musicApi.validateMusicUrl(musicUrl.value)) {
    loading.value = true
    try {
      const result = await musicApi.parseMusicInfo(musicUrl.value, selectedQuality)
      musicInfo.value = result

      const getApiVersionLabel = () => {
        const v = settings?.apiVersion
        switch (v) {
          case 'API_V2':
            return '接口2'
          case 'API_V1':
          default:
            return '接口1'
        }
      }

      notification.open({
        title: '解析成功',
        message: `成功解析歌曲：${result.name} (${result.qualityName}) ${getApiVersionLabel()}`,
        type: 'success'
      })
    } catch (error) {
      // 根据错误类型显示不同的提示信息
      let errorMessage = '解析失败，请检查链接是否正确'
      
      if (error.message && error.message.includes('API服务器暂时不可用')) {
        errorMessage = 'API服务器暂时不可用，请稍后重试。这可能是由于服务器维护或网络问题导致的。'
        message.info({
          message: errorMessage,
          type: 'warning',
          duration: 8000,
          showClose: true
        })
      } else if (error.message && (error.message.includes('付费') || error.message.includes('版权限制'))) {
        errorMessage = '该歌曲为付费或受版权限制，暂无法获取播放链接'
        message.info({
          message: errorMessage,
          type: 'error',
          duration: 6000,
          showClose: true
        })
      } else if (error.message && (error.message.includes('下架') || error.message.includes('无法获取'))) {
        errorMessage = '该歌曲已下架或者无法获取'
        message.info({
          message: errorMessage,
          type: 'error',
          duration: 6000,
          showClose: true
        })
      } else if (error.message && error.message.includes('网络连接失败')) {
        errorMessage = error.message
        message.info({
          message: errorMessage,
          type: 'error',
          duration: 6000,
          showClose: true
        })
      } else {
        message.error(error.message || errorMessage)
      }
    } finally {
      loading.value = false
    }
    return
  }

  // 如果不是URL，尝试搜索歌曲
  loading.value = true
  try {
    const result = await musicApi.searchMusic(musicUrl.value)
    if (result.success && result.data.songs && result.data.songs.length > 0) {
      searchResults.value = result.data.songs
      notification.open({
        title: '搜索成功',
        message: `找到 ${result.data.songs.length} 首相关歌曲`,
        type: 'success'
      })
    } else {
      searchResults.value = []
      message.warning(result.error || '搜索结果为空')
    }
  } catch (error) {
    searchResults.value = []
    message.error('搜索失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 当前解析状态
export const currentParsingTrack = ref(null)
export const parsingProgress = ref({
  currentIndex: 0,
  totalTracks: 0,
  successfulTracks: []
})

/**
 * 解析歌单
 */
export const parsePlaylist = async () => {
  // 直接使用导入的ref对象
  
  if (!playlistUrl.value.trim()) {
    message.warning('请输入歌单链接')
    return
  }

  // 验证歌单链接格式
  if (!musicApi.validatePlaylistUrl(playlistUrl.value)) {
    message.error('请输入有效的网易云音乐歌单链接')
    return
  }

  // 开始计时
  startTimer()

  playlistLoading.value = true
  currentParsingTrack.value = null
  parsingProgress.value = { currentIndex: 0, totalTracks: 0, successfulTracks: [] }
  
  try {
    // 调用 API 获取歌单详情
    const result = await musicApi.getPlaylistDetail(playlistUrl.value)
    
    if (result.success) {
      // 设置数据
      playlistInfo.value = result.data
      // 为每个track初始化parsed字段为false，表示尚未解析
      const tracks = (result.data.tracks || []).map(track => ({
        ...track,
        parsed: false,
        unavailable: isTrackUnavailable(track) // 用API返回的字段直接判断版权
      }))
      allTracks.value = tracks
      
      totalTracks.value = allTracks.value.length
      
      // 重置分页并显示第一页
      currentPage.value = 1
      
      // 立即更新显示第一页
      updateDisplayTracks()
      
      const totalTime = Math.floor((Date.now() - parseStartTime.value) / 1000)
      
      // 统计无版权歌曲数量
      const unavailableCount = tracks.filter(t => t.unavailable).length
      
      let message = `共 ${totalTracks.value} 首歌曲，用时 ${totalTime} 秒 ${getApiVersionLabel()}`
      if (unavailableCount > 0) {
        message += `（其中 ${unavailableCount} 首因版权问题无法播放）`
      }
      
      notification.open({
        title: '歌单解析完成！',
        message: message,
        type: 'success',
        duration: 5000
      })
    } else {
      throw new Error(result.error)
    }
  } catch (error) {
    // 根据错误类型显示不同的提示信息
    let errorMessage = '歌单解析失败，请检查链接是否正确'
    
    if (error.message && error.message.includes('API服务器暂时不可用')) {
      errorMessage = 'API服务器暂时不可用，请稍后重试。这可能是由于服务器维护或网络问题导致的。'
      message.info({
        message: errorMessage,
        type: 'warning',
        duration: 8000,
        showClose: true
      })
    } else if (error.message && error.message.includes('网络请求失败')) {
      errorMessage = error.message
      message.info({
        message: errorMessage,
        type: 'error',
        duration: 6000,
        showClose: true
      })
    } else {
      message.error(error.message || errorMessage)
    }
    
  } finally {
    // 停止计时器
    stopTimer()
    playlistLoading.value = false
    currentParsingTrack.value = null
  }
}

/**
 * 解析专辑
 */
export const parseAlbum = async () => {
  if (!albumUrl.value.trim()) {
    message.warning('请输入专辑链接')
    return
  }

  if (!musicApi.validateAlbumUrl(albumUrl.value)) {
    message.error('请输入有效的网易云音乐专辑链接')
    return
  }

  albumLoading.value = true
  startTimer()

  try {
    const result = await musicApi.getAlbumDetail(albumUrl.value)
    if (result.success) {
      albumInfo.value = result.data
      const tracks = result.data.tracks.map(track => ({ 
        ...track, 
        parsed: false, 
        unavailable: isTrackUnavailable(track) // 用API返回的字段直接判断版权
      }))
      allTracks.value = tracks
      totalTracks.value = allTracks.value.length
      currentPage.value = 1

      // 解析成功后立即更新显示
      updateDisplayTracks()
      
      // 统计无版权歌曲数量
      const unavailableCount = tracks.filter(t => t.unavailable).length
      
      let message = `成功解析专辑：${result.data.name} ${getApiVersionLabel()}`
      if (unavailableCount > 0) {
        message += `（其中 ${unavailableCount} 首因版权问题无法播放）`
      }
      
      notification.open({
        title: '专辑解析成功！',
        message: message,
        type: 'success'
      })
    } else {
      throw new Error(result.error)
    }
  } catch (error) {
    message.error(error.message || '专辑解析失败，请检查链接是否正确')
  } finally {
    stopTimer()
    albumLoading.value = false
  }
}

/**
 * 清空音乐解析结果
 */
export const clearMusicResult = () => {
  musicInfo.value = null
  musicUrl.value = ''
}

/**
 * 清空歌单解析结果
 */
export const clearPlaylistResult = () => {
  playlistInfo.value = null
  playlistUrl.value = ''
  allTracks.value = []
  displayTracks.value = []
  totalTracks.value = 0
  currentPage.value = 1
}

/**
 * 清空专辑解析结果
 */
export const clearAlbumResult = () => {
  albumInfo.value = null
  albumUrl.value = ''
  allTracks.value = []
  displayTracks.value = []
  totalTracks.value = 0
  currentPage.value = 1
}

/**
 * 继续解析下一页（循环解析模式）
 * @param {Function} updateDisplayTracks 更新显示歌曲的回调函数
 */
// 移除循环解析相关导出与逻辑

/**
 * 设置示例链接
 * @param {string} url 示例链接
 * @param {string} type 链接类型 ('music' 或 'playlist' 或 'album')
 */
export const setExampleUrl = (url, type) => {
  if (type === 'playlist') {
    playlistUrl.value = url
  } else if (type === 'album') {
    albumUrl.value = url
  } else {
    musicUrl.value = url
  }
}


