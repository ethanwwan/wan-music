"""QQ音乐API模块

参考musicdl项目的QQ音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py

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
    artists = item.get('artists') or item.get('singer') or []
    if isinstance(artists, list):
        artist_names = [a.get('name', '') for a in artists]
        artist_str = '/'.join(filter(None, artist_names))
    else:
        artist_str = str(artists) if artists else ''
    
    album_data = item.get('album') or item.get('albumInfo') or {}
    
    return {
        'id': item.get('id', 0),
        'name': item.get('name', '') or item.get('songName', ''),
        'artists': artist_str or item.get('artist') or '',
        'artist': artist_str or item.get('artist') or '',
        'album': album_data.get('name', '') or item.get('album') or '',
        'picUrl': album_data.get('picUrl') or album_data.get('cover') or item.get('picUrl') or '',
        'coverImgUrl': album_data.get('cover') or album_data.get('picUrl') or item.get('coverImgUrl') or '',
        'duration': item.get('duration') or item.get('interval') or 0,
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


class QQAPIClient:
    """QQ音乐API客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/'
        })
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params = {
            'ct': '24',
            'qqmusic_ver': '1298',
            'new_json': '1',
            'remoteplace': 'txt.yqq.top',
            'searchid': '6423056225238206',
            't': '0',
            'aggr': '1',
            'cr': '1',
            'catZhida': '1',
            'lossless': '0',
            'flag_qc': '0',
            'p': str(offset // limit + 1),
            'n': str(limit),
            'w': keyword,
            'g_tk_new_20200303': '1320007797',
            'g_tk': '1320007797',
            'loginUin': '0',
            'hostUin': '0',
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'notice': '0',
            'platform': 'yqq.json',
            'needNewCode': '0'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            songs = []
            for item in data.get('data', {}).get('song', {}).get('list', []):
                singer_name = '/'.join([s.get('name', '') for s in item.get('singer', [])])
                album_info = item.get('album', {})
                songs.append({
                    'id': item.get('songid', 0),
                    'name': item.get('songname', ''),
                    'artists': singer_name,
                    'album': album_info.get('name', ''),
                    'picUrl': album_info.get('mid', '') and f"https://y.qq.com/music/photo_new/T002R300x300M000{album_info['mid']}.jpg",
                    'artist_string': singer_name,
                    'source': 'qq'
                })
            return songs
        except Exception as e:
            logger.error(f"QQ音乐搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params = {
            'ct': '24',
            'qqmusic_ver': '1298',
            'new_json': '1',
            'remoteplace': 'txt.yqq.top',
            't': '10',
            'aggr': '1',
            'cr': '1',
            'catZhida': '1',
            'lossless': '0',
            'flag_qc': '0',
            'p': '1',
            'n': str(limit),
            'w': keyword,
            'g_tk_new_20200303': '1320007797',
            'g_tk': '1320007797',
            'loginUin': '0',
            'hostUin': '0',
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'notice': '0',
            'platform': 'yqq.json',
            'needNewCode': '0'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            playlists = []
            for item in data.get('data', {}).get('album', {}).get('list', []):
                playlists.append({
                    'id': item.get('dissid', 0),
                    'name': item.get('dissname', ''),
                    'coverImgUrl': item.get('imgurl', ''),
                    'description': item.get('desc', ''),
                    'trackCount': item.get('songnum', 0),
                    'playCount': item.get('listenum', 0),
                    'creator': {
                        'id': item.get('creator', {}).get('uin', 0),
                        'name': item.get('creator', {}).get('name', ''),
                        'nickname': item.get('creator', {}).get('name', '')
                    },
                    'source': 'qq'
                })
            return playlists
        except Exception as e:
            logger.error(f"QQ音乐搜索歌单失败: {e}")
            return []
    
    def search_album(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索专辑"""
        url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params = {
            'ct': '24',
            'qqmusic_ver': '1298',
            'new_json': '1',
            'remoteplace': 'txt.yqq.top',
            't': '8',
            'aggr': '1',
            'cr': '1',
            'catZhida': '1',
            'lossless': '0',
            'flag_qc': '0',
            'p': '1',
            'n': str(limit),
            'w': keyword,
            'g_tk_new_20200303': '1320007797',
            'g_tk': '1320007797',
            'loginUin': '0',
            'hostUin': '0',
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'notice': '0',
            'platform': 'yqq.json',
            'needNewCode': '0'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            albums = []
            for item in data.get('data', {}).get('album', {}).get('list', []):
                albums.append({
                    'id': item.get('albumid', 0),
                    'name': item.get('albumname', ''),
                    'picUrl': item.get('imgurl', ''),
                    'coverImgUrl': item.get('imgurl', ''),
                    'artist': {
                        'id': item.get('singer', {}).get('id', 0),
                        'name': item.get('singer', {}).get('name', '')
                    },
                    'artistName': item.get('singer', {}).get('name', ''),
                    'trackCount': item.get('songnum', 0),
                    'source': 'qq'
                })
            return albums
        except Exception as e:
            logger.error(f"QQ音乐搜索专辑失败: {e}")
            return []
    
    def get_song_url(self, song_id: int, quality: str = 'lossless', data_source: str = 'official') -> Dict[str, Any]:
        """获取歌曲下载链接"""
        try:
            # 获取歌曲vkey
            url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
            data = {
                'req_0': {
                    'module': 'vkey.GetVkeyServer',
                    'method': 'CgiGetVkey',
                    'param': {
                        'guid': '9476615898',
                        'songmid': [str(song_id)],
                        'songtype': [0],
                        'uin': '0',
                        'loginflag': 1,
                        'platform': '20'
                    }
                },
                'comm': {
                    'uin': '0',
                    'format': 'json',
                    'ct': 24,
                    'cv': 0
                }
            }
            
            response = self.session.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            vkey_info = result.get('req_0', {}).get('data', {})
            vkey = vkey_info.get('midurlinfo', [{}])[0].get('vkey', '')
            purl = vkey_info.get('midurlinfo', [{}])[0].get('purl', '')
            
            if vkey and purl:
                base_url = vkey_info.get('sip', ['https://dl.stream.qqmusic.qq.com/'])[0]
                song_url = f"{base_url}{purl}&vkey={vkey}"
                return {
                    'success': True,
                    'url': song_url,
                    'quality': quality,
                    'source': 'qq'
                }
            else:
                return {
                    'success': False,
                    'message': '无法获取歌曲URL'
                }
        except Exception as e:
            logger.error(f"QQ音乐获取歌曲URL失败: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def get_song_detail(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲详情"""
        url = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
        params = {
            'songmid': song_id,
            'tpl': 'yqq_song_detail',
            'format': 'json'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            song_info = data.get('data', {}).get('track_info', {})
            singer_name = '/'.join([s.get('name', '') for s in song_info.get('singer', [])])
            album_info = song_info.get('album', {})
            
            return {
                'id': song_info.get('id', 0),
                'name': song_info.get('name', ''),
                'artists': singer_name,
                'artist': singer_name,
                'album': album_info.get('name', ''),
                'picUrl': album_info.get('mid', '') and f"https://y.qq.com/music/photo_new/T002R300x300M000{album_info['mid']}.jpg",
                'coverImgUrl': album_info.get('mid', '') and f"https://y.qq.com/music/photo_new/T002R300x300M000{album_info['mid']}.jpg",
                'duration': song_info.get('interval', 0) * 1000,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"QQ音乐获取歌曲详情失败: {e}")
            return {}
    
    def get_lyric(self, song_id: int) -> Dict[str, Any]:
        """获取歌词"""
        url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        params = {
            'songmid': song_id,
            'format': 'json',
            'nobase64': '1'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'lrc': data.get('lyric', '')
            }
        except Exception as e:
            logger.error(f"QQ音乐获取歌词失败: {e}")
            return {'lrc': ''}
    
    def get_playlist_detail(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单详情"""
        url = "https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
        params = {
            'type': '1',
            'json': '1',
            'utf8': '1',
            'onlysong': '0',
            'disstid': playlist_id,
            'format': 'jsonp',
            'callback': 'jsonCallback'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # 处理JSONP响应
            content = response.text
            if content.startswith('jsonCallback(') and content.endswith(')'):
                content = content[13:-1]
            data = json.loads(content)
            
            playlist_info = data.get('cdlist', [{}])[0]
            tracks = []
            
            for item in playlist_info.get('songlist', []):
                singer_name = '/'.join([s.get('name', '') for s in item.get('singer', [])])
                album_info = item.get('album', {})
                tracks.append({
                    'id': item.get('songid', 0),
                    'name': item.get('songname', ''),
                    'artists': singer_name,
                    'artist': singer_name,
                    'album': album_info.get('name', ''),
                    'picUrl': album_info.get('mid', '') and f"https://y.qq.com/music/photo_new/T002R300x300M000{album_info['mid']}.jpg",
                    'duration': item.get('interval', 0) * 1000,
                    'source': 'qq'
                })
            
            return {
                'id': playlist_info.get('dissid', 0),
                'name': playlist_info.get('dissname', ''),
                'coverImgUrl': playlist_info.get('logo', ''),
                'description': playlist_info.get('desc', ''),
                'trackCount': playlist_info.get('songnum', 0),
                'playCount': playlist_info.get('listenum', 0),
                'creator': {
                    'id': playlist_info.get('creator', {}).get('uin', 0),
                    'name': playlist_info.get('creator', {}).get('name', '')
                },
                'tracks': tracks,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"QQ音乐获取歌单详情失败: {e}")
            return {}
    
    def get_album_detail(self, album_id: int) -> Dict[str, Any]:
        """获取专辑详情"""
        url = "https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg"
        params = {
            'albumid': album_id,
            'format': 'json'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            album_info = data.get('data', {})
            tracks = []
            
            for item in album_info.get('list', []):
                singer_name = '/'.join([s.get('name', '') for s in item.get('singer', [])])
                tracks.append({
                    'id': item.get('songid', 0),
                    'name': item.get('songname', ''),
                    'artists': singer_name,
                    'artist': singer_name,
                    'album': album_info.get('albumName', ''),
                    'picUrl': album_info.get('albumPic', ''),
                    'duration': item.get('interval', 0) * 1000,
                    'source': 'qq'
                })
            
            return {
                'id': album_info.get('albumID', 0),
                'name': album_info.get('albumName', ''),
                'picUrl': album_info.get('albumPic', ''),
                'coverImgUrl': album_info.get('albumPic', ''),
                'artist': {
                    'id': album_info.get('singerID', 0),
                    'name': album_info.get('singerName', '')
                },
                'artistName': album_info.get('singerName', ''),
                'trackCount': album_info.get('total', 0),
                'tracks': tracks,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"QQ音乐获取专辑详情失败: {e}")
            return {}
    
    @staticmethod
    def get_available_sources() -> List[Dict[str, str]]:
        """获取可用数据源列表"""
        return [
            {'value': 'official', 'label': '官方API', 'description': '直接调用QQ音乐官方API'}
        ]


# 创建全局QQ音乐API客户端实例
qq_client = QQAPIClient()
