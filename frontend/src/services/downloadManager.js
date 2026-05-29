/**
 * 下载管理器模块
 * 统一管理音乐下载功能
 */

import { logger } from './logger.js'
import { DownloadError } from './errors.js'
import { embedMetadata } from '../services/metadataWriter.js'
import { saveBlob, getMimeByExtension, sanitizeFilename } from './downloadHelper.js'

class DownloadManager {
  constructor() {
    this.maxConcurrent = 3
    this.activeDownloads = new Map()
    this.queue = []
    this.isProcessing = false
  }

  /**
   * 设置最大并发数
   */
  setMaxConcurrent(max) {
    this.maxConcurrent = max
  }

  /**
   * 下载单个音乐
   */
  async download(musicInfo, options = {}) {
    const {
      embedMetadata: shouldEmbedMetadata = true,
      embedLyrics = true,
      filename = null
    } = options

    try {
      logger.info(`开始下载: ${musicInfo.name}`)

      if (!musicInfo.url) {
        throw new DownloadError('音乐 URL 不存在', musicInfo.id)
      }

      const filenameBase = filename || sanitizeFilename(
        `${musicInfo.artist} - ${musicInfo.name}`
      )
      const extension = musicInfo.source?.url?.type || 'flac'
      const mimeType = getMimeByExtension(`.${extension}`)

      const response = await fetch(musicInfo.url)
      if (!response.ok) {
        throw new DownloadError(
          `下载失败: ${response.status} ${response.statusText}`,
          musicInfo.id
        )
      }

      let blob = await response.blob()

      if (shouldEmbedMetadata) {
        const lyrics = embedLyrics ? musicInfo.lrc : null
        blob = await embedMetadata(blob, {
          title: musicInfo.name,
          artist: musicInfo.artist,
          album: musicInfo.album,
          coverUrl: musicInfo.cover,
          lyrics: lyrics,
          fileExtension: extension
        })
      }

      const finalFilename = `${filenameBase}.${extension}`
      saveBlob(blob, finalFilename)

      logger.info(`下载完成: ${finalFilename}`)

      return {
        success: true,
        filename: finalFilename,
        size: blob.size,
        id: musicInfo.id
      }
    } catch (error) {
      logger.error(`下载失败: ${musicInfo.name}`, error)
      throw new DownloadError(
        error.message || '下载失败',
        musicInfo.id,
        error
      )
    }
  }

  /**
   * 批量下载音乐
   */
  async downloadBatch(musicList, options = {}) {
    const results = []
    const concurrency = this.maxConcurrent

    for (let i = 0; i < musicList.length; i += concurrency) {
      const batch = musicList.slice(i, i + concurrency)
      const batchResults = await Promise.allSettled(
        batch.map(music => this.download(music, options))
      )

      for (let j = 0; j < batch.length; j++) {
        const result = batchResults[j]
        if (result.status === 'fulfilled') {
          results.push({
            ...result.value,
            id: batch[j].id,
            name: batch[j].name,
            success: true
          })
        } else {
          results.push({
            id: batch[j].id,
            name: batch[j].name,
            success: false,
            error: result.reason?.message || '下载失败'
          })
        }
      }
    }

    return results
  }

  /**
   * 添加到下载队列
   */
  addToQueue(musicInfo, options = {}) {
    this.queue.push({ musicInfo, options })

    if (!this.isProcessing) {
      this.processQueue()
    }
  }

  /**
   * 处理下载队列
   */
  async processQueue() {
    if (this.isProcessing || this.queue.length === 0) {
      return
    }

    this.isProcessing = true

    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, this.maxConcurrent)
      await Promise.all(
        batch.map(({ musicInfo, options }) =>
          this.download(musicInfo, options).catch(error => ({
            success: false,
            error: error.message
          }))
        )
      )
    }

    this.isProcessing = false
  }

  /**
   * 取消所有下载
   */
  cancelAll() {
    this.queue = []
    this.activeDownloads.forEach((download, id) => {
      download.abort()
    })
    this.activeDownloads.clear()
  }

  /**
   * 获取下载统计
   */
  getStats() {
    return {
      queueLength: this.queue.length,
      activeDownloads: this.activeDownloads.size,
      maxConcurrent: this.maxConcurrent
    }
  }
}

export default new DownloadManager()
export { DownloadManager }
