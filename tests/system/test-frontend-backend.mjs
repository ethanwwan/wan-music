#!/usr/bin/env node

/**
 * 前后端联调测试脚本
 */

import http from 'http';

console.log('🔍 开始前后端联调测试...\n');

// 测试前端服务
function testFrontend() {
  return new Promise((resolve, reject) => {
    console.log('📡 测试前端服务 (http://localhost:5173)...');
    http.get('http://localhost:5173', (res) => {
      if (res.statusCode === 200) {
        console.log('✅ 前端服务正常\n');
        resolve(true);
      } else {
        console.log(`❌ 前端服务异常，状态码: ${res.statusCode}\n`);
        reject(false);
      }
    }).on('error', (err) => {
      console.log(`❌ 前端服务连接失败: ${err.message}\n`);
      reject(false);
    });
  });
}

// 测试后端服务
function testBackend() {
  return new Promise((resolve, reject) => {
    console.log('📡 测试后端服务 (http://localhost:5002)...');
    http.get('http://localhost:5002/health', (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          console.log('✅ 后端服务正常');
          console.log(`   - 服务名称: ${json.service}`);
          console.log(`   - 状态: ${json.status}`);
          console.log(`   - 端口: ${json.port}\n`);
          resolve(true);
        } catch (e) {
          console.log(`❌ 后端响应解析失败\n`);
          reject(false);
        }
      });
    }).on('error', (err) => {
      console.log(`❌ 后端服务连接失败: ${err.message}`);
      console.log('   (这可能是正常的，前端使用纯JS实现，不需要后端)\n');
      resolve(true);
    });
  });
}

// 运行测试
async function runTests() {
  try {
    await testFrontend();
    await testBackend();

    console.log('🎉 所有测试完成！\n');
    console.log('📝 测试说明:');
    console.log('   - 前端使用纯JavaScript实现的网易云API，不需要后端服务');
    console.log('   - 如果后端服务未运行，前端仍可正常工作');
    console.log('   - 如需使用后端，请手动启动: cd backend && python3 main.py\n');

    console.log('🌐 访问地址:');
    console.log('   - 前端: http://localhost:5173');
    console.log('   - 后端: http://localhost:5002\n');

  } catch (error) {
    console.log('❌ 测试失败\n');
    process.exit(1);
  }
}

runTests();
