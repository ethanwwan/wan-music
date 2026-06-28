/**
 * 解析管理
 * 提供搜索/解析音乐的核心状态与函数，
 * 由 App.vue 与 SearchResult.vue 共同消费。
 */

import { ref } from 'vue'
import { message, notification } from 'ant-design-vue'
import musicApi from '../services/musicApi.js'
import { settings } from './settingsManager.js'

// ==================== 状态 ====================

export const loading = ref(false)
export const searchResults = ref([])

// ==================== 搜索/解析 ====================

const notifySearchResult = (count, fromCache = false) => {
  notification.success({
    message: fromCache ? '读取缓存数据成功' : '搜索成功',
    description: fromCache ? `从缓存找到 ${count} 条结果` : `从网络获取 ${count} 条结果`
  })
}

/**
 * 统一搜索：URL 直接解析，单平台关键字搜索
 * @param {string} input 关键词或 URL
 * @param {string} source 数据源
 */
export const parseMusic = async (input, source) => {
  if (!input?.trim()) {
    message.warning('请输入内容')
    return
  }

  loading.value = true
  try {
    const result = await musicApi.unifiedSearch(input, [source || settings.selectedSource || 'netease'])
    if (!result.success) {
      searchResults.value = []
      message.error(`搜索失败：${result.error}`)
      return
    }

    const items = result.data || []
    searchResults.value = items

    if (items.length > 0) {
      notifySearchResult(items.length, result.fromCache)
    } else if (result.error) {
      // 后端有明确错误（如歌单 URL 暂不支持）→ 友好提示用户
      message.warning(result.error)
    } else {
      message.warning('未找到相关结果')
    }
  } catch {
    searchResults.value = []
    message.error('搜索失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
