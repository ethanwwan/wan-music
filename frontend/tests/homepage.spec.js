/**
 * 首页测试用例
 * 
 * TC-HOME-001: 页面加载
 * TC-HOME-002: 导航栏展示
 * TC-HOME-003: 搜索框功能
 * TC-HOME-004: 页脚展示
 * TC-HOME-005: 系统公告
 */

import { test, expect } from '@playwright/test'
import {
  BASE_URL,
  waitForPageLoad,
  waitForElementVisible,
  clickElement,
  typeText,
  verifyPageTitle,
  verifyElementText,
  verifyElementVisible,
} from './utils/helpers.js'

test.describe('首页测试', () => {
  test('TC-HOME-001: 页面加载', async ({ page }) => {
    await page.goto(BASE_URL)
    await waitForPageLoad(page)
    
    await verifyPageTitle(page, '网易云音乐解析工具')
  })

  test('TC-HOME-002: 导航栏展示', async ({ page }) => {
    await page.goto(BASE_URL)
    await waitForPageLoad(page)
    
    await verifyElementVisible(page, '.hero-header')
    await verifyElementVisible(page, '.search-container')
  })

  test('TC-HOME-003: 搜索框功能', async ({ page }) => {
    await page.goto(BASE_URL)
    await waitForPageLoad(page)
    
    const searchInput = 'input[placeholder*="请输入"]'
    await waitForElementVisible(page, searchInput)
    
    await typeText(page, searchInput, '周杰伦')
    
    const inputValue = await page.inputValue(searchInput)
    expect(inputValue).toBe('周杰伦')
  })

  test('TC-HOME-004: 页脚展示', async ({ page }) => {
    await page.goto(BASE_URL)
    await waitForPageLoad(page)
    
    await page.evaluate(() => {
      window.scrollTo(0, 2000)
    })
    
    await verifyElementVisible(page, '.footer')
    await verifyElementText(page, '.footer', '版权')
  })

  test('TC-HOME-005: 系统公告', async ({ page }) => {
    await page.goto(BASE_URL)
    await waitForPageLoad(page)
    
    await verifyElementVisible(page, '.system-notice')
  })
})