/**
 * 测试前端歌曲解析功能
 */

import { chromium } from 'playwright';

async function testSongParsing() {
  console.log('🎵 测试歌曲解析功能...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 收集控制台消息
  const consoleMessages = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleMessages.push(`[ERROR] ${msg.text()}`);
    }
  });

  try {
    console.log('1. 访问页面...');
    await page.goto('http://localhost:5173', {
      waitUntil: 'networkidle',
      timeout: 30000
    });
    console.log('   ✅ 页面加载成功\n');

    console.log('2. 查找输入框...');
    const songInput = page.locator('input[placeholder*="分享链接"]').first();

    if (await songInput.isVisible({ timeout: 5000 })) {
      console.log('   ✅ 找到输入框\n');

      console.log('3. 输入测试歌曲链接...');
      await songInput.fill('https://music.163.com/#/song?id=33894312');
      const value = await songInput.inputValue();
      console.log(`   输入内容: ${value}\n`);

      console.log('4. 点击解析按钮...');
      const parseButton = page.locator('button:has-text("开始解析")').first();
      await parseButton.click();
      console.log('   ✅ 已点击解析按钮\n');

      console.log('5. 等待解析结果...');
      await page.waitForTimeout(5000);

      // 检查是否有错误提示
      const errorMessages = consoleMessages.filter(m => m.includes('ERROR'));
      if (errorMessages.length > 0) {
        console.log('❌ 发现控制台错误:');
        errorMessages.forEach(err => console.log(`   ${err}`));
      } else {
        console.log('   ✅ 无控制台错误\n');
      }

      // 检查页面内容
      const pageContent = await page.content();

      if (pageContent.includes('情非得已')) {
        console.log('✅ 歌曲名称显示正确\n');
      } else if (pageContent.includes('未找到')) {
        console.log('❌ 显示"未找到歌曲详情"错误\n');
      } else {
        console.log('⚠️  未找到明显的错误或成功标识\n');
      }

      // 检查是否有播放器
      const player = page.locator('.aplayer, [class*="player"], [class*="Player"]');
      if (await player.count() > 0) {
        console.log('✅ 播放器已显示\n');
      } else {
        console.log('⚠️  未找到播放器\n');
      }

    } else {
      console.log('❌ 未找到歌曲输入框\n');
    }

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
  } finally {
    await browser.close();
  }
}

testSongParsing();
