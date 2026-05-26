import { chromium } from '@playwright/test'

async function checkParsingFeatures() {
  console.log('🚀 开始检查解析功能...\n')
  
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  
  const errors = []
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text())
    }
  })
  
  try {
    console.log('📍 访问页面: http://localhost:5174/')
    await page.goto('http://localhost:5174/', { waitUntil: 'networkidle', timeout: 30000 })
    await page.waitForTimeout(2000)
    
    console.log('✅ 页面加载成功\n')
    
    // 检查歌曲解析表单
    console.log('🔍 检查歌曲解析功能:')
    const songInput = await page.locator('input[placeholder="请输入网易云音乐歌曲链接"]')
    const songExists = await songInput.count() > 0
    console.log(`  歌曲解析表单: ${songExists ? '✅ 存在' : '❌ 不存在'}`)
    
    if (songExists) {
      await songInput.fill('https://music.163.com/song?id=1380946308')
      const songButton = await page.locator('button:has-text("解析")').first()
      console.log(`  解析按钮: ${await songButton.count() > 0 ? '✅ 存在' : '❌ 不存在'}`)
    }
    
    // 检查歌单解析表单
    console.log('\n🔍 检查歌单解析功能:')
    const playlistInput = await page.locator('input[placeholder="请输入网易云音乐歌单链接"]')
    const playlistExists = await playlistInput.count() > 0
    console.log(`  歌单解析表单: ${playlistExists ? '✅ 存在' : '❌ 不存在'}`)
    
    if (playlistExists) {
      await playlistInput.fill('https://music.163.com/playlist?id=225001/vue3_music')
      const playlistButton = await page.locator('button:has-text("解析歌单")').first()
      console.log(`  解析歌单按钮: ${await playlistButton.count() > 0 ? '✅ 存在' : '❌ 不存在'}`)
    }
    
    // 检查专辑解析表单
    console.log('\n🔍 检查专辑解析功能:')
    const albumInput = await page.locator('input[placeholder="请输入网易云音乐专辑链接"]')
    const albumExists = await albumInput.count() > 0
    console.log(`  专辑解析表单: ${albumExists ? '✅ 存在' : '❌ 不存在'}`)
    
    if (albumExists) {
      await albumInput.fill('https://music.163.com/album?id=14808721')
      const albumButton = await page.locator('button:has-text("解析专辑")').first()
      console.log(`  解析专辑按钮: ${await albumButton.count() > 0 ? '✅ 存在' : '❌ 不存在'}`)
    }
    
    // 检查音质选择
    console.log('\n🔍 检查音质选择:')
    const qualityButtons = await page.locator('.quality-selector').first()
    const qualityExists = await qualityButtons.count() > 0
    console.log(`  音质选择器: ${qualityExists ? '✅ 存在' : '❌ 不存在'}`)
    
    // 检查设置面板
    console.log('\n🔍 检查设置面板:')
    const settingsButton = await page.locator('button[circle]').nth(1)
    if (await settingsButton.count() > 0) {
      await settingsButton.click()
      await page.waitForTimeout(500)
      
      const drawer = await page.locator('.el-drawer')
      const drawerVisible = await drawer.isVisible()
      console.log(`  设置面板: ${drawerVisible ? '✅ 可打开' : '❌ 无法打开'}`)
      
      if (drawerVisible) {
        const closeButton = await drawer.locator('.el-drawer__header button')
        await closeButton.click()
      }
    }
    
    // 检查主题切换
    console.log('\n🔍 检查主题切换:')
    const themeButton = await page.locator('button[circle]').first()
    if (await themeButton.count() > 0) {
      await themeButton.click()
      await page.waitForTimeout(500)
      console.log(`  主题切换按钮: ✅ 可点击`)
    }
    
    // 检查欢迎对话框
    console.log('\n🔍 检查欢迎对话框:')
    await page.evaluate(() => localStorage.removeItem('hasSeenWelcome'))
    await page.reload()
    await page.waitForTimeout(1500)
    
    const welcomeDialog = await page.locator('.el-dialog')
    const welcomeExists = await welcomeDialog.isVisible()
    console.log(`  欢迎对话框: ${welcomeExists ? '✅ 显示' : '❌ 未显示'}`)
    
    if (welcomeExists) {
      const startButton = await page.locator('button:has-text("开始使用")')
      await startButton.click()
      await page.waitForTimeout(500)
      console.log(`  关闭欢迎对话框: ✅ 成功`)
    }
    
    // 检查错误
    if (errors.length > 0) {
      console.log('\n⚠️  发现错误:')
      errors.forEach((err, i) => {
        if (i < 5) console.log(`  ${i + 1}. ${err.substring(0, 100)}`)
      })
    } else {
      console.log('\n✅ 无 JavaScript 错误')
    }
    
    console.log('\n✅ 功能检查完成！')
    
  } catch (error) {
    console.error('❌ 检查失败:', error.message)
  } finally {
    await browser.close()
  }
}

checkParsingFeatures().catch(console.error)
