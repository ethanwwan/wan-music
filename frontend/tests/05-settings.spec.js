/**
 * 05 - 设置面板测试
 * 验证设置面板打开/关闭、字段持久化、所有设置项可改
 *
 * 注意：Ant Design Vue 4 的 drawer 通过 portal 渲染到 body，
 * 实际 DOM 中 .ant-drawer 元素不在 .settings-drawer 内部，
 * 所以选择器直接用 .ant-drawer-open 来定位可见的 drawer。
 */
import { test, expect } from '@playwright/test'
import {
  createInstrumentedPage,
  openSettings,
  closeSettings,
  assertConsoleClean,
  shot,
} from './lib/helpers.js'

// 选中"已打开的 drawer"
const drawer = () => ({ drawer: null })  // placeholder
const _DRAWER_SEL = '.ant-drawer-open'

test('设置 - 打开/关闭面板', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  await expect(page.locator(_DRAWER_SEL).first()).toBeVisible()
  await expect(page.locator('.settings-content')).toBeVisible()
  await shot(page, '05-settings-open')
  await closeSettings(page)
  await page.waitForTimeout(500)
})

test('设置 - 全部音质选项可见', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  const qualitySelect = page.locator(`${_DRAWER_SEL} .ant-form-item`).filter({ hasText: '默认音质' }).locator('.ant-select')
  await qualitySelect.click()
  for (const label of ['标准', '极高', '无损']) {
    await expect(page.locator('.ant-select-item-option').filter({ hasText: label }).first()).toBeVisible()
  }
  await page.keyboard.press('Escape')
  await closeSettings(page)
})

test('设置 - 切换音质后刷新页面应保留设置', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  const qualitySelect = page.locator(`${_DRAWER_SEL} .ant-form-item`).filter({ hasText: '默认音质' }).locator('.ant-select')
  await qualitySelect.click()
  await page.locator('.ant-select-item-option').filter({ hasText: '标准音质' }).first().click()
  await page.waitForTimeout(500)
  await closeSettings(page)

  const stored = await page.evaluate(() => localStorage.getItem('app-settings'))
  expect(stored).toContain('"selectedQuality":"standard"')

  await page.reload()
  await openSettings(page)
  const displayedLabel = await page.locator(`${_DRAWER_SEL} .ant-form-item`).filter({ hasText: '默认音质' })
    .locator('.ant-select-selection-item').textContent()
  expect(displayedLabel).toContain('标准')
  await closeSettings(page)
})

test('设置 - 切换线路后持久化', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  const lineSelect = page.locator(`${_DRAWER_SEL} .ant-form-item`).filter({ hasText: '接口线路' }).locator('.ant-select')
  await lineSelect.click()
  await page.locator('.ant-select-item-option').filter({ hasText: '线路二' }).first().click()
  await page.waitForTimeout(500)
  const stored = await page.evaluate(() => localStorage.getItem('app-settings'))
  expect(stored).toContain('"musicLine":1')
  await closeSettings(page)
})

test('设置 - 切换文件命名格式', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  const fmtSelect = page.locator(`${_DRAWER_SEL} .ant-form-item`).filter({ hasText: '文件命名格式' }).locator('.ant-select')
  await fmtSelect.click()
  await page.locator('.ant-select-item-option').filter({ hasText: '仅歌曲名' }).first().click()
  await page.waitForTimeout(500)
  const stored = await page.evaluate(() => localStorage.getItem('app-settings'))
  expect(stored).toContain('"filenameFormat":"song-only"')
  await closeSettings(page)
})

test('设置 - 元数据开关初始为开', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  const switchEl = page.locator(`${_DRAWER_SEL} .ant-form-item`).filter({ hasText: '自动写入元数据' }).locator('.ant-switch')
  const before = await switchEl.getAttribute('aria-checked')
  expect(before).toBe('true')
  await closeSettings(page)
})

test('设置 - 缓存开关初始为开', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  const switchEl = page.locator(`${_DRAWER_SEL} .ant-form-item`).filter({ hasText: '启用缓存' }).locator('.ant-switch')
  const before = await switchEl.getAttribute('aria-checked')
  expect(before).toBe('true')
  await closeSettings(page)
})

test('设置 - 缓存大小有显示', async ({ context }) => {
  const { page } = await createInstrumentedPage(context)
  await page.goto('/')
  await openSettings(page)
  await expect(page.locator(`${_DRAWER_SEL} .size-text`)).toBeVisible()
  await closeSettings(page)
})

test('设置 - 控制台干净', async ({ context }) => {
  const instrument = await createInstrumentedPage(context)
  const { page } = instrument
  await page.goto('/')
  await openSettings(page)
  await closeSettings(page)
  const clean = assertConsoleClean(instrument, '05-settings')
  expect(clean.consoleErrors).toHaveLength(0)
})