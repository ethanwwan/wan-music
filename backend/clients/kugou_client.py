"""酷狗音乐客户端

继承自 BaseMusicClient，实现酷狗音乐平台的具体逻辑。

参考 musicdl 的酷狗音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/kugou.py
"""

import re
import json
import base64
import hashlib
import logging
import requests
from typing import Dict, List, Optional, Any

from .base_client import BaseMusicClient
from .quality_config import QualityLevel

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
    
    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
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
                    'source': 'kugou',
                    'duration': item.get('Duration', 0) or item.get('timelen', 0)
                })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单

        注意：酷狗 songsearch API 的 type=playlist 实际返回的是带 playlist tag 的歌曲，
        而不是真正的歌单（ID 是歌曲 ID，不是歌单 ID；没有 songcount/playcount 字段）。
        实际歌单 ID 在搜索接口中无法获取，需通过其他途径（如分享链接）。

        这里返回空列表，歌单搜索请使用网易云/QQ 音乐。
        """
        logger.warning(
            f"[{self.platform_name}] 歌单搜索暂不支持：酷狗 songsearch API 不提供真正的歌单搜索接口"
        )
        return []
    
    def _get_song_meta_info(self, song_id: str) -> Dict[str, Any]:
        """获取歌曲元信息"""
        url = "https://m.kugou.com/app/i/getSongInfo.php"
        params = {"cmd": "playInfo", "hash": song_id.strip().upper()}
        
        try:
            song_detail = self._get(url, params=params)
            if not song_detail:
                return {}
            
            duration = float(song_detail.get("timeLength") or 0) / 1000
            
            album_url = "http://mobilecdnbj.kugou.com/api/v3/album/info"
            album_params = {"albumid": song_detail.get("albumid", 0), "version": "9108", "plat": "0"}
            album_info = self._get(album_url, params=album_params)
            album_info = album_info.get('data', {})
            
            cover_url = (album_info.get("imgurl") or song_detail.get("album_img") or "").replace("{size}", "400")
            
            return {
                "songname": song_detail.get("songName"),
                "singername": song_detail.get("singerName"),
                "album_name": album_info.get("albumname"),
                "duration": duration,
                "cover_url": cover_url,
                "song_detail": song_detail,
                "album_info": album_info
            }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 获取歌曲元信息失败: {e}")
            return {}
    
    def get_song_url(self, song_id: str, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        apis = [
            lambda sid: f"https://musicapi.haitangw.net/kgqq/kg.php?type=json&id={sid}&level=exhigh",
            lambda sid: f"https://music.haitangw.cc/kgqq/kg.php?type=json&id={sid}&level=exhigh",
            lambda sid: f"http://api.liuyunidc.cn/baimusic/musicurl.php?source=kg&musicId={sid}&quality=320k&card=BAI-153B4JE4I40HSG40H1FP",
            lambda sid: f"https://api.317ak.cn/api/yinyue/kugou?ckey=WE1VS0lBSjNQOExQWDNQOTcxS1U=&i={sid}&br=6&type=json&lrc=1",
            lambda sid: f"https://kw-api.cenguigui.cn/?id={sid}&type=song&level=lossless&format=json",
        ]
        
        headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        }
        
        for api_func in apis:
            api_url = api_func(song_id)
            try:
                resp = requests.get(api_url, headers=headers, timeout=10)
                try:
                    data = resp.json()
                except:
                    continue
                
                download_url = data.get('data', {}).get('url', '') or data.get('url', '')
                if download_url and download_url.startswith('http'):
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'kugou'
                    }
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 尝试API失败 {api_url}: {e}")
                continue
        
        return self._get_song_url_official(song_id, quality)
    
    def _get_song_url_official(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """使用官方API获取歌曲URL"""
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
        meta_info = self._get_song_meta_info(song_id)
        
        if meta_info:
            return {
                'id': song_id,
                'name': meta_info.get('songname', ''),
                'artists': meta_info.get('singername', ''),
                'album': meta_info.get('album_name', ''),
                'picUrl': meta_info.get('cover_url', ''),
                'duration': int(float(meta_info.get('duration', 0) or 0)) * 1000,
                'source': 'kugou'
            }
        
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
        """获取歌词 - 使用酷狗官方API"""
        try:
            song_info = self.get_song_info(song_id)
            duration = song_info.get('duration', 0)
            
            search_params = {
                'ver': '1',
                'man': 'yes',
                'client': 'pc',
                'keyword': song_info.get('name', ''),
                'duration': str(int(duration)),
                'hash': song_id
            }
            
            resp = self.session.get('http://lyrics.kugou.com/search', params=search_params, timeout=10)
            lyric_result = resp.json()
            
            candidates = lyric_result.get('candidates', [])
            if candidates:
                candidate = candidates[0]
                download_url = f"http://lyrics.kugou.com/download?ver=1&client=pc&id={candidate['id']}&accesskey={candidate['accesskey']}&fmt=lrc&charset=utf8"
                
                resp = self.session.get(download_url, timeout=10)
                download_result = resp.json()
                
                lyric_base64 = download_result.get('content', '')
                if lyric_base64 and lyric_base64 != 'NULL':
                    return base64.b64decode(lyric_base64).decode('utf-8')
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 获取歌词失败: {e}")
        
        return self._get_lyric_fallback(song_id)
    
    def _get_lyric_fallback(self, song_id: str) -> str:
        """备用获取歌词方式"""
        apis = [
            f"https://api.317ak.cn/api/yinyue/kugou?ckey=WE1VS0lBSjNQOExQWDNQOTcxS1U=&i={song_id}&br=6&type=json&lrc=1",
        ]
        
        for api_url in apis:
            try:
                resp = requests.get(api_url, timeout=10)
                try:
                    data = resp.json()
                except:
                    continue
                
                lyric = data.get('lyric', '')
                if lyric and lyric != 'NULL':
                    return lyric
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 尝试获取歌词失败 {api_url}: {e}")
        
        return ''
    
    def _clean_kugou_response(self, response_text: str) -> dict:
        """清理酷狗API响应中的HTML注释"""
        import re
        cleaned = re.sub(r'<!--KG_TAG_RES_START-->', '', response_text)
        cleaned = re.sub(r'<!--KG_TAG_RES_END-->', '', cleaned)
        return json.loads(cleaned)
    
    def get_playlist(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单 - 使用移动端API"""
        song_api = f"http://mobilecdn.kugou.com/api/v3/special/song?plat=0&specialid={playlist_id}&page=1&pagesize=-1&version=8352&with_res_tag=1"
        
        try:
            resp = self.session.get(song_api, timeout=10)
            data = self._clean_kugou_response(resp.text)
            
            if isinstance(data, dict) and data.get('data'):
                playlist_data = data['data']
                tracks_data = playlist_data.get('info', [])
                
                tracks = []
                for item in tracks_data:
                    filename = item.get('filename', '')
                    if '-' in filename:
                        parts = filename.split(' - ', 1)
                        singer_name = parts[0].strip()
                        song_name = parts[1].strip() if len(parts) > 1 else filename
                    else:
                        singer_name = ''
                        song_name = filename
                    
                    tracks.append({
                        'id': item.get('hash', ''),
                        'name': song_name,
                        'artists': singer_name,
                        'album': item.get('remark', ''),
                        'picUrl': item.get('trans_param', {}).get('union_cover', '').replace('{size}', '400'),
                        'source': 'kugou'
                    })
                
                info_api = f"http://mobilecdn.kugou.com/api/v3/special/info?plat=0&specialid={playlist_id}&version=8352"
                try:
                    resp_info = self.session.get(info_api, timeout=10)
                    info_data = self._clean_kugou_response(resp_info.text)
                    info = info_data.get('data', {})
                except:
                    info = {}
                
                return {
                    'id': info.get('specialid', playlist_id),
                    'name': info.get('specialname', '') or f'歌单 {playlist_id}',
                    'coverImgUrl': info.get('cover', '') or info.get('Logo', '').replace('{size}', '400'),
                    'description': info.get('intro', '') or info.get('Description', ''),
                    'trackCount': len(tracks),
                    'playCount': info.get('playcount', 0) or info.get('PlayCount', 0),
                    'tracks': tracks,
                    'source': 'kugou'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 获取歌单失败: {e}")
        
        return {}


kugou_client = KugouClient()