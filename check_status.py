#!/usr/bin/env python3
"""
检查GitHub Actions工作流状态
"""
import urllib.request
import json
import time


def check_workflow():
    url = "https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs/22897227900/jobs"
    
    try:
        print("正在获取GitHub Actions状态...")
        print("=" * 60)
        
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
        
        print(f"Total jobs: {data['total_count']}")
        print()
        
        for job in data['jobs']:
            status_emoji = {
                'queued': '⏳',
                'in_progress': '🔄',
                'completed': '✅'
            }.get(job['status'], '❓')
            
            conclusion_emoji = {
                'success': '✅',
                'failure': '❌',
                'cancelled': '🚫',
                'skipped': '⏭️'
            }.get(job.get('conclusion'), '⏳')
            
            print(f"{status_emoji} Job: {job['name']}")
            print(f"   Status: {job['status']}")
            if job.get('conclusion'):
                print(f"   Conclusion: {conclusion_emoji} {job['conclusion']}")
            
            # 显示未完成的步骤
            pending_steps = [s for s in job.get('steps', []) if s['status'] != 'completed']
            if pending_steps:
                print("   未完成的步骤:")
                for step in pending_steps:
                    step_emoji = {'queued': '⏳', 'in_progress': '🔄'}.get(step['status'], '❓')
                    print(f"     {step_emoji} {step['name']}")
            
            print()
            
        print("=" * 60)
        return data
        
    except Exception as e:
        print(f"错误: {e}")
        return None


if __name__ == "__main__":
    check_workflow()
