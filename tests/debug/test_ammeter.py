"""
测试微电流计页面和WebSocket连接
"""
from playwright.sync_api import sync_playwright
import time

def test_ammeter_page():
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 监听控制台日志
        logs = []
        def handle_console(msg):
            logs.append({
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            })
            print(f"[{msg.type}] {msg.text}")
        
        page.on('console', handle_console)
        
        # 监听网络请求
        network_logs = []
        def handle_request(request):
            if 'ws' in request.url or 'WebSocket' in request.url:
                network_logs.append({
                    'type': 'request',
                    'url': request.url,
                    'method': request.method
                })
        
        def handle_response(response):
            if 'ws' in response.url or 'WebSocket' in response.url:
                network_logs.append({
                    'type': 'response',
                    'url': response.url,
                    'status': response.status
                })
        
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        try:
            # 访问首页
            print("访问首页...")
            page.goto('http://localhost:5173', wait_until='networkidle', timeout=30000)
            time.sleep(2)
            
            # 截图首页
            page.screenshot(path='d:\\cauc-sep\\test_home.png', full_page=True)
            print("首页截图已保存")
            
            # 查找并点击微电流计菜单
            print("查找微电流计菜单项...")
            ammeter_link = page.get_by_text('微电流测量', exact=False) or page.get_by_text('微电流计', exact=False)
            
            if ammeter_link.count() > 0:
                print("找到微电流计菜单，点击进入...")
                ammeter_link.first.click()
                time.sleep(3)
                
                # 等待页面加载
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(2)
                
                # 截图微电流计页面
                page.screenshot(path='d:\\cauc-sep\\test_ammeter.png', full_page=True)
                print("微电流计页面截图已保存")
                
                # 检查页面是否有错误
                page_title = page.title()
                print(f"页面标题: {page_title}")
                
                # 检查Tabs组件是否存在
                tabs = page.locator('.el-tabs')
                if tabs.count() > 0:
                    print("✓ Tabs组件正常加载")
                else:
                    print("✗ 未找到Tabs组件")
                
                # 检查连接状态
                connection_status = page.locator('.connection-status')
                if connection_status.count() > 0:
                    status_text = connection_status.text_content()
                    print(f"连接状态: {status_text}")
                
                # 检查控制台错误
                error_logs = [log for log in logs if log['type'] in ['error', 'warning']]
                if error_logs:
                    print(f"\n发现 {len(error_logs)} 个警告/错误:")
                    for i, log in enumerate(error_logs[:10], 1):
                        print(f"  {i}. [{log['type']}] {log['text']}")
                else:
                    print("✓ 控制台无错误")
                
                # 检查WebSocket连接
                ws_logs = [log for log in network_logs if 'ws' in log['url'].lower()]
                if ws_logs:
                    print(f"\nWebSocket连接记录:")
                    for log in ws_logs:
                        print(f"  [{log['type']}] {log['url']}")
                else:
                    print("未检测到WebSocket连接")
                    
            else:
                print("未找到微电流计菜单项")
                # 打印页面内容帮助调试
                print("\n页面上的所有链接:")
                links = page.locator('a').all()
                for link in links[:20]:
                    print(f"  - {link.text_content()}")
                    
        except Exception as e:
            print(f"测试过程中出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 截图错误状态
            try:
                page.screenshot(path='d:\\cauc-sep\\test_error.png', full_page=True)
                print("错误截图已保存")
            except:
                pass
                
        finally:
            # 保持浏览器打开一段时间以便查看
            print("\n测试完成，浏览器将在5秒后关闭...")
            time.sleep(5)
            browser.close()

if __name__ == '__main__':
    test_ammeter_page()
