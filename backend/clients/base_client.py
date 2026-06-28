"""音乐客户端抽象基类

定义所有音乐平台客户端必须实现的接口规范。

设计原则：
  - 方法粒度对齐"用户场景"（search / get_song），不沿用上游 API 路径
  - 失败用显式 Optional/None 表达，不靠"空字符串字段"隐式表达
  - search 永远只搜歌曲（不分歌单），URL 解析另走 _resolve_from_url
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import requests

from .quality_config import get_default_quality, is_valid_quality


class BaseMusicClient(ABC):
    """音乐客户端抽象基类"""

    def __init__(self):
        self.session = requests.Session()
        self.platform_name = "base"
        self.platform_id = "base"

    @abstractmethod
    def search(self, keyword: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """搜索歌曲

        Returns:
            {
                'data': [{'id', 'name', 'artists', 'album', 'picUrl', 'duration',
                          'source', 'api_source'}, ...],
                'search_source': str,   # 命中的源名（None 表示完全失败）
                'warnings': list,       # 警告信息
            }
        """
        pass

    @abstractmethod
    def get_song(self, song_id: Any, quality: str = 'lossless',
                 with_lyric: bool = True) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息：元信息 + 播放 URL + (可选) 歌词

        Returns:
            None 表示完全失败
            成功时至少包含 {'id', 'url', 'source', 'quality', 'api_source'}，
            失败的部分字段可能为 ''（歌词等可选字段）
        """
        pass

    def get_health(self) -> dict:
        """获取客户端健康状态（子类可覆盖）"""
        return {}

    @staticmethod
    def _normalize_quality(quality: str) -> str:
        """音质归一化（无效时回退到 lossless）"""
        return quality if is_valid_quality(quality) else get_default_quality()

    def close(self):
        """关闭 session"""
        try:
            self.session.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
