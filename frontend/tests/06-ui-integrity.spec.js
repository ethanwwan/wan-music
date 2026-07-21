/**
 * 06 - UI 整体完整性测试
 * 检查：移动端响应式 / 深色模式 / 无障碍 / 视觉无错位
 */
import { test, expect } from '@playwright/test'
import { createInstrumentedPage, shot, performSearch } from './lib/helpers.js'

test('UI - 移动端响应式布局（375x812）', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  await shot(page, '06-ui-mobile-home')

  // 验证输入行是 column 布局（移动端）
  const flexDir = await page.locator('.input-row').evaluate((el) => getComputedStyle(el).flexDirection)
  expect(flexDir).toBe('column')
})

test('UI - 平板响应式布局（768x1024）', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.setViewportSize({ width: 768, height: 1024 })
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  await shot(page, '06-ui-tablet-home')
})

test('UI - 桌面端布局（1366x900）', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.setViewportSize({ width: 1366, height: 900 })
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  // 输入行应为 row 布局（桌面端）
  const flexDir = await page.locator('.input-row').evaluate((el) => getComputedStyle(el).flexDirection)
  expect(flexDir).toBe('row')
  await shot(page, '06-ui-desktop-home')
})

test('UI - 搜索结果无横向溢出', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  await performSearch(page, '周杰伦', { timeout: 90_000 })
  // 表格 wrapper 应可横向滚动，但页面不溢出
  const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth)
  const viewportWidth = await page.evaluate(() => window.innerWidth)
  // 允许 5px 误差
  expect(bodyScrollWidth).toBeLessThanOrEqual(viewportWidth + 5)
  await shot(page, '06-ui-search-results')
})

test('UI - footer 可见且包含版权信息', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await expect(page.locator('footer')).toContainText('Wan Music')
})

test('UI - 历史记录功能', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  await performSearch(page, '周杰伦', { timeout: 90_000 })
  // 历史记录应出现
  const historyTags = page.locator('.history-tag')
  await expect(historyTags.first()).toBeVisible({ timeout: 5_000 })
  await shot(page, '06-ui-history')

  // 点击历史 tag
  const tagText = await historyTags.first().textContent()
  await historyTags.first().click()
  await page.waitForTimeout(500)
  // 输入框填入了历史 URL
  const inputValue = await page.locator('.input-row .ant-input').first().inputValue()
  expect(inputValue.length).toBeGreaterThan(0)

  // 清除历史
  await page.locator('button').filter({ hasText: '清除历史' }).click()
  await page.waitForTimeout(300)
  await expect(historyTags).toHaveCount(0)
})