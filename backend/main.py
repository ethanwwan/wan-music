"""Wan Music API 服务主程序

提供多平台音乐搜索、解析、下载 API。

端口优先级：环境变量 PORT > config.json backend.devBackendPort > 默认 5005
"""
import json
import logging
import os
import sys
from pathlib import Path

from flask import Flask, redirect
from flask_cors import CORS

from routes import music_bp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 注册蓝图
app.register_blueprint(music_bp)

@app.route('/')
def index():
    """首页 - 重定向到API文档"""
    return redirect('/docs')


@app.route('/favicon.ico')
def favicon():
    return ('', 204)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return {'status': 'healthy'}


@app.errorhandler(404)
def not_found(error):
    return {'success': False, 'message': '资源未找到'}, 404


@app.errorhandler(500)
def internal_error(error):
    return {'success': False, 'message': '服务器内部错误'}, 500


def _resolve_default_port() -> int:
    """从项目根 config.json 解析默认端口，保持与前端 Vite 代理配置同步

    优先级：环境变量 > config.json backend.devBackendPort > 默认 5005
    """
    env_port = os.environ.get('PORT') or os.environ.get('BACKEND_PORT')
    if env_port:
        return int(env_port)

    config_path = Path(__file__).resolve().parent.parent / 'config.json'
    if config_path.is_file():
        try:
            with config_path.open(encoding='utf-8') as f:
                cfg = json.load(f)
            backend_cfg = cfg.get('backend', {}) or {}
            dev_port = backend_cfg.get('devBackendPort')
            if dev_port:
                return int(dev_port)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"读取 config.json 失败: {e}，将使用默认端口")
    return 5005


if __name__ == '__main__':
    try:
        port = _resolve_default_port()
        logger.info(f"启动服务: http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        sys.exit(1)
