"""跨平台可复用的第三方源

所有数据来源：musicdl common.py + 实测

每个 ApiSource 都通过 platform 字段归属一个具体平台。
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import extract_first_url, extract_text_url


COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
}


# gdstudio 跨平台源：支持 netease/qq/kugou/kuwo/bilibili/migu
_GDSTUDIO_PLATFORMS = ['netease', 'qq', 'kugou', 'kuwo']


COMMON_SOURCES = {
    # 通用 gdstudio（支持 netease/qq/kugou/kuwo）
    'gdstudio': [
        # URL 源
        *[
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
            ) for platform in _GDSTUDIO_PLATFORMS
        ],
        # Search 源
        *[
            ApiSource(
                name=f'gdstudio_search_{platform}',
                platform=platform,
                priority=15,
                description=f'gdstudio search (跨平台源，{platform})',
                can_search=True,
                search_url=f'https://music-api.gdstudio.xyz/api.php?types=search&source={platform}&name={{keyword_encoded}}&count={{limit}}',
                extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
                headers=COMMON_HEADERS,
                timeout=15,
            ) for platform in _GDSTUDIO_PLATFORMS
        ],
        # Info 源
        *[
            ApiSource(
                name=f'gdstudio_info_{platform}',
                platform=platform,
                priority=15,
                description=f'gdstudio info (跨平台源，{platform})',
                can_parse_info=True,
                parse_info_url=f'https://music-api.gdstudio.xyz/api.php?types=info&id={{song_id}}&source={platform}',
                extract_info=lambda d: (
                    {'id': str(d.get('id', '')),
                     'name': d.get('name', ''),
                     'artists': '/'.join(d.get('artist', []) if isinstance(d.get('artist'), list) else [str(d.get('artist', '') or '')]),
                     'album': d.get('album', ''),
                     'picUrl': d.get('pic', ''),
                     'duration': d.get('duration', 0)}
                    if isinstance(d, dict) and d.get('id') else {}
                ),
                headers=COMMON_HEADERS,
                timeout=15,
            ) for platform in _GDSTUDIO_PLATFORMS
        ],
        # Lyric 源
        *[
            ApiSource(
                name=f'gdstudio_lyric_{platform}',
                platform=platform,
                priority=15,
                description=f'gdstudio lyric (跨平台源，{platform})',
                can_parse_lyric=True,
                parse_lyric_url=f'https://music-api.gdstudio.xyz/api.php?types=lyric&id={{song_id}}&source={platform}',
                extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
                headers=COMMON_HEADERS,
                timeout=15,
            ) for platform in _GDSTUDIO_PLATFORMS
        ],
    ],
    # tunehub 跨平台源（musicdl 列表）
    'tunehub': [
        # netease
        ApiSource(
            name='tunehub_url_netease',
            platform='netease',
            priority=15,
            description='tunehub 解析 (musicdl 列表)',
            enabled=False,  # 需先验证
            can_parse_url=True,
            parse_url_url='https://api.tunehub.io/api/song/url?id={song_id}&source=netease',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # qq
        ApiSource(
            name='tunehub_url_qq',
            platform='qq',
            priority=15,
            description='tunehub 解析 (musicdl 列表)',
            enabled=False,  # 需先验证
            can_parse_url=True,
            parse_url_url='https://api.tunehub.io/api/song/url?id={song_id}&source=qq',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # kugou
        ApiSource(
            name='tunehub_url_kugou',
            platform='kugou',
            priority=15,
            description='tunehub 解析 (musicdl 列表)',
            enabled=False,  # 需先验证
            can_parse_url=True,
            parse_url_url='https://api.tunehub.io/api/song/url?id={song_id}&source=kugou',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # kuwo
        ApiSource(
            name='tunehub_url_kuwo',
            platform='kuwo',
            priority=15,
            description='tunehub 解析 (musicdl 列表)',
            enabled=False,  # 需先验证
            can_parse_url=True,
            parse_url_url='https://api.tunehub.io/api/song/url?id={song_id}&source=kuwo',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
    ],
    # jbsou 跨平台源（POST musicdl 列表，复杂）
    'jbsou': [
        # netease
        ApiSource(
            name='jbsou_url_netease',
            platform='netease',
            priority=20,
            description='jbsou POST (musicdl 列表，netease)',
            enabled=False,  # 需验证 POST
            can_parse_url=True,
            method='POST',
            parse_url_url='https://www.jbsou.cn/',
            post_data={'input': '{song_id}', 'filter': 'id', 'type': 'netease', 'page': '1'},
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
        ),
        # qq
        ApiSource(
            name='jbsou_url_qq',
            platform='qq',
            priority=20,
            description='jbsou POST (musicdl 列表，qq)',
            enabled=False,  # 需验证 POST
            can_parse_url=True,
            method='POST',
            parse_url_url='https://www.jbsou.cn/',
            post_data={'input': '{song_id}', 'filter': 'id', 'type': 'qq', 'page': '1'},
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
        ),
        # kuwo
        ApiSource(
            name='jbsou_url_kuwo',
            platform='kuwo',
            priority=20,
            description='jbsou POST (musicdl 列表，kuwo)',
            enabled=False,  # 需验证 POST
            can_parse_url=True,
            method='POST',
            parse_url_url='https://www.jbsou.cn/',
            post_data={'input': '{song_id}', 'filter': 'id', 'type': 'kuwo', 'page': '1'},
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
        ),
    ],
    # 317ak 跨平台源（musicdl 列表，需 ckey）
    '317ak': [
        # netease
        ApiSource(
            name='317ak_url_netease',
            platform='netease',
            priority=25,
            description='317ak 解析 (musicdl 列表，需 ckey)',
            enabled=False,  # 需 ckey
            can_parse_url=True,
            parse_url_url='https://api.317ak.cn/api/yinyue/163?ckey={ckey}&i={song_id}&br={quality}&type=json&lrc=1',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # qq
        ApiSource(
            name='317ak_url_qq',
            platform='qq',
            priority=25,
            description='317ak 解析 (musicdl 列表，需 ckey)',
            enabled=False,  # 需 ckey
            can_parse_url=True,
            parse_url_url='https://api.317ak.cn/api/yinyue/qq?ckey={ckey}&i={song_id}&br={quality}&type=json&lrc=1',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # kugou
        ApiSource(
            name='317ak_url_kugou',
            platform='kugou',
            priority=25,
            description='317ak 解析 (musicdl 列表，需 ckey)',
            enabled=False,  # 需 ckey
            can_parse_url=True,
            parse_url_url='https://api.317ak.cn/api/yinyue/kugou?ckey={ckey}&i={song_id}&br={quality}&type=json&lrc=1',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # kuwo
        ApiSource(
            name='317ak_url_kuwo',
            platform='kuwo',
            priority=25,
            description='317ak 解析 (musicdl 列表，需 ckey)',
            enabled=False,  # 需 ckey
            can_parse_url=True,
            parse_url_url='https://api.317ak.cn/api/yinyue/kuwo?ckey={ckey}&i={song_id}&br={quality}&type=json&lrc=1',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
    ],
    # 第三方通用 haitanw（musicdl 列表，kgqq 平台）
    'haitanw_kgqq': [
        # netease
        ApiSource(
            name='haitanw_kgqq_netease',
            platform='netease',
            priority=20,
            description='haitanw kgqq (musicdl 列表，netease)',
            enabled=False,  # musicdl 验证 data 无 url
            can_parse_url=True,
            parse_url_url='https://musicapi.haitangw.net/kgqq/wy.php?type=json&id={song_id}&level={quality}',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # qq
        ApiSource(
            name='haitanw_kgqq_qq',
            platform='qq',
            priority=20,
            description='haitanw kgqq (musicdl 列表，qq)',
            enabled=False,  # musicdl 验证 data 无 url
            can_parse_url=True,
            parse_url_url='https://musicapi.haitangw.net/kgqq/qq.php?type=json&id={song_id}&level={quality}',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
    ],
    # cocodownloader 跨平台源
    'cocodownloader': [
        # netease
        ApiSource(
            name='cocodownloader_netease',
            platform='netease',
            priority=15,
            description='cocodownloader (musicdl 验证，netease)',
            can_parse_url=True,
            parse_url_url='https://cocodownloader.markqq.com/api/url?id={song_id}&provider=netease&quality=jymaster',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # qq
        ApiSource(
            name='cocodownloader_qq',
            platform='qq',
            priority=15,
            description='cocodownloader (musicdl 验证，qq)',
            can_parse_url=True,
            parse_url_url='https://cocodownloader.markqq.com/api/url?id={song_id}&provider=qq&quality=jymaster',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # kugou
        ApiSource(
            name='cocodownloader_kugou',
            platform='kugou',
            priority=15,
            description='cocodownloader (musicdl 验证，kugou)',
            can_parse_url=True,
            parse_url_url='https://cocodownloader.markqq.com/api/url?id={song_id}&provider=kugou',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # kuwo
        ApiSource(
            name='cocodownloader_kuwo',
            platform='kuwo',
            priority=15,
            description='cocodownloader (musicdl 验证，kuwo)',
            can_parse_url=True,
            parse_url_url='https://cocodownloader.markqq.com/api/url?id={song_id}&provider=kuwo',
            extract_url=extract_first_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
    ],
    # lxmusic 跨平台源（musicdl 列表）
    'lxmusic': [
        # netease
        ApiSource(
            name='lxmusic_url_netease',
            platform='netease',
            priority=20,
            description='lxmusic 解析 (musicdl 列表，netease)',
            can_parse_url=True,
            parse_url_url='https://lxmusicapi.onrender.com/url/wy/{song_id}/flac',
            extract_url=extract_first_url,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'lx-music-request/2.6.0',
                'X-Request-Key': 'share-v3',
            },
            timeout=20,
        ),
        # qq
        ApiSource(
            name='lxmusic_url_qq',
            platform='qq',
            priority=20,
            description='lxmusic 解析 (musicdl 列表，qq)',
            can_parse_url=True,
            parse_url_url='https://lxmusicapi.onrender.com/url/tx/{song_id}/flac',
            extract_url=extract_first_url,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'lx-music-request/2.6.0',
                'X-Request-Key': 'share-v3',
            },
            timeout=20,
        ),
        # kuwo
        ApiSource(
            name='lxmusic_url_kuwo',
            platform='kuwo',
            priority=20,
            description='lxmusic 解析 (musicdl 列表，kuwo)',
            can_parse_url=True,
            parse_url_url='https://lxmusicapi.onrender.com/url/kw/{song_id}/flac',
            extract_url=extract_first_url,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'lx-music-request/2.6.0',
                'X-Request-Key': 'share-v3',
            },
            timeout=20,
        ),
    ],
    # meting 跨平台源（musicdl injatow 版，nanorocky 备份）
    'meting': [
        # netease
        ApiSource(
            name='meting_netease',
            platform='netease',
            priority=30,
            description='meting/nanorocky (musicdl injatow 替代)',
            can_parse_url=True,
            parse_url_url='https://metingapi.nanorocky.top/?server=netease&type=url&id={song_id}&br=2000',
            extract_url=extract_text_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
        # qq
        ApiSource(
            name='meting_qq',
            platform='qq',
            priority=30,
            description='meting/nanorocky (musicdl injatow 替代)',
            enabled=False,  # nanorocky qq 接口可能不可用
            can_parse_url=True,
            parse_url_url='https://metingapi.nanorocky.top/?server=tencent&type=url&id={song_id}&br=2000',
            extract_url=extract_text_url,
            headers=COMMON_HEADERS,
            timeout=15,
        ),
    ],
}
