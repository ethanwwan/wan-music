/**
 * Loading 状态管理 Composable
 * 统一管理 Loading 状态
 */

import { Spin } from 'ant-design-vue'
import { createVNode, render } from 'vue'

export function useLoading() {
  let loadingInstance = null

  const show = (options = {}) => {
    if (loadingInstance) {
      hide()
    }

    const { text = '加载中...', fullscreen = false, background } = options

    const container = fullscreen 
      ? document.body 
      : document.createElement('div')
    
    const spinNode = createVNode(Spin, {
      tip: text,
      size: 'large'
    })

    render(spinNode, container)
    
    if (!fullscreen) {
      const el = container.firstChild
      el.style.position = 'absolute'
      el.style.top = '50%'
      el.style.left = '50%'
      el.style.transform = 'translate(-50%, -50%)'
      el.style.zIndex = 1000
    }

    loadingInstance = {
      close: () => {
        if (spinNode.component?.ctx) {
          render(null, container)
        }
        if (!fullscreen && container.parentNode) {
          container.parentNode.removeChild(container)
        }
        loadingInstance = null
      },
      $el: container.firstChild
    }

    return loadingInstance
  }

  const hide = () => {
    if (loadingInstance) {
      loadingInstance.close()
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