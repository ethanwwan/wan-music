/**
 * 检查前端实际的网络请求
 */

import { chromium } from 'playwright';

async function checkFrontendNetwork() {
  console.log('🔍 检查前端网络请求...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 收集网络请求
  const requests = [];
  page.on('request', (request) => {
    const url = request.url();
    if (url.includes('localhost:3000') || url.includes('music.163.com')) {
      requests.push({
        url: url,
        method: request.method(),
        headers: request.headers()
      });
    }
  });

  // 收集响应
  const responses = [];
  page.on('response', (response) => {
    const url = response.url();
    if (url.includes('localhost:3000') || url.includes('music.163.com')) {
      responses.push({
        url: url,
        status: response.status()
      });
    }
  });

  // 收集错误
  const errors = [];
  page.on('requestfailed', (request) => {
    errors.push({
      url: request.url(),
      failure: request.failure()?.errorText
    });
  });

  try {
    console.log('🌐 访问页面...\n');
    await page.goto('http://localhost:5173', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // 等待一下让所有请求完成
    await page.waitForTimeout(2000);

    // 查找输入框并输入测试URL
    const songInput = page.locator('input[placeholder*="分享链接"]').first();
    if (await songInput.isVisible()) {
      console.log('📝 输入测试歌曲链接...');
      await songInput.fill('https://music.163.com/#/song?id=33894312');

      // 点击解析按钮
      const parseButton = page.locator('button:has-text("开始解析")').first();
      if (await parseButton.isVisible()) {
        console.log('🎵 点击解析按钮...\n');
        await parseButton.click();

        // 等待解析完成
        await page.waitForTimeout(5000);
      }
    }

    // 输出结果
    console.log('═'.repeat(60));
    console.log('📊 网络请求统计');
    console.log('═'.repeat(60));
    console.log(`总请求数: ${requests.length}\n`);

    if (requests.length > 0) {
      console.log('🌐 发送到 localhost:3000 的请求:');
      const backendRequests = requests.filter(r => r.url.includes('localhost:3000'));
      if (backendRequests.length > 0) {
        backendRequests.forEach((req, i) => {
          console.log(`  ${i + 1}. ${req.method} ${req.url}`);
        });
      } else {
        console.log('  无 - 前端没有调用后端API');
      }

      console.log('\n🌐 发送到 music.163.com 的请求:');
      const neteaseRequests = requests.filter(r => r.url.includes('music.163.com'));
      if (neteaseRequests.length > 0) {
        console.log(`  共 ${neteaseRequests.length} 个请求`);
        neteaseRequests.slice(0, 5).forEach((req, i) => {
          console.log(`  ${i + 1}. ${req.method} ${req.url.substring(0, 100)}...`);
        });
      } else {
        console.log('  无');
      }
    }

    if (errors.length > 0) {
      console.log('\n❌ 失败的请求:');
      errors.forEach((err, i) => {
        console.log(`  ${i + 1}. ${err.url}`);
        console.log(`     错误: ${err.failure}`);
      });
    }

    // 检查页面是否有错误信息
    const pageContent = await page.content();
    if (pageContent.includes('解析失败') || pageContent.includes('错误')) {
      console.log('\n⚠️  页面显示错误信息');
    }

    console.log('\n' + '='.repeat(60));

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
  } finally {
    await browser.close();
  }
}

checkFrontendNetwork();
