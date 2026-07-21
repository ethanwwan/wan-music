/**
 * 04 - 下载功能测试
 * 测试：单首下载 / 批量下载 / 队列状态
 *
 * 注意：Ant Design Vue 4 drawer 通过 portal 渲染，
 * 所以检测 drawer 可见用 .ant-drawer-open 而非 .download-drawer .ant-drawer-content
 */
import { test, expect } from '@playwright/test'
import {
  createInstrumentedPage,
  PLATFORMS,
  QUALITIES,
  performSearch,
  selectDataSource,
  selectQuality,
  openDownloadDrawer,
  assertConsoleClean,
  shot,
} from './lib/helpers.js'

const _DRAWER_OPEN = '.ant-drawer-open'

// 单首下载：对每个平台都测一遍
for (const platform of PLATFORMS) {
  for (const quality of [QUALITIES[2]]) {  // 仅 lossless，避免 12 倍冗余
    test(`下载 - ${platform.name} × ${quality.label} 单曲`, async ({ context }) => {
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
      await selectQuality(page, quality.label)
      await selectDataSource(page, platform.id)
      await performSearch(page, platform.query, { timeout: 90_000 })

      // 点击第一行的下载按钮（第二按钮，播放是第一个）
      const downloadBtn = page.locator('.tracks-table tbody tr.track-row').first().locator('button').nth(1)
      await downloadBtn.click()

      // 下载队列抽屉应自动打开（addTask 后调用 openDrawer）
      await page.locator(_DRAWER_OPEN).first().waitFor({ state: 'visible', timeout: 15_000 })
      // 至少一个 task card
      const taskCard = page.locator('.task-card').first()
      await taskCard.waitFor({ state: 'visible', timeout: 15_000 })
      await shot(page, `04-download-single-${platform.id}`)

      // 等待任务完成或失败
      await expect(async () => {
        const status = await page.locator('.task-card .ant-tag').first().textContent()
        expect(['已完成', '失败', '已取消'].some((s) => status.includes(s))).toBe(true)
      }).toPass({ timeout: 90_000, intervals: [2_000] })

      const clean = assertConsoleClean(instrument, `04-download-${platform.id}`)
      expect(clean.consoleErrors, `console error`).toHaveLength(0)
    })
  }
}

test('下载 - 批量下载（选择模式）', async ({ context }) => {
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
  await selectDataSource(page, 'netease')
  await performSearch(page, '周杰伦', { timeout: 90_000 })

  // 进入选择模式
  await page.locator('button').filter({ hasText: '批量操作' }).first().click()
  // 勾选前 3 首
  const checkboxes = page.locator('.tracks-table tbody .ant-checkbox-input')
  await checkboxes.nth(0).check({ force: true })
  await checkboxes.nth(1).check({ force: true })
  await checkboxes.nth(2).check({ force: true })
  await shot(page, '04-download-batch-select')
  // 点击下载按钮
  await page.locator('button').filter({ hasText: /^下载$/ }).first().click()
  // 队列抽屉出现
  await page.locator(_DRAWER_OPEN).first().waitFor({ state: 'visible', timeout: 15_000 })
  await page.locator('.task-card').first().waitFor({ state: 'visible', timeout: 15_000 })
})

test('下载 - 队列抽屉打开/关闭', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openDownloadDrawer(page)
  await expect(page.locator(_DRAWER_OPEN).first()).toBeVisible()
  await shot(page, '04-download-drawer-empty')
  // 关闭（download drawer 也用 "关 闭" 文本）
  await page.locator(`${_DRAWER_OPEN} .drawer-footer button`).filter({ hasText: /关\s*闭/ }).first().click()
  await page.waitForTimeout(800)
})