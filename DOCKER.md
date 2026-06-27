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
docker run -d \
  --name wan-music \
  -p 6005:6005 \
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
    restart: unless-stopped
```

```bash
docker compose up -d
```

## 🔗 链接

- GitHub: <https://github.com/ethanwwan/wan-music>
- 完整文档: <https://github.com/ethanwwan/wan-music/blob/main/README.md>
