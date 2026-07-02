#!/usr/bin/env python3
"""对比 service.search vs client.search"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service import music_service
from clients.kugou_client import KugouClient

keyword = '陈楚生 有我呢'
p = 'kugou'

print('=== service.search ===')
t0 = time.time()
r = music_service.search(keyword, p, limit=5)
elapsed = time.time() - t0
print(f'  耗时: {elapsed:.2f}s')
print(f'  keys: {list(r.keys())}')
print(f'  search_source: {r.get("search_source")!r}')
print(f'  data len: {len(r.get("data", []))}')
songs = r.get('data', [])
if songs:
    s = songs[0]
    print(f'  first song keys: {list(s.keys())[:10]}')
    print(f'  first song id={s.get("id")!r} name={s.get("name")!r}')
else:
    print(f'  data 为空!')

print()
print('=== client.search ===')
t0 = time.time()
r2 = music_service._get_client(p).search(keyword, limit=5)
elapsed = time.time() - t0
print(f'  耗时: {elapsed:.2f}s')
print(f'  keys: {list(r2.keys())}')
print(f'  search_source: {r2.get("search_source")!r}')
print(f'  data len: {len(r2.get("data", []))}')
