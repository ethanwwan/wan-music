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


def _extract_singers(search: dict, source: str) -> str:
    """从 search 结果中提取歌手名"""
    artists = search.get('ar') or search.get('artists') or search.get('singer') or []
    if isinstance(artists, list):
        names = [a.get('name', '') if isinstance(a, dict) else str(a) for a in artists]
        return ', '.join(n for n in names if n)
    if isinstance(artists, dict):
        return artists.get('name', '')
    return str(artists) if artists else ''


def _extract_album(search: dict) -> str:
    album = search.get('album') or search.get('al') or {}
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


def _raw_to_search_song(raw: dict, source: str) -> dict:
    """搜索 API 原始结果 → 统一搜索格式"""
    duration_ms = raw.get('duration', raw.get('dt', raw.get('interval', 0))) or 0
    raw_dict = {
        'identifier': str(raw.get('id', '')),
        'song_name': raw.get('name', '') or raw.get('title', ''),
        'singers': _extract_singers(raw, source),
        'album': _extract_album(raw),
        'cover_url': _extract_cover(raw),
        'ext': 'mp3',
        'file_size_bytes': 0,
        'bitrate': 0,
        'duration_s': duration_ms / 1000 if duration_ms else 0,
    }
    return converter.musicdl_to_search_song(raw_dict, source)


def _parse_songs(raw_data: dict, client_name: str) -> list[dict]:
    """从平台 API 原始响应中提取歌曲列表"""
    if client_name == 'NeteaseMusicClient':
        return raw_data.get('result', {}).get('songs', [])
    elif client_name == 'QQMusicClient':
        return raw_data.get('req_0', {}).get('data', {}).get('body', {}).get('song', {}).get('list', [])
    elif client_name == 'KuwoMusicClient':
        return raw_data.get('data', {}).get('list', [])
    elif client_name == 'KugouMusicClient':
        return raw_data.get('data', {}).get('info', [])
    return []


def search_via_http(keyword: str, source: str) -> list[dict]:
    """直接用平台 client 的 session 请求搜索 API，返回统一格式结果

    不使用 musicdl 的 _search（解析 URL 太慢），只用 _constructsearchurls
    构造请求参数，然后手动发 HTTP 请求获取元数据。
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
        page_url = url_info.pop('url', '')
        page_no = url_info.pop('page', idx + 1)

        # 记录实际请求 URL 和 keyword 编码
        logger.info(f"search_via_http URL {idx+1}: {page_url}")
        logger.info(f"search_via_http url_info: data keys={list(url_info.get('data', {}).keys()) if url_info.get('data') else 'no data'}")

        songs = []  # 默认空
        # 重试逻辑：musicdl 的 post() 有 max_retries=3，每次重试用不同 cookies/proxies
        for attempt in range(3):
            try:
                # 让 musicdl 的 post 自己处理 session 重试
                platform_client.default_headers = platform_client.default_search_headers
                if hasattr(platform_client, 'default_search_cookies'):
                    platform_client.default_cookies = platform_client.default_search_cookies
                platform_client._initsession()

                resp = platform_client.post(page_url, **url_info)
                if resp.status_code != 200:
                    logger.warning(f"搜索请求状态码 {resp.status_code} (attempt {attempt+1})")
                    continue

                raw_data = resp.json()
                songs = _parse_songs(raw_data, client_name)
                logger.info(f"search_via_http: page {page_no}, API 返回 {len(songs)} 条结果 (attempt {attempt+1})")
                break  # 成功就跳出重试循环
            except Exception as e:
                logger.warning(f"搜索请求失败 (attempt {attempt+1}): {e}")
                songs = []
                continue

        for s in songs:
                sid = str(s.get('id', ''))
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
