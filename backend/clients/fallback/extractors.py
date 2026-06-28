"""通用响应提取器

每个 ApiSource 在 extract_url / extract_info / extract_search / extract_lyric
中引用这些函数（或自己定义的函数）。

约定：所有提取器接收响应 dict，返回提取的数据。
找不到时返回 None / [] / '' / {}，不抛异常。
"""
import re
import time
from typing import List, Dict, Any, Optional
from urllib.parse import quote


# ==================== 通用 URL 提取 ====================

def extract_first_url(d: dict) -> str:
    """从常见字段中找第一个 http URL

    检查字段：url, data, download_url, song_file_url, music_url,
             song_play_url, song_play_url_standard, song_play_url_hq
    """
    if not isinstance(d, dict):
        return ''
    # 直接字段
    for k in ['url', 'data', 'download_url', 'song_file_url', 'music_url',
              'song_play_url', 'song_play_url_standard', 'song_play_url_hq']:
        v = d.get(k)
        if isinstance(v, str) and v.startswith('http'):
            return v
        if isinstance(v, dict):
            for kk in ['url', 'link', 'music_url']:
                vv = v.get(kk)
                if isinstance(vv, str) and vv.startswith('http'):
                    return vv
        if isinstance(v, list) and v and isinstance(v[0], dict):
            vv = v[0].get('url') or v[0].get('link') or v[0].get('music_url')
            if isinstance(vv, str) and vv.startswith('http'):
                return vv
    return ''


def extract_nested_url(d: dict, *keys: str) -> str:
    """从嵌套 dict 中按 keys 顺序查找 URL"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return ''
        cur = cur.get(k)
    if isinstance(cur, str) and cur.startswith('http'):
        return cur
    if isinstance(cur, dict):
        return extract_first_url(cur)
    if isinstance(cur, list) and cur and isinstance(cur[0], dict):
        return extract_first_url(cur[0])
    return ''


def extract_text_url(d: Any) -> str:
    """有些 API（如 byfuns）直接返回纯文本 URL"""
    if isinstance(d, str) and d.startswith('http'):
        return d
    return ''


# ==================== 网易云特定提取器 ====================

def extract_netease_official_url(d: dict) -> str:
    """网易云官方 /eapi/song/enhance/player/url 响应

    响应格式: {"data": [{"url": "..."}]}
    """
    if not isinstance(d, dict):
        return ''
    data = d.get('data')
    if isinstance(data, list) and data:
        url = data[0].get('url', '')
        if url and url.startswith('http'):
            return url
    return ''


def extract_xuanluoge_url(d: dict) -> str:
    """xuanluoge 响应可能是 list 也可能是 dict

    例子 1: [{"url": "https://..."}]
    例子 2: {"data": [{"url": "https://..."}]}
    """
    if isinstance(d, list) and d:
        return d[0].get('url', '') or ''
    if isinstance(d, dict):
        # 试 data[0].url
        data = d.get('data')
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0].get('url', '')
        if isinstance(data, dict):
            return data.get('url', '')
    return ''


def extract_xuanluoge_song_info(d: dict) -> dict:
    """xuanluoge getMusicInfo 响应

    {"id":..., "name":..., "artists":..., "album":..., "picUrl":..., "duration":...}
    """
    if not isinstance(d, dict) or not d.get('id'):
        return {}
    return {
        'id': d.get('id', 0),
        'name': d.get('name', ''),
        'artists': d.get('artists', ''),
        'album': d.get('album', ''),
        'picUrl': d.get('picUrl', ''),
        'duration': d.get('duration', 0),
    }


def extract_netease_song_info(d: dict) -> dict:
    """网易云官方 /api/song/detail 响应

    {"songs": [{"id", "name", "artists" or "ar", "album" or "al",
                "duration" or "dt", "fee", "noCopyrightRcmd", "st"}]}
    """
    songs = d.get('songs') if isinstance(d, dict) else None
    if not songs:
        return {}
    s = songs[0]
    artists = s.get('artists', s.get('ar', []))
    album_info = s.get('album', s.get('al', {}))
    artists_str = '/'.join(a['name'] for a in artists if isinstance(a, dict) and 'name' in a)
    # 付费/版权标记
    fee = s.get('fee', 0)
    st = s.get('st', 0)
    pay = (fee == 1) or (st < 0) or bool(s.get('noCopyrightRcmd'))
    return {
        'id': s.get('id', 0),
        'name': s.get('name', ''),
        'artists': artists_str,
        'album': album_info.get('name', '') if isinstance(album_info, dict) else '',
        'picUrl': album_info.get('picUrl', '') if isinstance(album_info, dict) else '',
        'duration': s.get('duration') or s.get('dt') or 0,
        'pay': pay,
        'fee': fee,
    }


def extract_gdstudio_song_info(d: dict) -> dict:
    """gdstudio /api.php?types=info 响应"""
    if not isinstance(d, dict) or not d.get('id'):
        return {}
    artists = d.get('artist', [])
    if isinstance(artists, list):
        artists_str = '/'.join(str(a) for a in artists)
    else:
        artists_str = str(artists or '')
    return {
        'id': int(d.get('id', 0)),
        'name': d.get('name', ''),
        'artists': artists_str,
        'album': d.get('album', ''),
        'picUrl': '',
        'duration': 0,
    }


def extract_haitangw_song_info(d: dict) -> str:
    """haitangw parse 端点返回 data 里只有元信息，但据说 url 也在

    响应: {"code":200, "data":{"rid":..., "name":..., "artist":..., ...}}
    """
    if not isinstance(d, dict):
        return ''
    data = d.get('data', {})
    if isinstance(data, dict):
        # haitanw 不会返回完整 url，跳过
        return ''
    return ''


def extract_netease_official_search(d: dict) -> list:
    """网易云 /api/cloudsearch/pc 响应

    {"result": {"songs": [...], "songCount": N}}
    """
    result = d.get('result', {}) if isinstance(d, dict) else {}
    return result.get('songs', []) if isinstance(result, dict) else []


def extract_netease_official_lyric(d: dict) -> str:
    """网易云 /api/song/lyric 响应"""
    if not isinstance(d, dict):
        return ''
    lrc = d.get('lrc', {})
    if isinstance(lrc, dict):
        return lrc.get('lyric', '') or ''
    return ''


def extract_netease_search(d: dict) -> list:
    """通用网易云搜索结果提取（统一接口）

    支持官方、gdstudio、xuanluoge 等多种响应格式
    """
    if not isinstance(d, dict):
        return []
    # 官方 cloudsearch 格式
    if 'result' in d and isinstance(d['result'], dict):
        return d['result'].get('songs', [])
    # gdstudio 直接返回 list
    if isinstance(d.get('data'), list):
        return d['data']
    # 其它: xuanluoge 返回 list of dict
    if 'songs' in d and isinstance(d['songs'], list):
        return d['songs']
    return []


# ==================== 关键词转义 ====================

def url_quote(s: str) -> str:
    """URL 编码，支持中文"""
    return quote(str(s), safe='')


# ==================== 质量码映射 ====================

QUALITY_BR_MAP = {
    # platform: quality -> bitrate (kbps)
    'standard': 128,
    'exhigh': 320,
    'lossless': 999,
    'hires': 999,
    'jymaster': 999,
}


def quality_to_br(quality: str, default: int = 999) -> int:
    """将 quality 名称转为 bitrate 数（kbps）"""
    return QUALITY_BR_MAP.get(quality, default)


# ==================== SongInfo 标准化 ====================

def normalize_netease_song(raw: dict) -> dict:
    """将任意来源的歌曲 dict 标准化为前端期望的格式

    输入可能是官方（ar/al 字段）、gdstudio（artist 列表）、xuanluoge（artists 字符串）
    输出统一为 {id, name, artists, album, picUrl, duration, qualityMap, ...}
    """
    if not isinstance(raw, dict):
        return {}
    # artist 字段可能在多个名字下
    artists = raw.get('artists') or raw.get('artist') or raw.get('ar', [])
    if isinstance(artists, list):
        artists_str = '/'.join(
            (a.get('name', '') if isinstance(a, dict) else str(a))
            for a in artists
        )
    else:
        artists_str = str(artists or '')

    # album 字段（可能是 dict 也可能是 str）
    album = raw.get('album') or raw.get('al') or ''
    album_name = ''
    album_cover = ''
    if isinstance(album, dict):
        album_name = album.get('name', '')
        album_cover = album.get('picUrl', '') or album.get('pic', '') or ''
    else:
        album_name = str(album or '')

    # picUrl 字段：可能在顶层 picUrl / pic，也可能在 al.picUrl
    pic = raw.get('picUrl') or raw.get('pic') or album_cover or ''
    if isinstance(pic, dict):
        pic = pic.get('url', '')

    # duration
    dur = raw.get('duration') or raw.get('dt') or 0
    try:
        dur = int(dur)
    except (TypeError, ValueError):
        dur = 0

    # 音质信息：网易云官方搜索响应中包含 h/m/l/sq/hr（每个都是 {bitrate, size}）
    # 转成 {quality_key: {br, size}}，缺失字段表示该音质不可用
    quality_map = _extract_netease_quality_map(raw)

    # pay：fee=1 (VIP 单曲) / 4 (专辑) / 8 (试听/版权) 都视为付费内容
    fee = raw.get('fee', 0)
    st = raw.get('st', 0)
    pay = fee in (1, 4, 8) or (st < 0) or bool(raw.get('noCopyrightRcmd'))

    return {
        'id': str(raw.get('id') or raw.get('rid') or ''),
        'name': raw.get('name') or raw.get('title') or '',
        'artists': artists_str,
        'album': album_name,
        'picUrl': pic,
        'duration': dur,
        'pay': pay,
        'fee': fee,
        'qualityMap': quality_map,
        'bestQuality': _best_quality(quality_map),
    }


# 网易云音质码 → 前端 quality 标识
_NETEASE_QUALITY_FIELDS = {
    'standard': 'l',   # 128k
    'exhigh':   'm',   # 192k
    'lossless': 'sq',  # 999k flac
    'hires':    'hr',  # 1750k+ flac
}


def _extract_netease_quality_map(raw: dict) -> dict:
    """从网易云搜索响应提取 qualityMap

    返回: {'standard': {br, size}, 'exhigh': ..., 'lossless': ..., 'hires': ...}
    """
    qmap = {}
    for quality_key, field in _NETEASE_QUALITY_FIELDS.items():
        v = raw.get(field)
        if v and isinstance(v, dict):
            qmap[quality_key] = {
                'br': v.get('br') or v.get('bitrate') or 0,
                'size': v.get('size') or 0,
            }
    return qmap


# 音质从高到低排序
_QUALITY_ORDER = ['hires', 'jymaster', 'lossless', 'exhigh', 'standard']


def _best_quality(quality_map: dict) -> str:
    """从 qualityMap 推断可用的最高音质"""
    for q in _QUALITY_ORDER:
        if quality_map.get(q):
            return q
    return ''


def normalize_qq_song(raw: dict) -> dict:
    """QQ 歌曲标准化（兼容 client_search_cp / get_song_detail_yqq / xunhuisi 兜底）

    字段来源：
      - QQ 官方 client_search_cp: songid/songmid/songname/singer[]/albummid/albumname/
        size128/size320/sizeflac/sizeape/pay/preview/interval
      - QQ 官方 get_song_detail_yqq: name/title/singer[]/album{name,mid}/interval/pay/file{}
      - xunhuisi (兜底): name/singer/mid
    """
    if not isinstance(raw, dict):
        return {}
    # id
    song_id = str(
        raw.get('songmid') or raw.get('mid') or raw.get('id') or raw.get('songid') or ''
    )

    # 歌手
    singers = raw.get('singer') or raw.get('artists') or raw.get('singers') or []
    if isinstance(singers, list):
        artists_str = '/'.join(
            s.get('name', '') if isinstance(s, dict) else str(s) for s in singers
        )
    else:
        artists_str = str(singers or '')

    # 专辑：client_search_cp 给 albumname/albummid，info 路径给 album{name,mid}
    album_name = raw.get('albumname') or raw.get('albumName') or ''
    if not album_name:
        album = raw.get('album') or ''
        if isinstance(album, dict):
            album_name = album.get('name') or album.get('title') or ''
        else:
            album_name = str(album or '')

    # 封面：优先用 raw.picUrl，否则用官方模板 y.gtimg.cn
    pic = raw.get('picUrl') or raw.get('cover') or ''
    if not pic:
        albummid = raw.get('albummid') or raw.get('albumMid') or ''
        if not albummid and isinstance(raw.get('album'), dict):
            albummid = raw['album'].get('mid') or raw['album'].get('albumMid') or ''
        if albummid:
            pic = f'https://y.gtimg.cn/music/photo_new/T002R300x300M000{albummid}.jpg'

    # duration：官方 search 是 interval(秒)，info 路径是 interval(秒)；转毫秒
    interval = raw.get('interval') or raw.get('duration') or 0
    try:
        dur_ms = int(interval) * 1000 if int(interval) < 100000 else int(interval)
    except (TypeError, ValueError):
        dur_ms = 0

    # 音质：官方 search 给 size128/size320/sizeflac/sizeape，info 路径给 file.size_*
    quality_map = _extract_qq_quality_map(raw)

    # 付费：client_search_cp 给 pay{payplay,paydownload,payalbum}，
    # info 路径给 pay{pay_month,pay_play}。任一>0 即付费
    pay_obj = raw.get('pay') or {}
    if isinstance(pay_obj, dict):
        pay_play = pay_obj.get('payplay') or pay_obj.get('pay_play') or 0
        pay_down = pay_obj.get('paydownload') or pay_obj.get('pay_down') or 0
        pay_album = pay_obj.get('payalbum') or pay_obj.get('pay_month') or 0
        pay = bool(int(pay_play) or int(pay_down) or int(pay_album))
        fee = 1 if pay else 0
    else:
        pay = bool(raw.get('pay') or raw.get('fee') or raw.get('isPay'))
        fee = int(raw.get('fee') or 0)

    return {
        'id': song_id,
        'name': raw.get('songname') or raw.get('name') or raw.get('title') or '',
        'artists': artists_str,
        'album': album_name,
        'picUrl': pic,
        'duration': dur_ms,
        'pay': pay,
        'fee': fee,
        'qualityMap': quality_map,
        'bestQuality': _best_quality(quality_map),
    }


# QQ 搜索/信息源 file.size_* / size128 等字段 → 前端 quality
_QQ_QUALITY_FIELDS = {
    'standard': ['size128', 'size_128mp3'],   # 128kbps MP3
    'exhigh':   ['size320', 'size_320mp3'],   # 320kbps MP3
    'lossless': ['sizeflac', 'size_flac'],    # FLAC
    'hires':    ['sizehires', 'size_hires'],  # 24bit HiRes
    'jymaster': ['sizejymaster', 'size_jymaster'],
}


def _extract_qq_quality_map(raw: dict) -> dict:
    """从 QQ 搜索/信息源 raw 提取 qualityMap

    支持两套字段：
      - client_search_cp 顶层: size128 / size320 / sizeflac / sizeape
      - get_song_detail_yqq 的 file.* : size_128mp3 / size_320mp3 / size_flac / size_hires
    """
    file_obj = raw.get('file') if isinstance(raw.get('file'), dict) else {}
    qmap = {}
    for quality_key, fields in _QQ_QUALITY_FIELDS.items():
        size = 0
        for f in fields:
            # 先看 file.* 嵌套路径
            if f in file_obj and file_obj[f]:
                try:
                    size = int(file_obj[f])
                    if size > 0:
                        break
                except (TypeError, ValueError):
                    pass
            # 再看顶层
            v = raw.get(f)
            if v:
                try:
                    size = int(v)
                    if size > 0:
                        break
                except (TypeError, ValueError):
                    pass
        if size > 0:
            qmap[quality_key] = {
                'size': size,
                'br': {
                    'standard': 128000,
                    'exhigh': 320000,
                    'lossless': 999000,
                    'hires': 1411000,
                    'jymaster': 1900000,
                }.get(quality_key, 0),
            }
    return qmap


def normalize_kugou_song(raw: dict) -> dict:
    """将酷狗搜索/信息源 dict 标准化为前端格式

    musicdl 酷狗搜索字段：SongName / SingerName / AlbumName / Duration / FileHash / Image
    扩展字段：HQFileSize / HQBitrate / SQFileSize / SQBitrate / Privilege / PayType
    """
    if not isinstance(raw, dict):
        return {}
    # artist 字段可能在多个名字下
    artists = raw.get('SingerName') or raw.get('singerName') or raw.get('singer') or ''
    if not artists and isinstance(raw.get('Singers'), list):
        artists = '/'.join(
            (s.get('name', '') if isinstance(s, dict) else str(s))
            for s in raw.get('Singers', [])
        )

    # album
    album = raw.get('AlbumName') or raw.get('album') or ''

    # picUrl：Image 字段是模板 URL（含 {size}），替换为 240
    pic = raw.get('Image') or raw.get('image') or raw.get('album_img') or raw.get('imgUrl') or raw.get('picUrl') or ''
    if isinstance(pic, str) and '{size}' in pic:
        pic = pic.replace('{size}', '240')

    # duration（酷狗是秒，其他源是毫秒）
    dur = raw.get('Duration') or raw.get('duration') or 0
    try:
        dur = int(dur)
    except (TypeError, ValueError):
        dur = 0
    # 如果 < 10000 当作秒，转成毫秒
    if 0 < dur < 10000:
        dur = dur * 1000

    # 音质：酷狗搜索有 HQ/SQ/基础字段
    quality_map = {}
    sq_size = raw.get('SQFileSize') or 0
    sq_br = raw.get('SQBitrate') or 0
    hq_size = raw.get('HQFileSize') or 0
    hq_br = raw.get('HQBitrate') or 0
    base_size = raw.get('FileSize') or 0
    base_br = raw.get('Bitrate') or 0
    if sq_br and sq_size:
        quality_map['lossless'] = {'br': int(sq_br) * 1000, 'size': int(sq_size)}
    if hq_br and hq_size:
        quality_map['exhigh'] = {'br': int(hq_br) * 1000, 'size': int(hq_size)}
    if base_br and base_size:
        quality_map['standard'] = {'br': int(base_br) * 1000, 'size': int(base_size)}

    # 付费：Privilege=8 (普通) / 10 (VIP) / 4 (专辑) / 0 (免费)
    privilege = raw.get('Privilege') or 0
    pay_type = raw.get('PayType') or 0
    pay = (privilege >= 4) or (pay_type >= 1)

    # 关键：优先用 SQFileHash（FLAC 的 hash），让请求 lossless 时用 FLAC 的 hash
    # 不这样处理的话，haitanw 等三方源会拿 MP3 的 hash 去请求，找不到 FLAC 资源
    # 兜底：FileHash / hash / id
    primary_hash = (
        raw.get('SQFileHash')  # FLAC 资源
        or raw.get('sqhash')   # 别名（移动端 API 返回的字段）
        or raw.get('FileHash')
        or raw.get('hash')
        or raw.get('id')
        or ''
    )

    return {
        'id': str(primary_hash),
        # 保留 MP3 hash 作为 fallback（exhigh/standard 用）
        'mp3_hash': str(raw.get('FileHash') or raw.get('hash') or ''),
        'name': raw.get('SongName') or raw.get('name') or raw.get('songname') or '',
        'artists': artists,
        'album': album,
        'picUrl': pic,
        'duration': dur,
        'pay': pay,
        'fee': pay_type,
        'qualityMap': quality_map,
        'bestQuality': _best_quality(quality_map),
    }


def normalize_kuwo_song(raw: dict) -> dict:
    """酷我歌曲标准化（兼容 musicdl 的 abslist 项和 cenguigui data 项）

    musicdl 酷我搜索结果字段：
      - MUSICRID: 'MUSIC_123456'  → 取数字部分作为 rid
      - SONGNAME / ARTIST / ALBUM / DURATION / hts_MVPIC
      - N_MINFO / MINFO: 音质描述，格式 "level:ff,bitrate:2000,format:flac,size:51.58Mb;..."
        level 编码：zply(臻品母带) / zp(臻品HiRes) / ff(flac lossless) / p(320k ogg/mp3)
                    / h(128k) / s(aac) / l(low)
      - PAY: 16515324 二进制位标记付费
      - payInfo: 详细付费结构
    """
    if not isinstance(raw, dict):
        return {}
    # 处理 MUSICRID
    musicrid = raw.get('MUSICRID') or raw.get('musicrid') or ''
    rid = musicrid.removeprefix('MUSIC_') if isinstance(musicrid, str) else ''
    if not rid:
        rid = str(raw.get('id') or raw.get('rid') or '')

    # duration 转换（酷我是秒，info 源是毫秒）
    dur = raw.get('DURATION') or raw.get('duration') or 0
    try:
        dur = int(dur)
    except (TypeError, ValueError):
        dur = 0
    if 0 < dur < 100000:
        dur = dur * 1000

    # picUrl: hts_MVPIC 是完整 URL 优先
    pic = raw.get('hts_MVPIC') or raw.get('web_albumpic_short') or raw.get('albumpic') or raw.get('pic') or raw.get('picUrl') or ''
    if isinstance(pic, str) and '{size}' in pic:
        pic = pic.replace('{size}', '300')
    # 短路径补全：web_albumpic_short 是 '120/s4s48/22/2558779422.jpg'，需要补全
    elif isinstance(pic, str) and pic and not pic.startswith('http'):
        pic = f'https://img4.kuwo.cn/wmvpic/{pic}'

    # 音质：N_MINFO（包含 zply/ff/zp 高码率）优先，否则用 MINFO
    minfo_str = raw.get('N_MINFO') or raw.get('MINFO') or ''
    quality_map = _parse_kuwo_minfo(minfo_str)

    # 付费：PAY 是 32 位二进制标志 (1=online, 2=download, 4=ring, ...)
    # 简化：fpay/tpay/opay 任一非 0 表示需要付费
    fpay = int(raw.get('fpay') or 0)
    tpay = int(raw.get('tpay') or 0)
    opay = int(raw.get('opay') or 0)
    payInfo = raw.get('payInfo') if isinstance(raw.get('payInfo'), dict) else {}
    fee_song = int(payInfo.get('feeType', {}).get('song', 0)) if isinstance(payInfo.get('feeType'), dict) else 0
    pay = bool(fpay or tpay or opay or fee_song)
    fee = 1 if pay else 0

    return {
        'id': str(rid),
        'name': raw.get('SONGNAME') or raw.get('NAME') or raw.get('name') or raw.get('songName') or raw.get('title') or '',
        'artists': raw.get('ARTIST') or raw.get('artists') or raw.get('AARTIST') or raw.get('artist') or raw.get('singer') or '',
        'album': raw.get('ALBUM') or raw.get('album') or '',
        'picUrl': pic,
        'duration': dur,
        'pay': pay,
        'fee': fee,
        'qualityMap': quality_map,
        'bestQuality': _best_quality(quality_map),
    }


# 酷我 level 编码 → 前端 quality + 是否更高优先级
_KUWO_LEVEL_QUALITY = {
    'zply':  ('jymaster', 50),   # 臻品母带 - 最高
    'zp':    ('hires',    40),   # 臻品音质 24bit
    'ff':    ('lossless', 30),   # FLAC 无损
    'p':     ('exhigh',   20),   # 320kbps
    'h':     ('standard', 10),   # 128kbps
    's':     ('standard', 5),    # aac 48k
    'l':     ('standard', 1),    # low
}


def _parse_size_to_bytes(size_str: str) -> int:
    """解析 '51.58Mb' / '5.23Mb' / '1024kb' 字符串为字节数"""
    if not size_str:
        return 0
    s = size_str.strip().lower()
    try:
        if s.endswith('mb'):
            return int(float(s[:-2]) * 1024 * 1024)
        if s.endswith('kb'):
            return int(float(s[:-2]) * 1024)
        if s.endswith('gb'):
            return int(float(s[:-2]) * 1024 * 1024 * 1024)
        return int(float(s))
    except (TypeError, ValueError):
        return 0


def _parse_kuwo_minfo(minfo_str: str) -> dict:
    """解析酷我 N_MINFO/MINFO 字符串为 qualityMap

    格式："level:ff,bitrate:2000,format:flac,size:51.58Mb;
            level:p,bitrate:320,format:mp3,size:10.03Mb;..."

    同一 quality 可能有多个（不同 format），保留 bitrate 最高的。
    """
    if not minfo_str or not isinstance(minfo_str, str):
        return {}
    qmap = {}
    for item in minfo_str.split(';'):
        item = item.strip()
        if not item or item.endswith('Mb') is False and 'bitrate' not in item:
            continue
        parts = {}
        for kv in item.split(','):
            if ':' in kv:
                k, v = kv.split(':', 1)
                parts[k.strip()] = v.strip()
        level = parts.get('level', '').lower()
        if not level:
            continue
        quality_key, _priority = _KUWO_LEVEL_QUALITY.get(level, ('', 0))
        if not quality_key:
            continue
        try:
            bitrate = int(parts.get('bitrate') or 0)
        except (TypeError, ValueError):
            bitrate = 0
        size = _parse_size_to_bytes(parts.get('size') or '')
        # 同 quality 保留 bitrate 最高的
        existing = qmap.get(quality_key)
        if existing and existing.get('br', 0) >= bitrate * 1000:
            continue
        qmap[quality_key] = {
            'br': bitrate * 1000,  # kbps → bps
            'size': size,
            'format': parts.get('format', ''),
        }
    return qmap


# ==================== 歌单解析 ====================
# 5 个歌单提取器（extract_kuwo_playlist / extract_netease_playlist /
# extract_qq_playlist / extract_kugou_playlist / extract_gdstudio_playlist）
# 已迁移到 sources/_playlist_extractors.py，避免循环 import。
