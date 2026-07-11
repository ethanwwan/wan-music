"""musicdl 流式搜索 — 直接请求平台 API，不经过 _search（更快）

关键改动：不调用 musicdl 的 _search（它会逐个解析音频 URL，很慢且不稳定），
而是平台 client 的 session 直接请求搜索 API，只获取元数据就返回，不解析音频 URL。

参考:
  https://github.com/CharlesPikachu/musicdl/tree/master/examples/claudeai-modern-web-music-player
"""
import contextlib
import json
import logging
import sys
import time

from . import converter
from .adapter import PLATFORM_MAP, _get_client, _cleanup_output

logger = logging.getLogger(__name__)

PER_SOURCE_TIMEOUT = 20
SEARCH_SIZE = 50  # 前端 limit 默认 50


def _get_ci(d: dict, *keys):
    """Case-insensitive key lookup — 依次尝试各 key，匹配大小写"""
    for key in keys:
        if key in d:
            return d[key]
    # fallback: 小写匹配
    lower_map = {k.lower(): k for k in d}
    for key in keys:
        if key.lower() in lower_map:
            return d[lower_map[key.lower()]]
    return ''


def _get_ci_int(d: dict, *keys) -> int:
    val = _get_ci(d, *keys)
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _extract_singers(search: dict, source: str) -> str:
    """"""
    artists = search.get('ar') or search.get('artists') or search.get('singer') or search.get('SingerName') or search.get('ARTIST') or search.get('artist') or []
    if isinstance(artists, str):
        return artists
    if isinstance(artists, list):
        names = [a.get('name', '') if isinstance(a, dict) else str(a) for a in artists]
        return ', '.join(n for n in names if n)
    if isinstance(artists, dict):
        return artists.get('name', '')
    return str(artists) if artists else ''


def _extract_album(search: dict) -> str:
    album = search.get('album') or search.get('al') or search.get('ALBUM') or search.get('AlbumName') or {}
    if isinstance(album, str):
        return album
    if isinstance(album, dict):
        return album.get('name', '') or album.get('title', '')
    return str(album) if album else ''


def _extract_cover(search: dict) -> str:
    album = search.get('album') or search.get('al') or {}
    if isinstance(album, dict):
        pic = album.get('picUrl') or album.get('picurl') or album.get('pic') or ''
        if pic:
            return pic
    albummid = search.get('albummid') or (album.get('albumMID') if isinstance(album, dict) else None)
    if albummid and 'y.qq.com' not in str(albummid):
        return f'https://y.qq.com/music/photo_new/T002R300x300M000{albummid}.jpg'
    return search.get('picUrl') or search.get('pic') or ''


def _parse_kuwo_minfo(minfo: str) -> dict:
    """解析 Kuwo MINFO/N_MINFO 字符串，返回 {quality: {br, size}}
    
    格式: level:ff,bitrate:2000,format:flac,size:31.36Mb;level:p,bitrate:320,format:mp3,size:12.39Mb;...
    level 映射:
      ff → lossless (FLAC), p → exhigh (320k mp3), h → standard (128k mp3)
      bcms → dolby, dtsx → sky, zply → jymaster, zpga* → hires
    """
    import re
    qmap = {}
    level_map = {
        'ff': 'lossless', 'p': 'exhigh', 'h': 'standard',
        'bcms': 'dolby', 'dtsx': 'sky', 'zply': 'jymaster',
    }
    for seg in minfo.split(';'):
        seg = seg.strip()
        if not seg:
            continue
        parts = dict(item.split(':', 1) for item in seg.split(',') if ':' in item)
        level_key = parts.get('level', '')
        bitrate = int(parts.get('bitrate', 0))
        size_str = parts.get('size', '0')
        # 解析 size: "31.36Mb" → bytes
        size_bytes = 0
        m = re.match(r'([\d.]+)\s*([KkMmGg]?[Bb]?)', size_str)
        if m:
            val = float(m.group(1))
            unit = m.group(2).lower()
            if 'g' in unit:
                size_bytes = int(val * 1024**3)
            elif 'm' in unit:
                size_bytes = int(val * 1024**2)
            elif 'k' in unit:
                size_bytes = int(val * 1024)
            else:
                size_bytes = int(val)
        # 映射 level → quality
        quality = level_map.get(level_key)
        if quality:
            qmap[quality] = {'br': bitrate, 'size': size_bytes}
        # zpga* → hires
        if level_key.startswith('zpga'):
            qmap['hires'] = {'br': bitrate, 'size': size_bytes}
    return qmap


def _extract_quality_map(raw: dict, source: str) -> dict:
    """从各平台搜索 API 原始响应中提取 qualityMap
    
    各平台搜索 API 原生返回音质信息，字段名和结构各不相同：
      - netease: 搜索阶段不返回音质信息，默认 standard
      - qq:      file 对象中有 size_* 字段（size_flac, size_320mp3 等）
      - kugou:   顶层字段 Bitrate/FileSize/ExtName + HQ* + SQ* + Res*
      - kuwo:    MINFO/N_MINFO 字符串编码多品质信息
    """
    qmap = {}

    if source == 'netease':
        qmap['standard'] = {'br': 128, 'size': 0}

    elif source == 'qq':
        file_info = raw.get('file') or {}
        if isinstance(file_info, dict):
            qq_rules = [
                ('size_hires', 'hires', 9999),
                ('size_ape', 'hires', 9999),
                ('size_flac', 'lossless', 1411),
                ('size_dolby', 'dolby', 9999),
                ('size_dts', 'sky', 9999),
                ('size_320mp3', 'exhigh', 320),
                ('size_192ogg', 'exhigh', 192),
                ('size_192aac', 'exhigh', 192),
                ('size_128mp3', 'standard', 128),
            ]
            for field, quality, default_br in qq_rules:
                size = int(file_info.get(field, 0) or 0)
                if size > 0:
                    qmap[quality] = {'br': default_br, 'size': size}
            if not qmap:
                qmap['standard'] = {'br': 128, 'size': 0}

    elif source == 'kugou':
        kugou_rules = [
            ('ResFileSize', 'ResBitrate', 'hires'),
            ('SQFileSize', 'SQBitrate', 'lossless'),
            ('HQFileSize', 'HQBitrate', 'exhigh'),
            ('FileSize', 'Bitrate', 'standard'),
        ]
        for size_field, br_field, quality in kugou_rules:
            size = int(raw.get(size_field, 0) or 0)
            br = int(raw.get(br_field, 0) or 0)
            if size > 0:
                qmap[quality] = {'br': br, 'size': size}

    elif source == 'kuwo':
        for field in ('N_MINFO', 'MINFO'):
            val = raw.get(field, '')
            if isinstance(val, str) and val.strip():
                parsed = _parse_kuwo_minfo(val)
                if parsed:
                    qmap.update(parsed)
                    break

    if not qmap:
        qmap['standard'] = {'br': 128, 'size': 0}

    return qmap


def _raw_to_search_song(raw: dict, source: str) -> dict:
    """搜索 API 原始结果 → 统一搜索格式
    
    不同平台的 key 命名不同：
      - netease: id, name, ar, al (小写)
      - qq:      mid(作为 id), title, singer[].name, album.title (小写)
      - kugou:   ID, SongName, SingerName, AlbumName (驼峰大写)
      - kuwo:    MUSICRID, NAME, ARTIST, ALBUM (全大写)
    """
    song_id = _get_ci(raw, 'id', 'ID', 'mid', 'MUSICRID', 'songmid')
    if song_id and (source == 'kuwo' or isinstance(song_id, str) and song_id.startswith('MUSIC_')):
        song_id = str(song_id).removeprefix('MUSIC_')

    song_name = _get_ci(raw, 'name', 'NAME', 'SongName', 'title', 'songname', 'SONGNAME')
    # 清理 kuwo 的污损名
    if isinstance(song_name, str) and '&' in song_name and source == 'kuwo':
        import html
        song_name = html.unescape(song_name)

    duration_ms = _get_ci_int(raw, 'duration', 'DURATION', 'dt', 'interval')
    if not duration_ms:
        duration_ms = 0

    quality_map = _extract_quality_map(raw, source)

    raw_dict = {
        'identifier': str(song_id) if song_id else '',
        'song_name': str(song_name) if song_name else '',
        'singers': _extract_singers(raw, source),
        'album': _extract_album(raw),
        'cover_url': _extract_cover(raw),
        'quality_map': quality_map,
        'duration_s': duration_ms / 1000 if duration_ms else 0,
    }
    return converter.musicdl_to_search_song(raw_dict, source)


def _parse_songs(raw_data: dict, client_name: str) -> list[dict]:
    """从平台 API 原始响应中提取歌曲列表
    
    musicdl 各平台 _constructsearchurls 的响应结构差异很大，
    需按实际 API 返回的 JSON 路径提取。
    """
    if client_name == 'NeteaseMusicClient':
        return raw_data.get('result', {}).get('songs', [])
    elif client_name == 'QQMusicClient':
        # QQ 搜索 API 返回动态模块 key（如 music.search.SearchCgiService.DoSearchForQQMusicMobile），
        # 需要找到第一个以 "music." 开头的 key，然后取 data.body.item_song
        for k, v in raw_data.items():
            if k.startswith('music.') and isinstance(v, dict):
                body = v.get('data', {}).get('body', {})
                if not isinstance(body, dict):
                    continue
                # item_song 是歌曲列表，item_album/singer 等的键类似
                songs = body.get('item_song', [])
                if songs:
                    return songs
        return []
    elif client_name == 'KuwoMusicClient':
        # Kuwo 搜索返回 abslist（顶层 key 就是歌曲列表）
        return raw_data.get('abslist', [])
    elif client_name == 'KugouMusicClient':
        # Kugou 搜索返回 data.lists（包含每首歌曲信息）
        return raw_data.get('data', {}).get('lists', [])
    return []


def search_via_http(keyword: str, source: str) -> list[dict]:
    """直接用平台 client 的 session 请求搜索 API，返回统一格式结果

    不使用 musicdl 的 _search（解析 URL 太慢），只用 _constructsearchurls
    构造请求参数，然后手动发 HTTP 请求获取元数据。

    不同平台 _constructsearchurls 返回格式：
      - netease: list[dict] with 'url'(str) + 'data'(dict) + 'page'(int)
      - qq:      list[dict] with 'url'(str) + 'data'(bytes) + 'page_no'(int)
      - kugou:   list[str]  (完整 GET URL)
      - kuwo:    list[str]  (完整 GET URL)
    """
    client_name = PLATFORM_MAP.get(source)
    if not client_name:
        return []

    client = _get_client(source)
    if not client:
        return []

    platform_client = client.music_clients.get(client_name)
    if not platform_client:
        return []

    try:
        with contextlib.redirect_stdout(sys.stderr):
            search_urls = platform_client._constructsearchurls(
                keyword=keyword, rule={}, request_overrides={}
            )
    except Exception as e:
        logger.error(f"构造搜索 URL 失败: {e}")
        return []

    if not search_urls:
        return []

    logger.info(f"search_via_http: {len(search_urls)} 个 URL, keyword={keyword!r}, source={source}")

    results = []
    seen_ids = set()

    for idx, url_info in enumerate(search_urls):
        # 处理 list[str] 格式 (kugou, kuwo) — 完整 URL，GET 请求
        if isinstance(url_info, str):
            page_url = url_info
            page_no = idx + 1
            is_get = True
            extra_kwargs = {}
        else:
            page_url = url_info.pop('url', '')
            page_no = url_info.pop('page', url_info.pop('page_no', idx + 1))
            is_get = False
            extra_kwargs = url_info

        # 记录实际请求 URL
        logger.info(f"search_via_http URL {idx+1}: {page_url}")

        songs = []
        for attempt in range(3):
            try:
                platform_client.default_headers = platform_client.default_search_headers
                if hasattr(platform_client, 'default_search_cookies'):
                    platform_client.default_cookies = platform_client.default_search_cookies
                platform_client._initsession()

                if is_get:
                    resp = platform_client.get(page_url, **extra_kwargs)
                else:
                    resp = platform_client.post(page_url, **extra_kwargs)

                if resp.status_code != 200:
                    logger.warning(f"搜索请求状态码 {resp.status_code} (attempt {attempt+1})")
                    continue

                raw_data = resp.json()
                songs = _parse_songs(raw_data, client_name)
                logger.info(f"search_via_http: page {page_no}, API 返回 {len(songs)} 条结果 (attempt {attempt+1})")
                break
            except Exception as e:
                logger.warning(f"搜索请求失败 (attempt {attempt+1}): {e}")
                songs = []
                continue

        for s in songs:
                sid = str(_get_ci(s, 'id', 'ID', 'mid', 'MUSICRID', 'songmid') or '')
                if sid and sid not in seen_ids:
                    seen_ids.add(sid)
                    try:
                        results.append(_raw_to_search_song(s, source))
                    except Exception:
                        continue

    return results[:SEARCH_SIZE]


def search_stream(keyword: str, source: str, timeout: int = PER_SOURCE_TIMEOUT):
    """流式搜索结果，逐条 yield（基于 HTTP 直接搜索，不解析 URL）"""
    try:
        songs = search_via_http(keyword, source)
    except Exception as e:
        logger.error(f"search_via_http 异常: {e}", exc_info=True)
        songs = []

    for s in songs:
        yield {'type': 'result', 'song': s}

    yield {'type': 'source_done', 'count': len(songs)}

    # 清理 musicdl 自动创建的输出目录
    client = _get_client(source)
    if client:
        try:
            _cleanup_output(client)
        except Exception:
            pass

    yield {'type': 'done', 'count': len(songs)}
