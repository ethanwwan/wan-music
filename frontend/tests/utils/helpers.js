/**
 * 测试辅助函数
 */

import { expect } from '@playwright/test'

export const BASE_URL = 'http://localhost:5173'
export const API_BASE_URL = 'http://localhost:5002'

export const TEST_CONFIG = {
  BASE_URL: 'http://localhost:5173',
  API_BASE_URL: 'http://localhost:5002',
  TIMEOUT: 10000,
  SHORT_TIMEOUT: 2000,
}

export const TEST_DATA = {
  keywords: {
    song: '周杰伦',
    playlist: '华语经典',
    album: '范特西',
    artist: '周杰伦',
  },
}

export const TestHelpers = {
  async waitForPageReady(page) {
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
  },

  async fillAndSubmitSearch(page, keyword) {
    const searchInput = page.locator('input[placeholder*="请输入"]')
    await searchInput.waitFor()
    await searchInput.fill(keyword)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)
  },

  async switchToTab(page, tabName) {
    const tab = page.locator('.ant-tabs-tab', { hasText: tabName })
    await tab.waitFor()
    await tab.click()
    await page.waitForTimeout(1000)
  },

  async verifyElementVisible(locator, name) {
    await locator.waitFor({ state: 'visible' })
    const isVisible = await locator.isVisible()
    expect(isVisible).toBe(true)
    console.log(`✓ ${name} 可见`)
  },

  async waitForElementVisible(page, selector, timeout = 10000) {
    await page.waitForSelector(selector, { visible: true, timeout })
  },

  async clickElement(page, selector) {
    await this.waitForElementVisible(page, selector)
    await page.click(selector)
  },

  async typeText(page, selector, text) {
    await this.waitForElementVisible(page, selector)
    await page.fill(selector, text)
  },

  async getElementText(page, selector) {
    await this.waitForElementVisible(page, selector)
    return page.textContent(selector)
  },

  async verifyPageTitle(page, expectedTitle) {
    const title = await page.title()
    expect(title).toContain(expectedTitle)
  },

  async verifyElementText(page, selector, expectedText) {
    const text = await this.getElementText(page, selector)
    expect(text).toContain(expectedText)
  },
}

/**
 * 等待页面加载完成
 */
export const waitForPageLoad = async (page) => {
  await page.waitForLoadState('networkidle')
}

/**
 * 检查元素可见
 */
export const waitForElementVisible = async (page, selector, timeout = 10000) => {
  await page.waitForSelector(selector, { visible: true, timeout })
}

/**
 * 检查元素存在
 */
export const waitForElementExists = async (page, selector, timeout = 10000) => {
  await page.waitForSelector(selector, { timeout })
}

/**
 * 检查元素不可见
 */
export const waitForElementHidden = async (page, selector, timeout = 10000) => {
  await page.waitForSelector(selector, { state: 'hidden', timeout })
}

/**
 * 点击元素
 */
export const clickElement = async (page, selector) => {
  await waitForElementVisible(page, selector)
  await page.click(selector)
}

/**
 * 输入文本
 */
export const typeText = async (page, selector, text) => {
  await waitForElementVisible(page, selector)
  await page.fill(selector, text)
}

/**
 * 获取元素文本
 */
export const getElementText = async (page, selector) => {
  await waitForElementVisible(page, selector)
  return page.textContent(selector)
}

/**
 * 验证页面标题
 */
export const verifyPageTitle = async (page, expectedTitle) => {
  const title = await page.title()
  expect(title).toContain(expectedTitle)
}

/**
 * 验证元素文本
 */
export const verifyElementText = async (page, selector, expectedText) => {
  const text = await getElementText(page, selector)
  expect(text).toContain(expectedText)
}

/**
 * 验证元素可见
 */
export const verifyElementVisible = async (page, selector) => {
  const isVisible = await page.isVisible(selector)
  expect(isVisible).toBe(true)
}

/**
 * 验证元素不可见
 */
export const verifyElementHidden = async (page, selector) => {
  const isVisible = await page.isVisible(selector)
  expect(isVisible).toBe(false)
}

/**
 * 验证元素包含指定数量的子元素
 */
export const verifyElementCount = async (page, selector, expectedCount) => {
  const count = await page.locator(selector).count()
  expect(count).toBe(expectedCount)
}

/**
 * 验证元素数量大于0
 */
export const verifyElementCountGreaterThanZero = async (page, selector) => {
  const count = await page.locator(selector).count()
  expect(count).toBeGreaterThan(0)
}

/**
 * API请求测试辅助函数
 */
export const apiRequest = async (method, endpoint, data = {}) => {
  const url = `${API_BASE_URL}${endpoint}`
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  }
  
  if (method !== 'GET') {
    options.body = JSON.stringify(data)
  }
  
  const response = await fetch(url, options)
  return {
    status: response.status,
    json: await response.json(),
  }
}

/**
 * 验证API响应成功
 */
export const verifyApiSuccess = (response) => {
  expect(response.status).toBe(200)
  expect(response.json.success).toBe(true)
}

/**
 * 验证API响应失败
 */
export const verifyApiError = (response, expectedStatus = 400) => {
  expect(response.status).toBe(expectedStatus)
  expect(response.json.success).toBe(false)
}

/**
 * 生成随机字符串
 */
export const generateRandomString = (length = 10) => {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * 等待一段时间
 */
export const wait = async (ms) => {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * 截图
 */
export const takeScreenshot = async (page, name) => {
  await page.screenshot({ path: `tests/screenshots/${name}.png` })
}