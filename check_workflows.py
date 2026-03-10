#!/usr/bin/env python3
import urllib.request
import json

req = urllib.request.Request(
    'https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs?per_page=10',
    headers={'Accept': 'application/vnd.github.v3+json'}
)
d = json.loads(urllib.request.urlopen(req).read())
print("GitHub Actions 最新运行状态:")
print("=" * 80)
for r in d['workflow_runs'][:8]:
    status = f"{r['status']} ({r.get('conclusion','N/A')})"
    print(f"{r['name']}: {status}")
    print(f"  分支: {r['head_branch']}, 事件: {r['event']}")
    print(f"  ID: {r['id']}, 创建时间: {r['created_at']}")
    print()
