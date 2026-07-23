"""后端统一配置：平台 / 音质 / 文件命名格式

所有配置集中管理，前端通过 /config 接口拉取。
"""
from typing import Dict, List, Any


# ==================== 平台配置 ====================

PLATFORMS: List[Dict[str, str]] = [
    {
        'id': 'netease',
        'name': '网易云音乐',
        'color': '#e72d2c',
        'description': '网易云音乐平台',
    },
    {
        'id': 'qq',
        'name': 'QQ音乐',
        'color': '#31c27c',
        'description': 'QQ音乐平台',
    },
    {
        'id': 'kugou',
        'name': '酷狗音乐',
        'color': '#2a8eff',
        'description': '酷狗音乐平台',
    },
    {
        'id': 'kuwo',
        'name': '酷我音乐',
        'color': '#ff6600',
        'description': '酷我音乐平台',
    },
]


# ==================== 音质配置 ====================

# 数值越小优先级越高（用于下拉排序和 fallback 链）
QUALITY_LEVELS: Dict[str, Dict[str, Any]] = {
    'standard': {
        'value': 'standard',
        'label': '标准',
        'description': '128kbps',
        'priority': 9,
        'format': 'MP3',
    },
    'exhigh': {
        'value': 'exhigh',
        'label': '极高',
        'description': '320kbps',
        'priority': 8,
        'format': 'MP3/AAC',
    },
    'lossless': {
        'value': 'lossless',
        'label': '无损',
        'description': 'FLAC',
        'priority': 7,
        'format': 'FLAC',
    },
    'hires': {
        'value': 'hires',
        'label': 'Hi-Res',
        'description': 'FLAC 24bit',
        'priority': 6,
        'format': 'FLAC 24bit',
    },
    'jyeffect': {
        'value': 'jyeffect',
        'label': '高清环绕声',
        'description': 'Spatial Audio',
        'priority': 5,
        'format': 'Spatial',
    },
    'sky': {
        'value': 'sky',
        'label': '沉浸环绕声',
        'description': 'Surround Audio',
        'priority': 4,
        'format': 'Surround',
    },
    'dolby': {
        'value': 'dolby',
        'label': '杜比全景声',
        'description': 'Dolby Atmos',
        'priority': 3,
        'format': 'Dolby Atmos',
    },
    'jysurround': {
        'value': 'jysurround',
        'label': '臻音全景声',
        'description': 'Surround 3D Audio',
        'priority': 2,
        'format': 'Surround 3D',
    },
    'jymaster': {
        'value': 'jymaster',
        'label': '超清母带',
        'description': 'FLAC 24bit/96kHz',
        'priority': 1,
        'format': 'FLAC 24bit/96kHz',
    },
}


# ==================== 平台-音质映射 ====================

# 每个平台在第三方 API 实际能获取到的最高音质
# 数据来源：实测（见 scripts/probe_apis.py + v1.1.3 对比测试）
#
# 实测结论（2026-06-28）：
# - netease: 第三方源（xuanluoge/cunyu/gdstudio/cenguigui）能拿到 lossless 和 hires
# - qq: vkeys quality=13 验证能拿 FLAC（25.3MB Q000 prefix），max=lossless
# - kugou: haitanw 用 SQFileHash 能拿 FLAC，max=lossless
# - kuwo: cenguigui (cgg) 拿 FLAC lossless 验证可用，max=lossless
#
# fallback_chain 是**平台能力上限**（不考虑单首歌曲），具体每首歌能下到哪个
# 等级由该歌曲的 qualityMap 决定（music_client.get_song 在循环时会用 qualityMap 过滤）
PLATFORM_QUALITY_SUPPORT: Dict[str, Dict[str, Any]] = {
    'netease': {
        'max_quality': 'hires',
        'fallback_chain': ['hires', 'lossless', 'exhigh', 'standard'],
    },
    'qq': {
        # vkeys quality=13 (SPATIAL_AUDIO) 验证能返 FLAC
        # Q000 prefix 实际是 Atmos 2.0 (25.3MB)，不是真正 lossless
        # max_quality 保守设为 lossless（不写 hires/dolby，避免假象）
        'max_quality': 'lossless',
        'fallback_chain': ['lossless', 'exhigh', 'standard'],
        'note': 'vkeys quality=13 能拿 FLAC (25MB+，Q000 prefix)',
    },
    'kugou': {
        'max_quality': 'lossless',
        'fallback_chain': ['lossless', 'exhigh', 'standard'],
        'note': 'FLAC 用 SQFileHash 命中，MP3 用 FileHash 命中（normalize 已分别存为 id/mp3_hash）',
    },
    'kuwo': {
        # 搜索 qualityMap 含 jymaster（77%）但唯一 jymaster 源 ccwu 已失效，
        # 可用源（nxinxz）hires/standard/exhigh 只返 mp3，lossless 返 flac
        'max_quality': 'lossless',
        'fallback_chain': ['lossless', 'exhigh', 'standard'],
        'note': '搜索 qualityMap 含 jymaster 但无可用源，实际最高=lossless',
    },
}


def get_platform_quality_chain(platform: str, requested: str = 'lossless',
                                quality_map: dict = None) -> List[str]:
    """获取平台在指定请求音质下的降级链

    逻辑（两层过滤）：
    1. 先按平台能力过滤：从 requested 往下降，找到平台 max_quality 对应的子链
    2. 再按 qualityMap 过滤：只保留该歌曲实际有该音质的等级

    Args:
        platform: 平台 ID
        requested: 用户请求的音质
        quality_map: 该歌曲的可用品质字典（可选），格式 {quality: {br, size}}

    Returns:
        该歌曲实际可用的音质降级链（从高到低，最少 1 个，最多 4 个）
    """
    plat = PLATFORM_QUALITY_SUPPORT.get(platform)
    if not plat:
        base_chain = [requested]
    else:
        chain = plat['fallback_chain']
        if requested in chain:
            idx = chain.index(requested)
            base_chain = chain[idx:]
        else:
            # 请求的音质超出平台能力，按平台 max_quality 起步
            base_chain = list(chain)

    # 关键：用 qualityMap 过滤不可用音质
    if quality_map and isinstance(quality_map, dict) and quality_map:
        # 取 base_chain 与 quality_map 的交集（按顺序）
        filtered = [q for q in base_chain if q in quality_map]
        if filtered:
            return filtered
        # 交集为空（所有基础音质都不可用），从 qualityMap 中选最高可用
        try:
            from ..sources.project_source.quality_config import match_quality
        except (ImportError, ValueError):
            import sys, os
            _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if _root not in sys.path:
                sys.path.insert(0, _root)
            from sources.project_source.quality_config import match_quality
        # 找到 qualityMap 中 base_chain 范围内能降级到的最高
        best = ''
        for q in base_chain:
            m = match_quality(quality_map, q)
            if m:
                best = m
                break
        if not best:
            # 最后兜底：qualityMap 中任意最高
            best = match_quality(quality_map, 'standard')
        return [best] if best else base_chain

    return base_chain


# ==================== 文件命名格式 ====================

FILENAME_FORMATS: List[Dict[str, str]] = [
    {
        'value': 'song-artist',
        'label': '歌曲名 - 歌手名',
        'example': '他不懂 - 张杰.flac',
    },
    {
        'value': 'artist-song',
        'label': '歌手名 - 歌曲名',
        'example': '张杰 - 他不懂.flac',
    },
    {
        'value': 'song-only',
        'label': '仅歌曲名',
        'example': '他不懂.flac',
    },
]


# ==================== 辅助函数 ====================

def get_quality_options() -> List[Dict[str, Any]]:
    """获取音质选项列表（按优先级排序）"""
    return sorted(QUALITY_LEVELS.values(), key=lambda x: x['priority'])


def get_filename_format_options() -> List[Dict[str, str]]:
    """获取文件命名格式选项"""
    return list(FILENAME_FORMATS)


def get_platforms() -> List[Dict[str, str]]:
    """获取平台列表"""
    return list(PLATFORMS)


def get_full_config() -> Dict[str, Any]:
    """获取完整配置（前端 /config 接口使用）"""
    import time
    return {
        'version': '1.0',
        'timestamp': int(time.time()),
        'platforms': get_platforms(),
        'qualities': get_quality_options(),
        'filename_formats': get_filename_format_options(),
        'platform_quality_support': PLATFORM_QUALITY_SUPPORT,
        'lines': [
            {'id': 0, 'name': '项目源', 'description': '自有音乐数据源'},
            {'id': 1, 'name': 'musicdl', 'description': 'musicdl 底层源'},
        ],
    }
