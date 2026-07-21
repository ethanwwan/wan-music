/**
 * 01 - 烟雾测试：页面加载、关键元素渲染、平台列表加载
 */
import { test, expect } from '@playwright/test'
import { createInstrumentedPage, PLATFORMS, assertConsoleClean, shot } from './lib/helpers.js'

test.describe('01 - 烟雾测试', () => {
  test('页面加载、关键 UI 渲染', async ({ context }) => {
    const { page, consoleErrors, pageErrors } = await createInstrumentedPage(context)
    await page.goto('/')
    // 标题
    await expect(page).toHaveTitle(/Wan Music/)
    // 主标题
    await expect(page.locator('.hero-title')).toContainText('Wan Music')
    // 输入框
    await expect(page.locator('.input-row .ant-input').first()).toBeVisible()
    // 搜索按钮
    await expect(page.locator('.input-row button.ant-btn-primary')).toBeVisible()
    // 设置按钮
    await expect(page.locator('.settings-btn')).toBeVisible()
    // 队列按钮
    await expect(page.locator('.queue-btn')).toBeVisible()

    // 等待平台列表加载完成（下拉非禁用状态）
    await page.waitForFunction(
      () => {
        const sel = document.querySelector('.input-row .ant-select')
        return sel && !sel.classList.contains('ant-select-disabled')
      },
      { timeout: 15_000 },
    )
    await shot(page, '01-smoke-loaded')

    const clean = assertConsoleClean({ consoleErrors, pageErrors }, '01-smoke')
    expect(clean.consoleErrors, `页面加载有 console error: ${JSON.stringify(clean.consoleErrors, null, 2)}`).toHaveLength(0)
    expect(clean.pageErrors, `页面加载有未捕获异常`).toHaveLength(0)
  })

  test('平台下拉包含全部 4 个平台', async ({ context }) => {
    const { page } = await createInstrumentedPage(context)
    await page.goto('/')
    await page.waitForFunction(
      () => {
        const sel = document.querySelector('.input-row .ant-select')
        return sel && !sel.classList.contains('ant-select-disabled')
      },
      { timeout: 15_000 },
    )
    await page.locator('.input-row .ant-select').first().click()
    for (const p of PLATFORMS) {
      await expect(page.locator('.ant-select-item-option').filter({ hasText: p.name }).first()).toBeVisible()
    }
    await page.keyboard.press('Escape')
  })
})