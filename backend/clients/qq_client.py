"""QQ音乐客户端

继承自 BaseMusicClient，实现QQ音乐平台的具体逻辑。
参考 musicdl 的QQ音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py
"""

import json
import random
import base64
import logging
import requests
from typing import Dict, List, Any

from .base_client import BaseMusicClient
from .quality_config import QualityLevel, match_quality

logger = logging.getLogger(__name__)


def strip_html_tags(text):
    """移除HTML标签，只保留纯文本"""
    if not text or not isinstance(text, str):
        return text
    import re
    return re.sub(r'<[^>]+>', '', text)


# QQ音乐文件命名规则：prefix + songmid + songmid + ext
# 参考 musicdl qqutils.py SongFileType.SORTED_QUALITIES
OFFICIAL_QUALITY_ORDER = [
    ("AI00", ".flac"),   # 母带
    ("Q000", ".flac"),   # Atmos 2.0
    ("Q001", ".flac"),   # Atmos 5.1
    ("F000", ".flac"),   # FLAC 无损
    ("O801", ".ogg"),    # OGG 640k
    ("O800", ".ogg"),    # OGG 320k
    ("O600", ".ogg"),    # OGG 192k
    ("O400", ".ogg"),    # OGG 96k
    ("M800", ".mp3"),    # MP3 320k
    ("M500", ".mp3"),    # MP3 128k
    ("C600", ".m4a"),    # AAC 192k
    ("C400", ".m4a"),    # AAC 96k
    ("C200", ".m4a"),    # AAC 48k
]

# 质量名称到文件配置的映射
QUALITY_TO_FILE_CONFIG = {
    'jymaster':  ('AI00', '.flac'),
    'master':    ('AI00', '.flac'),
    'dolby':     ('RS01', '.flac'),
    'sky':       ('Q001', '.flac'),
    'hires':     ('SQ00', '.flac'),
    'jyeffect':  ('SQ00', '.flac'),
    'lossless':  ('F000', '.flac'),
    'flac':      ('F000', '.flac'),
    'exhigh':    ('M800', '.mp3'),
    '320':       ('M800', '.mp3'),
    'standard':  ('M500', '.mp3'),
    '128':       ('M500', '.mp3'),
}


def _extract_pay_and_quality(item: dict, quality: str = 'lossless') -> dict:
    """从QQ音乐歌曲对象中提取统一的 payInfo 和 qualityMap"""
    pay_obj = item.get('pay', {}) if isinstance(item.get('pay'), dict) else {}
    pay_play = pay_obj.get('pay_play', 0)
    if pay_play == 0:
        pay_info = {'free': True, 'vipOnly': False, 'label': '免费'}
    else:
        pay_info = {'free': False, 'vipOnly': True, 'label': 'VIP'}

    file_obj = item.get('file', {}) if isinstance(item.get('file'), dict) else {}
    quality_map = {}
    size_map = {
        'l': ('size_128mp3', 128000),
        'h': ('size_320mp3', 320000),
        'sq': ('size_flac', 0),
        'hr': ('size_hires', 0),
        'ape': ('size_ape', 0),
    }
    for q_key, (field, br) in size_map.items():
        size = file_obj.get(field, 0) or item.get(field, 0)
        if size and size > 0:
            unified_key = {'l': 'standard', 'h': 'exhigh', 'sq': 'lossless', 'hr': 'hires', 'ape': 'hires'}.get(q_key, q_key)
            quality_map[unified_key] = {'bitrate': br, 'size': size}

    best = match_quality(quality_map, quality)
    return {'payInfo': pay_info, 'qualityMap': quality_map, 'bestQuality': best}


def _random_guid() -> str:
    """生成随机guid（参考 musicdl QQMusicClientUtils.randomguid）"""
    return ''.join(random.choices('abcdef1234567890', k=32))


def _random_search_id() -> str:
    """生成随机searchid（参考 musicdl QQMusicClientUtils.randomsearchid）"""
    t = random.randint(1, 20) * 18014398509481984
    n = random.randint(0, 4194304) * 4294967296
    r = round(__import__('time').time() * 1000) % (24 * 60 * 60 * 1000)
    return str(t + n + r)


class QQClient(BaseMusicClient):
    """QQ音乐客户端"""

    ENDPOINT = "https://u.y.qq.com/cgi-bin/musicu.fcg"

    def __init__(self):
        super().__init__()
        self.platform_name = "QQ音乐"
        self.platform_id = "qq"
        self.guid = _random_guid()
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/',
            'Origin': 'https://y.qq.com/',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Referer': 'http://y.qq.com',
        }
        self.session.headers.update(self.default_search_headers)

    def _safe_extract(self, data: dict, keys: list, default=None):
        """安全提取字典值"""
        result = data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            elif isinstance(result, list) and isinstance(key, int) and 0 <= key < len(result):
                result = result[key]
            else:
                return default
        return result

    def _build_request_data(self, params: dict, module: str, method: str,
                            common_override: dict = None) -> dict:
        """构建请求数据（参考 musicdl QQMusicClientUtils.buildrequestdata）"""
        common = {
            "cv": 0,
            "ct": 24,
            "format": "json",
            "inCharset": "utf-8",
            "outCharset": "utf-8",
        }
        if common_override:
            common.update(common_override)
        return {
            "comm": common,
            f"{module}.{method}": {
                "module": module,
                "method": method,
                "param": params,
            }
        }

    def _get_song_meta(self, song_id: str) -> dict:
        """获取歌曲元信息（参考 musicdl _getsongmetainfo）"""
        payload = {
            "songinfo": {
                "method": "get_song_detail_yqq",
                "module": "music.pf_song_detail_svr",
                "param": {"song_mid": song_id}
            }
        }
        try:
            resp = self.session.post(
                self.ENDPOINT,
                data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                headers=self.default_search_headers,
                timeout=10
            )
            resp.raise_for_status()
            return self._safe_extract(resp.json(), ['songinfo', 'data', 'track_info'], {})
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 获取歌曲元信息失败: {e}")
            return {}

    # ==================== 搜索 ====================

    def search(self, keyword: str, limit: int = 50, offset: int = 0, quality: str = 'lossless') -> List[Dict[str, Any]]:
        """搜索歌曲 - 使用 musicdl 风格的POST请求"""
        actual_limit = min(limit, 60)

        payload = {
            "music.search.SearchCgiService.DoSearchForQQMusicMobile": {
                "method": "DoSearchForQQMusicMobile",
                "module": "music.search.SearchCgiService",
                "param": {
                    "searchid": _random_search_id(),
                    "query": keyword,
                    "search_type": 0,
                    "num_per_page": actual_limit,
                    "page_num": offset // actual_limit + 1,
                    "highlight": 1,
                    "grp": 1
                }
            }
        }

        try:
            resp = self.session.post(
                self.ENDPOINT,
                data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                headers=self.default_search_headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            song_list = self._safe_extract(
                data, ['music.search.SearchCgiService.DoSearchForQQMusicMobile', 'data', 'body', 'item_song'], [])
            if not isinstance(song_list, list) or len(song_list) == 0:
                song_list = self._safe_extract(
                    data, ['music.search.SearchCgiService.DoSearchForQQMusicMobile', 'data', 'body', 'item_song', 'list'], [])

            songs = []
            for item in song_list:
                singer_name = '/'.join([strip_html_tags(s.get('name', ''))
                                       for s in item.get('singer', []) if isinstance(s, dict)])
                album_name = strip_html_tags(
                    self._safe_extract(item, ['album', 'title'], '') or item.get('albumname', ''))
                album_mid = self._safe_extract(item, ['album', 'mid'], '') or item.get('albummid', '')
                pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''

                pq = _extract_pay_and_quality(item, quality)
                songs.append({
                    'id': item.get('mid', '') or item.get('songmid', ''),
                    'name': strip_html_tags(item.get('title', '') or item.get('songname', '')),
                    'artists': singer_name,
                    'album': album_name,
                    'picUrl': pic_url,
                    'artist_string': singer_name,
                    'source': 'qq',
                    'interval': item.get('interval', 0),
                    **pq,
                })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}", exc_info=True)
            return []

    # ==================== 获取下载URL ====================

    def get_song_url(self, song_id: str, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取歌曲播放/下载URL

        策略（参考 musicdl）：
        1. 优先用官方 vkey API（music.vkey.GetVkey）
        2. 失败时降级到第三方 API
        """
        official = self._get_song_url_official(song_id, quality)
        if official and official.get('url'):
            return official

        third_party = self._get_song_url_third_party(song_id, quality)
        if third_party and third_party.get('url'):
            return third_party

        return {
            'url': '',
            'quality': quality,
            'song_id': song_id,
            'source': 'qq',
            'fileType': 'm4a',
            'error': 'QQ音乐所有渠道均无法获取此歌曲'
        }

    def _get_song_url_official(self, song_id: str, quality: str = 'lossless') -> Dict[str, Any]:
        """使用 QQ 官方 vkey API 获取歌曲URL

        参考 musicdl _parsewithofficialapiv1（非加密端点）
        文件命名规则：prefix + songmid + songmid + ext
        """
        prefix, ext = QUALITY_TO_FILE_CONFIG.get(quality, ('F000', '.flac'))
        filename = f"{prefix}{song_id}{song_id}{ext}"

        try:
            params = {
                "filename": [filename],
                "guid": self.guid,
                "songmid": [song_id],
                "songtype": [0],
                "uin": "0",
                "loginflag": 1,
                "platform": "20"
            }
            req_data = self._build_request_data(params, "music.vkey.GetVkey", "UrlGetVkey")

            resp = self.session.post(
                self.ENDPOINT,
                data=json.dumps(req_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                headers=self.default_search_headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            midurlinfo = self._safe_extract(
                data, ['music.vkey.GetVkey.UrlGetVkey', 'data', 'midurlinfo'], [])
            sip = self._safe_extract(
                data, ['music.vkey.GetVkey.UrlGetVkey', 'data', 'sip'], [])

            if midurlinfo and midurlinfo[0].get('purl') and sip:
                purl = midurlinfo[0]['purl']
                sip_index = 1 if len(sip) > 1 else 0
                music_url = sip[sip_index] + purl
                music_url = music_url.replace('http://', 'https://')
                return {
                    'url': music_url,
                    'quality': quality,
                    'song_id': song_id,
                    'source': 'qq',
                    'fileType': ext.lstrip('.')
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 官方API获取歌曲URL失败: {e}")

        return {}

    def _get_song_url_third_party(self, song_id: str, quality: str = 'lossless') -> Dict[str, Any]:
        """第三方API获取歌曲URL

        参考 musicdl _parsewiththirdpartapis 优先级：
        vkeys(svip) -> xcvts(svip) -> xianyuw(vip) -> nki(vip) -> tang(vip) ->
        317ak(vip) -> cyapi -> xunhuisi -> lxmusic -> lpz
        """
        # 第三方API不依赖cookie，始终尝试

        # 参考 musicdl 的 REQUEST_KEYS
        REQUEST_KEYS_XCVTS = [
            'Nzg5OTMzNDRiOWJmMTEwNTY1NTU5OTAwOWNkYmEzZDI=',
            'Y2U3NzhlYjBkMTg1OGVkZmI0YjIwNzFhMTE1ZjFlZGY=',
        ]
        REQUEST_KEYS_XIANYUW = [
            'charlespikachuc2stNTc2ZmFkZTQxNjI2M2I3ZmY3MjZhZjM1NGQ5ZDkzNzM=',
            'charlespikachuc2stMDE4YjlmOGQ4MGRjMTg5OGEyOTI3ZTgwMjA2NjNkODY=',
        ]
        REQUEST_KEYS_NKI = [
            'MjhmZWNlOTI1NDM5YjA1Mjc5MmE5Nzk4OWM4NzBjZWQzODAzYTcxYzZiNTM0ZjcxZTVhNTMzMzhiMmQzMWVmOA==',
            'YzRjNGY1ZmMzNmJhZDRjYWNiOTg4MzllMTRmZWE0MDI3N2IzNWVhMmViMWJhYmRhZDdiYmRlMTI4NDAwZjNiMQ==',
        ]
        REQUEST_KEYS_317AK = ['charlespikachuWk83NlFKQ0lINVBQSUNKT09YVUg=']
        REQUEST_KEYS_CYAPI = [
            '1ffdf5733f5d538760e63d7e46ba17438d9f7b9dfc18c51be1109386fd74c3a1',
            '2baf39266d8ef0580aba937245d5bb569fe376f230ff508f1faa0922dc320fe4',
        ]

        def _decrypt_b64(t):
            return base64.b64decode(str(t).encode('utf-8')).decode('utf-8')

        def _decrypt_b64_skip14(t):
            return base64.b64decode(str(t)[14:].encode('utf-8')).decode('utf-8')

        # 按 musicdl 优先级排列
        apis = [
            # L1: svip (vkeys 需要尝试多个 quality，14/12 有时返回截断URL)
            ('vkeys_multi', None),
            ('xcvts', lambda sid: f"https://api.xcvts.cn/api/music/qq?apiKey={_decrypt_b64(random.choice(REQUEST_KEYS_XCVTS))}&mid={sid}&type=臻品母带"),
            # L2: vip
            ('xianyuw', lambda sid: f"https://apii.xianyuw.cn/api/v1/qq-music-search?id={sid}&key={_decrypt_b64_skip14(random.choice(REQUEST_KEYS_XIANYUW))}&no_url=0&br=hires"),
            ('nki', lambda sid: f"https://api.nki.pw/API/music_open_api.php?mid={sid}&apikey={_decrypt_b64(random.choice(REQUEST_KEYS_NKI))}"),
            ('tang', lambda sid: f"https://tang.api.s01s.cn/music_open_api.php?mid={sid}"),
            ('317ak', lambda sid: f"https://api.317ak.cn/api/yinyue/qqyinyue?ckey={_decrypt_b64_skip14(random.choice(REQUEST_KEYS_317AK))}&i={sid}&br=7&type=json&lrc=1"),
            # L3: vip account but only mp3/m4a
            ('cyapi', lambda sid: f"https://cyapi.top/API/qq_music.php?apikey={random.choice(REQUEST_KEYS_CYAPI)}&type=json&mid={sid}&quality=lossless"),
            ('xunhuisi', lambda sid: f"https://api.xunhuisi.store/API/QQMusic/Song.php?mid={sid}&type=json"),
            ('lxmusic', lambda sid: f"https://lxmusicapi.onrender.com/url/tx/{sid}/flac24bit"),
            # L4: invalid or unstable
            ('lpz', lambda sid: f"https://lpz.chatc.vip/apiqq.php?songmid={sid}&type=json&br=1"),
        ]

        for api_name, api_func in apis:
            # vkeys 需要尝试多个 quality 值
            if api_name == 'vkeys_multi':
                for vq in [13, 11, 10, 9, 8]:
                    try:
                        api_url = f"https://api.vkeys.cn/music/tencent/song/link?mid={song_id}&quality={vq}"
                        resp = requests.get(api_url, headers=self.default_download_headers, timeout=8)
                        data = resp.json()
                        download_url = self._safe_extract(data, ['data', 'url'], '')
                        if download_url and str(download_url).startswith('http') and len(download_url) > 50:
                            dl_lower = str(download_url).lower()
                            file_type = 'flac' if '.flac' in dl_lower else 'mp3' if '.mp3' in dl_lower else 'm4a'
                            logger.info(f"[{self.platform_name}] 第三方API(vkeys q={vq})成功: {download_url[:80]}...")
                            return {'url': download_url, 'quality': quality, 'song_id': song_id, 'source': 'qq', 'fileType': file_type}
                    except Exception as e:
                        logger.debug(f"[{self.platform_name}] vkeys q={vq} 失败: {e}")
                continue

            api_url = api_func(song_id)
            try:
                resp = requests.get(api_url, headers=self.default_download_headers, timeout=10)
                data = resp.json()

                download_url = None
                if api_name == 'vkeys':
                    download_url = self._safe_extract(data, ['data', 'url'], '')
                elif api_name == 'xcvts':
                    download_url = self._safe_extract(data, ['data', 'music'], '')
                elif api_name == 'xianyuw':
                    download_url = self._safe_extract(data, ['data', 'url'], '')
                elif api_name == 'nki':
                    download_url = (data.get('song_play_url_sq') or data.get('song_play_url_pq')
                                    or data.get('song_play_url_accom') or data.get('song_play_url_hq')
                                    or data.get('song_play_url') or data.get('song_play_url_standard'))
                elif api_name == 'tang':
                    download_url = (data.get('song_play_url_sq') or data.get('song_play_url_pq')
                                    or data.get('song_play_url_accom') or data.get('song_play_url_hq')
                                    or data.get('song_play_url') or data.get('song_play_url_standard'))
                elif api_name == '317ak':
                    download_url = self._safe_extract(data, ['url'], '')
                elif api_name == 'cyapi':
                    download_url = data.get('url', '')
                elif api_name == 'xunhuisi':
                    download_url = data.get('music_url', '')
                elif api_name == 'lxmusic':
                    download_url = data.get('url', '')
                    if '无法获取' in str(data.get('msg')) or 'http://panspace.kuwo.cn/' in (download_url or ''):
                        continue
                elif api_name == 'lpz':
                    download_url = self._safe_extract(data, ['data', 'music_url'], '')

                if download_url and str(download_url).startswith('http'):
                    dl_lower = str(download_url).lower()
                    if '.flac' in dl_lower:
                        file_type = 'flac'
                    elif '.mp3' in dl_lower:
                        file_type = 'mp3'
                    elif '.m4a' in dl_lower or '.mp4' in dl_lower:
                        file_type = 'm4a'
                    elif '.ogg' in dl_lower:
                        file_type = 'ogg'
                    else:
                        file_type = 'm4a'
                    logger.info(f"[{self.platform_name}] 第三方API({api_name})成功: {download_url[:80]}...")
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'qq',
                        'fileType': file_type
                    }
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 第三方API({api_name})失败: {e}")
                continue

        return {}

    # ==================== 歌单 ====================

    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        payload = {
            "music.search.SearchCgiService.DoSearchForQQMusicMobile": {
                "method": "DoSearchForQQMusicMobile",
                "module": "music.search.SearchCgiService",
                "param": {
                    "searchid": _random_search_id(),
                    "query": keyword,
                    "search_type": 3,
                    "num_per_page": limit,
                    "page_num": 1,
                    "highlight": 1,
                    "grp": 1
                }
            }
        }

        try:
            resp = self.session.post(
                self.ENDPOINT,
                data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                headers=self.default_search_headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            playlist_list = self._safe_extract(
                data, ['music.search.SearchCgiService.DoSearchForQQMusicMobile', 'data', 'body', 'item_songlist'], [])

            playlists = []
            for item in playlist_list:
                playlists.append({
                    'id': item.get('dissid', 0),
                    'name': strip_html_tags(item.get('dissname', '')),
                    'coverImgUrl': item.get('logo', ''),
                    'description': strip_html_tags(item.get('description', '')),
                    'trackCount': item.get('songnum', 0),
                    'playCount': item.get('listennum', 0),
                    'source': 'qq'
                })
            return playlists
        except Exception as e:
            logger.error(f"[{self.platform_name}] 歌单搜索失败: {e}")
            return []

    def get_playlist(self, playlist_id: int, limit: int = 0) -> Dict[str, Any]:
        """获取歌单"""
        all_tracks = []
        total_songs = 0

        headers = {
            'Referer': f'https://y.qq.com/n/ryqq/playlist/{playlist_id}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
        }

        try:
            basic_url = "https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
            basic_params = {
                'disstid': str(playlist_id),
                'type': '1',
                'json': '1',
                'utf8': '1',
                'onlysong': '0',
                'format': 'json'
            }

            resp = self.session.get(basic_url, params=basic_params, headers=headers, timeout=15)
            resp.raise_for_status()
            basic_data = resp.json()

            subcode = basic_data.get('subcode', 0)
            msg = basic_data.get('msg', '')
            if subcode == 4000 or 'privacy' in msg.lower():
                return {'__error__': 'privacy', '__message__': f'该歌单已设置隐私保护，无法查看（{msg}）'}

            cdlist = basic_data.get('cdlist', [])
            if not cdlist:
                if subcode and subcode != 0:
                    return {'__error__': 'api_error', '__message__': f'QQ音乐API错误(subcode={subcode}): {msg}'}
                return {'__error__': 'empty', '__message__': '歌单不存在或需要登录'}

            playlist_info = cdlist[0]
            total_songs = playlist_info.get('songnum', 0)
            songlist = playlist_info.get('songlist', [])

            for item in songlist:
                singer_name = '/'.join([s.get('name', '') for s in item.get('singer', []) if isinstance(s, dict)])
                album_name = self._safe_extract(item, ['album', 'title'], '') or item.get('albumname', '')
                album_mid = self._safe_extract(item, ['album', 'mid'], '') or item.get('albummid', '')
                pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''

                pq = _extract_pay_and_quality(item)
                all_tracks.append({
                    'id': item.get('songmid', ''),
                    'name': item.get('songname', ''),
                    'artists': singer_name,
                    'album': album_name,
                    'picUrl': pic_url,
                    'source': 'qq',
                    **pq,
                })

            cover_mid = (playlist_info.get('logo', '')
                         .replace('https://y.gtimg.cn/music/photo_new/T002R800x800M000', '')
                         .replace('.jpg', ''))
            cover_url = (f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{cover_mid}.jpg?max_age=2592000"
                         if cover_mid else playlist_info.get('logo', ''))

            return {
                'id': playlist_info.get('dissid', 0),
                'name': playlist_info.get('dissname', ''),
                'coverImgUrl': cover_url,
                'description': playlist_info.get('desc', ''),
                'trackCount': total_songs if total_songs > 0 else len(all_tracks),
                'playCount': playlist_info.get('playcount', 0),
                'tracks': all_tracks,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌单信息失败: {e}")
            return {}

    # ==================== 歌曲详情 & 歌词 ====================

    def get_song_info(self, song_id: str) -> Dict[str, Any]:
        """获取歌曲信息"""
        track_info = self._get_song_meta(song_id)
        if not track_info:
            return {}

        singer_name = '/'.join([s.get('name', '') for s in track_info.get('singer', []) if isinstance(s, dict)])
        album_name = self._safe_extract(track_info, ['album', 'title'], '') or track_info.get('albumname', '')
        album_mid = self._safe_extract(track_info, ['album', 'mid'], '') or track_info.get('albummid', '')
        pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''

        pq = _extract_pay_and_quality(track_info)
        return {
            'id': track_info.get('mid', ''),
            'name': track_info.get('name', '') or track_info.get('title', ''),
            'artists': singer_name,
            'album': album_name,
            'picUrl': pic_url,
            'duration': int(float(track_info.get('interval', 0) or 0)) * 1000,
            'source': 'qq',
            **pq,
        }

    def get_lyric(self, song_id: str) -> str:
        """获取歌词"""
        url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        params = {
            'songmid': song_id,
            'g_tk': '5381',
            'loginUin': '0',
            'hostUin': '0',
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'platform': 'yqq'
        }

        try:
            detail_headers = {'Referer': 'https://y.qq.com/portal/player.html'}
            resp = self.session.get(url, params=params, headers=detail_headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            lyric_base64 = data.get('lyric', '')
            if lyric_base64 and lyric_base64 != 'NULL':
                try:
                    return base64.b64decode(lyric_base64).decode('utf-8')
                except Exception:
                    return lyric_base64
            return ''
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌词失败: {e}")
            return ''


qq_client = QQClient()
