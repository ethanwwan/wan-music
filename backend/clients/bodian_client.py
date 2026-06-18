"""波点音乐客户端

继承自 BaseMusicClient，实现波点音乐平台的具体逻辑。

参考 musicdl 的波点音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/bodian.py
"""

import os
import re
import uuid
import time
import json
import random
import base64
import hashlib
import logging
import requests
from contextlib import suppress
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, quote

from .base_client import BaseMusicClient
from .quality_config import QualityLevel

logger = logging.getLogger(__name__)


class BodianClient(BaseMusicClient):
    """波点音乐客户端"""
    
    def __init__(self):
        super().__init__()
        self.platform_name = "波点音乐"
        self.platform_id = "bodian"
        
        self.default_search_headers = {
            "user-agent": "Dart/3.3 (dart:io)",
            "plat": "win",
            "accept-encoding": "gzip",
            "api-ver": "application/json",
            "channel": "W1",
            "brand": "Windows 11 Pro for Workstations",
            "net": "wifi",
            "content-type": "application/json",
            "ver": "1.1.5",
            "svrver": "13"
        }
        
        self.default_download_headers = {
            "user-agent": "Dart/3.3 (dart:io)",
            "plat": "win",
            "accept-encoding": "gzip",
            "api-ver": "application/json",
            "channel": "W1",
            "brand": "Windows 11 Pro for Workstations",
            "net": "wifi",
            "content-type": "application/json",
            "ver": "1.1.5",
            "svrver": "13"
        }
        
        self.auth_info = {'uid': "-1", 'token': "", 'dev_id': hashlib.md5(uuid.uuid4().bytes).hexdigest()}
        
        self.default_search_headers["devid"] = self.auth_info['dev_id']
        self.default_search_headers["qimei36"] = self.auth_info['dev_id']
        self.default_download_headers["devid"] = self.auth_info['dev_id']
        self.default_download_headers["qimei36"] = self.auth_info['dev_id']
        
        self.session.headers.update(self.default_search_headers)
    
    def _signquery(self, path: str, params: Dict[str, Any], body_text: str = "") -> str:
        seed = f"kuwotest{''.join(sorted(ch for ch in urlencode(params) if ch.isalnum()))}"
        if body_text:
            seed += hashlib.md5(f"{body_text}kuwotest".encode("utf-8")).hexdigest()
        return hashlib.md5(f"{seed}{path}".encode("utf-8")).hexdigest()
    
    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        params = {
            "pn": str(offset),
            "rn": str(limit),
            "keyword": keyword,
            "correct": "1",
            "uid": self.auth_info['uid'],
            "token": self.auth_info['token']
        }
        
        url = "https://bd-api.kuwo.cn/api/search/music/list?" + urlencode(params)
        
        try:
            data = self._get(url)
            
            result_list = data.get('data', {}).get('resultList', [])
            songs = []
            for item in result_list:
                songs.append({
                    'id': item.get('id', ''),
                    'name': item.get('name', ''),
                    'artists': item.get('artist', ''),
                    'album': item.get('album', ''),
                    'picUrl': item.get('albumPic', ''),
                    'artist_string': item.get('artist', ''),
                    'source': 'bodian',
                    'freeSign': item.get('freeSign', '')
                })
            return songs
        except Exception as e:
            logger.error(f"[{self.platform_name}] 搜索失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单

        注意：波点（底层酷我）music/list API 的 type=playlist 实际返回的是带 playlist tag 的歌曲，
        而不是真正的歌单（id 是歌曲 ID，不是歌单 ID；没有 songNum/desc 字段）。

        这里返回空列表，歌单搜索请使用网易云/QQ 音乐。
        """
        logger.warning(
            f"[{self.platform_name}] 歌单搜索暂不支持：酷我 music/list API 不提供真正的歌单搜索接口"
        )
        return []
    
    def get_song_url(self, song_id: str, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        apis = [
            f"https://kw-api.cenguigui.cn/?id={song_id}&type=song&level=lossless&format=json",
            f"https://mobi.kuwo.cn/mobi.s?f=web&user={random.randint(1000000, 10000000)}&source=kwplayerhd_ar_4.3.0.8_tianbao_T1A_qirui.apk&type=convert_url_with_sign&br=2000kflac&rid={song_id}",
        ]
        
        headers = {"User-Agent": "Dart/2.19 (dart:io)", "plat": "ar", "channel": "aliopen"}
        
        for api_url in apis:
            try:
                resp = requests.get(api_url, headers=headers, timeout=10)
                try:
                    data = resp.json()
                except:
                    continue
                
                download_url = data.get('data', {}).get('url', '')
                if download_url and download_url.startswith('http'):
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'bodian'
                    }
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 尝试API失败 {api_url}: {e}")
                continue
        
        return self._get_song_url_official(song_id, quality)
    
    def _get_song_url_official(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """使用官方API获取歌曲URL"""
        try:
            params = {
                "uid": self.auth_info['uid'],
                "token": self.auth_info['token'],
                "timestamp": str(int(time.time() * 1000)),
                "musicId": str(song_id),
                "freeSign": ""
            }
            payload = json.dumps({"musicId": song_id, "freeSign": ""}, ensure_ascii=False, separators=(",", ":"))
            params["sign"] = self._signquery("/api/play/music/v2/checkRight", params, body_text=payload)
            
            data = self._get('https://bd-api.kuwo.cn/api/play/music/v2/checkRight', params=params)
            
            status = data.get('data', {}).get('status')
            if status in {3, '3'}:
                download_url = data.get('data', {}).get('audition', {}).get('https', '')
                if download_url:
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'bodian'
                    }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 官方API获取歌曲URL失败: {e}")
        
        return {}
    
    def get_song_info(self, song_id: str) -> Dict[str, Any]:
        """获取歌曲信息 - 使用第三方API"""
        apis = [
            f"https://kw-api.cenguigui.cn/?id={song_id}&type=song&level=lossless&format=json",
        ]
        
        for api_url in apis:
            try:
                resp = requests.get(api_url, timeout=15)
                try:
                    data = resp.json()
                except:
                    continue
                
                song_data = data.get('data', {})
                if song_data:
                    return {
                        'id': song_id,
                        'name': song_data.get('name', ''),
                        'artists': song_data.get('artist', ''),
                        'album': song_data.get('album', ''),
                        'picUrl': song_data.get('pic', ''),
                        'duration': int(float(song_data.get('duration', 0) or 0)) * 1000,
                        'source': 'bodian'
                    }
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 获取歌曲信息失败: {api_url}, 错误: {e}")
                continue
        
        return {}
    
    def get_lyric(self, song_id: str) -> str:
        """获取歌词 - 使用多种方式获取"""
        # 方法1: 使用第三方API获取歌词
        try:
            url = f"https://kw-api.cenguigui.cn/?id={song_id}&type=song&level=lossless&format=json"
            resp = requests.get(url, timeout=15)
            data = resp.json()
            
            lyric = data.get('data', {}).get('lyric', '')
            if lyric:
                return lyric
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 第三方API获取歌词失败: {e}")
        
        # 方法2: 使用歌曲名称搜索歌词
        try:
            song_info = self.get_song_info(song_id)
            song_name = song_info.get('name', '')
            
            if song_name:
                # 使用酷狗歌词API
                search_url = f"http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword={song_name}&page=1&pagesize=1"
                resp = requests.get(search_url, timeout=10)
                data = resp.json()
                songs = data.get('data', {}).get('info', [])
                
                if songs:
                    song = songs[0]
                    song_hash = song.get('hash')
                    duration_ms = song.get('duration', 0) * 1000
                    
                    # 搜索歌词
                    lyric_search_url = f"http://lyrics.kugou.com/search?ver=1&man=yes&client=pc&keyword={song_name}&duration={duration_ms}&hash={song_hash}"
                    resp = requests.get(lyric_search_url, timeout=10)
                    lyric_data = resp.json()
                    candidates = lyric_data.get('candidates', [])
                    
                    if candidates:
                        candidate = candidates[0]
                        download_url = f"http://lyrics.kugou.com/download?ver=1&client=pc&id={candidate['id']}&accesskey={candidate['accesskey']}&fmt=lrc&charset=utf8"
                        resp = requests.get(download_url, timeout=10)
                        download_data = resp.json()
                        
                        if 'content' in download_data:
                            lyric = base64.b64decode(download_data['content']).decode('utf-8')
                            return lyric
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 酷狗歌词API获取失败: {e}")
        
        return self._get_lyric_fallback(song_id)
    
    def _get_lyric_fallback(self, song_id: str) -> str:
        """备用获取歌词方式"""
        make_q_func = lambda sid: base64.b64encode(quote(f"type=lyric&req=2&lrcx=1&rid={sid}&songname=&artist=&corp=kuwo&fromchannel=bodian", safe="=&").encode("utf-8")).decode("ascii")
        url = f"http://mlyric.kuwo.cn/mobi.s?f=bodian&q={make_q_func(song_id)}&uid={self.auth_info['uid']}&token={self.auth_info['token']}"
        
        try:
            resp = self.session.get(url, timeout=10)
            data = resp.json()
            
            lyric_base64 = data.get('data', {}).get('content', '')
            if lyric_base64:
                lyric = base64.b64decode(lyric_base64).decode("utf-8", errors="replace")
                lyric = re.sub(r"<-?\d+,-?\d+>", "", lyric)
                return lyric
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 备用歌词获取失败: {e}")
        
        return ''
    
    def get_playlist(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单 - 使用酷我音乐歌单页面解析"""
        try:
            # 尝试从酷我音乐歌单页面解析歌曲
            url = f"https://www.kuwo.cn/playlist_detail/{playlist_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            
            # 从页面源码中提取歌曲ID
            matches = re.findall(r'href="/play_detail/(\d+)"', resp.text)
            song_names = re.findall(r'title="([^"]+)"[^>]*href="/play_detail/\d+"', resp.text)
            
            if matches:
                tracks = []
                for i, song_id in enumerate(matches[:100]):  # 限制最多100首
                    track_name = song_names[i] if i < len(song_names) else f"歌曲{song_id}"
                    tracks.append({
                        'id': song_id,
                        'name': track_name,
                        'artists': '',
                        'album': '',
                        'picUrl': '',
                        'source': 'bodian'
                    })
                
                return {
                    'id': playlist_id,
                    'name': f'歌单 {playlist_id}',
                    'coverImgUrl': '',
                    'description': '',
                    'trackCount': len(tracks),
                    'playCount': 0,
                    'tracks': tracks,
                    'source': 'bodian'
                }
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 酷我歌单页面解析失败: {e}")
        
        # 备用方案：使用bd-api.kuwo.cn
        return self._get_playlist_fallback(playlist_id)
    
    def _get_playlist_fallback(self, playlist_id: int) -> Dict[str, Any]:
        """备用获取歌单方式"""
        url = f"https://bd-api.kuwo.cn/api/service/playlist/{playlist_id}/musicList"
        params = {
            "source": "5",
            "pn": "1",
            "rn": "100",
            "uid": self.auth_info['uid'],
            "token": self.auth_info['token']
        }
        
        try:
            data = self._get(url, params=params)
            
            tracks_in_playlist = []
            page = 1
            while True:
                list_data = data.get('data', {}).get('list', [])
                if not list_data:
                    break
                tracks_in_playlist.extend(list_data)
                
                total = int(data.get('data', {}).get('total', 0))
                if len(tracks_in_playlist) >= total:
                    break
                
                page += 1
                params['pn'] = str(page)
                data = self._get(url, params=params)
            
            tracks = []
            for item in tracks_in_playlist:
                tracks.append({
                    'id': item.get('id', ''),
                    'name': item.get('name', ''),
                    'artists': item.get('artist', ''),
                    'album': item.get('album', ''),
                    'picUrl': item.get('albumPic', ''),
                    'source': 'bodian'
                })
            
            url_info = f"https://bd-api.kuwo.cn/api/service/playlist/info/{playlist_id}"
            info_data = self._get(url_info, params={"source": "5", "uid": self.auth_info['uid'], "token": self.auth_info['token']})
            
            return {
                'id': playlist_id,
                'name': info_data.get('data', {}).get('name', ''),
                'coverImgUrl': info_data.get('data', {}).get('cover', ''),
                'description': info_data.get('data', {}).get('desc', ''),
                'trackCount': len(tracks),
                'playCount': info_data.get('data', {}).get('playCount', 0),
                'tracks': tracks,
                'source': 'bodian'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌单信息失败: {e}")
            return {}


bodian_client = BodianClient()