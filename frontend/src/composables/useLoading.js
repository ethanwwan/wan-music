/**
 * Loading 状态管理 Composable
 * 统一管理 Loading 状态
 */

import { ElLoading } from 'element-plus'
import { isDark } from '../utils/themeManager'

export function useLoading() {
  let loadingInstance = null

  const show = (options = {}) => {
    if (loadingInstance) {
      loadingInstance.close()
    }

    const defaultOptions = {
      lock: true,
      text: '加载中...',
      background: isDark.value ? 'rgba(18, 18, 18, 0.9)' : 'rgba(255, 255, 255, 0.9)'
    }

    loadingInstance = ElLoading.service({
      ...defaultOptions,
      ...options
    })

    return loadingInstance
  }

  const hide = () => {
    if (loadingInstance) {
      loadingInstance.close()
      loadingInstance = null
    }
  }

  const showWithText = (text, options = {}) => {
    return show({ text, ...options })
  }

  const showFullScreen = (text = '加载中...') => {
    return show({ fullscreen: true, text })
  }

  return {
    show,
    hide,
    showWithText,
    showFullScreen,
    loadingInstance: () => loadingInstance
  }
}

export default useLoading
