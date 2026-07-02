"""检查 kugou songsearch 搜索 API 实际响应字段"""
import requests
import json

r = requests.get(
    'https://songsearch.kugou.com/song_search_v2',
    params={'keyword': '周杰伦', 'page': 1, 'pagesize': 2, 'platform': 'WebFilter'},
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
    timeout=10,
)
d = r.json()
songs = d.get('data', {}).get('lists', [])
print('Found:', len(songs))
if songs:
    s = songs[0]
    print('Top-level keys:', list(s.keys()))
    print()
    print(json.dumps(s, ensure_ascii=False, indent=2)[:1200])
