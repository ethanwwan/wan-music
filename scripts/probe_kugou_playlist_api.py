"""测试 mobilecdn.kugou.com 官方歌单 API 的可用性"""
import requests
import json

test_ids = [
    ('3641717744', '热门推荐'),
    ('2384404318', '热门华语'),
    ('546903', '经典歌单'),
    ('183241', '经典老歌'),
    ('13123', '默认歌单'),
]

url = 'http://mobilecdn.kugou.com/api/v3/special/song'
for sid, label in test_ids:
    params = {'specialid': sid, 'page': 1, 'pagesize': 5, 'version': 9108, 'area_code': 1}
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    d = r.json()
    data = d.get('data', {})
    info = data.get('info', [])
    err = d.get('error', '')[:40]
    print(f'{label} (id={sid}): total={data.get("total")} info={len(info)} status={d.get("status")} errcode={d.get("errcode")} err={err}')
    if info:
        first = info[0]
        h = first.get('hash') or first.get('FileHash') or ''
        print(f'    First: {first.get("songname")} - {first.get("singername")} hash={h[:20]} dur={first.get("duration")}ms')
