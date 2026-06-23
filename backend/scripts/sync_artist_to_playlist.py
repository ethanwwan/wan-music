#!/usr/bin/env python3
"""同步歌手目录与歌单歌曲目录

背景:
- /Volumes/资源库/音乐/歌曲/ 目录下有两类目录:
  - 歌手目录: 如 周杰伦/, 陈奕迅/ (按歌手分目录)
  - 歌单歌曲目录: 歌单原曲/ (所有歌混在一起)

功能:
- 扫描所有歌手目录，建立 {filename: 歌手路径} 索引
- 扫描歌单原曲中的所有文件
- 对于歌单原曲中已经在歌手目录里存在的文件:
  - 删除歌单原曲中的副本
  - 更新 music_root 下的 m3u 文件引用 (从 歌单原曲/xxx -> 歌手/xxx)

用法:
    python3 scripts/sync_artist_to_playlist.py              # DRY RUN
    python3 scripts/sync_artist_to_playlist.py --apply     # 实际执行
"""
import os
import re
import sys
from collections import defaultdict


# 配置
SONGS_DIR = '/Volumes/资源库/音乐/歌曲'        # 歌曲库根目录
MUSIC_ROOT = '/Volumes/资源库/音乐/歌单'        # m3u 文件所在目录
PLAYLIST_DIR_NAME = '歌单原曲'                  # 歌单歌曲目录名
AUDIO_EXTS = ('.flac', '.mp3', '.m4a', '.mp4', '.lrc')
M3U_EXT = '.m3u'


def is_audio_file(filename: str) -> bool:
    return filename.lower().endswith(AUDIO_EXTS)


def identify_dirs(songs_dir: str) -> tuple:
    """识别歌手目录和歌单歌曲目录

    Returns:
        (artist_dirs, playlist_dir)
    """
    if not os.path.isdir(songs_dir):
        return [], None

    artist_dirs = []
    playlist_dir = None
    for name in os.listdir(songs_dir):
        path = os.path.join(songs_dir, name)
        if not os.path.isdir(path):
            continue
        if name.startswith('.'):
            continue
        if name == PLAYLIST_DIR_NAME:
            playlist_dir = path
        else:
            artist_dirs.append(path)

    return sorted(artist_dirs), playlist_dir


def build_artist_index(artist_dirs: list, songs_dir: str) -> dict:
    """建立歌手目录索引: {filename: (relative_path, size, artist_name)}

    Returns:
        dict: {filename: [{'path': rel_path, 'size': size, 'artist': name}, ...]}
              同一首歌可能在多个歌手目录中存在（合唱歌曲）
    """
    index = defaultdict(list)
    for artist_dir in artist_dirs:
        artist_name = os.path.basename(artist_dir)
        for filename in os.listdir(artist_dir):
            if not is_audio_file(filename):
                continue
            filepath = os.path.join(artist_dir, filename)
            if not os.path.isfile(filepath):
                continue
            try:
                size = os.path.getsize(filepath)
            except OSError:
                continue
            rel_path = os.path.relpath(filepath, songs_dir)
            index[filename].append({
                'path': rel_path,
                'size': size,
                'artist': artist_name,
            })
    return index


def collect_playlist_files(playlist_dir: str) -> list:
    """收集歌单目录下的所有文件

    Returns:
        list: [(filepath, filename, size), ...]
    """
    if not os.path.isdir(playlist_dir):
        return []

    files = []
    for filename in os.listdir(playlist_dir):
        if not is_audio_file(filename):
            continue
        filepath = os.path.join(playlist_dir, filename)
        if os.path.isfile(filepath):
            try:
                size = os.path.getsize(filepath)
                files.append((filepath, filename, size))
            except OSError:
                pass
    return files


def resolve_m3u_path(m3u_path: str, relative_path: str) -> str:
    """解析 m3u 中的相对路径为绝对路径"""
    m3u_dir = os.path.dirname(m3u_path)
    parts = relative_path.split('/')
    stack = m3u_dir.split('/')
    for part in parts:
        if part == '..':
            if len(stack) > 1:
                stack.pop()
        elif part == '.' or part == '':
            continue
        else:
            stack.append(part)
    return '/'.join(stack)


def update_m3u_file(m3u_path: str, replacements: dict, apply: bool) -> dict:
    """更新单个 m3u 文件中的路径引用

    Args:
        m3u_path: m3u 文件绝对路径
        replacements: {old_playlist_path: new_artist_path}
        apply: 是否实际写入

    Returns:
        dict: {updated: int, removed: int, removed_paths: [str]}
    """
    result = {'updated': 0, 'removed': 0, 'removed_paths': []}

    with open(m3u_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = []
    skip_next = False

    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\r')

        if skip_next:
            skip_next = False
            i += 1
            continue

        if line.startswith('#EXTINF'):
            # #EXTINF 行后面跟着路径行
            if i + 1 < len(lines):
                path_line = lines[i + 1].rstrip('\r')
                # 处理路径
                new_path_line = path_line
                is_playlist_ref = False
                for old, new in replacements.items():
                    if old in path_line:
                        is_playlist_ref = True
                        new_path_line = path_line.replace(old, new)
                        break

                if is_playlist_ref:
                    # 检查新路径是否有效
                    abs_path = resolve_m3u_path(m3u_path, new_path_line)
                    if os.path.exists(abs_path):
                        # 有效，保留
                        new_lines.append(line)
                        new_lines.append(new_path_line)
                        result['updated'] += 1
                    else:
                        # 新路径无效，删除整条记录
                        result['removed'] += 1
                        result['removed_paths'].append(new_path_line)
                    i += 2
                    continue
                else:
                    # 不是目标歌单原曲的引用，保留
                    new_lines.append(line)
                    new_lines.append(path_line)
                    i += 2
                    continue
            else:
                # 没有路径行
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1

    # 写回文件
    if apply and (result['updated'] > 0 or result['removed'] > 0):
        with open(m3u_path, 'w', encoding='utf-8-sig') as f:
            f.write('\n'.join(new_lines))

    return result


def main():
    apply = '--apply' in sys.argv

    print('=' * 60)
    print(f'{"APPLY 模式" if apply else "DRY RUN 模式"} - {"会删除文件和更新 m3u" if apply else "不修改文件"}')
    print('=' * 60)
    print(f'歌曲库目录: {SONGS_DIR}')
    print(f'm3u 目录: {MUSIC_ROOT}')
    print(f'歌单歌曲目录: {PLAYLIST_DIR_NAME}')
    print()

    # 1. 识别目录
    artist_dirs, playlist_dir = identify_dirs(SONGS_DIR)
    if not artist_dirs:
        print('❌ 未找到歌手目录')
        return
    if not playlist_dir:
        print(f'❌ 未找到歌单歌曲目录: {PLAYLIST_DIR_NAME}')
        return

    print(f'找到 {len(artist_dirs)} 个歌手目录')
    print(f'歌单歌曲目录: {os.path.basename(playlist_dir)}')
    print()

    # 2. 构建歌手目录索引
    print('正在构建歌手目录索引...')
    artist_index = build_artist_index(artist_dirs, SONGS_DIR)
    print(f'歌手目录共 {sum(len(v) for v in artist_index.values())} 个文件，唯一文件名 {len(artist_index)}')
    print()

    # 3. 收集歌单原曲中的文件
    playlist_files = collect_playlist_files(playlist_dir)
    print(f'歌单歌曲目录共 {len(playlist_files)} 个文件')
    print()

    # 4. 找出重复文件
    to_delete = []       # [(playlist_filepath, filename, artist_match), ...]
    not_in_artist = []   # 歌手目录中没有的文件
    for filepath, filename, size in playlist_files:
        if filename in artist_index:
            # 歌手目录中有同名文件
            matches = artist_index[filename]
            # 优先选最大文件的
            best = max(matches, key=lambda x: x['size'])
            to_delete.append((filepath, filename, best))
        else:
            not_in_artist.append((filepath, filename, size))

    # 5. 显示计划
    print('=' * 60)
    print('处理计划:')
    print('=' * 60)

    print(f'\n🗑️  将删除 ({len(to_delete)} 个):')
    if to_delete:
        for fp, fn, match in to_delete[:5]:
            print(f'  - {fn}')
            print(f'    -> 由 {match["artist"]} 提供 ({match["path"]})')
        if len(to_delete) > 5:
            print(f'  ... 还有 {len(to_delete) - 5} 个')

    print(f'\n✓ 歌单原曲独有 ({len(not_in_artist)} 个):')
    for fp, fn, size in not_in_artist[:5]:
        print(f'  - {fn}')
    if len(not_in_artist) > 5:
        print(f'  ... 还有 {len(not_in_artist) - 5} 个')

    # 6. 准备 m3u 更新的替换映射
    # m3u 中引用格式: ../歌曲/歌单原曲/xxx.flac
    # 替换为: ../歌曲/歌手/xxx.flac
    replacements = {}
    for fp, fn, match in to_delete:
        # 旧路径（m3u 中的格式）
        old_path = f'../歌曲/{PLAYLIST_DIR_NAME}/{fn}'
        # 新路径
        new_path = f'../歌曲/{match["artist"]}/{fn}'
        replacements[old_path] = new_path

    print()
    print('=' * 60)
    print('m3u 更新计划:')
    print('=' * 60)
    print(f'将更新 {len(replacements)} 个路径引用')
    for old, new in list(replacements.items())[:3]:
        print(f'  {old}')
        print(f'  -> {new}')
    if len(replacements) > 3:
        print(f'  ... 还有 {len(replacements) - 3} 个')

    # 7. 实际执行
    if not apply:
        print()
        print('[DRY RUN] 跳过实际修改')
        print('使用 --apply 参数实际执行')
        return

    print()
    print('=' * 60)
    print('开始执行...')
    print('=' * 60)

    # 7.1 删除歌单原曲中的重复文件
    deleted = 0
    delete_failed = 0
    for fp, fn, match in to_delete:
        try:
            os.remove(fp)
            print(f'  🗑️  已删除: {fn}')
            deleted += 1
        except Exception as e:
            print(f'  ✗ 删除失败: {fn} - {e}')
            delete_failed += 1

    print()
    print(f'文件删除: 成功 {deleted} | 失败 {delete_failed}')

    # 7.2 更新所有 m3u 文件
    if os.path.isdir(MUSIC_ROOT):
        m3u_files = [os.path.join(MUSIC_ROOT, f) for f in os.listdir(MUSIC_ROOT)
                     if f.lower().endswith(M3U_EXT) and os.path.isfile(os.path.join(MUSIC_ROOT, f))]

        print()
        print(f'找到 {len(m3u_files)} 个 m3u 文件，开始更新...')
        print()

        total_updated = 0
        total_removed = 0
        for m3u_path in m3u_files:
            m3u_name = os.path.basename(m3u_path)
            result = update_m3u_file(m3u_path, replacements, apply=True)
            print(f'  📄 {m3u_name}: 更新 {result["updated"]} | 删除 {result["removed"]}')
            total_updated += result['updated']
            total_removed += result['removed']

        print()
        print(f'm3u 更新: 路径更新 {total_updated} | 条目删除 {total_removed}')

    print()
    print('=' * 60)
    print('✓ 完成')


if __name__ == '__main__':
    main()
