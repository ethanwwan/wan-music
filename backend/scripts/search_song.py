#!/usr/bin/env python3
"""搜索陈楚生《有我呢》并找正确的歌曲 ID"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service import music_service

# 目标歌曲
TARGET = '陈楚生 有我呢'

# 各平台「有我呢」候选
CANDIDATES = {
    'netease': [
        {'id': '3398250102', 'album': '天赐的声音第七季 第3期'},
        {'id': '3398250479', 'album': '天赐的声音第七季 第3期'},
        {'id': '3398253464', 'album': '有我呢(陈楚生&姚晓棠)天赐的声音'},
    ],
    'qq': [
        {'id': '001a8mcP1cnQ5T', 'album': '天赐的声音第七季 第3期'},
    ],
    'kugou': [
        {'id': 'E0420E6FFD9613170B5839D05AF2CA51', 'album': '天赐的声音第七季 第3期'},
    ],
    'kuwo': [
        {'id': '608664722', 'album': '天赐的声音第七季 第3期'},
    ],
}

def main():
    print(f"=== 搜索: {TARGET} ===\n")

    # 1. 验证 search_source 透传
    print("【1】search_source 透传验证")
    for p in ['netease', 'qq', 'kugou', 'kuwo']:
        r = music_service.search(TARGET, p, limit=5)
        src = r.get('search_source', '')
        songs = r.get('data', [])
        found = [s for s in songs if '有我呢' in s.get('name', '')]
        has_src = src != ''
        print(f"  {p}: search_source={src!r} {'✅' if has_src else '❌'} "
              f"有我呢={len(found)}/{len(songs)}首")

    print()

    # 2. 搜索结果详情
    print("【2】搜索结果（找有我呢）")
    all_songs = {}
    for p in ['netease', 'qq', 'kugou', 'kuwo']:
        r = music_service.search(TARGET, p, limit=10)
        songs = r.get('data', [])
        src = r.get('search_source', '')
        all_songs[p] = songs
        print(f"\n  {p.upper()} (search_src={src!r}):")
        for s in songs:
            name = s.get('name', '')
            if '有我呢' in name:
                print(f"    ★ {name}")
                print(f"      id={s.get('id')} album={s.get('album', '')}")
                print(f"      artists={s.get('artists', s.get('artist', ''))}")
                print(f"      qualityMap={s.get('qualityMap', {})}")
            elif '陈楚生' in name or '姚晓棠' in name:
                print(f"    → {name} | id={s.get('id')} album={s.get('album', '')}")

    print()

    # 3. 获取每首候选的 /song 信息（无损音质）
    print("【3】/song 无损音质测试（播放测试）")
    for p, candidates in CANDIDATES.items():
        print(f"\n  {p.upper()}:")
        for c in candidates:
            song_id = c['id']
            album = c['album']
            print(f"\n  → 测试 id={song_id} (album={album})")

            # 模拟前端点击播放：只获取 URL（最快）
            # 模拟前端点击下载：获取完整信息（URL + Info + Lyric）
            # 先测试 URL 获取（播放）
            from clients.music_client import music_client

            # 获取完整信息（无损）
            result = music_client.get_song(
                song_id={'id': song_id},
                quality='lossless',
                platform=p,
                with_lyric=False,  # 先不测歌词
            )

            if result:
                url = result.get('url', '')
                level = result.get('level', '')
                duration_ms = result.get('duration', 0)
                size = result.get('size', 0)
                api_src = result.get('api_source', {}) or {}

                print(f"    URL: {url[:80] if url else '❌无URL'}")
                print(f"    音质: {level} 大小: {size/1024/1024:.1f}MB 时长: {duration_ms/1000:.0f}s")
                print(f"    来源: url={api_src.get('url')} info={api_src.get('info')} lyric={api_src.get('lyric')}")
            else:
                print(f"    ❌ get_song 返回 None")

if __name__ == '__main__':
    main()
