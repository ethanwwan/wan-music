/**
 * Cookie 管理模块
 * 负责管理网易云音乐的登录状态
 */

const COOKIE_KEY = 'netease_music_cookie'
const COOKIE_EXPIRY_KEY = 'netease_music_cookie_expiry'

export class CookieManager {
  constructor() {
    this.cookieKey = COOKIE_KEY
    this.expiryKey = COOKIE_EXPIRY_KEY
  }

  /**
   * 获取 Cookie
   */
  getCookie() {
    return localStorage.getItem(this.cookieKey)
  }

  /**
   * 设置 Cookie
   */
  setCookie(cookie) {
    localStorage.setItem(this.cookieKey, cookie)
    const expiry = new Date()
    expiry.setDate(expiry.getDate() + 30)
    localStorage.setItem(this.expiryKey, expiry.toISOString())
  }

  /**
   * 清除 Cookie
   */
  clearCookie() {
    localStorage.removeItem(this.cookieKey)
    localStorage.removeItem(this.expiryKey)
  }

  /**
   * 检查 Cookie 是否有效
   */
  isCookieValid() {
    const cookie = this.getCookie()
    if (!cookie) return false

    const expiryStr = localStorage.getItem(this.expiryKey)
    if (!expiryStr) return false

    const expiry = new Date(expiryStr)
    return expiry > new Date()
  }

  /**
   * 获取 Cookie 信息
   */
  getCookieInfo() {
    const cookie = this.getCookie()
    const expiryStr = localStorage.getItem(this.expiryKey)

    const info = {
      exists: !!cookie,
      count: cookie ? cookie.split(';').length : 0,
      expiry: expiryStr ? new Date(expiryStr).toLocaleString() : null,
      isValid: this.isCookieValid()
    }

    if (cookie) {
      const cookies = cookie.split('; ')
      const importantCookies = ['NMTID', 'MUSIC_U', 'appver']
      const present = []
      const missing = []

      for (const name of importantCookies) {
        const found = cookies.some(c => c.startsWith(`${name}=`))
        if (found) {
          present.push(name)
        } else {
          missing.push(name)
        }
      }

      info.presentCookies = present
      info.missingCookies = missing
    }

    return info
  }

  /**
   * 备份 Cookie
   */
  backupCookie() {
    const cookie = this.getCookie()
    if (cookie) {
      const backupKey = `${this.cookieKey}_backup_${Date.now()}`
      localStorage.setItem(backupKey, cookie)
      return backupKey
    }
    return null
  }

  /**
   * 验证 Cookie
   */
  validateCookie() {
    const cookie = this.getCookie()
    if (!cookie) {
      return { valid: false, message: 'Cookie 不存在' }
    }

    const cookies = cookie.split('; ')
    const hasMusicU = cookies.some(c => c.startsWith('MUSIC_U='))
    const hasNMTID = cookies.some(c => c.startsWith('NMTID='))

    if (!hasMusicU) {
      return { valid: false, message: '缺少必要的 MUSIC_U Cookie' }
    }

    if (!hasNMTID) {
      return { valid: false, message: '缺少必要的 NMTID Cookie' }
    }

    return { valid: true, message: 'Cookie 有效' }
  }
}

export default new CookieManager()
