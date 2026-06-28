"""QQ 音乐 ApiSource 定义

所有数据来源：musicdl qq.py + 实测（见 scripts/probe_apis.py）

QQ 官方 API 鉴权复杂（sign/cookie），主要依赖第三方解析 API。
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import (
    extract_first_url,
    extract_text_url,
    url_quote,
)


QQ_COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Referer': 'https://y.qq.com/',
    'Origin': 'https://y.qq.com',
}

QQ_LXMUSIC_HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'lx-music-request/2.6.0',
    'X-Request-Key': 'share-v3',
}


# ==================== 搜索源 ====================

QQ_SEARCH_SOURCES = [
    # 1. xunhuisi（实测可用，参数名 name）- 也支持按 mid/name 查详情
    ApiSource(
        name='xunhuisi_search',
        platform='qq',
        priority=0,
        description='xunhuisi (实测可用，name 参数)',
        can_search=True,
        search_url='https://api.xunhuisi.store/API/QQMusic/Song.php?name={keyword_encoded}&type=json',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 2. QQ 官方 musicu.fcg（musicdl 列表，复杂 sign/cookie）
    ApiSource(
        name='qq_official_search',
        platform='qq',
        priority=10,
        description='QQ 官方 musicu.fcg DoSearchForQQMusicMobile（需 sign/cookie）',
        enabled=False,  # 复杂签名
        can_search=True,
        method='POST',
        search_url='https://u.y.qq.com/cgi-bin/musicu.fcg',
        post_data={
            'comm': '{"format":"json","inCharset":"utf-8","outCharset":"utf-8","notice":0,"platform":"yqq.json","needNewCode":1,"uin":"0"}',
            'req_0': '{"module":"music.search.SearchCgiService","method":"DoSearchForQQMusicMobile","param":{"searchid":"12345678","query":"{keyword}","num_per_page":{limit},"page_num":1}}',
        },
        extract_search=lambda d: (
            d.get('req_0', {}).get('data', {}).get('body', {}).get('song', {}).get('list', [])
            if isinstance(d, dict) else []
        ),
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. nki search - musicdl 列表（实测 404）
    ApiSource(
        name='nki_search',
        platform='qq',
        priority=20,
        description='nki search (musicdl 列表，实测 404)',
        enabled=False,  # 404
        can_search=True,
        search_url='https://api.nki.pw/API/music_search.php?keyword={keyword_encoded}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 4. cyapi search - musicdl 列表（需 apikey）
    ApiSource(
        name='cyapi_search',
        platform='qq',
        priority=30,
        description='cyapi search (musicdl 列表，需 apikey)',
        enabled=False,  # 需 apikey
        can_search=True,
        search_url='https://cyapi.top/API/qq_music.php?apikey={apikey}&type=search&keyword={keyword_encoded}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 5. 317ak search - musicdl 列表
    ApiSource(
        name='317ak_search',
        platform='qq',
        priority=40,
        description='317ak search (musicdl 列表)',
        enabled=False,  # 接口不存在
        can_search=True,
        search_url='https://api.317ak.cn/api/yinyue/qqsearch?keyword={keyword_encoded}&page=1&limit={limit}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
]


# ==================== 下载 URL 源 ====================

QQ_PARSE_URL_SOURCES = [
    # 1. xunhuisi - 解析 mid（实测可用，music_url 字段）
    ApiSource(
        name='xunhuisi_url',
        platform='qq',
        priority=0,
        description='xunhuisi (mid 解析，music_url 字段)',
        can_parse_url=True,
        parse_url_url='https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json',
        extract_url=lambda d: (
            d.get('music_url') or
            extract_first_url(d)
        ) if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 2. vkeys - musicdl 列表（带 lyric）
    ApiSource(
        name='vkeys_url',
        platform='qq',
        priority=10,
        description='vkeys (musicdl 列表)',
        can_parse_url=True,
        parse_url_url='https://api.vkeys.cn/music/tencent/song/link?mid={song_id}&quality=999',
        extract_url=lambda d: (
            d.get('data', {}).get('url', '') if isinstance(d, dict) else ''
        ),
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. xcvts - musicdl 列表（需解密 apiKey）
    ApiSource(
        name='xcvts_url',
        platform='qq',
        priority=20,
        description='xcvts (musicdl 列表，需解密 apiKey)',
        enabled=False,  # 需解密
        can_parse_url=True,
        parse_url_url='https://api.xcvts.cn/api/music/qq?mid={song_id}&type=SQ无损',
        extract_url=lambda d: d.get('data', {}).get('music', '') if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. 317ak - musicdl 列表
    ApiSource(
        name='317ak_url',
        platform='qq',
        priority=30,
        description='317ak (musicdl 列表)',
        enabled=False,  # 需 ckey
        can_parse_url=True,
        parse_url_url='https://api.317ak.cn/api/yinyue/qqyinyue?i={song_id}&br=10&type=json&lrc=1',
        extract_url=extract_first_url,
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 5. lxmusic - musicdl 列表
    ApiSource(
        name='lxmusic_url',
        platform='qq',
        priority=40,
        description='lxmusic (musicdl 列表)',
        can_parse_url=True,
        parse_url_url='https://lxmusicapi.onrender.com/url/tx/{song_id}/flac',
        extract_url=extract_first_url,
        headers=QQ_LXMUSIC_HEADERS,
        timeout=15,
    ),
    # 6. nki - musicdl 列表
    ApiSource(
        name='nki_url',
        platform='qq',
        priority=50,
        description='nki (musicdl 列表)',
        can_parse_url=True,
        parse_url_url='https://api.nki.pw/API/music_open_api.php?mid={song_id}&apikey=placeholder',
        extract_url=lambda d: (
            d.get('song_play_url_sq') or
            d.get('song_play_url_pq') or
            d.get('song_play_url_hq') or
            d.get('song_play_url') or
            ''
        ) if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=20,
    ),
    # 7. tang (s01s) - musicdl 列表（已死，保留作参考）
    ApiSource(
        name='tang_url',
        platform='qq',
        priority=60,
        description='tang.s01s (musicdl 列表，已死)',
        enabled=False,  # 站点不存在
        can_parse_url=True,
        parse_url_url='https://tang.api.s01s.cn/music_open_api.php?mid={song_id}',
        extract_url=lambda d: (
            d.get('song_play_url_sq') or
            d.get('song_play_url_pq') or
            d.get('song_play_url_hq') or
            d.get('song_play_url') or
            ''
        ) if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 8. xianyuw - musicdl 列表（需解密 key）
    ApiSource(
        name='xianyuw_url',
        platform='qq',
        priority=70,
        description='xianyuw (musicdl 列表，需解密 key)',
        enabled=False,  # 需解密
        can_parse_url=True,
        parse_url_url='https://apii.xianyuw.cn/api/v1/qq-music-search?id={song_id}&no_url=0&br=hires',
        extract_url=lambda d: d.get('data', {}).get('url', '') if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 9. lpz - musicdl 列表
    ApiSource(
        name='lpz_url',
        platform='qq',
        priority=80,
        description='lpz (musicdl 列表)',
        can_parse_url=True,
        parse_url_url='https://lpz.chatc.vip/apiqq.php?songmid={song_id}&type=json&br=1',
        extract_url=extract_first_url,
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 10. cyapi - musicdl 列表（需 apikey）
    ApiSource(
        name='cyapi_url',
        platform='qq',
        priority=90,
        description='cyapi (musicdl 列表，需 apikey)',
        enabled=False,  # 需 apikey
        can_parse_url=True,
        parse_url_url='https://cyapi.top/API/qq_music.php?apikey={apikey}&type=json&mid={song_id}&quality=lossless',
        extract_url=extract_first_url,
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 11. QQ 官方 musicu.fcg（vkey）- musicdl 列表（需 vkey/cookie）
    ApiSource(
        name='qq_official_vkey',
        platform='qq',
        priority=100,
        description='QQ 官方 vkey/GetVkey（需 sign/cookie）',
        enabled=False,  # 需 sign/cookie
        can_parse_url=True,
        method='POST',
        parse_url_url='https://u.y.qq.com/cgi-bin/musicu.fcg',
        post_data={
            'comm': '{"format":"json","inCharset":"utf-8","outCharset":"utf-8"}',
            'req_0': '{"module":"music.vkey.GetVkey","method":"CgiGetVkey","param":{"guid":"1234567890","songmid":["{song_id}"],"songtype":[0],"uin":"0","loginflag":1,"platform":"20"}}',
        },
        extract_url=lambda d: (
            d.get('req_0', {}).get('data', {}).get('midurlinfo', [{}])[0].get('purl', '')
            if isinstance(d, dict) else ''
        ),
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
]


# ==================== 歌曲元信息源 ====================

# QQ file.size_* 字段 → 前端 quality 字段映射
_QQ_FILE_QUALITY_MAP = {
    'standard': 'size_128mp3',  # 128kbps MP3
    'exhigh':   'size_320mp3',  # 320kbps MP3
    'lossless': 'size_flac',    # FLAC
    'hires':    'size_hires',   # 24bit HiRes
}


def _extract_qq_official_info(d: dict, song_id: str = '') -> dict:
    """从 QQ 官方 get_song_detail_yqq 响应提取歌曲元信息

    响应路径: songinfo.data.track_info
    关键字段:
      - name / title / mid / id
      - singer: [{name}, ...]
      - album: {name, mid} → cover_url = f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{album.mid}.jpg"
      - interval (秒)
      - pay: {pay_month, pay_play, pay_down, price_track, ...}
      - file: {size_128mp3, size_320mp3, size_flac, size_hires, size_ape, ...}
    """
    if not isinstance(d, dict):
        return {}
    track = d.get('songinfo', {}).get('data', {}).get('track_info', {}) or {}
    if not track:
        return {}
    # 歌手列表
    singers = track.get('singer') or []
    if isinstance(singers, list):
        artists_str = '/'.join(
            s.get('name', '') for s in singers if isinstance(s, dict) and s.get('name')
        )
    else:
        artists_str = ''
    # 专辑
    album = track.get('album') or {}
    if isinstance(album, dict):
        album_name = album.get('name', '') or album.get('title', '')
        album_mid = album.get('mid', '') or album.get('albumMid', '')
    else:
        album_name, album_mid = '', ''
    # 封面：官方封面 URL 模板
    pic = ''
    if album_mid:
        pic = f'https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg'
    # 时长（秒 → 毫秒）
    interval = int(track.get('interval') or 0) * 1000
    # 付费信息
    pay_info = track.get('pay') or {}
    pay_month = pay_info.get('pay_month', 0)
    pay_play = pay_info.get('pay_play', 0)
    pay_down = pay_info.get('pay_down', 0)
    pay = bool(pay_month or pay_play or pay_down)
    fee = 1 if (pay_month or pay_play) else 0
    # 音质大小
    file_info = track.get('file') or {}
    quality_map = {}
    for quality_key, file_field in _QQ_FILE_QUALITY_MAP.items():
        size = file_info.get(file_field) or 0
        if size > 0:
            quality_map[quality_key] = {
                'size': int(size),
                # bitrate 从字段名推断
                'br': {
                    'standard': 128000,
                    'exhigh': 320000,
                    'lossless': 999000,
                    'hires': 1411000,
                }.get(quality_key, 0),
            }
    return {
        'id': track.get('mid') or track.get('songmid') or song_id,
        'name': track.get('name') or track.get('title') or '',
        'artists': artists_str,
        'album': album_name,
        'picUrl': pic,
        'duration': interval,
        'pay': pay,
        'fee': fee,
        'qualityMap': quality_map,
    }


QQ_PARSE_INFO_SOURCES = [
    # 1. QQ 官方 get_song_detail_yqq（musicdl 列表，最完整：album/cover/qualityMap/pay）
    ApiSource(
        name='qq_official_info',
        platform='qq',
        priority=0,
        description='QQ 官方 get_song_detail_yqq (musicu.fcg)',
        can_parse_info=True,
        method='POST',
        parse_info_url='https://u.y.qq.com/cgi-bin/musicu.fcg',
        # 用 dict 让 chain 走 is_json=True (json.dumps) 路径，避免对字符串误做 .format()
        is_json=True,
        post_data={
            'songinfo': {
                'method': 'get_song_detail_yqq',
                'module': 'music.pf_song_detail_svr',
                'param': {'song_mid': '{song_id}'},
            }
        },
        # 用 helper 提取（支持 song_id 兜底）
        extract_info=lambda d, song_id='': _extract_qq_official_info(d, song_id),
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. xunhuisi_info（兜底，priority 10）
    ApiSource(
        name='xunhuisi_info',
        platform='qq',
        priority=10,
        description='xunhuisi (mid 解析，title/singer/cover)',
        can_parse_info=True,
        parse_info_url='https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json',
        extract_info=lambda d, song_id='': {
            'id': song_id,
            'name': d.get('title', ''),
            'artists': d.get('singer', ''),
            'album': '',
            'picUrl': d.get('cover', ''),
        } if isinstance(d, dict) and d.get('code') == 200 else {},
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. vkeys info - musicdl 列表
    ApiSource(
        name='vkeys_info',
        platform='qq',
        priority=20,
        description='vkeys info (musicdl 列表)',
        can_parse_info=True,
        parse_info_url='https://api.vkeys.cn/music/tencent/song/link?mid={song_id}&quality=999',
        extract_info=lambda d: d.get('data', {}) if isinstance(d, dict) else {},
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌词源 ====================

QQ_PARSE_LYRIC_SOURCES = [
    # 1. xunhuisi 提供 LRC 歌词（在 lyric 字段）
    ApiSource(
        name='xunhuisi_lyric',
        platform='qq',
        priority=0,
        description='xunhuisi (LRC 歌词)',
        can_parse_lyric=True,
        parse_lyric_url='https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 2. vkeys 提供 LRC 歌词
    ApiSource(
        name='vkeys_lyric',
        platform='qq',
        priority=10,
        description='vkeys (musicdl 列表，LRC 歌词)',
        can_parse_lyric=True,
        parse_lyric_url='https://api.vkeys.cn/v2/music/tencent/lyric?mid={song_id}',
        extract_lyric=lambda d: d.get('data', {}).get('lrc', '') if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=10,
    ),
    # 3. xcvts 提供 LRC 歌词（data.lyric）
    ApiSource(
        name='xcvts_lyric',
        platform='qq',
        priority=20,
        description='xcvts (musicdl 列表，data.lyric 字段)',
        enabled=False,  # 需解密
        can_parse_lyric=True,
        parse_lyric_url='https://api.xcvts.cn/api/music/qq?mid={song_id}&type=SQ无损',
        extract_lyric=lambda d: d.get('data', {}).get('lyric', '') if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. 317ak 提供 LRC 歌词（lyric 字段）
    ApiSource(
        name='317ak_lyric',
        platform='qq',
        priority=30,
        description='317ak (musicdl 列表，lyric 字段)',
        enabled=False,  # 需 ckey
        can_parse_lyric=True,
        parse_lyric_url='https://api.317ak.cn/api/yinyue/qqyinyue?i={song_id}&br=10&type=json&lrc=1',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 5. lxmusic 暂不提供歌词
    ApiSource(
        name='lxmusic_lyric',
        platform='qq',
        priority=40,
        description='lxmusic (musicdl 列表，暂未提供歌词)',
        enabled=False,
        can_parse_lyric=True,
        parse_lyric_url='https://lxmusicapi.onrender.com/url/tx/{song_id}/flac',
        extract_lyric=lambda d: '',
        headers=QQ_LXMUSIC_HEADERS,
        timeout=15,
    ),
]
