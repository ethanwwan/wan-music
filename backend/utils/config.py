"""统一配置加载工具

所有环境变量集中在项目根 config.json，端口解析等被前后端共享。

优先级：环境变量 > config.json > 默认值
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 候选 config.json 路径（按优先级）
_CONFIG_CANDIDATES = [
    Path('/app/config.json'),                                          # Docker 部署
    Path(__file__).resolve().parent.parent.parent / 'config.json',     # 本地开发
]


def find_config_path() -> Optional[Path]:
    """查找 config.json 实际位置"""
    for p in _CONFIG_CANDIDATES:
        if p.is_file():
            return p
    return None


def load_config() -> dict:
    """读取 config.json 全部内容；失败返回空 dict"""
    cfg_path = find_config_path()
    if not cfg_path:
        return {}
    try:
        with cfg_path.open(encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"读取 config.json 失败 ({cfg_path}): {e}")
        return {}


def resolve_port(default: int = 6005) -> int:
    """解析后端服务端口

    优先级：环境变量 PORT / BACKEND_PORT > config.json:backend.prodBackendPort > 默认值
    """
    env_port = os.environ.get('PORT') or os.environ.get('BACKEND_PORT')
    if env_port:
        return int(env_port)

    cfg = load_config().get('backend', {})
    if p := cfg.get('prodBackendPort'):
        return int(p)

    return default
