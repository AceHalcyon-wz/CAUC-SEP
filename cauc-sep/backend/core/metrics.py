"""
业务指标收集器模块

功能：
- 实验相关指标（实验数量、运行时间等）
- 设备操作指标（操作次数、成功率等）
- 数据存储指标（存储量、增长速率等）
- 遵循Prometheus命名规范
- 支持指标标签

命名规范：
- 使用snake_case命名
- 添加单位后缀（_total, _seconds, _bytes等）
- 添加HELP和TYPE注释

作者：DevOps Engineer Agent
创建日期：2026-03-08
依赖：threading, time, collections
"""

import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from threading import Lock, RLock
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ==================== 指标类型 ====================


class MetricType:
    """指标类型常量。"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


# ==================== 指标基类 ====================


class Metric:
    """
    指标基类。

    所有指标类型的基类，提供名称、帮助文本和标签支持。

    Attributes:
        name: 指标名称
        help_text: 帮助文本
        metric_type: 指标类型
        labels: 标签字典
    """

    def __init__(
        self,
        name: str,
        help_text: str,
        metric_type: str,
        labels: Optional[dict[str, str]] = None,
    ):
        """
        初始化指标。

        Args:
            name: 指标名称（snake_case格式）
            help_text: 帮助文本
            metric_type: 指标类型（counter/gauge/histogram/summary）
            labels: 标签字典
        """
        self._name = name
        self._help_text = help_text
        self._metric_type = metric_type
        self._labels = labels or {}
        self._lock = Lock()

    @property
    def name(self) -> str:
        """获取指标名称。"""
        return self._name

    @property
    def help_text(self) -> str:
        """获取帮助文本。"""
        return self._help_text

    @property
    def metric_type(self) -> str:
        """获取指标类型。"""
        return self._metric_type

    def _format_labels(self, extra_labels: Optional[dict[str, str]] = None) -> str:
        """
        格式化标签为Prometheus格式。

        Args:
            extra_labels: 额外标签

        Returns:
            str: 格式化的标签字符串
        """
        all_labels = {**self._labels, **(extra_labels or {})}
        if not all_labels:
            return ""

        label_str = ",".join(
            f'{k}="{v}"' for k, v in sorted(all_labels.items())
        )
        return f"{{{label_str}}}"

    def export(self) -> str:
        """
        导出指标为Prometheus格式。

        Returns:
            str: Prometheus格式的指标文本
        """
        raise NotImplementedError("Subclasses must implement export()")


class Counter(Metric):
    """
    计数器指标。

    只能递增的累积指标，用于记录事件总数。
    命名规范：以_total结尾。

    Example:
        experiments_total: 实验总数
        device_operations_total: 设备操作总数
    """

    def __init__(
        self,
        name: str,
        help_text: str,
        labels: Optional[dict[str, str]] = None,
    ):
        """
        初始化计数器。

        Args:
            name: 指标名称（建议以_total结尾）
            help_text: 帮助文本
            labels: 标签字典
        """
        super().__init__(name, help_text, MetricType.COUNTER, labels)
        self._value = 0.0
        self._created = time.time()

    def inc(self, amount: float = 1.0) -> None:
        """
        增加计数器值。

        Args:
            amount: 增加量（必须为正数）

        Raises:
            ValueError: amount为负数时抛出
        """
        if amount < 0:
            raise ValueError("Counter can only be incremented by non-negative values")

        with self._lock:
            self._value += amount

    def get(self) -> float:
        """获取当前值。"""
        with self._lock:
            return self._value

    def export(self) -> str:
        """导出为Prometheus格式。"""
        lines = []
        lines.append(f"# HELP {self._name} {self._help_text}")
        lines.append(f"# TYPE {self._name} counter")
        lines.append(f"{self._name}{self._format_labels()} {self._value}")
        return "\n".join(lines)


class Gauge(Metric):
    """
    仪表盘指标。

    可增可减的瞬时值指标，用于记录当前状态。
    命名规范：通常不带后缀，或使用单位后缀。

    Example:
        experiments_running: 正在运行的实验数
        device_temperature_celsius: 设备温度
        storage_used_bytes: 已用存储空间
    """

    def __init__(
        self,
        name: str,
        help_text: str,
        labels: Optional[dict[str, str]] = None,
    ):
        """
        初始化仪表盘。

        Args:
            name: 指标名称
            help_text: 帮助文本
            labels: 标签字典
        """
        super().__init__(name, help_text, MetricType.GAUGE, labels)
        self._value = 0.0

    def set(self, value: float) -> None:
        """
        设置仪表盘值。

        Args:
            value: 新值
        """
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        """增加值。"""
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        """减少值。"""
        with self._lock:
            self._value -= amount

    def get(self) -> float:
        """获取当前值。"""
        with self._lock:
            return self._value

    def export(self) -> str:
        """导出为Prometheus格式。"""
        lines = []
        lines.append(f"# HELP {self._name} {self._help_text}")
        lines.append(f"# TYPE {self._name} gauge")
        lines.append(f"{self._name}{self._format_labels()} {self._value}")
        return "\n".join(lines)


class Histogram(Metric):
    """
    直方图指标。

    用于观察值的分布情况，自动计算分位数。
    命名规范：通常不带后缀，或使用单位后缀。

    Example:
        experiment_duration_seconds: 实验持续时间
        device_operation_duration_seconds: 设备操作耗时
    """

    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0,
        2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0,
    )

    def __init__(
        self,
        name: str,
        help_text: str,
        labels: Optional[dict[str, str]] = None,
        buckets: Optional[tuple[float, ...]] = None,
    ):
        """
        初始化直方图。

        Args:
            name: 指标名称
            help_text: 帮助文本
            labels: 标签字典
            buckets: 桶边界（必须按升序排列）
        """
        super().__init__(name, help_text, MetricType.HISTOGRAM, labels)
        self._buckets = buckets or self.DEFAULT_BUCKETS
        self._bucket_counts = [0] * len(self._buckets)
        self._sum = 0.0
        self._count = 0

    def observe(self, value: float) -> None:
        """
        记录观察值。

        Args:
            value: 观察值
        """
        with self._lock:
            self._sum += value
            self._count += 1

            for i, bucket in enumerate(self._buckets):
                if value <= bucket:
                    self._bucket_counts[i] += 1

    def get(self) -> dict[str, Any]:
        """获取统计信息。"""
        with self._lock:
            return {
                "sum": self._sum,
                "count": self._count,
                "buckets": list(zip(self._buckets, self._bucket_counts)),
            }

    def export(self) -> str:
        """导出为Prometheus格式。"""
        lines = []
        lines.append(f"# HELP {self._name} {self._help_text}")
        lines.append(f"# TYPE {self._name} histogram")

        with self._lock:
            cumulative = 0
            for i, bucket in enumerate(self._buckets):
                cumulative += self._bucket_counts[i]
                lines.append(
                    f'{self._name}_bucket{self._format_labels({"le": str(bucket)})} {cumulative}'
                )
            lines.append(f'{self._name}_bucket{self._format_labels({"le": "+Inf"})} {self._count}')
            lines.append(f"{self._name}_sum{self._format_labels()} {self._sum}")
            lines.append(f"{self._name}_count{self._format_labels()} {self._count}")

        return "\n".join(lines)


# ==================== 指标注册表 ====================


class MetricsRegistry:
    """
    指标注册表。

    管理所有指标实例，提供统一的导出接口。

    Attributes:
        metrics: 指标字典
        prefix: 指标名称前缀
    """

    def __init__(self, prefix: str = "cauc_sep"):
        """
        初始化注册表。

        Args:
            prefix: 指标名称前缀（应用标识）
        """
        self._prefix = prefix
        self._metrics: dict[str, Metric] = {}
        self._lock = RLock()

    def _get_full_name(self, name: str) -> str:
        """获取完整指标名称（带前缀）。"""
        return f"{self._prefix}_{name}"

    def register(self, metric: Metric) -> None:
        """
        注册指标。

        Args:
            metric: 指标实例
        """
        with self._lock:
            self._metrics[metric.name] = metric
            logger.debug(f"Metric registered: {metric.name}")

    def unregister(self, name: str) -> bool:
        """
        注销指标。

        Args:
            name: 指标名称

        Returns:
            bool: 是否成功
        """
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                return True
            return False

    def get_metric(self, name: str) -> Optional[Metric]:
        """获取指标实例。"""
        with self._lock:
            return self._metrics.get(name)

    def export_all(self) -> str:
        """
        导出所有指标为Prometheus格式。

        Returns:
            str: Prometheus格式的指标文本
        """
        lines = []
        with self._lock:
            for metric in self._metrics.values():
                lines.append(metric.export())
                lines.append("")

        return "\n".join(lines)


# ==================== 业务指标收集器 ====================


class BusinessMetricsCollector:
    """
    业务指标收集器。

    收集和管理实验、设备、存储等业务指标。
    遵循Prometheus命名规范，支持标签。

    Attributes:
        registry: 指标注册表
        storage: 数据存储实例引用
    """

    def __init__(self, registry: Optional[MetricsRegistry] = None):
        """
        初始化收集器。

        Args:
            registry: 指标注册表（可选，默认创建新实例）
        """
        self._registry = registry or MetricsRegistry()
        self._storage = None
        self._lock = RLock()

        # 指标缓存（用于带标签的指标）
        self._labeled_metrics: dict[str, dict[str, Metric]] = defaultdict(dict)

        # 初始化基础指标
        self._init_base_metrics()

        logger.info("BusinessMetricsCollector initialized")

    def _init_base_metrics(self) -> None:
        """初始化基础指标。"""
        prefix = self._registry._prefix

        # ==================== 实验指标 ====================
        self._experiments_total = Counter(
            f"{prefix}_experiments_total",
            "实验总数",
        )
        self._registry.register(self._experiments_total)

        self._experiments_running = Gauge(
            f"{prefix}_experiments_running",
            "正在运行的实验数",
        )
        self._registry.register(self._experiments_running)

        self._experiments_completed_total = Counter(
            f"{prefix}_experiments_completed_total",
            "已完成的实验总数",
        )
        self._registry.register(self._experiments_completed_total)

        self._experiments_failed_total = Counter(
            f"{prefix}_experiments_failed_total",
            "失败的实验总数",
        )
        self._registry.register(self._experiments_failed_total)

        self._experiment_duration_seconds = Histogram(
            f"{prefix}_experiment_duration_seconds",
            "实验持续时间（秒）",
            buckets=(60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400),
        )
        self._registry.register(self._experiment_duration_seconds)

        # ==================== 设备操作指标 ====================
        self._device_operations_total = Counter(
            f"{prefix}_device_operations_total",
            "设备操作总数",
        )
        self._registry.register(self._device_operations_total)

        self._device_operations_successful_total = Counter(
            f"{prefix}_device_operations_successful_total",
            "成功的设备操作总数",
        )
        self._registry.register(self._device_operations_successful_total)

        self._device_operations_failed_total = Counter(
            f"{prefix}_device_operations_failed_total",
            "失败的设备操作总数",
        )
        self._registry.register(self._device_operations_failed_total)

        self._device_operation_duration_seconds = Histogram(
            f"{prefix}_device_operation_duration_seconds",
            "设备操作耗时（秒）",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )
        self._registry.register(self._device_operation_duration_seconds)

        # ==================== 设备状态指标 ====================
        self._devices_total = Gauge(
            f"{prefix}_devices_total",
            "设备总数",
        )
        self._registry.register(self._devices_total)

        self._devices_connected = Gauge(
            f"{prefix}_devices_connected",
            "已连接设备数",
        )
        self._registry.register(self._devices_connected)

        self._devices_disconnected = Gauge(
            f"{prefix}_devices_disconnected",
            "断开连接的设备数",
        )
        self._registry.register(self._devices_disconnected)

        self._devices_error = Gauge(
            f"{prefix}_devices_error",
            "错误状态的设备数",
        )
        self._registry.register(self._devices_error)

        # ==================== 数据存储指标 ====================
        self._storage_used_bytes = Gauge(
            f"{prefix}_storage_used_bytes",
            "已使用的存储空间（字节）",
        )
        self._registry.register(self._storage_used_bytes)

        self._storage_total_bytes = Gauge(
            f"{prefix}_storage_total_bytes",
            "总存储空间（字节）",
        )
        self._registry.register(self._storage_total_bytes)

        self._storage_usage_percent = Gauge(
            f"{prefix}_storage_usage_percent",
            "存储使用率百分比",
        )
        self._registry.register(self._storage_usage_percent)

        self._data_records_total = Counter(
            f"{prefix}_data_records_total",
            "数据记录总数",
        )
        self._registry.register(self._data_records_total)

        self._data_records_bytes = Counter(
            f"{prefix}_data_records_bytes",
            "数据记录总大小（字节）",
        )
        self._registry.register(self._data_records_bytes)

        # ==================== API请求指标 ====================
        self._api_requests_total = Counter(
            f"{prefix}_api_requests_total",
            "API请求总数",
        )
        self._registry.register(self._api_requests_total)

        self._api_request_duration_seconds = Histogram(
            f"{prefix}_api_request_duration_seconds",
            "API请求耗时（秒）",
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        self._registry.register(self._api_request_duration_seconds)

        self._api_requests_in_progress = Gauge(
            f"{prefix}_api_requests_in_progress",
            "正在处理的API请求数",
        )
        self._registry.register(self._api_requests_in_progress)

        # ==================== WebSocket指标 ====================
        self._websocket_connections = Gauge(
            f"{prefix}_websocket_connections",
            "WebSocket连接数",
        )
        self._registry.register(self._websocket_connections)

        self._websocket_messages_total = Counter(
            f"{prefix}_websocket_messages_total",
            "WebSocket消息总数",
        )
        self._registry.register(self._websocket_messages_total)

        self._websocket_errors_total = Counter(
            f"{prefix}_websocket_errors_total",
            "WebSocket错误总数",
        )
        self._registry.register(self._websocket_errors_total)

    def set_storage(self, storage) -> None:
        """
        设置数据存储实例引用。

        Args:
            storage: DataStorage实例
        """
        self._storage = storage

    # ==================== 实验指标方法 ====================

    def record_experiment_start(self, experiment_type: str = "default") -> None:
        """
        记录实验开始。

        Args:
            experiment_type: 实验类型
        """
        self._experiments_total.inc()
        self._experiments_running.inc()

        # 按实验类型记录
        metric_name = f"experiments_started_by_type_total"
        if metric_name not in self._labeled_metrics.get(experiment_type, {}):
            metric = Counter(
                f"{self._registry._prefix}_{metric_name}",
                "按类型统计的实验启动数",
                labels={"experiment_type": experiment_type},
            )
            self._registry.register(metric)
            self._labeled_metrics[experiment_type][metric_name] = metric

        self._labeled_metrics[experiment_type][metric_name].inc()

    def record_experiment_complete(
        self,
        duration_seconds: float,
        success: bool = True,
        experiment_type: str = "default",
    ) -> None:
        """
        记录实验完成。

        Args:
            duration_seconds: 实验持续时间（秒）
            success: 是否成功
            experiment_type: 实验类型
        """
        self._experiments_running.dec()

        if success:
            self._experiments_completed_total.inc()
        else:
            self._experiments_failed_total.inc()

        self._experiment_duration_seconds.observe(duration_seconds)

    # ==================== 设备操作指标方法 ====================

    def record_device_operation(
        self,
        device_type: str,
        operation_type: str,
        duration_seconds: float,
        success: bool,
        error_type: Optional[str] = None,
    ) -> None:
        """
        记录设备操作。

        Args:
            device_type: 设备类型
            operation_type: 操作类型
            duration_seconds: 操作耗时（秒）
            success: 是否成功
            error_type: 错误类型（失败时）
        """
        self._device_operations_total.inc()
        self._device_operation_duration_seconds.observe(duration_seconds)

        if success:
            self._device_operations_successful_total.inc()
        else:
            self._device_operations_failed_total.inc()

        # 按设备类型和操作类型记录
        label_key = f"{device_type}_{operation_type}"
        metric_name = "device_operations_by_type_total"

        if metric_name not in self._labeled_metrics.get(label_key, {}):
            metric = Counter(
                f"{self._registry._prefix}_{metric_name}",
                "按设备和操作类型统计的操作数",
                labels={
                    "device_type": device_type,
                    "operation_type": operation_type,
                },
            )
            self._registry.register(metric)
            self._labeled_metrics[label_key][metric_name] = metric

        self._labeled_metrics[label_key][metric_name].inc()

        # 记录错误类型
        if not success and error_type:
            error_label_key = f"error_{error_type}"
            error_metric_name = "device_operation_errors_total"

            if error_metric_name not in self._labeled_metrics.get(error_label_key, {}):
                metric = Counter(
                    f"{self._registry._prefix}_{error_metric_name}",
                    "按错误类型统计的设备操作错误数",
                    labels={
                        "device_type": device_type,
                        "error_type": error_type,
                    },
                )
                self._registry.register(metric)
                self._labeled_metrics[error_label_key][error_metric_name] = metric

            self._labeled_metrics[error_label_key][error_metric_name].inc()

    def update_device_status(
        self,
        total: int,
        connected: int,
        disconnected: int,
        error: int,
    ) -> None:
        """
        更新设备状态指标。

        Args:
            total: 设备总数
            connected: 已连接数
            disconnected: 断开数
            error: 错误数
        """
        self._devices_total.set(total)
        self._devices_connected.set(connected)
        self._devices_disconnected.set(disconnected)
        self._devices_error.set(error)

    # ==================== 数据存储指标方法 ====================

    def update_storage_metrics(
        self,
        used_bytes: int,
        total_bytes: int,
    ) -> None:
        """
        更新存储指标。

        Args:
            used_bytes: 已使用字节数
            total_bytes: 总字节数
        """
        self._storage_used_bytes.set(used_bytes)
        self._storage_total_bytes.set(total_bytes)

        if total_bytes > 0:
            usage_percent = (used_bytes / total_bytes) * 100
            self._storage_usage_percent.set(usage_percent)

    def record_data_record(self, size_bytes: int = 0) -> None:
        """
        记录数据记录添加。

        Args:
            size_bytes: 数据大小（字节）
        """
        self._data_records_total.inc()
        if size_bytes > 0:
            self._data_records_bytes.inc(size_bytes)

    def collect_storage_metrics(self, db_path: str) -> dict[str, Any]:
        """
        收集存储相关指标。

        Args:
            db_path: 数据库文件路径

        Returns:
            dict: 存储指标字典
        """
        try:
            if os.path.exists(db_path):
                stat = os.stat(db_path)
                used_bytes = stat.st_size

                # 获取磁盘信息
                disk_stat = os.statvfs(os.path.dirname(db_path)) if hasattr(os, 'statvfs') else None
                if disk_stat:
                    total_bytes = disk_stat.f_blocks * disk_stat.f_frsize
                else:
                    # Windows系统
                    import shutil
                    total, used, free = shutil.disk_usage(os.path.dirname(db_path) or ".")
                    total_bytes = total

                self.update_storage_metrics(used_bytes, total_bytes)

                return {
                    "db_size_bytes": used_bytes,
                    "disk_total_bytes": total_bytes,
                    "usage_percent": (used_bytes / total_bytes * 100) if total_bytes > 0 else 0,
                }
        except Exception as e:
            logger.error(f"Failed to collect storage metrics: {e}")

        return {}

    # ==================== API请求指标方法 ====================

    def record_api_request(
        self,
        method: str,
        endpoint: str,
        duration_seconds: float,
        status_code: int,
    ) -> None:
        """
        记录API请求。

        Args:
            method: HTTP方法
            endpoint: 端点路径
            duration_seconds: 请求耗时（秒）
            status_code: HTTP状态码
        """
        self._api_requests_total.inc()
        self._api_request_duration_seconds.observe(duration_seconds)

        # 按方法和状态码记录
        label_key = f"{method}_{status_code}"
        metric_name = "api_requests_by_status_total"

        if metric_name not in self._labeled_metrics.get(label_key, {}):
            metric = Counter(
                f"{self._registry._prefix}_{metric_name}",
                "按方法和状态码统计的API请求数",
                labels={
                    "method": method,
                    "status_code": str(status_code),
                },
            )
            self._registry.register(metric)
            self._labeled_metrics[label_key][metric_name] = metric

        self._labeled_metrics[label_key][metric_name].inc()

    def increment_api_requests_in_progress(self) -> None:
        """增加正在处理的API请求数。"""
        self._api_requests_in_progress.inc()

    def decrement_api_requests_in_progress(self) -> None:
        """减少正在处理的API请求数。"""
        self._api_requests_in_progress.dec()

    # ==================== WebSocket指标方法 ====================

    def update_websocket_connections(self, count: int) -> None:
        """
        更新WebSocket连接数。

        Args:
            count: 当前连接数
        """
        self._websocket_connections.set(count)

    def record_websocket_message(self, message_type: str = "default") -> None:
        """
        记录WebSocket消息。

        Args:
            message_type: 消息类型
        """
        self._websocket_messages_total.inc()

        # 按消息类型记录
        label_key = f"ws_{message_type}"
        metric_name = "websocket_messages_by_type_total"

        if metric_name not in self._labeled_metrics.get(label_key, {}):
            metric = Counter(
                f"{self._registry._prefix}_{metric_name}",
                "按类型统计的WebSocket消息数",
                labels={"message_type": message_type},
            )
            self._registry.register(metric)
            self._labeled_metrics[label_key][metric_name] = metric

        self._labeled_metrics[label_key][metric_name].inc()

    def record_websocket_error(self, error_type: str = "unknown") -> None:
        """
        记录WebSocket错误。

        Args:
            error_type: 错误类型
        """
        self._websocket_errors_total.inc()

        # 按错误类型记录
        label_key = f"ws_error_{error_type}"
        metric_name = "websocket_errors_by_type_total"

        if metric_name not in self._labeled_metrics.get(label_key, {}):
            metric = Counter(
                f"{self._registry._prefix}_{metric_name}",
                "按类型统计的WebSocket错误数",
                labels={"error_type": error_type},
            )
            self._registry.register(metric)
            self._labeled_metrics[label_key][metric_name] = metric

        self._labeled_metrics[label_key][metric_name].inc()

    # ==================== 导出方法 ====================

    def export_metrics(self) -> str:
        """
        导出所有业务指标为Prometheus格式。

        Returns:
            str: Prometheus格式的指标文本
        """
        return self._registry.export_all()

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        获取指标摘要。

        Returns:
            dict: 指标摘要字典
        """
        return {
            "experiments": {
                "total": self._experiments_total.get(),
                "running": self._experiments_running.get(),
                "completed": self._experiments_completed_total.get(),
                "failed": self._experiments_failed_total.get(),
            },
            "devices": {
                "total": self._devices_total.get(),
                "connected": self._devices_connected.get(),
                "disconnected": self._devices_disconnected.get(),
                "error": self._devices_error.get(),
            },
            "operations": {
                "total": self._device_operations_total.get(),
                "successful": self._device_operations_successful_total.get(),
                "failed": self._device_operations_failed_total.get(),
            },
            "api": {
                "requests_total": self._api_requests_total.get(),
                "requests_in_progress": self._api_requests_in_progress.get(),
            },
            "websocket": {
                "connections": self._websocket_connections.get(),
                "messages_total": self._websocket_messages_total.get(),
                "errors_total": self._websocket_errors_total.get(),
            },
        }


# ==================== 全局实例 ====================

# 默认指标注册表
default_registry = MetricsRegistry(prefix="cauc_sep")

# 默认业务指标收集器
business_metrics = BusinessMetricsCollector(default_registry)


def get_business_metrics() -> BusinessMetricsCollector:
    """
    获取全局业务指标收集器实例。

    Returns:
        BusinessMetricsCollector: 业务指标收集器实例
    """
    return business_metrics
