"""酷我音乐客户端（重写版 - 使用 FallbackChain 框架）

所有数据源参考 musicdl kuwo.py（13 个 parsewith + 1 个官方）。
"""
import logging
from typing import Dict, Any, List

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_kuwo_song
from .quality_config import QualityLevel, is_valid_quality, get_default_quality
from .sources.kuwo import (
    KUWO_SEARCH_SOURCES,
    KUWO_PARSE_URL_SOURCES,
    KUWO_PARSE_INFO_SOURCES,
    KUWO_PARSE_LYRIC_SOURCES,
)

logger = logging.getLogger(__name__)


class KuwoClient(BaseMusicClient):
    """酷我音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.platform_id = 'kuwo'
        self.platform_name = '酷我音乐'
        self.search_chain = FallbackChain(KUWO_SEARCH_SOURCES, platform='kuwo', strategy='parallel')
        self.parse_url_chain = FallbackChain(KUWO_PARSE_URL_SOURCES, platform='kuwo', strategy='serial')
        self.parse_info_chain = FallbackChain(KUWO_PARSE_INFO_SOURCES, platform='kuwo', strategy='serial')
        self.parse_lyric_chain = FallbackChain(KUWO_PARSE_LYRIC_SOURCES, platform='kuwo', strategy='serial')

    def search(self, keyword: str, limit: int = 50, offset: int = 0,
               quality: str = 'lossless', type_: int = 1) -> Dict[str, Any]:
        """搜索歌曲"""
        results, source = self.search_chain.try_fetch('search', keyword=keyword, limit=limit)
        normalized = []
        for r in results or []:
            n = normalize_kuwo_song(r)
            if n.get('name') and n.get('id'):
                n['source'] = 'kuwo'
                n['api_source'] = r.get('_source', source or 'unknown')
                normalized.append(n)
        return {
            'data': normalized[:limit],
            'type': type_,
            'source': 'kuwo',
            'total': len(normalized),
            'search_source': source,
            'warnings': [],
        }

    def get_song_info(self, song_id) -> Dict[str, Any]:
        """获取歌曲元信息（酷我用 rid）"""
        info, source = self.parse_info_chain.try_fetch('parse_info', rid=str(song_id))
        if info and isinstance(info, dict) and info.get('name'):
            n = normalize_kuwo_song(info)
            n['source'] = 'kuwo'
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
            'source': 'kuwo',
            'api_source': 'unknown',
        }

    def get_song_url(self, song_id, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取下载 URL（酷我用 rid）"""
        if not is_valid_quality(quality):
            quality = get_default_quality()
        url, source = self.parse_url_chain.try_fetch('parse_url', rid=str(song_id), quality=quality)
        if url and url.startswith('http'):
            return {
                'url': url,
                'quality': quality,
                'api_source': source,
                'song_id': str(song_id),
                'source': 'kuwo',
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


kuwo_client = KuwoClient()
