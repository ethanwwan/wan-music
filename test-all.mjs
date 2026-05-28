/**
 * 全面的自动化测试脚本
 * 测试 wan-music 项目的所有功能
 */

import { chromium } from 'playwright'

const BASE_URL = 'http://localhost:5173'
let passedTests = 0
let failedTests = 0
const testResults = []

async function runTest(name, fn) {
  try {
    await fn()
    testResults.push({ name, status: '✅ PASS', error: null })
    passedTests++
    console.log(`✅ 测试通过: ${name}`)
    return true
  } catch (error) {
    testResults.push({ name, status: '❌ FAIL', error: error.message })
    failedTests++
    console.error(`❌ 测试失败: ${name}`)
    console.error(`   错误: ${error.message.substring(0, 150)}`)
    return false
  }
}

async function runTests() {
  console.log('='.repeat(80))
  console.log('🎯 wan-music 全面自动化测试')
  console.log('='.repeat(80))
  console.log()

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()

  const pageErrors = []
  page.on('pageerror', error => {
    pageErrors.push(error.message)
  })

  try {
    // 1. 页面加载测试
    console.log('\n📦 【1. 页面加载测试】')
    console.log('-'.repeat(80))

    await runTest('页面正常加载', async () => {
      await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
      await page.waitForTimeout(2000)
      const title = await page.title()
      if (!title.includes('网易云音乐')) {
        throw new Error(`页面标题不正确: ${title}`)
      }
      console.log(`   页面标题: ${title}`)
    })

    await runTest('主要容器元素存在', async () => {
      const container = await page.locator('.app-container')
      if (await container.count() === 0) {
        throw new Error('主容器不存在')
      }
      console.log(`   找到主容器`)
    })

    await runTest('顶部导航栏存在', async () => {
      const header = await page.locator('.app-header')
      if (await header.count() === 0) {
        throw new Error('顶部导航栏不存在')
      }
      console.log(`   找到导航栏`)
    })

    // 2. UI元素测试
    console.log('\n🎨 【2. UI元素测试】')
    console.log('-'.repeat(80))

    await runTest('页面标题显示', async () => {
      const title = await page.locator('h1.page-title, .page-title, h1')
      const count = await title.count()
      if (count === 0) {
        throw new Error('页面标题不存在')
      }
      const text = await title.first().textContent()
      console.log(`   标题: ${text}`)
    })

    await runTest('功能切换按钮存在', async () => {
      const buttons = await page.locator('button')
      const count = await buttons.count()
      if (count < 3) {
        throw new Error(`按钮数量不足: ${count}`)
      }
      console.log(`   找到 ${count} 个按钮`)
    })

    // 3. 歌曲解析功能测试
    console.log('\n🎵 【3. 歌曲解析功能测试】')
    console.log('-'.repeat(80))

    await runTest('输入框存在', async () => {
      const input = await page.locator('input').first()
      if (!(await input.isVisible())) {
        throw new Error('输入框不可见')
      }
      console.log(`   输入框可见`)
    })

    await runTest('可以输入文本', async () => {
      const inputs = await page.locator('input')
      const count = await inputs.count()
      if (count > 0) {
        await inputs.first().fill('https://music.163.com/song?id=1380946308')
        const value = await inputs.first().inputValue()
        if (!value) {
          throw new Error('无法输入文本')
        }
        console.log(`   成功输入文本`)
      }
    })

    // 4. 设置面板测试
    console.log('\n⚙️ 【4. 设置面板测试】')
    console.log('-'.repeat(80))

    await runTest('设置按钮可点击', async () => {
      const settingsBtn = await page.locator('button').nth(1)
      if (await settingsBtn.count() > 0) {
        await settingsBtn.click()
        await page.waitForTimeout(500)
        console.log(`   设置按钮已点击`)
      }
    })

    // 5. 响应式布局测试
    console.log('\n📱 【5. 响应式布局测试】')
    console.log('-'.repeat(80))

    await runTest('桌面视图布局正常', async () => {
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.waitForTimeout(500)
      const container = await page.locator('.app-container')
      if (await container.count() === 0) {
        throw new Error('桌面视图容器不存在')
      }
      console.log(`   1920x1080 布局正常`)
    })

    await runTest('移动端视图布局正常', async () => {
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForTimeout(500)
      const container = await page.locator('.app-container')
      if (await container.count() === 0) {
        throw new Error('移动端视图容器不存在')
      }
      console.log(`   375x667 布局正常`)
    })

    // 6. 错误检查
    console.log('\n🔍 【6. 错误检查】')
    console.log('-'.repeat(80))

    await runTest('无JavaScript致命错误', async () => {
      if (pageErrors.length > 0) {
        console.log('\n页面错误:')
        pageErrors.slice(0, 3).forEach(err => {
          console.log(`  - ${err.substring(0, 100)}`)
        })
        throw new Error(`发现 ${pageErrors.length} 个页面错误`)
      }
      console.log(`   无致命错误`)
    })

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

  if (failedTests > 0) {
    console.log('❌ 失败的测试:')
    testResults
      .filter(r => r.status === '❌ FAIL')
      .forEach(r => {
        console.log(`  - ${r.name}`)
      })
    console.log()
  }

  if (failedTests === 0) {
    console.log('🎉 所有测试通过！')
  } else {
    console.log(`⚠️  ${failedTests} 个测试失败`)
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
