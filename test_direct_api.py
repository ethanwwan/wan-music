#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接测试网易云音乐API"""

import requests
import json

def test_artist_api(artist_id):
    print(f"测试歌手ID: {artist_id}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/2.10.2.200154',
        'Referer': 'https://music.163.com/'
    }
    
    url = f"https://music.163.com/api/artist/top/song?id={artist_id}"
    
    print(f"请求URL: {url}")
    print()
    
    response = requests.get(url, headers=headers, timeout=10)
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"响应code: {result.get('code')}")
        
        songs = result.get('songs', [])
        print(f"返回歌曲数: {len(songs)}")
        
        if songs:
            print(f"\n前3首歌:")
            for i, song in enumerate(songs[:3]):
                print(f"  {i+1}. {song.get('name')}")
                ar = song.get('ar', [])
                if ar:
                    print(f"     歌手: {[a.get('name', '') for a in ar]}")
                
                print()
        
        # 查看完整的响应数据，看看有没有歌手信息
        print(f"响应JSON keys: {list(result.keys())}")
    else:
        print(f"失败: {response.text}")

if __name__ == "__main__":
    test_artist_api(6452)  # 周杰伦
    print("\n" + "="*60 + "\n")
    test_artist_api(94733396)  # 广东周杰伦
