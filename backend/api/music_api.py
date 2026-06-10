"""音乐API总控模块

作为多平台音乐API的总控中心，支持：
- 网易云音乐（netease_api）
- QQ音乐（qq_api）
- 波点音乐（bodian_api）

提供统一的API接口，前端可指定数据源和平台。

参考 musicdl 的多客户端方案，支持：
1. 默认使用预定义的全局客户端实例
2. 支持初始化时传入自定义客户端
3. 支持动态注册新平台

使用示例：
    # 使用默认配置
    api = MusicAPI()
    
    # 传入自定义客户端
    api = MusicAPI(
        netease_client=MyCustomNeteaseClient(),
        qq_client=MyCustomQQClient(),
        bodian_client=MyCustomBodianClient()
    )
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

# 配置日志
logger = logging.getLogger(__name__)

# 导入平台特定的API模块
try:
    from .netease_api import NeteaseAPIClient, netease_client
    from .qq_api import QQAPIClient, qq_client
    from .bodian_api import BodianAPIClient, bodian_client
except ImportError as e:
    logger.error(f"导入API模块失败: {e}")
    raise


class PlatformType(Enum):
    """音乐平台枚举"""
    NETEASE = "netease"        # 网易云音乐
    QQ = "qq"                  # QQ音乐
    BODIAN = "bodian"          # 波点音乐（已更正命名）
    KUGOU = "kugou"            # 酷狗音乐（预留）
    KUWO = "kuwo"              # 酷我音乐（预留）
    MIGU = "migu"              # 咪咕音乐（预留）


class MusicAPI:
    """统一的音乐API总控类
    
    支持多种初始化方式：
    1. 默认方式 - 使用全局单例客户端
    2. 自定义方式 - 传入具体的客户端实例
    """
    
    def __init__(
        self,
        netease_client: Optional[NeteaseAPIClient] = None,
        qq_client: Optional[QQAPIClient] = None,
        bodian_client: Optional[BodianAPIClient] = None
    ):
        """初始化API总控
        
        Args:
            netease_client: 自定义网易云客户端实例，默认为全局单例
            qq_client: 自定义QQ音乐客户端实例，默认为全局单例
            bodian_client: 自定义波点音乐客户端实例，默认为全局单例
        """
        self.platform_clients: Dict[str, Any] = {}
        
        # 注册平台客户端（优先使用传入的自定义客户端）
        if netease_client:
            self.register_platform('netease', netease_client)
        else:
            self.register_platform('netease', globals()['netease_client'])
        
        if qq_client:
            self.register_platform('qq', qq_client)
        else:
            self.register_platform('qq', globals()['qq_client'])
        
        if bodian_client:
            self.register_platform('bodian', bodian_client)
        else:
            self.register_platform('bodian', globals()['bodian_client'])
        
        self.default_platform = 'netease'
    
    def register_platform(self, platform: str, client: Any) -> None:
        """注册平台客户端
        
        Args:
            platform: 平台标识（netease/qq/bodian等）
            client: 客户端实例，需实现标准接口（search, get_song_url等）
        """
        if not hasattr(client, 'search'):
            raise ValueError(f"客户端必须实现 search 方法")
        self.platform_clients[platform] = client
        logger.info(f"已注册平台: {platform}")
    
    def unregister_platform(self, platform: str) -> None:
        """取消注册平台
        
        Args:
            platform: 平台标识
        """
        if platform in self.platform_clients:
            del self.platform_clients[platform]
            logger.info(f"已取消注册平台: {platform}")
    
    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表"""
        return [
            {'value': 'netease', 'label': '网易云音乐', 'description': '网易云音乐平台'},
            {'value': 'qq', 'label': 'QQ音乐', 'description': 'QQ音乐平台'},
            {'value': 'bodian', 'label': '波点音乐', 'description': '波点音乐平台'}
        ]
    
    def get_data_sources(self, platform: str = 'netease') -> List[Dict[str, str]]:
        """获取指定平台的可用数据源列表"""
        client = self.platform_clients.get(platform)
        if client and hasattr(client, 'get_available_sources'):
            return client.get_available_sources()
        return []
    
    def _get_client(self, platform: str) -> Any:
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
        
        if not hasattr(client, 'search_playlist'):
            raise ValueError(f"平台 {platform} 不支持搜索歌单")
        
        return client.search_playlist(keyword, limit)
    
    def search_album(self, keyword: str, platform: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索专辑"""
        client = self._get_client(platform)
        
        if not hasattr(client, 'search_album'):
            raise ValueError(f"平台 {platform} 不支持搜索专辑")
        
        return client.search_album(keyword, limit)
    
    def get_song_url(self, song_id: int, quality: str = 'lossless', 
                      platform: str = None, data_source: str = 'official') -> Dict[str, Any]:
        """获取歌曲下载链接"""
        client = self._get_client(platform)
        
        if not hasattr(client, 'get_song_url'):
            raise ValueError(f"平台 {platform} 不支持获取歌曲URL")
        
        return client.get_song_url(song_id, quality, data_source)
    
    def get_song_detail(self, song_id: int, platform: str = None) -> Dict[str, Any]:
        """获取歌曲详情"""
        client = self._get_client(platform)
        return client.get_song_detail(song_id)
    
    def get_lyric(self, song_id: int, platform: str = None) -> Dict[str, Any]:
        """获取歌词"""
        client = self._get_client(platform)
        return client.get_lyric(song_id)
    
    def get_playlist_detail(self, playlist_id: int, platform: str = None) -> Dict[str, Any]:
        """获取歌单详情"""
        client = self._get_client(platform)
        return client.get_playlist_detail(playlist_id)
    
    def get_album_detail(self, album_id: int, platform: str = None) -> Dict[str, Any]:
        """获取专辑详情"""
        client = self._get_client(platform)
        return client.get_album_detail(album_id)


# 创建全局API实例（使用默认全局客户端）
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