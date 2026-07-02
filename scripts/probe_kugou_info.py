"""探测 kugou 官方 playInfo API 返回的实际字段"""
import sys
import json
import requests

sys.path.insert(0, 'backend')
from clients.sources.kugou import KUGOU_COMMON_HEADERS

# Use a known kugou song hash
hash_val = '78E125D093837C463270EAC03BB9D8A9'  # 晴天 from previous test

r = requests.get(
    'https://m.kugou.com/app/i/getSongInfo.php',
    params={'cmd': 'playInfo', 'hash': hash_val},
    headers=KUGOU_COMMON_HEADERS,
    timeout=10,
)
print('Status:', r.status_code)
d = r.json()
print('Keys:', list(d.keys()))
print('timeLength:', d.get('timeLength'), type(d.get('timeLength')))
print('duration:', d.get('duration'), type(d.get('duration')))
print('Duration:', d.get('Duration'), type(d.get('Duration')))
print('songName:', d.get('songName'))
print('singerName:', d.get('singerName'))
print('albumName:', d.get('albumName'))
print('imgUrl:', d.get('imgUrl'))
print('album_img:', d.get('album_img'))
print()
print('Full response (truncated):')
print(json.dumps(d, ensure_ascii=False, indent=2)[:1500])
