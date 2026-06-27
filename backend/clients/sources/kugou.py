"""酷狗音乐 ApiSource 定义

酷狗 file_hash 模式，第三方解析 API 较少。
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import extract_first_url


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
]


# ==================== 下载 URL 源 ====================

KUGOU_PARSE_URL_SOURCES = [
    # 1. 酷狗官方 playInfo
    ApiSource(
        name='kugou_official_url',
        platform='kugou',
        priority=0,
        description='酷狗官方 playInfo (需先获取 hash key)',
        enabled=False,  # 需要先解析 hash key 才能用
        can_parse_url=True,
        parse_url_url='https://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={hash}',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. cocodownloader (musicdl 验证可用)
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
]
