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
    
    # 使用正确的路由
    pages_to_check = [
        {'path': '/device/pr-path', 'name': 'PR路径配置'},  # 正确路由
        {'path': '/settings/audit', 'name': '审计日志'},
        {'path': '/experiment/motor', 'name': '电机控制'},
        {'path': '/analysis/charts', 'name': '图表分析'},
        {'path': '/settings/config', 'name': '系统配置'},
    ]
    
    for page_info in pages_to_check:
        print(f"\n{'='*60}")
        print(f"检查页面: {page_info['name']} ({page_info['path']})")
        print('='*60)
        
        try:
            page.goto(f"http://localhost:5173{page_info['path']}", wait_until='networkidle', timeout=15000)
            time.sleep(3)
            
            # 检查页面内容
            content = page.content()
            
            # 检查主要内容区域
            main_areas = page.locator('.page-container, .main-content, .page-header, .config-editor, .data-analysis, .pr-path-editor, .device-pr-path-page')
            main_count = main_areas.count()
            print(f"主要内容区域: {main_count}")
            
            # 检查卡片
            cards = page.locator('.el-card')
            card_count = cards.count()
            print(f"卡片数量: {card_count}")
            
            # 检查按钮
            buttons = page.locator('button:visible')
            button_count = buttons.count()
            print(f"可见按钮: {button_count}")
            
            # 检查页面文本
            body_text = page.locator('body').inner_text()
            text_length = len(body_text.strip())
            print(f"页面文本长度: {text_length}")
            
            # 检查是否有 404 错误
            if '404' in body_text or '页面不存在' in body_text:
                print("❌ 页面显示 404 错误")
            else:
                print("✅ 页面正常加载")
            
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
    
    # 输出关键错误
    critical_errors = [e for e in errors if e['type'] == 'error']
    if critical_errors:
        print(f"\n{'='*60}")
        print(f"控制台错误汇总 ({len(critical_errors)} 个):")
        print('='*60)
        seen = set()
        for err in critical_errors:
            err_text = err['text'][:100]
            if err_text not in seen and 'WebSocket' not in err_text:
                seen.add(err_text)
                print(f"  - {err_text}")
    
    browser.close()
    print("\n诊断完成！")
