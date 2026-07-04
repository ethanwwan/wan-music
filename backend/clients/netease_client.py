"""网易云音乐客户端（重写版 - 使用 FallbackChain 框架）

所有第三方 API 配置在 sources/netease.py 中，本文件只负责：
  - 协调多个 Chain（search / parse_url / parse_info / parse_lyric）
  - 标准化响应
  - 暴露 search / get_song 业务方法

设计原则：串行 fallback + 成功记忆。
  - parse_url / parse_lyric / parse_info 都使用 serial 策略
  - 按 priority 依次尝试各源，成功后 mark_source_success 记录
  - 下一次请求优先使用最近成功的源（_try_serial 的 _sort_key）
  - 失败后自动降级到下一个源（mark_source_failed）
  - 无需 parallel-first 抢答，节省 API 配额、降低并发压力
"""
import logging
import time
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
        super().__init__(cookie_file='netease_cookie.txt')
        self.platform_id = 'netease'
        self.platform_name = '网易云音乐'
        self.search_chain = FallbackChain(NETEASE_SEARCH_SOURCES, platform='netease', strategy='serial')
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
                 with_lyric: bool = True, preferred_source: str = '',
                 quality_map: dict = None,
                 _cached_info: dict = None) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息：URL + (元信息复用 search) + (可选) 歌词

        串行流程（serial fallback）：
          1. parse_url_chain → 串行尝试各 URL 源，第一个成功即返回
          2. parse_lyric_chain → 串行尝试各歌词源，携带 same_source 同源优先
          3. 元信息直接使用 _cached_info（search 阶段写入，几乎总是存在）

        成功记忆：
          - URL 成功后 `mark_source_success`，下次该源排最前
          - URL 失败后 `mark_source_failed`，下次跳过该源

        Args:
            preferred_source: 来自 search 的源名，传下去给 url/lyric 链优先使用
            quality_map: 该歌曲可用音质字典（来自 search result），用于 URL size 验证
            _cached_info: search 阶段缓存的完整 song info
        """
        quality = self._normalize_quality(quality)
        song_id_str = str(song_id)
        url_kwargs = dict(song_id=song_id_str, quality=quality,
                          preferred_source=preferred_source, quality_map=quality_map or {})

        t_start = time.time()

        # Step 1: 串行获取 URL（按 priority 依次尝试各源）
        url, url_src = self.parse_url_chain.try_fetch('parse_url', cookies=self.cookies, **url_kwargs)
        if not url or not url.startswith('http'):
            return None

        # Step 2: 串行获取歌词（带上 same_source 优先用 URL 同源）
        lyric, lyric_src = '', None
        if with_lyric:
            try:
                lyric, lyric_src = self.parse_lyric_chain.try_fetch(
                    'parse_lyric', song_id=song_id_str,
                    preferred_source=preferred_source,
                    same_source=url_src or '',
                    cookies=self.cookies,
                )
            except Exception as e:
                logger.warning(f'[{self.platform_id}] lyric 获取异常: {e}')

        logger.info(
            f'[{self.platform_id}] /song 串行完成: '
            f'url={url_src} lyric={lyric_src} info={"cached" if _cached_info else "none"} '
            f'耗时={time.time()-t_start:.2f}s'
        )

        # Step 3: 元信息直接复用 _cached_info
        if _cached_info and _cached_info.get('name'):
            base = normalize_netease_song(_cached_info)
            info_src_name = _cached_info.get('_search_source', 'cached')
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
            'level': quality,
            'lyric': lyric or '',
            'source': self.platform_id,
            'api_source': {'url': url_src, 'info': info_src_name, 'lyric': lyric_src},
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
