"""
@file test_settings_pages.py
@path tests/e2e/
@description 系统设置模块所有子页面的功能完整性验证测试
@author Test Debugger Agent
@date 2026-03-08
@dependencies playwright
"""

import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, expect


class SettingsPagesTester:
    """系统设置模块测试器"""

    def __init__(self, base_url: str = "http://localhost:5173"):
        self.base_url = base_url
        self.browser = None
        self.page = None
        self.context = None
        self.test_results = {
            "audit": {"status": "pending", "tests": [], "errors": []},
            "users": {"status": "pending", "tests": [], "errors": []},
            "config": {"status": "pending", "tests": [], "errors": []},
            "performance": {"status": "pending", "tests": [], "errors": []}
        }

    def setup(self):
        """初始化测试环境"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN"
        )
        self.page = self.context.new_page()

    def teardown(self):
        """清理测试环境"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def navigate_to_settings(self, sub_path: str = "") -> bool:
        """
        导航到设置页面

        Args:
            sub_path: 子路径，如 "audit", "users" 等

        Returns:
            bool: 是否成功导航
        """
        try:
            url = f"{self.base_url}/settings/{sub_path}" if sub_path else f"{self.base_url}/settings"
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(1)  # 等待Vue组件渲染
            return True
        except Exception as e:
            print(f"导航失败: {e}")
            return False

    def take_screenshot(self, filename: str):
        """截图保存"""
        try:
            self.page.screenshot(path=f"screenshots/{filename}", full_page=True)
        except Exception as e:
            print(f"截图失败: {e}")

    # ==================== 审计日志页面测试 ====================

    def test_audit_page(self):
        """测试审计日志页面功能"""
        print("\n=== 测试审计日志页面 ===")
        page_name = "audit"

        try:
            # 1. 页面加载测试
            print("1. 测试页面加载...")
            if not self.navigate_to_settings("audit"):
                self.test_results[page_name]["errors"].append("页面加载失败")
                return

            # 检查页面标题
            title = self.page.locator(".page-title").first
            if title.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "页面标题显示",
                    "status": "pass",
                    "detail": f"标题: {title.text_content()}"
                })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "页面标题显示",
                    "status": "fail",
                    "detail": "页面标题不可见"
                })

            # 2. 刷新按钮测试
            print("2. 测试刷新按钮...")
            refresh_btn = self.page.locator("button:has-text('刷新')").first
            if refresh_btn.is_visible() and refresh_btn.is_enabled():
                refresh_btn.click()
                self.page.wait_for_timeout(1000)
                self.test_results[page_name]["tests"].append({
                    "name": "刷新按钮功能",
                    "status": "pass",
                    "detail": "刷新按钮可点击"
                })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "刷新按钮功能",
                    "status": "fail",
                    "detail": "刷新按钮不可见或不可用"
                })

            # 3. 导出按钮测试
            print("3. 测试导出按钮...")
            export_btn = self.page.locator("button:has-text('导出')").first
            if export_btn.is_visible() and export_btn.is_enabled():
                self.test_results[page_name]["tests"].append({
                    "name": "导出按钮功能",
                    "status": "pass",
                    "detail": "导出按钮可点击"
                })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "导出按钮功能",
                    "status": "fail",
                    "detail": "导出按钮不可见或不可用"
                })

            # 4. 筛选功能测试
            print("4. 测试筛选功能...")
            # 检查是否有筛选组件
            filter_component = self.page.locator(".audit-log-filter, .filter-card").first
            if filter_component.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "筛选组件显示",
                    "status": "pass",
                    "detail": "筛选组件正常显示"
                })

                # 尝试使用筛选
                search_btn = self.page.locator("button:has-text('搜索')").first
                if search_btn.is_visible():
                    search_btn.click()
                    self.page.wait_for_timeout(500)
                    self.test_results[page_name]["tests"].append({
                        "name": "筛选搜索功能",
                        "status": "pass",
                        "detail": "搜索按钮可点击"
                    })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "筛选组件显示",
                    "status": "fail",
                    "detail": "筛选组件不可见"
                })

            # 5. 日志列表测试
            print("5. 测试日志列表...")
            log_table = self.page.locator(".el-table").first
            if log_table.is_visible():
                rows = self.page.locator(".el-table__row")
                row_count = rows.count()
                self.test_results[page_name]["tests"].append({
                    "name": "日志列表显示",
                    "status": "pass" if row_count > 0 else "warning",
                    "detail": f"日志列表可见，共 {row_count} 条记录"
                })

                # 测试详情查看
                if row_count > 0:
                    detail_btn = self.page.locator("button:has-text('详情')").first
                    if detail_btn.is_visible():
                        detail_btn.click()
                        self.page.wait_for_timeout(500)

                        # 检查详情对话框
                        dialog = self.page.locator(".el-dialog:visible").first
                        if dialog.is_visible():
                            self.test_results[page_name]["tests"].append({
                                "name": "日志详情查看",
                                "status": "pass",
                                "detail": "详情对话框正常显示"
                            })
                            # 关闭对话框
                            close_btn = dialog.locator("button:has-text('关闭')")
                            if close_btn.is_visible():
                                close_btn.click()
                                self.page.wait_for_timeout(300)
                        else:
                            self.test_results[page_name]["tests"].append({
                                "name": "日志详情查看",
                                "status": "fail",
                                "detail": "详情对话框未显示"
                            })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "日志列表显示",
                    "status": "fail",
                    "detail": "日志列表不可见"
                })

            # 6. 分页功能测试
            print("6. 测试分页功能...")
            pagination = self.page.locator(".el-pagination").first
            if pagination.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "分页组件显示",
                    "status": "pass",
                    "detail": "分页组件正常显示"
                })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "分页组件显示",
                    "status": "warning",
                    "detail": "分页组件不可见（可能数据较少）"
                })

            # 7. 标签页切换测试
            print("7. 测试标签页切换...")
            stats_tab = self.page.locator(".el-tabs__item:has-text('统计分析')").first
            if stats_tab.is_visible():
                stats_tab.click()
                self.page.wait_for_timeout(500)
                self.test_results[page_name]["tests"].append({
                    "name": "标签页切换",
                    "status": "pass",
                    "detail": "统计分析标签页可切换"
                })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "标签页切换",
                    "status": "warning",
                    "detail": "统计分析标签页不可见"
                })

            self.test_results[page_name]["status"] = "completed"

        except Exception as e:
            self.test_results[page_name]["errors"].append(f"测试异常: {str(e)}")
            self.test_results[page_name]["status"] = "error"

    # ==================== 用户管理页面测试 ====================

    def test_users_page(self):
        """测试用户管理页面功能"""
        print("\n=== 测试用户管理页面 ===")
        page_name = "users"

        try:
            # 1. 页面加载测试
            print("1. 测试页面加载...")
            if not self.navigate_to_settings("users"):
                self.test_results[page_name]["errors"].append("页面加载失败")
                return

            # 检查页面标题
            title = self.page.locator(".page-title").first
            if title.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "页面标题显示",
                    "status": "pass",
                    "detail": f"标题: {title.text_content()}"
                })

            # 2. 添加用户按钮测试
            print("2. 测试添加用户按钮...")
            add_user_btn = self.page.locator("button:has-text('添加用户')").first
            if add_user_btn.is_visible() and add_user_btn.is_enabled():
                self.test_results[page_name]["tests"].append({
                    "name": "添加用户按钮",
                    "status": "pass",
                    "detail": "添加用户按钮可点击"
                })

                # 点击添加用户
                add_user_btn.click()
                self.page.wait_for_timeout(500)

                # 检查对话框
                dialog = self.page.locator(".el-dialog:visible").first
                if dialog.is_visible():
                    self.test_results[page_name]["tests"].append({
                        "name": "添加用户对话框",
                        "status": "pass",
                        "detail": "添加用户对话框正常显示"
                    })

                    # 测试表单字段
                    username_input = dialog.locator("input[placeholder='请输入用户名']").first
                    email_input = dialog.locator("input[placeholder='请输入邮箱']").first
                    password_input = dialog.locator("input[placeholder='请输入密码']").first

                    if username_input.is_visible():
                        self.test_results[page_name]["tests"].append({
                            "name": "用户名输入框",
                            "status": "pass",
                            "detail": "用户名输入框可见"
                        })
                    else:
                        self.test_results[page_name]["tests"].append({
                            "name": "用户名输入框",
                            "status": "fail",
                            "detail": "用户名输入框不可见"
                        })

                    # 关闭对话框
                    cancel_btn = dialog.locator("button:has-text('取消')")
                    if cancel_btn.is_visible():
                        cancel_btn.click()
                        self.page.wait_for_timeout(300)
                else:
                    self.test_results[page_name]["tests"].append({
                        "name": "添加用户对话框",
                        "status": "fail",
                        "detail": "添加用户对话框未显示"
                    })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "添加用户按钮",
                    "status": "fail",
                    "detail": "添加用户按钮不可见或不可用"
                })

            # 3. 刷新按钮测试
            print("3. 测试刷新按钮...")
            refresh_btn = self.page.locator("button:has-text('刷新')").first
            if refresh_btn.is_visible() and refresh_btn.is_enabled():
                refresh_btn.click()
                self.page.wait_for_timeout(500)
                self.test_results[page_name]["tests"].append({
                    "name": "刷新按钮功能",
                    "status": "pass",
                    "detail": "刷新按钮可点击"
                })

            # 4. 筛选功能测试
            print("4. 测试筛选功能...")
            filter_card = self.page.locator(".filter-card").first
            if filter_card.is_visible():
                # 测试用户名筛选
                username_filter = self.page.locator("input[placeholder='请输入用户名']").first
                if username_filter.is_visible():
                    username_filter.fill("admin")
                    self.page.wait_for_timeout(300)

                    # 点击搜索
                    search_btn = self.page.locator("button:has-text('搜索')").first
                    if search_btn.is_visible():
                        search_btn.click()
                        self.page.wait_for_timeout(500)
                        self.test_results[page_name]["tests"].append({
                            "name": "筛选搜索功能",
                            "status": "pass",
                            "detail": "筛选搜索功能正常"
                        })

                # 重置筛选
                reset_btn = self.page.locator("button:has-text('重置')").first
                if reset_btn.is_visible():
                    reset_btn.click()
                    self.page.wait_for_timeout(300)

            # 5. 用户列表测试
            print("5. 测试用户列表...")
            user_table = self.page.locator(".el-table").first
            if user_table.is_visible():
                rows = self.page.locator(".el-table__row")
                row_count = rows.count()
                self.test_results[page_name]["tests"].append({
                    "name": "用户列表显示",
                    "status": "pass" if row_count > 0 else "warning",
                    "detail": f"用户列表可见，共 {row_count} 个用户"
                })

                # 测试编辑按钮
                if row_count > 0:
                    edit_btn = self.page.locator("button:has-text('编辑')").first
                    if edit_btn.is_visible():
                        edit_btn.click()
                        self.page.wait_for_timeout(500)

                        # 检查编辑对话框
                        dialog = self.page.locator(".el-dialog:visible").first
                        if dialog.is_visible():
                            self.test_results[page_name]["tests"].append({
                                "name": "编辑用户对话框",
                                "status": "pass",
                                "detail": "编辑用户对话框正常显示"
                            })
                            # 关闭对话框
                            cancel_btn = dialog.locator("button:has-text('取消')")
                            if cancel_btn.is_visible():
                                cancel_btn.click()
                                self.page.wait_for_timeout(300)

                # 测试权限按钮
                permission_btn = self.page.locator("button:has-text('权限')").first
                if permission_btn.is_visible():
                    permission_btn.click()
                    self.page.wait_for_timeout(500)

                    # 检查权限对话框
                    dialog = self.page.locator(".el-dialog:visible").first
                    if dialog.is_visible():
                        self.test_results[page_name]["tests"].append({
                            "name": "权限设置对话框",
                            "status": "pass",
                            "detail": "权限设置对话框正常显示"
                        })
                        # 关闭对话框
                        cancel_btn = dialog.locator("button:has-text('取消')")
                        if cancel_btn.is_visible():
                            cancel_btn.click()
                            self.page.wait_for_timeout(300)

            # 6. 状态切换测试
            print("6. 测试状态切换...")
            status_switch = self.page.locator(".el-switch").first
            if status_switch.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "状态切换开关",
                    "status": "pass",
                    "detail": "状态切换开关可见"
                })

            # 7. 分页功能测试
            print("7. 测试分页功能...")
            pagination = self.page.locator(".el-pagination").first
            if pagination.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "分页组件显示",
                    "status": "pass",
                    "detail": "分页组件正常显示"
                })

            self.test_results[page_name]["status"] = "completed"

        except Exception as e:
            self.test_results[page_name]["errors"].append(f"测试异常: {str(e)}")
            self.test_results[page_name]["status"] = "error"

    # ==================== 系统配置页面测试 ====================

    def test_config_page(self):
        """测试系统配置页面功能"""
        print("\n=== 测试系统配置页面 ===")
        page_name = "config"

        try:
            # 1. 页面加载测试
            print("1. 测试页面加载...")
            if not self.navigate_to_settings("config"):
                self.test_results[page_name]["errors"].append("页面加载失败")
                return

            # 检查页面标题
            title = self.page.locator(".page-title").first
            if title.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "页面标题显示",
                    "status": "pass",
                    "detail": f"标题: {title.text_content()}"
                })

            # 2. 导入配置按钮测试
            print("2. 测试导入配置按钮...")
            import_btn = self.page.locator("button:has-text('导入配置')").first
            if import_btn.is_visible() and import_btn.is_enabled():
                self.test_results[page_name]["tests"].append({
                    "name": "导入配置按钮",
                    "status": "pass",
                    "detail": "导入配置按钮可点击"
                })

                # 点击导入配置
                import_btn.click()
                self.page.wait_for_timeout(500)

                # 检查对话框
                dialog = self.page.locator(".el-dialog:visible").first
                if dialog.is_visible():
                    self.test_results[page_name]["tests"].append({
                        "name": "导入配置对话框",
                        "status": "pass",
                        "detail": "导入配置对话框正常显示"
                    })

                    # 检查上传组件
                    upload_area = dialog.locator(".el-upload-dragger").first
                    if upload_area.is_visible():
                        self.test_results[page_name]["tests"].append({
                            "name": "配置文件上传组件",
                            "status": "pass",
                            "detail": "上传组件可见"
                        })

                    # 关闭对话框
                    cancel_btn = dialog.locator("button:has-text('取消')")
                    if cancel_btn.is_visible():
                        cancel_btn.click()
                        self.page.wait_for_timeout(300)
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "导入配置按钮",
                    "status": "fail",
                    "detail": "导入配置按钮不可见或不可用"
                })

            # 3. 导出配置按钮测试
            print("3. 测试导出配置按钮...")
            export_btn = self.page.locator("button:has-text('导出配置')").first
            if export_btn.is_visible() and export_btn.is_enabled():
                export_btn.click()
                self.page.wait_for_timeout(500)

                # 检查导出对话框
                dialog = self.page.locator(".el-dialog:visible").first
                if dialog.is_visible():
                    self.test_results[page_name]["tests"].append({
                        "name": "导出配置对话框",
                        "status": "pass",
                        "detail": "导出配置对话框正常显示"
                    })

                    # 检查导出选项
                    checkboxes = dialog.locator(".el-checkbox")
                    if checkboxes.count() > 0:
                        self.test_results[page_name]["tests"].append({
                            "name": "导出分类选择",
                            "status": "pass",
                            "detail": f"导出分类选项可见，共 {checkboxes.count()} 个"
                        })

                    # 关闭对话框
                    cancel_btn = dialog.locator("button:has-text('取消')")
                    if cancel_btn.is_visible():
                        cancel_btn.click()
                        self.page.wait_for_timeout(300)
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "导出配置按钮",
                    "status": "fail",
                    "detail": "导出配置按钮不可见或不可用"
                })

            # 4. 重置按钮测试
            print("4. 测试重置按钮...")
            reset_btn = self.page.locator("button:has-text('重置')").first
            if reset_btn.is_visible() and reset_btn.is_enabled():
                self.test_results[page_name]["tests"].append({
                    "name": "重置按钮",
                    "status": "pass",
                    "detail": "重置按钮可点击"
                })
                # 不实际点击重置，避免影响配置

            # 5. 保存配置按钮测试
            print("5. 测试保存配置按钮...")
            save_btn = self.page.locator("button:has-text('保存配置')").first
            if save_btn.is_visible():
                is_disabled = save_btn.is_disabled()
                self.test_results[page_name]["tests"].append({
                    "name": "保存配置按钮",
                    "status": "pass",
                    "detail": f"保存配置按钮可见，{'禁用状态（无更改）' if is_disabled else '可用状态'}"
                })

            # 6. 配置状态指示器测试
            print("6. 测试配置状态指示器...")
            status_bar = self.page.locator(".status-bar").first
            if status_bar.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "配置状态指示器",
                    "status": "pass",
                    "detail": "配置状态指示器可见"
                })

                # 检查状态标签
                status_tags = self.page.locator(".status-bar .el-tag")
                if status_tags.count() > 0:
                    tag_text = status_tags.first.text_content()
                    self.test_results[page_name]["tests"].append({
                        "name": "配置状态标签",
                        "status": "pass",
                        "detail": f"当前状态: {tag_text}"
                    })

            # 7. 配置编辑器测试
            print("7. 测试配置编辑器...")
            config_editor = self.page.locator(".editor-card, .config-editor").first
            if config_editor.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "配置编辑器显示",
                    "status": "pass",
                    "detail": "配置编辑器可见"
                })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "配置编辑器显示",
                    "status": "warning",
                    "detail": "配置编辑器不可见"
                })

            # 8. 配置历史测试
            print("8. 测试配置历史...")
            history_card = self.page.locator(".history-card").first
            if history_card.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "配置历史显示",
                    "status": "pass",
                    "detail": "配置历史组件可见"
                })

            self.test_results[page_name]["status"] = "completed"

        except Exception as e:
            self.test_results[page_name]["errors"].append(f"测试异常: {str(e)}")
            self.test_results[page_name]["status"] = "error"

    # ==================== 性能分析页面测试 ====================

    def test_performance_page(self):
        """测试性能分析页面功能"""
        print("\n=== 测试性能分析页面 ===")
        page_name = "performance"

        try:
            # 1. 页面加载测试
            print("1. 测试页面加载...")
            if not self.navigate_to_settings("performance"):
                self.test_results[page_name]["errors"].append("页面加载失败")
                return

            # 检查页面标题
            title = self.page.locator(".page-title").first
            if title.is_visible():
                self.test_results[page_name]["tests"].append({
                    "name": "页面标题显示",
                    "status": "pass",
                    "detail": f"标题: {title.text_content()}"
                })

            # 2. 刷新按钮测试
            print("2. 测试刷新按钮...")
            refresh_btn = self.page.locator("button:has-text('刷新')").first
            if refresh_btn.is_visible() and refresh_btn.is_enabled():
                refresh_btn.click()
                self.page.wait_for_timeout(1000)
                self.test_results[page_name]["tests"].append({
                    "name": "刷新按钮功能",
                    "status": "pass",
                    "detail": "刷新按钮可点击"
                })

            # 3. 生成报告按钮测试
            print("3. 测试生成报告按钮...")
            generate_report_btn = self.page.locator("button:has-text('生成报告')").first
            if generate_report_btn.is_visible() and generate_report_btn.is_enabled():
                self.test_results[page_name]["tests"].append({
                    "name": "生成报告按钮",
                    "status": "pass",
                    "detail": "生成报告按钮可点击"
                })

            # 4. 导出报告按钮测试
            print("4. 测试导出报告按钮...")
            export_report_btn = self.page.locator("button:has-text('导出报告')").first
            if export_report_btn.is_visible() and export_report_btn.is_enabled():
                self.test_results[page_name]["tests"].append({
                    "name": "导出报告按钮",
                    "status": "pass",
                    "detail": "导出报告按钮可点击"
                })

            # 5. 性能摘要卡片测试
            print("5. 测试性能摘要卡片...")
            summary_cards = self.page.locator(".summary-card")
            if summary_cards.count() > 0:
                self.test_results[page_name]["tests"].append({
                    "name": "性能摘要卡片",
                    "status": "pass",
                    "detail": f"性能摘要卡片可见，共 {summary_cards.count()} 个"
                })

                # 检查CPU卡片
                cpu_card = self.page.locator(".cpu-card").first
                if cpu_card.is_visible():
                    self.test_results[page_name]["tests"].append({
                        "name": "CPU使用率卡片",
                        "status": "pass",
                        "detail": "CPU使用率卡片可见"
                    })

                # 检查内存卡片
                memory_card = self.page.locator(".memory-card").first
                if memory_card.is_visible():
                    self.test_results[page_name]["tests"].append({
                        "name": "内存使用率卡片",
                        "status": "pass",
                        "detail": "内存使用率卡片可见"
                    })
            else:
                self.test_results[page_name]["tests"].append({
                    "name": "性能摘要卡片",
                    "status": "warning",
                    "detail": "性能摘要卡片不可见"
                })

            # 6. 标签页测试
            print("6. 测试标签页功能...")
            tabs = self.page.locator(".el-tabs__item")
            if tabs.count() > 0:
                self.test_results[page_name]["tests"].append({
                    "name": "标签页显示",
                    "status": "pass",
                    "detail": f"标签页可见，共 {tabs.count()} 个"
                })

                # 测试系统资源标签页
                system_tab = self.page.locator(".el-tabs__item:has-text('系统资源')").first
                if system_tab.is_visible():
                    system_tab.click()
                    self.page.wait_for_timeout(500)
                    self.test_results[page_name]["tests"].append({
                        "name": "系统资源标签页",
                        "status": "pass",
                        "detail": "系统资源标签页可切换"
                    })

                    # 检查系统信息描述
                    descriptions = self.page.locator(".el-descriptions")
                    if descriptions.count() > 0:
                        self.test_results[page_name]["tests"].append({
                            "name": "系统信息显示",
                            "status": "pass",
                            "detail": f"系统信息描述可见，共 {descriptions.count()} 个"
                        })

                # 测试函数性能标签页
                functions_tab = self.page.locator(".el-tabs__item:has-text('函数性能')").first
                if functions_tab.is_visible():
                    functions_tab.click()
                    self.page.wait_for_timeout(500)
                    self.test_results[page_name]["tests"].append({
                        "name": "函数性能标签页",
                        "status": "pass",
                        "detail": "函数性能标签页可切换"
                    })

                    # 检查开始分析按钮
                    start_profiling_btn = self.page.locator("button:has-text('开始分析')").first
                    if start_profiling_btn.is_visible():
                        self.test_results[page_name]["tests"].append({
                            "name": "性能分析控制按钮",
                            "status": "pass",
                            "detail": "开始分析按钮可见"
                        })

                # 测试性能热点标签页
                hotspots_tab = self.page.locator(".el-tabs__item:has-text('性能热点')").first
                if hotspots_tab.is_visible():
                    hotspots_tab.click()
                    self.page.wait_for_timeout(500)
                    self.test_results[page_name]["tests"].append({
                        "name": "性能热点标签页",
                        "status": "pass",
                        "detail": "性能热点标签页可切换"
                    })

                    # 检查筛选控件
                    threshold_input = self.page.locator(".el-input-number").first
                    if threshold_input.is_visible():
                        self.test_results[page_name]["tests"].append({
                            "name": "性能热点筛选",
                            "status": "pass",
                            "detail": "时间阈值筛选控件可见"
                        })

                # 测试内存分析标签页
                memory_tab = self.page.locator(".el-tabs__item:has-text('内存分析')").first
                if memory_tab.is_visible():
                    memory_tab.click()
                    self.page.wait_for_timeout(500)
                    self.test_results[page_name]["tests"].append({
                        "name": "内存分析标签页",
                        "status": "pass",
                        "detail": "内存分析标签页可切换"
                    })

                    # 检查内存追踪按钮
                    start_tracking_btn = self.page.locator("button:has-text('开始追踪')").first
                    if start_tracking_btn.is_visible():
                        self.test_results[page_name]["tests"].append({
                            "name": "内存追踪控制按钮",
                            "status": "pass",
                            "detail": "开始追踪按钮可见"
                        })

            # 7. 进度条测试
            print("7. 测试进度条显示...")
            progress_bars = self.page.locator(".el-progress")
            if progress_bars.count() > 0:
                self.test_results[page_name]["tests"].append({
                    "name": "进度条显示",
                    "status": "pass",
                    "detail": f"进度条可见，共 {progress_bars.count()} 个"
                })

            self.test_results[page_name]["status"] = "completed"

        except Exception as e:
            self.test_results[page_name]["errors"].append(f"测试异常: {str(e)}")
            self.test_results[page_name]["status"] = "error"

    # ==================== 生成测试报告 ====================

    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("=" * 80)
        report.append("系统设置模块功能完整性验证报告")
        report.append("=" * 80)
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"测试环境: {self.base_url}")
        report.append("")

        # 统计信息
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warning_tests = 0

        for page_name, result in self.test_results.items():
            for test in result.get("tests", []):
                total_tests += 1
                if test["status"] == "pass":
                    passed_tests += 1
                elif test["status"] == "fail":
                    failed_tests += 1
                elif test["status"] == "warning":
                    warning_tests += 1

        report.append("测试统计:")
        report.append(f"  总测试数: {total_tests}")
        report.append(f"  通过: {passed_tests}")
        report.append(f"  失败: {failed_tests}")
        report.append(f"  警告: {warning_tests}")
        report.append(f"  通过率: {(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "  通过率: 0%")
        report.append("")

        # 详细结果
        for page_name, result in self.test_results.items():
            page_title = {
                "audit": "审计日志页面 (/settings/audit)",
                "users": "用户管理页面 (/settings/users)",
                "config": "系统配置页面 (/settings/config)",
                "performance": "性能分析页面 (/settings/performance)"
            }.get(page_name, page_name)

            report.append("-" * 80)
            report.append(f"{page_title}")
            report.append(f"状态: {result['status']}")
            report.append("")

            if result.get("tests"):
                report.append("测试项:")
                for i, test in enumerate(result["tests"], 1):
                    status_icon = {
                        "pass": "✓",
                        "fail": "✗",
                        "warning": "⚠"
                    }.get(test["status"], "?")
                    report.append(f"  {i}. [{status_icon}] {test['name']}: {test['detail']}")

            if result.get("errors"):
                report.append("")
                report.append("错误:")
                for error in result["errors"]:
                    report.append(f"  - {error}")

            report.append("")

        report.append("=" * 80)
        report.append("测试完成")
        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self, filename: str = "settings_test_report.txt"):
        """保存测试报告到文件"""
        report = self.generate_report()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n测试报告已保存到: {filename}")
        return report


def main():
    """主测试函数"""
    print("开始系统设置模块功能完整性验证测试...")
    print("=" * 80)

    tester = SettingsPagesTester(base_url="http://localhost:5173")

    try:
        # 初始化
        tester.setup()

        # 执行所有测试
        tester.test_audit_page()
        tester.test_users_page()
        tester.test_config_page()
        tester.test_performance_page()

        # 生成并保存报告
        report = tester.save_report("settings_test_report.txt")
        print("\n" + report)

    except Exception as e:
        print(f"\n测试执行失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理
        tester.teardown()


if __name__ == "__main__":
    main()
