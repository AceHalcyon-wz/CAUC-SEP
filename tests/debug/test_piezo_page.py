from playwright.sync_api import sync_playwright
import time
import sys

def test_piezo_page():
    with sync_playwright() as p:
        print("正在启动浏览器...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            print("正在访问前端应用...")
            page.goto('http://localhost:5173', wait_until='networkidle', timeout=30000)
            
            print("等待页面加载...")
            time.sleep(3)
            
            # 查找并点击压电陶瓷按钮
            print("正在查找压电陶瓷按钮...")
            piezo_button = None
            
            # 尝试多种选择器
            selectors = [
                'text=压电陶瓷',
                'button:has-text("压电陶瓷")',
                '[data-testid*="piezo"]',
                '.menu-item:has-text("压电陶瓷")',
                'a:has-text("压电陶瓷")',
            ]
            
            for selector in selectors:
                try:
                    piezo_button = page.wait_for_selector(selector, timeout=2000)
                    if piezo_button:
                        print(f"找到按钮: {selector}")
                        break
                except:
                    continue
            
            if not piezo_button:
                print("未找到压电陶瓷按钮，尝试查找所有可点击元素...")
                page.screenshot(path='d:/cauc-sep/piezo_page_before.png')
                print("已保存截图: piezo_page_before.png")
                
                # 打印所有文本
                print("\n页面文本:")
                print(page.text_content('body'))
                return
            
            print("点击压电陶瓷按钮...")
            piezo_button.click()
            
            print("等待页面加载...")
            time.sleep(5)
            
            # 截图
            page.screenshot(path='d:/cauc-sep/piezo_page_after.png')
            print("已保存截图: piezo_page_after.png")
            
            # 检查是否有错误
            print("\n检查控制台错误...")
            errors = []
            page.on('console', lambda msg: errors.append(msg.text))
            
            # 检查页面内容
            print("\n页面内容检查:")
            page_text = page.text_content('body')
            
            if '压电陶瓷' in page_text:
                print("✓ 页面标题正常")
            else:
                print("✗ 页面标题异常")
            
            if '电压控制' in page_text or '校准' in page_text:
                print("✓ 页面内容正常")
            else:
                print("✗ 页面内容异常")
            
            # 检查URL
            current_url = page.url
            print(f"\n当前URL: {current_url}")
            
            if 'piezo' in current_url.lower():
                print("✓ 路由跳转成功")
            else:
                print("✗ 路由跳转失败")
            
            print("\n测试完成！")
            
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            
            # 截图
            try:
                page.screenshot(path='d:/cauc-sep/piezo_page_error.png')
                print("已保存错误截图: piezo_page_error.png")
            except:
                pass
        finally:
            print("\n按任意键关闭浏览器...")
            input()
            browser.close()

if __name__ == '__main__':
    test_piezo_page()
