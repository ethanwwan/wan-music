"""音频工具函数

提供音频文件类型检测、比特率检测、封面下载等功能
"""
import logging
import os
import io
import shutil
import subprocess
import tempfile
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# 封面写入元数据的最大体积阈值（500K）
COVER_SIZE_LIMIT = 500 * 1024

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


def _sips_resize(input_path: str, output_path: str, max_dim: int, quality: int) -> bool:
    """调用 sips 缩放图片（macOS 系统工具）"""
    try:
        cmd = [
            'sips',
            '-s', 'format', 'jpeg',
            '-s', 'formatOptions', str(quality),
            '--resampleHeightWidthMax', str(max_dim),
            input_path,
            '--out', output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.debug(f"sips 失败: {e}")
        return False


def compress_cover(raw_bytes: bytes, max_size: int = COVER_SIZE_LIMIT) -> bytes:
    """压缩图片到指定体积以下（默认 500K）

    使用 macOS sips 工具尝试不同尺寸/质量组合，找到第一个 <= max_size 的版本。
    如果压缩失败（如非 macOS），返回原图。
    """
    if not raw_bytes or len(raw_bytes) <= max_size:
        return raw_bytes

    tmpdir = tempfile.mkdtemp(prefix='cover_')
    try:
        input_path = os.path.join(tmpdir, 'input')
        with open(input_path, 'wb') as f:
            f.write(raw_bytes)

        # 尝试不同尺寸 + 质量组合
        for max_dim, qualities in [
            (1400, (85, 75, 65, 55, 45, 35, 25)),
            (1200, (85, 75, 65, 55, 45, 35)),
            (1000, (85, 75, 65, 55, 45, 35)),
            (800,  (85, 75, 65, 55, 45, 35)),
            (600,  (85, 75, 65, 55, 45, 35)),
            (500,  (85, 75, 65, 55, 45, 35, 25, 20)),
        ]:
            for quality in qualities:
                output_path = os.path.join(tmpdir, f'out_{max_dim}_{quality}.jpg')
                if not _sips_resize(input_path, output_path, max_dim, quality):
                    continue
                size = os.path.getsize(output_path)
                if size <= max_size:
                    with open(output_path, 'rb') as f:
                        return f.read()
                try:
                    os.remove(output_path)
                except OSError:
                    pass
        return b''
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def download_cover(cover_url: str, max_size: int = COVER_SIZE_LIMIT) -> Optional[bytes]:
    """下载封面图片，自动压缩到 500K 以下

    Args:
        cover_url: 封面图片 URL
        max_size: 最大字节数（默认 500K），超过会自动压缩

    Returns:
        图片二进制数据（JPEG），如果下载失败返回 None
    """
    if not cover_url:
        return None
    try:
        # 下载最多 10MB（防止异常大图）
        download_limit = 10 * 1024 * 1024
        resp = requests.get(cover_url, timeout=15, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        content = b''
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > download_limit:
                logger.warning(f"封面图片超过下载上限 ({download_limit} bytes)")
                return None

        # 如果原图已经 <= max_size，直接返回
        if len(content) <= max_size:
            return content

        # 否则压缩到 max_size 以下
        compressed = compress_cover(content, max_size)
        if compressed:
            logger.debug(f"封面压缩 {len(content)} -> {len(compressed)} bytes")
            return compressed

        # 压缩失败（极少见），返回原图（让上层决定）
        logger.warning(f"封面压缩失败，返回原图 ({len(content)} bytes)")
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
