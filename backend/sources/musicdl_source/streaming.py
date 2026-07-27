"""musicdl 流式搜索 — 直接请求平台 API，不经过 _search（更快）

关键改动：不调用 musicdl 的 _search（它会逐个解析音频 URL，很慢且不稳定），
而是平台 client 的 session 直接请求搜索 API，只获取元数据就返回，不解析音频 URL。

参考:
  https://github.com/CharlesPikachu/musicdl/tree/master/examples/claudeai-modern-web-music-player
"""
import contextlib
import json
import logging
import queue
import sys
import threading
import time

from . import converter
from .adapter import PLATFORM_MAP, _get_client, _cleanup_output, _search_cache, _raw_search_cache

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


def _extract_cover(search: dict, source: str) -> str:
    """从搜索 API 原始响应中提取封面 URL"""
    # 1. Netease: al.picUrl
    album = search.get('album') or search.get('al') or {}
    if isinstance(album, dict):
        pic = album.get('picUrl') or album.get('picurl') or album.get('pic') or ''
        if pic:
            return pic
    # 2. QQ: 构造 y.gtimg.cn URL (album.mid)
    if source == 'qq':
        albummid = search.get('albummid') or (
            album.get('mid') if isinstance(album, dict) else None
        )
        if albummid and 'y.qq.com' not in str(albummid):
            return f'https://y.gtimg.cn/music/photo_new/T002R300x300M000{albummid}.jpg'
    # 3. Kugou: Image 模板 (替换 {size})
    if source == 'kugou':
        img = search.get('Image') or search.get('image') or ''
        if img and '{size}' in img:
            return img.replace('{size}', '240')
        if img:
            return img
    # 4. Kuwo: hts_MVPIC (完整 URL) 或 MVPIC (相对路径)
    if source == 'kuwo':
        hts = search.get('hts_MVPIC') or ''
        if hts:
            return hts
        mvp = search.get('MVPIC') or ''
        if mvp:
            return f'https://img4.kuwo.cn/{mvp.lstrip("/")}'
    # 5. 通用兜底
    albummid = search.get('albummid') or (
        album.get('albumMID') if isinstance(album, dict) else None
    )
    if albummid and 'y.qq.com' not in str(albummid):
        return f'https://y.qq.com/music/photo_new/T002R300x300M000{albummid}.jpg'
    return search.get('picUrl') or search.get('pic') or ''


def _extract_fee(search: dict, source: str) -> tuple:
    """从搜索 API 原始响应中提取 (fee_number, pay_bool)
    
    fee: 0=免费, 1=付费, 4=免费播放(需VIP下载), 8=VIP
    pay: 前端使用的 boolean
    """
    if source == 'netease':
        fee = int(search.get('fee', 1) or 1)
        pay = fee in (1, 4, 8)
        return fee, pay

    if source == 'qq':
        # QQ item_song 的 action.msgpay 或 pay 对象
        action = search.get('action') or {}
        msgpay = int(action.get('msgpay', 0) or 0)
        pay_obj = search.get('pay') or {}
        if isinstance(pay_obj, dict):
            pp = int(pay_obj.get('pay_play', 0) or 0)
            pd = int(pay_obj.get('pay_download', 0) or 0)
            if pp or pd:
                return 1, True
        if msgpay > 0:
            return 1, True
        return 0, False

    if source == 'kugou':
        pay_type = int(search.get('PayType', 0) or 0)
        privilege = int(search.get('Privilege', 0) or 0)
        pay = pay_type > 0 or privilege < 10
        fee = 1 if pay else 0
        return fee, pay

    if source == 'kuwo':
        fee_type = search.get('payInfo', {}).get('feeType', {})
        if isinstance(fee_type, dict):
            song_fee = int(fee_type.get('song', 0) or 0)
            vip_fee = int(fee_type.get('vip', 0) or 0)
            pay = song_fee > 0 or vip_fee > 0
        else:
            # fallback: tpay/fpay
            tpay = int(search.get('tpay', 0) or 0)
            fpay = int(search.get('fpay', 0) or 0)
            pay = tpay > 0 or fpay > 0
        fee = 1 if pay else 0
        return fee, pay

    return 1, True  # 未知平台默认付费


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
        # Netease 搜索 API 返回 l(128k)/m(192k)/h(320k)/sq(flac)/hr(hires)
        # 优先级从高到低遍历，同一 quality 只保留最高
        # 注意：hr.br 是采样率(Hz)，不是比特率(bps)，不能除以 1000 当比特率使用
        for key, quality in [('hr', 'hires'), ('sq', 'lossless'),
                              ('h', 'exhigh'), ('m', 'standard'),
                              ('l', 'standard')]:
            if quality in qmap:
                continue
            info = raw.get(key)
            if isinstance(info, dict):
                br = int(info.get('br', 0) or 0)
                size = int(info.get('size', 0) or 0)
                if br > 0:
                    if key == 'hr':
                        # hr.br 是采样率(Hz)，非比特率；用 9999 占位
                        qmap[quality] = {'br': 9999, 'size': size}
                    else:
                        qmap[quality] = {'br': br // 1000, 'size': size}
        if not qmap:
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


def _raw_to_search_song(raw: dict, source: str, quality: str = 'lossless') -> dict:
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
    fee, pay = _extract_fee(raw, source)

    raw_dict = {
        'identifier': str(song_id) if song_id else '',
        'song_name': str(song_name) if song_name else '',
        'singers': _extract_singers(raw, source),
        'album': _extract_album(raw),
        'cover_url': _extract_cover(raw, source),
        'quality_map': quality_map,
        'fee': fee,
        'pay': pay,
        'duration_s': duration_ms / 1000 if duration_ms else 0,
    }
    return converter.musicdl_to_search_song(raw_dict, source, requested=quality)


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


def search_via_http(keyword: str, source: str, quality: str = 'lossless') -> list[dict]:
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
    all_raw_songs = []

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
                all_raw_songs.extend(songs)
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
                        results.append(_raw_to_search_song(s, source, quality=quality))
                    except Exception:
                        continue

    # 缓存原始歌曲元数据到 adapter._search_cache，供后续 get_song() 解析下载 URL
    try:
        cache_key = f'{source}:{keyword}'
        cache_entries = []
        for s in all_raw_songs:
            sid = str(_get_ci(s, 'id', 'ID', 'mid', 'MUSICRID', 'songmid') or '')
            if not sid:
                continue
            # 归一化 kuwo 的 MUSIC_ 前缀，保持与前端 id 一致
            if source == 'kuwo' and sid.startswith('MUSIC_'):
                sid = sid.removeprefix('MUSIC_')
            song_name = str(_get_ci(s, 'name', 'NAME', 'SongName', 'title', 'songname', 'SONGNAME') or '')
            if not song_name:
                continue
            # 元数据缓存：供 _find_in_cache 查找
            cache_entries.append({
                'identifier': str(sid),
                'song_name': song_name,
                'singers': _extract_singers(s, source),
                'album': _extract_album(s),
                'ext': 'mp3',
                'file_size_bytes': 0,
                'duration_s': _get_ci_int(s, 'duration', 'DURATION', 'dt', 'interval') / 1000 or 0,
                'bitrate': 0,
                'lyric': '',
                'cover_url': _extract_cover(s, source),
                'source': source,
                'download_url': '',
                'root_source': '',
            })
            # 原始响应缓存：供 _parsewiththirdpartapis 快速 URL 解析
            _raw_search_cache[f'{source}:{sid}'] = s
        if cache_entries:
            _search_cache[cache_key] = cache_entries
    except Exception:
        pass

    return results[:SEARCH_SIZE]


# ---------------------------------------------------------------------------
# 参考 https://github.com/CharlesPikachu/musicdl/tree/master/examples/claudeai-modern-web-music-player
# 的 search_stream 改写：
#   - 每个 page URL 一个后台 daemon 线程
#   - 主线程以 120ms 节奏轮询共享队列，emit 每一首新结果
#   - 全局 hard timeout（默认 PER_SOURCE_TIMEOUT=20s）作 watchdog，
#     防止某个平台触发反爬拖死 worker（Gunicorn 默认 worker_timeout=30s）
#   - 共享 threadsafe queue.Queue：跨线程通讯，避免锁复杂度
# ---------------------------------------------------------------------------

def _fetch_one_page(platform_client, is_get, page_url, extra_kwargs, page_no,
                    out_queue, seen_ids, seen_lock):
    """单 page 后台线程：拉一页搜索结果、把每一首歌推入 out_queue。

    异常一律 swallow（参考项目 _safe_search 同款兜底），不让一个失败 page 杀死整个搜索。
    """
    try:
        client_name = platform_client.__class__.__name__
        for attempt in range(3):
            try:
                # 重置 session headers/cookies（避免上一页 stale 状态污染本页）
                platform_client.default_headers = platform_client.default_search_headers
                if hasattr(platform_client, 'default_search_cookies'):
                    platform_client.default_cookies = platform_client.default_search_cookies
                platform_client._initsession()

                if is_get:
                    resp = platform_client.get(page_url, **extra_kwargs)
                else:
                    resp = platform_client.post(page_url, **extra_kwargs)

                if resp.status_code != 200:
                    logger.warning(f"page {page_no} 状态码 {resp.status_code} (attempt {attempt+1})")
                    continue

                raw_data = resp.json()
                songs = _parse_songs(raw_data, client_name)
                logger.info(f"search_via_http page {page_no}: 返回 {len(songs)} 条结果 (attempt {attempt+1})")

                # 元数据缓存（与原 search_via_http 保持一致，供后续 _find_in_cache 使用）
                try:
                    cache_key = f'{source}:{keyword}'
                    cache_entries = []
                    for s in songs:
                        sid_str = str(_get_ci(s, 'id', 'ID', 'mid', 'MUSICRID', 'songmid') or '')
                        if not sid_str:
                            continue
                        if source == 'kuwo' and sid_str.startswith('MUSIC_'):
                            sid_str = sid_str.removeprefix('MUSIC_')
                        song_name = str(_get_ci(s, 'name', 'NAME', 'SongName', 'title', 'songname', 'SONGNAME') or '')
                        if not song_name:
                            continue
                        cache_entries.append({
                            'identifier': str(sid_str),
                            'song_name': song_name,
                            'singers': _extract_singers(s, source),
                            'album': _extract_album(s),
                            'ext': 'mp3',
                            'file_size_bytes': 0,
                            'duration_s': _get_ci_int(s, 'duration', 'DURATION', 'dt', 'interval') / 1000 or 0,
                            'bitrate': 0,
                            'lyric': '',
                            'cover_url': _extract_cover(s, source),
                            'source': source,
                            'download_url': '',
                            'root_source': '',
                        })
                        # 原始响应缓存：供 _parsewiththirdpartapis 快速 URL 解析
                        _raw_search_cache[f'{source}:{sid_str}'] = s
                    if cache_entries:
                        _search_cache[cache_key] = cache_entries
                except Exception:
                    pass

                for s in songs:
                    sid = str(_get_ci(s, 'id', 'ID', 'mid', 'MUSICRID', 'songmid') or '')
                    if not sid:
                        continue
                    if source_is_kuwo(platform_client, sid):
                        sid = sid.removeprefix('MUSIC_')
                    with seen_lock:
                        if sid in seen_ids:
                            continue
                        seen_ids.add(sid)
                    # 平台 client 没有 .source 属性；搜索 keyword/sid 都从 raw dict 已经能拿到
                    out_queue.put(('result', s))
                out_queue.put(('page_done', page_no))  # ← 新增：成功 page 也通知主线程
                return  # 这一页成功，退出重试
            except Exception as e:
                logger.warning(f"page {page_no} 异常 (attempt {attempt+1}): {e}")
                continue
        # 三次都失败：emit 一个空 page_done 让主线程知道这条 page 结束了
        out_queue.put(('page_done', page_no))
    except Exception:
        # 参考项目 _safe_search 的兜底：任何未捕获异常一律静默
        out_queue.put(('page_done', page_no))


def source_is_kuwo(platform_client, sid):
    """轻微工具：判断是不是 kuwo 的 MUSIC_ 前缀 ID。"""
    return sid.startswith('MUSIC_') and 'Kuwo' in platform_client.__class__.__name__


def search_stream_concurrent(keyword: str, source: str, timeout: int = PER_SOURCE_TIMEOUT,
                              quality: str = 'lossless', poll_interval: float = 0.12):
    """真·流式搜索：参考 claudeai-modern-web-music-player 的并发轮询模型。

    Args:
        keyword:    搜索词
        source:     'netease'/'qq'/'kugou'/'kuwo'
        timeout:    硬性总超时（默认 PER_SOURCE_TIMEOUT=20s）
        quality:    给音质标记传给 _raw_to_search_song（默认 lossless）
        poll_interval:  主线程轮询 out_queue 的间隔（秒，默认 0.12）
    """
    client_name = PLATFORM_MAP.get(source)
    if not client_name:
        logger.warning(f"search_stream_concurrent: 未知 source={source!r}")
        yield {'type': 'source_done', 'count': 0, 'timed_out': False}
        yield {'type': 'done', 'count': 0}
        return

    client = _get_client(source)
    if not client:
        yield {'type': 'source_done', 'count': 0, 'timed_out': False}
        yield {'type': 'done', 'count': 0}
        return

    platform_client = client.music_clients.get(client_name)
    if not platform_client:
        yield {'type': 'source_done', 'count': 0, 'timed_out': False}
        yield {'type': 'done', 'count': 0}
        return

    try:
        with contextlib.redirect_stdout(sys.stderr):
            search_urls = platform_client._constructsearchurls(
                keyword=keyword, rule={}, request_overrides={}
            )
    except Exception as e:
        logger.error(f"构造搜索 URL 失败: {e}")
        yield {'type': 'source_done', 'count': 0, 'timed_out': False}
        yield {'type': 'done', 'count': 0}
        return

    if not search_urls:
        yield {'type': 'source_done', 'count': 0, 'timed_out': False}
        yield {'type': 'done', 'count': 0}
        return

    logger.info(f"search_stream_concurrent: {len(search_urls)} 个 page URL, keyword={keyword!r}, source={source}, timeout={timeout}s")

    out_queue = queue.Queue()
    seen_ids = set()
    seen_lock = threading.Lock()

    # 启动每个 page 的后台线程
    threads = []
    for idx, url_info in enumerate(search_urls):
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

        logger.info(f"search_stream_concurrent URL {idx+1}: {page_url}")
        t = threading.Thread(
            target=_fetch_one_page,
            args=(platform_client, is_get, page_url, extra_kwargs, page_no,
                  out_queue, seen_ids, seen_lock),
            daemon=True,
        )
        t.start()
        threads.append(t)

    deadline = time.time() + timeout
    total = 0
    pages_done = 0
    total_pages = len(threads)
    timed_out = False

    while True:
        # 非阻塞轮询 out_queue
        try:
            while True:
                kind, payload = out_queue.get_nowait()
                if kind == 'result':
                    raw_song = payload
                    try:
                        song = _raw_to_search_song(raw_song, source, quality=quality)
                    except Exception:
                        continue
                    total += 1
                    yield {'type': 'result', 'song': song}
                elif kind == 'page_done':
                    pages_done += 1
                    logger.info(f"search_stream_concurrent: page_done {payload}/{total_pages} (累计 {total} 条)")
        except queue.Empty:
            pass

        alive = any(t.is_alive() for t in threads)
        if (pages_done >= total_pages and not alive) or time.time() > deadline:
            if time.time() > deadline and alive:
                timed_out = True
                logger.warning(
                    f"search_stream_concurrent watchdog 超时 {timeout}s，发出 {total} 条"
                )
            break

        time.sleep(poll_interval)

    yield {'type': 'source_done', 'count': total, 'timed_out': timed_out}

    # 清理 musicdl 自动创建的输出目录
    try:
        _cleanup_output(client)
    except Exception:
        pass

    yield {'type': 'done', 'count': total}
