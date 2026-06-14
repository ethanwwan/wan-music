/**
 * 测试音乐搜索API
 */

const API_BASE = 'http://localhost:5002';

async function testSearch(keyword, source) {
  console.log(`\n=== 测试搜索: ${keyword} (source: ${source}) ===`);

  const requestData = {
    keyword,
    limit: 10
  };

  if (source) {
    requestData.source = source;
  }

  console.log('请求数据:', JSON.stringify(requestData, null, 2));

  try {
    const response = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestData)
    });

    const result = await response.json();

    console.log('响应状态:', response.status);
    console.log('响应数据:', JSON.stringify(result, null, 2));
    console.log('结果数量:', result.data ? result.data.length : 0);

    if (result.data && result.data.length > 0) {
      console.log('第一条结果:', result.data[0].name);
    }

    return result;
  } catch (error) {
    console.error('请求失败:', error.message);
    return null;
  }
}

async function runTests() {
  console.log('开始测试音乐搜索API...\n');

  // 测试网易云音乐
  await testSearch('陈楚生', 'netease');

  // 测试QQ音乐
  await testSearch('陈楚生', 'qq');

  // 测试酷狗音乐
  await testSearch('陈楚生', 'kugou');

  // 测试波点音乐
  await testSearch('陈楚生', 'bodian');

  // 测试不带source参数（应该返回所有平台结果）
  await testSearch('陈楚生', null);

  console.log('\n=== 测试完成 ===');
}

runTests();
