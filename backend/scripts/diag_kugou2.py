#!/usr/bin/env python3
"""诊断 kugou search 为何返回 0 结果"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.kugou_client import KugouClient
from clients.fallback.chain import FallbackChain
from clients.sources.kugou import KUGOU_SEARCH_SOURCES
import time

# 手动模拟 chain 的 _fetch_one 逻辑
chain = FallbackChain(KUGOU_SEARCH_SOURCES, platform='kugou', strategy='parallel')

source = KUGOU_SEARCH_SOURCES[0]  # kugou_official_search
print(f'测试源: {source.name}')

kwargs = {'keyword': '陈楚生 有我呢', 'limit': 5}

# 1. 直接 fetch
try:
    resp = source.fetch(**kwargs)
    print(f'  fetch() 返回类型: {type(resp).__name__}')
    print(f'  fetch() 内容: {str(resp)[:200]}')
except Exception as e:
    print(f'  fetch() 异常: {e}')

# 2. extract_search
if resp:
    extracted = source.extract_search(resp)
    print(f'  extract_search() 返回: {type(extracted).__name__}, len={len(extracted) if isinstance(extracted, list) else "N/A"}')
    print(f'  前3项: {extracted[:3] if extracted else []}')
else:
    print(f'  extract_search() 无数据可提取')

# 3. _is_valid
valid = chain._is_valid(extracted if 'extracted' in dir() else resp, 'search')
print(f'  _is_valid: {valid}')

# 4. 直接用 try_fetch
print(f'\n调用 chain.try_fetch...')
t0 = time.time()
result, src = chain.try_fetch('search', keyword='陈楚生 有我呢', limit=5)
elapsed = time.time() - t0
print(f'  耗时: {elapsed:.2f}s, source={src!r}, 结果数={len(result) if result else 0}')
