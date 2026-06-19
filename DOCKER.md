# Docker 部署指南

## 架构

```
┌─────────────────────────────────────┐
│  Dockerfile (多阶段构建)            │
│                                     │
│  Stage 1: Node 20 构建前端          │
│  ┌───────────────────────────┐      │
│  │ npm ci + vite build       │      │
│  │ 输出: frontend/dist/      │      │
│  └───────────────────────────┘      │
│              ↓                      │
│  Stage 2: Python 3.11 运行后端      │
│  ┌───────────────────────────┐      │
│  │ flask + gunicorn          │      │
│  │ 端口: 5002                │      │
│  │ 非 root 用户运行          │      │
│  └───────────────────────────┘      │
└─────────────────────────────────────┘
```

## 快速开始

### 1. 本地构建

```bash
# 克隆代码
git clone https://github.com/<your-username>/wan-music.git
cd wan-music

# .env 已包含默认配置，按需修改
cat .env

# 构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f

# 访问
open http://localhost:5002
```

### 2. 拉取预构建镜像

```bash
# 拉取最新版
docker pull ghcr.io/<your-username>/wan-music:latest

# 拉取指定版本
docker pull ghcr.io/<your-username>/wan-music:v1.0.0

# 直接运行
docker run -d \
  --name wan-music \
  -p 5002:5002 \
  --restart unless-stopped \
  ghcr.io/<your-username>/wan-music:v1.0.0

# 或使用 docker compose
WAN_MUSIC_IMAGE=ghcr.io/<your-username>/wan-music:v1.0.0 \
  docker compose up -d
```

## GitHub Actions 自动发布

### 触发条件

| 事件 | 触发结果 |
|------|---------|
| `git push origin main` | 构建并推送 `:latest` + `:sha-<short>` |
| `git push origin v1.2.3` | 构建并推送 `:v1.2.3` + `:1.2` + `:1` + `:latest`（如果 main 落后） |
| `git push origin v1.2.3-rc1` | 构建并推送 `:v1.2.3-rc1`（预发布）|
| `pull_request` | 只构建不推送（用于验证）|
| `workflow_dispatch` | 手动指定 tag |

### 发布新版本流程

```bash
# 1. 确保所有改动已 commit
git status

# 2. 创建 tag（遵循语义化版本）
git tag -a v1.0.0 -m "Release 1.0.0"
# 或预发布
git tag -a v1.0.0-rc1 -m "Release 1.0.0 RC1"

# 3. 推送 tag
git push origin v1.0.0

# 4. GitHub Actions 自动：
#    - 构建多架构镜像 (linux/amd64 + linux/arm64)
#    - 推送到 ghcr.io
#    - 运行 Trivy 安全扫描
#    - 创建 GitHub Release
#    - 附带 docker pull/run 命令
```

### Tag 命名规范

遵循 [SemVer](https://semver.org/)：

- `v1.0.0` - 主版本.次版本.修订号
- `v1.0.0-rc1` - 预发布（`-rc1`、`-beta1`、`-alpha1`）
- `v1.0.0-hotfix.1` - 紧急修复

## 镜像信息

### 标签说明

| 标签 | 来源 | 示例 |
|------|------|------|
| `v1.2.3` | 完整版本 | `v1.2.3` |
| `1.2` | 主.次版本 | `1.2` |
| `1` | 主版本 | `1` |
| `latest` | 最新稳定版（仅 main 分支的 tag）| `latest` |
| `sha-abc1234` | main 分支 commit | `sha-abc1234` |

### 多架构支持

镜像同时支持 `linux/amd64` 和 `linux/arm64`：
- Intel/AMD 服务器（x86_64）
- Apple Silicon Mac（M1/M2/M3）
- AWS Graviton
- Raspberry Pi 4+

## 常用命令

```bash
# 查看运行中的容器
docker ps | grep wan-music

# 查看资源占用
docker stats wan-music

# 进入容器调试
docker exec -it wan-music /bin/bash

# 复制 cookie 文件到容器
docker cp ./netease_cookie.txt wan-music:/app/clients/cookie/
docker cp ./qq_cookie.txt wan-music:/app/clients/cookie/

# 容器内重启
docker restart wan-music

# 停止并删除
docker compose down

# 完全清理（包括卷）
docker compose down -v
```

## 持久化数据

容器使用 Docker volume 持久化 cookie 文件：

```yaml
volumes:
  - cookie-data:/app/clients/cookie
```

数据保留位置：`/var/lib/docker/volumes/cookie-data/_data/`

## 健康检查

镜像内置健康检查：

```bash
# 查看健康状态
docker ps  # STATUS 列显示 healthy/unhealthy

# 手动检查
curl http://localhost:5002/health
# 返回: {"status": "healthy"}
```

## 安全

| 措施 | 说明 |
|------|------|
| 非 root 用户 | 容器内使用 `wanmusic` 用户运行 |
| Trivy 扫描 | 每次构建自动扫描高危漏洞 |
| 多阶段构建 | 不包含构建工具，减小攻击面 |
| .dockerignore | 排除 cookie/.env 等敏感文件 |
| 自动标签 | 镜像元数据符合 OCI 标准 |

## 故障排查

### 容器无法启动

```bash
# 查看日志
docker logs wan-music

# 常见错误：
# 1) 端口被占用 → 修改 .env 的 HOST_PORT
# 2) 权限问题 → 检查 cookie-data volume
# 3) 前端构建失败 → 本地运行 npm run build 验证
```

### API 调用失败

```bash
# 进入容器测试
docker exec -it wan-music /bin/bash
curl http://localhost:5002/health
```

### 清理重建

```bash
# 清理所有缓存和容器
docker compose down -v
docker system prune -a
docker compose build --no-cache
docker compose up -d
```

## 生产部署建议

### 反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name music.example.com;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 长连接支持（SSE 流式下载）
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

### HTTPS（Let's Encrypt + Caddy）

```caddy
music.example.com {
    reverse_proxy 127.0.0.1:5002
    encode gzip
}
```

### 自动更新（Watchtower）

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --cleanup \
  --schedule "0 0 4 * * *"  # 每天凌晨 4 点检查更新
```
