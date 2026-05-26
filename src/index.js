/**
 * 应用入口和模块导出
 * 统一管理所有核心模块的导入
 */

// 配置模块
export { APP_CONFIG, ConfigManager, default as config } from './config/index.js'

// 日志模块
export { logger, Logger, LOG_LEVELS } from './utils/logger.js'

// 错误处理模块
export {
  APIError,
  NetworkError,
  DownloadError,
  ValidationError,
  ParseError,
  CookieError,
  MetadataError,
  handleError,
  formatErrorMessage
} from './utils/errors.js'

// Cookie 管理模块
export { CookieManager } from './utils/cookieManager.js'

// API 服务
export { default as neteaseApi, NeteaseAPI } from './services/neteaseApi.js'
export {
  parseUrl,
  getMusicUrl,
  getMusicInfo,
  parseSongInfo,
  parsePlaylistInfo,
  parseAlbumInfo,
  batchGetMusicInfo,
  downloadMusic,
  batchDownloadMusic,
  getLyrics,
  getQualityLevels,
  getQualityLabel,
  QUALITY_LEVELS
} from './services/musicApi.js'

// 下载管理
export { default as downloadManager, DownloadManager } from './services/downloadManager.js'

// 元数据写入
export { embedMetadata } from './services/metadataWriter.js'

// 工具函数
export { saveBlob, getMimeByExtension, sanitizeFilename } from './utils/downloadHelper.js'
export { settings } from './utils/settingsManager.js'
