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
from hashlib import md5
from enum import Enum

from .base_client import BaseMusicClient
from .quality_config import QualityLevel

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

logger = logging.getLogger(__name__)


class NeteaseAPISource(Enum):
    """网易云API源枚举"""
    OFFICIAL = "official"
    XUANLUOGE = "xuanluoge"
    HAITANGW = "haitangw"


class APIConstants:
    """API相关常量"""
    AES_KEY = b"e82ckenh8dichen8"
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154'
    REFERER = 'https://music.163.com/'
    
    SONG_URL_V1 = "https://interface3.music.163.com/eapi/song/enhance/player/url/v1"
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
    
    COOKIE_FILE_PATH = "netease_cookie.txt"


class CryptoUtils:
    """加密工具类"""
    
    @staticmethod
    def hex_digest(data: bytes) -> str:
        return "".join([hex(d)[2:].zfill(2) for d in data])
    
    @staticmethod
    def hash_digest(text: str) -> bytes:
        return md5(text.encode("utf-8")).digest()
    
    @staticmethod
    def hash_hex_digest(text: str) -> str:
        return CryptoUtils.hex_digest(CryptoUtils.hash_digest(text))
    
    @staticmethod
    def encrypt_params(url: str, payload: Dict[str, Any]) -> str:
        url_path = urllib.parse.urlparse(url).path.replace("/eapi/", "/api/")
        digest = CryptoUtils.hash_hex_digest(f"nobody{url_path}use{json.dumps(payload)}md5forencrypt")
        params = f"{url_path}-36cd479b6b5-{json.dumps(payload)}-36cd479b6b5-{digest}"
        
        padder = padding.PKCS7(algorithms.AES(APIConstants.AES_KEY).block_size).padder()
        padded_data = padder.update(params.encode()) + padder.finalize()
        cipher = Cipher(algorithms.AES(APIConstants.AES_KEY), modes.ECB())
        encryptor = cipher.encryptor()
        enc = encryptor.update(padded_data) + encryptor.finalize()
        
        return CryptoUtils.hex_digest(enc)


class NeteaseClient(BaseMusicClient):
    """网易云音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "网易云音乐"
        self.platform_id = "netease"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/'
        })
        self.session.cookies.update(APIConstants.DEFAULT_COOKIES)
        self._load_local_cookies()
    
    def _load_local_cookies(self):
        """加载本地cookie文件"""
        import os
        cookie_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), APIConstants.COOKIE_FILE_PATH)
        if os.path.exists(cookie_path):
            try:
                with open(cookie_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    cookie_count = 0
                    for line in lines:
                        line = line.strip()
                        # 跳过注释行和空行
                        if not line or line.startswith('#'):
                            continue
                        # 解析cookie对
                        for cookie_pair in line.split(';'):
                            cookie_pair = cookie_pair.strip()
                            if '=' in cookie_pair:
                                key, value = cookie_pair.split('=', 1)
                                self.session.cookies.set(key.strip(), value.strip())
                                cookie_count += 1
                    if cookie_count > 0:
                        logger.info(f"[{self.platform_name}] 成功加载本地cookie文件，共 {cookie_count} 个cookie")
                    else:
                        logger.debug(f"[{self.platform_name}] 本地cookie文件为空或只有注释")
            except Exception as e:
                logger.error(f"[{self.platform_name}] 加载本地cookie文件失败: {e}")
        else:
            logger.debug(f"[{self.platform_name}] 本地cookie文件不存在: {cookie_path}")
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        url = APIConstants.SEARCH_API
        params = {
            's': keyword,
            'type': 1,
            'limit': limit,
            'offset': offset
        }
        
        try:
            data = self._get(url, params=params)
            songs = []
            for item in data.get('result', {}).get('songs', []):
                songs.append({
                    'id': item['id'],
                    'name': item['name'],
                    'artists': '/'.join([a['name'] for a in item['ar']]),
                    'album': item['al']['name'],
                    'picUrl': item['al']['picUrl'],
                    'artist_string': '/'.join([a['name'] for a in item['ar']]),
                    'source': 'netease'
                })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}")
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
        """使用官方API获取歌曲URL"""
        try:
            payload = {
                "ids": [song_id],
                "level": quality,
                "encodeType": "flac" if quality in ['lossless', 'hires', 'jymaster'] else "mp3"
            }
            params = CryptoUtils.encrypt_params(APIConstants.SONG_URL_V1, payload)
            
            headers = {
                'User-Agent': APIConstants.USER_AGENT,
                'Referer': APIConstants.REFERER,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(
                APIConstants.SONG_URL_V1,
                data=f"params={params}",
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('data') and len(data['data']) > 0:
                url = data['data'][0].get('url')
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
        """获取歌曲播放/下载URL（自动切换线路）"""
        from .quality_config import is_valid_quality, get_default_quality
        if not is_valid_quality(quality):
            quality = get_default_quality()
        
        source_func_map = {
            'official': self._get_song_url_official,
            'xuanluoge': self._get_song_url_xuanluoge,
            'haitangw': self._get_song_url_haitangw,
            'meting': self._get_song_url_meting
        }
        
        sources_to_try = ['official', 'xuanluoge', 'haitangw', 'meting']
        
        for source in sources_to_try:
            download_url = source_func_map[source](song_id, quality)
            if download_url:
                return {
                    'url': download_url,
                    'quality': quality,
                    'api_source': source,
                    'song_id': song_id,
                    'source': 'netease'
                }
        
        return {}  # 返回空字典而不是抛异常，保持与其他客户端一致
    
    def get_song_info(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲信息（官方API优先，两条备用线路）"""
        # 线路1: 官方API
        url = APIConstants.SONG_DETAIL_API
        params = {'ids': f'[{song_id}]'}
        
        try:
            data = self._get(url, params=params)
            if data.get('songs') and len(data['songs']) > 0:
                song = data['songs'][0]
                # 注意：这里使用 artists 和 album 字段，而不是 ar 和 al
                artists = song.get('artists', song.get('ar', []))
                album_info = song.get('album', song.get('al', {}))
                return {
                    'id': song.get('id', 0),
                    'name': song.get('name', ''),
                    'artists': '/'.join([a['name'] for a in artists]),
                    'album': album_info.get('name', ''),
                    'picUrl': album_info.get('picUrl', ''),
                    'duration': song.get('duration') or song.get('dt') or 0,
                    'source': 'netease',
                    'api_source': 'official'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 官方API获取歌曲信息失败: {e}")
        
        # 线路2: xuanluoge
        try:
            url = f"{APIConstants.XUANLUOGE_URL}?miss=getMusicInfo&id={song_id}"
            data = self._get(url)
            if data:
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
        
        # 线路3: haitangw
        try:
            url = f"{APIConstants.HAITANGW_URL}?id={song_id}&type=json"
            data = self._get(url)
            if data.get('data'):
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
                    tracks.append({
                        'id': track.get('id', 0),
                        'name': track.get('name', ''),
                        'artists': '/'.join([a['name'] for a in track.get('ar', [])]),
                        'album': track.get('al', {}).get('name', ''),
                        'picUrl': track.get('al', {}).get('picUrl', ''),
                        'source': 'netease'
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