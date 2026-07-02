#!/usr/bin/env python3
"""诊断 kugou search 为何返回 0 结果"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from clients.sources.kugou import KUGOU_SEARCH_SOURCES, KUGOU_COMMON_HEADERS
from clients.fallback.chain import FallbackChain

# 手动重建 kugou_official_search 的请求
source = KUGOU_SEARCH_SOURCES[0]
keyword = '陈楚生 有我呢'
limit = 5

# 填充 URL 模板
from urllib.parse import quote
kw_encoded = quote(keyword, safe='')
url = source.search_url.format(keyword_encoded=kw_encoded, limit=limit)
url = url.replace('{keyword_encoded}', kw_encoded).replace('{limit}', str(limit))

print(f'URL: {url}')
headers = dict(KUGOU_COMMON_HEADERS)
headers.setdefault('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

t0 = time.time()
resp = requests.get(url, headers=headers, timeout=10)
elapsed = time.time() - t0
print(f'HTTP {resp.status_code} elapsed={elapsed:.2f}s')

data = resp.json()
print(f'response keys: {list(data.keys())}')

# extract_search
lists = source.extract_search(data)
print(f'extract_search() → len={len(lists)}')

# _is_valid
chain = FallbackChain(KUGOU_SEARCH_SOURCES, platform='kugou', strategy='parallel')
valid = chain._is_valid(lists, 'search')
print(f'_is_valid={valid}')

# 看看列表第一项
if lists:
    item = lists[0]
    print(f'第一项 keys: {list(item.keys())}')
    print(f'第一项 FileHash={item.get("FileHash")}')

# 也测试 chain.try_fetch
print(f'\nchain.try_fetch...')
t0 = time.time()
result, src = chain.try_fetch('search', keyword=keyword, limit=limit)
elapsed = time.time() - t0
print(f'  耗时: {elapsed:.2f}s, source={src!r}, 结果数={len(result) if result else 0}')
if result:
    for r in result[:2]:
        print(f'  item: {r.get("name","?")} id={r.get("id","?")} FileHash={r.get("FileHash","?")}')
