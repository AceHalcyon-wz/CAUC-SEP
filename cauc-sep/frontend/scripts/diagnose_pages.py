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
    
    # 检查特定页面
    pages_to_check = [
        {'path': '/device/prpath', 'name': 'PR路径配置'},
        {'path': '/settings/audit', 'name': '审计日志'},
        {'path': '/experiment/motor', 'name': '电机控制'},
        {'path': '/device/status', 'name': '设备状态'},
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
            main_areas = page.locator('.page-container, .main-content, .page-header, .config-editor, .data-analysis, .pr-path-editor, .audit-content')
            main_count = main_areas.count()
            print(f"主要内容区域: {main_count}")
            
            # 检查卡片
            cards = page.locator('.el-card')
            card_count = cards.count()
            print(f"卡片数量: {card_count}")
            
            # 检查表单
            forms = page.locator('.el-form')
            form_count = forms.count()
            print(f"表单数量: {form_count}")
            
            # 检查按钮
            buttons = page.locator('button:visible')
            button_count = buttons.count()
            print(f"可见按钮: {button_count}")
            
            # 检查是否有错误提示
            error_messages = page.locator('.el-message--error, .error-state')
            error_count = error_messages.count()
            if error_count > 0:
                print(f"⚠️ 发现错误提示: {error_count}")
            
            # 检查是否有加载状态
            loading = page.locator('.el-loading-mask, .loading-state')
            loading_count = loading.count()
            if loading_count > 0:
                print(f"⏳ 加载状态: {loading_count}")
            
            # 检查页面是否有实际内容（非空白）
            body_text = page.locator('body').inner_text()
            text_length = len(body_text.strip())
            print(f"页面文本长度: {text_length}")
            
            # 截图
            screenshot_path = f"c:/Users/15272/Downloads/kimiOKC/cauc-sep/frontend/{page_info['name'].replace('/', '_')}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"截图已保存: {screenshot_path}")
            
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
    
    # 输出关键错误
    critical_errors = [e for e in errors if e['type'] == 'error']
    if critical_errors:
        print(f"\n{'='*60}")
        print(f"控制台错误汇总 ({len(critical_errors)} 个):")
        print('='*60)
        # 去重
        seen = set()
        for err in critical_errors:
            err_text = err['text'][:100]
            if err_text not in seen:
                seen.add(err_text)
                print(f"  - {err_text}")
    
    browser.close()
    print("\n诊断完成！")
