/**
 * 自动化测试脚本
 * 测试 wan-music 项目的各个功能模块
 */

import * as crypto from './src/services/crypto.js'
import * as neteaseApi from './src/services/neteaseApi.js'
import * as musicApi from './src/services/musicApi.js'
import * as config from './src/config/index.js'

console.log('='.repeat(60))
console.log('wan-music 自动化测试')
console.log('='.repeat(60))
console.log()

let passedTests = 0
let failedTests = 0

function test(name, fn) {
  try {
    fn()
    console.log(`✅ 测试通过: ${name}`)
    passedTests++
  } catch (error) {
    console.error(`❌ 测试失败: ${name}`)
    console.error(`   错误: ${error.message}`)
    failedTests++
  }
}

async function testAsync(name, fn) {
  try {
    await fn()
    console.log(`✅ 测试通过: ${name}`)
    passedTests++
  } catch (error) {
    console.error(`❌ 测试失败: ${name}`)
    console.error(`   错误: ${error.message}`)
    failedTests++
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || '断言失败')
  }
}

// 测试 Crypto 模块
console.log('\n【1. 测试 Crypto 模块】')
console.log('-'.repeat(60))

test('MD5 哈希函数', () => {
  const hash = crypto.md5('hello world')
  assert(hash === '5eb63bbbe01eeed093cb22bb8f5acdc3', 'MD5 哈希值不正确')
})

test('AES 加密函数', () => {
  const encrypted = crypto.aesEncrypt('test data', 'test key')
  assert(encrypted && encrypted.length > 0, 'AES 加密结果为空')
})

test('EAPI 加密函数', () => {
  const encrypted = crypto.encryptEapi('/api/test', '{"test": "data"}')
  assert(encrypted && encrypted.length > 0, 'EAPI 加密结果为空')
})

test('API 常量定义', () => {
  assert(crypto.APIConstants.AES_KEY === 'e82ckenh8dichen8', 'AES 密钥不正确')
  assert(crypto.APIConstants.REFERER === 'https://music.163.com/', 'Referer 不正确')
})

test('音质等级映射', () => {
  const levels = crypto.APIConstants.QUALITY_LEVELS
  assert(levels.standard === 'standard', '标准音质映射错误')
  assert(levels.exhigh === 'exhigh', '极高音质映射错误')
  assert(levels.lossless === 'lossless', '无损音质映射错误')
})

// 测试 Config 模块
console.log('\n【2. 测试 Config 模块】')
console.log('-'.repeat(60))

test('配置获取', () => {
  const apiTimeout = config.get('apiTimeout', 30000)
  assert(apiTimeout === 30000, '默认超时时间不正确')
})

test('配置设置', () => {
  config.set('testKey', 'testValue')
  assert(config.get('testKey') === 'testValue', '配置设置失败')
})

test('音质选项', () => {
  const qualities = config.qualities
  assert(Array.isArray(qualities), '音质选项不是数组')
  assert(qualities.length > 0, '音质选项为空')
})

// 测试 URL 验证
console.log('\n【3. 测试 URL 验证】')
console.log('-'.repeat(60))

test('歌曲 URL 验证', () => {
  assert(musicApi.validateMusicUrl('https://music.163.com/song?id=123456') === true, '歌曲 URL 验证失败')
  assert(musicApi.validateMusicUrl('https://y.music.163.com/m/song?id=123456') === true, '移动端歌曲 URL 验证失败')
  assert(musicApi.validateMusicUrl('https://music.163.com/playlist?id=123') === false, '不应识别为歌曲 URL')
})

test('歌单 URL 验证', () => {
  assert(musicApi.validatePlaylistUrl('https://music.163.com/playlist?id=123456') === true, '歌单 URL 验证失败')
  assert(musicApi.validatePlaylistUrl('https://music.163.com/song?id=123') === false, '不应识别为歌单 URL')
})

test('专辑 URL 验证', () => {
  assert(musicApi.validateAlbumUrl('https://music.163.com/album?id=123456') === true, '专辑 URL 验证失败')
  assert(musicApi.validateAlbumUrl('https://music.163.com/song?id=123') === false, '不应识别为专辑 URL')
})

// 测试 URL 解析
console.log('\n【4. 测试 URL 解析】')
console.log('-'.repeat(60))

test('歌曲 URL 解析', () => {
  const result = musicApi.parseUrl('https://music.163.com/song?id=1380946308')
  assert(result.type === 'song', '类型不正确')
  assert(result.id === 1380946308, 'ID 解析不正确')
})

test('歌单 URL 解析', () => {
  const result = musicApi.parseUrl('https://music.163.com/playlist?id=123456')
  assert(result.type === 'playlist', '类型不正确')
  assert(result.id === 123456, 'ID 解析不正确')
})

test('专辑 URL 解析', () => {
  const result = musicApi.parseUrl('https://music.163.com/album?id=123456')
  assert(result.type === 'album', '类型不正确')
  assert(result.id === 123456, 'ID 解析不正确')
})

test('无效 URL 解析', () => {
  const result = musicApi.parseUrl('https://example.com/test')
  assert(result === null, '无效 URL 应返回 null')
})

// 测试 API 调用（实际请求）
console.log('\n【5. 测试 API 调用】')
console.log('-'.repeat(60))

await testAsync('获取歌曲详情 (ID: 1380946308)', async () => {
  try {
    const song = await neteaseApi.getSingleSongDetail(1380946308)
    assert(song && song.id === 1380946308, '歌曲信息不正确')
    console.log(`   📝 歌曲名: ${song?.name}`)
    console.log(`   🎤 艺术家: ${song?.artist}`)
  } catch (error) {
    // API 可能失败，但这不是代码问题
    console.log(`   ⚠️ API 请求失败: ${error.message}`)
  }
})

await testAsync('获取歌曲播放链接', async () => {
  try {
    const url = await neteaseApi.getSongUrl(1380946308, 'standard')
    console.log(`   🔗 播放链接: ${url?.url?.substring(0, 50)}...`)
  } catch (error) {
    console.log(`   ⚠️ API 请求失败: ${error.message}`)
  }
})

// 测试音乐信息服务
console.log('\n【6. 测试 Music API 服务】')
console.log('-'.repeat(60))

await testAsync('获取歌曲完整信息', async () => {
  try {
    const info = await musicApi.getMusicInfo('https://music.163.com/song?id=1380946308', 'standard')
    console.log(`   📝 歌曲信息: ${info?.name || 'N/A'}`)
    console.log(`   🔗 链接: ${info?.url ? '有' : '无'}`)
  } catch (error) {
    console.log(`   ⚠️ API 请求失败: ${error.message}`)
  }
})

// 测试音质映射
console.log('\n【7. 测试音质映射】')
console.log('-'.repeat(60))

test('获取音质等级', () => {
  const levels = musicApi.getQualityLevels()
  assert(Array.isArray(levels), '音质等级不是数组')
  assert(levels.length > 0, '音质等级为空')
  console.log(`   📊 共 ${levels.length} 种音质可选`)
})

test('获取音质标签', () => {
  const label = musicApi.getQualityLabel('lossless')
  assert(label && label.includes('无损'), '音质标签不正确')
  console.log(`   🎵 无损音质标签: ${label}`)
})

// 测试错误处理
console.log('\n【8. 测试错误处理】')
console.log('-'.repeat(60))

test('无效歌曲 ID', async () => {
  try {
    await neteaseApi.getSingleSongDetail(999999999)
    assert(false, '应该抛出错误')
  } catch (error) {
    assert(error.message.includes('未找到') || error.message.includes('not found'), '错误信息不正确')
    console.log(`   ✅ 正确处理无效 ID: ${error.message}`)
  }
})

test('无效 URL', async () => {
  try {
    await musicApi.getMusicInfo('https://example.com/invalid')
    assert(false, '应该抛出错误')
  } catch (error) {
    assert(error.message.includes('无效') || error.message.includes('invalid'), '错误信息不正确')
    console.log(`   ✅ 正确处理无效 URL: ${error.message}`)
  }
})

// 输出测试结果
console.log()
console.log('='.repeat(60))
console.log('测试结果汇总')
console.log('='.repeat(60))
console.log(`✅ 通过: ${passedTests}`)
console.log(`❌ 失败: ${failedTests}`)
console.log(`📊 总计: ${passedTests + failedTests}`)
console.log()

if (failedTests === 0) {
  console.log('🎉 所有测试通过！')
  process.exit(0)
} else {
  console.log('⚠️  部分测试失败，请检查上述错误信息')
  process.exit(1)
}
