"""波点音乐客户端

继承自 BaseMusicClient，实现波点音乐平台的具体逻辑。

参考 musicdl 的波点音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/bodian.py
"""

import logging
import uuid
import hashlib
from typing import Dict, List, Optional, Any

from .base_client import BaseMusicClient

logger = logging.getLogger(__name__)


class BodianClient(BaseMusicClient):
    """波点音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "波点音乐"
        self.platform_id = "bodian"
        
        self.dev_id = hashlib.md5(uuid.uuid4().bytes).hexdigest()
        
        self.session.headers.update({
            'user-agent': 'Dart/3.3 (dart:io)',
            'plat': 'win',
            'accept-encoding': 'gzip',
            'api-ver': 'application/json',
            'channel': 'W1',
            'brand': 'Windows 11 Pro for Workstations',
            'net': 'wifi',
            'content-type': 'application/json',
            'ver': '1.1.5',
            'svrver': '13',
            'devid': self.dev_id,
            'qimei36': self.dev_id
        })
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        url = "https://bd-api.kuwo.cn/api/search/searchMusic"
        params = {
            'key': keyword,
            'pn': offset // limit + 1,
            'rn': limit,
            'devId': self.dev_id
        }
        
        try:
            data = self._get(url, params=params)
            
            songs = []
            for item in data.get('data', {}).get('resultList', []):
                songs.append({
                    'id': item.get('rid', ''),
                    'name': item.get('name', ''),
                    'artists': item.get('artist', ''),
                    'album': item.get('album', ''),
                    'picUrl': item.get('pic', ''),
                    'artist_string': item.get('artist', ''),
                    'source': 'bodian'
                })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        url = "https://bd-api.kuwo.cn/api/search/searchAlbum"
        params = {
            'key': keyword,
            'pn': 1,
            'rn': limit,
            'devId': self.dev_id
        }
        
        try:
            data = self._get(url, params=params)
            playlists = []
            for item in data.get('data', {}).get('resultList', []):
                playlists.append({
                    'id': item.get('id', 0),
                    'name': item.get('name', ''),
                    'coverImgUrl': item.get('pic', ''),
                    'description': item.get('desc', ''),
                    'trackCount': item.get('songNum', 0),
                    'playCount': item.get('playNum', 0),
                    'source': 'bodian'
                })
            return playlists
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索歌单失败: {e}")
            return []
    
    def get_song_url(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        url = "https://bd-api.kuwo.cn/api/music/getMusicUrl"
        params = {
            'rid': song_id,
            'type': 'music',
            'devId': self.dev_id
        }
        
        try:
            data = self._get(url, params=params)
            
            download_url = data.get('data', {}).get('url', '')
            if download_url and download_url.startswith('http'):
                return {
                    'url': download_url,
                    'quality': quality,
                    'song_id': song_id,
                    'source': 'bodian'
                }
            return {}
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌曲URL失败: {e}")
            return {}
    
    def get_song_info(self, song_id: str) -> Dict[str, Any]:
        """获取歌曲信息"""
        url = "https://bd-api.kuwo.cn/api/music/getMusicInfo"
        params = {
            'rid': song_id,
            'devId': self.dev_id
        }
        
        try:
            data = self._get(url, params=params)
            song_info = data.get('data', {})
            
            return {
                'id': song_info.get('rid', ''),
                'name': song_info.get('name', ''),
                'artists': song_info.get('artist', ''),
                'album': song_info.get('album', ''),
                'picUrl': song_info.get('pic', ''),
                'duration': song_info.get('duration', 0) * 1000,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌曲信息失败: {e}")
            return {}
    
    def get_lyric(self, song_id: str) -> str:
        """获取歌词"""
        url = "https://bd-api.kuwo.cn/api/music/getLyric"
        params = {
            'rid': song_id,
            'devId': self.dev_id
        }
        
        try:
            data = self._get(url, params=params)
            return data.get('data', {}).get('lyric', '')
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌词失败: {e}")
            return ''
    
    def get_playlist(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单"""
        url = "https://bd-api.kuwo.cn/api/album/getAlbumInfo"
        params = {
            'id': playlist_id,
            'devId': self.dev_id
        }
        
        try:
            data = self._get(url, params=params)
            album_info = data.get('data', {})
            
            tracks = []
            for item in album_info.get('songList', []):
                tracks.append({
                    'id': item.get('rid', ''),
                    'name': item.get('name', ''),
                    'artists': item.get('artist', ''),
                    'album': item.get('album', ''),
                    'picUrl': item.get('pic', ''),
                    'source': 'bodian'
                })
            
            return {
                'id': album_info.get('id', 0),
                'name': album_info.get('name', ''),
                'coverImgUrl': album_info.get('pic', ''),
                'description': album_info.get('desc', ''),
                'trackCount': len(tracks),
                'playCount': album_info.get('playNum', 0),
                'tracks': tracks,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌单失败: {e}")
            return {}


bodian_client = BodianClient()