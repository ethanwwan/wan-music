"""酷我音乐 ApiSource 定义

所有数据来源：musicdl kuwo.py + 实测

酷我使用 MUSICRID（去掉 MUSIC_ 前缀）作为 song_id。
第三方源质量分级：lossless < exhigh < standard；特殊品质 jymaster 走 jymaster/ff/p/h 标签。
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import (
    extract_first_url,
    extract_text_url,
)
from ._playlist_extractors import (
    extract_kuwo_playlist as _extract_kuwo_playlist,
    extract_gdstudio_playlist as _extract_gdstudio_playlist,
)


KUWO_COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Referer': 'https://www.kuwo.cn/',
}

KUWO_LXMUSIC_HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'lx-music-request/2.6.0',
    'X-Request-Key': 'share-v3',
}


# ==================== 搜索源 ====================

KUWO_SEARCH_SOURCES = [
    # 1. 酷我官方 searchMusicBykeyWord
    ApiSource(
        name='kuwo_official_search',
        platform='kuwo',
        priority=0,
        description='酷我官方 searchMusicBykeyWord (musicdl 列表)',
        can_search=True,
        search_url='http://www.kuwo.cn/search/searchMusicBykeyWord?vipver=1&client=kt&ft=music&cluster=0&strategy=2012&encoding=utf8&rformat=json&mobi=1&issubtitle=1&show_copyright_off=1&pn=0&rn={limit}&all={keyword_encoded}',
        extract_search=lambda d: d.get('abslist', []) if isinstance(d, dict) else [],
        headers=KUWO_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. 酷我移动端 m.kuwo.cn newh5app 搜索（musicdl 列表）
    ApiSource(
        name='kuwo_mobile_search',
        platform='kuwo',
        priority=10,
        description='酷我移动端 m.kuwo.cn newh5app 搜索 (musicdl 列表)',
        can_search=True,
        search_url='https://m.kuwo.cn/newh5app/wapi/api/www/search/searchMusicBykeyWord?key={keyword_encoded}&pn=0&rn={limit}',
        extract_search=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('list', [])
            if isinstance(d, dict) else []
        ),
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.kuwo.cn/',
            'Accept': 'application/json, text/plain, */*',
        },
        timeout=10,
    ),
    # 3. gdstudio 跨平台 search
    ApiSource(
        name='gdstudio_search',
        platform='kuwo',
        priority=20,
        description='gdstudio (跨平台源，kuwo)',
        can_search=True,
        search_url='https://music-api.gdstudio.xyz/api.php?types=search&source=kuwo&name={keyword_encoded}&count={limit}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 下载 URL 源 ====================

KUWO_PARSE_URL_SOURCES = [
    # 1. cgg (cenguigui) - musicdl 验证可用
    # max_quality='lossless'：实测能返 FLAC lossless
    ApiSource(
        name='cgg_url',
        platform='kuwo',
        priority=0,
        description='cenguigui (musicdl 列表，level=lossless)',
        can_parse_url=True,
        parse_url_url='https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',
    ),
    # 2. ccwu (musicdl 列表) - 高码率 jymaster
    # max_quality='jymaster'：level=jymaster
    ApiSource(
        name='ccwu_url',
        platform='kuwo',
        priority=10,
        description='ccwu (musicdl 列表，jymaster 码率)',
        can_parse_url=True,
        parse_url_url='http://kw.006lp.ccwu.cc:7119/api/song?id={rid}&level=jymaster&stream=1',
        extract_url=extract_first_url,
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
        max_quality='jymaster',
    ),
    # 3. liuyunidc (musicdl 列表) - 需 RC4 加密
    # max_quality='hires'：musicdl 备注支持
    ApiSource(
        name='liuyunidc_url',
        platform='kuwo',
        priority=15,
        description='liuyunidc (musicdl 列表，RC4 加密 data 参数)',
        enabled=False,  # 需 RC4 加密
        can_parse_url=True,
        parse_url_url='https://kwdec.liuyunidc.cn/kwurl?data={__rc4_data__}',
        extract_url=extract_first_url,
        headers={
            'Accept': '*/*',
            'Origin': 'https://api.liuyunidc.cn',
            'Referer': 'https://api.liuyunidc.cn/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        },
        timeout=15,
        max_quality='hires',
    ),
    # 4. yyy001 (musicdl 列表) - 需 ckey
    # max_quality='hires'：quality 参数支持
    ApiSource(
        name='yyy001_url',
        platform='kuwo',
        priority=20,
        description='yyy001 (musicdl 列表，需 ckey 解密)',
        enabled=False,  # 需 base64 解密 ckey
        can_parse_url=True,
        parse_url_url='https://apione.apibyte.cn/kwmusic?key={ckey}&action=music_url&music_id={rid}&quality={quality}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',
    ),
    # 5. lxmusic (musicdl 列表)
    # max_quality='lossless'：/flac
    ApiSource(
        name='lxmusic_url',
        platform='kuwo',
        priority=25,
        description='lxmusic (musicdl 列表，lxmusicapi.onrender.com)',
        can_parse_url=True,
        parse_url_url='https://lxmusicapi.onrender.com/url/kw/{rid}/flac',
        extract_url=extract_first_url,
        headers=KUWO_LXMUSIC_HEADERS,
        timeout=20,  # onrender.com 冷启动慢
        max_quality='lossless',
    ),
    # 6. nxinxz (musicdl 列表) - 西柚
    # max_quality='hires'：level 参数支持
    ApiSource(
        name='nxinxz_url',
        platform='kuwo',
        priority=30,
        description='nxinxz (musicdl 列表，西柚)',
        can_parse_url=True,
        parse_url_url='http://music.nxinxz.com/kw.php?id={rid}&level={quality}&type=json',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',
    ),
    # 7. haitanw (musicdl 列表) - 海糖网
    # max_quality='lossless'：level=lossless/exhigh/standard
    ApiSource(
        name='haitanw_url',
        platform='kuwo',
        priority=35,
        description='haitanw (musicdl 列表，kw.php level=lossless/exhigh/standard)',
        can_parse_url=True,
        parse_url_url='https://musicapi.haitangw.net/music/kw.php?id={rid}&level={quality}&type=json',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',
    ),
    # 8. guyuei (musicdl 列表) - 需解密 final URL
    # max_quality='hires'：yinzhi=hns 是高品质
    ApiSource(
        name='guyuei_url',
        platform='kuwo',
        priority=40,
        description='guyuei (musicdl 列表，需 RC4/XOR 解密 final URL)',
        enabled=False,  # 需 RC4/XOR 解密
        can_parse_url=True,
        parse_url_url='https://www.guyuei.com/music/kw.php?url=https://www.kuwo.cn/play_detail/{rid}&yinzhi=hns',
        extract_url=extract_first_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
        },
        timeout=15,
        max_quality='hires',
    ),
    # 9. ceseet (musicdl 列表) - lx-music
    # max_quality='lossless'：/flac
    ApiSource(
        name='ceseet_url',
        platform='kuwo',
        priority=45,
        description='ceseet (musicdl 列表，lx-music-request)',
        can_parse_url=True,
        parse_url_url='https://m-api.ceseet.me/url/kw/{rid}/flac',
        extract_url=lambda d: d.get('data', '') if isinstance(d, dict) else '',
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'lx-music-request/2.6.0',
            'X-Request-Key': '',
        },
        timeout=15,
        max_quality='lossless',
    ),
    # 10. 酷我官方 mobi.kuwo.cn convert_url2 (musicdl 列表) - 需 encryptquery
    # max_quality='hires'：官方 API
    ApiSource(
        name='kuwo_official_mobi',
        platform='kuwo',
        priority=50,
        description='酷我官方 mobi.kuwo.cn convert_url2 (musicdl 列表，需 encryptquery)',
        enabled=False,  # 需 encryptquery 复杂签名
        can_parse_url=True,
        parse_url_url='http://mobi.kuwo.cn/mobi.s?f=kuwo&q={__encryptquery__}',
        extract_url=extract_first_url,
        headers={
            'user-agent': 'okhttp/3.10.0',
        },
        timeout=10,
        max_quality='hires',
    ),
    # 11. 酷我官方 convert_url_with_sign (musicdl 列表) - 不需要 user 参数
    # max_quality='hires'：br=2000kflac 是 FLAC
    ApiSource(
        name='kuwo_official_convert_url_with_sign',
        platform='kuwo',
        priority=55,
        description='酷我官方 convert_url_with_sign (musicdl 列表)',
        can_parse_url=True,
        parse_url_url='https://mobi.kuwo.cn/mobi.s?type=convert_url_with_sign&br=2000kflac&rid={rid}',
        extract_url=extract_first_url,
        headers={
            'User-Agent': 'Dart/2.19 (dart:io)',
            'plat': 'ar',
            'channel': 'aliopen',
        },
        timeout=15,
        max_quality='hires',
    ),
    # 12. gdstudio 跨平台 URL
    # max_quality='lossless'：gdstudio br 最高 lossless
    ApiSource(
        name='gdstudio_url',
        platform='kuwo',
        priority=60,
        description='gdstudio URL (跨平台源，kuwo)',
        can_parse_url=True,
        parse_url_url='https://music-api.gdstudio.xyz/api.php?types=url&id={rid}&source=kuwo&br={__br__}',
        extract_url=extract_first_url,
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',
    ),
]


# ==================== 歌曲元信息源 ====================

KUWO_PARSE_INFO_SOURCES = [
    # 1. 酷我官方 m.kuwo.cn newh5 singles (musicdl 列表)
    ApiSource(
        name='kuwo_official_info',
        platform='kuwo',
        priority=0,
        description='酷我官方 m.kuwo.cn newh5 singles (musicdl 列表)',
        can_parse_info=True,
        parse_info_url='https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}',
        # 酷我官方响应：{"data": {"songinfo": {"id", "songName", "artist", "album", "pic"}}}
        # 注意：mobi.kuwo.cn 偶尔返回 {"data": null, "msg": "..."}，需要 d.get('data') or {} 兜底
        extract_info=lambda d: {
            'id': ((d.get('data') or {}).get('songinfo') or {}).get('id', 0),
            'name': ((d.get('data') or {}).get('songinfo') or {}).get('songName', ''),
            'artists': ((d.get('data') or {}).get('songinfo') or {}).get('artist', ''),
            'album': ((d.get('data') or {}).get('songinfo') or {}).get('album', ''),
            'picUrl': ((d.get('data') or {}).get('songinfo') or {}).get('pic', ''),
        } if isinstance(d, dict) else {},
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.kuwo.cn/yinyue/{rid}',
            'Accept': 'application/json, text/plain, */*',
        },
        timeout=10,
    ),
    # 2. 酷我 play_detail HTML 解析 (musicdl 列表)
    ApiSource(
        name='kuwo_play_detail_info',
        platform='kuwo',
        priority=10,
        description='酷我 play_detail HTML 解析 (musicdl 列表)',
        enabled=False,  # 复杂 HTML 解析
        can_parse_info=True,
        parse_info_url='https://www.kuwo.cn/play_detail/{rid}',
        extract_info=lambda d: (
            d if isinstance(d, dict) else {}
        ),
        headers={
            'Referer': 'https://www.kuwo.cn/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        },
        timeout=10,
    ),
    # 3. cenguigui info (musicdl 列表，包含完整元信息)
    ApiSource(
        name='cgg_info',
        platform='kuwo',
        priority=20,
        description='cenguigui (musicdl 列表，包含完整元信息)',
        can_parse_info=True,
        parse_info_url='https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json',
        extract_info=lambda d: (
            {'id': str((d.get('data', {}) or {}).get('rid', '')) if isinstance(d, dict) else '',
             'name': (d.get('data', {}) or {}).get('name', '') if isinstance(d, dict) else '',
             'artists': (d.get('data', {}) or {}).get('artist', '') if isinstance(d, dict) else '',
             'album': (d.get('data', {}) or {}).get('album', '') if isinstance(d, dict) else '',
             'picUrl': (d.get('data', {}) or {}).get('pic', '') if isinstance(d, dict) else '',
             'duration': (d.get('data', {}) or {}).get('duration', 0) if isinstance(d, dict) else 0}
            if isinstance(d, dict) and (d.get('data', {}) or {}).get('name') else {}
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. haitanw info (musicdl 列表)
    ApiSource(
        name='haitanw_info',
        platform='kuwo',
        priority=30,
        description='haitanw info (musicdl 列表)',
        can_parse_info=True,
        parse_info_url='https://musicapi.haitangw.net/music/kw.php?id={rid}&level=lossless&type=json',
        extract_info=lambda d: (
            {'id': str((d.get('data', {}) or {}).get('rid', '')) if isinstance(d, dict) else '',
             'name': (d.get('data', {}) if isinstance(d, dict) else {}).get('name', ''),
             'artists': (d.get('data', {}) if isinstance(d, dict) else {}).get('artist', ''),
             'album': (d.get('data', {}) if isinstance(d, dict) else {}).get('album', ''),
             'picUrl': (d.get('data', {}) if isinstance(d, dict) else {}).get('pic', ''),
             'duration': (d.get('data', {}) if isinstance(d, dict) else {}).get('duration', 0)}
            if isinstance(d, dict) and (d.get('data', {}) or {}).get('name') else {}
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
    ),
    # 5. gdstudio info (跨平台)
    ApiSource(
        name='gdstudio_info',
        platform='kuwo',
        priority=40,
        description='gdstudio info (跨平台源，kuwo)',
        can_parse_info=True,
        parse_info_url='https://music-api.gdstudio.xyz/api.php?types=info&id={rid}&source=kuwo',
        extract_info=lambda d: (
            {'id': str(d.get('id', '')), 'name': d.get('name', ''),
             'artists': '/'.join(d.get('artist', []) if isinstance(d.get('artist'), list) else [str(d.get('artist', '') or '')]),
             'album': d.get('album', ''),
             'picUrl': d.get('pic', ''),
             'duration': d.get('duration', 0)}
            if isinstance(d, dict) and d.get('id') else {}
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌词源 ====================

def _extract_kuwo_lyric_from_lrclist(d: dict) -> str:
    """从酷我 m.kuwo.cn/newh5/singles/songinfoandlrc 响应里提取 LRC

    响应: data.lrclist[] = [{"time": "0.0", "lineLyric": "..."}]
    转换: [mm:ss.cc]lineLyric (time 为浮点秒)
    """
    if not isinstance(d, dict):
        return ''
    data = d.get('data') or {}
    if not isinstance(data, dict):
        return ''
    lrclist = data.get('lrclist') or []
    if not lrclist:
        return ''
    lines = []
    for item in lrclist:
        if not isinstance(item, dict):
            continue
        t = item.get('time')
        text = item.get('lineLyric') or ''
        if not text.strip():
            continue
        try:
            secs = float(t)
        except (TypeError, ValueError):
            continue
        m = int(secs) // 60
        s = int(secs) % 60
        # 保留 2 位小数（centiseconds）
        cs = int((secs - int(secs)) * 100)
        lines.append(f'[{m:02d}:{s:02d}.{cs:02d}]{text}')
    return '\n'.join(lines)


KUWO_PARSE_LYRIC_SOURCES = [
    # 0. 酷我官方 m.kuwo.cn 移动端歌词（实测可用，无需 cookie）
    # 参考 https://github.com/guohuiyuan/music-lib/blob/main/kuwo/lyric.go (legacy fallback)
    # 响应 data.lrclist[] = [{"time": "0.0", "lineLyric": "..."}]
    ApiSource(
        name='kuwo_official_lyric',
        platform='kuwo',
        priority=0,
        description='酷我官方 m.kuwo.cn/newh5 lyric (legacy JSON)',
        can_parse_lyric=True,
        parse_lyric_url=(
            'http://m.kuwo.cn/newh5/singles/songinfoandlrc'
            '?musicId={rid}&httpsStatus=1'
        ),
        extract_lyric=_extract_kuwo_lyric_from_lrclist,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) '
                          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 '
                          'Mobile/15E148 Safari/604.1',
            'Referer': 'http://m.kuwo.cn',
        },
        timeout=10,
    ),
    # 1. 酷我官方 newlyric.kuwo.cn (新 API，XOR+base64+zlib 加密)
    #   参考 music-lib kuwo.go fetchNewLyrics
    #   URL: http://newlyric.kuwo.cn/newlyric.lrc?{base64_xor_params}
    #   由于响应是二进制（zlib），chain 框架无法直接处理（r.text UTF-8 解码会乱码），
    #   此处 URL 仅作记录，实际需要 kuwo_client 直接调用 + 解码。
    #   当前已禁用，兜底用 cenguigui/haitanw/gdstudio 三方源。
    ApiSource(
        name='kuwo_newlyric',
        platform='kuwo',
        priority=10,
        description='酷我官方 newlyric (musicdl 列表，需 buildlyricsparams+decodelyrics，已禁用)',
        enabled=False,  # 需要框架支持二进制响应解码
        can_parse_lyric=True,
        parse_lyric_url='http://newlyric.kuwo.cn/newlyric.lrc?{__encoded_params__}',
        extract_lyric=lambda d: d if isinstance(d, str) else '',
        headers=KUWO_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. cenguigui lyric (data.lyric 字段)
    ApiSource(
        name='cgg_lyric',
        platform='kuwo',
        priority=20,
        description='cenguigui lyric (musicdl 列表，data.lyric 字段)',
        can_parse_lyric=True,
        parse_lyric_url='https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json',
        extract_lyric=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('lyric', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. haitanw lyric (data.lyric 字段)
    ApiSource(
        name='haitanw_lyric',
        platform='kuwo',
        priority=30,
        description='haitanw lyric (musicdl 列表，data.lyric 字段)',
        can_parse_lyric=True,
        parse_lyric_url='https://musicapi.haitangw.net/music/kw.php?id={rid}&level=lossless&type=json',
        extract_lyric=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('lyric', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. gdstudio lyric
    ApiSource(
        name='gdstudio_lyric',
        platform='kuwo',
        priority=40,
        description='gdstudio lyric (跨平台源，kuwo)',
        can_parse_lyric=True,
        parse_lyric_url='https://music-api.gdstudio.xyz/api.php?types=lyric&id={rid}&source=kuwo',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=KUWO_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌单解析 ====================

KUWO_PARSE_PLAYLIST_SOURCES = [
    # 1. 酷我官方 playListInfo（需登录态，匿名访问多返回 -1）
    ApiSource(
        name='kuwo_official_playlist',
        platform='kuwo',
        priority=0,
        description='酷我官方 playListInfo（分页：pn=page, rn=100）',
        can_parse_playlist=True,
        parse_playlist_url=(
            'https://m.kuwo.cn/newh5app/wapi/api/www/playlist/playListInfo'
            '?pid={playlist_id}&pn={page}&rn={size}'
        ),
        extract_playlist=_extract_kuwo_playlist,
        headers={
            **KUWO_COMMON_HEADERS,
            'Referer': 'https://m.kuwo.cn/',
        },
        timeout=15,
    ),
    # 2. gdstudio 跨平台歌单（兜底，gdstudio 实际固定返回网易云格式）
    ApiSource(
        name='gdstudio_playlist',
        platform='kuwo',
        priority=20,
        description='gdstudio 跨平台歌单（兜底，gdstudio 实际固定返回网易云格式）',
        can_parse_playlist=True,
        parse_playlist_url='https://music-api.gdstudio.xyz/api.php?types=playlist&id={playlist_id}&source=kuwo',
        extract_playlist=_extract_gdstudio_playlist,
        headers={'User-Agent': 'Mozilla/5.0'},
        timeout=20,
    ),
]
