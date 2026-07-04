"""QQ 音乐客户端（重写版 - 使用 FallbackChain 框架）

QQ 鉴权复杂，主要依赖第三方解析 API。
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _detect_actual_quality_from_url(url: str, default: str) -> str:
    """从 QQ CDN URL 推断实际音质

    QQ CDN URL 格式: http://ws.stream.qqmusic.qq.com/{PREFIX}{songmid}.{ext}
    - F000 = FLAC (lossless)
    - M800 = MP3 320kbps (exhigh)
    - M500 = MP3 128kbps (standard)
    - C200/C100 = low
    - A000 = AAC lossless
    """
    if not url:
        return default
    fname = url.split('/')[-1].split('?')[0]
    ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
    prefix = fname[:4].upper() if len(fname) >= 4 else ''

    if prefix == 'F000' or prefix == 'A000' or ext in ('flac', 'ape', 'wav'):
        return 'lossless'
    if prefix == 'M800':
        return 'exhigh'
    if prefix == 'M500':
        return 'standard'
    if prefix in ('C200', 'C100'):
        return 'standard'
    if ext == 'mp3':
        return 'exhigh'
    return default


class QQClient(BaseMusicClient):
    """QQ 音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__(cookie_file='qq_cookie.txt')
        self.platform_id = 'qq'
        self.platform_name = 'QQ音乐'
        self.search_chain = FallbackChain(QQ_SEARCH_SOURCES, platform='qq', strategy='serial')
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
                 with_lyric: bool = True, preferred_source: str = '',
                 quality_map: dict = None,
                 _cached_info: dict = None) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息

        跨源一致性策略：
        - 若传入了 _cached_info（来自 search 阶段 song_info_cache），
          **直接使用**作为 name/artist/album/cover/duration，
          不再抢答 parse_info_chain（避免 url/info 跨源不一致）
        - 若 _cached_info 缺失（URL 解析/歌单导入等无 search 上下文），
          回退到 parse_info_chain 兜底拿 info

        url/lyric 同源策略：
        - 先抢答 url，**成功后立刻用 url 选中的源**抢答 lyric
        - 避免 url 来自 A 源、lyric 来自 B 源导致的"音频/歌词版本错配"

        Args:
            preferred_source: 来自 search 链的源名（如 'qq_official_search'），
                传下去给 url/lyric 链优先使用（避免跨源不一致）
            quality_map: 该歌曲可用音质字典（来自 search result），
                用于 URL 链 size 验证
            _cached_info: search 阶段缓存的完整 song info
        """
        quality = self._normalize_quality(quality)
        song_id_str = str(song_id)
        url_kwargs = dict(song_id=song_id_str, quality=quality,
                          preferred_source=preferred_source, quality_map=quality_map or {})

        # ★ 关键：先抢答 url，**先不并行 lyric**
        t_start = time.time()
        use_info_fallback = not _cached_info
        max_workers = 2 if use_info_fallback else 1
        pool = ThreadPoolExecutor(max_workers=max_workers)
        f_url = pool.submit(self.parse_url_chain.try_fetch, 'parse_url', cookies=self.cookies, **url_kwargs)
        f_info = (pool.submit(self.parse_info_chain.try_fetch, 'parse_info',
                              song_id=song_id_str, preferred_source=preferred_source)
                  if use_info_fallback else None)
        pool.shutdown(wait=False)

        url, url_src = '', None
        info, info_src = None, None
        deadline = t_start + 5.0
        futures = [f for f in (f_url, f_info) if f is not None]
        try:
            for fut in as_completed(futures, timeout=max(0.1, deadline - time.time())):
                try:
                    data, src = fut.result()
                except Exception as e:
                    logger.warning(f'[{self.platform_id}] 单链 future 异常: {e}')
                    continue
                if fut is f_url:
                    url, url_src = data, src
                elif fut is f_info:
                    info, info_src = data, src
                if url and url.startswith('http') and (info or _cached_info):
                    break
        except TimeoutError:
            logger.warning(f'[{self.platform_id}] {"2" if use_info_fallback else "1"} 链 url 抢答超时')
            pass

        if not url or not url.startswith('http'):
            return None

        # ★ 关键：lyric 抢答 — 传 same_source 让 lyric 链优先用 url 选中的源
        lyric, lyric_src = '', None
        if with_lyric:
            lyric_kwargs = dict(song_id=song_id_str,
                                preferred_source=preferred_source,
                                same_source=url_src or '',
                                cookies=self.cookies)
            try:
                lyric, lyric_src = self.parse_lyric_chain.try_fetch('parse_lyric', **lyric_kwargs)
            except Exception as e:
                logger.warning(f'[{self.platform_id}] lyric 抢答异常: {e}')

        logger.info(
            f'[{self.platform_id}] /song 同源抢答: '
            f'url={url_src} lyric={lyric_src} info={info_src or "cached"} '
            f'耗时={time.time()-t_start:.2f}s'
        )

        # ★ 关键：info 拼接优先级 _cached_info > parse_info_chain
        if _cached_info and _cached_info.get('name'):
            base = normalize_qq_song(_cached_info)
            info_src_name = _cached_info.get('_search_source', 'cached')
        elif info and info.get('name'):
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
            'level': _detect_actual_quality_from_url(url, quality),  # 从 URL 推断实际音质
            'lyric': lyric or '',
            'source': self.platform_id,
            'api_source': {'url': url_src, 'info': info_src_name, 'lyric': lyric_src},
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
