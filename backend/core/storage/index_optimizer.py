"""
数据库索引优化模块

文件名: index_optimizer.py
路径: core/
功能: 数据库索引分析与优化，包括索引推荐、创建、监控和性能测试
作者: SQL架构师 Agent
创建日期: 2026-03-07
依赖: sqlalchemy, sqlite3
"""

import logging
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock, RLock
from typing import Any

from sqlalchemy import event

logger = logging.getLogger(__name__)


@dataclass
class QueryPattern:
    """查询模式分析结果。

    Attributes:
        query_hash: 查询哈希值
        table_name: 表名
        where_columns: WHERE子句涉及的列
        order_by_columns: ORDER BY子句涉及的列
        join_tables: JOIN的表
        execution_count: 执行次数
        avg_duration_ms: 平均执行时间（毫秒）
        max_duration_ms: 最大执行时间（毫秒）
        last_executed: 最后执行时间
    """

    query_hash: str
    table_name: str
    where_columns: list[str] = field(default_factory=list)
    order_by_columns: list[str] = field(default_factory=list)
    join_tables: list[str] = field(default_factory=list)
    execution_count: int = 0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    last_executed: datetime | None = None


@dataclass
class IndexRecommendation:
    """索引推荐。

    Attributes:
        table_name: 表名
        index_name: 索引名称
        columns: 索引列
        reason: 推荐原因
        priority: 优先级（1-5，5最高）
        estimated_benefit: 预估收益百分比
    """

    table_name: str
    index_name: str
    columns: list[str]
    reason: str
    priority: int = 3
    estimated_benefit: float = 0.0


@dataclass
class QueryPerformanceMetrics:
    """查询性能指标。

    Attributes:
        query_id: 查询标识
        sql: SQL语句
        duration_ms: 执行时间（毫秒）
        rows_affected: 影响行数
        timestamp: 执行时间戳
        success: 是否成功
        error_message: 错误信息
    """

    query_id: str
    sql: str
    duration_ms: float
    rows_affected: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str | None = None


class QueryPerformanceMonitor:
    """
    查询性能监控器。

    实时监控数据库查询性能，记录慢查询，
    分析查询模式，提供性能优化建议。

    Attributes:
        slow_query_threshold_ms: 慢查询阈值（毫秒）
        max_history_size: 最大历史记录数
    """

    def __init__(
        self,
        db_path: str,
        slow_query_threshold_ms: float = 100.0,
        max_history_size: int = 10000,
    ) -> None:
        """初始化查询性能监控器。

        Args:
            db_path: 数据库文件路径
            slow_query_threshold_ms: 慢查询阈值，默认100毫秒
            max_history_size: 最大历史记录数，默认10000
        """
        self._db_path = db_path
        self._slow_query_threshold = slow_query_threshold_ms
        self._max_history_size = max_history_size

        # 性能统计
        self._query_history: list[QueryPerformanceMetrics] = []
        self._slow_queries: list[QueryPerformanceMetrics] = []
        self._query_patterns: dict[str, QueryPattern] = {}

        # 线程安全
        self._lock = RLock()

        # 统计计数器
        self._total_queries = 0
        self._total_errors = 0
        self._total_duration_ms = 0.0

        logger.info(f"QueryPerformanceMonitor initialized for {db_path}")

    def record_query(
        self,
        sql: str,
        duration_ms: float,
        rows_affected: int = 0,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """记录查询性能指标。

        Args:
            sql: SQL语句
            duration_ms: 执行时间（毫秒）
            rows_affected: 影响行数
            success: 是否成功
            error_message: 错误信息
        """
        with self._lock:
            # 生成查询ID
            query_id = self._generate_query_id(sql)

            # 创建性能指标
            metrics = QueryPerformanceMetrics(
                query_id=query_id,
                sql=sql,
                duration_ms=duration_ms,
                rows_affected=rows_affected,
                success=success,
                error_message=error_message,
            )

            # 更新统计
            self._total_queries += 1
            self._total_duration_ms += duration_ms
            if not success:
                self._total_errors += 1

            # 记录到历史
            self._query_history.append(metrics)
            if len(self._query_history) > self._max_history_size:
                self._query_history.pop(0)

            # 记录慢查询
            if duration_ms > self._slow_query_threshold:
                self._slow_queries.append(metrics)
                logger.warning(f"Slow query detected: {duration_ms:.2f}ms - {sql[:100]}...")

            # 更新查询模式分析
            self._update_query_pattern(sql, duration_ms)

    def _generate_query_id(self, sql: str) -> str:
        """生成查询ID。

        Args:
            sql: SQL语句

        Returns:
            查询ID字符串
        """
        import hashlib

        normalized = " ".join(sql.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _update_query_pattern(self, sql: str, duration_ms: float) -> None:
        """更新查询模式分析。

        Args:
            sql: SQL语句
            duration_ms: 执行时间
        """
        query_id = self._generate_query_id(sql)

        if query_id in self._query_patterns:
            pattern = self._query_patterns[query_id]
            pattern.execution_count += 1
            pattern.avg_duration_ms = (
                pattern.avg_duration_ms * (pattern.execution_count - 1) + duration_ms
            ) / pattern.execution_count
            pattern.max_duration_ms = max(pattern.max_duration_ms, duration_ms)
            pattern.last_executed = datetime.now()
        else:
            # 解析查询模式
            pattern = self._parse_query_pattern(sql, query_id)
            pattern.execution_count = 1
            pattern.avg_duration_ms = duration_ms
            pattern.max_duration_ms = duration_ms
            pattern.last_executed = datetime.now()
            self._query_patterns[query_id] = pattern

    def _parse_query_pattern(self, sql: str, query_id: str) -> QueryPattern:
        """解析SQL查询模式。

        Args:
            sql: SQL语句
            query_id: 查询ID

        Returns:
            查询模式对象
        """
        sql_lower = sql.lower()

        # 提取表名
        table_name = ""
        if "from" in sql_lower:
            parts = sql_lower.split("from")
            if len(parts) > 1:
                table_part = parts[1].split()[0].strip()
                table_name = table_part.rstrip(";").strip('`"')

        # 提取WHERE列
        where_columns = []
        if "where" in sql_lower:
            where_part = sql_lower.split("where")[1].split("order by")[0]
            where_part = where_part.split("group by")[0]
            where_part = where_part.split("limit")[0]

            # 简单提取列名（实际应用中可能需要更复杂的解析）
            import re

            columns = re.findall(r"(\w+)\s*(?:=|>|<|>=|<=|!=|like|in)", where_part)
            where_columns = list(set(columns))

        # 提取ORDER BY列
        order_by_columns = []
        if "order by" in sql_lower:
            order_part = sql_lower.split("order by")[1].split("limit")[0]
            order_part = order_part.split(";")[0]
            columns = [col.strip().split()[0] for col in order_part.split(",")]
            order_by_columns = [c for c in columns if c]

        return QueryPattern(
            query_hash=query_id,
            table_name=table_name,
            where_columns=where_columns,
            order_by_columns=order_by_columns,
        )

    def get_statistics(self) -> dict[str, Any]:
        """获取性能统计信息。

        Returns:
            统计信息字典
        """
        with self._lock:
            avg_duration = (
                self._total_duration_ms / self._total_queries if self._total_queries > 0 else 0
            )

            return {
                "total_queries": self._total_queries,
                "total_errors": self._total_errors,
                "error_rate": (
                    self._total_errors / self._total_queries * 100 if self._total_queries > 0 else 0
                ),
                "avg_duration_ms": avg_duration,
                "slow_query_count": len(self._slow_queries),
                "slow_query_threshold_ms": self._slow_query_threshold,
                "unique_patterns": len(self._query_patterns),
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
                    "query_id": q.query_id,
                    "sql": q.sql,
                    "duration_ms": q.duration_ms,
                    "timestamp": q.timestamp.isoformat(),
                    "success": q.success,
                }
                for q in sorted_queries[:limit]
            ]

    def get_query_patterns(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取查询模式分析结果。

        Args:
            limit: 最大返回数量

        Returns:
            查询模式列表
        """
        with self._lock:
            sorted_patterns = sorted(
                self._query_patterns.values(),
                key=lambda x: x.execution_count,
                reverse=True,
            )
            return [
                {
                    "query_hash": p.query_hash,
                    "table_name": p.table_name,
                    "where_columns": p.where_columns,
                    "order_by_columns": p.order_by_columns,
                    "execution_count": p.execution_count,
                    "avg_duration_ms": p.avg_duration_ms,
                    "max_duration_ms": p.max_duration_ms,
                    "last_executed": (p.last_executed.isoformat() if p.last_executed else None),
                }
                for p in sorted_patterns[:limit]
            ]

    def clear_history(self) -> None:
        """清空历史记录。"""
        with self._lock:
            self._query_history.clear()
            self._slow_queries.clear()
            self._total_queries = 0
            self._total_errors = 0
            self._total_duration_ms = 0.0
            logger.info("Query history cleared")


class IndexOptimizer:
    """
    索引优化器。

    分析数据库查询模式，推荐和创建最优索引，
    提供索引使用统计和性能测试功能。

    Attributes:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: str) -> None:
        """初始化索引优化器。

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        self._lock = Lock()

        logger.info(f"IndexOptimizer initialized for {db_path}")

    def _get_connection(self):
        """获取数据库连接。

        Returns:
            sqlite3连接对象
        """
        return sqlite3.connect(self._db_path)

    def analyze_query_patterns(
        self, performance_monitor: QueryPerformanceMonitor | None = None
    ) -> list[IndexRecommendation]:
        """分析查询模式并生成索引推荐。

        Args:
            performance_monitor: 查询性能监控器，可选

        Returns:
            索引推荐列表
        """
        recommendations = []

        # 分析现有索引
        existing_indexes = self._get_existing_indexes()

        # 分析查询模式
        if performance_monitor:
            patterns = performance_monitor.get_query_patterns(limit=1000)
            for pattern in patterns:
                table_name = pattern["table_name"]
                where_cols = pattern["where_columns"]
                order_cols = pattern["order_by_columns"]

                if not table_name or not where_cols:
                    continue

                # 生成复合索引推荐
                if len(where_cols) > 1:
                    index_name = f"ix_{table_name}_{'_'.join(where_cols[:3])}"
                    if index_name not in existing_indexes.get(table_name, set()):
                        recommendations.append(
                            IndexRecommendation(
                                table_name=table_name,
                                index_name=index_name,
                                columns=where_cols[:3],
                                reason=f"高频查询模式，执行{pattern['execution_count']}次，"
                                f"平均耗时{pattern['avg_duration_ms']:.2f}ms",
                                priority=self._calculate_priority(pattern),
                                estimated_benefit=self._estimate_benefit(pattern),
                            )
                        )

        # 分析表结构和数据分布
        table_stats = self._analyze_table_statistics()
        for table_name, stats in table_stats.items():
            # 为大表添加时间索引
            if stats["row_count"] > 10000 and "timestamp" in stats["columns"]:
                index_name = f"ix_{table_name}_timestamp"
                if index_name not in existing_indexes.get(table_name, set()):
                    recommendations.append(
                        IndexRecommendation(
                            table_name=table_name,
                            index_name=index_name,
                            columns=["timestamp"],
                            reason=f"大表({stats['row_count']}行)时间范围查询优化",
                            priority=4,
                            estimated_benefit=30.0,
                        )
                    )

        # 去重并按优先级排序
        unique_recommendations = {}
        for rec in recommendations:
            key = f"{rec.table_name}:{','.join(rec.columns)}"
            if (
                key not in unique_recommendations
                or rec.priority > unique_recommendations[key].priority
            ):
                unique_recommendations[key] = rec

        return sorted(unique_recommendations.values(), key=lambda x: x.priority, reverse=True)

    def _calculate_priority(self, pattern: dict[str, Any]) -> int:
        """计算索引优先级。

        Args:
            pattern: 查询模式

        Returns:
            优先级（1-5）
        """
        priority = 3

        # 执行频率高
        if pattern["execution_count"] > 100:
            priority += 1
        if pattern["execution_count"] > 1000:
            priority += 1

        # 执行时间长
        if pattern["avg_duration_ms"] > 50:
            priority += 1
        if pattern["avg_duration_ms"] > 200:
            priority += 1

        return min(5, priority)

    def _estimate_benefit(self, pattern: dict[str, Any]) -> float:
        """预估索引收益。

        Args:
            pattern: 查询模式

        Returns:
            预估收益百分比
        """
        base_benefit = 20.0

        # 根据执行频率调整
        if pattern["execution_count"] > 100:
            base_benefit += 10
        if pattern["execution_count"] > 500:
            base_benefit += 10

        # 根据执行时间调整
        if pattern["avg_duration_ms"] > 50:
            base_benefit += 15
        if pattern["avg_duration_ms"] > 100:
            base_benefit += 15

        return min(80.0, base_benefit)

    def _get_existing_indexes(self) -> dict[str, set[str]]:
        """获取现有索引。

        Returns:
            表名到索引名集合的映射
        """
        indexes = defaultdict(set)

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            # 获取每个表的索引
            for table in tables:
                cursor.execute(f"PRAGMA index_list({table})")
                for row in cursor.fetchall():
                    index_name = row[1]
                    indexes[table].add(index_name)

        return dict(indexes)

    def _analyze_table_statistics(self) -> dict[str, dict[str, Any]]:
        """分析表统计信息。

        Returns:
            表统计信息字典
        """
        stats = {}

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                # 获取行数
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]

                # 获取列信息
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]

                stats[table] = {
                    "row_count": row_count,
                    "columns": columns,
                }

        return stats

    def create_index(self, table_name: str, index_name: str, columns: list[str]) -> bool:
        """创建索引。

        Args:
            table_name: 表名
            index_name: 索引名称
            columns: 索引列

        Returns:
            是否成功
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cols_str = ", ".join(columns)
                sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({cols_str})"
                cursor.execute(sql)
                conn.commit()

            logger.info(f"Index created: {index_name} on {table_name}({cols_str})")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False

    def drop_index(self, index_name: str) -> bool:
        """删除索引。

        Args:
            index_name: 索引名称

        Returns:
            是否成功
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
                conn.commit()

            logger.info(f"Index dropped: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to drop index {index_name}: {e}")
            return False

    def get_index_usage_statistics(self) -> dict[str, Any]:
        """获取索引使用统计。

        Returns:
            索引使用统计字典
        """
        stats = {}

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取所有索引
            cursor.execute("""
                SELECT m.name AS table_name, il.name AS index_name
                FROM sqlite_master m, pragma_index_list(m.name) il
                WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
                ORDER BY m.name, il.name
                """)

            for row in cursor.fetchall():
                table_name, index_name = row

                # 获取索引列
                cursor.execute(f"PRAGMA index_info({index_name})")
                columns = [col[2] for col in cursor.fetchall()]

                # 获取索引大小（SQLite不直接提供，使用文件大小估算）
                stats[index_name] = {
                    "table_name": table_name,
                    "columns": columns,
                    "index_name": index_name,
                }

        return stats

    def analyze_query_performance(self, sql: str) -> dict[str, Any]:
        """分析单个查询的性能。

        Args:
            sql: SQL语句

        Returns:
            性能分析结果
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 执行EXPLAIN QUERY PLAN
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            plan = cursor.fetchall()

            # 执行查询并计时
            start_time = time.perf_counter()
            try:
                cursor.execute(sql)
                rows = cursor.fetchall()
                duration_ms = (time.perf_counter() - start_time) * 1000
                success = True
                error = None
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                rows = []
                success = False
                error = str(e)

            return {
                "sql": sql,
                "plan": plan,
                "duration_ms": duration_ms,
                "rows_returned": len(rows),
                "success": success,
                "error": error,
            }


class DatabaseIndexMigration:
    """
    数据库索引迁移脚本。

    根据查询模式分析结果，自动创建和优化数据库索引。

    Attributes:
        db_path: 数据库文件路径
    """

    # 预定义的索引配置（基于项目查询模式）
    PREDEFINED_INDEXES = {
        "data_records": [
            {
                "name": "ix_data_records_exp_timestamp_desc",
                "columns": ["experiment_id", "timestamp DESC"],
                "reason": "实验数据按时间倒序查询优化",
            },
            {
                "name": "ix_data_records_exp_position",
                "columns": ["experiment_id", "position_steps"],
                "reason": "实验数据按位置查询优化",
            },
            {
                "name": "ix_data_records_timestamp_desc",
                "columns": ["timestamp DESC"],
                "reason": "全局时间范围查询优化",
            },
        ],
        "experiments": [
            {
                "name": "ix_experiments_status_created",
                "columns": ["status", "created_at DESC"],
                "reason": "按状态和时间查询实验",
            },
            {
                "name": "ix_experiments_type_status",
                "columns": ["exp_type", "status"],
                "reason": "按类型和状态查询实验",
            },
        ],
        "audit_logs": [
            {
                "name": "ix_audit_logs_timestamp_desc",
                "columns": ["timestamp DESC"],
                "reason": "审计日志时间范围查询优化",
            },
            {
                "name": "ix_audit_logs_type_timestamp",
                "columns": ["operation_type", "timestamp DESC"],
                "reason": "按操作类型查询审计日志",
            },
        ],
        "operation_logs": [
            {
                "name": "ix_operation_logs_created_desc",
                "columns": ["created_at DESC"],
                "reason": "操作日志时间范围查询优化",
            },
            {
                "name": "ix_operation_logs_operation_created",
                "columns": ["operation", "created_at DESC"],
                "reason": "按操作类型查询操作日志",
            },
        ],
        "device_calibrations": [
            {
                "name": "ix_calibrations_valid_device",
                "columns": ["valid_until", "device_id"],
                "reason": "查询即将过期的校准参数",
            },
        ],
    }

    def __init__(self, db_path: str) -> None:
        """初始化数据库索引迁移。

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        self._optimizer = IndexOptimizer(db_path)
        self._lock = Lock()

        logger.info(f"DatabaseIndexMigration initialized for {db_path}")

    def migrate(self, dry_run: bool = False) -> dict[str, Any]:
        """执行索引迁移。

        Args:
            dry_run: 是否只分析不执行

        Returns:
            迁移结果字典
        """
        result = {
            "created_indexes": [],
            "skipped_indexes": [],
            "failed_indexes": [],
            "dry_run": dry_run,
        }

        existing_indexes = self._optimizer._get_existing_indexes()

        for table_name, indexes in self.PREDEFINED_INDEXES.items():
            # 检查表是否存在
            if table_name not in existing_indexes:
                logger.warning(f"Table {table_name} does not exist, skipping")
                continue

            for index_config in indexes:
                index_name = index_config["name"]
                columns = index_config["columns"]
                reason = index_config["reason"]

                # 检查索引是否已存在
                if index_name in existing_indexes.get(table_name, set()):
                    result["skipped_indexes"].append(
                        {
                            "index_name": index_name,
                            "table_name": table_name,
                            "reason": "Already exists",
                        }
                    )
                    continue

                # 创建索引
                if dry_run:
                    result["created_indexes"].append(
                        {
                            "index_name": index_name,
                            "table_name": table_name,
                            "columns": columns,
                            "reason": reason,
                            "dry_run": True,
                        }
                    )
                else:
                    success = self._optimizer.create_index(table_name, index_name, columns)
                    if success:
                        result["created_indexes"].append(
                            {
                                "index_name": index_name,
                                "table_name": table_name,
                                "columns": columns,
                                "reason": reason,
                            }
                        )
                    else:
                        result["failed_indexes"].append(
                            {
                                "index_name": index_name,
                                "table_name": table_name,
                                "columns": columns,
                                "reason": reason,
                            }
                        )

        logger.info(
            f"Index migration completed: {len(result['created_indexes'])} created, "
            f"{len(result['skipped_indexes'])} skipped, "
            f"{len(result['failed_indexes'])} failed"
        )

        return result

    def rollback(self) -> dict[str, Any]:
        """回滚索引迁移（删除本次迁移创建的索引）。

        Returns:
            回滚结果字典
        """
        result = {
            "dropped_indexes": [],
            "failed_drops": [],
        }

        for table_name, indexes in self.PREDEFINED_INDEXES.items():
            for index_config in indexes:
                index_name = index_config["name"]

                success = self._optimizer.drop_index(index_name)
                if success:
                    result["dropped_indexes"].append(index_name)
                else:
                    result["failed_drops"].append(index_name)

        logger.info(
            f"Index rollback completed: {len(result['dropped_indexes'])} dropped, "
            f"{len(result['failed_drops'])} failed"
        )

        return result


# ==================== SQLAlchemy事件监听器 ====================


def setup_query_monitoring(engine: Any, monitor: QueryPerformanceMonitor) -> None:
    """设置SQLAlchemy查询监控。

    Args:
        engine: SQLAlchemy引擎
        monitor: 查询性能监控器
    """

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """查询执行前记录开始时间。"""
        context._query_start_time = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """查询执行后记录性能指标。"""
        duration_ms = (time.perf_counter() - context._query_start_time) * 1000
        rows_affected = cursor.rowcount if hasattr(cursor, "rowcount") else 0

        monitor.record_query(
            sql=statement,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            success=True,
        )


# ==================== 便捷函数 ====================


def create_index_optimizer(db_path: str) -> IndexOptimizer:
    """创建索引优化器的便捷函数。

    Args:
        db_path: 数据库文件路径

    Returns:
        IndexOptimizer实例

    Example:
        >>> optimizer = create_index_optimizer("experiments.db")
        >>> recommendations = optimizer.analyze_query_patterns()
    """
    return IndexOptimizer(db_path)


def create_performance_monitor(
    db_path: str, slow_query_threshold_ms: float = 100.0
) -> QueryPerformanceMonitor:
    """创建查询性能监控器的便捷函数。

    Args:
        db_path: 数据库文件路径
        slow_query_threshold_ms: 慢查询阈值

    Returns:
        QueryPerformanceMonitor实例

    Example:
        >>> monitor = create_performance_monitor("experiments.db")
        >>> monitor.record_query("SELECT * FROM users", 15.5)
    """
    return QueryPerformanceMonitor(db_path, slow_query_threshold_ms)


def run_index_migration(db_path: str, dry_run: bool = False) -> dict[str, Any]:
    """执行索引迁移的便捷函数。

    Args:
        db_path: 数据库文件路径
        dry_run: 是否只分析不执行

    Returns:
        迁移结果字典

    Example:
        >>> result = run_index_migration("experiments.db", dry_run=True)
        >>> print(f"Created: {len(result['created_indexes'])}")
    """
    migration = DatabaseIndexMigration(db_path)
    return migration.migrate(dry_run=dry_run)
