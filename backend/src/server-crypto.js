/**
 * Node.js版本的加密工具
 * 用于服务端API调用
 */

import crypto from 'crypto'

const AES_KEY = 'e82ckenh8dichen8'

export class NodeCrypto {
  /**
   * MD5哈希
   */
  static md5(text) {
    return crypto.createHash('md5').update(text, 'utf8').digest('hex')
  }

  /**
   * AES-CBC加密
   */
  static aesEncrypt(text, key = AES_KEY) {
    const cipher = crypto.createCipheriv(
      'aes-128-cbc',
      Buffer.from(key, 'utf8'),
      Buffer.alloc(16, 0)
    )

    let encrypted = cipher.update(text, 'utf8', 'hex')
    encrypted += cipher.final('hex')

    return encrypted
  }

  /**
   * 加密API参数
   */
  static async encryptParams(url, payload) {
    try {
      const urlPath = new URL(url).pathname.replace('/eapi/', '/api/')
      const dataString = JSON.stringify(payload)

      const digest = NodeCrypto.md5(`nobody${urlPath}use${dataString}md5forencrypt`)
      const params = `${urlPath}-36cd479b6b5-${dataString}-36cd479b6b5-${digest}`

      const encrypted = NodeCrypto.aesEncrypt(params)

      return encrypted
    } catch (error) {
      console.error('加密参数失败:', error)
      throw error
    }
  }
}

export default NodeCrypto
