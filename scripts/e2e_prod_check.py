#!/usr/bin/env python3
"""端到端生产环境模拟测试

模拟 Docker 镜像构建后的真实环境：
  1. 构建前端（vite build）
  2. 把 dist 产物复制到 backend 的 templates/ 和 static/（与 Dockerfile 一致）
  3. 用 gunicorn 启动后端
  4. 用 requests 真实访问各项接口，验证：
     - GET /            → 200, HTML
     - GET /docs        → 200, HTML（catch-all）
     - GET /favicon.svg → 200, image/svg+xml
     - GET /assets/index-*.js → 200, JS
     - GET /assets/index-*.css → 200, CSS
     - GET /favicon.ico → 204
     - GET /health      → 200, JSON
     - POST /search     → 200, JSON
     - GET /platforms   → 200, JSON

用法：
  python3 scripts/test_e2e_prod.py

注意：需要先安装前端依赖（npm ci）和后端依赖（pip install -r requirements.txt）。
"""
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / 'frontend'
BACKEND = ROOT / 'backend'
DIST = FRONTEND / 'dist'

# 真实可用的临时端口（避免硬编码）
def _free_port() -> int:
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p

PORT = _free_port()
BASE = f'http://127.0.0.1:{PORT}'


def log(step: str, msg: str = '') -> None:
    print(f'[{step}] {msg}', flush=True)


def step_build_frontend() -> None:
    log('1/5', f'构建前端 (npm run build) ...')
    subprocess.run(['npm', 'run', 'build'], cwd=str(FRONTEND), check=True)
    if not (DIST / 'index.html').exists():
        raise RuntimeError('前端构建失败：dist/index.html 不存在')
    log('1/5', f'  ✓ 构建完成: {DIST}')


def step_copy_to_backend() -> None:
    """与 Dockerfile 保持完全一致的产物布局"""
    log('2/5', '复制前端产物到 backend（模拟 Dockerfile 步骤）...')
    tmpl = BACKEND / 'templates'
    static = BACKEND / 'static'
    if tmpl.exists():
        shutil.rmtree(tmpl)
    if static.exists():
        shutil.rmtree(static)
    tmpl.mkdir(parents=True)
    static.mkdir(parents=True)
    shutil.copy(DIST / 'index.html', tmpl / 'index.html')
    shutil.copytree(DIST / 'assets', static / 'assets')
    if (DIST / 'favicon.svg').exists():
        shutil.copy(DIST / 'favicon.svg', static / 'favicon.svg')
    log('2/5', f'  ✓ templates/index.html, static/assets/, static/favicon.svg')


def step_start_gunicorn() -> subprocess.Popen:
    log('3/5', f'启动 gunicorn (port={PORT}) ...')
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
    # 等 gunicorn 真正起来
    for _ in range(50):
        time.sleep(0.2)
        try:
            r = requests.get(f'{BASE}/health', timeout=1)
            if r.status_code == 200:
                log('3/5', f'  ✓ gunicorn ready (pid={proc.pid})')
                return proc
        except requests.RequestException:
            continue
    proc.send_signal(signal.SIGTERM)
    raise RuntimeError('gunicorn 启动超时')


def step_test_endpoints() -> None:
    log('4/5', '逐项测试接口...')
    cases = []

    # 1. / 应返回 SPA index.html
    r = requests.get(f'{BASE}/')
    cases.append(('GET /', r.status_code, '<!DOCTYPE html>' in r.text or '<html' in r.text, 'HTML'))

    # 2. /docs 应被 catch-all 捕获并返回 index.html
    r = requests.get(f'{BASE}/docs')
    cases.append(('GET /docs', r.status_code, '<!DOCTYPE html>' in r.text or '<html' in r.text, 'HTML'))

    # 3. /favicon.ico 应返回 204
    r = requests.get(f'{BASE}/favicon.ico')
    cases.append(('GET /favicon.ico', r.status_code, r.status_code == 204, '204 No Content'))

    # 4. /favicon.svg 应返回 SVG
    r = requests.get(f'{BASE}/favicon.svg')
    cases.append(('GET /favicon.svg', r.status_code, 'svg' in r.headers.get('content-type', '').lower(), 'image/svg+xml'))

    # 5. /assets/index-*.js 应返回 JS（从 dist/index.html 解析实际文件名）
    dist_html = (DIST / 'index.html').read_text()
    js_match = re.search(r'/assets/(index-[^"]+\.js)', dist_html)
    css_match = re.search(r'/assets/(index-[^"]+\.css)', dist_html)
    if js_match:
        r = requests.get(f'{BASE}/assets/{js_match.group(1)}')
        cases.append((f'GET /assets/{js_match.group(1)}', r.status_code, 'javascript' in r.headers.get('content-type', '').lower(), 'JS'))
    if css_match:
        r = requests.get(f'{BASE}/assets/{css_match.group(1)}')
        cases.append((f'GET /assets/{css_match.group(1)}', r.status_code, 'css' in r.headers.get('content-type', '').lower(), 'CSS'))

    # 6. /health 应返回 JSON
    r = requests.get(f'{BASE}/health')
    body = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
    cases.append(('GET /health', r.status_code, body.get('status') == 'healthy', 'JSON {status: healthy}'))

    # 7. POST /search 应返回 JSON
    r = requests.post(f'{BASE}/search', json={'keyword': 'test', 'limit': 5})
    cases.append(('POST /search', r.status_code, 'json' in r.headers.get('content-type', '').lower(), 'JSON'))

    # 8. GET /platforms 应返回 JSON
    r = requests.get(f'{BASE}/platforms')
    cases.append(('GET /platforms', r.status_code, 'json' in r.headers.get('content-type', '').lower(), 'JSON'))

    # 9. /unknown/random/path 应被 catch-all 捕获
    r = requests.get(f'{BASE}/some/random/path')
    cases.append(('GET /some/random/path (catch-all)', r.status_code, '<!DOCTYPE html>' in r.text or '<html' in r.text, 'HTML'))

    # 打印结果
    failed = 0
    for name, code, ok, kind in cases:
        mark = '✓' if (code == 200 or (name == 'GET /favicon.ico' and code == 204)) and ok else '✗'
        if mark == '✗':
            failed += 1
        print(f'  {mark} {name:40s} {code}  ({kind})', flush=True)
    if failed:
        raise RuntimeError(f'有 {failed} 项测试失败')


def step_cleanup(proc: subprocess.Popen) -> None:
    log('5/5', '关闭 gunicorn & 清理临时文件...')
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    # 清理 backend 临时构建产物
    for p in [BACKEND / 'templates', BACKEND / 'static']:
        if p.exists():
            shutil.rmtree(p)
    log('5/5', '  ✓ 完成')


def main() -> int:
    print(f'=== 端到端生产环境测试 (port={PORT}) ===\n', flush=True)
    proc = None
    try:
        step_build_frontend()
        step_copy_to_backend()
        proc = step_start_gunicorn()
        step_test_endpoints()
    except Exception as e:
        print(f'\n❌ 测试失败: {e}', flush=True)
        if proc:
            proc.send_signal(signal.SIGTERM)
        return 1
    finally:
        if proc:
            step_cleanup(proc)
    print('\n✅ 所有测试通过', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
