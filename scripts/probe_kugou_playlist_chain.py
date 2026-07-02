"""集成测试：kugou 歌单 → 取歌曲 → 完整 get_song（验证 chain 全链路）"""
import sys
import logging

sys.path.insert(0, 'backend')
logging.basicConfig(level=logging.WARNING)

from clients.kugou_client import KugouClient

client = KugouClient()
client.parse_lyric_chain.reset_failed_sources()
client.parse_url_chain.reset_failed_sources()
client.parse_info_chain.reset_failed_sources()

# 1. 取歌单
print('=== 1. 取歌单 ===')
pl = client.parse_playlist('546903', page=1, size=5)
print(f'  playlist source: {pl.get("api_source")}')
print(f'  tracks: {len(pl.get("tracks", []))}')
if not pl or not pl.get('tracks'):
    sys.exit(1)

# 2. 拿第一首歌的 hash
first = pl['tracks'][0]
print(f'\n=== 2. 第一首歌详情 ===')
print(f'  {first.get("name")} - {first.get("artists")}')
print(f'  hash: {first.get("id")}')
print(f'  duration: {first.get("duration")}ms')

# 3. 用这个 hash 调 get_song (验证 chain 全链路)
print(f'\n=== 3. get_song 完整链路 ===')
detail = client.get_song(first['id'], quality='exhigh', with_lyric=True)
if detail:
    print(f'  url: {detail["url"][:80]}...')
    print(f'  url_src: {detail["api_source"]["url"]}')
    print(f'  info_src: {detail["api_source"]["info"]}')
    print(f'  lyric_src: {detail["api_source"]["lyric"]}')
    print(f'  duration: {detail.get("duration")}ms')
    lyric = detail.get('lyric', '')
    print(f'  lyric: {len(lyric)} chars')
    if lyric:
        print(f'  first line: {lyric.split(chr(10))[0] if lyric else "(empty)"}')
        # 打印带时间的几行
        for line in lyric.split('\n')[:5]:
            if line.startswith('[') and ':' in line[:10]:
                print(f'    {line}')
else:
    print('  (failed)')
