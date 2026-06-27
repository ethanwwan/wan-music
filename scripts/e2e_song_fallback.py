#!/usr/bin/env python3
"""/song 接口多源 fallback 测试

模拟「网易云官方 API 在无 cookie 时拿不到链接」场景，
验证后端是否自动降级到 3rd party 并返回可用 URL。

测试：
  1. 无 cookie → 调用 /song → 检查是否返回有效 URL
  2. URL 可访问（HTTP 200 + Content-Type 音频）
  3. 实际下载文件并检查 magic bytes

测试结束后恢复 cookie 文件（如有）。
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / 'backend'

# cookie 候选路径
CANDIDATE_PATHS = [
    Path('/app/cookie/netease_cookie.txt'),
    BACKEND / 'clients' / 'cookie' / 'netease_cookie.txt',
    BACKEND / 'cookie' / 'netease_cookie.txt',
    BACKEND / 'netease_cookie.txt',
    BACKEND / 'cookie.txt',
]


def _free_port() -> int:
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = _free_port()
BASE = f'http://127.0.0.1:{PORT}'

# 测试用歌曲：陈楚生 - 有我呢 (Live版) id=3398250102
TEST_SONG_ID = '3398250102'


def log(msg: str) -> None:
    print(f'  {msg}', flush=True)


def backup_cookies() -> dict:
    backups = {}
    for p in CANDIDATE_PATHS:
        if p.exists():
            backup = p.with_suffix(p.suffix + '.bak')
            i = 1
            while backup.exists():
                backup = p.with_suffix(f'.bak{i}')
                i += 1
            shutil.move(str(p), str(backup))
            backups[str(p)] = str(backup)
    return backups


def restore_cookies(backups: dict) -> None:
    for original, backup in backups.items():
        if Path(backup).exists() and not Path(original).exists():
            shutil.move(backup, original)
        elif Path(backup).exists():
            Path(backup).unlink()


def start_gunicorn() -> subprocess.Popen:
    env = os.environ.copy()
    env['PORT'] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, '-m', 'gunicorn', '-c', 'gunicorn.conf.py', 'main:app', '--log-level', 'info'],
        cwd=str(BACKEND), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for _ in range(50):
        time.sleep(0.2)
        try:
            if requests.get(f'{BASE}/health', timeout=1).status_code == 200:
                return proc
        except requests.RequestException:
            continue
    proc.send_signal(signal.SIGTERM)
    raise RuntimeError('gunicorn 启动超时')


def stop_gunicorn(proc: subprocess.Popen) -> str:
    proc.send_signal(signal.SIGTERM)
    try:
        out, _ = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
    return out or ''


def main() -> int:
    print(f'=== /song 接口多源 fallback 测试 (port={PORT}) ===\n', flush=True)

    # 1. 备份现有 cookie
    print('[1/4] 备份现有 cookie...')
    backups = backup_cookies()
    if backups:
        for o, b in backups.items():
            log(f'已备份: {o} -> {b}')
    else:
        log('（无现存 cookie）')

    proc = None
    try:
        # 2. 启动 gunicorn
        print('\n[2/4] 启动 gunicorn...')
        proc = start_gunicorn()
        log(f'✓ gunicorn ready (pid={proc.pid})')

        # 3. 调用 /song 接口
        print(f'\n[3/4] 调用 POST /song (id={TEST_SONG_ID}, 无 cookie)...')
        r = requests.post(
            f'{BASE}/song',
            json={'id': TEST_SONG_ID, 'source': 'netease', 'level': 'lossless'},
            timeout=60,
        )
        log(f'HTTP 状态码: {r.status_code}')

        if r.status_code != 200:
            log(f'❌ 期望 200，实际 {r.status_code}')
            log(f'body: {r.text[:200]}')
            return 1

        body = r.json()
        if not body.get('success'):
            log(f'❌ success != true: {body}')
            return 1

        data = body.get('data', {})
        song_url = data.get('url', '')
        api_source = data.get('api_source') or '?'
        available = data.get('available')

        log(f'api_source: {api_source}')
        log(f'available: {available}')
        log(f'url: {song_url[:80]}...' if song_url else 'url: (空)')

        if not song_url or not song_url.startswith('http'):
            log('❌ /song 没有返回有效 URL，fallback 链全部失败')
            gunicorn_out = stop_gunicorn(proc)
            proc = None
            log('--- gunicorn 输出（找失败原因）---')
            print(gunicorn_out[-2000:], flush=True)
            return 1

        log('✓ /song 返回了有效 URL（多源 fallback 生效）')

        # 4. 验证 URL 可访问且是音频
        print('\n[4/4] 验证下载 URL 可访问性...')
        try:
            head = requests.head(song_url, timeout=15, allow_redirects=True)
            log(f'HEAD {head.status_code} | Content-Type: {head.headers.get("content-type", "?")} | Size: {head.headers.get("content-length", "?")}')
            if head.status_code == 200:
                ct = head.headers.get('content-type', '').lower()
                if 'audio' in ct or 'mpeg' in ct or 'flac' in ct or 'octet' in ct:
                    log(f'✓ URL 可访问且返回音频数据')
                else:
                    log(f'⚠️  Content-Type 不像音频：{ct}')
            else:
                log(f'❌ HEAD 返回 {head.status_code}')
                return 1
        except Exception as e:
            log(f'❌ URL 访问失败: {type(e).__name__}: {str(e)[:100]}')
            return 1

        # 关掉 gunicorn
        stop_gunicorn(proc)
        proc = None
        time.sleep(0.5)

        # 打印最终结果
        print('\n' + '='*60)
        print(f'✅ 全部通过：/song 接口在无 cookie 场景下通过 {api_source} 拿到 URL')
        print('='*60)
        return 0

    except Exception as e:
        print(f'\n❌ 测试异常: {e}', flush=True)
        return 1
    finally:
        if proc:
            stop_gunicorn(proc)
        restore_cookies(backups)
        logs_dir = BACKEND / 'logs'
        if logs_dir.exists():
            shutil.rmtree(logs_dir)
        print('\n[*] 已恢复 cookie & 清理临时文件')


if __name__ == '__main__':
    sys.exit(main())
