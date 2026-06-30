"""汇总 /tmp/probe_official.json 关键信息"""
import json
import os

data = json.load(open('/tmp/probe_official.json'))
print('Test keyword:', data.get('test_keyword'))
print('File size:', os.path.getsize('/tmp/probe_official.json'), 'bytes')
print('Top keys:', list(data.keys()))
print()
print('=' * 100)
print('官方 API 状态详情 (官方源 alive/disabled/dead 状态)')
print('=' * 100)

for p, pdata in data.get('platforms', {}).items():
    print(f'\n【{p}】')
    for cap, cap_data in pdata.items():
        for name, info in cap_data.items():
            if 'official' not in name:
                continue
            status = info.get('status', '?')
            detail = info.get('detail', '')[:80]
            qr = info.get('quality_results', {})
            if qr:
                qr_summary = []
                for q, qinfo in qr.items():
                    qs = qinfo.get('status', '?')
                    if qs == 'alive':
                        qr_summary.append(f'✅{q}')
                    elif qs == 'skipped':
                        qr_summary.append(f'⏭{q}')
                    else:
                        qr_summary.append(f'❌{q}')
                print(f'  {cap:<10} {name:<35} {status:<12} {", ".join(qr_summary)}')
            else:
                print(f'  {cap:<10} {name:<35} {status:<12} {detail}')
