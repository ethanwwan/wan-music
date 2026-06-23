#!/usr/bin/env python3
"""专门处理周杰伦目录的脚本

使用波点音乐 API 搜索匹配周杰伦的所有歌曲，
并重新写入完整的元数据（标题、艺术家、专辑、歌词、封面、PLATFORM、SONG_ID）。

用法：
    python3 scripts/process_zhou_jielun.py              # DRY RUN 联网搜索
    python3 scripts/process_zhou_jielun.py --check     # 仅检测本地元数据完整性（不联网）
    python3 scripts/process_zhou_jielun.py --apply     # 实际写入元数据
"""
import os
import sys
import re
import time

sys.path.insert(0, '/Users/Awan/Public/Repository/wan-music/backend')

from clients.bodian_client import BodianClient
from utils.filename import normalize_artist_name, split_artists
from utils.metadata import read_metadata, write_metadata


ZHOU_JIELUN_DIR = '/Volumes/资源库/音乐/歌曲/周杰伦'
PLATFORM = 'bodian'  # 波点音乐
REPORT_PATH = os.path.join(os.path.dirname(__file__), 'zhou_jielun_report.txt')


# 元数据必需字段（视为"完整"）
# 文本字段: name, artist, platform, song_id
# 字节字段: cover (图片)
# 文本字段: lyric (歌词)
REQUIRED_TEXT_FIELDS = ['name', 'artist', 'platform', 'song_id']
REQUIRED_BLOB_FIELDS = ['cover']  # 封面（字节）必需
REQUIRED_LYRIC_FIELDS = ['lyric']  # 歌词（文本）必需


def parse_song_info(filename: str) -> dict:
    """从文件名解析歌曲名和歌手名"""
    name = os.path.splitext(filename)[0]
    match = re.match(r'^(.+?)\s*[-\u2013\u2014]\s*(.+)$', name)
    if match:
        artist = normalize_artist_name(match.group(2).strip())
        return {'name': match.group(1).strip(), 'artist': artist}
    return {'name': name.strip(), 'artist': '周杰伦'}


def check_metadata_completeness(metadata: dict) -> dict:
    """检查元数据是否完整

    检查以下字段:
    - 文本字段 (name, artist, platform, song_id): 非空
    - 字节字段 (cover): bytes 长度 > 0
    - 歌词字段 (lyric): 字符串长度 > 0

    Returns:
        dict: {
            'is_complete': bool,
            'missing_fields': list,
            'warnings': list,
        }
    """
    missing = []
    warnings = []

    # 检查文本字段
    for field in REQUIRED_TEXT_FIELDS:
        value = metadata.get(field, '')
        if not value:
            missing.append(field)

    # 检查封面（bytes）
    cover = metadata.get('cover', b'')
    if not cover or len(cover) == 0:
        missing.append('cover')

    # 检查歌词（str）
    lyric = metadata.get('lyric', '')
    if not lyric or len(lyric) == 0:
        missing.append('lyric')

    # 检查 platform 是否正确
    platform = metadata.get('platform', '')
    if platform and platform != PLATFORM:
        warnings.append(f"platform={platform!r} (期望 {PLATFORM!r})")

    # 检查 song_id 格式（应该是数字字符串）
    song_id = str(metadata.get('song_id', '')).strip()
    if song_id and not song_id.isdigit():
        warnings.append(f"song_id={song_id!r} 不是纯数字")

    # 检查歌手格式（多歌手用 / 分隔）
    artist = metadata.get('artist', '')
    if artist:
        for sep in [',', '，', ';', '；', '&', '\\', '、', '|', '_']:
            if sep in artist:
                warnings.append(f"artist={artist!r} 包含错误分隔符 {sep!r}")
                break

    return {
        'is_complete': len(missing) == 0,
        'missing_fields': missing,
        'warnings': warnings,
    }


def calculate_match_score(song_name: str, song_artist: str, result: dict) -> float:
    """计算搜索结果与本地歌曲的匹配分数（0-100）"""
    result_name = result.get('name', '').strip()
    result_artist = result.get('artists', '').strip()
    local_name = song_name.strip()
    local_artist = song_artist.strip()

    # 去除括号内容用于比较
    def strip_brackets(s):
        s = re.sub(r'\s*[\(\[（【][^\)\]）】]*[\)\]）】]', '', s)
        return s.strip()

    rn = strip_brackets(result_name)
    ln = strip_brackets(local_name)

    score = 0.0

    # 歌曲名匹配
    if rn == ln or rn == local_name or local_name == result_name:
        score += 50
    elif ln and rn and (ln in rn or rn in ln):
        score += 30

    # 艺术家匹配
    if not local_artist:
        score += 0
    elif local_artist == result_artist:
        score += 50
    elif result_artist and local_artist in result_artist:
        score += 30

    return score


def search_song(bodian: BodianClient, song_name: str, song_artist: str) -> dict:
    """使用多种策略搜索歌曲"""
    # 策略1: 歌曲名 + 歌手
    keyword1 = f"{song_name} {song_artist}" if song_artist else song_name
    # 策略2: 只用歌曲名
    keyword2 = song_name
    # 策略3: 去除括号后的歌曲名
    clean_name = re.sub(r'\s*[\(\[（【][^\)\]）】]*[\)\]）】]', '', song_name).strip()
    keyword3 = f"{clean_name} {song_artist}" if clean_name != song_name else None

    all_results = []
    seen_ids = set()

    for keyword in [keyword1, keyword2, keyword3]:
        if not keyword:
            continue
        try:
            results = bodian.search(keyword, limit=20)
            for r in results:
                rid = r.get('id', '')
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    all_results.append(r)
        except Exception as e:
            print(f'  ⚠️ 搜索失败 [{keyword}]: {e}')
        time.sleep(0.3)

    if not all_results:
        return None

    # 找最佳匹配
    best_match = None
    best_score = 0
    for r in all_results:
        score = calculate_match_score(song_name, song_artist, r)
        if score > best_score:
            best_score = score
            best_match = r

    if best_match and best_score >= 60:
        return {'song': best_match, 'score': best_score}
    return None


def fetch_full_metadata(bodian: BodianClient, song_id: str) -> dict:
    """从波点音乐获取完整的歌曲元数据

    注意: 多歌手需要使用 / 分隔（与 music_routes.py 的 _normalize_artist_name 行为一致）
    """
    info = bodian.get_song_info(song_id)
    lyric = ''
    try:
        lyric = bodian.get_lyric(song_id) or ''
    except Exception as e:
        print(f'  ⚠️ 获取歌词失败: {e}')

    # 关键: 歌手字段需要规范化（多歌手用 / 分隔）
    artist = info.get('artists', '')
    if artist:
        artist = normalize_artist_name(artist)

    return {
        'name': info.get('name', ''),
        'artist': artist,
        'album': info.get('album', ''),
        'picUrl': info.get('picUrl', ''),
        'lyric': lyric,
    }


def check_files():
    """检测周杰伦目录下所有歌曲的元数据完整性（不联网）

    Returns:
        bool: 所有文件元数据完整返回 True，否则 False
    """
    if not os.path.isdir(ZHOU_JIELUN_DIR):
        print(f'❌ 目录不存在: {ZHOU_JIELUN_DIR}')
        return False

    print('=' * 60)
    print('周杰伦目录元数据检测（不联网）')
    print('=' * 60)
    print(f'目录: {ZHOU_JIELUN_DIR}')
    print(f'平台: {PLATFORM} (波点音乐)')
    print(f'必需字段: {", ".join(REQUIRED_TEXT_FIELDS + REQUIRED_BLOB_FIELDS + REQUIRED_LYRIC_FIELDS)}')
    print()

    # 收集所有音频文件
    files = [f for f in os.listdir(ZHOU_JIELUN_DIR) if f.lower().endswith(('.flac', '.mp3', '.m4a'))]
    files.sort()
    print(f'共 {len(files)} 个音频文件')
    print()

    stats = {
        'total': len(files),
        'complete': 0,
        'incomplete': 0,
        'corrupted': 0,
        'with_warnings': 0,
    }

    incomplete_files = []
    corrupted_files = []
    warning_files = []

    for idx, filename in enumerate(files, 1):
        filepath = os.path.join(ZHOU_JIELUN_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()

        # 检查文件是否可读
        try:
            if ext == '.flac':
                from mutagen.flac import FLAC
                FLAC(filepath)
            elif ext == '.mp3':
                from mutagen.id3 import ID3
                ID3(filepath)
            elif ext in ('.m4a', '.mp4'):
                from mutagen.mp4 import MP4
                MP4(filepath)
        except Exception as e:
            print(f'[{idx:3d}/{len(files)}] ❌ {filename}')
            print(f'        文件损坏: {e}')
            stats['corrupted'] += 1
            corrupted_files.append((filename, str(e)))
            continue

        # 读取元数据
        try:
            metadata = read_metadata(filepath)
        except Exception as e:
            print(f'[{idx:3d}/{len(files)}] ❌ {filename}')
            print(f'        读取失败: {e}')
            stats['corrupted'] += 1
            corrupted_files.append((filename, str(e)))
            continue

        # 检查完整性
        check = check_metadata_completeness(metadata)

        # 输出
        if check['is_complete'] and not check['warnings']:
            mark = '✓'
        elif check['is_complete']:
            mark = '⚠️'
        else:
            mark = '✗'
        print(f'[{idx:3d}/{len(files)}] {mark} {filename}')

        # 显示元数据
        platform = metadata.get('platform', '')
        song_id = metadata.get('song_id', '')
        artist = metadata.get('artist', '')
        cover = metadata.get('cover', b'')
        lyric = metadata.get('lyric', '')
        print(f'        name:    {metadata.get("name", "")!r}')
        print(f'        artist:  {artist!r}')
        print(f'        album:   {metadata.get("album", "")!r}')
        print(f'        platform:{platform!r}, song_id: {song_id!r}')
        print(f'        cover:   {len(cover)} bytes')
        print(f'        lyric:   {len(lyric)} 字符')

        if check['is_complete']:
            stats['complete'] += 1
            if check['warnings']:
                stats['with_warnings'] += 1
                warning_files.append((filename, check['warnings']))
                for w in check['warnings']:
                    print(f'        ⚠️ {w}')
        else:
            stats['incomplete'] += 1
            incomplete_files.append((filename, check['missing_fields']))
            print(f'        缺失字段: {", ".join(check["missing_fields"])}')
            for w in check['warnings']:
                print(f'        ⚠️ {w}')

    # 输出统计
    print()
    print('=' * 60)
    print('检测统计:')
    print(f'  总文件数:    {stats["total"]}')
    print(f'  ✓ 完整:      {stats["complete"]}')
    print(f'  ⚠️ 完整但有警告: {stats["with_warnings"]}')
    print(f'  ✗ 不完整:    {stats["incomplete"]}')
    print(f'  ❌ 损坏:      {stats["corrupted"]}')

    # 不完整的文件
    if incomplete_files:
        print()
        print('=' * 60)
        print('元数据不完整的文件 (需要使用 --apply 修复):')
        print('=' * 60)
        for filename, missing in incomplete_files:
            print(f'  ✗ {filename}')
            print(f'    缺失: {", ".join(missing)}')

    # 有警告的文件
    if warning_files:
        print()
        print('=' * 60)
        print('元数据完整但有警告的文件:')
        print('=' * 60)
        for filename, warnings in warning_files:
            print(f'  ⚠️ {filename}')
            for w in warnings:
                print(f'    - {w}')

    # 损坏的文件
    if corrupted_files:
        print()
        print('=' * 60)
        print('损坏的文件:')
        print('=' * 60)
        for filename, error in corrupted_files:
            print(f'  ❌ {filename}: {error}')

    # 保存报告
    report = []
    report.append('周杰伦目录元数据检测报告')
    report.append('=' * 60)
    report.append(f'目录: {ZHOU_JIELUN_DIR}')
    report.append(f'平台: {PLATFORM} (波点音乐)')
    all_required = REQUIRED_TEXT_FIELDS + REQUIRED_BLOB_FIELDS + REQUIRED_LYRIC_FIELDS
    report.append(f'必需字段: {", ".join(all_required)}')
    report.append('')
    report.append('统计:')
    report.append(f'  总文件数:        {stats["total"]}')
    report.append(f'  ✓ 完整:          {stats["complete"]}')
    report.append(f'  ⚠️ 完整但有警告: {stats["with_warnings"]}')
    report.append(f'  ✗ 不完整:        {stats["incomplete"]}')
    report.append(f'  ❌ 损坏:          {stats["corrupted"]}')
    report.append('')

    if incomplete_files:
        report.append('=' * 60)
        report.append('元数据不完整的文件:')
        report.append('=' * 60)
        for filename, missing in incomplete_files:
            report.append(f'  {filename}')
            report.append(f'    缺失: {", ".join(missing)}')
        report.append('')

    if warning_files:
        report.append('=' * 60)
        report.append('元数据完整但有警告的文件:')
        report.append('=' * 60)
        for filename, warnings in warning_files:
            report.append(f'  {filename}')
            for w in warnings:
                report.append(f'    - {w}')
        report.append('')

    if corrupted_files:
        report.append('=' * 60)
        report.append('损坏的文件:')
        report.append('=' * 60)
        for filename, error in corrupted_files:
            report.append(f'  {filename}: {error}')

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print()
    print(f'报告已保存: {REPORT_PATH}')

    return stats['incomplete'] == 0 and stats['corrupted'] == 0


def process_files(apply: bool = False):
    """处理周杰伦目录下的所有文件"""
    if not os.path.isdir(ZHOU_JIELUN_DIR):
        print(f'❌ 目录不存在: {ZHOU_JIELUN_DIR}')
        return

    print('=' * 60)
    print(f'{"APPLY 模式" if apply else "DRY RUN 模式"} - {"会修改文件" if apply else "不修改文件"}')
    print('=' * 60)
    print(f'目录: {ZHOU_JIELUN_DIR}')
    print(f'平台: {PLATFORM} (波点音乐)')
    print()

    # 收集所有音频文件
    files = [f for f in os.listdir(ZHOU_JIELUN_DIR) if f.lower().endswith(('.flac', '.mp3', '.m4a'))]
    print(f'共 {len(files)} 个音频文件')
    print()

    bodian = BodianClient()

    stats = {
        'total': len(files),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'corrupted': 0,
    }

    report_lines = []
    report_lines.append('周杰伦目录处理报告')
    report_lines.append('=' * 60)
    report_lines.append(f'目录: {ZHOU_JIELUN_DIR}')
    report_lines.append(f'平台: {PLATFORM} (波点音乐)')
    report_lines.append('')
    report_lines.append('统计:')
    report_lines.append(f'  总文件数: {stats["total"]}')
    report_lines.append('')

    failed_items = []

    for idx, filename in enumerate(files, 1):
        filepath = os.path.join(ZHOU_JIELUN_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()

        print(f'[{idx}/{len(files)}] {filename}')

        # 1. 检查文件是否损坏
        try:
            if ext == '.flac':
                from mutagen.flac import FLAC
                FLAC(filepath)
            elif ext == '.mp3':
                from mutagen.id3 import ID3
                ID3(filepath)
            elif ext in ('.m4a', '.mp4'):
                from mutagen.mp4 import MP4
                MP4(filepath)
        except Exception as e:
            print(f'  ⚠️ 文件损坏: {e}')
            stats['corrupted'] += 1
            continue

        # 2. 解析文件名
        info = parse_song_info(filename)
        song_name = info['name']
        song_artist = info['artist']
        print(f'  解析: {song_name} - {song_artist}')

        # 3. 搜索
        match_result = search_song(bodian, song_name, song_artist)
        if not match_result:
            print(f'  ✗ 未找到匹配')
            stats['failed'] += 1
            failed_items.append(filename)
            continue

        matched_song = match_result['song']
        song_id = matched_song['id']
        score = match_result['score']
        print(f'  ✓ 匹配: {matched_song["name"]} | {matched_song["artists"]} (id={song_id}, score={score})')

        # 4. 获取完整元数据
        full_meta = fetch_full_metadata(bodian, song_id)
        print(f'  元数据: album={full_meta["album"]!r}, lyric_len={len(full_meta["lyric"])}')

        if not apply:
            stats['skipped'] += 1
            print(f'  [DRY RUN] 跳过写入')
            continue

        # 5. 写入元数据 - 歌手字段确保使用 / 分隔
        success = write_metadata(
            filepath, ext,
            name=full_meta['name'] or song_name,
            artist=full_meta['artist'] or normalize_artist_name(song_artist),
            album=full_meta['album'],
            lyric=full_meta['lyric'],
            cover_url=full_meta['picUrl'],
            platform=PLATFORM,
            song_id=song_id,
        )

        if success:
            print(f'  ✓ 写入成功')
            stats['success'] += 1
        else:
            print(f'  ✗ 写入失败')
            stats['failed'] += 1
            failed_items.append(filename)

        time.sleep(0.3)

    # 输出统计
    print()
    print('=' * 60)
    print('统计:')
    print(f'  总文件数: {stats["total"]}')
    print(f'  成功: {stats["success"]}')
    print(f'  失败: {stats["failed"]}')
    print(f'  跳过（DRY RUN）: {stats["skipped"]}')
    print(f'  文件损坏: {stats["corrupted"]}')

    if failed_items:
        print()
        print('失败文件:')
        for f in failed_items:
            print(f'  - {f}')


if __name__ == '__main__':
    if '--check' in sys.argv:
        # 检测模式：仅读取本地元数据，不联网
        success = check_files()
        sys.exit(0 if success else 1)
    else:
        apply = '--apply' in sys.argv
        process_files(apply=apply)
