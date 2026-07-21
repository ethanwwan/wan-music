/**
 * 02 - 搜索功能测试矩阵
 * 对每个平台 × 每个音质组合，测试搜索结果是否正常返回
 */
import { test, expect } from '@playwright/test'
import {
  createInstrumentedPage,
  PLATFORMS,
  QUALITIES,
  performSearch,
  selectDataSource,
  selectQuality,
  waitForSearchResults,
  assertConsoleClean,
  shot,
} from './lib/helpers.js'

// 每个平台 × 每个音质 = 4 × 3 = 12 个组合
for (const platform of PLATFORMS) {
  for (const quality of QUALITIES) {
    test(`搜索 - ${platform.name} × ${quality.label}`, async ({ context }) => {
      const instrument = await createInstrumentedPage(context)
      const { page } = instrument

      await page.goto('/')
      // 等平台列表
      await page.waitForFunction(
        () => {
          const sel = document.querySelector('.input-row .ant-select')
          return sel && !sel.classList.contains('ant-select-disabled')
        },
        { timeout: 15_000 },
      )

      // 1) 切音质
      await selectQuality(page, quality.label)
      // 2) 切平台
      await selectDataSource(page, platform.id)
      // 3) 搜索
      const rowCount = await performSearch(page, platform.query, { timeout: 90_000 })

      // 断言：搜索到结果（非空状态）
      expect(rowCount, `${platform.name}/${quality.label} 搜索无结果`).toBeGreaterThan(0)

      // 断言：每行都有歌名 + 平台 tag
      const firstRow = page.locator('.tracks-table tbody tr.track-row').first()
      await expect(firstRow.locator('.track-name')).not.toBeEmpty()
      await expect(firstRow.locator('.source-tag')).toBeVisible()

      // 截图（每组合都留档）
      await shot(page, `02-search-${platform.id}-${quality.value}`)

      // 控制台干净
      const clean = assertConsoleClean(instrument, `02-search-${platform.id}-${quality.value}`)
      expect(clean.consoleErrors, `console error: ${JSON.stringify(clean.consoleErrors, null, 2)}`).toHaveLength(0)
      expect(clean.pageErrors, `page error: ${JSON.stringify(clean.pageErrors, null, 2)}`).toHaveLength(0)
    })
  }
}

test('搜索 - 空输入应触发警告', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await page.locator('.input-row button.ant-btn-primary').filter({ hasText: '搜索' }).click()
  // 等待 message 警告出现
  const warning = page.locator('.ant-message-warning').first()
  await expect(warning).toBeVisible({ timeout: 5_000 })
})

test('搜索 - 空结果关键词应展示空状态', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  // 用一个不可能搜到的关键词
  const input = page.locator('.input-row .ant-input').first()
  await input.fill('zzzz_no_match_xyz123_不存在的关键词')
  await page.locator('.input-row button.ant-btn-primary').filter({ hasText: /搜\s*索/ }).click()
  // 等待空结果
  await page.locator('.ant-empty').waitFor({ state: 'visible', timeout: 60_000 })
})