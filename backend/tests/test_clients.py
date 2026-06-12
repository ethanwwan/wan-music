"""音乐客户端API测试脚本

测试所有音乐平台客户端的所有方法，确保API可正常访问。
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.music_client import music_client
from clients.netease_client import NeteaseClient
from clients.qq_client import QQClient
from clients.bodian_client import BodianClient
from clients.kugou_client import KugouClient


class APITester:
    """API测试类"""
    
    def __init__(self):
        self.clients = {
            'netease': NeteaseClient(),
            'qq': QQClient(),
            'bodian': BodianClient(),
            'kugou': KugouClient()
        }
        self.test_results = {}
        self.failed_tests = []
        
        self.song_ids = {
            'netease': '25706282',
            'qq': '003OUlho2HcRHC',
            'bodian': '3940273',
            'kugou': 'A758EF54F67AE76E2BD0C249CD7B904A'  # 使用FileHash而不是数字ID
        }
        
        self.playlist_ids = {
            'netease': '7583298906',
            'qq': '8262370668',
            'bodian': '2410926933',  # 酷我音乐歌单ID
            'kugou': '9180602'
        }
    
    def run_test(self, client_name, client, method_name, func, *args, **kwargs):
        """运行单个测试"""
        try:
            result = func(*args, **kwargs)
            success = False
            
            if method_name in ['search', 'search_playlist']:
                success = isinstance(result, list) and len(result) > 0
            elif method_name == 'get_song_url':
                success = isinstance(result, dict) and result.get('url')
            elif method_name == 'get_song_info':
                success = isinstance(result, dict) and result.get('id')
            elif method_name == 'get_lyric':
                success = isinstance(result, str) and len(result) > 0
            elif method_name == 'get_playlist':
                success = isinstance(result, dict) and result.get('tracks')
            
            if success:
                print(f"✅ [{client_name}] {method_name}: 成功")
                return {'success': True, 'result': result}
            else:
                print(f"❌ [{client_name}] {method_name}: 返回数据为空或格式不正确")
                self.failed_tests.append(f"{client_name}.{method_name}")
                return {'success': False, 'result': result}
                
        except Exception as e:
            print(f"❌ [{client_name}] {method_name}: 异常 - {str(e)}")
            self.failed_tests.append(f"{client_name}.{method_name}")
            return {'success': False, 'error': str(e)}
    
    def test_single_client(self, client_name):
        """测试单个平台客户端"""
        if client_name not in self.clients:
            print(f"❌ 未知平台: {client_name}")
            return
        
        client = self.clients[client_name]
        song_id = self.song_ids.get(client_name, '1')
        playlist_id = self.playlist_ids.get(client_name, '1')
        
        print("=" * 60)
        print(f"🎵 测试平台: {client.platform_name}")
        print("=" * 60)
        
        print("\n🔍 测试搜索功能")
        print("-" * 40)
        self.test_results[f"{client_name}_search"] = self.run_test(
            client_name, client, 'search', client.search, '陈楚生', limit=3
        )
        
        print("\n📋 测试歌单搜索")
        print("-" * 40)
        self.test_results[f"{client_name}_search_playlist"] = self.run_test(
            client_name, client, 'search_playlist', client.search_playlist, '华语流行', limit=3
        )
        
        print("\n🔗 测试获取歌曲URL")
        print("-" * 40)
        self.test_results[f"{client_name}_get_song_url"] = self.run_test(
            client_name, client, 'get_song_url', client.get_song_url, song_id, 'high'
        )
        
        print("\n🎶 测试获取歌曲信息")
        print("-" * 40)
        self.test_results[f"{client_name}_get_song_info"] = self.run_test(
            client_name, client, 'get_song_info', client.get_song_info, song_id
        )
        
        print("\n📝 测试获取歌词")
        print("-" * 40)
        self.test_results[f"{client_name}_get_lyric"] = self.run_test(
            client_name, client, 'get_lyric', client.get_lyric, song_id
        )
        
        print("\n📁 测试获取歌单")
        print("-" * 40)
        self.test_results[f"{client_name}_get_playlist"] = self.run_test(
            client_name, client, 'get_playlist', client.get_playlist, playlist_id
        )
        
        print("\n🏢 测试平台信息")
        print("-" * 40)
        result = client.get_platform_info()
        if isinstance(result, dict) and 'id' in result and 'name' in result:
            print(f"✅ [{client_name}] get_platform_info: {result}")
        else:
            print(f"❌ [{client_name}] get_platform_info: 失败")
            self.failed_tests.append(f"{client_name}.get_platform_info")
    
    def test_all_clients(self):
        """测试所有客户端"""
        print("=" * 60)
        print("🎵 音乐客户端API测试")
        print("=" * 60)
        
        print("\n🔍 测试搜索功能")
        print("-" * 40)
        for name, client in self.clients.items():
            self.test_results[f"{name}_search"] = self.run_test(
                name, client, 'search', client.search, '陈楚生', limit=3
            )
        
        print("\n📋 测试歌单搜索")
        print("-" * 40)
        for name, client in self.clients.items():
            self.test_results[f"{name}_search_playlist"] = self.run_test(
                name, client, 'search_playlist', client.search_playlist, '华语流行', limit=3
            )
        
        print("\n🔗 测试获取歌曲URL")
        print("-" * 40)
        for name, client in self.clients.items():
            song_id = self.song_ids.get(name, '1')
            self.test_results[f"{name}_get_song_url"] = self.run_test(
                name, client, 'get_song_url', client.get_song_url, song_id, 'high'
            )
        
        print("\n🎶 测试获取歌曲信息")
        print("-" * 40)
        for name, client in self.clients.items():
            song_id = self.song_ids.get(name, '1')
            self.test_results[f"{name}_get_song_info"] = self.run_test(
                name, client, 'get_song_info', client.get_song_info, song_id
            )
        
        print("\n📝 测试获取歌词")
        print("-" * 40)
        for name, client in self.clients.items():
            song_id = self.song_ids.get(name, '1')
            self.test_results[f"{name}_get_lyric"] = self.run_test(
                name, client, 'get_lyric', client.get_lyric, song_id
            )
        
        print("\n📁 测试获取歌单")
        print("-" * 40)
        for name, client in self.clients.items():
            playlist_id = self.playlist_ids.get(name, '1')
            self.test_results[f"{name}_get_playlist"] = self.run_test(
                name, client, 'get_playlist', client.get_playlist, playlist_id
            )
        
        print("\n🏢 测试平台信息")
        print("-" * 40)
        for name, client in self.clients.items():
            result = client.get_platform_info()
            if isinstance(result, dict) and 'id' in result and 'name' in result:
                print(f"✅ [{name}] get_platform_info: {result}")
            else:
                print(f"❌ [{name}] get_platform_info: 失败")
                self.failed_tests.append(f"{name}.get_platform_info")
        
        print("\n🗂️ 测试总控客户端")
        print("-" * 40)
        platforms = music_client.get_platforms()
        if isinstance(platforms, list) and len(platforms) > 0:
            print(f"✅ music_client.get_platforms: {len(platforms)} 个平台")
            for p in platforms:
                print(f"   - {p.get('label', '')}")
        else:
            print("❌ music_client.get_platforms: 失败")
            self.failed_tests.append("music_client.get_platforms")
        
        result = music_client.search('陈楚生', platform='netease', limit=3)
        if isinstance(result, list) and len(result) > 0:
            print(f"✅ music_client.search: 成功 ({len(result)} 条结果)")
        else:
            print("❌ music_client.search: 失败")
            self.failed_tests.append("music_client.search")
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        
        total_tests = len(self.test_results) + len(self.clients)
        passed_tests = sum(1 for r in self.test_results.values() if r.get('success')) + \
                       len(self.clients) - len([t for t in self.failed_tests if t.endswith('.get_platform_info')])
        
        print(f"\n总测试数: {total_tests}")
        print(f"通过数: {passed_tests}")
        print(f"失败数: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print("\n❌ 失败的测试:")
            for test in self.failed_tests:
                print(f"   - {test}")
        else:
            print("\n🎉 所有测试通过！")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='测试音乐客户端API')
    parser.add_argument('--platform', '-p', type=str, default='netease',
                        help='指定测试平台: netease, qq, bodian, kugou, all')
    args = parser.parse_args()
    
    tester = APITester()
    
    if args.platform == 'all':
        tester.test_all_clients()
    else:
        tester.test_single_client(args.platform)
    
    tester.print_summary()
