"""音质等级配置模块"""

from enum import Enum
from typing import Dict


class QualityLevel(Enum):
    """音质等级枚举"""
    STANDARD = "standard"
    EXHIGH = "exhigh"
    LOSSLESS = "lossless"
    HIRES = "hires"
    SKY = "sky"
    JYEFFECT = "jyeffect"
    JYMASTER = "jymaster"
    DOLBY = "dolby"


QUALITY_LABELS: Dict[str, str] = {
    "standard": "标准",
    "exhigh": "极高",
    "lossless": "无损",
    "hires": "Hi-Res",
    "sky": "沉浸环绕声",
    "jyeffect": "高清臻音",
    "jymaster": "超清母带",
    "dolby": "杜比全景声"
}


QUALITY_DESCRIPTIONS: Dict[str, str] = {
    "standard": "128kbps",
    "exhigh": "320kbps",
    "lossless": "FLAC",
    "hires": "FLAC 24bit",
    "sky": "Surround Audio",
    "jyeffect": "Spatial Audio",
    "jymaster": "FLAC 24bit/96kHz",
    "dolby": "Dolby Atmos"
}


QUALITY_PRIORITY = [
    "dolby",
    "jymaster",
    "jyeffect",
    "hires",
    "sky",
    "lossless",
    "exhigh",
    "standard"
]


def get_quality_label(quality: str) -> str:
    """获取音质标签"""
    return QUALITY_LABELS.get(quality, quality)


def get_quality_description(quality: str) -> str:
    """获取音质描述"""
    return QUALITY_DESCRIPTIONS.get(quality, "")


def is_valid_quality(quality: str) -> bool:
    """验证音质是否有效"""
    return quality in QUALITY_LABELS


def get_quality_priority(quality: str) -> int:
    """获取音质优先级（数值越小优先级越高）"""
    try:
        return QUALITY_PRIORITY.index(quality)
    except ValueError:
        return len(QUALITY_PRIORITY)


def get_qualities_to_try(quality: str) -> list:
    """获取音质尝试列表（包含降级策略）"""
    try:
        start_idx = QUALITY_PRIORITY.index(quality)
        return QUALITY_PRIORITY[start_idx:]
    except ValueError:
        return [quality] + QUALITY_PRIORITY


def get_all_qualities() -> list:
    """获取所有音质值"""
    return list(QUALITY_LABELS.keys())


def get_default_quality() -> str:
    """获取默认音质"""
    return "lossless"


# 统一音质优先级（从高到低，用于 bestQuality 匹配）
_UNIFIED_QUALITY_PRIORITY = [
    "jymaster", "jyeffect", "hires", "lossless", "dolby", "sky", "exhigh", "standard"
]


def match_quality(quality_map: dict, requested: str = 'lossless') -> str:
    """根据用户请求的音质，在 quality_map 中匹配最佳可用音质

    优先级逻辑：
    1. 精确匹配 requested
    2. 降级：从 requested 往低找第一个可用的
    3. 兜底：返回 quality_map 中最高音质
    """
    if not quality_map:
        return ''

    # 1. 精确匹配
    if requested in quality_map:
        return requested

    # 2. 从 requested 往低降级
    try:
        start = _UNIFIED_QUALITY_PRIORITY.index(requested)
    except ValueError:
        start = len(_UNIFIED_QUALITY_PRIORITY)
    for qk in _UNIFIED_QUALITY_PRIORITY[start:]:
        if qk in quality_map:
            return qk

    # 3. 兜底：最高音质
    for qk in _UNIFIED_QUALITY_PRIORITY:
        if qk in quality_map:
            return qk

    return next(iter(quality_map), '')