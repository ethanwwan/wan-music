# Backend

> Flask 后端服务

详细文档见根目录 [README.md](../README.md)。

## 启动

```bash
pip install -r requirements.txt
python3 main.py
```

## API 文档

[API_DOC.md](file:///Users/Awan/Public/Repository/wan-music/backend/API_DOC.md)

## 目录

- `clients/` - 音乐平台客户端
- `routes/` - Flask 路由
- `services/` - 业务服务
- `utils/` - 工具函数
- `scripts/` - 维护脚本

## 维护脚本

```bash
# 元数据检查
python3 scripts/check_metadata.py

# 歌单同步
python3 scripts/sync_artist_to_playlist.py
```

## 许可证

MIT
