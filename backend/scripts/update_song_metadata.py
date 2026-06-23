#!/usr/bin/env python3
"""批量更新歌曲库元数据

读取 /Volumes/资源库/音乐/歌曲 目录下所有歌曲文件，更新 platform 和 song_id 元数据。

规则:
- 跳过 1歌单原曲 目录
- 周杰伦 目录的歌曲从波点音乐搜索
- 其他歌手目录的歌曲从网易云音乐搜索

策略:
- 先尝试精确匹配 (歌曲名 + 歌手名)
- 失败则尝试只用歌曲名搜索
- 失败则尝试清理版本号/特殊字符后搜索
- 全部失败则跳过，记录到错误日志

用法:
    python3 scripts/update_song_metadata.py                 # DRY RUN - 全局搜索模式
    python3 scripts/update_song_metadata.py --apply        # APPLY - 全局搜索模式
    python3 scripts/update_song_metadata.py --playlist     # DRY RUN - 歌单模式
    python3 scripts/update_song_metadata.py --playlist --apply  # APPLY - 歌单模式

歌单模式配置（编辑脚本顶部的 PLAYLIST_URL 和 LOCAL_ARTIST_DIR）:
    PLAYLIST_URL       歌单 URL (支持网易云/QQ/波点/酷狗)
    LOCAL_ARTIST_DIR   本地歌手文件夹名 (例如: '陈楚生')
    PLAYLIST_MATCH_THRESHOLD  匹配阈值 (0-100，默认 70)
"""

import os
import re
import sys
import time
import json
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

sys.path.insert(0, '/Users/Awan/Public/Repository/wan-music/backend')

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, USLT, APIC, TXXX, error as ID3Error
from mutagen.mp4 import MP4, MP4Cover
import mutagen.mp4

from clients.music_client import MusicClient
# 使用重构后的工具模块
from utils.filename import normalize_artist_name, split_artists
from utils.metadata import write_metadata as _write_metadata, read_metadata as _read_metadata
from utils.audio_utils import safe_remove as _safe_remove
from utils.url_parser import parse_url as parse_music_url


MUSIC_DIR = '/Volumes/资源库/音乐/歌曲'
SKIP_DIR = '1歌单原曲'
BODIAN_ARTIST = '周杰伦'
REPORT_PATH = os.path.join(os.path.dirname(__file__), 'update_metadata_report.txt')

# ============================================================
# 歌单更新模式配置（使用 --playlist 模式时生效）
# ============================================================
# 网易云/波点音乐/QQ音乐的歌单 URL
PLAYLIST_URL = 'https://music.163.com/playlist?id=13594573645&uct2=U2FsdGVkX1/pK673OHOPBDRsWKG5o5y7wAjvO2gcht0='
# 本地歌手文件夹名（必须是 MUSIC_DIR 下的子目录）
# 例如: '陈楚生'、'林俊杰'、'毛不易'
LOCAL_ARTIST_DIR = '宝石Gem'
# 歌单匹配阈值 (0-100)，低于此分数视为不匹配
PLAYLIST_MATCH_THRESHOLD = 70
# 歌单模式报告路径
PLAYLIST_REPORT_PATH = os.path.join(os.path.dirname(__file__), 'update_from_playlist_report.txt')

# 详细统计
stats = {
    'total': 0,            # 总文件数
    'success': 0,          # 成功更新
    'skipped': 0,          # 跳过（已有元数据）
    'failed': 0,           # 匹配失败
    'corrupted': 0,        # 文件损坏
    'not_found': 0,        # 文件不存在
}

# 详细分类记录
report_data = {
    'success_files': [],       # 成功更新的文件
    'skipped_files': [],       # 跳过的文件（已有元数据）
    'failed_files': [],        # 匹配失败的文件 {歌手, 文件名, 歌曲名, 平台, 原因}
    'corrupted_files': [],     # 损坏的文件
    'not_found_files': [],     # 不存在的文件
    'exception_files': [],     # 处理异常的文件
}


# 多个歌手之间的分隔符（被错误使用的）
# _ 是分隔符 (例如: 汪苏泷_明柏辰, KEY.L刘聪_刘炫廷)
ARTIST_SEPARATORS = [',', '，', ';', '；', '&', '\\', '、', '|', '_']
CORRECT_SEPARATOR = '/'


def normalize_artist_string(artist_str: str) -> str:
    """将多个歌手的拼接格式统一为 /"""
    if not artist_str:
        return artist_str
    result = artist_str
    for sep in ARTIST_SEPARATORS:
        pattern = r'\s*' + re.escape(sep) + r'\s*'
        result = re.sub(pattern, lambda m, s=sep: s, result)
    for sep in ARTIST_SEPARATORS:
        result = result.replace(sep, CORRECT_SEPARATOR)
    result = re.sub(r'/+', '/', result)
    result = result.strip('/')
    return result.strip()


def split_artists(artist_str: str) -> list:
    """将多歌手字符串拆分为单个歌手列表"""
    if not artist_str:
        return []
    # 先标准化为 / 分割
    normalized = normalize_artist_string(artist_str)
    # 按 / 分割
    parts = [p.strip() for p in normalized.split('/') if p.strip()]
    return parts


def parse_song_info(filename: str) -> dict:
    """从文件名解析歌曲名和歌手名（歌手名内部用 / 拼接多歌手）"""
    name = os.path.splitext(filename)[0]
    match = re.match(r'^(.+?)\s*[-\u2013\u2014]\s*(.+)$', name)
    if match:
        # 歌手部分内部标准化
        artist = normalize_artist_string(match.group(2).strip())
        return {'name': match.group(1).strip(), 'artist': artist}
    return {'name': name.strip(), 'artist': ''}


def get_existing_metadata(filepath: str) -> dict:
    """获取现有元数据"""
    ext = os.path.splitext(filepath)[1].lower()
    metadata = {'name': '', 'artist': '', 'album': '', 'lyric': '', 'cover': ''}

    try:
        if ext == '.flac':
            audio = FLAC(filepath)
            metadata['name'] = audio.get('title', [''])[0]
            metadata['artist'] = audio.get('artist', [''])[0]
            metadata['album'] = audio.get('album', [''])[0]
            metadata['lyric'] = audio.get('lyrics', [''])[0] if 'lyrics' in audio else ''
        elif ext == '.mp3':
            audio = ID3(filepath)
            metadata['name'] = str(audio.get('TIT2', ''))
            metadata['artist'] = str(audio.get('TPE1', ''))
            metadata['album'] = str(audio.get('TALB', ''))
            uslt = audio.getall('USLT')
            metadata['lyric'] = uslt[0].text if uslt else ''
        elif ext in ('.m4a', '.mp4'):
            audio = MP4(filepath)
            metadata['name'] = audio.get('\xa9nam', [''])[0]
            metadata['artist'] = audio.get('\xa9ART', [''])[0]
            metadata['album'] = audio.get('\xa9alb', [''])[0]
            metadata['lyric'] = audio.get('\xa9lyr', [''])[0]
    except Exception as e:
        print(f'  ⚠️ 读取元数据失败: {e}')

    return metadata


def get_existing_platform_id(filepath: str) -> tuple:
    """获取现有的 platform 和 song_id"""
    ext = os.path.splitext(filepath)[1].lower()
    platform = ''
    song_id = ''

    try:
        if ext == '.flac':
            audio = FLAC(filepath)
            platform = audio.get('PLATFORM', [''])[0]
            song_id = audio.get('SONG_ID', [''])[0]
        elif ext == '.mp3':
            audio = ID3(filepath)
            txxx_p = audio.getall('TXXX:PLATFORM')
            platform = txxx_p[0].text[0] if txxx_p else ''
            txxx_s = audio.getall('TXXX:SONG_ID')
            song_id = txxx_s[0].text[0] if txxx_s else ''
        elif ext in ('.m4a', '.mp4'):
            audio = MP4(filepath)
            p_list = audio.get('----:com.apple.iTunes:PLATFORM', [])
            platform = p_list[0].decode('utf-8') if p_list else ''
            s_list = audio.get('----:com.apple.iTunes:SONG_ID', [])
            song_id = s_list[0].decode('utf-8') if s_list else ''
    except:
        pass

    return platform, song_id


def is_corrupted(filepath: str) -> bool:
    """检查文件是否损坏"""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.mp3':
            ID3(filepath)
        elif ext == '.flac':
            FLAC(filepath)
        elif ext in ('.m4a', '.mp4'):
            MP4(filepath)
        return False
    except:
        return True


def normalize_name(s: str) -> str:
    """标准化歌曲名：去除括号、空格、特殊字符"""
    if not s:
        return ''
    # 去除括号内容
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'\s*（[^）]*）', '', s)
    s = re.sub(r'\s*\[[^\]]*\]', '', s)
    s = re.sub(r'\s*【[^】]*】', '', s)
    # 标准化分隔符
    s = re.sub(r'[\s\-_]+', '', s)
    return s.lower().strip()


def calculate_match_score(song_name: str, song_artist: str, result: dict) -> float:
    """计算搜索结果与本地歌曲的匹配分数（0-100）

    关键: 多歌手情况下，先标准化分隔符再比较
    - 源文件: Beyond_刘汉乐_王菲_方季惟_黄翊 (_ 分隔)
    - API返回: Beyond/刘汉乐/王菲/方季惟/黄翊 (/ 分隔)
    - 这两个本质上是同一组歌手，需要正确识别

    匹配优先级:
    - 歌曲名完全匹配: 50
    - 歌曲名包含/部分匹配: 30
    - 艺术家完全匹配: 50
    - 艺术家部分匹配: 按比例给分
    """
    result_name = normalize_name(result.get('name', ''))
    result_artist_raw = result.get('artists', '')
    local_name = normalize_name(song_name)

    score = 0.0

    # 歌曲名匹配
    if result_name == local_name:
        score += 50
    elif local_name and result_name and (local_name in result_name or result_name in local_name):
        score += 30

    # 艺术家匹配 - 关键改进：先标准化再比较
    local_artists = split_artists(song_artist)  # 本地多歌手
    result_artists = split_artists(result_artist_raw)  # API 返回的多歌手

    if not local_artists:
        # 本地没有艺术家信息，跳过
        pass
    elif len(local_artists) == 1 and len(result_artists) == 1:
        # 单歌手 vs 单歌手 - 简单比较
        la_norm = normalize_name(local_artists[0])
        ra_norm = normalize_name(result_artists[0])
        if la_norm == ra_norm:
            score += 50
        elif la_norm and ra_norm and (la_norm in ra_norm or ra_norm in la_norm):
            score += 30
    else:
        # 多歌手情况 - 严格匹配
        if not result_artists:
            pass
        else:
            # 检查每个本地歌手是否在结果中找到（子串匹配）
            matched = 0
            for la in local_artists:
                la_norm = normalize_name(la)
                # 在 result_artists 列表中找匹配
                if any(la_norm == normalize_name(ra) or
                       (la_norm in normalize_name(ra)) or
                       (normalize_name(ra) in la_norm)
                       for ra in result_artists):
                    matched += 1

            if matched == len(local_artists) and matched == len(result_artists):
                # 所有歌手都精确匹配
                score += 50
            elif matched == len(local_artists):
                # 所有本地歌手都在结果中（结果可能多）
                score += 50
            elif matched > 0:
                # 部分匹配，按比例给分
                score += 30 * matched / len(local_artists)

    return score


def calculate_strict_artist_match(local_artist: str, result_artist: str) -> bool:
    """严格检查本地艺术家的每个歌手是否都在结果中出现（用于多歌手情况）"""
    if not local_artist or not result_artist:
        return False
    # 多歌手分割
    local_artists = re.split(r'[/、，,\s&]+', local_artist)
    local_artists = [a.strip() for a in local_artists if a.strip()]
    if not local_artists:
        return False
    # 每个本地歌手都要在结果中
    for la in local_artists:
        if la not in result_artist:
            return False
    return True


def safe_search(client: MusicClient, keyword: str, platform: str, limit: int = 10, max_retries: int = 5):
    """带重试和指数退避的安全搜索"""
    last_exception = None
    for attempt in range(max_retries):
        try:
            results = client.search(keyword, platform=platform, limit=limit)
            return results
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                # 指数退避: 1s, 2s, 4s, 8s
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    # 所有重试都失败
    raise last_exception if last_exception else Exception("搜索失败")


def search_song(client: MusicClient, song_name: str, song_artist: str, platform: str) -> dict:
    """在指定平台搜索歌曲，使用多种策略，返回最佳匹配

    优化策略:
    - 短歌名（≤3字）要求艺术家必须严格匹配
    - 多歌手时用 strict_artist_match
    - 多个关键词组合
    """
    best_match = None
    best_score = 0
    is_short_name = len(song_name) <= 3 if song_name else False

    def try_search(keyword: str, require_strict_artist: bool = False, is_cleaned: bool = False):
        """内部函数: 尝试一次搜索"""
        nonlocal best_match, best_score
        try:
            results = safe_search(client, keyword, platform=platform, limit=15)
            for r in results:
                result_artist = r.get('artists', '')
                result_name = r.get('name', '')

                # 短歌名/已清理: 要求艺术家必须严格匹配
                if require_strict_artist and song_artist:
                    # 严格匹配：本地歌手必须在结果中
                    if not calculate_strict_artist_match(song_artist, result_artist):
                        continue

                # 清理后的歌曲名: 歌曲名匹配要求更严格
                if is_cleaned:
                    cleaned_local = normalize_name(re.sub(r'\s*[\(\[【].*?[\)】】]\s*', '', song_name).strip())
                    cleaned_result = normalize_name(re.sub(r'\s*[\(\[【].*?[\)】】]\s*', '', result_name).strip())
                    if cleaned_local != cleaned_result:
                        continue

                score = calculate_match_score(song_name, song_artist, r)
                if score > best_score:
                    best_score = score
                    best_match = r
                if score >= 80:
                    return True  # 找到完美匹配
        except Exception:
            pass
        return False

    # 策略1: 歌曲名 + 歌手名（最优先）
    if song_name and song_artist:
        if try_search(f'{song_name} {song_artist}', require_strict_artist=False):
            return best_match, best_score

    # 策略2: 调换顺序 - 歌手 + 歌曲名
    if best_score < 80 and song_name and song_artist:
        if try_search(f'{song_artist} {song_name}', require_strict_artist=False):
            return best_match, best_score

    # 策略3: 只搜歌曲名 + 短歌名严格匹配
    if best_score < 80 and song_name:
        require_strict = is_short_name and bool(song_artist)
        if try_search(song_name, require_strict_artist=require_strict):
            return best_match, best_score

    # 策略4: 清理歌曲名（去括号）后再搜
    if best_score < 60 and song_name:
        cleaned_name = re.sub(r'\s*[\(\[【].*?[\)】】]\s*', '', song_name).strip()
        if cleaned_name and cleaned_name != song_name:
            require_strict = is_short_name and bool(song_artist)
            if try_search(cleaned_name, require_strict_artist=require_strict, is_cleaned=True):
                return best_match, best_score

    # 策略5: 艺术家单独搜索（用于非常短或容易混淆的歌曲名）
    if best_score < 60 and song_artist and is_short_name:
        if try_search(song_artist, require_strict_artist=True):
            return best_match, best_score

    # 策略6: 多歌手时，单独搜每个歌手（取第一个搜索）
    if best_score < 60 and song_artist and '/' in song_artist:
        local_artists = split_artists(song_artist)
        if local_artists:
            # 第一个歌手 + 歌曲名
            first_artist = local_artists[0]
            if try_search(f'{song_name} {first_artist}', require_strict_artist=False):
                return best_match, best_score
            # 只搜歌曲名
            if try_search(song_name, require_strict_artist=False):
                return best_match, best_score

    return best_match, best_score


def process_song(filepath: str, client: MusicClient, dry_run: bool = True) -> str:
    """处理单首歌曲

    Returns:
        'success' - 成功
        'failed' - 失败（找不到匹配）
        'skipped' - 跳过（已有元数据或无需更新）
        'corrupted' - 文件损坏
        'not_found' - 文件不存在
    """
    filename = os.path.basename(filepath)

    # 检查文件是否存在
    if not os.path.exists(filepath):
        return 'not_found'

    # 检查文件是否损坏
    if is_corrupted(filepath):
        return 'corrupted'

    # 读取现有元数据
    existing_platform, existing_song_id = get_existing_platform_id(filepath)
    if existing_platform and existing_song_id:
        # 已有完整元数据，跳过
        return 'skipped'

    # 解析文件名（用于文件名优先的策略）
    info = parse_song_info(filename)
    # 元数据中已有的更准确，优先使用
    metadata = get_existing_metadata(filepath)
    song_name = metadata.get('name') or info['name']
    song_artist = metadata.get('artist') or info['artist']

    if not song_name:
        return 'failed'

    # 确定平台
    platform = 'bodian' if song_artist == BODIAN_ARTIST else 'netease'

    # 搜索
    best_match, score = search_song(client, song_name, song_artist, platform)
    if not best_match or score < 60:
        return 'failed'

    song_id = str(best_match.get('id', ''))
    source = best_match.get('source', platform)

    if not song_id:
        return 'failed'

    if dry_run:
        return 'success'  # 测试模式下认为成功

    # 实际写入
    try:
        ext = os.path.splitext(filepath)[1].lower()
        _write_metadata(
            filepath, ext,
            name=metadata.get('name', song_name),
            artist=metadata.get('artist', song_artist),
            album=metadata.get('album', ''),
            lyric=metadata.get('lyric', ''),
            cover_url='',
            platform=source,
            song_id=song_id
        )
        return 'success'
    except Exception as e:
        print(f'  写入失败: {e}')
        return 'failed'


def process_artist_dir(artist_dir: str, client: MusicClient, dry_run: bool = True):
    """处理一个歌手目录"""
    artist_name = os.path.basename(artist_dir)
    print(f'\n=== {artist_name} ===')

    # 收集所有音频文件
    audio_files = []
    for f in sorted(os.listdir(artist_dir)):
        if f.lower().endswith(('.mp3', '.flac', '.m4a', '.mp4')):
            audio_files.append(os.path.join(artist_dir, f))

    print(f'  共 {len(audio_files)} 首歌曲')

    artist_stats = Counter()
    consecutive_failures = 0  # 跟踪连续失败次数

    for filepath in audio_files:
        filename = os.path.basename(filepath)
        try:
            # 文件不存在检查
            if not os.path.exists(filepath):
                artist_stats['not_found'] += 1
                report_data['not_found_files'].append(f'{artist_name}/{filename}')
                print(f'  ✗ {filename} - 文件不存在')
                continue

            # 文件损坏检查
            if is_corrupted(filepath):
                artist_stats['corrupted'] += 1
                report_data['corrupted_files'].append(f'{artist_name}/{filename}')
                print(f'  ⚠️ {filename} - 文件损坏')
                continue

            # 读取现有元数据
            existing_platform, existing_song_id = get_existing_platform_id(filepath)
            if existing_platform and existing_song_id:
                artist_stats['skipped'] += 1
                report_data['skipped_files'].append(
                    f'{artist_name}/{filename} (platform={existing_platform}, song_id={existing_song_id})'
                )
                continue

            # 解析歌曲信息
            info = parse_song_info(filename)
            metadata = get_existing_metadata(filepath)
            song_name = metadata.get('name') or info['name']
            song_artist = metadata.get('artist') or info['artist']

            if not song_name:
                artist_stats['failed'] += 1
                report_data['failed_files'].append({
                    'artist': artist_name,
                    'filename': filename,
                    'song_name': '(空)',
                    'platform': 'unknown',
                    'reason': '无法解析歌曲名',
                    'best_match': None,
                    'score': 0
                })
                print(f'  ✗ {filename} - 无法解析歌曲名')
                consecutive_failures += 1
                time.sleep(0.3)
                continue

            # 确定平台
            platform = 'bodian' if song_artist == BODIAN_ARTIST else 'netease'

            # 搜索
            best_match, score = search_song(client, song_name, song_artist, platform)
            if not best_match or score < 60:
                artist_stats['failed'] += 1
                reason = f'搜索无结果 (score={score})' if not best_match else f'匹配度低 (score={score})'
                report_data['failed_files'].append({
                    'artist': artist_name,
                    'filename': filename,
                    'song_name': song_name,
                    'song_artist': song_artist,
                    'platform': platform,
                    'reason': reason,
                    'best_match': {
                        'name': best_match.get('name') if best_match else None,
                        'artists': best_match.get('artists') if best_match else None,
                        'id': best_match.get('id') if best_match else None,
                    } if best_match else None,
                    'score': score
                })
                if best_match:
                    print(f'  ✗ {filename} (匹配: {best_match.get("name")} | {best_match.get("artists")} | score={score})')
                else:
                    print(f'  ✗ {filename} (未找到结果)')
                consecutive_failures += 1
            else:
                # 成功
                song_id = str(best_match.get('id', ''))
                source = best_match.get('source', platform)
                artist_stats['success'] += 1
                if not dry_run:
                    # 实际写入
                    try:
                        ext = os.path.splitext(filepath)[1].lower()
                        _write_metadata(
                            filepath, ext,
                            name=metadata.get('name', song_name),
                            artist=metadata.get('artist', song_artist),
                            album=metadata.get('album', ''),
                            lyric=metadata.get('lyric', ''),
                            cover_url='',
                            platform=source,
                            song_id=song_id
                        )
                        report_data['success_files'].append(
                            f'{artist_name}/{filename} → {source}:{song_id}'
                        )
                    except Exception as e:
                        # 写入失败，归类到异常
                        artist_stats['success'] -= 1
                        artist_stats['failed'] += 1
                        report_data['exception_files'].append(
                            f'{artist_name}/{filename} - 写入失败: {e}'
                        )
                        print(f'  ✗ {filename} - 写入失败: {e}')
                        consecutive_failures += 1
                else:
                    report_data['success_files'].append(
                        f'{artist_name}/{filename} → {source}:{song_id} (dry-run)'
                    )
                consecutive_failures = 0

            # 智能延迟避免 API 限流
            if consecutive_failures >= 3:
                wait = min(5 + (consecutive_failures - 3) * 2, 30)
                time.sleep(wait)
            elif consecutive_failures >= 2:
                time.sleep(2)
            elif consecutive_failures >= 1:
                time.sleep(1)
            else:
                time.sleep(0.3)

        except Exception as e:
            artist_stats['failed'] += 1
            report_data['exception_files'].append(f'{artist_name}/{filename} - {type(e).__name__}: {e}')
            print(f'  ✗ {filename} - 异常: {e}')
            consecutive_failures += 1
            time.sleep(2)

    # 统计
    for k, v in artist_stats.items():
        stats[k] = stats.get(k, 0) + v

    print(f'  ✓ 成功: {artist_stats["success"]} | ✗ 失败: {artist_stats["failed"]} | 跳过: {artist_stats["skipped"]} | ⚠️ 损坏: {artist_stats["corrupted"]} | 文件不存在: {artist_stats.get("not_found", 0)}')

    return dict(artist_stats)


# ============================================================
# 歌单更新模式 - 通过歌单URL匹配本地歌曲
# ============================================================

def fetch_playlist(playlist_url: str, client: MusicClient) -> list:
    """从歌单 URL 解析并获取歌单中的所有歌曲

    Args:
        playlist_url: 歌单 URL (支持网易云/QQ/波点/酷狗)
        client: MusicClient 实例

    Returns:
        list: 歌曲列表，每项包含 {id, name, artists, album, picUrl, source}
    """
    parsed = parse_music_url(playlist_url)
    if not parsed:
        print(f'❌ 无法解析歌单 URL: {playlist_url}')
        return []
    if parsed['type'] != 'playlist':
        print(f'❌ URL 不是歌单类型: {parsed["type"]}')
        return []

    platform = parsed['platform']
    playlist_id = parsed['id']
    print(f'✓ 解析歌单: platform={platform}, id={playlist_id}')

    try:
        info = client.get_playlist(playlist_id, platform=platform)
    except Exception as e:
        print(f'❌ 获取歌单失败: {e}')
        return []

    tracks = info.get('tracks', [])
    print(f'✓ 歌单: {info.get("name", "(无名称)")} - 共 {len(tracks)} 首歌曲')

    # 标准化每首歌曲的歌手字段
    for t in tracks:
        if 'artists' in t and t['artists']:
            t['artists'] = normalize_artist_string(t['artists'])

    return tracks


def match_local_with_playlist(
    local_files: list,
    playlist_tracks: list,
    target_artist: str,
    threshold: float = 70
) -> list:
    """将本地歌曲文件与歌单中的歌曲匹配

    Args:
        local_files: 本地文件路径列表
        playlist_tracks: 歌单歌曲列表
        target_artist: 目标歌手名（用于过滤歌单歌曲）
        threshold: 匹配阈值 (0-100)

    Returns:
        list: 匹配结果列表，每项:
            {
                'local_path': str,         # 本地文件路径
                'local_filename': str,     # 本地文件名
                'parsed_name': str,        # 从文件名解析的歌曲名
                'parsed_artist': str,      # 从文件名解析的歌手
                'matched_track': dict|None,  # 匹配的歌单歌曲
                'score': float,            # 匹配分数
            }
    """
    # 过滤歌单中目标歌手的歌曲（用 normalize 后的名字比较）
    target_artist_norm = normalize_artist_string(target_artist)
    target_artists = split_artists(target_artist_norm)

    relevant_tracks = []
    for track in playlist_tracks:
        track_artist = track.get('artists', '')
        if not track_artist:
            continue
        track_artists_list = split_artists(track_artist)
        # 目标歌手的任一名字在歌曲歌手列表中即认为相关
        for ta in target_artists:
            if any(ta in a or a in ta for a in track_artists_list):
                relevant_tracks.append(track)
                break

    print(f'  歌单中与歌手 [{target_artist}] 相关的歌曲: {len(relevant_tracks)}')

    results = []
    for filepath in local_files:
        filename = os.path.basename(filepath)
        info = parse_song_info(filename)
        result = {
            'local_path': filepath,
            'local_filename': filename,
            'parsed_name': info['name'],
            'parsed_artist': info['artist'],
            'matched_track': None,
            'score': 0,
        }

        # 与每首相关歌单歌曲计算匹配分数
        best_track = None
        best_score = 0
        for track in relevant_tracks:
            score = calculate_match_score(
                info['name'],
                target_artist_norm,
                {'name': track.get('name', ''), 'artists': track.get('artists', '')}
            )
            if score > best_score:
                best_score = score
                best_track = track

        if best_track and best_score >= threshold:
            result['matched_track'] = best_track
            result['score'] = best_score

        results.append(result)

    return results


def process_playlist_mode(apply: bool = False):
    """歌单更新模式 - 通过歌单URL匹配本地歌曲并更新元数据

    工作流程:
    1. 解析 PLAYLIST_URL 获取歌单中所有歌曲
    2. 扫描 LOCAL_ARTIST_DIR 目录下的所有音频文件
    3. 匹配本地歌曲与歌单歌曲
    4. 用歌单中的 ID 更新本地文件的元数据
    """
    print('=' * 60)
    print(f'歌单更新模式 - {"APPLY" if apply else "DRY RUN"}')
    print('=' * 60)
    print(f'歌单 URL: {PLAYLIST_URL}')
    print(f'本地歌手目录: {LOCAL_ARTIST_DIR}')
    print(f'匹配阈值: {PLAYLIST_MATCH_THRESHOLD}')
    print()

    # 检查本地歌手目录
    local_dir = os.path.join(MUSIC_DIR, LOCAL_ARTIST_DIR)
    if not os.path.isdir(local_dir):
        print(f'❌ 本地歌手目录不存在: {local_dir}')
        return

    # 1. 获取歌单歌曲
    client = MusicClient()
    playlist_tracks = fetch_playlist(PLAYLIST_URL, client)
    if not playlist_tracks:
        print('❌ 歌单为空或获取失败')
        return

    print()

    # 2. 扫描本地歌曲文件
    local_files = []
    for f in sorted(os.listdir(local_dir)):
        if f.lower().endswith(('.mp3', '.flac', '.m4a', '.mp4')):
            local_files.append(os.path.join(local_dir, f))

    print(f'本地歌手 [{LOCAL_ARTIST_DIR}] 共 {len(local_files)} 首歌曲')
    print()

    # 3. 匹配
    match_results = match_local_with_playlist(
        local_files, playlist_tracks, LOCAL_ARTIST_DIR,
        threshold=PLAYLIST_MATCH_THRESHOLD
    )

    # 4. 输出匹配结果
    matched_count = 0
    unmatched_count = 0
    platform_stats = {}

    print()
    print('=' * 60)
    print('匹配结果:')
    print('=' * 60)

    for r in match_results:
        if r['matched_track']:
            matched_count += 1
            track = r['matched_track']
            platform = track.get('source', 'unknown')
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
            print(f'  ✓ {r["local_filename"]}')
            print(f'      歌单: {track.get("name", "")} - {track.get("artists", "")} (id={track.get("id", "")}, {platform}, score={r["score"]:.0f})')
        else:
            unmatched_count += 1
            print(f'  ✗ {r["local_filename"]} - 歌单中无匹配')

    print()
    print('=' * 60)
    print('统计:')
    print(f'  歌单歌曲数:   {len(playlist_tracks)}')
    print(f'  歌单相关歌曲: {sum(1 for t in playlist_tracks if any(ta in normalize_artist_string(t.get("artists", "")) for ta in split_artists(LOCAL_ARTIST_DIR)))}')
    print(f'  本地歌曲数:   {len(local_files)}')
    print(f'  ✓ 已匹配:     {matched_count}')
    print(f'  ✗ 未匹配:     {unmatched_count}')
    if platform_stats:
        print('  平台分布:')
        for p, c in platform_stats.items():
            print(f'    - {p}: {c}')

    # 5. 实际写入
    if not apply:
        print()
        print('[DRY RUN] 跳过实际写入')
    else:
        print()
        print('=' * 60)
        print('写入元数据...')
        print('=' * 60)

        success = 0
        failed = 0
        for r in match_results:
            if not r['matched_track']:
                continue

            filepath = r['local_path']
            track = r['matched_track']
            ext = os.path.splitext(filepath)[1].lower()

            # 读取现有元数据
            try:
                existing = _read_metadata(filepath)
            except Exception as e:
                print(f'  ✗ {r["local_filename"]} - 读取失败: {e}')
                failed += 1
                continue

            # 歌手字段统一格式化
            new_artist = normalize_artist_string(track.get('artists', ''))

            try:
                ok = _write_metadata(
                    filepath, ext,
                    name=track.get('name', '') or existing.get('name', ''),
                    artist=new_artist or existing.get('artist', ''),
                    album=track.get('album', '') or existing.get('album', ''),
                    lyric=existing.get('lyric', ''),
                    cover_url=track.get('picUrl', ''),
                    platform=track.get('source', ''),
                    song_id=str(track.get('id', '')),
                )
                if ok:
                    print(f'  ✓ {r["local_filename"]} → {track.get("source", "")}:{track.get("id", "")}')
                    success += 1
                else:
                    print(f'  ✗ {r["local_filename"]} - 写入失败')
                    failed += 1
            except Exception as e:
                print(f'  ✗ {r["local_filename"]} - 异常: {e}')
                failed += 1

            time.sleep(0.3)

        print()
        print(f'写入完成: 成功 {success} | 失败 {failed}')

    # 6. 保存报告
    report = []
    report.append('歌单更新模式 - 处理报告')
    report.append('=' * 60)
    report.append(f'生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    report.append(f'运行模式: {"APPLY" if apply else "DRY RUN"}')
    report.append(f'歌单 URL: {PLAYLIST_URL}')
    report.append(f'本地歌手目录: {LOCAL_ARTIST_DIR}')
    report.append(f'匹配阈值: {PLAYLIST_MATCH_THRESHOLD}')
    report.append('')
    report.append('统计:')
    report.append(f'  歌单歌曲数:   {len(playlist_tracks)}')
    report.append(f'  本地歌曲数:   {len(local_files)}')
    report.append(f'  ✓ 已匹配:     {matched_count}')
    report.append(f'  ✗ 未匹配:     {unmatched_count}')
    report.append('')
    report.append('详细匹配结果:')
    for r in match_results:
        if r['matched_track']:
            t = r['matched_track']
            report.append(f'  ✓ {r["local_filename"]}  ↔  {t.get("name", "")} - {t.get("artists", "")} (id={t.get("id", "")}, {t.get("source", "")}, score={r["score"]:.0f})')
        else:
            report.append(f'  ✗ {r["local_filename"]}  -  歌单中无匹配')

    with open(PLAYLIST_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    print()
    print(f'📄 报告已保存: {PLAYLIST_REPORT_PATH}')


def save_report(dry_run: bool, duration: float = 0):
    """保存详细统计报告到 txt 文件"""
    total = stats['total']
    success = stats['success']
    failed = stats['failed']
    skipped = stats['skipped']
    corrupted = stats['corrupted']
    not_found = stats['not_found']

    success_rate = (success / total * 100) if total > 0 else 0

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('=' * 70 + '\n')
        f.write('歌曲元数据更新 - 详细统计报告\n')
        f.write('=' * 70 + '\n')
        f.write(f'生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'运行模式: {"DRY RUN (试运行)" if dry_run else "APPLY (实际写入)"}\n')
        f.write(f'歌曲库目录: {MUSIC_DIR}\n')
        f.write(f'运行耗时: {duration:.1f} 秒\n')
        f.write('\n')

        # 总体统计
        f.write('-' * 70 + '\n')
        f.write('【总体统计】\n')
        f.write('-' * 70 + '\n')
        f.write(f'  总文件数:        {total}\n')
        f.write(f'  ✓ 成功:          {success}  ({success_rate:.1f}%)\n')
        f.write(f'  ⏭  跳过(已有元数据): {skipped}\n')
        f.write(f'  ✗ 匹配失败:      {failed}\n')
        f.write(f'  ⚠️ 文件损坏:      {corrupted}\n')
        f.write(f'  ?  文件不存在:    {not_found}\n')
        f.write('\n')

        # 异常汇总
        f.write('-' * 70 + '\n')
        f.write('【异常汇总】\n')
        f.write('-' * 70 + '\n')
        total_exceptions = failed + corrupted + not_found + len(report_data['exception_files'])
        f.write(f'  需要人工处理的异常总数: {total_exceptions}\n')
        f.write(f'  ├─ 匹配失败（找不到歌曲）: {failed}\n')
        f.write(f'  ├─ 文件损坏:              {corrupted}\n')
        f.write(f'  ├─ 文件不存在:            {not_found}\n')
        f.write(f'  └─ 处理异常:              {len(report_data["exception_files"])}\n')
        f.write('\n')

        # 失败文件详情
        if report_data['failed_files']:
            f.write('-' * 70 + '\n')
            f.write(f'【匹配失败的文件】共 {len(report_data["failed_files"])} 个\n')
            f.write('-' * 70 + '\n')

            # 按歌手分组
            failed_by_artist = {}
            for item in report_data['failed_files']:
                artist = item.get('artist', 'unknown')
                failed_by_artist.setdefault(artist, []).append(item)

            for artist in sorted(failed_by_artist.keys()):
                items = failed_by_artist[artist]
                f.write(f'\n【{artist}】({len(items)} 个)\n')
                for item in items:
                    f.write(f'  - 文件: {item["filename"]}\n')
                    f.write(f'    歌曲: {item.get("song_name", "(空)")}')
                    if item.get('song_artist'):
                        f.write(f' - {item["song_artist"]}')
                    f.write('\n')
                    f.write(f'    平台: {item.get("platform", "unknown")}\n')
                    f.write(f'    原因: {item.get("reason", "未知")}\n')
                    if item.get('best_match'):
                        bm = item['best_match']
                        if bm.get('name'):
                            f.write(f'    最佳匹配: {bm["name"]} | {bm.get("artists", "")} (id={bm.get("id", "")})\n')
                    f.write('\n')

        # 文件损坏列表
        if report_data['corrupted_files']:
            f.write('-' * 70 + '\n')
            f.write(f'【文件损坏】共 {len(report_data["corrupted_files"])} 个\n')
            f.write('-' * 70 + '\n')
            f.write('建议：删除后重新下载\n\n')
            for fpath in report_data['corrupted_files']:
                f.write(f'  - {fpath}\n')
            f.write('\n')

        # 文件不存在列表
        if report_data['not_found_files']:
            f.write('-' * 70 + '\n')
            f.write(f'【文件不存在】共 {len(report_data["not_found_files"])} 个\n')
            f.write('-' * 70 + '\n')
            f.write('建议：检查文件是否被移动或删除\n\n')
            for fpath in report_data['not_found_files']:
                f.write(f'  - {fpath}\n')
            f.write('\n')

        # 处理异常列表
        if report_data['exception_files']:
            f.write('-' * 70 + '\n')
            f.write(f'【处理异常】共 {len(report_data["exception_files"])} 个\n')
            f.write('-' * 70 + '\n')
            for fpath in report_data['exception_files']:
                f.write(f'  - {fpath}\n')
            f.write('\n')

        # 成功文件列表（按歌手分组）
        if report_data['success_files']:
            f.write('-' * 70 + '\n')
            f.write(f'【成功更新】共 {len(report_data["success_files"])} 个\n')
            f.write('-' * 70 + '\n')

            # 按歌手分组
            success_by_artist = {}
            for line in report_data['success_files']:
                artist = line.split('/')[0] if '/' in line else 'unknown'
                success_by_artist.setdefault(artist, []).append(line)

            for artist in sorted(success_by_artist.keys()):
                items = success_by_artist[artist]
                f.write(f'\n【{artist}】({len(items)} 个)\n')
                for line in items[:50]:  # 每个歌手最多列 50 个
                    f.write(f'  ✓ {line}\n')
                if len(items) > 50:
                    f.write(f'  ... 还有 {len(items) - 50} 个\n')

        # 跳过文件列表
        if report_data['skipped_files']:
            f.write('\n')
            f.write('-' * 70 + '\n')
            f.write(f'【已跳过（已有元数据）】共 {len(report_data["skipped_files"])} 个\n')
            f.write('-' * 70 + '\n')
            # 按歌手分组
            skipped_by_artist = {}
            for line in report_data['skipped_files']:
                artist = line.split('/')[0] if '/' in line else 'unknown'
                skipped_by_artist.setdefault(artist, []).append(line)

            for artist in sorted(skipped_by_artist.keys()):
                items = skipped_by_artist[artist]
                f.write(f'\n【{artist}】({len(items)} 个)\n')
                for line in items[:10]:  # 每个歌手最多列 10 个
                    f.write(f'  ⏭  {line}\n')
                if len(items) > 10:
                    f.write(f'  ... 还有 {len(items) - 10} 个\n')

        f.write('\n' + '=' * 70 + '\n')
        f.write('报告结束\n')
        f.write('=' * 70 + '\n')

    print(f'\n📄 详细报告已保存: {REPORT_PATH}')


def main():
    dry_run = '--apply' not in sys.argv
    start_time = time.time()

    # 歌单更新模式
    if '--playlist' in sys.argv:
        process_playlist_mode(apply=dry_run is False)
        return

    if dry_run:
        print('=' * 60)
        print('DRY RUN 模式 - 不会修改任何文件')
        print('使用 --apply 参数实际写入元数据')
        print('=' * 60)
    else:
        print('=' * 60)
        print('APPLY 模式 - 实际写入元数据')
        print('=' * 60)

    if not os.path.isdir(MUSIC_DIR):
        print(f'错误: 目录不存在 - {MUSIC_DIR}')
        sys.exit(1)

    print(f'歌曲库目录: {MUSIC_DIR}')

    # 创建音乐客户端
    client = MusicClient()

    # 获取所有歌手目录
    artist_dirs = []
    for item in sorted(os.listdir(MUSIC_DIR)):
        if item == SKIP_DIR:
            print(f'\n跳过目录: {item}')
            continue
        item_path = os.path.join(MUSIC_DIR, item)
        if os.path.isdir(item_path):
            artist_dirs.append(item_path)

    print(f'找到 {len(artist_dirs)} 个歌手目录\n')

    # 统计总文件数
    total_count = 0
    for artist_dir in artist_dirs:
        for f in os.listdir(artist_dir):
            if f.lower().endswith(('.mp3', '.flac', '.m4a', '.mp4')):
                total_count += 1
    stats['total'] = total_count

    # 处理每个歌手
    for artist_dir in artist_dirs:
        process_artist_dir(artist_dir, client, dry_run=dry_run)

    # 计算耗时
    duration = time.time() - start_time

    # 输出控制台统计
    print('\n' + '=' * 60)
    print('统计结果:')
    print(f'  总文件数: {stats["total"]}')
    print(f'  ✓ 成功: {stats["success"]}')
    print(f'  ⏭  跳过: {stats["skipped"]}')
    print(f'  ✗ 失败: {stats["failed"]}')
    print(f'  ⚠️ 文件损坏: {stats["corrupted"]}')
    print(f'  ?  文件不存在: {stats["not_found"]}')
    print(f'  耗时: {duration:.1f} 秒')

    # 生成详细报告
    save_report(dry_run, duration)

    if dry_run:
        print('\n提示: 使用 --apply 参数实际执行修改')
    else:
        print('\n✓ 完成')


if __name__ == '__main__':
    main()
