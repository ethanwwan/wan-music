"""QQ 音乐客户端（重写版 - 使用 FallbackChain 框架）

QQ 鉴权复杂，主要依赖第三方解析 API。
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_qq_song
from .quality_config import QualityLevel
from .sources.qq import (
    QQ_SEARCH_SOURCES,
    QQ_PARSE_URL_SOURCES,
    QQ_PARSE_INFO_SOURCES,
    QQ_PARSE_LYRIC_SOURCES,
    QQ_PARSE_PLAYLIST_SOURCES,
)

logger = logging.getLogger(__name__)


class QQClient(BaseMusicClient):
    """QQ 音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.platform_id = 'qq'
        self.platform_name = 'QQ音乐'
        self.search_chain = FallbackChain(QQ_SEARCH_SOURCES, platform='qq', strategy='parallel')
        self.parse_url_chain = FallbackChain(QQ_PARSE_URL_SOURCES, platform='qq', strategy='serial')
        self.parse_info_chain = FallbackChain(QQ_PARSE_INFO_SOURCES, platform='qq', strategy='serial')
        self.parse_lyric_chain = FallbackChain(QQ_PARSE_LYRIC_SOURCES, platform='qq', strategy='serial')
        self.parse_playlist_chain = FallbackChain(QQ_PARSE_PLAYLIST_SOURCES, platform='qq', strategy='serial')

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """搜索歌曲"""
        results, source = self.search_chain.try_fetch('search', keyword=keyword, limit=limit)
        normalized = []
        for r in results or []:
            n = normalize_qq_song(r)
            if n.get('name') and n.get('id'):
                n['source'] = self.platform_id
                n['api_source'] = r.get('_source', source or 'unknown')
                normalized.append(n)
        return {
            'data': normalized[:limit],
            'search_source': source,
            'warnings': [],
        }

    def get_song(self, song_id, quality: str = QualityLevel.LOSSLESS.value,
                 with_lyric: bool = True) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息"""
        quality = self._normalize_quality(quality)
        song_id_str = str(song_id)

        with ThreadPoolExecutor(max_workers=3) as pool:
            f_url = pool.submit(self.parse_url_chain.try_fetch, 'parse_url',
                                song_id=song_id_str, quality=quality)
            f_info = pool.submit(self.parse_info_chain.try_fetch, 'parse_info',
                                 song_id=song_id_str)
            f_lyric = (pool.submit(self.parse_lyric_chain.try_fetch, 'parse_lyric',
                                   song_id=song_id_str) if with_lyric else None)

        url, url_src = f_url.result()
        info, info_src = f_info.result()
        lyric = f_lyric.result()[0] if f_lyric else ''

        if not url or not url.startswith('http'):
            return None

        if info and info.get('name'):
            base = normalize_qq_song(info)
            info_src_name = info_src
        else:
            base = {
                'id': song_id_str,
                'name': '',
                'artists': '',
                'album': '',
                'picUrl': '',
                'duration': 0,
            }
            info_src_name = 'unknown'

        return {
            **base,
            'url': url,
            'quality': quality,
            'lyric': lyric or '',
            'source': self.platform_id,
            'api_source': f'{url_src}|{info_src_name}',
        }

    def get_health(self) -> dict:
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
            'parse_lyric': self.parse_lyric_chain.get_health(),
            'parse_playlist': self.parse_playlist_chain.get_health(),
        }

    def parse_playlist(self, playlist_id: str, page: int = 1,
                       size: int = 100) -> Optional[Dict[str, Any]]:
        """解析歌单：返回 {name, creator, cover, trackCount, tracks, ...}"""
        data, source = self.parse_playlist_chain.try_fetch(
            'parse_playlist', playlist_id=str(playlist_id), page=page, size=size,
            target_platform=self.platform_id,
        )
        if not data or not isinstance(data, dict):
            return None
        for t in data.get('tracks', []) or []:
            if not t.get('source'):
                t['source'] = self.platform_id
        return {
            **data,
            'platform': self.platform_id,
            'api_source': source or 'unknown',
        }


qq_client = QQClient()
