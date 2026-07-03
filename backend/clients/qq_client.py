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


class QQClient(BaseMusicClient):
    """QQ 音乐客户端 - 数据驱动版"""

    def __init__(self):
        super().__init__()
        self.platform_id = 'qq'
        self.platform_name = 'QQ音乐'
        self.search_chain = FallbackChain(QQ_SEARCH_SOURCES, platform='qq', strategy='parallel')
        self.parse_url_chain = FallbackChain(QQ_PARSE_URL_SOURCES, platform='qq', strategy='parallel_first')
        self.parse_info_chain = FallbackChain(QQ_PARSE_INFO_SOURCES, platform='qq', strategy='parallel_first')
        self.parse_lyric_chain = FallbackChain(QQ_PARSE_LYRIC_SOURCES, platform='qq', strategy='parallel_first')
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

        实现策略：URL/Lyric 双链并行抢答（parse_info 仅兜底用）

        跨源一致性策略：
        - 若传入了 _cached_info（来自 search 阶段 song_info_cache），
          **直接使用**作为 name/artist/album/cover/duration，
          不再抢答 parse_info_chain（避免 url/info 跨源不一致）
        - 若 _cached_info 缺失（URL 解析/歌单导入等无 search 上下文），
          回退到 parse_info_chain 兜底拿 info

        Args:
            preferred_source: 来自 search 链的源名（如 'qq_official_search'），
                传下去给 url/lyric 链优先使用（避免跨源不一致）
            quality_map: 该歌曲可用音质字典（来自 search result），
                用于 URL 链 size 验证
            _cached_info: search 阶段缓存的完整 song info
        """
        quality = self._normalize_quality(quality)
        song_id_str = str(song_id)
        # 透传给 try_fetch（chain 内部按 preferred_source 排序）
        url_kwargs = dict(song_id=song_id_str, quality=quality,
                          preferred_source=preferred_source, quality_map=quality_map or {})
        lyric_kwargs = dict(song_id=song_id_str,
                            preferred_source=preferred_source)

        # ★ 关键：用 shutdown(wait=False) 替代 `with ThreadPoolExecutor`
        t_start = time.time()
        use_info_fallback = not _cached_info
        max_workers = 3 if use_info_fallback else 2
        pool = ThreadPoolExecutor(max_workers=max_workers)
        f_url = pool.submit(self.parse_url_chain.try_fetch, 'parse_url', **url_kwargs)
        f_info = (pool.submit(self.parse_info_chain.try_fetch, 'parse_info',
                              song_id=song_id_str, preferred_source=preferred_source)
                  if use_info_fallback else None)
        f_lyric = (pool.submit(self.parse_lyric_chain.try_fetch, 'parse_lyric',
                               **lyric_kwargs) if with_lyric else None)
        # shutdown(wait=False) 不阻塞主线程，让新 future 还能继续跑
        pool.shutdown(wait=False)

        # 用 as_completed 按需取结果，每条链最多等 max_chain_seconds (6s)
        # URL 是关键 → 优先等 url（但同时让 info/lyric 也跑）
        url, url_src = '', None
        info, info_src = None, None
        lyric, lyric_src = '', None
        deadline = t_start + 6.5  # 留 1.5s 余量给 JSON 解析等
        futures = [f for f in (f_url, f_info, f_lyric) if f is not None]
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
                elif fut is f_lyric:
                    lyric, lyric_src = data, src
                # URL 拿到就退出循环（其他链后台继续跑）
                if url and url.startswith('http'):
                    break
        except TimeoutError:
            logger.warning(f'[{self.platform_id}] {"3" if use_info_fallback else "2"} 链并行抢答超时')
            pass

        logger.info(
            f'[{self.platform_id}] /song {"3" if use_info_fallback else "2"} 链抢答完成: '
            f'url={url_src} info={info_src or "cached"} lyric={lyric_src} '
            f'耗时={time.time()-t_start:.2f}s'
        )

        if not url or not url.startswith('http'):
            return None

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
