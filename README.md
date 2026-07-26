# Wan Music

> 多平台音乐搜索、解析、下载工具

[![GitHub Container Registry](https://ghcr.io/ethanwwan/wan-music)](https://github.com/ethanwwan/wan-music/pkgs/container/wan-music)

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

### 方式三：拉取预构建镜像（GitHub Container Registry）

```bash
docker pull ghcr.io/ethanwwan/wan-music:latest

docker run -d \
  --name wan-music \
  -p 6005:6005 \
  -v $(pwd)/cookie:/app/cookie \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  ghcr.io/ethanwwan/wan-music:latest
```

## 🧪 测试

提供两套测试入口，按需选择：

### 一键运行（推荐）

```bash
cd frontend
npm install
npx playwright install chromium        # 首次需要

# 32 个测试覆盖：
#   01 烟雾（1）
#   02 搜索矩阵（2 线路 × 4 平台 × 3 音质 = 24）
#   03 播放（2）
#   04 下载（3：4 平台单首 + 批量 + 抽屉）
#   05 设置（1）
#   06 响应式（1）
#   08 保存按钮专项（1：验证 download 事件 + 任务清理）
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
# 创建 tag → 触发 GitHub Actions 自动构建
git tag -a v1.3.0 -m "Release 1.3.0"
git push origin v1.3.0

# GitHub Actions 自动：
#   1) 构建镜像 (linux/amd64)
#   2) 推送到 GitHub Container Registry（去 v 前缀，v1.3.0 → 1.3.0）
#   3) 创建 GitHub Release
```

镜像标签策略：`v1.3.0` → `:1.3.0` + `:latest`

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

镜像推送到 **GitHub Container Registry**（`ghcr.io/ethanwwan/wan-music`）。

| 事件 | 触发结果 |
|------|---------|
| `git push origin v1.2.3` | 构建并推送 `:1.2.3` + `:latest` |
| `git push origin v1.2.3-rc1` | 构建并推送 `:1.2.3-rc1` + `:latest-prerelease` |
| `git push origin main` | 构建并推送 `:main-<7位sha>`（不动 latest） |

镜像支持 `linux/amd64` + `linux/arm64`（Apple Silicon / AWS Graviton 原生支持）。首次拉取无需登录（公开镜像）。

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