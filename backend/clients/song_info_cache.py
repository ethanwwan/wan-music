"""搜索结果 info 短期缓存

设计目标：
- /search 阶段拿到的 name/artist/album/duration/cover/qualityMap
  是当前平台官方/最权威源的元信息。
- /song 阶段应**优先复用**这些 info，避免再去 parse_info_chain 抢答其他源
  （不同源可能拿不同版本，导致音频/歌词/元信息跨源不一致）。

缓存维度：
  key = (platform, song_id)
  value = {
      'name', 'artists', 'album', 'picUrl', 'duration', 'qualityMap',
      '_search_source', '_cached_at',
  }
  TTL = 5 分钟（搜索结果时效性短，5 分钟够覆盖单次会话）

实现：
  - 进程内 dict + threading.Lock（不需要跨进程）
  - 写入：search 阶段（music_client.search）每条 search_result 写一次
  - 读取：get_song 阶段第一件事
  - 不命中：回退到 parse_info_chain（保留旧兜底逻辑）
"""
import time
import threading
from typing import Any, Dict, Optional, Tuple


# ==================== 配置 ====================

# 1 小时：确保批量下载场景下搜索到下载之间的缓存有效性
# 单次搜索后到 /song 调用通常几秒内完成，1h 足够覆盖整轮下载
DEFAULT_TTL_SECONDS = 3600

# 最大缓存条数（避免长时间运行内存膨胀）
MAX_ENTRIES = 2000


# ==================== 存储 ====================

_lock = threading.Lock()
_store: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def _evict_expired() -> None:
    """清理过期条目（在锁内调用）"""
    now = _now()
    expired = [k for k, v in _store.items() if v.get('_cached_at', 0) + v.get('_ttl', DEFAULT_TTL_SECONDS) <= now]
    for k in expired:
        _store.pop(k, None)


def _evict_oldest_if_full() -> None:
    """超过 MAX_ENTRIES 时清理最早的（按 _cached_at 排序）"""
    if len(_store) <= MAX_ENTRIES:
        return
    items = sorted(_store.items(), key=lambda kv: kv[1].get('_cached_at', 0))
    overflow = len(_store) - MAX_ENTRIES
    for k, _ in items[:overflow]:
        _store.pop(k, None)


# ==================== 公开 API ====================

def put(platform: str, song_id: str, info: Dict[str, Any],
        ttl: int = DEFAULT_TTL_SECONDS) -> None:
    """写入一条 song info 缓存

    Args:
        platform: 平台 ID（'netease'/'qq'/'kugou'/'kuwo'）
        song_id: 平台内歌曲 ID
        info: 完整 search result dict（应至少含 name/artists/album/duration/picUrl/qualityMap）
        ttl: 过期秒数
    """
    if not platform or not song_id or not isinstance(info, dict):
        return
    payload = dict(info)
    payload['_cached_at'] = _now()
    payload['_ttl'] = ttl
    with _lock:
        _evict_expired()
        _store[(platform, str(song_id))] = payload
        _evict_oldest_if_full()


def get(platform: str, song_id: str) -> Optional[Dict[str, Any]]:
    """读取一条 song info 缓存（不修改源数据）

    Returns:
        命中且未过期返回 info dict（去掉 _cached_at / _ttl 内部字段），
        未命中或已过期返回 None
    """
    if not platform or not song_id:
        return None
    key = (platform, str(song_id))
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        cached_at = entry.get('_cached_at', 0)
        ttl = entry.get('_ttl', DEFAULT_TTL_SECONDS)
        if _now() - cached_at > ttl:
            _store.pop(key, None)
            return None
        # 返回拷贝，避免外部修改污染缓存
        return {k: v for k, v in entry.items() if not k.startswith('_')}


def invalidate(platform: str = None, song_id: str = None) -> int:
    """失效缓存（调试用）

    Args:
        platform: 指定平台；None 表示清空所有
        song_id: 指定 song_id；与 platform 都为 None 时清空全部
    Returns:
        实际清除的条数
    """
    with _lock:
        if platform is None and song_id is None:
            n = len(_store)
            _store.clear()
            return n
        if platform and song_id:
            return 1 if _store.pop((platform, str(song_id)), None) is not None else 0
        if platform:
            n = sum(1 for k in _store if k[0] == platform)
            for k in [k for k in _store if k[0] == platform]:
                _store.pop(k, None)
            return n
        return 0


def stats() -> Dict[str, Any]:
    """缓存统计（调试用）"""
    with _lock:
        now = _now()
        alive = sum(
            1 for v in _store.values()
            if now - v.get('_cached_at', 0) <= v.get('_ttl', DEFAULT_TTL_SECONDS)
        )
        by_platform: Dict[str, int] = {}
        for plat, _ in _store.keys():
            by_platform[plat] = by_platform.get(plat, 0) + 1
        return {
            'total': len(_store),
            'alive': alive,
            'by_platform': by_platform,
        }
