"""测试修复后的 kugou_official_playlist 端到端"""
import sys
import json
import logging

sys.path.insert(0, 'backend')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

from clients.kugou_client import KugouClient

client = KugouClient()
client.parse_playlist_chain.reset_failed_sources()

# 用真实有效 ID (546903 测试过有 32 首歌)
test_ids = [
    ('546903', '大壮等热门'),
    ('2602091030', '用户创建的歌单（用 gdstudio 兜底）'),
]

for pid, label in test_ids:
    print(f'\n=== {label} (id={pid}) ===')
    try:
        r = client.parse_playlist(pid, page=1, size=20)
        if r:
            print(f'  name: {r.get("name")!r}')
            print(f'  cover: {r.get("cover", "")[:80]}')
            print(f'  trackCount: {r.get("trackCount")}')
            print(f'  actual tracks: {len(r.get("tracks", []))}')
            print(f'  api_source: {r.get("api_source")}')
            if r.get('tracks'):
                for i, t in enumerate(r['tracks'][:3]):
                    print(f'  [{i}] {t.get("name")} - {t.get("artists")} '
                          f'(id={t.get("id")}, dur={t.get("duration")}ms, '
                          f'hq_hash={(t.get("HQFileHash") or t.get("320hash") or "")[:16]}...)')
        else:
            print('  (None result)')
    except Exception as e:
        print(f'  Error: {type(e).__name__}: {e}')
