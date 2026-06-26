"""Wan Music API 服务主程序

提供多平台音乐搜索、解析、下载 API。
"""
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent

# ============================================================
# 加载 .env（向后兼容，不强制要求）
# 优先级：WAN_MUSIC_ENV_FILE > 根 .env
# ============================================================
env_file_override = os.environ.get('WAN_MUSIC_ENV_FILE')
if env_file_override:
    target = Path(env_file_override)
    if not target.is_absolute():
        target = PROJECT_ROOT / env_file_override
    if target.exists():
        load_dotenv(target, override=False)
else:
    root_env = PROJECT_ROOT / '.env'
    if root_env.exists():
        load_dotenv(root_env, override=False)

from flask import Flask, request, render_template, redirect
from flask_cors import CORS

from routes import search_bp, music_bp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 注册蓝图
app.register_blueprint(search_bp)
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


if __name__ == '__main__':
    try:
        # 端口优先级：PORT > BACKEND_PORT > 默认 5002
        port = int(os.environ.get('PORT') or os.environ.get('BACKEND_PORT') or 5002)
        logger.info(f"启动服务: http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        sys.exit(1)
