"""网易云音乐客户端（重写版 - 使用 FallbackChain 框架）

所有第三方 API 配置在 sources/netease.py 中，本文件只负责：
  - 协调多个 Chain（search / parse_url / parse_info / parse_lyric）
  - 标准化响应
  - 暴露 search / get_song 业务方法
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_netease_song
from .quality_config import QualityLevel
from .sources.netease import (
    NETEASE_SEARCH_SOURCES,
    NETEASE_PARSE_URL_SOURCES,
    NETEASE_PARSE_INFO_SOURCES,
    NETEASE_PARSE_LYRIC_SOURCES,
    NETEASE_PARSE_PLAYLIST_SOURCES,
)

logger = logging.getLogger(__name__)


class NeteaseClient(BaseMusicClient):
    """网易云音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.platform_id = 'netease'
        self.platform_name = '网易云音乐'
        self.search_chain = FallbackChain(NETEASE_SEARCH_SOURCES, platform='netease', strategy='parallel')
        self.parse_url_chain = FallbackChain(NETEASE_PARSE_URL_SOURCES, platform='netease', strategy='serial')
        self.parse_info_chain = FallbackChain(NETEASE_PARSE_INFO_SOURCES, platform='netease', strategy='serial')
        self.parse_lyric_chain = FallbackChain(NETEASE_PARSE_LYRIC_SOURCES, platform='netease', strategy='serial')
        self.parse_playlist_chain = FallbackChain(NETEASE_PARSE_PLAYLIST_SOURCES, platform='netease', strategy='serial')

    # ==================== 业务方法 ====================

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """搜索歌曲（并行请求所有搜索源，去重合并）"""
        results, source = self.search_chain.try_fetch(
            'search', keyword=keyword, limit=limit, offset=offset
        )
        normalized = []
        for r in results or []:
            n = normalize_netease_song(r)
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
        """一次性获取歌曲完整信息：URL + 元信息 + (可选) 歌词

        实现策略：3 条链并行执行（URL 串行链可视为「一旦成功就返回」，
        整体仍然比串行快）
        """
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

        # URL 是关键，没有 URL 视为失败
        if not url or not url.startswith('http'):
            return None

        # 元信息是元信息，能拿到最好；没有就用最小 stub
        if info and info.get('name'):
            base = normalize_netease_song(info)
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
            'level': quality,                  # 前端用 'level' 字段
            'lyric': lyric or '',
            'source': self.platform_id,
            'api_source': f'{url_src}|{info_src_name}',
        }

    # ==================== 健康监控 ====================

    def get_health(self) -> dict:
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
            'parse_lyric': self.parse_lyric_chain.get_health(),
            'parse_playlist': self.parse_playlist_chain.get_health(),
        }

    # ==================== 歌单 ====================

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


# 全局单例
netease_client = NeteaseClient()
