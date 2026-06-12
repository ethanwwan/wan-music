"""QQ音乐客户端

继承自 BaseMusicClient，实现QQ音乐平台的具体逻辑。

参考 musicdl 的QQ音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py
"""

import json
import urllib.parse
import logging
import random
import time
from typing import Dict, List, Optional, Any

from .base_client import BaseMusicClient

logger = logging.getLogger(__name__)


class QQClient(BaseMusicClient):
    """QQ音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "QQ音乐"
        self.platform_id = "qq"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/',
            'Origin': 'https://y.qq.com/'
        })
        self.guid = self._generate_guid()
    
    def _generate_guid(self) -> str:
        """生成guid"""
        return str(random.randint(1000000000, 9999999999))
    
    def _generate_search_id(self) -> str:
        """生成搜索ID"""
        return str(random.randint(1000000000, 9999999999))
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
        
        payload = {
            'req_0': {
                'module': 'music.search.SearchCgiService',
                'method': 'DoSearchForQQMusicMobile',
                'param': {
                    'searchid': self._generate_search_id(),
                    'query': keyword,
                    'search_type': 0,
                    'num_per_page': limit,
                    'page_num': offset // limit + 1,
                    'highlight': 1,
                    'grp': 1
                }
            },
            'comm': {
                'format': 'json',
                'ct': '19',
                'cv': '1900'
            }
        }
        
        try:
            data = self._post(url, data=json.dumps(payload, ensure_ascii=False))
            
            if isinstance(data, dict) and data.get('req_0') and data['req_0'].get('data'):
                song_list = data['req_0']['data'].get('song', {}).get('list', [])
                songs = []
                for item in song_list:
                    singer_name = '/'.join([s.get('name', '') for s in item.get('singer', [])])
                    album_name = item.get('album', {}).get('name', '')
                    pic_url = item.get('album', {}).get('mid', '')
                    if pic_url:
                        pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{pic_url}.jpg?max_age=2592000"
                    
                    songs.append({
                        'id': item.get('mid', ''),
                        'name': item.get('name', ''),
                        'artists': singer_name,
                        'album': album_name,
                        'picUrl': pic_url,
                        'artist_string': singer_name,
                        'source': 'qq'
                    })
                return songs
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 搜索失败: {url}, 错误: {e}")
        
        return self._search_fallback(keyword, limit, offset)
    
    def _search_fallback(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """备用搜索方式"""
        url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?ct=24&qqmusic_ver=1298&new_json=1&remoteplace=txt.yqq.song&t=0&aggr=1&cr=1&catZhida=1&lossless=0&flag_qc=0&p={offset // limit + 1}&n={limit}&w={urllib.parse.quote(keyword)}&format=json"
        
        try:
            data = self._get(url)
            
            if isinstance(data, dict) and data.get('data') and data['data'].get('song', {}).get('list'):
                song_list = data['data']['song']['list']
                songs = []
                for item in song_list:
                    singer_name = '/'.join([s.get('name', '') for s in item.get('singer', [])])
                    album_name = item.get('album', {}).get('name', '')
                    pic_url = item.get('album', {}).get('mid', '')
                    if pic_url:
                        pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{pic_url}.jpg?max_age=2592000"
                    
                    songs.append({
                        'id': item.get('mid', ''),
                        'name': item.get('name', ''),
                        'artists': singer_name,
                        'album': album_name,
                        'picUrl': pic_url,
                        'artist_string': singer_name,
                        'source': 'qq'
                    })
                return songs
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 备用搜索失败: {url}, 错误: {e}")
        
        logger.error(f"[{self.platform_name}] 搜索失败")
        return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?ct=24&qqmusic_ver=1298&new_json=1&remoteplace=txt.yqq.playlist&t=2&aggr=1&cr=1&catZhida=1&lossless=0&flag_qc=0&p=1&n={limit}&w={urllib.parse.quote(keyword)}&format=json"
        
        try:
            data = self._get(url)
            
            if isinstance(data, dict) and data.get('data') and data['data'].get('playlist', {}).get('list'):
                playlist_list = data['data']['playlist']['list']
                playlists = []
                for item in playlist_list:
                    playlists.append({
                        'id': item.get('id', 0),
                        'name': item.get('dissname', ''),
                        'coverImgUrl': f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{item.get('logo', '')}.jpg?max_age=2592000",
                        'description': item.get('desc', ''),
                        'trackCount': item.get('songcount', 0),
                        'playCount': item.get('playcount', 0),
                        'source': 'qq'
                    })
                return playlists
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 搜索歌单失败: {url}, 错误: {e}")
        
        logger.error(f"[{self.platform_name}] 搜索歌单失败")
        return []
    
    def get_song_url(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        return self._get_song_url_official(song_id, quality)
    
    def _get_song_url_official(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """使用官方API获取歌曲URL（需要vkey）"""
        try:
            filename = f"C400{song_id}.m4a"
            url = "https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg"
            params = {
                'format': 'json',
                'cid': '205361747',
                'uin': '0',
                'songmid': song_id,
                'filename': filename,
                'guid': self.guid
            }
            
            data = self._get(url, params=params)
            items = data.get('data', {}).get('items', [])
            
            if items:
                vkey = items[0].get('vkey', '')
                if vkey:
                    audio_url = f"http://dl.stream.qqmusic.qq.com/{filename}?vkey={vkey}&guid={self.guid}&uin=0&fromtag=66"
                    return {
                        'url': audio_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'qq'
                    }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 官方API获取歌曲URL失败: {e}")
        
        return {}
    
    def get_song_info(self, song_id: str) -> Dict[str, Any]:
        """获取歌曲信息"""
        url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
        payload = {
            'req_0': {
                'module': 'music.pf_song_detail_svr',
                'method': 'get_song_detail',
                'param': {
                    'song_mid': song_id
                }
            },
            'comm': {
                'format': 'json',
                'ct': '19',
                'cv': '1900'
            }
        }
        
        try:
            data = self._post(url, data=json.dumps(payload))
            song_info = data.get('req_0', {}).get('data', {}).get('track_info', {})
            
            singer_name = '/'.join([s['name'] for s in song_info.get('singer', [])])
            album_name = song_info.get('album', {}).get('name', '')
            
            return {
                'id': song_info.get('mid', ''),
                'name': song_info.get('name', ''),
                'artists': singer_name,
                'album': album_name,
                'picUrl': song_info.get('album', {}).get('cover', ''),
                'duration': song_info.get('interval', 0) * 1000,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌曲信息失败: {e}")
            return {}
    
    def get_lyric(self, song_id: str) -> str:
        """获取歌词"""
        url = f"https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        params = {
            'songmid': song_id,
            'pcachetime': 0,
            'format': 'json'
        }
        
        try:
            data = self._get(url, params=params)
            import base64
            lyric_base64 = data.get('lyric', '')
            if lyric_base64:
                try:
                    return base64.b64decode(lyric_base64).decode('utf-8')
                except:
                    return lyric_base64
            return ''
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌词失败: {e}")
            return ''
    
    def get_playlist(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单"""
        url = f"https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
        params = {
            'type': '1',
            'json': '1',
            'utf8': '1',
            'onlysong': '0',
            'disstid': playlist_id,
            'format': 'json'
        }
        
        try:
            data = self._get(url, params=params)
            cdlist = data.get('cdlist', [])
            
            if not cdlist:
                return {}
            
            playlist_info = cdlist[0]
            tracks = []
            
            for item in playlist_info.get('songlist', []):
                singer_name = '/'.join([s['name'] for s in item.get('singer', [])])
                album_name = item.get('album', {}).get('name', '')
                
                tracks.append({
                    'id': item.get('songmid', ''),
                    'name': item.get('songname', ''),
                    'artists': singer_name,
                    'album': album_name,
                    'picUrl': item.get('album', {}).get('cover', ''),
                    'source': 'qq'
                })
            
            return {
                'id': playlist_info.get('dissid', 0),
                'name': playlist_info.get('dissname', ''),
                'coverImgUrl': playlist_info.get('logo', ''),
                'description': playlist_info.get('desc', ''),
                'trackCount': len(tracks),
                'playCount': playlist_info.get('playcount', 0