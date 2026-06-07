import { ref } from 'vue'

const isDark = ref(false)

const themeColors = {
  'blue': '#0057c2',
  'red': '#e53935',
  'purple': '#8e24aa',
  'green': '#43a047',
  'orange': '#fb8c00',
  'cyan': '#00acc1'
}

const getCustomThemeColor = () => {
  const saved = localStorage.getItem('themeColor')
  if (saved && themeColors[saved]) {
    return themeColors[saved]
  }
  return themeColors['blue']
}

const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : { r: 0, g: 87, b: 194 }
}

export const applyTheme = () => {
  if (typeof document === 'undefined') return
  
  const root = document.documentElement
  const customColor = getCustomThemeColor()
  
  root.style.setProperty('--color-primary', customColor)
  root.style.setProperty('--color-primary-hover', customColor)
  root.style.setProperty('--color-primary-light', `rgba(${hexToRgb(customColor).r}, ${hexToRgb(customColor).g}, ${hexToRgb(customColor).b}, 0.1)`)
  root.style.setProperty('--color-primary-dim', customColor)
  
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
  root.style.setProperty('--color-notice-bg', `rgba(${hexToRgb(customColor).r}, ${hexToRgb(customColor).g}, ${hexToRgb(customColor).b}, 0.1)`)
  root.style.setProperty('--color-notice-border', `rgba(${hexToRgb(customColor).r}, ${hexToRgb(customColor).g}, ${hexToRgb(customColor).b}, 0.3)`)
  
  root.style.setProperty('--app-bg', '#f0f2f5')
  root.style.setProperty('--app-header-bg', 'rgba(255, 255, 255, 0.95)')
  root.style.setProperty('--app-card-bg', '#FFFFFF')
  root.style.setProperty('--app-text-primary', '#333333')
  root.style.setProperty('--app-text-secondary', '#666666')
  root.style.setProperty('--app-text-muted', '#999999')
  root.style.setProperty('--app-border-color', '#E8E8E8')
  root.style.setProperty('--app-shadow', '0 4px 16px rgba(0, 0, 0, 0.08)')
  
  document.documentElement.classList.remove('dark')
}

export const setTheme = async (theme) => {
  if (typeof theme === 'string' && themeColors[theme]) {
    localStorage.setItem('themeColor', theme)
    applyTheme()
  }
}

export const toggleTheme = () => {
  console.warn('toggleTheme is deprecated, use setTheme with color instead')
}

export const initThemeFromLocalStorage = () => {
  applyTheme()
}

export { isDark }
