"""音乐客户端总控模块

作为多平台音乐客户端的总控中心：
  - 网易云音乐（netease_client）
  - QQ音乐（qq_client）
  - 酷狗音乐（kugou_client）
  - 酷我音乐（kuwo_client）

提供统一的 API 接口（search / get_song），前端可指定数据源和平台。
所有平台 search 走官方 API，一次返回完整元信息（album / cover / qualityMap / pay）。
"""
import logging
from typing import Any, Dict, List, Optional

from .base_client import BaseMusicClient
from .netease_client import NeteaseClient, netease_client
from .qq_client import QQClient, qq_client
from .kugou_client import KugouClient, kugou_client
from .kuwo_client import KuwoClient, kuwo_client
from . import song_info_cache

logger = logging.getLogger(__name__)


# ==================== 跨源防错：duration 交叉验证 ====================

import re as _re
# LRC 末行时间戳：[mm:ss.xx] 或 [mm:ss.xxx]
_LRC_LAST_TS_RE = _re.compile(r'\[(\d{1,2}):(\d{1,2})(?:[.:](\d{1,3}))?\]')


def _extract_lrc_max_ts(lrc_text: str) -> int:
    """从 LRC 文本中提取最大时间戳（毫秒）。返回 0 表示无歌词或无有效时间戳。"""
    if not lrc_text or not isinstance(lrc_text, str):
        return 0
    max_ms = 0
    for m in _LRC_LAST_TS_RE.finditer(lrc_text):
        mm = int(m.group(1) or 0)
        ss = int(m.group(2) or 0)
        # 处理 .xx / .xxx 两种格式
        frac = m.group(3)
        if frac is None:
            ms = 0
        elif len(frac) == 2:
            ms = int(frac) * 10
        else:
            ms = int(frac[:3].ljust(3, '0'))
        total = (mm * 60 + ss) * 1000 + ms
        if total > max_ms:
            max_ms = total
    return max_ms


def _check_lyric_duration_mismatch(result: dict, platform: str, song_id: str) -> None:
    """检测歌词版本是否与音频版本错配

    触发条件：info.duration > 0 && lyric 有内容 && 末时间戳 vs duration 差 > 5s
    标记：result['mismatch_warning'] = 'lyric_version_mismatch: 差 Xs'
    注意：只标记，不阻断（前端可决定是否提示用户）
    """
    if not isinstance(result, dict):
        return
    lyric = result.get('lyric') or ''
    if not lyric:
        return
    duration = result.get('duration')
    try:
        duration = int(duration or 0)
    except (TypeError, ValueError):
        return
    if duration <= 0:
        return
    # duration 来自 search 阶段（_cached_info），单位 ms
    max_ts = _extract_lrc_max_ts(lyric)
    if max_ts <= 0:
        return
    # 差值：duration - max_ts（正数表示歌词在音频结束前就完了）
    delta_ms = duration - max_ts
    delta_s = delta_ms / 1000
    # 阈值 5s（>5s 视为明显错配；intro/outro 静音造成的误差在 ±3s 内）
    if abs(delta_s) > 5:
        warning = f'lyric_version_mismatch: 差 {delta_s:.1f}s (info={duration/1000:.1f}s, lyric_max={max_ts/1000:.1f}s)'
        result['mismatch_warning'] = warning
        logger.warning(
            f'[{platform}/{song_id}] {warning}'
        )


def _pick_quality_info(quality_map: dict, quality: str) -> dict:
    """从 qualityMap 中取指定音质的 {br, size}；找不到返回空 dict。"""
    if not isinstance(quality_map, dict) or not quality:
        return {}
    qinfo = quality_map.get(quality) or {}
    if not isinstance(qinfo, dict):
        return {}
    # 兼容 size/br 直接是数字的情况
    out = {}
    if 'size' in qinfo:
        out['size'] = qinfo['size']
    if 'br' in qinfo:
        out['br'] = qinfo['br']
    elif isinstance(qinfo.get('bitrate'), (int, float)):
        out['br'] = qinfo['bitrate']
    return out


def _prune_quality_map(result: dict, requested_quality: str, actual_quality: str) -> None:
    """精简 result['qualityMap'] 为前端最小可见集

    旧格式（search 阶段原始 qualityMap，可能含 hires/lossless/exhigh/standard 全套）：
        {'hires': {'br': ..., 'size': ...}, 'lossless': {...}, ...}

    新格式（C2 方案：替换精简版）：
        {
            'requested': {'quality': <str>, ...info},   # 用户请求的音质
            'actual':    {'quality': <str>, ...info},   # 实际拿到的音质（可能降级或升级）
        }

    设计理由：
    - 前端只关心"请求的音质是什么"和"实际拿到的音质是什么"
    - 不再传整个 qualityMap（避免后端 4 平台 + 多音质的几十个字段冗余）
    - 实际音质字段放在 .actual（前端直接读取展示）
    - 请求音质字段放在 .requested（前端展示"用户选了 X，实际给了 Y"的对比）
    """
    if not isinstance(result, dict):
        return
    full = result.get('qualityMap')
    if not isinstance(full, dict):
        return
    req_info = _pick_quality_info(full, requested_quality)
    act_info = _pick_quality_info(full, actual_quality)

    new_map = {
        'requested': {'quality': requested_quality, **req_info},
        'actual': {'quality': actual_quality, **act_info},
    }
    result['qualityMap'] = new_map


class MusicClient:
    """统一的音乐客户端总控类"""

    PLATFORM_REGISTRY = [
        ('netease', netease_client, '网易云音乐', '#e72d2c', '网易云音乐平台'),
        ('qq',      qq_client,      'QQ音乐',    '#31c27c', 'QQ音乐平台'),
        ('kugou',   kugou_client,   '酷狗音乐',  '#2a8eff', '酷狗音乐平台'),
        ('kuwo',    kuwo_client,    '酷我音乐',  '#ff6600', '酷我音乐平台'),
    ]

    def __init__(self):
        self.platform_clients: Dict[str, BaseMusicClient] = {}
        for platform_id, client, *_ in self.PLATFORM_REGISTRY:
            self.register_client(platform_id, client)
        self.default_platform = 'netease'

    def register_client(self, platform: str, client: BaseMusicClient) -> None:
        if not isinstance(client, BaseMusicClient):
            raise ValueError("客户端必须继承自 BaseMusicClient")
        self.platform_clients[platform] = client
        logger.info(f"已注册平台: {platform}")

    def get_platforms(self) -> List[Dict[str, Any]]:
        """获取可用平台列表（id / name / color / description）"""
        return [
            {'id': p, 'name': name, 'color': color, 'description': desc}
            for p, _, name, color, desc in self.PLATFORM_REGISTRY
        ]

    # ==================== 坏源管理（service 层调用） ====================

    def mark_source_failed(self, platform: str, source_name: str,
                           reason: str = '', expire_seconds: int = 300,
                           song_id: str = None, scope: str = 'auto') -> None:
        """标记某 platform 的某个 source 为临时失败（让下次重试自动跳过）

        字段约定（用户定义）：
          platform  = 4 大平台名（'netease'/'qq'/'kugou'/'kuwo'）
          source    = 底层 API 域名（'vkeys_url'/'xuanluoge_url'/'gdstudio_lyric' 等）

        场景：service.py 下载时遇到 4xx（如 vkeys_url 返的 URL 403），
        通知 chain 这个 source 不可用，避免下次重试仍用同源。

        两段式失败缓存（向后兼容）：
          scope='auto'       → 自动分类（默认，旧调用方式）
          scope='transient'  → 强制全局（5xx/timeout）
          scope='permanent'  → 强制 per-rid（4xx/empty/parse，需要 song_id）
          不传 song_id 时降级为全局（旧行为）

        日志只打印 1 次（避免广播到 5 个 chain 重复 5 遍）。

        Args:
            platform: 4 大平台名
            source_name: 失败的 source 名
            reason: 失败原因（仅用于日志）
            expire_seconds: TTL（transient 5min, permanent 30min）
            song_id: 当前 song ID（per-rid 失败时需要）
            scope: 'auto'/'transient'/'permanent'
        """
        try:
            client = self._get_client(platform)
        except ValueError:
            return
        for chain in (client.parse_url_chain, client.parse_info_chain,
                      client.parse_lyric_chain, client.parse_playlist_chain,
                      client.search_chain):
            if chain:
                chain.mark_source_failed(
                    source_name, expire_seconds, reason,
                    song_id=song_id, scope=scope, log=False,
                )

    def reset_failed_sources(self, platform: str = None) -> None:
        """清空失败名单（task 启动时调用）

        Args:
            platform: 指定平台名（None=清空所有平台）
        """
        if platform:
            try:
                client = self._get_client(platform)
                for chain in (client.parse_url_chain, client.parse_info_chain,
                              client.parse_lyric_chain, client.parse_playlist_chain,
                              client.search_chain):
                    if chain:
                        chain.reset_failed_sources()
            except ValueError:
                pass
        else:
            for client in self.platform_clients.values():
                for chain in (client.parse_url_chain, client.parse_info_chain,
                              client.parse_lyric_chain, client.parse_playlist_chain,
                              client.search_chain):
                    if chain:
                        chain.reset_failed_sources()

    def mark_source_success(self, platform: str, source_name: str,
                            expire_seconds: int = 86400) -> None:
        """标记某 platform 的某个 source 最近成功（让后续 try_fetch 优先使用该 source）

        字段约定（用户定义）：
          platform  = 4 大平台名（'netease'/'qq'/'kugou'/'kuwo'）
          source    = 底层 API 域名（'vkeys_url'/'xuanluoge_url'/'gdstudio_lyric' 等）

        场景：vkeys_url 成功下载某首歌 → 后续 24 小时内优先用 vkeys_url
              直到它失败（被 mark_source_failed 覆盖）
        改为 24h：API 稳定性以天为单位，避免每 10 分钟重复 try 所有 source。

        日志只打印 1 次（避免广播到 5 个 chain 重复 5 遍）。
        """
        try:
            client = self._get_client(platform)
        except ValueError:
            return
        for chain in (client.parse_url_chain, client.parse_info_chain,
                      client.parse_lyric_chain, client.parse_playlist_chain,
                      client.search_chain):
            if chain:
                chain.mark_source_success(source_name, expire_seconds, log=False)

    def _get_client(self, platform: str) -> BaseMusicClient:
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        return client

    # ==================== 业务方法 ====================

    def search(self, keyword: str, platform: str = None, limit: int = 50) -> Dict[str, Any]:
        """搜索歌曲（永远只搜歌曲；URL 由 service 层另行解析）

        4 个平台 search 链都走官方 API，一次返回完整元信息
        （album / cover / qualityMap / pay），不需要后置补全

        返回 dict（含 search_source），兼容 routes.py 和 service.py
        """
        client = self._get_client(platform)
        result = client.search(keyword, limit=limit)
        if not isinstance(result, dict):
            return {'data': [], 'search_source': ''}
        songs = result.get('data', [])
        search_source = result.get('search_source', '')

        # ★ 关键：把每条 search_result 写入 song_info_cache
        # 这样后续 /song 阶段可以直接复用，**避免去 parse_info_chain
        # 拿不同源 info** 导致的"音频/歌词/元信息跨源不一致"问题。
        for s in songs:
            if not isinstance(s, dict):
                continue
            sid = s.get('id')
            if not sid:
                continue
            # 复制一份避免外部修改污染缓存
            payload = dict(s)
            if search_source and not payload.get('_search_source'):
                payload['_search_source'] = search_source
            song_info_cache.put(platform or self.default_platform, str(sid), payload)

        return {'data': songs, 'search_source': search_source}

    def get_song(self, song_id: Any, quality: str = 'lossless',
                 platform: str = None, with_lyric: bool = True,
                 quality_map: dict = None) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息（信息 + URL + 可选歌词）

        支持基于 qualityMap 的智能降级（按用户请求的音质）：
        1. 先按平台能力（PLATFORM_QUALITY_SUPPORT.fallback_chain）过滤
        2. 再按歌曲实际可用的 qualityMap 过滤
        3. 从用户请求的音质开始，依次尝试链中更低的音质
        4. 用户请求超清母带但该歌曲只有 exhigh → 直接从 exhigh 开始，
           跳过 hires/lossless，节省 5-10 秒

        song_id 可以是字符串（直接是 hash/id），也可以是 dict
        （包含 id 和 mp3_hash 字段，用于酷狗的 FLAC/MP3 双 hash 场景）

        quality_map（可选）：该歌曲的可用音质字典 {quality: {br, size}}
        - 来自 search 结果，可让降级更精准
        - 优先级：search 时的 qualityMap > 平台 fallback_chain 默认行为

        ★ 跨源一致性策略：
        1. 优先从 song_info_cache 读取 search 阶段写下的 info
           （**避免** /song 阶段去 parse_info_chain 拿不同源的 info）
        2. cache miss 时（URL 解析/歌单导入等无 search 上下文的场景），
           降级走 parse_info_chain 拿 info
        3. 最终返回的 info 永远来自 search 阶段或 parse_info_chain 兜底，
           不会和 url/lyric 跨源拼接

        Returns:
            None 表示完全失败
        """
        try:
            from ..app_config import get_platform_quality_chain
        except (ImportError, ValueError):
            # 兼容直接以脚本形式运行时（相对导入失败时走绝对路径）
            import os, sys
            _backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if _backend_root not in sys.path:
                sys.path.insert(0, _backend_root)
            from app_config import get_platform_quality_chain

        client = self._get_client(platform)
        plat = platform or self.default_platform

        # song_id 可能是 dict（包含多 hash 信息）
        mp3_hash = ''
        cached_info = None
        preferred = ''
        if isinstance(song_id, dict):
            mp3_hash = str(song_id.get('mp3_hash') or '')
            song_id_str = str(song_id.get('id') or song_id.get('hash') or '')
            # 兼容：dict 中也带 qualityMap
            if not quality_map:
                quality_map = song_id.get('qualityMap')
            preferred = song_id.get('_search_source', '') or song_id.get('api_source', '')
        else:
            song_id_str = str(song_id)

        # ★ 关键：从 song_info_cache 读取 search 阶段写下的 info
        # 命中后**用 cache 的 qualityMap 覆盖**入参 quality_map
        # （cache 里的 qualityMap 是 search 阶段权威源，更准确）
        cached_info = song_info_cache.get(plat, song_id_str)
        if cached_info:
            if not quality_map and isinstance(cached_info.get('qualityMap'), dict):
                quality_map = cached_info['qualityMap']
            if not preferred and isinstance(cached_info.get('_search_source'), str):
                preferred = cached_info['_search_source']
            logger.debug(
                f'[{plat}/{song_id_str}] song_info_cache 命中 '
                f'(name={cached_info.get("name", "")!r}, '
                f'duration={cached_info.get("duration", 0)})'
            )
        else:
            logger.debug(f'[{plat}/{song_id_str}] song_info_cache miss，将走 parse_info 兜底')

        # 关键：基于 qualityMap + 平台能力，获取该歌曲实际可用的降级链
        # 例：用户请求 jymaster，qualityMap 只有 exhigh → 链是 [exhigh, standard]
        #     用户请求 lossless，qualityMap 有 lossless/exhigh → 链是 [lossless, exhigh]
        chain = get_platform_quality_chain(platform, quality, quality_map)

        if chain and chain[0] != quality:
            logger.info(
                f"音质降级预过滤: {platform}/{song_id_str} "
                f"请求={quality} → 实际起始={chain[0]}（qualityMap 或平台能力限制）"
            )

        # ★ 总超时：每个 quality 单独跑可能很慢（链超时 6s × 3 音质 = 18s），
        # 超出后立即放弃剩余音质，返回已有结果
        # 配合前端 8s timeout 留 2s 余量
        import time as _time
        song_start = _time.time()
        max_total_seconds = 6.5

        last_result = None
        for try_quality in chain:
            # 检查总耗时
            if _time.time() - song_start >= max_total_seconds:
                logger.warning(
                    f'[{platform}/{song_id_str}] ⏱️ 总耗时超 {max_total_seconds}s，'
                    f'放弃剩余 {len(chain) - chain.index(try_quality)} 个音质（{try_quality} 起）'
                )
                break
            # 酷狗特殊：lossless/hires 用 FLAC hash（id = SQFileHash），
            # exhigh/standard 用 MP3 hash（mp3_hash = FileHash）
            if platform == 'kugou' and mp3_hash and try_quality in ('exhigh', 'standard'):
                parse_id = mp3_hash
            else:
                parse_id = song_id_str

            # 不传 quality_map 给子类：quality_map 只在 MusicClient 层用于降级链过滤
            # （get_platform_quality_chain），子类的 get_song 不需要这个参数
            # 否则会触发 TypeError: get_song() got an unexpected keyword argument 'quality_map'
            # 从 qualityMap 提取当前 try_quality 的 size（用于 URL size 验证）
            qmap_for_url = {}
            if quality_map and isinstance(quality_map, dict):
                qinfo = quality_map.get(try_quality) or {}
                if isinstance(qinfo, dict) and qinfo.get('size'):
                    qmap_for_url = {try_quality: qinfo}
            result = client.get_song(
                parse_id, try_quality, with_lyric=with_lyric,
                preferred_source=preferred, quality_map=qmap_for_url or None,
                _cached_info=cached_info,  # ★ 新增：把 search info 传给 client，client 不再抢答 parse_info
            )
            if result and result.get('url'):
                # ★ 把 cached_info（name/artist/album/cover/duration/qualityMap）
                # **优先**应用到 result（解决跨源不一致问题）
                if cached_info:
                    for k in ('name', 'artists', 'album', 'picUrl', 'duration'):
                        cv = cached_info.get(k)
                        if cv and not result.get(k):
                            result[k] = cv
                    # qualityMap 用 search 阶段的版本（更准确）
                    if isinstance(cached_info.get('qualityMap'), dict):
                        result['qualityMap'] = cached_info['qualityMap']

                # 标记实际拿到的音质（用于前端展示 + fallback 对比）
                result['level'] = try_quality
                # 附加前端展示字段（label 显示名、format 描述）
                from app_config import QUALITY_LEVELS
                level_cfg = QUALITY_LEVELS.get(try_quality) or {}
                result['level_name'] = level_cfg.get('label', try_quality)
                result['level_format'] = level_cfg.get('description', '')
                # 从 url 推断 file_ext（CDN URL 通常带 .flac/.mp3/.m4a 后缀）
                url_lower = result.get('url', '').lower()
                for ext in ('.flac', '.mp3', '.m4a', '.ape', '.ogg', '.opus', '.wav'):
                    if ext in url_lower:
                        result['file_ext'] = ext.lstrip('.')
                        break
                if try_quality != quality:
                    result['requested_quality'] = quality
                    # 区分升级/降级（用音质 rank 比较）
                    from .fallback.chain import _quality_rank
                    actual_rank = _quality_rank(try_quality)
                    requested_rank = _quality_rank(quality)
                    if actual_rank < requested_rank:
                        # 实际音质低于请求音质 → 真降级
                        result['level_fallback'] = True
                        result['level_upgrade'] = False
                        logger.info(
                            f"音质降级: {platform}/{song_id_str} "
                            f"{quality} → {try_quality}"
                        )
                    else:
                        # 实际音质高于请求音质 → 升级（数据源给得比请求更好）
                        result['level_fallback'] = False
                        result['level_upgrade'] = True
                        logger.info(
                            f"音质升级: {platform}/{song_id_str} "
                            f"{quality} → {try_quality} (数据源给得更好)"
                        )
                # ★ 跨源版本错配检测（B2 方案：duration 交叉验证）
                # 如果有歌词，取歌词最后时间戳与 info.duration 比对；
                # 差异 > 5s 视为 lyric 和 audio 版本不一致（Live vs Studio 错配）
                _check_lyric_duration_mismatch(result, platform, song_id_str)
                # ★ 精简 qualityMap：前端只关心"请求音质 + 实际音质"两项
                _prune_quality_map(result, quality, try_quality)
                return result
            last_result = result

        return last_result

    def parse_playlist(self, playlist_id: str, platform: str = None,
                       page: int = 1, size: int = 100) -> Optional[Dict[str, Any]]:
        """解析歌单：返回 {'name','creator','cover','trackCount','tracks', 'source', 'api_source'}

        Returns:
            None 表示该平台暂不支持歌单解析
        """
        client = self._get_client(platform)
        if not hasattr(client, 'parse_playlist'):
            return None
        return client.parse_playlist(playlist_id, page=page, size=size)


# 全局单例
music_client = MusicClient()


# ==================== 向后兼容的函数接口 ====================

def search_music(keywords: str, platform: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    return music_client.search(keywords, platform, limit=limit)


def get_song(song_id: str, quality: str, platform: str = None,
             with_lyric: bool = True,
             quality_map: dict = None) -> Optional[Dict[str, Any]]:
    """获取歌曲完整信息（向后兼容，新接口推荐用 music_client.get_song）

    quality_map: 该歌曲可用音质字典（从 search result 带过来），
                 传入后 music_client.get_song 会做智能降级
    """
    return music_client.get_song(song_id, quality, platform,
                                 with_lyric=with_lyric, quality_map=quality_map)


def parse_playlist(playlist_id: str, platform: str = None,
                   page: int = 1, size: int = 100) -> Optional[Dict[str, Any]]:
    """解析歌单（向后兼容函数）"""
    return music_client.parse_playlist(playlist_id, platform, page=page, size=size)


def get_platforms() -> List[Dict[str, str]]:
    return music_client.get_platforms()
