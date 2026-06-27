"""网易云音乐客户端

继承自 BaseMusicClient，实现网易云音乐平台的具体逻辑。

支持三条数据源线路：
1. official - 官方API（优先）
2. xuanluoge - 第三方解析API
3. haitangw - 第三方解析API

参考 musicdl 的网易云实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/netease.py
"""

import json
import urllib.parse
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

from .base_client import BaseMusicClient
from .quality_config import QualityLevel, match_quality

logger = logging.getLogger(__name__)

# 网易云原始 key → 统一 quality key
_NETEASE_QUALITY_MAP = {
    'l': 'standard',
    'm': 'exhigh',
    'h': 'lossless',
    'sq': 'hires',
    'hr': 'hires',
}

# 统一音质优先级（从高到低）
_QUALITY_PRIORITY = ['jymaster', 'jyeffect', 'hires', 'lossless', 'dolby', 'sky', 'exhigh', 'standard']


def _extract_pay_and_quality(track: dict, quality: str = 'lossless') -> dict:
    """从网易云歌曲对象中提取统一的 payInfo 和 qualityMap"""
    fee = track.get('fee', 0)
    if fee == 0 or fee == 4:
        pay_info = {'free': True, 'vipOnly': False, 'label': '免费'}
    elif fee == 8:
        pay_info = {'free': False, 'vipOnly': True, 'label': 'VIP'}
    else:
        pay_info = {'free': False, 'vipOnly': True, 'label': '付费'}

    quality_map = {}
    for key in ['l', 'm', 'h', 'sq', 'hr']:
        q = track.get(key)
        if q and q.get('size'):
            unified_key = _NETEASE_QUALITY_MAP.get(key, key)
            quality_map[unified_key] = {
                'bitrate': q.get('br', 0),
                'size': q.get('size', 0),
            }

    best = match_quality(quality_map, quality)
    return {'payInfo': pay_info, 'qualityMap': quality_map, 'bestQuality': best}


class NeteaseAPISource(Enum):
    """网易云API源枚举"""
    OFFICIAL = "official"
    GDSTUDIO = "gdstudio"
    XUANLUOGE = "xuanluoge"
    HAITANGW = "haitangw"


class APIConstants:
    """API相关常量"""
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154'
    REFERER = 'https://music.163.com/'

    SONG_DETAIL_API = "https://music.163.com/api/song/detail"
    LYRIC_API = "https://music.163.com/api/song/lyric"
    SEARCH_API = 'https://music.163.com/api/cloudsearch/pc'
    PLAYLIST_DETAIL_API = 'https://music.163.com/api/v6/playlist/detail'
    ALBUM_DETAIL_API = 'https://music.163.com/api/v1/album/'
    ARTIST_TOP_SONG_API = 'https://music.163.com/api/artist/top/song'

    DEFAULT_COOKIES = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!"
    }

    XUANLUOGE_URL = "http://118.24.104.108:3456/api.php"
    HAITANGW_URL = "https://musicapi.haitangw.net/music/wy.php"
    # gdstudio - musicdl 列表里唯一还活着的网易云 search 端点
    GDSTUDIO_URL = "https://music-api.gdstudio.xyz/api.php"

    COOKIE_FILE_PATH = "netease_cookie.txt"


class NeteaseClient(BaseMusicClient):
    """网易云音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "网易云音乐"
        self.platform_id = "netease"
        self._has_cookie = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/'
        })
        self.session.cookies.update(APIConstants.DEFAULT_COOKIES)
        self._load_local_cookies()
    
    def _load_local_cookies(self):
        """加载本地cookie文件（按优先级依次尝试多个位置）

        候选路径：
          1. /app/cookie/netease_cookie.txt        （Docker 部署，bind mount 位置）
          2. clients/cookie/netease_cookie.txt     （与本文件同级的 cookie 目录）
          3. cookie/netease_cookie.txt             （backend 下的 cookie 目录）
          4. netease_cookie.txt                    （backend 根目录，旧位置）
          5. cookie.txt                            （backend 根目录下的简写名）
        """
        import os
        # cookie 候选路径（按优先级排序）
        candidates = [
            '/app/cookie/netease_cookie.txt',
            os.path.join(os.path.dirname(__file__), 'cookie', 'netease_cookie.txt'),
            os.path.join(os.path.dirname(__file__), '..', 'cookie', 'netease_cookie.txt'),
            os.path.join(os.path.dirname(__file__), '..', 'netease_cookie.txt'),
            os.path.join(os.path.dirname(__file__), '..', 'cookie.txt'),
        ]

        # 找第一个存在的
        cookie_path = None
        for cand in candidates:
            cand_abs = os.path.abspath(cand)
            if os.path.exists(cand_abs):
                cookie_path = cand_abs
                break

        if cookie_path is None:
            logger.warning(
                f"[{self.platform_name}] cookie 文件不存在，已尝试以下位置:\n  " +
                "\n  ".join(os.path.abspath(c) for c in candidates) +
                "\n  提示: 在任一位置创建 netease_cookie.txt 并填入网易云 MUSIC_U 即可启用 VIP 无损/HiRes"
            )
            return

        try:
            with open(cookie_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            cookie_count = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                for cookie_pair in line.split(';'):
                    cookie_pair = cookie_pair.strip()
                    if '=' in cookie_pair:
                        key, value = cookie_pair.split('=', 1)
                        self.session.cookies.set(key.strip(), value.strip())
                        cookie_count += 1

            if cookie_count > 0:
                has_music_u = 'MUSIC_U' in self.session.cookies
                self._has_cookie = True
                self._last_cookie_mtime = os.path.getmtime(cookie_path)
                logger.info(
                    f"[{self.platform_name}] 从 {cookie_path} 加载 {cookie_count} 个 cookie"
                    f"{'（含 MUSIC_U = VIP 身份）' if has_music_u else '（无 MUSIC_U）'}"
                )
            else:
                logger.warning(
                    f"[{self.platform_name}] {cookie_path} 文件为空或没有有效内容（只有注释？）"
                )
        except Exception as e:
            logger.error(f"[{self.platform_name}] 加载本地 cookie 文件失败: {e}")

    def reload_cookies(self):
        """重新加载 cookie 文件（清空 session.cookies 后再读）

        用于用户修改 cookie 文件后动态生效，不需要重启后端
        """
        # 只清空业务 cookie，保留 DEFAULT_COOKIES 中的客户端标识
        for key in list(self.session.cookies.keys()):
            if key not in APIConstants.DEFAULT_COOKIES:
                del self.session.cookies[key]
        self._has_cookie = False
        self._load_local_cookies()
    
    def search(self, keyword: str, limit: int = 50, offset: int = 0, quality: str = 'lossless') -> List[Dict[str, Any]]:
        """搜索歌曲

        策略（参考 musicdl）：始终官方优先 + 多源降级
        1. 官方 cloudsearch（POST，无 cookie 也能搜到结果；带 cookie 能拿到付费标记）
        2. gdstudio（musicdl 列表中唯一仍可用的网易云 search 端点）
        3. xuanluoge / haitangw（已失效但作为最后兜底）
        """
        # 1. 官方 API：不带 cookie 也能搜到基础结果
        songs = self._search_official(keyword, limit, offset, quality)
        if songs:
            return songs

        # 2. gdstudio fallback
        logger.info(f"[{self.platform_name}] 官方搜索无结果，尝试 gdstudio")
        songs = self._search_gdstudio(keyword, limit)
        if songs:
            return songs

        # 3. xuanluoge / haitangw 兜底（已不稳定，保留兼容）
        songs = self._search_xuanluoge(keyword, limit)
        if songs:
            return songs
        songs = self._search_haitangw(keyword, limit)
        if not songs:
            logger.warning(f"[{self.platform_name}] 搜索无结果 keyword={keyword!r} (所有源失败)")
        return songs

    def _search_official(self, keyword: str, limit: int, offset: int, quality: str) -> List[Dict[str, Any]]:
        """官方 API 搜索（无需 cookie，带 cookie 时返回更完整的付费标记）

        musicdl 用 POST，我们 POST/GET 都验证过一致。
        """
        url = APIConstants.SEARCH_API
        params = {
            's': keyword,
            'type': 1,
            'limit': limit,
            'offset': offset
        }

        try:
            data = self._get(url, params=params)
            if not data:
                return []

            songs = []
            for item in data.get('result', {}).get('songs', []):
                pq = _extract_pay_and_quality(item, quality)
                songs.append({
                    'id': item['id'],
                    'name': item['name'],
                    'artists': '/'.join([a['name'] for a in item['ar']]),
                    'album': item['al']['name'],
                    'picUrl': item['al']['picUrl'],
                    'artist_string': '/'.join([a['name'] for a in item['ar']]),
                    'source': 'netease',
                    'duration': item.get('dt', 0),
                    **pq,
                })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 官方 API 搜索失败: {e}")
            return []

    def _search_gdstudio(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """gdstudio 第三方搜索（musicdl 验证过可用的网易云 search 端点）"""
        try:
            url = f"{APIConstants.GDSTUDIO_URL}?types=search&source=netease&name={urllib.parse.quote(keyword)}&count={limit}"
            data = self._get(url, timeout=15)
            if not isinstance(data, list) or not data:
                return []

            songs = []
            for item in data[:limit]:
                if not isinstance(item, dict):
                    continue
                # gdstudio 返回的 id 是字符串，统一转 int
                try:
                    sid = int(item.get('id', 0))
                except (TypeError, ValueError):
                    continue
                if not sid:
                    continue
                artists_raw = item.get('artist', [])
                if isinstance(artists_raw, list):
                    artists = '/'.join(a for a in artists_raw if a)
                else:
                    artists = str(artists_raw or '')
                songs.append({
                    'id': sid,
                    'name': item.get('name', ''),
                    'artists': artists,
                    'album': item.get('album', ''),
                    'picUrl': '',  # gdstudio 返回 pic_id，需要额外查；前端会用 name 占位
                    'artist_string': artists,
                    'source': 'netease',
                    'api_source': 'gdstudio',
                    'duration': 0,
                    'payInfo': {'free': True, 'vipOnly': False, 'label': '免费'},
                    'qualityMap': {},
                    'bestQuality': '',
                })
            return songs
        except Exception as e:
            logger.debug(f"[{self.platform_name}] gdstudio 搜索失败: {e}")
            return []

    def _search_xuanluoge(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """xuanluoge 第三方 API 搜索"""
        try:
            url = f"{APIConstants.XUANLUOGE_URL}?miss=search&keyword={urllib.parse.quote(keyword)}&limit={limit}"
            data = self._get(url)
            if not data:
                return []

            song_list = data.get('data', data) if isinstance(data, dict) else data
            if not isinstance(song_list, list):
                return []

            songs = []
            for item in song_list[:limit]:
                if not isinstance(item, dict):
                    continue
                artists = item.get('artists') or item.get('artist') or ''
                if isinstance(artists, list):
                    artists = '/'.join([a.get('name', '') for a in artists if a.get('name')])
                songs.append({
                    'id': str(item.get('id', '')),
                    'name': item.get('name', ''),
                    'artists': artists,
                    'album': item.get('album', ''),
                    'picUrl': item.get('picUrl') or item.get('pic') or '',
                    'artist_string': artists,
                    'source': 'netease',
                    'api_source': 'xuanluoge',
                    'duration': item.get('duration') or item.get('dt') or 0,
                    'payInfo': {'free': True, 'vipOnly': False, 'label': '免费'},
                    'qualityMap': {},
                    'bestQuality': '',
                })
            return songs
        except Exception as e:
            logger.debug(f"[{self.platform_name}] xuanluoge 搜索失败: {e}")
            return []

    def _search_haitangw(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        """haitangw 第三方 API 搜索"""
        try:
            url = f"{APIConstants.HAITANGW_URL}?keyword={urllib.parse.quote(keyword)}&type=search&limit={limit}"
            data = self._get(url)
            if not data or not data.get('data'):
                return []

            song_list = data['data'] if isinstance(data['data'], list) else data['data'].get('list', [])
            songs = []
            for item in song_list[:limit]:
                if not isinstance(item, dict):
                    continue
                artists = item.get('artists') or item.get('artist') or ''
                songs.append({
                    'id': str(item.get('id', '')),
                    'name': item.get('name', ''),
                    'artists': artists,
                    'album': item.get('album', ''),
                    'picUrl': item.get('picUrl') or item.get('pic') or '',
                    'artist_string': artists,
                    'source': 'netease',
                    'api_source': 'haitangw',
                    'duration': item.get('duration') or item.get('dt') or 0,
                    'payInfo': {'free': True, 'vipOnly': False, 'label': '免费'},
                    'qualityMap': {},
                    'bestQuality': '',
                })
            return songs
        except Exception as e:
            logger.debug(f"[{self.platform_name}] haitangw 搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        url = APIConstants.SEARCH_API
        params = {
            's': keyword,
            'type': 1000,
            'limit': limit,
            'offset': 0
        }
        
        try:
            data = self._get(url, params=params)
            playlists = []
            for item in data.get('result', {}).get('playlists', []):
                playlists.append({
                    'id': item.get('id', 0),
                    'name': item.get('name', ''),
                    'coverImgUrl': item.get('coverImgUrl') or item.get('picUrl') or '',
                    'description': item.get('description') or '',
                    'trackCount': item.get('trackCount') or item.get('size') or 0,
                    'playCount': item.get('playCount') or 0,
                    'source': 'netease'
                })
            return playlists
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索歌单失败: {e}")
            return []
    
    def _get_song_url_official(self, song_id: int, quality: str) -> Optional[str]:
        """使用官方API获取歌曲URL（GET 简单 API，无需 eapi 加密）

        注意：eapi 加密版的接口（/eapi/song/enhance/player/url/v1）在匿名用户下
        会忽略 level 字段并强制返回 320k MP3，而简单的 GET API 能正确返回码率。
        改用 GET 后可与第三方接口（xuanluoge）保持同等音质。
        """
        try:
            # level → br 码率（bps）映射
            br_map = {
                'standard': 128000,
                'exhigh': 320000,
                'lossless': 999000,
                'hires': 999000,
                'jymaster': 999000,
            }
            br = br_map.get(quality, 999000)

            params = {
                'id': str(song_id),
                'ids': f'[{song_id}]',
                'br': br,
            }
            headers = {
                'User-Agent': APIConstants.USER_AGENT,
                'Referer': APIConstants.REFERER,
            }
            response = self.session.get(
                'https://music.163.com/api/song/enhance/player/url',
                params=params,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            if data.get('data') and len(data['data']) > 0:
                item = data['data'][0]
                url = item.get('url')
                if url and url.startswith('http'):
                    return url
            return None
        except Exception as e:
            logger.error(f"[{self.platform_name}] 官方API获取歌曲URL失败: {e}")
            return None
    
    def _get_song_url_xuanluoge(self, song_id: int, quality: str) -> Optional[str]:
        """使用xuanluoge API获取歌曲URL"""
        try:
            url = f"{APIConstants.XUANLUOGE_URL}?miss=getMusicUrl&id={song_id}&level={quality}"
            data = self._get(url)

            if isinstance(data, list):
                download_url = data[0].get('url', '') if data else ''
            else:
                download_url = data.get('data', [{}])[0].get('url', '')

            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.error(f"[{self.platform_name}] xuanluoge API获取歌曲URL失败: {e}")
            return None

    def _get_song_url_cenguigui(self, song_id: int, quality: str) -> Optional[str]:
        """使用cenguigui API获取歌曲URL（musicdl 验证可用）"""
        try:
            url = f"https://api-v2.cenguigui.cn/api/netease/music_v1.php?id={song_id}&type=json&level={quality}"
            data = self._get(url)
            download_url = (data or {}).get('data', {}).get('url', '')
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.debug(f"[{self.platform_name}] cenguigui获取URL失败: {e}")
            return None

    def _get_song_url_bileizhen(self, song_id: int, quality: str) -> Optional[str]:
        """使用bileizhen API获取歌曲URL（musicdl 验证可用）"""
        try:
            url = f"https://api.bileizhen.top/api/netease?id={song_id}&level={quality}"
            data = self._get(url)
            download_url = (data or {}).get('data', {}).get('url', '')
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.debug(f"[{self.platform_name}] bileizhen获取URL失败: {e}")
            return None

    def _get_song_url_gdstudio(self, song_id: int, quality: str) -> Optional[str]:
        """使用gdstudio API获取歌曲URL（musicdl 验证可用）"""
        try:
            # br: 128/320/999(hires-lossless)/740(lossless FLAC)
            br_map = {'standard': 128, 'exhigh': 320, 'lossless': 999, 'hires': 999, 'jymaster': 999}
            br = br_map.get(quality, 999)
            url = f"https://music-api.gdstudio.xyz/api.php?types=url&id={song_id}&source=netease&br={br}"
            data = self._get(url, timeout=15)
            download_url = (data or {}).get('url', '') if isinstance(data, dict) else ''
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.debug(f"[{self.platform_name}] gdstudio获取URL失败: {e}")
            return None

    def _get_song_url_cunyu(self, song_id: int, quality: str) -> Optional[str]:
        """使用cunyu API获取歌曲URL（musicdl 验证可用）"""
        try:
            url = f"https://www.cunyuapi.top/163music_play?id={song_id}&quality={quality}"
            data = self._get(url, timeout=15)
            download_url = (data or {}).get('song_file_url', '') if isinstance(data, dict) else ''
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.debug(f"[{self.platform_name}] cunyu获取URL失败: {e}")
            return None

    def _get_song_url_rxtool(self, song_id: int, quality: str) -> Optional[str]:
        """使用rxtool API获取歌曲URL（musicdl 验证可用）"""
        try:
            url = f"https://api.rxtool.top/api/meteasecloudmusic.php?id={song_id}&level=hires"
            data = self._get(url, timeout=15)
            download_url = (data or {}).get('url', '') if isinstance(data, dict) else ''
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.debug(f"[{self.platform_name}] rxtool获取URL失败: {e}")
            return None

    def _get_song_url_cocodownloader(self, song_id: int, quality: str) -> Optional[str]:
        """使用cocodownloader API获取歌曲URL（musicdl 验证可用）"""
        try:
            url = f"https://cocodownloader.markqq.com/api/url?id={song_id}&provider=netease&quality=jymaster"
            data = self._get(url, timeout=15)
            download_url = (data or {}).get('url', '') if isinstance(data, dict) else ''
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.debug(f"[{self.platform_name}] cocodownloader获取URL失败: {e}")
            return None

    def _get_song_url_vincentzyu233(self, song_id: int, quality: str) -> Optional[str]:
        """使用vincentzyu233 API获取歌曲URL（musicdl 验证可用）"""
        try:
            url = f"http://xwl.vincentzyu233.cn:51217/v2/music/netease?id={song_id}&quality=9"
            data = self._get(url, timeout=15)
            download_url = (data or {}).get('data', {}).get('url', '') if isinstance(data, dict) else ''
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.debug(f"[{self.platform_name}] vincentzyu233获取URL失败: {e}")
            return None

    def _get_song_url_haitangw(self, song_id: int, quality: str) -> Optional[str]:
        """使用haitangw API获取歌曲URL"""
        try:
            url = f"{APIConstants.HAITANGW_URL}?id={song_id}&level={quality}&type=json"
            data = self._get(url)

            download_url = data.get('data', {}).get('url', '')
            if download_url and download_url.startswith('http'):
                return download_url
            return None
        except Exception as e:
            logger.error(f"[{self.platform_name}] haitangw API获取歌曲URL失败: {e}")
            return None

    def _get_song_url_backup(self, song_id: int, quality: str) -> Optional[str]:
        """使用备用API获取歌曲URL"""
        try:
            url = f"https://api.injahow.cn/meting/api?server=netease&type=url&id={song_id}&br={quality}"
            data = self._get(url)

            if isinstance(data, dict) and data.get('url'):
                return data['url']
            return None
        except Exception as e:
            logger.error(f"[{self.platform_name}] 备用API获取歌曲URL失败: {e}")
            return None

    def _get_song_url_meting(self, song_id: int, quality: str) -> Optional[str]:
        """使用Meting API获取歌曲URL"""
        try:
            # 尝试多个Meting API源
            apis = [
                f"https://api.paugram.com/api/meting?server=netease&type=url&id={song_id}&br={quality}",
                f"https://meting.sigure.xyz/api?server=netease&type=url&id={song_id}&br={quality}",
            ]
            
            for api_url in apis:
                data = self._get(api_url)
                if isinstance(data, dict) and data.get('data'):
                    download_url = data['data'].get('url', '')
                    if download_url and download_url.startswith('http'):
                        return download_url
            return None
        except Exception as e:
            logger.error(f"[{self.platform_name}] Meting API获取歌曲URL失败: {e}")
            return None
    
    def get_song_url(self, song_id: int, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取歌曲播放/下载URL（多源自动降级）

        策略（参考 musicdl）：始终尝试官方 → 9 个第三方源依次降级
        - 有 cookie 时官方能拿到 HiRes/付费资源
        - 无 cookie 或非 VIP 时官方返回空，自动落到第三方
        """
        from .quality_config import is_valid_quality, get_default_quality
        if not is_valid_quality(quality):
            quality = get_default_quality()

        source_func_map = {
            'official': self._get_song_url_official,        # 1. 官方（VIP cookie → HiRes）
            'cenguigui': self._get_song_url_cenguigui,      # 2. cenguigui
            'xuanluoge': self._get_song_url_xuanluoge,      # 3. xuanluoge
            'bileizhen': self._get_song_url_bileizhen,      # 4. bileizhen
            'gdstudio': self._get_song_url_gdstudio,        # 5. gdstudio
            'cunyu': self._get_song_url_cunyu,              # 6. cunyu
            'rxtool': self._get_song_url_rxtool,            # 7. rxtool
            'cocodownloader': self._get_song_url_cocodownloader,  # 8. cocodownloader
            'vincentzyu233': self._get_song_url_vincentzyu233,    # 9. vincentzyu233
            'meting': self._get_song_url_meting,            # 10. meting
        }
        # 始终走完整链：cookie 失效/VIP 受限时官方会快速返回空，自动落到第三方
        sources_to_try = list(source_func_map.keys())

        for source in sources_to_try:
            download_url = source_func_map[source](song_id, quality)
            if download_url:
                return {
                    'url': download_url,
                    'quality': quality,
                    'api_source': source,
                    'song_id': song_id,
                    'source': 'netease'
                    # 注意：网易云 URL 不带文件后缀，文件真实类型由后端下载后用 magic bytes 检测
                }

        return {}  # 返回空字典而不是抛异常，保持与其他客户端一致
    
    def get_song_info(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲详情（官方优先 + 多源降级）

        策略（参考 musicdl）：始终尝试官方 → 多个 3rd party
        官方 /api/song/detail 不需要 cookie 也能拿到完整信息
        """
        # 线路1: 官方 API（不带 cookie 也能用）
        try:
            url = APIConstants.SONG_DETAIL_API
            params = {'ids': f'[{song_id}]'}
            data = self._get(url, params=params)
            if data and data.get('songs') and len(data['songs']) > 0:
                song = data['songs'][0]
                artists = song.get('artists', song.get('ar', []))
                album_info = song.get('album', song.get('al', {}))
                pq = _extract_pay_and_quality(song)
                return {
                    'id': song.get('id', 0),
                    'name': song.get('name', ''),
                    'artists': '/'.join([a['name'] for a in artists]),
                    'album': album_info.get('name', ''),
                    'picUrl': album_info.get('picUrl', ''),
                    'duration': song.get('duration') or song.get('dt') or 0,
                    'source': 'netease',
                    'api_source': 'official',
                    **pq,
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 官方API获取歌曲信息失败: {e}")

        # 线路2: xuanluoge
        try:
            url = f"{APIConstants.XUANLUOGE_URL}?miss=getMusicInfo&id={song_id}"
            data = self._get(url)
            if data and data.get('id'):
                return {
                    'id': data.get('id', 0),
                    'name': data.get('name', ''),
                    'artists': data.get('artists', ''),
                    'album': data.get('album', ''),
                    'picUrl': data.get('picUrl', ''),
                    'duration': data.get('duration', 0),
                    'source': 'netease',
                    'api_source': 'xuanluoge'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] xuanluoge获取歌曲信息失败: {e}")

        # 线路3: gdstudio (musicdl 验证可用)
        try:
            url = f"https://music-api.gdstudio.xyz/api.php?types=info&id={song_id}&source=netease"
            data = self._get(url, timeout=15)
            if isinstance(data, dict) and data.get('id'):
                artists_raw = data.get('artist', [])
                if isinstance(artists_raw, list):
                    artists = '/'.join(a for a in artists_raw if a)
                else:
                    artists = str(artists_raw or '')
                return {
                    'id': int(data.get('id', song_id)),
                    'name': data.get('name', ''),
                    'artists': artists,
                    'album': data.get('album', ''),
                    'picUrl': '',
                    'duration': 0,
                    'source': 'netease',
                    'api_source': 'gdstudio',
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] gdstudio获取歌曲信息失败: {e}")

        # 线路4: haitangw（兜底）
        try:
            url = f"{APIConstants.HAITANGW_URL}?id={song_id}&type=json"
            data = self._get(url)
            if isinstance(data, dict) and data.get('data'):
                song_info = data['data']
                return {
                    'id': song_info.get('id', 0),
                    'name': song_info.get('name', ''),
                    'artists': song_info.get('artists', ''),
                    'album': song_info.get('album', ''),
                    'picUrl': song_info.get('pic', ''),
                    'duration': song_info.get('duration', 0),
                    'source': 'netease',
                    'api_source': 'haitangw'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] haitangw获取歌曲信息失败: {e}")

        logger.error(f"[{self.platform_name}] 获取歌曲信息失败: 所有API源均无法获取")
        return {}
    
    def get_lyric(self, song_id: int) -> str:
        """获取歌词"""
        url = APIConstants.LYRIC_API
        params = {
            'id': song_id,
            'lv': -1,
            'tv': -1
        }
        
        try:
            data = self._get(url, params=params)
            lrc = data.get('lrc', {}).get('lyric', '')
            return lrc
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌词失败: {e}")
            return ''
    
    def get_playlist(self, playlist_id: int, limit: int = 500) -> Dict[str, Any]:
        """获取歌单（官方API优先，两条备用线路）"""
        # 线路1: 官方API
        url = APIConstants.PLAYLIST_DETAIL_API
        params = {'id': playlist_id, 'n': limit if limit > 0 else 500}
        
        try:
            data = self._get(url, params=params)
            if data.get('code') == 200:
                playlist_info = data.get('playlist', data)
                tracks = []
                for track in playlist_info.get('tracks', []):
                    pq = _extract_pay_and_quality(track)
                    tracks.append({
                        'id': track.get('id', 0),
                        'name': track.get('name', ''),
                        'artists': '/'.join([a['name'] for a in track.get('ar', [])]),
                        'album': track.get('al', {}).get('name', ''),
                        'picUrl': track.get('al', {}).get('picUrl', ''),
                        'source': 'netease',
                        **pq,
                    })
                return {
                    'id': playlist_info.get('id', 0),
                    'name': playlist_info.get('name', ''),
                    'coverImgUrl': playlist_info.get('coverImgUrl') or playlist_info.get('picUrl') or '',
                    'description': playlist_info.get('description') or '',
                    'trackCount': playlist_info.get('trackCount', len(tracks)),
                    'playCount': playlist_info.get('playCount') or 0,
                    'tracks': tracks,
                    'source': 'netease',
                    'api_source': 'official'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 官方API获取歌单失败: {e}")
        
        # 线路2: xuanluoge
        try:
            url = f"{APIConstants.XUANLUOGE_URL}?miss=getPlaylistInfo&id={playlist_id}"
            data = self._get(url)
            if data:
                tracks = []
                for track in data.get('tracks', []):
                    tracks.append({
                        'id': track.get('id', 0),
                        'name': track.get('name', ''),
                        'artists': track.get('artists', ''),
                        'album': track.get('album', ''),
                        'picUrl': track.get('picUrl', ''),
                        'source': 'netease'
                    })
                return {
                    'id': data.get('id', 0),
                    'name': data.get('name', ''),
                    'coverImgUrl': data.get('coverImgUrl', ''),
                    'description': data.get('description', ''),
                    'trackCount': data.get('trackCount', len(tracks)),
                    'playCount': data.get('playCount', 0),
                    'tracks': tracks,
                    'source': 'netease',
                    'api_source': 'xuanluoge'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] xuanluoge获取歌单失败: {e}")
        
        # 线路3: haitangw
        try:
            url = f"{APIConstants.HAITANGW_URL}?id={playlist_id}&type=playlist"
            data = self._get(url)
            if data.get('data'):
                playlist_info = data['data']
                tracks = []
                for track in playlist_info.get('tracks', []):
                    tracks.append({
                        'id': track.get('id', 0),
                        'name': track.get('name', ''),
                        'artists': track.get('artists', ''),
                        'album': track.get('album', ''),
                        'picUrl': track.get('picUrl', ''),
                        'source': 'netease'
                    })
                return {
                    'id': playlist_info.get('id', 0),
                    'name': playlist_info.get('name', ''),
                    'coverImgUrl': playlist_info.get('coverImgUrl', ''),
                    'description': playlist_info.get('description', ''),
                    'trackCount': playlist_info.get('trackCount', len(tracks)),
                    'playCount': playlist_info.get('playCount', 0),
                    'tracks': tracks,
                    'source': 'netease',
                    'api_source': 'haitangw'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] haitangw获取歌单失败: {e}")
        
        logger.error(f"[{self.platform_name}] 获取歌单失败: 所有API源均无法获取")
        return {}


netease_client = NeteaseClient()