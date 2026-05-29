/**
 * 浏览器控制台错误捕获脚本
 */

import { chromium } from 'playwright';

async function captureConsoleErrors() {
  console.log('🚀 启动浏览器并访问页面...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 收集控制台消息
  const consoleMessages = {
    errors: [],
    warnings: [],
    logs: [],
    infos: []
  };

  // 监听控制台消息
  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();

    if (type === 'error') {
      consoleMessages.errors.push(text);
    } else if (type === 'warning') {
      consoleMessages.warnings.push(text);
    } else if (type === 'log') {
      consoleMessages.logs.push(text);
    } else if (type === 'info') {
      consoleMessages.infos.push(text);
    }
  });

  // 监听页面错误
  const pageErrors = [];
  page.on('pageerror', (error) => {
    pageErrors.push({
      message: error.message,
      stack: error.stack
    });
  });

  // 监听请求失败
  const failedRequests = [];
  page.on('requestfailed', (request) => {
    failedRequests.push({
      url: request.url(),
      failure: request.failure()?.errorText
    });
  });

  try {
    console.log('🌐 访问 http://localhost:5173...\n');

    const response = await page.goto('http://localhost:5173', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    console.log(`📊 页面状态码: ${response.status()}\n`);

    // 等待页面完全加载
    await page.waitForTimeout(3000);

    // 获取页面标题
    const title = await page.title();
    console.log(`📝 页面标题: ${title}\n`);

    // 输出错误
    if (consoleMessages.errors.length > 0) {
      console.log('═'.repeat(60));
      console.log('❌ 控制台错误 (Console Errors):');
      console.log('═'.repeat(60));
      consoleMessages.errors.forEach((err, i) => {
        console.log(`  ${i + 1}. ${err}`);
      });
      console.log('');
    } else {
      console.log('✅ 无控制台错误\n');
    }

    if (pageErrors.length > 0) {
      console.log('═'.repeat(60));
      console.log('💥 页面错误 (Page Errors):');
      console.log('═'.repeat(60));
      pageErrors.forEach((err, i) => {
        console.log(`  ${i + 1}. ${err.message}`);
        if (err.stack) {
          console.log(`     Stack: ${err.stack.substring(0, 200)}...`);
        }
      });
      console.log('');
    } else {
      console.log('✅ 无页面错误\n');
    }

    if (failedRequests.length > 0) {
      console.log('═'.repeat(60));
      console.log('⚠️  失败的请求 (Failed Requests):');
      console.log('═'.repeat(60));
      failedRequests.forEach((req, i) => {
        console.log(`  ${i + 1}. ${req.url}`);
        console.log(`     错误: ${req.failure}`);
      });
      console.log('');
    } else {
      console.log('✅ 无失败的请求\n');
    }

    if (consoleMessages.warnings.length > 0) {
      console.log('═'.repeat(60));
      console.log('⚠️  控制台警告 (Warnings):');
      console.log('═'.repeat(60));
      consoleMessages.warnings.slice(0, 5).forEach((warn, i) => {
        console.log(`  ${i + 1}. ${warn}`);
      });
      if (consoleMessages.warnings.length > 5) {
        console.log(`  ... 还有 ${consoleMessages.warnings.length - 5} 个警告`);
      }
      console.log('');
    }

    // 总结
    console.log('═'.repeat(60));
    console.log('📊 错误总结:');
    console.log('═'.repeat(60));
    console.log(`  总控制台错误: ${consoleMessages.errors.length}`);
    console.log(`  总页面错误: ${pageErrors.length}`);
    console.log(`  总失败请求: ${failedRequests.length}`);
    console.log(`  总警告: ${consoleMessages.warnings.length}`);

    if (consoleMessages.errors.length === 0 && pageErrors.length === 0) {
      console.log('\n✅🎉 页面运行正常，无任何错误！');
    } else {
      console.log('\n⚠️  发现问题，请查看上述错误详情');
    }

  } catch (error) {
    console.error('❌ 访问页面时出错:', error.message);
  } finally {
    await browser.close();
  }
}

captureConsoleErrors();
