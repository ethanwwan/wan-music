"""查看 mobilecdn.kugou.com 歌单 API 实际响应字段"""
import requests
import json

url = 'http://mobilecdn.kugou.com/api/v3/special/song'
params = {'specialid': '546903', 'page': 1, 'pagesize': 3, 'version': 9108, 'area_code': 1}
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
}
r = requests.get(url, params=params, headers=headers, timeout=10)
d = r.json()
data = d.get('data', {})
info = data.get('info', [])
print('Top-level data keys:', list(data.keys()))
print(f'total: {data.get("total")}')
print(f'timestamp: {data.get("timestamp")}')
print()
print(f'info count: {len(info)}')
if info:
    print(f'First song keys: {list(info[0].keys())}')
    print()
    print('First song full JSON:')
    print(json.dumps(info[0], ensure_ascii=False, indent=2)[:1500])
