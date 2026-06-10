"""波点音乐API模块

参考musicdl项目的波点音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/bodian.py

支持搜索歌曲、获取歌曲URL、歌单和专辑信息。
"""

import json
import urllib.parse
import logging
from typing import Dict, List, Optional, Any

import requests

# 数据结构标准化辅助函数
def _normalize_artist(item: Dict[str, Any]) -> Dict[str, Any]:
    """标准化单个歌手数据"""
    return {
        'id': item.get('id', 0),
        'name': item.get('name', ''),
        'avatarUrl': item.get('avatarUrl') or item.get('picUrl') or '',
        'picUrl': item.get('picUrl') or item.get('avatarUrl') or '',
        'musicCount': item.get('musicCount') or item.get('songCount') or 0,
        'songCount': item.get('songCount') or item.get('musicCount') or 0,
        'albumCount': item.get('albumCount') or 0,
        'fansCount': item.get('fansCount') or 0,
        'desc': item.get('desc') or item.get('description') or '',
        'alias': item.get('alias') or []
    }

def _normalize_album(item: Dict[str, Any]) -> Dict[str, Any]:
    """标准化单个专辑数据"""
    artist_data = item.get('artist', {})
    return {
        'id': item.get('id', 0),
        'name': item.get('name', ''),
        'picUrl': item.get('picUrl') or item.get('coverImgUrl') or '',
        'coverImgUrl': item.get('coverImgUrl') or item.get('picUrl') or '',
        'artist': {
            'id': artist_data.get('id') or artist_data.get('userId') or 0,
            'name': artist_data.get('name') or artist_data.get('nickname') or ''
        },
        'artistName': item.get('artistName') or artist_data.get('name') or '',
        'publishTime': item.get('publishTime') or 0,
        'size': item.get('size') or 0,
        'trackCount': item.get('trackCount') or item.get('size') or 0
    }

def _normalize_playlist(item: Dict[str, Any]) -> Dict[str, Any]:
    """标准化单个歌单数据"""
    creator_data = item.get('creator', {})
    return {
        'id': item.get('id', 0),
        'name': item.get('name', ''),
        'coverImgUrl': item.get('coverImgUrl') or item.get('picUrl') or '',
        'description': item.get('description') or '',
        'trackCount': item.get('trackCount') or item.get('size') or 0,
        'playCount': item.get('playCount') or 0,
        'creator': {
            'id': creator_data.get('id') or creator_data.get('userId') or 0,
            'name': creator_data.get('name') or creator_data.get('nickname') or '',
            'nickname': creator_data.get('nickname') or creator_data.get('name') or ''
        },
        'tracks': item.get('tracks') or []
    }

def _normalize_track(item: Dict[str, Any]) -> Dict[str, Any]:
    """标准化单个歌曲数据"""
    artists = item.get('artists') or item.get('artist') or []
    if isinstance(artists, list):
        artist_names = [a.get('name', '') for a in artists]
        artist_str = '/'.join(filter(None, artist_names))
    elif isinstance(artists, dict):
        artist_str = artists.get('name', '')
    else:
        artist_str = str(artists) if artists else ''
    
    album_data = item.get('album') or {}
    
    return {
        'id': item.get('id', 0),
        'name': item.get('name', '') or item.get('title', ''),
        'artists': artist_str or '',
        'artist': artist_str or '',
        'album': album_data.get('name', '') or item.get('album') or '',
        'picUrl': album_data.get('cover') or album_data.get('picUrl') or item.get('picUrl') or '',
        'coverImgUrl': album_data.get('cover') or album_data.get('picUrl') or item.get('coverImgUrl') or '',
        'duration': item.get('duration') or item.get('durationMs') or 0,
        'url': item.get('url') or '',
        'lrc': item.get('lrc') or ''
    }

# 配置日志
logger = logging.getLogger(__name__)


class QualityLevel:
    """音质等级枚举"""
    STANDARD = "standard"      # 标准音质
    EXHIGH = "exhigh"          # 极高音质
    LOSSLESS = "lossless"      # 无损音质


class BodianAPIClient:
    """波点音乐API客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://www.bodianmusic.com/'
        })
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        url = "https://www.bodianmusic.com/api/search"
        params = {
            'keyword': keyword,
            'type': 'track',
            'offset': offset,
            'limit': limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            songs = []
            for item in data.get('data', {}).get('tracks', []):
                artist_info = item.get('artist', {})
                album_info = item.get('album', {})
                
                songs.append({
                    'id': item.get('id', 0),
                    'name': item.get('title', ''),
                    'artists': artist_info.get('name', ''),
                    'album': album_info.get('name', ''),
                    'picUrl': album_info.get('cover', ''),
                    'artist_string': artist_info.get('name', ''),
                    'source': 'bodian'
                })
            return songs
        except Exception as e:
            logger.error(f"波点音乐搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        url = "https://www.bodianmusic.com/api/search"
        params = {
            'keyword': keyword,
            'type': 'playlist',
            'offset': 0,
            'limit': limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            playlists = []
            for item in data.get('data', {}).get('playlists', []):
                playlists.append({
                    'id': item.get('id', 0),
                    'name': item.get('title', ''),
                    'coverImgUrl': item.get('cover', ''),
                    'description': item.get('description', ''),
                    'trackCount': item.get('trackCount', 0),
                    'playCount': item.get('playCount', 0),
                    'creator': {
                        'id': item.get('creator', {}).get('id', 0),
                        'name': item.get('creator', {}).get('name', ''),
                        'nickname': item.get('creator', {}).get('name', '')
                    },
                    'source': 'bodian'
                })
            return playlists
        except Exception as e:
            logger.error(f"波点音乐搜索歌单失败: {e}")
            return []
    
    def search_album(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索专辑"""
        url = "https://www.bodianmusic.com/api/search"
        params = {
            'keyword': keyword,
            'type': 'album',
            'offset': 0,
            'limit': limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            albums = []
            for item in data.get('data', {}).get('albums', []):
                albums.append({
                    'id': item.get('id', 0),
                    'name': item.get('title', ''),
                    'picUrl': item.get('cover', ''),
                    'coverImgUrl': item.get('cover', ''),
                    'artist': {
                        'id': item.get('artist', {}).get('id', 0),
                        'name': item.get('artist', {}).get('name', '')
                    },
                    'artistName': item.get('artist', {}).get('name', ''),
                    'trackCount': item.get('trackCount', 0),
                    'source': 'bodian'
                })
            return albums
        except Exception as e:
            logger.error(f"波点音乐搜索专辑失败: {e}")
            return []
    
    def get_song_url(self, song_id: int, quality: str = 'lossless', data_source: str = 'official') -> Dict[str, Any]:
        """获取歌曲下载链接"""
        try:
            url = f"https://www.bodianmusic.com/api/track/{song_id}/playUrl"
            params = {
                'quality': quality
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('success') and data.get('data'):
                return {
                    'success': True,
                    'url': data.get('data', ''),
                    'quality': quality,
                    'source': 'bodian'
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', '无法获取歌曲URL')
                }
        except Exception as e:
            logger.error(f"波点音乐获取歌曲URL失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_song_detail(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲详情"""
        url = f"https://www.bodianmusic.com/api/track/{song_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            track_info = data.get('data', {})
            artist_info = track_info.get('artist', {})
            album_info = track_info.get('album', {})
            
            return {
                'id': track_info.get('id', 0),
                'name': track_info.get('title', ''),
                'artists': artist_info.get('name', ''),
                'artist': artist_info.get('name', ''),
                'album': album_info.get('name', ''),
                'picUrl': album_info.get('cover', ''),
                'coverImgUrl': album_info.get('cover', ''),
                'duration': track_info.get('duration', 0),
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"波点音乐获取歌曲详情失败: {e}")
            return {}
    
    def get_lyric(self, song_id: int) -> Dict[str, Any]:
        """获取歌词"""
        url = f"https://www.bodianmusic.com/api/track/{song_id}/lyric"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'lrc': data.get('data', {}).get('lyric', '')
            }
        except Exception as e:
            logger.error(f"波点音乐获取歌词失败: {e}")
            return {'lrc': ''}
    
    def get_playlist_detail(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单详情"""
        url = f"https://www.bodianmusic.com/api/playlist/{playlist_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            playlist_info = data.get('data', {})
            tracks = []
            
            for item in playlist_info.get('tracks', []):
                artist_info = item.get('artist', {})
                album_info = item.get('album', {})
                tracks.append({
                    'id': item.get('id', 0),
                    'name': item.get('title', ''),
                    'artists': artist_info.get('name', ''),
                    'artist': artist_info.get('name', ''),
                    'album': album_info.get('name', ''),
                    'picUrl': album_info.get('cover', ''),
                    'duration': item.get('duration', 0),
                    'source': 'bodian'
                })
            
            return {
                'id': playlist_info.get('id', 0),
                'name': playlist_info.get('title', ''),
                'coverImgUrl': playlist_info.get('cover', ''),
                'description': playlist_info.get('description', ''),
                'trackCount': playlist_info.get('trackCount', 0),
                'playCount': playlist_info.get('playCount', 0),
                'creator': {
                    'id': playlist_info.get('creator', {}).get('id', 0),
                    'name': playlist_info.get('creator', {}).get('name', '')
                },
                'tracks': tracks,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"波点音乐获取歌单详情失败: {e}")
            return {}
    
    def get_album_detail(self, album_id: int) -> Dict[str, Any]:
        """获取专辑详情"""
        url = f"https://www.bodianmusic.com/api/album/{album_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            album_info = data.get('data', {})
            tracks = []
            
            for item in album_info.get('tracks', []):
                artist_info = item.get('artist', {})
                tracks.append({
                    'id': item.get('id', 0),
                    'name': item.get('title', ''),
                    'artists': artist_info.get('name', ''),
                    'artist': artist_info.get('name', ''),
                    'album': album_info.get('title', ''),
                    'picUrl': album_info.get('cover', ''),
                    'duration': item.get('duration', 0),
                    'source': 'bodian'
                })
            
            return {
                'id': album_info.get('id', 0),
                'name': album_info.get('title', ''),
                'picUrl': album_info.get('cover', ''),
                'coverImgUrl': album_info.get('cover', ''),
                'artist': {
                    'id': album_info.get('artist', {}).get('id', 0),
                    'name': album_info.get('artist', {}).get('name', '')
                },
                'artistName': album_info.get('artist', {}).get('name', ''),
                'trackCount': album_info.get('trackCount', 0),
                'tracks': tracks,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"波点音乐获取专辑详情失败: {e}")
            return {}
    
    @staticmethod
    def get_available_sources() -> List[Dict[str, str]]:
        """获取可用数据源列表"""
        return [
            {'value': 'official', 'label': '官方API', 'description': '直接调用波点音乐官方API'}
        ]


# 创建全局波点音乐API客户端实例
bodian_client = BodianAPIClient()
