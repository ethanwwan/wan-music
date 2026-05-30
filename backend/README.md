# 网易云音乐 API 后端服务（Python版）

## 📁 目录结构

```
backend/
├── main.py        # Flask API服务器主文件
├── cookie.txt     # 网易云音乐认证Cookie
└── README.md      # 本文件
```

## 🔧 技术栈

- **Flask** - Web框架
- **Requests** - HTTP客户端
- **Cryptography** - 加密工具（MD5、AES-ECB）
- **Python 3** - 运行环境

## 🎯 核心功能

### 1. API代理服务
将前端请求代理到网易云音乐API，解决CORS跨域问题。

### 2. EAPI加密
网易云音乐使用EAPI协议进行加密通信：
- **MD5签名** - 生成请求摘要
- **AES-ECB加密** - 加密请求参数（PKCS7 padding）

### 3. Cookie认证
管理网易云音乐Cookie，支持Cookie认证获取VIP歌曲。

## 📡 API端点

### 健康检查
```bash
GET /health
```
返回服务状态。

### 歌曲解析（核心接口）
```bash
POST /Song_V1
Content-Type: application/x-www-form-urlencoded

ids=25706282&level=standard&type=json
```

参数说明：
- `ids` - 歌曲ID
- `level` - 音质（standard/exhigh/lossless/hires/sky）
- `type` - 返回格式（json/text/down）

## 🚀 启动方式

### 前置要求
```bash
pip install flask requests cryptography
```

### 启动服务
```bash
cd backend
python3 main.py
```

服务会在 `http://localhost:5002` 启动（5000和5001端口可能被占用）。

## 📝 Cookie配置

### Cookie文件格式
```
cookie.txt
```
包含网易云音乐的完整Cookie，通常为 `key=value; key=value` 格式。

### 获取Cookie
1. 登录 https://music.163.com
2. 打开开发者工具（F12）
3. 复制Cookie并保存到 `cookie.txt`

### 重要Cookie字段
- MUSIC_U - 用户认证令牌
- NMTID - 设备标识

## 🔐 安全说明

- ✅ Cookie文件已添加到 `.gitignore`
- ✅ 不要将Cookie提交到版本控制
- ✅ 定期更新Cookie

## 🧪 测试

```bash
# 健康检查
curl http://localhost:5002/health

# 测试歌曲解析
curl "http://localhost:5002/Song_V1?ids=25706282&level=standard&type=json"
```

## 🐛 故障排查

### Cookie无效
无法获取VIP歌曲URL。
**解决**：更新 `cookie.txt` 文件

### 端口占用
```
Port 5000 is in use
```
**解决**：代码中已自动使用5002端口，如需更改可修改 `main.py` 最后一行的端口号。

## 📚 相关文档

- [项目README](../README.md)
- [网易云音乐API文档](https://github.com/Binaryify/NeteaseCloudMusicApi)

## 📄 许可证

MIT License
