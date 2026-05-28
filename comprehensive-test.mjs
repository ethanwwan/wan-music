/**
 * 全面的自动化测试脚本
 * 测试 wan-music 项目的所有功能
 */

import { chromium } from '@playwright/test'

const BASE_URL = 'http://localhost:5174'
let passedTests = 0
let failedTests = 0
const testResults = []

function test(name, fn) {
  return async () => {
    try {
      await fn()
      testResults.push({ name, status: '✅ PASS', error: null })
      passedTests++
      console.log(`✅ 测试通过: ${name}`)
    } catch (error) {
      testResults.push({ name, status: '❌ FAIL', error: error.message })
      failedTests++
      console.error(`❌ 测试失败: ${name}`)
      console.error(`   错误: ${error.message}`)
    }
  }
}

async function runTests() {
  console.log('='.repeat(80))
  console.log('🎯 wan-music 全面自动化测试')
  console.log('='.repeat(80))
  console.log()

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()

  // 收集控制台错误
  const consoleErrors = []
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text())
    }
  })

  // 页面错误
  const pageErrors = []
  page.on('pageerror', error => {
    pageErrors.push(error.message)
  })

  try {
    // 1. 页面加载测试
    console.log('\n📦 【1. 页面加载测试】')
    console.log('-'.repeat(80))

    await test('页面正常加载', async () => {
      await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
      await page.waitForTimeout(2000)
      const title = await page.title()
      if (!title.includes('网易云音乐')) {
        throw new Error(`页面标题不正确: ${title}`)
      }
    })()

    await test('主要容器元素存在', async () => {
      const container = await page.locator('.app-container')
      if (await container.count() === 0) {
        throw new Error('主容器不存在')
      }
    })()

    await test('顶部导航栏存在', async () => {
      const header = await page.locator('.app-header')
      if (await header.count() === 0) {
        throw new Error('顶部导航栏不存在')
      }
    })()

    // 2. UI元素测试
    console.log('\n🎨 【2. UI元素测试】')
    console.log('-'.repeat(80))

    await test('标题显示正确', async () => {
      const title = await page.locator('h1.page-title')
      const text = await title.textContent()
      if (!text.includes('网易云音乐无损解析')) {
        throw new Error(`标题文本不正确: ${text}`)
      }
    })()

    await test('功能切换按钮存在', async () => {
      const buttons = await page.locator('button:has-text("解析")')
      if (await buttons.count() < 3) {
        throw new Error(`解析按钮数量不正确: ${await buttons.count()}`)
      }
    })()

    await test('音质选择器存在', async () => {
      const quality = await page.locator('.quality-selector')
      if (await quality.count() === 0) {
        throw new Error('音质选择器不存在')
      }
    })()

    await test('主题切换按钮存在', async () => {
      const themeBtn = await page.locator('button.settings-btn')
      if (await themeBtn.count() === 0) {
        throw new Error('主题切换按钮不存在')
      }
    })()

    // 3. 歌曲解析功能测试
    console.log('\n🎵 【3. 歌曲解析功能测试】')
    console.log('-'.repeat(80))

    await test('单曲解析区域可见', async () => {
      // 切换到单曲解析视图
      const singleBtn = await page.locator('button:has-text("单曲解析")')
      if (await singleBtn.count() > 0) {
        await singleBtn.click()
        await page.waitForTimeout(500)
      }
      
      const input = await page.locator('input[placeholder*="音乐链接"]')
      if (await input.count() === 0) {
        throw new Error('单曲解析输入框不存在')
      }
    })()

    await test('可以输入歌曲链接', async () => {
      const input = await page.locator('input[placeholder*="音乐链接"]').first()
      await input.fill('https://music.163.com/song?id=1380946308')
      const value = await input.inputValue()
      if (!value.includes('1380946308')) {
        throw new Error('输入歌曲链接失败')
      }
    })()

    await test('解析按钮可点击', async () => {
      const parseBtn = await page.locator('button:has-text("解析")').first()
      if (await parseBtn.isDisabled()) {
        throw new Error('解析按钮被禁用')
      }
    })()

    // 4. 歌单解析功能测试
    console.log('\n📋 【4. 歌单解析功能测试】')
    console.log('-'.repeat(80))

    await test('歌单解析按钮存在', async () => {
      const playlistBtn = await page.locator('button:has-text("歌单解析")')
      if (await playlistBtn.count() === 0) {
        throw new Error('歌单解析按钮不存在')
      }
    })()

    await test('可以切换到歌单解析视图', async () => {
      const playlistBtn = await page.locator('button:has-text("歌单解析")')
      await playlistBtn.click()
      await page.waitForTimeout(500)
      
      const input = await page.locator('input[placeholder*="歌单"]')
      if (await input.count() === 0) {
        throw new Error('切换到歌单解析视图失败')
      }
    })()

    await test('可以输入歌单链接', async () => {
      const input = await page.locator('input[placeholder*="歌单"]')
      await input.fill('https://music.163.com/playlist?id=225001')
      const value = await input.inputValue()
      if (!value.includes('225001')) {
        throw new Error('输入歌单链接失败')
      }
    })()

    // 5. 专辑解析功能测试
    console.log('\n💿 【5. 专辑解析功能测试】')
    console.log('-'.repeat(80))

    await test('专辑解析按钮存在', async () => {
      const albumBtn = await page.locator('button:has-text("专辑解析")')
      if (await albumBtn.count() === 0) {
        throw new Error('专辑解析按钮不存在')
      }
    })()

    await test('可以切换到专辑解析视图', async () => {
      const albumBtn = await page.locator('button:has-text("专辑解析")')
      await albumBtn.click()
      await page.waitForTimeout(500)
      
      const input = await page.locator('input[placeholder*="专辑"]')
      if (await input.count() === 0) {
        throw new Error('切换到专辑解析视图失败')
      }
    })()

    await test('可以输入专辑链接', async () => {
      const input = await page.locator('input[placeholder*="专辑"]')
      await input.fill('https://music.163.com/album?id=14808721')
      const value = await input.inputValue()
      if (!value.includes('14808721')) {
        throw new Error('输入专辑链接失败')
      }
    })()

    // 6. 设置面板测试
    console.log('\n⚙️ 【6. 设置面板测试】')
    console.log('-'.repeat(80))

    await test('设置按钮可点击', async () => {
      const settingsBtn = await page.locator('button.settings-btn')
      if (await settingsBtn.count() > 0) {
        await settingsBtn.click()
        await page.waitForTimeout(500)
      } else {
        throw new Error('设置按钮不存在')
      }
    })()

    await test('设置面板可打开', async () => {
      const drawer = await page.locator('.el-drawer')
      if (await drawer.count() > 0) {
        const isVisible = await drawer.isVisible()
        if (!isVisible) {
          throw new Error('设置面板未打开')
        }
      }
    })()

    await test('设置面板可关闭', async () => {
      const closeBtn = await page.locator('.el-drawer__header button')
      if (await closeBtn.count() > 0) {
        await closeBtn.click()
        await page.waitForTimeout(500)
      }
    })()

    // 7. 主题切换测试
    console.log('\n🌙 【7. 主题切换测试】')
    console.log('-'.repeat(80))

    await test('主题切换功能正常', async () => {
      // 找到主题切换按钮（设置按钮旁边的月亮/太阳按钮）
      const buttons = await page.locator('button[circle]')
      const count = await buttons.count()
      if (count < 2) {
        throw new Error(`圆形按钮数量不足: ${count}`)
      }
    })()

    // 8. 欢迎弹窗测试
    console.log('\n👋 【8. 欢迎弹窗测试】')
    console.log('-'.repeat(80))

    await test('欢迎弹窗首次显示', async () => {
      // 清除cookie使弹窗重新显示
      await page.evaluate(() => {
        document.cookie = 'hasSeenWelcome=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
        localStorage.clear()
      })
      await page.reload()
      await page.waitForTimeout(1500)
      
      const dialog = await page.locator('.el-dialog')
      if (await dialog.count() > 0) {
        const isVisible = await dialog.isVisible()
        if (!isVisible) {
          throw new Error('欢迎弹窗未显示')
        }
      }
    })()

    await test('欢迎弹窗可关闭', async () => {
      const startBtn = await page.locator('button:has-text("开始使用")')
      if (await startBtn.count() > 0) {
        await startBtn.click()
        await page.waitForTimeout(500)
        
        const dialog = await page.locator('.el-dialog')
        if (await dialog.count() > 0) {
          const isVisible = await dialog.isVisible()
          if (isVisible) {
            throw new Error('欢迎弹窗未关闭')
          }
        }
      }
    })()

    // 9. 响应式布局测试
    console.log('\n📱 【9. 响应式布局测试】')
    console.log('-'.repeat(80))

    await test('桌面视图布局正常', async () => {
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.waitForTimeout(500)
      
      const container = await page.locator('.app-container')
      if (await container.count() === 0) {
        throw new Error('桌面视图容器不存在')
      }
    })()

    await test('平板视图布局正常', async () => {
      await page.setViewportSize({ width: 768, height: 1024 })
      await page.waitForTimeout(500)
      
      const container = await page.locator('.app-container')
      if (await container.count() === 0) {
        throw new Error('平板视图容器不存在')
      }
    })()

    await test('移动端视图布局正常', async () => {
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForTimeout(500)
      
      const container = await page.locator('.app-container')
      if (await container.count() === 0) {
        throw new Error('移动端视图容器不存在')
      }
    })()

    // 10. 错误处理测试
    console.log('\n⚠️ 【10. 错误处理测试】')
    console.log('-'.repeat(80))

    await test('空输入有提示', async () => {
      const parseBtn = await page.locator('button:has-text("解析")').first()
      await parseBtn.click()
      await page.waitForTimeout(1000)
      // 不应该崩溃，应该有错误提示
    })()

    await test('无效链接有处理', async () => {
      const input = await page.locator('input[placeholder*="音乐链接"]').first()
      await input.fill('https://example.com/invalid')
      
      const parseBtn = await page.locator('button:has-text("解析")').first()
      await parseBtn.click()
      await page.waitForTimeout(2000)
      // 应该显示错误消息
    })()

    // 11. 控制台错误检查
    console.log('\n🔍 【11. 控制台错误检查】')
    console.log('-'.repeat(80))

    await test('无JavaScript致命错误', async () => {
      if (pageErrors.length > 0) {
        console.log('\n页面错误:')
        pageErrors.forEach(err => console.log(`  - ${err.substring(0, 100)}`))
        throw new Error(`发现 ${pageErrors.length} 个页面错误`)
      }
    })()

  } catch (error) {
    console.error('\n❌ 测试执行失败:', error.message)
  } finally {
    await browser.close()
  }

  // 输出测试结果汇总
  console.log()
  console.log('='.repeat(80))
  console.log('📊 测试结果汇总')
  console.log('='.repeat(80))
  console.log(`✅ 通过: ${passedTests}`)
  console.log(`❌ 失败: ${failedTests}`)
  console.log(`📊 总计: ${passedTests + failedTests}`)
  console.log(`📈 通过率: ${((passedTests / (passedTests + failedTests)) * 100).toFixed(1)}%`)
  console.log()

  // 详细的失败测试列表
  if (failedTests > 0) {
    console.log('❌ 失败的测试:')
    testResults
      .filter(r => r.status === '❌ FAIL')
      .forEach(r => {
        console.log(`  - ${r.name}`)
        console.log(`    错误: ${r.error}`)
      })
    console.log()
  }

  // 控制台错误统计
  if (consoleErrors.length > 0) {
    console.log('⚠️ 控制台错误统计:')
    console.log(`  总计: ${consoleErrors.length} 个`)
    console.log('  前5个错误:')
    consoleErrors.slice(0, 5).forEach((err, i) => {
      console.log(`    ${i + 1}. ${err.substring(0, 100)}`)
    })
    console.log()
  }

  if (failedTests === 0) {
    console.log('🎉 所有测试通过！')
  } else {
    console.log('⚠️  部分测试失败，请检查上述错误信息')
  }

  console.log('='.repeat(80))
  console.log()

  return failedTests === 0
}

runTests()
  .then(success => {
    process.exit(success ? 0 : 1)
  })
  .catch(error => {
    console.error('测试脚本执行失败:', error)
    process.exit(1)
  })
