"""酷狗音乐客户端（重写版 - 使用 FallbackChain 框架）

酷狗 file_hash 模式，第三方 API 较少。
歌词走两步流程（krcs.kugou.com/search → lyrics.kugou.com/download KRC 解密），
由 kugou_official_lyric (P=0) source 自动处理。
"""
import logging
from concurrent.futures import ThreadPoolExecutor
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
        self.search_chain = FallbackChain(KUGOU_SEARCH_SOURCES, platform='kugou', strategy='parallel')
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
                 with_lyric: bool = True) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息（酷狗用 hash 标识）"""
        quality = self._normalize_quality(quality)
        song_id_str = str(song_id)

        # 关键：酷狗的 lossless 用 SQ hash（FLAC），exhigh/standard 用 FileHash（MP3）
        # song_id_str 是 normalize 后的 primary_hash（已优先用 SQFileHash）
        # 但 exhigh/standard 时需要切到 mp3_hash（如果有的话）
        # 调用方在调用 get_song 时通常传入的是搜索结果的 id
        # 这里从传入的 id 中判断：
        # 简化处理：直接用传入的 id（已在 normalize 时选择过）
        parse_hash = song_id_str

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_url = pool.submit(self.parse_url_chain.try_fetch, 'parse_url',
                                hash=parse_hash, quality=quality)
            f_info = pool.submit(self.parse_info_chain.try_fetch, 'parse_info',
                                 hash=parse_hash)

        url, url_src = f_url.result()
        info, info_src = f_info.result()

        if not url or not url.startswith('http'):
            return None

        if info and info.get('name'):
            base = normalize_kugou_song(info)
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

        # 歌词链（酷狗官方两步：krcs.search + lyrics.download KRC 解密）
        # 必须用 info.duration（ms）当 search 的 duration 参数，所以 lyric 在 info 后再调
        lyric = ''
        lyric_src = None
        if with_lyric:
            try:
                duration_ms = int(base.get('duration') or 0)
                lyric, lyric_src = self.parse_lyric_chain.try_fetch(
                    'parse_lyric', song_id=parse_hash, duration=duration_ms
                )
            except Exception as e:
                logger.warning(f'[kugou.get_song] 取歌词失败: {e}')

        return {
            **base,
            'url': url,
            'level': quality,                  # 前端用 'level' 字段
            'lyric': lyric or '',
            'source': self.platform_id,
            'api_source': {'url': url_src, 'info': info_src_name, 'lyric': lyric_src},
        }

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
