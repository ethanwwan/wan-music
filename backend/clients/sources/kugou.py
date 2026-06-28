"""酷狗音乐 ApiSource 定义

所有数据来源：musicdl kugou.py + 实测（见 scripts/probe_apis.py）

酷狗 file_hash 模式，第三方解析 API 较少。
"""
import hashlib
import time
from ..fallback.api_source import ApiSource
from ..fallback.extractors import (
    extract_first_url,
    extract_text_url,
)
from ._playlist_extractors import (
    extract_kugou_playlist as _extract_kugou_playlist,
    extract_netease_playlist as _extract_netease_playlist,
)


KUGOU_COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Referer': 'https://www.kugou.com/',
}


# ==================== 搜索源 ====================

KUGOU_SEARCH_SOURCES = [
    # 1. 酷狗官方 song_search_v2
    ApiSource(
        name='kugou_official_search',
        platform='kugou',
        priority=0,
        description='酷狗官方 song_search_v2',
        can_search=True,
        search_url='https://songsearch.kugou.com/song_search_v2?keyword={keyword_encoded}&page=1&pagesize={limit}&platform=WebFilter',
        extract_search=lambda d: d.get('data', {}).get('lists', []) if isinstance(d, dict) else [],
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. gdstudio 跨平台 search
    ApiSource(
        name='gdstudio_search',
        platform='kugou',
        priority=10,
        description='gdstudio (跨平台源，kugou)',
        can_search=True,
        search_url='https://music-api.gdstudio.xyz/api.php?types=search&source=kugou&name={keyword_encoded}&count={limit}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 下载 URL 源 ====================

KUGOU_PARSE_URL_SOURCES = [
    # 1. haitanw (海糖网) - musicdl 列表（双重域名备份）
    ApiSource(
        name='haitanw_url',
        platform='kugou',
        priority=0,
        description='haitanw kg.php（musicdl 列表，level=hires/lossless/exhigh）',
        can_parse_url=True,
        parse_url_url='https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={hash}&level={quality}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d.get('data', {}) if isinstance(d, dict) else {}, dict) else
            (d.get('data', '') if isinstance(d, dict) else '')
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',  # 支持 hires/lossless/exhigh/standard
    ),
    # 2. haitanw 备用域名
    ApiSource(
        name='haitanw_url_backup',
        platform='kugou',
        priority=5,
        description='haitanw kg.php 备用域名（music.haitangw.cc）',
        can_parse_url=True,
        parse_url_url='https://music.haitangw.cc/kgqq/kg.php?type=json&id={hash}&level={quality}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d.get('data', {}) if isinstance(d, dict) else {}, dict) else
            (d.get('data', '') if isinstance(d, dict) else '')
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',  # 支持 hires/lossless/exhigh/standard
    ),
    # 3. cocodownloader (musicdl 验证可用)
    ApiSource(
        name='cocodownloader',
        platform='kugou',
        priority=10,
        description='cocodownloader (musicdl 验证可用)',
        can_parse_url=True,
        parse_url_url='https://cocodownloader.markqq.com/api/url?id={hash}&provider=kugou',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',
    ),
    # 4. 317ak (musicdl 列表) - 需 ckey 复杂鉴权
    ApiSource(
        name='317ak_url',
        platform='kugou',
        priority=15,
        description='317ak (musicdl 列表，需 ckey 解密)',
        enabled=False,  # 需 base64 解密 ckey
        can_parse_url=True,
        parse_url_url='https://api.317ak.cn/api/yinyue/kugou?ckey={ckey}&i={hash}&br={quality}&type=json&lrc=1',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',  # br=hires 理论支持
    ),
    # 5. jbsou (musicdl 列表) - POST 复杂
    ApiSource(
        name='jbsou_url',
        platform='kugou',
        priority=20,
        description='jbsou POST (musicdl 列表)',
        enabled=False,  # 需验证 POST 数据
        can_parse_url=True,
        method='POST',
        parse_url_url='https://www.jbsou.cn/',
        post_data={'input': '{hash}', 'filter': 'id', 'type': 'kugou', 'page': '1'},
        extract_url=lambda d: (
            (d.get('data', [{}])[0] if isinstance(d.get('data'), list) and d.get('data') else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers={
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://www.jbsou.cn',
            'referer': 'https://www.jbsou.cn/',
            'x-requested-with': 'XMLHttpRequest',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        },
        timeout=15,
        max_quality='lossless',
    ),
    # 6. 酷狗官方 playInfo (需先获取 hash key 才能用)
    ApiSource(
        name='kugou_official_url',
        platform='kugou',
        priority=30,
        description='酷狗官方 playInfo (需先获取 hash key)',
        enabled=False,  # 需要先解析 hash key 才能用
        can_parse_url=True,
        parse_url_url='https://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={hash}',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
        max_quality='exhigh',  # 官方 API 实际只返 mp3
    ),
    # 7. 酷狗官方 kgcloudv2 (md5+trackercdn 复杂) - musicdl 列表
    ApiSource(
        name='kugou_official_kgcloudv2',
        platform='kugou',
        priority=35,
        description='酷狗官方 trackercdn kgcloudv2 (musicdl 列表)',
        enabled=False,  # 需 md5(hash + kgcloudv2) 鉴权
        can_parse_url=True,
        parse_url_url='https://trackercdn.kugou.com/i/v2/?cdnBackup=1&behavior=download&pid=1&cmd=21&appid=1001&hash={hash}&key={__md5__}',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
        max_quality='hires',  # 理论支持
    ),
    # 8. gdstudio 跨平台 URL
    ApiSource(
        name='gdstudio_url',
        platform='kugou',
        priority=40,
        description='gdstudio URL (跨平台源，kugou)',
        can_parse_url=True,
        parse_url_url='https://music-api.gdstudio.xyz/api.php?types=url&id={hash}&source=kugou&br={__br__}',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',  # gdstudio __br__ 最高 lossless
    ),
]


# ==================== 歌曲元信息源 ====================

KUGOU_PARSE_INFO_SOURCES = [
    # 1. 酷狗官方 song info（响应直接在顶层，songName 字段；映射为 name 字段以通过 _is_valid）
    ApiSource(
        name='kugou_official_info',
        platform='kugou',
        priority=0,
        description='酷狗官方 song info',
        can_parse_info=True,
        parse_info_url='https://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={hash}',
        extract_info=lambda d: (
            {'id': d.get('hash', ''), 'name': d.get('songName', ''),
             'artists': d.get('singerName', ''), 'album': d.get('albumName', ''),
             'picUrl': d.get('album_img', d.get('imgUrl', '')),
             'duration': d.get('timeLength', 0) * 1000 if d.get('timeLength') else 0,
             **d} if isinstance(d, dict) and d.get('songName') else {}
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. gdstudio info (跨平台)
    ApiSource(
        name='gdstudio_info',
        platform='kugou',
        priority=10,
        description='gdstudio info (跨平台)',
        can_parse_info=True,
        parse_info_url='https://music-api.gdstudio.xyz/api.php?types=info&id={hash}&source=kugou',
        extract_info=lambda d: (
            {'id': str(d.get('id', '')), 'name': d.get('name', ''),
             'artists': '/'.join(d.get('artist', []) if isinstance(d.get('artist'), list) else [str(d.get('artist', '') or '')]),
             'album': d.get('album', ''),
             'picUrl': d.get('pic', ''),
             'duration': d.get('duration', 0)}
            if isinstance(d, dict) and d.get('id') else {}
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. haitanw info (元信息，但 musicdl 备注 url 也在 data)
    ApiSource(
        name='haitanw_info',
        platform='kugou',
        priority=20,
        description='haitanw info (元信息)',
        can_parse_info=True,
        parse_info_url='https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={hash}&level=lossless',
        extract_info=lambda d: (
            {'id': str(d.get('data', {}).get('rid', '')) if isinstance(d, dict) else '',
             'name': (d.get('data', {}) if isinstance(d, dict) else {}).get('name', '') or
                     (d.get('data', {}) if isinstance(d, dict) else {}).get('song', ''),
             'artists': (d.get('data', {}) if isinstance(d, dict) else {}).get('artist', '') or
                        (d.get('data', {}) if isinstance(d, dict) else {}).get('singer', ''),
             'album': (d.get('data', {}) if isinstance(d, dict) else {}).get('album', ''),
             'picUrl': (d.get('data', {}) if isinstance(d, dict) else {}).get('pic', '') or
                       (d.get('data', {}) if isinstance(d, dict) else {}).get('cover', ''),
             'duration': (d.get('data', {}) if isinstance(d, dict) else {}).get('duration', 0)}
            if isinstance(d, dict) and (d.get('data', {}) or {}).get('name') else {}
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌词源 ====================

KUGOU_PARSE_LYRIC_SOURCES = [
    # 1. 酷狗官方 lyrics.kugou.com（两步：search 然后 download）
    ApiSource(
        name='kugou_official_lyric',
        platform='kugou',
        priority=0,
        description='酷狗官方 lyrics.kugou.com (两步：search+download)',
        can_parse_lyric=True,
        parse_lyric_url='http://lyrics.kugou.com/search?keyword={keyword_encoded}&duration={duration}&hash={hash}',
        extract_lyric=lambda d: '',  # 实际为两步调用，由 _two_step_lyric 包装
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. haitanw lyric (data.lyric 字段)
    ApiSource(
        name='haitanw_lyric',
        platform='kugou',
        priority=10,
        description='haitanw lyric (musicdl 列表，data.lyric 字段)',
        can_parse_lyric=True,
        parse_lyric_url='https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={hash}&level=lossless',
        extract_lyric=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('lyric', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. 317ak lyric (musicdl 列表，lrc=1)
    ApiSource(
        name='317ak_lyric',
        platform='kugou',
        priority=20,
        description='317ak lyric (musicdl 列表)',
        enabled=False,  # 需 ckey
        can_parse_lyric=True,
        parse_lyric_url='https://api.317ak.cn/api/yinyue/kugou?ckey={ckey}&i={hash}&br=999&type=json&lrc=1',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. gdstudio lyric
    ApiSource(
        name='gdstudio_lyric',
        platform='kugou',
        priority=30,
        description='gdstudio lyric (跨平台)',
        can_parse_lyric=True,
        parse_lyric_url='https://music-api.gdstudio.xyz/api.php?types=lyric&id={hash}&source=kugou',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌单解析 ====================

def _kugou_playlist_prepare(url: str, method: str, headers: dict, post_data, is_json, kwargs: dict):
    """酷狗歌单 API 需要 MD5 签名（参考 musicdl kugou.py）

    signature = MD5("OIlwieks28dk2k092lksi2UIkp" + sorted_query + "OIlwieks28dk2k092lksi2UIkp")
    """
    # 替换 {clienttime} 占位
    if headers.get('clienttime') == '{clienttime}':
        headers['clienttime'] = str(int(time.time()))
    # 取 query 部分
    if '?' in url:
        q = url.split('?', 1)[1]
    else:
        q = ''
    # 排序拼接
    sorted_q = ''.join(sorted(q.split('&')))
    sig = hashlib.md5(
        ('OIlwieks28dk2k092lksi2UIkp' + sorted_q + 'OIlwieks28dk2k092lksi2UIkp').encode('utf-8')
    ).hexdigest()
    new_url = url + '&signature=' + sig
    return {'url': new_url, 'method': method, 'headers': headers,
            'post_data': post_data, 'is_json': is_json}


KUGOU_PARSE_PLAYLIST_SOURCES = [
    # 1. 酷狗官方 gatewayretry.kugou.com（带签名 + 特殊 headers）
    ApiSource(
        name='kugou_official_playlist',
        platform='kugou',
        priority=0,
        description='酷狗官方 gatewayretry.kugou.com（带签名，特殊 headers）',
        can_parse_playlist=True,
        parse_playlist_url=(
            'http://gatewayretry.kugou.com/v2/get_other_list_file'
            '?specialid={playlist_id}&need_sort=1&module=CloudMusic'
            '&clientver=11239&pagesize=300&specalidpgc={playlist_id}'
            '&userid=0&page={page}&type=0&area_code=1&appid=1005'
        ),
        extract_playlist=_extract_kugou_playlist,
        headers={
            'User-Agent': 'Android9-AndroidPhone-11239-18-0-playlist-wifi',
            'Host': 'gatewayretry.kugou.com',
            'x-router': 'pubsongscdn.kugou.com',
            'mid': '239526275778893399526700786998289824956',
            'dfid': '-',
            'clienttime': '{clienttime}',  # 运行时替换
        },
        prepare_request=_kugou_playlist_prepare,
        timeout=15,
    ),
    ApiSource(
        name='gdstudio_playlist',
        platform='kugou',
        priority=20,
        description='gdstudio 跨平台歌单（兜底，只接受 source=netease/kuwo/joox，固定返回网易云格式）',
        can_parse_playlist=True,
        parse_playlist_url='https://music-api.gdstudio.xyz/api.php?types=playlist&id={playlist_id}&source=netease',
        extract_playlist=_extract_netease_playlist,
        headers={'User-Agent': 'Mozilla/5.0'},
        timeout=20,
    ),
]
