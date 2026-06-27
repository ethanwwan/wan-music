# Backend

> Flask 后端服务

详细文档见根目录 [README.md](../README.md)。

## 目录

- `clients/` - 音乐平台客户端
- `routes/` - Flask 路由
- `services/` - 业务服务
- `utils/` - 工具函数

## 维护脚本

```bash
# 元数据检查
python3 ../scripts/check_metadata.py

# 歌单同步
python3 ../scripts/sync_artist_to_playlist.py
```

## 许可证

MIT

---

## API 文档

> 本文档只列出**前端实际使用**的接口。删除/调整前请确认前端调用。

### 基础信息

- **默认端口**: `5002`（可通过环境变量 `PORT` 覆盖）
- **数据格式**: JSON
- **统一响应格式**: `{success, message, data}`

```json
// 成功
{ "success": true, "message": "success", "data": { /* 响应数据 */ } }
// 失败
{ "success": false, "message": "错误信息", "data": null }
```

### 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 403 | 版权限制，无法获取播放链接 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

### 支持的平台

| value | 说明 |
|-------|------|
| `netease` | 网易云（支持搜索歌曲/歌单、下载，需 cookie 解锁 VIP 音质） |
| `qq` | QQ音乐（支持搜索歌曲/歌单、下载） |
| `kugou` | 酷狗（支持搜索歌曲、下载） |
| `bodian` | 波点（支持搜索歌曲、下载） |

### 音质等级

| 值 | 说明 |
|----|------|
| `standard` | 标准音质 (128kbps) |
| `exhigh` | 极高音质 (320kbps) |
| `lossless` | 无损音质 (FLAC) |
| `hires` | Hi-Res 音质 (FLAC 24bit) |
| `sky` | 沉浸环绕声 |
| `jyeffect` | 高清臻音 |
| `jymaster` | 超清母带 |
| `dolby` | 杜比全景声 |

---

## 接口列表

### 1. 健康检查

**`GET /health`**

```bash
curl http://localhost:5002/health
# {"status": "healthy"}
```

### 2. 获取平台列表

**`GET /platforms`**

返回后端支持的音乐平台元数据（id / name / color / description），前端从该接口读取并动态渲染下拉选项，避免硬编码平台列表。

```bash
curl http://localhost:5002/platforms
```

```json
{
  "success": true,
  "data": [
    {"id": "netease", "name": "网易云音乐",   "color": "#e72d2c", "description": "网易云音乐平台"},
    {"id": "qq",      "name": "QQ音乐",  "color": "#31c27c", "description": "QQ音乐平台"},
    {"id": "bodian",  "name": "波点音乐", "color": "#ff7e29", "description": "波点音乐平台"},
    {"id": "kugou",   "name": "酷狗音乐", "color": "#2a8eff", "description": "酷狗音乐平台"}
  ]
}
```

### 3. 统一搜索

**`POST /search`**

支持两种模式：
- **关键词搜索**：搜歌曲/歌单（`type` 控制）
- **URL 解析**：粘贴歌曲/歌单链接直接获取详情

**请求参数**（JSON）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword | string | 是 | - | 搜索关键词 或 完整 URL |
| type | int | 否 | 0 | 0=全部 / 1=歌曲 / 2=歌单（仅关键词搜索生效） |
| source | string | 否 | null | 平台过滤，null=全部 |
| quality | string | 否 | lossless | 音质偏好 |
| limit | int | 否 | 50 | 返回数量 |

**响应 data**：

```json
{
  "type": 1,
  "data": [
    {
      "_type": "song",
      "id": "123",
      "name": "有没有人告诉你",
      "artists": "陈楚生",
      "album": "快乐男声",
      "picUrl": "https://...",
      "duration": 245000,
      "source": "netease"
    }
  ],
  "warnings": []
}
```

**warnings**：
- `playlist_search_unsupported`：当前平台不支持搜索歌单

### 4. 获取歌曲信息

**`POST /song`**

获取歌曲完整信息：**基本信息 + 播放/下载地址 + 歌词**，前端播放、悬浮球歌词展示、下载均基于此接口的返回数据。

后端 `/download/batch/start` 内部也复用 `music_service.get_song_info` 拉取同样数据来写元数据，前端不需要为下载额外传 metadata。

支持**传链接**（推荐）或**传 ID**。

**请求体**（JSON 或 form）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 否 | - | 完整歌曲链接（推荐，自动解析平台和 ID） |
| id / ids | string | 否 | - | 歌曲 ID |
| source | string | 否 | - | 平台（不传则从 URL 推断） |
| level | string | 否 | lossless | 音质等级 |

**响应 data**：

```json
{
  "id": "123456",
  "name": "有没有人告诉你",
  "artist": "陈楚生",
  "album": "快乐男声",
  "cover": "https://...",
  "duration": 245000,
  "url": "https://example.com/song.flac",
  "level": "lossless",
  "fileType": "flac",
  "source": "netease",
  "available": true,
  "lyric": "[00:00.00]歌词内容\n[00:05.00]..."
}
```

`available=false` 表示该歌曲因版权问题无法播放。

### 5. 获取歌单详情

**`POST /playlist`**

支持**传链接**（推荐）或**传 ID**。

**请求参数**（`application/x-www-form-urlencoded`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 否 | 完整歌单链接（推荐） |
| id | string | 否 | 歌单 ID |
| source | string | 否 | 平台（不传则从 URL 推断） |

**响应 data.playlist**：

```json
{
  "id": "456",
  "name": "华语流行金曲",
  "cover": "https://...",
  "description": "...",
  "trackCount": 50,
  "playCount": 1234567,
  "source": "netease",
  "tracks": [
    { "id": "1", "name": "歌曲1", "artists": "歌手1", "album": "专辑1", "duration": 245000 }
  ]
}
```

### 5. 批量下载（异步 + SSE 进度）

支持并发下载 6 首歌曲，完成后打包成 ZIP（单曲则直接返回音频文件）。
单首下载也走同一异步流程，前端不再需要单独的同步下载接口。

#### 5.1 启动任务

**`POST /download/batch/start`**

```json
{
  "items": [
    {
      "id": "123",
      "quality": "lossless",
      "source": "netease",
      "name": "歌曲名",
      "artist": "歌手",
      "album": "专辑",
      "qualityMap": { "lossless": { "size": 12345 } }
    }
  ],
  "name": "我的歌单",
  "settings": {
    "writeMetadata": true,
    "filenameFormat": "song-artist"
  }
}
```

**响应**：

```json
{
  "data": { "task_id": "task_abc123", "total": 38, "file_size": 12345678 }
}
```

#### 5.2 任务列表

**`GET /download/batch/list`** — 返回所有任务（按创建时间倒序）

#### 5.3 SSE 实时进度

**`GET /download/batch/progress/<task_id>`**

```bash
curl -N http://localhost:5002/download/batch/progress/<task_id>
```

每 0.3s 推一条：

```
data: {"status":"running","total":38,"completed":15,"failed":1,"current":"歌名","file_size":12345}
```

status 取值：`running` / `done` / `error` / `cancelled`

#### 5.4 下载完成文件

**`GET /download/batch/file/<task_id>`**

- 单曲：直接返回音频文件
- 多首：返回 ZIP 压缩包

响应头会包含 `X-Actual-Quality` / `X-Quality-Downgraded` / `X-Actual-FileType` 用于前端展示真实音质。

#### 5.5 取消/删除任务

**`DELETE /download/batch/<task_id>`**

取消进行中的任务或清理已完成的文件。

---

## HTTP 方法说明

| 方法 | 用途 | 接口 |
|------|------|------|
| GET | 只读 + 文件下载（浏览器要求） | `/health`, `/download/batch/list`, `/download/batch/progress`, `/download/batch/file` |
| POST | 复杂请求体 / 表单 | `/search`, `/song`, `/playlist`, `/download/batch/start` |
| DELETE | 资源删除 | `/download/batch/<task_id>` |

## 部署说明

### 端口

端口由根目录 [`../config.json`](../config.json) 配置：

| 环境 | 端口 | 说明 |
|------|------|------|
| 开发（`PORT=5005`） | 5005 | `config.json: backend.devBackendPort` |
| 生产预览（`PORT=6005`） | 6005 | `config.json: backend.prodBackendPort` |
| Docker 部署 | 6005 | `Dockerfile` 的 `ARG PORT=6005` |

### 启动

```bash
PORT=5005 python3 main.py
```

## 使用示例（cURL）

```bash
# 健康检查
curl http://localhost:5002/health

# 搜索歌曲
curl -X POST http://localhost:5002/search \
  -H "Content-Type: application/json" \
  -d '{"keyword": "陈楚生", "type": 1, "limit": 5}'

# 通过 URL 获取歌曲完整信息
curl -X POST http://localhost:5002/song \
  -H "Content-Type: application/json" \
  -d '{"url": "https://music.163.com/song?id=123456", "level": "lossless"}'

# 通过 ID 获取歌曲完整信息
curl -X POST http://localhost:5002/song \
  -H "Content-Type: application/json" \
  -d '{"id": "123456", "source": "netease", "level": "lossless"}'

# 获取歌单详情
curl -X POST http://localhost:5002/playlist \
  -d "url=https://music.163.com/playlist?id=7583298906"

# 批量下载
curl -X POST http://localhost:5002/download/batch/start \
  -H "Content-Type: application/json" \
  -d '{"items":[{"id":"123","quality":"lossless"}],"name":"playlist"}'
```
