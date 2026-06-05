/**
 * 错误处理 Composable
 * 统一管理错误处理逻辑
 */

import { message, notification } from 'ant-design-vue'

export function useErrorHandler() {
  const handleApiError = (error, context = '') => {
    console.error(`[API Error] ${context}:`, error)

    const msg = error.message || error.msg || '请求失败，请稍后重试'

    message.error(msg)

    return { success: false, error, context }
  }

  const handleNetworkError = (error) => {
    console.error('[Network Error]:', error)

    message.error('网络连接失败，请检查网络设置')

    return { success: false, error }
  }

  const handleValidationError = (error, field = '') => {
    console.error(`[Validation Error] ${field}:`, error)

    const msg = field ? `${field}: ${error.message}` : error.message

    message.warning(msg)

    return { success: false, error }
  }

  const handleDownloadError = (error, filename = '') => {
    console.error('[Download Error]:', error)

    const msg = filename 
      ? `下载失败: ${filename}` 
      : '下载失败，请稍后重试'

    message.error(msg)

    return { success: false, error }
  }

  const showSuccess = (msg = '操作成功') => {
    message.success(msg)
  }

  const showWarning = (msg = '警告') => {
    message.warning(msg)
  }

  const showInfo = (msg = '提示') => {
    message.info(msg)
  }

  const notifySuccess = (title = '成功', msg = '') => {
    notification.success({
      message: title,
      description: msg
    })
  }

  const notifyError = (title = '错误', msg = '') => {
    notification.error({
      message: title,
      description: msg
    })
  }

  const notifyWarning = (title = '警告', msg = '') => {
    notification.warning({
      message: title,
      description: msg
    })
  }

  return {
    handleApiError,
    handleNetworkError,
    handleValidationError,
    handleDownloadError,
    showSuccess,
    showWarning,
    showInfo,
    notifySuccess,
    notifyError,
    notifyWarning
  }
}

export default useErrorHandler