"""波点音乐 ApiSource 定义

所有数据来源：musicdl bodian.py + kuwo.py（共用源） + 实测

波点底层是酷我（rid 模式），需要：
  - 特殊 headers（含 user-agent 'Dart/3.3'、devid、qimei36）
  - 动态签名 sign 参数（prepare_request 实现）
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import extract_first_url
from ..fallback.bodian_stateful import (
    prepare_bodian_search,
    prepare_bodian_audio_url,
    prepare_kuwo_official,
)


BODIAN_COMMON_HEADERS = {
    'User-Agent': 'Dart/3.3 (dart:io)',
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip',
    'Api-Ver': 'application/json',
    'Channel': 'W1',
    'Plat': 'win',
    'Ver': '1.1.5',
    'Svrver': '13',
    'Brand': 'Windows 11',
    'Net': 'wifi',
    'Content-Type': 'application/json',
}


# ==================== 搜索源 ====================

BODIAN_SEARCH_SOURCES = [
    # 1. 波点官方 search/music/list（带签名）
    ApiSource(
        name='bodian_official_search',
        platform='bodian',
        priority=0,
        description='波点官方 search/music/list (devid + sign)',
        can_search=True,
        search_url='https://bd-api.kuwo.cn/api/search/music/list?pn=0&rn={limit}&keyword={keyword_encoded}&correct=1',
        extract_search=lambda d: d.get('data', {}).get('resultList', []) if isinstance(d, dict) else [],
        headers=BODIAN_COMMON_HEADERS,
        timeout=10,
        prepare_request=prepare_bodian_search,
    ),
    # 2. 酷我官方 searchMusicBykeyWord (musicdl 列表)
    ApiSource(
        name='kuwo_official_search',
        platform='bodian',
        priority=10,
        description='酷我官方 searchMusicBykeyWord (musicdl 列表)',
        can_search=True,
        search_url='http://www.kuwo.cn/search/searchMusicBykeyWord?vipver=1&client=kt&ft=music&cluster=0&strategy=2012&encoding=utf8&rformat=json&mobi=1&issubtitle=1&show_copyright_off=1&pn=0&rn={limit}&all={keyword_encoded}',
        extract_search=lambda d: d.get('abslist', []) if isinstance(d, dict) else [],
        headers=BODIAN_COMMON_HEADERS,
        timeout=10,
    ),
    # 3. gdstudio 跨平台 search
    ApiSource(
        name='gdstudio_search',
        platform='bodian',
        priority=20,
        description='gdstudio (跨平台源，bodian 复用 kuwo)',
        can_search=True,
        search_url='https://music-api.gdstudio.xyz/api.php?types=search&source=kuwo&name={keyword_encoded}&count={limit}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 下载 URL 源 ====================

BODIAN_PARSE_URL_SOURCES = [
    # 1. 波点官方 audioUrl（带签名）
    ApiSource(
        name='bodian_official_url',
        platform='bodian',
        priority=0,
        description='波点官方 audioUrl (devid + sign)',
        can_parse_url=True,
        parse_url_url='https://bd-api.kuwo.cn/api/play/music/v2/audioUrl?format=flac&br=2000kflac&rid={rid}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('audioHttpsUrl')
            or (d.get('data', {}) if isinstance(d, dict) else {}).get('audioUrl')
            or ''
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=10,
        prepare_request=prepare_bodian_audio_url,
    ),
    # 2. 酷我官方 convert_url_with_sign (musicdl tianbao 同源)
    ApiSource(
        name='kuwo_official_url',
        platform='bodian',
        priority=10,
        description='酷我官方 convert_url_with_sign (devid)',
        can_parse_url=True,
        parse_url_url='https://mobi.kuwo.cn/mobi.s?type=convert_url_with_sign&br=2000kflac&rid={rid}',
        extract_url=extract_first_url,
        headers=BODIAN_COMMON_HEADERS,
        timeout=10,
        prepare_request=prepare_kuwo_official,
    ),
    # 3. tianbao (musicdl 列表, 旧版酷我客户端的接口)
    ApiSource(
        name='tianbao_url',
        platform='bodian',
        priority=15,
        description='tianbao (musicdl bodian 列表，kwplayerhd 客户端)',
        can_parse_url=True,
        parse_url_url='https://mobi.kuwo.cn/mobi.s?f=web&user={__random__}&source=kwplayerhd_ar_4.3.0.8_tianbao_T1A_qirui.apk&type=convert_url_with_sign&br=2000kflac&rid={rid}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers={
            'User-Agent': 'Dart/2.19 (dart:io)',
            'plat': 'ar',
            'channel': 'aliopen',
        },
        timeout=15,
    ),
    # 4. cenguigui (kw) - 不稳定
    ApiSource(
        name='cenguigui_kw',
        platform='bodian',
        priority=20,
        description='cenguigui (kw) - 不稳定',
        enabled=False,  # 实测超时
        can_parse_url=True,
        parse_url_url='https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 5. ccwu (musicdl 列表) - 高码率 jymaster
    ApiSource(
        name='ccwu_url',
        platform='bodian',
        priority=25,
        description='ccwu (musicdl 列表，jymaster)',
        can_parse_url=True,
        parse_url_url='http://kw.006lp.ccwu.cc:7119/api/song?id={rid}&level=jymaster&stream=1',
        extract_url=extract_first_url,  # ccwu 返回纯文本 URL（302 跳转）
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 6. ceseet (musicdl 列表) - lx-music
    ApiSource(
        name='ceseet_url',
        platform='bodian',
        priority=30,
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
    ),
    # 7. yyy001 (musicdl 列表) - 需 ckey
    ApiSource(
        name='yyy001_url',
        platform='bodian',
        priority=35,
        description='yyy001 (musicdl 列表，需 ckey 解密)',
        enabled=False,  # 需 base64 解密 ckey
        can_parse_url=True,
        parse_url_url='https://apione.apibyte.cn/kwmusic?key={ckey}&action=music_url&music_id={rid}&quality={quality}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 8. guyuei (musicdl 列表) - 需解密 final URL
    ApiSource(
        name='guyuei_url',
        platform='bodian',
        priority=40,
        description='guyuei (musicdl 列表，需解密 final URL)',
        enabled=False,  # 需 RC4/XOR 解密
        can_parse_url=True,
        parse_url_url='https://www.guyuei.com/music/kw.php?url=https://www.kuwo.cn/play_detail/{rid}&yinzhi=hns',
        extract_url=extract_first_url,
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 9. lxmusic (musicdl 列表)
    ApiSource(
        name='lxmusic_url',
        platform='bodian',
        priority=45,
        description='lxmusic (musicdl 列表，lxmusicapi.onrender.com)',
        can_parse_url=True,
        parse_url_url='https://lxmusicapi.onrender.com/url/kw/{rid}/flac',
        extract_url=extract_first_url,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'lx-music-request/2.6.0',
            'X-Request-Key': 'share-v3',
        },
        timeout=20,  # onrender.com 冷启动慢
    ),
    # 10. nxinxz (musicdl 列表) - 西柚
    ApiSource(
        name='nxinxz_url',
        platform='bodian',
        priority=50,
        description='nxinxz (musicdl 列表，西柚)',
        can_parse_url=True,
        parse_url_url='http://music.nxinxz.com/kw.php?id={rid}&level={quality}&type=json',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 11. haitanw (musicdl 列表)
    ApiSource(
        name='haitanw_url',
        platform='bodian',
        priority=55,
        description='haitanw (musicdl 列表，kw.php)',
        can_parse_url=True,
        parse_url_url='https://musicapi.haitangw.net/music/kw.php?id={rid}&level={quality}&type=json',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d, dict) else ''
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 12. liuyunidc (musicdl 列表) - 需 RC4 加密
    ApiSource(
        name='liuyunidc_url',
        platform='bodian',
        priority=60,
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
    ),
    # 13. gdstudio (跨平台)
    ApiSource(
        name='gdstudio_url',
        platform='bodian',
        priority=65,
        description='gdstudio URL (跨平台源，bodian 复用 kuwo)',
        can_parse_url=True,
        parse_url_url='https://music-api.gdstudio.xyz/api.php?types=url&id={rid}&source=kuwo&br={__br__}',
        extract_url=extract_first_url,
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌曲元信息源 ====================

BODIAN_PARSE_INFO_SOURCES = [
    # 1. 波点官方搜索结果中已含元信息
    # 真正的 info API 是 /api/search/music/list，但已用于搜索
    # 这里暂时依赖第三方（cenguigui）
    ApiSource(
        name='cenguigui_kw_info',
        platform='bodian',
        priority=0,
        description='cenguigui (kw) 包含完整元信息',
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
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 2. 酷我官方 m.kuwo.cn newh5 (musicdl 列表)
    ApiSource(
        name='kuwo_official_info',
        platform='bodian',
        priority=10,
        description='酷我官方 m.kuwo.cn newh5 singles (musicdl 列表)',
        can_parse_info=True,
        parse_info_url='https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={rid}',
        extract_info=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('songinfo', {})
            if isinstance(d, dict) else {}
        ),
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Referer': 'https://m.kuwo.cn/yinyue/{rid}',
            'Accept': 'application/json, text/plain, */*',
        },
        timeout=10,
    ),
    # 3. 酷我 play_detail HTML fallback (musicdl 列表)
    ApiSource(
        name='kuwo_play_detail_info',
        platform='bodian',
        priority=20,
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
    # 4. haitanw (musicdl 列表)
    ApiSource(
        name='haitanw_info',
        platform='bodian',
        priority=30,
        description='haitanw info (musicdl 列表)',
        can_parse_info=True,
        parse_info_url='https://musicapi.haitangw.net/music/kw.php?id={rid}&level=lossless&type=json',
        extract_info=lambda d: (
            {'id': str(d.get('data', {}).get('rid', '')) if isinstance(d, dict) else '',
             'name': (d.get('data', {}) if isinstance(d, dict) else {}).get('name', ''),
             'artists': (d.get('data', {}) if isinstance(d, dict) else {}).get('artist', ''),
             'album': (d.get('data', {}) if isinstance(d, dict) else {}).get('album', ''),
             'picUrl': (d.get('data', {}) if isinstance(d, dict) else {}).get('pic', ''),
             'duration': (d.get('data', {}) if isinstance(d, dict) else {}).get('duration', 0)}
            if isinstance(d, dict) and (d.get('data', {}) or {}).get('name') else {}
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 5. gdstudio info (跨平台)
    ApiSource(
        name='gdstudio_info',
        platform='bodian',
        priority=40,
        description='gdstudio info (跨平台源，bodian 复用 kuwo)',
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
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌词源 ====================

BODIAN_PARSE_LYRIC_SOURCES = [
    # 1. 酷我官方 mobi 歌词
    ApiSource(
        name='kuwo_official_lyric',
        platform='bodian',
        priority=0,
        description='酷我官方 mobi 歌词',
        can_parse_lyric=True,
        parse_lyric_url='http://mlyric.kuwo.cn/mobi.s?f=bodian&q={__base64_q__}',
        extract_lyric=lambda d: d.get('data', {}).get('lrclist', '') if isinstance(d, dict) else '',
        headers=BODIAN_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. 酷我官方 newlyric (musicdl 列表)
    ApiSource(
        name='kuwo_newlyric',
        platform='bodian',
        priority=10,
        description='酷我官方 newlyric (musicdl 列表)',
        can_parse_lyric=True,
        parse_lyric_url='http://newlyric.kuwo.cn/newlyric.lrc?{__encoded_params__}',
        extract_lyric=lambda d: d if isinstance(d, str) else '',
        headers=BODIAN_COMMON_HEADERS,
        timeout=10,
    ),
    # 3. cenguigui lyric (data.lyric 字段)
    ApiSource(
        name='cenguigui_lyric',
        platform='bodian',
        priority=20,
        description='cenguigui lyric (musicdl 列表，data.lyric 字段)',
        enabled=False,  # cenguigui 不稳定
        can_parse_lyric=True,
        parse_lyric_url='https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json',
        extract_lyric=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('lyric', '')
            if isinstance(d, dict) else ''
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. haitanw lyric (data.lyric 字段)
    ApiSource(
        name='haitanw_lyric',
        platform='bodian',
        priority=30,
        description='haitanw lyric (musicdl 列表，data.lyric 字段)',
        can_parse_lyric=True,
        parse_lyric_url='https://musicapi.haitangw.net/music/kw.php?id={rid}&level=lossless&type=json',
        extract_lyric=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('lyric', '')
            if isinstance(d, dict) else ''
        ),
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
    # 5. gdstudio lyric
    ApiSource(
        name='gdstudio_lyric',
        platform='bodian',
        priority=40,
        description='gdstudio lyric (跨平台源，bodian 复用 kuwo)',
        can_parse_lyric=True,
        parse_lyric_url='https://music-api.gdstudio.xyz/api.php?types=lyric&id={rid}&source=kuwo',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=BODIAN_COMMON_HEADERS,
        timeout=15,
    ),
]
