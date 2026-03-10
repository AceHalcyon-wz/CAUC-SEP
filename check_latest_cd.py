#!/usr/bin/env python3
import urllib.request
import json


def check_latest_cd():
    runs_url = "https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs?per_page=5"

    try:
        print("正在获取最新的CD工作流状态...")
        print("=" * 60)

        with urllib.request.urlopen(runs_url, timeout=15) as response:
            data = json.loads(response.read())

        cd_runs = [r for r in data['workflow_runs'] if 'cd' in r['name'].lower()]

        for run in cd_runs[:3]:
            print(f"工作流: {run['name']}")
            print(f"  状态: {run['status']} ({run.get('conclusion', 'N/A')})")
            print(f"  分支: {run['head_branch']}")
            print(f"  事件: {run['event']}")
            print(f"  运行ID: {run['id']}")
            print(f"  创建时间: {run['created_at']}")
            print(f"  链接: {run['html_url']}")
            print()

            jobs_url = f"https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs/{run['id']}/jobs"
            with urllib.request.urlopen(jobs_url, timeout=15) as jobs_resp:
                jobs_data = json.loads(jobs_resp.read())
                print(f"  作业数: {jobs_data['total_count']}")
                for job in jobs_data['jobs']:
                    status = job['status']
                    conclusion = job.get('conclusion', 'N/A')
                    print(f"    - {job['name']}: {status} ({conclusion})")
            print()

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_latest_cd()
