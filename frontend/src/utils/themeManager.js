import { ref } from 'vue'

// 主题状态
const isDark = ref(false)
// 当前自定义主题色
let currentThemeColor = null

/**
 * 应用主题（带动画效果）
 * @param {boolean} dark 是否为深色主题
 */
export const applyTheme = (dark) => {
  if (typeof document !== 'undefined') {
    const body = document.body
    
    // 添加主题切换动画类
    body.classList.add('theme-switching')
    
    // 延迟应用主题，让动画效果更自然
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
    // 如果是自定义主题色，设置为浅色主题并应用自定义颜色
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
    currentThemeColor = color
  }
}

// 导出主题状态
export { isDark }

// 初始化主题（基于本地存储，支持跟随系统）
export const initThemeFromLocalStorage = () => {
  const savedThemeMode = typeof window !== 'undefined' ? localStorage.getItem('themeMode') : null
  const savedTheme = typeof window !== 'undefined' ? localStorage.getItem('theme') : null
  const savedThemeColor = typeof window !== 'undefined' ? localStorage.getItem('themeColor') : null
  
  // 如果有主题模式设置
  if (savedThemeMode) {
    if (savedThemeMode === 'auto') {
      // 跟随系统
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      isDark.value = prefersDark
      applyTheme(prefersDark)
      
      // 监听系统主题变化
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (localStorage.getItem('themeMode') === 'auto') {
          isDark.value = e.matches
          applyTheme(e.matches)
        }
      })
    } else {
      // 手动设置的主题
      isDark.value = savedThemeMode === 'dark'
      applyTheme(isDark.value)
    }
  } else if (savedTheme) {
    // 兼容旧版本
    isDark.value = savedTheme === 'dark'
    applyTheme(isDark.value)
  } else {
    // 默认亮色
    isDark.value = false
    applyTheme(false)
  }
  
  // 恢复自定义主题色
  if (savedThemeColor) {
    setCustomThemeColor(savedThemeColor)
  }
}