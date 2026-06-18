"""音乐相关路由"""
from flask import Blueprint, request, jsonify, send_file, Response
from typing import Optional
import logging
import os
import tempfile
import zipfile
import time
import uuid
import json
import threading
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote_plus

from mutagen.id3 import ID3, TIT2, TPE1, TALB, USLT, error as ID3Error
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from services.music_service import music_service
from utils.api_response import APIResponse
from utils.url_parser import parse_url, is_music_url, is_playlist_url, is_album_url

logger = logging.getLogger(__name__)

music_bp = Blueprint('music', __name__)


# ==================== 下载代理（解决 CORS） ====================

EXT_MIME_TYPES = {
    '.mp3': 'audio/mpeg',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.wav': 'audio/wav',
}

# 批量下载任务存储（task_id -> 任务状态）
# 单进程 Flask 足够用，多进程部署需改为 Redis/DB
batch_tasks: dict[str, dict] = {}
batch_tasks_lock = threading.Lock()
BATCH_TASK_TTL = 600  # 任务完成后 10 分钟清理
BATCH_MAX_WORKERS = 6  # 并发下载线程数


def _sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip()


def _get_extension(url: str, fallback: str = '.mp3') -> str:
    """从 URL 后缀推断文件扩展名"""
    url_path = url.split('?')[0].split('#')[0].lower()
    for ext in ['.flac', '.m4a', '.mp4', '.aac', '.mp3', '.ogg', '.wav']:
        if url_path.endswith(ext):
            return ext
    return fallback


def _detect_audio_type(file_path: str) -> Optional[str]:
    """通过文件 magic bytes 检测真实音频类型

    支持检测：FLAC / MP3 / WAV / OGG / M4A(MP4) / APE
    返回: 'flac' / 'mp3' / 'wav' / 'ogg' / 'm4a' / 'ape' / None
    """
    try:
        with open(file_path, 'rb') as f:
            head = f.read(16)
        if len(head) < 4:
            return None

        # FLAC: 'fLaC' (66 4c 61 43)
        if head[:4] == b'fLaC':
            return 'flac'

        # RIFF / WAV: 'RIFF'....'WAVE' (52 49 46 46)
        if head[:4] == b'RIFF' and head[8:12] == b'WAVE':
            return 'wav'

        # OGG: 'OggS' (4f 67 67 53)
        if head[:4] == b'OggS':
            return 'ogg'

        # MP4/M4A: 'ftyp' at offset 4 (66 74 79 70)
        if head[4:8] == b'ftyp':
            return 'm4a'

        # APE: 'APETAGEX' (41 50 45 54 41 47 45 58)
        if head[:8] == b'APETAGEX':
            return 'ape'

        # MP3: ID3v2 头 ('ID3') 或帧同步 0xFFEx/0xFFFx
        if head[:3] == b'ID3':
            return 'mp3'
        if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
            return 'mp3'

        return None
    except Exception:
        return None


def _write_metadata(file_path: str, extension: str, name: str, artist: str, album: str, lyric: str = ''):
    """给音频文件写入 metadata（mp3/flac/m4a）"""
    try:
        if extension == '.mp3':
            try:
                audio = ID3(file_path)
            except ID3Error:
                audio = ID3()
            audio.delall('TIT2')
            audio.delall('TPE1')
            audio.delall('TALB')
            audio.delall('USLT')
            if name: audio.add(TIT2(encoding=3, text=[name]))
            if artist: audio.add(TPE1(encoding=3, text=[artist]))
            if album: audio.add(TALB(encoding=3, text=[album]))
            if lyric: audio.add(USLT(encoding=3, lang='chi', desc='', text=lyric))
            audio.save(file_path)
        elif extension == '.flac':
            audio = FLAC(file_path)
            audio['title'] = name
            audio['artist'] = artist
            audio['album'] = album
            if lyric: audio['lyrics'] = lyric
            audio.save()
        elif extension in ('.m4a', '.mp4'):
            audio = MP4(file_path)
            audio['\xa9nam'] = [name]
            audio['\xa9ART'] = [artist]
            audio['\xa9alb'] = [album]
            if lyric: audio['\xa9lyr'] = [lyric]
            audio.save()
    except Exception as e:
        logger.warning(f"写入 metadata 失败 ({extension}): {e}")


def _safe_remove(path: str):
    """安全删除文件（忽略错误）"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# Flask 请求上下文清理钩子
def _register_temp_file(tmp_path: str):
    """注册临时文件到当前请求，请求结束后会自动清理"""
    from flask import g
    if not hasattr(g, '_temp_files'):
        g._temp_files = set()
    g._temp_files.add(tmp_path)


@music_bp.teardown_request
def _cleanup_temp_files(exception=None):
    """请求结束时清理当前请求注册的临时文件"""
    from flask import g
    if hasattr(g, '_temp_files'):
        for path in list(g._temp_files):
            _safe_remove(path)
        g._temp_files.clear()


def _build_filename(artist: str, name: str, extension: str, filename_format: str = 'song-artist') -> str:
    """根据文件命名格式构造文件名

    filename_format: 'song-artist' (默认) | 'artist-song' | 'song'
    """
    if filename_format == 'artist-song':
        return f"{artist} - {name}{extension}" if artist else f"{name}{extension}"
    elif filename_format == 'song':
        return f"{name}{extension}"
    else:  # 'song-artist'
        return f"{name} - {artist}{extension}" if artist else f"{name}{extension}"


def _build_content_disposition(filename: str) -> str:
    """构造 Content-Disposition 头（兼容 UTF-8 和 ASCII）
    - 主用 filename*=UTF-8''...（现代浏览器都支持，保留中文）
    - 兼容老浏览器用 ASCII fallback（仅保留 ASCII 可打印部分，合并多余空白）
    """
    from urllib.parse import quote
    try:
        filename.encode('ascii')
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        # 分离扩展名
        m = re.search(r'(\.[A-Za-z0-9]+)$', filename)
        ext = m.group(1) if m else ''
        name_no_ext = filename[:m.start()] if m else filename
        # 提取 ASCII 可打印部分
        ascii_part = re.sub(r'[^\x20-\x7e]', '', name_no_ext).strip()
        ascii_part = re.sub(r'\s+', ' ', ascii_part)
        if len(ascii_part) > 80:
            ascii_part = ascii_part[:80]
        ascii_fallback = (ascii_part or 'download') + ext
        quoted = quote(filename, safe="!#$&+-.^_`|~")
        return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quoted}"


@music_bp.route('/download', methods=['GET'])
def download_proxy():
    """代理下载单曲（解决 CORS，可选写入 metadata，临时文件自动清理）

    参数：
      - id: 歌曲 ID
      - quality: 音质（默认 lossless）
      - source: 平台（默认 netease）
      - name: 歌曲名
      - artist: 歌手
      - album: 专辑
      - lrc: 歌词（可选，用于 metadata）
      - filenameFormat: song-artist / artist-song / song（默认 song-artist）
      - writeMetadata: true/false（默认 true）
    """
    song_id = request.args.get('id', '').strip()
    quality = request.args.get('quality', 'lossless').strip()
    source = request.args.get('source', '').strip() or None
    name = request.args.get('name', 'song')
    artist = request.args.get('artist', '')
    album = request.args.get('album', '')
    lyric = request.args.get('lrc', '')
    filename_format = request.args.get('filenameFormat', 'song-artist').strip()
    write_metadata = request.args.get('writeMetadata', 'true').lower() != 'false'

    if not song_id:
        return APIResponse.json_error("缺少歌曲 id 参数", 400)

    try:
        song_info = music_service.get_song_info(song_id, quality, source)
    except Exception as e:
        logger.error(f"获取歌曲信息失败: {e}")
        return APIResponse.json_error(f"获取歌曲信息失败: {str(e)}", 500)

    url = song_info.get('url')
    if not url:
        return APIResponse.json_error("无法获取歌曲下载链接（可能因版权问题不可用）", 404)

    extension = _get_extension(url, fallback=song_info.get('fileType', 'mp3'))
    if not extension.startswith('.'):
        extension = '.' + extension

    # 1. 下载到临时文件
    fd, tmp_path = tempfile.mkstemp(suffix=extension, prefix='wan-music-')
    os.close(fd)
    _register_temp_file(tmp_path)
    try:
        resp = requests.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        # 1.5 下载完成后，用 magic bytes 检测真实文件类型，覆盖可能错误的扩展名
        # （例如网易云 URL 不带后缀，但服务器返回的可能是 FLAC/MP3/M4A 中任一种）
        detected = _detect_audio_type(tmp_path)
        if detected and '.' + detected != extension:
            new_path = os.path.splitext(tmp_path)[0] + '.' + detected
            try:
                os.rename(tmp_path, new_path)
                tmp_path = new_path
                extension = '.' + detected
            except Exception:
                pass
        mime_type = EXT_MIME_TYPES.get(extension, 'audio/mpeg')

        # 2. 可选写 metadata
        if write_metadata:
            _write_metadata(
                tmp_path, extension,
                name or song_info.get('name', ''),
                artist or song_info.get('artists', ''),
                album or song_info.get('album', ''),
                lyric or song_info.get('lyric', '')
            )

        # 3. 发送文件：先读取文件到内存，再通过 Response 返回
        # 避免 send_file 内部流式读取与文件删除的时序问题
        # 确保 Content-Length 精确匹配实际文件大小
        with open(tmp_path, 'rb') as f:
            file_data = f.read()
        file_size = len(file_data)
        logger.info(f"下载到临时文件 {tmp_path} 完成，大小: {file_size} bytes")

        safe_name = _sanitize_filename(
            _build_filename(artist or song_info.get('artists', ''),
                            name or song_info.get('name', 'song'),
                            extension, filename_format)
        )
        logger.info(f"准备发送: filename={safe_name}, size={file_size}")

        # 实际音质推断（用于前端显示真实下载到的音质）
        # magic bytes 检测结果 + URL 主机名 + quality 关系
        actual_quality = quality
        if detected == 'flac' or detected == 'ape':
            actual_quality = 'lossless'
        elif detected == 'mp3':
            # 区分 320k / 128k（通过 m801/m701 主机名）
            url_host = (url or '').lower()
            logger.info(f"音质推断: detected={detected}, url_host={url_host[:80]}")
            if 'm801' in url_host or 'm802' in url_host or 'm803' in url_host:
                actual_quality = 'exhigh'  # 320k MP3
            else:
                actual_quality = 'standard'  # 128k MP3
        elif detected == 'm4a':
            # 网易云 M4A 通常 256k
            actual_quality = 'exhigh'
        # 告诉前端实际拿到的音质（user 可能选了 lossless 但实际只能下到 320k）
        downgraded = (actual_quality != quality)

        return Response(file_data, status=200, headers={
            'Content-Type': mime_type,
            'Content-Disposition': _build_content_disposition(safe_name),
            'Content-Length': str(file_size),
            'Accept-Ranges': 'none',
            'X-Actual-Quality': actual_quality,
            'X-Quality-Downgraded': '1' if downgraded else '0',
            'X-Actual-FileType': detected or extension.lstrip('.'),
        })
    except Exception as e:
        _safe_remove(tmp_path)
        logger.error(f"下载失败: {e}")
        return APIResponse.json_error(f"下载失败: {str(e)}", 500)


# ==================== 批量下载（异步任务 + SSE 进度） ====================

def _process_song(item: dict, settings: dict) -> dict | None:
    """处理单首歌曲：下载音频 + 写 metadata + 返回结果

    settings: {
      writeMetadata, filenameFormat, downloadLrcFile
    }
    返回：{ 'tmp_path', 'arcname', 'lrc_content', 'name' } 或 None
    """
    song_id = item.get('id')
    if not song_id:
        return None

    quality = item.get('quality', 'lossless')
    source = item.get('source', '').strip() or None
    name = item.get('name', 'song')
    artist = item.get('artist', '')
    album = item.get('album', '')

    last_error = None
    for attempt in range(3):
        try:
            song_info = music_service.get_song_info(song_id, quality, source)
            url = song_info.get('url')
            if not url:
                return None

            extension = _get_extension(url, fallback=song_info.get('fileType', 'mp3'))
            if not extension.startswith('.'):
                extension = '.' + extension

            fd, tmp_path = tempfile.mkstemp(suffix=extension, prefix='wan-music-batch-')
            os.close(fd)

            try:
                resp = requests.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
                resp.raise_for_status()
                with open(tmp_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
            except Exception as e:
                _safe_remove(tmp_path)
                raise e

            # 下载完成后用 magic bytes 检测真实类型，覆盖错误扩展名
            detected = _detect_audio_type(tmp_path)
            if detected and '.' + detected != extension:
                new_path = os.path.splitext(tmp_path)[0] + '.' + detected
                try:
                    os.rename(tmp_path, new_path)
                    tmp_path = new_path
                    extension = '.' + detected
                except Exception:
                    pass

            # 写 metadata
            lyric = song_info.get('lyric', '') or ''
            if settings.get('writeMetadata', True):
                _write_metadata(
                    tmp_path, extension,
                    name or song_info.get('name', ''),
                    artist or song_info.get('artists', ''),
                    album or song_info.get('album', ''),
                    lyric
                )

            arcname = _sanitize_filename(
                _build_filename(artist or song_info.get('artists', ''),
                                name or song_info.get('name', 'song'),
                                extension,
                                settings.get('filenameFormat', 'song-artist'))
            )

            result = {
                'tmp_path': tmp_path,
                'arcname': arcname,
                'lrc_content': None,
                'name': name
            }

            # 可选：下载 LRC 歌词文件
            if settings.get('downloadLrcFile', False) and lyric:
                result['lrc_content'] = lyric

            return result
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))

    logger.warning(f"批量下载: 重试 3 次仍失败 [{song_id}]: {last_error}")
    return None


def _run_batch_task(task_id: str, items: list, zip_name: str, settings: dict):
    """后台批量下载任务（Phase 1 并发下载 → Phase 2 单线程打包）"""
    with batch_tasks_lock:
        task = batch_tasks.get(task_id)
    if not task:
        return

    # Phase 1: 并发下载到临时目录（BATCH_MAX_WORKERS 线程）
    completed_results: list[dict] = []
    failed_items: list[dict] = []

    with ThreadPoolExecutor(max_workers=BATCH_MAX_WORKERS) as executor:
        future_to_item = {executor.submit(_process_song, item, settings): item for item in items}
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                result = future.result()
                if result:
                    completed_results.append(result)
                else:
                    failed_items.append({
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'reason': '无法获取下载链接（可能因版权问题）'
                    })
            except Exception as e:
                failed_items.append({
                    'id': item.get('id'),
                    'name': item.get('name', ''),
                    'reason': str(e)
                })

            with batch_tasks_lock:
                task['completed'] = len(completed_results)
                task['failed'] = len(failed_items)
                task['current'] = item.get('name', '')

    # Phase 2: 单线程打包到磁盘 zip
    fd, zip_path = tempfile.mkstemp(suffix='.zip', prefix='wan-music-batch-')
    os.close(fd)

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for result in completed_results:
                # 1. 写入音频文件
                zf.write(result['tmp_path'], result['arcname'])

                # 2. 可选：写入 LRC 歌词文件
                if result.get('lrc_content'):
                    lrc_name = result['arcname'].rsplit('.', 1)[0] + '.lrc'
                    zf.writestr(lrc_name, result['lrc_content'])

        with batch_tasks_lock:
            task['status'] = 'done'
            task['zip_path'] = zip_path
            task['errors'] = failed_items

        # 启动延迟清理（10 分钟未下载则清理）
        def _cleanup_task():
            with batch_tasks_lock:
                t = batch_tasks.pop(task_id, None)
            if t:
                _safe_remove(t.get('zip_path', ''))

        timer = threading.Timer(BATCH_TASK_TTL, _cleanup_task)
        timer.daemon = True
        timer.start()
    except Exception as e:
        _safe_remove(zip_path)
        for r in completed_results:
            _safe_remove(r['tmp_path'])
        with batch_tasks_lock:
            task['status'] = 'error'
            task['error'] = str(e)


@music_bp.route('/download/batch/start', methods=['POST'])
def download_batch_start():
    """启动批量下载任务（异步处理，立即返回 task_id）

    请求体：
      {
        "items": [{"id", "quality", "source", "name", "artist", "album"}, ...],
        "name": "歌单名",
        "settings": {
          "writeMetadata": true,
          "filenameFormat": "song-artist",
          "downloadLrcFile": false
        }
      }
    """
    data = request.get_json(silent=True) or {}
    items = data.get('items', [])
    zip_name = _sanitize_filename(data.get('name', 'playlist') or 'playlist')
    settings = data.get('settings', {})

    if not items:
        return jsonify(APIResponse.error("缺少 items 参数", 400))

    task_id = f"task_{uuid.uuid4().hex[:16]}"
    with batch_tasks_lock:
        batch_tasks[task_id] = {
            'status': 'running',
            'total': len(items),
            'completed': 0,
            'failed': 0,
            'current': '',
            'zip_path': None,
            'zip_name': zip_name,
            'errors': []
        }

    thread = threading.Thread(target=_run_batch_task, args=(task_id, items, zip_name, settings))
    thread.daemon = True
    thread.start()

    return jsonify(APIResponse.success({'task_id': task_id, 'total': len(items)}, "任务已启动"))


@music_bp.route('/download/batch/progress/<task_id>', methods=['GET'])
def download_batch_progress(task_id):
    """SSE 实时进度推送

    事件流（每 0.3s 推一次）：
      data: {"status":"running","total":38,"completed":15,"failed":1,"current":"歌名"}
      data: {"status":"done","completed":35,"failed":3,"errors":[...]}
    """
    def generate():
        last_data = None
        while True:
            with batch_tasks_lock:
                task = batch_tasks.get(task_id)

            if not task:
                yield f"data: {json.dumps({'error': '任务不存在或已过期'})}\n\n"
                break

            data = {
                'status': task['status'],
                'total': task['total'],
                'completed': task['completed'],
                'failed': task['failed'],
                'current': task['current']
            }

            if task['status'] == 'done':
                data['errors'] = task.get('errors', [])
                yield f"data: {json.dumps(data)}\n\n"
                break
            elif task['status'] == 'error':
                data['error'] = task.get('error', '未知错误')
                yield f"data: {json.dumps(data)}\n\n"
                break
            else:
                data_str = json.dumps(data, sort_keys=True)
                if data_str != last_data:
                    yield f"data: {data_str}\n\n"
                    last_data = data_str
                time.sleep(0.3)

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # 禁用 nginx 缓冲
    return response


@music_bp.route('/download/batch/file/<task_id>', methods=['GET'])
def download_batch_file(task_id):
    """下载已打包好的 zip 文件"""
    with batch_tasks_lock:
        task = batch_tasks.get(task_id)

    if not task:
        return jsonify(APIResponse.error("任务不存在或已过期", 404))
    if task['status'] != 'done':
        return jsonify(APIResponse.error("任务未完成", 400))

    zip_path = task.get('zip_path')
    if not zip_path or not os.path.exists(zip_path):
        return jsonify(APIResponse.error("文件不存在", 404))

    response = send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"{task.get('zip_name', 'playlist')}.zip"
    )

    # 响应关闭后清理
    def cleanup():
        with batch_tasks_lock:
            t = batch_tasks.pop(task_id, None)
        if t:
            _safe_remove(t.get('zip_path', ''))

    response.call_on_close(cleanup)
    return response


@music_bp.route('/download/batch/status/<task_id>', methods=['GET'])
def download_batch_status(task_id):
    """查询任务状态（一次性查询，不订阅 SSE）"""
    with batch_tasks_lock:
        task = batch_tasks.get(task_id)
    if not task:
        return jsonify(APIResponse.error("任务不存在或已过期", 404))
    return jsonify(APIResponse.success({
        'status': task['status'],
        'total': task['total'],
        'completed': task['completed'],
        'failed': task['failed'],
        'current': task['current']
    }, "查询成功"))


@music_bp.route('/parse/url', methods=['POST'])
def parse_url_endpoint():
    """
    解析 URL，返回平台、类型和资源 ID

    请求体（application/x-www-form-urlencoded）：
        url: 要解析的链接

    响应：
        {
            'platform': 'netease' | 'qq' | 'kugou' | 'bodian',
            'type': 'music' | 'playlist' | 'album',
            'id': '资源 ID'
        }
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        url = params.get('url', '')
        if not url:
            return jsonify(APIResponse.error("请提供 URL", 400))

        parsed = parse_url(url)
        if not parsed:
            return jsonify(APIResponse.error("无法识别的 URL", 400))

        return jsonify(APIResponse.success(parsed, "解析成功"))
    except Exception as e:
        logger.error(f"URL 解析异常: {e}")
        return jsonify(APIResponse.error(f"服务器错误: {str(e)}", 500))


@music_bp.route('/parse/validate', methods=['POST'])
def validate_url_endpoint():
    """
    验证 URL 类型

    请求体：
        url: 要验证的链接

    响应：
        {
            'type': 'music' | 'playlist' | 'album' | null,
            'isMusic': true/false,
            'isPlaylist': true/false,
            'isAlbum': true/false
        }
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        url = params.get('url', '')
        parsed = parse_url(url)
        url_type = parsed['type'] if parsed else None

        return jsonify(APIResponse.success({
            'type': url_type,
            'isMusic': url_type == 'music',
            'isPlaylist': url_type == 'playlist',
            'isAlbum': url_type == 'album',
        }, "验证成功"))
    except Exception as e:
        logger.error(f"URL 验证异常: {e}")
        return jsonify(APIResponse.error(f"服务器错误: {str(e)}", 500))


@music_bp.route('/song', methods=['POST'])
def get_song_info():
    """获取歌曲信息（支持多种类型：url/name/lyric/json）

    支持以下参数（任选其一）：
        - url: 完整的歌曲链接（推荐，由后端解析）
        - ids 或 id: 歌曲 ID（需配合 source 使用）
        - source: 平台（netease/qq/kugou/bodian），不传则从 URL 推断
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        # 优先使用 url 参数（推荐）
        url = params.get('url', '')
        ids = params.get('ids', '')
        music_id = ids.split(',')[0] if ids else params.get('id', '')
        source = params.get('source', '')

        # 如果传入了 url，则在后端解析
        if url and not music_id:
            parsed = parse_url(url)
            if parsed:
                music_id = parsed['id']
                if not source:
                    source = parsed['platform']

        # 兜底：尝试从 ID 格式判断平台
        if not source and music_id and not music_id.isdigit():
            source = 'qq'

        if not music_id:
            # 区分"没有提供任何参数"和"URL 解析失败"两种情况，给出更具体的错误信息
            if url:
                return jsonify(APIResponse.error("无法识别此歌曲链接，请检查格式", 400))
            return jsonify(APIResponse.error("请提供歌曲链接或 ID", 400))

        info_type = params.get('type', 'json')
        level = params.get('level', 'lossless')

        logger.info(f"[DEBUG] /song 请求: music_id={music_id}, source={source}, type={info_type}, level={level}")
        
        if info_type == 'url':
            result = music_service.get_song_url(music_id, level, source)
            if result and result.get('data') and len(result['data']) > 0:
                song_data = result['data'][0]
                if song_data.get('url'):
                    response_data = {
                        'id': song_data.get('id'),
                        'url': song_data.get('url'),
                        'level': song_data.get('level', level),
                        'type': song_data.get('type', 'mp3'),
                        'source': song_data.get('source', source or 'netease')
                    }
                    return jsonify(APIResponse.success(response_data, "获取歌曲URL成功"))
                else:
                    return jsonify(APIResponse.error("该歌曲因版权限制无法获取播放链接", 403))
            else:
                return jsonify(APIResponse.error("获取音乐URL失败，可能是版权限制或音质不支持", 404))
        
        elif info_type == 'name':
            result = music_service.get_song_detail(music_id, source)
            return jsonify(APIResponse.success(result, "获取歌曲信息成功"))
        
        elif info_type == 'lyric':
            lyric = music_service.get_lyric(music_id, source)
            return jsonify(APIResponse.success({'lyric': lyric}, "获取歌词成功"))
        
        elif info_type == 'json':
            song_info = music_service.get_song_info(music_id, level, source)
            if not song_info:
                logger.info(f"[DEBUG] /song 返回空结果: music_id={music_id}, source={source}, song_info={song_info}")
                return jsonify(APIResponse.error("未找到歌曲信息", 404))
            
            response_data = {
                'id': music_id,
                'name': song_info.get('name', ''),
                'ar_name': song_info.get('artists', ''),
                'al_name': song_info.get('album', ''),
                'pic': song_info.get('picUrl', ''),
                'level': level,
                'source': song_info.get('source', source or 'netease'),
                'lyric': song_info.get('lyric', ''),
                'tlyric': '',
                'fileType': song_info.get('fileType', 'mp3')  # 文件类型（mp3/flac等）
            }
            
            if song_info.get('url'):
                response_data['url'] = song_info['url']
            else:
                response_data['url'] = ''
                response_data['size'] = '获取失败'
            
            return jsonify(APIResponse.success(response_data, "获取歌曲信息成功"))
        
        else:
            return jsonify(APIResponse.error(f"不支持的类型: {info_type}", 400))
    
    except Exception as e:
        if "所有数据源均无法获取" in str(e):
            return jsonify(APIResponse.error("该歌曲因版权限制无法获取播放链接", 403))
        logger.error(f"获取歌曲信息异常: {e}")
        return jsonify(APIResponse.error(f"服务器错误: {str(e)}", 500))


@music_bp.route('/playlist', methods=['POST'])
def get_playlist():
    """获取歌单详情

    支持以下参数（任选其一）：
        - url: 完整的歌单链接（推荐，由后端解析）
        - id: 歌单 ID（需配合 source 使用）
        - source: 平台（netease/qq/kugou/bodian），不传则从 URL 推断
    """
    try:
        data = request.get_data(as_text=True)
        params = {}
        for pair in data.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[unquote_plus(key)] = unquote_plus(value)

        url = params.get('url', '')
        playlist_id = params.get('id', '')
        source = params.get('source', '')

        # 优先使用 url 参数（推荐）
        if url and not playlist_id:
            parsed = parse_url(url)
            if parsed:
                playlist_id = parsed['id']
                if not source:
                    source = parsed['platform']

        if not source and playlist_id and not playlist_id.isdigit():
            source = 'qq'

        if not playlist_id:
            return jsonify(APIResponse.error("请提供歌单链接或 ID", 400))

        result = music_service.get_playlist_detail(playlist_id, source)

        return jsonify(APIResponse.success({'playlist': result}, "获取歌单成功"))
    except Exception as e:
        logger.error(f"获取歌单失败: {e}")
        return jsonify(APIResponse.error(f"获取歌单失败: {str(e)}", 500))


@music_bp.route('/api/data-sources', methods=['GET'])
def get_data_sources():
    """获取可用数据源列表"""
    try:
        platforms = music_service.get_platforms()
        return jsonify(APIResponse.success(platforms, "获取数据源列表成功"))
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}")
        return jsonify(APIResponse.error(f"获取数据源列表失败: {str(e)}", 500))


# ==================== 网易云 Cookie 状态 ====================

@music_bp.route('/api/netease/cookie/status', methods=['GET'])
def get_netease_cookie_status():
    """查看当前网易云 cookie 状态（不返回具体值，不写文件）

    每次调用都会**检查文件 mtime**，如果文件被修改会自动 reload 到 session。
    """
    from clients.netease_client import APIConstants
    import os
    try:
        # 候选路径（与 netease_client._load_local_cookies 保持一致）
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'clients', 'cookie', 'netease_cookie.txt'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookie', 'netease_cookie.txt'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'netease_cookie.txt'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookie.txt'),
        ]
        active_path = next((c for c in candidates if os.path.exists(c)), None)
        from clients.music_client import music_client
        netease = music_client._get_client('netease') if hasattr(music_client, '_get_client') else None
        cookies = dict(netease.session.cookies) if netease else {}

        # 自动 reload：如果文件 mtime 比上次加载新，就重新加载
        if active_path and netease and hasattr(netease, '_last_cookie_mtime'):
            current_mtime = os.path.getmtime(active_path)
            if current_mtime > netease._last_cookie_mtime:
                logger.info(f"检测到 cookie 文件已修改，自动 reload...")
                netease.reload_cookies()
                cookies = dict(netease.session.cookies)

        has_music_u = 'MUSIC_U' in cookies
        return jsonify(APIResponse.success({
            'active_path': active_path,
            'candidates': candidates,
            'file_exists': active_path is not None,
            'cookie_keys': list(cookies.keys()),
            'has_music_u': has_music_u,
            'is_vip': has_music_u,
            'cookie_count': len(cookies)
        }, "Cookie 状态查询成功"))
    except Exception as e:
        return jsonify(APIResponse.error(f"查询失败: {str(e)}", 500))
