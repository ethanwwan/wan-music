# Wan-Music - 网易云音乐无损解析工具

<div align="center">

**功能强大的网易云音乐解析工具，支持多种音质下载**

[在线体验](http://localhost:5020) • [Docker Hub](https://hub.docker.com/r/ethanwwan/wan-music) • [GitHub](https://github.com/ethanwwan/wan-music) • [报告问题](https://github.com/ethanwwan/wan-music/issues)

![Docker Stars](https://img.shields.io/docker/stars/ethanwwan/wan-music)
![Docker Pulls](https://img.shields.io/docker/pulls/ethanwwan/wan-music)
![Docker Version](https://img.shields.io/docker/v/ethanwwan/wan-music?sort=semver)
![Docker Size](https://img.shields.io/docker/image-size/ethanwwan/wan-music/latest)

</div>

---

## ✨ 功能特性

### 🎵 核心功能
- **🔍 歌曲搜索** - 支持关键词搜索网易云音乐库，获取歌曲列表
- **🎧 单曲解析** - 解析单首歌曲的详细信息（歌手、专辑、封面）和下载链接
- **📋 歌单解析** - 批量解析歌单中的所有歌曲信息，支持导出
- **💿 专辑解析** - 批量解析专辑中的所有歌曲信息
- **⬇️ 音乐下载** - 支持多种音质的音乐文件下载，自动添加元数据
- **🌐 Web界面** - 简洁直观的Web操作界面，支持深色模式
- **📱 响应式设计** - 适配PC、平板和移动设备

### 🎼 音质支持

| 音质参数 | 说明 | 会员要求 | 文件格式 |
|----------|------|----------|----------|
| `standard` | 标准音质 (128kbps) | 免费 | MP3 |
| `exhigh` | 极高音质 (320kbps) | VIP | MP3 |
| `lossless` | 无损音质 (FLAC) | VIP | FLAC |
| `hires` | Hi-Res音质 (24bit/96kHz) | VIP | FLAC |
| `jyeffect` | 高清臻音 (Spatial Audio) | VIP | MP3 |
| `sky` | 沉浸环绕声 (Surround Audio) | SVIP | MP3 |
| `jymaster` | 超清母带 (Master) | SVIP | FLAC |
| `dolby` | 杜比全景声 (Dolby Atmos) | SVIP | M4A |

### 🎨 界面特性

- **深色模式** - 支持明暗主题切换
- **历史记录** - 记录最近解析的歌曲
- **批量操作** - 支持歌单和专辑批量解析
- **元数据自动添加** - 自动为下载的音乐添加ID3标签
- **进度显示** - 实时显示下载进度

---

## 🚀 快速开始

### 🐳 使用 Docker 部署（推荐）

#### 使用 Docker Compose（推荐）
```bash
# 1. 克隆项目
git clone https://github.com/Awan/wan-music.git
cd wan-music

# 2. 启动容器
docker-compose up -d

# 3. 访问界面
# 打开浏览器访问：http://localhost:5020
```

#### 使用 Docker Run
```bash
# 启动容器
docker run -d \
  --name wan-music \
  --restart always \
  -p 5020:5020 \
  -e TZ=Asia/Shanghai \
  -e MUSIC_COOKIE="_ntes_nnid=ec5976e5xxxxx" \
  ethanwwan/wan-music:latest
```

### 🐍 本地开发部署

```bash
# 1. 克隆项目
git clone https://github.com/Awan/wan-music.git
cd wan-music

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活虚拟环境
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置 Cookie
cp .env.example .env
nano .env

# 6. 启动服务
python main.py

# 7. 访问界面
# 打开浏览器访问：http://localhost:5020
```

### 🚀 生产环境部署（Gunicorn）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 直接使用 Gunicorn 启动
gunicorn main:app --bind 0.0.0.0:5020 --workers 4

```


---

## � 使用指南

### 1. 获取网易云音乐 Cookie

1. 登录 [网易云音乐网页版](https://music.163.com/)
2. 按 `F12` 打开开发者工具
3. 切换到 `Network` (网络) 标签页
4. 刷新页面或点击任意歌曲
5. 点击任意请求，在 `Request Headers` (请求头) 中找到 `Cookie`
6. 复制完整的 Cookie 值
7. 粘贴到 `.env` 文件中的 `MUSIC_COOKIE` 字段

> ⚠️ **重要提示**：
> - 必须使用黑胶会员账号的Cookie
> - 高音质（hires及以上）需要VIP账号
> - 杜比/母带/环绕声需要SVIP账号
> - 定期更新Cookie以保持有效性

### 2. Web界面使用

#### 🔍 歌曲搜索
1. 选择功能：**歌曲搜索**
2. 输入关键词（歌曲名、歌手名等）
3. 点击**搜索**按钮
4. 在搜索结果中点击**解析**或**下载**按钮

#### 🎧 单曲解析
1. 选择功能：**单曲解析**
2. 输入歌曲ID或网易云音乐链接
   - 支持格式：`1234567890` 或 `https://music.163.com/song?id=1234567890`
3. 点击**解析**按钮查看歌曲信息

#### 📋 歌单解析
1. 选择功能：**歌单解析**
2. 输入歌单ID或网易云音乐歌单链接
   - 支持格式：`1234567890` 或 `https://music.163.com/playlist?id=1234567890`
3. 点击**解析**按钮查看歌单中所有歌曲
4. 点击单首歌曲的**解析**或**下载**按钮

#### 💿 专辑解析
1. 选择功能：**专辑解析**
2. 输入专辑ID或网易云音乐专辑链接
   - 支持格式：`1234567890` 或 `https://music.163.com/album?id=1234567890`
3. 点击**解析**按钮查看专辑中所有歌曲
4. 点击单首歌曲的**解析**或**下载**按钮

#### ⬇️ 音乐下载
1. 选择功能：**音乐下载**
2. 输入歌曲ID或链接
3. 选择音质（标准/极高/无损/Hi-Res/杜比全景声等）
4. 点击**下载**按钮

### 支持的链接格式

```bash
# 歌曲链接
https://music.163.com/song?id=1234567890
https://music.163.com/#/song?id=1234567890

# 歌单链接
https://music.163.com/playlist?id=1234567890
https://music.163.com/#/playlist?id=1234567890

# 专辑链接
https://music.163.com/album?id=1234567890
https://music.163.com/#/album?id=1234567890

# 直接使用ID
1234567890
```

---

## 🔌 API接口文档

### 基础信息
- **Base URL**: `http://localhost:5020`
- **请求方式**: GET / POST
- **响应格式**: JSON

### 接口列表

#### 1. 健康检查
```http
GET http://localhost:5020/health
```

**响应示例**:
```json
{
  "status": "ok",
  "message": "Service is running"
}
```

#### 2. 歌曲搜索
```http
POST http://localhost:5020/search
Content-Type: application/json

{
  "keyword": "周杰伦 稻香",
  "limit": 10
}
```

**响应示例**:
```json
{
  "status": 200,
  "success": true,
  "message": "搜索成功",
  "data": [
    {
      "id": "123456789",
      "name": "稻香",
      "ar": [{"name": "周杰伦"}],
      "al": {"name": "魔杰座"}
    }
  ]
}
```

#### 3. 单曲解析
```http
GET http://localhost:5020/song?id=123456789&level=hires&type=json
```

**响应示例**:
```json
{
  "status": 200,
  "success": true,
  "message": "获取歌曲信息成功",
  "data": {
    "id": "123456789",
    "name": "歌曲名",
    "ar_name": "歌手名",
    "al_name": "专辑名",
    "level": "hires",
    "url": "https://...",
    "lyric": "..."
  }
}
```

#### 4. 歌单解析
```http
POST http://localhost:5020/playlist
Content-Type: application/json

{
  "id": "123456789"
}
```

#### 5. 专辑解析
```http
POST http://localhost:5020/album
Content-Type: application/json

{
  "id": "123456789"
}
```

#### 6. 音乐下载
```http
POST http://localhost:5020/download
Content-Type: application/json

{
  "id": "123456789",
  "quality": "lossless"
}
```

**响应**: 直接返回音频文件流

#### 7. API信息
```http
GET http://localhost:5020/api/info
```

---

## ⚙️ 配置说明

### 环境变量

可以通过 `.env` 文件配置服务：

```bash
# 复制.env.example为.env
cp .env.example .env
```

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_ENV` | prod | 运行环境（prod/dev） |
| `WEB_PORT` | 5020 | 服务端口 |
| `TZ` | Asia/Shanghai | 时区 |
| `LOG_LEVEL` | INFO | 日志级别 |
| `MAX_FILE_SIZE` | 524288000 | 文件大小限制（字节，默认500MB） |
| `REQUEST_TIMEOUT` | 30 | 请求超时时间（秒） |
| `CORS_ORIGINS` | * | 跨域白名单 |
| `MUSIC_COOKIE` | 空 | 网易云音乐Cookie（从 .env 文件获取，必填） |

### Docker Compose 配置

```yaml
services:
  wan-music:
    image: ethanwwan/wan-music:latest
    container_name: wan-music
    restart: always
    ports:
      - 5020:5020
    environment:
      - APP_ENV=prod
      - TZ=Asia/Shanghai
      - WEB_PORT=5020
      - MUSIC_COOKIE=_ntes_nnid=ec5976e5xxxxx

    networks:
      - wan-music-network

networks:
  wan-music-network:
    driver: bridge
```

---

## 🔧 故障排除

### 常见问题

#### 1. Cookie无效
**问题**：提示"Cookie无效"或"需要会员"

**解决方案**：
- 确认使用的是黑胶会员账号
- 重新获取Cookie并更新 `.env` 文件中的 `MUSIC_COOKIE` 配置
- 检查Cookie格式是否正确

#### 2. 无法下载高音质
**问题**：只能下载标准音质，选择高音质无响应

**解决方案**：
- 确认账号是VIP/SVIP会员
- 检查Cookie是否有效
- 确认歌曲本身支持所选音质

#### 3. 服务启动失败
**问题**：运行 `python main.py` 报错

**解决方案**：
- 检查Python版本（需要3.9+）
- 安装所有依赖：`pip install -r requirements.txt`
- 检查端口5020是否被占用

#### 4. 下载文件损坏
**问题**：下载的音频文件无法播放

**解决方案**：
- 检查网络连接是否稳定
- 重新下载文件
- 尝试其他音质选项

### 日志查看

```bash
# 查看服务日志
tail -f music_api.log

# Docker 日志
docker logs -f wan-music
```

---

## 📁 项目结构

```
wan-music/
├── main.py                 # 主程序入口
├── requirements.txt        # Python依赖
├── Dockerfile              # Docker构建文件
├── docker-compose.yml      # Docker Compose配置
├── .env.example            # 环境变量示例
├── .venv/                  # Python虚拟环境（本地开发）
├── .github/
│   └── workflows/
│       └── docker-publish.yml  # GitHub Actions
├── api/
│   ├── __init__.py
│   ├── music_api.py        # 音乐API核心模块
│   ├── music_downloader.py # 音乐下载模块
│   ├── cookie_manager.py   # Cookie管理模块
│   └── qr_login.py         # 二维码登录模块
└── frontend/
    ├── index.html          # Web界面
    ├── css/                # 样式文件
    ├── js/                 # 脚本文件
    └── imgs/               # 图片资源
```

### 技术栈

- **后端**：Flask + Python
- **前端**：Bootstrap + jQuery
- **音频处理**：mutagen
- **HTTP客户端**：aiohttp + requests
- **容器化**：Docker + GitHub Actions

---

## 🤖 CI/CD

### Docker 镜像标签

| 标签 | 说明 |
|------|------|
| `latest` | 最新稳定版 |
| `v1.x.x` | 语义化版本 |
| `dev` | 开发版本 |

### GitHub Actions

推送版本标签自动构建并推送到 Docker Hub：

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## 📄 许可证

本项目采用 MIT 许可证开源。

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

---

## 📞 联系方式

- **GitHub Issues**：[提交问题](https://github.com/ethanwwan/wan-music/issues)
- **Docker Hub**：[ethanwwan/wan-music](https://hub.docker.com/r/ethanwwan/wan-music)

---

欢迎 Star、Fork 和 PR！
