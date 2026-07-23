"""HealthMonitor：健康监控

定期（每 N 次请求）调用各源做一次轻量探测，自动禁用失败率过高的源。
"""
import time
import threading
import logging
from typing import Dict, List
from .chain import FallbackChain
from .api_source import ApiSource

logger = logging.getLogger(__name__)


class HealthMonitor:
    """定期探测各源可用性，自动禁用失败率过高的源

    策略：
      - 每隔 N 次请求后做一次健康检查
      - 如果某个源连续失败 K 次，自动禁用（enabled=False）
      - 30 分钟后再启用一次试试（self-heal）
    """
    CHECK_INTERVAL = 50       # 每 50 次请求检查一次
    AUTO_DISABLE_THRESHOLD = 5  # 连续失败 5 次自动禁用
    RE_ENABLE_AFTER_SEC = 1800  # 30 分钟后重新尝试

    def __init__(self, chains: List[FallbackChain]):
        self.chains = chains
        self._request_count = 0
        self._consecutive_fails = {}  # source_name -> count
        self._last_disabled_time = {}  # source_name -> timestamp
        self._lock = threading.Lock()

    def record_request(self, source_name: str, success: bool):
        """记录一次请求结果"""
        with self._lock:
            self._request_count += 1
            if success:
                self._consecutive_fails[source_name] = 0
            else:
                self._consecutive_fails[source_name] = self._consecutive_fails.get(source_name, 0) + 1
                if self._consecutive_fails[source_name] >= self.AUTO_DISABLE_THRESHOLD:
                    self._disable_source(source_name)
            # 定期重新启用（self-heal）
            if self._request_count % self.CHECK_INTERVAL == 0:
                self._maybe_re_enable()

    def _disable_source(self, source_name: str):
        """禁用源"""
        for chain in self.chains:
            for s in chain.sources:
                if s.name == source_name and s.enabled:
                    s.enabled = False
                    self._last_disabled_time[source_name] = time.time()
                    logger.warning(f'自动禁用源: {source_name}（连续失败 {self._consecutive_fails[source_name]} 次）')

    def _maybe_re_enable(self):
        """30 分钟后重新启用"""
        now = time.time()
        for name, ts in list(self._last_disabled_time.items()):
            if now - ts > self.RE_ENABLE_AFTER_SEC:
                for chain in self.chains:
                    for s in chain.sources:
                        if s.name == name and not s.enabled:
                            s.enabled = True
                            del self._last_disabled_time[name]
                            self._consecutive_fails[name] = 0
                            logger.info(f'自动重新启用源: {name}（已禁用 {(now - ts) / 60:.0f} 分钟）')

    def get_report(self) -> dict:
        """获取完整健康报告"""
        report = {'timestamp': time.time(), 'chains': []}
        for chain in self.chains:
            chain_info = {
                'platform': chain.platform,
                'strategy': chain.strategy,
                'sources': []
            }
            for s in chain.sources:
                stats = dict(s._stats)
                stats['enabled'] = s.enabled
                stats['priority'] = s.priority
                stats['name'] = s.name
                if stats.get('ok', 0) > 0:
                    stats['avg_ms'] = int(stats.get('total_ms', 0) / stats['ok'])
                else:
                    stats['avg_ms'] = 0
                chain_info['sources'].append(stats)
            report['chains'].append(chain_info)
        return report
