# Wan Music

> 多平台音乐搜索、解析、下载工具

[![GitHub](https://img.shields.io/badge/GitHub-wan--music-blue?logo=github)](https://github.com/ethanwwan/wan-music)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/ethanwwan/wan-music/blob/main/README.md)

支持网易云、QQ音乐、波点音乐、酷狗音乐等多个平台，提供统一搜索、歌单解析、批量下载等功能。

## ✨ 特性

- 🎵 **多平台支持**：网易云、QQ音乐、波点音乐、酷狗音乐
- 🔍 **统一搜索**：跨平台歌曲 / 歌单搜索
- ⬇️ **批量下载**：自动写入 ID3 标签（标题、歌手、专辑、歌词、封面）
- 🎨 **现代 Web UI**：Vue 3 + Vite + Ant Design Vue

## 🚀 快速开始

### 拉取镜像

```bash
docker pull ethanwwan/wan-music:latest
```

### 启动容器

```bash
docker run -d \
  --name wan-music \
  -p 6005:6005 \
  --restart unless-stopped \
  ethanwwan/wan-music:latest
```

### 访问

打开浏览器访问 <http://localhost:6005>

## 🐳 Docker Compose

```yaml
version: "3.8"

services:
  wan-music:
    image: ethanwwan/wan-music:latest
    container_name: wan-music
    ports:
      - "6005:6005"
    restart: unless-stopped
```

启动：

```bash
docker compose up -d
```

## 🏷️ 镜像标签

| Tag | 说明 |
|-----|------|
| `latest` | 最新稳定版 |
| `1` | 主版本号 |
| `1.0` | 主.次版本号 |
| `1.0.0` | 完整版本号 |
| `1.0.0-rc1` | 预发布版本 |
| `sha-xxxxxxx` | 特定 commit 构建 |

固定版本（推荐生产环境）：

```bash
docker pull ethanwwan/wan-music:1.0.0
```

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `6005` | 服务监听端口 |

自定义端口示例：

```bash
docker run -d \
  --name wan-music \
  -p 8080:8080 \
  -e PORT=8080 \
  ethanwwan/wan-music:latest
```

## 📡 主要 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/platforms` | GET | 支持的平台列表 |
| `/search` | POST | 统一搜索（type=0 全部 / 1 歌曲 / 2 歌单） |
| `/song` | POST | 获取歌曲详情（含下载链接） |
| `/playlist` | POST | 获取歌单详情 |
| `/download/batch/*` | POST/GET/DELETE | 批量下载 + SSE 进度 |

完整 API 文档：<https://github.com/ethanwwan/wan-music/blob/main/README.md>

## 🔧 常用命令

```bash
# 查看容器状态
docker ps | grep wan-music

# 实时日志
docker logs -f wan-music

# 停止 / 启动 / 重启
docker stop wan-music
docker start wan-music
docker restart wan-music

# 进入容器调试
docker exec -it wan-music /bin/bash

# 清理重建
docker rm -f wan-music && docker pull ethanwwan/wan-music:latest
```

## 🔒 安全

- 非 root 用户运行（`wanmusic`）
- 多阶段构建，最终镜像不包含构建工具
- 端口仅暴露必需项

## 📄 License

MIT License — 详见 <https://github.com/ethanwwan/wan-music/blob/main/README.md>
