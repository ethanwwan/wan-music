# 音乐服务 API 文档

## 基础信息

- **服务地址**: `http://localhost:5002`
- **前端开发代理**: `/api/*`, `/search/*`, `/song/*`, `/playlist/*`, `/health/*` 均代理到后端
- **数据格式**: JSON

---

## 通用响应格式

### 成功响应
```json
{
    "code": 200,
    "message": "success",
    "data": { /* 响应数据 */ }
}
```

### 失败响应
```json
{
    "code": 400,
    "message": "错误信息",
    "data": null
}
```

---

## 接口列表

### 1. 搜索歌曲

**路径**: `POST /search`

**功能**: 根据关键词搜索歌曲

**请求参数**:
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| keyword | string | 是 | - | 搜索关键词 |
| source | string | 否 | null | 平台来源（netease/qq/kugou/bodian），null表示全部平台 |
| limit | int | 否 | 10 | 返回数量 |

**请求示例**:
```json
{
    "keyword": "陈楚生",
    "source": "netease",
    "limit": 10
}
```

**响应示例**:
```json
{
    "code": 200,
    "message": "搜索成功",
    "data": [
        {
            "id": "123456",
            "name": "有没有人告诉你",
            "artists": "陈楚生",
            "album": "快乐男声",
            "picUrl": "https://example.com/cover.jpg",
            "duration": 245000,
            "source": "netease"
        }
    ]
}
```

---

### 2. 搜索歌单

**路径**: `POST /search/playlist`

**功能**: 根据关键词搜索歌单

**请求参数**:
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| keyword | string | 是 | - | 搜索关键词 |
| source | string | 否 | null | 平台来源 |
| limit | int | 否 | 20 | 返回数量 |

**请求示例**:
```json
{
    "keyword": "华语流行",
    "limit": 10
}
```

**响应示例**:
```json
{
    "code": 200,
    "message": "搜索成功",
    "data": [
        {
            "id": "123456",
            "name": "华语流行金曲",
            "cover": "https://example.com/cover.jpg",
            "description": "精选华语流行歌曲",
            "play_count": 1234567,
            "source": "netease"
        }
    ]
}
```

---

### 3. 获取歌曲信息

**路径**: `POST /song`

**功能**: 获取歌曲的详细信息，支持多种类型

**请求参数**（form-urlencoded）:
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| ids / id | string | 是 | - | 歌曲ID（优先取ids，逗号分隔，取第一个） |
| type | string | 否 | json | 返回类型：`url`/`name`/`lyric`/`json` |
| level | string | 否 | lossless | 音质等级 |

**音质等级说明**:
| 值 | 说明 |
|----|------|
| standard | 标准音质 (128kbps) |
| exhigh | 极高音质 (320kbps) |
| lossless | 无损音质 (FLAC) |
| hires | Hi-Res音质 (FLAC 24bit) |
| sky | 沉浸环绕声 |
| jyeffect | 高清臻音 |
| jymaster | 超清母带 |
| dolby | 杜比全景声 |

**请求示例**:
```bash
POST /song
Content-Type: application/x-www-form-urlencoded

ids=123456&type=json&level=lossless
```

**响应示例**（type=json）:
```json
{
    "code": 200,
    "message": "获取歌曲信息成功",
    "data": {
        "id": "123456",
        "name": "有没有人告诉你",
        "ar_name": "陈楚生",
        "al_name": "快乐男声",
        "pic": "https://example.com/cover.jpg",
        "level": "lossless",
        "source": "netease",
        "lyric": "[00:00.00]有没有人告诉你...",
        "tlyric": "",
        "url": "https://example.com/song.mp3"
    }
}
```

**响应示例**（type=url）:
```json
{
    "code": 200,
    "message": "获取歌曲URL成功",
    "data": {
        "id": "123456",
        "url": "https://example.com/song.mp3",
        "level": "lossless",
        "type": "mp3",
        "source": "netease"
    }
}
```

**响应示例**（type=lyric）:
```json
{
    "code": 200,
    "message": "获取歌词成功",
    "data": {
        "lyric": "[00:00.00]有没有人告诉你..."
    }
}
```

---

### 4. 获取歌单详情

**路径**: `POST /playlist`

**功能**: 获取歌单详情及歌曲列表

**请求参数**（form-urlencoded）:
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| id | string | 是 | - | 歌单ID |

**请求示例**:
```bash
POST /playlist
Content-Type: application/x-www-form-urlencoded

id=123456
```

**响应示例**:
```json
{
    "code": 200,
    "message": "获取歌单成功",
    "data": {
        "playlist": {
            "id": "123456",
            "name": "华语流行金曲",
            "cover": "https://example.com/cover.jpg",
            "description": "精选华语流行歌曲",
            "play_count": 1234567,
            "source": "netease",
            "tracks": [
                {
                    "id": "1",
                    "name": "歌曲1",
                    "artists": "歌手1",
                    "album": "专辑1"
                }
            ]
        }
    }
}
```

---

### 5. 获取数据源列表

**路径**: `GET /api/data-sources`

**功能**: 获取可用的音乐平台数据源列表

**请求参数**: 无

**响应示例**:
```json
{
    "code": 200,
    "message": "获取数据源列表成功",
    "data": [
        {
            "id": "netease",
            "name": "网易云音乐"
        },
        {
            "id": "qq",
            "name": "QQ音乐"
        },
        {
            "id": "kugou",
            "name": "酷狗音乐"
        },
        {
            "id": "bodian",
            "name": "波点音乐"
        }
    ]
}
```

---

### 6. 健康检查

**路径**: `GET /health`

**功能**: 检查服务健康状态

**请求参数**: 无

**响应示例**:
```json
{
    "code": 200,
    "message": "OK",
    "data": null
}
```

---

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 403 | 版权限制，无法获取播放链接 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

---

## 使用示例（JavaScript）

```javascript
// 搜索歌曲
async function searchSongs(keyword, source = null) {
    const response = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword, source, limit: 10 })
    });
    return await response.json();
}

// 获取歌曲信息
async function getSongInfo(songId, type = 'json', level = 'lossless') {
    const formData = new URLSearchParams();
    formData.append('ids', songId);
    formData.append('type', type);
    formData.append('level', level);
    
    const response = await fetch('/song', {
        method: 'POST',
        body: formData
    });
    return await response.json();
}

// 获取歌单详情
async function getPlaylist(playlistId) {
    const formData = new URLSearchParams();
    formData.append('id', playlistId);
    
    const response = await fetch('/playlist', {
        method: 'POST',
        body: formData
    });
    return await response.json();
}
```