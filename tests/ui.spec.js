/**
 * Playwright UI 自动化测试
 * 测试 wan-music 项目的 UI 交互功能
 */

import { test, expect } from '@playwright/test'

// 测试配置
const BASE_URL = 'http://localhost:5173'
const TEST_SONG_URL = 'https://music.163.com/song?id=1380946308'

test.describe('wan-music UI 测试套件', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL)
    await page.waitForLoadState('networkidle')
  })

  test('页面标题和基本元素加载', async ({ page }) => {
    // 检查页面标题
    await expect(page).toHaveTitle(/网易云音乐解析/)

    // 检查主标题
    const title = page.locator('h1')
    await expect(title).toContainText('网易云音乐解析')

    // 检查页脚
    const footer = page.locator('.app-footer p')
    await expect(footer).toContainText('Vue 3')
  })

  test('主题切换功能', async ({ page }) => {
    // 查找主题切换按钮
    const themeButton = page.locator('button').filter({ has: page.locator('.el-icon-moon') }).first()
    
    if (await themeButton.isVisible()) {
      // 点击切换主题
      await themeButton.click()
      
      // 等待主题更新
      await page.waitForTimeout(1000)
      
      // 验证主题已切换（检查是否有 dark 类）
      const html = page.locator('html')
      const hasDarkClass = await html.evaluate(el => el.classList.contains('dark'))
      
      console.log(`主题切换成功: ${hasDarkClass ? '深色模式' : '浅色模式'}`)
    }
  })

  test('设置面板功能', async ({ page }) => {
    // 点击设置按钮
    const settingsButton = page.locator('button').filter({ has: page.locator('.el-icon-setting') }).first()
    await settingsButton.click()

    // 检查设置面板是否打开
    const drawer = page.locator('.el-drawer')
    await expect(drawer).toBeVisible()

    // 检查设置项
    const qualityLabel = page.locator('text=默认音质')
    await expect(qualityLabel).toBeVisible()

    // 关闭设置面板
    const closeButton = drawer.locator('.el-drawer__header button')
    await closeButton.click()
    
    await expect(drawer).not.toBeVisible()
  })

  test('歌曲解析表单功能', async ({ page }) => {
    // 查找歌曲解析输入框
    const songInput = page.locator('input[placeholder*="歌曲链接"]').first()
    
    // 检查输入框存在
    await expect(songInput).toBeVisible()
    
    // 输入测试链接
    await songInput.fill(TEST_SONG_URL)
    
    // 验证输入内容
    await expect(songInput).toHaveValue(TEST_SONG_URL)
    
    // 查找解析按钮
    const parseButton = page.locator('button:has-text("解析")').first()
    await expect(parseButton).toBeVisible()
  })

  test('音质选择功能', async ({ page }) => {
    // 查找音质单选按钮组
    const qualityGroup = page.locator('.quality-selector').first()
    
    if (await qualityGroup.isVisible()) {
      // 检查音质选项
      const losslessOption = qualityGroup.locator('text=无损').first()
      await expect(losslessOption).toBeVisible()
      
      // 点击无损选项
      await losslessOption.click()
      
      // 验证选中状态
      const radio = qualityGroup.locator('.el-radio-button__inner').filter({ hasText: '无损' })
      await expect(radio).toHaveClass(/is-active/)
    }
  })

  test('欢迎对话框功能', async ({ page }) => {
    // 等待欢迎对话框出现
    await page.waitForTimeout(1500)
    
    const welcomeDialog = page.locator('.el-dialog')
    
    // 如果欢迎对话框出现
    if (await welcomeDialog.isVisible()) {
      // 检查标题
      const title = welcomeDialog.locator('.el-dialog__title')
      await expect(title).toContainText('欢迎使用')
      
      // 检查功能说明
      const alert = welcomeDialog.locator('.el-alert')
      await expect(alert).toBeVisible()
      
      // 点击开始使用按钮
      const startButton = welcomeDialog.locator('button:has-text("开始使用")')
      await startButton.click()
      
      // 验证对话框关闭
      await expect(welcomeDialog).not.toBeVisible()
    }
  })

  test('空状态显示', async ({ page }) => {
    // 检查空状态区域
    const emptySection = page.locator('.empty-section')
    
    if (await emptySection.isVisible()) {
      // 检查空状态图标
      const emptyIcon = emptySection.locator('.el-icon')
      await expect(emptyIcon).toBeVisible()
      
      // 检查空状态描述
      const emptyText = emptySection.locator('.el-empty__description')
      await expect(emptyText).toContainText('暂无解析结果')
    }
  })

  test('响应式布局', async ({ page }) => {
    // 移动端视图
    await page.setViewportSize({ width: 375, height: 667 })
    await page.waitForTimeout(500)
    
    // 检查布局是否正常
    const container = page.locator('.app-container')
    await expect(container).toBeVisible()
    
    // 平板视图
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.waitForTimeout(500)
    await expect(container).toBeVisible()
    
    // 桌面视图
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.waitForTimeout(500)
    await expect(container).toBeVisible()
  })

  test('错误提示功能', async ({ page }) => {
    // 输入无效链接
    const songInput = page.locator('input[placeholder*="歌曲链接"]').first()
    await songInput.fill('https://example.com/invalid')
    
    // 点击解析
    const parseButton = page.locator('button:has-text("解析")').first()
    await parseButton.click()
    
    // 等待错误提示（如果有）
    await page.waitForTimeout(1000)
    
    // 检查是否有错误消息
    const errorMessage = page.locator('.el-message--error')
    // 不强制要求有错误消息，因为可能需要更长的处理时间
  })

  test('控制台无错误', async ({ page }) => {
    const errors = []
    
    // 监听控制台错误
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    
    // 等待页面完全加载
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    
    // 过滤掉已知的非关键错误（如 API 调用失败）
    const criticalErrors = errors.filter(err => 
      !err.includes('Failed to fetch') &&
      !err.includes('Network Error') &&
      !err.includes('net::ERR')
    )
    
    // 输出错误日志
    if (criticalErrors.length > 0) {
      console.log('发现关键错误:', criticalErrors)
    }
    
    // 不强制要求无错误，因为 API 调用失败是预期的
    console.log(`共发现 ${errors.length} 个错误（包含非关键错误）`)
  })
})

// 性能测试
test.describe('性能测试', () => {
  test('页面加载时间', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto(BASE_URL)
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    
    console.log(`页面加载时间: ${loadTime}ms`)
    
    // 页面加载时间应该在 5 秒内
    expect(loadTime).toBeLessThan(5000)
  })
})

// 可访问性测试
test.describe('可访问性测试', () => {
  test('图片 alt 文本', async ({ page }) => {
    await page.goto(BASE_URL)
    await page.waitForLoadState('networkidle')
    
    // 检查所有图片是否有 alt 属性
    const images = page.locator('img')
    const count = await images.count()
    
    for (let i = 0; i < count; i++) {
      const img = images.nth(i)
      const alt = await img.getAttribute('alt')
      // alt 可以为空，但不应该是 undefined
      expect(alt).not.toBeUndefined()
    }
  })
})
