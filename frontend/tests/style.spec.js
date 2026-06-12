import { test, expect } from '@playwright/test'
import { TestHelpers, TEST_CONFIG, TEST_DATA } from './utils/helpers'

test.describe('样式规范测试', () => {
  test('主题色测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    const primaryButton = page.locator('button.ant-btn-primary')
    await TestHelpers.verifyElementVisible(primaryButton, '主按钮')

    const buttonStyle = await primaryButton.evaluate((el) => {
      const style = window.getComputedStyle(el)
      return {
        backgroundColor: style.backgroundColor,
        color: style.color,
        borderRadius: style.borderRadius
      }
    })

    console.log(`✓ 主按钮背景色: ${buttonStyle.backgroundColor}`)
    console.log(`✓ 主按钮文字色: ${buttonStyle.color}`)
    console.log(`✓ 主按钮圆角: ${buttonStyle.borderRadius}`)
  })

  test('字体大小测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    const heroTitle = page.locator('.hero-title')
    const titleStyle = await heroTitle.evaluate((el) => {
      const style = window.getComputedStyle(el)
      return {
        fontSize: style.fontSize,
        fontWeight: style.fontWeight
      }
    })

    console.log(`✓ 页面标题字体大小: ${titleStyle.fontSize}`)
    console.log(`✓ 页面标题字重: ${titleStyle.fontWeight}`)
  })

  test('卡片间距测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)

    const cards = page.locator('.song-item')
    const count = await cards.count()
    
    if (count > 0) {
      const firstCard = cards.first()
      const cardStyle = await firstCard.evaluate((el) => {
        const style = window.getComputedStyle(el)
        return {
          marginBottom: style.marginBottom,
          padding: style.padding
        }
      })

      console.log(`✓ 卡片底部间距: ${cardStyle.marginBottom}`)
      console.log(`✓ 卡片内边距: ${cardStyle.padding}`)
    }
  })

  test('响应式测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    const viewports = [
      { width: 375, height: 667, name: '手机' },
      { width: 768, height: 1024, name: '平板' },
      { width: 1280, height: 800, name: '桌面' }
    ]

    for (const { width, height, name } of viewports) {
      await page.setViewportSize({ width, height })
      
      const searchInput = page.locator('input[placeholder*="歌曲名"]')
      const isVisible = await searchInput.isVisible()
      
      console.log(`✓ ${name} (${width}x${height}): 搜索框可见=${isVisible}`)
    }

    await page.setViewportSize({ width: 1280, height: 800 })
  })

  test('渐变背景测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.playlist)
    await TestHelpers.switchToTab(page, '歌 单')

    const placeholder = page.locator('.playlist-cover-placeholder')
    if (await placeholder.isVisible()) {
      const bgStyle = await placeholder.evaluate((el) => {
        const style = window.getComputedStyle(el)
        return style.background
      })

      expect(bgStyle).toContain('linear-gradient')
      console.log(`✓ 占位图渐变背景: ${bgStyle}`)
    }
  })

  test('阴影效果测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)

    const cards = page.locator('.song-item')
    if ((await cards.count()) > 0) {
      const cardStyle = await cards.first().evaluate((el) => {
        const style = window.getComputedStyle(el)
        return style.boxShadow
      })

      console.log(`✓ 卡片阴影效果: ${cardStyle || '无阴影'}`)
    }
  })
})