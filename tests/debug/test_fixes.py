from playwright.sync_api import sync_playwright
import time

def test_application():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("正在访问前端应用...")
        page.goto('http://localhost:5173')
        page.wait_for_load_state('networkidle')
        
        print("等待3秒让页面完全加载...")
        time.sleep(3)
        
        print("截图: 首页")
        page.screenshot(path='d:\\cauc-sep\\screenshot_home.png', full_page=True)
        
        print("查找电磁铁控制菜单...")
        try:
            electromagnet_menu = page.locator('text=电磁铁控制').first
            if electromagnet_menu.is_visible(timeout=5000):
                print("找到电磁铁控制菜单，点击进入...")
                electromagnet_menu.click()
                page.wait_for_load_state('networkidle')
                time.sleep(3)
                
                print("截图: 电磁铁控制页面")
                page.screenshot(path='d:\\cauc-sep\\screenshot_electromagnet.png', full_page=True)
                
                print("检查控制台错误...")
                console_errors = []
                page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
                
                print("检查WebSocket连接状态...")
                connection_status = page.locator('.status-indicator').first
                if connection_status.is_visible():
                    print(f"连接状态: {connection_status.text_content()}")
                
        except Exception as e:
            print(f"电磁铁控制页面测试出错: {e}")
        
        print("查找微电流测量菜单...")
        try:
            ammeter_menu = page.locator('text=微电流测量').first
            if ammeter_menu.is_visible(timeout=5000):
                print("找到微电流测量菜单，点击进入...")
                ammeter_menu.click()
                page.wait_for_load_state('networkidle')
                time.sleep(3)
                
                print("截图: 微电流测量页面")
                page.screenshot(path='d:\\cauc-sep\\screenshot_ammeter.png', full_page=True)
                
        except Exception as e:
            print(f"微电流测量页面测试出错: {e}")
        
        print("测试完成，浏览器将保持打开5秒...")
        time.sleep(5)
        browser.close()

if __name__ == '__main__':
    test_application()
