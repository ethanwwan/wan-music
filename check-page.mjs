import { chromium } from '@playwright/test'

async function checkPageLoad() {
  console.log('🚀 开始检查页面加载...\n')
  
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  
  // 收集所有错误
  const errors = []
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text())
    }
  })
  
  page.on('pageerror', error => {
    errors.push(`Page Error: ${error.message}`)
  })
  
  try {
    console.log('📍 访问页面: http://localhost:5174/')
    await page.goto('http://localhost:5174/', { waitUntil: 'networkidle', timeout: 30000 })
    
    console.log('✅ 页面加载成功\n')
    
    // 等待一下让 Vue 初始化
    await page.waitForTimeout(3000)
    
    // 检查页面内容
    const title = await page.title()
    console.log(`📄 页面标题: ${title}`)
    
    // 检查 #app 元素
    const appContent = await page.evaluate(() => {
      const app = document.querySelector('#app')
      return app ? app.innerHTML.substring(0, 200) : 'NOT FOUND'
    })
    console.log(`\n📦 #app 内容: ${appContent.substring(0, 100)}...`)
    
    // 检查是否有明显错误
    const hasLoader = await page.locator('#initial-loader').count()
    console.log(`\n⏳ 是否还在加载: ${hasLoader > 0 ? '是' : '否'}`)
    
    // 检查控制台错误
    if (errors.length > 0) {
      console.log('\n❌ 发现错误:')
      errors.forEach((err, i) => {
        console.log(`  ${i + 1}. ${err}`)
      })
    } else {
      console.log('\n✅ 无控制台错误')
    }
    
    // 检查关键元素
    console.log('\n🔍 检查关键元素:')
    const elements = [
      { name: 'h1', selector: 'h1' },
      { name: '主容器', selector: '.app-container' },
      { name: '音乐播放器', selector: '.music-player-container' }
    ]
    
    for (const el of elements) {
      const count = await page.locator(el.selector).count()
      console.log(`  ${el.name}: ${count > 0 ? '✅ 存在' : '❌ 不存在'}`)
    }
    
    console.log('\n✅ 检查完成')
    
  } catch (error) {
    console.error('❌ 页面加载失败:', error.message)
  } finally {
    await browser.close()
  }
}

checkPageLoad().catch(console.error)
