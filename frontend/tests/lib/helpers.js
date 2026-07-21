/**
 * 测试辅助工具
 * 封装常用操作、监听器、断言
 */
import { expect } from '@playwright/test'

// 平台配置（与后端 /config 接口对齐）
export const PLATFORMS = [
  { id: 'netease', name: '网易云音乐', query: '周杰伦' },
  { id: 'qq', name: 'QQ音乐', query: '邓紫棋' },
  { id: 'kugou', name: '酷狗音乐', query: '薛之谦' },
  { id: 'kuwo', name: '酷我音乐', query: '林俊杰' },
]

// 音质档位（label 与后端 /config 接口一致：超清母带 / Hi-Res / 无损 / 极高 / 标准）
export const QUALITIES = [
  { value: 'standard', label: '标准' },
  { value: 'exhigh', label: '极高' },
  { value: 'lossless', label: '无损' },
]

// 已知的安全可忽略的 console 消息（vite HMR / dev server 的杂项提示）
const CONSOLE_IGNORE_PATTERNS = [
  /Download the Vue Devtools extension/i,
  /\[vite\] (connecting|connected)/i,
  // vite proxy ECONNREFUSED 是后端未就绪触发的，开发期可接受，但测试前我们确保后端已就绪
  // 真正的 ERR_EMPTY_RESPONSE / Failed to fetch 必须被检测
]

/**
 * 创建一个新的 page，注入监听器收集 console/pageerror/response
 */
export async function createInstrumentedPage(context) {
  const page = await context.newPage()
  const consoleErrors = []
  const consoleWarnings = []
  const consoleAll = []
  const pageErrors = []
  const failedRequests = []
  const apiRequests = []
  const apiResponses = []

  page.on('console', (msg) => {
    const entry = { type: msg.type(), text: msg.text(), location: msg.location() }
    consoleAll.push(entry)
    if (msg.type() === 'error') consoleErrors.push(entry)
    if (msg.type() === 'warning') consoleWarnings.push(entry)
  })
  page.on('pageerror', (err) => {
    pageErrors.push({ message: err.message, stack: err.stack })
  })
  page.on('requestfailed', (req) => {
    const failure = req.failure()
    failedRequests.push({
      url: req.url(),
      method: req.method(),
      failure: failure ? failure.errorText : 'unknown',
    })
  })
  page.on('response', async (resp) => {
    const url = resp.url()
    if (url.includes('/search') || url.includes('/song') || url.includes('/platforms') ||
        url.includes('/config') || url.includes('/download') || url.includes('/image')) {
      apiRequests.push({ url, method: resp.request().method(), status: resp.status() })
      // 收集少量响应体便于排查
      try {
        const ct = resp.headers()['content-type'] || ''
        if (ct.includes('json')) {
          const data = await resp.json()
          apiResponses.push({ url, status: resp.status(), dataPreview: JSON.stringify(data).slice(0, 500) })
        }
      } catch { /* ignore */ }
    }
  })

  return {
    page,
    consoleErrors,
    consoleWarnings,
    consoleAll,
    pageErrors,
    failedRequests,
    apiRequests,
    apiResponses,
  }
}

/**
 * 过滤掉已知的"可忽略"console 噪音
 */
export function filterConsoleErrors(errors) {
  return errors.filter((e) => {
    return !CONSOLE_IGNORE_PATTERNS.some((re) => re.test(e.text))
  })
}

/**
 * 等待搜索结果行出现
 */
export async function waitForSearchResults(page, { minRows = 1, timeout = 60_000 } = {}) {
  // 等待表格行或空状态出现
  const row = page.locator('.tracks-table tbody tr.track-row').first()
  const empty = page.locator('.ant-empty')
  await Promise.race([
    row.waitFor({ state: 'visible', timeout }).catch(() => {}),
    empty.waitFor({ state: 'visible', timeout }).catch(() => {}),
  ])
  const rowCount = await page.locator('.tracks-table tbody tr.track-row').count()
  return rowCount
}

/**
 * 截图辅助
 */
export async function shot(page, name) {
  await page.screenshot({ path: `tests/screenshots/${name}.png`, fullPage: true })
}

/**
 * 打开设置面板
 * 注意：Ant Design Vue 4 的 drawer 通过 portal 渲染到 body，
 * 所以选择器直接用 .ant-drawer 而非 .settings-drawer .ant-drawer-content
 */
export async function openSettings(page) {
  await page.locator('.settings-btn').click()
  // 等 drawer 出现 + open class
  await page.locator('.ant-drawer-open').first().waitFor({ state: 'visible', timeout: 10_000 })
  // 抽屉里包含 settings-content 才算打开成功
  await page.locator('.settings-content').waitFor({ state: 'visible', timeout: 10_000 })
}

/**
 * 关闭设置面板
 */
export async function closeSettings(page) {
  // 关闭按钮（drawer 里的关闭按钮，文本是 "关 闭" 带空格）
  const btn = page.locator('.ant-drawer-open .drawer-footer button').filter({ hasText: /关\s*闭/ }).first()
  if (await btn.isVisible().catch(() => false)) {
    await btn.click()
  } else {
    await page.locator('.ant-drawer-open .ant-drawer-close').click().catch(() => {})
  }
  // 等 drawer 关闭
  await page.waitForTimeout(800)
}

/**
 * 打开下载队列抽屉
 */
export async function openDownloadDrawer(page) {
  await page.locator('.queue-btn').click()
  await page.locator('.download-drawer .ant-drawer-open, .ant-drawer-open').first().waitFor({ state: 'visible', timeout: 10_000 })
  // 等空状态或 task card
  await page.waitForTimeout(500)
}

/**
 * 在设置面板选择音质
 */
export async function selectQuality(page, qualityLabel) {
  await openSettings(page)
  // 音质下拉（在 .ant-drawer-open 容器里找 ant-form-item 包含 "默认音质"）
  const drawer = page.locator('.ant-drawer-open').first()
  const qualityItem = drawer.locator('.ant-form-item').filter({ hasText: '默认音质' })
  const qualitySelect = qualityItem.locator('.ant-select').first()
  await qualitySelect.click()
  await page.locator('.ant-select-item-option').filter({ hasText: qualityLabel }).first().click()
  await page.waitForTimeout(500)
  await closeSettings(page)
}

/**
 * 选择数据源（顶部搜索框旁的下拉）
 */
export async function selectDataSource(page, platformId) {
  const select = page.locator('.input-row .ant-select').first()
  await select.click()
  const opt = page.locator('.ant-select-item-option').filter({ hasText: new RegExp(getPlatformName(platformId)) })
  await opt.first().click()
  await page.waitForTimeout(300)
}

export function getPlatformName(id) {
  return PLATFORMS.find((p) => p.id === id)?.name || id
}

/**
 * 触发搜索并等待结果
 * 注意：Ant Design Vue 4 自动给单字之间加空格（"搜 索"），
 * 所以 hasText 用正则匹配，避免硬编码空格
 */
export async function performSearch(page, keyword, { waitRows = 1, timeout = 60_000 } = {}) {
  const input = page.locator('.input-row .ant-input').first()
  await input.fill('')
  await input.fill(keyword)
  await page.locator('.input-row button.ant-btn-primary').filter({ hasText: /搜\s*索/ }).click()
  return waitForSearchResults(page, { minRows: waitRows, timeout })
}

/**
 * 断言 console 干净（核心断言）
 */
export function assertConsoleClean(instrument, label) {
  const realErrors = filterConsoleErrors(instrument.consoleErrors)
  if (realErrors.length > 0) {
    console.log(`\n❌ [${label}] 控制台错误 ${realErrors.length} 条:`)
    realErrors.slice(0, 10).forEach((e, i) => {
      console.log(`  ${i + 1}. ${e.text.slice(0, 200)}`)
    })
  }
  const realPageErrors = instrument.pageErrors.filter((e) => !e.message.includes('AbortError'))
  if (realPageErrors.length > 0) {
    console.log(`\n❌ [${label}] 未捕获异常 ${realPageErrors.length} 条:`)
    realPageErrors.slice(0, 5).forEach((e, i) => {
      console.log(`  ${i + 1}. ${e.message.slice(0, 200)}`)
    })
  }
  return {
    consoleErrors: realErrors,
    pageErrors: realPageErrors,
  }
}

export { expect }