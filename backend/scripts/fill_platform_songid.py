#!/usr/bin/env python3
"""为缺少 platform 和 song_id 的音频文件补写元数据

从文件名解析歌曲名和歌手，通过网易云 API 搜索匹配，写入 PLATFORM 和 SONG_ID。
支持多种搜索策略和模糊匹配。
"""
import os
import re
import sys
import time
import logging
from pathlib import Path
from difflib import SequenceMatcher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from clients.netease_client import netease_client
from utils.metadata import read_metadata

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

SCAN_DIR = '/Volumes/资源库/音乐/歌曲'
SKIP_DIRS = {'歌单原曲'}
SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.mp4'}
PLATFORM = 'netease'

# 所有可能的歌手分隔符
ARTIST_SEPARATORS = [',', '，', ';', '；', '&', '\\', '、', '|', '_']


def parse_filename(filename: str):
    """从文件名解析歌曲名和歌手"""
    stem = Path(filename).stem
    match = re.match(r'^(.+?)\s*-\s*(.+)$', stem)
    if not match:
        return None
    song_name = match.group(1).strip()
    artist_name = match.group(2).strip()
    if not song_name or not artist_name:
        return None
    return song_name, artist_name


def split_artists(artist_str: str) -> list:
    """拆分歌手字符串为列表"""
    if not artist_str:
        return []
    for sep in ARTIST_SEPARATORS:
        if sep in artist_str:
            return [a.strip() for a in artist_str.split(sep) if a.strip()]
    return [artist_str.strip()]


def normalize_for_compare(s: str) -> str:
    """标准化用于比较"""
    s = s.lower().strip()
    # 统一括号
    s = re.sub(r'[（）\(\)\[\]【】「」]', '', s)
    # 去掉版本后缀
    s = re.sub(r'\s*(live|翻唱|cover|remix|版|版).*$', '', s, flags=re.IGNORECASE)
    # 去掉多余空格和标点
    s = re.sub(r'[\s\-_.,，。、;；!！?？\'"「」]', '', s)
    return s


def name_match_score(local_name: str, remote_name: str) -> float:
    """名称匹配分数"""
    ln = normalize_for_compare(local_name)
    rn = normalize_for_compare(remote_name)

    # 完全一致
    if ln == rn:
        return 1.0

    # 一个包含另一个
    if ln in rn or rn in ln:
        return 0.9

    # 序列匹配
    return SequenceMatcher(None, ln, rn).ratio()


def artist_match_score(local_artists: list, remote_artist_str: str) -> float:
    """歌手匹配分数"""
    remote_artists = set(split_artists(remote_artist_str))
    local_set = set(local_artists)

    if not local_set or not remote_artists:
        return 0.5

    # 检查交集
    overlap = local_set & remote_artists
    if overlap:
        return 1.0

    # 检查部分匹配（如 "陈楚生" 在 "陈楚生/王栎鑫" 中）
    for la in local_artists:
        for ra in remote_artists:
            if la in ra or ra in la:
                return 0.8

    return 0.0


def match_song(song_name: str, artist_name: str, search_results: list,
               dir_artist: str = '', local_album: str = ''):
    """从搜索结果中匹配

    Args:
        song_name: 歌曲名
        artist_name: 歌手（文件名解析）
        search_results: 搜索结果列表
        dir_artist: 目录名作为歌手提示
        local_album: 本地文件的专辑名（用于辅助匹配）
    """
    if not search_results:
        return None

    local_artists = split_artists(artist_name)
    if not local_artists and dir_artist:
        local_artists = [dir_artist]

    local_album_norm = normalize_for_compare(local_album) if local_album else ''

    best_match = None
    best_score = 0

    for song in search_results:
        remote_name = song.get('name', '')
        remote_artist = song.get('artists', '')
        remote_album = song.get('album', '')

        # 名称分数
        ns = name_match_score(song_name, remote_name)
        if ns < 0.5:
            continue

        # 歌手分数
        as_ = artist_match_score(local_artists, remote_artist)

        # 专辑分数
        album_score = 0
        if local_album_norm and remote_album:
            remote_album_norm = normalize_for_compare(remote_album)
            if local_album_norm == remote_album_norm:
                album_score = 1.0
            elif local_album_norm in remote_album_norm or remote_album_norm in local_album_norm:
                album_score = 0.7
            else:
                album_score = SequenceMatcher(None, local_album_norm, remote_album_norm).ratio()

        # 综合评分
        # 有专辑信息时：名称 0.35 + 歌手 0.35 + 专辑 0.3
        # 无专辑信息时：名称 0.5 + 歌手 0.5
        if local_album_norm:
            score = ns * 0.35 + as_ * 0.35 + album_score * 0.3
        else:
            score = ns * 0.5 + as_ * 0.5

        if score > best_score:
            best_score = score
            best_match = song

    # 阈值
    if best_match and best_score >= 0.45:
        return best_match

    return None


def smart_search(song_name: str, artist_name: str, dir_artist: str = '', local_album: str = ''):
    """智能搜索：尝试多种关键词组合

    Args:
        song_name: 歌曲名
        artist_name: 歌手（文件名解析）
        dir_artist: 目录名作为歌手提示
        local_album: 本地文件的专辑名

    Returns:
        (matched_song, used_keyword) 或 (None, None)
    """
    artists = split_artists(artist_name)
    first_artist = artists[0] if artists else ''
    hint_artist = dir_artist or first_artist

    strategies = [
        (f'{song_name} {hint_artist}', '歌曲名 + 目录歌手'),
    ]

    if len(artists) > 1:
        strategies.append((f'{song_name} {artists[0]}', '歌曲名 + 第一歌手'))
        strategies.append((f'{song_name} {"/".join(artists[:2])}', '歌曲名 + 前两歌手'))

    strategies.append((f'{song_name}', '仅歌曲名'))

    for keyword, desc in strategies:
        try:
            results = netease_client.search(keyword, limit=15)
            time.sleep(0.25)
        except Exception:
            continue

        if not results:
            continue

        matched = match_song(song_name, artist_name, results, dir_artist, local_album)
        if matched:
            return matched, keyword

    return None, None


def write_platform_song_id(filepath: str, ext: str, song_id: str):
    """写入 PLATFORM 和 SONG_ID 字段"""
    if ext == '.flac':
        from mutagen.flac import FLAC
        audio = FLAC(filepath)
        if 'PLATFORM' in audio:
            del audio['PLATFORM']
        if 'SONG_ID' in audio:
            del audio['SONG_ID']
        audio['PLATFORM'] = PLATFORM
        audio['SONG_ID'] = str(song_id)
        audio.save()
    elif ext == '.mp3':
        from mutagen.id3 import ID3, TXXX
        try:
            audio = ID3(filepath)
        except Exception:
            audio = ID3()
        audio.delall('TXXX:PLATFORM')
        audio.delall('TXXX:SONG_ID')
        audio.add(TXXX(encoding=3, desc='PLATFORM', text=[PLATFORM]))
        audio.add(TXXX(encoding=3, desc='SONG_ID', text=[str(song_id)]))
        audio.save(filepath)
    elif ext in ('.m4a', '.mp4'):
        import mutagen.mp4
        from mutagen.mp4 import MP4
        audio = MP4(filepath)
        platform_key = '----:com.apple.iTunes:PLATFORM'
        song_id_key = '----:com.apple.iTunes:SONG_ID'
        if platform_key in audio:
            del audio[platform_key]
        if song_id_key in audio:
            del audio[song_id_key]
        audio[platform_key] = [mutagen.mp4.MP4FreeForm(PLATFORM.encode('utf-8'))]
        audio[song_id_key] = [mutagen.mp4.MP4FreeForm(str(song_id).encode('utf-8'))]
        audio.save()


def scan_directory(scan_dir: str, skip_dirs: set) -> list:
    """扫描缺少 platform/song_id 的文件"""
    audio_files = []
    scan_dir = os.path.abspath(scan_dir)
    skip_abs = {os.path.abspath(os.path.join(scan_dir, d)) for d in skip_dirs}
    for root, dirs, files in os.walk(scan_dir):
        root_abs = os.path.abspath(root)
        if any(root_abs == s or root_abs.startswith(s + os.sep) for s in skip_abs):
            continue
        for f in sorted(files):
            ext = Path(f).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                filepath = os.path.join(root, f)
                meta = read_metadata(filepath)
                if not meta.get('platform') or not meta.get('song_id'):
                    audio_files.append(filepath)
    return audio_files


def main():
    scan_dir = SCAN_DIR
    dry_run = False
    test_mode = False
    test_dir = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--dry-run':
            dry_run = True
        elif args[i] == '--test':
            test_mode = True
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                test_dir = args[i + 1]
                i += 1
        elif not args[i].startswith('--'):
            scan_dir = args[i]
        i += 1

    scan_dir = os.path.abspath(scan_dir)
    if not os.path.isdir(scan_dir):
        print(f'错误: 目录不存在: {scan_dir}')
        sys.exit(1)

    if test_mode and test_dir:
        scan_dir = os.path.join(scan_dir, test_dir)

    print(f'扫描目录: {scan_dir}')
    print(f'跳过目录: {", ".join(SKIP_DIRS)}')
    if dry_run:
        print('模式: 试运行 (不写入)')
    print()

    print('正在扫描缺少 platform/song_id 的文件...')
    audio_files = scan_directory(scan_dir, SKIP_DIRS)
    print(f'找到 {len(audio_files)} 个需要补写的文件')

    if not audio_files:
        print('所有文件元数据完整，无需操作')
        return

    # 按歌手目录分组
    artist_groups = {}
    for fp in audio_files:
        rel = os.path.relpath(fp, scan_dir)
        parts = Path(rel).parts
        artist_dir = parts[0] if len(parts) > 1 else '_root'
        artist_groups.setdefault(artist_dir, []).append(fp)

    stats = {'success': 0, 'failed': 0, 'skipped': 0, 'error': 0}
    failed_files = []

    for artist_dir, files in sorted(artist_groups.items()):
        print(f'\n{"═" * 60}')
        print(f'  歌手目录: {artist_dir} ({len(files)} 个文件)')
        print(f'{"═" * 60}')

        for filepath in files:
            filename = os.path.basename(filepath)
            ext = Path(filepath).suffix.lower()

            parsed = parse_filename(filename)
            if not parsed:
                print(f'  ✗ {filename}')
                print(f'    无法解析文件名')
                stats['skipped'] += 1
                failed_files.append((filepath, '文件名无法解析'))
                continue

            song_name, artist_name = parsed

            # 读取本地元数据中的专辑信息
            try:
                meta = read_metadata(filepath)
                local_album = meta.get('album', '')
            except Exception:
                local_album = ''

            # 智能搜索
            matched, used_keyword = smart_search(song_name, artist_name, artist_dir, local_album)

            if not matched:
                print(f'  ✗ {filename}')
                stats['failed'] += 1
                failed_files.append((filepath, '未找到匹配'))
                continue

            song_id = matched['id']
            matched_name = matched['name']
            matched_artist = matched['artists']

            if dry_run:
                print(f'  ○ {filename}')
                print(f'    -> {matched_name} - {matched_artist} (ID: {song_id})')
                stats['success'] += 1
            else:
                try:
                    write_platform_song_id(filepath, ext, song_id)
                    print(f'  ✓ {filename}')
                    print(f'    -> {matched_name} - {matched_artist} (ID: {song_id})')
                    stats['success'] += 1
                except Exception as e:
                    print(f'  ✗ {filename}')
                    print(f'    写入失败: {e}')
                    stats['error'] += 1
                    failed_files.append((filepath, f'写入失败: {e}'))

    # 汇总
    print(f'\n{"═" * 60}')
    print(f'  完成!')
    print(f'{"═" * 60}')
    print(f'  成功: {stats["success"]}')
    print(f'  失败: {stats["failed"]}')
    print(f'  跳过: {stats["skipped"]}')
    print(f'  错误: {stats["error"]}')

    if failed_files:
        print(f'\n  失败文件:')
        for fp, reason in failed_files:
            print(f'    - {os.path.basename(fp)}: {reason}')


if __name__ == '__main__':
    main()
