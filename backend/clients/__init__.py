"""API模块包初始化文件

导出音乐客户端相关模块和类。
"""

from .base_client import BaseMusicClient
from .netease_client import NeteaseClient, netease_client
from .qq_client import QQClient, qq_client
from .bodian_client import BodianClient, bodian_client
from .kugou_client import KugouClient, kugou_client
from .kuwo_client import KuwoClient, kuwo_client
from .music_client import MusicClient, music_client

__all__ = [
    'BaseMusicClient',
    'NeteaseClient', 'netease_client',
    'QQClient', 'qq_client',
    'BodianClient', 'bodian_client',
    'KugouClient', 'kugou_client',
    'KuwoClient', 'kuwo_client',
    'MusicClient', 'music_client'
]
