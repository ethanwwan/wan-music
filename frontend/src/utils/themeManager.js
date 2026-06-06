import { ref, watch } from 'vue'

// 主题状态
const isDark = ref(false)
// 当前自定义主题色
let currentThemeColor = null

/**
 * 获取自定义主题色
 */
const getCustomThemeColor = () => {
  if (currentThemeColor) {
    return currentThemeColor
  }
  if (typeof window !== 'undefined' && window.__currentThemeColor) {
    return window.__currentThemeColor
  }
  const saved = localStorage.getItem('themeColor')
  if (saved) {
    const colors = {
      'blue': '#0057c2',
      'red': '#e53935',
      'purple': '#8e24aa',
      'green': '#43a047',
      'orange': '#fb8c00',
      'cyan': '#00acc1'
    }
    return colors[saved] || null
  }
  return null
}

/**
 * 应用主题变量到 DOM
 * @param {boolean} dark 是否为深色主题
 */
const applyThemeVariables = (dark) => {
  if (typeof document === 'undefined') return
  
  const root = document.documentElement
  const customColor = getCustomThemeColor()
  
  if (dark) {
    const primaryColor = customColor || '#60a5fa'
    root.style.setProperty('--color-primary', primaryColor)
    root.style.setProperty('--color-primary-hover', customColor || '#3b82f6')
    root.style.setProperty('--color-primary-light', customColor ? `rgba(${hexToRgb(customColor).r}, ${hexToRgb(customColor).g}, ${hexToRgb(customColor).b}, 0.15)` : 'rgba(96, 165, 250, 0.15)')
    root.style.setProperty('--color-primary-dim', customColor || '#3b82f6')
    
    root.style.setProperty('--color-surface', '#0f0f0f')
    root.style.setProperty('--color-surface-white', '#1a1a1a')
    root.style.setProperty('--color-surface-variant', '#2a2a2a')
    root.style.setProperty('--color-surface-container', '#1e1e1e')
    root.style.setProperty('--color-surface-container-low', '#161616')
    root.style.setProperty('--color-surface-container-high', '#252525')
    root.style.setProperty('--color-surface-dim', '#0a0a0a')
    root.style.setProperty('--color-surface-white-rgb', '26, 26, 26')
    root.style.setProperty('--color-surface-dark-rgb', '10, 10, 10')
    
    root.style.setProperty('--color-on-surface', '#ffffff')
    root.style.setProperty('--color-on-surface-variant', '#d4d4d4')
    root.style.setProperty('--color-secondary', '#c0c0c0')
    root.style.setProperty('--color-text-muted', '#a0a0a0')
    root.style.setProperty('--color-outline', '#505050')
    
    root.style.setProperty('--color-border-subtle', '#2a2a2a')
    root.style.setProperty('--color-outline-variant', '#3a3a3a')
    
    root.style.setProperty('--color-background', '#0a0a0a')
    root.style.setProperty('--color-notice-bg', '#1e3a5f')
    root.style.setProperty('--color-notice-border', primaryColor)
    
    root.style.setProperty('--app-bg', '#0a0a0a')
    root.style.setProperty('--app-header-bg', 'rgba(10, 10, 10, 0.98)')
    root.style.setProperty('--app-card-bg', '#141414')
    root.style.setProperty('--app-text-primary', '#ffffff')
    root.style.setProperty('--app-text-secondary', '#e0e0e0')
    root.style.setProperty('--app-text-muted', '#b0b0b0')
    root.style.setProperty('--app-border-color', '#2a2a2a')
    root.style.setProperty('--app-shadow', '0 4px 20px rgba(0, 0, 0, 0.5)')
  } else {
    const primaryColor = customColor || '#0057c2'
    root.style.setProperty('--color-primary', primaryColor)
    root.style.setProperty('--color-primary-hover', customColor || '#004398')
    root.style.setProperty('--color-primary-light', customColor ? `rgba(${hexToRgb(customColor).r}, ${hexToRgb(customColor).g}, ${hexToRgb(customColor).b}, 0.1)` : '#ebf5ff')
    root.style.setProperty('--color-primary-dim', customColor || '#afc6ff')
    
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
    root.style.setProperty('--color-notice-bg', customColor ? `rgba(${hexToRgb(customColor).r}, ${hexToRgb(customColor).g}, ${hexToRgb(customColor).b}, 0.1)` : '#e7f3ff')
    root.style.setProperty('--color-notice-border', customColor ? `rgba(${hexToRgb(customColor).r}, ${hexToRgb(customColor).g}, ${hexToRgb(customColor).b}, 0.3)` : '#d1e9ff')
    
    root.style.setProperty('--app-bg', '#f0f2f5')
    root.style.setProperty('--app-header-bg', 'rgba(255, 255, 255, 0.95)')
    root.style.setProperty('--app-card-bg', '#FFFFFF')
    root.style.setProperty('--app-text-primary', '#333333')
    root.style.setProperty('--app-text-secondary', '#666666')
    root.style.setProperty('--app-text-muted', '#999999')
    root.style.setProperty('--app-border-color', '#E8E8E8')
    root.style.setProperty('--app-shadow', '0 4px 16px rgba(0, 0, 0, 0.08)')
  }
}

/**
 * 十六进制颜色转RGB
 */
const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : { r: 0, g: 87, b: 194 }
}

/**
 * 应用主题（带动画效果）
 * @param {boolean} dark 是否为深色主题
 */
export const applyTheme = (dark) => {
  if (typeof document === 'undefined') return
  
  const body = document.body
  
  // 添加主题切换动画类
  body.classList.add('theme-switching')
  
  // 立即应用主题变量
  applyThemeVariables(dark)
  
  // 切换 dark class
  setTimeout(() => {
    if (dark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, 50)
  
  // 动画完成后移除动画类
  setTimeout(() => {
    body.classList.remove('theme-switching')
  }, 600)
}

/**
 * 切换主题
 */
export const toggleTheme = () => {
  isDark.value = !isDark.value
  applyTheme(isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

/**
 * 设置主题
 * @param {string | boolean} theme 主题类型：'dark' | 'light' | boolean
 */
export const setTheme = (theme) => {
  if (typeof theme === 'boolean') {
    isDark.value = theme
    applyTheme(isDark.value)
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  } else if (theme === 'dark' || theme === 'light') {
    isDark.value = theme === 'dark'
    applyTheme(isDark.value)
    localStorage.setItem('theme', theme)
  } else if (typeof theme === 'string') {
    isDark.value = false
    applyTheme(false)
    setCustomThemeColor(theme)
    localStorage.setItem('theme', 'light')
    localStorage.setItem('themeColor', theme)
  }
}

/**
 * 设置自定义主题色
 * @param {string} color 主题色值
 */
const setCustomThemeColor = (color) => {
  if (typeof document !== 'undefined' && color) {
    document.documentElement.style.setProperty('--color-primary', color)
    document.documentElement.style.setProperty('--app-primary', color)
    currentThemeColor = color
  }
}

// 监听主题变化并同步
watch(isDark, (newVal) => {
  if (typeof document !== 'undefined') {
    applyThemeVariables(newVal)
  }
})

// 导出主题状态
export { isDark }

// 初始化主题（基于本地存储，支持跟随系统）
export const initThemeFromLocalStorage = () => {
  const savedThemeMode = typeof window !== 'undefined' ? localStorage.getItem('themeMode') : null
  const savedTheme = typeof window !== 'undefined' ? localStorage.getItem('theme') : null
  const savedThemeColor = typeof window !== 'undefined' ? localStorage.getItem('themeColor') : null
  
  let targetTheme = 'light'
  
  if (savedThemeMode) {
    if (savedThemeMode === 'auto') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      targetTheme = prefersDark ? 'dark' : 'light'
      
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (localStorage.getItem('themeMode') === 'auto') {
          isDark.value = e.matches
          applyTheme(e.matches)
        }
      })
    } else {
      targetTheme = savedThemeMode
    }
  } else if (savedTheme) {
    targetTheme = savedTheme
  }
  
  isDark.value = targetTheme === 'dark'
  applyTheme(isDark.value)
  
  if (savedThemeColor) {
    setCustomThemeColor(savedThemeColor)
  }
}

// 设置主题模式（auto/dark/light）
export const setThemeMode = (mode) => {
  localStorage.setItem('themeMode', mode)
  
  if (mode === 'auto') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDark.value = prefersDark
    applyTheme(prefersDark)
  } else {
    isDark.value = mode === 'dark'
    applyTheme(isDark.value)
  }
}

// 获取当前主题模式
export const getThemeMode = () => {
  return localStorage.getItem('themeMode') || 'light'
}