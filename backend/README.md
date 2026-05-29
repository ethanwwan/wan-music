# 网易云音乐 API 后端服务

## 📁 目录结构

```
backend/
├── server.js        # Express API服务器主文件
├── server-crypto.js # EAPI加密工具（MD5 + AES-CBC）
├── server-cookie.js # Cookie管理模块
├── cookie.txt       # 网易云音乐认证Cookie
└── README.md        # 本文件
```

## 🔧 技术栈

- **Express** - Web框架
- **Axios** - HTTP客户端
- **Node.js Crypto** - 加密工具（MD5、AES-CBC）
- **CORS** - 跨域资源共享

## 🎯 核心功能

### 1. API代理服务
将前端请求代理到网易云音乐API，解决CORS跨域问题。

### 2. EAPI加密
网易云音乐使用EAPI协议进行加密通信：
- **MD5签名** - 生成请求摘要
- **AES-CBC加密** - 加密请求参数

### 3. Cookie认证
管理网易云音乐Cookie，支持：
- 自动读取cookie.txt
- Cookie有效性验证
- 关键Cookie检查（MUSIC_U、NMTID、__csrf）

## 📡 API端点

### 健康检查
```bash
GET /health
```
返回服务状态和Cookie信息。

### 歌曲解析
```bash
POST /api/song
Content-Type: application/json

{
  "id": 33894312
}
```

### 歌曲URL
```bash
POST /api/song/url
Content-Type: application/json

{
  "ids": [33894312],
  "level": "lossless"
}
```

### 歌词获取
```bash
POST /api/lyric
Content-Type: application/json

{
  "id": 33894312
}
```

### 搜索音乐
```bash
POST /api/search
Content-Type: application/json

{
  "keyword": "周杰伦",
  "limit": 10
}
```

### 歌单详情
```bash
POST /api/playlist
Content-Type: application/json

{
  "id": 225001
}
```

### 专辑详情
```bash
POST /api/album
Content-Type: application/json

{
  "id": 14808721
}
```

### 通用代理
```bash
POST /eapi/*   # EAPI加密请求
POST /api/*    # 普通API请求
```

## 🚀 启动方式

### 方式1：使用npm脚本（推荐）
```bash
# 启动API服务器（端口3000）
npm run dev:api

# 或同时启动API和前端
npm run dev
```

### 方式2：直接运行
```bash
node backend/server.js
```

### 方式3：Docker部署
```bash
docker build -t wan-music-backend .
docker run -p 3000:3000 -v $(pwd)/backend/cookie.txt:/app/cookie.txt wan-music-backend
```

## 📝 Cookie配置

### Cookie文件格式
```
cookie.txt
```
包含网易云音乐的完整Cookie，通常为 `key=value; key=value` 格式。

### 重要Cookie字段
| Cookie名称 | 说明 | 必需 |
|-----------|------|------|
| MUSIC_U | 用户认证令牌 | ✅ |
| NMTID | 设备标识 | ✅ |
| __csrf | CSRF令牌 | ✅ |
| _ntes_nnid | 网易ID | ❌ |
| _ntes_nuid | 网易UID | ❌ |

### 获取Cookie
1. 使用Python后端的二维码登录
2. 或从浏览器开发者工具复制
3. 保存到 `cookie.txt` 文件

### 更新Cookie
```javascript
// 使用CookieManager
import cookieManager from './server-cookie.js'

// 更新Cookie文件
cookieManager.writeCookieFile('新的cookie字符串')

// 重新读取
cookieManager.readCookieFile()
```

## 🔐 安全说明

### Cookie安全
- ✅ Cookie文件已添加到 `.gitignore`
- ✅ 不要将Cookie提交到版本控制
- ✅ 定期更新Cookie

### API安全
- ✅ 使用EAPI加密协议
- ✅ 所有请求需要Cookie认证
- ⚠️ 生产环境建议添加API Key或IP白名单

## 🔧 配置

### 环境变量
```bash
# 后端端口（默认3000）
PORT=3000

# 网易云API地址（可选）
NETEASE_API_BASE_URL=https://interface3.music.163.com
```

### Vite代理配置
在 `vite.config.js` 中配置：
```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:3000',
      changeOrigin: true
    },
    '/eapi': {
      target: 'http://localhost:3000',
      changeOrigin: true
    },
    '/weapi': {
      target: 'http://localhost:3000',
      changeOrigin: true
    }
  }
}
```

## 📊 日志输出

服务器启动时会输出：
```
📋 Cookie管理器初始化...
✅ 成功读取Cookie，共 21 个字段
✅ Cookie验证通过
🎵 网易云音乐API服务已启动
📡 服务地址: http://localhost:3000
```

请求时会输出：
```
📡 EAPI请求（带Cookie）: /eapi/song/enhance/player/url/v1
📡 API请求（带Cookie）: /api/v3/song/detail
```

## 🧪 测试

### 测试脚本
```bash
# 完整API测试（带Cookie）
node test/test-complete-with-cookie.mjs

# EAPI加密测试
node test/test-eapi.mjs

# 基础API测试
node test/test-api.mjs

# UI交互测试
node test/test-ui-interaction.mjs
```

### Playwright测试
```bash
npm run test:ui
```

## 🐛 故障排查

### Cookie无效
```
⚠️ Cookie无效或缺失，可能无法获取VIP歌曲
```
**解决**：更新 `cookie.txt` 文件

### EAPI加密失败
```
❌ API请求失败
```
**解决**：
1. 检查Cookie是否有效
2. 确认网易云API地址可访问
3. 查看服务器日志

### 端口占用
```
Error: listen EADDRINUSE :::3000
```
**解决**：
```bash
# 查找占用端口的进程
lsof -i :3000

# 杀死进程
kill -9 <PID>
```

## 📚 相关文档

- [Python vs Node.js对比报告](../COMPARISON_REPORT.md)
- [项目README](../README.md)
- [测试目录说明](../test/README.md)
- [网易云音乐API文档](https://github.com/Binaryify/NeteaseCloudMusicApi)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License
