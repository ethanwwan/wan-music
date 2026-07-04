"""QQ 音乐 ApiSource 定义

所有数据来源：musicdl qq.py + 实测（见 scripts/probe_apis.py）

QQ 官方 c.y.qq.com/soso/fcgi-bin/client_search_cp 免登录免 sign，
返回完整字段（album/cover/qualityMap/pay）。
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import (
    extract_first_url,
    extract_text_url,
    url_quote,
)
from ._playlist_extractors import (
    extract_qq_playlist as _extract_qq_playlist,
    extract_netease_playlist as _extract_netease_playlist,
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


def _qq_album_cover(albummid: str, size: int = 300) -> str:
    """QQ 官方封面 URL 模板：https://y.gtimg.cn/music/photo_new/T002R{size}x{size}M000{albummid}.jpg"""
    if not albummid:
        return ''
    return f'https://y.gtimg.cn/music/photo_new/T002R{size}x{size}M000{albummid}.jpg'


def _decode_qq_cgi_lyric(d: dict) -> str:
    """解码 QQ 官方 c.y.qq.com 旧版歌词 API 返回的 base64 编码歌词

    字段:
        d['lyric']  : 原歌词 base64 字符串
        d['trans']  : 翻译歌词 base64 字符串
    """
    import base64
    b64 = d.get('lyric') or ''
    if not b64:
        return ''
    try:
        return base64.b64decode(b64).decode('utf-8', errors='replace')
    except Exception:
        return ''


# ==================== QQ 官方 music.vkey.GetVkey（参考 v1.1.3 + musicdl 实际可工作版本） ====================
# 关键实测发现（v1.1.3 真实代码能拿 FLAC，HEAD 改的 musicdl ct=19 反而拿不到）：
# 1. comm.ct 必须是 **24 (int)**，不是 musicdl 风格的 "19" (string)
# 2. comm.cv 必须是 **0 (int)**
# 3. comm 不能带 v/uid 字段
# 4. guid 字段对结果有影响（v1.1.3 用 self.guid 随机数, 这里用 "10000"）
# 5. module=music.vkey.GetVkey, method=UrlGetVkey（v1.1.3 正确）
# 6. URL 拼接：v1.1.3 用 sip[1] + purl，HEAD 改的 isure.stream.qqmusic.qq.com 是错的
#    实际 QQ 后端返的 sip 列表里：
#      [0] = http://aqqmusic.tc.qq.com/
#      [1] = http://isure.stream.qqmusic.qq.com/  ← 5.1 环绕声
#      [2] = http://ws.stream.qqmusic.qq.com/     ← 高品质 (FLAC)
#      [3+] = ...
#    选哪个 sip 取决于文件类型。V1.1.3 的 sip_index = 1 (second) 对大多数文件 OK
#    但无损 FLAC 应该是 sip[2] (ws.stream.qqmusic.qq.com)
#
# 经验证（v1.1.3 实测）：
#   张杰 - 他不懂 (003aQYLo2x8izx): result=101404 (无 cookie 必败)
#   巴拉莱卡 (002dB4xY3S3gCr):     ✅ 25.3MB FLAC (Q000 prefix = Atmos 2.0)
#
# QQ 音质 → (filename prefix, 文件后缀)
_QQ_VIP_FILE_CONFIG = {
    'jymaster': ('AI00', '.flac'),  # 母带
    'master':   ('AI00', '.flac'),
    'dolby':    ('RS01', '.flac'),  # 杜比全景声
    'sky':      ('Q001', '.flac'),  # 沉浸环绕声 5.1
    'hires':    ('SQ00', '.flac'),  # Hi-Res
    'jyeffect': ('SQ00', '.flac'),
    'lossless': ('F000', '.flac'),  # FLAC 无损
    'flac':     ('F000', '.flac'),
    'exhigh':   ('M800', '.mp3'),
    '320':      ('M800', '.mp3'),
    'standard': ('M500', '.mp3'),
    '128':      ('M500', '.mp3'),
}


def _qq_vkey_prepare_request(url, method, headers, post_data, is_json, kwargs):
    """动态生成 music.vkey.GetVkey/UrlGetVkey 请求（按 quality 选 filename）

    完全照搬 v1.1.3 _get_song_url_official 真实能下载 FLAC 的实现
    """
    song_id = kwargs.get('song_id', '')
    quality = kwargs.get('quality', 'lossless')
    # v1.1.3 用 dolby=RS01，hires=SQ00，lossless=F000，exhigh=M800，standard=M500
    prefix, ext = _QQ_VIP_FILE_CONFIG.get(quality, ('F000', '.flac'))
    filename = f"{prefix}{song_id}{song_id}{ext}"
    return {
        'url': url,
        'method': 'POST',
        'headers': {**headers, 'Content-Type': 'application/json; charset=utf-8'},
        'is_json': True,
        'post_data': {
            # v1.1.3 真实结构
            "music.vkey.GetVkey.UrlGetVkey": {
                "module": "music.vkey.GetVkey",
                "method": "UrlGetVkey",
                "param": {
                    "filename": [filename],
                    "guid": kwargs.get('guid', '10000'),  # v1.1.3 用 self.guid (32 字符随机)
                    "songmid": [song_id],
                    "songtype": [0],
                    "uin": "0",
                    "loginflag": 1,
                    "platform": "20"
                }
            },
            "comm": {
                "ct": 24,            # ★ 关键: int=24 (v1.1.3 实际能拿 FLAC)
                "cv": 0,             # ★ 关键: int=0
                "format": "json",
                "inCharset": "utf-8",
                "outCharset": "utf-8",
            }
        }
    }


def _extract_qq_official_vkey(d: dict, **kwargs) -> str:
    """从 music.vkey.GetVkey.UrlGetVkey 响应拼真实 URL

    v1.1.3 真实实现：sip[sip_index=1] + purl
    """
    if not isinstance(d, dict):
        return ''
    key = 'music.vkey.GetVkey.UrlGetVkey'
    data = d.get(key, {}).get('data', {}) if isinstance(d.get(key), dict) else {}
    if not isinstance(data, dict):
        return ''
    midurlinfo = data.get('midurlinfo', [])
    if not isinstance(midurlinfo, list) or not midurlinfo:
        return ''
    info = midurlinfo[0] if isinstance(midurlinfo[0], dict) else {}
    purl = info.get('purl') or info.get('wifiurl') or ''
    if not purl or not purl.startswith('/'):
        return ''
    sip = data.get('sip', [])
    if not isinstance(sip, list) or not sip:
        return ''
    # v1.1.3: sip_index = 1 if len(sip) > 1 else 0
    sip_index = 1 if len(sip) > 1 else 0
    base_sip = sip[sip_index] if isinstance(sip[sip_index], str) else ''
    if not base_sip:
        return ''
    return (base_sip + purl).replace('http://', 'https://')


def extract_qq_official_search(d: dict) -> list:
    """从 QQ 官方 client_search_cp 响应提取歌曲列表

    响应路径：data.song.list[]
    关键字段：
      - songid / songmid / songname
      - singer: [{id, mid, name}]
      - albumid / albummid / albumname
      - interval (秒) / pubtime
      - pay: {payalbum, paydownload, payinfo, payplay, paytrackmouth, paytrackprice}
      - size128 / size320 / sizeape / sizeflac / sizeogg
      - preview: {trybegin, tryend}
    """
    if not isinstance(d, dict):
        return []
    return d.get('data', {}).get('song', {}).get('list', []) or []


# ==================== 搜索源 ====================

QQ_SEARCH_SOURCES = [
    # 1. QQ 官方 client_search_cp - 免登录免 sign，返回完整字段（album/cover/qualityMap/pay）
    ApiSource(
        name='qq_official_search',
        platform='qq',
        priority=0,
        description='QQ 官方 client_search_cp（c.y.qq.com 完整字段）',
        can_search=True,
        search_url='https://c.y.qq.com/soso/fcgi-bin/client_search_cp?w={keyword_encoded}&n={limit}&format=json',
        extract_search=extract_qq_official_search,
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 2. xunhuisi（兜底：name 搜索 + mid 解析）
    ApiSource(
        name='xunhuisi_search',
        platform='qq',
        priority=10,
        description='xunhuisi (name 搜索兜底)',
        family='xunhuisi',
        can_search=True,
        search_url='https://api.xunhuisi.store/API/QQMusic/Song.php?name={keyword_encoded}&type=json',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 2. nki search - musicdl 列表（实测 404）
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
# 前2（保留）：qq_official_vkey(需cookie) → vkeys_url

def _vkeys_multi_extract(d: dict, song_id: str = None, **kwargs) -> str:
    """vkeys API 多质量降级提取器

    兼容 v1.1.3 逻辑：先试 quality=13（FLAC），不行就 11→10→8。
    """
    import requests as _requests
    if not isinstance(d, dict):
        return ''
    url = d.get('data', {}).get('url', '') if isinstance(d.get('data'), dict) else ''
    if url and url.startswith('http') and len(url) > 50:
        return url
    # 质量降级（v1.1.3 同款 requests.get，支持 SSL）
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://y.qq.com/'}
    for q in [11, 10, 8]:
        try:
            api_url = f'https://api.vkeys.cn/music/tencent/song/link?mid={song_id}&quality={q}'
            resp = _requests.get(api_url, headers=headers, timeout=8)
            data = resp.json()
            u = data.get('data', {}).get('url', '') if isinstance(data.get('data'), dict) else ''
            if u and u.startswith('http') and len(u) > 50:
                return u
        except Exception:
            continue
    return ''


QQ_PARSE_URL_SOURCES = [
    # 1. xunhuisi - musicdl 列表 (无 br 参数)
    # max_quality='exhigh'：实测只能返 M4A 256k
    ApiSource(
        name='xunhuisi_url',
        platform='qq',
        priority=20,
        description='xunhuisi (musicdl 列表, 只能 M4A 256k)',
        family='xunhuisi',  # ★ xunhuisi 家族
        enabled=False,
        can_parse_url=True,
        parse_url_url='https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json',
        extract_url=lambda d: (
            d.get('music_url', '') if isinstance(d, dict) else ''
        ),
        headers=QQ_COMMON_HEADERS,
        timeout=15,
        max_quality='exhigh',
    ),
    # 2. vkeys - v1.1.3 实测能拿 FLAC！quality=13 是关键 (SR_MASTER)
    # v1.1.3 实测: [vkeys quality=13] 成功返 FLAC
    # 实测 ✅ 可用，保留为第2兜底
    ApiSource(
        name='vkeys_url',
        platform='qq',
        priority=5,
        description='vkeys (多质量降级: 13→11→10→8，返 FLAC)',
        family='vkeys',
        can_parse_url=True,
        parse_url_url='https://api.vkeys.cn/music/tencent/song/link?mid={song_id}&quality=13',
        extract_url=_vkeys_multi_extract,
        headers=QQ_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',
    ),
    # 3. xcvts - musicdl 列表（需解密 apiKey）
    # max_quality='lossless'：API 描述是 SQ无损（FLAC）
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
        max_quality='lossless',
    ),
    # 4. 317ak - musicdl 列表
    # max_quality='lossless'：br=10 是 lossless
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
        max_quality='lossless',
    ),
    # 5. lxmusic - 只返 MP3 320kbps，无无损，已禁用
    # max_quality='hires'：模板写的是 flac24bit，实测只返普通 MP3
    # 注：lxmusic_lyric 已禁用（API 不存在），不设 family，避免误导
    ApiSource(
        name='lxmusic_url',
        platform='qq',
        priority=40,
        description='lxmusic (测试只返 MP3，无无损)',
        enabled=False,  # 实测只返 MP3 320kbps，无无损
        can_parse_url=True,
        parse_url_url='https://lxmusicapi.onrender.com/url/tx/{song_id}/flac24bit',
        extract_url=extract_first_url,
        headers=QQ_LXMUSIC_HEADERS,
        timeout=8,  # onrender.com 冷启动慢，但有其他源兜底时不必等
        max_quality='hires',
    ),
    # 6. nki - musicdl 列表（需解密 apikey，HTTP 403）
    # max_quality='lossless'：song_play_url_sq 是 FLAC
    ApiSource(
        name='nki_url',
        platform='qq',
        priority=50,
        description='nki (musicdl 列表，需解密 apikey)',
        enabled=False,  # HTTP 403，无有效 apikey
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
        max_quality='lossless',
    ),
    # 7. tang (s01s) - musicdl 列表（P=60 低优先级，可用但不保留）
    ApiSource(
        name='tang_url',
        platform='qq',
        priority=60,
        description='tang.s01s (musicdl 列表，实测返 FLAC，保留前3已满)',
        enabled=False,  # 保留前2: qq_official_vkey → vkeys_url (lxmusic 实测只返 MP3 已禁用)
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
        max_quality='lossless',
    ),
    # 8. xianyuw - musicdl 列表（需解密 key）
    # max_quality='hires'：br=hires 参数
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
        max_quality='hires',
    ),
    # 9. lpz - musicdl 列表
    # max_quality='exhigh'：br=1 实际只返 320k
    ApiSource(
        name='lpz_url',
        platform='qq',
        priority=80,
        description='lpz (musicdl 列表, br=1 实际只返 320k)',
        enabled=False,
        can_parse_url=True,
        parse_url_url='https://lpz.chatc.vip/apiqq.php?songmid={song_id}&type=json&br=1',
        extract_url=extract_first_url,
        headers=QQ_COMMON_HEADERS,
        timeout=10,
        max_quality='exhigh',
    ),
    # 10. cyapi - musicdl 列表（需 apikey）
    # max_quality='lossless'：quality=lossless 参数
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
        max_quality='lossless',
    ),
    # 11. QQ 官方 music.vkey.GetVkey/UrlGetVkey（★ 关键数据源，能拿 FLAC）
    # 完整照搬 v1.1.3 _get_song_url_official 真实能下载 FLAC 的实现
    # 实测：002dB4xY3S3gCr (巴拉莱卡) → 25.3MB FLAC ✅
    # 必须有 QQ cookie（uin + qqmusic_key），无 cookie 时 result=101404/purl 空
    # needs_cookie=True：chain 框架自动跳过无 cookie 情况，行为与 netease 一致
    ApiSource(
        name='qq_official_vkey',
        platform='qq',
        priority=0,  # 最高：有 cookie 时能拿 FLAC
        description='QQ 官方 vkey (v1.1.3 同款，需 cookie 才能拿 FLAC)',
        enabled=True,
        needs_cookie=True,
        cookie_file='qq_cookie.txt',
        can_parse_url=True,
        method='POST',
        parse_url_url='https://u.y.qq.com/cgi-bin/musicu.fcg',
        # 用 prepare_request 钩子动态构造 filename（按 quality）
        prepare_request=_qq_vkey_prepare_request,
        extract_url=_extract_qq_official_vkey,
        headers=QQ_COMMON_HEADERS,
        timeout=8,
        max_quality='hires',  # 有 cookie 时理论能拿 SQ00 (Hi-Res)
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
    # ★ musicdl 参考：xunhuisi 响应 code=0 表示成功，data 字段含 title/singer/cover
    #   code=200 是旧版，新版统一用 code=0
    ApiSource(
        name='xunhuisi_info',
        platform='qq',
        priority=10,
        description='xunhuisi (mid 解析，title/singer/cover)',
        family='xunhuisi',  # ★ xunhuisi 家族
        can_parse_info=True,
        parse_info_url='https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json',
        extract_info=lambda d, song_id='': (
            {
                'id': song_id,
                'name': (d.get('data') or {}).get('title', '') or d.get('title', ''),
                'artists': (d.get('data') or {}).get('singer', '') or d.get('singer', ''),
                'album': (d.get('data') or {}).get('album', '') or d.get('album', ''),
                'picUrl': (d.get('data') or {}).get('cover', '') or d.get('cover', ''),
            }
            if isinstance(d, dict) and (d.get('code') in (0, 200) or d.get('data'))
            else {}
        ),
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. vkeys info - musicdl 列表（只返回 URL/quality 信息，无歌曲元数据）
    # vkeys 没有独立的 info 接口，URL 端点返回的是 songID/songMID/kbps/url，不含 name/title
    # 禁用，交由 qq_official_info 和 xunhuisi_info 处理
    ApiSource(
        name='vkeys_info',
        platform='qq',
        priority=20,
        description='vkeys info (只返回 URL 信息，无元数据)',
        enabled=False,
        can_parse_info=True,
        parse_info_url='https://api.vkeys.cn/music/tencent/song/link?mid={song_id}&quality=999',
        extract_info=lambda d: d.get('data', {}) if isinstance(d, dict) else {},
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌词源 ====================

QQ_PARSE_LYRIC_SOURCES = [
    # 0. QQ 官方 c.y.qq.com 旧版歌词接口（实测可用，无 cookie 也能拿到）
    # GET  c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid=...
    # 返 Content-Type: text/html 但 body 是 JSON
    # 字段: data.lyric (base64), data.trans (base64 翻译)
    # priority=0 最高：官方源无第三方依赖，无 cookie
    ApiSource(
        name='qq_official_cgi_lyric',
        platform='qq',
        priority=0,
        description='QQ 官方 c.y.qq.com 旧版歌词（base64，无 cookie 即可）',
        can_parse_lyric=True,
        parse_lyric_url='https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid={song_id}&format=json',
        extract_lyric=lambda d: _decode_qq_cgi_lyric(d) if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=5,  # c.y.qq.com 有时 ReadTimeout，缩短超时避免 8s 前端超时
    ),
    # 1. xunhuisi 提供 LRC 歌词（在 lyric 字段，可能嵌套在 data 里）
    # ★ musicdl 参考：xunhuisi 响应 code=0 表示成功，lyric 可能在 data.lyric 或顶层 lyric
    ApiSource(
        name='xunhuisi_lyric',
        platform='qq',
        priority=10,
        description='xunhuisi (LRC 歌词)',
        family='xunhuisi',  # ★ xunhuisi 家族
        can_parse_lyric=True,
        parse_lyric_url='https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json',
        extract_lyric=lambda d: (
            (d.get('data') or {}).get('lyric', '') or d.get('lyric', '')
        ) if isinstance(d, dict) else '',
        headers=QQ_COMMON_HEADERS,
        timeout=15,
    ),
    # 2. vkeys 提供 LRC 歌词
    # ★ musicdl 参考：vkeys 响应 data 可能是 dict 或 list，lrc 在 data.lrc 或 data[0].lrc
    ApiSource(
        name='vkeys_lyric',
        platform='qq',
        priority=10,
        description='vkeys (musicdl 列表，LRC 歌词)',
        family='vkeys',  # ★ vkeys 家族：vkeys_url 抢答后优先用这个 lyric
        can_parse_lyric=True,
        parse_lyric_url='https://api.vkeys.cn/v2/music/tencent/lyric?mid={song_id}',
        extract_lyric=lambda d: (
            (d.get('data', {}) or {}).get('lrc', '')
            if isinstance(d.get('data'), dict)
            else (d.get('data', [{}])[0].get('lrc', '') if isinstance(d.get('data'), list) and d['data'] else '')
        ) if isinstance(d, dict) else '',
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


# ==================== 歌单解析 ====================

QQ_PARSE_PLAYLIST_SOURCES = [
    ApiSource(
        name='qq_official_playlist',
        platform='qq',
        priority=0,
        description='QQ 官方 qzone fcg_ucc_getcdinfo_byids_cp（无需登录）',
        can_parse_playlist=True,
        parse_playlist_url=(
            'https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg'
            '?disstid={playlist_id}&type=1&json=1&utf8=1&onlysong=0&format=json'
        ),
        extract_playlist=_extract_qq_playlist,
        headers={
            **QQ_COMMON_HEADERS,
            'Referer': 'https://y.qq.com/n/ryqq/playlist',
        },
        timeout=15,
    ),
    ApiSource(
        name='gdstudio_playlist',
        platform='qq',
        priority=20,
        description='gdstudio 跨平台歌单（兜底，只接受 source=netease/kuwo/joox，固定返回网易云格式）',
        family='gdstudio',
        can_parse_playlist=True,
        parse_playlist_url='https://music-api.gdstudio.xyz/api.php?types=playlist&id={playlist_id}&source=netease',
        extract_playlist=_extract_netease_playlist,
        headers={'User-Agent': 'Mozilla/5.0'},
        timeout=20,
    ),
]
