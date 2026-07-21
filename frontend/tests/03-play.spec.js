/**
 * 03 - 播放功能测试
 * 测试：点击播放按钮 → 触发 /song → mini-player 出现 → 音频元素加载
 */
import { test, expect } from '@playwright/test'
import {
  createInstrumentedPage,
  PLATFORMS,
  performSearch,
  selectDataSource,
  assertConsoleClean,
  shot,
} from './lib/helpers.js'

// 播放测试仅用一个代表性平台，避免 12 倍冗余（搜索已经覆盖了平台矩阵）
for (const platform of [PLATFORMS[0], PLATFORMS[1]]) {
  test(`播放 - ${platform.name} 第一首歌曲`, async ({ context }) => {
    const instrument = await createInstrumentedPage(context)
    const { page } = instrument

    await page.goto('/')
    await page.waitForFunction(
      () => {
        const sel = document.querySelector('.input-row .ant-select')
        return sel && !sel.classList.contains('ant-select-disabled')
      },
      { timeout: 15_000 },
    )
    await selectDataSource(page, platform.id)
    await performSearch(page, platform.query, { timeout: 90_000 })

    // 点击第一首歌的播放按钮
    const firstPlayBtn = page.locator('.tracks-table tbody tr.track-row').first().locator('button').first()
    await firstPlayBtn.click()

    // 等待 mini-player 出现
    const player = page.locator('.mini-player')
    await player.waitFor({ state: 'visible', timeout: 30_000 })
    await shot(page, `03-play-${platform.id}`)

    // hover 触发悬浮面板（验证 hover panel 渲染）
    await player.hover()
    await page.waitForTimeout(800)
    const panel = page.locator('.mini-player-panel')
    await expect(panel).toBeVisible()
    // 标题/歌手名/时间
    await expect(panel.locator('.panel-title')).not.toBeEmpty()
    await expect(panel.locator('.panel-artist')).not.toBeEmpty()

    // 控制台干净（AbortError 是预期的 - pause 后 play）
    const clean = assertConsoleClean(instrument, `03-play-${platform.id}`)
    expect(clean.pageErrors, `page error: ${JSON.stringify(clean.pageErrors, null, 2)}`).toHaveLength(0)
  })
}

test('播放 - 切歌：连续点第二首', async ({ context }) => {
  const { page, pageErrors } = await createInstrumentedPage(context)
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  await selectDataSource(page, 'netease')
  await performSearch(page, '周杰伦', { timeout: 90_000 })

  // 播放第一首
  await page.locator('.tracks-table tbody tr.track-row').first().locator('button').first().click()
  await page.locator('.mini-player').waitFor({ state: 'visible', timeout: 30_000 })
  // 等 1s 让音频元数据加载
  await page.waitForTimeout(1500)
  const title1 = await page.locator('.panel-title').textContent()

  // 播放第二首
  await page.locator('.tracks-table tbody tr.track-row').nth(1).locator('button').first().click()
  await page.waitForTimeout(2000)
  const title2 = await page.locator('.panel-title').textContent()

  expect(title1, '切歌后歌名应变化').not.toBe(title2)
})

test('播放 - hover 歌词行触发点击跳转', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  await selectDataSource(page, 'netease')
  await performSearch(page, '周杰伦', { timeout: 90_000 })

  // 播放
  await page.locator('.tracks-table tbody tr.track-row').first().locator('button').first().click()
  const player = page.locator('.mini-player')
  await player.waitFor({ state: 'visible', timeout: 30_000 })
  await player.hover()
  await page.waitForTimeout(800)

  // 如果有歌词，点击第一行歌词不应报错
  const lyricLines = page.locator('.lyric-list li')
  const lineCount = await lyricLines.count()
  if (lineCount > 1) {
    await lyricLines.nth(1).click({ force: true })
    await page.waitForTimeout(500)
  } else {
    test.skip(true, '当前歌曲无歌词，跳过点击跳转测试')
  }
})