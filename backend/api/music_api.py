"""网易云音乐API模块

提供网易云音乐相关API接口的封装，包括：
- 音乐URL获取
- 歌曲详情获取
- 歌词获取
- 搜索功能
- 歌单和专辑详情
- 二维码登录
"""

import json
import urllib.parse
import time
import logging
from random import randrange
from typing import Dict, List, Optional, Tuple, Any
from hashlib import md5
from enum import Enum

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# 配置日志
logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """音质等级枚举"""
    STANDARD = "standard"      # 标准音质
    EXHIGH = "exhigh"          # 极高音质
    LOSSLESS = "lossless"      # 无损音质
    HIRES = "hires"            # Hi-Res音质
    SKY = "sky"                # 沉浸环绕声
    JYEFFECT = "jyeffect"      # 高清环绕声
    JYMASTER = "jymaster"      # 超清母带
    DOLBY = "dolby"      # 杜比全景声


# 常量定义
class APIConstants:
    """API相关常量"""
    AES_KEY = b"e82ckenh8dichen8"
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154'
    REFERER = 'https://music.163.com/'
    
    # API URLs
    SONG_URL_V1 = "https://interface3.music.163.com/eapi/song/enhance/player/url/v1"
    SONG_DETAIL_V3 = "https://interface3.music.163.com/api/v3/song/detail"
    LYRIC_API = "https://interface3.music.163.com/api/song/lyric"
    SEARCH_API = 'https://music.163.com/api/cloudsearch/pc'
    PLAYLIST_DETAIL_API = 'https://music.163.com/api/v6/playlist/detail'
    ALBUM_DETAIL_API = 'https://music.163.com/api/v1/album/'
    QR_UNIKEY_API = 'https://interface3.music.163.com/eapi/login/qrcode/unikey'
    QR_LOGIN_API = 'https://interface3.music.163.com/eapi/login/qrcode/client/login'
    ARTIST_TOP_SONG_API = 'https://music.163.com/api/artist/top/song'
    
    # 默认配置
    DEFAULT_CONFIG = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!"
    }
    
    DEFAULT_COOKIES = {
        "os": "pc",
        "appver": "",
        "osver": "",
        "deviceId": "pyncm!"
    }


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


class HTTPClient:
    """HTTP客户端类"""
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 3]  # 每次重试的等待时间（秒）
    
    @staticmethod
    def _is_retryable_error(e: Exception) -> bool:
        """判断错误是否应该重试"""
        if isinstance(e, requests.exceptions.Timeout):
            return True
        if isinstance(e, requests.exceptions.ConnectionError):
            return True
        return False
    
    @staticmethod
    def post_request_with_retry(url: str, params: str, cookies: Dict[str, str], 
                                  retries: int = None) -> str:
        """发送POST请求并返回文本响应，支持重试
        
        Args:
            url: 请求URL
            params: 加密参数
            cookies: Cookie字典
            retries: 最大重试次数，默认使用 MAX_RETRIES
            
        Returns:
            响应文本
            
        Raises:
            APIException: 重试次数用尽后抛出
        """
        if retries is None:
            retries = HTTPClient.MAX_RETRIES
            
        headers = {
            'User-Agent': APIConstants.USER_AGENT,
            'Referer': APIConstants.REFERER,
        }
        
        request_cookies = APIConstants.DEFAULT_COOKIES.copy()
        request_cookies.update(cookies)
        
        last_error = None
        for attempt in range(retries):
            try:
                response = requests.post(url, headers=headers, cookies=request_cookies, 
                                        data={"params": params}, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                last_error = e
                # 只有可重试的错误才进行重试
                if HTTPClient._is_retryable_error(e) and attempt < retries - 1:
                    delay = HTTPClient.RETRY_DELAYS[attempt]
                    logger.warning(f"API请求失败 (尝试 {attempt + 1}/{retries}): {e}, {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    raise APIException(f"HTTP请求失败: {e}")
        
        # 不应该到达这里，但以防万一
        raise APIException(f"HTTP请求失败: {last_error}")
    
    @staticmethod
    def post_request(url: str, params: str, cookies: Dict[str, str]) -> str:
        """发送POST请求并返回文本响应（带重试）"""
        return HTTPClient.post_request_with_retry(url, params, cookies)
    
    @staticmethod
    def post_request_full(url: str, params: str, cookies: Dict[str, str]) -> requests.Response:
        """发送POST请求并返回完整响应对象（带重试）"""
        headers = {
            'User-Agent': APIConstants.USER_AGENT,
            'Referer': APIConstants.REFERER,
        }
        
        request_cookies = APIConstants.DEFAULT_COOKIES.copy()
        request_cookies.update(cookies)
        
        last_error = None
        for attempt in range(HTTPClient.MAX_RETRIES):
            try:
                response = requests.post(url, headers=headers, cookies=request_cookies, 
                                       data={"params": params}, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_error = e
                if HTTPClient._is_retryable_error(e) and attempt < HTTPClient.MAX_RETRIES - 1:
                    delay = HTTPClient.RETRY_DELAYS[attempt]
                    logger.warning(f"API请求失败 (尝试 {attempt + 1}/{HTTPClient.MAX_RETRIES}): {e}, {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    raise APIException(f"HTTP请求失败: {e}")
        
        raise APIException(f"HTTP请求失败: {last_error}")
    
    @staticmethod
    def post_with_retry(url: str, data: Dict = None, cookies: Dict[str, str] = None, timeout: int = 30) -> requests.Response:
        """发送POST请求并返回响应对象（带重试）"""
        headers = {
            'User-Agent': APIConstants.USER_AGENT,
            'Referer': APIConstants.REFERER,
        }
        
        request_cookies = APIConstants.DEFAULT_COOKIES.copy()
        if cookies:
            request_cookies.update(cookies)
        
        last_error = None
        for attempt in range(HTTPClient.MAX_RETRIES):
            try:
                response = requests.post(url, headers=headers, cookies=request_cookies, 
                                       data=data, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_error = e
                if HTTPClient._is_retryable_error(e) and attempt < HTTPClient.MAX_RETRIES - 1:
                    delay = HTTPClient.RETRY_DELAYS[attempt]
                    logger.warning(f"POST请求失败 (尝试 {attempt + 1}/{HTTPClient.MAX_RETRIES}): {e}, {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    raise APIException(f"POST请求失败: {e}")
        
        raise APIException(f"POST请求失败: {last_error}")
    
    @staticmethod
    def get_with_retry(url: str, cookies: Dict[str, str] = None, timeout: int = 30) -> requests.Response:
        """发送GET请求并返回响应对象（带重试）"""
        headers = {
            'User-Agent': APIConstants.USER_AGENT,
            'Referer': APIConstants.REFERER,
        }
        
        request_cookies = APIConstants.DEFAULT_COOKIES.copy()
        if cookies:
            request_cookies.update(cookies)
        
        last_error = None
        for attempt in range(HTTPClient.MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, cookies=request_cookies, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_error = e
                if HTTPClient._is_retryable_error(e) and attempt < HTTPClient.MAX_RETRIES - 1:
                    delay = HTTPClient.RETRY_DELAYS[attempt]
                    logger.warning(f"GET请求失败 (尝试 {attempt + 1}/{HTTPClient.MAX_RETRIES}): {e}, {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    raise APIException(f"GET请求失败: {e}")
        
        raise APIException(f"GET请求失败: {last_error}")


class APIException(Exception):
    """API异常类"""
    pass


class NeteaseAPI:
    """网易云音乐API主类"""
    
    def __init__(self):
        self.http_client = HTTPClient()
        self.crypto_utils = CryptoUtils()
    
    def get_song_url(self, song_id: int, quality: str, cookies: Dict[str, str]) -> Dict[str, Any]:
        """获取歌曲播放URL
        
        Args:
            song_id: 歌曲ID
            quality: 音质等级 (standard, exhigh, lossless, hires, sky, jyeffect, jymaster)
            cookies: 用户cookies
            
        Returns:
            包含歌曲URL信息的字典
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            config = APIConstants.DEFAULT_CONFIG.copy()
            config["requestId"] = str(randrange(20000000, 30000000))
            
            payload = {
                'ids': [song_id],
                'level': quality,
                'encodeType': 'flac',
                'header': json.dumps(config),
            }
            
            if quality == 'sky':
                payload['immerseType'] = 'c51'
            
            params = self.crypto_utils.encrypt_params(APIConstants.SONG_URL_V1, payload)
            response_text = self.http_client.post_request(APIConstants.SONG_URL_V1, params, cookies)
            
            result = json.loads(response_text)
            if result.get('code') != 200:
                raise APIException(f"获取歌曲URL失败: {result.get('message', '未知错误')}")
            
            return result
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析响应数据失败: {e}")
    
    def get_song_detail(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲详细信息
        
        Args:
            song_id: 歌曲ID
            
        Returns:
            包含歌曲详细信息的字典
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            data = {'c': json.dumps([{"id": song_id, "v": 0}])}
            response = HTTPClient.post_with_retry(APIConstants.SONG_DETAIL_V3, data=data)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"获取歌曲详情失败: {result.get('message', '未知错误')}")
            
            return result
        except APIException:
            raise
        except json.JSONDecodeError as e:
            raise APIException(f"解析歌曲详情响应失败: {e}")
    
    def get_lyric(self, song_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        """获取歌词信息
        
        Args:
            song_id: 歌曲ID
            cookies: 用户cookies
            
        Returns:
            包含歌词信息的字典
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            data = {
                'id': song_id, 
                'cp': 'false', 
                'tv': '0', 
                'lv': '0', 
                'rv': '0', 
                'kv': '0', 
                'yv': '0', 
                'ytv': '0', 
                'yrv': '0'
            }
            
            response = HTTPClient.post_with_retry(APIConstants.LYRIC_API, data=data, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"获取歌词失败: {result.get('message', '未知错误')}")
            
            return result
        except APIException:
            raise
        except json.JSONDecodeError as e:
            raise APIException(f"解析歌词响应失败: {e}")
    
    def search_music(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        """搜索音乐
        
        Args:
            keywords: 搜索关键词
            cookies: 用户cookies
            limit: 返回数量限制
            
        Returns:
            歌曲信息列表
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            data = {'s': keywords, 'type': 1, 'limit': limit}
            response = HTTPClient.post_with_retry(APIConstants.SEARCH_API, data=data, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"搜索失败: {result.get('message', '未知错误')}")
            
            songs = []
            for item in result.get('result', {}).get('songs', []):
                song_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'artists': '/'.join(artist['name'] for artist in item['ar']),
                    'album': item['al']['name'],
                    'picUrl': item['al']['picUrl']
                }
                songs.append(song_info)
            
            return songs
        except APIException:
            raise
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析搜索响应失败: {e}")
    
    def search_playlist(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        """搜索歌单
        
        Args:
            keywords: 搜索关键词
            cookies: 用户cookies
            limit: 返回数量限制
            
        Returns:
            歌单信息列表
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            data = {'s': keywords, 'type': 1000, 'limit': limit}
            response = HTTPClient.post_with_retry(APIConstants.SEARCH_API, data=data, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"搜索失败: {result.get('message', '未知错误')}")
            
            playlists = []
            for item in result.get('result', {}).get('playlists', []):
                playlist_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'creator': item['creator']['nickname'] if item.get('creator') else '',
                    'coverImgUrl': item['coverImgUrl'],
                    'trackCount': item['trackCount']
                }
                playlists.append(playlist_info)
            
            return playlists
        except APIException:
            raise
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析搜索响应失败: {e}")
    
    def search_album(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        """搜索专辑
        
        Args:
            keywords: 搜索关键词
            cookies: 用户cookies
            limit: 返回数量限制
            
        Returns:
            专辑信息列表
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            data = {'s': keywords, 'type': 10, 'limit': limit}
            response = HTTPClient.post_with_retry(APIConstants.SEARCH_API, data=data, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"搜索失败: {result.get('message', '未知错误')}")
            
            albums = []
            for item in result.get('result', {}).get('albums', []):
                album_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'artist': '/'.join(artist['name'] for artist in item.get('artists', [])),
                    'coverImgUrl': item['picUrl'],
                    'trackCount': item['size']
                }
                albums.append(album_info)
            
            return albums
        except APIException:
            raise
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析搜索响应失败: {e}")
    
    def search_artist(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        """搜索歌手
        
        Args:
            keywords: 搜索关键词
            cookies: 用户cookies
            limit: 返回数量限制
            
        Returns:
            歌手信息列表
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            data = {'s': keywords, 'type': 100, 'limit': limit}
            response = HTTPClient.post_with_retry(APIConstants.SEARCH_API, data=data, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"搜索失败: {result.get('message', '未知错误')}")
            
            artists = []
            for item in result.get('result', {}).get('artists', []):
                artist_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'avatarUrl': item.get('picUrl', item.get('img1v1Url', '')),
                    'musicCount': item.get('musicSize', 0)
                }
                artists.append(artist_info)
            
            return artists
        except APIException:
            raise
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析搜索响应失败: {e}")
    
    def get_artist_detail(self, artist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        """获取歌手详情（包含歌手信息和热门歌曲）
        
        Args:
            artist_id: 歌手ID
            cookies: 用户cookies
            
        Returns:
            包含歌手信息和歌曲列表的字典
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            # 使用网易云音乐官方API获取歌手热门歌曲
            headers = {
                'User-Agent': APIConstants.USER_AGENT,
                'Referer': APIConstants.REFERER
            }
            
            url = f"{APIConstants.ARTIST_TOP_SONG_API}?id={artist_id}"
            response = HTTPClient.get_with_retry(url, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"获取歌手详情失败: {result.get('message', '未知错误')}")
            
            # 解析歌手信息
            songs = result.get('songs', [])
            artist_info = {}
            
            if songs:
                # 根据请求的artist_id查找正确的歌手信息
                # 遍历歌曲，找到匹配的歌手
                found_artist = None
                for song in songs:
                    artists = song.get('ar', [])
                    for artist in artists:
                        if str(artist.get('id')) == str(artist_id):
                            found_artist = artist
                            break
                    if found_artist:
                        break
                
                # 如果找到匹配的歌手，使用其信息
                if found_artist:
                    artist_info['id'] = found_artist.get('id')
                    artist_info['name'] = found_artist.get('name')
                    artist_info['avatarUrl'] = found_artist.get('picUrl', '')
                    artist_info['musicCount'] = len(songs)
                else:
                    # 如果没有找到匹配的，使用第一首歌的第一个歌手作为 fallback
                    first_song = songs[0]
                    artists = first_song.get('ar', [])
                    if artists:
                        artist_info['id'] = artists[0].get('id')
                        artist_info['name'] = artists[0].get('name')
                        artist_info['avatarUrl'] = artists[0].get('picUrl', '')
                        artist_info['musicCount'] = len(songs)
            
            # 格式化歌曲列表
            formatted_songs = []
            for item in songs:
                album = item.get('al', {})
                song_artists = item.get('ar', [])
                
                formatted_songs.append({
                    'id': item['id'],
                    'name': item['name'],
                    'artist': '/'.join(a.get('name', '') for a in song_artists),
                    'album': album.get('name', ''),
                    'picUrl': album.get('picUrl', ''),
                    'duration': item.get('dt', 0)
                })
            
            return {
                'artist': artist_info,
                'songs': formatted_songs
            }
        except APIException:
            raise
        except Exception as e:
            raise APIException(f"获取歌手详情失败: {e}")
    
    def get_artist_top_songs(self, artist_id: int, cookies: Dict[str, str], limit: int = 50) -> List[Dict[str, Any]]:
        """获取歌手热门歌曲
        
        Args:
            artist_id: 歌手ID
            cookies: 用户cookies
            limit: 返回数量限制
            
        Returns:
            歌手热门歌曲列表
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            # 使用网易云音乐官方API获取歌手热门歌曲
            headers = {
                'User-Agent': APIConstants.USER_AGENT,
                'Referer': APIConstants.REFERER
            }
            
            url = f"{APIConstants.ARTIST_TOP_SONG_API}?id={artist_id}"
            response = HTTPClient.get_with_retry(url, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"获取歌手热门歌曲失败: {result.get('message', '未知错误')}")
            
            songs = []
            for item in result.get('songs', [])[:limit]:
                album = item.get('al', {})
                artists = item.get('ar', [])
                
                song_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'artists': '/'.join(artist.get('name', '') for artist in artists),
                    'album': album.get('name', ''),
                    'picUrl': album.get('picUrl', '')
                }
                songs.append(song_info)
            
            return songs
        except APIException:
            raise
        except Exception as e:
            raise APIException(f"获取歌手热门歌曲失败: {e}")
    
    def get_playlist_detail(self, playlist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        """获取歌单详情
        
        Args:
            playlist_id: 歌单ID
            cookies: 用户cookies
            
        Returns:
            歌单详情信息
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            data = {'id': playlist_id}
            response = HTTPClient.post_with_retry(APIConstants.PLAYLIST_DETAIL_API, data=data, cookies=cookies)
            
            result = response.json()
            if result.get('code') != 200:
                raise APIException(f"获取歌单详情失败: {result.get('message', '未知错误')}")
            
            playlist = result.get('playlist')
            if not playlist:
                # 打印调试信息
                logger.info(f"网易云API响应: {json.dumps(result)[:500]}")
                raise APIException("获取歌单详情失败: 歌单不存在或已被删除")
            info = {
                'id': playlist.get('id'),
                'name': playlist.get('name'),
                'coverImgUrl': playlist.get('coverImgUrl'),
                'creator': playlist.get('creator', {}).get('nickname', '') if playlist.get('creator') else '',
                'trackCount': playlist.get('trackCount'),
                'description': playlist.get('description', ''),
                'tracks': []
            }
            
            # 获取所有trackIds并分批获取详细信息
            track_ids = [str(t['id']) for t in playlist.get('trackIds', [])]
            for i in range(0, len(track_ids), 100):
                batch_ids = track_ids[i:i+100]
                song_data = {'c': json.dumps([{'id': int(sid), 'v': 0} for sid in batch_ids])}
                
                song_resp = HTTPClient.post_with_retry(APIConstants.SONG_DETAIL_V3, data=song_data, cookies=cookies)
                
                song_result = song_resp.json()
                for song in song_result.get('songs', []):
                    info['tracks'].append({
                        'id': song['id'],
                        'name': song['name'],
                        'artists': '/'.join(artist['name'] for artist in song['ar']),
                        'album': song['al']['name'],
                        'picUrl': song['al']['picUrl']
                    })
            
            return info
        except APIException:
            raise
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析歌单详情响应失败: {e}")
    
    def get_album_detail(self, album_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        """获取专辑详情
        
        Args:
            album_id: 专辑ID
            cookies: 用户cookies
            
        Returns:
            专辑详情信息
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            url = f'{APIConstants.ALBUM_DETAIL_API}{album_id}'
            response = HTTPClient.get_with_retry(url, cookies=cookies)
            
            logger.info(f"专辑API响应: code={response.json().get('code')}")
            result = response.json()
            
            if result.get('code') != 200:
                error_msg = result.get('message', '未知错误')
                logger.error(f"专辑API返回错误: {error_msg}")
                raise APIException(f"获取专辑详情失败: {error_msg}")
            
            album = result.get('album', {})
            info = {
                'id': album.get('id'),
                'name': album.get('name'),
                'coverImgUrl': self.get_pic_url(album.get('pic')),
                'artist': album.get('artist', {}).get('name', ''),
                'publishTime': album.get('publishTime'),
                'description': album.get('description', ''),
                'songs': []
            }
            
            for song in result.get('songs', []):
                info['songs'].append({
                    'id': song['id'],
                    'name': song['name'],
                    'artists': '/'.join(artist['name'] for artist in song['ar']),
                    'album': song['al']['name'],
                    'picUrl': self.get_pic_url(song['al'].get('pic'))
                })
            
            return info
        except APIException:
            raise
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析专辑详情响应失败: {e}")
    
    def netease_encrypt_id(self, id_str: str) -> str:
        """网易云加密图片ID算法
        
        Args:
            id_str: 图片ID字符串
            
        Returns:
            加密后的字符串
        """
        import base64
        import hashlib
        
        magic = list('3go8&$8*3*3h0k(2)2')
        song_id = list(id_str)
        
        for i in range(len(song_id)):
            song_id[i] = chr(ord(song_id[i]) ^ ord(magic[i % len(magic)]))
        
        m = ''.join(song_id)
        md5_bytes = hashlib.md5(m.encode('utf-8')).digest()
        result = base64.b64encode(md5_bytes).decode('utf-8')
        result = result.replace('/', '_').replace('+', '-')
        
        return result
    
    def get_pic_url(self, pic_id: Optional[int], size: int = 300) -> str:
        """获取网易云加密歌曲/专辑封面直链
        
        Args:
            pic_id: 封面ID
            size: 图片尺寸
            
        Returns:
            图片URL
        """
        if pic_id is None:
            return ''
        
        enc_id = self.netease_encrypt_id(str(pic_id))
        return f'https://p3.music.126.net/{enc_id}/{pic_id}.jpg?param={size}y{size}'


class QRLoginManager:
    """二维码登录管理器"""
    
    def __init__(self):
        self.http_client = HTTPClient()
        self.crypto_utils = CryptoUtils()
    
    def generate_qr_key(self) -> Optional[str]:
        """生成二维码的key
        
        Returns:
            成功返回unikey，失败返回None
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            config = APIConstants.DEFAULT_CONFIG.copy()
            config["requestId"] = str(randrange(20000000, 30000000))
            
            payload = {
                'type': 1,
                'header': json.dumps(config)
            }
            
            params = self.crypto_utils.encrypt_params(APIConstants.QR_UNIKEY_API, payload)
            response = self.http_client.post_request_full(APIConstants.QR_UNIKEY_API, params, {})
            
            result = json.loads(response.text)
            if result.get('code') == 200:
                return result.get('unikey')
            else:
                raise APIException(f"生成二维码key失败: {result.get('message', '未知错误')}")
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析二维码key响应失败: {e}")
    
    def create_qr_login(self) -> Optional[str]:
        """创建登录二维码并在控制台显示
        
        Returns:
            成功返回unikey，失败返回None
        """
        try:
            import qrcode
            
            unikey = self.generate_qr_key()
            if not unikey:
                print("生成二维码key失败")
                return None
            
            # 创建二维码
            qr = qrcode.QRCode()
            qr.add_data(f'https://music.163.com/login?codekey={unikey}')
            qr.make(fit=True)
            
            # 在控制台显示二维码
            qr.print_ascii(tty=True)
            print("\n请使用网易云音乐APP扫描上方二维码登录")
            return unikey
        except ImportError:
            print("请安装qrcode库: pip install qrcode")
            return None
        except Exception as e:
            print(f"创建二维码失败: {e}")
            return None
    
    def check_qr_login(self, unikey: str) -> Tuple[int, Dict[str, str]]:
        """检查二维码登录状态
        
        Args:
            unikey: 二维码key
            
        Returns:
            (登录状态码, cookie字典)
            
        Raises:
            APIException: API调用失败时抛出
        """
        try:
            config = APIConstants.DEFAULT_CONFIG.copy()
            config["requestId"] = str(randrange(20000000, 30000000))
            
            payload = {
                'key': unikey,
                'type': 1,
                'header': json.dumps(config)
            }
            
            params = self.crypto_utils.encrypt_params(APIConstants.QR_LOGIN_API, payload)
            response = self.http_client.post_request_full(APIConstants.QR_LOGIN_API, params, {})
            
            result = json.loads(response.text)
            cookie_dict = {}
            
            if result.get('code') == 803:
                # 登录成功，提取cookie
                all_cookies = response.headers.get('Set-Cookie', '').split(', ')
                for cookie_str in all_cookies:
                    if 'MUSIC_U=' in cookie_str:
                        cookie_dict['MUSIC_U'] = cookie_str.split('MUSIC_U=')[1].split(';')[0]
            
            return result.get('code', -1), cookie_dict
        except (json.JSONDecodeError, KeyError) as e:
            raise APIException(f"解析登录状态响应失败: {e}")
    
    def qr_login(self) -> Optional[str]:
        """完整的二维码登录流程
        
        Returns:
            成功返回cookie字符串，失败返回None
        """
        try:
            unikey = self.create_qr_login()
            if not unikey:
                return None
            
            while True:
                code, cookies = self.check_qr_login(unikey)
                
                if code == 803:
                    print("\n登录成功！")
                    return f"MUSIC_U={cookies['MUSIC_U']};os=pc;appver=8.9.70;"
                elif code == 801:
                    print("\r等待扫码...", end='')
                elif code == 802:
                    print("\r扫码成功，请在手机上确认登录...", end='')
                else:
                    print(f"\n登录失败，错误码：{code}")
                    return None
                
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n用户取消登录")
            return None
        except Exception as e:
            print(f"\n登录过程中发生错误: {e}")
            return None


# 向后兼容的函数接口
def url_v1(song_id: int, level: str, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌曲URL（向后兼容）"""
    api = NeteaseAPI()
    return api.get_song_url(song_id, level, cookies)


def name_v1(song_id: int) -> Dict[str, Any]:
    """获取歌曲详情（向后兼容）"""
    api = NeteaseAPI()
    return api.get_song_detail(song_id)


def lyric_v1(song_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌词（向后兼容）"""
    api = NeteaseAPI()
    return api.get_lyric(song_id, cookies)


def search_music(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索音乐（向后兼容）"""
    api = NeteaseAPI()
    return api.search_music(keywords, cookies, limit)


def search_playlist(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索歌单（向后兼容）"""
    api = NeteaseAPI()
    return api.search_playlist(keywords, cookies, limit)


def search_album(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索专辑（向后兼容）"""
    api = NeteaseAPI()
    return api.search_album(keywords, cookies, limit)


def search_artist(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索歌手（向后兼容）"""
    api = NeteaseAPI()
    return api.search_artist(keywords, cookies, limit)


def get_artist_detail(artist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌手详情（包含歌手信息和热门歌曲）"""
    api = NeteaseAPI()
    return api.get_artist_detail(artist_id, cookies)


def get_artist_top_songs(artist_id: int, cookies: Dict[str, str], limit: int = 50) -> List[Dict[str, Any]]:
    """获取歌手热门歌曲"""
    api = NeteaseAPI()
    return api.get_artist_top_songs(artist_id, cookies, limit)


def playlist_detail(playlist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌单详情（向后兼容）"""
    api = NeteaseAPI()
    return api.get_playlist_detail(playlist_id, cookies)


def album_detail(album_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取专辑详情（向后兼容）"""
    api = NeteaseAPI()
    return api.get_album_detail(album_id, cookies)


def get_pic_url(pic_id: Optional[int], size: int = 300) -> str:
    """获取图片URL（向后兼容）"""
    api = NeteaseAPI()
    return api.get_pic_url(pic_id, size)


def qr_login() -> Optional[str]:
    """二维码登录（向后兼容）"""
    manager = QRLoginManager()
    return manager.qr_login()


if __name__ == "__main__":
    # 测试代码
    print("网易云音乐API模块")
    print("支持的功能:")
    print("- 歌曲URL获取")
    print("- 歌曲详情获取")
    print("- 歌词获取")
    print("- 音乐搜索")
    print("- 歌单详情")
    print("- 专辑详情")
    print("- 二维码登录")
