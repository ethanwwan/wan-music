"""测试酷我歌词两个 API + 找到真实 rid"""
import requests
import base64
import json
import zlib
import sys

# 1. 用官方搜索 API
print('=== Step 1: Search to get real rid ===')
sr = requests.get(
    'http://www.kuwo.cn/search/searchMusicBykeyWord',
    params={
        'vipver': '1', 'client': 'kt', 'ft': 'music', 'cluster': '0',
        'strategy': '2012', 'encoding': 'utf8', 'rformat': 'json', 'mobi': '1',
        'issubtitle': '1', 'show_copyright_off': '1', 'pn': '0', 'rn': '3',
        'all': '周杰伦 晴天',
    },
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        'Referer': 'https://www.kuwo.cn/',
    },
    timeout=10,
)
print(f'Search status: {sr.status_code}')
try:
    d = sr.json()
except Exception as e:
    print(f'JSON error: {e}')
    print(f'Body[:200]: {sr.text[:200]}')
    sys.exit(1)

print(f'Search top keys: {list(d.keys())[:10]}')
songs = d.get('abslist', [])
if not songs:
    print(f'abslist empty, full: {json.dumps(d)[:500]}')
    sys.exit(1)
s = songs[0]
rid = str(s.get('MUSICRID', '')).replace('MUSIC_', '')
name = s.get('SONGNAME', '')
singer = s.get('ARTIST', '')
print(f'  Found: {name} - {singer} (rid={rid})')

# 2. Legacy API
print()
print('=== Step 2: Legacy API (m.kuwo.cn/newh5/singles/songinfoandlrc) ===')
r = requests.get(
    'http://m.kuwo.cn/newh5/singles/songinfoandlrc',
    params={'musicId': rid, 'httpsStatus': 1},
    headers={
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
        'Referer': 'http://m.kuwo.cn',
    },
    timeout=10,
)
print(f'Status: {r.status_code}')
try:
    d = r.json()
    print(f'Top keys: {list(d.keys())}')
    data = d.get('data') or {}
    print(f'data type: {type(data).__name__}, value: {repr(data)[:100] if data else "None"}')
    if isinstance(data, dict):
        print(f'data keys: {list(data.keys())}')
        lrclist = data.get('lrclist', [])
        print(f'lrclist count: {len(lrclist)}')
        if lrclist:
            print(f'Sample (first 3):')
            for line in lrclist[:3]:
                print(f'  {line}')
    elif isinstance(data, str):
        print(f'data is string (base64?): {data[:100]}')
except Exception as e:
    print(f'JSON error: {e}')
    print(f'Body[:200]: {r.text[:200]}')

# 3. New API (XOR+base64 params)
print()
print('=== Step 3: New API (newlyric.kuwo.cn) ===')
KEY = b'yeelion'
params_str = f'user=12345,web,web,web&requester=localhost&req=1&rid=MUSIC_{rid}&lrcx=1'
encrypted = bytes([b ^ KEY[i % len(KEY)] for i, b in enumerate(params_str.encode('utf-8'))])
b64 = base64.b64encode(encrypted).decode('utf-8')
print(f'  Encoded params: {b64[:50]}...')

# 尝试不同参数名
for param_name in ['', 'pc', 'data', 'q', 'p']:
    if param_name == '':
        # 直接放 URL 里
        r = requests.get(
            f'http://newlyric.kuwo.cn/newlyric.lrc?{b64}',
            headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'},
            timeout=10,
        )
    else:
        r = requests.get(
            'http://newlyric.kuwo.cn/newlyric.lrc',
            params={param_name: b64},
            headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'},
            timeout=10,
        )
    print(f'  Param={param_name or "(direct)"}: status={r.status_code} len={len(r.content)} first50={r.content[:50]!r}')
