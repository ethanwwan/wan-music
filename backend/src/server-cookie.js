/**
 * Cookie管理器
 * 用于读取和管理网易云音乐Cookie
 */

import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

class CookieManager {
  constructor(cookieFilePath = null) {
    this.cookieFilePath = cookieFilePath || path.join(__dirname, '..', 'cookie.txt')
    this.cookies = null
    this.lastRead = null
  }

  /**
   * 读取Cookie文件
   */
  readCookieFile() {
    try {
      if (!fs.existsSync(this.cookieFilePath)) {
        console.warn(`Cookie文件不存在: ${this.cookieFilePath}`)
        return null
      }

      const content = fs.readFileSync(this.cookieFilePath, 'utf-8').trim()

      if (!content) {
        console.warn('Cookie文件为空')
        return null
      }

      this.cookies = this.parseCookieString(content)
      this.lastRead = Date.now()

      console.log(`✅ 成功读取Cookie，共 ${Object.keys(this.cookies).length} 个字段`)
      return this.cookies
    } catch (error) {
      console.error('读取Cookie文件失败:', error.message)
      return null
    }
  }

  /**
   * 解析Cookie字符串
   */
  parseCookieString(cookieString) {
    if (!cookieString || !cookieString.trim()) {
      return {}
    }

    const cookies = {}
    const cookieStringClean = cookieString.trim()

    // 处理多种分隔符
    let cookiePairs = []
    if (cookieStringClean.includes(';')) {
      cookiePairs = cookieStringClean.split(';')
    } else if (cookieStringClean.includes('\n')) {
      cookiePairs = cookieStringClean.split('\n')
    } else {
      cookiePairs = [cookieStringClean]
    }

    for (const pair of cookiePairs) {
      const trimmedPair = pair.trim()
      if (!trimmedPair || !trimmedPair.includes('=')) {
        continue
      }

      const [name, ...valueParts] = trimmedPair.split('=')
      const key = name.trim()
      const value = valueParts.join('=').trim()

      if (key && value) {
        cookies[key] = value
      }
    }

    return cookies
  }

  /**
   * 验证Cookie是否有效
   */
  isCookieValid() {
    if (!this.cookies || Object.keys(this.cookies).length === 0) {
      console.warn('Cookie为空')
      return false
    }

    // 检查关键Cookie字段
    const importantCookies = ['MUSIC_U', 'NMTID', '__csrf']
    const missingCookies = importantCookies.filter(key => !this.cookies[key])

    if (missingCookies.length > 0) {
      console.warn(`缺少关键Cookie: ${missingCookies.join(', ')}`)
      return false
    }

    // 验证MUSIC_U长度
    if (this.cookies.MUSIC_U && this.cookies.MUSIC_U.length < 10) {
      console.warn('MUSIC_U Cookie无效（太短）')
      return false
    }

    console.log('✅ Cookie验证通过')
    return true
  }

  /**
   * 获取Cookie（自动读取和验证）
   */
  getCookies() {
    if (!this.cookies || Date.now() - this.lastRead > 3600000) { // 1小时刷新
      this.readCookieFile()
    }

    if (!this.isCookieValid()) {
      console.warn('⚠️ Cookie无效，可能无法获取VIP歌曲')
    }

    return this.cookies || {}
  }

  /**
   * 获取Cookie字符串（用于HTTP请求头）
   */
  getCookieString() {
    const cookies = this.getCookies()
    return Object.entries(cookies)
      .map(([key, value]) => `${key}=${value}`)
      .join('; ')
  }

  /**
   * 获取Cookie信息
   */
  getCookieInfo() {
    const cookies = this.getCookies()
    const importantCookies = ['MUSIC_U', 'NMTID', '__csrf', '_ntes_nnid', '_ntes_nuid']

    return {
      valid: this.isCookieValid(),
      cookieCount: Object.keys(cookies).length,
      hasMusicU: !!cookies.MUSIC_U,
      hasNmtid: !!cookies.NMTID,
      hasCsrf: !!cookies.__csrf,
      presentCookies: importantCookies.filter(key => cookies[key]),
      missingCookies: importantCookies.filter(key => !cookies[key])
    }
  }

  /**
   * 设置Cookie文件路径
   */
  setCookieFile(cookieFilePath) {
    this.cookieFilePath = cookieFilePath
    this.cookies = null
    this.lastRead = null
  }

  /**
   * 写入Cookie文件
   */
  writeCookieFile(cookieString) {
    try {
      if (!cookieString || !cookieString.trim()) {
        throw new Error('Cookie内容不能为空')
      }

      const cookies = this.parseCookieString(cookieString)
      if (Object.keys(cookies).length === 0) {
        throw new Error('Cookie格式无效')
      }

      fs.writeFileSync(this.cookieFilePath, cookieString.trim(), 'utf-8')
      this.cookies = cookies
      this.lastRead = Date.now()

      console.log(`✅ 成功写入Cookie到文件: ${this.cookieFilePath}`)
      return true
    } catch (error) {
      console.error('写入Cookie文件失败:', error.message)
      return false
    }
  }

  /**
   * 清空Cookie
   */
  clearCookie() {
    try {
      if (fs.existsSync(this.cookieFilePath)) {
        fs.unlinkSync(this.cookieFilePath)
        console.log(`✅ 已清空Cookie文件: ${this.cookieFilePath}`)
      }
      this.cookies = null
      this.lastRead = null
      return true
    } catch (error) {
      console.error('清空Cookie失败:', error.message)
      return false
    }
  }
}

// 导出单例
const cookieManager = new CookieManager()

export default cookieManager
export { CookieManager }
