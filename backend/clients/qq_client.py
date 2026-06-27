"""QQ 音乐客户端（重写版 - 使用 FallbackChain 框架）

QQ 鉴权复杂，主要依赖第三方解析 API。
"""
import logging
from typing import Dict, Any, List

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_qq_song
from .quality_config import QualityLevel, is_valid_quality, get_default_quality
from .sources.qq import (
    QQ_SEARCH_SOURCES,
    QQ_PARSE_URL_SOURCES,
    QQ_PARSE_INFO_SOURCES,
    QQ_PARSE_LYRIC_SOURCES,
)

logger = logging.getLogger(__name__)


class QQClient(BaseMusicClient):
    """QQ 音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.search_chain = FallbackChain(QQ_SEARCH_SOURCES, platform='qq', strategy='parallel')
        self.parse_url_chain = FallbackChain(QQ_PARSE_URL_SOURCES, platform='qq', strategy='serial')
        self.parse_info_chain = FallbackChain(QQ_PARSE_INFO_SOURCES, platform='qq', strategy='serial')
        self.parse_lyric_chain = FallbackChain(QQ_PARSE_LYRIC_SOURCES, platform='qq', strategy='serial')

    def search(self, keyword: str, limit: int = 50, offset: int = 0,
               quality: str = 'lossless', type_: int = 1) -> Dict[str, Any]:
        """搜索歌曲"""
        results, source = self.search_chain.try_fetch('search', keyword=keyword, limit=limit)
        normalized = []
        for r in results or []:
            n = normalize_qq_song(r)
            if n.get('name') and n.get('id'):
                n['source'] = 'qq'
                n['api_source'] = r.get('_source', source or 'unknown')
                normalized.append(n)
        return {
            'data': normalized[:limit],
            'type': type_,
            'source': 'qq',
            'total': len(normalized),
            'search_source': source,
            'warnings': [],
        }

    def get_song_info(self, song_id) -> Dict[str, Any]:
        """获取歌曲元信息

        Fallback: 解析失败时返回最小 stub（只含 id），让 /song 接口继续走 URL 流程。
        """
        info, source = self.parse_info_chain.try_fetch('parse_info', song_id=str(song_id))
        if info and isinstance(info, dict) and info.get('name'):
            n = normalize_qq_song(info)
            n['source'] = 'qq'
            n['api_source'] = source or 'unknown'
            return n
        # Fallback stub
        return {
            'id': str(song_id),
            'name': '',
            'artists': '',
            'album': '',
            'picUrl': '',
            'duration': 0,
            'source': 'qq',
            'api_source': 'unknown',
        }

    def get_song_url(self, song_id, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取下载 URL"""
        if not is_valid_quality(quality):
            quality = get_default_quality()
        url, source = self.parse_url_chain.try_fetch('parse_url', song_id=str(song_id), quality=quality)
        if url and url.startswith('http'):
            return {
                'url': url,
                'quality': quality,
                'api_source': source,
                'song_id': str(song_id),
                'source': 'qq',
            }
        return {}

    def get_lyric(self, song_id) -> str:
        """获取歌词"""
        lyric, _ = self.parse_lyric_chain.try_fetch('parse_lyric', song_id=str(song_id))
        return lyric or ''

    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单（暂未实现）"""
        return []

    def get_playlist(self, playlist_id) -> Dict[str, Any]:
        """获取歌单（暂未实现）"""
        return {'id': str(playlist_id), 'name': '', 'cover': '', 'songs': []}

    def get_health(self) -> dict:
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
            'parse_lyric': self.parse_lyric_chain.get_health(),
        }


qq_client = QQClient()
