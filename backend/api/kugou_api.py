"""酷狗音乐API模块

参考musicdl项目的酷狗音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kugou.py

支持搜索歌曲、获取歌曲URL、歌单和专辑信息。
"""

import json
import urllib.parse
import logging
from typing import Dict, List, Optional, Any

import requests

# 配置日志
logger = logging.getLogger(__name__)


class KugouAPIClient:
    """酷狗音乐API客户端"""
    
    def __init__(self):
        """初始化客户端"""
        self.session = requests.Session()
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
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
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
            logger.error(f"酷狗音乐搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        from urllib.parse import urlencode
        
        # 使用搜索接口获取歌单（通过type参数）
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
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
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
            logger.error(f"酷狗音乐歌单搜索失败: {e}")
            return []
    
    def get_song_url(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放URL（使用第三方解析API）"""
        quality_map = {
            'standard': '128k',
            'high': '320k',
            'exhigh': '320k',
            'lossless': 'flac',
            'hires': 'flac24bit'
        }
        
        api_quality = quality_map.get(quality, '320k')
        
        # 尝试多个第三方API
        apis = [
            f"http://api.liuyunidc.cn/baimusic/musicurl.php?source=kg&musicId={song_id}&quality={api_quality}&card=BAI-153B4JE4I40HSG40H1FP"
        ]
        
        headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": "http://api.liuyunidc.cn/baimusic/",
            "host": "api.liuyunidc.cn",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        }
        
        for api_url in apis:
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                download_url = data.get('url')
                if download_url and download_url.startswith('http'):
                    return {'url': download_url, 'quality': quality, 'source': 'kugou'}
            except Exception as e:
                logger.debug(f"尝试API失败: {api_url}, 错误: {e}")
                continue
        
        # 如果第三方API都失败，尝试官方API
        try:
            url = f"https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash={song_id}&mid=1"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            audio_info = data.get('data', {})
            play_url = audio_info.get('play_url') or audio_info.get('url')
            if play_url:
                return {'url': play_url, 'quality': quality, 'source': 'kugou'}
        except Exception as e:
            logger.error(f"获取酷狗音乐歌曲URL失败: {e}")
        
        return {}
    
    def get_playlist_detail(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单详情"""
        url = f"https://www.kugou.com/yy/index.php?r=play/getPlaylistInfo&specialid={playlist_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            playlist_data = data.get('data', {})
            tracks = []
            for item in playlist_data.get('list', []):
                tracks.append({
                    'id': item.get('hash', ''),
                    'name': item.get('songname', ''),
                    'artists': item.get('singername', ''),
                    'album': item.get('album_name', ''),
                    'picUrl': item.get('cover', ''),
                    'source': 'kugou'
                })
            
            return {
                'id': playlist_id,
                'name': playlist_data.get('specialname', ''),
                'coverImgUrl': playlist_data.get('cover', ''),
                'description': playlist_data.get('intro', ''),
                'trackCount': len(tracks),
                'playCount': playlist_data.get('playcount', 0),
                'tracks': tracks,
                'source': 'kugou'
            }
        except Exception as e:
            logger.error(f"获取酷狗音乐歌单详情失败: {e}")
            return {}
    
    def get_lyric(self, song_id: str) -> str:
        """获取歌词"""
        url = f"https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash={song_id}&mid=1"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('lyrics', '')
        except Exception as e:
            logger.error(f"获取酷狗音乐歌词失败: {e}")
            return ''


# 创建全局客户端实例
kugou_client = KugouAPIClient()
