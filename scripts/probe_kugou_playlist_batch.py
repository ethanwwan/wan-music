"""批量测试 kugou_official_playlist（多歌单 + 性能）"""
import sys
import time
import logging

sys.path.insert(0, 'backend')
logging.basicConfig(level=logging.WARNING)  # 减少噪音

from clients.kugou_client import KugouClient

client = KugouClient()

# 多个真实 kugou 歌单 ID（从 kugou.com 网页上的热门歌单）
test_ids = [
    ('546903', '热门华语榜'),
    ('492829', '经典老歌'),
    ('86284', '怀旧粤语'),
    ('119749', '网络红歌'),
    ('102419', '伤感歌曲'),
]

print('=' * 80)
print(f'{"歌单 ID":<12} {"歌单名":<18} {"count":<6} {"tracks":<6} {"source":<22} {"time"}')
print('=' * 80)

total_ok = 0
for pid, label in test_ids:
    client.parse_playlist_chain.reset_failed_sources()
    t0 = time.time()
    r = client.parse_playlist(pid, page=1, size=20)
    elapsed = (time.time() - t0) * 1000
    if r and r.get('tracks'):
        total_ok += 1
        first = r['tracks'][0]
        nm = (r.get('name') or '-')[:16]
        print(f'{pid:<12} {nm:<18} {r.get("trackCount", 0):<6} '
              f'{len(r["tracks"]):<6} {r.get("api_source", "-"):<22} {elapsed:.0f}ms')
        print(f'    歌曲: {first.get("name")} - {first.get("artists")} '
              f'(hash={first.get("id", "")[:20]})')
    else:
        print(f'{pid:<12} {"":<18} {"-":<6} {"0":<6} {"(失败)":<22} {elapsed:.0f}ms')

print()
print(f'Total: {total_ok}/{len(test_ids)} successful via kugou_official_playlist')
