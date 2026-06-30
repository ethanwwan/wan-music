"""统计 4 平台官方 API 状态（基于 probe_apis.py 的探测 JSON 报告）"""
import json
import subprocess

subprocess.run(
    ['python3', 'scripts/probe_apis.py', '--json-out', '/tmp/probe_official.json'],
    capture_output=True, text=True, cwd='/Users/Awan/Public/Repository/wan-music'
)

data = json.load(open('/tmp/probe_official.json'))
platforms_data = data.get('platforms', {})

PLATFORMS = ['netease', 'qq', 'kugou', 'kuwo']
CAPS = ['search', 'url', 'info', 'lyric', 'playlist']
CAP_NAMES = {'search': '搜索', 'url': 'URL', 'info': '元信息', 'lyric': '歌词', 'playlist': '歌单'}
ALIVE_STATUSES = {'alive', 'alive_url_text'}

print('=' * 90)
print('【4 平台官方 API 状态统计】')
print('=' * 90)
print(f"{'平台':<10}{'能力':<10}{'官方源':<35}{'状态':<10}{'详情'}")
print('-' * 90)

official_total = 0
official_alive = 0
official_no_official = []
official_dead_list = []

for p in PLATFORMS:
    pdata = platforms_data.get(p, {})
    for c in CAPS:
        cap_data = pdata.get(c, {})
        # 找该平台该能力的官方源
        officials = {k: v for k, v in cap_data.items() if 'official' in k}

        if not officials:
            official_no_official.append((p, c))
            print(f"{p:<10}{CAP_NAMES[c]:<10}{'(无官方 API)':<35}{'⚠️ N/A':<10}")
            continue

        for name, info in officials.items():
            official_total += 1
            status = info.get('status', '?')
            detail = info.get('detail', '')[:60]
            if status in ALIVE_STATUSES:
                official_alive += 1
                icon = '✅'
            elif status in ('dead', 'no_data', 'no_url', 'no_lyric'):
                icon = '❌'
                official_dead_list.append((p, c, name, status, detail))
            elif status in ('off',):
                icon = '⚫'
                official_dead_list.append((p, c, name, status, detail))
            else:
                icon = '🟡'

            print(f"{p:<10}{CAP_NAMES[c]:<10}{name:<35}{icon+status:<10}{detail}")

    print()

print('=' * 90)
print(f'【统计】 官方 API: {official_alive}/{official_total} 存活')
if official_no_official:
    print(f'\n【无官方 API】 {len(official_no_official)} 个能力必须用三方:')
    for p, c in official_no_official:
        print(f'  - {p} {CAP_NAMES[c]}')

if official_dead_list:
    print(f'\n【官方 API 失败】 {len(official_dead_list)} 个:')
    for p, c, name, status, detail in official_dead_list:
        print(f'  ❌ {p} {CAP_NAMES[c]} {name} 状态={status} 详情={detail}')

print('=' * 90)
