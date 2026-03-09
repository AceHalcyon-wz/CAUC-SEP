from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    errors = []
    page.on('console', lambda msg: errors.append({
        'type': msg.type,
        'text': msg.text
    }) if msg.type in ['error', 'warning'] else None)
    
    # 定义所有子页面路由
    sub_pages = [
        # 实验控制
        {'path': '/experiment/motor', 'name': '电机控制', 'category': 'experiment'},
        {'path': '/experiment/electromagnet', 'name': '电磁铁控制', 'category': 'experiment'},
        {'path': '/experiment/temperature', 'name': '温度控制', 'category': 'experiment'},
        {'path': '/experiment/piezo', 'name': '压电控制', 'category': 'experiment'},
        {'path': '/experiment/ammeter', 'name': '皮安表控制', 'category': 'experiment'},
        # 设备管理
        {'path': '/device/status', 'name': '设备状态', 'category': 'device'},
        {'path': '/device/connection', 'name': '连接配置', 'category': 'device'},
        {'path': '/device/prpath', 'name': 'PR路径配置', 'category': 'device'},
        # 数据分析
        {'path': '/analysis/realtime', 'name': '实时数据', 'category': 'analysis'},
        {'path': '/analysis/history', 'name': '历史数据', 'category': 'analysis'},
        {'path': '/analysis/charts', 'name': '图表分析', 'category': 'analysis'},
        # 系统设置
        {'path': '/settings/config', 'name': '系统配置', 'category': 'settings'},
        {'path': '/settings/logs', 'name': '审计日志', 'category': 'settings'},
        {'path': '/settings/users', 'name': '用户管理', 'category': 'settings'},
    ]
    
    results = []
    
    for sub_page in sub_pages:
        print(f"检查: {sub_page['name']} ({sub_page['path']})")
        try:
            page.goto(f"http://localhost:5173{sub_page['path']}", wait_until='networkidle', timeout=10000)
            time.sleep(2)
            
            # 检查页面内容
            content = page.content()
            content_length = len(content)
            
            # 检查主要内容区域
            main_areas = page.locator('.page-container, .main-content, .page-header, .config-editor, .data-analysis')
            main_count = main_areas.count()
            
            # 检查空白状态
            empty_states = page.locator('.empty-state, .error-state, .loading-state')
            empty_count = empty_states.count()
            
            # 检查功能模块
            buttons = page.locator('button:visible')
            button_count = buttons.count()
            
            inputs = page.locator('input:visible, select:visible')
            input_count = inputs.count()
            
            # 检查是否有"开发中"或"未实现"文本
            dev_text = page.locator('text=/开发中|未实现|coming soon|TODO/i')
            dev_count = dev_text.count()
            
            results.append({
                'name': sub_page['name'],
                'path': sub_page['path'],
                'category': sub_page['category'],
                'content_length': content_length,
                'main_areas': main_count,
                'empty_states': empty_count,
                'buttons': button_count,
                'inputs': input_count,
                'dev_text': dev_count,
                'status': 'ok' if main_count > 0 and empty_count == 0 else 'warning'
            })
            
            print(f"  ✓ 内容长度: {content_length}, 主区域: {main_count}, 按钮: {button_count}, 输入: {input_count}")
            if dev_count > 0:
                print(f"  ⚠ 发现 {dev_count} 个'开发中'标记")
            
        except Exception as e:
            print(f"  ✗ 错误: {str(e)[:50]}")
            results.append({
                'name': sub_page['name'],
                'path': sub_page['path'],
                'category': sub_page['category'],
                'status': 'error',
                'error': str(e)
            })
    
    # 统计结果
    print("\n" + "="*60)
    print("检查结果汇总:")
    print("="*60)
    
    ok_pages = [r for r in results if r.get('status') == 'ok']
    warning_pages = [r for r in results if r.get('status') == 'warning']
    error_pages = [r for r in results if r.get('status') == 'error']
    
    print(f"\n正常页面: {len(ok_pages)}/{len(results)}")
    print(f"警告页面: {len(warning_pages)}/{len(results)}")
    print(f"错误页面: {len(error_pages)}/{len(results)}")
    
    if warning_pages:
        print("\n⚠️ 警告页面:")
        for p in warning_pages:
            print(f"  - {p['name']}: 空白状态={p.get('empty_states', 0)}")
    
    if error_pages:
        print("\n❌ 错误页面:")
        for p in error_pages:
            print(f"  - {p['name']}: {p.get('error', 'Unknown')[:50]}")
    
    # 输出关键错误
    critical_errors = [e for e in errors if e['type'] == 'error']
    if critical_errors:
        print(f"\n控制台错误 ({len(critical_errors)} 个):")
        for err in critical_errors[:5]:
            print(f"  - {err['text'][:80]}")
    
    browser.close()
    print("\n检查完成！")
