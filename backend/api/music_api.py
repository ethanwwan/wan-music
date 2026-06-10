"""音乐API总控模块

作为多平台音乐API的总控中心，支持：
- 网易云音乐（netease_api）
- 未来可扩展支持QQ音乐、酷狗音乐等

提供统一的API接口，前端可指定数据源和平台。
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

# 配置日志
logger = logging.getLogger(__name__)

# 导入平台特定的API模块
try:
    from .netease_api import NeteaseAPIClient, netease_client, QualityLevel
except ImportError as e:
    logger.error(f"导入网易云API模块失败: {e}")
    raise


class PlatformType(Enum):
    """音乐平台枚举"""
    NETEASE = "netease"        # 网易云音乐
    QQ = "qq"                  # QQ音乐（预留）
    KUGOU = "kugou"            # 酷狗音乐（预留）
    KUWO = "kuwo"              # 酷我音乐（预留）
    MIGU = "migu"              # 咪咕音乐（预留）


class MusicAPI:
    """统一的音乐API总控类"""
    
    def __init__(self):
        """初始化API总控"""
        self.platform_clients = {
            'netease': netease_client
        }
        self.default_platform = 'netease'
    
    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表"""
        return [
            {'value': 'netease', 'label': '网易云音乐', 'description': '网易云音乐平台'}
            # 未来可扩展其他平台
        ]
    
    def get_data_sources(self, platform: str = 'netease') -> List[Dict[str, str]]:
        """获取指定平台的可用数据源列表"""
        client = self.platform_clients.get(platform)
        if client and hasattr(client, 'get_available_sources'):
            return client.get_available_sources()
        return []
    
    def search(self, keyword: str, platform: str = None, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        
        return client.search(keyword, limit, offset)
    
    def get_song_url(self, song_id: int, quality: str = 'lossless', 
                      platform: str = None, data_source: str = 'official') -> Dict[str, Any]:
        """获取歌曲下载链接"""
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        
        if not hasattr(client, 'get_song_url'):
            raise ValueError(f"平台 {platform} 不支持获取歌曲URL")
        
        return client.get_song_url(song_id, quality, data_source)
    
    def get_song_detail(self, song_id: int, platform: str = None) -> Dict[str, Any]:
        """获取歌曲详情"""
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        
        return client.get_song_detail(song_id)
    
    def get_lyric(self, song_id: int, platform: str = None) -> Dict[str, Any]:
        """获取歌词"""
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        
        return client.get_lyric(song_id)
    
    def get_playlist_detail(self, playlist_id: int, platform: str = None) -> Dict[str, Any]:
        """获取歌单详情"""
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        
        return client.get_playlist_detail(playlist_id)
    
    def get_album_detail(self, album_id: int, platform: str = None) -> Dict[str, Any]:
        """获取专辑详情"""
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        
        return client.get_album_detail(album_id)


# 创建全局API实例
music_api = MusicAPI()


# ==================== 向后兼容的函数接口 ====================

def search_music(keywords: str, cookies: Dict[str, str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """搜索音乐（向后兼容）"""
    return music_api.search(keywords, limit=limit)


def url_v1(song_id: int, level: str, cookies: Dict[str, str], data_source: str = 'official') -> Dict[str, Any]:
    """获取歌曲URL（向后兼容，支持指定数据源）"""
    try:
        result = music_api.get_song_url(song_id, level, data_source=data_source)
        return {
            'data': [{
                'id': song_id,
                'url': result.get('url', ''),
                'level': level,
                'type': 'flac' if level in ['lossless', 'hires', 'jymaster'] else 'mp3',
                'size': 0,
                'br': 0,
                'source': result.get('source', data_source)
            }]
        }
    except Exception as e:
        logger.error(f"获取歌曲URL失败: {e}")
        raise


def name_v1(song_id: int) -> Dict[str, Any]:
    """获取歌曲详情（向后兼容）"""
    return music_api.get_song_detail(song_id)


def lyric_v1(song_id: int, cookies: Dict[str, str] = None) -> Dict[str, Any]:
    """获取歌词（向后兼容）"""
    return music_api.get_lyric(song_id)


def playlist_detail_v1(playlist_id: int) -> Dict[str, Any]:
    """获取歌单详情（向后兼容）"""
    return music_api.get_playlist_detail(playlist_id)


def album_detail_v1(album_id: int) -> Dict[str, Any]:
    """获取专辑详情（向后兼容）"""
    return music_api.get_album_detail(album_id)


def get_platforms() -> List[Dict[str, str]]:
    """获取可用平台列表"""
    return music_api.get_platforms()


def get_data_sources(platform: str = 'netease') -> List[Dict[str, str]]:
    """获取指定平台的可用数据源列表"""
    return music_api.get_data_sources(platform)


# 导入其他必要的函数（保持向后兼容）
try:
    from .netease_api import search_music as netease_search, url_v1 as netease_url_v1
except ImportError:
    pass