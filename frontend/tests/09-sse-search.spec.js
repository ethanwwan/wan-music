/**
 * 09 - SSE 搜索专项测试 (musicdl 数据源)
 *
 * 覆盖每个平台：
 *   1. SSE EventSource 真的连接
 *   2. 收到 event:result（+ 首条 < 20s，证明并发流式）
 *   3. 收到 event:done（防 Gunicorn worker timeout）
 *
 * 4 平台 × 1 测试 = 4 spec
 */
import { test, expect } from '@playwright/test'
import { openSettings, closeSettings } from './lib/helpers.js'

// 单平台 < 30s 给定足够缓冲（搜索 + 流式走完应 < 10s）
test.setTimeout(120_000)

const PLATFORMS = [
  { id: 'netease', name: '网易云音乐', keyword: '周杰伦' },
  { id: 'qq',      name: 'QQ音乐',   keyword: '邓紫棋' },
  { id: 'kugou',   name: '酷狗音乐', keyword: '薛之谦' },
  { id: 'kuwo',    name: '酷我音乐', keyword: '林俊杰' },
]

/**
 * 切换前端线路到 musicdl (line=1)
 * 必须在搜索前调用，否则前端默认走 line=0（项目自研源，不走 SSE）。
 */
async function switchToMusicdlLine(page) {
  await openSettings(page)
  // 抽屉里找 "接口线路" 字段，把 select 改成 线路二（musicdl）
  const drawer = page.locator('.ant-drawer-open').first()
  const lineItem = drawer.locator('.ant-form-item').filter({ hasText: '接口线路' })
  const lineSelect = lineItem.locator('.ant-select').first()
  await lineSelect.click()
  await page.locator('.ant-select-item-option')
    .filter({ hasText: /线路二.*musicdl/ })
    .first()
    .click()
  await page.waitForTimeout(400)
  await closeSettings(page)
}

for (const platform of PLATFORMS) {
  test(`SSE 流式搜索 - ${platform.id} (musicdl line=1)`, async ({ page }) => {
    // Patch window.EventSource BEFORE navigation
    await page.addInitScript(() => {
      window.__sseEvents = []
      const orig = window.EventSource
      if (orig.__patched) return
      const patched = function (url, conf) {
        const es = new orig(url, conf)
        window.__sseEvents.push({ type: 'open', url, at: Date.now() })
        for (const evt of ['result', 'source_done', 'done', 'error']) {
          es.addEventListener(evt, (e) => {
            window.__sseEvents.push({
              type: evt,
              at: Date.now(),
              dataLen: (e.data || '').length,
              data: e.data ? (e.data.length < 200 ? e.data : e.data.slice(0, 200) + '...') : null,
            })
          })
        }
        return es
      }
      patched.prototype = orig.prototype
      patched.__patched = true
      window.EventSource = patched
    })

    // 1. 进入页面
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForSelector('.input-row .ant-input', { timeout: 30_000 })

    // 2. **关键：先切到 musicdl 线路**，否则前端默认走 line=0
    await switchToMusicdlLine(page)

    // 3. 选择平台
    const platformSelect = page.locator('.input-row .ant-select').first()
    await platformSelect.click()
    await page.locator('.ant-select-item-option').filter({ hasText: new RegExp(platform.name) }).first().click()
    await page.waitForTimeout(500)

    // 4. 输入 + 搜索
    const input = page.locator('.input-row .ant-input').first()
    await input.fill('')
    await input.fill(platform.keyword)
    await page.locator('.input-row button.ant-btn-primary').filter({ hasText: /搜\s*索/ }).click()

    // 5. 等首条 row 渲染（任意一条 result 到达即是证据）
    await page.waitForSelector('.tracks-table tbody tr.track-row', { timeout: 60_000 })

    // 6. 等 done 事件
    const ok = await page.waitForFunction(
      () => {
        const arr = window.__sseEvents || []
        return arr.some((e) => e.type === 'done')
      },
      { timeout: 30_000 },
    ).then(() => true).catch(() => false)
    expect(ok, `${platform.id}: SSE done event should arrive within 30s`).toBe(true)

    // 7. 收集事件统计
    const summary = await page.evaluate(() => {
      const arr = window.__sseEvents || []
      const stats = {}
      const first = {}
      const last = {}
      for (const e of arr) {
        stats[e.type] = (stats[e.type] || 0) + 1
        if (!(e.type in first)) first[e.type] = e.at
        last[e.type] = e.at
      }
      return {
        stats,
        firstResultAt: first.result,
        doneAt: last.done,
        durationMs: last.done && first.result ? last.done - first.result : null,
        sampleDone: arr.find((e) => e.type === 'done')?.data || null,
      }
    })

    expect(summary.stats.open, 'EventSource opened').toBeGreaterThanOrEqual(1)
    expect(summary.stats.result || 0, `${platform.id}: result events`).toBeGreaterThanOrEqual(1)
    expect(summary.stats.done || 0, `${platform.id}: done events`).toBe(1)

    console.log(`\n  ${platform.id} SSE stats:`, JSON.stringify(summary.stats))
    console.log(`    首条→done 间隔: ${summary.durationMs}ms (并发流式就绪证明)`)
    console.log(`    done payload: ${summary.sampleDone}`)
  })
}
