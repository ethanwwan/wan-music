# 网易云音乐 API 后端服务（Python版）

## 📁 目录结构

```
backend/
├── clients/          # 音乐平台客户端
│   ├── base_client.py      # 抽象基类
│   ├── netease_client.py   # 网易云音乐
│   ├── qq_client.py        # QQ音乐
│   ├── bodian_client.py    # 波点音乐
│   └── kugou_client.py     # 酷狗音乐
├── routes/           # Flask 路由
│   ├── search_routes.py    # 搜索路由
│   └── music_routes.py     # 音乐路由
├── services/         # 业务服务层
│   └── music_service.py    # 音乐业务服务
├── utils/            # 工具函数
│   └── api_response.py     # 统一响应工具
├── logs/             # 日志目录
├── tests/            # 测试目录
├── main.py           # Flask API服务器主文件
├── LICENSE           # 许可证
├── .gitignore        # Git忽略配置
└── README.md         # 本文件
```

## 🔧 技术栈

- **Flask** - Web框架
- **Flask-CORS** - CORS跨域支持
- **Requests** - HTTP客户端
- **Python 3.8+** - 运行环境

## 🎯 核心功能

### 1. 多平台音乐API
支持网易云、QQ、波点、酷狗音乐平台的音乐搜索和播放。

### 2. 统一接口规范
通过 `BaseMusicClient` 抽象基类定义统一的接口规范。

### 3. 自动线路切换
网易云音乐API支持自动切换线路（官方API优先）。

## 📡 API端点

### 健康检查
```bash
GET /health
```

### 搜索歌曲
```bash
POST /search
Content-Type: application/json

{"keyword": "陈楚生", "source": "netease", "limit": 10}
```

### 搜索歌单
```bash
POST /search/playlist
Content-Type: application/json

{"keyword": "华语", "source": "netease", "limit": 20}
```

### 获取歌曲信息
```bash
POST /song
Content-Type: application/x-www-form-urlencoded

ids=25706282&level=lossless&type=json
```

### 获取歌单详情
```bash
POST /playlist
Content-Type: application/x-www-form-urlencoded

id=7583298906
```

### 获取数据源列表
```bash
GET /api/data-sources
```

## 🚀 启动方式

### 前置要求
```bash
pip install flask flask-cors requests
```

### 启动服务
```bash
cd backend
python3 main.py
```

服务会在 `http://localhost:5002` 启动。

## 🧪 测试

```bash
# 健康检查
curl http://localhost:5002/health

# 测试搜索
curl -X POST http://localhost:5002/search \
  -H "Content-Type: application/json" \
  -d '{"keyword": "陈楚生", "limit": 5}'
```

## 📄 许可证

MIT License