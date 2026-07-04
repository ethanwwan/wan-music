"""酷狗音乐 ApiSource 定义

所有数据来源：musicdl kugou.py + 实测（见 scripts/probe_apis.py）

酷狗 file_hash 模式，第三方解析 API 较少。
"""
import base64
import random
from ..fallback.api_source import ApiSource
from ..fallback.extractors import (
    extract_first_url,
    extract_text_url,
)
from ._playlist_extractors import (
    extract_kugou_playlist as _extract_kugou_playlist,
    extract_netease_playlist as _extract_netease_playlist,
)


KUGOU_COMMON_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Referer': 'https://www.kugou.com/',
}


# 移动端 UA（mobilecdn.kugou.com 官方 mobile API 需要 iPhone UA，参考 music-lib kugou.go）
KUGOU_MOBILE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 '
                  'Mobile/15E148 Safari/604.1',
    'Referer': 'http://m.kugou.com',
}


# ==================== musicdl 兼容的解密函数 ====================

# 317ak 源的 ckey 池（musicdl 提供）+ 解密函数（与 yyy001 同模式）
# 解密逻辑：跳过前 14 字符 "charlespikachu"，剩余 base64 解码得真实 key
_317AK_REQUEST_KEYS = [
    'charlespikachuUE9WTUhLSklYOEE3SUdIMkZNMVA=',
    'charlespikachuWE1VS0lBSjNQOExQWDNQOTcxS1U=',
    'charlespikachuN0tUSTUyVDdWTE9EUjZTVDM3UFQ=',
]


def _317ak_prepare_request(url: str, method: str, headers: dict, post_data, is_json: bool, kwargs: dict):
    """317ak 源 prepare_request：随机选一个 ckey 解密后注入 URL（同 yyy001 模式），SSL 证书无效需 verify=False"""
    try:
        ckey = base64.b64decode(random.choice(_317AK_REQUEST_KEYS)[14:].encode('utf-8')).decode('utf-8')
        url = url.replace('{ckey}', ckey)
    except Exception:
        pass
    return {'url': url, 'verify': False}


def _urljoin_safe(base: str, url: str) -> str:
    """urljoin 兜底：url 为空/异常时返回空字符串。绝对路径直接返，路径用 base 拼。"""
    if not url:
        return ''
    try:
        from urllib.parse import urljoin
        result = urljoin(base, url)
        return result if result.startswith('http') else ''
    except Exception:
        return '' if not url.startswith('http') else url


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
    # 2. gdstudio 跨平台 search
    ApiSource(
        name='gdstudio_search',
        platform='kugou',
        priority=10,
        description='gdstudio (跨平台源，kugou)',
        enabled=False,  # HTTP 503
        family='gdstudio',
        can_search=True,
        search_url='https://music-api.gdstudio.xyz/api.php?types=search&source=kugou&name={keyword_encoded}&count={limit}',
        extract_search=lambda d: d.get('data', []) if isinstance(d, dict) else [],
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 下载 URL 源 ====================

KUGOU_PARSE_URL_SOURCES = [
    # 1. haitanw (海糖网) - musicdl 列表（双重域名备份）
    ApiSource(
        name='haitanw_url',
        platform='kugou',
        priority=0,
        description='haitanw kg.php（musicdl 列表，level=hires/lossless/exhigh）',
        family='haitanw',
        can_parse_url=True,
        parse_url_url='https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={hash}&level={quality}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d.get('data', {}) if isinstance(d, dict) else {}, dict) else
            (d.get('data', '') if isinstance(d, dict) else '')
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',  # 支持 hires/lossless/exhigh/standard
    ),
    # 2. haitanw 备用域名
    ApiSource(
        name='haitanw_url_backup',
        platform='kugou',
        priority=5,
        description='haitanw kg.php 备用域名（music.haitangw.cc）',
        enabled=False,  # 备用域名超时
        family='haitanw',
        can_parse_url=True,
        parse_url_url='https://music.haitangw.cc/kgqq/kg.php?type=json&id={hash}&level={quality}',
        extract_url=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('url', '')
            if isinstance(d.get('data', {}) if isinstance(d, dict) else {}, dict) else
            (d.get('data', '') if isinstance(d, dict) else '')
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',  # 支持 hires/lossless/exhigh/standard
    ),
    # 3. cocodownloader (musicdl 验证可用)
    ApiSource(
        name='cocodownloader',
        platform='kugou',
        priority=10,
        description='cocodownloader (musicdl 验证可用)',
        enabled=False,  # HTTP 500
        can_parse_url=True,
        parse_url_url='https://cocodownloader.markqq.com/api/url?id={hash}&provider=kugou',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',
    ),
    # 4. 317ak (musicdl 列表) - 需 ckey 复杂鉴权
    # ★ ckey 解密已实现（见文件顶部 _317ak_prepare_request，与 yyy001 同模式）
    # max_quality='hires'：br=hires 理论支持
    ApiSource(
        name='317ak_url',
        platform='kugou',
        priority=15,
        description='317ak (musicdl 列表，ckey 解密已实现，SSL 彻底不可用)',
        enabled=False,  # SSL UNEXPECTED_EOF，服务器已失效
        family='317ak',
        can_parse_url=True,
        parse_url_url='https://api.317ak.cn/api/yinyue/kugou?ckey={ckey}&i={hash}&br={quality}&type=json&lrc=1',
        extract_url=extract_first_url,
        prepare_request=_317ak_prepare_request,
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='hires',  # br=hires 理论支持
    ),
    # 5. jbsou (musicdl 列表) - POST 复杂
    # ★ musicdl 用 urljoin 拼 base_url（jbsou API 可能返相对路径）
    # 我们用 urljoin 兜底：相对路径自动拼 https://www.jbsou.cn/
    # 6. 酷狗官方 playInfo (需先获取 hash key 才能用)
    ApiSource(
        name='kugou_official_url',
        platform='kugou',
        priority=30,
        description='酷狗官方 playInfo (需先获取 hash key)',
        enabled=False,  # 需要先解析 hash key 才能用
        can_parse_url=True,
        parse_url_url='https://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={hash}',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
        max_quality='exhigh',  # 官方 API 实际只返 mp3
    ),
    # 7. 酷狗官方 kgcloudv2 (md5+trackercdn 复杂) - musicdl 列表
    ApiSource(
        name='kugou_official_kgcloudv2',
        platform='kugou',
        priority=35,
        description='酷狗官方 trackercdn kgcloudv2 (musicdl 列表)',
        enabled=False,  # 需 md5(hash + kgcloudv2) 鉴权
        can_parse_url=True,
        parse_url_url='https://trackercdn.kugou.com/i/v2/?cdnBackup=1&behavior=download&pid=1&cmd=21&appid=1001&hash={hash}&key={__md5__}',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
        max_quality='hires',  # 理论支持
    ),
    # 8. gdstudio 跨平台 URL
    ApiSource(
        name='gdstudio_url',
        platform='kugou',
        priority=40,
        description='gdstudio URL (跨平台源，kugou)',
        enabled=False,  # HTTP 400
        family='gdstudio',
        can_parse_url=True,
        parse_url_url='https://music-api.gdstudio.xyz/api.php?types=url&id={hash}&source=kugou&br={__br__}',
        extract_url=extract_first_url,
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
        max_quality='lossless',  # gdstudio __br__ 最高 lossless
    ),
]


# ==================== 歌曲元信息源 ====================

KUGOU_PARSE_INFO_SOURCES = [
    # 1. 酷狗官方 song info（响应直接在顶层，songName 字段；映射为 name 字段以通过 _is_valid）
    # duration 在 extra.{sq/high/320/128}timelength（ms），顶层 timeLength 经常为 0
    ApiSource(
        name='kugou_official_info',
        platform='kugou',
        priority=0,
        description='酷狗官方 song info',
        can_parse_info=True,
        parse_info_url='https://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={hash}',
        extract_info=lambda d: (
            (lambda extra: {
                'id': d.get('hash', ''),
                'name': d.get('songName', ''),
                'artists': d.get('singerName', ''),
                'album': d.get('albumName', ''),
                'picUrl': d.get('album_img', d.get('imgUrl', '')),
                # 时长优先取 SQ > high > 320 > 128（毫秒）
                'duration': (extra.get('sqtimelength') or extra.get('hightimelength')
                             or extra.get('320timelength') or extra.get('128timelength')
                             or 0),
                **d,
            })(d.get('extra') or {}) if isinstance(d, dict) and d.get('songName') else {}
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. gdstudio info (跨平台)
    ApiSource(
        name='gdstudio_info',
        platform='kugou',
        priority=10,
        description='gdstudio info (跨平台)',
        enabled=False,  # HTTP 400
        family='gdstudio',
        can_parse_info=True,
        parse_info_url='https://music-api.gdstudio.xyz/api.php?types=info&id={hash}&source=kugou',
        extract_info=lambda d: (
            {'id': str(d.get('id', '')), 'name': d.get('name', ''),
             'artists': '/'.join(d.get('artist', []) if isinstance(d.get('artist'), list) else [str(d.get('artist', '') or '')]),
             'album': d.get('album', ''),
             'picUrl': d.get('pic', ''),
             'duration': d.get('duration', 0)}
            if isinstance(d, dict) and d.get('id') else {}
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. haitanw info (元信息，但 musicdl 备注 url 也在 data)
    ApiSource(
        name='haitanw_info',
        platform='kugou',
        priority=20,
        description='haitanw info (元信息)',
        family='haitanw',
        can_parse_info=True,
        parse_info_url='https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={hash}&level=lossless',
        extract_info=lambda d: (
            {'id': str(d.get('data', {}).get('rid', '')) if isinstance(d, dict) else '',
             'name': (d.get('data', {}) if isinstance(d, dict) else {}).get('name', '') or
                     (d.get('data', {}) if isinstance(d, dict) else {}).get('song', ''),
             'artists': (d.get('data', {}) if isinstance(d, dict) else {}).get('artist', '') or
                        (d.get('data', {}) if isinstance(d, dict) else {}).get('singer', ''),
             'album': (d.get('data', {}) if isinstance(d, dict) else {}).get('album', ''),
             'picUrl': (d.get('data', {}) if isinstance(d, dict) else {}).get('pic', '') or
                       (d.get('data', {}) if isinstance(d, dict) else {}).get('cover', ''),
             'duration': (d.get('data', {}) if isinstance(d, dict) else {}).get('duration', 0)}
            if isinstance(d, dict) and (d.get('data', {}) or {}).get('name') else {}
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌词源 ====================

# KRC 解密 key（16 字节），参考 music-lib krcKey
_KRC_KEY = bytes([0x40, 0x47, 0x61, 0x77, 0x5e, 0x32, 0x74, 0x47,
                  0x51, 0x36, 0x31, 0x2d, 0xce, 0xd2, 0x6e, 0x69])


def _decode_kugou_lyric_content(d: dict) -> str:
    """解码酷狗官方 lyrics.kugou.com/download API 返回的歌词

    支持两种 fmt:
      - fmt=krc: KRC 加密格式（跳过 4 字节 + XOR 16 字节 key + zlib raw deflate）
      - fmt=lrc: 简单 base64 LRC（直接 base64 解码即可）

    参考 https://github.com/guohuiyuan/music-lib/blob/main/lyrics/lyrics.go (DecodeKRCBase64)
    """
    import base64
    import zlib
    import re

    if not isinstance(d, dict):
        return ''
    content = d.get('content', '')
    if not content:
        return ''
    fmt = d.get('fmt', '')
    try:
        decoded_bytes = base64.b64decode(content)
    except Exception:
        return ''

    if fmt == 'lrc':
        # LRC 模式：直接 base64 解码
        try:
            return decoded_bytes.decode('utf-8', errors='replace')
        except Exception:
            return ''

    if fmt == 'krc':
        # KRC 模式：跳过 4 字节 + XOR + zlib（带 78xx header）解压
        if len(decoded_bytes) < 4:
            return ''
        encrypted = decoded_bytes[4:]
        # XOR 解密
        plain = bytes([b ^ _KRC_KEY[i % 16] for i, b in enumerate(encrypted)])
        # zlib 解压（注意：xor 后第 1 字节是 0x78 = zlib header）
        try:
            text = zlib.decompress(plain).decode('utf-8', errors='replace')
        except Exception:
            return ''

        # 提取 LRC 头部标签 + 把 KRC 时间格式转 LRC
        # KRC 行: [start_ms,duration_ms]<word_offset,word_duration,0>word1<...>word2
        # LRC 行: [mm:ss.xx]line
        lines = text.split('\n')
        out_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 标签行 [ti:xxx]
            if re.match(r'^\[[A-Za-z]+:', line):
                out_lines.append(line)
                continue
            # 时间行 [start,duration]<...>words
            m = re.match(r'^\[(\d+),(\d+)\](.*)$', line)
            if m:
                start_ms = int(m.group(1))
                # 转换 ms → mm:ss.xx
                minutes = start_ms // 60000
                seconds = (start_ms % 60000) // 1000
                cents = (start_ms % 1000) // 10
                # 提取所有 word 文本
                content_part = m.group(3)
                words = re.findall(r'<[^>]*>([^<]*)', content_part)
                lyric_text = ''.join(words)
                out_lines.append(f'[{minutes:02d}:{seconds:02d}.{cents:02d}]{lyric_text}')
            else:
                out_lines.append(line)
        return '\n'.join(out_lines)

    return ''


def _kugou_two_step_lyric(search_resp: dict) -> str:
    """酷狗官方歌词两步调用包装器（Step 2 + 3）

    入参: search_resp (来自 krcs.kugou.com/search 的 JSON 响应)
    流程:
      1. 从 search_resp.candidates[0] 拿 id + accesskey
      2. 调 lyrics.kugou.com/download?fmt=krc 拿加密歌词
      3. 解密 (XOR + zlib) + 转 LRC 格式

    参考 https://github.com/guohuiyuan/music-lib/blob/main/kugou/lyric.go
    失败返回空字符串（fallback 链继续走下一个 source）
    """
    import requests

    if not isinstance(search_resp, dict):
        return ''
    candidates = search_resp.get('candidates', [])
    if not candidates:
        return ''
    top = candidates[0]
    cid = top.get('id')
    accesskey = top.get('accesskey')
    if not cid or not accesskey:
        return ''

    # Step 2: download 加密歌词（参考 music-lib 不带 duration 参数）
    try:
        r = requests.get(
            'http://lyrics.kugou.com/download',
            params={
                'ver': 1, 'client': 'pc',
                'id': cid, 'accesskey': accesskey,
                'fmt': 'krc', 'charset': 'utf8',
            },
            headers=KUGOU_COMMON_HEADERS,
            timeout=10,
        )
        if r.status_code >= 400:
            return ''
        d2 = r.json()
        return _decode_kugou_lyric_content(d2)
    except Exception:
        return ''


KUGOU_PARSE_LYRIC_SOURCES = [
    # 0. 酷狗官方 krcs.kugou.com + lyrics.kugou.com（两步：search+download，KRC 加密歌词）
    # Step 1: chain 调 parse_lyric_url (krcs.kugou.com/search) 拿 candidates JSON
    #   URL 中 duration={duration} 来自 service.py 透传（ms）
    #         song_id={song_id} 来自 service.py 透传（file_hash）
    # Step 2: extract_lyric 接 candidates，自己调 download API + 解密
    # 参考 https://github.com/guohuiyuan/music-lib/blob/main/kugou/lyric.go
    ApiSource(
        name='kugou_official_lyric',
        platform='kugou',
        priority=0,
        description='酷狗官方 krcs+lyrics.kugou.com (两步 KRC 解密)',
        family='kugou_official',
        can_parse_lyric=True,
        parse_lyric_url='http://krcs.kugou.com/search?ver=1&client=mobi&duration={duration}&hash={song_id}&album_audio_id=',
        extract_lyric=_kugou_two_step_lyric,  # (d) 一个参数，duration 已在 Step1 URL
        headers=KUGOU_COMMON_HEADERS,
        timeout=10,
    ),
    # 2. haitanw lyric (data.lyric 字段)
    ApiSource(
        name='haitanw_lyric',
        platform='kugou',
        priority=10,
        description='haitanw lyric (musicdl 列表，data.lyric 字段)',
        family='haitanw',
        can_parse_lyric=True,
        parse_lyric_url='https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={hash}&level=lossless',
        extract_lyric=lambda d: (
            (d.get('data', {}) if isinstance(d, dict) else {}).get('lyric', '')
            if isinstance(d, dict) else ''
        ),
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
    # 3. 317ak lyric (musicdl 列表，lrc=1)
    # ★ ckey 解密已实现，复用 _317ak_prepare_request
    ApiSource(
        name='317ak_lyric',
        platform='kugou',
        priority=20,
        description='317ak lyric (musicdl 列表，ckey 解密已实现，SSL 彻底不可用)',
        enabled=False,  # SSL UNEXPECTED_EOF，服务器已失效
        family='317ak',
        can_parse_lyric=True,
        parse_lyric_url='https://api.317ak.cn/api/yinyue/kugou?ckey={ckey}&i={hash}&br=999&type=json&lrc=1',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        prepare_request=_317ak_prepare_request,
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
    # 4. gdstudio lyric
    ApiSource(
        name='gdstudio_lyric',
        platform='kugou',
        priority=30,
        description='gdstudio lyric (跨平台)',
        enabled=False,  # HTTP 400
        family='gdstudio',
        can_parse_lyric=True,
        parse_lyric_url='https://music-api.gdstudio.xyz/api.php?types=lyric&id={hash}&source=kugou',
        extract_lyric=lambda d: d.get('lyric', '') if isinstance(d, dict) else '',
        headers=KUGOU_COMMON_HEADERS,
        timeout=15,
    ),
]


# ==================== 歌单解析 ====================

KUGOU_PARSE_PLAYLIST_SOURCES = [
    # 1. 酷狗官方 mobilecdn.kugou.com（移动端 API，无需签名）
    # 参考 https://github.com/guohuiyuan/music-lib/blob/main/kugou/kugou.go (fetchPlaylistDetail)
    # 响应：data.info[] 里 hash/filename/duration/320hash/sqhash 等
    ApiSource(
        name='kugou_official_playlist',
        platform='kugou',
        priority=0,
        description='酷狗官方 mobilecdn.kugou.com (移动端 API，无需签名)',
        can_parse_playlist=True,
        parse_playlist_url=(
            'http://mobilecdn.kugou.com/api/v3/special/song'
            '?specialid={playlist_id}&page=1&pagesize=300&version=9108&area_code=1'
        ),
        extract_playlist=_extract_kugou_playlist,
        headers=KUGOU_MOBILE_HEADERS,
        timeout=15,
    ),
    ApiSource(
        name='gdstudio_playlist',
        platform='kugou',
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
