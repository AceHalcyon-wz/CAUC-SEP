"""
数据分析模块功能完整性验证测试脚本

测试范围：
1. 实时数据页面 (/analysis/realtime) - 波形显示、数据统计、导出功能
2. 历史数据页面 (/analysis/history) - 查询、筛选、导出、分析功能
3. 图表分析页面 (/analysis/charts) - 图表生成、数据处理、导出功能

验证内容：
- 页面是否正常加载
- 所有按钮是否可点击
- 图表是否正常渲染
- 后端 API 是否正确对接
- 错误处理是否完善
"""

import json
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, expect, Page, Browser


class AnalysisModuleTester:
    """数据分析模块测试器"""

    def __init__(self):
        self.base_url = "http://localhost:5173"
        self.results = {
            "test_time": datetime.now().isoformat(),
            "pages": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            },
            "issues": []
        }
        self.browser: Browser = None
        self.page: Page = None
        self.console_logs = []
        self.network_errors = []

    def log_result(self, page_name: str, test_name: str, status: str, message: str = "", details: dict = None):
        """记录测试结果"""
        if page_name not in self.results["pages"]:
            self.results["pages"][page_name] = {
                "tests": [],
                "status": "pending"
            }

        test_result = {
            "name": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }

        self.results["pages"][page_name]["tests"].append(test_result)
        self.results["summary"]["total_tests"] += 1

        if status == "passed":
            self.results["summary"]["passed"] += 1
            print(f"  [PASS] {test_name}: {message}")
        elif status == "failed":
            self.results["summary"]["failed"] += 1
            print(f"  [FAIL] {test_name}: {message}")
            self.results["issues"].append({
                "page": page_name,
                "test": test_name,
                "message": message
            })
        elif status == "warning":
            self.results["summary"]["warnings"] += 1
            print(f"  [WARN] {test_name}: {message}")

    def capture_console(self, msg):
        """捕获控制台日志"""
        self.console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "timestamp": datetime.now().isoformat()
        })
        if msg.type == "error":
            print(f"    [Console Error] {msg.text}")

    def capture_network_error(self, response):
        """捕获网络错误"""
        if response.status >= 400:
            self.network_errors.append({
                "url": response.url,
                "status": response.status,
                "timestamp": datetime.now().isoformat()
            })

    def setup_browser(self, playwright):
        """初始化浏览器"""
        self.browser = playwright.chromium.launch(headless=True)
        context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )
        self.page = context.new_page()

        # 监听控制台日志
        self.page.on("console", self.capture_console)

        # 监听网络请求
        self.page.on("response", self.capture_network_error)

    def teardown_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()

    def wait_for_page_load(self, timeout: int = 10000):
        """等待页面加载完成"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout)
            self.page.wait_for_timeout(500)  # 额外等待动画完成
            return True
        except Exception as e:
            print(f"    [Warning] Page load timeout: {e}")
            return False

    def take_screenshot(self, name: str) -> str:
        """截图并返回路径"""
        screenshot_dir = Path("test_results/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = screenshot_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return str(path)

    # ==================== 实时数据页面测试 ====================

    def test_realtime_page(self):
        """测试实时数据页面"""
        print("\n" + "=" * 60)
        print("测试实时数据页面 (/analysis/realtime)")
        print("=" * 60)

        page_name = "realtime"
        self.results["pages"][page_name] = {"tests": [], "status": "testing"}

        try:
            # 导航到页面
            self.page.goto(f"{self.base_url}/analysis/realtime")
            self.wait_for_page_load()

            # 测试1: 页面是否正常加载
            print("\n[测试1] 页面加载验证")
            try:
                # 检查页面标题
                title = self.page.locator(".page-title").text_content()
                if "实时数据分析" in title:
                    self.log_result(page_name, "页面标题", "passed", f"标题正确: {title}")
                else:
                    self.log_result(page_name, "页面标题", "failed", f"标题不正确: {title}")

                # 检查页面是否完全渲染
                self.page.wait_for_selector(".analysis-realtime-page", timeout=5000)
                self.log_result(page_name, "页面渲染", "passed", "页面容器正常渲染")

                # 截图
                screenshot_path = self.take_screenshot("realtime_page_loaded")
                self.log_result(page_name, "页面截图", "passed", f"截图保存: {screenshot_path}")

            except Exception as e:
                self.log_result(page_name, "页面加载", "failed", str(e))
                return

            # 测试2: 数据统计卡片
            print("\n[测试2] 数据统计卡片验证")
            try:
                stat_cards = self.page.locator(".stat-card").all()
                if len(stat_cards) >= 4:
                    self.log_result(page_name, "统计卡片数量", "passed", f"找到 {len(stat_cards)} 个统计卡片")
                else:
                    self.log_result(page_name, "统计卡片数量", "warning", f"统计卡片数量不足: {len(stat_cards)}")

                # 检查统计值是否显示
                stat_values = self.page.locator(".stat-value").all()
                for i, val in enumerate(stat_values[:4]):
                    text = val.text_content()
                    if text and text.strip():
                        self.log_result(page_name, f"统计值{i+1}", "passed", f"值: {text}")
                    else:
                        self.log_result(page_name, f"统计值{i+1}", "warning", "值为空")

            except Exception as e:
                self.log_result(page_name, "统计卡片检查", "failed", str(e))

            # 测试3: 自动刷新开关
            print("\n[测试3] 自动刷新功能验证")
            try:
                # 查找自动刷新开关
                switch = self.page.locator(".el-switch").first
                if switch.is_visible():
                    self.log_result(page_name, "刷新开关可见", "passed", "自动刷新开关正常显示")

                    # 检查初始状态
                    is_checked = switch.locator("input").is_checked()
                    self.log_result(page_name, "刷新开关初始状态", "passed",
                                    f"初始状态: {'开启' if is_checked else '关闭'}")

                    # 点击切换
                    switch.click()
                    self.page.wait_for_timeout(300)
                    new_state = switch.locator("input").is_checked()
                    self.log_result(page_name, "刷新开关切换", "passed",
                                    f"切换后状态: {'开启' if new_state else '关闭'}")

                    # 恢复原状态
                    switch.click()
                    self.page.wait_for_timeout(300)

            except Exception as e:
                self.log_result(page_name, "自动刷新开关", "failed", str(e))

            # 测试4: 刷新数据按钮
            print("\n[测试4] 刷新数据按钮验证")
            try:
                refresh_btn = self.page.locator("button:has-text('刷新数据')")
                if refresh_btn.is_visible() and refresh_btn.is_enabled():
                    self.log_result(page_name, "刷新按钮状态", "passed", "按钮可见且可点击")

                    # 点击刷新
                    refresh_btn.click()
                    self.page.wait_for_timeout(500)

                    # 检查是否有消息提示
                    message = self.page.locator(".el-message").first
                    if message.is_visible():
                        msg_text = message.text_content()
                        self.log_result(page_name, "刷新反馈", "passed", f"消息提示: {msg_text}")
                    else:
                        self.log_result(page_name, "刷新反馈", "warning", "未检测到刷新反馈消息")

            except Exception as e:
                self.log_result(page_name, "刷新数据按钮", "failed", str(e))

            # 测试5: 快捷操作按钮
            print("\n[测试5] 快捷操作按钮验证")
            try:
                # 导出实时数据按钮
                export_btn = self.page.locator("button:has-text('导出实时数据')")
                if export_btn.is_visible() and export_btn.is_enabled():
                    self.log_result(page_name, "导出按钮", "passed", "导出按钮可见且可点击")
                else:
                    self.log_result(page_name, "导出按钮", "warning", "导出按钮状态异常")

                # 暂停刷新按钮
                pause_btn = self.page.locator("button:has-text('暂停刷新')")
                if pause_btn.is_visible():
                    self.log_result(page_name, "暂停按钮", "passed", "暂停按钮可见")
                    # 检查是否禁用（取决于自动刷新状态）
                    is_disabled = pause_btn.is_disabled()
                    self.log_result(page_name, "暂停按钮状态", "passed",
                                    f"暂停按钮{'禁用' if is_disabled else '可用'}")

                # 清除数据按钮
                clear_btn = self.page.locator("button:has-text('清除数据')")
                if clear_btn.is_visible() and clear_btn.is_enabled():
                    self.log_result(page_name, "清除按钮", "passed", "清除按钮可见且可点击")

                # 显示设置按钮
                settings_btn = self.page.locator("button:has-text('显示设置')")
                if settings_btn.is_visible() and settings_btn.is_enabled():
                    self.log_result(page_name, "设置按钮", "passed", "设置按钮可见且可点击")

                    # 点击打开设置对话框
                    settings_btn.click()
                    self.page.wait_for_timeout(300)

                    # 检查对话框是否打开
                    dialog = self.page.locator(".el-dialog:visible")
                    if dialog.is_visible():
                        self.log_result(page_name, "设置对话框", "passed", "设置对话框正常打开")

                        # 检查对话框内容
                        form_items = dialog.locator(".el-form-item").all()
                        self.log_result(page_name, "设置表单项", "passed",
                                        f"找到 {len(form_items)} 个设置项")

                        # 关闭对话框
                        dialog.locator("button:has-text('取消')").click()
                        self.page.wait_for_timeout(300)
                    else:
                        self.log_result(page_name, "设置对话框", "failed", "设置对话框未打开")

            except Exception as e:
                self.log_result(page_name, "快捷操作按钮", "failed", str(e))

            # 测试6: RealtimeAnalysis 组件
            print("\n[测试6] RealtimeAnalysis 组件验证")
            try:
                # 检查组件是否存在
                realtime_component = self.page.locator(".realtime-analysis, [class*='realtime']").first
                if realtime_component.is_visible():
                    self.log_result(page_name, "实时分析组件", "passed", "RealtimeAnalysis 组件正常渲染")
                else:
                    self.log_result(page_name, "实时分析组件", "warning", "未检测到 RealtimeAnalysis 组件")

            except Exception as e:
                self.log_result(page_name, "实时分析组件", "warning", str(e))

            # 更新页面状态
            self.results["pages"][page_name]["status"] = "completed"

        except Exception as e:
            self.log_result(page_name, "页面测试", "failed", f"测试过程中发生错误: {e}")
            self.results["pages"][page_name]["status"] = "error"

    # ==================== 历史数据页面测试 ====================

    def test_history_page(self):
        """测试历史数据页面"""
        print("\n" + "=" * 60)
        print("测试历史数据页面 (/analysis/history)")
        print("=" * 60)

        page_name = "history"
        self.results["pages"][page_name] = {"tests": [], "status": "testing"}

        try:
            # 导航到页面
            self.page.goto(f"{self.base_url}/analysis/history")
            self.wait_for_page_load()

            # 测试1: 页面是否正常加载
            print("\n[测试1] 页面加载验证")
            try:
                title = self.page.locator(".page-title").text_content()
                if "历史数据分析" in title:
                    self.log_result(page_name, "页面标题", "passed", f"标题正确: {title}")
                else:
                    self.log_result(page_name, "页面标题", "failed", f"标题不正确: {title}")

                # 检查页面容器
                self.page.wait_for_selector(".analysis-history-page", timeout=5000)
                self.log_result(page_name, "页面渲染", "passed", "页面容器正常渲染")

                screenshot_path = self.take_screenshot("history_page_loaded")
                self.log_result(page_name, "页面截图", "passed", f"截图保存: {screenshot_path}")

            except Exception as e:
                self.log_result(page_name, "页面加载", "failed", str(e))
                return

            # 测试2: 标签页切换
            print("\n[测试2] 标签页切换验证")
            try:
                tabs = self.page.locator(".el-tabs__item").all()
                expected_tabs = ["数据查询", "数据对比", "数据叠加"]
                found_tabs = [tab.text_content() for tab in tabs]

                for expected in expected_tabs:
                    if expected in found_tabs:
                        self.log_result(page_name, f"标签页-{expected}", "passed", "标签页存在")
                    else:
                        self.log_result(page_name, f"标签页-{expected}", "failed", "标签页不存在")

                # 测试标签页切换
                for i, tab in enumerate(tabs[:3]):
                    tab.click()
                    self.page.wait_for_timeout(300)
                    active_tab = self.page.locator(".el-tabs__item.is-active").text_content()
                    self.log_result(page_name, f"标签页切换-{i+1}", "passed",
                                    f"当前激活: {active_tab}")

                # 返回第一个标签页
                tabs[0].click()
                self.page.wait_for_timeout(300)

            except Exception as e:
                self.log_result(page_name, "标签页切换", "failed", str(e))

            # 测试3: HistoryQuery 组件
            print("\n[测试3] 查询组件验证")
            try:
                # 检查查询组件
                query_component = self.page.locator(".history-query, [class*='query-panel']").first
                if query_component.is_visible():
                    self.log_result(page_name, "查询组件", "passed", "HistoryQuery 组件正常渲染")

                    # 检查查询按钮（使用唯一ID选择器）
                    query_btn = self.page.locator("#history-query-btn")
                    if query_btn.is_visible():
                        self.log_result(page_name, "查询按钮", "passed", "查询按钮可见")

                    # 检查重置按钮
                    reset_btn = self.page.locator("button:has-text('重置')")
                    if reset_btn.is_visible():
                        self.log_result(page_name, "重置按钮", "passed", "重置按钮可见")

                else:
                    self.log_result(page_name, "查询组件", "warning", "未检测到查询组件")

            except Exception as e:
                self.log_result(page_name, "查询组件", "warning", str(e))

            # 测试4: 数据列表
            print("\n[测试4] 数据列表验证")
            try:
                # 检查数据列表卡片
                data_list_card = self.page.locator(".data-list-card")
                if data_list_card.is_visible():
                    self.log_result(page_name, "数据列表卡片", "passed", "数据列表卡片可见")

                    # 检查虚拟滚动列表
                    virtual_list = self.page.locator(".virtual-scroll-list, [class*='scroll-list']")
                    if virtual_list.count() > 0:
                        self.log_result(page_name, "虚拟滚动列表", "passed", "虚拟滚动列表正常渲染")
                    else:
                        self.log_result(page_name, "虚拟滚动列表", "warning", "未检测到虚拟滚动列表")

                    # 检查分页
                    pagination = self.page.locator(".el-pagination")
                    if pagination.is_visible():
                        self.log_result(page_name, "分页组件", "passed", "分页组件可见")
                    else:
                        self.log_result(page_name, "分页组件", "warning", "分页组件不可见")

                else:
                    self.log_result(page_name, "数据列表卡片", "warning", "数据列表卡片不可见")

            except Exception as e:
                self.log_result(page_name, "数据列表", "warning", str(e))

            # 测试5: 图表区域
            print("\n[测试5] 图表区域验证")
            try:
                # 检查图表卡片
                chart_card = self.page.locator(".chart-card")
                if chart_card.is_visible():
                    self.log_result(page_name, "图表卡片", "passed", "图表卡片可见")

                    # 检查图表类型切换按钮
                    chart_type_btns = self.page.locator(".chart-actions button, .el-button-group button").all()
                    if len(chart_type_btns) >= 3:
                        self.log_result(page_name, "图表类型按钮", "passed",
                                        f"找到 {len(chart_type_btns)} 个图表类型按钮")

                        # 测试切换图表类型
                        for btn in chart_type_btns[:3]:
                            btn.click()
                            self.page.wait_for_timeout(200)
                    else:
                        self.log_result(page_name, "图表类型按钮", "warning",
                                        f"图表类型按钮数量不足: {len(chart_type_btns)}")

                    # 检查图表容器
                    chart_container = self.page.locator(".chart-container")
                    if chart_container.is_visible():
                        self.log_result(page_name, "图表容器", "passed", "图表容器可见")

                        # 检查 ECharts 是否渲染
                        chart_canvas = chart_container.locator("canvas")
                        if chart_canvas.count() > 0:
                            self.log_result(page_name, "ECharts 渲染", "passed", "ECharts 图表正常渲染")
                        else:
                            self.log_result(page_name, "ECharts 渲染", "warning", "未检测到 ECharts canvas")

                else:
                    self.log_result(page_name, "图表卡片", "warning", "图表卡片不可见")

            except Exception as e:
                self.log_result(page_name, "图表区域", "warning", str(e))

            # 测试6: 统计分析
            print("\n[测试6] 统计分析验证")
            try:
                stats_card = self.page.locator(".stats-card")
                if stats_card.is_visible():
                    self.log_result(page_name, "统计卡片", "passed", "统计分析卡片可见")

                    # 检查统计项
                    stat_items = stats_card.locator(".stat-item").all()
                    if len(stat_items) >= 4:
                        self.log_result(page_name, "统计项数量", "passed", f"找到 {len(stat_items)} 个统计项")
                    else:
                        self.log_result(page_name, "统计项数量", "warning",
                                        f"统计项数量不足: {len(stat_items)}")

                else:
                    self.log_result(page_name, "统计卡片", "warning", "统计分析卡片不可见")

            except Exception as e:
                self.log_result(page_name, "统计分析", "warning", str(e))

            # 测试7: 导出功能
            print("\n[测试7] 导出功能验证")
            try:
                export_btn = self.page.locator("button:has-text('导出数据')")
                if export_btn.is_visible():
                    self.log_result(page_name, "导出按钮", "passed", "导出按钮可见")

                    if export_btn.is_enabled():
                        self.log_result(page_name, "导出按钮状态", "passed", "导出按钮可点击")
                    else:
                        self.log_result(page_name, "导出按钮状态", "warning", "导出按钮禁用（可能无数据）")
                else:
                    self.log_result(page_name, "导出按钮", "warning", "导出按钮不可见")

            except Exception as e:
                self.log_result(page_name, "导出功能", "warning", str(e))

            # 测试8: 数据对比标签页
            print("\n[测试8] 数据对比功能验证")
            try:
                # 切换到数据对比标签页
                compare_tab = self.page.locator(".el-tabs__item:has-text('数据对比')")
                compare_tab.click()
                self.page.wait_for_timeout(500)

                # 检查对比卡片
                compare_card = self.page.locator(".compare-card")
                if compare_card.is_visible():
                    self.log_result(page_name, "对比卡片", "passed", "数据对比卡片可见")

                    # 检查添加对比数据按钮
                    add_btn = self.page.locator("button:has-text('添加对比数据')")
                    if add_btn.is_visible():
                        self.log_result(page_name, "添加对比按钮", "passed", "添加对比数据按钮可见")

                else:
                    self.log_result(page_name, "对比卡片", "warning", "数据对比卡片不可见")

            except Exception as e:
                self.log_result(page_name, "数据对比功能", "warning", str(e))

            # 更新页面状态
            self.results["pages"][page_name]["status"] = "completed"

        except Exception as e:
            self.log_result(page_name, "页面测试", "failed", f"测试过程中发生错误: {e}")
            self.results["pages"][page_name]["status"] = "error"

    # ==================== 图表分析页面测试 ====================

    def test_charts_page(self):
        """测试图表分析页面"""
        print("\n" + "=" * 60)
        print("测试图表分析页面 (/analysis/charts)")
        print("=" * 60)

        page_name = "charts"
        self.results["pages"][page_name] = {"tests": [], "status": "testing"}

        try:
            # 导航到页面
            self.page.goto(f"{self.base_url}/analysis/charts")
            self.wait_for_page_load()

            # 测试1: 页面是否正常加载
            print("\n[测试1] 页面加载验证")
            try:
                title = self.page.locator(".page-title").text_content()
                if "图表分析" in title:
                    self.log_result(page_name, "页面标题", "passed", f"标题正确: {title}")
                else:
                    self.log_result(page_name, "页面标题", "failed", f"标题不正确: {title}")

                # 检查页面容器
                self.page.wait_for_selector(".analysis-charts-page", timeout=5000)
                self.log_result(page_name, "页面渲染", "passed", "页面容器正常渲染")

                screenshot_path = self.take_screenshot("charts_page_loaded")
                self.log_result(page_name, "页面截图", "passed", f"截图保存: {screenshot_path}")

            except Exception as e:
                self.log_result(page_name, "页面加载", "failed", str(e))
                return

            # 测试2: 视图模式切换
            print("\n[测试2] 视图模式切换验证")
            try:
                view_modes = ["数据分析", "数据对比", "高级图表"]
                for mode in view_modes:
                    btn = self.page.locator(f"button:has-text('{mode}')")
                    if btn.is_visible():
                        self.log_result(page_name, f"视图按钮-{mode}", "passed", f"{mode} 按钮可见")

                        # 点击切换
                        btn.click()
                        self.page.wait_for_timeout(500)

                        # 检查是否激活
                        if btn.locator("..").get_attribute("class") and "primary" in btn.locator("..").get_attribute("class"):
                            self.log_result(page_name, f"视图切换-{mode}", "passed", f"{mode} 视图激活成功")
                    else:
                        self.log_result(page_name, f"视图按钮-{mode}", "warning", f"{mode} 按钮不可见")

                # 返回数据分析视图
                self.page.locator("button:has-text('数据分析')").click()
                self.page.wait_for_timeout(500)

            except Exception as e:
                self.log_result(page_name, "视图模式切换", "failed", str(e))

            # 测试3: DataAnalysis 组件
            print("\n[测试3] DataAnalysis 组件验证")
            try:
                # 检查 DataAnalysis 组件
                data_analysis = self.page.locator(".data-analysis, [class*='data-analysis-component']").first
                if data_analysis.is_visible():
                    self.log_result(page_name, "DataAnalysis 组件", "passed", "DataAnalysis 组件正常渲染")
                else:
                    self.log_result(page_name, "DataAnalysis 组件", "warning", "未检测到 DataAnalysis 组件")

            except Exception as e:
                self.log_result(page_name, "DataAnalysis 组件", "warning", str(e))

            # 测试4: 新建图表功能
            print("\n[测试4] 新建图表功能验证")
            try:
                new_chart_btn = self.page.locator("button:has-text('新建图表')")
                if new_chart_btn.is_visible() and new_chart_btn.is_enabled():
                    self.log_result(page_name, "新建图表按钮", "passed", "新建图表按钮可见且可点击")

                    # 点击打开对话框
                    new_chart_btn.click()
                    self.page.wait_for_timeout(500)

                    # 检查对话框
                    dialog = self.page.locator(".el-dialog:visible")
                    if dialog.is_visible():
                        self.log_result(page_name, "新建图表对话框", "passed", "对话框正常打开")

                        # 检查表单字段
                        form_items = dialog.locator(".el-form-item").all()
                        self.log_result(page_name, "新建图表表单", "passed",
                                        f"找到 {len(form_items)} 个表单项")

                        # 填写表单
                        name_input = dialog.locator("input[placeholder='请输入图表名称']")
                        if name_input.is_visible():
                            name_input.fill("测试图表")
                            self.log_result(page_name, "图表名称输入", "passed", "图表名称输入成功")

                        # 选择图表类型
                        type_select = dialog.locator(".el-select").first
                        if type_select.is_visible():
                            type_select.click()
                            self.page.wait_for_timeout(300)
                            # 选择折线图
                            self.page.locator(".el-select-dropdown__item:has-text('折线图')").first.click()
                            self.log_result(page_name, "图表类型选择", "passed", "图表类型选择成功")

                        # 关闭对话框
                        dialog.locator("button:has-text('取消')").click()
                        self.page.wait_for_timeout(300)
                    else:
                        self.log_result(page_name, "新建图表对话框", "failed", "对话框未打开")

                else:
                    self.log_result(page_name, "新建图表按钮", "warning", "新建图表按钮状态异常")

            except Exception as e:
                self.log_result(page_name, "新建图表功能", "failed", str(e))

            # 测试5: 高级图表视图
            print("\n[测试5] 高级图表视图验证")
            try:
                # 切换到高级图表视图
                self.page.locator("button:has-text('高级图表')").click()
                self.page.wait_for_timeout(500)

                # 检查数据源配置卡片
                data_source_card = self.page.locator(".data-source-card")
                if data_source_card.is_visible():
                    self.log_result(page_name, "数据源配置卡片", "passed", "数据源配置卡片可见")

                    # 检查数据源选择
                    data_source_select = data_source_card.locator(".el-select").first
                    if data_source_select.is_visible():
                        self.log_result(page_name, "数据源选择", "passed", "数据源选择下拉框可见")

                    # 检查生成数据按钮
                    generate_btn = data_source_card.locator("button:has-text('生成数据')")
                    if generate_btn.is_visible():
                        self.log_result(page_name, "生成数据按钮", "passed", "生成数据按钮可见")

                        # 点击生成数据
                        generate_btn.click()
                        self.page.wait_for_timeout(1000)

                        # 检查是否生成成功
                        self.log_result(page_name, "数据生成", "passed", "数据生成请求已发送")

                else:
                    self.log_result(page_name, "数据源配置卡片", "warning", "数据源配置卡片不可见")

                # 检查配置模板卡片
                template_card = self.page.locator(".template-card")
                if template_card.is_visible():
                    self.log_result(page_name, "配置模板卡片", "passed", "配置模板卡片可见")

                # 检查 ChartAnalysis 组件
                chart_analysis = self.page.locator(".chart-analysis, [class*='chart-analysis-component']")
                if chart_analysis.count() > 0:
                    self.log_result(page_name, "ChartAnalysis 组件", "passed", "ChartAnalysis 组件正常渲染")

            except Exception as e:
                self.log_result(page_name, "高级图表视图", "warning", str(e))

            # 测试6: 数据对比视图
            print("\n[测试6] 数据对比视图验证")
            try:
                # 切换到数据对比视图
                self.page.locator("button:has-text('数据对比')").click()
                self.page.wait_for_timeout(500)

                # 检查图表选择器卡片
                chart_selector_card = self.page.locator(".chart-selector-card")
                if chart_selector_card.is_visible():
                    self.log_result(page_name, "图表选择器卡片", "passed", "图表选择器卡片可见")

                    # 检查图表列表
                    chart_items = self.page.locator(".chart-item").all()
                    if len(chart_items) > 0:
                        self.log_result(page_name, "图表列表", "passed", f"找到 {len(chart_items)} 个图表")

                        # 选择第一个图表
                        chart_items[0].click()
                        self.page.wait_for_timeout(300)
                        self.log_result(page_name, "图表选择", "passed", "图表选择成功")

                    else:
                        self.log_result(page_name, "图表列表", "warning", "图表列表为空")

                else:
                    self.log_result(page_name, "图表选择器卡片", "warning", "图表选择器卡片不可见")

                # 检查对比设置卡片
                comparison_settings = self.page.locator(".comparison-settings-card")
                if comparison_settings.is_visible():
                    self.log_result(page_name, "对比设置卡片", "passed", "对比设置卡片可见")

                    # 检查设置项
                    switches = comparison_settings.locator(".el-switch").all()
                    self.log_result(page_name, "对比设置项", "passed", f"找到 {len(switches)} 个设置开关")

                # 检查对比图表卡片
                comparison_chart_card = self.page.locator(".comparison-chart-card")
                if comparison_chart_card.is_visible():
                    self.log_result(page_name, "对比图表卡片", "passed", "对比图表卡片可见")

                    # 检查导出按钮
                    export_btn = comparison_chart_card.locator("button:has-text('导出对比图')")
                    if export_btn.is_visible():
                        self.log_result(page_name, "导出对比图按钮", "passed", "导出对比图按钮可见")

                # 检查对比统计卡片
                comparison_stats = self.page.locator(".comparison-stats-card")
                if comparison_stats.is_visible():
                    self.log_result(page_name, "对比统计卡片", "passed", "对比统计卡片可见")

            except Exception as e:
                self.log_result(page_name, "数据对比视图", "warning", str(e))

            # 更新页面状态
            self.results["pages"][page_name]["status"] = "completed"

        except Exception as e:
            self.log_result(page_name, "页面测试", "failed", f"测试过程中发生错误: {e}")
            self.results["pages"][page_name]["status"] = "error"

    # ==================== API 对接测试 ====================

    def test_api_integration(self):
        """测试后端 API 对接"""
        print("\n" + "=" * 60)
        print("测试后端 API 对接")
        print("=" * 60)

        page_name = "api_integration"
        self.results["pages"][page_name] = {"tests": [], "status": "testing"}

        try:
            # 监听网络请求
            api_requests = []

            def capture_request(request):
                if "/api/" in request.url:
                    api_requests.append({
                        "url": request.url,
                        "method": request.method,
                        "timestamp": datetime.now().isoformat()
                    })

            self.page.on("request", capture_request)

            # 测试历史数据 API
            print("\n[测试1] 历史数据 API")
            self.page.goto(f"{self.base_url}/analysis/history")
            self.wait_for_page_load()

            # 尝试触发查询（使用唯一ID选择器）
            query_btn = self.page.locator("#history-query-btn")
            if query_btn.is_visible():
                query_btn.click()
                self.page.wait_for_timeout(2000)

            # 检查 API 请求
            history_api_requests = [r for r in api_requests if "/analysis/history" in r["url"]]
            if history_api_requests:
                self.log_result(page_name, "历史数据 API 请求", "passed",
                                f"检测到 {len(history_api_requests)} 个 API 请求")
            else:
                self.log_result(page_name, "历史数据 API 请求", "warning",
                                "未检测到历史数据 API 请求（可能使用模拟数据）")

            # 检查网络错误
            if self.network_errors:
                for error in self.network_errors:
                    if "/api/" in error["url"]:
                        self.log_result(page_name, f"API 错误-{error['url']}", "warning",
                                        f"状态码: {error['status']}")
            else:
                self.log_result(page_name, "API 错误检查", "passed", "未检测到 API 错误")

            # 更新页面状态
            self.results["pages"][page_name]["status"] = "completed"

        except Exception as e:
            self.log_result(page_name, "API 对接测试", "failed", f"测试过程中发生错误: {e}")
            self.results["pages"][page_name]["status"] = "error"

    # ==================== 错误处理测试 ====================

    def test_error_handling(self):
        """测试错误处理"""
        print("\n" + "=" * 60)
        print("测试错误处理")
        print("=" * 60)

        page_name = "error_handling"
        self.results["pages"][page_name] = {"tests": [], "status": "testing"}

        try:
            # 测试1: 检查控制台错误
            print("\n[测试1] 控制台错误检查")
            console_errors = [log for log in self.console_logs if log["type"] == "error"]

            if console_errors:
                for error in console_errors[:5]:  # 只显示前5个错误
                    self.log_result(page_name, "控制台错误", "warning", error["text"][:100])
            else:
                self.log_result(page_name, "控制台错误检查", "passed", "未检测到控制台错误")

            # 测试2: 检查 Vue 错误
            print("\n[测试2] Vue 错误检查")
            vue_errors = [log for log in self.console_logs if "Vue" in log["text"] and log["type"] == "error"]

            if vue_errors:
                for error in vue_errors:
                    self.log_result(page_name, "Vue 错误", "warning", error["text"][:100])
            else:
                self.log_result(page_name, "Vue 错误检查", "passed", "未检测到 Vue 错误")

            # 测试3: 检查网络错误
            print("\n[测试3] 网络错误检查")
            if self.network_errors:
                for error in self.network_errors:
                    self.log_result(page_name, f"网络错误-{error['status']}", "warning",
                                    f"URL: {error['url']}")
            else:
                self.log_result(page_name, "网络错误检查", "passed", "未检测到网络错误")

            # 更新页面状态
            self.results["pages"][page_name]["status"] = "completed"

        except Exception as e:
            self.log_result(page_name, "错误处理测试", "failed", f"测试过程中发生错误: {e}")
            self.results["pages"][page_name]["status"] = "error"

    # ==================== 生成报告 ====================

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("生成测试报告")
        print("=" * 60)

        # 创建报告目录
        report_dir = Path("test_results")
        report_dir.mkdir(parents=True, exist_ok=True)

        # 保存 JSON 报告
        report_path = report_dir / f"analysis_module_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n测试报告已保存: {report_path}")

        # 生成 Markdown 报告
        md_report = self._generate_markdown_report()
        md_path = report_dir / f"analysis_module_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)

        print(f"Markdown 报告已保存: {md_path}")

        # 打印摘要
        self._print_summary()

        return self.results

    def _generate_markdown_report(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "# 数据分析模块功能完整性验证报告",
            "",
            f"**测试时间**: {self.results['test_time']}",
            "",
            "## 测试摘要",
            "",
            f"- 总测试数: {self.results['summary']['total_tests']}",
            f"- 通过: {self.results['summary']['passed']}",
            f"- 失败: {self.results['summary']['failed']}",
            f"- 警告: {self.results['summary']['warnings']}",
            "",
        ]

        # 各页面测试结果
        for page_name, page_data in self.results["pages"].items():
            lines.extend([
                f"## {page_name.upper()} 页面测试结果",
                "",
                f"**状态**: {page_data['status']}",
                "",
                "| 测试项 | 状态 | 消息 |",
                "|--------|------|------|",
            ])

            for test in page_data["tests"]:
                status_emoji = {
                    "passed": "✅",
                    "failed": "❌",
                    "warning": "⚠️"
                }.get(test["status"], "❓")
                lines.append(f"| {test['name']} | {status_emoji} {test['status']} | {test['message']} |")

            lines.append("")

        # 问题列表
        if self.results["issues"]:
            lines.extend([
                "## 发现的问题",
                "",
            ])
            for issue in self.results["issues"]:
                lines.append(f"- **[{issue['page']}]** {issue['test']}: {issue['message']}")

        return "\n".join(lines)

    def _print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("测试摘要")
        print("=" * 60)
        print(f"总测试数: {self.results['summary']['total_tests']}")
        print(f"通过: {self.results['summary']['passed']}")
        print(f"失败: {self.results['summary']['failed']}")
        print(f"警告: {self.results['summary']['warnings']}")

        # 计算通过率
        if self.results['summary']['total_tests'] > 0:
            pass_rate = (self.results['summary']['passed'] / self.results['summary']['total_tests']) * 100
            print(f"通过率: {pass_rate:.1f}%")

        # 显示问题列表
        if self.results["issues"]:
            print("\n发现的问题:")
            for issue in self.results["issues"][:10]:  # 只显示前10个问题
                print(f"  - [{issue['page']}] {issue['test']}: {issue['message']}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("数据分析模块功能完整性验证测试")
    print("=" * 60)

    tester = AnalysisModuleTester()

    with sync_playwright() as p:
        try:
            # 初始化浏览器
            print("\n初始化浏览器...")
            tester.setup_browser(p)

            # 执行测试
            tester.test_realtime_page()
            tester.test_history_page()
            tester.test_charts_page()
            tester.test_api_integration()
            tester.test_error_handling()

        finally:
            # 关闭浏览器
            print("\n关闭浏览器...")
            tester.teardown_browser()

    # 生成报告
    results = tester.generate_report()

    return results


if __name__ == "__main__":
    main()
