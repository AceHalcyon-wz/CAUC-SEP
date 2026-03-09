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
    
    print("访问数据分析-图表分析页面...")
    page.goto('http://localhost:5173/analysis/charts', wait_until='networkidle')
    time.sleep(3)
    
    # 截图
    page.screenshot(path='c:/Users/15272/Downloads/kimiOKC/cauc-sep/frontend/charts_page.png', full_page=True)
    
    # 获取页面内容
    content = page.content()
    print(f"页面内容长度: {len(content)}")
    
    # 检查是否有内容
    main_content = page.locator('.data-analysis, .charts-container, .main-content, .page-container')
    count = main_content.count()
    print(f"找到主要内容区域: {count} 个")
    
    # 检查空白状态
    empty_states = page.locator('.empty-state, .error-state, .loading-state')
    empty_count = empty_states.count()
    print(f"找到空白/错误/加载状态: {empty_count} 个")
    
    print("\n访问系统设置-系统配置页面...")
    page.goto('http://localhost:5173/settings/config', wait_until='networkidle')
    time.sleep(3)
    
    # 截图
    page.screenshot(path='c:/Users/15272/Downloads/kimiOKC/cauc-sep/frontend/config_page.png', full_page=True)
    
    # 检查配置页面
    config_content = page.locator('.config-editor, .config-container, .settings-container')
    config_count = config_content.count()
    print(f"找到配置内容区域: {config_count} 个")
    
    # 检查空白状态
    config_empty = page.locator('.empty-state, .error-state, .loading-state')
    config_empty_count = config_empty.count()
    print(f"找到空白/错误/加载状态: {config_empty_count} 个")
    
    # 输出错误
    critical_errors = [e for e in errors if e['type'] == 'error']
    if critical_errors:
        print(f"\n发现 {len(critical_errors)} 个错误:")
        for err in critical_errors[:5]:
            print(f"  - {err['text'][:100]}")
    
    browser.close()
    print("\n截图已保存到:")
    print("  - charts_page.png")
    print("  - config_page.png")
