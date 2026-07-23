"""API模块包初始化文件

导出音乐客户端相关模块和类。

注意：clients.sources.* 各模块顶层 import 大量 ApiSource 列表，需要
先 import fallback.extractors 再 import sources.*。而 *_client 加载
时 from .sources.* import 常量又会触发 sources.* 加载，形成循环。
解决方法：先把 fallback.extractors 完整加载，再 sources.*，最后 client。
歌单提取器（5 个）已经迁移到 sources/_playlist_extractors.py，那里
只 import fallback.extractors 的 normalize_*_song，不会反向依赖。
"""

# 1. 先 import base（无依赖）
from .base_client import BaseMusicClient

# 2. 直接 import extractors（确保所有 normalize_*_song 已定义）
from . import fallback  # noqa: F401

# 3. 再 import sources 各模块（会触发 _playlist_extractors 加载，
#    进而使用 fallback.extractors 的 normalize 函数）
from . import sources  # noqa: F401

# 4. 最后 import 各 client
from .netease_client import NeteaseClient, netease_client
from .qq_client import QQClient, qq_client
from .kugou_client import KugouClient, kugou_client
from .kuwo_client import KuwoClient, kuwo_client
from .music_client import MusicClient, music_client

__all__ = [
    'BaseMusicClient',
    'NeteaseClient', 'netease_client',
    'QQClient', 'qq_client',
    'KugouClient', 'kugou_client',
    'KuwoClient', 'kuwo_client',
    'MusicClient', 'music_client'
]
