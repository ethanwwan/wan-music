"""网易云音乐API模块 - 独立实现

包含三条数据源线路：
1. official - 官方API（优先）
2. xuanluoge - 第三方解析API
3. haitangw - 第三方解析API

支持前端指定数据源，统一音质等级。
集成了Cookie管理和二维码登录功能。
"""

import json
import urllib.parse
import logging
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from hashlib import md5
from enum import Enum
from pathlib import Path
from datetime import datetime

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# 数据结构标准化辅助函数
def _normalize_artist(item: Dict[str, Any]) -> Dict[str, Any]:
    """标准化单个歌手数据"""
    return {
        'id': item.get('id', 0),
        'name': item.get('name', ''),
        'avatarUrl': item.get('avatarUrl') or item.get('picUrl') or '',
        'picUrl': item.get('picUrl') or item.get('avatarUrl') or '',
        'musicCount': item.get('musicCount') or item.get('songCount') or item.get('musicSize') or 0,
        'songCount': item.get('songCount') or item.get('musicCount') or item.get('musicSize') or 0,
        'albumCount': item.get('albumCount') or item.get('albumSize') or 0,
        'fansCount': item.get('fansCount') or item.get('fansSize') or 0,
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
        'artistName': item.get('artistName') or artist_data.get('name') or artist_data.get('nickname') or '',
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
    artists = item.get('artists') or item.get('ar') or []
    artist_names = [a.get('name', '') for a in artists]
    artist_str = '/'.join(filter(None, artist_names))
    album_data = item.get('album') or item.get('al') or {}
    
    return {
        'id': item.get('id', 0),
        'name': item.get('name', ''),
        'artists': artist_str or item.get('artists') or item.get('artist') or '',
        'artist': artist_str or item.get('artist') or '',
        'album': album_data.get('name', '') or item.get('album') or '',
        'picUrl': album_data.get('picUrl') or album_data.get('coverImgUrl') or item.get('picUrl') or '',
        'coverImgUrl': album_data.get('coverImgUrl') or album_data.get('picUrl') or item.get('coverImgUrl') or '',
        'duration': item.get('duration') or item.get('dt') or 0,
        'url': item.get('url') or '',
        'lrc': item.get('lrc') or ''
    }

# 配置日志
logger = logging.getLogger(__name__)


class CookieException(Exception):
    """Cookie相关异常类"""
    pass


class CookieManager:
    """Cookie管理器"""
    
    def __init__(self, cookie_file: str = "cookie.txt"):
        self.cookie_file = Path(cookie_file)
        self.important_cookies = {
            'MUSIC_U', 'MUSIC_A', '__csrf', 'NMTID', 'WEVNSM', 'WNMCID'
        }
        self._ensure_cookie_file_exists()
    
    def _ensure_cookie_file_exists(self) -> None:
        if not self.cookie_file.exists():
            self.cookie_file.touch()
            logger.info(f"创建Cookie文件: {self.cookie_file}")
    
    def read_cookie(self) -> str:
        try:
            if not self.cookie_file.exists():
                return ""
            content = self.cookie_file.read_text(encoding='utf-8').strip()
            return content
        except Exception as e:
            raise CookieException(f"读取Cookie文件失败: {e}")
    
    def write_cookie(self, cookie_content: str) -> bool:
        try:
            if not cookie_content or not cookie_content.strip():
                raise CookieException("Cookie内容不能为空")
            self.cookie_file.write_text(cookie_content.strip(), encoding='utf-8')
            logger.info(f"成功写入Cookie到文件: {self.cookie_file}")
            return True
        except Exception as e:
            raise CookieException(f"写入Cookie文件失败: {e}")
    
    def parse_cookies(self) -> Dict[str, str]:
        try:
            cookie_content = self.read_cookie()
            return self.parse_cookie_string(cookie_content)
        except Exception as e:
            raise CookieException(f"解析Cookie失败: {e}")
    
    def parse_cookie_string(self, cookie_string: str) -> Dict[str, str]:
        if not cookie_string or not cookie_string.strip():
            return {}
        
        cookies = {}
        try:
            cookie_string = cookie_string.strip()
            cookie_pairs = []
            if ';' in cookie_string:
                cookie_pairs = cookie_string.split(';')
            elif '\n' in cookie_string:
                cookie_pairs = cookie_string.split('\n')
            else:
                cookie_pairs = [cookie_string]
            
            for pair in cookie_pairs:
                pair = pair.strip()
                if not pair or '=' not in pair:
                    continue
                key, value = pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    cookies[key] = value
            return cookies
        except Exception as e:
            logger.error(f"解析Cookie字符串失败: {e}")
            return {}
    
    def is_cookie_valid(self) -> bool:
        try:
            cookies = self.parse_cookies()
            if not cookies:
                return False
            missing_cookies = self.important_cookies - set(cookies.keys())
            if missing_cookies:
                logger.warning(f"缺少重要Cookie: {missing_cookies}")
                return False
            music_u = cookies.get('MUSIC_U', '')
            if not music_u or len(music_u) < 10:
                return False
            return True
        except Exception as e:
            logger.error(f"Cookie验证失败: {e}")
            return False
    
    def get_cookie_for_request(self) -> Dict[str, str]:
        try:
            cookies = self.parse_cookies()
            return {k: v for k, v in cookies.items() if k and v}
        except Exception as e:
            logger.error(f"获取请求Cookie失败: {e}")
            return {}
    
    def backup_cookie(self, backup_suffix: str = None) -> str:
        try:
            if not self.cookie_file.exists():
                raise CookieException("Cookie文件不存在")
            if backup_suffix is None:
                backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.cookie_file.with_suffix(f".{backup_suffix}.bak")
            content = self.cookie_file.read_text(encoding='utf-8')
            backup_path.write_text(content, encoding='utf-8')
            logger.info(f"Cookie备份成功: {backup_path}")
            return str(backup_path)
        except Exception as e:
            raise CookieException(f"备份Cookie失败: {e}")
    
    def clear_cookie(self) -> bool:
        try:
            if self.cookie_file.exists():
                self.cookie_file.write_text("", encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"清空Cookie失败: {e}")
            return False


class QRLoginManager:
    """二维码登录管理器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36',
            'Referer': 'https://music.163.com/'
        })
    
    def create_qr_login(self) -> Dict[str, Any]:
        """创建二维码登录"""
        try:
            url = "https://music.163.com/api/login/qrcode/unikey"
            response = self.session.post(url, data={'type': 1})
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 200:
                return {
                    'success': True,
                    'qr_key': data.get('unikey'),
                    'message': '二维码生成成功'
                }
            else:
                return {
                    'success': False,
                    'message': data.get('message', '生成二维码失败')
                }
        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            return {'success': False, 'message': str(e)}
    
    def check_qr_login(self, qr_key: str) -> Dict[str, Any]:
        """检查二维码登录状态"""
        try:
            url = f"https://music.163.com/api/login/qrcode/client/login?key={qr_key}"
            response = self.session.post(url)
            response.raise_for_status()
            data = response.json()
            
            code = data.get('code', -1)
            
            if code == 800:
                return {'success': True, 'status': 'expired', 'message': '二维码已过期'}
            elif code == 801:
                return {'success': True, 'status': 'waiting', 'message': '等待扫码'}
            elif code == 802:
                return {'success': True, 'status': 'scanned', 'message': '已扫码，等待确认'}
            elif code == 803:
                cookie = response.headers.get('Set-Cookie', '')
                return {
                    'success': True,
                    'status': 'success',
                    'message': '登录成功',
                    'cookie': cookie
                }
            elif code == 400:
                return {'success': False, 'status': 'error', 'message': '请求参数错误'}
            else:
                return {'success': False, 'status': 'error', 'message': data.get('message', '未知错误')}
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return {'success': False, 'status': 'error', 'message': str(e)}


class NeteaseDataSource(Enum):
    """网易云数据源枚举"""
    OFFICIAL = "official"        # 官方API
    XUANLUOGE = "xuanluoge"      # xuanluoge第三方API
    HAITANGW = "haitangw"        # haitangw第三方API


class QualityLevel(Enum):
    """音质等级枚举"""
    STANDARD = "standard"      # 标准音质
    EXHIGH = "exhigh"          # 极高音质
    LOSSLESS = "lossless"      # 无损音质
    HIRES = "hires"            # Hi-Res音质
    SKY = "sky"                # 沉浸环绕声
    JYEFFECT = "jyeffect"      # 高清环绕声
    JYMASTER = "jymaster"      # 超清母带
    DOLBY = "dolby"            # 杜比全景声


# 常量定义
class APIConstants:
    """API相关常量"""
    AES_KEY = b"e82ckenh8dichen8"
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154'
    REFERER = 'https://music.163.com/'
    
    # 官方API URLs
    SONG_URL_V1 = "https://interface3.music.163.com/eapi/song/enhance/player/url/v1"
    SONG_DETAIL_V3 = "https://interface3.music.163.com/api/v3/song/detail"
    LYRIC_API = "https://interface3.music.163.com/api/song/lyric"
    SEARCH_API = 'https://music.163.com/api/cloudsearch/pc'
    PLAYLIST_DETAIL_API = 'https://music.163.com/api/v6/playlist/detail'
    ALBUM_DETAIL_API = 'https://music.163.com/api/v1/album/'
    ARTIST_TOP_SONG_API = 'https://music.163.com/api/artist/top/song'
    
    # 默认配置
    DEFAULT_COOKIES = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!"
    }
    
    # 第三方API配置
    XUANLUOGE_URL = "http://118.24.104.108:3456/api.php"
    HAITANGW_URL = "https://musicapi.haitangw.net/music/wy.php"


class CryptoUtils:
    """加密工具类"""
    
    @staticmethod
    def hex_digest(data: bytes) -> str:
        """将字节数据转换为十六进制字符串"""
        return "".join([hex(d)[2:].zfill(2) for d in data])
    
    @staticmethod
    def hash_digest(text: str) -> bytes:
        """计算MD5哈希值"""
        return md5(text.encode("utf-8")).digest()
    
    @staticmethod
    def hash_hex_digest(text: str) -> str:
        """计算MD5哈希值并转换为十六进制字符串"""
        return CryptoUtils.hex_digest(CryptoUtils.hash_digest(text))
    
    @staticmethod
    def encrypt_params(url: str, payload: Dict[str, Any]) -> str:
        """加密请求参数"""
        url_path = urllib.parse.urlparse(url).path.replace("/eapi/", "/api/")
        digest = CryptoUtils.hash_hex_digest(f"nobody{url_path}use{json.dumps(payload)}md5forencrypt")
        params = f"{url_path}-36cd479b6b5-{json.dumps(payload)}-36cd479b6b5-{digest}"
        
        # AES加密
        padder = padding.PKCS7(algorithms.AES(APIConstants.AES_KEY).block_size).padder()
        padded_data = padder.update(params.encode()) + padder.finalize()
        cipher = Cipher(algorithms.AES(APIConstants.AES_KEY), modes.ECB())
        encryptor = cipher.encryptor()
        enc = encryptor.update(padded_data) + encryptor.finalize()
        
        return CryptoUtils.hex_digest(enc)


class NeteaseAPIClient:
    """网易云音乐API客户端，支持多数据源"""
    
    def __init__(self):
        """初始化客户端"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/'
        })
        self.session.cookies.update(APIConstants.DEFAULT_COOKIES)
    
    def search(self, keyword: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """搜索歌曲（统一使用官方API）"""
        url = APIConstants.SEARCH_API
        params = {
            's': keyword,
            'type': 1,
            'limit': limit,
            'offset': offset
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            songs = []
            for item in data.get('result', {}).get('songs', []):
                songs.append({
                    'id': item['id'],
                    'name': item['name'],
                    'artists': '/'.join([a['name'] for a in item['ar']]),
                    'album': item['al']['name'],
                    'picUrl': item['al']['picUrl'],
                    'artist_string': '/'.join([a['name'] for a in item['ar']])
                })
            return songs
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def search_artist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌手（使用网易云官方模糊匹配）"""
        url = "https://music.163.com/api/search/get"
        data = {
            's': keyword,
            'type': 100,
            'limit': limit,
            'offset': 0
        }
        
        try:
            response = self.session.post(url, data=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            # 使用网易云官方模糊匹配结果，直接标准化返回
            return [_normalize_artist(item) for item in result.get('result', {}).get('artists', [])][:limit]
        except Exception as e:
            logger.error(f"搜索歌手失败: {e}")
            return []
    
    def search_playlist(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        url = APIConstants.SEARCH_API
        params = {
            's': keyword,
            'type': 1000,
            'limit': limit,
            'offset': 0
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            return [_normalize_playlist(item) for item in result.get('result', {}).get('playlists', [])]
        except Exception as e:
            logger.error(f"搜索歌单失败: {e}")
            return []
    
    def search_album(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索专辑"""
        url = APIConstants.SEARCH_API
        params = {
            's': keyword,
            'type': 10,
            'limit': limit,
            'offset': 0
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            return [_normalize_album(item) for item in result.get('result', {}).get('albums', [])]
        except Exception as e:
            logger.error(f"搜索专辑失败: {e}")
            return []
    
    def get_artist_detail(self, artist_id: int) -> Dict[str, Any]:
        """获取歌手详情和热门歌曲"""
        url = APIConstants.ARTIST_TOP_SONG_API
        params = {
            'id': artist_id,
            'csrf_token': ''
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            artist_info = {}
            songs = []
            
            # 从热门歌曲中提取歌手信息
            if data.get('songs') and len(data['songs']) > 0:
                first_song = data['songs'][0]
                # 找到匹配的歌手
                for ar in first_song.get('ar', []):
                    if ar.get('id') == artist_id:
                        artist_info = {
                            'id': ar.get('id', 0),
                            'name': ar.get('name', ''),
                            'picUrl': '',
                            'avatarUrl': '',
                            'musicCount': 0,
                            'albumCount': 0,
                            'fansCount': 0,
                            'desc': '',
                            'alias': []
                        }
                        break
            
            if data.get('songs'):
                songs = [_normalize_track(song) for song in data['songs']]
            
            return {'artist': artist_info, 'songs': songs}
        except Exception as e:
            logger.error(f"获取歌手详情失败: {e}")
            return {'artist': {}, 'songs': []}
    
    def get_song_url_official(self, song_id: int, quality: str) -> Optional[str]:
        """使用官方API获取歌曲URL"""
        try:
            logger.info(f"[测试日志] 开始使用官方API获取歌曲URL - song_id={song_id}, quality={quality}")
            
            payload = {
                "ids": [song_id],
                "level": quality,
                "encodeType": "flac" if quality in ['lossless', 'hires', 'jymaster'] else "mp3"
            }
            params = CryptoUtils.encrypt_params(APIConstants.SONG_URL_V1, payload)
            
            headers = {
                'User-Agent': APIConstants.USER_AGENT,
                'Referer': APIConstants.REFERER,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            logger.debug(f"[测试日志] 官方API请求 - URL={APIConstants.SONG_URL_V1}, payload={payload}")
            
            response = requests.post(
                APIConstants.SONG_URL_V1,
                data=f"params={params}",
                headers=headers,
                cookies=APIConstants.DEFAULT_COOKIES.copy(),
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"[测试日志] 官方API响应 - status_code={response.status_code}, data_keys={list(data.keys())}")
            
            if data.get('data') and len(data['data']) > 0:
                url = data['data'][0].get('url')
                if url and url.startswith('http'):
                    logger.info(f"[测试日志] 官方API成功获取歌曲URL - song_id={song_id}, url_length={len(url)}")
                    return url
                else:
                    logger.warning(f"[测试日志] 官方API返回空URL - song_id={song_id}, data={data}")
            else:
                logger.warning(f"[测试日志] 官方API返回数据为空或格式异常 - song_id={song_id}, data={data}")
            return None
        except Exception as e:
            logger.error(f"[测试日志] 官方API获取歌曲URL失败 - song_id={song_id}, error={str(e)}")
            return None
    
    def get_song_url_xuanluoge(self, song_id: int, quality: str) -> Optional[str]:
        """使用xuanluoge API获取歌曲URL"""
        try:
            logger.info(f"[测试日志] 开始使用xuanluoge API获取歌曲URL - song_id={song_id}, quality={quality}")
            
            url = f"{APIConstants.XUANLUOGE_URL}?miss=getMusicUrl&id={song_id}&level={quality}"
            logger.debug(f"[测试日志] xuanluoge API请求 - URL={url}")
            
            response = self.session.get(url, timeout=10, verify=False)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"[测试日志] xuanluoge API响应 - status_code={response.status_code}, data_type={type(data).__name__}")
            
            if isinstance(data, list):
                download_url = data[0].get('url', '') if data else ''
            else:
                download_url = data.get('data', [{}])[0].get('url', '')
            
            if download_url and download_url.startswith('http'):
                logger.info(f"[测试日志] xuanluoge API成功获取歌曲URL - song_id={song_id}, url_length={len(download_url)}")
                return download_url
            else:
                logger.warning(f"[测试日志] xuanluoge API返回空URL - song_id={song_id}, data={data}")
            return None
        except Exception as e:
            logger.error(f"[测试日志] xuanluoge API获取歌曲URL失败 - song_id={song_id}, error={str(e)}")
            return None
    
    def get_song_url_haitangw(self, song_id: int, quality: str) -> Optional[str]:
        """使用haitangw API获取歌曲URL"""
        try:
            logger.info(f"[测试日志] 开始使用haitangw API获取歌曲URL - song_id={song_id}, quality={quality}")
            
            url = f"{APIConstants.HAITANGW_URL}?id={song_id}&level={quality}&type=json"
            logger.debug(f"[测试日志] haitangw API请求 - URL={url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"[测试日志] haitangw API响应 - status_code={response.status_code}, data_keys={list(data.keys())}")
            
            download_url = data.get('data', {}).get('url', '')
            if download_url and download_url.startswith('http'):
                logger.info(f"[测试日志] haitangw API成功获取歌曲URL - song_id={song_id}, url_length={len(download_url)}")
                return download_url
            else:
                logger.warning(f"[测试日志] haitangw API返回空URL - song_id={song_id}, data={data}")
            return None
        except Exception as e:
            logger.error(f"[测试日志] haitangw API获取歌曲URL失败 - song_id={song_id}, error={str(e)}")
            return None
    
    def get_song_url(self, song_id: int, quality: str, data_source: str) -> Dict[str, Any]:
        """获取歌曲下载链接（根据指定数据源，支持自动回退）"""
        logger.info(f"[测试日志] ===== 开始获取歌曲URL ===== song_id={song_id}, quality={quality}, data_source={data_source}")
        
        # 验证音质参数
        valid_qualities = [q.value for q in QualityLevel]
        if quality not in valid_qualities:
            logger.warning(f"[测试日志] 无效音质参数 '{quality}'，使用默认值 'lossless'")
            quality = 'lossless'
        
        # 数据源函数映射
        source_func_map = {
            'official': self.get_song_url_official,
            'xuanluoge': self.get_song_url_xuanluoge,
            'haitangw': self.get_song_url_haitangw
        }
        
        # 获取指定数据源的函数
        source_func = source_func_map.get(data_source)
        if not source_func:
            logger.error(f"[测试日志] 无效的数据源: {data_source}")
            raise ValueError(f"无效的数据源: {data_source}")
        
        logger.info(f"[测试日志] 将尝试数据源: {data_source}")
        
        # 首先尝试用户指定的数据源
        download_url = source_func(song_id, quality)
        
        if download_url:
            logger.info(f"[测试日志] ===== 成功获取歌曲URL ===== song_id={song_id}, source={data_source}, url_length={len(download_url)}")
            return {
                'url': download_url,
                'quality': quality,
                'source': data_source,
                'song_id': song_id
            }
        
        # 如果指定数据源失败，尝试其他数据源
        logger.warning(f"[测试日志] 指定数据源 {data_source} 失败，开始尝试备用数据源...")
        other_sources = [key for key in source_func_map.keys() if key != data_source]
        
        for source in other_sources:
            try:
                logger.info(f"[测试日志] 尝试备用数据源: {source}")
                fallback_url = source_func_map[source](song_id, quality)
                if fallback_url:
                    logger.info(f"[测试日志] ===== 备用数据源成功 ===== song_id={song_id}, original_source={data_source}, fallback_source={source}, url_length={len(fallback_url)}")
                    return {
                        'url': fallback_url,
                        'quality': quality,
                        'source': source,
                        'song_id': song_id,
                        'fallback': True
                    }
                else:
                    logger.warning(f"[测试日志] 备用数据源 {source} 也返回空URL")
            except Exception as e:
                logger.warning(f"[测试日志] 备用数据源 {source} 调用失败: {e}")
        
        logger.error(f"[测试日志] ===== 所有数据源均失败 ===== song_id={song_id}, requested_source={data_source}")
        raise Exception(f"所有数据源均无法获取歌曲 {song_id} 的下载链接")
    
    def get_song_detail(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲详情"""
        url = APIConstants.SONG_DETAIL_V3
        params = {'ids': f'[{song_id}]'}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"获取歌曲详情失败: {e}")
            return {}
    
    def get_lyric(self, song_id: int) -> Dict[str, Any]:
        """获取歌词"""
        url = APIConstants.LYRIC_API
        params = {
            'id': song_id,
            'lv': -1,
            'tv': -1
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"获取歌词失败: {e}")
            return {}
    
    def get_playlist_detail(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单详情"""
        url = APIConstants.PLAYLIST_DETAIL_API
        params = {'id': playlist_id}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 检查网易云API返回的错误码
            if data.get('code') != 200:
                logger.error(f"网易云API返回错误: code={data.get('code')}, message={data.get('message')}")
                raise Exception(f"获取歌单失败: {data.get('message', '未知错误')}")
            
            # 网易云歌单API返回的结构是: {"result": {...}, "code": 200}
            # 需要从result字段中提取歌单信息
            playlist_info = data.get('result', data)
            
            # 标准化歌单信息
            playlist_info = _normalize_playlist(playlist_info)
            
            # 标准化tracks数据
            if 'tracks' in playlist_info and isinstance(playlist_info['tracks'], list):
                playlist_info['tracks'] = [_normalize_track(track) for track in playlist_info['tracks']]
            
            return playlist_info
        except Exception as e:
            logger.error(f"获取歌单详情失败: {e}")
            return {}
    
    def get_album_detail(self, album_id: int) -> Dict[str, Any]:
        """获取专辑详情"""
        url = f"{APIConstants.ALBUM_DETAIL_API}{album_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 网易云专辑API返回的结构是: {"album": {...}, "songs": [...]}
            # 需要提取专辑信息并将songs转换为tracks
            album_info = data.get('album', data)
            
            # 标准化专辑信息
            album_info = _normalize_album(album_info)
            
            # 处理歌曲列表：网易云API返回的是songs，需要转换为tracks
            tracks = data.get('songs', data.get('tracks', []))
            if isinstance(tracks, list):
                album_info['tracks'] = [_normalize_track(track) for track in tracks]
            else:
                album_info['tracks'] = []
            
            return album_info
        except Exception as e:
            logger.error(f"获取专辑详情失败: {e}")
            return {}
    
    @staticmethod
    def get_available_sources() -> List[Dict[str, str]]:
        """获取可用数据源列表"""
        return [
            {'value': 'official', 'label': '官方API', 'description': '直接调用网易云官方API，速度快'},
            {'value': 'xuanluoge', 'label': 'xuanluoge', 'description': '第三方解析API，支持无损音质'},
            {'value': 'haitangw', 'label': 'haitangw', 'description': '第三方解析API，稳定性好'}
        ]


# 创建全局客户端实例
netease_client = NeteaseAPIClient()
