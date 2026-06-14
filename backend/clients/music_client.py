"""音乐客户端总控模块

作为多平台音乐客户端的总控中心，支持：
- 网易云音乐（netease_client）
- QQ音乐（qq_client）
- 波点音乐（bodian_client）
- 酷狗音乐（kugou_client）

提供统一的API接口，前端可指定数据源和平台。

参考 musicdl 的 MusicClient 设计模式：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/musicdl.py
"""

import logging
from typing import Dict, List, Optional, Any, Type

from .base_client import BaseMusicClient
from .netease_client import NeteaseClient, netease_client
from .qq_client import QQClient, qq_client
from .bodian_client import BodianClient, bodian_client
from .kugou_client import KugouClient, kugou_client

logger = logging.getLogger(__name__)


class MusicClient:
    """统一的音乐客户端总控类
    
    支持多种初始化方式：
    1. 默认方式 - 使用全局单例客户端
    2. 自定义方式 - 传入具体的客户端实例
    """
    
    def __init__(
        self,
        netease_client: Optional[NeteaseClient] = None,
        qq_client: Optional[QQClient] = None,
        bodian_client: Optional[BodianClient] = None,
        kugou_client: Optional[KugouClient] = None
    ):
        """初始化客户端总控
        
        Args:
            netease_client: 自定义网易云客户端实例，默认为全局单例
            qq_client: 自定义QQ音乐客户端实例，默认为全局单例
            bodian_client: 自定义波点音乐客户端实例，默认为全局单例
            kugou_client: 自定义酷狗音乐客户端实例，默认为全局单例
        """
        self.platform_clients: Dict[str, BaseMusicClient] = {}
        
        if netease_client:
            self.register_client('netease', netease_client)
        else:
            self.register_client('netease', globals()['netease_client'])
        
        if qq_client:
            self.register_client('qq', qq_client)
        else:
            self.register_client('qq', globals()['qq_client'])
        
        if bodian_client:
            self.register_client('bodian', bodian_client)
        else:
            self.register_client('bodian', globals()['bodian_client'])
        
        if kugou_client:
            self.register_client('kugou', kugou_client)
        else:
            self.register_client('kugou', globals()['kugou_client'])
        
        self.default_platform = 'netease'
    
    def register_client(self, platform: str, client: BaseMusicClient) -> None:
        """注册平台客户端
        
        Args:
            platform: 平台标识（netease/qq/bodian/kugou）
            client: 客户端实例，需继承自BaseMusicClient
        """
        if not isinstance(client, BaseMusicClient):
            raise ValueError(f"客户端必须继承自 BaseMusicClient")
        self.platform_clients[platform] = client
        logger.info(f"已注册平台: {platform}")
    
    def unregister_client(self, platform: str) -> None:
        """取消注册平台"""
        if platform in self.platform_clients:
            del self.platform_clients[platform]
            logger.info(f"已取消注册平台: {platform}")
    
    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表"""
        return [
            {'value': 'netease', 'label': '网易云音乐', 'description': '网易云音乐平台'},
            {'value': 'qq', 'label': 'QQ音乐', 'description': 'QQ音乐平台'},
            {'value': 'bodian', 'label': '波点音乐', 'description': '波点音乐平台'},
            {'value': 'kugou', 'label': '酷狗音乐', 'description': '酷狗音乐平台'}
        ]
    
    def _get_client(self, platform: str) -> BaseMusicClient:
        """获取指定平台的客户端（内部方法）"""
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        
        return client
    
    def search(self, keyword: str, platform: str = None, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        client = self._get_client(platform)
        return client.search(keyword, limit, offset)
    
    def search_playlist(self, keyword: str, platform: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        client = self._get_client(platform)
        return client.search_playlist(keyword, limit)
    
    def get_song_url(self, song_id: Any, quality: str = 'high', platform: str = None) -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        client = self._get_client(platform)
        return client.get_song_url(song_id, quality)
    
    def get_song_info(self, song_id: Any, platform: str = None) -> Dict[str, Any]:
        """获取歌曲信息"""
        client = self._get_client(platform)
        return client.get_song_info(song_id)
    
    def get_lyric(self, song_id: Any, platform: str = None) -> str:
        """获取歌词"""
        client = self._get_client(platform)
        return client.get_lyric(song_id)
    
    def get_playlist(self, playlist_id: Any, platform: str = None) -> Dict[str, Any]:
        """获取歌单"""
        client = self._get_client(platform)
        return client.get_playlist(playlist_id)


# 创建全局客户端实例（使用默认全局客户端）
music_client = MusicClient()


# ==================== 向后兼容的函数接口 ====================

def search_music(keywords: str, platform: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """搜索音乐（向后兼容）"""
    return music_client.search(keywords, platform, limit=limit)


def get_song_url(song_id: int, quality: str, platform: str = None) -> Dict[str, Any]:
    """获取歌曲URL（向后兼容）"""
    try:
        result = music_client.get_song_url(song_id, quality, platform)
        return {
            'data': [{
                'id': song_id,
                'url': result.get('url', ''),
                'level': quality,
                'type': 'flac' if quality in ['lossless', 'hires', 'jymaster'] else 'mp3',
                'size': 0,
                'br': 0,
                'source': result.get('source', platform or 'netease')
            }]
        }
    except Exception as e:
        logger.error(f"获取歌曲URL失败: {e}")
        raise


def get_song_detail(song_id: int, platform: str = None) -> Dict[str, Any]:
    """获取歌曲详情（向后兼容）"""
    return music_client.get_song_info(song_id, platform)


def get_lyric(song_id: int, platform: str = None) -> Dict[str, Any]:
    """获取歌词（向后兼容）"""
    lyric = music_client.get_lyric(song_id, platform)
    return {'lyric': lyric}


def get_playlist_detail(playlist_id: int, platform: str = None) -> Dict[str, Any]:
    """获取歌单详情"""
    return music_client.get_playlist(playlist_id, platform)


def get_platforms() -> List[Dict[str, str]]:
    """获取可用平台列表"""
    return music_client.get_platforms()