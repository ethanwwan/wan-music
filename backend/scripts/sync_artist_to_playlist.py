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


def strip_brackets(s: str) -> str:
    """去除文件名中的括号标记（如 (Live), [Remix], （现场版） 等）

    去除形式: (...) [...] （...） 【...】
    同时将括号前后的多余空格合并为一个空格
    """
    result = re.sub(r'\s*[\(\[（【][^\)\]）】]*[\)\]）】]', '', s)
    # 把多个连续空格合并为一个
    result = re.sub(r'\s+', ' ', result)
    return result.strip()


def _to_halfwidth(s: str) -> str:
    """全角字符转半角（包括标点、英文字母、数字、特殊符号）"""
    # 特殊符号映射
    special = {
        '，': ',',  # 全角逗号
        '。': '.',  # 全角句号
        '！': '!',  # 全角感叹号
        '？': '?',  # 全角问号
        '：': ':',  # 全角冒号
        '；': ';',  # 全角分号
        '（': '(',  # 全角左括号
        '）': ')',  # 全角右括号
        '【': '[',  # 全角左方括号
        '】': ']',  # 全角右方括号
        '《': '<',  # 全角左书名号
        '》': '>',  # 全角右书名号
        '℃': '°C',  # 摄氏度（统一为 °C 形式）
        '℉': '°F',  # 华氏度
        '、': ',',  # 顿号
        '。': '.',
    }
    result = []
    for ch in s:
        if ch in special:
            result.append(special[ch])
            continue
        code = ord(ch)
        # 全角空格 → 半角空格
        if code == 0x3000:
            result.append(' ')
        # 全角 ASCII 区间 (0xFF01-0xFF5E) → 半角 (0x21-0x7E)
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return ''.join(result)


def normalize_filename(s: str) -> str:
    """激进版：去除所有空白和括号（用于最后的兜底匹配）

    处理步骤:
        1. 全角转半角
        2. 标点符号统一（，,。.；;：:、→ ,, _,-, -）
        3. 去除括号内容
        4. 去除所有空白
        5. 转小写
    """
    s = _to_halfwidth(s)
    # 把各种分隔符统一为下划线 (因为歌手目录里都是用 _ 分隔歌名)
    s = re.sub(r'[，,。.;；:：、/_-]+', '_', s)
    no_brackets = re.sub(r'[\(\[（【][^\)\]）】]*[\)\]）】]', '', s)
    no_spaces = re.sub(r'\s+', '', no_brackets)
    return no_spaces.lower()


def extract_song_name(filename: str) -> str:
    """从文件名提取纯歌名（去除歌手部分和扩展名）

    例: '七里香 - 周杰伦.flac' -> '七里香'
        '100 Ways - 王嘉尔.flac' -> '100 Ways'
        '凤毛麟角 - 薛之谦.flac' -> '凤毛麟角'
    """
    name = os.path.splitext(filename)[0]
    match = re.match(r'^(.+?)\s*[-\u2013\u2014]\s*.+$', name)
    if match:
        return match.group(1).strip()
    return name.strip()


def normalize_song_name(song_name: str) -> str:
    """归一化歌名（去括号 + 去空格 + 小写）"""
    no_brackets = re.sub(r'[\(\[（【][^\)\]）】]*[\)\]）】]', '', song_name)
    no_spaces = re.sub(r'\s+', '', no_brackets)
    return no_spaces.lower()


def build_artist_index(artist_dirs: list, songs_dir: str) -> dict:
    """建立歌手目录索引: {filename: [...]}

    返回多重索引:
        - index[filename]: 按原始文件名匹配
        - index[strip_brackets(filename)]: 去除括号后匹配
        - index[normalize_filename(filename)]: 激进归一化（去括号+去空格+小写）
        - index[song_name]: 纯歌名（去除歌手部分）匹配
        - index[normalize_song_name(song_name)]: 归一化纯歌名匹配
        这样即使歌手顺序/分隔符不同，也能匹配：
            '你最珍贵 - 高慧君,张学友.flac' 匹配到
            '你最珍贵 - 张学友_高慧君.flac'

    Returns:
        dict: {key: [{'path', 'size', 'artist', 'orig_filename', 'song_name'}, ...]}
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
            song_name = extract_song_name(filename)
            entry = {
                'path': rel_path,
                'size': size,
                'artist': artist_name,
                'orig_filename': filename,
                'song_name': song_name,
            }
            # 1. 原文件名索引
            index[filename].append(entry)
            # 2. 去除括号后索引
            stripped = strip_brackets(filename)
            if stripped:
                index[stripped].append(entry)
            # 3. 激进归一化
            normalized = normalize_filename(filename)
            if normalized:
                index[normalized].append(entry)
            # 4. 纯歌名索引
            if song_name:
                index[song_name].append(entry)
                # 5. 归一化歌名索引
                norm_song = normalize_song_name(song_name)
                if norm_song:
                    index[norm_song].append(entry)
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


def parse_song_artist(filename: str) -> str:
    """从文件名解析歌手（文件名格式: 歌名 - 歌手.ext）

    Returns:
        歌手名（多歌手用 / 分隔），无歌手返回 ''
    """
    name = os.path.splitext(filename)[0]
    match = re.match(r'^(.+?)\s*[-\u2013\u2014]\s*(.+)$', name)
    if match:
        artist = match.group(2).strip()
        return artist
    return ''


def extract_artists(artist_str: str) -> list:
    """拆分多歌手字段为列表

    支持分隔符: / , & ; _ \  、 ， ； |
    """
    if not artist_str:
        return []
    # 先按 顿号 分（顿号天然就是多歌手）
    parts = re.split(r'[/,&;_\u3001\uff0c\uff1b\\|]+', artist_str)
    return [p.strip() for p in parts if p.strip()]


def count_playlist_artists(playlist_files: list, existing_artists: set) -> list:
    """统计歌单原曲中的歌手排行

    Args:
        playlist_files: [(filepath, filename, size), ...]
        existing_artists: 已存在的歌手目录名集合

    Returns:
        list: [(artist, count, exists_in_songs, songs), ...] 按歌曲数倒序
              songs: list of filename
    """
    artist_songs = defaultdict(list)
    for filepath, filename, size in playlist_files:
        artist_str = parse_song_artist(filename)
        if not artist_str:
            artist_songs['(未知)'].append(filename)
            continue
        artists = extract_artists(artist_str)
        if not artists:
            artist_songs['(未知)'].append(filename)
        else:
            for a in artists:
                artist_songs[a].append(filename)

    # 转 list，添加是否存在的标记
    result = []
    for artist, songs in artist_songs.items():
        result.append((artist, len(songs), artist in existing_artists, songs))

    # 按歌曲数倒序
    result.sort(key=lambda x: -x[1])
    return result


def print_artist_ranking(playlist_files: list, artist_dirs: list, playlist_dir_name: str):
    """打印歌单原曲的歌手排行统计（精简版，详细见报告文件）"""
    existing_artists = {os.path.basename(d) for d in artist_dirs}
    ranking = count_playlist_artists(playlist_files, existing_artists)

    if not ranking:
        return

    print('=' * 60)
    print('歌单原曲的歌手统计（功能 2）')
    print('=' * 60)
    print(f'歌手总数: {len(ranking)}')
    print()

    # 分两栏：已存在 / 不存在
    exists_list = [item for item in ranking if item[2]]
    missing_list = [item for item in ranking if not item[2]]

    def display_width(s: str) -> int:
        """计算字符串的终端显示宽度（中文=2，英文=1）"""
        w = 0
        for ch in s:
            if ord(ch) > 127:
                w += 2
            else:
                w += 1
        return w

    def pad_right(s: str, width: int) -> str:
        """右填充字符串到指定显示宽度"""
        return s + ' ' * max(0, width - display_width(s))

    print(f'✓ 已在 SONGS_DIR 中存在: {len(exists_list)} 个歌手')
    for i, (a, c, _, _) in enumerate(exists_list, 1):
        bar = '█' * min(c, 50)
        print(f'  {i:3d}. {pad_right(a, 24)}{c:>4} 首  {bar}')

    # 详细列出已存在歌手的歌曲
    if exists_list:
        print()
        print('  ┌─ 已存在歌手的歌曲详情 ─────────────────')
        for i, (a, c, _, songs) in enumerate(exists_list, 1):
            print(f'  │ [{i:3d}] {a} ({c} 首)')
            for song in sorted(songs):
                print(f'  │     - {song}')
        print('  └─────────────────────────────────────────')

    print()
    print(f'⚠️  在 SONGS_DIR 中不存在: {len(missing_list)} 个歌手 (前 50 个)')
    for i, (a, c, _, _) in enumerate(missing_list[:50], 1):
        bar = '█' * min(c, 50)
        print(f'  {i:3d}. {pad_right(a, 24)}{c:>4} 首  {bar}')
    if len(missing_list) > 50:
        print(f'  ... 还有 {len(missing_list) - 50} 个')

    # 总计
    total_songs = sum(c for _, c, _, _ in ranking)
    exists_songs = sum(c for _, c, e, _ in ranking if e)
    missing_songs = sum(c for _, c, e, _ in ranking if not e)
    print()
    print(f'歌曲数总计: {total_songs} 首')
    if total_songs > 0:
        print(f'  已在歌曲库的: {exists_songs} 首 ({exists_songs*100/total_songs:.1f}%)')
        print(f'  未在歌曲库的: {missing_songs} 首 ({missing_songs*100/total_songs:.1f}%)')
    print()
    print('  💡 详细歌曲列表请查看歌手排行报告文件')


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
        dict: {updated: int, removed: int, removed_paths: [str], invalid: int}
    """
    result = {'updated': 0, 'removed': 0, 'invalid': 0, 'removed_paths': [], 'invalid_paths': []}

    with open(m3u_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\r')

        if line.startswith('#EXTINF'):
            # #EXTINF 行后面跟着路径行
            if i + 1 < len(lines):
                path_line = lines[i + 1].rstrip('\r')

                # 1) 先做 replacements 替换（如果有匹配）
                new_path_line = path_line
                is_playlist_ref = False
                for old, new in replacements.items():
                    if old in path_line:
                        is_playlist_ref = True
                        new_path_line = path_line.replace(old, new)
                        break

                # 2) 验证文件是否存在（无论是否做替换都验证）
                abs_path = resolve_m3u_path(m3u_path, new_path_line)
                if os.path.exists(abs_path):
                    # 文件存在，保留
                    new_lines.append(line)
                    new_lines.append(new_path_line)
                    if is_playlist_ref:
                        result['updated'] += 1
                else:
                    # 文件不存在，删除整条记录
                    result['invalid'] += 1
                    result['invalid_paths'].append(new_path_line)
                    if is_playlist_ref:
                        result['removed'] += 1
                        result['removed_paths'].append(new_path_line)
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
    if apply and (result['updated'] > 0 or result['invalid'] > 0):
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

    # 3.5 功能2: 歌单原曲歌手统计
    print_artist_ranking(playlist_files, artist_dirs, PLAYLIST_DIR_NAME)
    print()

    # 4. 找出重复文件（5 级匹配: 原名→去括号→归一化→纯歌名→归一化歌名）
    to_delete = []       # [(playlist_filepath, filename, artist_match, match_level), ...]
    not_in_artist = []   # 歌手目录中没有的文件
    for filepath, filename, size in playlist_files:
        # 5 级匹配
        song_name = extract_song_name(filename)
        local_artist_str = parse_song_artist(filename)
        local_artists = set(extract_artists(local_artist_str))
        lookup_keys = [
            ('filename', filename),
            ('strip_brackets', strip_brackets(filename)),
            ('normalize', normalize_filename(filename)),
            ('song_name', strip_brackets(song_name) if song_name else ''),
            ('song_norm', normalize_song_name(song_name) if song_name else ''),
        ]
        matches = None
        match_level = None
        for level, key in lookup_keys:
            if key and key in artist_index:
                # 4-5 级（歌名匹配）需要验证歌手是否重叠，避免误删翻唱版本
                if level in ('song_name', 'song_norm'):
                    candidates = artist_index[key]
                    # 只要有一个共同歌手就算同一首歌
                    overlapped = []
                    for c in candidates:
                        c_artist = c.get('artist', '')
                        if not c_artist:
                            continue
                        # 歌手目录中的歌的"歌手"= 目录名，需要和歌单原曲的 singer list 匹配
                        if c_artist in local_artists:
                            overlapped.append(c)
                    if not overlapped:
                        continue  # 没有共同歌手，跳过这个 level
                    matches = overlapped
                    match_level = level
                    break
                else:
                    matches = artist_index[key]
                    match_level = level
                    break
        if matches:
            # 优先选最大文件的
            best = max(matches, key=lambda x: x['size'])
            to_delete.append((filepath, filename, best, match_level))
        else:
            not_in_artist.append((filepath, filename, size))

    # 5. 显示计划
    print('=' * 60)
    print('处理计划:')
    print('=' * 60)

    print(f'\n🗑️  将删除 ({len(to_delete)} 个):')
    if to_delete:
        for fp, fn, match, level in to_delete:
            print(f'  - {fn} (匹配: {level}) → {match["artist"]}')

    print(f'\n✓ 歌单原曲独有 ({len(not_in_artist)} 个, 详情见报告文件)')

    # 6. 准备 m3u 更新的替换映射
    # m3u 中引用格式: ../歌曲/歌单原曲/xxx.flac
    # 替换为: ../歌曲/歌手/xxx.flac
    replacements = {}
    for fp, fn, match, level in to_delete:
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
    for fp, fn, match, level in to_delete:
        try:
            os.remove(fp)
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
        total_invalid = 0
        for m3u_path in m3u_files:
            m3u_name = os.path.basename(m3u_path)
            result = update_m3u_file(m3u_path, replacements, apply=True)
            print(f'  📄 {m3u_name}: 更新 {result["updated"]} | 删除(replacements) {result["removed"]} | 删除(无效引用) {result["invalid"] - result["removed"]}')
            total_updated += result['updated']
            total_removed += result['removed']
            total_invalid += result['invalid']

        print()
        print(f'm3u 更新: 路径更新 {total_updated} | 删除(replacements) {total_removed} | 删除(无效引用) {total_invalid - total_removed}')

    print()
    print('=' * 60)
    print('✓ 完成')


if __name__ == '__main__':
    main()
