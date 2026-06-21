#!/usr/bin/env python3
"""更新 m3u 文件中的歌曲引用路径

将 m3u 中保留在歌单目录的歌曲引用，从:
    歌单名/歌曲文件
更新为:
    1歌单原曲/歌单名/歌曲文件
"""

import os
import re
import sys


def update_m3u_references(m3u_path: str, old_prefix: str, new_prefix: str) -> dict:
    """更新 m3u 文件中以 old_prefix 开头的引用路径

    Args:
        m3u_path: m3u 文件路径
        old_prefix: 旧路径前缀（如 "10w热评的中文歌"）
        new_prefix: 新路径前缀（如 "1歌单原曲/10w热评的中文歌"）
    """
    if not os.path.exists(m3u_path):
        return {'success': False, 'message': f'文件不存在: {m3u_path}'}

    with open(m3u_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    lines = content.split('\n')
    updated_count = 0
    new_lines = []

    for line in lines:
        # 只处理路径行（不是以 # 开头的 EXTINF 行）
        if not line.startswith('#') and line.strip():
            # 检查是否以 old_prefix 开头
            if line.startswith(old_prefix + '/') or line == old_prefix:
                new_line = new_prefix + line[len(old_prefix):]
                new_lines.append(new_line)
                updated_count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 写回文件
    with open(m3u_path, 'w', encoding='utf-8-sig') as f:
        f.write('\n'.join(new_lines))

    return {
        'success': True,
        'file': m3u_path,
        'updated_count': updated_count
    }


def main():
    m3u_dir = '/Volumes/资源库/音乐/歌单'      # m3u 文件所在目录
    new_prefix_root = '1歌单原曲'                # 新的统一前缀

    if not os.path.isdir(m3u_dir):
        print(f'错误: 目录不存在 - {m3u_dir}')
        sys.exit(1)

    print(f'm3u 目录: {m3u_dir}')
    print(f'新前缀: {new_prefix_root}/<歌单名>/')
    print('=' * 60)

    # 查找所有 m3u 文件
    m3u_files = [f for f in os.listdir(m3u_dir) if f.lower().endswith('.m3u')]

    if not m3u_files:
        print('未找到 m3u 文件')
        sys.exit(0)

    print(f'找到 {len(m3u_files)} 个 m3u 文件\n')

    total_updated = 0

    for m3u_file in sorted(m3u_files):
        m3u_path = os.path.join(m3u_dir, m3u_file)
        # m3u 文件名 = 歌单名
        playlist_name = os.path.splitext(m3u_file)[0]
        old_prefix = playlist_name
        new_prefix = f'{new_prefix_root}/{playlist_name}'

        result = update_m3u_references(m3u_path, old_prefix, new_prefix)

        if result['success']:
            total_updated += result['updated_count']
            print(f'✓ {m3u_file}')
            print(f'    {old_prefix}/ → {new_prefix}/')
            print(f'    更新数量: {result["updated_count"]}')
        else:
            print(f'✗ {m3u_file}: {result["message"]}')
        print()

    print('=' * 60)
    print(f'完成! 总更新数量: {total_updated}')


if __name__ == '__main__':
    main()
