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


## 基础信息

- **服务地址**: `http://localhost:5002`
- **数据格式**: JSON
- **统一响应格式**: `{code, message, data}`

---

## 通用响应格式

### 成功
```json
{
  "code": 200,
  "message": "success",
  "data": { /* 响应数据 */ }
}
```

### 失败
```json
{
  "code": 400,
  "message": "错误信息",
  "data": null
}
```

### 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 403 | 版权限制，无法获取播放链接 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

---

## 支持的平台

| value | label | 说明 |
|-------|-------|------|
| `netease` | 网易云音乐 | 支持搜索歌曲/歌单、下载（含 VIP 音质，需 cookie） |
| `qq` | QQ音乐 | 支持搜索歌曲/歌单、下载 |
| `bodian` | 波点音乐 | 支持搜索歌曲、下载（不支持搜索歌单） |
| `kugou` | 酷狗音乐 | 支持搜索歌曲、下载（不支持搜索歌单） |

---

## 接口列表

### 1. 健康检查

**`GET /health`**

```bash
curl http://localhost:5002/health
# {"status": "healthy"}
```

---

### 2. 统一搜索（推荐）

**`POST /search`**

支持三种搜索模式：
- **关键词搜索**：搜歌曲/歌单
- **URL 解析**：粘贴歌曲/歌单链接直接获取详情

**请求参数**（JSON）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword | string | 是 | - | 搜索关键词 或 完整 URL |
| type | int | 否 | 0 | 0=全部 / 1=歌曲 / 2=歌单（仅关键词搜索生效） |
| source | string | 否 | null | 平台过滤（netease/qq/kugou/bodian），null=全部 |
| quality | string | 否 | lossless | 音质偏好（用于选择最佳可用音质） |
| limit | int | 否 | 50 | 返回数量 |

**响应 data**：

```json
{
  "type": 0,
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
    },
    {
      "_type": "playlist",
      "id": "456",
      "name": "华语流行金曲",
      "cover": "https://...",
      "trackCount": 50,
      "playCount": 1234567,
      "source": "netease"
    }
  ],
  "warnings": []
}
```

**warnings 字段**：
- `playlist_search_unsupported`：当前平台不支持搜索歌单

**URL 解析示例**：

```json
// 请求
{ "keyword": "https://music.163.com/song?id=123456" }

// 响应：type=1, data=[{...该歌曲详情, _type: "song"}]
```

---

### 3. 搜索歌单（兼容旧接口）

**`POST /search/playlist`**

内部转调 `/search` 的 `type=2`，仅返回歌单。

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 是 | 搜索关键词 |
| source | string | 否 | 平台过滤 |
| limit | int | 否 | 默认 20 |

**响应 data**：

```json
{
  "playlists": [
    {
      "id": "456",
      "name": "华语流行金曲",
      "cover": "https://...",
      "trackCount": 50,
      "playCount": 1234567,
      "source": "netease"
    }
  ],
  "warnings": []
}
```

---

### 4. 获取歌曲信息

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

**type 说明**：

- `url`：仅返回下载 URL
- `name`：仅返回歌曲名/歌手/专辑
- `lyric`：仅返回歌词
- `json`：返回完整信息（默认）

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

**响应示例（type=json）**：

```json
{
  "code": 200,
  "message": "获取歌曲信息成功",
  "data": {
    "id": "123456",
    "name": "有没有人告诉你",
    "ar_name": "陈楚生",
    "al_name": "快乐男声",
    "pic": "https://...",
    "level": "lossless",
    "source": "netease",
    "lyric": "[00:00.00]有没有人告诉你...",
    "tlyric": "",
    "fileType": "flac",
    "url": "https://example.com/song.flac"
  }
}
```

---

### 5. 获取歌单详情

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
  "code": 200,
  "message": "获取歌单成功",
  "data": {
    "playlist": {
      "id": "456",
      "name": "华语流行金曲",
      "cover": "https://...",
      "description": "精选华语流行歌曲",
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

---

### 6. 获取数据源列表

**`GET /api/data-sources`**

```json
{
  "code": 200,
  "message": "获取数据源列表成功",
  "data": [
    { "value": "netease", "label": "网易云音乐", "description": "网易云音乐平台" },
    { "value": "qq", "label": "QQ音乐", "description": "QQ音乐平台" },
    { "value": "bodian", "label": "波点音乐", "description": "波点音乐平台" },
    { "value": "kugou", "label": "酷狗音乐", "description": "酷狗音乐平台" }
  ]
}
```

---

### 7. URL 解析

**`POST /parse/url`**

解析 URL，返回平台、类型、资源 ID。

**请求参数**（`application/x-www-form-urlencoded`）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 是 | 要解析的链接 |

**响应**：

```json
{
  "code": 200,
  "message": "解析成功",
  "data": {
    "platform": "netease",
    "type": "music",
    "id": "123456"
  }
}
```

type 取值：`music` / `playlist` / `album`

---

### 8. URL 验证

**`POST /parse/validate`**

仅判断 URL 类型，不返回 ID。

**响应**：

```json
{
  "code": 200,
  "message": "验证成功",
  "data": {
    "type": "music",
    "isMusic": true,
    "isPlaylist": false,
    "isAlbum": false
  }
}
```

---

### 9. 单曲下载（代理，解决 CORS）

**`GET /download`**

后端代理下载单曲，可选自动写入 ID3 标签（标题/歌手/专辑/歌词/封面/平台/歌曲ID）。

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
- `X-Actual-Quality`: 实际音质（可能比请求的 quality 低，如 VIP 不可用时）
- `X-Quality-Downgraded`: `1` 表示实际音质被降级
- `X-Actual-FileType`: 实际文件类型（mp3/flac/m4a，通过 magic bytes 检测）

---

### 10. 批量下载（异步 + SSE 进度）

支持并发下载 6 首歌曲，完成后打包成 ZIP（单曲则直接返回音频文件）。

#### 10.1 启动批量任务

**`POST /download/batch/start`**

**请求体**：

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
  "code": 200,
  "message": "任务已启动",
  "data": {
    "task_id": "task_abc123",
    "total": 38,
    "file_size": 12345678
  }
}
```

#### 10.2 任务列表

**`GET /download/batch/list`**

返回所有任务（按创建时间倒序）。

#### 10.3 任务详情

**`GET /download/batch/info/<task_id>`**

#### 10.4 任务状态（一次性查询）

**`GET /download/batch/status/<task_id>`**

```json
{
  "code": 200,
  "data": {
    "status": "running",
    "total": 38,
    "completed": 15,
    "failed": 1,
    "current": "正在下载的歌名"
  }
}
```

#### 10.5 SSE 实时进度

**`GET /download/batch/progress/<task_id>`**

```bash
curl -N http://localhost:5002/download/batch/progress/<task_id>
```

每 0.3s 推一条：

```
data: {"status":"running","total":38,"completed":15,"failed":1,"current":"歌名","file_size":12345}
```

status 取值：`running` / `done` / `error` / `cancelled`

#### 10.6 下载完成文件

**`GET /download/batch/file/<task_id>`**

- 单曲：直接返回音频文件
- 多首：返回 ZIP 压缩包

#### 10.7 取消/删除任务

**`DELETE /download/batch/<task_id>`**

取消进行中的任务或清理已完成的文件。

---

### 11. 网易云 Cookie 状态

**`GET /api/netease/cookie/status`**

查看网易云 cookie 状态（不返回具体值），**自动 reload**：如果 cookie 文件被修改，下次调用会重新加载。

```json
{
  "code": 200,
  "data": {
    "active_path": "/app/clients/cookie/netease_cookie.txt",
    "file_exists": true,
    "cookie_keys": ["MUSIC_U", "NMTID", "__csrf"],
    "has_music_u": true,
    "is_vip": true,
    "cookie_count": 3
  }
}
```

---

## 使用示例

### JavaScript

```javascript
// 搜索歌曲
async function searchSongs(keyword, source = null) {
  const res = await fetch('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ keyword, source, type: 1, limit: 10 })
  });
  return (await res.json()).data;
}

// 通过 URL 获取歌曲
async function getSongByUrl(url) {
  const form = new URLSearchParams({ url, type: 'json', level: 'lossless' });
  const res = await fetch('/song', { method: 'POST', body: form });
  return (await res.json()).data;
}

// 解析歌单 URL
async function getPlaylistByUrl(url) {
  const form = new URLSearchParams({ url });
  const res = await fetch('/playlist', { method: 'POST', body: form });
  return (await res.json()).data.playlist;
}

// 单曲下载
function downloadSong(song) {
  const params = new URLSearchParams({
    id: song.id,
    quality: 'lossless',
    source: song.source,
    name: song.name,
    artist: song.artists,
    album: song.album,
    writeMetadata: 'true'
  });
  window.location.href = `/download?${params}`;
}

// 批量下载 + SSE 进度
async function batchDownload(items, name) {
  // 1. 启动任务
  const start = await (await fetch('/download/batch/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, name })
  })).json();

  const taskId = start.data.task_id;

  // 2. 订阅 SSE 进度
  const es = new EventSource(`/download/batch/progress/${taskId}`);
  es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    console.log(`${data.completed}/${data.total}`, data.current);
    if (data.status === 'done') {
      // 3. 下载文件
      window.location.href = `/download/batch/file/${taskId}`;
      es.close();
    }
  };
}
```

### cURL

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

# 解析 URL
curl -X POST http://localhost:5002/parse/url \
  -d "url=https://music.163.com/playlist?id=7583298906"

# 单曲下载
curl -o song.flac "http://localhost:5002/download?id=123456&quality=lossless&name=test&artist=test"
```

---

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
# 1. 直接用环境变量
PORT=5005 python3 main.py

# 2. 用 .env 文件（可选）
WAN_MUSIC_ENV_FILE=.env python3 main.py
```
