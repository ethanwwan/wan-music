"""歌单提取器（独立于 fallback.extractors 避免循环 import）

为避免循环 import（fallback.extractors 不能 import sources.*，但 sources.* 内部
要使用 normalize_*_song 标准化歌曲字段），把 5 个歌单提取器放在 sources 包内部。
"""
from typing import List, Dict, Any, Optional
from urllib.parse import quote

# 复用 fallback.extractors 中已定义的歌曲标准化函数
from ..fallback.extractors import (
    normalize_netease_song,
    normalize_qq_song,
    normalize_kugou_song,
    normalize_kuwo_song,
)


def extract_kuwo_playlist(raw: dict, **kwargs) -> dict:
    """从酷我 playListInfo 接口响应中提取歌单信息"""
    data = raw.get('data') or {}
    name = data.get('name') or ''
    creator = (data.get('creator') or data.get('userName') or data.get('uname')
               or '').strip() or None
    # 酷我 playListInfo 字段：img (列表封面) / img500 / img300 / img700
    cover = (data.get('img') or data.get('img500') or data.get('img300')
             or data.get('img700') or data.get('pic') or data.get('cover') or '')
    if cover and not cover.startswith('http'):
        if cover.startswith('//'):
            cover = 'https:' + cover
        elif cover.startswith('/'):
            cover = 'https://m.kuwo.cn' + cover
        else:
            cover = 'https://img1.kuwo.cn/playlistcover/' + cover
    track_count = int(data.get('total') or 0)
    raw_tracks = data.get('musicList') or []
    tracks = []
    for t in raw_tracks:
        if not isinstance(t, dict):
            continue
        try:
            tracks.append(normalize_kuwo_song(t))
        except Exception:
            continue
    return {
        'name': name,
        'creator': creator,
        'cover': cover,
        'trackCount': track_count,
        'tracks': tracks,
    }


def extract_netease_playlist(raw: dict, **kwargs) -> dict:
    """从网易云 /api/v6/playlist/detail 响应中提取歌单信息"""
    if not isinstance(raw, dict) or int(raw.get('code', 0)) != 200:
        return {'name': '', 'creator': '', 'cover': '', 'trackCount': 0, 'tracks': []}
    pl = raw.get('playlist') or {}
    if not pl:
        return {'name': '', 'creator': '', 'cover': '', 'trackCount': 0, 'tracks': []}
    name = pl.get('name') or ''
    cover = pl.get('coverImgUrl') or ''
    track_count = int(pl.get('trackCount') or 0)
    creator_obj = pl.get('creator') or {}
    creator = creator_obj.get('nickname') if isinstance(creator_obj, dict) else ''
    raw_tracks = pl.get('tracks') or []
    tracks = []
    for t in raw_tracks:
        if not isinstance(t, dict):
            continue
        try:
            tracks.append(normalize_netease_song(t))
        except Exception:
            continue
    return {
        'name': name, 'creator': creator, 'cover': cover,
        'trackCount': track_count or len(tracks), 'tracks': tracks,
    }


def extract_qq_playlist(raw: dict, **kwargs) -> dict:
    """从 QQ /qzone/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg 响应中提取歌单信息"""
    if not isinstance(raw, dict) or int(raw.get('code', 0)) not in (0, 200):
        return {'name': '', 'creator': '', 'cover': '', 'trackCount': 0, 'tracks': []}
    cdlist = raw.get('cdlist') or []
    if not cdlist:
        return {'name': '', 'creator': '', 'cover': '', 'trackCount': 0, 'tracks': []}
    pl = cdlist[0] or {}
    name = pl.get('dissname') or pl.get('title') or ''
    cover = pl.get('logo') or pl.get('cover') or ''
    raw_tracks = pl.get('songlist') or []
    target_platform = kwargs.get('target_platform') or 'qq'
    tracks = []
    for t in raw_tracks:
        if not isinstance(t, dict):
            continue
        try:
            track = normalize_qq_song(t)
            track['source'] = target_platform
            tracks.append(track)
        except Exception:
            continue
    return {
        'name': name, 'creator': '', 'cover': cover,
        'trackCount': len(tracks), 'tracks': tracks,
    }


def extract_kugou_playlist(raw: dict, **kwargs) -> dict:
    """从酷狗 /v2/get_other_list_file 响应中提取歌单信息"""
    if not isinstance(raw, dict) or int(raw.get('status', 0)) != 1:
        return {'name': '', 'creator': '', 'cover': '', 'trackCount': 0, 'tracks': []}
    data = raw.get('data') or {}
    raw_tracks = data.get('info') or []
    target_platform = kwargs.get('target_platform') or 'kugou'
    tracks = []
    for t in raw_tracks:
        if not isinstance(t, dict):
            continue
        try:
            tracks.append(normalize_kugou_song(t))
        except Exception:
            continue
    return {
        'name': data.get('specialname') or kwargs.get('playlist_name') or '',
        'creator': '',
        'cover': data.get('img') or data.get('cover') or '',
        'trackCount': int(data.get('count') or len(tracks)),
        'tracks': tracks,
    }


def extract_gdstudio_playlist(raw: dict, **kwargs) -> dict:
    """从 gdstudio 跨平台歌单 API 响应中提取信息（兜底）

    注意：gdstudio 的 source 参数**实际无效**，无论传什么都返回网易云格式
    """
    if not isinstance(raw, dict) or int(raw.get('code', 0)) != 200:
        return {'name': '', 'creator': '', 'cover': '', 'trackCount': 0, 'tracks': []}

    playlist = raw.get('playlist') or raw.get('data', {}).get('playlist') or {}
    if not playlist:
        return {'name': '', 'creator': '', 'cover': '', 'trackCount': 0, 'tracks': []}

    name = playlist.get('name') or ''
    cover = playlist.get('coverImgUrl') or ''
    track_count = int(playlist.get('trackCount') or 0)
    creator_obj = playlist.get('creator') or {}
    if isinstance(creator_obj, dict):
        creator = creator_obj.get('nickname') or creator_obj.get('name') or ''
    else:
        creator = str(creator_obj) if creator_obj else ''

    raw_tracks = playlist.get('tracks') or []
    target_platform = kwargs.get('target_platform') or 'netease'

    tracks = []
    for t in raw_tracks:
        if not isinstance(t, dict):
            continue
        try:
            normalized = normalize_netease_song(t)
            normalized['source'] = target_platform
            tracks.append(normalized)
        except Exception:
            continue

    return {
        'name': name,
        'creator': creator,
        'cover': cover,
        'trackCount': track_count or len(tracks),
        'tracks': tracks,
    }
