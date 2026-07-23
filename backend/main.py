"""Wan Music API 服务主程序

提供多平台音乐搜索、解析、下载 API。

端口优先级：环境变量 PORT > config.json:backend.devBackendPort > 默认 5005
（dev 模式专用，prod 模式由 gunicorn -b CLI 参数硬编码 6005）
"""
import logging
import os
import sys
import time

from flask import Flask, render_template, request, send_from_directory
from flask_cors import CORS

from routes import music_bp
from utils.config import resolve_port
from utils.logging_config import setup_logging, LOG_FILE

# 初始化日志：同时输出到 stderr 和 logs/wan-music.log
setup_logging()

logger = logging.getLogger(__name__)

# 注意：启动日志（日志文件路径、服务地址）在 if __name__ == '__main__' 内打印，
# 同时用 WERKZEUG_RUN_MAIN 避免 debug reloader 双进程重复打印

app = Flask(
    __name__,
    # static_url_path 保持默认 /static；Vite 输出的 /assets/* 和 /favicon.svg 用下面的显式路由转发
    static_folder='static',
    static_url_path='/static',
)
CORS(app)

# 注册 API 蓝图
app.register_blueprint(music_bp)


# ==================== HTTP 请求日志 ====================

# 不打日志的路径（健康检查 + 静态资源 + 图片代理 噪声大）
_QUIET_PATHS = {
    '/health', '/favicon.ico', '/favicon.svg',
    '/image',  # 图片代理：每首歌封面/歌手头像都会触发，刷屏
}


def _extract_request_context(path: str) -> str:
    """提取 API 请求的关键业务参数（不打印完整 URL，避免日志爆炸）

    目的：让 /search /song /lyric /playlist /download 的日志更可读
    格式：path + 关键参数（song_id, keyword, quality, task_id）
    """
    if path == '/search' and request.method == 'POST':
        body = request.get_json(silent=True) or {}
        kw = body.get('keyword', '')[:20]
        src = body.get('source', 'all')
        return f'/search k="{kw}" src={src}'
    if path == '/song' and request.method == 'POST':
        body = request.get_json(silent=True) or {}
        sid = body.get('id', '')[:30]
        src = body.get('source', 'auto')
        q = body.get('quality', '')
        return f'/song id={sid} src={src} q={q}'
    if path == '/lyric' and request.method == 'POST':
        body = request.get_json(silent=True) or {}
        sid = body.get('id', '')[:30]
        src = body.get('source', 'auto')
        return f'/lyric id={sid} src={src}'
    if path == '/playlist' and request.method == 'POST':
        body = request.get_json(silent=True) or {}
        pid = body.get('id', '')[:30]
        src = body.get('source', 'auto')
        return f'/playlist id={pid} src={src}'
    if path == '/download/batch/start':
        body = request.get_json(silent=True) or {}
        items = body.get('items', [])
        quality = body.get('settings', {}).get('selectedQuality', 'lossless')
        return f'/download/batch/start 歌曲数={len(items)} quality={quality}'
    if path.startswith('/download/batch/progress/'):
        task_id = path.rsplit('/', 1)[-1][:30]
        return f'/download/batch/progress task={task_id}'
    if path.startswith('/download/batch/file/'):
        task_id = path.rsplit('/', 1)[-1][:30]
        return f'/download/batch/file task={task_id}'
    return path  # 其他路径原样


@app.before_request
def _start_timer():
    request._start_time = time.time()


@app.after_request
def _log_request(response):
    """统一 API 请求日志：跳过噪声路径 + 提取关键参数 + 单行格式 + 错误时附带 message"""
    try:
        # 静默噪声路径
        if request.path in _QUIET_PATHS or request.path.startswith('/assets/'):
            return response
        if request.path in {'/', '/docs'}:
            return response
        duration_ms = (time.time() - request._start_time) * 1000
        context = _extract_request_context(request.path)
        status = response.status_code

        # 错误响应（4xx/5xx 或 success=False）：WARNING 级别 + 附带 message
        error_msg = None
        if status >= 400:
            error_msg = _extract_error_message(response)
        else:
            # 200 但业务 success=False（如 APIResponse.error）
            error_msg = _extract_business_error(response)

        if error_msg:
            logger.warning(
                f'{request.method} {context} {status} {duration_ms:.0f}ms ✗ {error_msg}'
            )
        else:
            logger.info(
                f'{request.method} {context} {status} {duration_ms:.0f}ms'
            )
    except Exception:
        pass
    return response


def _extract_error_message(response) -> str:
    """从 JSON 响应中提取错误信息（避免直接打印完整 body）"""
    try:
        data = response.get_json(silent=True)
        if not isinstance(data, dict):
            return ''
        # 优先 message 字段
        msg = data.get('message') or data.get('msg') or data.get('error') or ''
        code = data.get('code')
        if code and msg:
            return f'[{code}] {msg[:150]}'
        if msg:
            return msg[:150]
        return ''
    except Exception:
        return ''


def _extract_business_error(response) -> str:
    """从 200 响应里检测业务失败（success=False）"""
    try:
        data = response.get_json(silent=True)
        if isinstance(data, dict) and data.get('success') is False:
            return _extract_error_message(response)
    except Exception:
        pass
    return ''


@app.route('/')
def index():
    """首页 - 返回前端 SPA 的 index.html"""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon_ico():
    """兼容旧浏览器请求 /favicon.ico"""
    return ('', 204)


@app.route('/favicon.svg')
@app.route('/assets/<path:filename>')
def vite_static(filename=None):
    """Vite 构建产物路径：/favicon.svg 和 /assets/* 从 static/ 目录服务"""
    if filename is None:
        # /favicon.svg
        return send_from_directory(app.static_folder, 'favicon.svg', mimetype='image/svg+xml')
    # /assets/<path>
    return send_from_directory(app.static_folder + '/assets', filename)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return {'status': 'healthy'}


# SPA catch-all：未匹配到的非 API 路径全部回退到 index.html
@app.route('/<path:path>')
def spa_fallback(path):
    # API 蓝图已注册的路径不会走到这里
    return render_template('index.html')


@app.errorhandler(404)
def not_found(error):
    return {'success': False, 'message': '资源未找到'}, 404


@app.errorhandler(500)
def internal_error(error):
    return {'success': False, 'message': '服务器内部错误'}, 500


def _resolve_default_port() -> int:
    """从项目根 config.json 解析 dev 端口"""
    return resolve_port(mode='dev')


if __name__ == '__main__':
    try:
        port = _resolve_default_port()

        # werkzeug reloader 会启动双进程：父进程监控文件变化，子进程提供服务。
        # WERKZEUG_RUN_MAIN 仅在子进程中有值，用此判断避免重复打印。
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            logger.info(f'日志文件: {LOG_FILE}')
            logger.info(f"启动服务: http://0.0.0.0:{port}")

        # 用 werkzeug.serving.run_simple 替代 app.run：
        # 1. 立即监听端口（不等待 reloader fork 完成，reloader fork 期间也能接受请求）
        # 2. threaded=True 多线程（避免单请求 hang 阻塞）
        # 3. use_reloader=True 保留 auto-reload
        # 4. passthrough_errors=True 异常直接抛出
        # 这样 Vite proxy 在 0.5s 内就能连上后端，不再 ECONNREFUSED
        from werkzeug.serving import run_simple
        run_simple(
            hostname='0.0.0.0',
            port=port,
            application=app,
            use_reloader=True,        # 保留 auto-reload
            use_debugger=True,        # 保留 debugger
            threaded=True,            # 多线程
            passthrough_errors=False,
        )
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        sys.exit(1)
