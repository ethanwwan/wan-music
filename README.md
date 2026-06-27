# Wan Music

> 多平台音乐搜索、解析、下载工具

[![Docker Hub](https://hub.docker.com/r/ethanwwan/wan-music)](https://hub.docker.com/r/ethanwwan/wan-music)

## ✨ 特性

- 🎵 **多平台支持**：网易云、QQ音乐、波点音乐、酷狗音乐
- 🔍 **歌曲/歌单搜索**：跨平台统一搜索接口
- ⬇️ **批量下载**：自动写入 ID3 标签（标题、歌手、专辑、歌词、封面）
- 🐳 **一键部署**：Docker 镜像（linux/amd64）
- 🎨 **现代 Web UI**：Vue 3 + Vite + Ant Design Vue

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

修改后无需同步，前端 (vite.config.js) 和 Docker 都会自动读取最新值。

## 📁 目录结构

```
wan-music/
├── backend/                # Python Flask 后端
│   ├── clients/            # 音乐平台客户端（netease/qq/bodian/kugou）
│   ├── routes/             # Flask 路由
│   ├── services/           # 业务服务层
│   ├── utils/              # 工具函数（音频、元数据、响应）
│   ├── main.py             # 入口
│   └── requirements.txt
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── components/     # 业务组件
│   │   ├── composables/    # 组合式 API
│   │   ├── stores/         # Pinia 状态
│   │   └── utils/          # 工具函数
│   └── package.json
├── scripts/                # 仓库级维护脚本（元数据检查、歌单同步）
├── config.json             # ⭐ 统一配置（前端/后端端口）
├── Dockerfile              # 根目录 Docker 镜像构建
├── docker/                 # Docker 部署参考配置（demo）
└── README.md
```

## 🚀 快速开始

### 方式一：Docker（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/pgwan/wan-music.git
cd wan-music

# 2. 启动（使用 docker/ 下的 demo 配置）
docker compose -f docker/docker-compose.yml up -d --build

# 3. 访问
open http://localhost:6005
```

### 方式二：本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python3 main.py          # http://localhost:5005

# 前端
cd frontend
npm install
npm run dev:full         # 同时启动前后端（端口由 config.json 决定）
```

### 方式三：拉取预构建镜像

```bash
docker pull pgwan/wan-music:latest

docker run -d \
  --name wan-music \
  -p 6005:6005 \
  --restart unless-stopped \
  pgwan/wan-music:latest
```

## 📡 主要 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/search` | POST | 统一搜索（type=0 全部 / 1 歌曲 / 2 歌单） |
| `/song` | POST | 获取歌曲详情（含下载链接） |
| `/playlist` | POST | 获取歌单详情 |
| `/download` | GET | 单曲下载（流式） |
| `/download/batch/*` | POST/GET/DELETE | 批量下载 + SSE 进度 |

详细文档：[backend/README.md](file:///Users/Awan/Public/Repository/wan-music/backend/README.md)（含完整 API 文档）

## 🛠️ 技术栈

**后端**：Python 3.11 · Flask · Gunicorn · Mutagen · Requests
**前端**：Vue 3 · Vite · Pinia · Ant Design Vue · Axios
**部署**：Docker · Docker Compose · GitHub Actions

## 🔧 维护脚本

```bash
# 扫描音频文件元数据完整性
python3 scripts/check_metadata.py

# 同步歌手目录与歌单原曲
python3 scripts/sync_artist_to_playlist.py
```

## 📦 版本发布

```bash
# 创建 tag
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# GitHub Actions 自动：
# 1) 构建镜像 (linux/amd64)
# 2) 推送到 Docker Hub（去 v 前缀，例如 v1.0.0 → 1.0.0）
# 3) 同步 README 到 Docker Hub 描述
# 4) 创建 GitHub Release
```

## 🐳 Docker 部署

### 本地构建

```bash
# 根目录的 Dockerfile，多阶段构建
docker build -t wan-music:local .

# 运行
docker run -d \
  --name wan-music \
  -p 6005:6005 \
  --restart unless-stopped \
  wan-music:local

# 访问
open http://localhost:6005
```

### docker/ 目录

提供 `docker-compose.yml` 作为参考 demo（端口 6005），部署到远程服务器时复制到部署目录后修改使用：

```bash
cp docker/docker-compose.yml deploy/
cd deploy && docker compose up -d
```

### GitHub Actions 自动发布

| 事件 | 触发结果 |
|------|---------|
| `git push origin v1.2.3` | 构建并推送 `:1.2.3` + `:1.2` + `:1` + `:latest` |
| `git push origin v1.2.3-rc1` | 构建并推送 `:1.2.3-rc1`（预发布） |

镜像支持 `linux/amd64`。

### 拉取预构建镜像

```bash
docker pull pgwan/wan-music:latest

docker run -d \
  --name wan-music \
  -p 6005:6005 \
  --restart unless-stopped \
  pgwan/wan-music:latest
```

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
# 2) cookie 问题 → docker exec 检查 /app/clients/cookie/
# 3) 清理重建 → docker compose down -v && docker system prune -a
```

### 安全特性

- 非 root 用户运行（`wanmusic`）
- 多阶段构建（不包含构建工具）
- `.dockerignore` 排除 cookie / .env / node_modules

## 📄 许可证

MIT License
