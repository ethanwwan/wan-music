"""QQ音乐客户端

继承自 BaseMusicClient，实现QQ音乐平台的具体逻辑。

参考 musicdl 的QQ音乐实现：
https://github.com/CharlesPikachu/musicdl/blob/master/musicdl/modules/sources/qq.py
"""

import json
import time
import urllib.parse
import logging
import random
import requests
import base64
import re
import os
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
        self.cookie = self._load_cookie()
        # 参考 https://github.com/Suxiaoqinx/qqmusic_flac 的 fileConfig
        # 统一使用 Chrome 58 UA 和固定 guid '10000'，与参考项目保持一致
        self.default_search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://y.qq.com/',
            'Origin': 'https://y.qq.com/',
        }
        self.default_parse_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://y.qq.com/',
            'Origin': 'https://y.qq.com/',
        }
        self.default_download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'http://y.qq.com',
        }
        self.session.headers.update(self.default_search_headers)
        # 参考项目使用固定 guid '10000'
        self.guid = '10000'
    
    def _load_cookie(self) -> str:
        """加载cookie文件"""
        cookie_file = os.path.join(os.path.dirname(__file__), 'cookie', 'qq_cookie.txt')
        try:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            logger.debug(f"[{self.platform_name}] 加载cookie失败: {e}")
        return ''
    
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
    
    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
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
            # 合并 headers：默认 headers + Cookie（Cookie 是登录鉴权关键，必须带）
            req_headers = dict(self.default_search_headers)
            if self.cookie:
                req_headers['Cookie'] = self.cookie
            resp = self.session.post(url, data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                                    headers=req_headers, timeout=10)
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
    
    def _search_fallback(self, keyword: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
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
        """搜索歌单 - 多重降级策略

        1. 官方 API（u.y.qq.com）— 需要 cookie，偶尔会限流返回空
        2. 第三方 API（cyapi.top）— 备用，绕过限流
        3. 都失败返回 []
        """
        # ---- 第 1 次：官方 API，带重试 ----
        for attempt in range(2):
            try:
                result = self._search_playlist_official(keyword, limit)
                if result:
                    return result
                logger.warning(f"[{self.platform_name}] 歌单搜索官方 API 返回空 (尝试 {attempt + 1}/2)")
            except Exception as e:
                logger.warning(f"[{self.platform_name}] 歌单搜索官方 API 失败 (尝试 {attempt + 1}/2): {e}")
            time.sleep(0.5)

        # ---- 第 2 次：第三方 API ----
        try:
            result = self._search_playlist_fallback(keyword, limit)
            if result:
                logger.info(f"[{self.platform_name}] 歌单搜索走第三方 API 成功，返回 {len(result)} 个")
                return result
        except Exception as e:
            logger.warning(f"[{self.platform_name}] 歌单搜索第三方 API 失败: {e}")

        logger.error(f"[{self.platform_name}] 歌单搜索全部失败: keyword={keyword}")
        return []

    def _search_playlist_official(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """官方 API 搜歌单（u.y.qq.com）"""
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

        # 合并 headers：默认 + Cookie（歌单搜索需要登录态才能拿到 user 自己的私人歌单）
        req_headers = dict(self.default_search_headers)
        if self.cookie:
            req_headers['Cookie'] = self.cookie
        resp = self.session.post(
            url,
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            headers=req_headers,
            timeout=10
        )
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

    def _search_playlist_fallback(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """第三方 cyapi.top 搜歌单（备用）"""
        url = f"https://cyapi.top/API/qq_music.php"
        # cyapi 搜歌单的接口可能与搜歌不同，这里用通用搜索接口搜 type=playlist
        try:
            api_url = f"https://cyapi.top/API/qq_music.php?apikey=1ffdf5733f5d538760e63d7e46ba17438d9f7b9dfc18c51be1109386fd74c3a1&type=json&input={urllib.parse.quote(keyword)}&filter=playlist&num={limit}"
            resp = self.session.get(api_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get('data'):
                playlists = []
                for item in data.get('data', [])[:limit]:
                    playlists.append({
                        'id': item.get('id', item.get('tid', 0)),
                        'name': item.get('name', item.get('title', '')),
                        'coverImgUrl': item.get('cover', item.get('pic', '')),
                        'description': item.get('desc', item.get('description', '')),
                        'trackCount': item.get('count', item.get('songnum', 0)),
                        'playCount': item.get('playCount', item.get('listennum', 0)),
                        'source': 'qq'
                    })
                return playlists
        except Exception as e:
            logger.debug(f"[{self.platform_name}] cyapi 歌单搜索失败: {e}")
        return []
    
    def get_song_url(self, song_id: str, quality: str = QualityLevel.LOSSLESS.value) -> Dict[str, Any]:
        """获取歌曲播放/下载URL

        策略：
        1. 优先用官方 vkey API（需要 cookie，普通用户也能下到 EXhigh 320k M4A）
        2. 失败时降级到第三方 API（保证至少能下到 M4A 256k）

        注意：QQ 第三方 API（vkeys/xcvts/cyapi 等）通常都会返回 M4A 256k，
        只有官方 API 配合 VIP cookie 才能下到 FLAC/Hi-Res/Master。
        """
        # 先尝试官方 API（用当前 cookie，普通用户通常能拿到 exhigh 320k M4A）
        official = self._get_song_url_official(song_id, quality)
        if official and official.get('url'):
            return official

        # 官方失败：降级到第三方 API（保证能下到 m4a 256k）
        # 只试主流的几个第三方 API，避免等待太久
        third_party_apis = [
            lambda sid: f"https://api.vkeys.cn/v2/music/tencent/geturl?mid={sid}&quality=3",
            lambda sid: f"https://api.nki.pw/API/music_open_api.php?mid={sid}&apikey=MjhmZWNlOTI1NDM5YjA1Mjc5MmE5Nzk4OWM4NzBjZWQzODAzYTcxYzZiNTM0ZjcxZTVhNTMzMzhiMmQzMWVmOA==",
            lambda sid: f"https://cyapi.top/API/qq_music.php?apikey=1ffdf5733f5d538760e63d7e46ba17438d9f7b9dfc18c51be1109386fd74c3a1&type=json&mid={sid}&quality=lossless",
        ]

        for api_func in third_party_apis:
            api_url = api_func(song_id)
            try:
                resp = requests.get(api_url, headers=self.default_download_headers, timeout=5)
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
                    # 从 URL 后缀推断文件类型
                    dl_lower = str(download_url).lower()
                    if '.flac' in dl_lower:
                        file_type = 'flac'
                    elif '.mp3' in dl_lower:
                        file_type = 'mp3'
                    elif '.m4a' in dl_lower or '.mp4' in dl_lower:
                        file_type = 'm4a'
                    elif '.ogg' in dl_lower:
                        file_type = 'ogg'
                    else:
                        file_type = 'm4a'  # 兜底，QQ 大多数情况是 m4a 容器
                    logger.info(f"[{self.platform_name}] 第三方API音质 → {download_url[:100]}, fileType={file_type}")
                    return {
                        'url': download_url,
                        'quality': quality,
                        'song_id': song_id,
                        'source': 'qq',
                        'fileType': file_type
                    }
            except Exception as e:
                logger.debug(f"[{self.platform_name}] 尝试API失败 {api_url}: {e}")
                continue

        # 第三方也全部失败：返回空（前端会提示下载失败）
        return {
            'url': '',
            'quality': quality,
            'song_id': song_id,
            'source': 'qq',
            'fileType': 'm4a',
            'error': 'QQ音乐所有渠道均无法获取此歌曲，请尝试其他平台或单曲'
        }
    
    def _get_song_url_official(self, song_id: str, quality: str = 'high') -> Dict[str, Any]:
        """使用 QQ 官方 vkey API 获取歌曲URL
        完全参考 https://github.com/Suxiaoqinx/qqmusic_flac/blob/main/qqapi.js

        QQ音乐 fileConfig 命名规则：{prefix}{songmid}{songmid}{ext}
        - M500/M800 + .mp3 = MP3 128k/320k
        - F000 + .flac = FLAC 无损
        - AI00 + .flac = Master 母带
        - SQ00 + .flac = Hi-Res
        - Q000/Q001 + .flac = Atmos 2.0/5.1
        - O400-O801 + .ogg = OGG 96k~640k
        - C100-C800 + .m4a = AAC 24k~320k (m4a 容器)
        - RS01 + .flac = Dolby Atmos
        """
        # 完整对照参考项目的 fileConfig
        QQ_FILE_CONFIG = {
            # 极高 / 320k
            'exhigh':    ('M800', '.mp3'),
            '320':       ('M800', '.mp3'),
            # 标准 / 128k
            'standard':  ('M500', '.mp3'),
            '128':       ('M500', '.mp3'),
            # 无损 / FLAC
            'lossless':  ('F000', '.flac'),
            'flac':      ('F000', '.flac'),
            # 母带
            'jymaster':  ('AI00', '.flac'),
            'master':    ('AI00', '.flac'),
            # Hi-Res
            'hires':     ('SQ00', '.flac'),
            'jyeffect':  ('SQ00', '.flac'),
            # 杜比全景声（注意：参考项目是 RS01）
            'dolby':     ('RS01', '.flac'),
            # 沉浸环绕声（参考项目用 Q001 = Atmos 5.1）
            'sky':       ('Q001', '.flac'),
            # Atmos 2.0
            'atmos_2':   ('Q000', '.flac'),
            # Atmos 5.1
            'atmos_51':  ('Q001', '.flac'),
            # OGG 系列
            'ogg_640':   ('O801', '.ogg'),
            'ogg_320':   ('O800', '.ogg'),
            'ogg_192':   ('O600', '.ogg'),
            'ogg_96':    ('O400', '.ogg'),
            # AAC 系列
            'aac_320':   ('C800', '.m4a'),
            'aac_256':   ('C700', '.m4a'),
            'aac_192':   ('C600', '.m4a'),
            'aac_128':   ('C500', '.m4a'),
            'aac_96':    ('C400', '.m4a'),
            'aac_64':    ('C300', '.m4a'),
            'aac_48':    ('C200', '.m4a'),
            'aac_24':    ('C100', '.m4a'),
            # APE/DTS
            'ape':       ('A000', '.ape'),
            'dts':       ('D000', '.dts'),
        }
        prefix, ext = QQ_FILE_CONFIG.get(quality, ('F000', '.flac'))
        # 官方 filename 规则：prefix + songmid + songmid + ext
        filename = f"{prefix}{song_id}{song_id}{ext}"

        try:
            # 使用 musicu.fcg GetVkeyServer API（与参考项目完全一致）
            url = 'https://u.y.qq.com/cgi-bin/musicu.fcg'
            req_data = {
                "req_1": {
                    "module": "vkey.GetVkeyServer",
                    "method": "CgiGetVkey",
                    "param": {
                        "filename": [filename],
                        "guid": self.guid,
                        "songmid": [song_id],
                        "songtype": [0],
                        "uin": "0",
                        "loginflag": 1,
                        "platform": "20"
                    }
                },
                "loginUin": "0",
                "comm": {
                    "uin": "0",
                    "format": "json",
                    "ct": 24,
                    "cv": 0
                }
            }
            # 完全照搬参考项目的 headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
                'Referer': 'https://y.qq.com/',
            }
            if self.cookie:
                headers['Cookie'] = self.cookie

            resp = self.session.post(url, data=json.dumps(req_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                                     headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[{self.platform_name}] 官方API resp keys: {list(data.keys())}, req_1 keys: {list(data.get('req_1', {}).keys())}")
            midurlinfo = data.get('req_1', {}).get('data', {}).get('midurlinfo', [])
            sip = data.get('req_1', {}).get('data', {}).get('sip', [])
            logger.info(f"[{self.platform_name}] 官方API midurlinfo={midurlinfo}, sip={sip[:2] if sip else []}")

            if midurlinfo and midurlinfo[0].get('purl') and sip:
                purl = midurlinfo[0]['purl']
                # 完全照搬参考项目：sip[1] + purl，再替换 http 为 https
                sip_index = 1 if len(sip) > 1 else 0
                music_url = sip[sip_index] + purl
                music_url = music_url.replace('http://', 'https://')
                logger.info(f"[{self.platform_name}] 官方音质 {quality} → {filename}, url长度={len(music_url)}")
                return {
                    'url': music_url,
                    'quality': quality,
                    'song_id': song_id,
                    'source': 'qq',
                    'fileType': ext.lstrip('.')
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
            # 歌曲详情接口需要登录态才能看到 user 收藏、VIP 标识等信息
            detail_headers = {'Referer': 'https://y.qq.com/portal/player.html'}
            if self.cookie:
                detail_headers['Cookie'] = self.cookie
            resp = self.session.get(url, params=params, headers=detail_headers, timeout=10)
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
    
    def get_playlist(self, playlist_id: int, limit: int = 0) -> Dict[str, Any]:
        """获取歌单"""
        all_tracks = []
        total_songs = 0
        
        # 使用分页API获取完整歌曲列表
        url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
        
        # 准备请求头，添加cookie
        headers = {
            'Referer': f'https://y.qq.com/n/ryqq/playlist/{playlist_id}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36'
        }
        if self.cookie:
            headers['Cookie'] = self.cookie
        
        try:
            # 先获取基本信息
            basic_url = "https://c.y.qq.com/qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
            basic_params = {
                'disstid': str(playlist_id),
                'type': '1',
                'json': '1',
                'utf8': '1',
                'onlysong': '0',
                'format': 'json'
            }
            
            resp = self.session.get(basic_url, params=basic_params, headers=headers, timeout=15)
            resp.raise_for_status()
            basic_data = resp.json()

            # 检测隐私保护错误（subcode=4000 = check privacy error）
            subcode = basic_data.get('subcode', 0)
            msg = basic_data.get('msg', '')
            if subcode == 4000 or 'privacy' in msg.lower():
                logger.warning(f"[{self.platform_name}] 歌单 {playlist_id} 设置了隐私保护: {msg}")
                return {'__error__': 'privacy', '__message__': f'该歌单已设置隐私保护，无法查看（{msg}）'}

            cdlist = basic_data.get('cdlist', [])
            if not cdlist:
                logger.warning(f"[{self.platform_name}] 歌单 {playlist_id} 返回为空，code={basic_data.get('code')}, subcode={subcode}, msg={msg}")
                if subcode and subcode != 0:
                    return {'__error__': 'api_error', '__message__': f'QQ音乐API错误(subcode={subcode}): {msg}'}
                return {'__error__': 'empty', '__message__': '歌单不存在或需要登录'}

            playlist_info = cdlist[0]
            total_songs = playlist_info.get('songnum', 0)
            songlist = playlist_info.get('songlist', [])
            
            # 添加第一页歌曲
            for item in songlist:
                singer_name = '/'.join([s.get('name', '') for s in item.get('singer', []) if isinstance(s, dict)])
                album_name = self._safe_extract(item, ['album', 'title'], '') or item.get('albumname', '')
                album_mid = self._safe_extract(item, ['album', 'mid'], '') or item.get('albummid', '')
                pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''
                
                all_tracks.append({
                    'id': item.get('songmid', ''),
                    'name': item.get('songname', ''),
                    'artists': singer_name,
                    'album': album_name,
                    'picUrl': pic_url,
                    'source': 'qq'
                })
            
            # 如果歌曲数大于已获取的数量，尝试分页获取
            if total_songs > len(all_tracks):
                page = 2
                while len(all_tracks) < total_songs and page <= 10:  # 最多获取10页
                    try:
                        payload = {
                            "comm": {"ct": 24, "cv": 0},
                            "playlist": {
                                "module": "music.pf_song_detail_comm",
                                "method": "get_song_detail_songinfo",
                                "param": {
                                    "song_mid_list": [str(playlist_id)],
                                    "song_id_list": []
                                }
                            }
                        }
                        # 歌单分页也要带 cookie
                        page_headers = dict(self.default_search_headers)
                        if self.cookie:
                            page_headers['Cookie'] = self.cookie
                        page_resp = self.session.post(url, data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                                                headers=page_headers, timeout=10)
                        if page_resp.status_code == 200:
                            page_data = page_resp.json()
                            track_list = self._safe_extract(page_data, ['playlist', 'data', 'track_list'], [])
                            if not track_list:
                                break
                            for item in track_list:
                                singer_name = '/'.join([s.get('name', '') for s in item.get('singer', []) if isinstance(s, dict)])
                                album_name = self._safe_extract(item, ['album', 'name'], '') or item.get('albumname', '')
                                album_mid = self._safe_extract(item, ['album', 'mid'], '') or item.get('albummid', '')
                                pic_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg?max_age=2592000" if album_mid else ''
                                
                                # 检查是否已存在
                                track_id = item.get('mid', '') or item.get('songmid', '')
                                if not any(t['id'] == track_id for t in all_tracks):
                                    all_tracks.append({
                                        'id': track_id,
                                        'name': item.get('name', '') or item.get('songname', ''),
                                        'artists': singer_name,
                                        'album': album_name,
                                        'picUrl': pic_url,
                                        'source': 'qq'
                                    })
                            if len(track_list) < 100:
                                break
                            page += 1
                        else:
                            break
                    except Exception as e:
                        logger.debug(f"[{self.platform_name}] 分页获取歌曲失败: {e}")
                        break
            
            cover_mid = playlist_info.get('logo', '').replace('https://y.gtimg.cn/music/photo_new/T002R800x800M000', '').replace('.jpg', '')
            cover_url = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{cover_mid}.jpg?max_age=2592000" if cover_mid else playlist_info.get('logo', '')
            
            return {
                'id': playlist_info.get('dissid', 0),
                'name': playlist_info.get('dissname', ''),
                'coverImgUrl': cover_url,
                'description': playlist_info.get('desc', ''),
                'trackCount': total_songs if total_songs > 0 else len(all_tracks),
                'playCount': playlist_info.get('playcount', 0),
                'tracks': all_tracks,
                'source': 'qq'
            }
        except Exception as e:
            logger.error(f"[{self.platform_name}] 获取歌单信息失败: {e}")
            return {}


qq_client = QQClient()