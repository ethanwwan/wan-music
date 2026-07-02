#!/usr/bin/env python3
"""诊断 kugou search_source=None"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.kugou_client import KugouClient
c = KugouClient()
r, src = c.search_chain.try_fetch('search', keyword='陈楚生 有我呢', limit=5)
print(f'results={len(r) if r else 0}, source={src!r}')

import requests
resp = requests.get('https://songsearch.kugou.com/song_search_v2', params={
    'keyword': '陈楚生 有我呢',
    'page': 1, 'pagesize': 5, 'platform': 'WebFilter'
}, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
print(f'HTTP {resp.status_code}, elapsed={resp.elapsed.total_seconds():.2f}s')
data = resp.json()
lists = data.get('data', {}).get('lists', [])
print(f'lists={len(lists)}')
