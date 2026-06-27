"""网易云音乐 ApiSource 定义

所有数据来源：musicdl netease.py + 实测（见 scripts/probe_apis.py）

每个 ApiSource 的能力：
  - can_search: 能否搜索
  - can_parse_url: 能否获取下载 URL
  - can_parse_info: 能否获取歌曲元信息
  - can_parse_lyric: 能否获取歌词

priority 数字越小越优先（0 最高），同 capability 的源按此顺序尝试。
"""
from ..fallback.api_source import ApiSource
from ..fallback.extractors import (
    extract_netease_official_url,
    extract_netease_official_search,
    extract_netease_official_lyric,
    extract_netease_search,
    extract_netease_song_info,
    extract_xuanluoge_url,
    extract_xuanluoge_song_info,
    extract_gdstudio_song_info,
    extract_first_url,
    extract_text_url,
    url_quote,
)


# ==================== 通用 headers ====================

NETEASE_COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Referer': 'https://music.163.com/',
}

NETEASE_EAPI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Referer': 'https://music.163.com/',
    'Content-Type': 'application/x-www-form-urlencoded',
}


# ==================== 搜索源 ====================

NETEASE_SEARCH_SOURCES = [
    # 1. 网易云官方 cloudsearch - 无 cookie 也能用
    ApiSource(
        name='netease_official_search',
        platform='netease',
        priority=0,
        description='网易云官方 cloudsearch（无 cookie 可用）',
        can_search=True,
        search_url='https://music.163.com/api/cloudsearch/pc?s={keyword_encoded}&type=1&limit={limit}&offset=0',
        extract_search=extract_netease_official_search,
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. gdstudio - 跨平台源
    ApiSource(
        name='gdstudio_search',
        platform='netease',
        priority=10,
        description='gdstudio (musicdl 验证)',
        can_search=True,
        search_url='https://music-api.gdstudio.xyz/api.php?types=search&source=netease&name={keyword_encoded}&count={limit}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. xuanluoge search - 已知 search 死链，但保留作为兜底
    ApiSource(
        name='xuanluoge_search',
        platform='netease',
        priority=20,
        description='xuanluoge search（实测 400，保留兜底）',
        enabled=False,  # 已知死链，禁用
        can_search=True,
        search_url='http://118.24.104.108:3456/api.php?miss=search&keyword={keyword_encoded}&limit={limit}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
]


# ==================== 下载 URL 源 ====================

NETEASE_PARSE_URL_SOURCES = [
    # 1. 网易云官方 eapi - 有 cookie 可拿 HiRes
    ApiSource(
        name='netease_official_url',
        platform='netease',
        priority=0,
        description='网易云官方 player/url（需 cookie 才能拿付费资源）',
        can_parse_url=True,
        parse_url_url='https://interface3.music.163.com/eapi/song/enhance/player/url/v1?',
        method='POST',
        post_data={'ids': '[{song_id}]', 'br': '{__br__}', 'e_r': True},
        extract_url=extract_netease_official_url,
        headers=NETEASE_EAPI_HEADERS,
        timeout=10,
        needs_cookie=True,
        cookie_file='netease_cookie.txt',
    ),
    # 2. cenguigui - musicdl 验证可用
    ApiSource(
        name='cenguigui',
        platform='netease',
        priority=10,
        description='cenguigui (musicdl 验证可用)',
        can_parse_url=True,
        parse_url_url='https://api-v2.cenguigui.cn/api/netease/music_v1.php?id={song_id}&type=json&level={quality}',
        extract_url=lambda d: d.get('data', {}).get('url', '') if isinstance(d, dict) else '',
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
    # 3. xuanluoge parse
    ApiSource(
        name='xuanluoge_url',
        platform='netease',
        priority=20,
        description='xuanluoge parse（实测可用，search 已死）',
        can_parse_url=True,
        parse_url_url='http://118.24.104.108:3456/api.php?miss=getMusicUrl&id={song_id}&level={quality}',
        extract_url=extract_xuanluoge_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
    # 4. bileizhen
    ApiSource(
        name='bileizhen',
        platform='netease',
        priority=30,
        description='bileizhen (musicdl 验证)',
        can_parse_url=True,
        parse_url_url='https://api.bileizhen.top/api/netease?id={song_id}&level={quality}',
        extract_url=lambda d: d.get('data', {}).get('url', '') if isinstance(d, dict) else '',
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
    # 5. gdstudio
    ApiSource(
        name='gdstudio_url',
        platform='netease',
        priority=40,
        description='gdstudio (musicdl 验证)',
        can_parse_url=True,
        parse_url_url='https://music-api.gdstudio.xyz/api.php?types=url&id={song_id}&source=netease&br={__br__}',
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 6. cunyu
    ApiSource(
        name='cunyu',
        platform='netease',
        priority=50,
        description='cunyu (musicdl 验证)',
        can_parse_url=True,
        parse_url_url='https://www.cunyuapi.top/163music_play?id={song_id}&quality={quality}',
        extract_url=lambda d: d.get('song_file_url', '') if isinstance(d, dict) else '',
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 7. rxtool
    ApiSource(
        name='rxtool',
        platform='netease',
        priority=60,
        description='rxtool (musicdl 验证)',
        can_parse_url=True,
        parse_url_url='https://api.rxtool.top/api/meteasecloudmusic.php?id={song_id}&level=hires',
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 8. cocodownloader
    ApiSource(
        name='cocodownloader',
        platform='netease',
        priority=70,
        description='cocodownloader (musicdl 验证)',
        can_parse_url=True,
        parse_url_url='https://cocodownloader.markqq.com/api/url?id={song_id}&provider=netease&quality=jymaster',
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 9. vincentzyu233
    ApiSource(
        name='vincentzyu233',
        platform='netease',
        priority=80,
        description='vincentzyu233 (musicdl 验证)',
        can_parse_url=True,
        parse_url_url='http://xwl.vincentzyu233.cn:51217/v2/music/netease?id={song_id}&quality=9',
        extract_url=lambda d: d.get('data', {}).get('url', '') if isinstance(d, dict) else '',
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 10. rrvenn (POST)
    ApiSource(
        name='rrvenn',
        platform='netease',
        priority=90,
        description='rrvenn (musicdl 列表)',
        can_parse_url=True,
        method='POST',
        parse_url_url='https://music.rrvenn.cn/Song_V1',
        post_data={'url': '{song_id}', 'level': '{quality}', 'type': 'json'},
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 11. kangqiovo (POST)
    ApiSource(
        name='kangqiovo',
        platform='netease',
        priority=100,
        description='kangqiovo (musicdl 列表)',
        can_parse_url=True,
        method='POST',
        parse_url_url='https://ncm.kangqiovo.com/Song_V1',
        post_data={'url': '{song_id}', 'level': '{quality}', 'type': 'json'},
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 12. yutangxiaowu
    ApiSource(
        name='yutangxiaowu',
        platform='netease',
        priority=110,
        description='yutangxiaowu (musicdl 列表)',
        can_parse_url=True,
        parse_url_url='https://yutangxiaowu.cn:4000/Song_V1?url={song_id}&level={quality}&type=json',
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 13. qjqq (POST)
    ApiSource(
        name='qjqq',
        platform='netease',
        priority=120,
        description='qjqq (musicdl 列表)',
        can_parse_url=True,
        method='POST',
        parse_url_url='https://metings.qjqq.cn/Song_V1',
        post_data={'url': '{song_id}', 'level': '{quality}', 'type': 'json'},
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 14. bugpk (返回 redirect URL 到 music.163.com)
    ApiSource(
        name='bugpk',
        platform='netease',
        priority=130,
        description='bugpk (musicdl 列表，返回 redirect 链接)',
        can_parse_url=True,
        parse_url_url='https://api.bugpk.com/api/163_music?ids={song_id}&level={quality}&type=json',
        extract_url=extract_text_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 15. byfuns (返回纯文本 URL)
    ApiSource(
        name='byfuns',
        platform='netease',
        priority=140,
        description='byfuns (musicdl 列表，纯文本 URL)',
        can_parse_url=True,
        parse_url_url='https://api.byfuns.top/1/?id={song_id}&level=hires',
        extract_url=extract_text_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 16. haitanw parse - 实际不返回 url，保留占位
    ApiSource(
        name='haitanw_url',
        platform='netease',
        priority=150,
        description='haitanw parse（实测 data 无 url）',
        enabled=False,  # 不返回 url，禁用
        can_parse_url=True,
        parse_url_url='https://musicapi.haitangw.net/music/wy.php?id={song_id}&level={quality}&type=json',
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
    # 17. meting (injatow) - 已知死
    ApiSource(
        name='meting',
        platform='netease',
        priority=200,
        description='meting/injatow（已知死链）',
        enabled=False,  # 已知死
        can_parse_url=True,
        parse_url_url='https://api.injahow.cn/meting/api?server=netease&type=url&id={song_id}&br={quality}',
        extract_url=extract_first_url,
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
]


# ==================== 歌曲元信息源 ====================

NETEASE_PARSE_INFO_SOURCES = [
    # 1. 网易云官方 /api/song/detail
    ApiSource(
        name='netease_official_info',
        platform='netease',
        priority=0,
        description='网易云官方 song/detail（无 cookie 也能用）',
        can_parse_info=True,
        parse_info_url='https://music.163.com/api/song/detail?ids=[{song_id}]',
        extract_info=extract_netease_song_info,
        headers=NETEASE_COMMON_HEADERS,
        timeout=20,  # 国内访问偶尔慢
    ),
    # 2. xuanluoge info - 实测 404
    ApiSource(
        name='xuanluoge_info',
        platform='netease',
        priority=10,
        description='xuanluoge getMusicInfo (实测 404)',
        enabled=False,  # 死链
        can_parse_info=True,
        parse_info_url='http://118.24.104.108:3456/api.php?miss=getMusicInfo&id={song_id}',
        extract_info=extract_xuanluoge_song_info,
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
    # 3. gdstudio info - 实测 types=info 不支持，禁用
    ApiSource(
        name='gdstudio_info',
        platform='netease',
        priority=20,
        description='gdstudio info (实测 types=info 不支持)',
        enabled=False,  # API 不支持 types=info
        can_parse_info=True,
        parse_info_url='https://music-api.gdstudio.xyz/api.php?types=info&id={song_id}&source=netease',
        extract_info=extract_gdstudio_song_info,
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. haitanw info - 返回字段多为 null，只能拿到 rid
    ApiSource(
        name='haitanw_info',
        platform='netease',
        priority=30,
        description='haitanw info (实测大部分字段为 null)',
        enabled=False,  # 元信息全 null，没用
        can_parse_info=True,
        parse_info_url='https://musicapi.haitangw.net/music/wy.php?id={song_id}&type=json',
        extract_info=lambda d: {
            'id': (d.get('data', {}) or {}).get('rid', ''),
            'name': '',
            'artists': '',
            'album': '',
            'picUrl': '',
            'duration': 0,
        } if isinstance(d, dict) else {},
        headers=NETEASE_COMMON_HEADERS,
        timeout=10,
    ),
]


# ==================== 歌词源 ====================

NETEASE_PARSE_LYRIC_SOURCES = [
    # 1. 网易云官方 lyric
    ApiSource(
        name='netease_official_lyric',
        platform='netease',
        priority=0,
        description='网易云官方 lyric',
        can_parse_lyric=True,
        parse_lyric_url='https://interface3.music.163.com/api/song/lyric?id={song_id}&lv=1&kv=1&tv=-1',
        extract_lyric=extract_netease_official_lyric,
        headers=NETEASE_EAPI_HEADERS,
        timeout=10,
    ),
    # 2. gdstudio lyric
    ApiSource(
        name='gdstudio_lyric',
        platform='netease',
        priority=10,
        description='gdstudio lyric',
        can_parse_lyric=True,
        parse_lyric_url='https://music-api.gdstudio.xyz/api.php?types=lyric&id={song_id}&source=netease',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=NETEASE_COMMON_HEADERS,
        timeout=15,
    ),
]
