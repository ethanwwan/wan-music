/**
 * 测试脚本 - 验证所有模块是否正常工作
 * 运行方式：node src/test.js
 */

import { logger, config, neteaseApi, QUALITY_LEVELS } from './index.js'

console.log('🧪 开始测试模块...\n')

console.log('1. 测试日志模块:')
logger.info('日志模块工作正常')
logger.debug('Debug 信息')
logger.warn('警告信息')
logger.error('错误信息')

console.log('\n2. 测试配置模块:')
console.log(`应用名称: ${config.get('appName')}`)
console.log(`版本: ${config.get('version')}`)
console.log(`API 超时: ${config.get('api.timeout')}ms`)
console.log(`默认音质: ${config.get('quality.default')}`)

console.log('\n3. 测试音质等级:')
QUALITY_LEVELS.forEach(level => {
  console.log(`  - ${level.label}: ${level.value} (${level.bitrate})`)
})

console.log('\n4. 测试 Cookie 管理:')
import { CookieManager } from './utils/cookieManager.js'
const cookieManager = new CookieManager()
console.log(`Cookie 有效: ${cookieManager.isCookieValid()}`)

console.log('\n5. 测试错误处理:')
import { APIError, DownloadError, formatErrorMessage } from './utils/errors.js'
const apiError = new APIError('测试 API 错误', 'TEST_001', 500)
console.log(formatErrorMessage(apiError))

console.log('\n✅ 所有模块测试完成!')
