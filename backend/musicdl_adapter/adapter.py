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


def _get_client(source: str, search_size: int = 5) -> Optional[musicdl.MusicClient]:
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


def search(keyword: str, source: str, limit: int = 0) -> list[dict]:
    """搜索歌曲，返回统一格式的搜索结果列表"""
    cache_key = f'{source}:{keyword}:{limit}'
    # musicdl 的 search_size_per_source 控制每个平台搜索多少条数据
    # search_size=15 通常返回 10~15 条结果（足够日常使用）
    search_size = 15
    raw_songs = _do_search(keyword, source, search_size)

    # 转为统一格式
    songs = []
    for raw in raw_songs:
        try:
            songs.append(musicdl_to_search_song(raw, source))
        except Exception:
            continue

    # 按 limit 截断后缓存
    result = songs[:limit] if limit > 0 else songs
    _search_cache[cache_key] = result
    return result


def get_song(song_id: str, source: str, keyword: str = '') -> Optional[dict]:
    """获取单曲信息，返回 /song 接口格式"""
    raw = _find_in_cache(song_id, source, keyword)
    if not raw:
        return None
    return musicdl_to_song_info(raw, source)


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
