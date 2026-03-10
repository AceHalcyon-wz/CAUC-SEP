#!/usr/bin/env python3
"""
获取GitHub Actions构建日志
"""
import urllib.request
import json


def get_run_logs():
    # 获取工作流运行
    runs_url = "https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs"
    
    try:
        print("正在获取工作流运行...")
        with urllib.request.urlopen(runs_url, timeout=15) as response:
            data = json.loads(response.read())
        
        print(f"找到 {len(data.get('workflow_runs', []))} 个工作流运行")
        print()
        
        # 显示最新的几个运行
        for i, run in enumerate(data.get('workflow_runs', [])[:3], 1):
            print(f"{i}. {run['name']} - {run['status']} ({run['conclusion']})")
            print(f"   创建时间: {run['created_at']}")
            print(f"   分支: {run['head_branch']}")
            print(f"   运行ID: {run['id']}")
            print(f"   日志URL: {run['html_url']}")
            print()
            
            # 获取该运行的作业
            jobs_url = f"https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs/{run['id']}/jobs"
            with urllib.request.urlopen(jobs_url, timeout=15) as jobs_resp:
                jobs_data = json.loads(jobs_resp.read())
                print(f"   作业数: {jobs_data['total_count']}")
                for job in jobs_data['jobs']:
                    print(f"   - {job['name']}: {job['status']} ({job.get('conclusion', 'N/A')})")
                    if job.get('html_url'):
                        print(f"     日志: {job['html_url']}")
            print()
        
        return data
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    get_run_logs()
