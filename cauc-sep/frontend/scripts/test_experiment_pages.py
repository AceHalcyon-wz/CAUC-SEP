"""
@file test_experiment_pages.py
@path cauc-sep/frontend/
@description 实验控制模块所有子页面功能完整性验证测试脚本
@author Agent
@date 2024-03-08
"""

from playwright.sync_api import sync_playwright, Page, expect
import time
import json
from datetime import datetime
from typing import Dict, List, Any


class TestResult:
    """测试结果记录类"""

    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.now()

    def add_page_result(self, page_name: str, tests: Dict[str, Any]):
        """添加页面测试结果"""
        self.results[page_name] = {
            "tests": tests,
            "passed": sum(1 for t in tests.values() if t.get("status") == "pass"),
            "failed": sum(1 for t in tests.values() if t.get("status") == "fail"),
            "warnings": sum(1 for t in tests.values() if t.get("status") == "warning"),
            "timestamp": datetime.now().isoformat()
        }

    def generate_report(self) -> str:
        """生成测试报告"""
        total_passed = sum(r["passed"] for r in self.results.values())
        total_failed = sum(r["failed"] for r in self.results.values())
        total_warnings = sum(r["warnings"] for r in self.results.values())

        report = []
        report.append("=" * 80)
        report.append("实验控制模块功能完整性验证报告")
        report.append("=" * 80)
        report.append(f"测试时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"总测试项: {total_passed + total_failed + total_warnings}")
        report.append(f"通过: {total_passed} | 失败: {total_failed} | 警告: {total_warnings}")
        report.append("=" * 80)

        for page_name, page_result in self.results.items():
            report.append(f"\n{'─' * 80}")
            report.append(f"页面: {page_name}")
            report.append(f"通过: {page_result['passed']} | 失败: {page_result['failed']} | 警告: {page_result['warnings']}")
            report.append("─" * 40)

            for test_name, test_result in page_result["tests"].items():
                status_icon = {
                    "pass": "[PASS]",
                    "fail": "[FAIL]",
                    "warning": "[WARN]"
                }.get(test_result.get("status"), "[????]")

                report.append(f"  {status_icon} {test_name}")
                if test_result.get("message"):
                    report.append(f"         {test_result['message']}")
                if test_result.get("error"):
                    report.append(f"         错误: {test_result['error']}")

        report.append("\n" + "=" * 80)
        report.append("测试完成")
        report.append("=" * 80)

        return "\n".join(report)


def wait_for_page_load(page: Page, timeout: int = 10000):
    """等待页面完全加载"""
    page.wait_for_load_state("networkidle", timeout=timeout)
    page.wait_for_timeout(500)  # 额外等待动画完成


def check_element_exists(page: Page, selector: str, description: str) -> Dict[str, Any]:
    """检查元素是否存在"""
    try:
        element = page.locator(selector).first
        if element.count() > 0:
            return {"status": "pass", "message": f"{description} 存在"}
        else:
            return {"status": "fail", "message": f"{description} 不存在"}
    except Exception as e:
        return {"status": "fail", "message": f"{description} 检查失败", "error": str(e)}


def check_element_clickable(page: Page, selector: str, description: str) -> Dict[str, Any]:
    """检查元素是否可点击"""
    try:
        element = page.locator(selector).first
        if element.count() == 0:
            return {"status": "fail", "message": f"{description} 不存在"}

        # 检查是否可见
        if not element.is_visible():
            return {"status": "warning", "message": f"{description} 存在但不可见"}

        # 检查是否禁用
        is_disabled = element.is_disabled()
        if is_disabled:
            return {"status": "warning", "message": f"{description} 存在但被禁用（可能需要先连接设备）"}

        return {"status": "pass", "message": f"{description} 可点击"}
    except Exception as e:
        return {"status": "fail", "message": f"{description} 检查失败", "error": str(e)}


def check_form_input(page: Page, selector: str, description: str) -> Dict[str, Any]:
    """检查表单输入框是否可用"""
    try:
        element = page.locator(selector).first
        if element.count() == 0:
            return {"status": "fail", "message": f"{description} 不存在"}

        # 检查是否可见
        if not element.is_visible():
            return {"status": "warning", "message": f"{description} 存在但不可见"}

        # 检查是否禁用
        is_disabled = element.is_disabled()
        if is_disabled:
            return {"status": "warning", "message": f"{description} 存在但被禁用"}

        return {"status": "pass", "message": f"{description} 可输入"}
    except Exception as e:
        return {"status": "fail", "message": f"{description} 检查失败", "error": str(e)}


def test_motor_control_page(page: Page) -> Dict[str, Any]:
    """测试电机控制页面"""
    tests = {}

    # 导航到电机控制页面
    page.goto("http://localhost:5173/experiment/motor")
    wait_for_page_load(page)

    # 页面标题检查
    tests["页面标题"] = check_element_exists(page, ".page-title:has-text('电机控制')", "页面标题")

    # 刷新数据按钮
    tests["刷新数据按钮"] = check_element_clickable(page, ".action-btn:has-text('刷新数据')", "刷新数据按钮")

    # 导出数据按钮
    tests["导出数据按钮"] = check_element_clickable(page, ".action-btn:has-text('导出数据')", "导出数据按钮")

    # 急停按钮
    tests["急停按钮"] = check_element_exists(page, ".emergency-stop-btn", "急停按钮")

    # 运动控制卡片
    tests["运动控制卡片"] = check_element_exists(page, ".motor-control", "运动控制卡片")

    # 目标位置输入
    tests["目标位置输入"] = check_form_input(page, ".position-input .el-input__inner", "目标位置输入框")

    # 运动速度输入
    tests["运动速度输入"] = check_form_input(page, ".velocity-input .el-input__inner", "运动速度输入框")

    # 绝对定位按钮
    tests["绝对定位按钮"] = check_element_exists(page, ".move-btn:has-text('绝对定位')", "绝对定位按钮")

    # 回零按钮
    tests["回零按钮"] = check_element_exists(page, ".home-btn:has-text('回零')", "回零按钮")

    # JOG按钮
    tests["JOG-按钮"] = check_element_exists(page, ".jog-btn-left:has-text('JOG-')", "JOG-按钮")
    tests["JOG+按钮"] = check_element_exists(page, ".jog-btn-right:has-text('JOG+')", "JOG+按钮")

    # 限位设置
    tests["限位设置区域"] = check_element_exists(page, ".limit-form", "限位设置区域")
    tests["应用限位按钮"] = check_element_exists(page, ".apply-limit-btn:has-text('应用限位')", "应用限位按钮")

    # 连接面板
    tests["连接面板"] = check_element_exists(page, ".control-card:has(.connection-panel), .connection-panel", "连接面板")

    # 位置显示
    tests["位置显示组件"] = check_element_exists(page, ".position-display, .monitor-card", "位置显示组件")

    # 实时曲线
    tests["实时曲线图表"] = check_element_exists(page, ".chart-container, .chart-card", "实时曲线图表")

    # 截图保存
    page.screenshot(path="test_screenshots/motor_control.png")

    return tests


def test_electromagnet_control_page(page: Page) -> Dict[str, Any]:
    """测试电磁铁控制页面"""
    tests = {}

    # 导航到电磁铁控制页面
    page.goto("http://localhost:5173/experiment/electromagnet")
    wait_for_page_load(page)

    # 页面标题检查
    tests["页面标题"] = check_element_exists(page, ".page-title:has-text('电磁铁控制')", "页面标题")

    # 高功率设备标签
    tests["高功率设备标签"] = check_element_exists(page, ".el-tag:has-text('高功率设备')", "高功率设备标签")

    # 电磁铁控制组件
    tests["电磁铁控制组件"] = check_element_exists(page, ".electromagnet-control", "电磁铁控制组件")

    # 实时状态卡片
    tests["实时状态卡片"] = check_element_exists(page, ".status-card", "实时状态卡片")

    # 电流设置区域
    tests["目标电流输入"] = check_form_input(page, ".current-form .el-input-number input", "目标电流输入框")
    tests["目标磁场输入"] = check_form_input(page, ".current-form:has(.el-input-number) input", "目标磁场输入框")

    # 设置按钮
    tests["设置电流按钮"] = check_element_exists(page, ".set-btn:has-text('设置电流')", "设置电流按钮")
    tests["设置磁场按钮"] = check_element_exists(page, ".set-btn:has-text('设置磁场')", "设置磁场按钮")

    # 电流滑块
    tests["电流滑块"] = check_element_exists(page, ".current-slider .el-slider", "电流滑块")

    # 扫描模式
    tests["扫描模式配置"] = check_element_exists(page, ".scan-form", "扫描模式配置")
    tests["配置扫描按钮"] = check_element_exists(page, ".config-btn:has-text('配置扫描')", "配置扫描按钮")
    tests["验证参数按钮"] = check_element_exists(page, ".config-btn:has-text('验证参数')", "验证参数按钮")

    # 扫描控制按钮
    tests["开始扫描按钮"] = check_element_exists(page, ".start-btn:has-text('开始扫描')", "开始扫描按钮")
    tests["暂停按钮"] = check_element_exists(page, ".pause-btn:has-text('暂停')", "暂停按钮")
    tests["停止扫描按钮"] = check_element_exists(page, ".stop-btn:has-text('停止扫描')", "停止扫描按钮")

    # 校准区域
    tests["校准曲线区域"] = check_element_exists(page, ".calibration-section", "校准曲线区域")
    tests["刷新校准按钮"] = check_element_exists(page, ".action-btn:has-text('刷新校准')", "刷新校准按钮")
    tests["添加校准点按钮"] = check_element_exists(page, ".add-point-btn:has-text('添加校准点')", "添加校准点按钮")

    # 安全控制
    tests["急停按钮"] = check_element_exists(page, ".emergency-btn:has-text('急停')", "急停按钮")
    tests["过流保护复位按钮"] = check_element_exists(page, ".reset-btn:has-text('过流保护复位')", "过流保护复位按钮")

    # 安全警告卡片
    tests["安全警告卡片"] = check_element_exists(page, ".warning-card", "安全警告卡片")

    # 操作提示卡片
    tests["操作提示卡片"] = check_element_exists(page, ".tips-card", "操作提示卡片")

    # 截图保存
    page.screenshot(path="test_screenshots/electromagnet_control.png")

    return tests


def test_temperature_control_page(page: Page) -> Dict[str, Any]:
    """测试温度控制页面"""
    tests = {}

    # 导航到温度控制页面
    page.goto("http://localhost:5173/experiment/temperature")
    wait_for_page_load(page)

    # 页面标题检查
    tests["页面标题"] = check_element_exists(page, ".page-title:has-text('温度控制')", "页面标题")

    # 恒温控制标签
    tests["恒温控制标签"] = check_element_exists(page, ".el-tag:has-text('恒温控制')", "恒温控制标签")

    # 温度控制组件
    tests["温度控制组件"] = check_element_exists(page, ".temperature-control", "温度控制组件")

    # 温度状态卡片
    tests["当前温度卡片"] = check_element_exists(page, ".status-card--current", "当前温度卡片")
    tests["目标温度卡片"] = check_element_exists(page, ".status-card--target", "目标温度卡片")
    tests["升温速率卡片"] = check_element_exists(page, ".status-card--rate", "升温速率卡片")

    # 温度曲线图表
    tests["温度曲线图表"] = check_element_exists(page, ".chart-section .temp-chart", "温度曲线图表")

    # 目标温度设置
    tests["目标温度输入"] = check_form_input(page, ".temp-input .el-input-number input", "目标温度输入框")
    tests["升温速率输入"] = check_form_input(page, ".form-group:has(.el-input-number) input", "升温速率输入框")
    tests["应用设置按钮"] = check_element_exists(page, ".action-btn:has-text('应用设置')", "应用设置按钮")
    tests["停止加热按钮"] = check_element_exists(page, ".action-btn:has-text('停止加热')", "停止加热按钮")

    # PID参数配置
    tests["PID参数区域"] = check_element_exists(page, ".pid-grid", "PID参数区域")
    tests["Kp输入"] = check_form_input(page, ".pid-item:has(.form-label:has-text('比例系数')) .el-input-number input", "Kp输入框")
    tests["Ki输入"] = check_form_input(page, ".pid-item:has(.form-label:has-text('积分系数')) .el-input-number input", "Ki输入框")
    tests["Kd输入"] = check_form_input(page, ".pid-item:has(.form-label:has-text('微分系数')) .el-input-number input", "Kd输入框")
    tests["应用PID参数按钮"] = check_element_exists(page, ".action-btn:has-text('应用 PID 参数')", "应用PID参数按钮")
    tests["验证参数按钮"] = check_element_exists(page, ".action-btn:has-text('验证参数')", "验证参数按钮")
    tests["启动PID按钮"] = check_element_exists(page, ".action-btn:has-text('启动PID')", "启动PID按钮")

    # 程序控温
    tests["程序控温标签页"] = check_element_exists(page, ".program-tabs", "程序控温标签页")
    tests["程序列表"] = check_element_exists(page, ".program-table", "程序列表")

    # 温度保护配置
    tests["温度保护区域"] = check_element_exists(page, ".protection-grid", "温度保护区域")
    tests["应用保护配置按钮"] = check_element_exists(page, ".action-btn:has-text('应用保护配置')", "应用保护配置按钮")

    # 历史记录管理
    tests["历史记录区域"] = check_element_exists(page, ".control-section:has(.section-title:has-text('历史记录'))", "历史记录区域")
    tests["导出CSV按钮"] = check_element_exists(page, ".action-btn:has-text('导出 CSV')", "导出CSV按钮")
    tests["导出JSON按钮"] = check_element_exists(page, ".action-btn:has-text('导出 JSON')", "导出JSON按钮")

    # 连接控制
    tests["连接按钮"] = check_element_exists(page, ".connect-btn", "连接按钮")

    # 紧急停止
    tests["紧急停止按钮"] = check_element_exists(page, ".emergency-stop-btn", "紧急停止按钮")

    # 截图保存
    page.screenshot(path="test_screenshots/temperature_control.png")

    return tests


def test_piezo_control_page(page: Page) -> Dict[str, Any]:
    """测试压电控制页面"""
    tests = {}

    # 导航到压电控制页面
    page.goto("http://localhost:5173/experiment/piezo")
    wait_for_page_load(page)

    # 页面标题检查
    tests["页面标题"] = check_element_exists(page, ".page-title:has-text('压电陶瓷控制')", "页面标题")

    # 精密控制标签
    tests["精密控制标签"] = check_element_exists(page, ".el-tag:has-text('精密控制')", "精密控制标签")

    # 压电控制组件
    tests["压电控制组件"] = check_element_exists(page, ".piezo-control", "压电控制组件")

    # 连接状态
    tests["连接状态显示"] = check_element_exists(page, ".connection-status", "连接状态显示")

    # 电压控制标签页
    tests["电压控制标签页"] = check_element_exists(page, ".el-tabs__item:has-text('电压控制')", "电压控制标签页")

    # 电压滑块
    tests["电压滑块"] = check_element_exists(page, ".voltage-slider .el-slider", "电压滑块")

    # 快捷电压按钮
    tests["快捷电压按钮组"] = check_element_exists(page, ".quick-voltage-buttons", "快捷电压按钮组")

    # 位移显示
    tests["位移显示区域"] = check_element_exists(page, ".displacement-section", "位移显示区域")
    tests["位移值显示"] = check_element_exists(page, ".displacement-value", "位移值显示")

    # 详细信息卡片
    tests["电压显示卡片"] = check_element_exists(page, ".detail-card:has(.detail-label:has-text('电压'))", "电压显示卡片")
    tests["温度显示卡片"] = check_element_exists(page, ".detail-card:has(.detail-label:has-text('温度'))", "温度显示卡片")
    tests["状态显示卡片"] = check_element_exists(page, ".detail-card:has(.detail-label:has-text('状态'))", "状态显示卡片")

    # 电压位移映射标签页
    tests["电压位移映射标签页"] = check_element_exists(page, ".el-tabs__item:has-text('电压位移映射')", "电压位移映射标签页")

    # 校准标签页
    tests["校准标签页"] = check_element_exists(page, ".el-tabs__item:has-text('校准')", "校准标签页")

    # 数据图表标签页
    tests["数据图表标签页"] = check_element_exists(page, ".el-tabs__item:has-text('数据图表')", "数据图表标签页")

    # 图表控制按钮
    tests["开始采集按钮"] = check_element_exists(page, ".chart-btn:has-text('开始采集')", "开始采集按钮")
    tests["导出按钮"] = check_element_exists(page, ".chart-btn:has-text('导出')", "导出按钮")
    tests["清空按钮"] = check_element_exists(page, ".chart-btn:has-text('清空')", "清空按钮")

    # 实时状态卡片
    tests["实时状态卡片"] = check_element_exists(page, ".status-card", "实时状态卡片")
    tests["校准信息卡片"] = check_element_exists(page, ".calibration-card", "校准信息卡片")
    tests["操作提示卡片"] = check_element_exists(page, ".tips-card", "操作提示卡片")

    # 截图保存
    page.screenshot(path="test_screenshots/piezo_control.png")

    return tests


def test_ammeter_control_page(page: Page) -> Dict[str, Any]:
    """测试皮安表控制页面"""
    tests = {}

    # 导航到皮安表控制页面
    page.goto("http://localhost:5173/experiment/ammeter")
    wait_for_page_load(page)

    # 页面标题检查
    tests["页面标题"] = check_element_exists(page, ".page-title:has-text('微电流测量')", "页面标题")

    # 高精度测量标签
    tests["高精度测量标签"] = check_element_exists(page, ".el-tag:has-text('高精度测量')", "高精度测量标签")

    # 皮安表控制组件
    tests["皮安表控制组件"] = check_element_exists(page, ".ammeter-control", "皮安表控制组件")

    # 连接状态
    tests["连接状态显示"] = check_element_exists(page, ".connection-status", "连接状态显示")

    # 采集控制标签页
    tests["采集控制标签页"] = check_element_exists(page, ".el-tabs__item:has-text('采集控制')", "采集控制标签页")

    # 采样率设置
    tests["采样率显示"] = check_element_exists(page, ".rate-display", "采样率显示")
    tests["采样率滑块"] = check_element_exists(page, ".rate-slider .el-slider", "采样率滑块")

    # 快捷采样率按钮
    tests["快捷采样率按钮组"] = check_element_exists(page, ".quick-rate-buttons", "快捷采样率按钮组")

    # 采集控制按钮
    tests["开始采集按钮"] = check_element_exists(page, ".action-btn:has-text('开始采集')", "开始采集按钮")
    tests["清空缓冲区按钮"] = check_element_exists(page, ".action-btn:has-text('清空缓冲区')", "清空缓冲区按钮")
    tests["刷新状态按钮"] = check_element_exists(page, ".action-btn:has-text('刷新状态')", "刷新状态按钮")

    # 采集统计信息
    tests["采集统计区域"] = check_element_exists(page, ".stats-section", "采集统计区域")
    tests["采集状态显示"] = check_element_exists(page, ".stat-card:has(.stat-label:has-text('采集状态'))", "采集状态显示")
    tests["采样率显示卡片"] = check_element_exists(page, ".stat-card:has(.stat-label:has-text('采样率'))", "采样率显示卡片")
    tests["已采集样本显示"] = check_element_exists(page, ".stat-card:has(.stat-label:has-text('已采集样本'))", "已采集样本显示")

    # 通道配置标签页
    tests["通道配置标签页"] = check_element_exists(page, ".el-tabs__item:has-text('通道配置')", "通道配置标签页")

    # 实时数据标签页
    tests["实时数据标签页"] = check_element_exists(page, ".el-tabs__item:has-text('实时数据')", "实时数据标签页")

    # 缓冲区状态
    tests["缓冲区状态区域"] = check_element_exists(page, ".buffer-status-section", "缓冲区状态区域")

    # 通道数据显示
    tests["通道数据显示区域"] = check_element_exists(page, ".channel-data-section", "通道数据显示区域")

    # 信噪比监控
    tests["信噪比监控区域"] = check_element_exists(page, ".snr-section", "信噪比监控区域")

    # 数据图表标签页
    tests["数据图表标签页"] = check_element_exists(page, ".el-tabs__item:has-text('数据图表')", "数据图表标签页")

    # 高级配置标签页
    tests["高级配置标签页"] = check_element_exists(page, ".el-tabs__item:has-text('高级配置')", "高级配置标签页")

    # 模板管理标签页
    tests["模板管理标签页"] = check_element_exists(page, ".el-tabs__item:has-text('模板管理')", "模板管理标签页")

    # 实时状态卡片
    tests["实时状态卡片"] = check_element_exists(page, ".status-card", "实时状态卡片")
    tests["测量精度卡片"] = check_element_exists(page, ".precision-card", "测量精度卡片")
    tests["操作提示卡片"] = check_element_exists(page, ".tips-card", "操作提示卡片")

    # 截图保存
    page.screenshot(path="test_screenshots/ammeter_control.png")

    return tests


def test_api_integration(page: Page) -> Dict[str, Any]:
    """测试API集成（检查网络请求）"""
    tests = {}

    # 监听网络请求
    api_requests = []
    api_errors = []

    def handle_request(request):
        if "/api/" in request.url:
            api_requests.append({
                "url": request.url,
                "method": request.method
            })

    def handle_response(response):
        if "/api/" in response.url:
            if response.status >= 400:
                api_errors.append({
                    "url": response.url,
                    "status": response.status
                })

    page.on("request", handle_request)
    page.on("response", handle_response)

    # 访问各个页面触发API请求
    pages_to_test = [
        ("/experiment/motor", "电机控制"),
        ("/experiment/electromagnet", "电磁铁控制"),
        ("/experiment/temperature", "温度控制"),
        ("/experiment/piezo", "压电控制"),
        ("/experiment/ammeter", "皮安表控制")
    ]

    for path, name in pages_to_test:
        page.goto(f"http://localhost:5173{path}")
        wait_for_page_load(page)

    # 检查API请求
    if len(api_requests) > 0:
        tests["API请求发送"] = {
            "status": "pass",
            "message": f"检测到 {len(api_requests)} 个API请求"
        }
    else:
        tests["API请求发送"] = {
            "status": "warning",
            "message": "未检测到API请求（可能需要后端服务运行）"
        }

    # 检查API错误
    if len(api_errors) > 0:
        tests["API错误检查"] = {
            "status": "warning",
            "message": f"检测到 {len(api_errors)} 个API错误响应"
        }
    else:
        tests["API错误检查"] = {
            "status": "pass",
            "message": "无API错误响应"
        }

    return tests


def test_error_handling(page: Page) -> Dict[str, Any]:
    """测试错误处理"""
    tests = {}

    # 导航到电机控制页面
    page.goto("http://localhost:5173/experiment/motor")
    wait_for_page_load(page)

    # 检查是否有错误提示组件
    error_alert = page.locator(".el-alert--error, .error-alert, .el-message--error").count()
    if error_alert > 0:
        tests["错误提示组件"] = {
            "status": "warning",
            "message": f"页面存在 {error_alert} 个错误提示"
        }
    else:
        tests["错误提示组件"] = {
            "status": "pass",
            "message": "无错误提示"
        }

    # 检查控制台错误
    console_errors = []

    def handle_console(msg):
        if msg.type == "error":
            console_errors.append(msg.text)

    page.on("console", handle_console)

    # 刷新页面触发可能的错误
    page.reload()
    wait_for_page_load(page)

    # 过滤掉一些已知的非关键错误
    critical_errors = [e for e in console_errors if "Failed to load resource" not in e and "net::ERR" not in e]

    if len(critical_errors) > 0:
        tests["控制台错误"] = {
            "status": "warning",
            "message": f"检测到 {len(critical_errors)} 个控制台错误",
            "error": critical_errors[:3]  # 只显示前3个
        }
    else:
        tests["控制台错误"] = {
            "status": "pass",
            "message": "无关键控制台错误"
        }

    return tests


def test_responsive_design(page: Page) -> Dict[str, Any]:
    """测试响应式设计"""
    tests = {}

    # 测试不同屏幕尺寸
    viewports = [
        {"width": 1920, "height": 1080, "name": "桌面"},
        {"width": 1366, "height": 768, "name": "笔记本"},
        {"width": 768, "height": 1024, "name": "平板"},
        {"width": 375, "height": 667, "name": "手机"}
    ]

    for viewport in viewports:
        page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
        page.goto("http://localhost:5173/experiment/motor")
        wait_for_page_load(page)

        # 检查页面是否正常显示
        page_title = page.locator(".page-title").count()
        if page_title > 0:
            tests[f"{viewport['name']}视图"] = {
                "status": "pass",
                "message": f"{viewport['width']}x{viewport['height']} 正常显示"
            }
        else:
            tests[f"{viewport['name']}视图"] = {
                "status": "fail",
                "message": f"{viewport['width']}x{viewport['height']} 显示异常"
            }

        # 保存不同尺寸的截图
        page.screenshot(path=f"test_screenshots/motor_control_{viewport['width']}x{viewport['height']}.png")

    # 恢复默认视口
    page.set_viewport_size({"width": 1920, "height": 1080})

    return tests


def main():
    """主测试函数"""
    print("=" * 80)
    print("开始实验控制模块功能完整性验证测试")
    print("=" * 80)

    # 创建测试结果记录
    test_result = TestResult()

    # 创建截图目录
    import os
    os.makedirs("test_screenshots", exist_ok=True)

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            # 测试各个页面
            print("\n测试电机控制页面...")
            motor_tests = test_motor_control_page(page)
            test_result.add_page_result("电机控制页面 (/experiment/motor)", motor_tests)

            print("测试电磁铁控制页面...")
            electromagnet_tests = test_electromagnet_control_page(page)
            test_result.add_page_result("电磁铁控制页面 (/experiment/electromagnet)", electromagnet_tests)

            print("测试温度控制页面...")
            temperature_tests = test_temperature_control_page(page)
            test_result.add_page_result("温度控制页面 (/experiment/temperature)", temperature_tests)

            print("测试压电控制页面...")
            piezo_tests = test_piezo_control_page(page)
            test_result.add_page_result("压电控制页面 (/experiment/piezo)", piezo_tests)

            print("测试皮安表控制页面...")
            ammeter_tests = test_ammeter_control_page(page)
            test_result.add_page_result("皮安表控制页面 (/experiment/ammeter)", ammeter_tests)

            # 测试API集成
            print("\n测试API集成...")
            api_tests = test_api_integration(page)
            test_result.add_page_result("API集成测试", api_tests)

            # 测试错误处理
            print("测试错误处理...")
            error_tests = test_error_handling(page)
            test_result.add_page_result("错误处理测试", error_tests)

            # 测试响应式设计
            print("测试响应式设计...")
            responsive_tests = test_responsive_design(page)
            test_result.add_page_result("响应式设计测试", responsive_tests)

        except Exception as e:
            print(f"\n测试过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # 关闭浏览器
            context.close()
            browser.close()

    # 生成并输出报告
    report = test_result.generate_report()
    print("\n" + report)

    # 保存报告到文件
    with open("test_report.txt", "w", encoding="utf-8") as f:
        f.write(report)

    # 保存JSON格式的详细结果
    with open("test_report.json", "w", encoding="utf-8") as f:
        json.dump(test_result.results, f, ensure_ascii=False, indent=2)

    print("\n测试报告已保存到 test_report.txt 和 test_report.json")
    print("截图已保存到 test_screenshots/ 目录")


if __name__ == "__main__":
    main()
