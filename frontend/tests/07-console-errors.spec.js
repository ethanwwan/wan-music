/**
 * 07 - Console / 网络错误监控
 * 专门检测：浏览器层 ERR_EMPTY_RESPONSE / ERR_ABORTED / 404 / 5xx / 跨域等
 */
import { test, expect } from '@playwright/test'
import { createInstrumentedPage, performSearch } from './lib/helpers.js'

test('网络 - 无 ERR_EMPTY_RESPONSE / ECONNREFUSED', async ({ context }) => {
  const instrument = await createInstrumentedPage(context)
  const { page, failedRequests, consoleErrors } = instrument

  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )

  // 执行一次搜索
  await performSearch(page, '周杰伦', { timeout: 90_000 })

  // 失败的请求：忽略 favicon（开发环境常见）
  const realFailures = failedRequests.filter(
    (r) => !r.url.includes('favicon') && !r.url.endsWith('.map'),
  )
  if (realFailures.length > 0) {
    console.log('失败请求:', JSON.stringify(realFailures, null, 2))
  }
  expect(realFailures, `有失败的网络请求`).toHaveLength(0)

  // 控制台错误
  const realErrs = consoleErrors.filter((e) => !/Failed to load resource/i.test(e.text))
  if (realErrs.length > 0) {
    console.log('控制台错误:', realErrs.map((e) => e.text).slice(0, 5))
  }
  expect(realErrs).toHaveLength(0)
})

test('网络 - API 响应均为 2xx', async ({ context }) => {
  const instrument = await createInstrumentedPage(context)
  const { page, apiResponses } = instrument
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )

  await performSearch(page, '周杰伦', { timeout: 90_000 })

  // 检查所有 api 响应
  const badResp = apiResponses.filter((r) => r.status >= 400)
  if (badResp.length > 0) {
    console.log('4xx/5xx 响应:', JSON.stringify(badResp, null, 2))
  }
  expect(badResp).toHaveLength(0)
})

test('网络 - 封面图代理（/image）正常', async ({ context }) => {
  const instrument = await createInstrumentedPage(context)
  const { page, apiResponses } = instrument
  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 15_000 },
  )
  await performSearch(page, '周杰伦', { timeout: 90_000 })
  // 等待 3s 让图片代理请求完成
  await page.waitForTimeout(3000)
  const imageProxies = apiResponses.filter((r) => r.url.includes('/image'))
  console.log(`封面代理请求: ${imageProxies.length} 条`)
  // 至少有一些封面图请求（如果后端能加载）
  // 不强制断言数量（取决于歌曲是否有封面），但若有则全部 2xx
  const badImage = imageProxies.filter((r) => r.status >= 400)
  expect(badImage).toHaveLength(0)
})