#!/usr/bin/env python3
"""为本地歌单目录生成 m3u 格式的歌单文件，支持去重和路径优先级"""

import os
import re
import sys
import shutil
from pathlib import Path


# 音乐文件扩展名
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.ogg', '.wav', '.wma', '.aac', '.opus')
LYRIC_EXTENSIONS = ('.lrc',)


def is_audio_file(filename: str) -> bool:
    """判断是否是音频文件"""
    return filename.lower().endswith(AUDIO_EXTENSIONS)


def is_lyric_file(filename: str) -> bool:
    """判断是否是歌词文件"""
    return filename.lower().endswith(LYRIC_EXTENSIONS)


def parse_song_info(filename: str) -> dict:
    """从文件名解析歌曲名和歌手名"""
    name = os.path.splitext(filename)[0]
    match = re.match(r'^(.+?)\s*[-\u2013\u2014]\s*(.+)$', name)
    if match:
        return {'name': match.group(1).strip(), 'artist': match.group(2).strip()}
    return {'name': name.strip(), 'artist': ''}


def normalize_for_match(s: str) -> str:
    """标准化字符串用于匹配（去除空格、特殊字符、转小写）"""
    s = s.lower()
    # 去除括号内容（如 Live、Remix 版本信息等）
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'\s*（[^）]*）', '', s)
    # 标准化分隔符
    s = re.sub(r'[\s\-_]+', '', s)
    return s


def build_song_index(songs_dir: str) -> dict:
    """构建歌曲索引：{归一化键: 文件路径}

    Args:
        songs_dir: 歌曲根目录（B目录），按歌手分子目录
    Returns:
        {归一化键: 相对路径(相对于songs_dir)}
    """
    index = {}
    for root, dirs, files in os.walk(songs_dir):
        for f in files:
            if not is_audio_file(f):
                continue
            info = parse_song_info(f)
            if not info['artist']:
                continue

            # 多个归一化键
            key1 = normalize_for_match(f"{info['name']}_{info['artist']}")
            key2 = normalize_for_match(f"{info['artist']}_{info['name']}")

            rel_path = os.path.relpath(os.path.join(root, f), songs_dir)

            for key in (key1, key2):
                if key and key not in index:
                    index[key] = rel_path
    return index


def find_lyric_file(song_path: str, base_dir: str) -> str:
    """查找同名的歌词文件"""
    base, _ = os.path.splitext(song_path)
    lyric_path = base + '.lrc'
    full_path = os.path.join(base_dir, lyric_path)
    if os.path.exists(full_path):
        return lyric_path
    return None


def generate_m3u(playlist_dir: str, songs_dir: str, output_dir: str = None) -> dict:
    """为指定歌单目录生成 m3u 文件

    Args:
        playlist_dir: 歌单目录路径 (A目录)
        songs_dir: 歌曲根目录 (B目录)
        output_dir: 输出目录路径，默认为歌单目录（与歌单子目录同级）
    """
    playlist_dir = os.path.abspath(playlist_dir)
    songs_dir = os.path.abspath(songs_dir)
    playlist_name = os.path.basename(playlist_dir)

    if not os.path.isdir(playlist_dir):
        return {'success': False, 'message': f'歌单目录不存在: {playlist_dir}'}

    if not os.path.isdir(songs_dir):
        return {'success': False, 'message': f'歌曲目录不存在: {songs_dir}'}

    if output_dir is None:
        output_dir = os.path.dirname(playlist_dir)

    output_file = os.path.join(output_dir, f'{playlist_name}.m3u')

    # 构建歌曲库索引
    print(f'  正在构建歌曲库索引...')
    songs_index = build_song_index(songs_dir)
    print(f'  歌曲库共 {len(songs_index)} 首歌曲')

    # 收集歌单中所有文件
    audio_files = []
    lyric_files = []
    for filename in os.listdir(playlist_dir):
        filepath = os.path.join(playlist_dir, filename)
        if not os.path.isfile(filepath):
            continue
        if is_audio_file(filename):
            audio_files.append(filename)
        elif is_lyric_file(filename):
            lyric_files.append(filename)

    if not audio_files:
        return {'success': False, 'message': f'歌单中未找到音频文件: {playlist_name}'}

    # 检查并删除孤立的歌词文件（没有对应音频文件）
    orphan_lyrics = []
    audio_basenames = {os.path.splitext(f)[0] for f in audio_files}
    for lyric_file in lyric_files:
        lyric_basename = os.path.splitext(lyric_file)[0]
        if lyric_basename not in audio_basenames:
            orphan_lyric_path = os.path.join(playlist_dir, lyric_file)
            try:
                os.remove(orphan_lyric_path)
                orphan_lyrics.append(lyric_file)
            except Exception as e:
                print(f'  ⚠️ 删除孤立歌词失败: {lyric_file} - {e}')

    lyrics_count = len(lyric_files) - len(orphan_lyrics)

    if orphan_lyrics:
        print(f'  🗑️ 已删除 {len(orphan_lyrics)} 个孤立歌词文件')

    # 按歌曲名排序
    audio_files.sort(key=lambda f: parse_song_info(f)['name'])

    # 处理每首歌曲：判断是否重复，生成引用路径，决定是否删除
    m3u_entries = []  # [(ext_info, path)]
    removed_files = []  # 已删除的重复文件
    kept_files = []  # 保留的文件
    used_in_songs_lib = 0
    used_in_playlist = 0

    for filename in audio_files:
        info = parse_song_info(filename)
        if not info['artist']:
            # 无法解析歌手名，保留在歌单目录，使用歌单相对路径
            m3u_entries.append((
                f'#EXTINF:-1,{filename}',
                f'{playlist_name}/{filename}'
            ))
            kept_files.append(filename)
            used_in_playlist += 1
            continue

        # 在歌曲库中查找匹配
        key1 = normalize_for_match(f"{info['name']}_{info['artist']}")
        key2 = normalize_for_match(f"{info['artist']}_{info['name']}")

        matched = None
        for key in (key1, key2):
            if key in songs_index:
                matched = songs_index[key]
                break

        if matched:
            # 歌曲库中有，使用歌曲库引用
            m3u_entries.append((
                f'#EXTINF:-1,{info["artist"]} - {info["name"]}',
                matched  # 相对于 songs_dir
            ))
            # 删除歌单目录中的重复文件
            src = os.path.join(playlist_dir, filename)
            try:
                os.remove(src)
                removed_files.append(filename)
                # 同时删除对应的歌词文件
                base, _ = os.path.splitext(filename)
                lyric_src = os.path.join(playlist_dir, base + '.lrc')
                if os.path.exists(lyric_src):
                    os.remove(lyric_src)
                    removed_files.append(base + '.lrc')
            except Exception as e:
                print(f'  ⚠️ 删除失败: {filename} - {e}')
            used_in_songs_lib += 1
        else:
            # 歌曲库中没有，保留在歌单目录
            m3u_entries.append((
                f'#EXTINF:-1,{info["artist"]} - {info["name"]}',
                f'{playlist_name}/{filename}'
            ))
            kept_files.append(filename)
            used_in_playlist += 1

    # 生成 m3u 文件
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write('#EXTM3U\n')
        for ext_info, path in m3u_entries:
            f.write(f'{ext_info}\n')
            f.write(f'{path}\n')

    return {
        'success': True,
        'message': f'成功生成: {os.path.basename(output_file)}',
        'playlist': playlist_name,
        'total_in_playlist': len(audio_files),
        'from_songs_lib': used_in_songs_lib,
        'kept_in_playlist': used_in_playlist,
        'lyrics_count': lyrics_count,
        'removed_files': removed_files,
        'orphan_lyrics': len(orphan_lyrics),
        'output_file': output_file
    }


def main():
    music_root = '/Volumes/资源库/音乐/歌单'    # A 目录
    songs_dir = '/Volumes/资源库/音乐/歌曲'      # B 目录
    output_root = music_root  # m3u 文件输出到歌单目录下

    if not os.path.isdir(music_root):
        print(f'错误: 歌单目录不存在 - {music_root}')
        sys.exit(1)

    if not os.path.isdir(songs_dir):
        print(f'错误: 歌曲目录不存在 - {songs_dir}')
        sys.exit(1)

    print(f'歌单根目录 (A): {music_root}')
    print(f'歌曲库目录 (B): {songs_dir}')
    print(f'输出目录: {output_root}')
    print('=' * 60)

    # 查找所有歌单子目录
    playlists = []
    for item in sorted(os.listdir(music_root)):
        item_path = os.path.join(music_root, item)
        # 跳过已存在的 m3u 文件和非目录项
        if os.path.isdir(item_path) and not item.endswith('.m3u'):
            playlists.append(item_path)

    if not playlists:
        print('未找到任何歌单子目录')
        sys.exit(1)

    print(f'找到 {len(playlists)} 个歌单\n')

    # 统计
    total_songs = 0
    total_from_lib = 0
    total_kept = 0
    total_removed = 0
    total_orphan_lyrics = 0
    success_count = 0
    failed_count = 0

    for playlist_path in playlists:
        playlist_name = os.path.basename(playlist_path)
        result = generate_m3u(playlist_path, songs_dir, output_root)

        if result['success']:
            success_count += 1
            total_songs += result['total_in_playlist']
            total_from_lib += result['from_songs_lib']
            total_kept += result['kept_in_playlist']
            total_removed += len(result['removed_files'])
            total_orphan_lyrics += result.get('orphan_lyrics', 0)

            print(f'✓ {playlist_name}')
            print(f'    歌曲总数: {result["total_in_playlist"]}')
            print(f'    来自歌曲库: {result["from_songs_lib"]}')
            print(f'    保留在歌单: {result["kept_in_playlist"]}')
            print(f'    删除重复文件: {len(result["removed_files"])}')
            if result.get('orphan_lyrics', 0) > 0:
                print(f'    删除孤立歌词: {result["orphan_lyrics"]}')
            print(f'    输出: {os.path.basename(result["output_file"])}')
        else:
            failed_count += 1
            print(f'✗ {playlist_name}: {result["message"]}')
        print()

    print('=' * 60)
    print(f'完成! 成功: {success_count} | 失败: {failed_count}')
    print(f'歌曲总数: {total_songs} | 来自歌曲库: {total_from_lib} | 保留在歌单: {total_kept}')
    print(f'已删除重复文件: {total_removed}')
    print(f'已删除孤立歌词: {total_orphan_lyrics}')


if __name__ == '__main__':
    main()
