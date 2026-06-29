"""统一日志配置

日志同时输出到：
  1. stderr（容器标准输出，docker logs 可看）
  2. 文件 logs/wan-music.log（持久化，可用 `docker exec` 进容器查看）

按大小自动轮转：单文件最大 10 MB，保留 5 个备份。
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 日志目录：与本文件同级 backend/logs/
LOG_DIR = Path(__file__).resolve().parent.parent / 'logs'
LOG_FILE = LOG_DIR / 'wan-music.log'

# 格式
CONSOLE_FORMAT = '%(asctime)s - %(levelname)-5s - %(name)s - %(message)s'
FILE_FORMAT = '%(asctime)s - %(levelname)-5s - %(name)s - %(message)s'

# 轮转参数
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logging(level: int = logging.INFO) -> None:
    """初始化日志：清掉已存在的 handler，统一接管所有 logger。"""
    # 1. 确保日志目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 2. 根 logger
    root = logging.getLogger()
    root.setLevel(level)
    # 清掉已配置的 handler（避免重复输出）
    for h in list(root.handlers):
        root.removeHandler(h)

    # 3. 控制台 handler（stderr）
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt='%Y-%m-%d %H:%M:%S'))
    root.addHandler(console)

    # 4. 文件 handler（滚动）
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8',
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt='%Y-%m-%d %H:%M:%S'))
        root.addHandler(file_handler)
    except OSError as e:
        # 文件日志不可用时退化为只输出到 stderr，不阻塞启动
        logging.getLogger(__name__).warning(f'文件日志初始化失败 ({LOG_FILE}): {e}')

    # 5. 静默一些过吵的第三方 logger
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    # werkzeug 自带 access log 与 __main__.after_request 双行重复，静默 werkzeug
    # （我们自己的 _log_request 已经记录 API 请求）
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
