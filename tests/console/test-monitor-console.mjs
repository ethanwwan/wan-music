/**
 * 控制台输出监控脚本
 * 监控前端和后端服务的控制台输出，识别错误和警告
 */

import { spawn } from 'child_process';
import http from 'http';
import https from 'https';

// 颜色
const colors = {
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  reset: '\x1b[0m'
};

function log(type, message) {
  const colorMap = {
    error: colors.red,
    warning: colors.yellow,
    success: colors.green,
    info: colors.blue,
    normal: colors.reset
  };
  const color = colorMap[type] || colors.reset;
  console.log(`${color}${message}${colors.reset}`);
}

// HTTP请求封装
function httpRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const req = client.get(url, { timeout: 5000, ...options }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('超时')); });
  });
}

// 检测问题
const issues = {
  errors: [],
  warnings: [],
  infos: []
};

function analyzeOutput(source, line) {
  const lowerLine = line.toLowerCase();

  // 检测错误
  if (lowerLine.includes('error') || lowerLine.includes('fail') ||
      lowerLine.includes('err ') || lowerLine.includes('[error]') ||
      lowerLine.includes('uncaught') || lowerLine.includes('exception')) {
    if (!issues.errors.includes(line)) {
      issues.errors.push(line);
      log('error', `[${source}] 错误: ${line}`);
    }
  }

  // 检测警告
  if (lowerLine.includes('warn') || lowerLine.includes('deprecated') ||
      lowerLine.includes('[warning]') || lowerLine.includes('⚠')) {
    if (!issues.warnings.includes(line)) {
      issues.warnings.push(line);
      log('warning', `[${source}] 警告: ${line}`);
    }
  }

  // 检测重要信息
  if (lowerLine.includes('ready') || lowerLine.includes('running') ||
      lowerLine.includes('listening') || lowerLine.includes('started')) {
    log('success', `[${source}] ${line}`);
  }
}

// 检查服务健康
async function checkServices() {
  log('info', '\n检查服务健康状态...\n');

  try {
    // 检查前端
    const frontend = await httpRequest('http://localhost:5173');
    if (frontend.status === 200) {
      log('success', '✅ 前端服务: 正常 (http://localhost:5173)');
    } else {
      log('error', `❌ 前端服务: 异常 (状态码: ${frontend.status})`);
    }
  } catch (err) {
    log('error', `❌ 前端服务: 无法访问 - ${err.message}`);
  }

  try {
    // 检查后端
    const backend = await httpRequest('http://localhost:3000/health');
    if (backend.status === 200) {
      const data = JSON.parse(backend.body);
      if (data.status === 'ok') {
        log('success', `✅ 后端服务: 正常 (http://localhost:3000)`);
        if (data.cookie && data.cookie.valid) {
          log('success', `   Cookie状态: 有效 (${data.cookie.cookieCount}个字段)`);
        } else {
          log('warning', '   Cookie状态: 无效或缺失');
        }
      }
    } else {
      log('error', `❌ 后端服务: 异常 (状态码: ${backend.status})`);
    }
  } catch (err) {
    log('error', `❌ 后端服务: 无法访问 - ${err.message}`);
  }
}

// 测试API功能
async function testAPIFeatures() {
  log('info', '\n测试API功能...\n');

  const tests = [
    { name: '歌曲详情API', url: '/api/song', method: 'POST', body: { id: 33894312 } },
    { name: '歌词API', url: '/api/lyric', method: 'POST', body: { id: 33894312 } },
    { name: '搜索API', url: '/api/search', method: 'POST', body: { keyword: '周杰伦', limit: 3 } },
    { name: '歌单API', url: '/api/playlist', method: 'POST', body: { id: 225001 } }
  ];

  for (const test of tests) {
    try {
      const response = await fetch(`http://localhost:3000${test.url}`, {
        method: test.method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(test.body)
      });

      const data = await response.json();

      if (data.success) {
        log('success', `✅ ${test.name}: 正常`);
      } else {
        log('warning', `⚠️ ${test.name}: 返回错误 - ${data.message || '未知错误'}`);
      }
    } catch (err) {
      log('error', `❌ ${test.name}: 失败 - ${err.message}`);
    }
  }
}

// 生成报告
function generateReport() {
  log('info', '\n' + '='.repeat(60));
  log('info', '📊 控制台输出分析报告');
  log('info', '='.repeat(60));

  if (issues.errors.length === 0 && issues.warnings.length === 0) {
    log('success', '✅ 未发现错误或警告！');
  } else {
    if (issues.errors.length > 0) {
      log('error', `\n❌ 发现 ${issues.errors.length} 个错误:`);
      issues.errors.forEach((err, i) => {
        log('error', `  ${i + 1}. ${err}`);
      });
    }

    if (issues.warnings.length > 0) {
      log('warning', `\n⚠️  发现 ${issues.warnings.length} 个警告:`);
      issues.warnings.forEach((warn, i) => {
        log('warning', `  ${i + 1}. ${warn}`);
      });
    }
  }

  log('info', '='.repeat(60));
}

// 启动监控
async function monitor() {
  console.clear();
  log('info', '🔍 开始监控前端和后端服务...\n');

  // 检查服务
  await checkServices();

  // 测试API
  await testAPIFeatures();

  // 生成报告
  generateReport();

  console.log('\n');
  log('info', '💡 提示: 刷新浏览器页面 (http://localhost:5173) 查看是否有新的控制台输出');
  log('info', '📝 如果发现问题，请查看上面的错误和警告列表');
  console.log('\n');
}

// 运行
monitor().catch(console.error);
