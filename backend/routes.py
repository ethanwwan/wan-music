"""所有 HTTP 路由（仅做请求/响应包装，业务逻辑在 service.py）"""
from flask import Blueprint, request, jsonify, send_file, Response
from typing import Optional
import json
import logging
import os
import time

from service import music_service, batch_download_service
from utils.url_parser import parse_url
from utils.filename import sanitize_filename as _sanitize_filename

logger = logging.getLogger(__name__)


# ==================== 统一响应 ====================

class APIResponse:
    """统一 API 响应格式"""

    @staticmethod
    def success(data=None, message: str = "操作成功"):
        return {'success': True, 'message': message, 'data': data}

    @staticmethod
    def error(message: str, code: int = 500, data=None):
        return {'success': False, 'message': message, 'code': code, 'data': data}


# ==================== Blueprint ====================

music_bp = Blueprint('music', __name__)


# ==================== 辅助：从请求体解析歌曲引用 ====================

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


# ==================== 核心业务接口 ====================

@music_bp.route('/search', methods=['POST'])
def search():
    """统一搜索接口
    接受参数：
      - keyword: 搜索内容（可以是关键词或 URL）
      - type: 搜索类型（0=全部 / 1=歌曲 / 2=歌单），仅在 keyword 不是 URL 时生效
      - source: 数据源（netease/qq/kugou/bodian/kuwo）
      - quality: 用户选择的音质
      - limit: 返回数量（默认 50）
    """
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        search_type = int(data.get('type', 0))
        platform = data.get('source')
        quality = data.get('quality', 'lossless')
        limit = data.get('limit', 50)

        logger.info(f"[搜索请求] keyword={keyword!r}, type={search_type}, source={platform}, limit={limit}")

        if not keyword:
            return jsonify(APIResponse.error("请输入搜索关键词", 400))

        result = music_service.search(keyword, search_type, platform, limit, quality=quality)

        logger.info(f"[搜索结果] type={result.get('type')}, 结果数量={len(result.get('data', []))}")

        return jsonify(APIResponse.success(result, "搜索成功"))
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return jsonify(APIResponse.error(f"搜索失败: {str(e)}", 500))


@music_bp.route('/song', methods=['POST'])
def get_song_info():
    """获取歌曲完整信息：基本信息 + 播放/下载地址 + 歌词

    请求体（JSON 或 form）：
        - url: 完整的歌曲链接（由后端解析出 id 和 source）
        - id 或 ids: 歌曲 ID（需配合 source 使用）
        - source: 平台（netease/qq/kugou/bodian/kuwo），不传则从 URL 推断
        - level: 音质，默认 lossless
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
        'api_source': song_info.get('api_source', ''),
        'available': bool(play_url),
        'lyric': song_info.get('lyric', '') or '',
    }, "获取歌曲信息成功"))


@music_bp.route('/platforms', methods=['GET'])
def get_platforms():
    """获取支持的音乐平台列表

    平台元数据由 music_client 维护，前端从该接口读取，避免硬编码。
    """
    return jsonify(APIResponse.success(music_service.get_platforms(), "获取平台列表成功"))


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


# ==================== 批量下载接口 ====================

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

    try:
        result = batch_download_service.start(items, zip_name, settings)
    except ValueError as e:
        return jsonify(APIResponse.error(str(e), 400))

    return jsonify(APIResponse.success(result, "任务已启动"))


@music_bp.route('/download/batch/list', methods=['GET'])
def download_batch_list():
    """列出所有批量下载任务（用于前端恢复/同步）

    返回按创建时间倒序的任务列表
    """
    items = batch_download_service.get_list()
    return jsonify(APIResponse.success(items, "查询成功"))


@music_bp.route('/download/batch/<task_id>', methods=['DELETE'])
def download_batch_delete(task_id):
    """取消/删除批量下载任务

    - 任务进行中：标记 cancelled，清理已下载文件
    - 任务已完成：清理 zip 文件
    """
    result = batch_download_service.cancel(task_id)
    if result is None:
        return jsonify(APIResponse.error("任务不存在或已过期", 404))
    return jsonify(APIResponse.success(result, "任务已取消"))


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
            state = batch_download_service.get_state(task_id)

            if state is None:
                yield f"data: {json.dumps({'error': '任务不存在或已过期'})}\n\n"
                break

            data = {
                'status': state['status'],
                'total': state['total'],
                'completed': state['completed'],
                'failed': state['failed'],
                'current': state['current'],
                'file_size': state['file_size']
            }

            if state['status'] == 'done':
                data['errors'] = state['errors']
                yield f"data: {json.dumps(data)}\n\n"
                break
            elif state['status'] == 'error':
                data['error'] = state['error'] or '未知错误'
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
    info = batch_download_service.get_file_info(task_id)

    if info is None:
        return jsonify(APIResponse.error("任务不存在或已过期", 404))
    if info['status'] != 'done':
        return jsonify(APIResponse.error("任务未完成", 400))
    if not info['path'] or not os.path.exists(info['path']):
        return jsonify(APIResponse.error("文件不存在", 404))

    if info['is_single']:
        # 单曲：直接返回音频文件
        download_name = info['name'] or 'song'
        response = send_file(
            info['path'],
            mimetype=info['mime_type'],
            as_attachment=True,
            download_name=download_name
        )
    else:
        # 多首：返回 ZIP
        response = send_file(
            info['path'],
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{info['name']}.zip"
        )

    # 响应关闭后清理
    response.call_on_close(lambda: batch_download_service.cleanup(task_id))
    return response
