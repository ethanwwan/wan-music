/**
 * 模拟前端页面调用API测试
 * 测试前端如何调用backend API
 */

const API_BASE = 'http://localhost:5173' // Vite开发服务器

async function simulateFrontendCall() {
  console.log('🌐 模拟前端页面调用API')
  console.log('='.repeat(50))

  console.log('\n📝 场景1: 用户输入歌曲ID并点击解析')
  console.log('歌曲ID: 25706282')
  console.log('音质选择: lossless (无损)')

  try {
    console.log('\n⏳ 正在调用 frontendApi.getSongInfo(25706282, "lossless")...')

    const response = await fetch(`${API_BASE}/Song_V1`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        ids: '25706282',
        level: 'lossless',
        type: 'json'
      })
    })

    const data = await response.json()

    console.log('\n📥 收到API响应:')
    console.log(JSON.stringify(data, null, 2))

    if (data.status === 200) {
      console.log('\n✅ API调用成功!')
      console.log('\n📺 前端页面应该显示:')
      console.log(`  🎵 歌曲: ${data.name}`)
      console.log(`  👤 歌手: ${data.ar_name}`)
      console.log(`  💿 专辑: ${data.al_name}`)
      console.log(`  🎧 音质: ${data.level}`)
      console.log(`  📦 大小: ${data.size}`)

      console.log('\n🔗 获取到的音乐URL:')
      console.log(`  ${data.url.substring(0, 80)}...`)

      console.log('\n🎵 前端播放器应该开始播放这首歌')

      return true
    } else {
      console.error('\n❌ API返回错误:')
      console.error(data.msg || data.error)
      return false
    }
  } catch (error) {
    console.error('\n❌ 前端调用失败:', error.message)
    return false
  }
}

async function testDifferentQuality() {
  console.log('\n\n' + '='.repeat(50))
  console.log('📝 场景2: 测试不同音质选项')

  const qualities = ['standard', 'exhigh', 'lossless', 'hires']

  for (const quality of qualities) {
    try {
      console.log(`\n⏳ 测试音质: ${quality}`)

      const response = await fetch(`${API_BASE}/Song_V1`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          ids: '25706282',
          level: quality,
          type: 'json'
        })
      })

      const data = await response.json()

      if (data.status === 200) {
        console.log(`✅ ${quality}: ${data.level} (${data.size})`)
      } else {
        console.log(`❌ ${quality}: ${data.msg || '失败'}`)
      }
    } catch (error) {
      console.error(`❌ ${quality}: ${error.message}`)
    }
  }
}

async function main() {
  const result1 = await simulateFrontendCall()
  await testDifferentQuality()

  console.log('\n' + '='.repeat(50))
  if (result1) {
    console.log('🎉 前后端联调测试成功！')
    console.log('🌐 您可以在浏览器中访问 http://localhost:5173')
    console.log('📝 输入歌曲ID测试完整流程')
  } else {
    console.log('⚠️ 前后端联调测试发现问题，请检查配置')
  }
  console.log('='.repeat(50))
}

main()
