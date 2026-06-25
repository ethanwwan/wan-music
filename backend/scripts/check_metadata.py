#!/usr/bin/env python3
"""批量检查音频文件元数据

扫描指定目录下的所有音频文件，检查元数据是否完整。
支持格式: MP3, FLAC, M4A/MP4
"""
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import mutagen
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.mp4 import MP4

# ============================================================
# 配置
# ============================================================
SCAN_DIR = '/Volumes/资源库/音乐/歌曲'
SKIP_DIRS = {'歌单原曲'}
SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.mp4'}

# 后端写入的元数据字段（完整才算合格）
REQUIRED_FIELDS = ['title', 'artist', 'album', 'lyrics', 'cover', 'platform', 'song_id']


@dataclass
class MetadataReport:
    """单个文件的元数据检查报告"""
    filepath: str
    filename: str
    file_size: int = 0
    format: str = ''
    # 元数据字段
    title: str = ''
    artist: str = ''
    album: str = ''
    lyrics: str = ''
    platform: str = ''
    song_id: str = ''
    has_cover: bool = False
    cover_count: int = 0
    # 音频信息
    duration: float = 0
    sample_rate: int = 0
    bitrate: int = 0
    channels: int = 0
    bits_per_sample: int = 0
    # 检查结果
    missing_fields: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    all_keys: list = field(default_factory=list)


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / 1024 / 1024:.2f} MB'
    else:
        return f'{size_bytes / 1024 / 1024 / 1024:.2f} GB'


def format_duration(seconds: float) -> str:
    """格式化时长"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f'{minutes}:{secs:02d}'


def check_mp3(filepath: str) -> MetadataReport:
    """检查 MP3 文件元数据 (ID3)"""
    report = MetadataReport(filepath=filepath, filename=os.path.basename(filepath))
    report.file_size = os.path.getsize(filepath)
    report.format = 'MP3'

    try:
        audio = ID3(filepath)
    except Exception as e:
        report.errors.append(f'无法读取 ID3 标签: {e}')
        return report

    # 基础字段
    tit2 = audio.get('TIT2')
    report.title = str(tit2) if tit2 else ''

    tpe1 = audio.get('TPE1')
    report.artist = str(tpe1) if tpe1 else ''

    talb = audio.get('TALB')
    report.album = str(talb) if talb else ''

    # 歌词
    uslt = audio.getall('USLT')
    if uslt:
        report.lyrics = uslt[0].text

    # 封面
    apic = audio.getall('APIC')
    report.has_cover = len(apic) > 0
    report.cover_count = len(apic)

    # 自定义字段
    txxx_p = audio.getall('TXXX:PLATFORM')
    if txxx_p:
        report.platform = txxx_p[0].text[0] if txxx_p[0].text else ''

    txxx_s = audio.getall('TXXX:SONG_ID')
    if txxx_s:
        report.song_id = txxx_s[0].text[0] if txxx_s[0].text else ''

    # 所有键
    report.all_keys = [str(k) for k in audio.keys()]

    # 音频信息（ID3 没有 info，需要通过 mutagen.File 获取）
    try:
        mf = mutagen.File(filepath)
        if mf and hasattr(mf.info, 'length'):
            report.duration = mf.info.length
        if mf and hasattr(mf.info, 'sample_rate'):
            report.sample_rate = mf.info.sample_rate
        if mf and hasattr(mf.info, 'bitrate'):
            report.bitrate = mf.info.bitrate
        if mf and hasattr(mf.info, 'channels'):
            report.channels = mf.info.channels
    except Exception:
        pass

    return report


def check_flac(filepath: str) -> MetadataReport:
    """检查 FLAC 文件元数据 (Vorbis Comment)"""
    report = MetadataReport(filepath=filepath, filename=os.path.basename(filepath))
    report.file_size = os.path.getsize(filepath)
    report.format = 'FLAC'

    try:
        audio = FLAC(filepath)
    except Exception as e:
        report.errors.append(f'无法读取 FLAC 标签: {e}')
        return report

    # 基础字段
    report.title = audio.get('title', [''])[0]
    report.artist = audio.get('artist', [''])[0]
    report.album = audio.get('album', [''])[0]

    # 歌词（不区分大小写）
    for k in audio.keys():
        if k.lower() in ('lyrics', 'lyric') and audio[k]:
            report.lyrics = audio[k][0]
            break

    # 封面
    report.has_cover = len(audio.pictures) > 0
    report.cover_count = len(audio.pictures)

    # 自定义字段
    report.platform = audio.get('PLATFORM', [''])[0]
    report.song_id = audio.get('SONG_ID', [''])[0]

    # 所有键
    report.all_keys = list(audio.keys())

    # 音频信息
    if hasattr(audio.info, 'length'):
        report.duration = audio.info.length
    if hasattr(audio.info, 'sample_rate'):
        report.sample_rate = audio.info.sample_rate
    if hasattr(audio.info, 'bits_per_sample'):
        report.bits_per_sample = audio.info.bits_per_sample
    if hasattr(audio.info, 'channels'):
        report.channels = audio.info.channels
    if hasattr(audio.info, 'bitrate'):
        report.bitrate = audio.info.bitrate

    return report


def check_m4a(filepath: str) -> MetadataReport:
    """检查 M4A/MP4 文件元数据 (iTunes)"""
    report = MetadataReport(filepath=filepath, filename=os.path.basename(filepath))
    report.file_size = os.path.getsize(filepath)
    report.format = 'M4A'

    try:
        audio = MP4(filepath)
    except Exception as e:
        report.errors.append(f'无法读取 MP4 标签: {e}')
        return report

    # 基础字段
    report.title = audio.get('\xa9nam', [''])[0]
    report.artist = audio.get('\xa9ART', [''])[0]
    report.album = audio.get('\xa9alb', [''])[0]

    # 歌词
    report.lyrics = audio.get('\xa9lyr', [''])[0]

    # 封面
    covr = audio.get('covr', [])
    report.has_cover = len(covr) > 0
    report.cover_count = len(covr)

    # 自定义字段
    p_list = audio.get('----:com.apple.iTunes:PLATFORM', [])
    if p_list:
        try:
            report.platform = p_list[0].decode('utf-8')
        except Exception:
            report.platform = str(p_list[0])

    s_list = audio.get('----:com.apple.iTunes:SONG_ID', [])
    if s_list:
        try:
            report.song_id = s_list[0].decode('utf-8')
        except Exception:
            report.song_id = str(s_list[0])

    # 所有键
    report.all_keys = [str(k) for k in audio.keys()]

    # 音频信息
    if hasattr(audio.info, 'length'):
        report.duration = audio.info.length
    if hasattr(audio.info, 'sample_rate'):
        report.sample_rate = audio.info.sample_rate
    if hasattr(audio.info, 'channels'):
        report.channels = audio.info.channels
    if hasattr(audio.info, 'bitrate'):
        report.bitrate = audio.info.bitrate

    return report


def check_metadata(filepath: str) -> MetadataReport:
    """根据文件扩展名选择检查函数"""
    ext = Path(filepath).suffix.lower()
    if ext == '.mp3':
        return check_mp3(filepath)
    elif ext == '.flac':
        return check_flac(filepath)
    elif ext in ('.m4a', '.mp4'):
        return check_m4a(filepath)
    else:
        report = MetadataReport(filepath=filepath, filename=os.path.basename(filepath))
        report.errors.append(f'不支持的格式: {ext}')
        return report


def analyze_report(report: MetadataReport) -> list:
    """分析报告，返回缺失字段列表"""
    missing = []
    if not report.title:
        missing.append('title')
    if not report.artist:
        missing.append('artist')
    if not report.album:
        missing.append('album')
    if not report.lyrics:
        missing.append('lyrics')
    if not report.has_cover:
        missing.append('cover')
    if not report.platform:
        missing.append('platform')
    if not report.song_id:
        missing.append('song_id')
    return missing


def print_report_detail(report: MetadataReport, index: int):
    """打印单个文件的详细报告"""
    print(f'\n{"─" * 70}')
    print(f'  [{index}] {report.filename}')
    print(f'  路径: {report.filepath}')
    print(f'  大小: {format_size(report.file_size)}  格式: {report.format}')

    if report.errors:
        print(f'  ⚠ 错误: {", ".join(report.errors)}')
        return

    # 音频信息
    if report.duration:
        print(f'  时长: {format_duration(report.duration)}  采样率: {report.sample_rate} Hz  声道: {report.channels}', end='')
        if report.bits_per_sample:
            print(f'  位深: {report.bits_per_sample} bit', end='')
        if report.bitrate:
            print(f'  比特率: {report.bitrate // 1000} kbps', end='')
        print()

    # 元数据字段
    print(f'  ┌─ 元数据检查 ─────────────────────────────────')
    fields = [
        ('title',    '标题',   report.title),
        ('artist',   '歌手',   report.artist),
        ('album',    '专辑',   report.album),
        ('lyrics',   '歌词',   f'{len(report.lyrics)} 字符' if report.lyrics else ''),
        ('cover',    '封面',   f'{report.cover_count} 张' if report.has_cover else ''),
        ('platform', '平台',   report.platform),
        ('song_id',  '歌曲ID', report.song_id),
    ]
    for field_key, label, value in fields:
        status = '✓' if value else '✗'
        display = value if value else '(空)'
        print(f'  │ {status} {label}: {display}')
    print(f'  └──────────────────────────────────────────────')

    # 所有元数据键
    if report.all_keys:
        print(f'  所有键({len(report.all_keys)}): {", ".join(report.all_keys[:20])}' +
              (' ...' if len(report.all_keys) > 20 else ''))


def print_summary(results: dict, total_files: int):
    """打印汇总统计"""
    print(f'\n{"═" * 70}')
    print(f'  扫描完成: 共 {total_files} 个文件')
    print(f'{"═" * 70}')

    # 按格式统计
    format_counts = {}
    for report in results['all']:
        fmt = report.format
        format_counts[fmt] = format_counts.get(fmt, 0) + 1
    print(f'\n  【格式分布】')
    for fmt, count in sorted(format_counts.items()):
        print(f'    {fmt}: {count} 个')

    # 缺失字段统计
    missing_stats = {}
    for report in results['incomplete']:
        for field_name in report.missing_fields:
            missing_stats[field_name] = missing_stats.get(field_name, 0) + 1

    print(f'\n  【元数据完整性】')
    print(f'    完整: {len(results["complete"])} 个')
    print(f'    不完整: {len(results["incomplete"])} 个')
    print(f'    错误: {len(results["errors"])} 个')

    if missing_stats:
        print(f'\n  【缺失字段统计】')
        field_labels = {
            'title': '标题', 'artist': '歌手', 'album': '专辑',
            'lyrics': '歌词', 'cover': '封面', 'platform': '平台', 'song_id': '歌曲ID'
        }
        for field_name, count in sorted(missing_stats.items(), key=lambda x: -x[1]):
            label = field_labels.get(field_name, field_name)
            print(f'    {label}({field_name}): {count} 个文件缺失')

    # 列出不完整的文件
    if results['incomplete']:
        print(f'\n  【不完整文件列表】')
        for i, report in enumerate(results['incomplete'], 1):
            missing_labels = []
            field_labels = {
                'title': '标题', 'artist': '歌手', 'album': '专辑',
                'lyrics': '歌词', 'cover': '封面', 'platform': '平台', 'song_id': '歌曲ID'
            }
            for f in report.missing_fields:
                missing_labels.append(field_labels.get(f, f))
            print(f'    {i}. {report.filename}')
            print(f'       缺失: {", ".join(missing_labels)}')

    # 列出错误文件
    if results['errors']:
        print(f'\n  【错误文件列表】')
        for i, report in enumerate(results['errors'], 1):
            print(f'    {i}. {report.filename}')
            for err in report.errors:
                print(f'       错误: {err}')


def scan_directory(scan_dir: str, skip_dirs: set) -> list:
    """递归扫描目录，返回音频文件路径列表"""
    audio_files = []
    scan_dir = os.path.abspath(scan_dir)
    skip_abs = {os.path.abspath(os.path.join(scan_dir, d)) for d in skip_dirs}

    for root, dirs, files in os.walk(scan_dir):
        # 跳过指定目录
        root_abs = os.path.abspath(root)
        if any(root_abs == s or root_abs.startswith(s + os.sep) for s in skip_abs):
            continue

        for f in sorted(files):
            ext = Path(f).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                audio_files.append(os.path.join(root, f))

    return audio_files


# ============================================================
# 文件大小分析
# ============================================================
def print_top_files(reports: list, n: int = 10, label: str = '', ascending: bool = False):
    """打印 Top N 文件（按大小）"""
    if not reports:
        return
    sorted_reports = sorted(reports, key=lambda r: r.file_size, reverse=not ascending)
    top = sorted_reports[:n]

    arrow = '↓' if ascending else '↑'
    print(f'\n{"═" * 70}')
    print(f'  {label} ({arrow} {len(top)} 个)')
    print(f'{"═" * 70}')

    for i, r in enumerate(top, 1):
        status = '✓' if not r.missing_fields and not r.errors else '✗'
        print(f'  {i:3d}. {status} {format_size(r.file_size):>10} - {r.format:>4} - {r.filename}')
        if r.missing_fields:
            print(f'        缺失: {", ".join(r.missing_fields)}')


def main():
    scan_dir = SCAN_DIR
    if len(sys.argv) > 1:
        scan_dir = sys.argv[1]

    scan_dir = os.path.abspath(scan_dir)
    if not os.path.isdir(scan_dir):
        print(f'错误: 目录不存在: {scan_dir}')
        sys.exit(1)

    print(f'扫描目录: {scan_dir}')
    print(f'跳过目录: {", ".join(SKIP_DIRS)}')
    print(f'支持格式: {", ".join(SUPPORTED_EXTENSIONS)}')
    print(f'正在扫描...')

    audio_files = scan_directory(scan_dir, SKIP_DIRS)
    print(f'找到 {len(audio_files)} 个音频文件')

    if not audio_files:
        print('没有找到音频文件')
        return

    results = {
        'all': [],
        'complete': [],
        'incomplete': [],
        'errors': [],
    }

    for i, filepath in enumerate(audio_files, 1):
        report = check_metadata(filepath)
        report.missing_fields = analyze_report(report)
        results['all'].append(report)

        if report.errors:
            results['errors'].append(report)
        elif not report.missing_fields:
            results['complete'].append(report)
        else:
            results['incomplete'].append(report)

        # 实时打印进度和每个文件的摘要
        status = '✓' if not report.missing_fields and not report.errors else '✗'
        print(f'  [{i}/{len(audio_files)}] {status} {report.filename}')

    # 打印不完整文件的详细信息
    if results['incomplete']:
        print(f'\n{"═" * 70}')
        print(f'  不完整文件详细报告 ({len(results["incomplete"])} 个)')
        print(f'{"═" * 70}')
        for i, report in enumerate(results['incomplete'], 1):
            print_report_detail(report, i)

    # 打印错误文件的详细信息
    if results['errors']:
        print(f'\n{"═" * 70}')
        print(f'  错误文件详细报告 ({len(results["errors"])} 个)')
        print(f'{"═" * 70}')
        for i, report in enumerate(results['errors'], 1):
            print_report_detail(report, i)

    print_summary(results, len(audio_files))

    # 文件大小分析
    print_top_files(results['all'], 10, "文件最大的 10 个")
    print_top_files(results['all'], 10, "文件最小的 10 个", ascending=True)


if __name__ == '__main__':
    main()
