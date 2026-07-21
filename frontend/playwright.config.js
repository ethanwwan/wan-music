/**
 * Playwright 测试配置
 * Wan Music 前端 UI 全自动化测试
 */

import { defineConfig, devices } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:5175'
const HEADLESS = process.env.HEADFUL !== '1'

export default defineConfig({
  testDir: './tests',
  // 不限制测试目录后缀，跑所有 *.spec.js
  testMatch: /.*\.spec\.js$/,
  // 单线程运行，避免后端并发争用；超时设长一些（部分平台搜索耗时较大）
  fullyParallel: false,
  workers: 1,
  // 失败时自动重试 1 次（排除已知网络抖动）
  retries: 0,
  // 测试报告
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/report/html', open: 'never' }],
    ['json', { outputFile: 'tests/report/results.json' }],
  ],
  // 全局超时
  timeout: 120_000,
  expect: { timeout: 15_000 },

  use: {
    baseURL: BASE_URL,
    headless: HEADLESS,
    viewport: { width: 1366, height: 900 },
    // 默认禁用动画，提升稳定性
    actionTimeout: 20_000,
    navigationTimeout: 30_000,
    // 收集控制台输出和页面错误，供测试断言
    // 注意：通过 page.on('console') 在每个测试中独立收集
    screenshot: 'only-on-failure',
    video: 'off',
    trace: 'retain-on-failure',
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',  // 复用系统 Chrome，更贴近真实用户
      },
    },
  ],

  // 后端启动慢，前置检测一下避免假阳性
  globalSetup: undefined,
})