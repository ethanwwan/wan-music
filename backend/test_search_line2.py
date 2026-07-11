"""测试线路二（musicdl）搜索功能

测试所有 4 个平台（netease/qq/kugou/kuwo）的搜索接口：
  - GET /search/debug (JSON 调试接口)
  - GET /search/sse    (SSE 流式，前端线路二实际调用)
  - POST /search       (线路一对比参考)

用法：
  python backend/test_search_line2.py
  python backend/test_search_line2.py --keyword 周杰伦
  python backend/test_search_line2.py --platform netease
  python backend/test_search_line2.py --verbose   # 显示原始响应
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse


BACKEND_URL = 'http://127.0.0.1:5005'
TIMEOUT = 120
PLATFORMS = ['netease', 'qq', 'kugou', 'kuwo']
KEYWORD = '海阔天空'


def _http_get(url: str, timeout: int = TIMEOUT) -> tuple[int, str]:
    """发起 GET 请求，返回 (status_code, body)"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return e.code, body
    except Exception as e:
        return 0, str(e)


def _http_post(url: str, data: dict, timeout: int = TIMEOUT) -> tuple[int, str]:
    """发起 POST 请求，返回 (status_code, body)"""
    try:
        body_bytes = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body_bytes,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return e.code, body
    except Exception as e:
        return 0, str(e)


def parse_sse(body: str) -> list[dict]:
    """解析 SSE 文本，返回 result 事件的 song 列表"""
    songs = []
    for block in body.strip().split('\n\n'):
        lines = block.strip().split('\n')
        event_type = ''
        data_str = ''
        for line in lines:
            line = line.strip()
            if line.startswith('event:'):
                event_type = line[len('event:'):].strip()
            elif line.startswith('data:'):
                data_str = line[len('data:'):].strip()
        if event_type == 'result' and data_str:
            try:
                data = json.loads(data_str)
                if 'song' in data:
                    songs.append(data['song'])
            except json.JSONDecodeError:
                pass
    return songs


def check_song(song: dict, platform: str) -> list[str]:
    """检查单首歌曲字段完整性，返回问题列表"""
    issues = []

    fields = [('id', str), ('name', str), ('artist', str),
              ('qualityMap', dict), ('bestQuality', str), ('source', str)]
    for field, ftype in fields:
        val = song.get(field)
        if val is None or (ftype == str and val == ''):
            issues.append(f'缺少 {field}')

    if song.get('source') != platform:
        issues.append(f'source 不一致(期望={platform}, 实际={song.get("source")})')

    qm = song.get('qualityMap', {})
    if not qm:
        issues.append('qualityMap 为空')
    else:
        for q, info in qm.items():
            if not isinstance(info, dict):
                issues.append(f'qualityMap[{q}] 不是 dict')
                break
            if 'br' not in info:
                issues.append(f'qualityMap[{q}] 缺少 br')
                break

    return issues


def print_songs(songs: list[dict], platform: str, label: str):
    """打印歌曲列表摘要"""
    if not songs:
        print(f'    {label}: 0 条结果')
        return
    print(f'    {label}: {len(songs)} 条结果')
    for i, s in enumerate(songs[:3]):
        q_keys = list(s.get('qualityMap', {}).keys())
        q_str = ', '.join(q_keys) if q_keys else '无'
        artist = s.get('artist', '?') or '?'
        print(f'      [{i+1}] {s.get("name","?"):16s} - {artist:12s}  [{q_str}]')
    if len(songs) > 3:
        print(f'      ... 还有 {len(songs)-3} 条')


def test_debug_endpoint(keyword: str, platform: str, verbose: bool = False):
    """测试 /search/debug (JSON)"""
    url = f'{BACKEND_URL}/search/debug?keyword={urllib.parse.quote(keyword)}&source={platform}'
    start = time.time()
    status, body = _http_get(url)
    elapsed = time.time() - start

    if verbose:
        print(f'      URL: {url}')
        print(f'      HTTP {status}, body({len(body)} bytes)')

    if status != 200:
        return {'status': 'FAIL', 'reason': f'HTTP {status}', 'elapsed': elapsed}

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        return {'status': 'FAIL', 'reason': 'JSON 解析失败', 'elapsed': elapsed}

    count = result.get('search_count', 0)
    songs = result.get('songs', [])

    if 'error' in result:
        return {'status': 'FAIL', 'reason': result['error'], 'elapsed': elapsed, 'count': count}

    issues = []
    if songs:
        issues = check_song(songs[0], platform)

    return {
        'status': 'FAIL' if issues or not songs else 'PASS',
        'reason': '; '.join(issues) if issues else ('空结果' if not songs else ''),
        'elapsed': elapsed,
        'count': count,
        'songs': songs,
    }


def test_sse_endpoint(keyword: str, platform: str, verbose: bool = False):
    """测试 /search/sse (SSE 流式)"""
    url = f'{BACKEND_URL}/search/sse?keyword={urllib.parse.quote(keyword)}&source={platform}&timeout=20'
    start = time.time()
    status, body = _http_get(url)
    elapsed = time.time() - start

    if verbose:
        print(f'      URL: {url}')
        print(f'      HTTP {status}, body({len(body)} bytes)')

    if status != 200:
        return {'status': 'FAIL', 'reason': f'HTTP {status}', 'elapsed': elapsed}

    songs = parse_sse(body)

    issues = []
    if songs:
        issues = check_song(songs[0], platform)

    return {
        'status': 'FAIL' if issues or not songs else 'PASS',
        'reason': '; '.join(issues) if issues else ('空结果' if not songs else ''),
        'elapsed': elapsed,
        'count': len(songs),
        'songs': songs,
    }


def test_line1_endpoint(keyword: str, platform: str, verbose: bool = False):
    """测试 POST /search (线路一，对比参考)"""
    url = f'{BACKEND_URL}/search'
    payload = {'keyword': keyword, 'source': platform, 'limit': 50, 'line': 0}
    start = time.time()
    status, body = _http_post(url, payload)
    elapsed = time.time() - start

    if verbose:
        print(f'      POST /search body: {json.dumps(payload, ensure_ascii=False)}')
        print(f'      HTTP {status}, body({len(body)} bytes)')

    if status != 200:
        return {'status': 'FAIL', 'reason': f'HTTP {status}', 'elapsed': elapsed}

    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        return {'status': 'FAIL', 'reason': 'JSON 解析失败', 'elapsed': elapsed}

    if not result.get('success'):
        msg = result.get('message', '未知错误')
        return {'status': 'FAIL', 'reason': msg, 'elapsed': elapsed}

    inner = result.get('data', {})
    songs = inner.get('data', [])

    return {
        'status': 'PASS' if songs else 'FAIL',
        'reason': '' if songs else '空结果',
        'elapsed': elapsed,
        'count': len(songs),
        'songs': songs,
    }


def run_tests(platform: str, keyword: str, verbose: bool = False) -> tuple[int, int]:
    """运行单个平台的全部测试"""
    passed = 0
    failed = 0

    tests = [
        ('/search/debug (JSON 调试)', test_debug_endpoint),
        ('/search/sse     (SSE 流式)', test_sse_endpoint),
        ('/search POST    (线路一对比)', test_line1_endpoint),
    ]

    print(f'\n  [{platform}]')

    for label, test_fn in tests:
        print(f'    {label} ... ', end='', flush=True)
        result = test_fn(keyword, platform, verbose)
        elapsed = result['elapsed']
        count = result.get('count', 0)

        if result['status'] == 'PASS':
            print(f'✓ ({elapsed:.1f}s, {count} 条)')
            passed += 1
        else:
            reason = result['reason'] or '未知错误'
            print(f'✗ ({elapsed:.1f}s): {reason}')
            failed += 1

        songs = result.get('songs', [])
        if songs:
            for i, s in enumerate(songs[:3]):
                q_keys = list(s.get('qualityMap', {}).keys())
                q_str = ', '.join(q_keys) if q_keys else '无'
                artist = s.get('artist', '?') or '?'
                print(f'        [{i+1}] {s.get("name","?"):16s} - {artist:12s}  [{q_str}]')
            if len(songs) > 3:
                print(f'        ... 还有 {len(songs)-3} 条')
        else:
            # 显示原始响应摘要帮助调试
            if verbose and result.get('status') == 'FAIL':
                print(f'        (详细错误见 verbose 输出)')

    return passed, failed


def main():
    parser = argparse.ArgumentParser(description='测试线路二搜索功能')
    parser.add_argument('--keyword', default=KEYWORD, help=f'搜索关键词（默认: {KEYWORD}）')
    parser.add_argument('--platform', choices=PLATFORMS, help='指定平台（默认全部）')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示原始请求详情')
    args = parser.parse_args()

    print(f'Wan Music - 线路二搜索功能测试')
    print(f'后端地址: {BACKEND_URL}')
    print(f'关键词: "{args.keyword}"')
    print()

    # 后端连通性检查
    print('[0] 后端连通性 ... ', end='', flush=True)
    status, body = _http_get(f'{BACKEND_URL}/config', timeout=5)
    if status == 200:
        print('✓')
    else:
        print(f'✗ HTTP {status}')
        print('请先启动后端: 在 backend/ 目录下执行 python main.py')
        return 1

    platforms = [args.platform] if args.platform else PLATFORMS
    total_pass = 0
    total_fail = 0

    for p in platforms:
        p_pass, p_fail = run_tests(p, args.keyword, args.verbose)
        total_pass += p_pass
        total_fail += p_fail

    print(f'\n{"─"*50}')
    print(f'  最终结果: 通过 {total_pass} / 失败 {total_fail}')
    if total_fail == 0:
        print('  结论: 全部通过 ✓')
    else:
        print(f'  结论: {total_fail} 个测试未通过 — 需要修复后端')
    print()

    return 0 if total_fail == 0 else 1


if __name__ == '__main__':
    import urllib.error
    sys.exit(main())
