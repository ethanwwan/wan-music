"""酷我音乐客户端（重写版 - 使用 FallbackChain 框架）

所有数据源参考 musicdl kuwo.py。
"""
import logging
from typing import Any, Dict, Optional

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_kuwo_song
from .quality_config import QualityLevel
from .sources.kuwo import (
    KUWO_SEARCH_SOURCES,
    KUWO_PARSE_URL_SOURCES,
    KUWO_PARSE_INFO_SOURCES,
    KUWO_PARSE_LYRIC_SOURCES,
    KUWO_PARSE_PLAYLIST_SOURCES,
)

logger = logging.getLogger(__name__)


class KuwoClient(BaseMusicClient):
    """酷我音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.platform_id = 'kuwo'
        self.platform_name = '酷我音乐'
        self.search_chain = FallbackChain(KUWO_SEARCH_SOURCES, platform='kuwo', strategy='serial')
        self.parse_url_chain = FallbackChain(KUWO_PARSE_URL_SOURCES, platform='kuwo', strategy='serial')
        self.parse_info_chain = FallbackChain(KUWO_PARSE_INFO_SOURCES, platform='kuwo', strategy='serial')
        self.parse_lyric_chain = FallbackChain(KUWO_PARSE_LYRIC_SOURCES, platform='kuwo', strategy='serial')
        self.parse_playlist_chain = FallbackChain(KUWO_PARSE_PLAYLIST_SOURCES, platform='kuwo', strategy='serial')

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """搜索歌曲"""
        results, source = self.search_chain.try_fetch('search', keyword=keyword, limit=limit)
        normalized = []
        for r in results or []:
            n = normalize_kuwo_song(r)
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
        """一次性获取歌曲完整信息（酷我用 rid，使用基类模板方法）

        跨源一致性策略：
        - 若传入了 _cached_info（来自 search 阶段 song_info_cache），
          **直接使用**作为 name/artist/album/cover/duration，
          不再抢答 parse_info_chain（避免 url/info 跨源不一致）
        - 若 _cached_info 缺失（URL 解析/歌单导入等无 search 上下文），
          回退到 parse_info_chain 兜底拿 info

        url/lyric 同源策略：
        - 先抢答 url，**成功后立刻用 url 选中的源**抢答 lyric
        - 避免 url 来自 A 源、lyric 来自 B 源导致的"音频/歌词版本错配"

        酷我特殊处理：URL/Info/Lyric 链都用 `rid` 而非 `song_id`

        Args:
            preferred_source: 来自 search 的源名，传下去给 url/lyric 链优先使用
            quality_map: 该歌曲可用音质字典（来自 search result），用于 URL size 验证
            _cached_info: search 阶段缓存的完整 song info
        """

        def build_url_params(song_id_str, quality, preferred_source, quality_map):
            return {
                'rid': song_id_str,
                'quality': quality,
                'preferred_source': preferred_source,
                'quality_map': quality_map or {},
            }

        def build_lyric_params(song_id_str, preferred_source, url_src):
            return {
                'rid': song_id_str,
                'preferred_source': preferred_source,
            }

        return self._get_song_template(
            song_id=song_id,
            quality=quality,
            with_lyric=with_lyric,
            preferred_source=preferred_source,
            quality_map=quality_map,
            _cached_info=_cached_info,
            url_chain=self.parse_url_chain,
            lyric_chain=self.parse_lyric_chain,
            info_chain=self.parse_info_chain,
            normalize_func=normalize_kuwo_song,
            url_params_builder=build_url_params,
            lyric_params_builder=build_lyric_params,
            url_deadline_seconds=5.0,
        )

    def _build_info_params(self, song_id_str: str, preferred_source: str) -> dict:
        """覆盖基类实现：酷我 info_chain 使用 rid 参数"""
        return {'rid': song_id_str, 'preferred_source': preferred_source}

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
        """解析歌单：返回 {'name','creator','cover','trackCount','tracks', 'source', 'api_source'}

        串行：调用链中第一个成功解析的源
        """
        data, source = self.parse_playlist_chain.try_fetch(
            'parse_playlist',
            playlist_id=str(playlist_id),
            page=page,
            size=size,
            target_platform=self.platform_id,
        )
        if not data or not isinstance(data, dict):
            return None
        # 给每首歌曲补上平台标记
        for t in data.get('tracks', []) or []:
            if not t.get('source'):
                t['source'] = self.platform_id
        return {
            **data,
            'platform': self.platform_id,
            'api_source': source or 'unknown',
        }


kuwo_client = KuwoClient()
