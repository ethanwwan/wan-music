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
- **统一响应格式**: `{code, message, data}`

```json
// 成功
{ "code": 200, "message": "success", "data": { /* 响应数据 */ } }
// 失败
{ "code": 400, "message": "错误信息", "data": null }
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

---

## 接口列表

### 1. 健康检查

**`GET /health`**

```bash
curl http://localhost:5002/health
# {"status": "healthy"}
```

### 2. 统一搜索

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
| quality | string | 否 | lossless | 音质偏好（用于选择最佳可用音质） |
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

### 3. 获取歌曲信息

**`POST /song`**

支持**传链接**（推荐）或**传 ID**。根据 `type` 参数返回不同内容。

**请求参数**（`application/x-www-form-urlencoded`）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 否 | - | 完整歌曲链接（推荐，自动解析平台和 ID） |
| ids / id | string | 否 | - | 歌曲 ID（逗号分隔时取第一个） |
| source | string | 否 | - | 平台（不传则从 URL 推断） |
| type | string | 否 | json | `url` / `name` / `lyric` / `json` |
| level | string | 否 | lossless | 音质等级 |

**音质等级**：

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

**type=json 响应**：

```json
{
  "data": {
    "id": "123456",
    "name": "有没有人告诉你",
    "ar_name": "陈楚生",
    "al_name": "快乐男声",
    "pic": "https://...",
    "level": "lossless",
    "source": "netease",
    "lyric": "[00:00.00]...",
    "tlyric": "",
    "fileType": "flac",
    "url": "https://example.com/song.flac"
  }
}
```

### 4. 获取歌单详情

**`POST /playlist`**

支持**传链接**（推荐）或**传 ID**。

**请求参数**（`application/x-www-form-urlencoded`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 否 | 完整歌单链接（推荐） |
| id | string | 否 | 歌单 ID |
| source | string | 否 | 平台（不传则从 URL 推断） |

**响应 data**：

```json
{
  "data": {
    "playlist": {
      "id": "456",
      "name": "华语流行金曲",
      "cover": "https://...",
      "description": "...",
      "trackCount": 50,
      "playCount": 1234567,
      "creator": "...",
      "source": "netease",
      "tracks": [
        {
          "id": "1",
          "name": "歌曲1",
          "artists": "歌手1",
          "album": "专辑1",
          "duration": 245000
        }
      ]
    }
  }
}
```

### 5. 单曲下载（代理）

**`GET /download`**

后端代理下载单曲（解决 CORS），可选自动写入 ID3 标签。

**Query 参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | string | 是 | - | 歌曲 ID |
| quality | string | 否 | lossless | 音质 |
| source | string | 否 | - | 平台 |
| name | string | 否 | song | 歌曲名 |
| artist | string | 否 | - | 歌手 |
| album | string | 否 | - | 专辑 |
| lrc | string | 否 | - | 歌词（用于 metadata） |
| filenameFormat | string | 否 | song-artist | song-artist / artist-song / song |
| writeMetadata | bool | 否 | true | 是否写入元数据 |

**响应**：音频文件流（`audio/mpeg` / `audio/flac` / `audio/mp4`）

**响应头**：
- `Content-Disposition`: 文件名
- `X-Actual-Quality`: 实际音质（VIP 不可用时降级）
- `X-Quality-Downgraded`: `1` 表示音质被降级
- `X-Actual-FileType`: 实际文件类型（mp3/flac/m4a，通过 magic bytes 检测）

### 6. 批量下载（异步 + SSE 进度）

支持并发下载 6 首歌曲，完成后打包成 ZIP（单曲则直接返回音频文件）。

#### 6.1 启动任务

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
  "data": {
    "task_id": "task_abc123",
    "total": 38,
    "file_size": 12345678
  }
}
```

#### 6.2 任务列表

**`GET /download/batch/list`** — 返回所有任务（按创建时间倒序）

#### 6.3 任务详情

**`GET /download/batch/info/<task_id>`**

#### 6.4 SSE 实时进度

**`GET /download/batch/progress/<task_id>`**

```bash
curl -N http://localhost:5002/download/batch/progress/<task_id>
```

每 0.3s 推一条：

```
data: {"status":"running","total":38,"completed":15,"failed":1,"current":"歌名","file_size":12345}
```

status 取值：`running` / `done` / `error` / `cancelled`

#### 6.5 下载完成文件

**`GET /download/batch/file/<task_id>`**

- 单曲：直接返回音频文件
- 多首：返回 ZIP 压缩包

#### 6.6 取消/删除任务

**`DELETE /download/batch/<task_id>`**

取消进行中的任务或清理已完成的文件。

---

## HTTP 方法说明

按 RESTful 规范设计，**不强求统一方法**：

| 方法 | 用途 | 接口 |
|------|------|------|
| GET | 只读 + 文件下载（浏览器要求） | `/health`, `/download/batch/list`, `/download/batch/info`, `/download/batch/progress`, `/download/batch/file`, `/download` |
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

# 通过 URL 获取歌曲
curl -X POST http://localhost:5002/song \
  -d "url=https://music.163.com/song?id=123456&type=json&level=lossless"

# 获取歌单详情
curl -X POST http://localhost:5002/playlist \
  -d "url=https://music.163.com/playlist?id=7583298906"

# 单曲下载
curl -o song.flac "http://localhost:5002/download?id=123456&quality=lossless&name=test&artist=test"

# 批量下载
curl -X POST http://localhost:5002/download/batch/start \
  -H "Content-Type: application/json" \
  -d '{"items":[{"id":"123","quality":"lossless"}],"name":"playlist"}'
```
