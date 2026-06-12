"""波点音乐客户端

继承自 BaseMusicClient，实现波点音乐平台的具体逻辑。
"""

import logging
from typing import Dict, List, Any

from .base_client import BaseMusicClient

logger = logging.getLogger(__name__)


class BodianClient(BaseMusicClient):
    """波点音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "波点音乐"
        self.platform_id = "bodian"
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.bodianmusic.com/'
        })
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        try:
            url = "https://www.bodianmusic.com/api/search"
            params = {
                'keyword': keyword,
                'page': offset // limit + 1,
                'limit': limit,
                'type': 'song'
            }
            
            data = self._get(url, params=params)
            
            songs = []
            if isinstance(data, dict):
                for item in data.get('data', {}).get('list', []):
                    songs.append({
                        'id': item.get('id', ''),
                        'name': item.get('name', ''),
                        'artists': item.get('artist', ''),
                        'album': item.get('album', ''),
                        'picUrl': item.get('cover', ''),
                        'artist_string': item.get('artist', ''),
                        'source': 'bodian'
                    })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        try:
            url = "https://www.bodianmusic.com/api/search"
            params = {
                'keyword': keyword,
                'page': 1,
                'limit': limit,
                'type': 'playlist'
            }
            
            data = self._get(url, params=params)
            playlists = []
            if isinstance(data, dict):
                for item in data.get('data', {}).get('list', []):
                    playlists.append({
                        'id': item.get('id', 0),
                        'name': item.get('name', ''),
                        'coverImgUrl': item.get('cover', ''),
                        'description': item.get('desc', ''),
                        'trackCount': item.get('songCount', 0),
                        'playCount': item.get('playCount', 0),
                        'source': 'bodian'
                    })
            return playlists
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索歌单失败: {e}")
            return []
    
    def get_song_url(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        try:
            url = f"https://www.bodianmusic.com/api/song/url?id={song_id}"
            
            data = self._get(url)
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
        try:
            url = f"https://www.bodianmusic.com/api/song/detail?id={song_id}"
            
            data = self._get(url)
            song_info = data.get('data', {})
            
            return {
                'id': song_info.get('id', ''),
                'name': song_info.get('name', ''),
                'artists': song_info.get('artist', ''),
                'album': song_info.get('album', ''),
                'picUrl': song_info.get('cover', ''),
                'duration': song_info.get('duration', 0) * 1000,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌曲信息失败: {e}")
            return {}
    
    def get_lyric(self, song_id: str) -> str:
        """获取歌词"""
        try:
            url = f"https://www.bodianmusic.com/api/song/lyric?id={song_id}"
            
            data = self._get(url)
            return data.get('data', {}).get('lyric', '')
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌词失败: {e}")
            return ''
    
    def get_playlist(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单"""
        try:
            url = f"https://www.bodianmusic.com/api/playlist/detail?id={playlist_id}"
            
            data = self._get(url)
            playlist_info = data.get('data', {})
            
            tracks = []
            for item in playlist_info.get('songs', []):
                tracks.append({
                    'id': item.get('id', ''),
                    'name': item.get('name', ''),
                    'artists': item.get('artist', ''),
                    'album': item.get('album', ''),
                    'picUrl': item.get('cover', ''),
                    'source': 'bodian'
                })
            
            return {
                'id': playlist_info.get('id', 0),
                'name': playlist_info.get('name', ''),
                'coverImgUrl': playlist_info.get('cover', ''),
                'description': playlist_info.get('desc', ''),
                'trackCount': len(tracks),
                'playCount': playlist_info.get('playCount', 0),
                'tracks': tracks,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌单失败: {e}")
            return {}


bodian_client = BodianClient()