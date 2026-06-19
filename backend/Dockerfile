# ============================================================
# Stage 1: 构建前端 (Vue 3 + Vite)
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 单独复制 package.json 利用 Docker 缓存
COPY frontend/package.json frontend/package-lock.json* ./

# 安装依赖
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# ============================================================
# Stage 2: 构建后端镜像 (Flask)
# ============================================================
FROM python:3.11-slim AS backend

# 元数据
LABEL maintainer="PGWan" \
      description="Wan Music - 多平台音乐搜索/解析/下载" \
      version="1.0.0"

# 环境变量（可通过 docker run -e PORT=8080 或 compose environment 覆盖）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=main.py \
    FLASK_ENV=production \
    PORT=5002

# 容器内可配置端口（构建时默认值，可被运行时覆盖）
ARG PORT=5002
ENV PORT=${PORT}

# 安装系统依赖（mutagen 需要 + 健康检查）
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
# Vite 默认输出到 dist/，结构为 dist/index.html + dist/assets/*
COPY --from=frontend-builder /app/frontend/dist/index.html ./templates/index.html
COPY --from=frontend-builder /app/frontend/dist/assets ./static/assets
# Vite 构建时 public/ 下的文件会输出到 dist/ 根目录
COPY --from=frontend-builder /app/frontend/dist/favicon.svg ./static/favicon.svg 2>/dev/null || true

# 创建 cookie 目录（运行时会用到）
RUN mkdir -p /app/clients/cookie && chown -R wanmusic:wanmusic /app

# 切换到非 root 用户
USER wanmusic

EXPOSE ${PORT}

# 健康检查（端口从 $PORT 读取，curl 在 alpine 中不预装，所以先要装）
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# 使用 gunicorn 启动（生产环境）
# 4 worker × 2 threads，根据 CPU 核心数调整
# 端口从 $PORT 环境变量读取（默认 5002）
CMD ["sh", "-c", "gunicorn \
     --bind 0.0.0.0:${PORT} \
     --workers 2 \
     --threads 4 \
     --timeout 120 \
     --access-logfile - \
     --error-logfile - \
     main:app"]
