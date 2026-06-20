"""网易云音乐API服务主程序

提供网易云音乐相关API服务，包括：
- 歌曲信息获取
- 音乐搜索
- 歌单和专辑详情
- 音乐下载
- 健康检查
"""

import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
# 优先级：WAN_MUSIC_ENV_FILE > frontend/.env.dev > 根 .env.docker
# - dev:api 启动时用默认 .env.dev（开发环境，5005）
# - preview:api 启动时设置 WAN_MUSIC_ENV_FILE=frontend/.env.prod（生产预览，6005）
# - Docker 部署用根 .env.docker 的 CONTAINER_PORT（5002）
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent

# 加载根 .env.docker（Docker 部署用），已存在的环境变量不覆盖
for env_name in ['.env.docker', '.env']:
    root_env = PROJECT_ROOT / env_name
    if root_env.exists():
        load_dotenv(root_env, override=False)
        break  # 找到第一个就停

# 加载前端 .env 文件（dev 或 prod 二选一）
env_file = os.environ.get('WAN_MUSIC_ENV_FILE')
if env_file:
    # 显式指定的 .env 文件（生产预览）
    target = Path(env_file)
    if not target.is_absolute():
        target = PROJECT_ROOT / env_file
    if target.exists():
        load_dotenv(target, override=True)
else:
    # 默认加载 .env.dev（开发环境）
    dev_env = PROJECT_ROOT / 'frontend' / '.env.dev'
    if dev_env.exists():
        load_dotenv(dev_env, override=True)

from flask import Flask, request, render_template
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
        # 端口从环境变量读取，默认 5002
        # 开发：BACKEND_PORT=5005（在 .env.dev 中配置）
        # 生产：PORT=6005（Docker 环境变量或 .env.prod）
        port = int(os.environ.get('PORT') or os.environ.get('BACKEND_PORT') or 5002)
        logger.info(f"启动服务: http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        sys.exit(1)