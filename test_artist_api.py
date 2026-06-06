#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试网易云音乐歌手热门歌曲API"""

import requests
import json


def test_artist_songs():
    """测试获取歌手热门歌曲"""
    
    # 测试歌手ID：94733396（广东周杰伦）
    artist_id = 94733396
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154',
        'Referer': 'https://music.163.com/'
    }
    
    # 方式1：直接请求API
    print("方式1：直接请求api/artist/top/song...")
    try:
        url = f"https://music.163.com/api/artist/top/song?id={artist_id}"
        response = requests.get(url, headers=headers, timeout=30)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
            
            if result.get('code') == 200:
                print("\n✅ 获取成功！")
                songs = result.get('songs', [])
                print(f"获取到 {len(songs)} 首歌曲")
                for i, song in enumerate(songs[:5]):
                    print(f"{i+1}. {song.get('name')}")
        else:
            print(f"❌ 失败: {response.text}")
    except Exception as e:
        print(f"❌ 异常: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # 方式2：搜索歌手
    print("方式2：搜索歌手...")
    try:
        search_url = "https://music.163.com/api/cloudsearch/pc"
        data = {'s': str(artist_id), 'type': 100, 'limit': 10}
        response = requests.post(search_url, data=data, headers=headers, timeout=30)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
            
            if result.get('code') == 200:
                artists = result.get('result', {}).get('artists', [])
                print(f"\n获取到 {len(artists)} 个歌手")
                for artist in artists:
                    print(f"  - {artist.get('name')} (ID: {artist.get('id')})")
                    if artist.get('id') == artist_id:
                        print(f"  ✅ 找到匹配的歌手！")
                        
                        # 搜索该歌手的歌曲
                        print(f"\n搜索歌手 '{artist.get('name')}' 的歌曲...")
                        search_data = {'s': artist.get('name'), 'type': 1, 'limit': 20}
                        search_response = requests.post(search_url, data=search_data, headers=headers, timeout=30)
                        songs_result = search_response.json()
                        if songs_result.get('code') == 200:
                            songs = songs_result.get('result', {}).get('songs', [])
                            print(f"  找到 {len(songs)} 首歌曲")
                            for i, song in enumerate(songs[:5]):
                                print(f"    {i+1}. {song.get('name')}")
    except Exception as e:
        print(f"❌ 异常: {e}")


if __name__ == "__main__":
    test_artist_songs()
