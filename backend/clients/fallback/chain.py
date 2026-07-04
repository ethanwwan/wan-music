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
import re
import time
import threading
import logging
import requests
from typing import List, Optional, Any, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from .api_source import ApiSource
from .extractors import quality_to_br

logger = logging.getLogger(__name__)

# 全局 HTTP 信号量：限制对外部 API 的并发请求数
# 每首歌 URL 抢答阶段占 4 个（parallel-first × 4 源），后续 lyric/info 占 1-2 个
# 8 = 允许 2 首歌 URL 抢答同时进行，兼顾并发和限流
# 防止：外网限流、连接池耗尽、TCP 拥塞导致的链超时
_http_semaphore = threading.Semaphore(8)

# 全局 Source 注册表：name → family
# 用来跨链查找 same_source 的 family（parse_url 成功源名 → 找同 family 的 parse_lyric 源）
_SOURCE_REGISTRY: dict[str, ApiSource] = {}


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
        # 注册到全局表（跨链查找 family 用）
        for s in self.sources:
            _SOURCE_REGISTRY[s.name] = s
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
        # Cookie 加载由各平台客户端负责（BaseMusicClient.__init__），
        # 通过 try_fetch(..., cookies=...) 传入，链本身不读文件。

    def set_source_enabled(self, name: str, enabled: bool) -> bool:
        """动态启用/禁用某个源"""
        for s in self.sources:
            if s.name == name:
                s.enabled = enabled
                return True
        return False

    def mark_source_failed(self, name: str, expire_seconds: int = 300,
                           reason: str = '', song_id: str = None,
                           scope: str = 'auto', log: bool = True) -> None:
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

        Args:
            log: 是否打印失败日志。music_client.mark_source_failed 会一次
                 广播到 5 个 chain，避免重复打印 5 遍。
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
            if log:
                logger.warning(
                    f'[{self.platform}] 全局禁用 source {name}（{ttl}s 内所有 song 都跳过）'
                    f' 原因: {reason[:80]}'
                )
        elif scope == 'permanent':
            if not song_id:
                # 没传 song_id 时降级为 transient（保证旧调用不破坏）
                ttl = expire_seconds
                self._global_failed[name] = time.time() + ttl
                if log:
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
            if log:
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
                            song_id: str = None, log: bool = True) -> None:
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

        Args:
            log: 是否打印成功日志。music_client.mark_source_success 会一次
                 广播到 5 个 chain（search/parse_url/parse_info/parse_lyric/
                 parse_playlist），调用方传入 log=False 避免重复打印 5 遍。
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
        if log:
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
        _http_semaphore.acquire()
        try:
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
        finally:
            _http_semaphore.release()

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
                特殊 kwarg:
                  - preferred_source: str  优先用这个 source
                  - same_source: str  ★ 同源优先：必须先用这个 source，
                    它不能 provide 当前 op 时才降级到其他源。
                    用于"url 抢答成功后告诉 lyric 链用同一个源"，
                    避免 url 和 lyric 跨源版本错配。

        Returns:
            (data, source_name) 或 (None/empty_default, None)
        """
        # 过滤出支持该 op 的源
        candidates = [s for s in self.sources if s.supports(op)]
        if not candidates:
            logger.debug(f'[{self.platform}.{op}] 无可用源')
            return _default_for_op(op), None

        # ★ 同源优先：same_source 不为空时，把这个源（或同 family 的源）放在第一位
        # 1. 先按 source name 匹配：same_source=haitanw，lyric 链有 haitanw_lyric → 优先用
        # 2. name 没匹配但 family 匹配：url=gdstudio_url，lyric 链有 gdstudio_lyric (family=gdstudio) → 优先用
        # 3. 都未匹配：降级到其他能 provide 该能力的源
        #
        # ★ 关键：same_s 在 self.sources（而非 candidates）中查找
        # 原因：URL 源（如 gdstudio_url）通常不支持 parse_lyric，会被 candidates 过滤掉
        #      但 family 匹配需要拿到 URL 源的 family 字段（gdstudio）去 lyric 链里找同 family 源
        #      所以必须查 self.sources 拿 family
        #
        # ★ 关键：把 family_match 注入到 kwargs['_family_preferred']
        # 原因：_try_serial 内部会按 priority 重新排序，family_match 的 reorder 会被覆盖
        #      通过 _family_preferred 机制让 _try_serial 把 family_match 排在最前
        #      （用 _ 前缀避免与业务参数冲突）
        same_source = kwargs.pop('same_source', None) or ''
        if same_source:
            cap = 'lyric' if op == 'parse_lyric' else ('url' if op == 'parse_url' else op.replace('parse_', ''))
            # 优先在当前链的 sources 中查找 same_source
            same_s = next((s for s in self.sources if s.name == same_source), None)
            # 当前链找不到则从全局注册表查找（跨链匹配，如 URL 源名 → 歌词链内同 family）
            if not same_s:
                same_s = _SOURCE_REGISTRY.get(same_source)
                if same_s:
                    logger.debug(
                        f'[{self.platform}.{op}] same_source={same_source} '
                        f'从全局注册表查到 family={same_s.family!r}'
                    )
            target_family = same_s.family if same_s else ''
            # 1) 名字匹配：source 自身就能 provide 该能力 → 优先用
            if same_s and same_s.has(cap) and same_s in candidates:
                kwargs['_family_preferred'] = same_source
                logger.info(
                    f'[{self.platform}.{op}] 🎯 同源优先: {same_source} (自身支持 {cap})'
                )
            # 2) family 匹配：候选中有同 family 且能 provide cap 的源
            elif target_family:
                family_match = next(
                    (s for s in candidates if s.family == target_family and s.has(cap)),
                    None,
                )
                if family_match:
                    kwargs['_family_preferred'] = family_match.name
                    logger.info(
                        f'[{self.platform}.{op}] 🎯 同 family 优先: '
                        f'{same_source}({target_family}) → {family_match.name}'
                    )
                else:
                    logger.debug(
                        f'[{self.platform}.{op}] same_source={same_source} family={target_family} '
                        f'无 {cap} 源，降级到其他源'
                    )
            # 3) source 自身不能 provide cap，且无 family 标识
            elif same_s:
                logger.debug(
                    f'[{self.platform}.{op}] same_source={same_source} '
                    f'不提供 {cap}，降级到其他源'
                )
            # 4) same_source 在当前链的 candidates 中找不到
            else:
                logger.debug(
                    f'[{self.platform}.{op}] same_source={same_source} '
                    f'不在当前 {op} 链的候选中，降级到其他源'
                )

        return self._try_serial(candidates, op, **kwargs)

    def _try_serial(self, sources: List[ApiSource], op: str, **kwargs) -> Tuple[Any, Optional[str]]:
        """串行：按 priority 依次尝试各源，第一个成功的返回

        适用所有 ops（search / parse_url / parse_lyric / parse_info）：
          - search：第一个返回有效数据的源即成功
          - parse_url：拿到 URL 后还要 HEAD 验证，验证通过才算成功

        关键优化：
          - max_quality 过滤（跳过无法提供目标音质的源）
          - 链级超时（max_chain_seconds）
          - 成功记忆（_sort_key 把最近成功的源排前面）
        """
        user_quality = kwargs.get('quality', '')
        song_id = kwargs.get('song_id') or kwargs.get('rid') or kwargs.get('mid') or kwargs.get('hash') or kwargs.get('playlist_id')

        # ★ 按成功记忆重排：最近成功的源排前面（24 小时内）
        preferred = kwargs.pop('preferred_source', None) or ''
        family_preferred = kwargs.pop('_family_preferred', None) or ''
        def _sort_key(s):
            if family_preferred and s.name == family_preferred:
                return (0, 0, 0, s.priority)
            if preferred and s.name == preferred:
                return (0, 0, 1, s.priority)
            if self._is_source_success_recent(s.name):
                return (0, 1, 0, s.priority)
            return (1, 0, 0, s.priority)
        sources = sorted(sources, key=_sort_key)
        if family_preferred:
            logger.debug(f'[{self.platform}.{op}] 家族匹配优先: {family_preferred}')
        if any(self._is_source_success_recent(s.name) for s in sources):
            recent = [s.name for s in sources if self._is_source_success_recent(s.name)]
            logger.debug(f'[{self.platform}.{op}] 优先使用最近成功源: {recent}')
        if preferred:
            logger.debug(f'[{self.platform}.{op}] 同源优先: {preferred}')

        chain_start = time.time()
        for source in sources:
            # 链级超时
            if self.max_chain_seconds > 0:
                elapsed_chain = time.time() - chain_start
                if elapsed_chain >= self.max_chain_seconds:
                    logger.warning(
                        f'[{self.platform}.{op}] ⏱️ 链超时 ({elapsed_chain:.1f}s >= {self.max_chain_seconds}s)，'
                        f'放弃剩余 {len(sources) - sources.index(source)} 个源（{source.name} 起）'
                    )
                    break
            # 失败名单
            if self._is_source_failed(source.name, song_id):
                reason = '全局' if source.name in self._global_failed else f'per-rid({song_id})'
                logger.info(
                    f'[{self.platform}.{op}] 跳过 {source.name}（{reason} 失败名单中）'
                )
                continue
            # max_quality 过滤
            if source.max_quality and user_quality:
                if _quality_rank(source.max_quality) < _quality_rank(user_quality):
                    logger.info(
                        f'[{self.platform}.{op}] 跳过 {source.name} '
                        f'(max_quality={source.max_quality} < user_quality={user_quality})'
                    )
                    continue
            # cookie 检查（cookies 由客户端通过 try_fetch(cookies=...) 传入）
            cookies = kwargs.get('cookies')
            if source.needs_cookie and not cookies:
                logger.info(
                    f'[{self.platform}.{op}] 跳过 {source.name} '
                    f'({source.name} 需要 cookie，但未提供)'
                )
                continue

            logger.info(f'[{self.platform}.{op}] 尝试 {source.name} (P={source.priority})...')
            t0 = time.time()
            elapsed_ms = 0
            data = None
            try:
                data = self._fetch_one(source, op, **kwargs)
                elapsed_ms = int((time.time() - t0) * 1000)
                if not self._is_valid(data, op):
                    source._stats['fail'] += 1
                    source._stats['last_error'] = '数据无效（empty/parse）'
                    source._stats['total_ms'] += elapsed_ms
                    logger.info(
                        f'[{self.platform}.{op}] ⚠️ {source.name} 返空数据 ({elapsed_ms}ms)'
                    )
                    continue

                # parse_url 额外：URL 验证
                if op == 'parse_url' and isinstance(data, str):
                    if self._is_url_dead(data):
                        logger.info(
                            f'[{self.platform}.{op}] 跳过 {source.name}（URL 在死链列表中）: {data[:60]}'
                        )
                        continue
                    if not self._verify_url_reachable(data):
                        source._stats['fail'] += 1
                        source._stats['last_error'] = 'URL 验证失败'
                        source._stats['total_ms'] += elapsed_ms
                        self.mark_url_dead(data, source.name, expire_seconds=300)
                        logger.warning(
                            f'[{self.platform}.{op}] ⚠️ {source.name} URL 不可用（已标死链 5 分钟）: {data[:80]}'
                        )
                        continue

                # 成功：立即返回
                source._stats['ok'] += 1
                source._stats['last_used'] = time.time()
                source._stats['total_ms'] += elapsed_ms
                self._per_rid_failed.pop((source.name, str(song_id)) if song_id else None, None)
                url_preview = ''
                if op == 'parse_url' and isinstance(data, str):
                    url_preview = f' → {data[:80]}'
                logger.info(
                    f'[{self.platform}.{op}] ✅ {source.name} 成功 ({elapsed_ms}ms){url_preview}'
                )
                return data, source.name
            except Exception as e:
                source._stats['fail'] += 1
                source._stats['last_error'] = f'{type(e).__name__}: {str(e)[:80]}'
                source._stats['total_ms'] += elapsed_ms
                logger.info(
                    f'[{self.platform}.{op}] ❌ {source.name} 失败: '
                    f'{type(e).__name__}: {str(e)[:80]}'
                )

        return _default_for_op(op), None

    def _fetch_one(self, source: ApiSource, op: str, **kwargs) -> Any:
        """执行单次 API 调用"""
        url_template = source.get_url(op)
        if not url_template:
            raise ValueError(f'源 {source.name} 未配置 {op} URL')

        # 填充占位符（用 SafeDict 兜底未知占位符，保留为 {name} 形式给 prepare_request 解析）
        resolved = self._resolve_placeholders(source, op, kwargs)
        url = url_template.format_map(_SafeDict(resolved))
        # 一些 URL 模板中含有 __br__ 等特殊占位符
        url = url.replace('{{', '{').replace('}}', '}')

        # ★ 直传模式：源 API 不返回 JSON，直接返音频流（如 ccwu）。
        #    跳过 HTTP 请求，把 URL 模板本身当作下载 URL 返回，
        #    chain 后续会 HEAD/Range 验证 URL 可用性。
        if getattr(source, 'passthrough', False):
            logger.debug(
                f'[{self.platform}] passthrough 源 {source.name}：直接返回 URL {url[:80]}'
            )
            return url

        # 拼接 headers
        headers = dict(source.headers)
        # 默认 UA
        headers.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')

        # Cookie（从 try_fetch 传入，已缓存，避免重复加载）
        cookies = kwargs.get('cookies')

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

        # 发起请求（受全局信号量限制，避免并发过多触发外网限流）
        # ★ 关键：源 timeout 上限 = 链 timeout - 1s 余量
        # 例：源 timeout=15, 链 timeout=6 → 该源会跑 15s，链超时失去意义
        # 这里取 min(源, 链-余量)，让单源不会撑爆链
        # 例外：源 timeout ≤ 5s 时不截断（本身就快，不要越搞越慢）
        eff_timeout = source.timeout or self.request_timeout_default
        if self.max_chain_seconds > 0 and eff_timeout > 5:
            eff_timeout = min(eff_timeout, max(2, int(self.max_chain_seconds - 1)))

        _http_semaphore.acquire()
        try:
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
        finally:
            _http_semaphore.release()

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
            # 修复：原来只检查 name OR id，但 fallback 源可能返回 {id: '...', name: ''}
            # 这种半空对象应该跳过，要求至少 name + id 同时存在（或 name + artists）
            if not isinstance(data, dict):
                return False
            has_id = bool(data.get('id') or data.get('mid') or data.get('rid') or data.get('hash'))
            has_name = bool(data.get('name') or data.get('title') or data.get('songName'))
            return has_id and has_name
        if op == 'parse_lyric':
            # 修复：原来只检查 len > 0，但 '暂无歌词' / 'no lyrics' / '纯音乐' 等占位符
            # 长度 > 0 会被误判为有效 → 前端以为有歌词但实际是占位符
            if not isinstance(data, str):
                return False
            s = data.strip()
            if len(s) < 10:  # 真实歌词至少几十字符
                return False
            # 检查是否包含时间戳（真实歌词必有 [00:xx.xx] 或 LRC 头标签）
            if not (re.search(r'\[\d{1,2}:\d{2}', s) or s.startswith('[ti:') or s.startswith('[ar:')):
                return False
            # 排除明显的占位符
            placeholders = ('暂无歌词', 'no lyrics', 'no lyric', '纯音乐', 'lyric not found',
                            'lyrics not found', '该歌曲为纯音乐', '暂未发现歌词')
            s_lower = s.lower()
            if any(p in s_lower for p in placeholders):
                return False
            return True
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
        """（废弃）由客户端层接管 cookie 加载，链内不再读写 cookie 文件"""
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


class _SafeDict(dict):
    """dict 包装，让 str.format_map 对未知占位符保留为 {name} 形式不抛 KeyError。

    用途：源 URL 模板含 prepare_request 动态注入的占位符（如 {ckey}），
    标准 format() 会因 KeyError 抛错导致整源静默失败；
    用 format_map(SafeDict) 保留占位符，prepare_request 后续替换。
    """
    def __missing__(self, key: str) -> str:
        return '{' + key + '}'
