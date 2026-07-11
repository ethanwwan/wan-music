"""musicdl SongInfo → 统一 API 格式转换器

将 musicdl 代理返回的歌曲 dict 转换为前端 /search 和 /song 接口需要的格式。
"""

_UNIFIED_QUALITY_PRIORITY = [
    'jymaster', 'jysurround', 'dolby', 'sky', 'jyeffect', 'hires', 'lossless', 'exhigh', 'standard'
]


def _match_quality(quality_map: dict, requested: str = 'lossless') -> str:
    """根据用户请求音质匹配实际可用音质（从高到低降级）"""
    if not quality_map:
        return ''
    if requested in quality_map:
        return requested
    try:
        start = _UNIFIED_QUALITY_PRIORITY.index(requested)
    except ValueError:
        start = len(_UNIFIED_QUALITY_PRIORITY)
    for qk in _UNIFIED_QUALITY_PRIORITY[start:]:
        if qk in quality_map:
            return qk
    for qk in _UNIFIED_QUALITY_PRIORITY:
        if qk in quality_map:
            return qk
    return next(iter(quality_map), '')


def musicdl_to_search_song(s: dict, source: str, requested: str = 'lossless') -> dict:
    """musicdl 搜索歌曲 → 统一搜索格式"""
    song_id = str(s.get('identifier', ''))
    song_name = s.get('song_name', '') or ''
    singers = s.get('singers', '') or ''
    album = s.get('album', '') or ''
    ext = s.get('ext', 'mp3') or 'mp3'
    duration_s = s.get('duration_s', 0) or 0

    # 优先使用预构建的 quality_map（流式搜索时各平台已有完整音质信息）
    quality_map = s.get('quality_map') or _build_quality_map(
        ext,
        s.get('file_size_bytes', 0) or 0,
        s.get('bitrate', 0) or 0,
    )

    # 根据用户请求音质降级匹配最佳可用音质（而非取最高）
    best_quality = _match_quality(quality_map, requested) or 'standard'

    duration_ms = duration_s * 1000
    return {
        'id': song_id,
        'name': song_name,
        'artist': singers,
        'artists': singers,  # 兼容前端 mapSearchSong
        'album': album,
        'pic': s.get('cover_url', ''),
        'picUrl': s.get('cover_url', ''),  # 兼容前端 mapSearchSong
        'qualityMap': quality_map,
        'bestQuality': best_quality,
        'source': source,
        'api_source': 'musicdl',
        'fee': s.get('fee', 1),
        'pay': s.get('pay', False),
        'url': '',  # 搜索阶段不返回 URL
        'duration': duration_ms,       # 前端 mapSearchSong 读这个
        'songTime': duration_ms,       # 兼容旧版
    }


def musicdl_to_song_info(s: dict, source: str, level: str = 'lossless') -> dict:
    """musicdl 歌曲信息 → /song 接口格式"""
    song_id = str(s.get('identifier', ''))
    song_name = s.get('song_name', '') or ''
    singers = s.get('singers', '') or ''
    album = s.get('album', '') or ''
    ext = s.get('ext', 'mp3') or 'mp3'
    duration_s = s.get('duration_s', 0) or 0
    file_size_bytes = s.get('file_size_bytes', 0) or 0
    bitrate = s.get('bitrate', 0) or 0
    download_url = s.get('download_url', '') or ''
    lyric = s.get('lyric', '') or ''

    quality_map = _build_quality_map(ext, file_size_bytes, bitrate)
    actual_level = _detect_level(ext, quality_map, level)

    return {
        'id': song_id,
        'name': song_name,
        'artist': singers,
        'artists': singers,  # 兼容前端
        'album': album,
        'cover': s.get('cover_url', ''),
        'duration': duration_s * 1000,
        'url': download_url,
        'level': actual_level,
        'requested_level': level,
        'level_fallback': level != actual_level,
        'fileType': ext,
        'source': source,
        'api_source': 'musicdl',
        'available': bool(download_url),
        'lyric': lyric,
        'br': quality_map.get(actual_level, {}).get('br', 0),
        'size': file_size_bytes,
    }


def _build_quality_map(ext: str, file_size_bytes: int, bitrate: int) -> dict:
    """根据文件信息构建 qualityMap"""
    quality_map = {}
    ext = (ext or 'mp3').lower()

    if ext in ('flac', 'ape', 'wav'):
        quality_map['lossless'] = {'br': 1411, 'size': file_size_bytes}
    elif ext == 'm4a':
        quality_map['lossless'] = {'br': 1411, 'size': file_size_bytes}
    elif ext == 'ogg':
        quality_map['exhigh'] = {'br': 320, 'size': file_size_bytes}
    elif ext == 'mp3':
        if bitrate >= 320:
            quality_map['exhigh'] = {'br': 320, 'size': file_size_bytes}
        elif bitrate >= 192:
            quality_map['standard'] = {'br': 192, 'size': file_size_bytes}
        else:
            quality_map['standard'] = {'br': 128, 'size': file_size_bytes}
    else:
        quality_map['standard'] = {'br': 128, 'size': file_size_bytes}

    return quality_map


def _detect_level(ext: str, quality_map: dict, requested: str) -> str:
    """根据请求音质匹配实际可用音质（而非取最高）"""
    return _match_quality(quality_map, requested) or 'standard'


def merge_singers(singers) -> str:
    """歌手名格式化为逗号分隔字符串"""
    if isinstance(singers, str):
        return singers
    if isinstance(singers, list):
        return ', '.join(singers)
    return str(singers) if singers else ''
