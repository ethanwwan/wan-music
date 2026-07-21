/**
 * 自定义测试 runner：
 * - 不用 @playwright/test 的 CLI
 * - 用 playwright 库直跑
 * - 跨 spec 文件汇总 console error
 *
 * 用法：node tests/quick-run.js
 */
const path = require('path')
const fs = require('fs')

// 切到 frontend 目录跑（require 路径更简单）
process.chdir(path.resolve(__dirname, '..'))

const { chromium } = require('playwright')

const BASE_URL = process.env.BASE_URL || 'http://localhost:5175'

// 测试矩阵
const PLATFORMS = [
  { id: 'netease', name: '网易云音乐', query: '周杰伦' },
  { id: 'qq', name: 'QQ音乐', query: '邓紫棋' },
  { id: 'kugou', name: '酷狗音乐', query: '薛之谦' },
  { id: 'kuwo', name: '酷我音乐', query: '林俊杰' },
]
const QUALITIES = [
  { value: 'standard', label: '标准' },
  { value: 'exhigh', label: '极高' },
  { value: 'lossless', label: '无损' },
]
// 两条线路：0=项目源, 1=musicdl
const LINES = [
  { value: 0, label: '项目源' },
  { value: 1, label: 'musicdl' },
]

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function run() {
  console.log('🚀 Wan Music UI 测试启动')
  console.log(`   BASE_URL: ${BASE_URL}`)
  console.log('')

  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  })

  const summary = {
    total: 0,
    passed: 0,
    failed: 0,
    issues: [],  // 收集所有问题
  }

  // ============== 测试 1: 烟雾 ==============
  console.log('▶ 测试 01 - 烟雾测试')
  {
    const page = await context.newPage()
    const errors = []
    const pageErrors = []
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()) })
    page.on('pageerror', (err) => pageErrors.push(err.message))

    summary.total++
    try {
      await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
      await page.waitForFunction(() => {
        const sel = document.querySelector('.input-row .ant-select')
        return sel && !sel.classList.contains('ant-select-disabled')
      }, { timeout: 15000 })
      const title = await page.title()
      if (!/Wan Music/.test(title)) throw new Error(`标题不正确: ${title}`)
      await page.screenshot({ path: 'tests/screenshots/quick-01-smoke.png', fullPage: true })
      console.log('  ✅ 页面加载成功')

      // console error 检查
      if (errors.length > 0) {
        summary.issues.push({ test: '01-smoke', type: 'console-error', detail: errors })
        throw new Error(`${errors.length} console errors`)
      }
      if (pageErrors.length > 0) {
        summary.issues.push({ test: '01-smoke', type: 'page-error', detail: pageErrors })
        throw new Error(`${pageErrors.length} page errors`)
      }
      summary.passed++
    } catch (e) {
      summary.failed++
      console.log(`  ❌ ${e.message}`)
    }
    await page.close()
  }

  // ============== 测试 2: 搜索矩阵 ==============
  console.log('')
  console.log('▶ 测试 02 - 搜索矩阵 (2线路 × 4平台 × 3音质 = 24 组合)')
  for (const l of LINES) {
    console.log(`  ── 线路: ${l.label} ──`)
    for (const p of PLATFORMS) {
      // musicdl 用更轻量查询（避免 SSE 流超时）；项目源走原查询
      const query = (l.value === 1) ? (p.id === 'netease' ? '周杰伦' : p.id === 'qq' ? '邓紫棋' : p.id === 'kugou' ? '薛之谦' : '林俊杰') : p.query
      for (const q of QUALITIES) {
        const page = await context.newPage()
        const errors = []
        const pageErrors = []
        page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()) })
        page.on('pageerror', (err) => pageErrors.push(err.message))

        summary.total++
        const label = `[${l.label}] ${p.name} × ${q.label}`
        try {
          await page.goto(BASE_URL)
          await page.waitForFunction(() => {
            const sel = document.querySelector('.input-row .ant-select')
            return sel && !sel.classList.contains('ant-select-disabled')
          }, { timeout: 15000 })

          // 设置线路
          await page.locator('.settings-btn').click()
          await page.locator('.ant-drawer-open').first().waitFor({ state: 'visible' })
          await page.locator('.settings-content').waitFor({ state: 'visible' })
          // 接口线路
          const lineSel = page.locator('.ant-drawer-open .ant-form-item').filter({ hasText: '接口线路' }).locator('.ant-select')
          await lineSel.click()
          // 线路一/线路二（可能受字符间距影响）
          const lineOptionText = l.value === 0 ? /线路一/ : /线路二/
          await page.locator('.ant-select-item-option').filter({ hasText: lineOptionText }).first().click()
          await sleep(300)
          // 默认音质
          const qSel = page.locator('.ant-drawer-open .ant-form-item').filter({ hasText: '默认音质' }).locator('.ant-select')
          await qSel.click()
          await page.locator('.ant-select-item-option').filter({ hasText: q.label }).first().click()
          await sleep(400)
          await page.locator('.ant-drawer-open .drawer-footer button').filter({ hasText: /关\s*闭/ }).first().click()
          await sleep(800)

          // 设置平台
          const pSel = page.locator('.input-row .ant-select').first()
          await pSel.click()
          await page.locator('.ant-select-item-option').filter({ hasText: p.name }).first().click()
          await sleep(300)

          // 搜索
          await page.locator('.input-row .ant-input').first().fill(query)
          await page.locator('.input-row button.ant-btn-primary').filter({ hasText: /搜\s*索/ }).click()

          // 等结果（musicdl 流式稍慢，给更多时间）
          const rowCount = await page.locator('.tracks-table tbody tr.track-row').count()
          if (rowCount === 0) {
            await page.waitForSelector('.tracks-table tbody tr.track-row', { timeout: 90000 })
          }
          const finalCount = await page.locator('.tracks-table tbody tr.track-row').count()

          if (finalCount === 0) {
            throw new Error('搜索结果为空')
          }

          const safeP = p.id
          const safeL = l.value
          await page.screenshot({ path: `tests/screenshots/quick-02-search-L${safeL}-${safeP}-${q.value}.png`, fullPage: true })

          // console 干净
          const realErrors = errors.filter((e) => !e.includes('favicon'))
          if (realErrors.length > 0) {
            summary.issues.push({ test: `02-search-L${l.value}-${p.id}-${q.value}`, type: 'console-error', detail: realErrors })
            throw new Error(`${realErrors.length} console errors: ${realErrors[0].slice(0, 100)}`)
          }
          if (pageErrors.length > 0) {
            summary.issues.push({ test: `02-search-L${l.value}-${p.id}-${q.value}`, type: 'page-error', detail: pageErrors })
            throw new Error(`${pageErrors.length} page errors`)
          }
          console.log(`  ✅ ${label} → ${finalCount} 首`)
          summary.passed++
        } catch (e) {
          summary.failed++
          console.log(`  ❌ ${label}: ${e.message}`)
          await page.screenshot({ path: `tests/screenshots/quick-FAIL-02-search-L${l.value}-${p.id}-${q.value}.png`, fullPage: true })
        }
        await page.close()
      }
    }
  }

  // ============== 测试 3: 播放 ==============
  console.log('')
  console.log('▶ 测试 03 - 播放功能')
  for (const p of [PLATFORMS[0], PLATFORMS[1]]) {
    const page = await context.newPage()
    const errors = []
    const pageErrors = []
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()) })
    page.on('pageerror', (err) => pageErrors.push(err.message))

    summary.total++
    try {
      await page.goto(BASE_URL)
      await page.waitForFunction(() => {
        const sel = document.querySelector('.input-row .ant-select')
        return sel && !sel.classList.contains('ant-select-disabled')
      }, { timeout: 15000 })

      // 显式设置线路=0（项目源），避免上一轮 musicdl 残留导致 /song 走 musicdl
      await page.locator('.settings-btn').click()
      await page.locator('.ant-drawer-open').first().waitFor({ state: 'visible' })
      const lineSel = page.locator('.ant-drawer-open .ant-form-item').filter({ hasText: '接口线路' }).locator('.ant-select')
      await lineSel.click()
      await page.locator('.ant-select-item-option').filter({ hasText: /线路一/ }).first().click()
      await sleep(300)
      await page.locator('.ant-drawer-open .drawer-footer button').filter({ hasText: /关\s*闭/ }).first().click()
      await sleep(500)

      // 选平台
      await page.locator('.input-row .ant-select').first().click()
      await page.locator('.ant-select-item-option').filter({ hasText: p.name }).first().click()
      await sleep(300)

      // 搜索
      await page.locator('.input-row .ant-input').first().fill(p.query)
      await page.locator('.input-row button.ant-btn-primary').filter({ hasText: /搜\s*索/ }).click()
      await page.waitForSelector('.tracks-table tbody tr.track-row', { timeout: 90000 })

      // 点击播放
      const firstRow = page.locator('.tracks-table tbody tr.track-row').first()
      // 跳过 unavailable 行：选第一个未标 unavailable 的行
      const rowCount = await page.locator('.tracks-table tbody tr.track-row').count()
      let playableRow = null
      for (let i = 0; i < Math.min(rowCount, 10); i++) {
        const r = page.locator('.tracks-table tbody tr.track-row').nth(i)
        const cls = await r.getAttribute('class') || ''
        if (!cls.includes('unavailable')) { playableRow = r; break }
      }
      if (!playableRow) {
        // 调试：打印前 5 行的 class
        for (let i = 0; i < Math.min(rowCount, 5); i++) {
          const r = page.locator('.tracks-table tbody tr.track-row').nth(i)
          const cls = await r.getAttribute('class') || ''
          const name = await r.locator('.track-name').textContent().catch(() => '?')
          console.log(`     [debug] row ${i}: class="${cls}" name="${(name||'').trim()}"`)
        }
        throw new Error('无可用播放的歌曲')
      }
      await playableRow.locator('button').first().click()
      await page.locator('.mini-player').waitFor({ state: 'visible', timeout: 30000 })

      // hover
      await page.locator('.mini-player').hover()
      await sleep(1000)

      await page.screenshot({ path: `tests/screenshots/quick-03-play-${p.id}.png`, fullPage: true })

      const realPageErrors = pageErrors.filter((e) => !e.includes('AbortError'))
      if (realPageErrors.length > 0) {
        summary.issues.push({ test: `03-play-${p.id}`, type: 'page-error', detail: realPageErrors })
        throw new Error(`${realPageErrors.length} page errors`)
      }
      console.log(`  ✅ ${p.name} 播放正常`)
      summary.passed++
    } catch (e) {
      summary.failed++
      console.log(`  ❌ ${p.name}: ${e.message}`)
    }
    await page.close()
  }

  // ============== 测试 4: 下载（单平台） ==============
  console.log('')
  console.log('▶ 测试 04 - 下载功能（单平台验证）')
  {
    const page = await context.newPage()
    const errors = []
    const pageErrors = []
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()) })
    page.on('pageerror', (err) => pageErrors.push(err.message))

    summary.total++
    try {
      await page.goto(BASE_URL)
      await page.waitForFunction(() => {
        const sel = document.querySelector('.input-row .ant-select')
        return sel && !sel.classList.contains('ant-select-disabled')
      }, { timeout: 15000 })

      // 显式设置线路=0（项目源），避免上一轮 musicdl 残留
      await page.locator('.settings-btn').click()
      await page.locator('.ant-drawer-open').first().waitFor({ state: 'visible' })
      const lineSel = page.locator('.ant-drawer-open .ant-form-item').filter({ hasText: '接口线路' }).locator('.ant-select')
      await lineSel.click()
      await page.locator('.ant-select-item-option').filter({ hasText: /线路一/ }).first().click()
      await sleep(300)
      await page.locator('.ant-drawer-open .drawer-footer button').filter({ hasText: /关\s*闭/ }).first().click()
      await sleep(500)

      // 选 netease
      await page.locator('.input-row .ant-select').first().click()
      await page.locator('.ant-select-item-option').filter({ hasText: '网易云音乐' }).first().click()
      await sleep(300)

      await page.locator('.input-row .ant-input').first().fill('周杰伦')
      await page.locator('.input-row button.ant-btn-primary').filter({ hasText: /搜\s*索/ }).click()
      await page.waitForSelector('.tracks-table tbody tr.track-row', { timeout: 90000 })

      // 点击第一首下载
      await page.locator('.tracks-table tbody tr.track-row').first().locator('button').nth(1).click()
      await page.locator('.ant-drawer-open').first().waitFor({ state: 'visible', timeout: 10000 })
      await page.locator('.ant-drawer-open .task-card').first().waitFor({ state: 'visible', timeout: 10000 })

      await page.screenshot({ path: 'tests/screenshots/quick-04-download.png', fullPage: true })

      const realErrors = errors.filter((e) => !e.includes('favicon') && !e.includes('AbortError'))
      if (realErrors.length > 0) {
        summary.issues.push({ test: '04-download', type: 'console-error', detail: realErrors })
        throw new Error(`${realErrors.length} console errors`)
      }
      if (pageErrors.length > 0) {
        summary.issues.push({ test: '04-download', type: 'page-error', detail: pageErrors })
        throw new Error(`${pageErrors.length} page errors`)
      }
      console.log('  ✅ 下载任务已加入队列')
      summary.passed++
    } catch (e) {
      summary.failed++
      console.log(`  ❌ ${e.message}`)
    }
    await page.close()
  }

  // ============== 测试 5: 设置面板 ==============
  console.log('')
  console.log('▶ 测试 05 - 设置面板')
  {
    const page = await context.newPage()
    const errors = []
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()) })

    summary.total++
    try {
      await page.goto(BASE_URL)
      await page.locator('.settings-btn').click()
      await page.locator('.ant-drawer-open').first().waitFor({ state: 'visible' })

      // 切音质
      const qSel = page.locator('.ant-drawer-open .ant-form-item').filter({ hasText: '默认音质' }).locator('.ant-select')
      await qSel.click()
      await page.locator('.ant-select-item-option').filter({ hasText: /^极高$/ }).first().click()
      await sleep(500)

      const stored = await page.evaluate(() => localStorage.getItem('app-settings'))
      if (!stored.includes('"selectedQuality":"exhigh"')) {
        throw new Error('音质未持久化')
      }

      await page.screenshot({ path: 'tests/screenshots/quick-05-settings.png', fullPage: true })

      await page.locator('.ant-drawer-open .drawer-footer button').filter({ hasText: /关\s*闭/ }).click()
      await sleep(400)

      if (errors.length > 0) {
        summary.issues.push({ test: '05-settings', type: 'console-error', detail: errors })
        throw new Error(`${errors.length} console errors`)
      }
      console.log('  ✅ 设置面板正常 + 持久化')
      summary.passed++
    } catch (e) {
      summary.failed++
      console.log(`  ❌ ${e.message}`)
    }
    await page.close()
  }

  // ============== 测试 6: 响应式 ==============
  console.log('')
  console.log('▶ 测试 06 - 响应式')
  for (const vp of [{ w: 375, h: 812, name: 'mobile' }, { w: 1366, h: 900, name: 'desktop' }]) {
    const page = await context.newPage()
    summary.total++
    try {
      await page.setViewportSize({ width: vp.w, height: vp.h })
      await page.goto(BASE_URL)
      await page.waitForFunction(() => {
        const sel = document.querySelector('.input-row .ant-select')
        return sel && !sel.classList.contains('ant-select-disabled')
      }, { timeout: 15000 })
      await page.screenshot({ path: `tests/screenshots/quick-06-${vp.name}.png`, fullPage: true })
      console.log(`  ✅ ${vp.name} (${vp.w}x${vp.h})`)
      summary.passed++
    } catch (e) {
      summary.failed++
      console.log(`  ❌ ${vp.name}: ${e.message}`)
    }
    await page.close()
  }

  await browser.close()

  // ============== 汇总 ==============
  console.log('')
  console.log('='.repeat(60))
  console.log(`📊 测试汇总: ${summary.passed}/${summary.total} 通过, ${summary.failed} 失败`)
  console.log('='.repeat(60))

  if (summary.issues.length > 0) {
    console.log('')
    console.log('⚠️ 发现问题:')
    summary.issues.forEach((iss, i) => {
      console.log(`  ${i + 1}. [${iss.test}] ${iss.type}`)
      if (Array.isArray(iss.detail)) {
        iss.detail.slice(0, 3).forEach((d) => {
          console.log(`     - ${typeof d === 'string' ? d.slice(0, 200) : JSON.stringify(d).slice(0, 200)}`)
        })
      }
    })

    // 写报告
    fs.writeFileSync(
      'tests/report/issues.json',
      JSON.stringify(summary, null, 2),
    )
  }

  process.exit(summary.failed > 0 ? 1 : 0)
}

run().catch((e) => {
  console.error('💥 测试运行异常:', e)
  process.exit(1)
})