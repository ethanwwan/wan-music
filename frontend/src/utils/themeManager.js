/**
 * 主题管理：当前仅使用一套浅色主题 token，
 * applyTheme 把全部 CSS 变量写入 :root，
 * 让 App.vue 与 global.css 共用同一套色板。
 */

/** 默认主题色：蓝色 #0057c2 */
export const DEFAULT_THEME_COLOR = '#0057c2'

export const applyTheme = () => {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  const color = DEFAULT_THEME_COLOR
  const r = 0, g = 87, b = 194  // #0057c2 的 RGB 解析结果

  root.style.setProperty('--color-primary', color)
  root.style.setProperty('--color-primary-hover', color)
  root.style.setProperty('--color-primary-light', `rgba(${r}, ${g}, ${b}, 0.1)`)
  root.style.setProperty('--color-primary-dim', color)

  root.style.setProperty('--color-surface', '#f9f9f9')
  root.style.setProperty('--color-surface-white', '#ffffff')
  root.style.setProperty('--color-surface-variant', '#e2e2e2')
  root.style.setProperty('--color-surface-container', '#eeeeee')
  root.style.setProperty('--color-surface-container-low', '#f3f3f3')
  root.style.setProperty('--color-surface-container-high', '#e8e8e8')
  root.style.setProperty('--color-surface-dim', '#dadada')
  root.style.setProperty('--color-surface-white-rgb', '255, 255, 255')
  root.style.setProperty('--color-surface-dark-rgb', '30, 30, 30')

  root.style.setProperty('--color-on-surface', '#1b1b1b')
  root.style.setProperty('--color-on-surface-variant', '#414755')
  root.style.setProperty('--color-secondary', '#5d5f5f')
  root.style.setProperty('--color-text-muted', '#595959')
  root.style.setProperty('--color-outline', '#727786')

  root.style.setProperty('--color-border-subtle', '#e5e5e5')
  root.style.setProperty('--color-outline-variant', '#c1c6d7')

  root.style.setProperty('--color-background', '#f5f5f5')
  root.style.setProperty('--color-notice-bg', `rgba(${r}, ${g}, ${b}, 0.1)`)
  root.style.setProperty('--color-notice-border', `rgba(${r}, ${g}, ${b}, 0.3)`)

  document.documentElement.classList.remove('dark')
}

/** 启动入口：保留命名以兼容 App.vue 的现有调用 */
export const initThemeFromLocalStorage = applyTheme
