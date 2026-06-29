"""所有 HTTP 路由（仅做请求/响应包装，业务逻辑在 service.py）"""
from flask import Blueprint, request, jsonify, send_file, Response
from typing import Optional
import json
import logging
import os
import time

from service import music_service, batch_download_service
from app_config import get_full_config
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
    """从请求体里提取 (music_id, source, url)"""
    url = (payload.get('url') or '').strip() or None
    ids = (payload.get('ids') or '').strip()
    music_id = ids.split(',')[0] if ids else (payload.get('id') or '').strip() or None
    source = (payload.get('source') or '').strip() or None

    if url and not music_id:
        parsed = parse_url(url)
        if parsed and parsed.get('type') == 'music':
            music_id = parsed['id']
            if not source:
                source = parsed['platform']

    if not source and music_id and not music_id.isdigit():
        source = 'qq'

    return music_id, source, url


def _infer_file_type(url: str) -> str:
    """从 URL 推断文件类型：flac > m4a > mp3

    用于 fileType 字段，前端可基于此选择解码器（FLAC 需 hifi 解码）
    """
    if not url:
        return 'mp3'
    url_lower = url.lower()
    if '.flac' in url_lower:
        return 'flac'
    if '.m4a' in url_lower or '.mp4' in url_lower:
        return 'm4a'
    if '.ogg' in url_lower or '.oga' in url_lower:
        return 'ogg'
    if '.wav' in url_lower:
        return 'wav'
    return 'mp3'


# ==================== 核心业务接口 ====================

@music_bp.route('/search', methods=['POST'])
def search():
    """搜索接口

    接受参数：
      - keyword: 搜索内容（关键词或 URL）
      - source: 数据源（netease/qq/kugou/kuwo）
      - limit: 返回数量（默认 50）
    """
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        platform = data.get('source')
        limit = data.get('limit', 50)

        logger.info(f"[搜索请求] keyword={keyword!r}, source={platform}, limit={limit}")

        if not keyword:
            return jsonify(APIResponse.error("请输入搜索关键词", 400))

        result = music_service.search(keyword, platform, limit)
        logger.info(f"[搜索结果] 结果数量={len(result.get('data', []))}")
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
        - source: 平台（netease/qq/kugou/kuwo），不传则从 URL 推断
        - level: 音质，默认 lossless
        - qualityMap: 该歌曲可用音质字典（可选，传入后降级更精准）
    """
    payload = request.get_json(silent=True) or request.form.to_dict()
    music_id, source, url = _resolve_song_ref(payload)
    level = (payload.get('level') or 'lossless').strip() or 'lossless'

    # 解析 qualityMap：允许 dict 或 JSON 字符串
    quality_map = payload.get('qualityMap')
    if isinstance(quality_map, str) and quality_map:
        try:
            quality_map = json.loads(quality_map)
        except (ValueError, TypeError):
            quality_map = None
    if not isinstance(quality_map, dict):
        quality_map = None

    if not music_id:
        if url:
            return jsonify(APIResponse.error("无法识别此歌曲链接，请检查格式", 400))
        return jsonify(APIResponse.error("请提供歌曲链接或 ID", 400))

    logger.info(
        f"/song 请求: music_id={music_id}, source={source}, level={level}, "
        f"qualityMap={'yes' if quality_map else 'no'}"
    )

    try:
        song_info = music_service.get_song_info(music_id, level, source, quality_map=quality_map)
    except Exception as e:
        logger.error(f"/song 获取歌曲信息失败: {e}")
        return jsonify(APIResponse.error(f"获取歌曲信息失败: {str(e)}", 500))

    if not song_info or not song_info.get('id') or not song_info.get('url'):
        return jsonify(APIResponse.error("未找到歌曲信息", 404))

    actual_level = song_info.get('level', level)
    return jsonify(APIResponse.success({
        'id': music_id,
        'name': song_info.get('name', ''),
        'artist': song_info.get('artists', ''),
        'album': song_info.get('album', ''),
        'cover': song_info.get('picUrl', ''),
        'duration': song_info.get('duration', 0),
        'url': song_info.get('url', ''),
        'level': actual_level,                                 # 实际获取的音质
        'requested_level': level,                              # 用户请求的音质
        'level_fallback': bool(song_info.get('level_fallback', False)),  # 是否降级
        'fileType': song_info.get('fileType') or _infer_file_type(song_info.get('url', '')),
        'source': song_info.get('source', source or 'netease'),
        'api_source': song_info.get('api_source', ''),
        'available': True,
        'lyric': song_info.get('lyric', '') or '',
    }, "获取歌曲信息成功"))


@music_bp.route('/platforms', methods=['GET'])
def get_platforms():
    """获取支持的音乐平台列表（向后兼容，推荐使用 /config）"""
    return jsonify(APIResponse.success(music_service.get_platforms(), "获取平台列表成功"))


@music_bp.route('/config', methods=['GET'])
def get_config():
    """获取前端所需的全部配置（平台 / 音质 / 命名格式 / 平台-音质映射）

    前端应在启动时拉取并缓存 24 小时。配置统一在后端维护。
    """
    return jsonify(APIResponse.success(get_full_config(), "获取配置成功"))


# ==================== 图片代理 ====================

# 白名单：仅代理已知音乐平台的图片域名
_ALLOWED_IMAGE_HOSTS = (
    'img4.kuwo.cn', 'img3.kuwo.cn', 'img2.kuwo.cn', 'img1.kuwo.cn',
    'y.gtimg.cn',
    'imge.kugou.com',
    'p1.music.126.net', 'p2.music.126.net', 'p3.music.126.net', 'p4.music.126.net',
    'music.126.net',
)
# 1×1 透明 PNG（fallback）
_FALLBACK_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


@music_bp.route('/image', methods=['GET'])
def proxy_image():
    """代理外部音乐平台图片，避免跨域 ORB 阻断（Chrome 108+）"""
    from urllib.parse import urlparse
    import requests as _requests

    url = request.args.get('url', '').strip()
    if not url:
        return Response(_FALLBACK_PNG, mimetype='image/png', status=200)

    try:
        parsed = urlparse(url)
    except Exception:
        return Response(_FALLBACK_PNG, mimetype='image/png', status=200)

    if parsed.scheme not in ('http', 'https') or parsed.netloc not in _ALLOWED_IMAGE_HOSTS:
        logger.warning(f'proxy_image: blocked host {parsed.netloc}')
        return Response(_FALLBACK_PNG, mimetype='image/png', status=200)

    try:
        r = _requests.get(
            url, timeout=10, stream=True,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://www.kuwo.cn/' if 'kuwo' in parsed.netloc else
                           'https://y.qq.com/' if 'qq' in parsed.netloc else
                           'https://www.kugou.com/' if 'kugou' in parsed.netloc else
                           'https://music.163.com/',
            },
        )
        content_type = r.headers.get('Content-Type', '').lower()
        # 仅放行图片
        if not content_type.startswith('image/') or r.status_code != 200:
            return Response(_FALLBACK_PNG, mimetype='image/png', status=200)
        return Response(r.content, mimetype=content_type, status=200)
    except Exception as e:
        logger.debug(f'proxy_image: {url} failed: {e}')
        return Response(_FALLBACK_PNG, mimetype='image/png', status=200)


# ==================== 批量下载接口 ====================

@music_bp.route('/download/batch/start', methods=['POST'])
def download_batch_start():
    """启动批量下载任务（异步处理，立即返回 task_id）"""
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
    """列出所有批量下载任务"""
    items = batch_download_service.get_list()
    return jsonify(APIResponse.success(items, "查询成功"))


@music_bp.route('/download/batch/<task_id>', methods=['DELETE'])
def download_batch_delete(task_id):
    """取消/删除批量下载任务"""
    result = batch_download_service.cancel(task_id)
    if result is None:
        return jsonify(APIResponse.error("任务不存在或已过期", 404))
    return jsonify(APIResponse.success(result, "任务已取消"))


@music_bp.route('/download/batch/progress/<task_id>', methods=['GET'])
def download_batch_progress(task_id):
    """SSE 实时进度推送"""
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
                'file_size': state['file_size'],
                'songs': state.get('songs', []),   # per-song 状态
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

    # 根据 Accept header 决定返回 SSE 还是 JSON：
    # - EventSource 发送 Accept: text/event-stream → 返 SSE 流（用于浏览器原生 EventSource）
    # - fetch 发送 Accept: */* 或 application/json → 返 JSON（轮询场景）
    # 这样同一路由同时支持 SSE 和轮询两种客户端
    accept = request.headers.get('Accept', '')
    if 'text/event-stream' in accept:
        # SSE 模式
        response = Response(generate(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response
    else:
        # JSON 模式（轮询）：返回单次快照
        state = batch_download_service.get_state(task_id)
        if state is None:
            return jsonify(APIResponse.error("任务不存在或已过期", 404))
        data = {
            'status': state['status'],
            'total': state['total'],
            'completed': state['completed'],
            'failed': state['failed'],
            'current': state['current'],
            'file_size': state['file_size'],
            'songs': state.get('songs', []),
        }
        if state['status'] == 'done':
            data['errors'] = state['errors']
        elif state['status'] == 'error':
            data['error'] = state.get('error', '未知错误')
        return jsonify(APIResponse.success(data))


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
        download_name = info['name'] or 'song'
        response = send_file(
            info['path'],
            mimetype=info['mime_type'],
            as_attachment=True,
            download_name=download_name
        )
    else:
        response = send_file(
            info['path'],
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{info['name']}.zip"
        )

    response.call_on_close(lambda: batch_download_service.cleanup(task_id))
    return response
