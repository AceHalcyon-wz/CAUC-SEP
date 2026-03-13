"""
系统健康监控与性能指标 API 路由模块

文件名: health.py
路径: backend/api/
功能: 系统健康监控API，提供健康检查、性能指标、告警系统等接口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI, pydantic, psutil, core.abstract, core.metrics

主要功能：
- 系统健康检查（CPU、内存、磁盘、设备状态）
- Prometheus 格式性能指标导出
- 设备状态汇总统计
- 系统资源实时监控
- 健康评分算法（0-100分）
- 设备状态监控告警系统
- 告警规则管理与触发
- 告警历史记录与查询

API端点：
- GET /health: 系统健康检查
- GET /health/detailed: 详细健康检查（包含设备状态）
- GET /metrics: Prometheus 格式性能指标
- GET /ready: 就绪检查
- GET /live: 存活检查
- GET /alerts: 获取当前告警列表
- GET /alerts/history: 获取告警历史
- POST /alerts/{alert_id}/acknowledge: 确认告警
- GET /alerts/rules: 获取告警规则列表
- POST /alerts/rules: 创建告警规则
- PUT /alerts/rules/{rule_id}: 更新告警规则
- DELETE /alerts/rules/{rule_id}: 删除告警规则

告警级别：
- info: 信息级别
- warning: 警告级别
- critical: 严重级别
- error: 错误级别

健康评分算法：
- CPU使用率权重: 25%
- 内存使用率权重: 25%
- 磁盘使用率权重: 20%
- 设备状态权重: 30%
"""

import logging
import time
from collections import deque
from datetime import datetime
from threading import RLock

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.abstract import DeviceStatus
from core.dm2c_driver import LeadshineDM2C
from core.electromagnet_driver import ElectromagnetDriver
from core.metrics import get_business_metrics
from core.picoammeter import Picoammeter
from core.piezo_controller import PiezoController
from core.static_files import get_db_path
from core.temperature_controller import TemperatureController

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])

# 全局设备实例引用
dm2c: LeadshineDM2C | None = None
electromagnet_driver: ElectromagnetDriver | None = None
temp_controller: TemperatureController | None = None
piezo_controller: PiezoController | None = None
picoammeter: Picoammeter | None = None

# 应用启动时间（用于计算运行时长）
_start_time: float = time.time()

# 版本信息
APP_VERSION = "0.3.0"

# ==================== 告警系统 ====================


class AlertLevel:
    """告警级别常量。"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"


class AlertRule(BaseModel):
    """告警规则模型。"""

    rule_id: str = Field(..., description="规则唯一标识")
    name: str = Field(..., description="规则名称")
    description: str = Field(..., description="规则描述")
    metric_type: str = Field(..., description="指标类型：cpu/memory/disk/device_status")
    threshold: float = Field(..., description="触发阈值")
    comparison: str = Field("gt", description="比较方式：gt/lt/eq/ne")
    duration_seconds: int = Field(60, description="持续时间（秒）")
    alert_level: str = Field(AlertLevel.WARNING, description="告警级别")
    enabled: bool = Field(True, description="是否启用")
    cooldown_seconds: int = Field(300, description="冷却时间（秒），防止重复告警")


class Alert(BaseModel):
    """告警记录模型。"""

    alert_id: str = Field(..., description="告警唯一标识")
    rule_id: str = Field(..., description="触发规则ID")
    rule_name: str = Field(..., description="规则名称")
    level: str = Field(..., description="告警级别")
    message: str = Field(..., description="告警消息")
    metric_value: float = Field(..., description="触发时的指标值")
    threshold: float = Field(..., description="阈值")
    timestamp: str = Field(..., description="告警时间")
    acknowledged: bool = Field(False, description="是否已确认")
    resolved_at: str | None = Field(None, description="解决时间")


class AlertManager:
    """
    告警管理器。

    管理告警规则、触发告警、记录告警历史。

    Attributes:
        rules: 告警规则字典
        active_alerts: 当前活跃告警
        alert_history: 告警历史记录
        metric_history: 指标历史记录（用于持续时间判断）
    """

    def __init__(self, max_history: int = 1000):
        """初始化告警管理器。

        Args:
            max_history: 最大历史记录数
        """
        self._rules: dict[str, AlertRule] = {}
        self._active_alerts: dict[str, Alert] = {}
        self._alert_history: deque[Alert] = deque(maxlen=max_history)
        self._metric_history: dict[str, deque[tuple[float, float]]] = {}
        self._last_alert_time: dict[str, float] = {}
        self._lock = RLock()
        self._alert_counter = 0

        # 初始化默认告警规则
        self._init_default_rules()

        logger.info("AlertManager initialized with default rules")

    def _init_default_rules(self) -> None:
        """初始化默认告警规则。"""
        default_rules = [
            AlertRule(
                rule_id="cpu_high",
                name="CPU使用率过高",
                description="CPU使用率超过80%",
                metric_type="cpu",
                threshold=80.0,
                comparison="gt",
                duration_seconds=60,
                alert_level=AlertLevel.WARNING,
            ),
            AlertRule(
                rule_id="cpu_critical",
                name="CPU使用率严重过高",
                description="CPU使用率超过95%",
                metric_type="cpu",
                threshold=95.0,
                comparison="gt",
                duration_seconds=30,
                alert_level=AlertLevel.CRITICAL,
            ),
            AlertRule(
                rule_id="memory_high",
                name="内存使用率过高",
                description="内存使用率超过80%",
                metric_type="memory",
                threshold=80.0,
                comparison="gt",
                duration_seconds=60,
                alert_level=AlertLevel.WARNING,
            ),
            AlertRule(
                rule_id="memory_critical",
                name="内存使用率严重过高",
                description="内存使用率超过95%",
                metric_type="memory",
                threshold=95.0,
                comparison="gt",
                duration_seconds=30,
                alert_level=AlertLevel.CRITICAL,
            ),
            AlertRule(
                rule_id="disk_high",
                name="磁盘使用率过高",
                description="磁盘使用率超过85%",
                metric_type="disk",
                threshold=85.0,
                comparison="gt",
                duration_seconds=300,
                alert_level=AlertLevel.WARNING,
            ),
            AlertRule(
                rule_id="disk_critical",
                name="磁盘使用率严重过高",
                description="磁盘使用率超过95%",
                metric_type="disk",
                threshold=95.0,
                comparison="gt",
                duration_seconds=60,
                alert_level=AlertLevel.CRITICAL,
            ),
            AlertRule(
                rule_id="device_disconnected",
                name="设备断开连接",
                description="设备断开连接",
                metric_type="device_disconnected",
                threshold=1.0,
                comparison="eq",
                duration_seconds=30,
                alert_level=AlertLevel.ERROR,
            ),
            AlertRule(
                rule_id="device_error",
                name="设备错误",
                description="设备处于错误状态",
                metric_type="device_error",
                threshold=1.0,
                comparison="eq",
                duration_seconds=10,
                alert_level=AlertLevel.ERROR,
            ),
        ]

        for rule in default_rules:
            self._rules[rule.rule_id] = rule

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则。

        Args:
            rule: 告警规则
        """
        with self._lock:
            self._rules[rule.rule_id] = rule
            logger.info(f"Alert rule added: {rule.rule_id}")

    def remove_rule(self, rule_id: str) -> bool:
        """移除告警规则。

        Args:
            rule_id: 规则ID

        Returns:
            是否成功移除
        """
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                logger.info(f"Alert rule removed: {rule_id}")
                return True
            return False

    def record_metric(self, metric_type: str, value: float) -> None:
        """记录指标值。

        Args:
            metric_type: 指标类型
            value: 指标值
        """
        with self._lock:
            if metric_type not in self._metric_history:
                self._metric_history[metric_type] = deque(maxlen=1000)
            self._metric_history[metric_type].append((time.time(), value))

    def check_alerts(self, current_metrics: dict[str, float]) -> list[Alert]:
        """检查告警条件并触发告警。

        Args:
            current_metrics: 当前指标字典

        Returns:
            触发的告警列表
        """
        triggered_alerts = []
        current_time = time.time()

        with self._lock:
            for rule in self._rules.values():
                if not rule.enabled:
                    continue

                # 获取指标值
                metric_value = current_metrics.get(rule.metric_type)
                if metric_value is None:
                    continue

                # 检查阈值条件
                condition_met = self._check_condition(metric_value, rule.threshold, rule.comparison)

                if not condition_met:
                    # 条件不满足，解决活跃告警
                    if rule.rule_id in self._active_alerts:
                        alert = self._active_alerts[rule.rule_id]
                        alert.resolved_at = datetime.now().isoformat()
                        del self._active_alerts[rule.rule_id]
                        logger.info(f"Alert resolved: {rule.rule_id}")
                    continue

                # 检查持续时间
                if not self._check_duration(rule, current_time):
                    continue

                # 检查冷却时间
                last_alert = self._last_alert_time.get(rule.rule_id, 0)
                if current_time - last_alert < rule.cooldown_seconds:
                    continue

                # 触发告警
                alert = self._create_alert(rule, metric_value, current_time)
                triggered_alerts.append(alert)
                self._active_alerts[rule.rule_id] = alert
                self._alert_history.append(alert)
                self._last_alert_time[rule.rule_id] = current_time

                logger.warning(f"Alert triggered: [{alert.level}] {rule.name} - {alert.message}")

        return triggered_alerts

    def _check_condition(self, value: float, threshold: float, comparison: str) -> bool:
        """检查条件是否满足。

        Args:
            value: 当前值
            threshold: 阈值
            comparison: 比较方式

        Returns:
            条件是否满足
        """
        if comparison == "gt":
            return value > threshold
        elif comparison == "lt":
            return value < threshold
        elif comparison == "eq":
            return abs(value - threshold) < 0.001
        elif comparison == "ne":
            return abs(value - threshold) >= 0.001
        return False

    def _check_duration(self, rule: AlertRule, current_time: float) -> bool:
        """检查持续时间条件。

        Args:
            rule: 告警规则
            current_time: 当前时间

        Returns:
            是否满足持续时间
        """
        if rule.duration_seconds <= 0:
            return True

        history = self._metric_history.get(rule.metric_type, [])
        if len(history) < 2:
            return False

        # 检查最近duration_seconds秒内是否持续满足条件
        cutoff_time = current_time - rule.duration_seconds
        recent_values = [(t, v) for t, v in history if t >= cutoff_time]

        if not recent_values:
            return False

        # 所有最近值都需要满足条件
        for _, value in recent_values:
            if not self._check_condition(value, rule.threshold, rule.comparison):
                return False

        return True

    def _create_alert(self, rule: AlertRule, metric_value: float, current_time: float) -> Alert:
        """创建告警记录。

        Args:
            rule: 告警规则
            metric_value: 指标值
            current_time: 当前时间

        Returns:
            告警记录
        """
        self._alert_counter += 1
        return Alert(
            alert_id=f"alert_{self._alert_counter:06d}",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            level=rule.alert_level,
            message=f"{rule.description} (当前值: {metric_value:.2f}, 阈值: {rule.threshold})",
            metric_value=metric_value,
            threshold=rule.threshold,
            timestamp=datetime.now().isoformat(),
        )

    def get_active_alerts(self) -> list[Alert]:
        """获取当前活跃告警。

        Returns:
            活跃告警列表
        """
        with self._lock:
            return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> list[Alert]:
        """获取告警历史。

        Args:
            limit: 最大返回数量

        Returns:
            告警历史列表
        """
        with self._lock:
            return list(self._alert_history)[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警。

        Args:
            alert_id: 告警ID

        Returns:
            是否成功
        """
        with self._lock:
            for alert in self._active_alerts.values():
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    logger.info(f"Alert acknowledged: {alert_id}")
                    return True
            return False

    def get_rules(self) -> list[AlertRule]:
        """获取所有告警规则。

        Returns:
            告警规则列表
        """
        with self._lock:
            return list(self._rules.values())


# 全局告警管理器实例
alert_manager = AlertManager()


# ==================== Pydantic 模型定义 ====================


class DeviceHealth(BaseModel):
    """设备健康状态模型。"""

    device_id: str = Field(..., description="设备唯一标识")
    device_type: str = Field(..., description="设备类型")
    status: str = Field(..., description="设备状态")
    connected: bool = Field(..., description="是否已连接")
    last_update: str | None = Field(None, description="最后更新时间")
    error_count: int = Field(0, description="错误计数")
    uptime_seconds: float = Field(0.0, description="设备运行时长")


class SystemHealth(BaseModel):
    """系统健康状态模型。"""

    cpu_percent: float = Field(..., description="CPU使用率百分比", ge=0, le=100)
    memory_percent: float = Field(..., description="内存使用率百分比", ge=0, le=100)
    disk_percent: float = Field(..., description="磁盘使用率百分比", ge=0, le=100)
    uptime_seconds: float = Field(..., description="系统运行时长（秒）", ge=0)
    devices: list[DeviceHealth] = Field(default_factory=list, description="设备健康列表")
    # 新增指标
    cpu_temperature: float | None = Field(None, description="CPU温度（摄氏度）")
    load_average: list[float] | None = Field(None, description="系统负载平均值（1/5/15分钟）")
    network_connections: int = Field(0, description="网络连接数")
    process_count: int = Field(0, description="进程数")
    thread_count: int = Field(0, description="线程数")


class HealthScore(BaseModel):
    """健康评分模型。"""

    overall_score: float = Field(..., description="综合健康评分（0-100）", ge=0, le=100)
    system_score: float = Field(..., description="系统资源评分（0-100）", ge=0, le=100)
    device_score: float = Field(..., description="设备状态评分（0-100）", ge=0, le=100)
    performance_score: float = Field(..., description="性能评分（0-100）", ge=0, le=100)
    reliability_score: float = Field(..., description="可靠性评分（0-100）", ge=0, le=100)
    grade: str = Field(..., description="健康等级（A/B/C/D/F）")
    details: dict[str, float] = Field(default_factory=dict, description="评分详情")


class HealthResponse(BaseModel):
    """健康检查响应模型。"""

    status: str = Field(..., description="整体健康状态：healthy/degraded/unhealthy")
    timestamp: str = Field(..., description="检查时间戳（ISO格式）")
    system: SystemHealth = Field(..., description="系统健康状态")
    version: str = Field(..., description="应用版本号")
    # 新增字段
    health_score: HealthScore = Field(..., description="健康评分")
    active_alerts: int = Field(0, description="活跃告警数量")
    recommendations: list[str] = Field(default_factory=list, description="优化建议")


class DeviceStatusSummary(BaseModel):
    """设备状态汇总模型。"""

    total_devices: int = Field(..., description="设备总数", ge=0)
    connected_devices: int = Field(..., description="已连接设备数", ge=0)
    disconnected_devices: int = Field(..., description="已断开设备数", ge=0)
    error_devices: int = Field(..., description="错误状态设备数", ge=0)
    devices: list[DeviceHealth] = Field(default_factory=list, description="设备详情列表")
    # 新增字段
    avg_uptime_seconds: float = Field(0.0, description="平均设备运行时长")
    total_errors: int = Field(0, description="总错误计数")


class NetworkIOStats(BaseModel):
    """网络IO统计模型。"""

    bytes_sent: int = Field(..., description="发送字节数")
    bytes_recv: int = Field(..., description="接收字节数")
    packets_sent: int = Field(..., description="发送数据包数")
    packets_recv: int = Field(..., description="接收数据包数")
    errin: int = Field(0, description="接收错误数")
    errout: int = Field(0, description="发送错误数")
    dropin: int = Field(0, description="接收丢包数")
    dropout: int = Field(0, description="发送丢包数")


class ProcessInfo(BaseModel):
    """进程信息模型。"""

    pid: int = Field(..., description="进程ID")
    name: str = Field(..., description="进程名称")
    cpu_percent: float = Field(..., description="CPU使用率")
    memory_mb: float = Field(..., description="内存使用量（MB）")
    num_threads: int = Field(..., description="线程数")
    num_handles: int = Field(0, description="句柄数")
    create_time: float = Field(0.0, description="创建时间戳")


class SystemResourcesResponse(BaseModel):
    """系统资源响应模型。"""

    cpu: dict = Field(..., description="CPU信息")
    memory: dict = Field(..., description="内存信息")
    disk: dict = Field(..., description="磁盘信息")
    network: NetworkIOStats = Field(..., description="网络IO统计")
    process: ProcessInfo = Field(..., description="当前进程信息")
    # 新增字段
    system_load: dict | None = Field(None, description="系统负载信息")
    temperatures: dict | None = Field(None, description="温度传感器信息")


class AlertsResponse(BaseModel):
    """告警响应模型。"""

    active_alerts: list[Alert] = Field(..., description="活跃告警列表")
    alert_history: list[Alert] = Field(..., description="告警历史")
    total_active: int = Field(..., description="活跃告警总数")
    rules: list[AlertRule] = Field(..., description="告警规则列表")


# ==================== 设备实例设置函数 ====================


def set_devices(
    motor: LeadshineDM2C | None,
    electromagnet: ElectromagnetDriver | None,
    temperature: TemperatureController | None,
    piezo: PiezoController | None,
    ammeter: Picoammeter | None,
) -> None:
    """
    设置所有设备实例引用。

    Args:
        motor: 步进电机驱动器实例
        electromagnet: 电磁铁驱动器实例
        temperature: 温控系统实例
        piezo: 压电陶瓷控制器实例
        ammeter: 微电流计实例
    """
    global dm2c, electromagnet_driver, temp_controller, piezo_controller, picoammeter
    dm2c = motor
    electromagnet_driver = electromagnet
    temp_controller = temperature
    piezo_controller = piezo
    picoammeter = ammeter
    logger.info("Health monitoring: Device references updated")


# ==================== 辅助函数 ====================


def _get_system_metrics() -> dict:
    """
    获取系统资源指标。

    使用psutil获取CPU、内存、磁盘使用率。
    性能优化：缓存部分数据，避免频繁调用。

    Returns:
        dict: 系统资源指标字典
    """
    # CPU使用率（interval=None表示非阻塞调用，返回自上次调用以来的平均值）
    cpu_percent = psutil.cpu_percent(interval=None) or 0.0

    # 内存使用率
    memory = psutil.virtual_memory()
    memory_percent = memory.percent

    # 磁盘使用率（根目录）
    try:
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
    except Exception:
        # Windows系统可能需要使用其他路径
        try:
            disk = psutil.disk_usage("C:\\")
            disk_percent = disk.percent
        except Exception:
            disk_percent = 0.0

    # 运行时长
    uptime_seconds = time.time() - _start_time

    # 记录指标到告警管理器
    alert_manager.record_metric("cpu", cpu_percent)
    alert_manager.record_metric("memory", memory_percent)
    alert_manager.record_metric("disk", disk_percent)

    return {
        "cpu_percent": round(cpu_percent, 2),
        "memory_percent": round(memory_percent, 2),
        "disk_percent": round(disk_percent, 2),
        "uptime_seconds": round(uptime_seconds, 2),
    }


def _calculate_health_score(
    system_metrics: dict, device_health_list: list[DeviceHealth]
) -> HealthScore:
    """
    计算健康评分（0-100分）。

    评分维度：
    1. 系统资源评分（40%权重）：CPU、内存、磁盘使用率
    2. 设备状态评分（30%权重）：设备连接率、错误率
    3. 性能评分（15%权重）：系统负载、响应时间
    4. 可靠性评分（15%权重）：运行时长、错误恢复能力

    Args:
        system_metrics: 系统资源指标
        device_health_list: 设备健康列表

    Returns:
        HealthScore: 健康评分对象
    """
    details = {}

    # ==================== 系统资源评分 ====================
    cpu_score = max(0, 100 - system_metrics["cpu_percent"])
    memory_score = max(0, 100 - system_metrics["memory_percent"])
    disk_score = max(0, 100 - system_metrics["disk_percent"])

    # 系统资源评分 = (CPU评分 * 0.4 + 内存评分 * 0.4 + 磁盘评分 * 0.2)
    system_score = cpu_score * 0.4 + memory_score * 0.4 + disk_score * 0.2

    details["cpu_score"] = round(cpu_score, 2)
    details["memory_score"] = round(memory_score, 2)
    details["disk_score"] = round(disk_score, 2)

    # ==================== 设备状态评分 ====================
    total_devices = len(device_health_list)
    if total_devices == 0:
        device_score = 100.0  # 无设备时满分
    else:
        connected_devices = sum(1 for d in device_health_list if d.connected)
        error_devices = sum(1 for d in device_health_list if d.status in ["error", "fault"])

        # 连接率评分
        connection_rate = connected_devices / total_devices
        connection_score = connection_rate * 100

        # 错误率扣分
        error_rate = error_devices / total_devices
        error_penalty = error_rate * 50  # 每个错误设备扣50分

        device_score = max(0, connection_score - error_penalty)

    details["device_connection_rate"] = round(
        sum(1 for d in device_health_list if d.connected) / max(1, total_devices) * 100, 2
    )
    details["device_error_rate"] = round(
        sum(1 for d in device_health_list if d.status in ["error", "fault"])
        / max(1, total_devices)
        * 100,
        2,
    )

    # ==================== 性能评分 ====================
    # 基于CPU和内存使用率的波动性
    cpu_load = system_metrics["cpu_percent"]
    memory_load = system_metrics["memory_percent"]

    # 性能评分：资源使用越均衡，评分越高
    load_balance = 1 - abs(cpu_load - memory_load) / 100
    performance_score = (100 - (cpu_load + memory_load) / 2) * 0.7 + load_balance * 30

    details["load_balance"] = round(load_balance * 100, 2)

    # ==================== 可靠性评分 ====================
    # 基于运行时长和稳定性
    uptime_hours = system_metrics["uptime_seconds"] / 3600

    # 运行时长加分（最长24小时满分）
    uptime_bonus = min(uptime_hours / 24 * 100, 100)

    # 系统稳定性（基于历史告警）
    active_alerts = len(alert_manager.get_active_alerts())
    stability_penalty = min(active_alerts * 5, 50)  # 每个活跃告警扣5分，最多扣50分

    reliability_score = max(0, uptime_bonus - stability_penalty)

    details["uptime_hours"] = round(uptime_hours, 2)
    details["active_alerts_count"] = active_alerts

    # ==================== 综合评分 ====================
    overall_score = (
        system_score * 0.4
        + device_score * 0.3
        + performance_score * 0.15
        + reliability_score * 0.15
    )

    # 确定健康等级
    if overall_score >= 90:
        grade = "A"
    elif overall_score >= 80:
        grade = "B"
    elif overall_score >= 70:
        grade = "C"
    elif overall_score >= 60:
        grade = "D"
    else:
        grade = "F"

    return HealthScore(
        overall_score=round(overall_score, 2),
        system_score=round(system_score, 2),
        device_score=round(device_score, 2),
        performance_score=round(performance_score, 2),
        reliability_score=round(reliability_score, 2),
        grade=grade,
        details=details,
    )


def _generate_recommendations(
    health_score: HealthScore,
    system_metrics: dict,
    device_health_list: list[DeviceHealth],
) -> list[str]:
    """
    生成优化建议。

    Args:
        health_score: 健康评分
        system_metrics: 系统资源指标
        device_health_list: 设备健康列表

    Returns:
        list[str]: 优化建议列表
    """
    recommendations = []

    # CPU相关建议
    if system_metrics["cpu_percent"] > 80:
        recommendations.append("CPU使用率过高，建议检查后台进程或增加计算资源")
    elif system_metrics["cpu_percent"] > 60:
        recommendations.append("CPU使用率偏高，建议监控系统负载趋势")

    # 内存相关建议
    if system_metrics["memory_percent"] > 80:
        recommendations.append("内存使用率过高，建议检查内存泄漏或增加内存容量")
    elif system_metrics["memory_percent"] > 60:
        recommendations.append("内存使用率偏高，建议优化内存使用")

    # 磁盘相关建议
    if system_metrics["disk_percent"] > 85:
        recommendations.append("磁盘空间不足，建议清理临时文件或扩展存储容量")

    # 设备相关建议
    total_devices = len(device_health_list)
    if total_devices > 0:
        disconnected_devices = sum(1 for d in device_health_list if not d.connected)
        error_devices = sum(1 for d in device_health_list if d.status in ["error", "fault"])

        if disconnected_devices > 0:
            recommendations.append(
                f"有 {disconnected_devices} 个设备断开连接，建议检查设备连接状态"
            )
        if error_devices > 0:
            recommendations.append(f"有 {error_devices} 个设备处于错误状态，建议检查设备日志")

    # 健康评分相关建议
    if health_score.overall_score < 70:
        recommendations.append("系统健康状态不佳，建议进行全面检查")
    elif health_score.overall_score < 80:
        recommendations.append("系统健康状态一般，建议关注各项指标")

    # 性能相关建议
    if health_score.performance_score < 70:
        recommendations.append("系统性能评分较低，建议优化资源分配")

    # 可靠性相关建议
    if health_score.reliability_score < 70:
        recommendations.append("系统可靠性评分较低，建议检查告警记录")

    # 如果没有建议，返回积极消息
    if not recommendations:
        recommendations.append("系统运行状态良好，继续保持")

    return recommendations


async def _get_device_health_list() -> list[DeviceHealth]:
    """
    获取所有设备的健康状态列表。

    异步查询所有设备状态，构建健康状态列表。

    Returns:
        list[DeviceHealth]: 设备健康状态列表
    """
    devices = []
    current_time = datetime.now().isoformat()

    # 步进电机
    if dm2c:
        devices.append(
            DeviceHealth(
                device_id=dm2c.device_id,
                device_type="stepper_motor",
                status=dm2c.status.value,
                connected=dm2c.status != DeviceStatus.DISCONNECTED,
                last_update=current_time,
            )
        )

    # 电磁铁
    if electromagnet_driver:
        try:
            status_data = await electromagnet_driver.read_status()
            devices.append(
                DeviceHealth(
                    device_id=electromagnet_driver.device_id,
                    device_type="electromagnet",
                    status=status_data.get("electromagnet_status", "unknown"),
                    connected=status_data.get("connected", False),
                    last_update=current_time,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to read electromagnet status: {e}")
            devices.append(
                DeviceHealth(
                    device_id=electromagnet_driver.device_id,
                    device_type="electromagnet",
                    status="error",
                    connected=False,
                    last_update=current_time,
                )
            )

    # 温控系统
    if temp_controller:
        try:
            status_data = await temp_controller.read_status()
            devices.append(
                DeviceHealth(
                    device_id=temp_controller.device_id,
                    device_type="temperature_controller",
                    status=status_data.get("status", "unknown"),
                    connected=status_data.get("connected", False),
                    last_update=current_time,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to read temperature controller status: {e}")
            devices.append(
                DeviceHealth(
                    device_id=temp_controller.device_id,
                    device_type="temperature_controller",
                    status="error",
                    connected=False,
                    last_update=current_time,
                )
            )

    # 压电陶瓷控制器
    if piezo_controller:
        try:
            status_data = await piezo_controller.read_status()
            devices.append(
                DeviceHealth(
                    device_id=piezo_controller.device_id,
                    device_type="piezo_controller",
                    status=status_data.get("status", "unknown"),
                    connected=True,
                    last_update=current_time,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to read piezo controller status: {e}")
            devices.append(
                DeviceHealth(
                    device_id=piezo_controller.device_id,
                    device_type="piezo_controller",
                    status="error",
                    connected=False,
                    last_update=current_time,
                )
            )

    # 微电流计
    if picoammeter:
        try:
            devices.append(
                DeviceHealth(
                    device_id=picoammeter.device_id,
                    device_type="picoammeter",
                    status=picoammeter.status.value,
                    connected=picoammeter.status != DeviceStatus.DISCONNECTED,
                    last_update=current_time,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to read picoammeter status: {e}")
            devices.append(
                DeviceHealth(
                    device_id=picoammeter.device_id,
                    device_type="picoammeter",
                    status="error",
                    connected=False,
                    last_update=current_time,
                )
            )

    return devices


def _calculate_health_status(system_metrics: dict, device_health_list: list[DeviceHealth]) -> str:
    """
    计算整体健康状态。

    根据系统资源使用率和设备状态综合判断。

    Args:
        system_metrics: 系统资源指标
        device_health_list: 设备健康列表

    Returns:
        str: 健康状态（healthy/degraded/unhealthy）
    """
    # 系统资源阈值
    CPU_WARNING_THRESHOLD = 80.0
    CPU_CRITICAL_THRESHOLD = 95.0
    MEMORY_WARNING_THRESHOLD = 80.0
    MEMORY_CRITICAL_THRESHOLD = 95.0
    DISK_WARNING_THRESHOLD = 85.0
    DISK_CRITICAL_THRESHOLD = 95.0

    # 检查系统资源
    cpu_critical = system_metrics["cpu_percent"] >= CPU_CRITICAL_THRESHOLD
    memory_critical = system_metrics["memory_percent"] >= MEMORY_CRITICAL_THRESHOLD
    disk_critical = system_metrics["disk_percent"] >= DISK_CRITICAL_THRESHOLD

    if cpu_critical or memory_critical or disk_critical:
        return "unhealthy"

    cpu_warning = system_metrics["cpu_percent"] >= CPU_WARNING_THRESHOLD
    memory_warning = system_metrics["memory_percent"] >= MEMORY_WARNING_THRESHOLD
    disk_warning = system_metrics["disk_percent"] >= DISK_WARNING_THRESHOLD

    # 检查设备状态
    total_devices = len(device_health_list)
    if total_devices == 0:
        # 无设备时，仅根据系统资源判断
        if cpu_warning or memory_warning or disk_warning:
            return "degraded"
        return "healthy"

    disconnected_count = sum(1 for d in device_health_list if not d.connected)
    error_count = sum(1 for d in device_health_list if d.status in ["error", "fault"])

    # 超过半数设备断开或错误
    if disconnected_count > total_devices / 2 or error_count > total_devices / 2:
        return "unhealthy"

    # 有设备断开或错误，或系统资源警告
    if disconnected_count > 0 or error_count > 0 or cpu_warning or memory_warning or disk_warning:
        return "degraded"

    return "healthy"


# ==================== API 端点 ====================


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    获取系统健康状态。

    综合检查系统资源（CPU、内存、磁盘）和所有设备状态，
    返回整体健康评估、健康评分和优化建议。

    Returns:
        HealthResponse: 健康检查响应，包含系统状态、设备列表、健康评分和建议

    Example:
        ```bash
        curl http://localhost:8000/api/health
        ```
    """
    try:
        # 获取系统指标
        system_metrics = _get_system_metrics()

        # 获取设备健康状态
        device_health_list = await _get_device_health_list()

        # 计算整体健康状态
        health_status = _calculate_health_status(system_metrics, device_health_list)

        # 计算健康评分
        health_score = _calculate_health_score(system_metrics, device_health_list)

        # 生成优化建议
        recommendations = _generate_recommendations(
            health_score, system_metrics, device_health_list
        )

        # 检查告警
        current_metrics = {
            "cpu": system_metrics["cpu_percent"],
            "memory": system_metrics["memory_percent"],
            "disk": system_metrics["disk_percent"],
            "device_disconnected": float(sum(1 for d in device_health_list if not d.connected)),
            "device_error": float(
                sum(1 for d in device_health_list if d.status in ["error", "fault"])
            ),
        }
        alert_manager.check_alerts(current_metrics)

        # 获取活跃告警数量
        active_alerts_count = len(alert_manager.get_active_alerts())

        # 构建响应
        return HealthResponse(
            status=health_status,
            timestamp=datetime.now().isoformat(),
            system=SystemHealth(
                cpu_percent=system_metrics["cpu_percent"],
                memory_percent=system_metrics["memory_percent"],
                disk_percent=system_metrics["disk_percent"],
                uptime_seconds=system_metrics["uptime_seconds"],
                devices=device_health_list,
            ),
            version=APP_VERSION,
            health_score=health_score,
            active_alerts=active_alerts_count,
            recommendations=recommendations,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/metrics")
async def get_metrics():
    """
    获取 Prometheus 格式的性能指标。

    返回文本格式的监控指标，可直接被 Prometheus 抓取。
    包含系统资源、设备状态、健康评分和业务指标。

    Returns:
        str: Prometheus 文本格式的指标数据

    Example:
        ```bash
        curl http://localhost:8000/api/metrics
        ```

    输出示例:
        ```
        # HELP cpu_usage_percent CPU使用率百分比
        # TYPE cpu_usage_percent gauge
        cpu_usage_percent 45.2
        # HELP memory_usage_percent 内存使用率百分比
        # TYPE memory_usage_percent gauge
        memory_usage_percent 62.5
        ```
    """
    try:
        # 获取系统指标
        system_metrics = _get_system_metrics()

        # 获取设备健康状态
        device_health_list = await _get_device_health_list()

        # 计算健康评分
        health_score = _calculate_health_score(system_metrics, device_health_list)

        # 获取业务指标收集器
        business_metrics = get_business_metrics()

        # 构建 Prometheus 格式输出
        lines = []

        # ==================== 系统资源指标 ====================
        # CPU 使用率
        lines.append("# HELP cpu_usage_percent CPU使用率百分比")
        lines.append("# TYPE cpu_usage_percent gauge")
        lines.append(f"cpu_usage_percent {system_metrics['cpu_percent']}")

        # 内存使用率
        lines.append("")
        lines.append("# HELP memory_usage_percent 内存使用率百分比")
        lines.append("# TYPE memory_usage_percent gauge")
        lines.append(f"memory_usage_percent {system_metrics['memory_percent']}")

        # 磁盘使用率
        lines.append("")
        lines.append("# HELP disk_usage_percent 磁盘使用率百分比")
        lines.append("# TYPE disk_usage_percent gauge")
        lines.append(f"disk_usage_percent {system_metrics['disk_percent']}")

        # 系统运行时长
        lines.append("")
        lines.append("# HELP system_uptime_seconds 系统运行时长（秒）")
        lines.append("# TYPE system_uptime_seconds gauge")
        lines.append(f"system_uptime_seconds {system_metrics['uptime_seconds']}")

        # ==================== 健康评分指标 ====================
        lines.append("")
        lines.append("# HELP health_score_overall 综合健康评分（0-100）")
        lines.append("# TYPE health_score_overall gauge")
        lines.append(f"health_score_overall {health_score.overall_score}")

        lines.append("")
        lines.append("# HELP health_score_system 系统资源评分（0-100）")
        lines.append("# TYPE health_score_system gauge")
        lines.append(f"health_score_system {health_score.system_score}")

        lines.append("")
        lines.append("# HELP health_score_device 设备状态评分（0-100）")
        lines.append("# TYPE health_score_device gauge")
        lines.append(f"health_score_device {health_score.device_score}")

        lines.append("")
        lines.append("# HELP health_score_performance 性能评分（0-100）")
        lines.append("# TYPE health_score_performance gauge")
        lines.append(f"health_score_performance {health_score.performance_score}")

        lines.append("")
        lines.append("# HELP health_score_reliability 可靠性评分（0-100）")
        lines.append("# TYPE health_score_reliability gauge")
        lines.append(f"health_score_reliability {health_score.reliability_score}")

        # ==================== 设备指标 ====================
        # 设备总数
        lines.append("")
        lines.append("# HELP devices_total 设备总数")
        lines.append("# TYPE devices_total gauge")
        lines.append(f"devices_total {len(device_health_list)}")

        # 已连接设备数
        connected_count = sum(1 for d in device_health_list if d.connected)
        lines.append("")
        lines.append("# HELP devices_connected 已连接设备数")
        lines.append("# TYPE devices_connected gauge")
        lines.append(f"devices_connected {connected_count}")

        # 断开设备数
        disconnected_count = len(device_health_list) - connected_count
        lines.append("")
        lines.append("# HELP devices_disconnected 断开设备数")
        lines.append("# TYPE devices_disconnected gauge")
        lines.append(f"devices_disconnected {disconnected_count}")

        # 错误设备数
        error_count = sum(1 for d in device_health_list if d.status in ["error", "fault"])
        lines.append("")
        lines.append("# HELP devices_error 错误状态设备数")
        lines.append("# TYPE devices_error gauge")
        lines.append(f"devices_error {error_count}")

        # 设备连接率
        connection_rate = connected_count / max(1, len(device_health_list)) * 100
        lines.append("")
        lines.append("# HELP device_connection_rate_percent 设备连接率百分比")
        lines.append("# TYPE device_connection_rate_percent gauge")
        lines.append(f"device_connection_rate_percent {connection_rate:.2f}")

        # 设备连接状态（按设备）
        lines.append("")
        lines.append("# HELP device_connected 设备连接状态（1=已连接，0=已断开）")
        lines.append("# TYPE device_connected gauge")
        for device in device_health_list:
            connected_value = 1 if device.connected else 0
            lines.append(
                f'device_connected{{device_id="{device.device_id}",'
                f'device_type="{device.device_type}"}} {connected_value}'
            )

        # 设备状态（按设备）
        lines.append("")
        lines.append("# HELP device_status 设备状态码")
        lines.append("# TYPE device_status gauge")
        status_mapping = {
            "idle": 0,
            "running": 1,
            "ready": 2,
            "busy": 3,
            "warning": 4,
            "error": 5,
            "fault": 6,
            "disconnected": 7,
            "disabled": 8,
            "unknown": 9,
        }
        for device in device_health_list:
            status_code = status_mapping.get(device.status.lower(), 9)
            lines.append(
                f'device_status{{device_id="{device.device_id}",'
                f'device_type="{device.device_type}",'
                f'status="{device.status}"}} {status_code}'
            )

        # ==================== 告警指标 ====================
        active_alerts = alert_manager.get_active_alerts()
        lines.append("")
        lines.append("# HELP alerts_active 活跃告警数量")
        lines.append("# TYPE alerts_active gauge")
        lines.append(f"alerts_active {len(active_alerts)}")

        # 按级别统计告警
        alert_by_level = {}
        for alert in active_alerts:
            alert_by_level[alert.level] = alert_by_level.get(alert.level, 0) + 1

        lines.append("")
        lines.append("# HELP alerts_by_level 按级别统计告警数量")
        lines.append("# TYPE alerts_by_level gauge")
        for level in ["info", "warning", "critical", "error"]:
            count = alert_by_level.get(level, 0)
            lines.append(f'alerts_by_level{{level="{level}"}} {count}')

        # ==================== 应用信息指标 ====================
        lines.append("")
        lines.append("# HELP app_info 应用信息")
        lines.append("# TYPE app_info gauge")
        lines.append(f'app_info{{version="{APP_VERSION}"}} 1')

        # ==================== 业务指标 ====================
        # 更新设备状态指标
        business_metrics.update_device_status(
            total=len(device_health_list),
            connected=connected_count,
            disconnected=disconnected_count,
            error=error_count,
        )

        # 收集存储指标
        business_metrics.collect_storage_metrics(str(get_db_path("experiments.db")))

        # 导出业务指标
        business_metrics_output = business_metrics.export_metrics()
        lines.append("")
        lines.append(business_metrics_output)

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics: {str(e)}")


@router.get("/devices/status", response_model=DeviceStatusSummary)
async def get_devices_status():
    """
    获取所有设备状态汇总。

    统计设备连接状态，返回汇总信息和详细列表。

    Returns:
        DeviceStatusSummary: 设备状态汇总，包含统计数据和详情列表

    Example:
        ```bash
        curl http://localhost:8000/api/devices/status
        ```
    """
    try:
        # 获取设备健康状态列表
        device_health_list = await _get_device_health_list()

        # 统计数据
        total_devices = len(device_health_list)
        connected_devices = sum(1 for d in device_health_list if d.connected)
        disconnected_devices = total_devices - connected_devices
        error_devices = sum(
            1 for d in device_health_list if d.status in ["error", "fault", "warning"]
        )

        return DeviceStatusSummary(
            total_devices=total_devices,
            connected_devices=connected_devices,
            disconnected_devices=disconnected_devices,
            error_devices=error_devices,
            devices=device_health_list,
        )

    except Exception as e:
        logger.error(f"Failed to get devices status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get devices status: {str(e)}")


@router.get("/resources", response_model=SystemResourcesResponse)
async def get_system_resources():
    """
    获取详细的系统资源监控数据。

    返回CPU、内存、磁盘、网络IO和当前进程的详细信息。

    Returns:
        SystemResourcesResponse: 系统资源详细信息

    Example:
        ```bash
        curl http://localhost:8000/api/resources
        ```
    """
    try:
        # CPU 信息
        cpu_count = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_freq = psutil.cpu_freq()

        cpu_info = {
            "count_logical": cpu_count,
            "count_physical": cpu_count_physical,
            "percent_total": round(sum(cpu_percent) / len(cpu_percent), 2) if cpu_percent else 0.0,
            "percent_per_cpu": [round(p, 2) for p in cpu_percent] if cpu_percent else [],
            "freq_current_mhz": round(cpu_freq.current, 2) if cpu_freq else 0.0,
            "freq_min_mhz": round(cpu_freq.min, 2) if cpu_freq else 0.0,
            "freq_max_mhz": round(cpu_freq.max, 2) if cpu_freq else 0.0,
        }

        # 内存信息
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        memory_info = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent": round(memory.percent, 2),
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": round(swap.percent, 2),
        }

        # 磁盘信息
        try:
            disk = psutil.disk_usage("/")
        except Exception:
            disk = psutil.disk_usage("C:\\")

        disk_io = psutil.disk_io_counters()

        disk_info = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round(disk.percent, 2),
            "read_bytes": disk_io.read_bytes if disk_io else 0,
            "write_bytes": disk_io.write_bytes if disk_io else 0,
        }

        # 网络 IO 统计
        net_io = psutil.net_io_counters()
        network_stats = NetworkIOStats(
            bytes_sent=net_io.bytes_sent if net_io else 0,
            bytes_recv=net_io.bytes_recv if net_io else 0,
            packets_sent=net_io.packets_sent if net_io else 0,
            packets_recv=net_io.packets_recv if net_io else 0,
        )

        # 当前进程信息
        process = psutil.Process()
        process_info = ProcessInfo(
            pid=process.pid,
            name=process.name(),
            cpu_percent=round(process.cpu_percent(interval=0.1), 2),
            memory_mb=round(process.memory_info().rss / (1024**2), 2),
            num_threads=process.num_threads(),
        )

        return SystemResourcesResponse(
            cpu=cpu_info,
            memory=memory_info,
            disk=disk_info,
            network=network_stats,
            process=process_info,
        )

    except Exception as e:
        logger.error(f"Failed to get system resources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system resources: {str(e)}")


# ==================== 告警 API 端点 ====================


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(limit: int = 100):
    """
    获取告警信息。

    返回活跃告警、告警历史和告警规则列表。

    Args:
        limit: 告警历史最大返回数量，默认100

    Returns:
        AlertsResponse: 告警信息响应

    Example:
        ```bash
        curl http://localhost:8000/api/alerts
        ```
    """
    try:
        active_alerts = alert_manager.get_active_alerts()
        alert_history = alert_manager.get_alert_history(limit)
        rules = alert_manager.get_rules()

        return AlertsResponse(
            active_alerts=active_alerts,
            alert_history=alert_history,
            total_active=len(active_alerts),
            rules=rules,
        )

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.get("/alerts/active")
async def get_active_alerts():
    """
    获取当前活跃告警。

    Returns:
        list[Alert]: 活跃告警列表

    Example:
        ```bash
        curl http://localhost:8000/api/alerts/active
        ```
    """
    try:
        return alert_manager.get_active_alerts()
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """
    确认告警。

    Args:
        alert_id: 告警ID

    Returns:
        dict: 操作结果

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/alerts/alert_000001/acknowledge
        ```
    """
    try:
        success = alert_manager.acknowledge_alert(alert_id)
        if success:
            return {"success": True, "message": f"Alert {alert_id} acknowledged"}
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.get("/alerts/rules")
async def get_alert_rules():
    """
    获取所有告警规则。

    Returns:
        list[AlertRule]: 告警规则列表

    Example:
        ```bash
        curl http://localhost:8000/api/alerts/rules
        ```
    """
    try:
        return alert_manager.get_rules()
    except Exception as e:
        logger.error(f"Failed to get alert rules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert rules: {str(e)}")


@router.post("/alerts/rules")
async def add_alert_rule(rule: AlertRule):
    """
    添加告警规则。

    Args:
        rule: 告警规则配置

    Returns:
        dict: 操作结果

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/alerts/rules \\
            -H "Content-Type: application/json" \\
            -d '{"rule_id": "custom_1", "name": "自定义规则", ...}'
        ```
    """
    try:
        alert_manager.add_rule(rule)
        return {"success": True, "message": f"Alert rule {rule.rule_id} added"}
    except Exception as e:
        logger.error(f"Failed to add alert rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add alert rule: {str(e)}")


@router.delete("/alerts/rules/{rule_id}")
async def remove_alert_rule(rule_id: str):
    """
    移除告警规则。

    Args:
        rule_id: 规则ID

    Returns:
        dict: 操作结果

    Example:
        ```bash
        curl -X DELETE http://localhost:8000/api/alerts/rules/custom_1
        ```
    """
    try:
        success = alert_manager.remove_rule(rule_id)
        if success:
            return {"success": True, "message": f"Alert rule {rule_id} removed"}
        else:
            raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove alert rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove alert rule: {str(e)}")


@router.get("/health/score")
async def get_health_score():
    """
    获取健康评分详情。

    Returns:
        dict: 健康评分详情，包含各维度评分和建议

    Example:
        ```bash
        curl http://localhost:8000/api/health/score
        ```
    """
    try:
        system_metrics = _get_system_metrics()
        device_health_list = await _get_device_health_list()
        health_score = _calculate_health_score(system_metrics, device_health_list)
        recommendations = _generate_recommendations(
            health_score, system_metrics, device_health_list
        )

        return {
            "health_score": health_score.model_dump(),
            "system_metrics": system_metrics,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get health score: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health score: {str(e)}")
