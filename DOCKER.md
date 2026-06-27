# Wan Music

多平台音乐搜索、解析、下载工具。支持网易云、QQ音乐、波点音乐、酷狗音乐。

## ✨ 功能

- 🔍 跨平台统一搜索（歌曲 / 歌单）
- 📋 歌单解析与批量下载
- 🏷️ 自动写入 ID3 标签（标题、歌手、专辑、歌词、封面）
- 🎨 Vue 3 Web 界面

## 🚀 快速部署

### 方式一：docker run

```bash
# 1. 创建 cookie 目录（用于挂载，持久化登录状态）
mkdir -p ./wan-music/cookie

# 2. 启动容器
docker run -d \
  --name wan-music \
  -p 6005:6005 \
  -v $(pwd)/wan-music/cookie:/app/clients/cookie \
  --restart unless-stopped \
  ethanwwan/wan-music:latest
```

访问 <http://localhost:6005>

### 方式二：docker compose

```yaml
services:
  wan-music:
    image: ethanwwan/wan-music:latest
    container_name: wan-music
    ports:
      - "6005:6005"
    volumes:
      - ./cookie:/app/clients/cookie
    restart: unless-stopped
```

```bash
docker compose up -d
```

> 💡 **为什么要挂载 cookie 目录？**  
> 容器重建时会丢失所有数据，挂载后 `netease_cookie.txt` 持久化在宿主机，VIP 登录状态不会丢失。  
> 文件位置：`./wan-music/cookie/netease_cookie.txt`（每行一个 `key=value` 格式，如 `MUSIC_U=xxx`）

## 🔗 链接

- GitHub: <https://github.com/ethanwwan/wan-music>
- 完整文档: <https://github.com/ethanwwan/wan-music/blob/main/README.md>
