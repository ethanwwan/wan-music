"""音频工具函数

提供音频文件类型检测、比特率检测、封面下载等功能
"""
import logging
import os
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# 音频格式的 magic bytes
AUDIO_SIGNATURES = [
    (b'ID3', 'mp3'),                 # MP3 with ID3v2 tag
    (b'\xff\xfb', 'mp3'),            # MP3 frame sync
    (b'\xff\xf3', 'mp3'),            # MP3 frame sync
    (b'\xff\xf2', 'mp3'),            # MP3 frame sync
    (b'fLaC', 'flac'),               # FLAC
    (b'\x00\x00\x00', 'mp4'),        # MP4/M4A (ftyp box starts after)
    (b'OggS', 'ogg'),                # OGG
    (b'RIFF', 'wav'),                # WAV
]

# MP3 比特率表（简化版，仅常用比特率）
MP3_BITRATES_V2_L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]


def get_extension(url: str, fallback: str = '.mp3') -> str:
    """从 URL 中提取文件扩展名

    Args:
        url: 音频文件 URL
        fallback: 提取不到时的默认扩展名

    Returns:
        带点的扩展名（如 .mp3）
    """
    path = urlparse(url).path
    if '.' in path:
        ext = '.' + path.rsplit('.', 1)[-1].lower()
        if ext in ('.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.wav', '.opus'):
            return ext
    return fallback if fallback.startswith('.') else '.' + fallback


def detect_audio_type(file_path: str) -> Optional[str]:
    """通过 magic bytes 检测音频文件真实类型

    Args:
        file_path: 音频文件路径

    Returns:
        文件类型字符串（'mp3'/'flac'/'m4a'/'ogg'/'wav'）或 None
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        for sig, ext in AUDIO_SIGNATURES:
            if header.startswith(sig):
                # MP4 还需要验证 ftyp box
                if ext == 'mp4':
                    f.seek(4)
                    box_size = int.from_bytes(f.read(4), 'big')
                    f.seek(box_size)
                    if f.read(4) == b'ftyp':
                        return ext
                else:
                    return ext
    except Exception as e:
        logger.debug(f"检测音频类型失败: {e}")
    return None


def detect_mp3_bitrate(file_path: str) -> Optional[int]:
    """检测 MP3 文件的比特率（kbps）

    Args:
        file_path: MP3 文件路径

    Returns:
        比特率（kbps）或 None
    """
    try:
        with open(file_path, 'rb') as f:
            # 跳过 ID3v2 标签头（如果有）
            header = f.read(10)
            if header[:3] == b'ID3':
                # ID3v2 头: 10 bytes
                tag_size = (header[6] & 0x7f) << 21 | (header[7] & 0x7f) << 14 | (header[8] & 0x7f) << 7 | (header[9] & 0x7f)
                f.seek(10 + tag_size)
            else:
                f.seek(0)

            # 查找第一个 MP3 frame sync
            data = f.read(4096)
            for i in range(len(data) - 4):
                if data[i] == 0xff and (data[i+1] & 0xe0) == 0xe0:
                    # 找到 frame sync
                    byte2 = data[i+2]
                    version = (byte2 >> 3) & 0x03
                    layer = (byte2 >> 1) & 0x03
                    byte3 = data[i+3]
                    bitrate_idx = (byte3 >> 4) & 0x0f

                    # 简化版：只支持 MPEG2 Layer 3
                    if version == 2 and layer == 1:  # MPEG2, Layer 3
                        if 1 <= bitrate_idx <= 14:
                            return MP3_BITRATES_V2_L3[bitrate_idx]
                    return None
    except Exception as e:
        logger.debug(f"检测 MP3 比特率失败: {e}")
    return None


def download_cover(cover_url: str, max_size: int = 3145728) -> bytes | None:
    """下载封面图片（限制大小，默认 3MB）

    Args:
        cover_url: 封面图片 URL
        max_size: 最大字节数（默认 3MB）

    Returns:
        图片二进制数据或 None
    """
    if not cover_url:
        return None
    try:
        resp = requests.get(cover_url, timeout=10, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        content = b''
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_size:
                logger.warning(f"封面图片超过大小限制 ({max_size} bytes)")
                return None
        return content
    except Exception as e:
        logger.warning(f"下载封面失败: {e}")
        return None


def safe_remove(path: str) -> bool:
    """安全删除文件（忽略错误）

    Args:
        path: 文件路径

    Returns:
        True 成功删除或文件不存在，False 删除失败
    """
    try:
        if os.path.exists(path):
            os.remove(path)
        return True
    except Exception:
        return False
