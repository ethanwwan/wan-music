import { test, expect } from '@playwright/test'
import { TestHelpers, TEST_CONFIG, TEST_DATA } from './utils/helpers'

test.describe('搜索功能测试', () => {
  test('单曲搜索测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)

    const songList = page.locator('.search-result-panel')
    await TestHelpers.verifyElementVisible(songList, '搜索结果面板')

    const songItems = page.locator('tr')
    await page.waitForTimeout(1000)
    const count = await songItems.count()
    expect(count).toBeGreaterThan(0)
    console.log(`✓ 单曲搜索成功，找到 ${count} 条记录`)
  })

  test('歌手搜索测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)

    await TestHelpers.switchToTab(page, '歌 手')

    const artistGrid = page.locator('.artist-grid')
    await TestHelpers.verifyElementVisible(artistGrid, '歌手网格')

    const artistCards = page.locator('.artist-card')
    const count = await artistCards.count()
    expect(count).toBeGreaterThan(0)
    console.log(`✓ 歌手搜索成功，找到 ${count} 位歌手`)
  })

  test('歌单搜索测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.playlist)

    await TestHelpers.switchToTab(page, '歌 单')

    const playlistGrid = page.locator('.playlist-grid')
    await TestHelpers.verifyElementVisible(playlistGrid, '歌单网格')

    const playlistCards = page.locator('.playlist-card')
    const count = await playlistCards.count()
    expect(count).toBeGreaterThan(0)
    console.log(`✓ 歌单搜索成功，找到 ${count} 个歌单`)
  })

  test('专辑搜索测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.album)

    await TestHelpers.switchToTab(page, '专 辑')

    const albumGrid = page.locator('.album-grid')
    await TestHelpers.verifyElementVisible(albumGrid, '专辑网格')

    const albumCards = page.locator('.album-card')
    const count = await albumCards.count()
    expect(count).toBeGreaterThan(0)
    console.log(`✓ 专辑搜索成功，找到 ${count} 张专辑`)
  })

  test('Tab切换测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)

    const tabs = ['歌 手', '歌 单', '专 辑']
    for (const tab of tabs) {
      await TestHelpers.switchToTab(page, tab)
      console.log(`✓ 成功切换到 ${tab} Tab`)
    }
  })

  test('搜索关键词保持测试', async ({ page }) => {
    await page.goto(TEST_CONFIG.BASE_URL)
    await TestHelpers.waitForPageReady(page)

    await TestHelpers.fillAndSubmitSearch(page, TEST_DATA.keywords.song)

    await TestHelpers.switchToTab(page, '歌 单')
    await TestHelpers.switchToTab(page, '歌 手')

    const artistGrid = page.locator('.artist-grid')
    await TestHelpers.verifyElementVisible(artistGrid, '歌手网格')

    const firstArtistName = page.locator('.artist-name').first()
    const name = await firstArtistName.textContent()
    expect(name).toBe('周杰伦')
    console.log(`✓ Tab切换后关键词保持正确，显示歌手: ${name}`)
  })
})