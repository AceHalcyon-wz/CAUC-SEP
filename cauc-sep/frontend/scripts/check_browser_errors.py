from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 捕获控制台错误
    errors = []
    page.on('console', lambda msg: errors.append({
        'type': msg.type,
        'text': msg.text,
        'location': f"{msg.location.get('url', 'unknown')}:{msg.location.get('lineNumber', '')}"
    }) if msg.type in ['error', 'warning'] else None)
    
    # 导航到主页面
    print("正在访问 http://localhost:5173/...")
    page.goto('http://localhost:5173/', wait_until='networkidle')
    
    # 等待页面加载
    time.sleep(3)
    
    # 访问几个关键页面
    test_routes = [
        '/experiment/motor',
        '/device/status', 
        '/analysis/realtime',
        '/settings/config'
    ]
    
    for route in test_routes:
        print(f"测试路由：{route}")
        try:
            page.goto(f'http://localhost:5173{route}', wait_until='networkidle')
            time.sleep(2)
        except Exception as e:
            errors.append({
                'type': 'navigation',
                'text': str(e),
                'location': route
            })
    
    # 检查控制台错误
    critical_errors = [e for e in errors if e['type'] == 'error']
    
    if critical_errors:
        print("\n❌ 发现严重错误:")
        for error in critical_errors[:10]:  # 只显示前 10 个错误
            print(f"  [{error['type']}] {error['text']}")
            print(f"    位置：{error['location']}")
    else:
        print("\n✅ 未发现严重运行时错误")
    
    if any(e['type'] == 'warning' for e in errors):
        print(f"\n⚠️  发现 {len([e for e in errors if e['type'] == 'warning'])} 个警告")
    
    # 保存完整日志
    with open('c:/Users/15272/Downloads/kimiOKC/cauc-sep/frontend/browser_errors.log', 'w', encoding='utf-8') as f:
        f.write("浏览器控制台日志\n")
        f.write("=" * 50 + "\n\n")
        for error in errors:
            f.write(f"类型：{error['type']}\n")
            f.write(f"内容：{error['text']}\n")
            f.write(f"位置：{error['location']}\n")
            f.write("-" * 50 + "\n")
    
    print(f"\n完整日志已保存到：browser_errors.log")
    print(f"总共捕获 {len(errors)} 条日志，其中 {len(critical_errors)} 条错误")
    
    browser.close()
