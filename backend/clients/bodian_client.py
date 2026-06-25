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
from .quality_config import QualityLevel, match_quality

logger = logging.getLogger(__name__)


# 波点 audios level -> 统一 quality key 映射
_BODIAN_LEVEL_MAP = {
    'dtsx': 'dolby',
    'bcms': 'sky',
    'zply': 'jymaster',
    'zpga501': 'jyeffect',
    'zpga201': 'jyeffect',
    'zp': 'hires',
}
# 波点 format+bitrate -> 统一 quality key 映射
_BODIAN_FORMAT_MAP = {
    ('flac', 2000): 'lossless',
    ('ogg', 192): 'exhigh',
    ('ogg', 100): 'standard',
    ('mp3', 320): 'exhigh',
    ('mp3', 128): 'standard',
    ('aac', 48): 'standard',
}


def _parse_size_str(size_str: str) -> int:
    """解析 '10.77Mb' 格式为字节数"""
    try:
        s = size_str.strip().lower()
        if s.endswith('mb'):
            return int(float(s[:-2]) * 1024 * 1024)
        elif s.endswith('kb'):
            return int(float(s[:-2]) * 1024)
        elif s.endswith('gb'):
            return int(float(s[:-2]) * 1024 * 1024 * 1024)
        return int(float(s))
    except:
        return 0


_QUALITY_PRIORITY = ['jymaster', 'jyeffect', 'hires', 'lossless', 'dolby', 'sky', 'exhigh', 'standard']


def _extract_pay_and_quality(item: dict, quality: str = 'lossless') -> dict:
    """从波点音乐搜索结果中提取统一的 payInfo 和 qualityMap"""
    pay_info_obj = item.get('payInfo', {}) if isinstance(item.get('payInfo'), dict) else {}
    fee_type = pay_info_obj.get('feeType', {}) if isinstance(pay_info_obj.get('feeType'), dict) else {}
    is_vip = fee_type.get('vip', '0') == '1'
    is_song_paid = fee_type.get('song', '0') == '1'

    if is_vip:
        pay_info = {'free': False, 'vipOnly': True, 'label': 'VIP'}
    elif is_song_paid:
        pay_info = {'free': False, 'vipOnly': False, 'label': '付费'}
    else:
        pay_info = {'free': True, 'vipOnly': False, 'label': '免费'}

    quality_map = {}
    seenQualities = set()
    for audio in item.get('audios', []):
        level = audio.get('level', '')
        fmt = audio.get('format', '')
        bitrate = audio.get('bitrate', '0')
        size = _parse_size_str(audio.get('size', '0'))

        q_key = _BODIAN_LEVEL_MAP.get(level)
        if not q_key:
            q_key = _BODIAN_FORMAT_MAP.get((fmt, int(bitrate) if bitrate.isdigit() else 0))
        if not q_key:
            continue
        if q_key in seenQualities:
            continue
        if size <= 0:
            continue
        seenQualities.add(q_key)
        quality_map[q_key] = {'bitrate': int(bitrate) if bitrate.isdigit() else 0, 'size': size}

    best = match_quality(quality_map, quality)

    return {'payInfo': pay_info, 'qualityMap': quality_map, 'bestQuality': best}


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
    
    def search(self, keyword: str, limit: int = 50, offset: int = 0, quality: str = 'lossless') -> List[Dict[str, Any]]:
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
                pq = _extract_pay_and_quality(item, quality)
                songs.append({
                    'id': item.get('id', ''),
                    'name': item.get('name', ''),
                    'artists': item.get('artist', ''),
                    'album': item.get('album', ''),
                    'picUrl': item.get('albumPic', ''),
                    'artist_string': item.get('artist', ''),
                    'source': 'bodian',
                    **pq,
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
        """获取歌曲播放/下载URL

        参考 musicdl bodian.py 的 API 链：
        1. 第三方 API 先尝试（cggapi → tianbaoapi）— 无 token 时优先
        2. 官方 API（/api/play/music/v2/checkRight → /api/play/music/v2/audioUrl）
        """
        third_party = self._get_song_url_third_party(song_id, quality)
        if third_party and third_party.get('url'):
            return third_party

        official = self._get_song_url_official(song_id, quality)
        if official and official.get('url'):
            return official

        return {}

    def _get_song_url_third_party(self, song_id: str, quality: str = 'lossless') -> Dict[str, Any]:
        """第三方API获取歌曲URL（按 musicdl 优先级）"""
        for api_name, api_func in self._third_party_apis(song_id):
            try:
                resp = requests.get(api_func, headers=self.default_download_headers, timeout=10)
                data = resp.json()

                download_url = data.get('data', {}).get('url', '') or data.get('url', '')
                if download_url and str(download_url).startswith('http'):
                    logger.info(f"[{self.platform_name}] 第三方API({api_name})成功: {download_url[:80]}...")
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'bodian'
                    }
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 第三方API({api_name})失败: {e}")
                continue

        return {}

    def _third_party_apis(self, song_id: str):
        """返回第三方 API 列表（按 musicdl 优先级：cggapi → tianbaoapi）"""
        return [
            ('cggapi', f"https://kw-api.cenguigui.cn/?id={song_id}&type=song&level=lossless&format=json"),
            ('tianbaoapi', f"https://mobi.kuwo.cn/mobi.s?f=web&user={random.randint(1000000, 10000000)}&source=kwplayerhd_ar_4.3.0.8_tianbao_T1A_qirui.apk&type=convert_url_with_sign&br=2000kflac&rid={song_id}"),
        ]

    def _get_song_url_official(self, song_id: str, quality: str = 'lossless') -> Dict[str, Any]:
        """使用官方API获取歌曲URL

        参考 musicdl _parsewithofficialapiv1：
        1. POST /api/play/music/v2/checkRight（检查权限）
           - status=3 → 试听 URL（audition.https）
        2. POST /api/play/music/v2/audioUrl（获取完整 URL）
        """
        try:
            # Step 1: checkRight
            free_sign = ""
            params = {
                "uid": self.auth_info['uid'],
                "token": self.auth_info['token'],
                "timestamp": str(int(time.time() * 1000)),
                "musicId": str(song_id),
                "freeSign": free_sign
            }
            payload = json.dumps({"musicId": song_id, "freeSign": free_sign}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            params["sign"] = self._signquery("/api/play/music/v2/checkRight", params, body_text=payload.decode("utf-8"))

            resp = self.session.post(
                'https://bd-api.kuwo.cn/api/play/music/v2/checkRight',
                params=params,
                data=payload,
                headers=self.default_download_headers,
                timeout=10
            )
            resp.raise_for_status()
            download_result = resp.json()

            status = download_result.get('data', {}).get('status')
            if status in {3, '3'}:
                # 试听 URL
                download_url = (download_result.get('data', {}).get('audition', {}).get('https')
                                or download_result.get('data', {}).get('audition', {}).get('url'))
                if download_url and str(download_url).startswith('http'):
                    logger.info(f"[{self.platform_name}] 官方API(checkRight)成功: {download_url[:80]}...")
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'bodian'
                    }
            else:
                # VIP 用户，获取完整 URL
                fmt, br = "flac", "2000kflac"
                params2 = {
                    "uid": self.auth_info['uid'],
                    "token": self.auth_info['token'],
                    "timestamp": str(int(time.time() * 1000)),
                    "devId": self.auth_info['dev_id'],
                    "musicId": str(song_id),
                    "format": fmt,
                    "br": br,
                    "freeSign": free_sign
                }
                payload2 = json.dumps({"devId": self.auth_info['dev_id'], "musicId": song_id, "format": fmt, "br": br, "freeSign": free_sign}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                params2["sign"] = self._signquery("/api/play/music/v2/audioUrl", params2, body_text=payload2.decode("utf-8"))

                resp2 = self.session.post(
                    'https://bd-api.kuwo.cn/api/play/music/v2/audioUrl',
                    params=params2,
                    data=payload2,
                    headers={**self.default_download_headers, "uid": self.auth_info['uid'], "token": self.auth_info['token']},
                    timeout=10
                )
                resp2.raise_for_status()
                download_result2 = resp2.json()

                download_url = (download_result2.get('data', {}).get('audioHttpsUrl')
                                or download_result2.get('data', {}).get('audioUrl'))
                if download_url and str(download_url).startswith('http'):
                    logger.info(f"[{self.platform_name}] 官方API(audioUrl)成功: {download_url[:80]}...")
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