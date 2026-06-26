# Docker 部署 demo

本目录是 **Docker 部署的参考配置**，方便本地测试和复制到部署环境。

## ⚠️ 参考性质

`docker-compose.yml` 只用于 demo，正式部署请按需修改：
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

## 部署到远程

复制 `docker-compose.yml` 到部署目录后修改使用：

```bash
cp docker/docker-compose.yml deploy/
cd deploy
# 修改端口、卷、镜像名等
nano docker-compose.yml

docker compose up -d
```

## 配置来源

- **端口 6005**：硬编码在 yml 里
- **后端端口 6005**：由 [../Dockerfile](../Dockerfile) 的 `ARG PORT=6005` 决定
- **统一管理**：如需通过 [../config.json](../config.json) 管理，可扩展 yml 和 Dockerfile
