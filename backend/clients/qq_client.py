"""QQ音乐客户端

继承自 BaseMusicClient，实现QQ音乐平台的具体逻辑。

参考 musicdl 的QQ音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py
"""

import json
import urllib.parse
import logging
import random
import requests
import base64
import re
from typing import Dict, List, Optional, Any
from contextlib import suppress

from .base_client import BaseMusicClient
from .quality_config import QualityLevel

logger = logging.getLogger(__name__)


def strip_html_tags(text):
    """移除HTML标签，只保留纯文本"""
    if not text or not isinstance(text, str):
        return text
    return re.sub(r'<[^>]+>', '', text)


class QQClient(BaseMusicClient):
    """QQ音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "QQ音乐"
        self.platform_id = "qq"
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/',
            'Origin': 'https://y.qq.com/',
        }
        self.default_parse_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Referer': 'https://y.qq.com/',
            'Origin': 'https://y.qq.com/',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            'Referer': 'http://y.qq.com',
        }
        self.session.headers.update(self.default_search_headers)
        self.guid = self._generate_guid()
    
    def _generate_guid(self) -> str:
        """生成guid"""
        return str(random.randint(1000000000, 9999999999))
    
    def _safe_extract(self, data: dict, keys: list, default=None):
        """安全提取字典值"""
        result = data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            elif isinstance(result, list) and isinstance(key, int) and 0 <= key < len(result):
                result = result[key]
            else:
                return default
        return result
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲 - 使用musicdl风格的POST请求"""
        logger.info(f"[QQ] 搜索开始: keyword={keyword}, limit={limit}, offset={offset}")
        url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
        
        # QQ音乐API对num_per_page有限制，最大不能超过60
        actual_limit = min(limit, 60)
        
        payload = {
            "music.search.SearchCgiService.DoSearchForQQMusicMobile": {
                "method": "DoSearchForQQMusicMobile",
                "module": "music.search.SearchCgiService",
                "param": {
                    "searchid": str(random.randint(1000000000, 9999999999)),
                    "query": keyword,
                    "search_type": 0,
                    "num_per_page": actual_limit,
                    "page_num": offset // actual_limit + 1,
                    "highlight": 1,
                    "grp": 1
                }
            }
        }
        
        try:
            logger.info(f"[QQ] 发送请求到: {url}")
            resp = self.session.post(url, data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 
                                    headers=self.default_search_headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[QQ] API响应状态码: {resp.status_code}")
            
            song_list = self._safe_extract(data, ['music.search.SearchCgiService.DoSearchForQQMusicMobile', 'data', 'body', 'item_song'], [])
            logger.info(f"[QQ] 第一次提取item_song结果: {len(song_list) if isinstance(song_list, list) else 'not list'}")
            if not isinstance(song_list, list) or len(song_list) == 0:
                song_list = self._safe_extract(data, ['music.search.SearchCgiService.DoSearchForQQMusicMobile', 'data', 'body', 'item_song', 'list'], [])
                logger.info(f"[QQ] 第二次提取item_song.list结果: {len(song_list) if isinstance(song_list, list) else 'not list'}")
            
            songs = []
            for item in song_list:
                singer_name = '/'.join([strip_html_tags(s.get('name', '')) for s in item.get('singer', []) if isinstance(s, dict)])
                album_name = strip_html_tags(self._safe_extract(item, ['album', 'title'], '') or item.get('albumname', ''))
                album_mid = self._safe_extract(item, ['album', 'mid'], '') or item.get('albummid', '')
                
                pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''
                
                songs.append({
                    'id': item.get('mid', '') or item.get('songmid', ''),
                    'name': strip_html_tags(item.get('title', '') or item.get('songname', '')),
                    'artists': singer_name,
                    'album': album_name,
                    'picUrl': pic_url,
                    'artist_string': singer_name,
                    'source': 'qq',
                    'interval': item.get('interval', 0)
                })
            logger.info(f"[QQ] 搜索成功，返回 {len(songs)} 首歌曲")
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}", exc_info=True)
        
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
                    singer_name = '/'.join([strip_html_tags(s.get('name', '')) for s in item.get('singer', [])])
                    album_name = strip_html_tags(item.get('album', {}).get('name', ''))
                    pic_url = item.get('album', {}).get('mid', '')
                    if pic_url:
                        pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{pic_url}.jpg?max_age=2592000"
                    
                    songs.append({
                        'id': item.get('mid', ''),
                        'name': strip_html_tags(item.get('name', '')),
                        'artists': singer_name,
                        'album': album_name,
                        'picUrl': pic_url,
                        'artist_string': singer_name,
                        'source': 'qq',
                        'interval': item.get('interval', 0)
                    })
                return songs
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 备用搜索失败: {e}")
        
        logger.error(f"[{self.platform_name}] 搜索失败")
        return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
        
        payload = {
            "music.search.SearchCgiService.DoSearchForQQMusicMobile": {
                "method": "DoSearchForQQMusicMobile",
                "module": "music.search.SearchCgiService",
                "param": {
                    "searchid": str(random.randint(1000000000, 9999999999)),
                    "query": keyword,
                    "search_type": 3,
                    "num_per_page": limit,
                    "page_num": 1,
                    "highlight": 1,
                    "grp": 1
                }
            }
        }
        
        try:
            resp = self.session.post(url, data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 
                                    headers=self.default_search_headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            playlist_list = self._safe_extract(data, ['music.search.SearchCgiService.DoSearchForQQMusicMobile', 'data', 'body', 'item_songlist'], [])
            
            playlists = []
            for item in playlist_list:
                cover_url = item.get('logo', '')
                
                playlists.append({
                    'id': item.get('dissid', 0),
                    'name': strip_html_tags(item.get('dissname', '')),
                    'coverImgUrl': cover_url,
                    'description': strip_html_tags(item.get('description', '')),
                    'trackCount': item.get('songnum', 0),
                    'playCount': item.get('listennum', 0),
                    'source': 'qq'
                })
            return playlists
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 搜索歌单失败: {e}")
        
        logger.error(f"[{self.platform_name}] 搜索歌单失败")
        return []
    
    def get_song_url(self, song_id: str, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取歌曲播放/下载URL - 使用分层的第三方API"""
        l1_apis = [
            lambda sid: f"https://api.vkeys.cn/v2/music/tencent/geturl?mid={sid}&quality=3",
            lambda sid: f"https://api.xcvts.cn/api/music/qq?apiKey=Nzg5OTMzNDRiOWJmMTEwNTY1NTU5OTAwOWNkYmEzZDI=&mid={sid}&type=HQ高品质",
        ]
        
        l2_apis = [
            lambda sid: f"https://api.nki.pw/API/music_open_api.php?mid={sid}&apikey=MjhmZWNlOTI1NDM5YjA1Mjc5MmE5Nzk4OWM4NzBjZWQzODAzYTcxYzZiNTM0ZjcxZTVhNTMzMzhiMmQzMWVmOA==",
            lambda sid: f"https://tang.api.s01s.cn/music_open_api.php?mid={sid}",
        ]
        
        l3_apis = [
            lambda sid: f"https://api.xunhuisi.store/API/QQMusic/Song.php?mid={sid}&type=json",
            lambda sid: f"https://lpz.chatc.vip/apiqq.php?songmid={sid}&type=json&br=1",
            lambda sid: f"https://cyapi.top/API/qq_music.php?apikey=1ffdf5733f5d538760e63d7e46ba17438d9f7b9dfc18c51be1109386fd74c3a1&type=json&mid={sid}&quality=lossless",
        ]
        
        l4_apis = [
            lambda sid: f"https://api.ygking.top/api/song/url?mid={sid}&quality=320",
            lambda sid: f"https://lxmusicapi.onrender.com/url/tx/{sid}/320k",
        ]
        
        all_apis = l1_apis + l2_apis + l3_apis + l4_apis
        
        for api_func in all_apis:
            api_url = api_func(song_id)
            try:
                resp = requests.get(api_url, headers=self.default_download_headers, timeout=10)
                try:
                    data = resp.json()
                except:
                    continue
                
                download_url = self._safe_extract(data, ['data', 'url'], '') or \
                              data.get('url', '') or \
                              data.get('song_play_url', '') or \
                              data.get('song_play_url_hq', '') or \
                              data.get('music_url', '') or \
                              data.get('song_play_url_sq', '')
                
                if download_url and str(download_url).startswith('http'):
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'qq'
                    }
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 尝试API失败 {api_url}: {e}")
                continue
        
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
            "music.pf_song_detail_svr.get_song_detail_yqq": {
                "method": "get_song_detail_yqq",
                "module": "music.pf_song_detail_svr",
                "param": {
                    "song_mid": song_id
                }
            }
        }
        
        try:
            resp = self.session.post(url, data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 
                                    headers=self.default_parse_headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            song_info = self._safe_extract(data, ['music.pf_song_detail_svr.get_song_detail_yqq', 'data', 'track_info'], {})
            
            singer_name = '/'.join([s.get('name', '') for s in song_info.get('singer', []) if isinstance(s, dict)])
            album_name = self._safe_extract(song_info, ['album', 'title'], '') or song_info.get('albumname', '')
            album_mid = self._safe_extract(song_info, ['album', 'mid'], '') or song_info.get('albummid', '')
            pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''
            
            return {
                'id': song_info.get('mid', ''),
                'name': song_info.get('name', '') or song_info.get('title', ''),
                'artists': singer_name,
                'album': album_name,
                'picUrl': pic_url,
                'duration': int(float(song_info.get('interval', 0) or 0)) * 1000,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌曲信息失败: {e}")
            return {}
    
    def get_lyric(self, song_id: str) -> str:
        """获取歌词"""
        url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        params = {
            'songmid': song_id,
            'g_tk': '5381',
            'loginUin': '0',
            'hostUin': '0',
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'platform': 'yqq'
        }
        
        try:
            resp = self.session.get(url, params=params, headers={'Referer': 'https://y.qq.com/portal/player.html'}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            lyric_base64 = data.get('lyric', '')
            if lyric_base64 and lyric_base64 != 'NULL':
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
        url = "https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
        params = {
            'disstid': str(playlist_id),
            'type': '1',
            'json': '1',
            'utf8': '1',
            'onlysong': '0',
            'format': 'json'
        }
        
        try:
            resp = self.session.get(url, params=params, headers={'Referer': f"https://y.qq.com/n/ryqq/playlist/{playlist_id}"}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            cdlist = data.get('cdlist', [])
            if not cdlist:
                return {}
            
            playlist_info = cdlist[0]
            tracks = []
            
            songlist = playlist_info.get('songlist', [])
            for item in songlist:
                singer_name = '/'.join([s.get('name', '') for s in item.get('singer', []) if isinstance(s, dict)])
                album_name = self._safe_extract(item, ['album', 'title'], '') or item.get('albumname', '')
                album_mid = self._safe_extract(item, ['album', 'mid'], '') or item.get('albummid', '')
                pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''
                
                tracks.append({
                    'id': item.get('songmid', ''),
                    'name': item.get('songname', ''),
                    'artists': singer_name,
                    'album': album_name,
                    'picUrl': pic_url,
                    'source': 'qq'
                })
            
            cover_mid = playlist_info.get('logo', '').replace('https://y.gtimg.cn/music/photo_new/T002R800x800M000', '').replace('.jpg', '')
            cover_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{cover_mid}.jpg?max_age=2592000" if cover_mid else playlist_info.get('logo', '')
            
            return {
                'id': playlist_info.get('dissid', 0),
                'name': playlist_info.get('dissname', ''),
                'coverImgUrl': cover_url,
                'description': playlist_info.get('desc', ''),
                'trackCount': len(tracks),
                'playCount': playlist_info.get('playcount', 0),
                'tracks': tracks,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌单信息失败: {e}")
            return {}


qq_client = QQClient()