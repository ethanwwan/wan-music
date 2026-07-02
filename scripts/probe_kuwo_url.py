"""检查 kuwo URL chain 状态 + 是否有可达的 URL 源"""
import sys
sys.path.insert(0, 'backend')

import requests
import json

rid = '228908'

# 1. m.kuwo.cn URL API (看响应字段)
r = requests.get(
    'http://m.kuwo.cn/newh5/singles/songinfoandlrc',
    params={'musicId': rid, 'httpsStatus': 1},
    headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
             'Referer': 'http://m.kuwo.cn'}, timeout=10)
print('songinfoandlrc status:', r.status_code)
d = r.json()
data = d.get('data') or {}
songinfo = data.get('songinfo') or {}
print('songinfo keys:', list(songinfo.keys()))
print('  artist:', songinfo.get('artist', ''))
print('  name:', songinfo.get('name', ''))
print('  duration:', songinfo.get('duration', ''))
print('  pic:', songinfo.get('pic', ''))
print('  mp3Url:', songinfo.get('mp3Url', ''))
print('  mp3:', songinfo.get('mp3', ''))
print('  aac:', songinfo.get('aac', ''))
print('  wma:', songinfo.get('wma', ''))
print('  320kbps:', songinfo.get('320kbps', ''))
print('  lossless:', songinfo.get('lossless', ''))
print('  hasPlayUrl:', songinfo.get('hasPlayUrl', ''))
print('  hasLossless:', songinfo.get('hasLossless', ''))
print('  hasFlac:', songinfo.get('hasFlac', ''))
print('  has192:', songinfo.get('has192', ''))
print('  has128:', songinfo.get('has128', ''))

# 2. 看看 kuwo URL 链各 source 状态
print()
print('=== kuwo parse_url sources status ===')
from clients.kuwo_client import KuwoClient
client = KuwoClient()
client.parse_url_chain.reset_failed_sources()

# 调一个 URL source 看具体返回什么
from clients.sources.kuwo import KUWO_PARSE_URL_SOURCES
for src in KUWO_PARSE_URL_SOURCES[:5]:
    print(f'\n--- {src.name} ---')
    print(f'  url: {src.parse_url_url[:100]}')
    print(f'  desc: {src.description}')

# 3. 测试 第一个源的实际 URL
print()
print('=== Test first source directly ===')
import importlib
kuwo_mod = importlib.import_module('clients.sources.kuwo')
# Look for URL extractors
import inspect
for name, obj in inspect.getmembers(kuwo_mod):
    if name.endswith('_url') and callable(obj) and name not in ('KUWO_COMMON_HEADERS', 'KUWO_LXMUSIC_HEADERS'):
        if name.startswith('extract'):
            print(f'  {name}: {obj}')
