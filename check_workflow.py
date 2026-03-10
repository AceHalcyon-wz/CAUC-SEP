"""检查GitHub Actions工作流状态"""
import urllib.request
import json

url = "https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs/22897227900/jobs"
data = json.loads(urllib.request.urlopen(url).read())

print(f"Total jobs: {data['total_count']}")
for job in data['jobs']:
    print(f"Job: {job['name']} | Status: {job['status']} | Conclusion: {job['conclusion']}")
    for step in job.get('steps', []):
        if step['status'] != 'completed':
            print(f"  - Step: {step['name']} | Status: {step['status']}")
