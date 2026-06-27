"""跨平台可复用的第三方源（如 gdstudio、tunehub）"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import extract_first_url, extract_text_url


COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
}


COMMON_SOURCES = {
    # 通用 gdstudio（支持 netease/qq/kugou/kuwo/bilibili 等）
    'gdstudio': [
        ApiSource(
            name=f'gdstudio_url_{platform}',
            platform=platform,
            priority=5,  # 比官方高
            description=f'gdstudio URL (跨平台源，{platform})',
            can_parse_url=True,
            parse_url_url=f'https://music-api.gdstudio.xyz/api.php?types=url&id={{song_id}}&source={platform}&br={{__br__}}',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ) for platform in ['netease', 'qq', 'kugou']
    ],
    'tunehub': [
        # tunehub 是 musicdl 的另一个跨平台源
        ApiSource(
            name='tunehub_url_netease',
            platform='netease',
            priority=15,
            description='tunehub 解析 (musicdl 列表)',
            enabled=False,  # 需要先验证
            can_parse_url=True,
            parse_url_url='https://api.tunehub.io/api/song/url?id={song_id}&source=netease',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
    ],
}
