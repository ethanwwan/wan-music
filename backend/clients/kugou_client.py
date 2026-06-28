"""酷狗音乐客户端（重写版 - 使用 FallbackChain 框架）

酷狗 file_hash 模式，第三方 API 较少。酷狗的歌词走搜词 → 选 → 拿 lyric_url，
需要 2 步，目前未实现，所以 with_lyric=False。
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
        """一次性获取歌曲完整信息（酷狗用 hash 标识；暂无歌词链）"""
        quality = self._normalize_quality(quality)
        song_id_str = str(song_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_url = pool.submit(self.parse_url_chain.try_fetch, 'parse_url',
                                hash=song_id_str, quality=quality)
            f_info = pool.submit(self.parse_info_chain.try_fetch, 'parse_info',
                                 hash=song_id_str)

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

        return {
            **base,
            'url': url,
            'quality': quality,
            'lyric': '',  # 酷狗暂未实现歌词链
            'source': self.platform_id,
            'api_source': f'{url_src}|{info_src_name}',
        }

    def get_health(self) -> dict:
        return {
            'search': self.search_chain.get_health(),
            'parse_url': self.parse_url_chain.get_health(),
            'parse_info': self.parse_info_chain.get_health(),
        }


kugou_client = KugouClient()
