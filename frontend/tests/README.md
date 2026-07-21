# Wan Music UI 测试

基于 **Playwright** 的全自动化 UI 测试套件。

## 覆盖范围

- **01-smoke** — 页面加载、关键 UI 元素
- **02-search** — 4 平台 × 3 音质 = 12 个组合的搜索功能矩阵
- **03-play** — 播放、单曲播放、切歌、歌词跳转
- **04-download** — 单曲下载、批量下载、队列抽屉
- **05-settings** — 设置面板（音质/线路/命名/元数据/缓存）
- **06-ui-integrity** — 响应式（手机/平板/桌面）、footer、历史记录
- **07-console-errors** — console error、API 4xx/5xx、ERR_EMPTY_RESPONSE 监控

## 准备

```bash
cd frontend
npm install
npx playwright install chromium  # 仅首次需要
```

## 运行

```bash
# 默认无头跑全部测试
npx playwright test

# 调试（带浏览器窗口）
HEADFUL=1 npx playwright test

# 只跑某个文件
npx playwright test tests/02-search.spec.js

# 只跑某个用例（按 title 匹配）
npx playwright test -g "netease.*lossless"

# 跑全部 + 报告
npx playwright test
npx playwright show-report
```

## 产物

- `tests/screenshots/` — 每个用例的截图（每平台 × 音质都有留档）
- `tests/report/html/` — HTML 报告
- `tests/report/results.json` — 原始 JSON 结果

## 前置依赖

- 后端跑在 `localhost:5005`（启动：`backend/.venv/bin/python3 backend/main.py`）
- 前端跑在 `localhost:5175`（启动：`npm run dev`）

测试脚本本身不会启动前后端服务，需要手动启动。

## 自定义 BASE_URL

```bash
BASE_URL=http://my-host:5175 npx playwright test
```