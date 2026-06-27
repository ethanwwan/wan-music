"""波点音乐 ApiSource 定义

波点底层是酷我，需要：
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
    # 2. 酷我官方 convert_url_with_sign
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
    # 3. cenguigui (kw) - 不稳定
    ApiSource(
        name='cenguigui_kw',
        platform='bodian',
        priority=20,
        description='cenguigui (kw) - 不稳定',
        enabled=False,  # 实测超时
        can_parse_url=True,
        parse_url_url='https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json',
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
        enabled=False,  # 不稳定
        can_parse_info=True,
        parse_info_url='https://kw-api.cenguigui.cn/?id={rid}&type=song&level=lossless&format=json',
        extract_info=lambda d: d if isinstance(d, dict) else {},
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
        parse_lyric_url='http://mlyric.kuwo.cn/mobi.s?f=bodian&q={rid}',
        extract_lyric=lambda d: d.get('data', {}).get('lrclist', '') if isinstance(d, dict) else '',
        headers=BODIAN_COMMON_HEADERS,
        timeout=10,
    ),
]
