"""QQ 音乐 ApiSource 定义

QQ 官方 API 鉴权复杂（sign/cookie），主要依赖第三方解析 API。
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import (
    extract_first_url,
    extract_text_url,
)


QQ_COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Referer': 'https://y.qq.com/',
    'Origin': 'https://y.qq.com',
}


# ==================== 搜索源 ====================

QQ_SEARCH_SOURCES = [
    # 1. xunhuisi（实测可用，参数名 name）
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
]


# ==================== 下载 URL 源 ====================

QQ_PARSE_URL_SOURCES = [
    # 1. xunhuisi - 解析 mid（实测可用）
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
]


# ==================== 歌曲元信息源 ====================

QQ_PARSE_INFO_SOURCES = [
    # 1. xunhuisi 返回的 title/singer/cover 可作为元信息
    ApiSource(
        name='xunhuisi_info',
        platform='qq',
        priority=0,
        description='xunhuisi (mid 解析，title/singer/cover)',
        can_parse_info=True,
        parse_info_url='https://api.xunhuisi.store/API/QQMusic/Song.php?mid={song_id}&type=json',
        extract_info=lambda d: d if isinstance(d, dict) and d.get('code') == 200 else {},
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
]
