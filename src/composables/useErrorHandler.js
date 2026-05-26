/**
 * 错误处理 Composable
 * 统一管理错误处理逻辑
 */

import { ElMessage, ElNotification } from 'element-plus'

export function useErrorHandler() {
  const handleApiError = (error, context = '') => {
    console.error(`[API Error] ${context}:`, error)

    const message = error.message || error.msg || '请求失败，请稍后重试'

    ElMessage.error({
      message,
      duration: 3000,
      showClose: true
    })

    return { success: false, error, context }
  }

  const handleNetworkError = (error) => {
    console.error('[Network Error]:', error)

    ElMessage.error({
      message: '网络连接失败，请检查网络设置',
      duration: 4000,
      showClose: true
    })

    return { success: false, error }
  }

  const handleValidationError = (error, field = '') => {
    console.error(`[Validation Error] ${field}:`, error)

    const message = field ? `${field}: ${error.message}` : error.message

    ElMessage.warning({
      message,
      duration: 3000,
      showClose: true
    })

    return { success: false, error }
  }

  const handleDownloadError = (error, filename = '') => {
    console.error('[Download Error]:', error)

    const message = filename 
      ? `下载失败: ${filename}` 
      : '下载失败，请稍后重试'

    ElMessage.error({
      message,
      duration: 4000,
      showClose: true
    })

    return { success: false, error }
  }

  const showSuccess = (message = '操作成功') => {
    ElMessage.success({
      message,
      duration: 2000,
      showClose: true
    })
  }

  const showWarning = (message = '警告') => {
    ElMessage.warning({
      message,
      duration: 3000,
      showClose: true
    })
  }

  const showInfo = (message = '提示') => {
    ElMessage.info({
      message,
      duration: 2000,
      showClose: true
    })
  }

  const notifySuccess = (title = '成功', message = '') => {
    ElNotification.success({
      title,
      message,
      duration: 3000
    })
  }

  const notifyError = (title = '错误', message = '') => {
    ElNotification.error({
      title,
      message,
      duration: 5000
    })
  }

  const notifyWarning = (title = '警告', message = '') => {
    ElNotification.warning({
      title,
      message,
      duration: 4000
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
