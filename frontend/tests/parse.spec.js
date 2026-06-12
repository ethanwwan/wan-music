import { test, expect } from '@playwright/test'
import { TestHelpers, TEST_CONFIG, TEST_DATA } from './utils/helpers'

test.describe('解析功能测试', () => {
  test('解析歌手测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)
    await TestHelpers.switchToTab(page, '歌 手')

    const firstArtistCard = page.locator('.artist-card').first()
    const artistName = await firstArtistCard.locator('.artist-name').textContent()
    
    const parseButton = firstArtistCard.locator('button', { hasText: '解析歌手' })
    await parseButton.click()

    await page.waitForTimeout(3000)

    const detailName = page.locator('.detail-name')
    await TestHelpers.verifyElementVisible(detailName, '详情名称')
    
    const detailNameText = await detailName.textContent()
    expect(detailNameText).toBe(artistName)
    console.log(`✓ 解析歌手成功，显示: ${detailNameText}`)

    const rows = page.locator('tr')
    await page.waitForTimeout(1000)
    const count = await rows.count()
    expect(count).toBeGreaterThan(0)
    console.log(`✓ 显示 ${count} 行记录`)
  })

  test('解析歌单测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.playlist)
    await TestHelpers.switchToTab(page, '歌 单')

    const firstPlaylistCard = page.locator('.playlist-card').first()
    const parseButton = firstPlaylistCard.locator('button', { hasText: '解析歌单' })
    
    if (await parseButton.isVisible()) {
      await parseButton.click()
      await page.waitForTimeout(3000)

      const detailName = page.locator('.detail-name')
      await TestHelpers.verifyElementVisible(detailName, '歌单详情名称')

      const rows = page.locator('tr')
      const count = await rows.count()
      console.log(`✓ 解析歌单成功，显示 ${count} 行记录`)
    } else {
      console.log('⚠ 未找到可解析的歌单卡片')
    }
  })

  test('解析专辑测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.album)
    await TestHelpers.switchToTab(page, '专 辑')

    const firstAlbumCard = page.locator('.album-card').first()
    const parseButton = firstAlbumCard.locator('button', { hasText: '解析专辑' })
    
    if (await parseButton.isVisible()) {
      await parseButton.click()
      await page.waitForTimeout(3000)

      const detailName = page.locator('.detail-name')
      await TestHelpers.verifyElementVisible(detailName, '专辑详情名称')

      const rows = page.locator('tr')
      const count = await rows.count()
      console.log(`✓ 解析专辑成功，显示 ${count} 行记录`)
    } else {
      console.log('⚠ 未找到可解析的专辑卡片')
    }
  })

  test('返回按钮测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)
    await TestHelpers.switchToTab(page, '歌 手')

    const firstArtistCard = page.locator('.artist-card').first()
    const parseButton = firstArtistCard.locator('button', { hasText: '解析歌手' })
    await parseButton.click()

    await page.waitForTimeout(2000)

    const backButton = page.locator('.back-bar button')
    await TestHelpers.verifyElementVisible(backButton, '返回按钮')
    
    await backButton.click()
    await page.waitForTimeout(1000)

    const artistGrid = page.locator('.artist-grid')
    await TestHelpers.verifyElementVisible(artistGrid, '歌手网格')
    console.log('✓ 返回按钮功能正常')
  })
})