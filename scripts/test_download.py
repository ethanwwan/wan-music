#!/usr/bin/env python3
"""模拟前端下载队列，测试后端重试/换源逻辑

测试 2 个场景：
  1. 单曲下载（QQ 平台 lossless）
  2. 批量下载（3 首歌，QQ 平台 lossless）

观察后端日志：
  - 是否重试（外层重试 1 次）
  - 是否自动换源（mark_source_failed + chain skip）
  - 是否优先成功源（mark_source_success 跨歌曲生效）
  - 文件大小是否正常（FLAC lossless 通常 20-50MB）
"""
import json
import time
import requests
from datetime import datetime

BASE = 'http://localhost:5005'
LOG_FILE = '/Users/Awan/Public/Repository/wan-music/backend/logs/wan-music.log'

def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}')

def search_song(keyword, source, limit=3):
    """搜索歌曲（模仿前端 /search）"""
    r = requests.post(f'{BASE}/search',
                      json={'keyword': keyword, 'source': source, 'limit': limit},
                      timeout=120)
    r.raise_for_status()
    data = r.json()['data']['data']
    log(f'搜索 "{keyword}" source={source}: 找到 {len(data)} 首')
    return data

def start_batch(songs, quality='lossless', name='test'):
    """启动批量下载（模仿前端 /download/batch/start）

    字段约定（用户定义）：
      item['source']  =  platform：4 大平台名（netease/qq/kugou/kuwo）
      song_info['api_source'] = source：底层 API 域名（vkeys_url 等）
      前端 buildDownloadItem 用 'source' 字段名传 platform
    """
    items = []
    for s in songs:
        items.append({
            'id': s['id'],
            'name': s['name'],
            'artist': s['artists'],
            'source': s['source'],   # source 字段 = platform（4 大平台名）
            'quality': quality,
            'picUrl': s.get('picUrl', ''),
            'album': s.get('album', ''),
            'duration': s.get('duration', 0),
        })
    r = requests.post(f'{BASE}/download/batch/start',
                      json={'name': name, 'items': items},
                      timeout=30)
    r.raise_for_status()
    result = r.json()['data']
    log(f'批量下载已启动: task_id={result["task_id"]}, songs={len(items)}')
    return result['task_id']

def poll_progress(task_id, max_wait=60, interval=2):
    """轮询下载进度（模仿前端 /download/batch/list + /progress）"""
    log(f'开始轮询 task={task_id} (max_wait={max_wait}s, interval={interval}s)')
    start = time.time()
    last_progress = -1
    while time.time() - start < max_wait:
        r = requests.get(f'{BASE}/download/batch/list', timeout=10)
        r.raise_for_status()
        tasks = r.json()['data']
        task = next((t for t in tasks if t.get('task_id') == task_id or t.get('id') == task_id), None)
        if not task:
            log(f'  task 不存在了？')
            return None
        prog = task.get('progress', 0)
        if prog != last_progress:
            log(f'  status={task.get("status")}, progress={prog*100:.0f}%, '
                f'completed={task.get("completed", 0)}/{task.get("total", 0)}')
            last_progress = prog
        if task.get('status') in ('done', 'error', 'cancelled'):
            log(f'任务结束: status={task["status"]}')
            return task
        time.sleep(interval)
    log('轮询超时')
    return None

def get_file_info(task_id):
    """拿到下载的 zip 文件信息"""
    # 用进度接口拿 songs 列表
    r = requests.get(f'{BASE}/download/batch/progress/{task_id}', timeout=5)
    # 这个是 SSE 流，普通 GET 拿不到。但 list 已经返了 status。
    # 实际文件大小要看 task 内部字段
    return None

def get_log_lines(after_line, pattern=None):
    """读后端日志中 after_line 行之后的所有行（可选 pattern 过滤）"""
    with open(LOG_FILE) as f:
        lines = f.readlines()
    matched = lines[after_line:]
    if pattern:
        matched = [l for l in matched if pattern in l]
    return matched

def scenario_single():
    """场景 1：单曲下载（netease 平台 lossless）"""
    log('='*70)
    log('场景 1: 单曲下载（netease lossless）')
    log('='*70)

    # 记下当前日志行号
    with open(LOG_FILE) as f:
        before = sum(1 for _ in f)

    # 搜索陈楚生的歌
    songs = search_song('陈楚生', 'netease', limit=1)
    if not songs:
        log('搜索无结果，跳过')
        return
    song = songs[0]
    log(f'  选定歌曲: {song["name"]} (id={song["id"]}) - {song["artists"]}')

    # 启动下载
    task_id = start_batch([song], quality='lossless', name=f'single-{song["id"]}')

    # 轮询
    task = poll_progress(task_id, max_wait=120, interval=2)
    if task:
        # 检查 songs 列表
        songs_in_task = task.get('songs', [])
        log(f'下载结果:')
        for s in songs_in_task:
            size = s.get('file_size', 0)
            status = s.get('status', '?')
            level = s.get('level', '?')
            api = s.get('api_source', {})
            if isinstance(api, dict):
                api = api.get('url', '?')
            log(f'  {s.get("name")}: status={status}, level={level}, '
                f'size={size/1024/1024:.1f} MB, api_source={api}')

    # 收集这个场景的日志
    log('--- 本场景后端日志（chain + service）---')
    matched = get_log_lines(before, pattern='chain')
    matched += get_log_lines(before, pattern='批量下载')
    matched += get_log_lines(before, pattern='确定性')
    matched += get_log_lines(before, pattern='临时禁用')
    matched += get_log_lines(before, pattern='最近成功')
    for l in matched[-30:]:  # 最多 30 条
        print('  ' + l.rstrip())

def scenario_batch():
    """场景 2：批量下载 3 首 netease 歌曲（验证 mark_source_success 跨歌曲生效）"""
    log('='*70)
    log('场景 2: 批量下载 3 首（netease lossless）')
    log('='*70)

    with open(LOG_FILE) as f:
        before = sum(1 for _ in f)

    # 搜索陈楚生的歌（拿 3 首）
    songs = search_song('陈楚生', 'netease', limit=5)
    if not songs or len(songs) < 3:
        log('搜索结果不足 3 首，跳过')
        return
    selected = songs[:3]
    log(f'  选定 3 首歌: {[s["name"] for s in selected]}')

    # 启动批量下载
    task_id = start_batch(selected, quality='lossless', name='batch-test')

    # 轮询
    task = poll_progress(task_id, max_wait=180, interval=2)
    if task:
        songs_in_task = task.get('songs', [])
        log(f'批量下载结果:')
        for s in songs_in_task:
            size = s.get('file_size', 0)
            status = s.get('status', '?')
            level = s.get('level', '?')
            api = s.get('api_source', {})
            if isinstance(api, dict):
                api = api.get('url', '?')
            log(f'  {s.get("name")}: status={status}, level={level}, '
                f'size={size/1024/1024:.1f} MB, api_source={api}')

    # 收集日志
    log('--- 本场景后端日志（chain + service）---')
    matched = get_log_lines(before, pattern='chain')
    matched += get_log_lines(before, pattern='批量下载')
    matched += get_log_lines(before, pattern='确定性')
    matched += get_log_lines(before, pattern='临时禁用')
    matched += get_log_lines(before, pattern='最近成功')
    for l in matched[-50:]:
        print('  ' + l.rstrip())

def main():
    log(f'开始测试: BASE={BASE}, LOG={LOG_FILE}')
    log(f'后端日志当前大小: {sum(1 for _ in open(LOG_FILE))} 行')

    scenario_single()
    time.sleep(3)
    scenario_batch()

    log('='*70)
    log('测试完成')
    log('='*70)
    log('后端日志完整路径: ' + LOG_FILE)

if __name__ == '__main__':
    main()
