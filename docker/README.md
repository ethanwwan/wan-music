# Docker 部署 demo

本目录是 **Docker 部署的示例配置**，方便本地测试。

## ⚠️ 这只是 demo

正式部署时请根据需要修改：
- 端口（默认 6005）
- 镜像名
- 卷挂载
- 资源限制

## 文件

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 部署示例（直接用 `docker compose -f` 启动） |

## 本地测试

```bash
# 在项目根目录
docker compose -f docker/docker-compose.yml up -d --build
open http://localhost:6005
```

## 正式部署

复制 `docker-compose.yml` 到你的部署目录，按需修改后启动：

```bash
# 1. 复制并修改
cp docker/docker-compose.yml deploy/
cd deploy
nano docker-compose.yml  # 改端口/卷等

# 2. 拉取/构建镜像后启动
docker compose up -d
```

## 配置来源

- **端口**：硬编码在 yml 里（6005）
- **后端端口**：也由 [../Dockerfile](../Dockerfile) 的 `ARG PORT=6005` 决定
- **自定义**：修改 yml 中的 `ports` 和 Dockerfile 中的 `ARG PORT`

如果想统一管理端口到 [../config.json](../config.json)，可以扩展 yml 和 Dockerfile。
