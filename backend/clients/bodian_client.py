"""波点音乐客户端（重写版 - 使用 FallbackChain 框架）

波点底层是酷我，需要特殊 headers。
"""
import logging
from typing import Dict, Any, List

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_bodian_song
from .quality_config import QualityLevel, is_valid_quality, get_default_quality
from .sources.bodian import (
    BODIAN_SEARCH_SOURCES,
    BODIAN_PARSE_URL_SOURCES,
    BODIAN_PARSE_INFO_SOURCES,
    BODIAN_PARSE_LYRIC_SOURCES,
)

logger = logging.getLogger(__name__)


class BodianClient(BaseMusicClient):
    """波点音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.search_chain = FallbackChain(BODIAN_SEARCH_SOURCES, platform='bodian', strategy='parallel')
        self.parse_url_chain = FallbackChain(BODIAN_PARSE_URL_SOURCES, platform='bodian', strategy='serial')
        self.parse_info_chain = FallbackChain(BODIAN_PARSE_INFO_SOURCES, platform='bodian', strategy='serial')
        self.parse_lyric_chain = FallbackChain(BODIAN_PARSE_LYRIC_SOURCES, platform='bodian', strategy='serial')

    def search(self, keyword: str, limit: int = 50, offset: int = 0,
               quality: str = 'lossless', type_: int = 1) -> Dict[str, Any]:
        """搜索歌曲"""
        results, source = self.search_chain.try_fetch('search', keyword=keyword, limit=limit)
        normalized = []
        for r in results or []:
            n = normalize_bodian_song(r)
            if n.get('name') and n.get('id'):
                n['source'] = 'bodian'
                n['api_source'] = r.get('_source', source or 'unknown')
                normalized.append(n)
        return {
            'data': normalized[:limit],
            'type': type_,
            'source': 'bodian',
            'total': len(normalized),
            'search_source': source,
            'warnings': [],
        }

    def get_song_info(self, song_id) -> Dict[str, Any]:
        """获取歌曲元信息（波点用 rid）

        注意：波点没有稳定的 info API（cenguigui 已不可用）。
        当解析失败时返回最小 stub（只含 id），让 /song 接口继续走 URL 流程。
        """
        info, source = self.parse_info_chain.try_fetch('parse_info', rid=str(song_id))
        if info and isinstance(info, dict) and info.get('name'):
            n = normalize_bodian_song(info)
            n['source'] = 'bodian'
            n['api_source'] = source or 'unknown'
            return n
        # Fallback: 至少返回 id，让 /song 可以拿 URL
        return {
            'id': str(song_id),
            'name': '',
            'artists': '',
            'album': '',
            'picUrl': '',
            'duration': 0,
            'source': 'bodian',
            'api_source': 'unknown',
        }

    def get_song_url(self, song_id, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取下载 URL（波点用 rid）"""
        if not is_valid_quality(quality):
            quality = get_default_quality()
        url, source = self.parse_url_chain.try_fetch('parse_url', rid=str(song_id), quality=quality)
        if url and url.startswith('http'):
            return {
                'url': url,
                'quality': quality,
                'api_source': source,
                'song_id': str(song_id),
                'source': 'bodian',
            }
        return {}

    def get_lyric(self, song_id) -> str:
        """获取歌词"""
        lyric, _ = self.parse_lyric_chain.try_fetch('parse_lyric', rid=str(song_id))
        return lyric or ''

    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        return []

    def get_playlist(self, playlist_id) -> Dict[str, Any]:
        return {'id': str(playlist_id), 'name': '', 'cover': '', 'songs': []}

    def get_health(self) -> dict:
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
            'parse_lyric': self.parse_lyric_chain.get_health(),
        }


bodian_client = BodianClient()
