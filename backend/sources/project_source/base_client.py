"""音乐客户端抽象基类

定义所有音乐平台客户端必须实现的接口规范。

设计原则：
  - 方法粒度对齐"用户场景"（search / get_song），不沿用上游 API 路径
  - 失败用显式 Optional/None 表达，不靠"空字符串字段"隐式表达
  - search 永远只搜歌曲（不分歌单），URL 解析另走 _resolve_from_url
"""
import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

import requests

from .quality_config import get_default_quality, is_valid_quality

logger = logging.getLogger(__name__)


class BaseMusicClient(ABC):
    """音乐客户端抽象基类"""

    def __init__(self, cookie_file: str = ''):
        self.session = requests.Session()
        self.platform_name = "base"
        self.platform_id = "base"
        self.cookie_file = cookie_file
        self.cookies = self._load_cookie()

    def _load_cookie(self) -> dict:
        """从 cookie 文件加载，结果缓存在 self.cookies 中（仅初始化时读一次文件）"""
        if not self.cookie_file:
            return {}
        from pathlib import Path
        candidates = [
            Path(self.cookie_file),
            Path('clients/cookie') / Path(self.cookie_file).name,
            Path('backend/clients/cookie') / Path(self.cookie_file).name,
            Path('/app/cookie') / Path(self.cookie_file).name,
            Path('/app/clients/cookie') / Path(self.cookie_file).name,
        ]
        for p in candidates:
            if p.exists():
                try:
                    content = p.read_text(encoding='utf-8', errors='ignore').strip()
                    if not content:
                        continue
                    cookies = {}
                    if '\t' in content:
                        for line in content.splitlines():
                            if not line.strip() or line.startswith('#'):
                                continue
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                cookies[parts[5]] = parts[6]
                    else:
                        for pair in content.split(';'):
                            pair = pair.strip()
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                cookies[k.strip()] = v.strip()
                    if cookies:
                        import logging
                        logging.getLogger(__name__).info(
                            f'[{self.platform_id}] 加载 cookie {p}（{len(cookies)} 个字段）'
                        )
                        return cookies
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).debug(f'加载 cookie 失败 {p}: {e}')
                break
        return {}

    @abstractmethod
    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """搜索歌曲

        Returns:
            {
                'data': [{'id', 'name', 'artists', 'album', 'picUrl', 'duration',
                          'source', 'api_source'}, ...],
                'search_source': str,   # 命中的源名（None 表示完全失败）
                'warnings': list,       # 警告信息
            }
        """
        pass

    @abstractmethod
    def get_song(self, song_id: Any, quality: str = 'lossless',
                 with_lyric: bool = True) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息：元信息 + 播放 URL + (可选) 歌词

        Returns:
            None 表示完全失败
            成功时至少包含 {'id', 'url', 'source', 'quality', 'api_source'}，
            失败的部分字段可能为 ''（歌词等可选字段）
        """
        pass

    def get_health(self) -> dict:
        """获取客户端健康状态（子类可覆盖）"""
        return {}

    @staticmethod
    def _normalize_quality(quality: str) -> str:
        """音质归一化（无效时回退到 lossless）"""
        return quality if is_valid_quality(quality) else get_default_quality()

    # ==================== 通用模板方法（重构：消除各平台 get_song 重复代码） ====================

    def _process_base_info(self, cached_info: Optional[dict], info: Optional[dict],
                           info_src: Optional[str], song_id_str: str,
                           normalize_func: Callable) -> tuple:
        """处理基础信息的优先级逻辑（共享给各平台客户端）

        优先级：cached_info > parse_info_chain > 空字典

        Args:
            cached_info: 来自 search 阶段的 song_info_cache（优先使用）
            info: 来自 parse_info_chain 的兜底结果
            info_src: info 的来源名
            song_id_str: 字符串化的 song id
            normalize_func: 平台特定的 normalize 函数

        Returns:
            (base_dict, info_src_name)
        """
        if cached_info and cached_info.get('name'):
            base = normalize_func(cached_info)
            info_src_name = cached_info.get('_search_source', 'cached')
        elif info and info.get('name'):
            base = normalize_func(info)
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
        return base, info_src_name

    def _build_info_params(self, song_id_str: str, preferred_source: str) -> dict:
        """构造 info_chain 参数（子类可覆盖以适配不同参数名）

        默认使用 song_id 参数；酷狗使用 hash，酷我使用 rid
        """
        return {'song_id': song_id_str, 'preferred_source': preferred_source}

    def _get_song_template(self, *, song_id: Any, quality: str, with_lyric: bool,
                           preferred_source: str, quality_map: Optional[dict],
                           _cached_info: Optional[dict],
                           url_chain, lyric_chain, info_chain=None,
                           normalize_func: Callable,
                           url_params_builder: Callable,
                           lyric_params_builder: Optional[Callable] = None,
                           url_deadline_seconds: float = 5.0) -> Optional[Dict[str, Any]]:
        """通用的歌曲信息获取模板方法（并行抢答模式）

        封装共享逻辑：
          1. 音质归一化
          2. URL + Info 并行抢答（cached_info 缺失时启用 info_chain 兜底）
          3. 抢答超时控制
          4. Lyric 抢答（带 same_source 同源优先）
          5. cached_info 优先级处理
          6. 标准化日志输出
          7. 标准化返回值构造

        Args:
            song_id: 歌曲 ID
            quality: 音质
            with_lyric: 是否获取歌词
            preferred_source: 来自 search 的源名
            quality_map: 该歌曲可用音质字典
            _cached_info: search 阶段缓存的完整 song info
            url_chain: URL 获取链
            lyric_chain: 歌词获取链
            info_chain: 元信息获取链（_cached_info 缺失时启用兜底）
            normalize_func: 平台特定的 normalize 函数
            url_params_builder: URL 参数构造函数 (song_id_str, quality, preferred_source, quality_map) -> dict
            lyric_params_builder: Lyric 参数构造函数 (song_id_str, preferred_source, url_src) -> dict
            url_deadline_seconds: URL 抢答硬切超时（秒）

        Returns:
            标准化的歌曲信息字典
        """
        quality = self._normalize_quality(quality)
        song_id_str = str(song_id)

        # 构造 URL 参数（平台特定）
        url_kwargs = url_params_builder(song_id_str, quality, preferred_source, quality_map)

        t_start = time.time()
        use_info_fallback = not _cached_info and info_chain is not None
        max_workers = 2 if use_info_fallback else 1
        pool = ThreadPoolExecutor(max_workers=max_workers)

        # 并行提交 URL + Info 抢答
        f_url = pool.submit(url_chain.try_fetch, 'parse_url', cookies=self.cookies, **url_kwargs)
        f_info = None
        if use_info_fallback:
            info_kwargs = self._build_info_params(song_id_str, preferred_source)
            f_info = pool.submit(info_chain.try_fetch, 'parse_info', **info_kwargs)

        pool.shutdown(wait=False)

        # 收集结果
        url, url_src = '', None
        info, info_src = None, None
        deadline = t_start + url_deadline_seconds
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
                # URL 拿到且 (info 也拿到 或 cached_info 存在) 就退出
                if url and url.startswith('http') and (info or _cached_info):
                    break
        except TimeoutError:
            logger.warning(
                f'[{self.platform_id}] {"2" if use_info_fallback else "1"} 链 url 抢答超时'
            )

        if not url or not url.startswith('http'):
            # ★ 失败时也返回带 api_source 的 dict，让上层能给用户具体的错误信息
            # 不返回 None（避免 chain 内部 _is_valid 把 api_source 误丢弃）
            return {
                'url': None,
                'level': quality,
                'lyric': '',
                'source': self.platform_id,
                'api_source': {'url': url_src, 'info': None, 'lyric': None},
                '_last_attempt_source': url_src,  # ★ 方便上层定位失败的源
            }

        # Lyric 抢答（带 same_source 同源优先）
        lyric, lyric_src = '', None
        if with_lyric and lyric_chain:
            if lyric_params_builder:
                lyric_kwargs = lyric_params_builder(song_id_str, preferred_source, url_src)
            else:
                lyric_kwargs = {'song_id': song_id_str, 'preferred_source': preferred_source}
            # 同源优先 + cookie 注入
            lyric_kwargs.update({
                'same_source': url_src or '',
                'cookies': self.cookies,
            })
            try:
                lyric, lyric_src = lyric_chain.try_fetch('parse_lyric', **lyric_kwargs)
            except Exception as e:
                logger.warning(f'[{self.platform_id}] lyric 抢答异常: {e}')

        # 基础信息优先级处理（cached > info > 空）
        base, info_src_name = self._process_base_info(
            _cached_info, info, info_src, song_id_str, normalize_func
        )

        # 统一日志格式
        logger.info(
            f'[{self.platform_id}] /song 同源抢答: '
            f'url={url_src} lyric={lyric_src} info={info_src_name} '
            f'耗时={time.time()-t_start:.2f}s'
        )

        # 标准化返回值
        return {
            **base,
            'url': url,
            'level': quality,
            'lyric': lyric or '',
            'source': self.platform_id,
            'api_source': {'url': url_src, 'info': info_src_name, 'lyric': lyric_src},
        }

    def close(self):
        """关闭 session"""
        try:
            self.session.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
