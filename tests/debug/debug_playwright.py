
from playwright.sync_api import sync_playwright
import json
import time


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        console_errors = []
        console_logs = []
        
        page.on("console", lambda msg: console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location
        }))
        
        page.on("pageerror", lambda err: console_errors.append({
            "message": err.message,
            "stack": err.stack
        }))
        
        print("正在访问前端页面 http://localhost:5173")
        page.goto("http://localhost:5173", wait_until="networkidle")
        time.sleep(3)
        
        print("\n=== 控制台日志 ===")
        for log in console_logs:
            print(f"[{log['type']}] {log['text']}")
        
        print("\n=== 控制台错误 ===")
        for err in console_errors:
            print(f"ERROR: {err['message']}")
            if err['stack']:
                print(f"STACK: {err['stack']}")
        
        print("\n=== 当前页面标题 ===")
        print(page.title())
        
        print("\n=== 页面内容预览 ===")
        content = page.content()
        print(content[:1000])
        
        print("\n=== 正在截图 ===")
        page.screenshot(path="d:/cauc-sep/debug_screenshot.png", full_page=True)
        print("截图已保存至: d:/cauc-sep/debug_screenshot.png")
        
        print("\n=== 正在尝试访问电磁铁控制页面 ===")
        try:
            page.click("text=电磁铁控制", timeout=5000)
            time.sleep(3)
            
            page.screenshot(path="d:/cauc-sep/debug_electromagnet.png", full_page=True)
            print("电磁铁控制页面截图已保存")
            
            print("\n=== 电磁铁控制页面控制台日志 ===")
            for log in console_logs:
                print(f"[{log['type']}] {log['text']}")
            
            print("\n=== 电磁铁控制页面控制台错误 ===")
            for err in console_errors:
                print(f"ERROR: {err['message']}")
        except Exception as e:
            print(f"访问电磁铁控制页面失败: {e}")
        
        print("\n=== 正在尝试访问微电流计页面 ===")
        try:
            page.click("text=微电流计", timeout=5000)
            time.sleep(3)
            
            page.screenshot(path="d:/cauc-sep/debug_ammeter.png", full_page=True)
            print("微电流计页面截图已保存")
        except Exception as e:
            print(f"访问微电流计页面失败: {e}")
        
        print("\n=== 调试完成，请按任意键关闭浏览器 ===")
        input()
        
        browser.close()


if __name__ == "__main__":
    main()

