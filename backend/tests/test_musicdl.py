"""直接调用musicdl平台模块测试四大音乐平台

参考: https://github.com/CharlesPikachu/musicdl/tree/master/musicdl/modules/sources
"""

import sys
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_platform_direct(platform_name, module_name):
    """直接调用musicdl平台模块测试"""
    print(f"\n{'='*60}")
    print(f"测试平台: {platform_name}")
    print('='*60)

    try:
        module = __import__(f"musicdl.modules.sources.{module_name}", fromlist=['*'])
        client_class = getattr(module, f"{module_name.capitalize()}MusicClient")
        client = client_class()
        print(f"[OK] 加载模块并创建客户端成功")
    except Exception as e:
        print(f"[FAIL] 加载模块或创建客户端失败: {e}")
        return

    print("\n[1] 测试搜索功能")
    print("-" * 40)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(client.search, '陈楚生')
            result = future.result(timeout=12)
        if result:
            print(f"[OK] 搜索成功: {len(result)} 条结果")
            for i, song in enumerate(result[:3]):
                if hasattr(song, 'songname') and hasattr(song, 'singer'):
                    print(f"    {i+1}. {song.songname} - {song.singer}")
                elif isinstance(song, dict):
                    print(f"    {i+1}. {song.get('songname', '未知')} - {song.get('singer', '未知')}")
                else:
                    print(f"    {i+1}. {str(song)[:50]}...")
            
            if result:
                first_item = result[0]
                fields = []
                if hasattr(first_item, '__dict__'):
                    fields = list(first_item.__dict__.keys())
                elif isinstance(first_item, dict):
                    fields = list(first_item.keys())
                
                copyright_fields = ['pay', 'fee', 'canplay', 'available', 'copyright', 'status']
                found_copyright_fields = [f for f in fields if any(c in f.lower() for c in copyright_fields)]
                if found_copyright_fields:
                    print(f"\n    ⚠️ 发现版权相关字段: {', '.join(found_copyright_fields)}")
        else:
            print("[FAIL] 搜索失败: 返回空结果")
    except TimeoutError:
        print("[SKIP] 搜索超时(>12秒)，跳过")
    except Exception as e:
        print(f"[FAIL] 搜索失败: {e}")

    print("\n[2] 测试获取歌曲信息功能")
    print("-" * 40)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(client.search, '林俊杰')
            search_result = future.result(timeout=12)
        
        if search_result and len(search_result) > 0:
            song = search_result[0]
            if hasattr(song, 'songid'):
                song_id = song.songid
            elif isinstance(song, dict) and 'songid' in song:
                song_id = song['songid']
            else:
                print("[SKIP] 无法获取歌曲ID")
                return
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(client.get_song_info, song_id)
                song_info = future.result(timeout=12)
            
            if song_info:
                print(f"[OK] 获取歌曲信息成功")
                if hasattr(song_info, 'songname'):
                    print(f"    歌曲: {song_info.songname}")
                    if hasattr(song_info, 'singer'):
                        print(f"    歌手: {song_info.singer}")
                    if hasattr(song_info, 'download_url') and song_info.download_url:
                        print(f"    下载链接: 存在")
                    else:
                        print(f"    下载链接: 无")
                elif isinstance(song_info, dict):
                    print(f"    歌曲: {song_info.get('songname', '未知')}")
                    print(f"    歌手: {song_info.get('singer', '未知')}")
                    if song_info.get('download_url'):
                        print(f"    下载链接: 存在")
                    else:
                        print(f"    下载链接: 无")
            else:
                print("[FAIL] 获取歌曲信息失败: 返回空结果")
        else:
            print("[SKIP] 搜索无结果，跳过歌曲信息测试")
    except TimeoutError:
        print("[SKIP] 获取歌曲信息超时(>12秒)，跳过")
    except Exception as e:
        print(f"[FAIL] 获取歌曲信息失败: {e}")

    print("\n[3] 测试歌单解析功能")
    print("-" * 40)
    playlist_urls = {
        'netease': 'https://music.163.com/#/playlist?id=7583298906',
        'qq': 'https://y.qq.com/n/ryqq/playlist/7583298906',
        'bodian': 'https://bodian.kuwo.cn/playlist?id=1001',
        'kugou': 'https://www.kugou.com/yy/special/single/694966.html',
    }

    url = playlist_urls.get(module_name)
    if url:
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(client.parse_playlist, url)
                result = future.result(timeout=12)
            if result:
                print(f"[OK] 歌单解析成功: {len(result)} 首歌曲")
                for i, song in enumerate(result[:3]):
                    if hasattr(song, 'songname') and hasattr(song, 'singer'):
                        print(f"    {i+1}. {song.songname} - {song.singer}")
                    elif isinstance(song, dict):
                        print(f"    {i+1}. {song.get('songname', '未知')} - {song.get('singer', '未知')}")
                    else:
                        print(f"    {i+1}. {str(song)[:50]}...")
            else:
                print("[FAIL] 歌单解析失败: 返回空结果")
        except TimeoutError:
            print("[SKIP] 歌单解析超时(>12秒)，跳过")
        except Exception as e:
            print(f"[FAIL] 歌单解析失败: {e}")
    else:
        print("[SKIP] 无对应平台的歌单URL")

if __name__ == '__main__':
    platforms = [
        ('QQ音乐', 'qq'),
        ('波点音乐', 'bodian'),
        ('酷狗音乐', 'kugou'),
    ]

    print("="*60)
    print("直接调用musicdl平台模块测试四大音乐平台")
    print("="*60)

    for platform_name, module_name in platforms:
        test_platform_direct(platform_name, module_name)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)