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
    
    results = []
    
    print("="*60)
    print("前端验证问题修复 - 验证测试")
    print("="*60)
    
    # 1. 验证温度控制页面
    print("\n1. 温度控制页面修复验证")
    print("-"*40)
    page.goto('http://localhost:5173/experiment/temperature', wait_until='networkidle')
    time.sleep(2)
    
    # 检查紧急停止按钮（多种选择器）
    emergency_btn = page.locator('button:has-text("紧急停止"), button:has-text("急停"), .emergency-stop-btn')
    emergency_count = emergency_btn.count()
    print(f"  紧急停止按钮: {'✅ 存在' if emergency_count > 0 else '❌ 不存在'}")
    results.append(('温度控制-紧急停止按钮', emergency_count > 0))
    
    # 检查目标温度输入框
    temp_input = page.locator('.el-input-number')
    temp_input_count = temp_input.count()
    print(f"  目标温度输入框: {'✅ 存在' if temp_input_count > 0 else '❌ 不存在'} (数量: {temp_input_count})")
    results.append(('温度控制-目标温度输入框', temp_input_count > 0))
    
    # 2. 验证压电控制页面
    print("\n2. 压电控制页面修复验证")
    print("-"*40)
    page.goto('http://localhost:5173/experiment/piezo', wait_until='networkidle')
    time.sleep(2)
    
    # 检查电压滑块
    voltage_slider = page.locator('.el-slider')
    voltage_count = voltage_slider.count()
    print(f"  电压滑块: {'✅ 存在' if voltage_count > 0 else '❌ 不存在'} (数量: {voltage_count})")
    results.append(('压电控制-电压滑块', voltage_count > 0))
    
    # 3. 验证皮安表控制页面
    print("\n3. 皮安表控制页面修复验证")
    print("-"*40)
    page.goto('http://localhost:5173/experiment/ammeter', wait_until='networkidle')
    time.sleep(2)
    
    # 检查采样率滑块
    rate_slider = page.locator('.el-slider')
    rate_count = rate_slider.count()
    print(f"  采样率滑块: {'✅ 存在' if rate_count > 0 else '❌ 不存在'} (数量: {rate_count})")
    results.append(('皮安表控制-采样率滑块', rate_count > 0))
    
    # 4. 验证PR路径配置页面
    print("\n4. PR路径配置页面修复验证")
    print("-"*40)
    page.goto('http://localhost:5173/device/pr-path', wait_until='networkidle')
    time.sleep(2)
    
    # 检查导出按钮
    export_btn = page.locator('button:has-text("导出")')
    export_count = export_btn.count()
    print(f"  导出按钮: {'✅ 存在' if export_count > 0 else '❌ 不存在'}")
    results.append(('PR路径-导出按钮', export_count > 0))
    
    # 点击导出按钮测试对话框
    if export_count > 0:
        try:
            export_btn.first.click()
            time.sleep(1)
            dialog = page.locator('.el-dialog:visible')
            dialog_count = dialog.count()
            print(f"  导出对话框: {'✅ 正常打开' if dialog_count > 0 else '❌ 未打开'}")
            results.append(('PR路径-导出对话框', dialog_count > 0))
            
            # 关闭对话框
            close_btn = page.locator('.el-dialog__headerbtn:visible')
            if close_btn.count() > 0:
                close_btn.first.click()
                time.sleep(0.5)
                print(f"  对话框关闭: ✅ 正常")
                results.append(('PR路径-对话框关闭', True))
        except Exception as e:
            print(f"  对话框测试: ❌ 错误 - {str(e)[:30]}")
            results.append(('PR路径-对话框测试', False))
    
    # 5. 验证审计日志页面
    print("\n5. 审计日志页面修复验证")
    print("-"*40)
    page.goto('http://localhost:5173/settings/audit', wait_until='networkidle')
    time.sleep(2)
    
    # 检查空数据提示
    empty_state = page.locator('.el-empty')
    empty_count = empty_state.count()
    
    # 检查文本提示
    page_text = page.locator('body').inner_text()
    has_empty_text = '暂无' in page_text or '无数据' in page_text or '没有记录' in page_text
    
    print(f"  空数据提示: {'✅ 存在' if empty_count > 0 or has_empty_text else '⚠️ 未检测到'}")
    results.append(('审计日志-空数据提示', empty_count > 0 or has_empty_text))
    
    # 检查日志表格
    log_table = page.locator('.el-table')
    table_count = log_table.count()
    print(f"  日志表格: {'✅ 存在' if table_count > 0 else '❌ 不存在'}")
    results.append(('审计日志-日志表格', table_count > 0))
    
    # 6. 验证历史数据页面
    print("\n6. 历史数据页面修复验证")
    print("-"*40)
    page.goto('http://localhost:5173/analysis/history', wait_until='networkidle')
    time.sleep(2)
    
    # 检查查询按钮（使用唯一ID）
    query_btn = page.locator('#history-query-btn')
    query_count = query_btn.count()
    print(f"  查询按钮(ID选择器): {'✅ 存在' if query_count > 0 else '❌ 不存在'}")
    results.append(('历史数据-查询按钮', query_count > 0))
    
    # 检查查询按钮是否唯一
    all_query_btns = page.locator("button:has-text('查询')")
    all_query_count = all_query_btns.count()
    print(f"  查询按钮总数: {all_query_count} 个")
    
    # 汇总结果
    print("\n" + "="*60)
    print("验证结果汇总")
    print("="*60)
    
    passed = sum(1 for r in results if r[1])
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n总测试项: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {pass_rate:.1f}%")
    
    print("\n详细结果:")
    for name, status in results:
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}")
    
    # 检查控制台错误
    critical_errors = [e for e in errors if e['type'] == 'error' and 'WebSocket' not in e['text']]
    if critical_errors:
        print(f"\n控制台错误 ({len(critical_errors)} 个):")
        for err in critical_errors[:3]:
            print(f"  - {err['text'][:60]}")
    
    browser.close()
    print("\n验证完成！")
