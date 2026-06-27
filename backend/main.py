"""Wan Music API 服务主程序

提供多平台音乐搜索、解析、下载 API。

端口优先级：环境变量 PORT > config.json:backend.prodBackendPort > 默认 6005
（与 gunicorn.conf.py 共享 utils.config.resolve_port）
"""
import logging
import sys

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

from routes import music_bp
from utils.config import resolve_port

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    # static_url_path 保持默认 /static；Vite 输出的 /assets/* 和 /favicon.svg 用下面的显式路由转发
    static_folder='static',
    static_url_path='/static',
)
CORS(app)

# 注册 API 蓝图
app.register_blueprint(music_bp)


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
    """从项目根 config.json 解析 dev 端口（与 gunicorn.conf.py 共用 resolve_port）"""
    return resolve_port(mode='dev')


if __name__ == '__main__':
    try:
        port = _resolve_default_port()
        logger.info(f"启动服务: http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        sys.exit(1)
