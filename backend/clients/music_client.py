"""音乐客户端总控模块

作为多平台音乐客户端的总控中心：
  - 网易云音乐（netease_client）
  - QQ音乐（qq_client）
  - 酷狗音乐（kugou_client）
  - 酷我音乐（kuwo_client）

提供统一的 API 接口（search / get_song），前端可指定数据源和平台。
所有平台 search 走官方 API，一次返回完整元信息（album / cover / qualityMap / pay）。
"""
import logging
from typing import Any, Dict, List, Optional

from .base_client import BaseMusicClient
from .netease_client import NeteaseClient, netease_client
from .qq_client import QQClient, qq_client
from .kugou_client import KugouClient, kugou_client
from .kuwo_client import KuwoClient, kuwo_client

logger = logging.getLogger(__name__)


class MusicClient:
    """统一的音乐客户端总控类"""

    PLATFORM_REGISTRY = [
        ('netease', netease_client, '网易云音乐', '#e72d2c', '网易云音乐平台'),
        ('qq',      qq_client,      'QQ音乐',    '#31c27c', 'QQ音乐平台'),
        ('kugou',   kugou_client,   '酷狗音乐',  '#2a8eff', '酷狗音乐平台'),
        ('kuwo',    kuwo_client,    '酷我音乐',  '#ff6600', '酷我音乐平台'),
    ]

    def __init__(self):
        self.platform_clients: Dict[str, BaseMusicClient] = {}
        for platform_id, client, *_ in self.PLATFORM_REGISTRY:
            self.register_client(platform_id, client)
        self.default_platform = 'netease'

    def register_client(self, platform: str, client: BaseMusicClient) -> None:
        if not isinstance(client, BaseMusicClient):
            raise ValueError("客户端必须继承自 BaseMusicClient")
        self.platform_clients[platform] = client
        logger.info(f"已注册平台: {platform}")

    def get_platforms(self) -> List[Dict[str, str]]:
        """获取可用平台列表（id / name / color / description）"""
        return [
            {'id': p, 'name': name, 'color': color, 'description': desc}
            for p, _, name, color, desc in self.PLATFORM_REGISTRY
        ]

    def _get_client(self, platform: str) -> BaseMusicClient:
        platform = platform or self.default_platform
        client = self.platform_clients.get(platform)
        if not client:
            raise ValueError(f"不支持的平台: {platform}")
        return client

    # ==================== 业务方法 ====================

    def search(self, keyword: str, platform: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """搜索歌曲（永远只搜歌曲；URL 由 service 层另行解析）

        4 个平台 search 链都走官方 API，一次返回完整元信息
        （album / cover / qualityMap / pay），不需要后置补全
        """
        client = self._get_client(platform)
        result = client.search(keyword, limit=limit)
        return result.get('data', []) if isinstance(result, dict) else []

    def get_song(self, song_id: Any, quality: str = 'lossless',
                 platform: str = None, with_lyric: bool = True,
                 quality_map: dict = None) -> Optional[Dict[str, Any]]:
        """一次性获取歌曲完整信息（信息 + URL + 可选歌词）

        支持基于 qualityMap 的智能降级（按用户请求的音质）：
        1. 先按平台能力（PLATFORM_QUALITY_SUPPORT.fallback_chain）过滤
        2. 再按歌曲实际可用的 qualityMap 过滤
        3. 从用户请求的音质开始，依次尝试链中更低的音质
        4. 用户请求超清母带但该歌曲只有 exhigh → 直接从 exhigh 开始，
           跳过 hires/lossless，节省 5-10 秒

        song_id 可以是字符串（直接是 hash/id），也可以是 dict
        （包含 id 和 mp3_hash 字段，用于酷狗的 FLAC/MP3 双 hash 场景）

        quality_map（可选）：该歌曲的可用音质字典 {quality: {br, size}}
        - 来自 search 结果，可让降级更精准
        - 优先级：search 时的 qualityMap > 平台 fallback_chain 默认行为

        Returns:
            None 表示完全失败
        """
        try:
            from ..app_config import get_platform_quality_chain
        except (ImportError, ValueError):
            # 兼容直接以脚本形式运行时（相对导入失败时走绝对路径）
            import os, sys
            _backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if _backend_root not in sys.path:
                sys.path.insert(0, _backend_root)
            from app_config import get_platform_quality_chain

        client = self._get_client(platform)

        # song_id 可能是 dict（包含多 hash 信息）
        mp3_hash = ''
        if isinstance(song_id, dict):
            mp3_hash = str(song_id.get('mp3_hash') or '')
            song_id_str = str(song_id.get('id') or song_id.get('hash') or '')
            # 兼容：dict 中也带 qualityMap
            if not quality_map:
                quality_map = song_id.get('qualityMap')
        else:
            song_id_str = str(song_id)

        # 关键：基于 qualityMap + 平台能力，获取该歌曲实际可用的降级链
        # 例：用户请求 jymaster，qualityMap 只有 exhigh → 链是 [exhigh, standard]
        #     用户请求 lossless，qualityMap 有 lossless/exhigh → 链是 [lossless, exhigh]
        chain = get_platform_quality_chain(platform, quality, quality_map)

        if chain and chain[0] != quality:
            logger.info(
                f"音质降级预过滤: {platform}/{song_id_str} "
                f"请求={quality} → 实际起始={chain[0]}（qualityMap 或平台能力限制）"
            )

        last_result = None
        for try_quality in chain:
            # 酷狗特殊：lossless/hires 用 FLAC hash（id = SQFileHash），
            # exhigh/standard 用 MP3 hash（mp3_hash = FileHash）
            if platform == 'kugou' and mp3_hash and try_quality in ('exhigh', 'standard'):
                parse_id = mp3_hash
            else:
                parse_id = song_id_str

            result = client.get_song(parse_id, try_quality, with_lyric=with_lyric)
            if result and result.get('url'):
                # 标记实际使用的音质（前端可基于此判断是否降级）
                if try_quality != quality:
                    result['requested_quality'] = quality
                    # 区分升级/降级（用音质 rank 比较）
                    from .fallback.chain import _quality_rank
                    actual_rank = _quality_rank(try_quality)
                    requested_rank = _quality_rank(quality)
                    if actual_rank < requested_rank:
                        # 实际音质低于请求音质 → 真降级
                        result['level_fallback'] = True
                        result['level_upgrade'] = False
                        logger.info(
                            f"音质降级: {platform}/{song_id_str} "
                            f"{quality} → {try_quality}"
                        )
                    else:
                        # 实际音质高于请求音质 → 升级（数据源给得比请求更好）
                        result['level_fallback'] = False
                        result['level_upgrade'] = True
                        logger.info(
                            f"音质升级: {platform}/{song_id_str} "
                            f"{quality} → {try_quality} (数据源给得更好)"
                        )
                return result
            last_result = result

        return last_result

    def parse_playlist(self, playlist_id: str, platform: str = None,
                       page: int = 1, size: int = 100) -> Optional[Dict[str, Any]]:
        """解析歌单：返回 {'name','creator','cover','trackCount','tracks', 'source', 'api_source'}

        Returns:
            None 表示该平台暂不支持歌单解析
        """
        client = self._get_client(platform)
        if not hasattr(client, 'parse_playlist'):
            return None
        return client.parse_playlist(playlist_id, page=page, size=size)


# 全局单例
music_client = MusicClient()


# ==================== 向后兼容的函数接口 ====================

def search_music(keywords: str, platform: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    return music_client.search(keywords, platform, limit=limit)


def get_song(song_id: str, quality: str, platform: str = None,
             with_lyric: bool = True) -> Optional[Dict[str, Any]]:
    """获取歌曲完整信息（向后兼容，新接口推荐用 music_client.get_song）"""
    return music_client.get_song(song_id, quality, platform, with_lyric=with_lyric)


def parse_playlist(playlist_id: str, platform: str = None,
                   page: int = 1, size: int = 100) -> Optional[Dict[str, Any]]:
    """解析歌单（向后兼容函数）"""
    return music_client.parse_playlist(playlist_id, platform, page=page, size=size)


def get_platforms() -> List[Dict[str, str]]:
    return music_client.get_platforms()
