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
        # 临时失败名单：mark_source_failed() 加入，过期自动恢复
        # 场景：下载 4xx 时通知 chain 跳过该源，避免重试仍用同源失败
        self._failed_sources: dict = {}  # {name: expire_timestamp}
        # 成功记忆：mark_source_success() 记录成功时间，过期后回归 priority
        # 场景：vkeys_url 成功下载后，5 分钟内其他歌曲优先用 vkeys_url（直到它失败）
        self._success_recent: dict = {}  # {name: success_at_timestamp}

    def set_source_enabled(self, name: str, enabled: bool) -> bool:
        """动态启用/禁用某个源"""
        for s in self.sources:
            if s.name == name:
                s.enabled = enabled
                return True
        return False

    def mark_source_failed(self, name: str, expire_seconds: int = 300,
                           reason: str = '') -> None:
        """标记 source 临时失败（默认 5 分钟内 try_fetch 自动跳过）

        字段约定（用户定义）：
          self.platform = 4 大 platform（netease/qq/kugou/kuwo）
          name          = source 名称（底层 API 域名，如 'vkeys_url'）

        场景：service.py 下载时遇到 4xx（如 vkeys_url 返的 URL 403），
        通知 chain 这个 source 不可用，避免下次重试仍用同源。

        Args:
            name: 失败的 source 名称
            expire_seconds: 多少秒后自动恢复（默认 5 分钟，QQ 风控通常临时）
            reason: 失败原因（仅用于日志）
        """
        self._failed_sources[name] = time.time() + expire_seconds
        logger.warning(
            f'[{self.platform}] 临时禁用 source {name}（{expire_seconds}s 内 try_fetch 跳过）'
            f' 原因: {reason[:80]}'
        )

    def reset_failed_sources(self) -> None:
        """清空失败名单（通常在 task 启动时调用）"""
        if self._failed_sources:
            logger.info(f'[{self.platform}] 重置失败名单: {list(self._failed_sources.keys())}')
            self._failed_sources.clear()

    def mark_source_success(self, name: str, expire_seconds: int = 86400) -> None:
        """标记 source 最近成功（默认 24 小时内优先使用）

        字段约定（用户定义）：
          self.platform = 4 大 platform（netease/qq/kugou/kuwo）
          name          = source 名称（底层 API 域名，如 'vkeys_url'）

        场景：vkeys_url 成功下载 → 后续 24h 优先用 vkeys_url
              如果 vkeys_url 失败，mark_source_failed 会覆盖
        改为 24h：QQ/酷狗 等平台 API 稳定性以天为单位，
                 source 24h 内不会突然从"能下"变成"不能下"（除非风控）。
        """
        self._success_recent[name] = time.time() + expire_seconds
        logger.info(f'[{self.platform}] source {name} 最近成功（{expire_seconds}s 内优先使用）')

    def _is_source_success_recent(self, name: str) -> bool:
        """检查源是否在成功记忆内（自动清理过期项）"""
        expire_at = self._success_recent.get(name)
        if expire_at is None:
            return False
        if time.time() > expire_at:
            del self._success_recent[name]
            return False
        return True

    def _verify_url_reachable(self, url: str, timeout: int = 5) -> bool:
        """验证 URL 是否可访问（HEAD 探测，HEAD 405 时 fallback Range GET）

        用途：chain 拿到下载 URL 后，立刻验证 URL 是否真能用。
              拿到 URL 不代表能用（CDN 可能 403/404/token 过期），
              验证失败 → mark_source_failed 换源（不浪费真正下载时间）。
        """
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code in (200, 206):
                return True
            if resp.status_code == 405:  # HEAD 不支持
                # Range GET 1KB 探测
                r2 = requests.get(url, headers={'Range': 'bytes=0-1023'},
                                  timeout=timeout, stream=True)
                try:
                    return r2.status_code in (200, 206)
                finally:
                    r2.close()
            return False
        except Exception as e:
            logger.debug(f'[verify_url] {url[:60]}... 验证失败: {type(e).__name__}: {str(e)[:60]}')
            return False

    def _is_source_failed(self, name: str) -> bool:
        """检查源是否在失败名单中（自动清理过期项）"""
        expire_at = self._failed_sources.get(name)
        if expire_at is None:
            return False
        if time.time() > expire_at:
            del self._failed_sources[name]
            logger.info(f'[{self.platform}] 源 {name} 失败名单已过期，自动恢复')
            return False
        return True

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
        """串行：找到第一个成功的源就返回

        关键优化：按 quality 过滤源
        - 如果 source.max_quality 不为空，且 source.max_quality < 用户请求的 quality
        - 则跳过这个源（它永远拿不到目标音质）
        - 例：用户请求 lossless，xunhuisi_url (max_quality=exhigh) 应该跳过
        """
        user_quality = kwargs.get('quality', '')

        # ★ 按成功记忆重排：最近成功的源排前面（24 小时内）
        # 稳定排序：保留 priority 顺序，只把成功过的源前置
        sources = sorted(
            sources,
            key=lambda s: (0 if self._is_source_success_recent(s.name) else 1, s.priority)
        )
        # 调试：打印重排后的顺序
        if any(self._is_source_success_recent(s.name) for s in sources):
            recent = [s.name for s in sources if self._is_source_success_recent(s.name)]
            logger.debug(f'[{self.platform}.{op}] 优先使用最近成功源: {recent}')

        for source in sources:
            # ★ 跳过失败名单（mark_source_failed 标记的源）
            if self._is_source_failed(source.name):
                logger.info(
                    f'[{self.platform}.{op}] 跳过 {source.name}（失败名单中，临时禁用）'
                )
                continue
            # 关键：按 max_quality 过滤
            if source.max_quality and user_quality:
                if _quality_rank(source.max_quality) < _quality_rank(user_quality):
                    logger.info(
                        f'[{self.platform}.{op}] 跳过 {source.name} '
                        f'(max_quality={source.max_quality} < user_quality={user_quality})'
                    )
                    continue
            # ★ 跳过需要 cookie 但 cookie 文件不存在的源
            if source.needs_cookie and source.cookie_file:
                cookies = self._load_cookie(source.cookie_file)
                if not cookies:
                    logger.info(
                        f'[{self.platform}.{op}] 跳过 {source.name} '
                        f'(无 cookie file: {source.cookie_file})'
                    )
                    continue

            logger.info(f'[{self.platform}.{op}] 尝试 {source.name} (P={source.priority})...')
            t0 = time.time()
            try:
                data = self._fetch_one(source, op, **kwargs)
                elapsed_ms = int((time.time() - t0) * 1000)
                if self._is_valid(data, op):
                    # ★ parse_url：拿到 URL 后立刻验证可用性（避免下载时才发现 4xx）
                    if op == 'parse_url' and isinstance(data, str):
                        if not self._verify_url_reachable(data):
                            source._stats['fail'] += 1
                            source._stats['last_error'] = 'URL 验证失败（HEAD/RANGE 4xx/超时）'
                            source._stats['total_ms'] += elapsed_ms
                            # 直接 mark 失败（5 分钟内不再尝试）
                            self._failed_sources[source.name] = time.time() + 300
                            logger.warning(
                                f'[{self.platform}.{op}] ⚠️ {source.name} URL 不可用（已 mark 失败 5 分钟）: {data[:80]}'
                            )
                            continue
                    source._stats['ok'] += 1
                    source._stats['last_used'] = time.time()
                    source._stats['total_ms'] += elapsed_ms
                    url_preview = ''
                    if op == 'parse_url' and isinstance(data, str):
                        url_preview = f' → {data[:80]}'
                    logger.info(
                        f'[{self.platform}.{op}] ✅ {source.name} 成功 ({elapsed_ms}ms){url_preview}'
                    )
                    return data, source.name
                # 拿到数据但无效（如 url 为空）算 fail
                source._stats['fail'] += 1
                source._stats['last_error'] = '数据无效'
                source._stats['total_ms'] += elapsed_ms
                logger.info(
                    f'[{self.platform}.{op}] ⚠️ {source.name} 返空数据 ({elapsed_ms}ms)'
                )
            except Exception as e:
                source._stats['fail'] += 1
                source._stats['last_error'] = f'{type(e).__name__}: {str(e)[:80]}'
                logger.info(f'[{self.platform}.{op}] ❌ {source.name} 失败 ({type(e).__name__}): {str(e)[:80]}')
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
            # 网易云 eapi 端点：先用 AES-ECB 加密 payload，再以 form-encoded "params=..." 发送
            if source.is_eapi:
                encrypted = _eapi_encrypt(url, post_data)
                body = f'params={encrypted}'
                # 强制 form-urlencoded Content-Type
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
            else:
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
        # eapi encodeType: 网易云根据 quality 决定返回 flac 还是 mp3
        if 'quality' in result:
            quality = result['quality']
            if quality in ('lossless', 'hires', 'jymaster', 'jyeffect', 'sky', 'dolby', 'jysurround'):
                result['encode_type'] = 'flac'
            else:
                result['encode_type'] = 'mp3'
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
            if not (isinstance(data, dict) and (data.get('tracks') or data.get('name'))):
                return False
            # 完整性检查：声明的 trackCount 必须 >= 实际返回的 tracks
            # 否则视为被截断（部分平台官方 API 仅返回前 10 首），应回退到下一个源
            try:
                declared = int(data.get('trackCount') or 0)
                actual = len(data.get('tracks') or [])
                if declared > actual:
                    return False
            except (TypeError, ValueError):
                pass
            return True
        return bool(data)

    def _load_cookie(self, cookie_file: str) -> dict:
        """从 cookie 文件加载（netease 专用）

        支持两种格式：
          1. Netscape 7-tab 格式（标准）：
                # Netscape HTTP Cookie File
                domain	flag	path	secure	expiration	name	value
          2. 单行 key=value 格式（Cookie header 风格，用 ; 分隔）：
                _ntes_nnid=xxx; _ntes_nuid=xxx; MUSIC_U=xxx; ...

        候选路径（CWD 启动 vs docker 部署）：
          backend/netease_cookie.txt           ← 相对 CWD
          backend/clients/cookie/...           ← 实际项目结构
          /app/cookie/...                      ← docker 镜像根
          /app/clients/cookie/...              ← docker 镜像源码路径
        """
        from pathlib import Path
        candidates = [
            Path(cookie_file),                                          # CWD 相对
            Path('clients/cookie') / Path(cookie_file).name,            # 项目内 (CWD=backend/)
            Path('backend/clients/cookie') / Path(cookie_file).name,    # 项目内 (CWD=root/)
            Path('/app/cookie') / Path(cookie_file).name,               # docker 根
            Path('/app/clients/cookie') / Path(cookie_file).name,       # docker 源码路径
        ]
        for p in candidates:
            if p.exists():
                try:
                    content = p.read_text(encoding='utf-8', errors='ignore').strip()
                    if not content:
                        continue
                    cookies = {}
                    # 格式探测：是否含 \t → Netscape 格式；否则 → 单行 key=value
                    if '\t' in content:
                        # Netscape 7-tab 格式
                        for line in content.splitlines():
                            if not line.strip() or line.startswith('#'):
                                continue
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                cookies[parts[5]] = parts[6]
                    else:
                        # 单行 key=value 格式（Cookie header 风格，; 分隔）
                        for pair in content.split(';'):
                            pair = pair.strip()
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                cookies[k.strip()] = v.strip()
                    if cookies:
                        logger.info(
                            f'[{self.platform}] 加载 cookie {p}（{len(cookies)} 个字段）'
                        )
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


# ==================== 网易云 eapi 加密 ====================
# 网易云 /eapi/ 端点必须 AES-ECB 加密 body 才能识别。
# 重构时移除了 cryptography 依赖，改用纯 Python 实现。
# 实现参考 NeteaseCloudMusicApi SDK 的 eapi 加密逻辑。

def _eapi_encrypt(url: str, payload: dict) -> str:
    """网易云 eapi 加密

    流程：
      1. url_path = url 路径中的 /eapi/ 替换为 /api/
      2. digest = md5("nobody{url_path}use{json_payload}md5forencrypt") → hex
      3. params = "{url_path}-36cd479b6b5-{json_payload}-36cd479b6b5-{digest}"
      4. AES-128-ECB(PKCS7) 加密 params
      5. 返回 hex(ciphertext)  (前端请求时作为 "params=" 的值)
    """
    import urllib.parse
    from hashlib import md5

    url_path = urllib.parse.urlparse(url).path.replace('/eapi/', '/api/')
    payload_json = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    digest = md5(f'nobody{url_path}use{payload_json}md5forencrypt'.encode('utf-8')).hexdigest()
    params = f'{url_path}-36cd479b6b5-{payload_json}-36cd479b6b5-{digest}'
    ciphertext = _aes_128_ecb_encrypt(params.encode('utf-8'), EAPI_AES_KEY)
    return ciphertext.hex()


# AES-128-ECB 密钥（网易云公开常量）
EAPI_AES_KEY = b'e82ckenh8dichen8'

# AES S-box (256 bytes) 和逆 S-box，纯 Python AES-128 查表实现
_AES_SBOX = [
    0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30, 0x01, 0x67, 0x2b, 0xfe, 0xd7, 0xab, 0x76,
    0xca, 0x82, 0xc9, 0x7d, 0xfa, 0x59, 0x47, 0xf0, 0xad, 0xd4, 0xa2, 0xaf, 0x9c, 0xa4, 0x72, 0xc0,
    0xb7, 0xfd, 0x93, 0x26, 0x36, 0x3f, 0xf7, 0xcc, 0x34, 0xa5, 0xe5, 0xf1, 0x71, 0xd8, 0x31, 0x15,
    0x04, 0xc7, 0x23, 0xc3, 0x18, 0x96, 0x05, 0x9a, 0x07, 0x12, 0x80, 0xe2, 0xeb, 0x27, 0xb2, 0x75,
    0x09, 0x83, 0x2c, 0x1a, 0x1b, 0x6e, 0x5a, 0xa0, 0x52, 0x3b, 0xd6, 0xb3, 0x29, 0xe3, 0x2f, 0x84,
    0x53, 0xd1, 0x00, 0xed, 0x20, 0xfc, 0xb1, 0x5b, 0x6a, 0xcb, 0xbe, 0x39, 0x4a, 0x4c, 0x58, 0xcf,
    0xd0, 0xef, 0xaa, 0xfb, 0x43, 0x4d, 0x33, 0x85, 0x45, 0xf9, 0x02, 0x7f, 0x50, 0x3c, 0x9f, 0xa8,
    0x51, 0xa3, 0x40, 0x8f, 0x92, 0x9d, 0x38, 0xf5, 0xbc, 0xb6, 0xda, 0x21, 0x10, 0xff, 0xf3, 0xd2,
    0xcd, 0x0c, 0x13, 0xec, 0x5f, 0x97, 0x44, 0x17, 0xc4, 0xa7, 0x7e, 0x3d, 0x64, 0x5d, 0x19, 0x73,
    0x60, 0x81, 0x4f, 0xdc, 0x22, 0x2a, 0x90, 0x88, 0x46, 0xee, 0xb8, 0x14, 0xde, 0x5e, 0x0b, 0xdb,
    0xe0, 0x32, 0x3a, 0x0a, 0x49, 0x06, 0x24, 0x5c, 0xc2, 0xd3, 0xac, 0x62, 0x91, 0x95, 0xe4, 0x79,
    0xe7, 0xc8, 0x37, 0x6d, 0x8d, 0xd5, 0x4e, 0xa9, 0x6c, 0x56, 0xf4, 0xea, 0x65, 0x7a, 0xae, 0x08,
    0xba, 0x78, 0x25, 0x2e, 0x1c, 0xa6, 0xb4, 0xc6, 0xe8, 0xdd, 0x74, 0x1f, 0x4b, 0xbd, 0x8b, 0x8a,
    0x70, 0x3e, 0xb5, 0x66, 0x48, 0x03, 0xf6, 0x0e, 0x61, 0x35, 0x57, 0xb9, 0x86, 0xc1, 0x1d, 0x9e,
    0xe1, 0xf8, 0x98, 0x11, 0x69, 0xd9, 0x8e, 0x94, 0x9b, 0x1e, 0x87, 0xe9, 0xce, 0x55, 0x28, 0xdf,
    0x8c, 0xa1, 0x89, 0x0d, 0xbf, 0xe6, 0x42, 0x68, 0x41, 0x99, 0x2d, 0x0f, 0xb0, 0x54, 0xbb, 0x16,
]
_AES_RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]


def _gf_mul(a: int, b: int) -> int:
    """GF(2^8) 乘法"""
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xff
        if hi:
            a ^= 0x1b
        b >>= 1
    return p


def _aes_key_expansion(key: bytes) -> list:
    """AES-128 key expansion: 16 bytes → 11 round keys (176 bytes)"""
    assert len(key) == 16
    w = list(key)
    for i in range(4, 44):
        temp = w[(i - 1) * 4:(i - 1) * 4 + 4]
        if i % 4 == 0:
            # RotWord + SubWord + Rcon
            temp = [_AES_SBOX[temp[1]], _AES_SBOX[temp[2]], _AES_SBOX[temp[3]], _AES_SBOX[temp[0]]]
            temp[0] ^= _AES_RCON[i // 4]
        for j in range(4):
            w.append(w[(i - 4) * 4 + j] ^ temp[j])
    # 切成 11 个 16-byte round keys
    return [bytes(w[i * 16:i * 16 + 16]) for i in range(11)]


def _aes_128_ecb_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-128-ECB 加密（含 PKCS7 padding）
    纯 Python 实现，零外部依赖。约 1ms/16B 块。
    """
    # 1. PKCS7 padding
    pad_len = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad_len] * pad_len)

    # 2. Key expansion
    round_keys = _aes_key_expansion(key)

    # 3. 块加密
    out = bytearray()
    for i in range(0, len(padded), 16):
        block = list(padded[i:i + 16])
        # AddRoundKey (round 0)
        block = [b ^ k for b, k in zip(block, round_keys[0])]
        # 9 main rounds
        for r in range(1, 10):
            # SubBytes
            block = [_AES_SBOX[b] for b in block]
            # ShiftRows
            block = [
                block[0], block[5], block[10], block[15],
                block[4], block[9], block[14], block[3],
                block[8], block[13], block[2], block[7],
                block[12], block[1], block[6], block[11],
            ]
            # MixColumns
            new_block = []
            for c in range(4):
                col = block[c * 4:c * 4 + 4]
                new_block.extend([
                    _gf_mul(col[0], 2) ^ _gf_mul(col[1], 3) ^ col[2] ^ col[3],
                    col[0] ^ _gf_mul(col[1], 2) ^ _gf_mul(col[2], 3) ^ col[3],
                    col[0] ^ col[1] ^ _gf_mul(col[2], 2) ^ _gf_mul(col[3], 3),
                    _gf_mul(col[0], 3) ^ col[1] ^ col[2] ^ _gf_mul(col[3], 2),
                ])
            block = new_block
            # AddRoundKey
            block = [b ^ k for b, k in zip(block, round_keys[r])]
        # Final round (no MixColumns)
        block = [_AES_SBOX[b] for b in block]
        block = [
            block[0], block[5], block[10], block[15],
            block[4], block[9], block[14], block[3],
            block[8], block[13], block[2], block[7],
            block[12], block[1], block[6], block[11],
        ]
        block = [b ^ k for b, k in zip(block, round_keys[10])]
        out.extend(bytes(b & 0xff for b in block))
    return bytes(out)


# 音质等级从高到低排序（数字越大等级越高）
# 用于 max_quality 过滤：source.max_quality < user_quality 时跳过源
_QUALITY_RANK = {
    'standard': 0,
    'exhigh': 1,
    'lossless': 2,
    'hires': 3,
    'sky': 4,
    'jyeffect': 4,
    'jymaster': 5,
    'dolby': 6,
}


def _quality_rank(quality: str) -> int:
    """获取音质的等级（数字越大音质越高），未知名为 -1"""
    return _QUALITY_RANK.get(quality, -1)
