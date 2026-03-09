"""
数据库索引优化迁移脚本

文件名: optimize_indexes.py
路径: migrations/
功能: 执行数据库索引优化迁移，包括索引分析、创建和验证
作者: SQL架构师 Agent
创建日期: 2026-03-07
版本: 1.0

使用方法:
    python migrations/optimize_indexes.py --db experiments.db --analyze
    python migrations/optimize_indexes.py --db experiments.db --migrate
    python migrations/optimize_indexes.py --db experiments.db --rollback
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime

from sqlalchemy import create_engine, text

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.index_optimizer import (
    DatabaseIndexMigration,
    IndexOptimizer,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def backup_database(db_path: str) -> str:
    """备份数据库文件。

    Args:
        db_path: 数据库文件路径

    Returns:
        备份文件路径
    """
    from shutil import copy2

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.index_backup_{timestamp}"
    copy2(db_path, backup_path)
    logger.info(f"数据库已备份到: {backup_path}")
    return backup_path


def analyze_indexes(db_path: str) -> dict:
    """分析数据库索引。

    Args:
        db_path: 数据库文件路径

    Returns:
        分析结果字典
    """
    logger.info("=" * 60)
    logger.info("开始索引分析")
    logger.info("=" * 60)

    optimizer = IndexOptimizer(db_path)

    # 获取现有索引
    existing_indexes = optimizer._get_existing_indexes()
    logger.info(f"\n现有索引数量: {sum(len(v) for v in existing_indexes.values())}")
    for table, indexes in existing_indexes.items():
        logger.info(f"  {table}: {len(indexes)} 个索引")
        for idx in sorted(indexes):
            logger.info(f"    - {idx}")

    # 分析表统计
    table_stats = optimizer._analyze_table_statistics()
    logger.info("\n表统计信息:")
    for table, stats in table_stats.items():
        logger.info(f"  {table}: {stats['row_count']} 行, {len(stats['columns'])} 列")

    # 生成索引推荐
    recommendations = optimizer.analyze_query_patterns()
    logger.info(f"\n索引推荐数量: {len(recommendations)}")
    for rec in recommendations[:10]:  # 只显示前10个
        logger.info(f"  [{rec.priority}] {rec.table_name}.{rec.index_name}")
        logger.info(f"      列: {', '.join(rec.columns)}")
        logger.info(f"      原因: {rec.reason}")
        logger.info(f"      预估收益: {rec.estimated_benefit:.1f}%")

    return {
        "existing_indexes": existing_indexes,
        "table_stats": table_stats,
        "recommendations": [
            {
                "table_name": r.table_name,
                "index_name": r.index_name,
                "columns": r.columns,
                "reason": r.reason,
                "priority": r.priority,
                "estimated_benefit": r.estimated_benefit,
            }
            for r in recommendations
        ],
    }


def migrate_indexes(db_path: str, dry_run: bool = False, skip_backup: bool = False) -> dict:
    """执行索引迁移。

    Args:
        db_path: 数据库文件路径
        dry_run: 是否只分析不执行
        skip_backup: 是否跳过备份

    Returns:
        迁移结果字典
    """
    logger.info("=" * 60)
    logger.info("开始索引迁移")
    logger.info(f"数据库路径: {db_path}")
    logger.info(f"模式: {'预演' if dry_run else '执行'}")
    logger.info("=" * 60)

    # 备份数据库
    if not dry_run and not skip_backup:
        backup_path = backup_database(db_path)
        logger.info(f"如需回滚，请将 {backup_path} 重命名为 {db_path}")

    # 执行迁移
    migration = DatabaseIndexMigration(db_path)
    result = migration.migrate(dry_run=dry_run)

    # 输出结果
    logger.info("\n迁移结果:")
    logger.info(f"  创建索引: {len(result['created_indexes'])} 个")
    for idx in result["created_indexes"]:
        logger.info(
            f"    + {idx['index_name']} on {idx['table_name']}({', '.join(idx['columns'])})"
        )

    logger.info(f"  跳过索引: {len(result['skipped_indexes'])} 个")
    for idx in result["skipped_indexes"]:
        logger.info(f"    = {idx['index_name']} ({idx['reason']})")

    logger.info(f"  失败索引: {len(result['failed_indexes'])} 个")
    for idx in result["failed_indexes"]:
        logger.info(f"    x {idx['index_name']} ({idx['reason']})")

    return result


def rollback_indexes(db_path: str) -> dict:
    """回滚索引迁移。

    Args:
        db_path: 数据库文件路径

    Returns:
        回滚结果字典
    """
    logger.info("=" * 60)
    logger.info("开始索引回滚")
    logger.info("=" * 60)

    migration = DatabaseIndexMigration(db_path)
    result = migration.rollback()

    logger.info("\n回滚结果:")
    logger.info(f"  删除索引: {len(result['dropped_indexes'])} 个")
    for idx in result["dropped_indexes"]:
        logger.info(f"    - {idx}")

    logger.info(f"  失败删除: {len(result['failed_drops'])} 个")
    for idx in result["failed_drops"]:
        logger.info(f"    x {idx}")

    return result


def verify_indexes(db_path: str) -> dict:
    """验证索引创建情况。

    Args:
        db_path: 数据库文件路径

    Returns:
        验证结果字典
    """
    logger.info("=" * 60)
    logger.info("验证索引")
    logger.info("=" * 60)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    with engine.connect() as conn:
        # 获取所有索引
        result = conn.execute(text("""
                SELECT m.name AS table_name, il.name AS index_name
                FROM sqlite_master m, pragma_index_list(m.name) il
                WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
                ORDER BY m.name, il.name
            """))
        indexes = result.fetchall()

        logger.info(f"\n总索引数: {len(indexes)}")

        # 按表分组
        indexes_by_table = {}
        for table_name, index_name in indexes:
            if table_name not in indexes_by_table:
                indexes_by_table[table_name] = []
            indexes_by_table[table_name].append(index_name)

        for table, idx_list in sorted(indexes_by_table.items()):
            logger.info(f"\n{table}: {len(idx_list)} 个索引")
            for idx in sorted(idx_list):
                # 获取索引列
                col_result = conn.execute(text(f"PRAGMA index_info({idx})"))
                columns = [row[2] for row in col_result.fetchall()]
                logger.info(f"  - {idx} ({', '.join(columns)})")

        # 检查关键索引
        required_indexes = {
            "data_records": ["ix_data_records_exp_timestamp"],
            "experiments": ["ix_experiments_user_status"],
            "audit_logs": ["ix_audit_logs_timestamp"],
        }

        missing_indexes = []
        for table, required in required_indexes.items():
            existing = indexes_by_table.get(table, [])
            for idx in required:
                if idx not in existing:
                    missing_indexes.append(f"{table}.{idx}")

        if missing_indexes:
            logger.warning(f"\n缺失关键索引: {missing_indexes}")
        else:
            logger.info("\n所有关键索引已创建")

    return {
        "total_indexes": len(indexes),
        "indexes_by_table": indexes_by_table,
        "missing_indexes": missing_indexes,
    }


def test_query_performance(db_path: str) -> dict:
    """测试查询性能。

    Args:
        db_path: 数据库文件路径

    Returns:
        性能测试结果字典
    """
    logger.info("=" * 60)
    logger.info("查询性能测试")
    logger.info("=" * 60)

    optimizer = IndexOptimizer(db_path)

    # 定义测试查询
    test_queries = [
        {
            "name": "实验数据时间范围查询",
            "sql": """
                SELECT * FROM data_records
                WHERE experiment_id = 1
                AND timestamp >= datetime('now', '-1 day')
                ORDER BY timestamp DESC
                LIMIT 1000
            """,
        },
        {
            "name": "实验列表查询",
            "sql": """
                SELECT * FROM experiments
                WHERE status = 'completed'
                ORDER BY created_at DESC
                LIMIT 50
            """,
        },
        {
            "name": "审计日志查询",
            "sql": """
                SELECT * FROM audit_logs
                WHERE timestamp >= datetime('now', '-7 days')
                ORDER BY timestamp DESC
                LIMIT 100
            """,
        },
        {
            "name": "用户实验关联查询",
            "sql": """
                SELECT e.*, u.username
                FROM experiments e
                LEFT JOIN users u ON e.user_id = u.id
                WHERE e.status = 'running'
                ORDER BY e.created_at DESC
            """,
        },
    ]

    results = []
    for query in test_queries:
        logger.info(f"\n测试查询: {query['name']}")
        result = optimizer.analyze_query_performance(query["sql"])
        logger.info(f"  执行时间: {result['duration_ms']:.2f}ms")
        logger.info(f"  返回行数: {result['rows_returned']}")
        logger.info(f"  执行计划: {result['plan'][0] if result['plan'] else 'N/A'}")

        results.append(
            {
                "name": query["name"],
                "duration_ms": result["duration_ms"],
                "rows_returned": result["rows_returned"],
                "success": result["success"],
            }
        )

    return {"test_results": results}


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="数据库索引优化迁移脚本")
    parser.add_argument(
        "--db",
        default="experiments.db",
        help="数据库文件路径 (默认: experiments.db)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="分析索引并生成推荐",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="执行索引迁移",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚索引迁移",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="验证索引创建情况",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试查询性能",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只分析不执行（配合--migrate使用）",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="跳过数据库备份",
    )
    parser.add_argument(
        "--output",
        help="输出结果到JSON文件",
    )

    args = parser.parse_args()

    # 检查数据库文件是否存在
    if not os.path.exists(args.db):
        logger.error(f"数据库文件不存在: {args.db}")
        logger.info("提示: 如果是新数据库，请先运行主程序初始化")
        sys.exit(1)

    # 执行操作
    result = {}

    if args.analyze:
        result["analysis"] = analyze_indexes(args.db)

    if args.migrate:
        result["migration"] = migrate_indexes(args.db, args.dry_run, args.skip_backup)

    if args.rollback:
        result["rollback"] = rollback_indexes(args.db)

    if args.verify:
        result["verification"] = verify_indexes(args.db)

    if args.test:
        result["performance_test"] = test_query_performance(args.db)

    # 如果没有指定任何操作，显示帮助
    if not any([args.analyze, args.migrate, args.rollback, args.verify, args.test]):
        parser.print_help()
        return

    # 输出结果到文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"\n结果已保存到: {args.output}")

    logger.info("\n操作完成!")


if __name__ == "__main__":
    main()
