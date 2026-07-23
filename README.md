# Wan Music

> 多平台音乐搜索、解析、下载工具

[![Docker Hub](https://hub.docker.com/r/ethanwwan/wan-music)](https://hub.docker.com/r/ethanwwan/wan-music)

## ✨ 特性

- 🎵 **多平台支持**：网易云音乐、QQ音乐、酷狗音乐、酷我音乐
- 🔌 **双线路解析**：项目自研 chain + musicdl 库，按歌曲自动 fallback
- 🔍 **歌曲/歌单搜索**：跨平台统一搜索接口（含 SSE 流式返回）
- 🎚️ **智能音质降级**：hires → lossless → exhigh → standard，失败时自动尝试下一档
- ⬇️ **批量下载**：自动写入 ID3 标签（标题、歌手、专辑、歌词、封面）
- 📊 **任务进度 SSE**：批量任务实时推送进度
- 🛡️ **详细失败信息**：下载失败时透传降级链、尝试源、可用音质给前端
- 🐳 **一键部署**：单一 Docker 镜像（含前后端）
- 🎨 **现代 Web UI**：Vue 3 + Vite + Ant Design Vue
- ✅ **E2E 测试覆盖**：Playwright 自动化测试覆盖 2 线路 × 4 平台 × 3 音质 = 24 搜索组合

## 📸 预览

| 桌面 | 移动端 |
|------|--------|
| ![desktop](frontend/tests/screenshots/quick-06-desktop.png) | ![mobile](frontend/tests/screenshots/quick-06-mobile.png) |

## ⚙️ 统一配置

所有环境变量集中在根目录 [`config.json`](/config.json)：

```json
{
  "frontend": {
    "devPort": 5175,
    "prodPort": 6175,
    "apiProxyTarget": "",
    "apiBase": ""
  },
  "backend": {
    "devBackendPort": 5005,
    "prodBackendPort": 6005
  }
}
```

修改后无需同步，前端 (`vite.config.js`) 和 Docker 都会自动读取最新值。

## 📁 目录结构

```
wan-music/
├── backend/                          # Python Flask 后端
│   ├── clients/                      # 音乐平台客户端
│   │   ├── base_client.py            # 客户端基类（URL 抢答 + 音质验证）
│   │   ├── music_client.py           # 统一入口（含音质降级链 + API 源 fallback）
│   │   ├── song_info_cache.py        # 内存缓存（避免重复 search）
│   │   ├── netease_client.py / qq_client.py / kugou_client.py / kuwo_client.py
│   │   ├── data_models.py            # 数据模型（SongInfo / SongUrl）
│   │   ├── quality_config.py         # 平台音质等级 + fallback_chain 配置
│   │   ├── fallback/                 # 跨源 fallback chain 实现
│   │   │   ├── chain.py              # 串行/并行源尝试 + URL/音质验证 + 超时
│   │   │   ├── api_source.py         # 单个 API 源包装（动态解析 + 健康统计）
│   │   │   ├── health.py             # 源健康状态（mark_source_failed + 5min expire）
│   │   │   └── extractors.py         # 跨平台 extractors（含 _safe_int 兜底）
│   │   └── sources/                  # 各平台的多个 URL/API 源
│   │       ├── netease.py / qq.py / kugou.py / kuwo.py
│   │       ├── _jbsou.py             # 跨平台聚合源
│   │       └── _playlist_extractors.py
│   ├── musicdl_adapter/              # musicdl 线路适配层（line=1）
│   │   ├── adapter.py                # musicdl → 项目接口格式转换
│   │   ├── converter.py              # 字段映射
│   │   └── streaming.py              # 流式搜索 (yield)
│   ├── utils/                        # 工具函数
│   │   ├── audio_utils.py            # 流式下载 + 重试
│   │   ├── filename.py               # 合法化文件名（处理特殊字符）
│   │   ├── metadata.py               # ID3 标签写入
│   │   ├── url_parser.py             # 歌单/单曲链接解析
│   │   ├── logging_config.py
│   │   └── config.py
│   ├── app_config.py                 # 全局配置 + 平台音质等级表
│   ├── service.py                    # MusicService + BatchDownloadService + 详细错误构造
│   ├── routes.py                     # Flask 路由（含 SSE 流式搜索）
│   ├── main.py                       # 入口（dev 模式 Flask dev server）
│   └── requirements.txt              # Flask / requests / mutagen / gunicorn / musicdl / curl_cffi
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── components/               # 业务组件
│   │   │   ├── SearchContainer.vue   # 搜索框 + 平台切换 + 线路切换
│   │   │   ├── SearchResult.vue      # 结果列表 + 批量选择 + 下载触发
│   │   │   ├── MusicPlayer.vue       # 内嵌播放器
│   │   │   ├── DownloadDrawer.vue    # 下载队列抽屉
│   │   │   └── SettingsDialog.vue    # 设置面板（音质/线路/平台默认值）
│   │   ├── stores/
│   │   │   └── downloadQueue.js      # 下载队列 + SSE 进度订阅
│   │   ├── services/
│   │   │   └── musicApi.js           # Axios 封装
│   │   ├── utils/                    # 配置/平台/主题/下载/设置/解析工具
│   │   │   ├── configManager.js      # 读取 config.json
│   │   │   ├── settingsManager.js    # localStorage 持久化（音质/线路/平台）
│   │   │   ├── platformsManager.js   # 平台列表 + 图标
│   │   │   ├── themeManager.js       # 暗色主题
│   │   │   ├── parseManager.js       # URL 解析入口
│   │   │   └── downloadHelper.js     # 下载触发辅助
│   │   ├── styles/global.css
│   │   ├── App.vue
│   │   └── main.js
│   ├── tests/                        # Playwright E2E 测试套件
│   │   ├── 01-smoke.spec.js          # 页面加载
│   │   ├── 02-search.spec.js         # 搜索矩阵（@playwright/test）
│   │   ├── 03-play.spec.js           # 播放功能
│   │   ├── 04-download.spec.js       # 下载功能
│   │   ├── 05-settings.spec.js       # 设置面板
│   │   ├── 06-ui-integrity.spec.js   # 响应式 + 历史记录 + 页脚
│   │   ├── 07-console-errors.spec.js # 控制台错误监控
│   │   ├── quick-run.cjs             # 一键运行（31 个测试，无需 CLI）
│   │   ├── lib/helpers.js            # 公共 helper（drawer portal 选择器等）
│   │   └── README.md
│   ├── playwright.config.js
│   ├── vite.config.js
│   └── package.json
├── scripts/                          # 仓库级维护脚本
│   ├── check_metadata.py             # 扫描音频文件元数据完整性
│   └── sync_artist_to_playlist.py    # 同步歌手目录与歌单原曲
├── .github/workflows/
│   └── docker-build-and-push.yml     # Tag 触发构建并推送 Docker Hub
├── config.json                       # ⭐ 统一配置（前后端端口）
├── docker-compose.yml                # 单一容器部署（前后端一体）
├── Dockerfile                        # 多阶段构建（前后端 → 单一镜像）
├── .gitignore
├── LICENSE
└── README.md
```

## 🚀 快速开始

### 方式一：Docker（推荐）

```bash
# 1) 首次部署需先把 host 目录权限给容器用户（UID=1000）
sudo chown -R 1000:1000 ./cookie ./logs

# 2) 拉取镜像并启动
docker compose up -d

# 3) 访问
open http://localhost:6005

# 持久化目录（cookie + 下载 + 日志）已映射到当前目录
# - ./cookie   VIP 登录 cookie
# - ./logs      运行日志
```

### 方式二：本地开发

```bash
# 后端
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 main.py             # http://localhost:5005（端口由 config.json 决定）

# 前端（另一个终端）
cd frontend
npm install
npm run dev                 # 仅前端 http://localhost:5175
npm run dev:full            # 同时启动前后端（推荐）
npm run build               # 生产构建
```

前端 `npm run dev:full` 会同时拉起前后端，端口/代理从根目录 [`config.json`](/config.json) 自动读取（devBackendPort=5005 / devPort=5175）。

### 方式三：拉取预构建镜像

```bash
docker pull ethanwwan/wan-music:latest

docker run -d \
  --name wan-music \
  -p 6005:6005 \
  -v $(pwd)/cookie:/app/cookie \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  ethanwwan/wan-music:latest
```

## 🧪 测试

提供两套测试入口，按需选择：

### 一键运行（推荐）

```bash
cd frontend
npm install
npx playwright install chromium        # 首次需要

# 31 个测试覆盖：
#   01 烟雾（1）
#   02 搜索矩阵（2 线路 × 4 平台 × 3 音质 = 24）
#   03 播放（2）
#   04 下载（2）
#   05 设置（1）
#   06 响应式（1）
node tests/quick-run.cjs

# 日志输出：tests/report/quick-run.log
# 截图归档：tests/screenshots/quick-*.png
```

### @playwright/test 标准运行

```bash
cd frontend
npm run test                           # 全部 7 个 spec 文件
npm run test:headed                    # 带浏览器界面
npm run test -- tests/02-search.spec.js  # 单个文件
```

> 测试套件要求：后端 (5005) + 前端 (5175) 同时运行。详细说明见 [frontend/tests/README.md](frontend/tests/README.md)。

## 📡 主要 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/search` | POST | 统一搜索（type=0 全部 / 1 歌曲 / 2 歌单） |
| `/search/stream` | POST (SSE) | 流式搜索（边搜边返回，musicdl 线路） |
| `/song` | POST | 获取歌曲详情 + 下载链接（含音质降级） |
| `/playlist` | POST | 获取歌单详情 |
| `/download` | GET | 单曲下载（流式） |
| `/download/batch/start` | POST | 启动批量下载任务 |
| `/download/batch/progress` | GET (SSE) | 批量任务进度推送 |
| `/download/batch/list` | GET | 所有任务列表 |
| `/download/batch/{id}` | DELETE | 删除任务 |

详细文档：[backend/README.md](backend/README.md)

### 失败错误信息示例

下载失败时，错误信息不再笼统的"可能因版权问题"，而是给出**降级链 + 尝试源 + 平台/线路**：

```
降级链: 无损→...→标准（3档均失败） | [无损] 源A | [极高] 源B | [标准] 源C
| 该歌曲可用音质: 无损/极高/标准 | 平台=qq 线路=0
```

## 🛠️ 技术栈

**后端**：Python 3.11 · Flask 3 · Gunicorn · Mutagen · Requests · curl_cffi · musicdl 2.13
**前端**：Vue 3 · Vite 5 · Pinia · Ant Design Vue 4 · Axios
**测试**：Playwright 1.61（chromium, 1366×900, headless）
**部署**：Docker · Docker Compose · GitHub Actions

## 📦 版本发布

```bash
# 创建 tag → 触发 Docker 自动构建
git tag -a v1.3.0 -m "Release 1.3.0"
git push origin v1.3.0

# GitHub Actions 自动：
#   1) 构建镜像 (linux/amd64)
#   2) 推送到 Docker Hub（去 v 前缀，v1.3.0 → 1.3.0）
#   3) 同步 README 到 Docker Hub 描述
#   4) 创建 GitHub Release
```

镜像标签策略：`v1.3.0` → `:1.3.0` + `:1.3` + `:1` + `:latest`

## 🐳 Docker 部署

### 本地构建

```bash
# 根目录的 Dockerfile，多阶段构建（前端 Vite build → 后端 Flask 静态托管）
docker build -t wan-music:local .

docker run -d \
  --name wan-music \
  -p 6005:6005 \
  -v $(pwd)/cookie:/app/cookie \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  wan-music:local

open http://localhost:6005
```

### GitHub Actions 自动发布

| 事件 | 触发结果 |
|------|---------|
| `git push origin v1.2.3` | 构建并推送 `:1.2.3` + `:1.2` + `:1` + `:latest` |
| `git push origin v1.2.3-rc1` | 构建并推送 `:1.2.3-rc1`（预发布） |

镜像支持 `linux/amd64`。

### 常用命令

```bash
docker ps | grep wan-music              # 查看运行中的容器
docker stats wan-music                 # 资源占用
docker exec -it wan-music /bin/bash    # 进入容器
docker logs -f wan-music               # 实时日志
docker compose down -v                 # 停止并清理卷
```

### 反向代理

Nginx 示例（用于 `music.example.com`）：

```nginx
server {
    listen 80;
    server_name music.example.com;

    location / {
        proxy_pass http://127.0.0.1:6005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;  # SSE 支持
        proxy_read_timeout 300s;
    }
}
```

### 故障排查

```bash
# 1) 端口被占用 → 修改 docker-compose.yml 的 ports
# 2) cookie 问题 → docker exec 检查 /app/cookie/
#    或修复 host 目录权限：sudo chown -R 1000:1000 ./cookie ./logs ./downloads
# 3) 清理重建 → docker compose down -v && docker system prune -a
```

### 安全特性

- 非 root 用户运行（`wanmusic`，UID=1000）
- 多阶段构建（不包含构建工具）
- `.dockerignore` 排除 cookie / .env / node_modules

## 📄 许可证

MIT License