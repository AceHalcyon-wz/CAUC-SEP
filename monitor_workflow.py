#!/usr/bin/env python3
"""
持续监控GitHub Actions工作流状态
"""
import urllib.request
import json
import time


def check_workflow():
    url = "https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs/22897227900/jobs"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
        return data
    except Exception as e:
        print(f"错误: {e}")
        return None


def print_status(data):
    print("\n" + "=" * 60)
    print(f"  GitHub Actions 状态 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    all_completed = True
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
        
        print(f"{status_emoji} {job['name']}")
        print(f"   Status: {job['status']}")
        if job.get('conclusion'):
            print(f"   Conclusion: {conclusion_emoji} {job['conclusion']}")
        
        if job['status'] != 'completed':
            all_completed = False
            
            pending_steps = [s for s in job.get('steps', []) if s['status'] != 'completed']
            if pending_steps:
                print("   当前步骤:")
                for step in pending_steps:
                    step_emoji = {'queued': '⏳', 'in_progress': '🔄'}.get(step['status'], '❓')
                    print(f"     {step_emoji} {step['name']}")
        
        print()
    
    return all_completed


def main():
    print("开始监控GitHub Actions工作流...")
    print("按Ctrl+C停止监控")
    print()
    
    check_count = 0
    while True:
        check_count += 1
        data = check_workflow()
        
        if data:
            all_completed = print_status(data)
            
            if all_completed:
                print("=" * 60)
                print("  所有任务已完成！")
                print("=" * 60)
                break
        
        # 每60秒检查一次
        if not all_completed:
            print(f"[{check_count}] 等待60秒后继续检查...")
            time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n监控已停止。")
