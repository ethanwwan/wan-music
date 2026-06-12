# 网易云音乐解析工具 - UI自动化测试方案

## 1. 测试概述

### 1.1 项目背景
本项目是一个网易云音乐解析工具，基于 Vue 3 + Ant Design Vue 构建，后端使用 Flask + musicdl 提供音乐搜索和下载服务。支持多平台音乐搜索（网易云、QQ音乐、酷狗、酷我、咪咕）。

### 1.2 测试目标
- 确保前端UI正确展示和交互
- 验证所有API接口正常响应
- 检查样式规范（颜色、字体、间距）
- 确保主题切换功能正常
- 提供自动化回归测试能力

### 1.3 测试范围
| 模块 | 测试内容 | 优先级 |
|------|----------|--------|
| 首页 | 页面加载、标题、导航栏、搜索框 | 高 |
| 搜索功能 | 单曲/歌手/歌单/专辑搜索 | 高 |
| 解析功能 | 解析按钮、详情展示、播放功能 | 高 |
| 下载功能 | 下载按钮、文件处理 | 中 |
| 主题设置 | 主题色切换、深色模式适配 | 中 |
| API接口 | 搜索API、歌手API、专辑API、歌单API、下载API | 高 |

---

## 2. 测试环境

### 2.1 环境要求
- Node.js >= 18.0.0
- Playwright >= 1.60.0
- 前端服务: http://localhost:5173
- 后端服务: http://localhost:5002

### 2.2 测试命令
```bash
# 安装依赖
cd frontend && npm install

# 安装浏览器
npx playwright install

# 运行所有测试
npm run test:ui

# 运行指定测试
npx playwright test tests/homepage.spec.js

# 生成测试报告
npx playwright test --reporter=html
```

---

## 3. 功能模块分析

### 3.1 后端功能模块

| 模块 | 接口 | 方法 | 功能描述 |
|------|------|------|----------|
| 健康检查 | `/health` | GET | 检查服务状态 |
| 歌曲信息 | `/song` | GET/POST | 获取歌曲URL、名称、歌词 |
| 音乐搜索 | `/search` | GET/POST | 搜索单曲 |
| 歌单搜索 | `/search/playlist` | GET/POST | 搜索歌单 |
| 专辑搜索 | `/search/album` | GET/POST | 搜索专辑 |
| 歌手搜索 | `/search/artist` | GET/POST | 搜索歌手 |
| 歌单详情 | `/playlist` | GET/POST | 获取歌单详情和歌曲列表 |
| 专辑详情 | `/album` | GET/POST | 获取专辑详情和歌曲列表 |
| 歌手详情 | `/artist` | GET/POST | 获取歌手信息和热门歌曲 |
| 音乐下载 | `/download` | GET/POST | 下载音乐文件 |
| 下载队列 | `/api/download/queue` | GET/POST | 管理下载队列 |
| API信息 | `/api/info` | GET | 获取API服务信息 |

### 3.2 前端功能模块

| 模块 | 组件 | 功能描述 |
|------|------|----------|
| 首页 | HeroHeader, SystemNotice | 展示标题、副标题、系统公告 |
| 搜索 | SearchContainer, SearchResult | 支持单曲/歌手/歌单/专辑搜索 |
| 解析 | parseManager | 解析单曲、歌单、专辑 |
| 播放 | MusicPlayer | 音乐播放、歌词显示 |
| 歌曲列表 | SongList | 展示歌单/专辑歌曲列表 |
| 设置 | SettingsDialog | 主题色切换、音质设置、下载配置 |
| 浮动按钮 | FloatingActions | 设置入口 |
| 主题管理 | themeManager | 主题色应用、localStorage持久化 |

---

## 4. 测试用例设计

### 4.1 首页测试

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-HOME-001 | 页面加载 | 页面标题正确，状态码200 |
| TC-HOME-002 | 导航栏展示 | Logo、搜索框可见 |
| TC-HOME-003 | 搜索框功能 | 支持输入，回车搜索 |
| TC-HOME-004 | 页脚展示 | 版权信息正确 |
| TC-HOME-005 | 系统公告 | 首次访问显示公告 |

### 4.2 搜索功能测试

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-SEARCH-001 | 单曲搜索 | 返回歌曲列表，数量>0 |
| TC-SEARCH-002 | 歌手搜索 | 返回歌手列表，数量>0 |
| TC-SEARCH-003 | 歌单搜索 | 返回歌单列表，数量>0 |
| TC-SEARCH-004 | 专辑搜索 | 返回专辑列表，数量>0 |
| TC-SEARCH-005 | Tab切换 | 切换后显示对应内容 |
| TC-SEARCH-006 | 空关键词 | 提示请输入关键词 |
| TC-SEARCH-007 | 热门搜索 | 热门搜索tag可点击 |

### 4.3 解析功能测试

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-PARSE-001 | 解析单曲 | 显示歌曲详情，可播放 |
| TC-PARSE-002 | 解析歌单 | 显示歌单详情和歌曲列表 |
| TC-PARSE-003 | 解析专辑 | 显示专辑详情和歌曲列表 |
| TC-PARSE-004 | 解析失败 | 显示错误提示 |

### 4.4 播放功能测试

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-PLAY-001 | 点击播放 | 播放器显示歌曲信息 |
| TC-PLAY-002 | 暂停播放 | 播放状态切换 |
| TC-PLAY-003 | 下一曲 | 切换到下一首 |
| TC-PLAY-004 | 歌词显示 | 歌词同步滚动 |

### 4.5 设置功能测试

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-SETTINGS-001 | 主题色切换 | 主题色即时生效 |
| TC-SETTINGS-002 | 主题色持久化 | 刷新后保持设置 |
| TC-SETTINGS-003 | 音质选择 | 支持多种音质选项 |
| TC-SETTINGS-004 | 清除缓存 | 缓存被清除，提示成功 |

### 4.6 API接口测试

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-API-001 | 健康检查 | 返回success=true，服务运行正常 |
| TC-API-002 | 搜索单曲API | 返回success=true，data有数据 |
| TC-API-003 | 搜索歌单API | 返回success=true，data有数据 |
| TC-API-004 | 搜索专辑API | 返回success=true，data有数据 |
| TC-API-005 | 搜索歌手API | 返回success=true，data有数据 |
| TC-API-006 | 歌单详情API | 返回success=true，包含歌曲列表 |
| TC-API-007 | 专辑详情API | 返回success=true，包含歌曲列表 |
| TC-API-008 | 歌手详情API | 返回success=true，包含歌曲列表 |
| TC-API-009 | 歌曲信息API | 返回success=true，包含URL |
| TC-API-010 | API信息 | 返回API版本和端点列表 |

### 4.7 样式规范测试

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-STYLE-001 | 主题色应用 | 主按钮使用主题色 |
| TC-STYLE-002 | 字体大小 | 标题、正文字体规范 |
| TC-STYLE-003 | 间距 | 卡片间距符合设计规范 |
| TC-STYLE-004 | 响应式 | 不同屏幕尺寸正常显示 |

---

## 5. 测试脚本结构

```
frontend/tests/
├── homepage.spec.js        # 首页测试
├── search.spec.js          # 搜索功能测试
├── parse.spec.js           # 解析功能测试
├── api.spec.js             # API接口测试
├── settings.spec.js        # 设置功能测试
└── utils/
    └── helpers.js          # 辅助函数
```

---

## 6. 测试执行流程

```
1. 启动后端服务 (npm run dev:api)
2. 启动前端服务 (npm run dev)
3. 执行Playwright测试
4. 生成测试报告
5. 检查失败用例
6. 修复问题
7. 重新运行失败用例
```

---

## 7. 测试报告

测试完成后生成HTML报告，包含：
- 测试用例统计
- 通过率
- 失败原因
- 截图（失败时）
- 视频记录（失败时）

---

## 8. 多平台搜索测试（新增）

| 用例ID | 测试场景 | 预期结果 |
|--------|----------|----------|
| TC-MULTI-001 | 网易云搜索 | 返回网易云音乐结果 |
| TC-MULTI-002 | QQ音乐搜索 | 返回QQ音乐结果 |
| TC-MULTI-003 | 多平台搜索 | 返回多平台聚合结果 |