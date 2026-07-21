"""酷狗音乐客户端（重写版 - 使用 FallbackChain 框架）

酷狗 file_hash 模式，第三方 API 较少。
歌词走两步流程（krcs.kugou.com/search → lyrics.kugou.com/download KRC 解密），
由 kugou_official_lyric (P=0) source 自动处理。
"""
import logging
from typing import Any, Dict, Optional

from .base_client import BaseMusicClient
from .fallback.chain import FallbackChain
from .fallback.extractors import normalize_kugou_song
from .quality_config import QualityLevel
from .sources.kugou import (
    KUGOU_SEARCH_SOURCES,
    KUGOU_PARSE_URL_SOURCES,
    KUGOU_PARSE_INFO_SOURCES,
    KUGOU_PARSE_LYRIC_SOURCES,
    KUGOU_PARSE_PLAYLIST_SOURCES,
)

logger = logging.getLogger(__name__)


class KugouClient(BaseMusicClient):
    """酷狗音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.platform_id = 'kugou'
        self.platform_name = '酷狗音乐'
        self.search_chain = FallbackChain(KUGOU_SEARCH_SOURCES, platform='kugou', strategy='serial')
        self.parse_url_chain = FallbackChain(KUGOU_PARSE_URL_SOURCES, platform='kugou', strategy='serial')
        self.parse_info_chain = FallbackChain(KUGOU_PARSE_INFO_SOURCES, platform='kugou', strategy='serial')
        self.parse_lyric_chain = FallbackChain(KUGOU_PARSE_LYRIC_SOURCES, platform='kugou', strategy='serial')
        self.parse_playlist_chain = FallbackChain(KUGOU_PARSE_PLAYLIST_SOURCES, platform='kugou', strategy='serial')

    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """搜索歌曲"""
        results, source = self.search_chain.try_fetch('search', keyword=keyword, limit=limit)
        normalized = []
        for r in results or []:
            n = normalize_kugou_song(r)
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
        """一次性获取歌曲完整信息（酷狗用 hash 标识，使用基类模板方法）

        跨源一致性策略：
        - 若传入了 _cached_info（来自 search 阶段 song_info_cache），
          **直接使用**作为 name/artist/album/cover/duration，
          不再抢答 parse_info_chain（避免 url/info 跨源不一致）
        - 若 _cached_info 缺失（URL 解析/歌单导入等无 search 上下文），
          回退到 parse_info_chain 兜底拿 info

        酷狗特殊处理：
        1. URL 参数用 `hash` 而非 `song_id`
        2. Info 参数同样用 `hash`
        3. Lyric 需要 `duration_ms` 参数（来自 cached_info.duration）

        Args:
            preferred_source: 来自 search 的源名，传下去给 url/info/lyric 链优先使用
            quality_map: 该歌曲可用音质字典（来自 search result），用于 URL size 验证
            _cached_info: search 阶段缓存的完整 song info
        """
        # 关键：酷狗的 lossless 用 SQ hash（FLAC），exhigh/standard 用 FileHash（MP3）
        # song_id 是 normalize 后的 primary_hash（已优先用 SQFileHash）
        # 但 exhigh/standard 时需要切到 mp3_hash（如果有的话）
        # 调用方在调用 get_song 时通常传入的是搜索结果的 id
        # 这里从传入的 id 中判断：
        # 简化处理：直接用传入的 id（已在 normalize 时选择过）
        parse_hash = str(song_id)

        # 缓存中提取 duration（毫秒）用于歌词链
        cached_duration_ms = 0
        if _cached_info:
            try:
                cached_duration_ms = int(_cached_info.get('duration') or 0)
            except (TypeError, ValueError):
                cached_duration_ms = 0

        def build_url_params(song_id_str, quality, preferred_source, quality_map):
            return {
                'hash': song_id_str,
                'quality': quality,
                'preferred_source': preferred_source,
                'quality_map': quality_map or {},
            }

        def build_lyric_params(song_id_str, preferred_source, url_src):
            # 酷狗官方两步：krcs.search + lyrics.download KRC 解密
            # 需要 duration_ms（来自 cached_info 或 info）作为 search 参数
            return {
                'song_id': song_id_str,
                'duration': cached_duration_ms,
                'preferred_source': preferred_source,
            }

        result = self._get_song_template(
            song_id=parse_hash,
            quality=quality,
            with_lyric=with_lyric,
            preferred_source=preferred_source,
            quality_map=quality_map,
            _cached_info=_cached_info,
            url_chain=self.parse_url_chain,
            lyric_chain=self.parse_lyric_chain,
            info_chain=self.parse_info_chain,
            normalize_func=normalize_kugou_song,
            url_params_builder=build_url_params,
            lyric_params_builder=build_lyric_params,
            url_deadline_seconds=6.5,
        )

        # 酷狗特殊处理：info_chain 用 hash 参数而非 song_id
        # 由于模板方法内 _build_info_params 走基类默认实现，已正确处理 hash 命名
        return result

    def _build_info_params(self, song_id_str: str, preferred_source: str) -> dict:
        """覆盖基类实现：酷狗 info_chain 使用 hash 参数"""
        return {'hash': song_id_str, 'preferred_source': preferred_source}

    def get_health(self) -> dict:
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
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


kugou_client = KugouClient()
