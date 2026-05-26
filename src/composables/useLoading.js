/**
 * Loading 状态管理 Composable
 * 统一管理 Loading 状态
 */

import { ElLoading } from 'element-plus'

export function useLoading() {
  let loadingInstance = null

  const show = (options = {}) => {
    if (loadingInstance) {
      loadingInstance.close()
    }

    const defaultOptions = {
      lock: true,
      text: '加载中...',
      background: 'rgba(0, 0, 0, 0.7)'
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
