/**
 * 日志管理模块
 * 支持开发/生产环境分级日志
 */

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
}

const LEVEL_NAMES = {
  [LOG_LEVELS.DEBUG]: 'DEBUG',
  [LOG_LEVELS.INFO]: 'INFO',
  [LOG_LEVELS.WARN]: 'WARN',
  [LOG_LEVELS.ERROR]: 'ERROR'
}

class Logger {
  constructor() {
    this.level = LOG_LEVELS.DEBUG
    this.prefix = ''
    this.enabled = true
  }

  /**
   * 设置日志级别
   * @param {string|number} level - 日志级别
   */
  setLevel(level) {
    if (typeof level === 'string') {
      const upperLevel = level.toUpperCase()
      this.level = LOG_LEVELS[upperLevel] ?? LOG_LEVELS.INFO
    } else {
      this.level = level
    }
  }

  /**
   * 设置日志前缀
   * @param {string} prefix
   */
  setPrefix(prefix) {
    this.prefix = prefix
  }

  /**
   * 启用/禁用日志
   * @param {boolean} enabled
   */
  setEnabled(enabled) {
    this.enabled = enabled
  }

  /**
   * 格式化日志消息
   */
  format(level, ...args) {
    const timestamp = new Date().toISOString()
    const levelName = LEVEL_NAMES[level]
    const prefix = this.prefix ? `[${this.prefix}]` : ''
    return `[${timestamp}] [${levelName}]${prefix}`
  }

  /**
   * Debug 级别日志
   */
  debug(...args) {
    if (this.enabled && this.level <= LOG_LEVELS.DEBUG) {
      console.debug(this.format(LOG_LEVELS.DEBUG), ...args)
    }
  }

  /**
   * Info 级别日志
   */
  info(...args) {
    if (this.enabled && this.level <= LOG_LEVELS.INFO) {
      console.info(this.format(LOG_LEVELS.INFO), ...args)
    }
  }

  /**
   * Warn 级别日志
   */
  warn(...args) {
    if (this.enabled && this.level <= LOG_LEVELS.WARN) {
      console.warn(this.format(LOG_LEVELS.WARN), ...args)
    }
  }

  /**
   * Error 级别日志
   */
  error(...args) {
    if (this.enabled && this.level <= LOG_LEVELS.ERROR) {
      console.error(this.format(LOG_LEVELS.ERROR), ...args)
    }
  }

  /**
   * 创建子日志器
   * @param {string} prefix
   */
  createChild(prefix) {
    const child = new Logger()
    child.level = this.level
    child.prefix = prefix
    child.enabled = this.enabled
    return child
  }
}

const logger = new Logger()

const isDev = import.meta.env.DEV

if (!isDev) {
  logger.setLevel(LOG_LEVELS.WARN)
}

export { logger, Logger, LOG_LEVELS }
export default logger
