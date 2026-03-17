"""
微电流计页面测试脚本
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_ammeter_page():
    """测试微电流计页面是否可以正常加载"""
    print("=" * 60)
    print("开始测试微电流计页面")
    print("=" * 60)
    
    async with async_playwright() as p:
        print("\n[1/4] 启动浏览器...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # 监听控制台错误
        errors = []
        page.on('console', lambda msg: print(f"[Console] {msg.type}: {msg.text}"))
        page.on('pageerror', lambda err: errors.append(str(err)))
        
        try:
            print("\n[2/4] 导航到主页...")
            await page.goto('http://localhost:5173', timeout=30000)
            await asyncio.sleep(2)
            
            print("\n[3/4] 查找并点击微电流计按钮...")
            
            # 尝试多种方式找到微电流计按钮
            ammeter_button = None
            
            # 方式1: 查找包含"微电流"或"ammeter"的按钮
            selectors = [
                'button:has-text("微电流")',
                'button:has-text("Ammeter")',
                'a:has-text("微电流")',
                'a:has-text("Ammeter")',
                '[role="button"]:has-text("微电流")',
                '[role="button"]:has-text("Ammeter")',
            ]
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        ammeter_button = elements[0]
                        print(f"  ✓ 使用选择器找到按钮: {selector}")
                        break
                except:
                    continue
            
            # 方式2: 查找所有按钮并过滤
            if not ammeter_button:
                print("  尝试查找所有按钮...")
                all_buttons = await page.query_selector_all('button, a, [role="button"]')
                print(f"  找到 {len(all_buttons)} 个按钮/链接")
                
                for btn in all_buttons:
                    try:
                        text = await btn.inner_text()
                        if '微电流' in text or 'Ammeter' in text or '电流' in text:
                            ammeter_button = btn
                            print(f"  ✓ 通过文本找到按钮: {text}")
                            break
                    except:
                        continue
            
            if not ammeter_button:
                print("\n✗ 未找到微电流计按钮")
                print("\n当前页面内容:")
                content = await page.content()
                print(content[:2000])
                return False
            
            print("\n[4/4] 点击按钮并等待页面加载...")
            await ammeter_button.click()
            
            # 等待页面加载
            await asyncio.sleep(3)
            
            # 截图
            screenshot_path = 'ammeter_page_loaded.png'
            await page.screenshot(path=screenshot_path)
            print(f"\n✓ 截图已保存: {screenshot_path}")
            
            # 检查错误
            if errors:
                print(f"\n⚠ 发现 {len(errors)} 个错误:")
                for i, err in enumerate(errors[:5], 1):
                    print(f"  {i}. {err[:200]}")
            else:
                print("\n✓ 未发现控制台错误")
            
            # 检查URL变化
            current_url = page.url
            print(f"\n当前URL: {current_url}")
            
            print("\n" + "=" * 60)
            print("测试完成！")
            print("=" * 60)
            
            # 保持浏览器打开一段时间以便观察
            print("\n浏览器将保持打开10秒...")
            await asyncio.sleep(10)
            
            return len(errors) == 0
            
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ammeter_page())
