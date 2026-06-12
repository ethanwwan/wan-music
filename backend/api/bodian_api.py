"""波点音乐API模块

参考musicdl项目的波点音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/bodian.py

支持搜索歌曲、获取歌曲URL、歌单和专辑信息。
"""

import json
import urllib.parse
import logging
import uuid
import hashlib
from typing import Dict, List, Optional, Any

import requests

from .quality_config import QualityLevel

# 数据结构标准化辅助函数
def _normalize_artist(item: Dict[str, Any]) -> Dict[str, Any]:
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
    artists = item.get('artists') or item.get('artist') or []
    if isinstance(artists, list):
        artist_names = [a.get('name', '') for a in artists]
        artist_str = '/'.join(filter(None, artist_names))
    elif isinstance(artists, dict):
        artist_str = artists.get('name', '')
    else:
        artist_str = str(artists) if artists else ''
    
    album_data = item.get('album', {})
    return {
        'id': item.get('id', 0),
        'name': item.get('name', ''),
        'artists': [_normalize_artist(a) for a in (artists if isinstance(artists, list) else [])],
        'artistsName': artist_str,
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


class BodianAPIClient:
    """波点音乐API客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.session = requests.Session()
        
        # 生成设备ID
        self.dev_id = hashlib.md5(uuid.uuid4().bytes).hexdigest()
        
        # 设置默认请求头（与musicdl一致）
        self.default_headers = {
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
        }
        
        # 设置session的默认headers
        self.session.headers.update(self.default_headers)
        
        # 认证信息
        self.auth_info = {
            'uid': '-1',
            'token': '',
            'dev_id': self.dev_id
        }
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲 - 使用musicdl方式"""
        from urllib.parse import urlencode
        
        params = {
            'pn': offset // limit,
            'rn': limit,
            'keyword': keyword,
            'correct': '1',
            'uid': self.auth_info['uid'],
            'token': self.auth_info['token']
        }
        
        url = "https://bd-api.kuwo.cn/api/search/music/list?" + urlencode(params)
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            songs = []
            for item in data.get('data', {}).get('resultList', []):
                artist_name = item.get('artist', '')
                album_name = item.get('album', '')
                
                songs.append({
                    'id': item.get('id', 0),
                    'name': item.get('name', ''),
                    'artists': artist_name,
                    'album': album_name,
                    'picUrl': item.get('albumPic', ''),
                    'artist_string': artist_name,
                    'source': 'bodian'
                })
            return songs
        except Exception as e:
            logger.error(f"波点音乐搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        from urllib.parse import urlencode
        
        params = {
            'pn': 0,
            'rn': limit,
            'keyword': keyword,
            'uid': self.auth_info['uid'],
            'token': self.auth_info['token']
        }
        
        url = "https://bd-api.kuwo.cn/api/search/playlist?" + urlencode(params)
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            playlists = []
            for item in data.get('data', {}).get('list', []):
                playlists.append({
                    'id': item.get('id', 0),
                    'name': item.get('name', ''),
                    'coverImgUrl': item.get('pic', ''),
                    'description': item.get('intro', ''),
                    'trackCount': item.get('musicCount', 0),
                    'playCount': item.get('playCount', 0),
                    'source': 'bodian'
                })
            return playlists
        except Exception as e:
            logger.error(f"波点音乐歌单搜索失败: {e}")
            return []
    
    def get_song_url(self, song_id: int, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放URL"""
        try:
            url = f"https://bd-api.kuwo.cn/api/play/music/v2/audioUrl?musicId={song_id}&uid={self.auth_info['uid']}&token={self.auth_info['token']}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            audio_url = data.get('data', {}).get('audioHttpsUrl') or data.get('data', {}).get('audioUrl')
            if audio_url:
                return {'url': audio_url, 'quality': quality, 'source': 'bodian'}
            return {}
        except Exception as e:
            logger.error(f"获取波点音乐歌曲URL失败: {e}")
            return {}
    
    def get_playlist_detail(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单详情"""
        url = f"https://bd-api.kuwo.cn/api/playlist/detail?pid={playlist_id}&uid={self.auth_info['uid']}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            playlist_data = data.get('data', {})
            tracks = []
            for item in playlist_data.get('musicList', []):
                tracks.append({
                    'id': item.get('id', 0),
                    'name': item.get('name', ''),
                    'artists': item.get('artist', ''),
                    'album': item.get('album', ''),
                    'picUrl': item.get('albumPic', ''),
                    'source': 'bodian'
                })
            
            return {
                'id': playlist_id,
                'name': playlist_data.get('name', ''),
                'coverImgUrl': playlist_data.get('pic', ''),
                'description': playlist_data.get('intro', ''),
                'trackCount': len(tracks),
                'playCount': playlist_data.get('playCount', 0),
                'tracks': tracks,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"获取波点音乐歌单详情失败: {e}")
            return {}
    
    def get_lyric(self, song_id: int) -> str:
        """获取歌词"""
        url = f"https://bd-api.kuwo.cn/api/lyric?musicId={song_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('lyric', '')
        except Exception as e:
            logger.error(f"获取波点音乐歌词失败: {e}")
            return ''


# 创建全局客户端实例
bodian_client = BodianAPIClient()
