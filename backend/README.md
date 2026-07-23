# Backend API

> Wan Music 后端 API 参考手册

项目总览见根目录 [README.md](../README.md)。本文档只列出**前端实际使用**的接口。

## 端口

| 环境 | 端口 | 配置 |
|------|------|------|
| dev（Flask dev server） | 5005 | `config.json: backend.devBackendPort` |
| prod（Docker / gunicorn） | 6005 | Dockerfile `gunicorn -b` 硬编码 |

---

## API 文档

> 本文档只列出**前端实际使用**的接口。删除/调整前请确认前端调用。

### 基础信息

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
| `kuwo` | 酷我（支持搜索歌曲、下载） |

### 音质等级

| 值 | 说明 |
|----|------|
| `standard` | 标准 (128kbps) |
| `exhigh` | 极高音质 (320kbps) |
| `lossless` | 无损 (FLAC) |
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
curl http://localhost:5005/health
# {"status": "healthy"}
```

### 2. 获取平台列表

**`GET /platforms`**

返回后端支持的音乐平台元数据（id / name / color / description），前端从该接口读取并动态渲染下拉选项，避免硬编码平台列表。

```bash
curl http://localhost:5005/platforms
```

```json
{
  "success": true,
  "data": [
    {"id": "netease", "name": "网易云音乐",   "color": "#e72d2c", "description": "网易云音乐平台"},
    {"id": "qq",      "name": "QQ音乐",  "color": "#31c27c", "description": "QQ音乐平台"},
    {"id": "kugou",   "name": "酷狗音乐", "color": "#2a8eff", "description": "酷狗音乐平台"},
    {"id": "kuwo",    "name": "酷我音乐", "color": "#ff6600", "description": "酷我音乐平台"}
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

#### 4.1 完整响应字段

实际后端返回的字段比上面的简版示例更多，常见字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` / `name` / `artists` / `album` / `picUrl` / `duration` | 基础 | 来自 search 阶段（歌名/歌手/专辑/封面/时长，ms） |
| `url` | string | 可下载的音频 URL |
| `level` | string | **实际**拿到的音质（可能与请求音质不同） |
| `level_name` / `level_format` | string | 音质的展示名和格式描述（前端展示用） |
| `requested_quality` | string | 仅当降级/升级时存在，等于用户请求的音质 |
| `level_fallback` | bool | 仅当降级时为 true（实际音质 < 请求音质） |
| `level_upgrade` | bool | 仅当升级时为 true（实际音质 > 请求音质） |
| `lyric` | string | LRC 歌词 |
| `qualityMap` | object | **精简版**音质映射（见下） |
| `api_source` | object | 各字段来自哪个数据源 `{url, info, lyric}`（调试用） |
| `mismatch_warning` | string | 仅当 lyric 与 audio 版本不一致时存在（见下） |

#### 4.2 qualityMap 精简格式

后端**不再**传完整 qualityMap（hires/lossless/exhigh/standard 全部音质 + size）。
只传 `requested`（用户请求的音质）和 `actual`（实际拿到的音质）两项：

```json
{
  "qualityMap": {
    "requested": {
      "quality": "hires",
      "size": 90000000,
      "br": 9000
    },
    "actual": {
      "quality": "lossless",
      "size": 30000000,
      "br": 1411
    }
  }
}
```

- `requested.quality` 等于请求参数里的 `level`
- `actual.quality` 等于响应里的 `level`（降级/升级时不同）
- `size` 单位字节，`br` 单位 kbps
- 前端展示 "用户选了 hires，实际给了 lossless" 时直接对比这两个字段

#### 4.3 url/lyric 同源策略

为避免"音频来自 A 源、歌词来自 B 源"导致的**版本错配**（Live vs Studio 混搭），/song 接口采用**同源优先**策略：

1. **先抢答 url**：并行/串行调用 url 链，拿到第一个返回有效 URL 的源（如 `haitanw_url`）
2. **lyric 复用 url 选中的源**：lyric 链拿到 `url_src = haitanw_url` 后，**强制优先**从 haitanw 拉歌词
3. **降级到下一个能提供 lyric 的源**：如果 haitanw 不提供 lyric（如直传模式 ccwu），
   降级到下一个能 provide `lyric` 能力的源

实现细节见 [chain.py:329-374](file:///Users/Awan/Public/Repository/wan-music/backend/clients/fallback/chain.py#L329-L374) 的 `same_source` 机制。
每个 ApiSource 通过 `provides` 字段（自动从 `can_*` 字段推导）声明自己提供哪些能力。

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
curl -N http://localhost:5005/download/batch/progress/<task_id>
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


---

## 许可证

MIT
