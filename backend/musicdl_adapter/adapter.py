"""musicdl 适配器 - 直接调用 musicdl 库（Python 3.10+ 兼容）"""
import contextlib
import os
import shutil
import sys
from typing import Optional

from musicdl import musicdl

from .converter import musicdl_to_search_song, musicdl_to_song_info

# 平台名 → musicdl 内部 client class 名
PLATFORM_MAP = {
    'netease': 'NeteaseMusicClient',
    'qq': 'QQMusicClient',
    'kugou': 'KugouMusicClient',
    'kuwo': 'KuwoMusicClient',
}

# 单例 client 缓存（按 source 懒加载）
_clients: dict[str, musicdl.MusicClient] = {}

# 搜索结果缓存 {source:keyword → list[dict]}
_search_cache: dict[str, list[dict]] = {}

# 原始搜索 API 响应缓存 {source:song_id → 原始 dict}，用于快速 URL 解析
_raw_search_cache: dict[str, dict] = {}


def _get_client(source: str, search_size: int = 50) -> Optional[musicdl.MusicClient]:
    """获取或创建对应平台的 MusicClient 实例"""
    client_name = PLATFORM_MAP.get(source)
    if not client_name:
        return None
    cache_key = f'{client_name}_size{search_size}'
    if cache_key not in _clients:
        init_cfg = {client_name: {'search_size_per_source': search_size}}
        _clients[cache_key] = musicdl.MusicClient(
            music_sources=[client_name],
            init_music_clients_cfg=init_cfg,
        )
    return _clients[cache_key]


def _cleanup_output(client: musicdl.MusicClient):
    """删除 musicdl 自动创建的 search_results.pkl 目录"""
    for src_name, work_dir in getattr(client, 'work_dirs', {}).items():
        if work_dir and os.path.isdir(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)


def parse_playlist(playlist_url: str) -> Optional[dict]:
    """musicdl v2.13.1 未实现 parseplaylist，此函数保留以便前端提示"""
    return None


def _do_search(keyword: str, source: str, search_size: int = 5) -> list[dict]:
    """执行搜索，返回原始 dict 列表"""
    client = _get_client(source, search_size)
    if not client:
        return []

    client_name = PLATFORM_MAP[source]
    try:
        with contextlib.redirect_stdout(sys.stderr):
            results = client.search(keyword)
    except Exception:
        return []
    finally:
        _cleanup_output(client)

    items = results.get(client_name, [])
    return [_song_to_dict(s) for s in items]


def _song_to_dict(song) -> dict:
    """SongInfo → 可 JSON 序列化的 dict"""
    return {
        'identifier': song.identifier or '',
        'song_name': song.song_name or '',
        'singers': song.singers or '',
        'album': song.album or '',
        'ext': song.ext or '',
        'file_size_bytes': song.file_size_bytes or 0,
        'duration_s': song.duration_s or 0,
        'bitrate': song.bitrate or 0,
        'lyric': song.lyric or '',
        'cover_url': song.cover_url or '',
        'source': song.source or '',
        'download_url': _normalize_download_url(song.download_url),
        'root_source': song.root_source or '',
    }


def _normalize_download_url(url) -> str:
    """将 musicdl 的各种 download_url 格式归一化为字符串"""
    if not url:
        return ''
    if isinstance(url, str):
        return url
    if isinstance(url, list):
        for item in url:
            if isinstance(item, dict):
                u = item.get('url') or item.get('dlurl') or ''
                if u:
                    return u
        return ''
    if isinstance(url, dict):
        return url.get('url') or url.get('dlurl') or ''
    return str(url)


def search(keyword: str, source: str, limit: int = 0, quality: str = 'lossless') -> list[dict]:
    """搜索歌曲，返回统一格式的搜索结果列表"""
    cache_key = f'{source}:{keyword}:{limit}'
    # musicdl 的 search_size_per_source 控制每个平台搜索多少条数据
    # search_size=15 通常返回 10~15 条结果（足够日常使用）
    search_size = 15
    raw_songs = _do_search(keyword, source, search_size)

    # 转为统一格式（传入用户请求音质，让 converter 做 qualityMap 过滤）
    songs = []
    for raw in raw_songs:
        try:
            songs.append(musicdl_to_search_song(raw, source, requested=quality))
        except Exception:
            continue

    # 按 limit 截断后缓存
    result = songs[:limit] if limit > 0 else songs
    _search_cache[cache_key] = result
    return result


def get_song(song_id: str, source: str, keyword: str = '', quality: str = 'lossless') -> Optional[dict]:
    """获取单曲信息，返回 /song 接口格式"""
    raw = _find_in_cache(song_id, source, keyword)
    if not raw:
        return None

    # 缓存命中但没有下载 URL → 用 musicdl 平台 client 直接解析
    if not raw.get('download_url'):
        _resolve_song_url(raw, song_id, source, quality=quality)

    return musicdl_to_song_info(raw, source, level=quality)


def _resolve_song_url(raw: dict, song_id: str, source: str, quality: str = 'lossless'):
    """用 musicdl 平台 client 的 _parsewiththirdpartapis 快速解析单曲下载 URL"""
    _log = __import__('logging').getLogger(__name__)
    raw_key = f'{source}:{song_id}'
    raw_search = _raw_search_cache.get(raw_key)
    if not raw_search:
        # 尝试带前缀的 key（kuwo 可能存为 MUSIC_xxx）
        alt_key = f'{source}:MUSIC_{song_id}'
        raw_search = _raw_search_cache.get(alt_key)
        if not raw_search:
            _log.warning('resolve_song_url: raw_search not found for %s', raw_key)
            return
    client = _get_client(source)
    if not client:
        return

    client_name = PLATFORM_MAP.get(source)
    if not client_name:
        return

    platform_client = client.music_clients.get(client_name)
    if not platform_client:
        return

    # ===== 各平台音质档位截断配置 =====
    # key: platform, value: (导入路径, 类/变量名, 属性名, {quality→截断下标})
    _QUALITY_LIST_CONF = {
        'qq': ('musicdl.modules.utils.qqutils', 'SongFileType', 'SORTED_QUALITIES',
               {'lossless': 3, 'exhigh': 8, 'standard': 9}),
        'netease': ('musicdl.modules.utils.neteaseutils', None, 'MUSIC_QUALITIES',
                    {'hires': 3, 'lossless': 4, 'exhigh': 6, 'standard': 7}),
        'kugou': ('musicdl.modules.utils.kugouutils', None, 'MUSIC_QUALITIES',
                  {'lossless': 3, 'exhigh': 5, 'standard': 6}),
        'kuwo': ('musicdl.modules.sources.kuwo', 'KuwoMusicClient', 'MUSIC_QUALITIES',
                 {'lossless': 0, 'exhigh': 1, 'standard': 1}),
    }
    _conf = _QUALITY_LIST_CONF.get(source)
    _truncate_idx = _conf[3].get(quality) if _conf else None
    _log.info(f'resolve_song_url: source={source}, 请求音质={quality}, 截断索引={_truncate_idx}')

    # 预加载截断目标所在的模块/类
    _quality_container = None
    if _truncate_idx is not None and _conf is not None:
        try:
            _mod_path, _cls_name, _attr_name = _conf[0], _conf[1], _conf[2]
            import importlib
            _mod = importlib.import_module(_mod_path)
            _quality_container = getattr(_mod, _cls_name) if _cls_name else _mod
        except Exception:
            _log.warning(f'resolve_song_url: 无法加载 {_conf[0]}.{_conf[1] or ""}，不截断')

    try:
        with contextlib.redirect_stdout(sys.stderr):
            platform_client._initsession()
            request_overrides = {}
            song_info = platform_client._parsewiththirdpartapis(
                search_result=raw_search,
                request_overrides=request_overrides,
            )

            # 低音质请求：丢弃第三方 API 结果 + 截断音质列表让 musicdl 只尝试对应档位
            _ql = None
            _ql_snapshot = None
            _ql_is_tuple = False
            if _truncate_idx is not None and _quality_container is not None:
                _ql = getattr(_quality_container, _conf[2], None)
                if _ql is not None:
                    import enum
                    if isinstance(_ql, enum.Enum):
                        # QQ: SORTED_QUALITIES 是 enum 成员，通过 .value 获取底层列表
                        _ql_snapshot = list(_ql.value)
                        _ql.value[:] = _ql.value[_truncate_idx:]
                    elif isinstance(_ql, tuple):
                        _ql_is_tuple = True
                        _ql_snapshot = _ql
                        setattr(_quality_container, _conf[2], _ql[_truncate_idx:])
                        # 某些平台（如 kugou）的 _parsewithofficialapiv1 通过
                        # from ... import 本地引用，setattr 对定义模块不生效，
                        # 需直接修补源模块的全局变量
                        _src_mod_map = {'kugou': 'musicdl.modules.sources.kugou'}
                        _src_path = _src_mod_map.get(source)
                        if _src_path:
                            try:
                                setattr(importlib.import_module(_src_path), _conf[2], _ql[_truncate_idx:])
                            except Exception:
                                pass
                    else:
                        _ql_snapshot = list(_ql)
                        _ql[:] = _ql[_truncate_idx:]
                song_info = None

            try:
                song_info = platform_client._parsewithofficialapiv1(
                    search_result=raw_search,
                    song_info_flac=song_info,
                    lossless_quality_is_sufficient=_truncate_idx is None,
                    lossless_quality_definitions={'flac', 'm4a', 'ogg', 'ape', 'wav'},
                    request_overrides=request_overrides,
                )
            finally:
                if _ql_snapshot is not None and _quality_container is not None:
                    if isinstance(_ql, enum.Enum):
                        _ql.value[:] = _ql_snapshot
                    elif _ql_is_tuple:
                        setattr(_quality_container, _conf[2], _ql_snapshot)
                        # 恢复源模块的全局变量
                        _src_mod_map = {'kugou': 'musicdl.modules.sources.kugou'}
                        _src_path = _src_mod_map.get(source)
                        if _src_path:
                            try:
                                setattr(importlib.import_module(_src_path), _conf[2], _ql_snapshot)
                            except Exception:
                                pass
                    else:
                        _ql[:] = _ql_snapshot
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'resolve_song_url error for {source}:{song_id}: {e}')
        return
    finally:
        _cleanup_output(client)

    if song_info and song_info.download_url:
        raw['download_url'] = _normalize_download_url(song_info.download_url)
        raw['ext'] = song_info.ext or raw.get('ext', 'mp3')
        raw['bitrate'] = song_info.bitrate or raw.get('bitrate', 0)
        raw['file_size_bytes'] = song_info.file_size_bytes or raw.get('file_size_bytes', 0)
        raw['lyric'] = song_info.lyric or raw.get('lyric', '')
        raw['cover_url'] = song_info.cover_url or raw.get('cover_url', '')
        # musicdl 解析器通常不填写 file_size_bytes，用 Range 请求获取实际 Content-Length
        if not raw['file_size_bytes'] and raw['download_url']:
            _url = raw['download_url']
            try:
                import requests as _req
                import re as _re
                r = _req.get(
                    _url,
                    headers={'Range': 'bytes=0-0', 'Referer': 'https://music.163.com'},
                    timeout=10,
                )
                cr = r.headers.get('Content-Range') or r.headers.get('content-range', '')
                m = _re.search(r'/(\d+)$', cr)
                if m:
                    raw['file_size_bytes'] = int(m.group(1))
            except Exception:
                pass
        # 用实际解析后的 size/br 重建 quality_map
        from .converter import _build_quality_map
        raw['quality_map'] = _build_quality_map(raw['ext'], raw['file_size_bytes'], raw['bitrate'])
        # 更新缓存
        for cache_key, songs in list(_search_cache.items()):
            if cache_key.startswith(f'{source}:'):
                for i, s in enumerate(songs):
                    if str(s.get('identifier', '')) == str(song_id):
                        _search_cache[cache_key][i] = raw
                        break


def _find_in_cache(song_id: str, source: str, keyword: str = '') -> Optional[dict]:
    """在缓存中查找歌曲"""
    if keyword:
        cache_key = f'{source}:{keyword}'
        if cache_key in _search_cache:
            for s in _search_cache[cache_key]:
                if str(s.get('identifier', '')) == str(song_id):
                    return s

    for cache_key, songs in _search_cache.items():
        if cache_key.startswith(f'{source}:'):
            for s in songs:
                if str(s.get('identifier', '')) == str(song_id):
                    return s

    if keyword != song_id:
        raw = _do_search(song_id, source)
        if raw:
            cache_key = f'{source}:{song_id}'
            _search_cache[cache_key] = raw
            for s in raw:
                if str(s.get('identifier', '')) == str(song_id):
                    return s
            return raw[0]

    return None
