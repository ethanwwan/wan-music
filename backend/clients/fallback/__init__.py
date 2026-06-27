"""数据驱动的第三方 API fallback 框架

设计目标：
  1. 新增第三方 API 只需 1 处改动（在 sources/{platform}.py 加 ApiSource）
  2. 自动健康监控（每个源的成功/失败次数）
  3. 串行/并行双模式（parse 串行取最快，search 并行取最多）

参考 musicdl 的设计，但解耦了 search/parse（我们的 /search 和 /song 是分开的）。
"""
from .api_source import ApiSource
from .chain import FallbackChain
from .extractors import (
    extract_first_url,
    extract_nested_url,
    extract_text_url,
    extract_netease_song_info,
    extract_xuanluoge_song_info,
    extract_gdstudio_song_info,
    extract_netease_search,
    extract_netease_official_lyric,
)
from .health import HealthMonitor

__all__ = [
    'ApiSource',
    'FallbackChain',
    'HealthMonitor',
    'extract_first_url',
    'extract_nested_url',
    'extract_text_url',
    'extract_netease_song_info',
    'extract_xuanluoge_song_info',
    'extract_gdstudio_song_info',
    'extract_netease_search',
    'extract_netease_official_lyric',
]
