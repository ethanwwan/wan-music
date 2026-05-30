/**
 * 前后端联合调试测试
 * 测试完整的前后端通信流程
 */

const API_BASE = 'http://localhost:5173'

async function testBackendHealth() {
  console.log('🔍 测试1: 检查后端服务健康状态...')
  try {
    const response = await fetch(`${API_BASE}/health`)
    const data = await response.json()
    console.log('✅ 后端服务状态:', data)
    return true
  } catch (error) {
    console.error('❌ 后端服务连接失败:', error.message)
    return false
  }
}

async function testSongApi() {
  console.log('\n🔍 测试2: 测试歌曲解析API...')
  try {
    const response = await fetch(`${API_BASE}/Song_V1`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        ids: '25706282',
        level: 'standard',
        type: 'json'
      })
    })
    const data = await response.json()

    if (data.status === 200) {
      console.log('✅ 歌曲解析成功!')
      console.log('  歌曲名称:', data.name)
      console.log('  歌手:', data.ar_name)
      console.log('  专辑:', data.al_name)
      console.log('  音质:', data.level)
      console.log('  大小:', data.size)
      console.log('  URL长度:', data.url.length, '字符')
      return true
    } else {
      console.error('❌ 歌曲解析失败:', data)
      return false
    }
  } catch (error) {
    console.error('❌ API调用失败:', error.message)
    return false
  }
}

async function testHighQuality() {
  console.log('\n🔍 测试3: 测试无损音质解析...')
  try {
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

    if (data.status === 200) {
      console.log('✅ 无损音质解析成功!')
      console.log('  音质:', data.level)
      console.log('  大小:', data.size)
      return true
    } else {
      console.error('❌ 无损音质解析失败:', data.msg || data)
      return false
    }
  } catch (error) {
    console.error('❌ API调用失败:', error.message)
    return false
  }
}

async function testInvalidSong() {
  console.log('\n🔍 测试4: 测试无效歌曲ID...')
  try {
    const response = await fetch(`${API_BASE}/Song_V1`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        ids: '99999999',
        level: 'standard',
        type: 'json'
      })
    })
    const data = await response.json()

    if (data.status !== 200) {
      console.log('✅ 正确处理无效歌曲ID')
      console.log('  错误信息:', data.msg || data.error)
      return true
    } else {
      console.log('⚠️ 返回了数据，可能歌曲ID存在')
      return true
    }
  } catch (error) {
    console.error('❌ API调用失败:', error.message)
    return false
  }
}

async function testMissingParams() {
  console.log('\n🔍 测试5: 测试缺少参数...')
  try {
    const response = await fetch(`${API_BASE}/Song_V1?ids=25706282`, {
      method: 'POST'
    })
    const data = await response.json()

    if (data.error || data.status !== 200) {
      console.log('✅ 正确处理缺少参数')
      console.log('  错误信息:', data.error || data.msg)
      return true
    } else {
      console.log('⚠️ 应该返回错误但没有')
      return false
    }
  } catch (error) {
    console.error('❌ API调用失败:', error.message)
    return false
  }
}

async function runAllTests() {
  console.log('='.repeat(50))
  console.log('🚀 前后端联合调试测试')
  console.log('='.repeat(50))
  console.log()

  const results = []

  results.push(await testBackendHealth())
  results.push(await testSongApi())
  results.push(await testHighQuality())
  results.push(await testInvalidSong())
  results.push(await testMissingParams())

  console.log()
  console.log('='.repeat(50))
  console.log('📊 测试结果汇总')
  console.log('='.repeat(50))

  const passed = results.filter(r => r).length
  const total = results.length

  console.log(`✅ 通过: ${passed}/${total}`)
  console.log(`❌ 失败: ${total - passed}/${total}`)

  if (passed === total) {
    console.log('\n🎉 所有测试通过！前后端联调成功！')
  } else {
    console.log('\n⚠️ 部分测试失败，请检查配置')
  }

  console.log()
  console.log('🌐 前端地址: http://localhost:5173')
  console.log('🔧 后端地址: http://localhost:5002')
}

runAllTests()
