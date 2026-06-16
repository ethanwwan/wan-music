"""URL 解析工具

集中处理各平台音乐/歌单/专辑链接的解析，提取 ID 和识别平台。
"""

import re
from typing import Dict, Optional, Tuple

# 各平台 URL 匹配模式
URL_PATTERNS = {
    'netease': {
        'music': [
            r'https?://music\.163\.com/song\?id=(\d+)',
            r'https?://y\.music\.163\.com/m/song/(\d+)',
            r'https?://y\.music\.163\.com/m/song\?id=(\d+)',
            r'https?://music\.163\.com/#/song\?id=(\d+)',
        ],
        'playlist': [
            r'https?://music\.163\.com/playlist\?id=(\d+)',
            r'https?://y\.music\.163\.com/m/playlist\?id=(\d+)',
            r'https?://y\.music\.163\.com/m/playlist/(\d+)',
            r'https?://music\.163\.com/#/playlist\?id=(\d+)',
            r'https?://music\.163\.com/discover/toplist\?id=(\d+)',
        ],
        'album': [
            r'https?://music\.163\.com/album\?id=(\d+)',
            r'https?://music\.163\.com/album/(\d+)',
            r'https?://y\.music\.163\.com/m/album\?id=(\d+)',
            r'https?://music\.163\.com/#/album\?id=(\d+)',
            r'https?://music\.163\.com/#/album/(\d+)',
        ],
        'short': r'https?://163cn\.tv/([a-zA-Z0-9]+)',
    },
    'qq': {
        'music': [
            r'https?://y\.qq\.com/n/ryqq/songDetail/([a-zA-Z0-9]+)',
            r'https?://i\.y\.qq\.com/n2/m/share/details/song\.html\?.*songid=(\d+)',
            r'https?://c\.y\.qq\.com/base/cgi-bin/u\.cgi\?.*url=.*songDetail/([a-zA-Z0-9]+)',
        ],
        'playlist': [
            r'https?://y\.qq\.com/n/ryqq/playlist/(\d+)',
            r'https?://i\.y\.qq\.com/n2/m/share/details/taoge\.html\?.*id=(\d+)',
        ],
    },
    'kugou': {
        'music': [
            r'https?://www\.kugou\.com/song/#hash=([a-zA-Z0-9]+)',
            r'https?://www\.kugou\.com/mixsong/([a-zA-Z0-9]+)',
            r'https?://m\.kugou\.com/app/i/getSongInfo\.php\?.*hash=([a-zA-Z0-9]+)',
        ],
        'playlist': [
            r'https?://www\.kugou\.com/yy/special/single/(\d+)\.html',
            r'https?://m\.kugou\.com/plist/list/index\.php\?.*id=(\d+)',
        ],
    },
    'bodian': {
        'music': [
            r'https?://bodian\.kuwo\.cn/song/([a-zA-Z0-9]+)',
            r'https?://www\.bodianmusic\.com/song/([a-zA-Z0-9]+)',
        ],
        'playlist': [
            r'https?://bodian\.kuwo\.cn/playlist/([a-zA-Z0-9]+)',
            r'https?://www\.bodianmusic\.com/playlist/([a-zA-Z0-9]+)',
        ],
    },
}


def _extract_url(text: str) -> str:
    """从文本中提取 URL"""
    if not text:
        return text or ''
    match = re.search(r'(https?://[^\s"<>]+)', text)
    return match.group(0) if match else text


def parse_url(text: str) -> Optional[Dict[str, str]]:
    """
    解析 URL，识别平台、类型和资源 ID

    Args:
        text: 原始文本（可以是 URL 或包含 URL 的文本）

    Returns:
        {
            'platform': 'netease' | 'qq' | 'kugou' | 'bodian',
            'type': 'music' | 'playlist' | 'album',
            'id': '资源 ID'
        } 或 None（如果无法识别）
    """
    if not text:
        return None
    url = _extract_url(str(text))
    if not url or not url.startswith('http'):
        return None

    for platform, type_patterns in URL_PATTERNS.items():
        for resource_type, patterns in type_patterns.items():
            if not isinstance(patterns, list):
                continue
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return {
                        'platform': platform,
                        'type': resource_type,
                        'id': match.group(1)
                    }
    return None


def get_url_type(url: str) -> Optional[str]:
    """
    判断 URL 是什么类型（music/playlist/album）
    """
    parsed = parse_url(url)
    return parsed['type'] if parsed else None


def is_music_url(url: str) -> bool:
    return get_url_type(url) == 'music'


def is_playlist_url(url: str) -> bool:
    return get_url_type(url) == 'playlist'


def is_album_url(url: str) -> bool:
    return get_url_type(url) == 'album'
