"""使用musicdl测试四大音乐平台

参考: https://github.com/CharlesPikachu/musicdl/blob/master/README.md
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from musicdl.musicdl import MusicClient

def test_platform(platform_name, client_class_name):
    """测试单个平台"""
    print(f"\n{'='*60}")
    print(f"测试平台: {platform_name} ({client_class_name})")
    print('='*60)

    try:
        client = MusicClient(music_sources=[client_class_name])
        print(f"[OK] 创建客户端成功")
    except Exception as e:
        print(f"[FAIL] 创建客户端失败: {e}")
        return

    # 测试搜索
    print("\n[1] 测试搜索功能")
    print("-" * 40)
    try:
        result = client.search('陈楚生')
        if result:
            print(f"[OK] 搜索成功: {len(result)} 条结果")
            for i, song in enumerate(result[:3]):
                print(f"    {i+1}. {song.songname} - {song.singer}")
        else:
            print("[FAIL] 搜索失败: 返回空结果")
    except Exception as e:
        print(f"[FAIL] 搜索失败: {e}")

    # 测试歌单解析
    print("\n[2] 测试歌单解析功能")
    print("-" * 40)
    playlist_urls = {
        'NeteaseMusicClient': 'https://music.163.com/#/playlist?id=7583298906',
        'QQMusicClient': 'https://y.qq.com/n/ryqq/playlist/7583298906',
        'BodianMusicClient': 'https://bodian.kuwo.cn/playlist?id=1001',
        'KugouMusicClient': 'https://www.kugou.com/yy/special/single/694966.html',
    }

    url = playlist_urls.get(client_class_name)
    if url:
        try:
            result = client.parseplaylist(url)
            if result:
                print(f"[OK] 歌单解析成功: {len(result)} 首歌曲")
                for i, song in enumerate(result[:3]):
                    print(f"    {i+1}. {song.songname} - {song.singer}")
            else:
                print("[FAIL] 歌单解析失败: 返回空结果")
        except Exception as e:
            print(f"[FAIL] 歌单解析失败: {e}")
    else:
        print("[SKIP] 无对应平台的歌单URL")

if __name__ == '__main__':
    platforms = [
        ('网易云音乐', 'NeteaseMusicClient'),
        ('QQ音乐', 'QQMusicClient'),
        ('波点音乐', 'BodianMusicClient'),
        ('酷狗音乐', 'KugouMusicClient'),
    ]

    print("="*60)
    print("使用musicdl测试四大音乐平台")
    print("="*60)

    for platform_name, client_class_name in platforms:
        test_platform(platform_name, client_class_name)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
