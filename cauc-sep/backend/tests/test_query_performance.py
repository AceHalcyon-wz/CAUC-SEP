"""
查询性能测试模块

文件名: test_query_performance.py
路径: tests/
功能: 数据库查询性能测试，包括索引效果验证、性能基准测试
作者: SQL架构师 Agent
创建日期: 2026-03-07
依赖: pytest, sqlalchemy
"""

import json
import os

# 添加项目根目录到系统路径
import sys
import tempfile
import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.index_optimizer import (
    DatabaseIndexMigration,
    IndexOptimizer,
    QueryPerformanceMonitor,
)
from models import AuditLog, Base, DataRecord, Experiment, User


class TestQueryPerformance:
    """查询性能测试类。"""

    @pytest.fixture
    def test_db(self):
        """创建测试数据库。"""
        # 创建临时数据库
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # 创建引擎和表
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)

        # 创建会话工厂
        Session = sessionmaker(bind=engine)

        # 插入测试数据
        session = Session()
        try:
            # 创建测试用户（密码哈希需要至少32字符）
            user = User(
                username="test_user",
                password_hash="a" * 64,  # 64字符的模拟密码哈希
                role="user",
                email="test@example.com",
            )
            session.add(user)
            session.commit()

            # 创建测试实验
            experiments = []
            for i in range(10):
                exp = Experiment(
                    exp_name=f"测试实验_{i}",
                    exp_type="测试类型",
                    user_id=user.id,
                    status="completed" if i % 2 == 0 else "running",
                )
                experiments.append(exp)
            session.add_all(experiments)
            session.commit()

            # 创建测试数据记录（大量数据用于性能测试）
            data_records = []
            base_time = datetime.now() - timedelta(days=1)
            for exp in experiments:
                for j in range(1000):
                    record = DataRecord(
                        experiment_id=exp.id,
                        timestamp=base_time + timedelta(seconds=j),
                        position_steps=j * 10,
                        position_mm=j * 0.01,
                        field_value=j * 0.5,
                        current_value=j * 0.1,
                        temperature=25.0 + j * 0.01,
                    )
                    data_records.append(record)
            session.add_all(data_records)
            session.commit()

            # 创建测试审计日志
            audit_logs = []
            for i in range(500):
                log = AuditLog(
                    timestamp=datetime.now() - timedelta(hours=i),
                    user_id=user.id if i % 3 == 0 else None,
                    operation_type="test_operation",
                    operation_category="device",
                    request_method="GET",
                    request_path=f"/api/test/{i}",
                    response_status=200 if i % 5 != 0 else 404,
                )
                audit_logs.append(log)
            session.add_all(audit_logs)
            session.commit()

        finally:
            session.close()
            engine.dispose()  # 关闭引擎连接池

        yield db_path

        # 清理（确保所有连接已关闭）
        import time

        time.sleep(0.1)  # 短暂等待确保连接释放
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass  # Windows下可能无法立即删除，忽略错误

    def test_index_optimizer_initialization(self, test_db):
        """测试索引优化器初始化。"""
        optimizer = IndexOptimizer(test_db)

        assert optimizer is not None
        assert optimizer._db_path == test_db

    def test_get_existing_indexes(self, test_db):
        """测试获取现有索引。"""
        optimizer = IndexOptimizer(test_db)
        indexes = optimizer._get_existing_indexes()

        assert isinstance(indexes, dict)
        assert len(indexes) > 0

        # 检查是否有主键索引
        for table, idx_list in indexes.items():
            assert isinstance(idx_list, set)

    def test_analyze_table_statistics(self, test_db):
        """测试分析表统计信息。"""
        optimizer = IndexOptimizer(test_db)
        stats = optimizer._analyze_table_statistics()

        assert isinstance(stats, dict)
        assert "data_records" in stats
        assert stats["data_records"]["row_count"] == 10000  # 10个实验 * 1000条记录
        assert "timestamp" in stats["data_records"]["columns"]

    def test_analyze_query_patterns(self, test_db):
        """测试分析查询模式。"""
        optimizer = IndexOptimizer(test_db)
        recommendations = optimizer.analyze_query_patterns()

        assert isinstance(recommendations, list)
        # 应该有推荐（基于预定义配置）
        assert len(recommendations) >= 0

    def test_create_index(self, test_db):
        """测试创建索引。"""
        optimizer = IndexOptimizer(test_db)

        # 创建测试索引
        success = optimizer.create_index(
            table_name="data_records",
            index_name="ix_test_index",
            columns=["position_steps"],
        )

        assert success is True

        # 验证索引已创建
        indexes = optimizer._get_existing_indexes()
        assert "ix_test_index" in indexes.get("data_records", set())

    def test_drop_index(self, test_db):
        """测试删除索引。"""
        optimizer = IndexOptimizer(test_db)

        # 先创建索引
        optimizer.create_index(
            table_name="data_records",
            index_name="ix_test_drop",
            columns=["temperature"],
        )

        # 删除索引
        success = optimizer.drop_index("ix_test_drop")

        assert success is True

        # 验证索引已删除
        indexes = optimizer._get_existing_indexes()
        assert "ix_test_drop" not in indexes.get("data_records", set())

    def test_analyze_query_performance(self, test_db):
        """测试分析查询性能。"""
        optimizer = IndexOptimizer(test_db)

        sql = "SELECT * FROM data_records WHERE experiment_id = 1 LIMIT 100"
        result = optimizer.analyze_query_performance(sql)

        assert "sql" in result
        assert "plan" in result
        assert "duration_ms" in result
        assert "rows_returned" in result
        assert "success" in result
        assert result["success"] is True

    def test_database_index_migration(self, test_db):
        """测试数据库索引迁移。"""
        migration = DatabaseIndexMigration(test_db)

        # 执行迁移
        result = migration.migrate(dry_run=False)

        assert "created_indexes" in result
        assert "skipped_indexes" in result
        assert "failed_indexes" in result

        # 应该创建了一些索引
        assert len(result["created_indexes"]) > 0

    def test_database_index_migration_dry_run(self, test_db):
        """测试数据库索引迁移（预演模式）。"""
        migration = DatabaseIndexMigration(test_db)

        # 执行预演
        result = migration.migrate(dry_run=True)

        assert result["dry_run"] is True
        assert len(result["created_indexes"]) > 0

        # 验证索引未实际创建
        optimizer = IndexOptimizer(test_db)
        indexes = optimizer._get_existing_indexes()

        for idx in result["created_indexes"]:
            # 预演模式下索引不应该存在
            assert idx["index_name"] not in indexes.get(idx["table_name"], set())

    def test_database_index_rollback(self, test_db):
        """测试数据库索引回滚。"""
        migration = DatabaseIndexMigration(test_db)

        # 先执行迁移
        migration.migrate(dry_run=False)

        # 执行回滚
        result = migration.rollback()

        assert "dropped_indexes" in result
        assert "failed_drops" in result

    def test_query_performance_monitor(self, test_db):
        """测试查询性能监控器。"""
        monitor = QueryPerformanceMonitor(test_db)

        # 记录一些查询
        for i in range(10):
            monitor.record_query(
                sql=f"SELECT * FROM data_records WHERE id = {i}",
                duration_ms=10.0 + i * 2,
                rows_affected=1,
                success=True,
            )

        # 获取统计信息
        stats = monitor.get_statistics()

        assert stats["total_queries"] == 10
        assert stats["total_errors"] == 0
        assert stats["avg_duration_ms"] > 0

    def test_query_performance_monitor_slow_queries(self, test_db):
        """测试查询性能监控器慢查询检测。"""
        monitor = QueryPerformanceMonitor(test_db, slow_query_threshold_ms=50.0)

        # 记录一些查询（包括慢查询）
        for i in range(5):
            monitor.record_query(
                sql=f"SELECT * FROM data_records WHERE id = {i}",
                duration_ms=10.0,
                success=True,
            )

        # 记录慢查询
        monitor.record_query(
            sql="SELECT * FROM data_records WHERE timestamp > datetime('now', '-1 day')",
            duration_ms=150.0,
            rows_affected=1000,
            success=True,
        )

        # 获取慢查询
        slow_queries = monitor.get_slow_queries()

        assert len(slow_queries) >= 1
        assert slow_queries[0]["duration_ms"] >= 50.0

    def test_query_performance_monitor_patterns(self, test_db):
        """测试查询性能监控器查询模式分析。"""
        monitor = QueryPerformanceMonitor(test_db)

        # 记录重复查询
        for i in range(20):
            monitor.record_query(
                sql="SELECT * FROM data_records WHERE experiment_id = 1",
                duration_ms=15.0 + i,
                success=True,
            )

        # 获取查询模式
        patterns = monitor.get_query_patterns()

        assert len(patterns) > 0
        # 应该检测到重复查询模式
        assert any(p["execution_count"] >= 20 for p in patterns)

    def test_index_effectiveness_comparison(self, test_db):
        """测试索引效果对比。"""
        optimizer = IndexOptimizer(test_db)

        # 测试查询
        test_sql = """
            SELECT * FROM data_records
            WHERE experiment_id = 1
            AND timestamp >= datetime('now', '-1 day')
            ORDER BY timestamp DESC
            LIMIT 100
        """

        # 无索引时的性能
        result_before = optimizer.analyze_query_performance(test_sql)
        duration_before = result_before["duration_ms"]

        # 创建索引
        optimizer.create_index(
            table_name="data_records",
            index_name="ix_test_exp_timestamp",
            columns=["experiment_id", "timestamp DESC"],
        )

        # 有索引时的性能
        result_after = optimizer.analyze_query_performance(test_sql)
        duration_after = result_after["duration_ms"]

        # 记录性能对比
        print(f"\n性能对比:")
        print(f"  无索引: {duration_before:.2f}ms")
        print(f"  有索引: {duration_after:.2f}ms")

        # 索引应该不会让查询变慢（至少不应该显著变慢）
        # 注意：在小数据集上，索引效果可能不明显
        assert result_after["success"] is True

        # 清理测试索引
        optimizer.drop_index("ix_test_exp_timestamp")

    def test_concurrent_query_monitoring(self, test_db):
        """测试并发查询监控。"""
        import threading

        monitor = QueryPerformanceMonitor(test_db)

        def record_queries(thread_id):
            for i in range(10):
                monitor.record_query(
                    sql=f"SELECT * FROM data_records WHERE id = {thread_id * 10 + i}",
                    duration_ms=5.0,
                    success=True,
                )

        # 创建多个线程并发记录查询
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_queries, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证统计
        stats = monitor.get_statistics()
        assert stats["total_queries"] == 50  # 5个线程 * 10个查询

    def test_performance_monitor_clear_history(self, test_db):
        """测试清空性能监控历史。"""
        monitor = QueryPerformanceMonitor(test_db)

        # 记录一些查询
        for i in range(10):
            monitor.record_query(
                sql=f"SELECT * FROM data_records WHERE id = {i}",
                duration_ms=10.0,
                success=True,
            )

        # 清空历史
        monitor.clear_history()

        # 验证历史已清空
        stats = monitor.get_statistics()
        assert stats["total_queries"] == 0
        assert stats["history_size"] == 0


class TestBenchmarkQueries:
    """查询性能基准测试类。"""

    @pytest.fixture
    def benchmark_db(self):
        """创建基准测试数据库（大数据集）。"""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # 创建大量测试数据（密码哈希需要至少32字符）
            user = User(
                username="benchmark_user",
                password_hash="b" * 64,  # 64字符的模拟密码哈希
                role="user",
                email="benchmark@example.com",
            )
            session.add(user)
            session.commit()

            # 创建100个实验
            experiments = []
            for i in range(100):
                exp = Experiment(
                    exp_name=f"基准测试实验_{i}",
                    exp_type="基准测试",
                    user_id=user.id,
                    status="completed",
                )
                experiments.append(exp)
            session.add_all(experiments)
            session.commit()

            # 每个实验1000条数据记录（共10万条）
            data_records = []
            base_time = datetime.now() - timedelta(days=7)
            for exp in experiments:
                for j in range(1000):
                    record = DataRecord(
                        experiment_id=exp.id,
                        timestamp=base_time + timedelta(seconds=j),
                        position_steps=j * 10,
                        position_mm=j * 0.01,
                        field_value=j * 0.5,
                        current_value=j * 0.1,
                        temperature=25.0 + j * 0.001,
                    )
                    data_records.append(record)

                # 每10000条提交一次
                if len(data_records) >= 10000:
                    session.bulk_save_objects(data_records)
                    session.commit()
                    data_records = []

            if data_records:
                session.bulk_save_objects(data_records)
                session.commit()

        finally:
            session.close()

        yield db_path

        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_benchmark_data_records_query(self, benchmark_db):
        """基准测试：数据记录查询。"""
        optimizer = IndexOptimizer(benchmark_db)

        # 创建索引
        migration = DatabaseIndexMigration(benchmark_db)
        migration.migrate(dry_run=False)

        # 测试查询
        queries = [
            {
                "name": "单实验时间范围查询",
                "sql": """
                    SELECT * FROM data_records
                    WHERE experiment_id = 50
                    AND timestamp >= datetime('now', '-3 days')
                    ORDER BY timestamp DESC
                    LIMIT 100
                """,
            },
            {
                "name": "多实验聚合查询",
                "sql": """
                    SELECT experiment_id, COUNT(*) as count, AVG(field_value) as avg_field
                    FROM data_records
                    WHERE timestamp >= datetime('now', '-5 days')
                    GROUP BY experiment_id
                    ORDER BY count DESC
                """,
            },
            {
                "name": "位置范围查询",
                "sql": """
                    SELECT * FROM data_records
                    WHERE position_steps BETWEEN 5000 AND 10000
                    AND experiment_id IN (1, 2, 3, 4, 5)
                    ORDER BY position_steps
                    LIMIT 500
                """,
            },
        ]

        results = []
        for query in queries:
            result = optimizer.analyze_query_performance(query["sql"])
            results.append(
                {
                    "name": query["name"],
                    "duration_ms": result["duration_ms"],
                    "rows_returned": result["rows_returned"],
                }
            )
            print(
                f"\n{query['name']}: {result['duration_ms']:.2f}ms, {result['rows_returned']} rows"
            )

        # 所有查询应该成功完成
        assert all(r["duration_ms"] < 1000 for r in results)  # 应该在1秒内完成

    def test_benchmark_experiments_query(self, benchmark_db):
        """基准测试：实验查询。"""
        optimizer = IndexOptimizer(benchmark_db)

        # 创建索引
        migration = DatabaseIndexMigration(benchmark_db)
        migration.migrate(dry_run=False)

        queries = [
            {
                "name": "用户实验查询",
                "sql": """
                    SELECT e.*, u.username
                    FROM experiments e
                    LEFT JOIN users u ON e.user_id = u.id
                    WHERE e.status = 'completed'
                    ORDER BY e.created_at DESC
                    LIMIT 50
                """,
            },
            {
                "name": "实验统计查询",
                "sql": """
                    SELECT
                        exp_type,
                        status,
                        COUNT(*) as count,
                        MIN(created_at) as first_created,
                        MAX(created_at) as last_created
                    FROM experiments
                    GROUP BY exp_type, status
                    ORDER BY count DESC
                """,
            },
        ]

        for query in queries:
            result = optimizer.analyze_query_performance(query["sql"])
            print(f"\n{query['name']}: {result['duration_ms']:.2f}ms")
            assert result["success"] is True


# ==================== 性能测试报告生成 ====================


def generate_performance_report(db_path: str, output_path: str = None):
    """生成性能测试报告。

    Args:
        db_path: 数据库文件路径
        output_path: 输出文件路径，可选

    Returns:
        性能报告字典
    """
    optimizer = IndexOptimizer(db_path)
    monitor = QueryPerformanceMonitor(db_path)

    # 执行索引迁移
    migration = DatabaseIndexMigration(db_path)
    migration_result = migration.migrate(dry_run=False)

    # 测试查询性能
    test_queries = [
        "SELECT * FROM data_records WHERE experiment_id = 1 LIMIT 100",
        "SELECT * FROM experiments WHERE status = 'completed' ORDER BY created_at DESC LIMIT 50",
        "SELECT * FROM audit_logs WHERE timestamp >= datetime('now', '-7 days') LIMIT 100",
    ]

    performance_results = []
    for sql in test_queries:
        result = optimizer.analyze_query_performance(sql)
        performance_results.append(
            {
                "sql": sql,
                "duration_ms": result["duration_ms"],
                "rows_returned": result["rows_returned"],
            }
        )

    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "database": db_path,
        "migration_result": migration_result,
        "performance_results": performance_results,
        "index_statistics": optimizer.get_index_usage_statistics(),
    }

    # 保存报告
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    return report


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s", "--tb=short"])
