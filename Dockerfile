# ============================================================
# Stage 1: 构建前端 (Vue 3 + Vite)
# Node 22 是当前 LTS（Node 20 已被 GitHub Actions runner 弃用）
# ============================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

# 单独复制 package.json 利用 Docker 缓存
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# ============================================================
# Stage 2: 构建后端镜像 (Flask + gunicorn)
# ============================================================
FROM python:3.11-slim AS backend

# 元数据
LABEL maintainer="PGWan" \
      description="Wan Music - 多平台音乐搜索/解析/下载"

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=main.py \
    PORT=6005

# 安装系统依赖（仅 curl 用于健康检查 + gcc 用于构建 mutagen 等含 C 扩展的包）
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r wanmusic && useradd -r -g wanmusic wanmusic

WORKDIR /app

# 单独复制 requirements.txt 利用 Docker 缓存
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./

# 复制前端构建产物到 Flask 的 templates/static 目录
# Vite 默认输出到 dist/，结构为 dist/index.html + dist/assets/* + dist/favicon.svg
COPY --from=frontend-builder /app/frontend/dist/index.html ./templates/index.html
COPY --from=frontend-builder /app/frontend/dist/assets ./static/assets
COPY --from=frontend-builder /app/frontend/dist/favicon.svg ./static/favicon.svg

# 创建 cookie 目录（运行时会用到）
RUN mkdir -p /app/clients/cookie && chown -R wanmusic:wanmusic /app

USER wanmusic

EXPOSE ${PORT}

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 使用 gunicorn 启动（生产环境）
# 端口从 $PORT 环境变量读取（默认 6005，可被运行时覆盖）
CMD ["sh", "-c", "gunicorn \
     --bind 0.0.0.0:${PORT} \
     --workers 2 \
     --threads 4 \
     --timeout 120 \
     --access-logfile - \
     --error-logfile - \
     main:app"]
