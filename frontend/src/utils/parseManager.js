/**
 * 解析管理
 * 提供搜索/解析音乐、歌单的核心状态与函数，
 * 由 App.vue 与 SearchResult.vue 共同消费。
 */

import { ref } from 'vue'
import { message, notification } from 'ant-design-vue'
import musicApi from '../services/musicApi.js'
import { settings } from './settingsManager.js'

// ==================== 解析结果状态 ====================

export const loading = ref(false)
/** tab 切换专用 loading（与搜索按钮独立） */
export const tabLoading = ref(false)

export const searchResults = ref([])
export const playlistSearchResults = ref([])
/** 后端搜索返回的警告（如 'playlist_search_unsupported'，表示某平台不支持歌单搜索） */
export const searchWarnings = ref([])

// ==================== 搜索/解析 ====================

/** 通知搜索结果（统一通知格式：message + description） */
const notifySearchResult = (count, fromCache = false) => {
  notification.success({
    message: fromCache ? '读取缓存数据成功' : '搜索成功',
    description: fromCache ? `从缓存找到 ${count} 条结果` : `从网络获取 ${count} 条结果`
  })
}

/**
 * 统一搜索
 * @param {string} keyword 输入内容（URL 或关键词）
 * @param {number} searchType 1=只搜歌曲 / 2=只搜歌单
 * @param {Array<string>} sources
 * @param {boolean} fromButton true=点击搜索按钮（影响 loading 状态）/ false=tab 切换
 */
const doSearch = async (keyword, searchType, sources, fromButton) => {
  const setLoading = fromButton ? (v) => { loading.value = v } : (v) => { tabLoading.value = v }
  setLoading(true)
  try {
    const result = await musicApi.unifiedSearch(keyword, searchType, sources, settings.selectedQuality || 'lossless')
    const data = result.success ? result.data : { type: searchType, songs: [], playlists: [], warnings: [] }
    searchWarnings.value = data.warnings || []

    if (fromButton || searchType === 1) searchResults.value = data.songs || []
    if (fromButton || searchType === 2) playlistSearchResults.value = data.playlists || []

    if (fromButton) {
      const totalCount = (data.songs?.length || 0) + (data.playlists?.length || 0)
      if (totalCount > 0) {
        notifySearchResult(totalCount, result.fromCache)
      } else if (!(searchType === 2 && searchWarnings.value.includes('playlist_search_unsupported'))) {
        // 该情况由 UI 展示专门提示，这里不再通用 warn
        message.warning('未找到相关结果')
      }
    }
  } catch {
    if (fromButton) {
      searchResults.value = []
      playlistSearchResults.value = []
      message.error('搜索失败，请稍后重试')
    } else {
      message.error('加载失败，请稍后重试')
    }
  } finally {
    setLoading(false)
  }
}

/**
 * 点击搜索按钮时调用（影响 loading 状态 + 通知用户）
 * @param {string} keyword
 * @param {Array<string>} sources
 * @param {number} searchType
 */
export const parseMusic = (keyword, sources = ['netease'], searchType = 1) =>
  doSearch(keyword, searchType, sources, true)

/**
 * tab 切换时调用：只更新对应 tab 的数据，不影响搜索按钮的 loading
 * @param {string} keyword
 * @param {Array<string>} sources
 * @param {number} searchType 1=歌曲 / 2=歌单
 */
export const searchByTab = (keyword, sources, searchType) => {
  if (!keyword?.trim()) {
    message.warning('请输入内容')
    return
  }
  return doSearch(keyword, searchType, sources, false)
}
