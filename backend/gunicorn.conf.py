"""gunicorn 生产配置

端口优先级：环境变量 PORT > config.json:backend.prodBackendPort > 默认 6005
worker / 线程数等参数也集中在此，方便调整。
"""
import os
import sys

# 把 backend/ 加入 path（gunicorn 启动时 cwd 不一定是 backend/）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import resolve_port  # noqa: E402

bind = f'0.0.0.0:{resolve_port(mode="prod")}'
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
threads = int(os.environ.get('GUNICORN_THREADS', '4'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
accesslog = '-'
errorlog = '-'
