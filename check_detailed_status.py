#!/usr/bin/env python3
"""
获取GitHub Actions工作流的最新详细状态
"""
import urllib.request
import json


def check_workflow():
    url = "https://api.github.com/repos/AceHalcyon-wz/CAUC-SEP/actions/runs/22897227900/jobs"
    
    try:
        print("正在获取GitHub Actions状态...")
        print("=" * 80)
        
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read())
        
        print(f"总作业数: {data['total_count']}")
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
            
            print(f"{status_emoji} {job['name']}")
            print(f"   状态: {job['status']}")
            if job.get('conclusion'):
                print(f"   结果: {conclusion_emoji} {job['conclusion']}")
            print(f"   开始时间: {job.get('started_at', 'N/A')}")
            if job.get('completed_at'):
                print(f"   完成时间: {job.get('completed_at')}")
            
            # 显示所有步骤
            print("   步骤:")
            for i, step in enumerate(job.get('steps', []), 1):
                step_status_emoji = {
                    'queued': '⏳',
                    'in_progress': '🔄',
                    'completed': '✅'
                }.get(step['status'], '❓')
                
                step_conclusion_emoji = {
                    'success': '✅',
                    'failure': '❌',
                    'cancelled': '🚫',
                    'skipped': '⏭️'
                }.get(step.get('conclusion'), '')
                
                print(f"     {i}. {step_status_emoji} {step['name']}" + 
                      (f" {step_conclusion_emoji}" if step_conclusion_emoji else ""))
            
            print()
        
        print("=" * 80)
        return data
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    check_workflow()
