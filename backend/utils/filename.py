"""文件名处理工具

提供文件名清理、构建、规范化等功能
"""
import re
import unicodedata
from typing import Optional


# 多个歌手之间的分隔符（被错误使用的）
# _ 是分隔符 (例如: 汪苏泷_明柏辰, KEY.L刘聪_刘炫廷)
ARTIST_SEPARATORS = [',', '，', ';', '；', '&', '\\', '、', '|', '_']
CORRECT_SEPARATOR = '/'


def normalize_artist_name(artist: Optional[str]) -> str:
    """统一多歌手的拼接格式为 /

    处理以下错误分隔符: , ; & _ \\ ，；、 |
    例如: '陈楚生，王铮亮' -> '陈楚生/王铮亮'
         '汪苏泷_明柏辰&明筱岩' -> '汪苏泷/明柏辰/明筱岩'

    Args:
        artist: 歌手字符串（可能为 None 或空字符串）

    Returns:
        规范化后的歌手字符串，多个歌手用 / 拼接
    """
    if not artist:
        return artist or ''

    # 先去掉分隔符周围的空格
    for sep in [',', '，', ';', '；', '&', '\\', '、', '|']:
        pattern = r'\s*' + re.escape(sep) + r'\s*'
        artist = re.sub(pattern, lambda m, s=sep: s, artist)

    # 然后将所有错误分隔符替换为 /
    for sep in ARTIST_SEPARATORS:
        artist = artist.replace(sep, CORRECT_SEPARATOR)

    # 合并连续的分隔符
    artist = re.sub(r'/+', '/', artist)
    return artist.strip().strip(CORRECT_SEPARATOR)


def split_artists(artist_str: Optional[str]) -> list:
    """将多歌手字符串拆分为单个歌手列表

    Args:
        artist_str: 歌手字符串（支持多种分隔符）

    Returns:
        单个歌手列表，如 ['陈楚生', '王铮亮']
    """
    if not artist_str:
        return []
    normalized = normalize_artist_name(artist_str)
    return [p.strip() for p in normalized.split('/') if p.strip()]


# 文件名非法字符（Windows + macOS 兼容）
_INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
# Windows 保留名称
_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """清理文件名中的非法字符（跨平台兼容）

    Args:
        name: 原始文件名
        max_length: 最大长度（默认 200）

    Returns:
        清理后的安全文件名
    """
    if not name:
        return 'untitled'

    # 替换非法字符
    name = re.sub(_INVALID_FILENAME_CHARS, '_', name)

    # 去除控制字符
    name = ''.join(c for c in name if unicodedata.category(c)[0] != 'C' or c in (' ',))

    # 去除首尾空白和点（Windows 不允许结尾是点）
    name = name.strip().strip('.')

    # 检查保留名称
    base_name = name.split('.')[0].upper()
    if base_name in _RESERVED_NAMES:
        name = '_' + name

    # 截断长度
    if len(name) > max_length:
        # 保留扩展名
        if '.' in name:
            base, ext = name.rsplit('.', 1)
            base = base[:max_length - len(ext) - 1]
            name = f'{base}.{ext}'
        else:
            name = name[:max_length]

    return name or 'untitled'


def build_filename(artist: str, name: str, extension: str, filename_format: str = 'song-artist') -> str:
    """根据文件命名格式构造文件名

    Args:
        artist: 歌手
        name: 歌曲名
        extension: 文件扩展名（带点，如 .flac）
        filename_format:
            - 'song-artist' (默认): 歌曲名 - 歌手
            - 'artist-song': 歌手 - 歌曲名
            - 'song': 仅歌曲名

    Returns:
        构造的文件名
    """
    # 统一多歌手拼接格式
    artist = normalize_artist_name(artist)
    if filename_format != 'song':
        name = normalize_artist_name(name)

    if filename_format == 'artist-song':
        return f"{artist} - {name}{extension}" if artist else f"{name}{extension}"
    elif filename_format == 'song':
        return f"{name}{extension}"
    else:  # 'song-artist'
        return f"{name} - {artist}{extension}" if artist else f"{name}{extension}"


def build_content_disposition(filename: str) -> str:
    """构造 HTTP Content-Disposition 头（支持中文文件名）

    Args:
        filename: 文件名

    Returns:
        Content-Disposition 头的值
    """
    from urllib.parse import quote
    # RFC 5987: 同时提供 filename 和 filename* (UTF-8 编码)
    encoded = quote(filename, safe='')
    return f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded}"
