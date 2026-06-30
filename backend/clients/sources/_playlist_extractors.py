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


def _normalize_kugou_playlist_song(raw: dict) -> dict:
    """把 mobilecdn.kugou.com 返回的歌曲 dict 标准化为 normalize_kugou_song 能识别的格式

    移动端 API 字段（小写）：
      - hash (主 hash)
      - 320hash / sqhash (各音质 hash)
      - filename = "歌手 - 歌名"（参考 music-lib kugou.go fetchPlaylistDetail）
      - duration: 秒
      - album_id / audio_id
      - trans_param.union_cover (封面)

    标准化映射（让 normalize_kugou_song 能直接处理）：
      - hash → FileHash
      - 320hash → FileHash（如需 320 音质时 normalize_kugou_song 自行覆盖）
      - filename → 拆出 SingerName + SongName
      - duration 秒 → 毫秒
      - trans_param.union_cover → Image
    """
    if not isinstance(raw, dict):
        return {}
    out = dict(raw)  # 保留原字段

    # 1. hash 兼容（playlist API 用小写 hash，normalize_kugou_song 用 FileHash）
    h = raw.get('hash') or raw.get('FileHash') or ''
    if h:
        out['FileHash'] = h

    # 2. filename 拆出歌手 + 歌名（参考 music-lib）
    fn = raw.get('filename') or raw.get('FileName') or ''
    if fn and (not raw.get('SongName') or not raw.get('SingerName')):
        parts = fn.split(' - ', 1)
        if len(parts) == 2:
            if not raw.get('SingerName'):
                out['SingerName'] = parts[0].strip()
            if not raw.get('SongName'):
                out['SongName'] = parts[1].strip()
        elif not raw.get('SongName'):
            out['SongName'] = fn.strip()

    # 3. 封面：trans_param.union_cover → Image
    if not raw.get('Image'):
        tp = raw.get('trans_param') or {}
        cover = tp.get('union_cover') if isinstance(tp, dict) else ''
        if cover:
            out['Image'] = cover

    # 4. duration：playlist API 返回秒，normalize_kugou_song 有智能检测 (<10000 当秒)
    # 但为了明确，强制转 ms
    d = raw.get('duration')
    if d is not None and 0 < int(d) < 10000:
        out['Duration'] = int(d) * 1000

    # 5. 时长：playlist API 没 AlbumName 字段（响应中为 None），但有 album_id
    return out


def extract_kugou_playlist(raw: dict, **kwargs) -> dict:
    """从酷狗 mobilecdn.kugou.com 歌单 API 响应中提取歌单信息

    参考 https://github.com/guohuiyuan/music-lib/blob/main/kugou/kugou.go
    注意：此 API 不返回歌单元数据（name/cover），只有歌曲列表。
    name/cover 由调用方通过 kwargs['playlist_name'] / kwargs['playlist_cover'] 传入。
    """
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
            normalized = normalize_kugou_song(_normalize_kugou_playlist_song(t))
            tracks.append(normalized)
        except Exception:
            continue
    return {
        'name': data.get('specialname') or kwargs.get('playlist_name') or '',
        'creator': '',
        'cover': data.get('img') or data.get('cover') or kwargs.get('playlist_cover') or '',
        'trackCount': int(data.get('total') or data.get('count') or len(tracks)),
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
