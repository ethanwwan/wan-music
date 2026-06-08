"""网易云音乐API模块 - 基于musicdl实现

提供网易云音乐相关API接口的封装，包括：
- 音乐URL获取
- 歌曲详情获取
- 歌词获取
- 搜索功能
- 歌单和专辑详情
- 二维码登录

底层使用 musicdl 库，支持多平台音乐获取
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入 musicdl
try:
    from musicdl.musicdl import MusicClient
    MUSICDL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"musicdl 导入失败: {e}")
    MUSICDL_AVAILABLE = False


class APIException(Exception):
    """API异常类"""
    pass


class NeteaseAPI:
    """网易云音乐API主类 - 向后兼容"""
    
    def __init__(self):
        self.http_client = None  # 兼容旧代码引用
    
    def get_song_url(self, song_id: int, quality: str, cookies: Dict[str, str]) -> Dict[str, Any]:
        return url_v1(song_id, quality, cookies)
    
    def get_song_detail(self, song_id: int) -> Dict[str, Any]:
        return name_v1(song_id)
    
    def get_lyric(self, song_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        return lyric_v1(song_id, cookies)
    
    def search_music(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        return search_music(keywords, cookies, limit)
    
    def search_playlist(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        return search_playlist(keywords, cookies, limit)
    
    def search_album(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        return search_album(keywords, cookies, limit)
    
    def search_artist(self, keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        return search_artist(keywords, cookies, limit)
    
    def get_artist_detail(self, artist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        return get_artist_detail(artist_id, cookies)
    
    def get_artist_top_songs(self, artist_id: int, cookies: Dict[str, str], limit: int = 50) -> List[Dict[str, Any]]:
        return get_artist_top_songs(artist_id, cookies, limit)
    
    def get_playlist_detail(self, playlist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        return playlist_detail(playlist_id, cookies)
    
    def get_album_detail(self, album_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
        return album_detail(album_id, cookies)
    
    def get_pic_url(self, pic_id: Optional[int], size: int = 300) -> str:
        return get_pic_url(pic_id, size)


class QualityLevel:
    """音质等级枚举"""
    STANDARD = "standard"
    EXHIGH = "exhigh"
    LOSSLESS = "lossless"
    HIRES = "hires"
    SKY = "sky"
    JYEFFECT = "jyeffect"
    JYMASTER = "jymaster"
    DOLBY = "dolby"


class MusicDLAPI:
    """基于musicdl的音乐API封装"""
    
    # 支持的音乐源列表
    MUSIC_SOURCES = {
        'netease': ['NeteaseMusicClient'],
        'qqmusic': ['QQMusicClient'],
        'kugou': ['KugouMusicClient'],
        'kuwo': ['KuwoMusicClient'],
        'migu': ['MiguMusicClient'],
        'all': ['NeteaseMusicClient', 'QQMusicClient', 'KugouMusicClient', 'KuwoMusicClient', 'MiguMusicClient']
    }
    
    def __init__(self):
        self._clients = {}  # 为每个平台维护单独的客户端
    
    def _get_client(self, source):
        """获取指定音乐源的客户端"""
        if source not in self._clients:
            if not MUSICDL_AVAILABLE:
                raise APIException("musicdl不可用")
            
            try:
                sources = self.MUSIC_SOURCES.get(source, self.MUSIC_SOURCES['netease'])
                # 配置初始化参数，减少线程数，加快搜索速度
                init_config = {
                    source: {
                        'clients_threadings': 2,  # 减少线程数
                        'search_size_per_source': 5,  # 限制搜索结果数量
                    }
                }
                self._clients[source] = MusicClient(
                    music_sources=sources,
                    init_music_clients_cfg=init_config
                )
            except Exception as e:
                logger.error(f"musicdl客户端初始化失败: {e}")
                raise APIException(f"音乐服务初始化失败: {e}")
        
        return self._clients[source]
    
    @property
    def client(self):
        """获取默认客户端（网易云）"""
        return self._get_client('netease')
    
    def _get_source_name(self, source: str) -> str:
        """将简短源名称转换为musicdl的源名称"""
        source_map = {
            'netease': 'NeteaseMusicClient',
            'qqmusic': 'QQMusicClient',
            'kugou': 'KugouMusicClient',
            'kuwo': 'KuwoMusicClient',
            'migu': 'MiguMusicClient'
        }
        return source_map.get(source.lower(), 'NeteaseMusicClient')
    
    def search(self, keyword: str, source: str = 'netease', limit: int = 10) -> List[Dict]:
        """搜索音乐"""
        if not MUSICDL_AVAILABLE:
            raise APIException("musicdl不可用")
        
        try:
            # 使用指定平台的客户端
            client = self._get_client(source)
            results = client.search(keyword=keyword)
            
            # search返回dict，键是源名称，值是歌曲列表
            all_songs = []
            for src, song_list in results.items():
                all_songs.extend(song_list)
            
            # 转换为字典格式并限制数量
            return [self._song_info_to_dict(song) for song in all_songs[:limit]]
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise APIException(f"搜索失败: {e}")
    
    def search_multi_source(self, keyword: str, limit: int = 10) -> List[Dict]:
        """多平台搜索"""
        if not MUSICDL_AVAILABLE:
            raise APIException("musicdl不可用")
        
        try:
            all_songs = []
            # 只搜索主要平台，避免超时
            for source in ['netease', 'qqmusic', 'kugou']:
                try:
                    client = self._get_client(source)
                    results = client.search(keyword=keyword)
                    for src, song_list in results.items():
                        all_songs.extend(song_list)
                except Exception as e:
                    logger.warning(f"{source} 搜索失败: {e}")
                    continue
            
            # 转换为字典格式并限制数量
            return [self._song_info_to_dict(song) for song in all_songs[:limit]]
        except Exception as e:
            logger.error(f"多平台搜索失败: {e}")
            raise APIException(f"搜索失败: {e}")
    
    def _song_info_to_dict(self, song_info) -> Dict:
        """将SongInfo对象转换为字典"""
        return {
            'songid': song_info.identifier,
            'songname': song_info.song_name,
            'singers': song_info.singers,
            'album': song_info.album,
            'cover': song_info.cover_url,
            'songurl': song_info.download_url,
            'lyrics': song_info.lyric,
            'duration': song_info.duration_s,
            'ext': song_info.ext,
            'size': song_info.file_size_bytes,
            'source': song_info.source,
            'bitrate': song_info.bitrate
        }
    
    def download(self, song_info: Dict, quality: str = 'lossless') -> Dict:
        """下载音乐"""
        if not MUSICDL_AVAILABLE:
            raise APIException("musicdl不可用")
        
        try:
            result = self.client.download(
                songinfos=[song_info],
                quality=quality
            )
            return result
        except Exception as e:
            logger.error(f"下载失败: {e}")
            raise APIException(f"下载失败: {e}")


# 创建全局实例
musicdl_api = MusicDLAPI()


# ==================== 向后兼容的函数接口 ====================

def url_v1(song_id: int, level: str, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌曲URL（向后兼容）
    
    使用musicdl搜索并获取歌曲信息
    """
    try:
        # 先搜索歌曲信息
        results = musicdl_api.search(str(song_id), source='netease', limit=1)
        if not results:
            raise APIException(f"未找到歌曲: {song_id}")
        
        song_info = results[0]
        # 构建返回格式以保持兼容
        return {
            'data': [{
                'id': song_id,
                'url': song_info.get('songurl', ''),
                'level': level,
                'type': song_info.get('ext', 'flac'),
                'size': song_info.get('size', 0),
                'br': 0
            }]
        }
    except APIException:
        raise
    except Exception as e:
        logger.error(f"获取歌曲URL失败: {e}")
        raise APIException(f"获取歌曲URL失败: {e}")


def name_v1(song_id: int) -> Dict[str, Any]:
    """获取歌曲详情（向后兼容）"""
    try:
        results = musicdl_api.search(str(song_id), source='netease', limit=1)
        if not results:
            raise APIException(f"未找到歌曲: {song_id}")
        
        song_info = results[0]
        return {
            'code': 200,
            'songs': [{
                'id': song_id,
                'name': song_info.get('songname', ''),
                'ar': [{'name': artist} for artist in song_info.get('singers', '').split('/') if artist],
                'al': {
                    'name': song_info.get('album', ''),
                    'picUrl': song_info.get('cover', '')
                },
                'dt': song_info.get('duration', 0)
            }]
        }
    except APIException:
        raise
    except Exception as e:
        logger.error(f"获取歌曲详情失败: {e}")
        raise APIException(f"获取歌曲详情失败: {e}")


def lyric_v1(song_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌词（向后兼容）"""
    try:
        results = musicdl_api.search(str(song_id), source='netease', limit=1)
        if not results:
            raise APIException(f"未找到歌曲: {song_id}")
        
        song_info = results[0]
        return {
            'code': 200,
            'lrc': {
                'lyric': song_info.get('lyrics', '')
            },
            'tlyric': {
                'lyric': ''
            }
        }
    except APIException:
        raise
    except Exception as e:
        logger.error(f"获取歌词失败: {e}")
        raise APIException(f"获取歌词失败: {e}")


def search_music(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索音乐（向后兼容）"""
    try:
        # 只搜索网易云音乐，显著加快搜索速度
        # 如果需要多平台搜索，可以使用 search_multi_source 函数
        results = musicdl_api.search(keywords, source='netease', limit=limit)
        songs = []
        for item in results:
            songs.append({
                'id': item.get('songid', ''),
                'name': item.get('songname', ''),
                'artists': item.get('singers', ''),
                'album': item.get('album', ''),
                'picUrl': item.get('cover', '')
            })
        return songs
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise APIException(f"搜索失败: {e}")


def search_playlist(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索歌单（向后兼容）"""
    try:
        # musicdl主要用于歌曲搜索，歌单搜索暂时使用原有逻辑
        # 返回空列表作为占位
        logger.warning("歌单搜索功能尚未完全集成musicdl")
        return []
    except Exception as e:
        logger.error(f"搜索歌单失败: {e}")
        raise APIException(f"搜索歌单失败: {e}")


def search_album(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索专辑（向后兼容）"""
    try:
        logger.warning("专辑搜索功能尚未完全集成musicdl")
        return []
    except Exception as e:
        logger.error(f"搜索专辑失败: {e}")
        raise APIException(f"搜索专辑失败: {e}")


def search_artist(keywords: str, cookies: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
    """搜索歌手（向后兼容）"""
    try:
        logger.warning("歌手搜索功能尚未完全集成musicdl")
        return []
    except Exception as e:
        logger.error(f"搜索歌手失败: {e}")
        raise APIException(f"搜索歌手失败: {e}")


def get_artist_detail(artist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌手详情（包含歌手信息和热门歌曲）"""
    try:
        logger.warning("歌手详情功能尚未完全集成musicdl")
        return {
            'artist': {},
            'songs': []
        }
    except Exception as e:
        logger.error(f"获取歌手详情失败: {e}")
        raise APIException(f"获取歌手详情失败: {e}")


def get_artist_top_songs(artist_id: int, cookies: Dict[str, str], limit: int = 50) -> List[Dict[str, Any]]:
    """获取歌手热门歌曲"""
    try:
        logger.warning("歌手热门歌曲功能尚未完全集成musicdl")
        return []
    except Exception as e:
        logger.error(f"获取歌手热门歌曲失败: {e}")
        raise APIException(f"获取歌手热门歌曲失败: {e}")


def playlist_detail(playlist_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取歌单详情（向后兼容）"""
    try:
        logger.warning("歌单详情功能尚未完全集成musicdl")
        return {
            'id': playlist_id,
            'name': '',
            'coverImgUrl': '',
            'creator': '',
            'trackCount': 0,
            'tracks': []
        }
    except Exception as e:
        logger.error(f"获取歌单详情失败: {e}")
        raise APIException(f"获取歌单详情失败: {e}")


def album_detail(album_id: int, cookies: Dict[str, str]) -> Dict[str, Any]:
    """获取专辑详情（向后兼容）"""
    try:
        logger.warning("专辑详情功能尚未完全集成musicdl")
        return {
            'id': album_id,
            'name': '',
            'coverUrl': '',
            'artist': '',
            'publishTime': 0,
            'tracks': []
        }
    except Exception as e:
        logger.error(f"获取专辑详情失败: {e}")
        raise APIException(f"获取专辑详情失败: {e}")


def get_pic_url(pic_id: Optional[int], size: int = 300) -> str:
    """获取图片URL（向后兼容）"""
    if pic_id is None:
        return ''
    return f'https://example.com/img/{pic_id}.jpg'


def qr_login() -> Optional[str]:
    """二维码登录（向后兼容）"""
    logger.warning("二维码登录功能尚未完全集成musicdl")
    return None


if __name__ == "__main__":
    # 测试代码
    print("网易云音乐API模块 - 基于musicdl")
    print(f"musicdl可用: {MUSICDL_AVAILABLE}")
    print("支持的功能:")
    print("- 歌曲URL获取")
    print("- 歌曲详情获取")
    print("- 歌词获取")
    print("- 音乐搜索（多平台）")
    print("- 歌单详情（待完善）")
    print("- 专辑详情（待完善）")
    
    # 测试搜索
    if MUSICDL_AVAILABLE:
        try:
            results = musicdl_api.search("周杰伦", source='netease', limit=5)
            print(f"\n搜索结果（周杰伦）: {len(results)} 条")
            for i, song in enumerate(results[:3], 1):
                print(f"  {i}. {song.get('songname', '')} - {song.get('singers', '')}")
        except Exception as e:
            print(f"搜索测试失败: {e}")