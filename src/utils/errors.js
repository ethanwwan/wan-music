/**
 * 异常处理模块
 * 定义应用自定义异常
 */

export class APIError extends Error {
  constructor(message, code = null, status = null) {
    super(message)
    this.name = 'APIError'
    this.code = code
    this.status = status
  }
}

export class NetworkError extends Error {
  constructor(message, originalError = null) {
    super(message)
    this.name = 'NetworkError'
    this.originalError = originalError
  }
}

export class DownloadError extends Error {
  constructor(message, songId = null, originalError = null) {
    super(message)
    this.name = 'DownloadError'
    this.songId = songId
    this.originalError = originalError
  }
}

export class ValidationError extends Error {
  constructor(message, field = null) {
    super(message)
    this.name = 'ValidationError'
    this.field = field
  }
}

export class ParseError extends Error {
  constructor(message, url = null) {
    super(message)
    this.name = 'ParseError'
    this.url = url
  }
}

export class CookieError extends Error {
  constructor(message, code = null) {
    super(message)
    this.name = 'CookieError'
    this.code = code
  }
}

export class MetadataError extends Error {
  constructor(message, fileType = null) {
    super(message)
    this.name = 'MetadataError'
    this.fileType = fileType
  }
}

/**
 * 全局异常处理器
 */
export function handleError(error, context = '') {
  const errorInfo = {
    name: error.name || 'Error',
    message: error.message || '未知错误',
    stack: error.stack,
    context,
    timestamp: new Date().toISOString()
  }

  if (error instanceof APIError) {
    errorInfo.code = error.code
    errorInfo.status = error.status
  }

  if (error instanceof DownloadError) {
    errorInfo.songId = error.songId
  }

  if (error instanceof ValidationError) {
    errorInfo.field = error.field
  }

  console.error('应用错误:', errorInfo)

  return errorInfo
}

/**
 * 错误信息格式化
 */
export function formatErrorMessage(error) {
  if (error instanceof APIError) {
    return `API 错误: ${error.message}`
  }

  if (error instanceof NetworkError) {
    return `网络错误: ${error.message}`
  }

  if (error instanceof DownloadError) {
    return `下载错误: ${error.message}`
  }

  if (error instanceof ValidationError) {
    return `验证错误: ${error.message}`
  }

  if (error instanceof ParseError) {
    return `解析错误: ${error.message}`
  }

  if (error instanceof CookieError) {
    return `Cookie 错误: ${error.message}`
  }

  if (error instanceof MetadataError) {
    return `元数据错误: ${error.message}`
  }

  return error.message || '未知错误'
}

export default {
  APIError,
  NetworkError,
  DownloadError,
  ValidationError,
  ParseError,
  CookieError,
  MetadataError,
  handleError,
  formatErrorMessage
}
