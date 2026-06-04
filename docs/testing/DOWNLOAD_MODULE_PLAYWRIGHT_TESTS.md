# 增强版下载模块 Playwright 测试

## 📋 测试概述

本测试套件使用 Playwright 对增强版下载模块进行全面测试，包括：

- ✅ 后端 API 接口测试
- ✅ 前端下载界面测试
- ✅ 下载进度追踪测试
- ✅ 下载任务控制测试（暂停、恢复、取消）
- ✅ 下载队列管理测试
- ✅ 错误处理测试
- ✅ 音质降级测试
- ✅ 性能测试

---

## 🚀 快速开始

### 1. 安装依赖

如果还没有安装 Playwright 依赖：

```bash
npm run test:install
```

### 2. 运行测试

#### 运行所有下载模块测试
```bash
npm run test:download
```

#### 在浏览器中运行测试（可视化）
```bash
npm run test:download:headed
```

#### 运行所有测试（后端 + Playwright）
```bash
npm run test:all
```

---

## 📝 测试详情

### 测试文件位置
```
tests/
└── system/
    └── test-download-module.mjs    # 增强版下载模块测试
```

### 测试类别

#### 1. 后端API接口测试

| 测试用例 | 说明 |
|---------|------|
| `健康检查接口应该正常响应` | 测试 `/health` 接口 |
| `添加下载任务到队列` | 测试 `/api/download/queue` POST |
| `获取下载队列状态` | 测试 `/api/download/queue` GET |
| `批量添加下载任务` | 测试 `/api/download/queue/batch` |

#### 2. 前端下载界面测试

| 测试用例 | 说明 |
|---------|------|
| `应该显示下载队列组件` | 验证下载队列 UI 组件存在 |
| `下载按钮应该可点击` | 验证下载按钮可见 |

#### 3. 下载进度追踪测试

| 测试用例 | 说明 |
|---------|------|
| `任务应该包含正确的状态字段` | 验证进度数据结构完整性 |

#### 4. 下载任务控制测试

| 测试用例 | 说明 |
|---------|------|
| `应该能够暂停任务` | 测试 `/api/download/task/<id>/pause` |
| `应该能够取消任务` | 测试 `/api/download/task/<id>/cancel` |
| `应该能够删除任务` | 测试 `/api/download/task/<id>` DELETE |

#### 5. 下载队列管理测试

| 测试用例 | 说明 |
|---------|------|
| `队列应该维护任务顺序` | 测试优先级功能 |
| `队列应该限制并发数` | 测试并发控制 |

#### 6. 错误处理测试

| 测试用例 | 说明 |
|---------|------|
| `无效的音乐ID应该返回错误` | 测试参数验证 |
| `不存在的任务ID应该返回404` | 测试任务不存在处理 |
| `无效的任务操作应该返回错误` | 测试异常操作处理 |

#### 7. 音质降级测试

| 测试用例 | 说明 |
|---------|------|
| `应该支持所有音质等级` | 测试所有音质选项 |

#### 8. 性能测试

| 测试用例 | 说明 |
|---------|------|
| `批量添加100个任务应该快速响应` | 测试批量操作性能 |
| `获取队列状态应该快速响应` | 测试查询性能 |

---

## 🎯 运行特定测试

### 运行单个测试文件
```bash
npx playwright test tests/system/test-download-module.mjs
```

### 运行特定测试用例
```bash
npx playwright test tests/system/test-download-module.mjs --grep "健康检查"
```

### 运行特定浏览器
```bash
npx playwright test tests/system/test-download-module.mjs --project=chromium
```

### 生成测试报告
```bash
npx playwright test tests/system/test-download-module.mjs --reporter=html
```

---

## 📊 测试配置

### Playwright 配置 (`playwright.config.js`)

```javascript
{
  testDir: './tests',
  outputDir: './tests/results',
  fullyParallel: true,
  retries: 0,
  workers: undefined,
  reporter: 'html',
  baseURL: 'http://localhost:5176',
  actionTimeout: 10000,
  navigationTimeout: 30000,
}
```

### 支持的浏览器

- ✅ Chromium (Desktop Chrome)
- ✅ Firefox (Desktop Firefox)
- ✅ WebKit (Desktop Safari)
- ✅ Mobile Chrome (Pixel 5)
- ✅ Mobile Safari (iPhone 12)

---

## 🔍 查看测试结果

### 1. 命令行输出
测试完成后，测试结果会直接在终端显示：

```
✅ 通过的测试: [绿色]
❌ 失败的测试: [红色]
⏱️  耗时信息
```

### 2. HTML 报告
测试完成后，会在 `tests/results/` 目录生成 HTML 报告：

```bash
# 打开 HTML 报告
open tests/results/playwright-report.html
```

### 3. 测试截图
如果测试失败，会在 `tests/results/` 目录保存失败截图。

### 4. 视频录制
如果测试失败，会在 `tests/results/` 目录保存失败时的视频录制。

---

## 🐛 调试测试

### 使用 headed 模式
```bash
npm run test:download:headed
```
这会在浏览器窗口中显示测试执行过程。

### 使用 Playwright Inspector
```bash
npx playwright test tests/system/test-download-module.mjs --debug
```

### 单独运行失败的测试
```bash
npx playwright test tests/system/test-download-module.mjs --grep "@failed"
```

---

## ✅ 预期结果

### 成功的测试
所有测试应该通过，显示绿色 ✅ 标记：

```
✅ 健康检查接口应该正常响应
✅ 添加下载任务到队列
✅ 获取下载队列状态
✅ 批量添加下载任务
✅ 任务应该包含正确的状态字段
✅ 应该能够取消任务
✅ 应该能够删除任务
✅ 队列应该维护任务顺序
✅ 队列应该限制并发数
✅ 无效的音乐ID应该返回错误
✅ 不存在的任务ID应该返回404
✅ 应该支持所有音质等级
✅ 批量添加100个任务应该快速响应
✅ 获取队列状态应该快速响应
```

### 可能的失败情况

如果测试失败，可能的原因：

1. **服务未启动**
   - 后端服务未运行在端口 5002
   - 前端服务未运行在端口 5176

2. **网络问题**
   - 无法连接到网易云音乐 API
   - 网络超时

3. **依赖问题**
   - Python 依赖未安装
   - Node.js 依赖未安装

4. **测试数据问题**
   - 测试使用的歌曲 ID 可能已下架

---

## 📦 集成测试

### 前后端联调测试

运行前后端联调测试：
```bash
node tests/system/test-frontend-backend.mjs
```

这会测试：
- 前端服务是否正常运行
- 后端服务是否正常运行
- API 接口是否响应正常

### 完整系统测试

运行完整系统测试：
```bash
npm run test:all
```

这会依次运行：
1. 后端单元测试
2. Playwright 下载模块测试

---

## 🎓 测试最佳实践

### 1. 本地开发
```bash
# 先启动服务
npm run dev

# 再运行测试（另一个终端）
npm run test:download
```

### 2. CI/CD 环境
```bash
# 安装依赖
npm install
npm run test:install

# 运行测试
npm run test:all
```

### 3. 调试特定功能
```bash
# 只测试 API 接口
npm run test:download -- --grep "API"

# 只测试性能
npm run test:download -- --grep "性能"
```

---

## 📞 故障排除

### 测试超时
如果测试超时，可以增加超时时间：

```bash
npx playwright test tests/system/test-download-module.mjs --timeout=60000
```

### 端口被占用
如果端口被占用，检查并停止占用进程：

```bash
# 检查端口占用
lsof -i :5002
lsof -i :5176

# 停止进程
kill <PID>
```

### 清理测试缓存
```bash
# 清理 Playwright 缓存
rm -rf tests/results/*
rm -rf node_modules/.cache

# 重新安装
npm run test:install
```

---

## 🎉 测试通过标准

所有测试通过后，你会看到：

```
✓ 14 passed (XXs)

Test Suites: 1 passed, 1 total
Tests:       14 passed, 14 total
```

这意味着增强版下载模块的所有功能都正常工作！

---

## 📚 相关文档

- [下载模块完整说明](../docs/testing/DOWNLOAD_MODULE_README.md)
- [Playwright 官方文档](https://playwright.dev/docs/intro)
- [项目测试报告](../docs/testing/FINAL_TEST_REPORT.md)
