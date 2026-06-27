"""酷狗音乐客户端（重写版 - 使用 FallbackChain 框架）

酷狗 file_hash 模式，第三方 API 较少。
"""
import logging
from typing import Dict, Any, List

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_kugou_song
from .quality_config import QualityLevel, is_valid_quality, get_default_quality
from .sources.kugou import (
    KUGOU_SEARCH_SOURCES,
    KUGOU_PARSE_URL_SOURCES,
    KUGOU_PARSE_INFO_SOURCES,
)

logger = logging.getLogger(__name__)


class KugouClient(BaseMusicClient):
    """酷狗音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.search_chain = FallbackChain(KUGOU_SEARCH_SOURCES, platform='kugou', strategy='parallel')
        self.parse_url_chain = FallbackChain(KUGOU_PARSE_URL_SOURCES, platform='kugou', strategy='serial')
        self.parse_info_chain = FallbackChain(KUGOU_PARSE_INFO_SOURCES, platform='kugou', strategy='serial')

    def search(self, keyword: str, limit: int = 50, offset: int = 0,
               quality: str = 'lossless', type_: int = 1) -> Dict[str, Any]:
        """搜索歌曲"""
        results, source = self.search_chain.try_fetch('search', keyword=keyword, limit=limit)
        normalized = []
        for r in results or []:
            n = normalize_kugou_song(r)
            if n.get('name') and n.get('id'):
                n['source'] = 'kugou'
                n['api_source'] = r.get('_source', source or 'unknown')
                normalized.append(n)
        return {
            'data': normalized[:limit],
            'type': type_,
            'source': 'kugou',
            'total': len(normalized),
            'search_source': source,
            'warnings': [],
        }

    def get_song_info(self, song_id) -> Dict[str, Any]:
        """获取歌曲元信息（酷狗用 hash 标识）"""
        info, source = self.parse_info_chain.try_fetch('parse_info', hash=str(song_id))
        if info and isinstance(info, dict) and info.get('name'):
            n = normalize_kugou_song(info)
            n['source'] = 'kugou'
            n['api_source'] = source or 'unknown'
            return n
        return {}

    def get_song_url(self, song_id, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取下载 URL（酷狗用 hash）"""
        if not is_valid_quality(quality):
            quality = get_default_quality()
        url, source = self.parse_url_chain.try_fetch('parse_url', hash=str(song_id), quality=quality)
        if url and url.startswith('http'):
            return {
                'url': url,
                'quality': quality,
                'api_source': source,
                'song_id': str(song_id),
                'source': 'kugou',
            }
        return {}

    def get_lyric(self, song_id) -> str:
        """酷狗暂未实现 fallback"""
        return ''

    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        return []

    def get_playlist(self, playlist_id) -> Dict[str, Any]:
        return {'id': str(playlist_id), 'name': '', 'cover': '', 'songs': []}

    def get_health(self) -> dict:
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
        }


kugou_client = KugouClient()
