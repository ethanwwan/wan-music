#!/usr/bin/env python3
"""无 cookie 场景下网易云搜索接口专项测试

模拟「容器内 /app/cookie/netease_cookie.txt 不存在」的真实情况，
验证：
  1. 后端能正常启动（不因 cookie 缺失而崩溃）
  2. POST /search 接口返回 200
  3. 响应结构正确（success=true, data=[]，不报错）
  4. 容器/进程日志中有明确的 cookie 缺失警告

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

# 候选 cookie 路径（与 netease_client.py 中的顺序保持一致）
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


def log(msg: str) -> None:
    print(f'  {msg}', flush=True)


def backup_existing_cookies() -> dict:
    """把现存的 cookie 文件临时改名，测试完恢复。返回 {path: backup_path}。"""
    backups = {}
    for p in CANDIDATE_PATHS:
        if p.exists():
            backup = p.with_suffix(p.suffix + '.bak')
            # 避免重名覆盖
            i = 1
            while backup.exists():
                backup = p.with_suffix(f'.bak{i}')
                i += 1
            shutil.move(str(p), str(backup))
            backups[str(p)] = str(backup)
    return backups


def restore_cookies(backups: dict) -> None:
    """测试结束后把 cookie 文件恢复原位。"""
    for original, backup in backups.items():
        if Path(backup).exists() and not Path(original).exists():
            shutil.move(backup, original)
        elif Path(backup).exists():
            # 目标位置意外存在，删掉 backup
            Path(backup).unlink()


def start_gunicorn() -> subprocess.Popen:
    env = os.environ.copy()
    env['PORT'] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, '-m', 'gunicorn', '-c', 'gunicorn.conf.py', 'main:app', '--log-level', 'info'],
        cwd=str(BACKEND),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(50):
        time.sleep(0.2)
        try:
            r = requests.get(f'{BASE}/health', timeout=1)
            if r.status_code == 200:
                return proc
        except requests.RequestException:
            continue
    proc.send_signal(signal.SIGTERM)
    raise RuntimeError('gunicorn 启动超时')


def stop_gunicorn(proc: subprocess.Popen) -> str:
    """终止 gunicorn 并返回完整输出。"""
    proc.send_signal(signal.SIGTERM)
    try:
        out, _ = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
    return out or ''


def main() -> int:
    print(f'=== 无 cookie 场景下网易云搜索测试 (port={PORT}) ===\n', flush=True)

    # 1. 备份现有 cookie
    print('[1/5] 备份现有 cookie 文件...')
    backups = backup_existing_cookies()
    if backups:
        for orig, bak in backups.items():
            log(f'已备份: {orig} -> {bak}')
    else:
        log('（无现存 cookie 文件）')

    # 2. 确认所有候选路径都不存在
    print('\n[2/5] 确认所有候选 cookie 路径都不存在...')
    for p in CANDIDATE_PATHS:
        if p.exists():
            print(f'❌ 路径仍存在: {p}', flush=True)
            restore_cookies(backups)
            return 1
    log(f'已确认 {len(CANDIDATE_PATHS)} 个候选路径全部不存在')

    proc = None
    try:
        # 3. 启动 gunicorn
        print('\n[3/5] 启动 gunicorn...')
        proc = start_gunicorn()
        log(f'✓ gunicorn ready (pid={proc.pid})')

        # 4. 调用 /search 接口
        print('\n[4/5] 调用 POST /search (source=netease, keyword=陈楚生)...')
        payload = {'keyword': '陈楚生', 'type': 1, 'limit': 10, 'source': 'netease', 'quality': 'lossless'}
        r = requests.post(f'{BASE}/search', json=payload, timeout=60)

        log(f'HTTP 状态码: {r.status_code}')
        log(f'Content-Type: {r.headers.get("content-type", "")}')

        # 5. 验证响应
        print('\n[5/5] 验证响应...')
        ok = True

        if r.status_code != 200:
            log(f'❌ 期望 200，实际 {r.status_code}')
            ok = False
        else:
            log('✓ 状态码 200')

        try:
            body = r.json()
        except json.JSONDecodeError:
            log(f'❌ 响应不是 JSON: {r.text[:200]}')
            ok = False
        else:
            log(f'响应体: {json.dumps(body, ensure_ascii=False)[:200]}...')

            if body.get('success') is True:
                log('✓ success=true')
            else:
                log(f'❌ success != true: {body.get("success")}')
                ok = False

            data = body.get('data', {})
            if isinstance(data, dict) and 'data' in data:
                if data['data'] == []:
                    log('✓ data.data = [] (空结果符合预期)')
                else:
                    log(f'⚠️  data.data = {len(data["data"])} 条 (网络可达时正常)')
            else:
                log(f'❌ 响应结构异常: {type(data)}')
                ok = False

            if data.get('warnings', []) == []:
                log('✓ warnings=[] (无平台错误)')
            else:
                log(f'⚠️  warnings: {data["warnings"]}')

        # 关掉进程，拿到日志
        print('\n[*] 关闭 gunicorn...')
        gunicorn_out = stop_gunicorn(proc)
        proc = None
        # 等 worker 进程 flush 文件 handler
        time.sleep(0.5)

        # 6. 检查日志
        print('\n[6/5] 检查日志中是否包含 cookie 缺失警告...')
        # gunicorn 输出包含 stderr
        expected_warn = 'cookie 文件不存在'
        if expected_warn in gunicorn_out:
            log(f'✓ 日志包含警告: "{expected_warn}"')
        else:
            log(f'❌ 日志未包含 "{expected_warn}"')
            log('--- gunicorn 完整输出 ---')
            print(gunicorn_out, flush=True)
            ok = False

        # 也看文件日志
        log_file = BACKEND / 'logs' / 'wan-music.log'
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8', errors='replace')
            if expected_warn in content:
                log(f'✓ 文件日志 {log_file} 也包含警告')
            else:
                log(f'⚠️  文件日志未包含警告')

        return 0 if ok else 1

    except Exception as e:
        print(f'\n❌ 测试异常: {e}', flush=True)
        return 1
    finally:
        if proc:
            stop_gunicorn(proc)
        restore_cookies(backups)
        # 清理测试产生的日志
        logs_dir = BACKEND / 'logs'
        if logs_dir.exists():
            shutil.rmtree(logs_dir)
        print('\n[*] 已恢复 cookie 文件 & 清理临时日志')


if __name__ == '__main__':
    sys.exit(main())
