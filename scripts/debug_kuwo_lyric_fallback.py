"""调试：为什么部分歌曲落到 gdstudio 而不是 kuwo_official_lyric"""
import sys
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, 'backend')

from clients.kuwo_client import KuwoClient

client = KuwoClient()

for kw in ['林俊杰 江南', '陈奕迅 十年', '薛之谦 演员']:
    print(f'\n=== {kw} ===')
    sr = client.search(kw, limit=1)
    if not sr['data']:
        print('  no result')
        continue
    s = sr['data'][0]
    rid = s.get('id')
    print(f'  rid: {rid}')

    # 直接打 API
    r = requests.get(
        'http://m.kuwo.cn/newh5/singles/songinfoandlrc',
        params={'musicId': rid, 'httpsStatus': 1},
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            'Referer': 'http://m.kuwo.cn',
        },
        timeout=10,
    )
    print(f'  raw status: {r.status_code}')
    try:
        d = r.json()
        data = d.get('data') or {}
        lrclist = data.get('lrclist', [])
        print(f'  raw lrclist count: {len(lrclist)}')
        if lrclist:
            print(f'  sample first: {lrclist[0]}')
    except Exception as e:
        print(f'  parse err: {e}')

    # 走 chain
    client.parse_lyric_chain.reset_failed_sources()
    lyric, src = client.parse_lyric_chain.try_fetch('parse_lyric', rid=rid)
    print(f'  chain: src={src}, len={len(lyric)}')
