/**
 * 08 - 保存按钮专项测试
 * 验证：单首下载完成后，"保存"按钮能否真正触发文件下载
 *
 * 修复目标：
 *   - downloadBatchAsZip 加 fetchWithTimeout（避免后端 hang 时按钮"无反应"）
 *   - downloadTask 在 saveBlob 后延迟 500ms 再清理任务 + DELETE
 *     （避免同域请求竞争连接/打断下载流）
 *
 * 已知 UI 细节：
 *   - 抽屉使用 Teleport，按钮不在 .ant-drawer-open DOM 子树内
 *   - Ant Design <a-button> 把内部 "保存" 渲染成 "保 存"（中间有空格）
 *     → 选择器用 /保\s*存/ 匹配
 */
import { test, expect } from '@playwright/test'
import {
  createInstrumentedPage,
  selectDataSource,
  selectQuality,
  performSearch,
} from './lib/helpers.js'

// 单曲下载/网络较慢，测试整体放宽到 180s
test.setTimeout(180_000)

test('保存按钮 - 单曲下载完成后点击保存可触发文件下载', async ({ context }) => {
  const instrument = await createInstrumentedPage(context)
  const { page } = instrument

  await page.goto('/')
  await page.waitForFunction(
    () => {
      const sel = document.querySelector('.input-row .ant-select')
      return sel && !sel.classList.contains('ant-select-disabled')
    },
    { timeout: 30_000 },
  )
  await selectQuality(page, '无损')
  await selectDataSource(page, 'netease')
  await performSearch(page, '周杰伦', { timeout: 90_000 })

  // 点击第一行的下载按钮（播放按钮是第 1 个，下载是第 2 个）
  const downloadBtn = page.locator('.tracks-table tbody tr.track-row').first().locator('button').nth(1)
  await downloadBtn.click()

  // 队列抽屉打开
  await page.locator('.ant-drawer-open').first().waitFor({ state: 'visible', timeout: 15_000 })

  // 等任务完成 + 保存按钮出现（status-done 卡片内的"保存"按钮）
  // Ant Design button 把 "保存" 渲染为 "保 存"（中间有空格）
  const saveBtn = page.locator('.task-card.status-done button').filter({ hasText: /保\s*存/ }).first()
  await expect(saveBtn).toBeVisible({ timeout: 150_000 })

  // 记录点击前的 task-card 总数
  const cardsBefore = await page.locator('.task-card.status-done').count()

  // 监听浏览器的 download 事件
  const downloadPromise = page.waitForEvent('download', { timeout: 30_000 })

  await saveBtn.click()

  // 验证：浏览器真的接收到了一个 download 事件
  const download = await downloadPromise
  expect(download).toBeTruthy()

  // 文件名应包含歌曲扩展名（.mp3 / .flac / .m4a）或 zip
  const suggestedFilename = download.suggestedFilename()
  expect(suggestedFilename).toMatch(/\.(mp3|flac|m4a|zip)$/i)

  // 验证：saveBlob 触发下载后，约 500ms 后任务被清理（removeTask）
  await page.waitForTimeout(1500)
  // 已完成卡片数应比点击前少 1
  const cardsAfter = await page.locator('.task-card.status-done').count()
  expect(cardsAfter).toBe(cardsBefore - 1)
})