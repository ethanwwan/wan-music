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

    def __init__(self, cookie_file: str = ''):
        self.session = requests.Session()
        self.platform_name = "base"
        self.platform_id = "base"
        self.cookie_file = cookie_file
        self.cookies = self._load_cookie()

    def _load_cookie(self) -> dict:
        """从 cookie 文件加载，结果缓存在 self.cookies 中（仅初始化时读一次文件）"""
        if not self.cookie_file:
            return {}
        from pathlib import Path
        candidates = [
            Path(self.cookie_file),
            Path('clients/cookie') / Path(self.cookie_file).name,
            Path('backend/clients/cookie') / Path(self.cookie_file).name,
            Path('/app/cookie') / Path(self.cookie_file).name,
            Path('/app/clients/cookie') / Path(self.cookie_file).name,
        ]
        for p in candidates:
            if p.exists():
                try:
                    content = p.read_text(encoding='utf-8', errors='ignore').strip()
                    if not content:
                        continue
                    cookies = {}
                    if '\t' in content:
                        for line in content.splitlines():
                            if not line.strip() or line.startswith('#'):
                                continue
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                cookies[parts[5]] = parts[6]
                    else:
                        for pair in content.split(';'):
                            pair = pair.strip()
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                cookies[k.strip()] = v.strip()
                    if cookies:
                        import logging
                        logging.getLogger(__name__).info(
                            f'[{self.platform_id}] 加载 cookie {p}（{len(cookies)} 个字段）'
                        )
                        return cookies
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).debug(f'加载 cookie 失败 {p}: {e}')
                break
        return {}

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
