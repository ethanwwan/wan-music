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
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.music_service import music_service
from utils.api_response import APIResponse
from utils.url_parser import parse_url
from utils.filename import (
    sanitize_filename as _sanitize_filename,
    build_filename as _build_filename,
    build_content_disposition as _build_content_disposition,
)
from utils.audio_utils import (
    get_extension as _get_extension,
    detect_audio_type as _detect_audio_type,
    detect_mp3_bitrate as _detect_mp3_bitrate,
    safe_remove as _safe_remove,
)
from utils.metadata import write_metadata as _write_metadata

logger = logging.getLogger(__name__)

music_bp = Blueprint('music', __name__)


# ==================== 批量下载（异步任务 + SSE 进度） ====================

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


# ==================== 批量下载（异步任务 + SSE 进度） ====================

def _process_song(item: dict, settings: dict) -> Optional[dict]:
    """处理单首歌曲：下载音频 + 写 metadata + 返回结果

    settings: {
      writeMetadata, filenameFormat
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
                    lyric,
                    song_info.get('picUrl', ''),
                    platform=song_info.get('source', source or ''),
                    song_id=song_info.get('id', song_id)
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

            return result
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))

    logger.warning(f"批量下载: 重试 3 次仍失败 [{song_id}]: {last_error}")
    return None


def _run_batch_task(task_id: str, items: list, zip_name: str, settings: dict):
    """后台批量下载任务（Phase 1 并发下载 → Phase 2 单线程打包）

    支持取消：通过设置 task['cancelled'] = True 触发取消
    """
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
            # 检查是否被取消
            with batch_tasks_lock:
                if task.get('cancelled'):
                    # 取消未开始的 future
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

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
                if task.get('cancelled'):
                    break
                task['completed'] = len(completed_results)
                task['failed'] = len(failed_items)
                task['current'] = item.get('name', '')

    # 检查是否被取消
    with batch_tasks_lock:
        if task.get('cancelled'):
            task['status'] = 'cancelled'
            # 清理已下载的临时文件
            for r in completed_results:
                _safe_remove(r.get('tmp_path', ''))
            return

    # Phase 2: 单曲直接保留，多首打包 zip
    try:
        if len(completed_results) == 1:
            # 单曲：直接使用已下载的文件，不需要 ZIP
            result = completed_results[0]
            final_path = result['tmp_path']
            # 重命名为带正确扩展名的文件
            final_name = result['arcname']
            with batch_tasks_lock:
                task['status'] = 'done'
                task['zip_path'] = final_path
                task['zip_name'] = final_name
                task['single_file'] = True
                task['errors'] = failed_items
                task['completed_at'] = time.time()
        else:
            # 多首：打包 ZIP
            fd, zip_path = tempfile.mkstemp(suffix='.zip', prefix='wan-music-batch-')
            os.close(fd)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for result in completed_results:
                    zf.write(result['tmp_path'], result['arcname'])

            with batch_tasks_lock:
                task['status'] = 'done'
                task['zip_path'] = zip_path
                task['errors'] = failed_items
                task['completed_at'] = time.time()

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
        "items": [{"id", "quality", "source", "name", "artist", "album", "qualityMap"}, ...],
        "name": "歌单名",
        "settings": {
          "writeMetadata": true,
          "filenameFormat": "song-artist"
        }
      }
    """
    data = request.get_json(silent=True) or {}
    items = data.get('items', [])
    zip_name = _sanitize_filename(data.get('name', 'playlist') or 'playlist')
    settings = data.get('settings', {})

    if not items:
        return jsonify(APIResponse.error("缺少 items 参数", 400))

    # 从 qualityMap 估算总文件大小
    estimated_file_size = 0
    for item in items:
        qm = item.get('qualityMap') or {}
        quality = item.get('quality', 'lossless')
        if quality in qm:
            estimated_file_size += qm[quality].get('size', 0)

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
            'errors': [],
            'cancelled': False,
            'created_at': time.time(),
            'completed_at': 0,
            'file_size': estimated_file_size,
        }

    thread = threading.Thread(target=_run_batch_task, args=(task_id, items, zip_name, settings))
    thread.daemon = True
    thread.start()

    return jsonify(APIResponse.success({'task_id': task_id, 'total': len(items), 'file_size': estimated_file_size}, "任务已启动"))


def _task_to_dict(task_id: str, task: dict) -> dict:
    """将内部任务状态转换为对外暴露的字典（不包含 zip_path 等敏感字段）"""
    return {
        'task_id': task_id,
        'status': task['status'],
        'name': task.get('zip_name', ''),
        'total': task['total'],
        'completed': task['completed'],
        'failed': task['failed'],
        'current': task.get('current', ''),
        'errors': task.get('errors', []),
        'error': task.get('error', ''),
        'created_at': task.get('created_at', 0),
        'completed_at': task.get('completed_at', 0),
        'single_file': task.get('single_file', False),
        'file_size': task.get('file_size', 0),
    }


@music_bp.route('/download/batch/list', methods=['GET'])
def download_batch_list():
    """列出所有批量下载任务（用于前端恢复/同步）

    返回按创建时间倒序的任务列表
    """
    with batch_tasks_lock:
        items = [
            _task_to_dict(tid, t)
            for tid, t in batch_tasks.items()
        ]

    # 倒序：最新的在前
    items.sort(key=lambda x: x.get('created_at', 0), reverse=True)
    return jsonify(APIResponse.success(items, "查询成功"))


@music_bp.route('/download/batch/<task_id>', methods=['DELETE'])
def download_batch_delete(task_id):
    """取消/删除批量下载任务

    - 任务进行中：标记 cancelled，清理已下载文件
    - 任务已完成：清理 zip 文件
    """
    with batch_tasks_lock:
        task = batch_tasks.get(task_id)

    if not task:
        return jsonify(APIResponse.error("任务不存在或已过期", 404))

    # 标记取消
    with batch_tasks_lock:
        task['cancelled'] = True
        status = task['status']
        zip_path = task.get('zip_path')

    # 同步清理 zip 文件
    if zip_path and os.path.exists(zip_path):
        _safe_remove(zip_path)

    # 等待短暂时间让后台线程检测到取消（如果还在运行）
    # 不阻塞响应，最多等 0.5s
    if status == 'running':
        time.sleep(0.3)

    # 从字典中移除
    with batch_tasks_lock:
        batch_tasks.pop(task_id, None)

    return jsonify(APIResponse.success({'task_id': task_id, 'previous_status': status}, "任务已取消"))


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
                'current': task['current'],
                'file_size': task.get('file_size', 0)
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

    is_single = task.get('single_file', False)
    if is_single:
        # 单曲：直接返回音频文件
        ext = os.path.splitext(zip_path)[1]
        mime_type = EXT_MIME_TYPES.get(ext, 'audio/mpeg')
        download_name = task.get('zip_name', 'song' + ext)
        response = send_file(
            zip_path,
            mimetype=mime_type,
            as_attachment=True,
            download_name=download_name
        )
    else:
        # 多首：返回 ZIP
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


def _resolve_song_ref(payload: dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """从请求体里提取 (music_id, source, url) 之一
    - 优先用 url（推荐，url 必传时由后端解析 id + source）
    - 否则用 ids / id + source
    - 兜底：QQ 的 ID 是字母数字混合，其他平台都是纯数字
    """
    url = (payload.get('url') or '').strip() or None
    ids = (payload.get('ids') or '').strip()
    music_id = ids.split(',')[0] if ids else (payload.get('id') or '').strip() or None
    source = (payload.get('source') or '').strip() or None

    if url and not music_id:
        parsed = parse_url(url)
        if parsed:
            music_id = parsed['id']
            if not source:
                source = parsed['platform']

    if not source and music_id and not music_id.isdigit():
        source = 'qq'

    return music_id, source, url


@music_bp.route('/song', methods=['POST'])
def get_song_info():
    """获取歌曲完整信息：基本信息 + 播放/下载地址 + 歌词

    支持传链接（推荐）或传 ID。返回字段统一，前端播放、下载均走此接口。
    后端 /download/batch/start 内部也复用 music_service.get_song_info 拉取同样数据。

    请求体（JSON 或 form）：
        - url: 完整的歌曲链接（由后端解析出 id 和 source）
        - id 或 ids: 歌曲 ID（需配合 source 使用）
        - source: 平台（netease/qq/kugou/bodian），不传则从 URL 推断
        - level: 音质，默认 lossless

    返回：
        {
          id, name, artist, album, cover, duration,
          url, level, fileType, source,
          available: bool,           // false 时因版权无法播放
          lyric: 'LRC 文本'          // 无歌词时为空字符串
        }
    """
    payload = request.get_json(silent=True) or request.form.to_dict()
    music_id, source, url = _resolve_song_ref(payload)
    level = (payload.get('level') or 'lossless').strip() or 'lossless'

    if not music_id:
        if url:
            return jsonify(APIResponse.error("无法识别此歌曲链接，请检查格式", 400))
        return jsonify(APIResponse.error("请提供歌曲链接或 ID", 400))

    logger.info(f"/song 请求: music_id={music_id}, source={source}, level={level}")

    try:
        song_info = music_service.get_song_info(music_id, level, source)
    except Exception as e:
        if "所有数据源均无法获取" in str(e):
            return jsonify(APIResponse.error("该歌曲因版权限制无法获取播放链接", 403))
        logger.error(f"/song 获取歌曲信息失败: {e}")
        return jsonify(APIResponse.error(f"获取歌曲信息失败: {str(e)}", 500))

    if not song_info or not song_info.get('id'):
        return jsonify(APIResponse.error("未找到歌曲信息", 404))

    play_url = song_info.get('url') or ''
    return jsonify(APIResponse.success({
        'id': music_id,
        'name': song_info.get('name', ''),
        'artist': song_info.get('artists', ''),
        'album': song_info.get('album', ''),
        'cover': song_info.get('picUrl', ''),
        'duration': song_info.get('duration', 0),
        'url': play_url,
        'level': level,
        'fileType': song_info.get('fileType', 'mp3'),
        'source': song_info.get('source', source or 'netease'),
        'available': bool(play_url),
        'lyric': song_info.get('lyric', '') or '',
    }, "获取歌曲信息成功"))


@music_bp.route('/playlist', methods=['POST'])
def get_playlist():
    """获取歌单详情

    支持以下参数（任选其一）：
        - url: 完整的歌单链接（推荐，由后端解析）
        - id: 歌单 ID（需配合 source 使用）
        - source: 平台（netease/qq/kugou/bodian），不传则从 URL 推断
    """
    try:
        url = request.form.get('url', '').strip()
        playlist_id = request.form.get('id', '').strip()
        source = request.form.get('source', '').strip()

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
