/**
 * 批量下载 Composable
 * 把批量下载请求加入下载队列（异步、不阻塞）
 * 用户在 Drawer 中查看进度、下载 zip、取消任务
 */

import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { downloadQueueStore as queueStore } from '../stores/downloadQueue.js'
import { downloadBatchAsZip } from '../services/musicApi.js'

/**
 * @param {Object} options
 * @param {string} options.playlistName 歌单/任务名
 * @param {Array} options.items 歌曲列表 [{id, name, artist, album, source}]
 * @param {Object} options.settings {selectedQuality, filenameFormat, writeMetadata}
 * @returns {Promise<{task_id, total}>}
 */
export const useBatchDownload = () => {
  const isStarting = ref(false)

  const startBatchDownload = async ({ playlistName = '', items = [], settings = {} }) => {
    if (items.length === 0) {
      throw new Error('没有可下载的歌曲')
    }

    isStarting.value = true
    try {
      const quality = settings.selectedQuality || 'lossless'
      const backendItems = items.map(m => ({
        id: m.id,
        name: m.name,
        artist: m.artist,
        album: m.album,
        source: m.source,
        quality,
        qualityMap: m.qualityMap || {}
      }))
      const backendSettings = {
        writeMetadata: settings.writeMetadata !== false,
        filenameFormat: settings.filenameFormat || 'song-artist',
      }

      // 加入下载队列
      const result = await queueStore.addTask(
        backendItems,
        playlistName || 'playlist',
        backendSettings
      )
      message.success(`已加入下载队列：${items.length} 首歌曲`)
      // 自动打开抽屉，让用户看到进度
      queueStore.openDrawer()
      return result
    } finally {
      isStarting.value = false
    }
  }

  return {
    isStarting,
    startBatchDownload
  }
}
