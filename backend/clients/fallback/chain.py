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
                 max_workers: int = 4, request_timeout_default: int = 10,
                 max_chain_seconds: float = 6.0):
        """
        Args:
            max_chain_seconds: 整条链的最大执行时间（秒），超过立即返回
                - 0 或负数表示不限制
                - 设为 6 是经验值：留 2s 给前端 8s timeout 内的网络/JSON 解析开销
                - 配合前端 DEFAULT_TIMEOUT_MS=8s，避免 ERR_EMPTY_RESPONSE
        """
        self.platform = platform
        self.strategy = strategy  # 'serial' | 'parallel'
        self.max_workers = max_workers
        self.request_timeout_default = request_timeout_default
        self.max_chain_seconds = max_chain_seconds
        # 按 priority 排序
        self.sources = sorted([s for s in sources if s.platform == platform or platform == ''],
                              key=lambda s: s.priority)
        # 共享的 session（连接复用）
        self._session = requests.Session()
        # 统计
        self._stats = defaultdict(lambda: {'ok': 0, 'fail': 0, 'last_error': '', 'last_used': 0, 'total_ms': 0})
        # ============ 失败名单：两段式设计 ============
        # 1. 全局 transient 失败（per-source，服务端临时故障如 5xx/timeout）
        #    旧设计用 _failed_sources，5 分钟内其他歌曲也跳过同一源。
        #    改造后只用于真正"服务不可用"的场景，TTL 短（60-120s）。
        self._global_failed: dict = {}  # {name: expire_timestamp}
        # 2. Per-rid permanent 失败（per-source + song_id，这首歌没数据）
        #    例：江南在 kuwo_official_lyric 返空（无版权）→ 只对江南跳过该源，
        #    不影响晴天/十年等其他 rid。这是旧设计缺失的关键能力。
        #    容量上限 _max_per_rid_cache 防内存爆。
        self._per_rid_failed: dict = {}  # {(name, song_id): expire_timestamp}
        self._max_per_rid_cache = 1000
        # 3. 死 URL 列表（per-URL，URL HEAD 验证失败时记录）
        #    旧设计把"URL 404"算作"源失败"，会误伤其他 URL。
        #    现在只死该 URL，TTL 5min。
        self._url_dead: dict = {}  # {url: expire_timestamp}
        # ============================================
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
                           reason: str = '', song_id: str = None,
                           scope: str = 'auto') -> None:
        """标记 source 临时失败

        字段约定（用户定义）：
          self.platform = 4 大 platform（netease/qq/kugou/kuwo）
          name          = source 名称（底层 API 域名，如 'vkeys_url'）

        两段式设计：
          scope='transient'  → 写入 _global_failed（per-source）
                              用于 5xx/timeout/网络错误等"服务端临时故障"
                              默认 TTL 120s（兼容旧行为 expire_seconds=300）
          scope='permanent'  → 写入 _per_rid_failed（per-source + song_id）
                              用于 4xx/empty/parse_error 等"这首歌该源没数据"
                              默认 TTL 1800s（30 分钟）
                              必须传 song_id 才生效
          scope='auto'       → 根据 reason 字符串自动分类（向后兼容默认）
                              含 'timeout'/'connect'/'5' 等关键词 → transient
                              其他 → permanent（需 song_id，否则降级 transient）

        旧调用方式（service.py 仍按此调用）默认 scope='auto' 走老逻辑：
          - expire_seconds=300 仍按 5 分钟兜底
          - 不传 song_id 时按 transient 处理（避免 per-rid 升级为全局时反而更宽松）
        """
        # 自动分类
        if scope == 'auto':
            r = (reason or '').lower()
            if any(k in r for k in ('timeout', 'timed out', 'connect', 'connection', '5xx', '5', 'proxy')):
                scope = 'transient'
            else:
                scope = 'permanent' if song_id else 'transient'

        if scope == 'transient':
            ttl = expire_seconds
            self._global_failed[name] = time.time() + ttl
            logger.warning(
                f'[{self.platform}] 全局禁用 source {name}（{ttl}s 内所有 song 都跳过）'
                f' 原因: {reason[:80]}'
            )
        elif scope == 'permanent':
            if not song_id:
                # 没传 song_id 时降级为 transient（保证旧调用不破坏）
                ttl = expire_seconds
                self._global_failed[name] = time.time() + ttl
                logger.warning(
                    f'[{self.platform}] permanent 失败未传 song_id，降级为全局 {ttl}s: {name}'
                )
                return
            ttl = expire_seconds
            key = (name, str(song_id))
            self._per_rid_failed[key] = time.time() + ttl
            # LRU 容量控制
            if len(self._per_rid_failed) > self._max_per_rid_cache:
                # 删除最旧的 20%
                n_drop = len(self._per_rid_failed) // 5 or 1
                oldest = sorted(self._per_rid_failed.items(), key=lambda x: x[1])[:n_drop]
                for k, _ in oldest:
                    del self._per_rid_failed[k]
                logger.debug(f'[{self.platform}] per-rid 失败缓存满，清理 {n_drop} 条')
            logger.info(
                f'[{self.platform}] per-rid 禁用 {name}（{song_id}）（{ttl}s 内跳过该 song）'
                f' 原因: {reason[:80]}'
            )
        else:
            raise ValueError(f'mark_source_failed: unknown scope={scope!r}')

    def mark_url_dead(self, url: str, source_name: str = '',
                      expire_seconds: int = 300) -> None:
        """标记某个 URL 不可用（5min 内同 URL 跳过）

        场景：parse_url 拿到 URL 后 HEAD 验证 4xx/超时 → 标记该 URL 死，
        避免下次同 URL 再次触发 HEAD 探测浪费 5s 超时。
        不会影响该 source 对其他 song 的工作（与旧 mark_source_failed 关键区别）。
        """
        self._url_dead[url] = time.time() + expire_seconds
        logger.debug(
            f'[{self.platform}] 标记死 URL ({source_name}, {expire_seconds}s): {url[:80]}'
        )

    def _is_url_dead(self, url: str) -> bool:
        """检查 URL 是否在死链列表中（自动清理过期项）"""
        expire_at = self._url_dead.get(url)
        if expire_at is None:
            return False
        if time.time() > expire_at:
            del self._url_dead[url]
            return False
        return True

    def reset_failed_sources(self) -> None:
        """清空失败名单（通常在 task 启动时调用）"""
        items = list(self._global_failed.keys())
        per_rid_count = len(self._per_rid_failed)
        url_count = len(self._url_dead)
        if items or per_rid_count or url_count:
            logger.info(
                f'[{self.platform}] 重置失败名单: global={items}, '
                f'per_rid={per_rid_count}, url_dead={url_count}'
            )
        self._global_failed.clear()
        self._per_rid_failed.clear()
        self._url_dead.clear()

    def mark_source_success(self, name: str, expire_seconds: int = 86400,
                            song_id: str = None) -> None:
        """标记 source 最近成功（默认 24 小时内优先使用）

        字段约定（用户定义）：
          self.platform = 4 大 platform（netease/qq/kugou/kuwo）
          name          = source 名称（底层 API 域名，如 'vkeys_url'）

        场景：vkeys_url 成功下载 → 后续 24h 优先用 vkeys_url
              如果 vkeys_url 失败，mark_source_failed 会覆盖
        改为 24h：QQ/酷狗 等平台 API 稳定性以天为单位，
                 source 24h 内不会突然从"能下"变成"不能下"（除非风控）。

        顺带：清掉 per-rid 中关于该 source 的失败记录，
              因为这个 source 现在能成功 → 之前 per-rid 标记的失败应该失效。
              （避免"江南失败后晴天明明成功还用不了"的脏状态）
        """
        self._success_recent[name] = time.time() + expire_seconds
        # 清掉该 source 在 per-rid 中的所有失败记录
        # 一次成功的请求说明该源整体可用
        before = len(self._per_rid_failed)
        self._per_rid_failed = {
            k: v for k, v in self._per_rid_failed.items() if k[0] != name
        }
        cleared = before - len(self._per_rid_failed)
        if cleared:
            logger.debug(
                f'[{self.platform}] source {name} 成功，顺带清掉 {cleared} 条 per-rid 失败'
            )
        # 同时清掉全局（如果它在失败名单里被 mark 过）
        if name in self._global_failed:
            del self._global_failed[name]
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

    def _verify_url_reachable(self, url: str, timeout: int = 5,
                              expected_min_size: int = 0) -> bool:
        """验证 URL 是否可访问（HEAD 探测，HEAD 405 时 fallback Range GET）

        用途：chain 拿到下载 URL 后，立刻验证 URL 是否真能用。
              拿到 URL 不代表能用（CDN 可能 403/404/token 过期），
              验证失败 → mark_source_failed 换源（不浪费真正下载时间）。

        Args:
            url: 待验证的 URL
            timeout: 超时秒数
            expected_min_size: 预期最小字节数（来自 qualityMap），0 表示不检查
                - 用于发现"用低码率顶替高码率"的情况
                - 例：qualityMap 说 FLAC=50MB，HEAD 返回 Content-Length=5MB → 验证失败
                - 容差：实际 ≥ 预期 × 0.5 才认为合理（CDN 偶发不准）
        """
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code in (200, 206):
                # ★ size check：避免小源顶替大源（不同 CDN 给的资源 bitrate 不一样）
                if expected_min_size > 0:
                    cl = int(resp.headers.get('Content-Length', 0) or 0)
                    if cl > 0 and cl < expected_min_size * 0.5:
                        logger.debug(
                            f'[verify_url] {url[:60]}... size 不匹配: '
                            f'cl={cl} < expected={expected_min_size}×0.5'
                        )
                        return False
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

    def _is_source_failed(self, name: str, song_id: str = None) -> bool:
        """检查源是否在失败名单中（自动清理过期项）

        两段式检查：
          1. _global_failed：per-source，所有 song 都被跳过
          2. _per_rid_failed：per-(source, song_id)，只跳过该 song

        Args:
            name: source 名
            song_id: 当前 song 的 ID（可选；不传则只检查全局）
        """
        # 1. 全局检查（任何原因导致的"服务不可用"）
        expire_at = self._global_failed.get(name)
        if expire_at is not None:
            if time.time() > expire_at:
                del self._global_failed[name]
                logger.info(f'[{self.platform}] 源 {name} 全局失败名单已过期，自动恢复')
            else:
                return True
        # 2. Per-rid 检查（这首歌该源没数据）
        if song_id:
            key = (name, str(song_id))
            expire_at = self._per_rid_failed.get(key)
            if expire_at is not None:
                if time.time() > expire_at:
                    del self._per_rid_failed[key]
                    logger.debug(f'[{self.platform}] 源 {name}({song_id}) per-rid 失败已过期')
                else:
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
        if self.strategy == 'parallel_first':
            # 并行首胜：所有源同时跑，第一个成功的返回
            return self._try_parallel_first(candidates, op, **kwargs)
        return self._try_serial(candidates, op, **kwargs)

    def _try_serial(self, sources: List[ApiSource], op: str, **kwargs) -> Tuple[Any, Optional[str]]:
        """串行：找到第一个成功的源就返回

        关键优化：按 quality 过滤源
        - 如果 source.max_quality 不为空，且 source.max_quality < 用户请求的 quality
        - 则跳过这个源（它永远拿不到目标音质）
        - 例：用户请求 lossless，xunhuisi_url (max_quality=exhigh) 应该跳过
        """
        user_quality = kwargs.get('quality', '')
        # 取 song_id（per-rid 失败检查用）
        song_id = kwargs.get('song_id') or kwargs.get('rid') or kwargs.get('mid') or kwargs.get('hash') or kwargs.get('playlist_id')

        # ★ 按成功记忆重排：最近成功的源排前面（24 小时内）
        # 稳定排序：保留 priority 顺序，只把成功过的源前置
        # 第一优先级：preferred_source（来自上游链：search→info→url 保持一致）
        # 第二优先级：最近成功过的源
        # 第三优先级：priority
        preferred = kwargs.pop('preferred_source', None) or ''
        def _sort_key(s):
            if preferred and s.name == preferred:
                return (0, 0, s.priority)
            if self._is_source_success_recent(s.name):
                return (0, 1, s.priority)
            return (1, 0, s.priority)
        sources = sorted(sources, key=_sort_key)
        # 调试：打印重排后的顺序
        if any(self._is_source_success_recent(s.name) for s in sources):
            recent = [s.name for s in sources if self._is_source_success_recent(s.name)]
            logger.debug(f'[{self.platform}.{op}] 优先使用最近成功源: {recent}')
        if preferred:
            logger.debug(f'[{self.platform}.{op}] 同源优先: {preferred}')

        # ★ 链级超时：避免链中多个源依次超时导致总耗时超过前端 timeout
        chain_start = time.time()

        for source in sources:
            # ★ 链级超时检查：超过 max_chain_seconds 立即放弃
            if self.max_chain_seconds > 0:
                elapsed_chain = time.time() - chain_start
                if elapsed_chain >= self.max_chain_seconds:
                    logger.warning(
                        f'[{self.platform}.{op}] ⏱️ 链超时 ({elapsed_chain:.1f}s >= {self.max_chain_seconds}s)，'
                        f'放弃剩余 {len(sources) - sources.index(source)} 个源（{source.name} 起）'
                    )
                    return _default_for_op(op), None
            # ★ 跳过失败名单（两段式：global + per-rid）
            if self._is_source_failed(source.name, song_id):
                reason = '全局' if source.name in self._global_failed else f'per-rid({song_id})'
                logger.info(
                    f'[{self.platform}.{op}] 跳过 {source.name}（{reason} 失败名单中）'
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
            elapsed_ms = 0
            data = None
            try:
                data = self._fetch_one(source, op, **kwargs)
                elapsed_ms = int((time.time() - t0) * 1000)
                if self._is_valid(data, op):
                    # ★ parse_url：拿到 URL 后立刻验证可用性（避免下载时才发现 4xx）
                    if op == 'parse_url' and isinstance(data, str):
                        if self._is_url_dead(data):
                            # 之前已验证过该 URL 不可用 → 直接跳过该源（不动 source 状态）
                            logger.info(
                                f'[{self.platform}.{op}] 跳过 {source.name}（URL 在死链列表中）: {data[:60]}'
                            )
                            continue
                        # ★ 阶段 2：size check
                        # 期望大小从 kwargs['quality_map'] 取（调用方传入，来自 search/info）
                        qmap = kwargs.get('quality_map') or {}
                        user_q = user_quality
                        expected_size = int((qmap.get(user_q) or {}).get('size') or 0)
                        if not self._verify_url_reachable(data, expected_min_size=expected_size):
                            source._stats['fail'] += 1
                            source._stats['last_error'] = 'URL 验证失败（HEAD/RANGE 4xx/超时/size 不匹配）'
                            source._stats['total_ms'] += elapsed_ms
                            # ★ 改造：只标记这个 URL 死，不影响 source 对其他 song 的工作
                            # 旧版会全局禁用 source 5min（误伤其他 song）
                            self.mark_url_dead(data, source.name, expire_seconds=300)
                            logger.warning(
                                f'[{self.platform}.{op}] ⚠️ {source.name} URL 不可用（已标死链 5 分钟）: {data[:80]}'
                            )
                            continue
                    # 成功：清理该 source 的 per-rid 失败记录 + 全局失败
                    self._per_rid_failed.pop((source.name, str(song_id)) if song_id else None, None)
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
                # 拿到数据但无效（如 url 为空 / lyric 为空）→ permanent 失败（per-rid）
                source._stats['fail'] += 1
                source._stats['last_error'] = '数据无效（empty/parse）'
                source._stats['total_ms'] += elapsed_ms
                if song_id:
                    self.mark_source_failed(
                        source.name, expire_seconds=1800,  # 30 分钟
                        reason='empty result / parse error', song_id=song_id, scope='permanent',
                    )
                else:
                    # 没有 song_id 时降级为 transient
                    self.mark_source_failed(
                        source.name, expire_seconds=300, reason='empty result (no song_id)', scope='transient',
                    )
                logger.info(
                    f'[{self.platform}.{op}] ⚠️ {source.name} 返空数据 ({elapsed_ms}ms)'
                )
            except Exception as e:
                source._stats['fail'] += 1
                source._stats['last_error'] = f'{type(e).__name__}: {str(e)[:80]}'
                source._stats['total_ms'] += elapsed_ms
                # 分类：5xx/timeout → transient（global）；4xx → permanent（per-rid）
                status_code = getattr(e, 'status_code', None)
                err_msg = f'{type(e).__name__}: {str(e)[:80]}'
                if status_code and status_code >= 500:
                    # 5xx → 全局临时
                    self.mark_source_failed(
                        source.name, expire_seconds=120, reason=err_msg, scope='transient',
                    )
                elif status_code and 400 <= status_code < 500:
                    # 4xx → per-rid permanent
                    if song_id:
                        self.mark_source_failed(
                            source.name, expire_seconds=1800, reason=err_msg,
                            song_id=song_id, scope='permanent',
                        )
                    else:
                        self.mark_source_failed(
                            source.name, expire_seconds=300, reason=err_msg, scope='transient',
                        )
                elif isinstance(e, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
                    # 网络层 transient
                    self.mark_source_failed(
                        source.name, expire_seconds=120, reason=err_msg, scope='transient',
                    )
                else:
                    # 其他异常（parse / extractor 错误）→ per-rid permanent
                    if song_id:
                        self.mark_source_failed(
                            source.name, expire_seconds=1800, reason=err_msg,
                            song_id=song_id, scope='permanent',
                        )
                    else:
                        self.mark_source_failed(
                            source.name, expire_seconds=300, reason=err_msg, scope='transient',
                        )
                logger.info(f'[{self.platform}.{op}] ❌ {source.name} 失败: {err_msg}')
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

    def _try_parallel_first(self, sources: List[ApiSource], op: str, **kwargs) -> Tuple[Any, Optional[str]]:
        """并行：同时请求多个源，**取第一个成功**的（race-style）

        与 _try_serial 对比：
        - 串行：source1 超时 5s → 试 source2 (再 5s) → 共 10s+
        - 并行首胜：所有源同时跑，1s 内出结果就停 → 通常 1-3s

        与 _try_parallel 对比：
        - _try_parallel：所有源的结果**合并去重**（仅用于 search）
        - _try_parallel_first：所有源**抢答**，第一个成功的返回（用于 url/info/lyric）

        关键：第一个成功的 future 就 cancel 其余（避免浪费 CDN 流量和源配额）
        """
        all_sources = list(sources)
        if not all_sources:
            return _default_for_op(op), None

        all_results = []  # (data, source) 按完成顺序
        winner: Tuple[Any, Optional[str]] = (_default_for_op(op), None)
        # 链级超时
        chain_start = time.time()
        deadline = chain_start + self.max_chain_seconds if self.max_chain_seconds > 0 else float('inf')

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_to_source = {
                pool.submit(self._fetch_one, s, op, **kwargs): s
                for s in all_sources
            }
            try:
                # 等待第一个成功的（带超时）
                # 注意：as_completed 的 timeout 只在"完全没有 future 完成"时触发
                # 内部循环也要检查链级超时（防止所有源都失败时等待到 timeout）
                for fut in as_completed(future_to_source, timeout=max(0.1, deadline - time.time())):
                    # ★ 链级超时检查（每轮迭代都看）
                    if time.time() >= deadline:
                        logger.warning(
                            f'[{self.platform}.{op}] ⏱️ parallel_first 链级超时 ({time.time()-chain_start:.1f}s)'
                        )
                        break
                    source = future_to_source[fut]
                    try:
                        data = fut.result()
                    except Exception as e:
                        source._stats['fail'] += 1
                        source._stats['last_error'] = f'{type(e).__name__}: {str(e)[:80]}'
                        continue
                    if not self._is_valid(data, op):
                        source._stats['fail'] += 1
                        source._stats['last_error'] = '数据无效（empty/parse）'
                        continue
                    # ★ 成功：第一个返回有效结果的获胜
                    source._stats['ok'] += 1
                    source._stats['last_used'] = time.time()
                    self.mark_source_success(source.name)
                    winner = (data, source.name)
                    logger.info(
                        f'[{self.platform}.{op}] ✅ {source.name} 成功 (race-first)'
                    )
                    # 取消其他 future
                    for f in future_to_source:
                        if not f.done():
                            f.cancel()
                    return winner
            except TimeoutError:
                logger.warning(
                    f'[{self.platform}.{op}] ⏱️ parallel_first 超时 ({time.time()-chain_start:.1f}s)'
                )
            finally:
                # 等待所有 future 收尾（最多 0.5s），清理资源
                for f in list(future_to_source.keys()):
                    if not f.done():
                        f.cancel()
        return winner

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
        # ★ 关键：源 timeout 上限 = 链 timeout - 1s 余量
        # 例：源 timeout=15, 链 timeout=6 → 该源会跑 15s，链超时失去意义
        # 这里取 min(源, 链-余量)，让单源不会撑爆链
        # 例外：源 timeout ≤ 5s 时不截断（本身就快，不要越搞越慢）
        eff_timeout = source.timeout or self.request_timeout_default
        if self.max_chain_seconds > 0 and eff_timeout > 5:
            eff_timeout = min(eff_timeout, max(2, int(self.max_chain_seconds - 1)))

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
                                   timeout=eff_timeout)
        else:
            r = self._session.get(url, headers=headers, cookies=cookies,
                                  timeout=eff_timeout)

        # 解析
        if r.status_code >= 400:
            # 把 status_code 挂在异常上，_try_serial 用来分类 5xx/4xx
            err = RuntimeError(f'HTTP {r.status_code}')
            err.status_code = r.status_code
            raise err

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
