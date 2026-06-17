"""音乐业务服务层"""

import logging
from typing import Dict, List, Any, Optional

from clients.music_client import music_client, search_music, get_song_url, get_song_detail, get_lyric, get_playlist_detail
from clients.quality_config import QualityLevel
from utils.url_parser import parse_url

logger = logging.getLogger(__name__)


class MusicService:
    """音乐业务服务类"""

    def __init__(self):
        self.music_client = music_client

    def search_songs(self, keyword: str, platform: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """搜索歌曲"""
        try:
            return search_music(keyword, platform, limit)
        except Exception as e:
            logger.error(f"搜索歌曲失败: {e}")
            return []

    def search_playlists(self, keyword: str, platform: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索歌单"""
        try:
            return self.music_client.search_playlist(keyword, platform, limit)
        except Exception as e:
            logger.error(f"搜索歌单失败: {e}")
            return []

    def search(self, keyword: str, search_type: int = 0, platform: str = None, limit: int = 20) -> Dict[str, Any]:
        """
        统一搜索方法

        1. 先判断 keyword 是否是 URL：
           - 歌曲 URL → 解析歌曲详情，返回 type=1
           - 歌单 URL → 解析歌单详情，返回 type=2
           - 专辑 URL → 暂未实现

        2. 如果不是 URL，按 search_type 搜索：
           - search_type=0 → 搜歌曲+歌单（返回 type=0）
           - search_type=1 → 只搜歌曲（返回 type=1）
           - search_type=2 → 只搜歌单（返回 type=2）

        返回：{'type': 0/1/2, 'data': [...]}，每项带 _type 字段
        """
        # 1. URL 检测
        parsed = parse_url(keyword)
        if parsed:
            return self._search_by_url(parsed)

        # 2. 关键字搜索
        return self._search_by_keyword(keyword, search_type, platform, limit)

    def _search_by_url(self, parsed: Dict[str, str]) -> Dict[str, Any]:
        """根据解析后的 URL 信息获取详情"""
        resource_type = parsed['type']
        resource_id = parsed['id']
        source_platform = parsed['platform']

        if resource_type == 'music':
            song_info = self.get_song_info(resource_id, 'lossless', source_platform)
            if song_info and song_info.get('id'):
                song_info['_type'] = 'song'
                return {'type': 1, 'data': [song_info]}
            return {'type': 1, 'data': [], 'error': '未找到歌曲信息'}

        if resource_type == 'playlist':
            playlist_info = self.get_playlist_detail(resource_id, source_platform)
            if playlist_info and playlist_info.get('id'):
                playlist_info['_type'] = 'playlist'
                return {'type': 2, 'data': [playlist_info]}
            return {'type': 2, 'data': [], 'error': '未找到歌单信息'}

        # 专辑暂未实现
        return {'type': 0, 'data': [], 'error': f'暂不支持解析{resource_type}类型'}

    def _search_by_keyword(self, keyword: str, search_type: int, platform: str, limit: int) -> Dict[str, Any]:
        """按关键字搜索"""
        items: List[Dict[str, Any]] = []

        if search_type in (0, 1):
            songs = self.search_songs(keyword, platform, limit)
            for s in songs:
                s['_type'] = 'song'
            items.extend(songs)

        if search_type in (0, 2):
            playlists = self.search_playlists(keyword, platform, limit)
            for p in playlists:
                p['_type'] = 'playlist'
            items.extend(playlists)

        return {'type': search_type, 'data': items}
    
    def get_song_url(self, song_id: str, quality: str = 'high', platform: str = None) -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        try:
            valid_qualities = [q.value for q in QualityLevel]
            if quality not in valid_qualities:
                quality = 'lossless'
            
            result = get_song_url(song_id, quality, platform)
            return result
        except Exception as e:
            logger.error(f"获取歌曲URL失败: {e}")
            raise
    
    def get_song_detail(self, song_id: str, platform: str = None) -> Dict[str, Any]:
        """获取歌曲详情"""
        try:
            return get_song_detail(song_id, platform)
        except Exception as e:
            logger.error(f"获取歌曲详情失败: {e}")
            return {}
    
    def get_lyric(self, song_id: str, platform: str = None) -> str:
        """获取歌词"""
        try:
            result = get_lyric(song_id, platform)
            return result.get('lyric', '') if isinstance(result, dict) else result
        except Exception as e:
            logger.error(f"获取歌词失败: {e}")
            return ''
    
    def get_playlist_detail(self, playlist_id: str, platform: str = None) -> Dict[str, Any]:
        """获取歌单详情"""
        try:
            return get_playlist_detail(playlist_id, platform)
        except Exception as e:
            logger.error(f"获取歌单详情失败: {e}")
            return {}
    
    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表"""
        try:
            return self.music_client.get_platforms()
        except Exception as e:
            logger.error(f"获取平台列表失败: {e}")
            return []
    
    def get_song_info(self, song_id: str, quality: str = 'lossless', platform: str = None) -> Dict[str, Any]:
        """获取完整歌曲信息（包含URL和歌词）"""
        try:
            song_info = self.get_song_detail(song_id, platform)
            if not song_info or not song_info.get('id'):
                return {}
            
            url_info = self.get_song_url(song_id, quality, platform)
            lyric = self.get_lyric(song_id, platform)
            
            url_data = url_info.get('data', [{}])[0] if isinstance(url_info, dict) else {}
            
            return {
                'id': str(song_info.get('id', song_id)),
                'name': song_info.get('name', ''),
                'artists': song_info.get('artists', ''),
                'album': song_info.get('album', ''),
                'picUrl': song_info.get('picUrl', ''),
                'duration': song_info.get('duration', 0),
                'url': url_data.get('url', ''),
                'quality': quality,
                'lyric': lyric,
                'source': url_data.get('source', 'netease'),
                'fileType': url_data.get('type', 'mp3')  # 文件类型（mp3/flac等）
            }
        except Exception as e:
            logger.error(f"获取歌曲信息失败: {e}")
            return {}


music_service = MusicService()