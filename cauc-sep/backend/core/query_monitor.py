"""
查询性能监控集成模块

文件名: query_monitor.py
路径: core/
功能: 查询性能监控、慢查询日志、性能统计集成
作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: sqlalchemy, logging, threading
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock, RLock
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ============================================================================
# 性能指标数据结构
# ============================================================================


@dataclass
class QueryMetric:
    """查询性能指标。

    Attributes:
        sql: SQL语句
        duration_ms: 执行时间（毫秒）
        rows_affected: 影响行数
        timestamp: 执行时间戳
        success: 是否成功
        error_message: 错误信息
        params: 查询参数（脱敏）
        caller: 调用者信息
    """

    sql: str
    duration_ms: float
    rows_affected: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str | None = None
    params: dict[str, Any] | None = None
    caller: str | None = None


@dataclass
class QueryStatistics:
    """查询统计信息。

    Attributes:
        total_queries: 总查询数
        total_errors: 总错误数
        total_duration_ms: 总执行时间
        slow_query_count: 慢查询数量
        avg_duration_ms: 平均执行时间
        max_duration_ms: 最大执行时间
        min_duration_ms: 最小执行时间
    """

    total_queries: int = 0
    total_errors: int = 0
    total_duration_ms: float = 0.0
    slow_query_count: int = 0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")


# ============================================================================
# 查询性能监控器
# ============================================================================


class QueryPerformanceMonitor:
    """
    查询性能监控器。

    实时监控数据库查询性能，记录慢查询，
    分析查询模式，提供性能统计。

    Attributes:
        slow_query_threshold_ms: 慢查询阈值（毫秒）
        max_history_size: 最大历史记录数
        enable_logging: 是否启用日志记录
    """

    def __init__(
        self,
        slow_query_threshold_ms: float = 100.0,
        max_history_size: int = 10000,
        enable_logging: bool = True,
        log_slow_queries: bool = True,
    ) -> None:
        """初始化查询性能监控器。

        Args:
            slow_query_threshold_ms: 慢查询阈值，默认100毫秒
            max_history_size: 最大历史记录数，默认10000
            enable_logging: 是否启用日志记录
            log_slow_queries: 是否记录慢查询日志
        """
        self._slow_query_threshold = slow_query_threshold_ms
        self._max_history_size = max_history_size
        self._enable_logging = enable_logging
        self._log_slow_queries = log_slow_queries

        # 查询历史
        self._query_history: list[QueryMetric] = []
        self._slow_queries: list[QueryMetric] = []

        # 查询统计（按查询模式分组）
        self._query_stats: dict[str, QueryStatistics] = defaultdict(QueryStatistics)

        # 线程安全
        self._lock = RLock()

        # 回调函数
        self._on_slow_query_callbacks: list[Callable[[QueryMetric], None]] = []
        self._on_error_callbacks: list[Callable[[QueryMetric], None]] = []

        logger.info(
            f"QueryPerformanceMonitor initialized "
            f"(threshold: {slow_query_threshold_ms}ms, "
            f"max_history: {max_history_size})"
        )

    def record_query(
        self,
        sql: str,
        duration_ms: float,
        rows_affected: int = 0,
        success: bool = True,
        error_message: str | None = None,
        params: dict[str, Any] | None = None,
        caller: str | None = None,
    ) -> None:
        """记录查询性能指标。

        Args:
            sql: SQL语句
            duration_ms: 执行时间（毫秒）
            rows_affected: 影响行数
            success: 是否成功
            error_message: 错误信息
            params: 查询参数
            caller: 调用者信息
        """
        # 脱敏参数
        sanitized_params = self._sanitize_params(params) if params else None

        metric = QueryMetric(
            sql=sql,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            success=success,
            error_message=error_message,
            params=sanitized_params,
            caller=caller,
        )

        with self._lock:
            # 记录到历史
            self._query_history.append(metric)
            if len(self._query_history) > self._max_history_size:
                self._query_history.pop(0)

            # 更新统计
            self._update_statistics(metric)

            # 记录慢查询
            if duration_ms > self._slow_query_threshold:
                self._slow_queries.append(metric)
                if len(self._slow_queries) > self._max_history_size:
                    self._slow_queries.pop(0)

                # 触发慢查询回调
                self._trigger_slow_query_callbacks(metric)

                # 记录慢查询日志
                if self._log_slow_queries:
                    logger.warning(
                        f"Slow query detected: {duration_ms:.2f}ms - "
                        f"{sql[:100]}{'...' if len(sql) > 100 else ''}"
                    )

            # 记录错误回调
            if not success:
                self._trigger_error_callbacks(metric)

        # 记录调试日志
        if self._enable_logging and not success:
            logger.error(
                f"Query failed: {error_message} - " f"{sql[:100]}{'...' if len(sql) > 100 else ''}"
            )

    def _update_statistics(self, metric: QueryMetric) -> None:
        """更新查询统计。

        Args:
            metric: 查询指标
        """
        # 生成查询模式键（简化SQL）
        pattern_key = self._get_query_pattern(metric.sql)

        stats = self._query_stats[pattern_key]
        stats.total_queries += 1
        stats.total_duration_ms += metric.duration_ms

        if not metric.success:
            stats.total_errors += 1

        if metric.duration_ms > self._slow_query_threshold:
            stats.slow_query_count += 1

        # 更新最大最小值
        stats.max_duration_ms = max(stats.max_duration_ms, metric.duration_ms)
        stats.min_duration_ms = min(stats.min_duration_ms, metric.duration_ms)

        # 计算平均值
        stats.avg_duration_ms = stats.total_duration_ms / stats.total_queries

    def _get_query_pattern(self, sql: str) -> str:
        """获取查询模式键。

        将SQL语句简化为模式键，用于统计分组。

        Args:
            sql: SQL语句

        Returns:
            查询模式键
        """
        # 简化SQL：移除具体值，保留结构
        import re

        # 移除字符串字面量
        pattern = re.sub(r"'[^']*'", "'?'", sql)
        # 移除数字字面量
        pattern = re.sub(r"\b\d+\b", "?", pattern)
        # 移除多余空格
        pattern = " ".join(pattern.split())

        return pattern[:200]  # 限制长度

    def _sanitize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """脱敏查询参数。

        Args:
            params: 原始参数

        Returns:
            脱敏后的参数
        """
        sensitive_keys = {
            "password",
            "token",
            "secret",
            "key",
            "credential",
            "auth",
        }

        sanitized = {}
        for key, value in params.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:100] + "..."
            else:
                sanitized[key] = value

        return sanitized

    def _trigger_slow_query_callbacks(self, metric: QueryMetric) -> None:
        """触发慢查询回调。

        Args:
            metric: 查询指标
        """
        for callback in self._on_slow_query_callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Slow query callback error: {e}")

    def _trigger_error_callbacks(self, metric: QueryMetric) -> None:
        """触发错误回调。

        Args:
            metric: 查询指标
        """
        for callback in self._on_error_callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Error callback error: {e}")

    def register_slow_query_callback(self, callback: Callable[[QueryMetric], None]) -> None:
        """注册慢查询回调函数。

        Args:
            callback: 回调函数
        """
        self._on_slow_query_callbacks.append(callback)

    def register_error_callback(self, callback: Callable[[QueryMetric], None]) -> None:
        """注册错误回调函数。

        Args:
            callback: 回调函数
        """
        self._on_error_callbacks.append(callback)

    def get_statistics(self) -> dict[str, Any]:
        """获取性能统计信息。

        Returns:
            统计信息字典
        """
        with self._lock:
            # 计算总体统计
            total_queries = sum(stats.total_queries for stats in self._query_stats.values())
            total_errors = sum(stats.total_errors for stats in self._query_stats.values())
            total_duration = sum(stats.total_duration_ms for stats in self._query_stats.values())
            slow_query_count = sum(stats.slow_query_count for stats in self._query_stats.values())

            return {
                "total_queries": total_queries,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_queries * 100 if total_queries > 0 else 0),
                "total_duration_ms": total_duration,
                "avg_duration_ms": (total_duration / total_queries if total_queries > 0 else 0),
                "slow_query_count": slow_query_count,
                "slow_query_threshold_ms": self._slow_query_threshold,
                "query_patterns": len(self._query_stats),
                "history_size": len(self._query_history),
            }

    def get_slow_queries(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取慢查询列表。

        Args:
            limit: 最大返回数量

        Returns:
            慢查询列表
        """
        with self._lock:
            sorted_queries = sorted(self._slow_queries, key=lambda x: x.duration_ms, reverse=True)
            return [
                {
                    "sql": q.sql,
                    "duration_ms": q.duration_ms,
                    "timestamp": q.timestamp.isoformat(),
                    "success": q.success,
                    "rows_affected": q.rows_affected,
                    "caller": q.caller,
                }
                for q in sorted_queries[:limit]
            ]

    def get_query_patterns(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取查询模式统计。

        Args:
            limit: 最大返回数量

        Returns:
            查询模式列表
        """
        with self._lock:
            sorted_patterns = sorted(
                self._query_stats.items(),
                key=lambda x: x[1].total_queries,
                reverse=True,
            )

            return [
                {
                    "pattern": pattern[:100],
                    "total_queries": stats.total_queries,
                    "total_errors": stats.total_errors,
                    "avg_duration_ms": round(stats.avg_duration_ms, 2),
                    "max_duration_ms": round(stats.max_duration_ms, 2),
                    "min_duration_ms": (
                        round(stats.min_duration_ms, 2)
                        if stats.min_duration_ms != float("inf")
                        else 0
                    ),
                    "slow_query_count": stats.slow_query_count,
                }
                for pattern, stats in sorted_patterns[:limit]
            ]

    def get_recent_queries(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取最近的查询记录。

        Args:
            limit: 最大返回数量

        Returns:
            查询记录列表
        """
        with self._lock:
            return [
                {
                    "sql": q.sql,
                    "duration_ms": q.duration_ms,
                    "timestamp": q.timestamp.isoformat(),
                    "success": q.success,
                    "rows_affected": q.rows_affected,
                }
                for q in self._query_history[-limit:]
            ]

    def clear_history(self) -> None:
        """清空历史记录。"""
        with self._lock:
            self._query_history.clear()
            self._slow_queries.clear()
            self._query_stats.clear()

        logger.info("Query history cleared")

    def export_metrics(self) -> dict[str, Any]:
        """导出性能指标。

        Returns:
            性能指标字典
        """
        return {
            "statistics": self.get_statistics(),
            "slow_queries": self.get_slow_queries(limit=50),
            "query_patterns": self.get_query_patterns(limit=50),
            "recent_queries": self.get_recent_queries(limit=50),
            "exported_at": datetime.now().isoformat(),
        }


# ============================================================================
# SQLAlchemy事件监听器
# ============================================================================


def setup_query_monitoring(
    engine: Engine,
    monitor: QueryPerformanceMonitor,
    include_caller: bool = True,
) -> None:
    """设置SQLAlchemy查询监控。

    Args:
        engine: SQLAlchemy引擎
        monitor: 查询性能监控器
        include_caller: 是否包含调用者信息
    """
    import traceback

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """查询执行前记录开始时间。"""
        context._query_start_time = time.perf_counter()

        # 记录调用者信息
        if include_caller:
            # 获取调用栈
            stack = traceback.extract_stack()
            # 查找调用者（跳过SQLAlchemy内部调用）
            caller = None
            for frame in reversed(stack):
                if "sqlalchemy" not in frame.filename:
                    caller = f"{frame.filename}:{frame.lineno} in {frame.name}"
                    break
            context._query_caller = caller

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """查询执行后记录性能指标。"""
        duration_ms = (time.perf_counter() - context._query_start_time) * 1000
        rows_affected = cursor.rowcount if hasattr(cursor, "rowcount") else 0

        # 获取调用者信息
        caller = getattr(context, "_query_caller", None)

        # 记录查询
        monitor.record_query(
            sql=statement,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            success=True,
            params=parameters if isinstance(parameters, dict) else None,
            caller=caller,
        )

    @event.listens_for(engine, "handle_error")
    def handle_error(exception_context):
        """处理查询错误。"""
        # 获取执行时间
        duration_ms = 0.0
        if hasattr(exception_context, "_query_start_time"):
            duration_ms = (time.perf_counter() - exception_context._query_start_time) * 1000

        # 记录错误查询
        monitor.record_query(
            sql=str(exception_context.statement),
            duration_ms=duration_ms,
            success=False,
            error_message=str(exception_context.original_exception),
            caller=getattr(exception_context, "_query_caller", None),
        )

    logger.info("Query monitoring setup completed")


# ============================================================================
# 性能监控上下文管理器
# ============================================================================


class QueryPerformanceTracker:
    """查询性能追踪器。

    用于追踪特定代码块的查询性能。

    Example:
        >>> with QueryPerformanceTracker("data_loading") as tracker:
        ...     data = load_data()
        >>> print(tracker.duration_ms)
    """

    def __init__(self, name: str = "query_block") -> None:
        """初始化追踪器。

        Args:
            name: 追踪块名称
        """
        self._name = name
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._duration_ms: float = 0.0
        self._query_count: int = 0

    @property
    def duration_ms(self) -> float:
        """获取执行时间（毫秒）。"""
        return self._duration_ms

    @property
    def query_count(self) -> int:
        """获取查询次数。"""
        return self._query_count

    def __enter__(self) -> "QueryPerformanceTracker":
        """进入上下文。"""
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文。"""
        self._end_time = time.perf_counter()
        self._duration_ms = (self._end_time - self._start_time) * 1000

        logger.debug(
            f"[{self._name}] Duration: {self._duration_ms:.2f}ms, " f"Queries: {self._query_count}"
        )


@contextmanager
def track_query_performance(name: str = "query"):
    """查询性能追踪上下文管理器。

    Args:
        name: 追踪块名称

    Yields:
        QueryPerformanceTracker: 追踪器实例

    Example:
        >>> with track_query_performance("load_users") as tracker:
        ...     users = session.query(User).all()
    """
    tracker = QueryPerformanceTracker(name)
    try:
        yield tracker
    finally:
        pass


# ============================================================================
# 全局实例
# ============================================================================

_global_monitor: QueryPerformanceMonitor | None = None
_global_monitor_lock = Lock()


def get_query_monitor() -> QueryPerformanceMonitor:
    """获取全局查询性能监控器。

    Returns:
        QueryPerformanceMonitor: 全局监控器实例
    """
    global _global_monitor

    if _global_monitor is None:
        with _global_monitor_lock:
            if _global_monitor is None:
                _global_monitor = QueryPerformanceMonitor()

    return _global_monitor


def init_query_monitor(
    slow_query_threshold_ms: float = 100.0,
    max_history_size: int = 10000,
    enable_logging: bool = True,
) -> QueryPerformanceMonitor:
    """初始化全局查询性能监控器。

    Args:
        slow_query_threshold_ms: 慢查询阈值
        max_history_size: 最大历史记录数
        enable_logging: 是否启用日志

    Returns:
        QueryPerformanceMonitor: 监控器实例
    """
    global _global_monitor

    with _global_monitor_lock:
        _global_monitor = QueryPerformanceMonitor(
            slow_query_threshold_ms=slow_query_threshold_ms,
            max_history_size=max_history_size,
            enable_logging=enable_logging,
        )

    return _global_monitor


# ============================================================================
# 便捷函数
# ============================================================================


def record_query(
    sql: str,
    duration_ms: float,
    rows_affected: int = 0,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """记录查询性能指标的便捷函数。

    Args:
        sql: SQL语句
        duration_ms: 执行时间（毫秒）
        rows_affected: 影响行数
        success: 是否成功
        error_message: 错误信息
    """
    monitor = get_query_monitor()
    monitor.record_query(
        sql=sql,
        duration_ms=duration_ms,
        rows_affected=rows_affected,
        success=success,
        error_message=error_message,
    )


def get_slow_queries(limit: int = 100) -> list[dict[str, Any]]:
    """获取慢查询列表的便捷函数。

    Args:
        limit: 最大返回数量

    Returns:
        慢查询列表
    """
    monitor = get_query_monitor()
    return monitor.get_slow_queries(limit)


def get_query_statistics() -> dict[str, Any]:
    """获取查询统计的便捷函数。

    Returns:
        统计信息字典
    """
    monitor = get_query_monitor()
    return monitor.get_statistics()
