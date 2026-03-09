"""
数据库迁移脚本 - 添加设备校准、操作日志和实验配置表

文件名: add_calibration_logs_configs.py
路径: migrations/
功能: 为现有数据库添加三个新表
作者: Backend Engineer Agent
创建日期: 2026-03-07
版本: 1.0

使用方法:
    python migrations/add_calibration_logs_configs.py

注意:
    - 执行前请备份数据库
    - 脚本会自动检测表是否存在,避免重复创建
"""

import logging
import os
import sys
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import DeviceCalibration, ExperimentConfig, OperationLog

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_table_exists(engine, table_name: str) -> bool:
    """
    检查表是否存在

    Args:
        engine: SQLAlchemy引擎
        table_name: 表名

    Returns:
        bool: 表是否存在
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
            {"table_name": table_name},
        )
        return result.fetchone() is not None


def migrate_database(db_path: str = "experiments.db"):
    """
    执行数据库迁移

    Args:
        db_path: 数据库文件路径
    """
    logger.info(f"开始数据库迁移: {db_path}")

    # 创建数据库引擎
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    # 检查并创建新表
    tables_to_create = {
        "device_calibrations": DeviceCalibration,
        "operation_logs": OperationLog,
        "experiment_configs": ExperimentConfig,
    }

    created_tables = []
    skipped_tables = []

    for table_name, model_class in tables_to_create.items():
        if check_table_exists(engine, table_name):
            logger.info(f"表 {table_name} 已存在,跳过创建")
            skipped_tables.append(table_name)
        else:
            # 创建单个表
            model_class.__table__.create(engine, checkfirst=True)
            logger.info(f"表 {table_name} 创建成功")
            created_tables.append(table_name)

    # 验证表结构
    logger.info("=" * 60)
    logger.info("迁移结果汇总:")
    logger.info(f"  新建表: {len(created_tables)} 个")
    for table in created_tables:
        logger.info(f"    - {table}")
    logger.info(f"  跳过表: {len(skipped_tables)} 个")
    for table in skipped_tables:
        logger.info(f"    - {table}")
    logger.info("=" * 60)

    # 验证新表是否可访问
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 测试插入和查询
        logger.info("验证新表功能...")

        # 测试设备校准表
        if "device_calibrations" in created_tables:
            test_calibration = DeviceCalibration(
                device_id="test_device",
                param_name="test_param",
                param_value="test_value",
                calibration_date=datetime.now(),
            )
            session.add(test_calibration)
            session.commit()
            session.delete(test_calibration)
            session.commit()
            logger.info("  ✓ device_calibrations 表功能正常")

        # 测试操作日志表
        if "operation_logs" in created_tables:
            test_log = OperationLog(
                operation="test_operation",
                result="success",
            )
            session.add(test_log)
            session.commit()
            session.delete(test_log)
            session.commit()
            logger.info("  ✓ operation_logs 表功能正常")

        # 测试实验配置表
        if "experiment_configs" in created_tables:
            test_config = ExperimentConfig(
                name="test_config",
                config_json='{"test": "value"}',
            )
            session.add(test_config)
            session.commit()
            session.delete(test_config)
            session.commit()
            logger.info("  ✓ experiment_configs 表功能正常")

    except Exception as e:
        logger.error(f"验证失败: {e}")
        session.rollback()
        raise
    finally:
        session.close()

    logger.info("数据库迁移完成!")


def rollback_migration(db_path: str = "experiments.db"):
    """
    回滚迁移（删除新创建的表）

    Args:
        db_path: 数据库文件路径

    注意:
        此操作会删除表及数据,请谨慎使用
    """
    logger.warning("警告: 即将删除新创建的表,数据将丢失!")
    logger.warning(
        "请确认是否继续 (yes/no): ",
    )

    confirmation = input().strip().lower()
    if confirmation != "yes":
        logger.info("回滚操作已取消")
        return

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    tables_to_drop = [
        "device_calibrations",
        "operation_logs",
        "experiment_configs",
    ]

    with engine.connect() as conn:
        for table_name in tables_to_drop:
            if check_table_exists(engine, table_name):
                conn.execute(text(f"DROP TABLE {table_name}"))
                conn.commit()
                logger.info(f"表 {table_name} 已删除")
            else:
                logger.info(f"表 {table_name} 不存在,跳过")

    logger.info("回滚完成")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移脚本")
    parser.add_argument(
        "--db", default="experiments.db", help="数据库文件路径 (默认: experiments.db)"
    )
    parser.add_argument("--rollback", action="store_true", help="回滚迁移（删除新表）")

    args = parser.parse_args()

    # 检查数据库文件是否存在
    if not os.path.exists(args.db):
        logger.error(f"数据库文件不存在: {args.db}")
        logger.info("提示: 如果是新数据库,请先运行主程序初始化")
        sys.exit(1)

    try:
        if args.rollback:
            rollback_migration(args.db)
        else:
            migrate_database(args.db)
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        sys.exit(1)
