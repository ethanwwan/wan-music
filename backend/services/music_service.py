"""音乐业务服务层"""

import logging
from typing import Dict, List, Any, Optional

from clients.music_client import music_client, search_music, get_song_url, get_song_detail, get_lyric, get_playlist_detail
from clients.quality_config import QualityLevel

logger = logging.getLogger(__name__)


class MusicService:
    """音乐业务服务类"""
    
    def __init__(self):
        self.music_client = music_client
    
    def search_songs(self, keyword: str, platform: str = None, limit: int = 10) -> List[Dict[str, Any]]:
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
    
    def get_song_url(self, song_id: int, quality: str = 'high') -> Dict[str, Any]:
        """获取歌曲播放/下载URL"""
        try:
            valid_qualities = [q.value for q in QualityLevel]
            if quality not in valid_qualities:
                quality = 'lossless'
            
            result = get_song_url(song_id, quality)
            return result
        except Exception as e:
            logger.error(f"获取歌曲URL失败: {e}")
            raise
    
    def get_song_detail(self, song_id: int) -> Dict[str, Any]:
        """获取歌曲详情"""
        try:
            return get_song_detail(song_id)
        except Exception as e:
            logger.error(f"获取歌曲详情失败: {e}")
            return {}
    
    def get_lyric(self, song_id: int) -> str:
        """获取歌词"""
        try:
            result = get_lyric(song_id)
            return result.get('lyric', '') if isinstance(result, dict) else result
        except Exception as e:
            logger.error(f"获取歌词失败: {e}")
            return ''
    
    def get_playlist_detail(self, playlist_id: int) -> Dict[str, Any]:
        """获取歌单详情"""
        try:
            return get_playlist_detail(playlist_id)
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
    
    def get_song_info(self, song_id: int, quality: str = 'lossless') -> Dict[str, Any]:
        """获取完整歌曲信息（包含URL和歌词）"""
        try:
            song_info = self.get_song_detail(song_id)
            if not song_info or not song_info.get('id'):
                return {}
            
            url_info = self.get_song_url(song_id, quality)
            lyric = self.get_lyric(song_id)
            
            return {
                'id': song_id,
                'name': song_info.get('name', ''),
                'artists': song_info.get('artists', ''),
                'album': song_info.get('album', ''),
                'picUrl': song_info.get('picUrl', ''),
                'duration': song_info.get('duration', 0),
                'url': url_info.get('data', [{}])[0].get('url', '') if isinstance(url_info, dict) else '',
                'quality': quality,
                'lyric': lyric,
                'source': url_info.get('data', [{}])[0].get('source', 'netease') if isinstance(url_info, dict) else 'netease'
            }
        except Exception as e:
            logger.error(f"获取歌曲信息失败: {e}")
            return {}


music_service = MusicService()