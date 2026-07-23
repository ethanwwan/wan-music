from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Artist:
    """歌手数据模型"""
    id: int
    name: str
    avatarUrl: str = ''
    picUrl: str = ''
    musicCount: int = 0
    songCount: int = 0
    albumCount: int = 0
    fansCount: int = 0
    desc: str = ''
    alias: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Artist':
        """从字典创建Artist对象，支持多种数据源格式"""
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            avatarUrl=data.get('avatarUrl') or data.get('picUrl') or '',
            picUrl=data.get('picUrl') or data.get('avatarUrl') or '',
            musicCount=data.get('musicCount') or data.get('songCount') or data.get('musicSize') or 0,
            songCount=data.get('songCount') or data.get('musicCount') or data.get('musicSize') or 0,
            albumCount=data.get('albumCount') or data.get('albumSize') or 0,
            fansCount=data.get('fansCount') or data.get('fansSize') or 0,
            desc=data.get('desc') or data.get('description') or '',
            alias=data.get('alias') or []
        )


@dataclass
class Album:
    """专辑数据模型"""
    id: int
    name: str
    picUrl: str = ''
    coverImgUrl: str = ''
    artist: Dict[str, Any] = field(default_factory=dict)
    artistName: str = ''
    publishTime: int = 0
    size: int = 0
    trackCount: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Album':
        """从字典创建Album对象，支持多种数据源格式"""
        artist_data = data.get('artist', {})
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            picUrl=data.get('picUrl') or data.get('coverImgUrl') or '',
            coverImgUrl=data.get('coverImgUrl') or data.get('picUrl') or '',
            artist={
                'id': artist_data.get('id') or artist_data.get('userId') or 0,
                'name': artist_data.get('name') or artist_data.get('nickname') or ''
            },
            artistName=data.get('artistName') or artist_data.get('name') or artist_data.get('nickname') or '',
            publishTime=data.get('publishTime') or 0,
            size=data.get('size') or 0,
            trackCount=data.get('trackCount') or data.get('size') or 0
        )


@dataclass
class Playlist:
    """歌单数据模型"""
    id: int
    name: str
    coverImgUrl: str = ''
    description: str = ''
    trackCount: int = 0
    playCount: int = 0
    creator: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playlist':
        """从字典创建Playlist对象，支持多种数据源格式"""
        creator_data = data.get('creator', {})
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            coverImgUrl=data.get('coverImgUrl') or data.get('picUrl') or '',
            description=data.get('description') or '',
            trackCount=data.get('trackCount') or data.get('size') or 0,
            playCount=data.get('playCount') or 0,
            creator={
                'id': creator_data.get('id') or creator_data.get('userId') or 0,
                'name': creator_data.get('name') or creator_data.get('nickname') or '',
                'nickname': creator_data.get('nickname') or creator_data.get('name') or ''
            }
        )


@dataclass
class Track:
    """歌曲数据模型"""
    id: int
    name: str
    artists: str = ''
    artist: str = ''
    album: str = ''
    picUrl: str = ''
    coverImgUrl: str = ''
    duration: int = 0
    url: str = ''
    lrc: str = ''
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """从字典创建Track对象，支持多种数据源格式"""
        # 处理歌手信息
        artists = data.get('artists') or data.get('ar') or []
        artist_names = [a.get('name', '') for a in artists]
        artist_str = '/'.join(filter(None, artist_names))
        
        # 处理专辑信息
        album_data = data.get('album') or data.get('al') or {}
        
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            artists=artist_str or data.get('artists') or data.get('artist') or '',
            artist=artist_str or data.get('artist') or '',
            album=album_data.get('name', '') or data.get('album') or '',
            picUrl=album_data.get('picUrl') or album_data.get('coverImgUrl') or data.get('picUrl') or '',
            coverImgUrl=album_data.get('coverImgUrl') or album_data.get('picUrl') or data.get('coverImgUrl') or '',
            duration=data.get('duration') or data.get('dt') or 0,
            url=data.get('url') or '',
            lrc=data.get('lrc') or ''
        )


def normalize_artist_list(artists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化歌手列表数据结构"""
    return [Artist.from_dict(a).__dict__ for a in artists]


def normalize_album_list(albums: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化专辑列表数据结构"""
    return [Album.from_dict(a).__dict__ for a in albums]


def normalize_playlist_list(playlists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化歌单列表数据结构"""
    return [Playlist.from_dict(p).__dict__ for p in playlists]


def normalize_track_list(tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """标准化歌曲列表数据结构"""
    return [Track.from_dict(t).__dict__ for t in tracks]
