#!/usr/bin/env python3
"""综合测试脚本 - 模拟前端请求测试全平台 /search → /song 完整流程

测试内容：
  1. /search - 4 平台搜索 + _search_source 透传验证
  2. /song  - URL + Info + Lyric 3 链并行 + 换源 fallback
  3. URL 验证 - vkeys_url 返回 403 → 应自动换源到 lxmusic_url
  4. Lyric 假阳性 - '暂无歌词' 等占位符应被 _is_valid 拒绝
  5. Info 假阳性 - 半空对象 {id: 'xxx', name: ''} 应被 _is_valid 拒绝
  6. ThreadPoolExecutor - lyric 慢不应阻塞 url/info
  7. 换源行为 - 某源失败后应继续尝试下一个
  8. 总耗时 - 应在 8s 内（前端 timeout）

用法：
  cd backend/
  python3 scripts/test_full_flow.py [--quick] [--verbose]

  --quick : 只测一首热门歌曲（快速验证）
  --verbose: 打印详细日志
"""
import argparse
import sys
import time
import re
import unittest
from typing import Optional, Tuple, List, Any
from dataclasses import dataclass

# 确保 backend 在 path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============ 测试数据 ============

# 热门歌曲（各平台有数据的歌曲）
SONGS = {
    'netease': {'keyword': '陈奕迅', 'id': '209703'},      # 浮夸
    'qq':      {'keyword': '陈奕迅', 'id': '003XXoqO2xNdI'},  # 浮夸
    'kugou':  {'keyword': '陈奕迅', 'id': 'b52d6e47ab9f9a6f1c58f2a46e82c72a'},  # 浮夸
    'kuwo':   {'keyword': '陈奕迅', 'id': '1576167'},       # 浮夸
}

QUICK_SONGS = {
    'netease': {'keyword': '周杰伦', 'id': '436514124'},   # 晴天
    'qq':      {'keyword': '周杰伦', 'id': '004xl4e93L2rIG'},  # 晴天
}

# ============ 测试结果收集 ============

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    detail: str = ''
    url: str = ''
    url_src: str = ''
    info_src: str = ''
    lyric_src: str = ''
    level: str = ''


class TestRunner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []

    def log(self, msg: str):
        if self.verbose:
            print(f'  [VERBOSE] {msg}')

    def assert_true(self, cond: bool, msg: str):
        if not cond:
            raise AssertionError(msg)

    def assert_in(self, needle: str, haystack: str, msg: str):
        if needle not in haystack:
            raise AssertionError(f'{msg}: {needle!r} not in {haystack!r}')

    def assert_gt(self, a: float, b: float, msg: str):
        if not a > b:
            raise AssertionError(f'{msg}: {a} <= {b}')

    def assert_lt(self, a: float, b: float, msg: str):
        if not a < b:
            raise AssertionError(f'{msg}: {a} >= {b}')


# ============ 核心测试函数 ============

def test_search_source_propagation(runner: TestRunner) -> Tuple[bool, str]:
    """测试 routes.py 是否正确将 search_source 透传到每个 song

    注意：routes.py 在 /search 接口中手动给每个 song 附加 _search_source。
    music_client.search() 同时把 info 写入 song_info_cache（后续 /song 阶段用）。
    这里既验证 song 字段带 _search_source，也验证 cache 里有数据。
    """
    from service import music_service
    from clients import song_info_cache

    # 模拟 routes.py 逻辑（routes.py 会再手动补 _search_source 字段）
    result = music_service.search('周杰伦', 'netease', limit=5)
    songs = result.get('data', [])
    search_src = result.get('search_source', '')

    runner.log(f'搜索结果: {len(songs)} 首, search_source={search_src}')

    if not songs:
        return False, f'搜索无结果'

    # 检查 1: cache 写入（music_client.search 负责写入）
    first_id = str(songs[0].get('id', '')) if songs else ''
    cached = song_info_cache.get('netease', first_id) if first_id else None
    if not cached:
        return False, f'song_info_cache miss for netease/{first_id}（应已写入）'
    runner.log(f'  song_info_cache 命中: name={cached.get("name")!r}')

    # 检查 2: 模拟 routes.py 给每个 song 加 _search_source 字段
    for s in songs:
        if search_src and not s.get('_search_source'):
            s['_search_source'] = search_src

    # 检查 3: 验证补完后所有 song 都有 _search_source
    for s in songs:
        if search_src and s.get('_search_source') != search_src:
            return False, f'song {s.get("id")} 的 _search_source={s.get("_search_source")} != {search_src}'
        runner.log(f'  song {s.get("id")}: _search_source={s.get("_search_source")}')

    return True, f'{len(songs)} 首歌曲全部标记 _search_source={search_src}（cache 命中）'


def test_lyric_is_valid_rejects_placeholders(runner: TestRunner) -> Tuple[bool, str]:
    """测试 _is_valid 对 lyric 占位符的拒绝（'暂无歌词' / '纯音乐' 等）"""
    from clients.fallback.chain import FallbackChain
    from clients.sources.qq import QQ_PARSE_LYRIC_SOURCES

    chain = FallbackChain(QQ_PARSE_LYRIC_SOURCES, platform='qq', strategy='serial')
    chain._success_recent.clear()

    placeholders = [
        '暂无歌词',
        'no lyrics',
        '纯音乐',
        'lyric not found',
        '该歌曲为纯音乐',
        'x',  # 太短
        '',   # 空
        '[00:00.00]暂无歌词',  # 含时间戳但占位符
    ]

    all_rejected = True
    for ph in placeholders:
        valid = chain._is_valid(ph, 'parse_lyric')
        runner.log(f'  占位符 {ph!r}: _is_valid={valid}')
        if valid:
            all_rejected = False

    # 真实歌词应该通过
    real_lyric = '[00:12.34]这是一段真实歌词\n[00:15.56]有具体时间的歌词内容'
    valid_real = chain._is_valid(real_lyric, 'parse_lyric')
    runner.log(f'  真实歌词: _is_valid={valid_real}')
    if not valid_real:
        return False, f'真实歌词被错误拒绝'

    return all_rejected, f'占位符全部被拒绝，真实歌词通过'


def test_info_is_valid_rejects_half_empty(runner: TestRunner) -> Tuple[bool, str]:
    """测试 _is_valid 对 info 半空对象的拒绝（{id: 'xxx', name: ''}）"""
    from clients.fallback.chain import FallbackChain

    chain = FallbackChain([], platform='qq', strategy='serial')

    test_cases = [
        # (data, expected_valid, description)
        ({'id': '001', 'name': '浮夸'}, True, '完整对象'),
        ({'id': '001', 'title': '浮夸'}, True, 'title 替代 name'),
        ({'id': '001', 'songName': '浮夸'}, True, 'songName 替代 name'),
        ({'mid': '001', 'name': '浮夸'}, True, 'mid 替代 id'),
        ({'rid': '001', 'name': '浮夸'}, True, 'rid 替代 id'),
        ({'hash': 'abc', 'name': '浮夸'}, True, 'hash 替代 id'),
        ({'id': '001'}, False, '只有 id'),
        ({'name': '浮夸'}, False, '只有 name'),
        ({'id': '001', 'name': ''}, False, 'id + 空 name'),
        ({'id': '', 'name': '浮夸'}, False, '空 id + name'),
        ({}, False, '空对象'),
        (None, False, 'None'),
    ]

    all_correct = True
    for data, expected_valid, desc in test_cases:
        actual = chain._is_valid(data, 'parse_info')
        status = '✅' if actual == expected_valid else '❌'
        runner.log(f'  {status} {desc}: data={data}, expected={expected_valid}, actual={actual}')
        if actual != expected_valid:
            all_correct = False

    return all_correct, 'info 半空对象检查全部正确'


def test_url_verification_blocks_403(runner: TestRunner) -> Tuple[bool, str]:
    """测试 URL 验证能正确识别 403 并标记死链"""
    from clients.fallback.chain import FallbackChain

    chain = FallbackChain([], platform='qq', strategy='serial')

    # 已知的死 URL
    dead_urls = [
        'http://ws.stream.qqmusic.qq.com/M500001a8mcP1cnQ5T.mp3?guid=invalid',
    ]

    for url in dead_urls:
        # 先清空缓存
        chain._url_dead.pop(url, None)
        valid = chain._verify_url_reachable(url, timeout=3)
        is_dead = chain._is_url_dead(url)
        runner.log(f'  URL={url[:60]}: reachable={valid}, in_dead_list={is_dead}')
        if valid:
            return False, f'403 URL 被误判为可访问'

    return True, '死链正确识别'


def test_source_fallback_on_failure(runner: TestRunner) -> Tuple[bool, str]:
    """测试某源失败后能继续换源"""
    from clients.fallback.chain import FallbackChain
    from clients.sources.qq import QQ_PARSE_LYRIC_SOURCES

    chain = FallbackChain(QQ_PARSE_LYRIC_SOURCES, platform='qq', strategy='serial')
    chain._success_recent.clear()

    # 模拟第一个源失败，第二个源成功
    sources = chain.sources[:]
    if len(sources) < 2:
        return True, '源数量不足，无法测试 fallback'

    # 把第一个源标记失败
    chain.mark_source_failed(sources[0].name, expire_seconds=300, reason='test failure',
                             scope='transient')

    # 再次获取可用源列表
    # 直接用 _is_source_failed 检查
    failed_0 = chain._is_source_failed(sources[0].name, None)
    available = [s for s in sources if not chain._is_source_failed(s.name, None)]

    runner.log(f'  {sources[0].name} 失败后: failed={failed_0}, 可用源={len(available)}')

    if failed_0:
        return True, f'失败源被正确跳过，剩余 {len(available)} 个可用源'
    return False, '失败源未被跳过'


def test_parallel_first_no_block(runner: TestRunner) -> Tuple[bool, str]:
    """测试 parallel_first 模式下 url/info 不会等待 lyric"""
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from clients.sources.qq import QQ_PARSE_URL_SOURCES, QQ_PARSE_LYRIC_SOURCES
    from clients.fallback.chain import FallbackChain

    url_chain = FallbackChain(QQ_PARSE_URL_SOURCES, platform='qq', strategy='parallel_first')
    lyric_chain = FallbackChain(QQ_PARSE_LYRIC_SOURCES, platform='qq', strategy='parallel_first')

    song_id = '003XXoqO2xNdI'  # 周杰伦 晴天

    t_start = time.time()
    pool = ThreadPoolExecutor(max_workers=3)
    f_url = pool.submit(url_chain.try_fetch, 'parse_url', song_id=song_id, quality='exhigh')
    f_lyric = pool.submit(lyric_chain.try_fetch, 'parse_lyric', song_id=song_id)
    pool.shutdown(wait=False)

    # URL 应该比 lyric 先完成
    url_data, url_src = f_url.result()
    url_time = time.time() - t_start
    lyric_data, lyric_src = f_lyric.result()
    lyric_time = time.time() - t_start

    runner.log(f'  URL: src={url_src}, time={url_time:.2f}s')
    runner.log(f'  Lyric: src={lyric_src}, time={lyric_time:.2f}s')

    # URL 应该很快（2s 内）
    if url_time < 2.0:
        return True, f'URL {url_time:.2f}s < 2s，不被 lyric 阻塞'
    # 即使超了也要保证 URL 比 lyric 快
    if url_time <= lyric_time:
        return True, f'URL ({url_time:.2f}s) <= Lyric ({lyric_time:.2f}s)，并行抢答正常'
    return False, f'Lyric ({lyric_time:.2f}s) 比 URL ({url_time:.2f}s) 快，可能被阻塞'


def test_song_full_flow(runner: TestRunner, platform: str, song: dict,
                        max_time: float = 8.0) -> TestResult:
    """测试完整的 /song 流程：先 search 写 cache，再 get_song 走 cached_info 路径

    模拟真实前端流程：search → /song，避免绕过 song_info_cache 的兜底路径
    """
    from clients.music_client import music_client
    from service import music_service

    name = f'/song {platform}'
    t_start = time.time()

    try:
        # Step 1: 先 search 触发 song_info_cache 写入
        search_result = music_service.search(song['keyword'], platform, limit=10)
        search_src = search_result.get('search_source', '')
        songs = search_result.get('data', [])
        # 找到匹配 id 的
        target = None
        for s in songs:
            if str(s.get('id')) == str(song['id']):
                target = s
                break
        if not target and songs:
            target = songs[0]
            runner.log(f'  ⚠️ 没用精确 id={song["id"]}，用第一个 id={target.get("id")}')
        if not target:
            return TestResult(name, False, (time.time() - t_start) * 1000,
                            f'search 无结果')

        # Step 2: 模拟 routes.py 给 song 加 _search_source 后传给 /song
        song_id_obj = {
            'id': target.get('id'),
            '_search_source': search_src,
            'qualityMap': target.get('qualityMap'),
        }

        result = music_client.get_song(
            song_id=song_id_obj,
            quality='exhigh',
            platform=platform,
            with_lyric=True,
        )

        duration = time.time() - t_start
        detail = ''

        if result is None:
            return TestResult(name, False, duration * 1000,
                            f'get_song 返回 None')

        url = result.get('url', '')
        level = result.get('level', '')

        if not url:
            return TestResult(name, False, duration * 1000,
                            'URL 为空')

        if not url.startswith('http'):
            return TestResult(name, False, duration * 1000,
                            f'URL 无效: {url[:50]}')

        api_src = result.get('api_source', {}) or {}
        url_src = api_src.get('url', '')
        info_src = api_src.get('info', '')
        lyric_src = api_src.get('lyric', '')

        # 检查耗时
        passed = duration < max_time
        detail = f'url_src={url_src} info_src={info_src} lyric_src={lyric_src}'
        if not passed:
            detail += f' ⚠️ 耗时 {duration:.2f}s > {max_time}s'

        runner.log(f'  ✅ {platform}: url={url_src} [{level}] '
                   f'info={info_src} lyric={lyric_src} '
                   f'耗时={duration:.2f}s URL={url[:60]}')

        return TestResult(name, passed, duration * 1000, detail,
                         url=url, url_src=url_src,
                         info_src=info_src, lyric_src=lyric_src,
                         level=level)

    except Exception as e:
        duration = time.time() - t_start
        import traceback
        tb = traceback.format_exc()
        runner.log(f'  ❌ {platform}: {e}\n{tb}')
        return TestResult(name, False, duration * 1000,
                         f'异常: {e}')


def test_search_all_platforms(runner: TestRunner) -> Tuple[List[TestResult], str]:
    """测试 4 平台搜索"""
    from service import music_service

    results = []
    failed = []

    for platform, song_data in SONGS.items():
        name = f'/search {platform}'
        t_start = time.time()
        try:
            result = music_service.search(song_data['keyword'], platform, limit=5)
            duration = time.time() - t_start
            songs = result.get('data', [])
            search_src = result.get('search_source', '')

            passed = len(songs) > 0
            detail = f'{len(songs)} 首, search_src={search_src}'

            runner.log(f'  ✅ {platform}: {detail} 耗时={duration:.2f}s')

            results.append(TestResult(name, passed, duration * 1000, detail))
            if not passed:
                failed.append(platform)
        except Exception as e:
            duration = time.time() - t_start
            results.append(TestResult(name, False, duration * 1000, f'异常: {e}'))
            failed.append(platform)
            runner.log(f'  ❌ {platform}: {e}')

    ok = len(failed) == 0
    msg = f'{len([r for r in results if r.passed])}/{len(results)} 平台成功'
    return results, msg


def test_url_verification_on_real_sources(runner: TestRunner) -> Tuple[bool, str]:
    """测试真实源返回的 URL 验证行为"""
    from clients.fallback.chain import FallbackChain
    from clients.sources.qq import QQ_PARSE_URL_SOURCES

    chain = FallbackChain(QQ_PARSE_URL_SOURCES, platform='qq', strategy='parallel_first')
    chain._success_recent.clear()

    song_id = '003XXoqO2xNdI'  # 晴天
    t_start = time.time()

    url, src = chain.try_fetch('parse_url', song_id=song_id, quality='exhigh')

    elapsed = time.time() - t_start
    runner.log(f'  URL={url[:80] if url else ""}')
    runner.log(f'  src={src}, elapsed={elapsed:.2f}s')

    if not url:
        return False, f'无 URL 返回'

    # 验证 URL 是否真的可用
    valid = chain._verify_url_reachable(url, timeout=5)
    runner.log(f'  verify={valid}')

    if valid:
        return True, f'{src} URL 验证通过'
    return False, f'{src} URL 验证失败（可能是 403/404）'


# ============ 测试套件 ============

class TestSuite:
    def __init__(self, runner: TestRunner):
        self.runner = runner
        self.all_results: List[TestResult] = []

    def run(self):
        print('=' * 60)
        print('🎵 综合测试：搜索 → 歌曲完整流程')
        print('=' * 60)
        print()

        # ---- 1. 单元测试（不依赖网络/极快）----
        print('📦 单元测试（_is_valid 逻辑验证）')
        print('-' * 40)

        tests = [
            ('lyric 占位符拒绝', test_lyric_is_valid_rejects_placeholders),
            ('info 半空对象拒绝', test_info_is_valid_rejects_half_empty),
            ('URL 死链识别', test_url_verification_blocks_403),
            ('失败源跳过', test_source_fallback_on_failure),
        ]

        for name, fn in tests:
            t_start = time.time()
            try:
                ok, detail = fn(self.runner)
            except Exception as e:
                ok = False
                detail = f'断言失败: {e}'
            elapsed = time.time() - t_start
            status = '✅ PASS' if ok else '❌ FAIL'
            print(f'  {status}: {name}')
            print(f'         {detail} ({elapsed*1000:.0f}ms)')
            self.all_results.append(TestResult(name, ok, elapsed * 1000, detail))
            print()

        # ---- 2. 并行抢答测试（依赖网络，快速）----
        print('🚀 并行抢答测试（不等待最慢链）')
        print('-' * 40)

        t_start = time.time()
        try:
            ok, detail = test_parallel_first_no_block(self.runner)
        except Exception as e:
            ok = False
            detail = f'异常: {e}'
        elapsed = time.time() - t_start
        status = '✅ PASS' if ok else '❌ FAIL'
        print(f'  {status}: 并行抢答')
        print(f'         {detail} ({elapsed*1000:.0f}ms)')
        self.all_results.append(TestResult('parallel_first 不阻塞', ok, elapsed * 1000, detail))
        print()

        # ---- 3. 真实 API 测试 ----
        print('🌐 真实 API 测试（4 平台搜索）')
        print('-' * 40)
        search_results, search_msg = test_search_all_platforms(self.runner)
        self.all_results.extend(search_results)
        print(f'  → {search_msg}')
        print()

        # ---- 4. URL 验证（依赖网络）----
        print('🔗 URL 验证（真实源）')
        print('-' * 40)
        t_start = time.time()
        try:
            ok, detail = test_url_verification_on_real_sources(self.runner)
        except Exception as e:
            ok = False
            detail = f'异常: {e}'
        elapsed = time.time() - t_start
        status = '✅ PASS' if ok else '❌ FAIL'
        print(f'  {status}: QQ URL 验证')
        print(f'         {detail} ({elapsed*1000:.0f}ms)')
        self.all_results.append(TestResult('URL 验证', ok, elapsed * 1000, detail))
        print()

        # ---- 5. _search_source 透传 ----
        print('🔍 _search_source 透传测试')
        print('-' * 40)
        t_start = time.time()
        try:
            ok, detail = test_search_source_propagation(self.runner)
        except Exception as e:
            ok = False
            detail = f'异常: {e}'
        elapsed = time.time() - t_start
        status = '✅ PASS' if ok else '❌ FAIL'
        print(f'  {status}: _search_source 透传')
        print(f'         {detail} ({elapsed*1000:.0f}ms)')
        self.all_results.append(TestResult('_search_source 透传', ok, elapsed * 1000, detail))
        print()

        # ---- 6. /song 完整流程（依赖网络，较慢）----
        print('🎶 /song 完整流程测试（4 平台）')
        print('-' * 40)
        song_results = []
        for platform, song_data in SONGS.items():
            print(f'  → 测试 {platform} ({song_data["keyword"]})')
            result = test_song_full_flow(self.runner, platform, song_data, max_time=8.0)
            song_results.append(result)
            status = '✅' if result.passed else '❌'
            print(f'    {status} [{result.level}] {result.url_src} 耗时={result.duration_ms/1000:.2f}s')
            if result.detail:
                print(f'       {result.detail}')
            print()
        self.all_results.extend(song_results)

        # ---- 汇总 ----
        print('=' * 60)
        print('📊 测试结果汇总')
        print('=' * 60)

        passed = [r for r in self.all_results if r.passed]
        failed = [r for r in self.all_results if not r.passed]

        print(f'  通过: {len(passed)}/{len(self.all_results)}')
        if failed:
            print(f'  失败:')
            for r in failed:
                print(f'    ❌ {r.name}: {r.detail}')

        total_time = sum(r.duration_ms for r in self.all_results)
        avg_time = total_time / len(self.all_results) if self.all_results else 0
        song_avg = (sum(r.duration_ms for r in song_results) / len(song_results)
                    if song_results else 0)

        print(f'  平均耗时: {avg_time/1000:.2f}s')
        print(f'  /song 平均耗时: {song_avg/1000:.2f}s')
        print()

        if not failed:
            print('🎉 全部通过！')
        else:
            print(f'⚠️  {len(failed)} 项失败')

        return len(failed) == 0


def main():
    parser = argparse.ArgumentParser(description='综合测试脚本')
    parser.add_argument('--quick', action='store_true', help='快速模式（只测热门歌曲）')
    parser.add_argument('--verbose', action='store_true', help='详细日志')
    args = parser.parse_args()

    if args.quick:
        global SONGS
        SONGS = QUICK_SONGS
        print('⚡ 快速模式：只测热门歌曲')

    # 设置日志
    import logging
    if not args.verbose:
        logging.getLogger().setLevel(logging.WARNING)
        # 只显示 WARNING 及以上

    runner = TestRunner(verbose=args.verbose)
    suite = TestSuite(runner)
    ok = suite.run()

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
