"""网易云音乐客户端（重写版 - 使用 FallbackChain 框架）

所有第三方 API 配置在 sources/netease.py 中，本文件只负责：
  - 协调多个 Chain（search/parse_url/parse_info/parse_lyric）
  - 标准化响应
  - 兼容老 API
"""
import logging
import time
from typing import Dict, Any, List, Optional

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_netease_song
from .fallback.api_source import ApiSource
from .quality_config import QualityLevel, is_valid_quality, get_default_quality
from .sources.netease import (
    NETEASE_SEARCH_SOURCES,
    NETEASE_PARSE_URL_SOURCES,
    NETEASE_PARSE_INFO_SOURCES,
    NETEASE_PARSE_LYRIC_SOURCES,
)

logger = logging.getLogger(__name__)


class NeteaseClient(BaseMusicClient):
    """网易云音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        # 4 条独立的 fallback 链
        self.search_chain = FallbackChain(NETEASE_SEARCH_SOURCES, platform='netease', strategy='parallel')
        self.parse_url_chain = FallbackChain(NETEASE_PARSE_URL_SOURCES, platform='netease', strategy='serial')
        self.parse_info_chain = FallbackChain(NETEASE_PARSE_INFO_SOURCES, platform='netease', strategy='serial')
        self.parse_lyric_chain = FallbackChain(NETEASE_PARSE_LYRIC_SOURCES, platform='netease', strategy='serial')

    # ==================== 搜索 ====================

    def search(self, keyword: str, limit: int = 50, offset: int = 0,
               quality: str = 'lossless', type_: int = 1) -> Dict[str, Any]:
        """搜索歌曲（并行请求所有搜索源，去重合并）"""
        results, source = self.search_chain.try_fetch(
            'search', keyword=keyword, limit=limit, offset=offset
        )
        # 标准化结果
        normalized = []
        for r in results or []:
            n = normalize_netease_song(r)
            if n.get('name') and n.get('id'):
                n['source'] = 'netease'
                n['api_source'] = r.get('_source', source or 'unknown')
                normalized.append(n)
        return {
            'data': normalized[:limit],
            'type': type_,
            'source': 'netease',
            'total': len(normalized),
            'search_source': source,
            'warnings': [],
        }

    # ==================== 歌曲详情 ====================

    def get_song_info(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲元信息（串行 fallback）"""
        info, source = self.parse_info_chain.try_fetch('parse_info', song_id=str(song_id))
        if info and isinstance(info, dict) and info.get('name'):
            info['source'] = 'netease'
            info['api_source'] = source or 'unknown'
            return info
        return {}

    # ==================== 下载 URL ====================

    def get_song_url(self, song_id: int, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取下载 URL（串行 fallback 直至成功）"""
        if not is_valid_quality(quality):
            quality = get_default_quality()
        url, source = self.parse_url_chain.try_fetch(
            'parse_url', song_id=str(song_id), quality=quality
        )
        if url and url.startswith('http'):
            return {
                'url': url,
                'quality': quality,
                'api_source': source,
                'song_id': str(song_id),
                'source': 'netease',
            }
        return {}

    # ==================== 歌词 ====================

    def get_lyric(self, song_id: int) -> str:
        """获取歌词"""
        lyric, source = self.parse_lyric_chain.try_fetch('parse_lyric', song_id=str(song_id))
        return lyric or ''

    # ==================== 歌单 ====================

    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单（暂未实现 fallback，保留接口）"""
        logger.debug(f'[netease] search_playlist: keyword={keyword}, limit={limit}')
        return []

    def get_playlist(self, playlist_id: Any) -> Dict[str, Any]:
        """获取歌单详情（暂未实现 fallback，保留接口）"""
        logger.debug(f'[netease] get_playlist: id={playlist_id}')
        return {'id': str(playlist_id), 'name': '', 'cover': '', 'songs': []}

    # ==================== 健康监控 ====================

    def get_health(self) -> dict:
        """获取所有 fallback 链的健康状态"""
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
            'parse_lyric': self.parse_lyric_chain.get_health(),
        }


# 全局单例
netease_client = NeteaseClient()
