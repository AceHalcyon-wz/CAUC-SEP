
"""
简单测试微电流计页面
"""
from playwright.sync_api import sync_playwright
import time


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            print("导航到微电流计页面...")
            page.goto('http://localhost:5173/experiment/ammeter')
            time.sleep(5)
            
            print("截图...")
            page.screenshot(path='d:\\cauc-sep\\ammeter_page.png', full_page=True)
            print("截图已保存到 ammeter_page.png")
            
            print("检查页面内容...")
            content = page.content()
            print(f"页面长度: {len(content)} 字符")
            
            print("\n检查关键元素:")
            key_elements = [
                'el-tabs',
                '微电流',
                '采集控制',
                'connection-status'
            ]
            
            for elem in key_elements:
                found = elem in content
                print(f"  {'✓' if found else '✗'} {elem}")
            
            print("\n等待10秒后关闭...")
            time.sleep(10)
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            browser.close()


if __name__ == "__main__":
    main()
