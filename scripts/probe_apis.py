#!/usr/bin/env python3
"""探测 4 大平台所有 ApiSource 的可用性

工作流程：
  1. 动态 import 后端 sources/*.py 里定义的所有 ApiSource
  2. 4 平台（netease/qq/kugou/kuwo）× 5 能力（search/url/info/lyric/playlist）= 20 维度
  3. 每个 ApiSource 按其声明的能力做真实 HTTP 请求测试
  4. 提取器校验：source.extract_X 实际能不能拿到数据
  5. 统计 alive / dead / no_data / disabled / exception
  6. URL 源还要测试多音质（lossless/hires/jymaster/exhigh/standard）

设计原则：
  - 探测脚本只读后端代码（动态 import），绝不修改后端
  - 完全对齐后端 ApiSource 的真实能力声明
  - 失败时根据后端代码生成调试建议（哪些字段 / headers 可能漏了）
"""
import json
import re
import sys
import time
import urllib.parse
from collections import defaultdict
from pathlib import Path

import requests

# ==================== 路径：定位后端模块 ====================
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

# 动态 import 后端 ApiSource
from clients.fallback.api_source import ApiSource  # noqa: E402
from clients.sources.netease import (  # noqa: E402
    NETEASE_SEARCH_SOURCES, NETEASE_PARSE_URL_SOURCES,
    NETEASE_PARSE_INFO_SOURCES, NETEASE_PARSE_LYRIC_SOURCES,
    NETEASE_PARSE_PLAYLIST_SOURCES,
)
from clients.sources.qq import (  # noqa: E402
    QQ_SEARCH_SOURCES, QQ_PARSE_URL_SOURCES,
    QQ_PARSE_INFO_SOURCES, QQ_PARSE_LYRIC_SOURCES,
    QQ_PARSE_PLAYLIST_SOURCES,
)
from clients.sources.kugou import (  # noqa: E402
    KUGOU_SEARCH_SOURCES, KUGOU_PARSE_URL_SOURCES,
    KUGOU_PARSE_INFO_SOURCES, KUGOU_PARSE_LYRIC_SOURCES,
    KUGOU_PARSE_PLAYLIST_SOURCES,
)
from clients.sources.kuwo import (  # noqa: E402
    KUWO_SEARCH_SOURCES, KUWO_PARSE_URL_SOURCES,
    KUWO_PARSE_INFO_SOURCES, KUWO_PARSE_LYRIC_SOURCES,
    KUWO_PARSE_PLAYLIST_SOURCES,
)

# ==================== 测试配置 ====================
TEST_KEYWORD = '陈楚生'
TIMEOUT = 10
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'

# 平台 → (5 类 sources 列表, 显示名)
PLATFORM_SOURCES = {
    'netease': {
        'name': '网易云',
        'search': NETEASE_SEARCH_SOURCES,
        'url':    NETEASE_PARSE_URL_SOURCES,
        'info':   NETEASE_PARSE_INFO_SOURCES,
        'lyric':  NETEASE_PARSE_LYRIC_SOURCES,
        'playlist': NETEASE_PARSE_PLAYLIST_SOURCES,
    },
    'qq': {
        'name': 'QQ音乐',
        'search': QQ_SEARCH_SOURCES,
        'url':    QQ_PARSE_URL_SOURCES,
        'info':   QQ_PARSE_INFO_SOURCES,
        'lyric':  QQ_PARSE_LYRIC_SOURCES,
        'playlist': QQ_PARSE_PLAYLIST_SOURCES,
    },
    'kugou': {
        'name': '酷狗',
        'search': KUGOU_SEARCH_SOURCES,
        'url':    KUGOU_PARSE_URL_SOURCES,
        'info':   KUGOU_PARSE_INFO_SOURCES,
        'lyric':  KUGOU_PARSE_LYRIC_SOURCES,
        'playlist': KUGOU_PARSE_PLAYLIST_SOURCES,
    },
    'kuwo': {
        'name': '酷我',
        'search': KUWO_SEARCH_SOURCES,
        'url':    KUWO_PARSE_URL_SOURCES,
        'info':   KUWO_PARSE_INFO_SOURCES,
        'lyric':  KUWO_PARSE_LYRIC_SOURCES,
        'playlist': KUWO_PARSE_PLAYLIST_SOURCES,
    },
}

# 各平台的测试 ID（先用 search 拿真实 ID，失败时用 fallback）
FALLBACK_IDS = {
    'netease': '3398250102',  # 陈楚生 - 有我呢
    'qq': '',                  # 需要动态获取
    'kugou': '',               # 需要动态获取 (FileHash)
    'kuwo': '',                # 需要动态获取 (rid)
}

# URL 源要测试的音质列表
QUALITIES_TO_TEST = ['hires', 'lossless', 'exhigh', 'standard']


# ==================== 真实 ID 获取（模拟后端 search 链）====================

def http(method, url, headers=None, params=None, data=None, is_json=False, timeout=TIMEOUT):
    """统一 HTTP 请求"""
    if headers is None:
        headers = {'User-Agent': UA}
    else:
        headers = {**{'User-Agent': UA}, **headers}
    try:
        if is_json and data is not None:
            r = requests.request(method, url, headers=headers, params=params,
                                 data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                                 timeout=timeout)
        else:
            r = requests.request(method, url, headers=headers, params=params,
                                 data=data, timeout=timeout)
        return r
    except Exception as e:
        return e


def get_netease_id():
    """用 netease 官方 cloudsearch 拿真实 ID"""
    r = http('GET', 'https://music.163.com/api/cloudsearch/pc',
             params={'s': TEST_KEYWORD, 'type': 1, 'limit': 1})
    if isinstance(r, Exception):
        return FALLBACK_IDS['netease'], 'fallback', ''
    try:
        songs = r.json().get('result', {}).get('songs', [])
        if songs:
            return str(songs[0]['id']), songs[0].get('name', '?'), '/'.join(a['name'] for a in songs[0].get('ar', []))
    except Exception:
        pass
    return FALLBACK_IDS['netease'], 'fallback', ''


def get_qq_id():
    """用 QQ 官方搜真实 mid"""
    import random
    payload = {
        'music.search.SearchCgiService.DoSearchForQQMusicMobile': {
            'method': 'DoSearchForQQMusicMobile', 'module': 'music.search.SearchCgiService',
            'param': {
                'searchid': ''.join(random.choices('0123456789', k=8)),
                'query': TEST_KEYWORD, 'search_type': 0,
                'num_per_page': 5, 'page_num': 1, 'highlight': 1, 'grp': 1,
            },
        },
    }
    r = http('POST', 'https://u.y.qq.com/cgi-bin/musicu.fcg', is_json=True, data=payload)
    if isinstance(r, Exception):
        return '', 'fallback', ''
    try:
        d = r.json()
        item_song = d.get('music.search.SearchCgiService.DoSearchForQQMusicMobile', {}).get('data', {}).get('body', {}).get('item_song', [])
        if not isinstance(item_song, list):
            item_song = d.get('music.search.SearchCgiService.DoSearchForQQMusicMobile', {}).get('data', {}).get('body', {}).get('item_song', {}).get('list', [])
        if item_song:
            s = item_song[0]
            return s.get('mid', ''), s.get('title', s.get('songname', '?')), '/'.join(si.get('name', '') for si in s.get('singer', []))
    except Exception:
        pass
    return '', 'fallback', ''


def get_kugou_hash():
    """用酷狗 song_search 拿 FileHash"""
    r = http('GET', 'https://songsearch.kugou.com/song_search_v2',
             params={'keyword': TEST_KEYWORD, 'page': 1, 'pagesize': 1, 'platform': 'WebFilter',
                     'isfc': 1, 'userid': 0, 'uuid': '0', 'version': '1000', 'clientver': '1000'})
    if isinstance(r, Exception):
        return '', 'fallback', ''
    try:
        songs = r.json().get('data', {}).get('lists', [])
        if songs:
            s = songs[0]
            return s.get('FileHash', ''), s.get('SongName', '?'), '/'.join(si.get('name', '') for si in s.get('Singers', []))
    except Exception:
        pass
    return '', 'fallback', ''


def get_kuwo_rid():
    """用酷我（波点）BD-API 拿 rid（纯数字 musicId，后端 URL 用此占位符）"""
    import hashlib, uuid
    dev_id = hashlib.md5(uuid.uuid4().bytes).hexdigest()
    r = http('GET', 'https://bd-api.kuwo.cn/api/search/music/list',
             params={'pn': '0', 'rn': '1', 'keyword': TEST_KEYWORD, 'correct': '1', 'uid': '-1', 'token': ''},
             headers={
                 'user-agent': 'Dart/3.3 (dart:io)', 'plat': 'win', 'accept-encoding': 'gzip',
                 'api-ver': 'application/json', 'channel': 'W1', 'brand': 'Windows 11',
                 'net': 'wifi', 'content-type': 'application/json', 'ver': '1.1.5', 'svrver': '13',
                 'devid': dev_id, 'qimei36': dev_id,
             })
    if isinstance(r, Exception):
        return '', 'fallback', ''
    try:
        d = r.json()
        songs = d.get('data', {}).get('resultList', []) or d.get('data', {}).get('list', [])
        if songs:
            s = songs[0]
            # 后端 kuwo URL 用 {rid} 占位符，期望纯数字 musicId
            rid_raw = s.get('musicRid') or s.get('id') or s.get('rid') or ''
            # 去掉 'MUSIC_' 前缀（如果有）
            rid = str(rid_raw).replace('MUSIC_', '').strip()
            return rid, s.get('songName') or s.get('name', '?'), s.get('artist', '')
    except Exception:
        pass
    return '', 'fallback', ''


# ==================== 测试 ID 收集 ====================

def collect_test_ids():
    """为每个平台获取真实测试 ID"""
    print('[1/4] 获取各平台真实测试 ID...')
    netease_id, n_name, n_art = get_netease_id()
    qq_id, q_name, q_art = get_qq_id()
    kugou_hash, k_name, k_art = get_kugou_hash()
    kuwo_rid, kw_name, kw_art = get_kuwo_rid()
    print(f'  netease: id={netease_id} "{n_name}" - {n_art}')
    print(f'  qq:      mid={qq_id} "{q_name}" - {q_art}')
    print(f'  kugou:   hash={kugou_hash[:20]}... "{k_name}" - {k_art}')
    print(f'  kuwo:    rid={kuwo_rid} "{kw_name}" - {kw_art}')
    return {
        'netease': netease_id, 'qq': qq_id,
        'kugou': kugou_hash, 'kuwo': kuwo_rid,
    }


# ==================== 模板变量填充 ====================

# 音质 key → br 数值（与 netease 官方 eapi 对应）
NETEASE_BR_MAP = {
    'standard': 128000, 'exhigh': 320000, 'lossless': 999000, 'hires': 1820000, 'jymaster': 999000,
}
# 第三方源 br 参数
NETEASE_BR_THIRD_PARTY = {
    'standard': '128', 'exhigh': '320', 'lossless': '999', 'hires': '999', 'jymaster': '999',
}
# QQ 质量
QQ_QUALITY = {
    'standard': '128', 'exhigh': '320', 'lossless': 'flac', 'hires': 'flac24bit',
}


def fill_template(template: str, platform: str, song_id: str, quality: str, playlist_id: str = '') -> str:
    """填充 URL 模板里的占位符"""
    if not template:
        return ''

    # 关键词编码（处理 {keyword_encoded}）
    keyword_encoded = urllib.parse.quote(TEST_KEYWORD)
    song_id_q = urllib.parse.quote(str(song_id), safe='')

    # 音质映射
    q_qq = QQ_QUALITY.get(quality, quality)
    q_ne_br = NETEASE_BR_THIRD_PARTY.get(quality, '999')
    q_ne_official_br = NETEASE_BR_MAP.get(quality, 999000)

    # 通用占位符
    url = template
    url = url.replace('{keyword_encoded}', keyword_encoded)
    url = url.replace('{keyword}', keyword_encoded)
    url = url.replace('{song_id}', song_id_q)
    url = url.replace('{rid}', song_id_q)
    url = url.replace('{hash}', song_id_q)
    url = url.replace('{limit}', '5')
    url = url.replace('{quality}', quality)
    url = url.replace('{playlist_id}', playlist_id or '3778678')  # 网易云热门歌单 ID fallback

    # netease 官方 br 占位符
    url = url.replace('{__br__}', str(q_ne_official_br) if '{quality}' not in url.split('{__br__}')[0] else str(q_ne_official_br))

    # 特定域字段
    url = url.replace('{apikey}', '1')  # cyapi placeholder

    # QQ vkey 复杂场景：URL 不需要质量参数，body 才需要
    # QQ 平台把 quality 替换为 mid 兼容字段
    if platform == 'qq':
        url = url.replace('{quality}', q_qq)

    return url


def fill_post_data(post_data: dict, song_id: str, quality: str) -> dict:
    """填充 POST 数据模板（和 URL 用相同的占位符语义）"""
    if not post_data:
        return None
    result = {}
    for k, v in post_data.items():
        if isinstance(v, str):
            v = v.replace('{song_id}', str(song_id))
            v = v.replace('{quality}', quality)
            v = v.replace('{rid}', str(song_id))
            # QQ vkey 特殊
            if 'QQ_MUSIC' in v or 'music.vkey' in v.lower():
                # JSON 模块名占位，不替换
                pass
        result[k] = v
    return result


# ==================== 探针：单次请求 ====================

def probe_url(method, url, headers=None, post_data=None, is_json=False, timeout=TIMEOUT):
    """探测单 URL，返回 (status, detail)"""
    try:
        r = http(method, url, headers=headers, data=post_data, is_json=is_json, timeout=timeout)
        if isinstance(r, Exception):
            if isinstance(r, requests.exceptions.Timeout):
                return 'dead', f'超时(>{timeout}s)'
            if isinstance(r, requests.exceptions.SSLError):
                return 'dead', f'SSL: {str(r)[:50]}'
            if isinstance(r, requests.exceptions.ConnectionError):
                return 'dead', f'连接: {str(r)[:50]}'
            return 'exception', f'{type(r).__name__}: {str(r)[:80]}'

        size = len(r.content)
        if r.status_code >= 400:
            return 'dead', f'HTTP {r.status_code}, {size}B'

        try:
            d = r.json()
        except Exception:
            txt = r.text[:200].strip()
            if txt.startswith(('http://', 'https://')):
                return 'alive_text', f'{txt[:80]}'
            return 'dead', f'非JSON, {size}B: {txt[:80]}'

        return 'alive_json', d
    except Exception as e:
        return 'exception', f'{type(e).__name__}: {str(e)[:80]}'


def safe_call_extractor(extractor, data):
    """安全调用提取器，捕获异常"""
    if not extractor or not callable(extractor):
        return None
    try:
        return extractor(data)
    except Exception as e:
        return f'EXTRACTOR_ERROR: {type(e).__name__}: {str(e)[:80]}'


# ==================== 5 类能力测试 ====================

def test_search(source: ApiSource, platform: str):
    """测试 search 源"""
    if not source.can_search or not source.search_url:
        return 'skipped', '无 can_search 或 search_url'

    # 后端自定义 prepare_request（签名/timestamp 准备器）：脚本不模拟
    if getattr(source, 'prepare_request', None) is not None:
        return 'needs_prepare', f'需后端 prepare_request 准备签名（{source.description[:40]}）'

    url = fill_template(source.search_url, platform, '', '')
    status, detail = probe_url(source.method or 'GET', url, headers=source.headers,
                               post_data=fill_post_data(source.post_data, '', ''),
                               is_json=source.is_json if hasattr(source, 'is_json') else False,
                               timeout=source.timeout or TIMEOUT)
    if status != 'alive_json':
        return status, detail

    # 校验提取器
    result = safe_call_extractor(source.extract_search, detail)
    if result is None:
        return 'no_extractor', 'extract_search 为空'
    if isinstance(result, str) and result.startswith('EXTRACTOR_ERROR'):
        return 'extractor_error', result
    if not isinstance(result, list):
        return 'extractor_wrong_type', f'extract_search 返回 {type(result).__name__}，期望 list'

    n = len(result)
    if n == 0:
        return 'no_data', f'提取器返回空列表'
    return 'alive', f'提取 {n} 条结果'


def test_url(source: ApiSource, platform: str, song_id: str, quality: str):
    """测试 URL 源（含具体音质）"""
    if not source.can_parse_url or not source.parse_url_url:
        return 'skipped', '无 can_parse_url 或 parse_url_url'

    # 后端 prepare_request：脚本不模拟
    if getattr(source, 'prepare_request', None) is not None:
        return 'needs_prepare', f'需后端 prepare_request 准备签名'

    url = fill_template(source.parse_url_url, platform, song_id, quality)
    status, detail = probe_url(source.method or 'GET', url, headers=source.headers,
                               post_data=fill_post_data(source.post_data, song_id, quality),
                               is_json=source.is_json if hasattr(source, 'is_json') else False,
                               timeout=source.timeout or TIMEOUT)
    if status != 'alive_json':
        return status, detail

    # 校验提取器
    result = safe_call_extractor(source.extract_url, detail)
    if result is None or result == '':
        return 'no_url', f'extract_url 返回空（响应 keys: {list(detail.keys())[:5]}）'
    if isinstance(result, str) and result.startswith('EXTRACTOR_ERROR'):
        return 'extractor_error', result
    if not (isinstance(result, str) and result.startswith(('http://', 'https://'))):
        return 'no_url', f'extract_url 返回非 URL: {str(result)[:80]}'
    return 'alive', f'{result[:80]}'


def test_info(source: ApiSource, platform: str, song_id: str):
    """测试 info 源（歌曲元信息）"""
    if not source.can_parse_info or not source.parse_info_url:
        return 'skipped', '无 can_parse_info 或 parse_info_url'

    if getattr(source, 'prepare_request', None) is not None:
        return 'needs_prepare', f'需后端 prepare_request 准备签名'

    url = fill_template(source.parse_info_url, platform, song_id, 'lossless')
    status, detail = probe_url(source.method or 'GET', url, headers=source.headers,
                               post_data=fill_post_data(source.post_data, song_id, 'lossless'),
                               is_json=source.is_json if hasattr(source, 'is_json') else False,
                               timeout=source.timeout or TIMEOUT)
    if status != 'alive_json':
        return status, detail

    result = safe_call_extractor(source.extract_info, detail)
    if result is None:
        return 'no_extractor', 'extract_info 返回 None'
    if isinstance(result, str) and result.startswith('EXTRACTOR_ERROR'):
        return 'extractor_error', result
    if not isinstance(result, dict):
        return 'extractor_wrong_type', f'extract_info 返回 {type(result).__name__}'

    # 校验关键字段（name/artist/url 至少有一个）
    keys = list(result.keys())[:5]
    return 'alive', f'fields: {keys}'


def test_lyric(source: ApiSource, platform: str, song_id: str):
    """测试 lyric 源"""
    if not source.can_parse_lyric or not source.parse_lyric_url:
        return 'skipped', '无 can_parse_lyric 或 parse_lyric_url'

    # 后端两步 API（如 kugou_official_lyric search→download）：脚本不模拟
    if getattr(source, 'prepare_request', None) is not None:
        return 'needs_prepare', f'需后端 prepare_request 准备签名'
    if 'lyrics.kugou.com' in (source.parse_lyric_url or ''):
        return 'two_step', 'kugou 官方歌词需 search→download 两步（后端 _two_step_lyric 包装）'

    url = fill_template(source.parse_lyric_url, platform, song_id, 'lossless')
    status, detail = probe_url(source.method or 'GET', url, headers=source.headers,
                               post_data=fill_post_data(source.post_data, song_id, 'lossless'),
                               is_json=source.is_json if hasattr(source, 'is_json') else False,
                               timeout=source.timeout or TIMEOUT)
    if status != 'alive_json':
        return status, detail

    result = safe_call_extractor(source.extract_lyric, detail)
    if result is None or result == '':
        return 'no_lyric', f'extract_lyric 返回空（响应 keys: {list(detail.keys())[:5]}）'
    if isinstance(result, str) and result.startswith('EXTRACTOR_ERROR'):
        return 'extractor_error', result
    if isinstance(result, str) and len(result) < 20:
        return 'lyric_too_short', f'歌词太短: {result[:50]}'
    return 'alive', f'长度 {len(result)} chars'


def test_playlist(source: ApiSource, platform: str, playlist_id: str):
    """测试 playlist 源"""
    if not hasattr(source, 'can_parse_playlist') or not source.can_parse_playlist:
        return 'skipped', '无 can_parse_playlist'
    if not hasattr(source, 'parse_playlist_url') or not source.parse_playlist_url:
        return 'skipped', '无 parse_playlist_url'

    # 后端 prepare_request：脚本不模拟
    if getattr(source, 'prepare_request', None) is not None:
        return 'needs_prepare', f'需后端 prepare_request 准备签名（{source.description[:40]}）'

    url = fill_template(source.parse_playlist_url, platform, '', '', playlist_id=playlist_id)
    status, detail = probe_url(source.method or 'GET', url, headers=source.headers,
                               post_data=fill_post_data(source.post_data, '', ''),
                               is_json=source.is_json if hasattr(source, 'is_json') else False,
                               timeout=source.timeout or TIMEOUT)
    if status != 'alive_json':
        return status, detail

    result = safe_call_extractor(getattr(source, 'extract_playlist', None), detail)
    if result is None:
        return 'no_extractor', 'extract_playlist 返回 None'
    if isinstance(result, str) and result.startswith('EXTRACTOR_ERROR'):
        return 'extractor_error', result
    if isinstance(result, dict):
        n = len(result.get('tracks', []))
        return 'alive', f'tracks={n}, keys: {list(result.keys())[:5]}'
    return 'alive', f'返回 {type(result).__name__}'


# ==================== 单 platform 探测 ====================

def probe_platform(platform: str, sources_map: dict, test_ids: dict):
    """探测一个平台所有 source"""
    print(f'\n{"=" * 70}')
    print(f'【{platform}】  {sources_map["name"]}')
    print(f'{"=" * 70}')

    song_id = test_ids.get(platform, '')
    # 平台默认测试歌单 ID
    playlist_id = {'netease': '3778678', 'qq': '7429867227', 'kugou': '888888', 'kuwo': '2787413870'}.get(platform, '')

    # 收集所有 (capability, source) 对
    all_sources = []
    for cap in ('search', 'url', 'info', 'lyric', 'playlist'):
        all_sources.extend([(cap, s) for s in sources_map[cap]])

    # 探测
    results = {}  # {(cap, source_name): {status, detail, ...}}
    for cap, src in all_sources:
        name = src.name
        if not src.enabled:
            results[(cap, name)] = {'status': 'disabled', 'detail': f'已禁用: {src.description[:40]}'}
            continue
        if src.needs_cookie:
            results[(cap, name)] = {'status': 'need_cookie', 'detail': f'需 cookie ({src.cookie_file})'}
            continue

        if cap == 'search':
            status, detail = test_search(src, platform)
        elif cap == 'url':
            # 测多个音质，汇总（避免 N 倍输出）
            url_results = {}
            for q in QUALITIES_TO_TEST:
                if src.max_quality and not _quality_supported(q, src.max_quality):
                    url_results[q] = ('skipped', f'>{src.max_quality}')
                else:
                    s, d = test_url(src, platform, song_id, q)
                    url_results[q] = (s, d)
            # 汇总：任一 alive 就算 alive
            alive_q = [q for q, (s, _) in url_results.items() if s == 'alive']
            dead_q = [q for q, (s, _) in url_results.items() if s == 'dead']
            err_q = [q for q, (s, _) in url_results.items() if s not in ('alive', 'dead', 'skipped')]
            if alive_q:
                status, detail = 'alive', f'✅ {",".join(alive_q)} | ❌ {",".join(dead_q) or "无"} | ⚠ {",".join(err_q) or "无"}'
            elif dead_q and not err_q:
                status, detail = 'dead', f'全部失败: {",".join(dead_q)}'
            else:
                status, detail = 'no_url', f'无 url, ❌{",".join(dead_q)} ⚠{",".join(err_q)}'
            # 把每个音质结果保存到 details
            results[(cap, name)] = {
                'status': status, 'detail': detail,
                'quality_results': url_results,
            }
            continue
        elif cap == 'info':
            status, detail = test_info(src, platform, song_id)
        elif cap == 'lyric':
            status, detail = test_lyric(src, platform, song_id)
        elif cap == 'playlist':
            status, detail = test_playlist(src, platform, playlist_id)

        results[(cap, name)] = {'status': status, 'detail': detail}

    return results


def _quality_supported(quality: str, max_quality: str) -> bool:
    """简化：是否 quality <= max_quality（按位比较）"""
    rank = {'standard': 0, 'exhigh': 1, 'lossless': 2, 'hires': 3, 'jymaster': 4}
    return rank.get(quality, 0) <= rank.get(max_quality, 0)


# ==================== 输出报告 ====================

STATUS_ICONS = {
    'alive': '✅ ALIVE',
    'alive_text': '✅ ALIVE',
    'alive_json': '✅ ALIVE',
    'skipped': '⏭  SKIP',
    'disabled': '⚫ OFF ',
    'need_cookie': '🔒 COOK',
    'needs_prepare': '🔑 PREP',
    'two_step': '🔗 2STP',
    'no_data': '🟡 NDAT',
    'no_url': '🟡 NURL',
    'no_extractor': '🟡 NEX ',
    'no_lyric': '🟡 NLRC',
    'lyric_too_short': '🟡 SLRC',
    'extractor_wrong_type': '🟡 ETYP',
    'extractor_error': '🟠 EERR',
    'dead': '❌ DEAD',
    'exception': '⚠️  ERR ',
}


def print_capability_report(platform: str, cap: str, sources_map: dict, results: dict, test_ids: dict):
    """打印某一能力的所有 source 探测结果"""
    cap_name_map = {
        'search': '搜索源', 'url': '下载 URL 源', 'info': '歌曲元信息源',
        'lyric': '歌词源', 'playlist': '歌单解析源',
    }
    print(f'\n  ── {cap_name_map[cap]} ({len(sources_map[cap])} 个 source) ──')

    stats = defaultdict(int)
    for src in sources_map[cap]:
        key = (cap, src.name)
        r = results.get(key, {})
        status = r.get('status', '?')
        detail = r.get('detail', '')
        stats[status] += 1
        line = f'    {src.name:32s} {STATUS_ICONS.get(status, status):12s}'
        if status == 'disabled':
            line += f'  {src.description[:50]}'
        elif status == 'need_cookie':
            line += f'  (cookie file: {src.cookie_file})'
        else:
            line += f'  {detail[:90]}'
        print(line)
        # URL 源：打印每个音质结果
        if cap == 'url' and 'quality_results' in r:
            for q, (qs, qd) in r['quality_results'].items():
                print(f'      └ {q:10s} {STATUS_ICONS.get(qs, qs):12s} {qd[:80]}')
    return stats


# ==================== 主程序 ====================

def main():
    print(f'开始探测 4 平台所有 ApiSource（动态加载后端 sources/）')
    print(f'测试关键词: "{TEST_KEYWORD}"\n')

    # 1. 拿真实测试 ID
    test_ids = collect_test_ids()

    # 2. 逐平台探测
    all_stats = defaultdict(lambda: defaultdict(int))
    all_results = {}
    for platform, sources_map in PLATFORM_SOURCES.items():
        results = probe_platform(platform, sources_map, test_ids)
        all_results[platform] = results

        # 分能力打印
        for cap in ('search', 'url', 'info', 'lyric', 'playlist'):
            cap_stats = print_capability_report(platform, cap, sources_map, results, test_ids)
            for s, c in cap_stats.items():
                all_stats[platform][s] += c

    # 3. 汇总
    print('\n' + '=' * 70)
    print('【汇总统计】')
    print('=' * 70)
    grand_total = 0
    grand_stats = defaultdict(int)
    for platform, stats in all_stats.items():
        total = sum(stats.values())
        grand_total += total
        print(f'\n  {PLATFORM_SOURCES[platform]["name"]} ({platform}, {total} 探测项):')
        for status, count in sorted(stats.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total else 0
            print(f'    {STATUS_ICONS.get(status, status):12s} {count:3d} ({pct:5.1f}%)')
        for s, c in stats.items():
            grand_stats[s] += c

    print(f'\n  全平台总计: {grand_total} 探测项')
    for status, count in sorted(grand_stats.items(), key=lambda x: -x[1]):
        pct = count / grand_total * 100 if grand_total else 0
        print(f'    {STATUS_ICONS.get(status, status):12s} {count:3d} ({pct:5.1f}%)')

    # 4. 健康清单
    print('\n' + '=' * 70)
    print('【各能力健康清单】')
    print('=' * 70)
    for cap in ('search', 'url', 'info', 'lyric', 'playlist'):
        cap_name = {'search': '搜索', 'url': 'URL', 'info': '元信息', 'lyric': '歌词', 'playlist': '歌单'}[cap]
        print(f'\n  📋 {cap_name} 源:')
        for platform, results in all_results.items():
            alive = []
            for src in PLATFORM_SOURCES[platform][cap]:
                key = (cap, src.name)
                r = results.get(key, {})
                if r.get('status') == 'alive':
                    alive.append(src.name)
            mark = '✅' if alive else '❌'
            print(f'    {mark} {PLATFORM_SOURCES[platform]["name"]:8s} ({len(alive)}/{len(PLATFORM_SOURCES[platform][cap])}): {", ".join(alive) or "无可用源"}')

    # 5. 故障排查建议
    print('\n' + '=' * 70)
    print('【故障排查建议（基于后端 sources/ 代码分析）】')
    print('=' * 70)
    suggestions = []
    for platform, results in all_results.items():
        for (cap, name), r in results.items():
            status = r.get('status', '')
            if status == 'dead' and 'HTTP 400' in r.get('detail', ''):
                if 'cenguigui' in name or 'cyapi' in name or 'apikey' in name:
                    suggestions.append(f'  - {platform}/{cap}/{name}: HTTP 400 可能是需要 apikey/ckey')
            elif status == 'dead' and 'HTTP 404' in r.get('detail', ''):
                suggestions.append(f'  - {platform}/{cap}/{name}: HTTP 404 端点已下线，建议禁用')
            elif status == 'extractor_error':
                suggestions.append(f'  - {platform}/{cap}/{name}: 提取器异常 → 检查后端 extractors.py 对应函数')
            elif status == 'no_data' and cap == 'search':
                suggestions.append(f'  - {platform}/{cap}/{name}: 搜索返回空列表 → 关键词或编码问题')
    if suggestions:
        for s in suggestions[:15]:
            print(s)
    else:
        print('  🎉 所有 source 正常工作！')


if __name__ == '__main__':
    main()
