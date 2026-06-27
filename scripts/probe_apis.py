#!/usr/bin/env python3
"""探测 musicdl 4 平台所有 API 的可用性

工作流程：
  1. 各平台官方 API 搜索「陈楚生」拿一个真实 song_id
  2. 用 song_id 测试 musicdl 中所有该平台的 parse 端点
  3. 统计 alive / dead / 异常 / 不支持

输出：按平台分组的详细报告 + 汇总统计
"""
import json
import time
import urllib.parse
from pathlib import Path
from collections import defaultdict

import requests

TEST_KEYWORD = '陈楚生'
TIMEOUT = 10

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'

# 各平台使用的 test_song_id（在主程序里通过搜索动态获取）
# 这些是初始 fallback，若搜索失败则使用
FALLBACK_IDS = {
    'netease': '3398250102',   # 陈楚生 - 有我呢
    'qq': '001X0PDp0SwOjV',    # placeholder
    'kugou': '',               # 需要动态搜索
    'bodian': '',
}


def http(method: str, url: str, **kwargs) -> requests.Response:
    return requests.request(method, url, timeout=kwargs.pop('timeout', TIMEOUT),
                            headers=kwargs.pop('headers', {'User-Agent': UA}), **kwargs)


# ==================== 1. 获取各平台真实 song_id ====================

def get_netease_id() -> str:
    """从 netease cloudsearch 拿一个真实 song_id"""
    try:
        r = http('GET', 'https://music.163.com/api/cloudsearch/pc',
                 params={'s': TEST_KEYWORD, 'type': 1, 'limit': 1})
        songs = r.json().get('result', {}).get('songs', [])
        if songs:
            return str(songs[0]['id']), songs[0].get('name', '?'), '/'.join(a['name'] for a in songs[0]['ar'])
    except Exception as e:
        print(f'  netease 搜索失败: {e}')
    return FALLBACK_IDS['netease'], 'fallback', ''


def get_qq_id() -> tuple:
    """从 QQ 官方搜一个真实 song_id（song_mid）"""
    try:
        import random
        url = 'https://u.y.qq.com/cgi-bin/musicu.fcg'
        payload = {
            'music.search.SearchCgiService.DoSearchForQQMusicMobile': {
                'method': 'DoSearchForQQMusicMobile',
                'module': 'music.search.SearchCgiService',
                'param': {
                    'searchid': ''.join(random.choices('0123456789', k=8)),
                    'query': TEST_KEYWORD,
                    'search_type': 0,
                    'num_per_page': 5,
                    'page_num': 1,
                    'highlight': 1,
                    'grp': 1,
                },
            },
        }
        r = requests.post(url, data=json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8'),
                          headers={'User-Agent': UA, 'Referer': 'https://y.qq.com/', 'Origin': 'https://y.qq.com/'}, timeout=10)
        d = r.json()
        song_list = d.get('music.search.SearchCgiService.DoSearchForQQMusicMobile', {}).get('data', {}).get('body', {}).get('item_song', [])
        if not isinstance(song_list, list):
            song_list = d.get('music.search.SearchCgiService.DoSearchForQQMusicMobile', {}).get('data', {}).get('body', {}).get('item_song', {}).get('list', [])
        if song_list:
            s = song_list[0]
            return s.get('mid', ''), s.get('title', s.get('songname', '?')), '/'.join(singer.get('name', '') for singer in s.get('singer', []))
    except Exception as e:
        print(f'  qq 搜索失败: {e}')
    return FALLBACK_IDS['qq'], 'fallback', ''


def get_kugou_id() -> tuple:
    """从酷狗搜一个 file_hash"""
    try:
        url = 'https://songsearch.kugou.com/song_search_v2?'
        params = {'keyword': TEST_KEYWORD, 'page': 1, 'pagesize': 1, 'platform': 'WebFilter',
                  'isfc': 1, 'userid': 0, 'uuid': '0', 'version': '1000', 'clientver': '1000'}
        r = http('GET', url, params=params)
        songs = r.json().get('data', {}).get('lists', [])
        if songs:
            s = songs[0]
            return s.get('FileHash', ''), s.get('SongName', '?'), '/'.join(singer.get('name', '') for singer in s.get('Singers', []))
    except Exception as e:
        print(f'  kugou 搜索失败: {e}')
    return '', 'fallback', ''


def get_bodian_id() -> tuple:
    """从波点搜一个 song_id (rid)"""
    try:
        import hashlib, uuid, time
        dev_id = hashlib.md5(uuid.uuid4().bytes).hexdigest()
        url = 'https://bd-api.kuwo.cn/api/search/music/list'
        params = {
            'pn': '0', 'rn': '1', 'keyword': TEST_KEYWORD,
            'correct': '1', 'uid': '-1', 'token': '',
        }
        r = requests.get(url, params=params, headers={
            'user-agent': 'Dart/3.3 (dart:io)', 'plat': 'win', 'accept-encoding': 'gzip',
            'api-ver': 'application/json', 'channel': 'W1', 'brand': 'Windows 11',
            'net': 'wifi', 'content-type': 'application/json', 'ver': '1.1.5', 'svrver': '13',
            'devid': dev_id, 'qimei36': dev_id,
        }, timeout=10)
        d = r.json()
        # 新版 API 字段是 resultList，id 是 song id
        songs = d.get('data', {}).get('resultList', []) or d.get('data', {}).get('list', [])
        if songs:
            s = songs[0]
            rid = s.get('musicRid') or s.get('id') or s.get('rid')
            return str(rid), s.get('songName') or s.get('name', '?'), s.get('artist', '')
    except Exception as e:
        print(f'  bodian 搜索失败: {e}')
    return '', 'fallback', ''


# ==================== 2. 各平台 API 定义 ====================

# 工具：探测函数，统一返回 (status, detail) 其中 status ∈ {alive, dead, exception}
def probe(name: str, method: str, url: str, kwargs: dict = None) -> tuple:
    """探测 API 可用性，提取 url（如有）"""
    kwargs = kwargs or {}
    try:
        r = requests.request(method, url, timeout=kwargs.pop('timeout', TIMEOUT),
                             headers=kwargs.pop('headers', {'User-Agent': UA}), **kwargs)
        size = len(r.content)
        if r.status_code >= 400:
            return name, 'dead', f'HTTP {r.status_code}, {size}B'
        try:
            d = r.json()
        except Exception:
            txt = r.text[:200].strip()
            if txt.startswith('http://') or txt.startswith('https://'):
                return name, 'alive_url_text', f'{txt[:60]}...'
            return name, 'dead', f'非JSON, {size}B, body: {txt[:80]}'

        url_found = None
        if isinstance(d, dict):
            # 尝试常见字段（含 musicdl 特殊字段名）
            for k in ['url', 'data', 'download_url', 'song_file_url', 'music_url',
                      'song_play_url', 'song_play_url_standard', 'song_play_url_hq']:
                v = d.get(k)
                if isinstance(v, str) and v.startswith('http'):
                    url_found = v
                    break
                if isinstance(v, dict):
                    for kk in ['url', 'link', 'music_url']:
                        vv = v.get(kk)
                        if isinstance(vv, str) and vv.startswith('http'):
                            url_found = vv
                            break
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    vv = v[0].get('url') or v[0].get('link') or v[0].get('music_url')
                    if isinstance(vv, str) and vv.startswith('http'):
                        url_found = vv
                        break
            # 尝试 quality_urls 数组 (xunhuisi 风格)
            if not url_found and isinstance(d.get('quality_urls'), list):
                for q in d['quality_urls']:
                    if isinstance(q, dict) and isinstance(q.get('url'), str) and q['url'].startswith('http') and not q.get('encrypted'):
                        url_found = q['url']
                        break
            # 尝试 quality_urls_string 嵌套 (tang.s01s 风格)
            if not url_found and isinstance(d.get('quality_urls_string'), dict):
                for kk in ['song_play_url_hq', 'song_play_url', 'song_play_url_standard']:
                    v = d['quality_urls_string'].get(kk)
                    if isinstance(v, str) and v.startswith('http'):
                        url_found = v
                        break
        if url_found:
            return name, 'alive', f'{url_found[:60]}...'
        if d.get('code') == 200 and d.get('data'):
            return name, 'alive', f'code=200, data keys: {list(d["data"].keys())[:3]}'
        return name, 'no_url', f'无url, 顶层keys: {list(d.keys())[:5]}, 大小:{size}B'
    except requests.exceptions.Timeout:
        return name, 'dead', f'超时 (>{TIMEOUT}s)'
    except requests.exceptions.SSLError as e:
        return name, 'dead', f'SSL: {str(e)[:50]}'
    except requests.exceptions.ConnectionError as e:
        return name, 'dead', f'连接: {str(e)[:50]}'
    except Exception as e:
        return name, 'exception', f'{type(e).__name__}: {str(e)[:50]}'


# ==================== 3. 主测试逻辑 ====================

def test_netease(song_id: str):
    """netease parse API 测试"""
    apis = [
        # (name, method, url, kwargs_dict)
        ('cenguigui', 'GET', f'https://api-v2.cenguigui.cn/api/netease/music_v1.php?id={song_id}&type=json&level=lossless', {}),
        ('xuanluoge (search)', 'GET', f'http://118.24.104.108:3456/api.php?miss=search&keyword={TEST_KEYWORD}&limit=5', {}),
        ('xuanluoge (parse)', 'GET', f'http://118.24.104.108:3456/api.php?miss=getMusicUrl&id={song_id}&level=lossless', {}),
        ('xuanluoge (info)', 'GET', f'http://118.24.104.108:3456/api.php?miss=getMusicInfo&id={song_id}', {}),
        ('haitangw (search)', 'GET', f'https://musicapi.haitangw.net/music/wy.php?keyword={TEST_KEYWORD}&type=search&limit=5', {}),
        ('haitangw (parse)', 'GET', f'https://musicapi.haitangw.net/music/wy.php?id={song_id}&level=lossless&type=json', {}),
        ('haitangw (info)', 'GET', f'https://musicapi.haitangw.net/music/wy.php?id={song_id}&type=json', {}),
        ('bileizhen', 'GET', f'https://api.bileizhen.top/api/netease?id={song_id}&level=lossless', {}),
        ('bugpk', 'GET', f'https://api.bugpk.com/api/163_music?ids={song_id}&level=lossless&type=json', {}),
        ('cocodownloader', 'GET', f'https://cocodownloader.markqq.com/api/url?id={song_id}&provider=netease&quality=jymaster', {}),
        ('cunyu', 'GET', f'https://www.cunyuapi.top/163music_play?id={song_id}&quality=lossless', {}),
        ('gdstudio (search)', 'GET', f'https://music-api.gdstudio.xyz/api.php?types=search&source=netease&name={urllib.parse.quote(TEST_KEYWORD)}&count=5', {}),
        ('gdstudio (parse)', 'GET', f'https://music-api.gdstudio.xyz/api.php?types=url&id={song_id}&source=netease&br=999', {}),
        ('gdstudio (info)', 'GET', f'https://music-api.gdstudio.xyz/api.php?types=info&id={song_id}&source=netease', {}),
        ('rxtool', 'GET', f'https://api.rxtool.top/api/meteasecloudmusic.php?id={song_id}&level=hires', {}),
        ('vincentzyu233', 'GET', f'http://xwl.vincentzyu233.cn:51217/v2/music/netease?id={song_id}&quality=9', {}),
        ('rrvenn', 'POST', 'https://music.rrvenn.cn/Song_V1', {'data': {'url': song_id, 'level': 'lossless', 'type': 'json'}}),
        ('jfjt', 'POST', 'https://dm.jfjt.cc/Song_V1', {'data': {'url': song_id, 'level': 'lossless', 'type': 'json'}}),
        ('kangqiovo', 'POST', 'https://ncm.kangqiovo.com/Song_V1', {'data': {'url': song_id, 'level': 'lossless', 'type': 'json'}}),
        ('yutangxiaowu', 'GET', f'https://yutangxiaowu.cn:4000/Song_V1?url={song_id}&level=lossless&type=json', {}),
        ('lblb', 'POST', 'https://music163.lblb.eu/Song_V1', {'data': {'url': song_id, 'level': 'lossless', 'type': 'json'}}),
        ('qjqq', 'POST', 'https://metings.qjqq.cn/Song_V1', {'data': {'url': song_id, 'level': 'lossless', 'type': 'json'}}),
        ('manshuo', 'POST', 'https://api.manshuo.ink/wyy/Song_V1', {'data': {'url': song_id, 'level': 'lossless', 'type': 'json'}}),
        ('ceseet', 'GET', f'https://m-api.ceseet.me/url/wy/{song_id}/hires', {}),
        ('rxtool (s0o1)', 'GET', f'https://api.s0o1.com/API/wyy_music/?id={song_id}&yz=7', {}),
        ('byfuns (text)', 'GET', f'https://api.byfuns.top/1/?id={song_id}&level=hires', {}),
    ]
    return [probe(*api) for api in apis]


def test_qq(song_mid: str):
    """QQ parse API 测试"""
    if not song_mid or song_mid == FALLBACK_IDS['qq']:
        return [('fallback_id', 'exception', '无有效 song_mid，跳过 QQ API 测试')]
    apis = [
        ('vkeys (parse)', 'GET', f'https://api.vkeys.cn/music/tencent/song/link?mid={song_mid}&quality=320', {}),
        ('vkeys (lyric)', 'GET', f'https://api.vkeys.cn/v2/music/tencent/lyric?mid={song_mid}', {}),
        ('317ak', 'GET', f'https://api.317ak.cn/api/yinyue/qqyinyue?i={song_mid}&br=320&type=json&lrc=1', {}),
        ('lxmusicapi', 'GET', f'https://lxmusicapi.onrender.com/url/tx/{song_mid}/320', {}),
        ('xunhuisi', 'GET', f'https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_mid}&type=json', {}),
        ('tang.s01s', 'GET', f'https://tang.api.s01s.cn/music_open_api.php?mid={song_mid}', {}),
        ('cyapi', 'GET', 'https://cyapi.top/API/qq_music.php', {'params': {'mid': song_mid, 'quality': '320', 'type': 'json'}}),
    ]
    return [probe(*api) for api in apis]


def test_kugou(file_hash: str):
    """酷狗 parse API 测试"""
    if not file_hash:
        return [('fallback_id', 'exception', '无有效 file_hash，跳过酷狗 API 测试')]
    apis = [
        ('haitangw (kg)', 'GET', f'https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={file_hash}&level=320', {}),
        ('haitangw.cc (kg)', 'GET', f'https://music.haitangw.cc/kgqq/kg.php?type=json&id={file_hash}&level=320', {}),
        ('cocodownloader (kg)', 'GET', f'https://cocodownloader.markqq.com/api/url?id={file_hash}&provider=kugou', {}),
        ('317ak (kg)', 'GET', f'https://api.317ak.cn/api/yinyue/kugou?i={file_hash}&br=320&type=json&lrc=1', {}),
        ('jbsou', 'POST', 'https://www.jbsou.cn/', {'data': {'input': file_hash, 'filter': 'id', 'type': 'kugou', 'page': '1'}}),
    ]
    return [probe(*api) for api in apis]


def test_bodian(rid: str):
    """波点 parse API 测试"""
    if not rid:
        return [('fallback_id', 'exception', '无有效 rid，跳过波点 API 测试')]
    apis = [
        ('cenguigui (kw)', 'GET', f'https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json', {}),
        ('cenguigui (kw-search)', 'GET', 'https://kw-api.cenguigui.cn/?id=&type=search&keyword=陈楚生&level=lossless&format=json', {}),
    ]
    return [probe(*api) for api in apis]


# ==================== 4. 输出报告 ====================

def fmt_status(s: str) -> str:
    return {
        'alive': '✅ ALIVE',
        'alive_url_text': '✅ ALIVE',
        'no_url': '🟡 NO_URL',
        'dead': '❌ DEAD',
        'exception': '⚠️  ERR',
    }.get(s, s)


def print_report(platform: str, song_info: str, results: list) -> dict:
    print(f'\n{"="*70}')
    print(f'【{platform}】  {song_info}')
    print('='*70)
    stats = defaultdict(int)
    for name, status, detail in results:
        if name == 'fallback_id':
            print(f'  {name:30s} {fmt_status(status):12s} {detail}')
            continue
        print(f'  {name:30s} {fmt_status(status):12s} {detail[:100]}')
        stats[status] += 1
    return dict(stats)


def main():
    print(f'开始探测 4 平台所有 musicdl API 可用性 (关键词="{TEST_KEYWORD}")\n')

    print('[1/4] 获取各平台真实 song_id...')
    netease_id, n_name, n_art = get_netease_id()
    qq_id, q_name, q_art = get_qq_id()
    kugou_hash, k_name, k_art = get_kugou_id()
    bodian_rid, b_name, b_art = get_bodian_id()
    print(f'  netease: {netease_id} - {n_name} - {n_art}')
    print(f'  qq:      {qq_id} - {q_name} - {q_art}')
    print(f'  kugou:   {kugou_hash} - {k_name} - {k_art}')
    print(f'  bodian:  {bodian_rid} - {b_name} - {b_art}')

    print('\n[2/4] 测试 netease 26 个 API...')
    netease_results = test_netease(netease_id)
    n_stats = print_report('netease', f'id={netease_id}, "{n_name}"', netease_results)

    print('\n[3/4] 测试 QQ 7 个 API...')
    qq_results = test_qq(qq_id)
    q_stats = print_report('qq', f'mid={qq_id}, "{q_name}"', qq_results)

    print('\n[4/4] 测试 kugou 5 个 + bodian 1 个 API...')
    kugou_results = test_kugou(kugou_hash)
    k_stats = print_report('kugou', f'hash={kugou_hash}, "{k_name}"', kugou_results)
    bodian_results = test_bodian(bodian_rid)
    b_stats = print_report('bodian', f'rid={bodian_rid}, "{b_name}"', bodian_results)

    # 汇总
    print('\n' + '='*70)
    print('【汇总统计】')
    print('='*70)
    all_stats = defaultdict(int)
    for s in [n_stats, q_stats, k_stats, b_stats]:
        for k, v in s.items():
            all_stats[k] += v
    total = sum(all_stats.values())
    print(f'  共测试: {total} 个 API 端点')
    for status, count in sorted(all_stats.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total else 0
        print(f'  {fmt_status(status):12s} {count:3d} ({pct:5.1f}%)')
    print()
    # 列出可用的 API
    print('【可用 API 清单】')
    for platform, results in [('netease', netease_results), ('qq', qq_results), ('kugou', kugou_results), ('bodian', bodian_results)]:
        alive = [n for n, s, d in results if s in ('alive', 'alive_url_text')]
        if alive:
            print(f'  {platform}: {len(alive)} 个 - {", ".join(alive)}')


if __name__ == '__main__':
    main()
