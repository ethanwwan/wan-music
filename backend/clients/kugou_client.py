"""酷狗音乐客户端

继承自 BaseMusicClient，实现酷狗音乐平台的具体逻辑。

参考 musicdl 的酷狗音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kugou.py
"""

import logging
import hashlib
import json
from typing import Dict, List, Optional, Any

from .base_client import BaseMusicClient

logger = logging.getLogger(__name__)


class KugouClient(BaseMusicClient):
    """酷狗音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "酷狗音乐"
        self.platform_id = "kugou"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        })
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        from urllib.parse import urlencode
        
        params = {
            'format': 'json',
            'keyword': keyword,
            'platform': 'WebFilter',
            'page': offset // limit + 1,
            'pagesize': limit
        }
        
        url = "https://songsearch.kugou.com/song_search_v2?" + urlencode(params)
        
        try:
            data = self._get(url)
            
            songs = []
            for item in data.get('data', {}).get('lists', []):
                pic_url = item.get('Image', '').replace('{size}', '400')
                songs.append({
                    'id': item.get('FileHash', ''),
                    'name': item.get('SongName', ''),
                    'artists': item.get('SingerName', ''),
                    'album': item.get('AlbumName', ''),
                    'picUrl': pic_url,
                    'artist_string': item.get('SingerName', ''),
                    'source': 'kugou'
                })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        from urllib.parse import urlencode
        
        params = {
            'format': 'json',
            'keyword': keyword,
            'platform': 'WebFilter',
            'page': 1,
            'pagesize': limit,
            'type': 'playlist'
        }
        
        url = "https://songsearch.kugou.com/song_search_v2?" + urlencode(params)
        
        try:
            data = self._get(url)
            playlists = []
            for item in data.get('data', {}).get('lists', []):
                playlists.append({
                    'id': item.get('specialid', 0) or item.get('ID', 0),
                    'name': item.get('specialname', '') or item.get('SongName', ''),
                    'coverImgUrl': item.get('cover', '') or item.get('Image', '').replace('{size}', '400'),
                    'description': item.get('intro', '') or '',
                    'trackCount': item.get('songcount', 0) or 0,
                    'playCount': item.get('playcount', 0) or item.get('play_count', 0),
                    'source': 'kugou'
                })
            return playlists
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索歌单失败: {e}")
            return []
    
    def get_song_url(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        url = f"https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash={song_id}&mid=1"
        
        try:
            data = self._get(url)
            
            if isinstance(data, dict) and data.get('data'):
                song_info = data['data']
                play_url = song_info.get('play_url') or song_info.get('url')
                if play_url and play_url.startswith('http'):
                    return {
                        'url': play_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'kugou'
                    }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 获取歌曲URL失败: {url}, 错误: {e}")
        
        logger.error(f"[{self.platform_name}] 获取歌曲URL失败")
        return {}
    
    def get_song_info(self, song_id: str) -> Dict[str, Any]:
        """获取歌曲信息"""
        url = f"https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash={song_id}&mid=1"
        
        try:
            data = self._get(url)
            
            if isinstance(data, dict) and data.get('data'):
                song_info = data['data']
                return {
                    'id': song_info.get('hash', ''),
                    'name': song_info.get('song_name', ''),
                    'artists': song_info.get('singer_name', ''),
                    'album': song_info.get('album_name', ''),
                    'picUrl': song_info.get('img', ''),
                    'duration': song_info.get('timelength', 0),
                    'source': 'kugou'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 获取歌曲信息失败: {url}, 错误: {e}")
        
        logger.error(f"[{self.platform_name}] 获取歌曲信息失败")
        return {}
    
    def get_lyric(self, song_id: str) -> str:
        """获取歌词"""
        url = f"https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash={song_id}&mid=1"
        
        try:
            data = self._get(url)
            
            if isinstance(data, dict) and data.get('data'):
                return data['data'].get('lyrics', '') or data['data'].get('lyric', '')
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 获取歌词失败: {url}, 错误: {e}")
        
        logger.error(f"[{self.platform_name}] 获取歌词失败")
        return ''
    
    def get_playlist(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单"""
        url = f"https://wwwapi.kugou.com/yy/index.php?r=play/get_special&specialid={playlist_id}"
        
        try:
            data = self._get(url)
            
            if isinstance(data, dict) and data.get('data'):
                playlist_info = data['data']
                tracks = []
                for item in playlist_info.get('list', []):
                    tracks.append({
                        'id': item.get('hash', ''),
                        'name': item.get('songname', ''),
                        'artists': item.get('singername', ''),
                        'album': item.get('albumname', ''),
                        'picUrl': item.get('img', ''),
                        'source': 'kugou'
                    })
                
                return {
                    'id': playlist_info.get('specialid', 0),
                    'name': playlist_info.get('specialname', ''),
                    'coverImgUrl': playlist_info.get('cover', ''),
                    'description': playlist_info.get('intro', ''),
                    'trackCount': len(tracks),
                    'playCount': playlist_info.get('playcount', 0),
                    'tracks': tracks,
                    'source': 'kugou'
                }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌单失败: {e}")
        
        return {}


kugou_client = KugouClient()
