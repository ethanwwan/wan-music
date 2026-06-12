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
    """首页"""
    return render_template('index.html')


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
        app.run(host='0.0.0.0', port=5002, debug=True)
    except Exception as e:
        logger.error(f"启动服务失败: {e}")
        sys.exit(1)