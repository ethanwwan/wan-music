"""音乐客户端总控模块

作为多平台音乐客户端的总控中心：
  - 网易云音乐（netease_client）
  - QQ音乐（qq_client）
  - 酷狗音乐（kugou_client）
  - 酷我音乐（kuwo_client）

提供统一的 API 接口（search / get_song），前端可指定数据源和平台。
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .base_client import BaseMusicClient
from .netease_client import NeteaseClient, netease_client
from .qq_client import QQClient, qq_client
from .kugou_client import KugouClient, kugou_client
from .kuwo_client import KuwoClient, kuwo_client

logger = logging.getLogger(__name__)


def _merge_song_info(base: dict, info: dict) -> dict:
    """把 info 链返回的字段补全到 search 拿到的歌曲上

    只补空字段，避免覆盖 search 链已有的真实数据
    """
    if not info:
        return base
    for key in ('album', 'picUrl', 'artists', 'pay', 'fee', 'qualityMap', 'bestQuality'):
        cur = base.get(key)
        if not cur and info.get(key):
            base[key] = info[key]
    # 兜底：补完 qualityMap 后重算 bestQuality（info 链可能没给 bestQuality）
    if base.get('qualityMap') and not base.get('bestQuality'):
        from .fallback.extractors import _best_quality
        base['bestQuality'] = _best_quality(base['qualityMap'])
    return base


class MusicClient:
    """统一的音乐客户端总控类"""

    PLATFORM_REGISTRY = [
        ('netease', netease_client, '网易云音乐', '#e72d2c', '网易云音乐平台'),
        ('qq',      qq_client,      'QQ音乐',    '#31c27c', 'QQ音乐平台'),
        ('kugou',   kugou_client,   '酷狗音乐',  '#2a8eff', '酷狗音乐平台'),
        ('kuwo',    kuwo_client,    '酷我音乐',  '#ff6600', '酷我音乐平台'),
    ]

    def __init__(self):
        self.platform_clients: Dict[str, BaseMusicClient] = {}
        for platform_id, client, *_ in self.PLATFORM_REGISTRY:
            self.register_client(platform_id, client)
        self.default_platform = 'netease'

    def register_client(self, platform: str, client: BaseMusicClient) -> None:
        if not isinstance(client, BaseMusicClient):
            raise ValueError("客户端必须继承自 BaseMusicClient")
        self.platform_clients[platform] = client
        logger.info(f"已注册平台: {platform}")

    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表（id / name / color / description）"""
        return [
            {'id': p, 'name': name, 'color': color, 'description': desc}
            for p, _, name, color, desc in self.PLATFORM_REGISTRY
        ]

    def _get_client(self, platform: str) -> BaseMusicClient:
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        return client

    # ==================== 业务方法 ====================

    def search(self, keyword: str, platform: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """搜索歌曲（永远只搜歌曲；URL 由 service 层另行解析）

        拿到搜索结果后，对每首并发调一次 info 链补全元信息
        （album/picUrl/qualityMap 等），因为部分搜索源（如 xunhuisi）
        搜索结果缺少这些字段。
        """
        client = self._get_client(platform)
        result = client.search(keyword, limit=limit)
        songs = result.get('data', []) if isinstance(result, dict) else []
        if not songs or not getattr(client, 'parse_info_chain', None):
            return songs

        def _enrich(song: dict) -> dict:
            try:
                info, _src = client.parse_info_chain.try_fetch(
                    'parse_info', song_id=str(song.get('id') or ''),
                )
                return _merge_song_info(song, info or {})
            except Exception as e:  # noqa
                logger.debug(f'enrich song {song.get("id")} failed: {e}')
                return song

        try:
            with ThreadPoolExecutor(max_workers=min(8, len(songs))) as pool:
                enriched = list(pool.map(_enrich, songs))
            return enriched
        except Exception as e:  # noqa
            logger.debug(f'enrich batch failed: {e}')
            return songs

    def get_song(self, song_id: Any, quality: str = 'lossless',
                 platform: str = None, with_lyric: bool = True) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息（信息 + URL + 可选歌词）

        Returns:
            None 表示完全失败
        """
        client = self._get_client(platform)
        return client.get_song(str(song_id), quality, with_lyric=with_lyric)


# 全局单例
music_client = MusicClient()


# ==================== 向后兼容的函数接口 ====================

def search_music(keywords: str, platform: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    return music_client.search(keywords, platform, limit=limit)


def get_song(song_id: str, quality: str, platform: str = None,
             with_lyric: bool = True) -> Optional[Dict[str, Any]]:
    """获取歌曲完整信息（向后兼容，新接口推荐用 music_client.get_song）"""
    return music_client.get_song(song_id, quality, platform, with_lyric=with_lyric)


def get_platforms() -> List[Dict[str, str]]:
    return music_client.get_platforms()
