/**
 * 完整自动化测试脚本
 * 测试所有前端和后端功能
 */

import http from 'http';
import https from 'https';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 颜色输出
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

function log(type, message) {
  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️',
    test: '🔍'
  };
  const color = {
    success: colors.green,
    error: colors.red,
    warning: colors.yellow,
    info: colors.blue,
    test: colors.blue
  }[type] || colors.reset;

  console.log(`${color}${icons[type] || '•'} ${message}${colors.reset}`);
}

// HTTP请求封装
function httpRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;

    const defaultOptions = {
      timeout: 10000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36'
      }
    };

    const reqOptions = { ...defaultOptions, ...options };

    const req = client.get(url, reqOptions, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: data,
          contentType: res.headers['content-type']
        });
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('请求超时'));
    });
  });
}

// 测试结果统计
const results = {
  passed: 0,
  failed: 0,
  total: 0
};

function test(name, fn) {
  results.total++;
  log('test', `测试: ${name}`);

  return fn()
    .then(() => {
      results.passed++;
      log('success', `✅ 通过: ${name}`);
      return true;
    })
    .catch((err) => {
      results.failed++;
      log('error', `❌ 失败: ${name}`);
      log('error', `   错误: ${err.message}`);
      return false;
    });
}

// 测试套件
const tests = {
  // 1. 文件结构检查
  async checkFileStructure() {
    log('info', '\n📁 检查文件结构...');

    const requiredFiles = [
      'frontend/index.html',
      'frontend/src/main.js',
      'frontend/src/App.vue',
      'backend/src/server.js',
      'backend/src/server-cookie.js',
      'backend/src/server-crypto.js',
      'backend/cookie.txt',
      'vite.config.js',
      'package.json'
    ];

    const missing = [];
    for (const file of requiredFiles) {
      const exists = fs.existsSync(file);
      if (!exists) {
        missing.push(file);
      }
    }

    if (missing.length > 0) {
      throw new Error(`缺少文件: ${missing.join(', ')}`);
    }

    log('success', '文件结构检查通过');
  },

  // 2. Cookie文件检查
  async checkCookieFile() {
    log('info', '\n🍪 检查Cookie文件...');

    const cookiePath = 'backend/cookie.txt';
    if (!fs.existsSync(cookiePath)) {
      throw new Error('Cookie文件不存在');
    }

    const content = fs.readFileSync(cookiePath, 'utf-8');
    if (!content || content.trim().length === 0) {
      throw new Error('Cookie文件为空');
    }

    const hasMUSICU = content.includes('MUSIC_U=');
    if (!hasMUSICU) {
      throw new Error('Cookie缺少MUSIC_U字段');
    }

    log('success', 'Cookie文件检查通过');
  },

  // 3. 启动后端服务
  async startBackendServer() {
    log('info', '\n🚀 启动后端服务...');

    const backendPath = path.join(__dirname, 'backend', 'src', 'server.js');

    if (!fs.existsSync(backendPath)) {
      throw new Error(`后端入口文件不存在: ${backendPath}`);
    }

    const { spawn } = await import('child_process');
    const backendProcess = spawn('node', [backendPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      detached: false
    });

    let output = '';
    backendProcess.stdout.on('data', (data) => {
      output += data.toString();
    });
    backendProcess.stderr.on('data', (data) => {
      output += data.toString();
    });

    // 等待服务启动
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('后端服务启动超时'));
      }, 10000);

      const check = () => {
        httpRequest('http://localhost:3000/health')
          .then(() => {
            clearTimeout(timeout);
            resolve();
          })
          .catch(() => {
            setTimeout(check, 500);
          });
      };

      check();
    });

    log('success', '后端服务启动成功');
    return backendProcess;
  },

  // 4. 测试后端健康检查
  async testBackendHealth() {
    log('info', '\n🏥 测试后端健康检查...');

    const response = await httpRequest('http://localhost:3000/health');

    if (response.status !== 200) {
      throw new Error(`健康检查失败，状态码: ${response.status}`);
    }

    const data = JSON.parse(response.body);
    if (data.status !== 'ok') {
      throw new Error(`健康状态异常: ${JSON.stringify(data)}`);
    }

    log('success', '健康检查通过');
  },

  // 5. 测试Cookie验证
  async testCookieValidation() {
    log('info', '\n🍪 测试Cookie验证...');

    const response = await httpRequest('http://localhost:3000/health');
    const data = JSON.parse(response.body);

    if (!data.cookie || !data.cookie.valid) {
      throw new Error('Cookie验证失败');
    }

    if (data.cookie.missingCookies && data.cookie.missingCookies.length > 0) {
      log('warning', `⚠️ 警告: 缺少Cookie字段: ${data.cookie.missingCookies.join(', ')}`);
    }

    log('success', 'Cookie验证通过');
  },

  // 6. 测试歌曲详情API
  async testSongDetailAPI() {
    log('info', '\n🎵 测试歌曲详情API...');

    const response = await fetch('http://localhost:3000/api/song', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: 33894312 })
    });

    if (!response.ok) {
      throw new Error(`API请求失败，状态码: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(`API返回错误: ${data.message || '未知错误'}`);
    }

    if (!data.data || !data.data.songs || data.data.songs.length === 0) {
      throw new Error('API返回数据为空');
    }

    log('success', `歌曲详情API测试通过: ${data.data.songs[0].name}`);
  },

  // 7. 测试歌词API
  async testLyricAPI() {
    log('info', '\n📝 测试歌词API...');

    const response = await fetch('http://localhost:3000/api/lyric', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: 33894312 })
    });

    if (!response.ok) {
      throw new Error(`API请求失败，状态码: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success && data.message !== '暂无歌词') {
      throw new Error(`API返回错误: ${data.message || '未知错误'}`);
    }

    log('success', '歌词API测试通过');
  },

  // 8. 测试搜索API
  async testSearchAPI() {
    log('info', '\n🔍 测试搜索API...');

    const response = await fetch('http://localhost:3000/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword: '周杰伦', limit: 5 })
    });

    if (!response.ok) {
      throw new Error(`API请求失败，状态码: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(`API返回错误: ${data.message || '未知错误'}`);
    }

    if (!data.data || !data.data.result || !data.data.result.songs) {
      throw new Error('搜索结果格式错误');
    }

    log('success', `搜索API测试通过，找到 ${data.data.result.songs.length} 首歌曲`);
  },

  // 9. 测试歌单API
  async testPlaylistAPI() {
    log('info', '\n📋 测试歌单API...');

    const response = await fetch('http://localhost:3000/api/playlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: 225001 })
    });

    if (!response.ok) {
      throw new Error(`API请求失败，状态码: ${response.status}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(`API返回错误: ${data.message || '未知错误'}`);
    }

    if (!data.data || !data.data.playlist) {
      throw new Error('歌单数据格式错误');
    }

    log('success', `歌单API测试通过: ${data.data.playlist.name}`);
  },

  // 10. 启动前端服务
  async startFrontendServer() {
    log('info', '\n🚀 启动前端服务...');

    // 检查index.html是否存在
    const indexPath = 'frontend/index.html';
    if (!fs.existsSync(indexPath)) {
      throw new Error(`index.html不存在: ${indexPath}`);
    }

    // 检查vite.config.js
    const viteConfigPath = 'vite.config.js';
    if (!fs.existsSync(viteConfigPath)) {
      throw new Error(`vite.config.js不存在: ${viteConfigPath}`);
    }

    const { spawn } = await import('child_process');
    const frontendProcess = spawn('npx', ['vite'], {
      cwd: process.cwd(),
      stdio: ['pipe', 'pipe', 'pipe'],
      detached: false
    });

    let output = '';
    frontendProcess.stdout.on('data', (data) => {
      output += data.toString();
    });
    frontendProcess.stderr.on('data', (data) => {
      output += data.toString();
    });

    // 等待服务启动
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        log('error', '前端服务启动输出:\n' + output);
        reject(new Error('前端服务启动超时'));
      }, 15000);

      const check = () => {
        httpRequest('http://localhost:5173')
          .then((response) => {
            if (response.status === 200 && response.body.includes('html')) {
              clearTimeout(timeout);
              resolve();
            } else {
              setTimeout(check, 500);
            }
          })
          .catch(() => {
            setTimeout(check, 500);
          });
      };

      check();
    });

    log('success', '前端服务启动成功');
    return frontendProcess;
  },

  // 11. 测试前端页面访问
  async testFrontendPage() {
    log('info', '\n🌐 测试前端页面访问...');

    const response = await httpRequest('http://localhost:5173');

    if (response.status !== 200) {
      throw new Error(`前端页面访问失败，状态码: ${response.status}`);
    }

    if (!response.body.includes('<!DOCTYPE html>') && !response.body.includes('<html')) {
      throw new Error('前端页面返回的不是HTML');
    }

    if (!response.body.includes('vue') && !response.body.includes('vite')) {
      log('warning', '⚠️ 警告: 页面可能未正确加载Vue应用');
    }

    log('success', '前端页面访问测试通过');
  },

  // 12. 测试前端资源加载
  async testFrontendAssets() {
    log('info', '\n📦 测试前端资源加载...');

    // 测试主入口文件
    const mainResponse = await httpRequest('http://localhost:5173/src/main.js');
    if (mainResponse.status !== 200) {
      throw new Error(`main.js加载失败，状态码: ${mainResponse.status}`);
    }

    if (!mainResponse.body.includes('createApp')) {
      throw new Error('main.js不是有效的Vue入口文件');
    }

    log('success', '前端资源加载测试通过');
  },

  // 13. 测试API代理
  async testAPIProxy() {
    log('info', '\n🔄 测试API代理...');

    const response = await httpRequest('http://localhost:5173/api/song', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // 应该返回200或JSON错误，而不是404
    if (response.status === 404) {
      throw new Error('API代理失败，返回404');
    }

    log('success', 'API代理测试通过');
  }
};

// 主测试函数
async function runAllTests() {
  console.log('\n');
  log('info', '═'.repeat(60));
  log('info', '🎵 万能音乐 - 完整自动化测试');
  log('info', '═'.repeat(60));
  log('info', `⏰ 开始时间: ${new Date().toLocaleString()}`);
  log('info', '═'.repeat(60));

  let backendProcess = null;
  let frontendProcess = null;

  try {
    // 1. 文件结构检查
    await test('文件结构检查', tests.checkFileStructure);

    // 2. Cookie文件检查
    await test('Cookie文件检查', tests.checkCookieFile);

    // 3. 启动后端服务
    backendProcess = await test('启动后端服务', tests.startBackendServer);

    // 4. 后端健康检查
    await test('后端健康检查', tests.testBackendHealth);

    // 5. Cookie验证
    await test('Cookie验证', tests.testCookieValidation);

    // 6. 歌曲详情API
    await test('歌曲详情API', tests.testSongDetailAPI);

    // 7. 歌词API
    await test('歌词API', tests.testLyricAPI);

    // 8. 搜索API
    await test('搜索API', tests.testSearchAPI);

    // 9. 歌单API
    await test('歌单API', tests.testPlaylistAPI);

    // 10. 启动前端服务
    frontendProcess = await test('启动前端服务', tests.startFrontendServer);

    // 11. 前端页面访问
    await test('前端页面访问', tests.testFrontendPage);

    // 12. 前端资源加载
    await test('前端资源加载', tests.testFrontendAssets);

    // 13. API代理
    await test('API代理', tests.testAPIProxy);

  } catch (error) {
    log('error', `\n❌ 测试过程中发生错误: ${error.message}`);
    if (error.stack) {
      log('error', error.stack);
    }
  } finally {
    // 清理进程
    log('info', '\n🧹 清理测试进程...');

    if (frontendProcess) {
      frontendProcess.kill();
      log('info', '前端服务已停止');
    }

    if (backendProcess) {
      backendProcess.kill();
      log('info', '后端服务已停止');
    }
  }

  // 输出测试结果
  console.log('\n');
  log('info', '═'.repeat(60));
  log('info', '📊 测试结果统计');
  log('info', '═'.repeat(60));
  log('info', `总计: ${results.total}`);
  log(results.passed > 0 ? 'success' : 'error', `通过: ${results.passed}`);
  log(results.failed > 0 ? 'error' : 'success', `失败: ${results.failed}`);
  log('info', `成功率: ${((results.passed / results.total) * 100).toFixed(2)}%`);
  log('info', '═'.repeat(60));

  if (results.failed === 0) {
    log('success', '\n🎉 所有测试通过！');
  } else {
    log('error', `\n⚠️  有 ${results.failed} 个测试失败，请检查上述错误`);
  }

  return results.failed === 0;
}

// 运行测试
runAllTests()
  .then((success) => {
    process.exit(success ? 0 : 1);
  })
  .catch((error) => {
    log('error', `\n❌ 测试脚本执行失败: ${error.message}`);
    process.exit(1);
  });
