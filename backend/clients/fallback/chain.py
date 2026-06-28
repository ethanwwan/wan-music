"""FallbackChain：串行/并行 fallback 引擎

核心思想（参考 musicdl）：
  - 每个 ApiSource 都是一个能力声明
  - 客户端只关心「搜索」「拿 URL」「拿元信息」三件事
  - 框架按 priority 排序所有启用的源，依次尝试直到成功

两种模式：
  - serial: 顺序尝试，取第一个成功的源（用于 parse_url，因为只需要一个 URL）
  - parallel: 并行请求多个源，结果去重合并（用于 search，结果越多越好）

统计：
  - 每个源的成功/失败次数
  - 最后一次失败的错误信息
  - 通过 health() 暴露给前端做监控
"""
import json
import time
import logging
import requests
from typing import List, Optional, Any, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from .api_source import ApiSource
from .extractors import quality_to_br

logger = logging.getLogger(__name__)


class FallbackChain:
    """一组 ApiSource 的迭代器

    用法：
        chain = FallbackChain([source1, source2, source3])
        url, source_name = chain.try_fetch('parse_url', song_id='123', quality='lossless')
    """

    def __init__(self, sources: List[ApiSource], platform: str = '', strategy: str = 'serial',
                 max_workers: int = 4, request_timeout_default: int = 10):
        self.platform = platform
        self.strategy = strategy  # 'serial' | 'parallel'
        self.max_workers = max_workers
        self.request_timeout_default = request_timeout_default
        # 按 priority 排序
        self.sources = sorted([s for s in sources if s.platform == platform or platform == ''],
                              key=lambda s: s.priority)
        # 共享的 session（连接复用）
        self._session = requests.Session()
        # 统计
        self._stats = defaultdict(lambda: {'ok': 0, 'fail': 0, 'last_error': '', 'last_used': 0, 'total_ms': 0})

    def set_source_enabled(self, name: str, enabled: bool) -> bool:
        """动态启用/禁用某个源"""
        for s in self.sources:
            if s.name == name:
                s.enabled = enabled
                return True
        return False

    def get_health(self) -> dict:
        """获取所有源的健康状态"""
        return {s.name: dict(s._stats) | {'enabled': s.enabled, 'priority': s.priority}
                for s in self.sources}

    def try_fetch(self, op: str, **kwargs) -> Tuple[Any, Optional[str]]:
        """统一入口：尝试执行某个操作

        Args:
            op: 'search' | 'parse_url' | 'parse_info' | 'parse_lyric'
            **kwargs: 替换 URL 模板中的占位符，如 song_id='123', quality='lossless'

        Returns:
            (data, source_name) 或 (None/empty_default, None)
        """
        # 过滤出支持该 op 的源
        candidates = [s for s in self.sources if s.supports(op)]
        if not candidates:
            logger.debug(f'[{self.platform}.{op}] 无可用源')
            return _default_for_op(op), None

        if self.strategy == 'parallel' and op == 'search':
            return self._try_parallel(candidates, op, **kwargs)
        return self._try_serial(candidates, op, **kwargs)

    def _try_serial(self, sources: List[ApiSource], op: str, **kwargs) -> Tuple[Any, Optional[str]]:
        """串行：找到第一个成功的源就返回"""
        for source in sources:
            t0 = time.time()
            try:
                data = self._fetch_one(source, op, **kwargs)
                elapsed_ms = int((time.time() - t0) * 1000)
                if self._is_valid(data, op):
                    source._stats['ok'] += 1
                    source._stats['last_used'] = time.time()
                    source._stats['total_ms'] += elapsed_ms
                    return data, source.name
                # 拿到数据但无效（如 url 为空）算 fail
                source._stats['fail'] += 1
                source._stats['last_error'] = '数据无效'
                source._stats['total_ms'] += elapsed_ms
            except Exception as e:
                source._stats['fail'] += 1
                source._stats['last_error'] = f'{type(e).__name__}: {str(e)[:80]}'
                logger.debug(f'[{source.name}.{op}] 失败: {e}')
        return _default_for_op(op), None

    def _try_parallel(self, sources: List[ApiSource], op: str, **kwargs) -> Tuple[Any, Optional[str]]:
        """并行：所有源同时请求，结果去重合并（仅用于 search）"""
        all_results: List[dict] = []
        first_source: Optional[str] = None
        seen_ids: set = set()
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._fetch_one, s, op, **kwargs): s for s in sources}
            for fut in as_completed(futures):
                source = futures[fut]
                try:
                    data = fut.result()
                except Exception as e:
                    source._stats['fail'] += 1
                    source._stats['last_error'] = str(e)[:80]
                    continue
                if not self._is_valid(data, op):
                    source._stats['fail'] += 1
                    continue
                source._stats['ok'] += 1
                source._stats['last_used'] = time.time()
                if first_source is None:
                    first_source = source.name
                # 合并去重（按 id）
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item_id = str(
                                item.get('id')
                                or item.get('rid')
                                or item.get('mid')
                                or item.get('FileHash')
                                or item.get('hash')
                                or item.get('MUSICRID')
                                or item.get('musicrid')
                                or ''
                            ).removeprefix('MUSIC_')
                            if item_id and item_id not in seen_ids:
                                seen_ids.add(item_id)
                                item['_source'] = source.name
                                all_results.append(item)
                            elif not item_id:
                                # 没有 ID 字段也保留（如搜索结果只有 hash）
                                item['_source'] = source.name
                                all_results.append(item)
                else:
                    all_results.append(data)
        return all_results, first_source

    def _fetch_one(self, source: ApiSource, op: str, **kwargs) -> Any:
        """执行单次 API 调用"""
        url_template = source.get_url(op)
        if not url_template:
            raise ValueError(f'源 {source.name} 未配置 {op} URL')

        # 填充占位符
        resolved = self._resolve_placeholders(source, op, kwargs)
        url = url_template.format(**resolved)
        # 一些 URL 模板中含有 __br__ 等特殊占位符
        url = url.replace('{{', '{').replace('}}', '}')

        # 拼接 headers
        headers = dict(source.headers)
        # 默认 UA
        headers.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')

        # Cookie（如需要）
        cookies = None
        if source.needs_cookie and source.cookie_file:
            cookies = self._load_cookie(source.cookie_file)

        # POST 数据（支持占位符替换）
        post_data = source.post_data
        if post_data:
            # 替换占位符
            post_data = self._format_post_data(post_data, resolved)

        # 高级：有状态请求准备器（动态签名、token、devid 等）
        if source.prepare_request is not None:
            prepared = source.prepare_request(
                url=url, method=source.method, headers=headers,
                post_data=post_data, is_json=source.is_json, kwargs=resolved,
            )
            if prepared:
                url = prepared.get('url', url)
                method = prepared.get('method', source.method)
                headers = prepared.get('headers', headers)
                post_data = prepared.get('post_data', post_data)
                is_json = prepared.get('is_json', source.is_json)
            else:
                method = source.method
                is_json = source.is_json
        else:
            method = source.method
            is_json = source.is_json

        # 发起请求
        if method.upper() == 'POST':
            body = json.dumps(post_data) if is_json else post_data
            r = self._session.post(url, data=body, headers=headers, cookies=cookies,
                                   timeout=source.timeout or self.request_timeout_default)
        else:
            r = self._session.get(url, headers=headers, cookies=cookies,
                                  timeout=source.timeout or self.request_timeout_default)

        # 解析
        if r.status_code >= 400:
            raise RuntimeError(f'HTTP {r.status_code}')

        # 尝试 JSON
        try:
            d = r.json()
        except Exception:
            # 非 JSON（如纯文本 URL）
            d = {'_text': r.text.strip()}

        # 提取（同时支持 (d) 和 (d, **kwargs) 两种签名）
        extractor = source.get_extractor(op)
        if extractor is None:
            return d  # 原始数据
        try:
            return extractor(d, **resolved) if callable(extractor) else d
        except TypeError:
            # 提取器只接受 (d) 一个参数
            return extractor(d) if callable(extractor) else d

    def _format_post_data(self, post_data, resolved: dict):
        """对 post_data 中的字符串值做占位符替换

        支持 dict / str / 其他类型
        """
        if isinstance(post_data, dict):
            return {k: self._format_post_data(v, resolved) for k, v in post_data.items()}
        if isinstance(post_data, str):
            try:
                return post_data.format(**resolved)
            except (KeyError, IndexError):
                return post_data
        return post_data

    def _resolve_placeholders(self, source: ApiSource, op: str, kwargs: dict) -> dict:
        """构造 URL 模板替换字典"""
        result = dict(kwargs)
        # 质量转 bitrate
        if 'quality' in result and '__br__' in source.get_url(op):
            result['__br__'] = quality_to_br(result['quality'])
        # URL 编码
        if 'keyword' in result and isinstance(result['keyword'], str):
            from .extractors import url_quote
            result['keyword_encoded'] = url_quote(result['keyword'])
        return result

    def _is_valid(self, data: Any, op: str) -> bool:
        """验证返回数据是否有效"""
        if data is None:
            return False
        if op == 'parse_url':
            return isinstance(data, str) and data.startswith('http')
        if op == 'search':
            return isinstance(data, list) and len(data) > 0
        if op == 'parse_info':
            return isinstance(data, dict) and bool(data.get('name') or data.get('id'))
        if op == 'parse_lyric':
            return isinstance(data, str) and len(data.strip()) > 0
        if op == 'parse_playlist':
            return isinstance(data, dict) and bool(data.get('tracks') or data.get('name'))
        return bool(data)

    def _load_cookie(self, cookie_file: str) -> dict:
        """从 cookie 文件加载（netease 专用）"""
        from pathlib import Path
        # 候选路径
        candidates = [
            Path(cookie_file),
            Path('/app/cookie') / Path(cookie_file).name,
            Path('/app/clients/cookie') / Path(cookie_file).name,
        ]
        for p in candidates:
            if p.exists():
                try:
                    lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
                    cookies = {}
                    for line in lines:
                        if not line.strip() or line.startswith('#'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            cookies[parts[5]] = parts[6]
                    return cookies
                except Exception as e:
                    logger.debug(f'加载 cookie 失败 {p}: {e}')
        return {}


def _default_for_op(op: str):
    """操作失败时返回的默认值"""
    if op == 'search':
        return []
    if op == 'parse_url':
        return ''
    if op == 'parse_info':
        return {}
    if op == 'parse_lyric':
        return ''
    return None
