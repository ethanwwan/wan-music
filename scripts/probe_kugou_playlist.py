"""直接测试 kugou_official_playlist 端到端"""
import sys
import json
import logging

sys.path.insert(0, 'backend')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from clients.kugou_client import KugouClient

client = KugouClient()
client.parse_playlist_chain.reset_failed_sources()

# 用一个真实酷狗歌单 ID 测试
# 酷狗歌单 ID 示例：https://www.kugou.com/playlist/specialid/<id>.html
test_ids = [
    ('3641717744', '官方推荐热门歌单'),
    ('2384404318', '热门华语'),
    ('2602091030', '默认歌单'),
]

for pid, label in test_ids:
    print(f'\n=== {label} (id={pid}) ===')
    try:
        r = client.parse_playlist(pid, page=1, size=20)
        if r:
            print(f'  name: {r.get("name")}')
            print(f'  creator: {r.get("creator")}')
            print(f'  cover: {r.get("cover", "")[:80]}')
            print(f'  trackCount: {r.get("trackCount")}')
            print(f'  actual tracks: {len(r.get("tracks", []))}')
            print(f'  platform: {r.get("platform")}')
            print(f'  api_source: {r.get("api_source")}')
            if r.get('tracks'):
                t = r['tracks'][0]
                print(f'  first track: {t.get("name")} - {t.get("artists")} '
                      f'(id={t.get("id")}, dur={t.get("duration")}ms)')
        else:
            print('  (None result)')
    except Exception as e:
        print(f'  Error: {type(e).__name__}: {e}')
