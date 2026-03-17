"""
调试测试脚本 - 用于检查电磁铁控制和微电流计页面
"""

from playwright.sync_api import sync_playwright
import json
import time


def log_console_message(msg):
    """记录控制台消息"""
    print(f"[CONSOLE {msg.type}] {msg.text}")
    if msg.type == "error":
        print(f"[ERROR DETAILS] {json.dumps(msg.args, default=str, indent=2)}")


def test_page(page, url, name):
    """测试单个页面"""
    print(f"\n{'='*60}")
    print(f"测试页面: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        page.goto(url)
        page.wait_for_load_state('networkidle', timeout=10000)
        print(f"✓ 页面加载完成")
        
        # 截图
        screenshot_path = f"d:\\cauc-sep\\debug_{name.replace(' ', '_')}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"✓ 截图已保存: {screenshot_path}")
        
        # 获取页面标题
        title = page.title()
        print(f"✓ 页面标题: {title}")
        
        # 检查页面是否有内容
        body_text = page.locator('body').text_content()
        if body_text and len(body_text.strip()) > 0:
            print(f"✓ 页面有内容")
        else:
            print(f"✗ 警告: 页面似乎没有内容")
        
        # 检查是否有错误元素
        error_elements = page.locator('[class*="error"], [id*="error"]').count()
        if error_elements > 0:
            print(f"✗ 发现 {error_elements} 个错误相关元素")
        
        # 等待一下，让WebSocket连接尝试
        time.sleep(3)
        
        return True
        
    except Exception as e:
        print(f"✗ 页面测试失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("开始调试测试...")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    with sync_playwright() as p:
        # 启动浏览器（有头模式，方便观察）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # 监听控制台事件
        page.on("console", log_console_message)
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))
        page.on("requestfailed", lambda req: print(f"[REQUEST FAILED] {req.url} - {req.failure}"))
        
        # 测试各个页面
        base_url = "http://localhost:5173"
        
        pages_to_test = [
            (f"{base_url}/", "首页"),
            (f"{base_url}/experiment/electromagnet", "电磁铁控制"),
            (f"{base_url}/experiment/ammeter", "微电流计"),
            (f"{base_url}/experiment/motor", "电机控制"),
            (f"{base_url}/experiment/piezo", "压电控制"),
        ]
        
        for url, name in pages_to_test:
            test_page(page, url, name)
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print("测试完成，请按任意键关闭浏览器...")
        input()
        
        browser.close()


if __name__ == "__main__":
    main()
