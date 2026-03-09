"""
数据库迁移脚本 - 添加字段约束和索引优化

文件名: add_constraints_indexes.py
路径: migrations/
功能: 为现有表添加CHECK约束、索引优化和外键级联
作者: Backend Engineer Agent
创建日期: 2026-03-07
版本: 1.0

使用方法:
    python migrations/add_constraints_indexes.py

注意:
    - 执行前请务必备份数据库
    - SQLite不支持ALTER TABLE ADD CONSTRAINT
    - 此脚本通过重建表的方式添加约束
"""

import logging
import os
import shutil
import sys
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

VALID_USER_ROLES = ("admin", "operator", "viewer")
VALID_DEVICE_STATUSES = ("offline", "online", "busy", "error", "maintenance")
VALID_EXPERIMENT_STATUSES = ("pending", "running", "completed", "failed", "cancelled")
VALID_OPERATION_CATEGORIES = ("device", "experiment", "system", "calibration", "config")
VALID_REQUEST_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


def backup_database(db_path: str) -> str:
    """
    备份数据库文件

    Args:
        db_path: 数据库文件路径

    Returns:
        str: 备份文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    logger.info(f"数据库已备份到: {backup_path}")
    return backup_path


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


def migrate_users_table(conn):
    """
    迁移用户表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 users 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'operator' NOT NULL,
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            CHECK (role IN ('admin', 'operator', 'viewer')),
            CHECK (LENGTH(username) >= 3),
            CHECK (LENGTH(password_hash) >= 32)
        )
    """))

    conn.execute(text("""
        INSERT INTO users_new (id, username, password_hash, role, email, created_at, last_login, is_active)
        SELECT id, username, password_hash, 
               CASE WHEN role IN ('admin', 'operator', 'viewer') THEN role ELSE 'operator' END,
               email, created_at, last_login, 
               CASE WHEN is_active IS NULL THEN 1 ELSE is_active END
        FROM users
    """))

    conn.execute(text("DROP TABLE users"))
    conn.execute(text("ALTER TABLE users_new RENAME TO users"))

    # 创建索引
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_username ON users(username)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_role_active ON users(role, is_active)"))

    logger.info("  users 表迁移完成")


def migrate_devices_table(conn):
    """
    迁移设备表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 devices 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS devices_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id VARCHAR(50) UNIQUE NOT NULL,
            device_type VARCHAR(50) NOT NULL,
            device_name VARCHAR(100),
            connection_params TEXT,
            status VARCHAR(20) DEFAULT 'offline' NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CHECK (status IN ('offline', 'online', 'busy', 'error', 'maintenance')),
            CHECK (LENGTH(device_id) >= 1)
        )
    """))

    conn.execute(text("""
        INSERT INTO devices_new (id, device_id, device_type, device_name, connection_params, status, created_at)
        SELECT id, device_id, device_type, device_name, connection_params,
               CASE WHEN status IN ('offline', 'online', 'busy', 'error', 'maintenance') 
                    THEN status ELSE 'offline' END,
               created_at
        FROM devices
    """))

    conn.execute(text("DROP TABLE devices"))
    conn.execute(text("ALTER TABLE devices_new RENAME TO devices"))

    # 创建索引
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_devices_device_id ON devices(device_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_devices_device_type ON devices(device_type)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_devices_status ON devices(status)"))
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_devices_type_status ON devices(device_type, status)")
    )

    logger.info("  devices 表迁移完成")


def migrate_experiments_table(conn):
    """
    迁移实验表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 experiments 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS experiments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exp_name VARCHAR(100) NOT NULL,
            exp_type VARCHAR(50),
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            sequence_config TEXT,
            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            data_file_path VARCHAR(255),
            experiment_metadata TEXT,
            CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
            CHECK (LENGTH(exp_name) >= 1)
        )
    """))

    conn.execute(text("""
        INSERT INTO experiments_new (id, exp_name, exp_type, user_id, sequence_config, status, 
                                     created_at, started_at, completed_at, data_file_path, experiment_metadata)
        SELECT id, exp_name, exp_type, user_id, sequence_config,
               CASE WHEN status IN ('pending', 'running', 'completed', 'failed', 'cancelled') 
                    THEN status ELSE 'pending' END,
               created_at, started_at, completed_at, data_file_path, experiment_metadata
        FROM experiments
    """))

    conn.execute(text("DROP TABLE experiments"))
    conn.execute(text("ALTER TABLE experiments_new RENAME TO experiments"))

    # 创建索引
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_experiments_exp_name ON experiments(exp_name)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_experiments_exp_type ON experiments(exp_type)")
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_experiments_user_id ON experiments(user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_experiments_status ON experiments(status)"))
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_experiments_created_at ON experiments(created_at)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_experiments_user_status ON experiments(user_id, status)"
        )
    )

    logger.info("  experiments 表迁移完成")


def migrate_data_records_table(conn):
    """
    迁移数据记录表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 data_records 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS data_records_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            position_steps INTEGER,
            position_mm REAL,
            field_value REAL,
            current_value REAL,
            temperature REAL,
            extra_data TEXT
        )
    """))

    conn.execute(text("""
        INSERT INTO data_records_new (id, experiment_id, timestamp, position_steps, position_mm, 
                                       field_value, current_value, temperature, extra_data)
        SELECT id, experiment_id, 
               COALESCE(timestamp, CURRENT_TIMESTAMP),
               position_steps, position_mm, field_value, current_value, temperature, extra_data
        FROM data_records
    """))

    conn.execute(text("DROP TABLE data_records"))
    conn.execute(text("ALTER TABLE data_records_new RENAME TO data_records"))

    # 创建索引
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_data_records_experiment_id ON data_records(experiment_id)"
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_data_records_timestamp ON data_records(timestamp)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_data_records_exp_timestamp ON data_records(experiment_id, timestamp)"
        )
    )

    logger.info("  data_records 表迁移完成")


def migrate_pr_paths_table(conn):
    """
    迁移PR路径表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 pr_paths 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS pr_paths_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id VARCHAR(50) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
            path_number INTEGER NOT NULL,
            mode INTEGER DEFAULT 1 NOT NULL,
            position_high INTEGER DEFAULT 0 NOT NULL,
            position_low INTEGER DEFAULT 0 NOT NULL,
            velocity INTEGER DEFAULT 1000 NOT NULL,
            accel_time INTEGER DEFAULT 100 NOT NULL,
            decel_time INTEGER DEFAULT 100 NOT NULL,
            dwell_time INTEGER DEFAULT 0 NOT NULL,
            special_param INTEGER DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CHECK (path_number >= 0 AND path_number <= 15),
            CHECK (velocity > 0),
            CHECK (accel_time >= 0),
            CHECK (decel_time >= 0),
            UNIQUE(device_id, path_number)
        )
    """))

    conn.execute(text("""
        INSERT INTO pr_paths_new (id, device_id, path_number, mode, position_high, position_low, 
                                   velocity, accel_time, decel_time, dwell_time, special_param, 
                                   created_at, updated_at)
        SELECT id, device_id, 
               CASE WHEN path_number BETWEEN 0 AND 15 THEN path_number ELSE 0 END,
               COALESCE(mode, 1),
               COALESCE(position_high, 0),
               COALESCE(position_low, 0),
               CASE WHEN velocity > 0 THEN velocity ELSE 1000 END,
               CASE WHEN accel_time >= 0 THEN accel_time ELSE 100 END,
               CASE WHEN decel_time >= 0 THEN decel_time ELSE 100 END,
               COALESCE(dwell_time, 0),
               COALESCE(special_param, 0),
               COALESCE(created_at, CURRENT_TIMESTAMP),
               COALESCE(updated_at, CURRENT_TIMESTAMP)
        FROM pr_paths
    """))

    conn.execute(text("DROP TABLE pr_paths"))
    conn.execute(text("ALTER TABLE pr_paths_new RENAME TO pr_paths"))

    # 创建索引
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pr_paths_device_id ON pr_paths(device_id)"))
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_pr_paths_device_path ON pr_paths(device_id, path_number)"
        )
    )

    logger.info("  pr_paths 表迁移完成")


def migrate_audit_logs_table(conn):
    """
    迁移审计日志表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 audit_logs 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audit_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            device_id VARCHAR(50) REFERENCES devices(device_id) ON DELETE SET NULL,
            operation_type VARCHAR(50) NOT NULL,
            operation_category VARCHAR(30) NOT NULL,
            request_method VARCHAR(10) NOT NULL,
            request_path VARCHAR(255) NOT NULL,
            request_params TEXT,
            response_status INTEGER,
            response_message TEXT,
            ip_address VARCHAR(45),
            user_agent VARCHAR(255),
            duration_ms INTEGER,
            extra_data TEXT,
            CHECK (operation_category IN ('device', 'experiment', 'system', 'calibration', 'config')),
            CHECK (request_method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')),
            CHECK (response_status >= 100 AND response_status < 600 OR response_status IS NULL),
            CHECK (duration_ms >= 0 OR duration_ms IS NULL)
        )
    """))

    conn.execute(text("""
        INSERT INTO audit_logs_new (id, timestamp, user_id, device_id, operation_type, 
                                     operation_category, request_method, request_path, 
                                     request_params, response_status, response_message, 
                                     ip_address, user_agent, duration_ms, extra_data)
        SELECT id, COALESCE(timestamp, CURRENT_TIMESTAMP), user_id, device_id, operation_type,
               CASE WHEN operation_category IN ('device', 'experiment', 'system', 'calibration', 'config') 
                    THEN operation_category ELSE 'system' END,
               CASE WHEN request_method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH') 
                    THEN request_method ELSE 'GET' END,
               request_path, request_params, response_status, response_message, 
               ip_address, user_agent, duration_ms, extra_data
        FROM audit_logs
    """))

    conn.execute(text("DROP TABLE audit_logs"))
    conn.execute(text("ALTER TABLE audit_logs_new RENAME TO audit_logs"))

    # 创建索引
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs(timestamp)")
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id)"))
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_audit_logs_device_id ON audit_logs(device_id)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_operation_type ON audit_logs(operation_type)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_operation_category ON audit_logs(operation_category)"
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_audit_logs_request_path ON audit_logs(request_path)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_response_status ON audit_logs(response_status)"
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_audit_logs_ip_address ON audit_logs(ip_address)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_timestamp ON audit_logs(user_id, timestamp)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_device_timestamp ON audit_logs(device_id, timestamp)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_category_timestamp ON audit_logs(operation_category, timestamp)"
        )
    )

    logger.info("  audit_logs 表迁移完成")


def migrate_operation_logs_table(conn):
    """
    迁移操作日志表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 operation_logs 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS operation_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            device_id VARCHAR(50) REFERENCES devices(device_id) ON DELETE SET NULL,
            operation VARCHAR(100) NOT NULL,
            parameters TEXT,
            result VARCHAR(20),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CHECK (result IN ('success', 'failed', 'pending') OR result IS NULL)
        )
    """))

    conn.execute(text("""
        INSERT INTO operation_logs_new (id, user_id, device_id, operation, parameters, 
                                         result, error_message, created_at)
        SELECT id, user_id, device_id, operation, parameters, result, error_message, 
               COALESCE(created_at, CURRENT_TIMESTAMP)
        FROM operation_logs
    """))

    conn.execute(text("DROP TABLE operation_logs"))
    conn.execute(text("ALTER TABLE operation_logs_new RENAME TO operation_logs"))

    # 创建索引
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_operation_logs_user_id ON operation_logs(user_id)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_operation_logs_device_id ON operation_logs(device_id)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_operation_logs_operation ON operation_logs(operation)")
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_operation_logs_result ON operation_logs(result)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_operation_logs_created_at ON operation_logs(created_at)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_operation_logs_user_created ON operation_logs(user_id, created_at)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_operation_logs_device_created ON operation_logs(device_id, created_at)"
        )
    )

    logger.info("  operation_logs 表迁移完成")


def migrate_device_calibrations_table(conn):
    """
    迁移设备校准表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 device_calibrations 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS device_calibrations_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id VARCHAR(50) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
            param_name VARCHAR(100) NOT NULL,
            param_value TEXT,
            calibration_date TIMESTAMP,
            valid_until TIMESTAMP,
            CHECK (LENGTH(device_id) >= 1),
            CHECK (LENGTH(param_name) >= 1),
            UNIQUE(device_id, param_name)
        )
    """))

    conn.execute(text("""
        INSERT INTO device_calibrations_new (id, device_id, param_name, param_value, 
                                              calibration_date, valid_until)
        SELECT id, device_id, param_name, param_value, calibration_date, valid_until
        FROM device_calibrations
    """))

    conn.execute(text("DROP TABLE device_calibrations"))
    conn.execute(text("ALTER TABLE device_calibrations_new RENAME TO device_calibrations"))

    # 创建索引
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_calibrations_device_id ON device_calibrations(device_id)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_calibrations_valid_until ON device_calibrations(valid_until)"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_calibrations_device_param ON device_calibrations(device_id, param_name)"
        )
    )

    logger.info("  device_calibrations 表迁移完成")


def migrate_experiment_configs_table(conn):
    """
    迁移实验配置表 - 添加约束和索引

    Args:
        conn: 数据库连接
    """
    logger.info("迁移 experiment_configs 表...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS experiment_configs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            config_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CHECK (LENGTH(name) >= 1),
            CHECK (LENGTH(config_json) >= 2)
        )
    """))

    conn.execute(text("""
        INSERT INTO experiment_configs_new (id, name, description, config_json, created_at, updated_at)
        SELECT id, name, description, config_json, 
               COALESCE(created_at, CURRENT_TIMESTAMP),
               COALESCE(updated_at, CURRENT_TIMESTAMP)
        FROM experiment_configs
    """))

    conn.execute(text("DROP TABLE experiment_configs"))
    conn.execute(text("ALTER TABLE experiment_configs_new RENAME TO experiment_configs"))

    # 创建索引
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_configs_name ON experiment_configs(name)"))

    logger.info("  experiment_configs 表迁移完成")


def migrate_database(db_path: str = "experiments.db", skip_backup: bool = False):
    """
    执行数据库迁移

    Args:
        db_path: 数据库文件路径
        skip_backup: 是否跳过备份
    """
    logger.info("=" * 60)
    logger.info("开始数据库迁移: 添加约束和索引")
    logger.info(f"数据库路径: {db_path}")
    logger.info("=" * 60)

    # 备份数据库
    if not skip_backup:
        backup_path = backup_database(db_path)
        logger.info(f"如需回滚,请将 {backup_path} 重命名为 {db_path}")

    # 创建数据库引擎
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    # 定义迁移顺序（考虑外键依赖）
    migrations = [
        ("users", migrate_users_table),
        ("devices", migrate_devices_table),
        ("experiments", migrate_experiments_table),
        ("data_records", migrate_data_records_table),
        ("pr_paths", migrate_pr_paths_table),
        ("audit_logs", migrate_audit_logs_table),
        ("operation_logs", migrate_operation_logs_table),
        ("device_calibrations", migrate_device_calibrations_table),
        ("experiment_configs", migrate_experiment_configs_table),
    ]

    migrated_tables = []
    skipped_tables = []

    with engine.connect() as conn:
        for table_name, migrate_func in migrations:
            if check_table_exists(engine, table_name):
                try:
                    migrate_func(conn)
                    migrated_tables.append(table_name)
                except Exception as e:
                    logger.error(f"  迁移 {table_name} 表失败: {e}")
                    raise
            else:
                logger.info(f"表 {table_name} 不存在,跳过")
                skipped_tables.append(table_name)

        # 提交所有更改
        conn.commit()

    # 输出迁移结果
    logger.info("=" * 60)
    logger.info("迁移结果汇总:")
    logger.info(f"  已迁移表: {len(migrated_tables)} 个")
    for table in migrated_tables:
        logger.info(f"    - {table}")
    logger.info(f"  跳过表: {len(skipped_tables)} 个")
    for table in skipped_tables:
        logger.info(f"    - {table}")
    logger.info("=" * 60)

    # 验证索引
    logger.info("验证索引创建...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT m.name AS table_name, il.name AS index_name
            FROM sqlite_master m, pragma_index_list(m.name) il
            WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
            ORDER BY m.name, il.name
        """))
        indexes = result.fetchall()
        logger.info(f"共创建 {len(indexes)} 个索引")

    logger.info("数据库迁移完成!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移脚本 - 添加约束和索引")
    parser.add_argument(
        "--db", default="experiments.db", help="数据库文件路径 (默认: experiments.db)"
    )
    parser.add_argument("--skip-backup", action="store_true", help="跳过数据库备份")

    args = parser.parse_args()

    # 检查数据库文件是否存在
    if not os.path.exists(args.db):
        logger.error(f"数据库文件不存在: {args.db}")
        logger.info("提示: 如果是新数据库,请先运行主程序初始化")
        sys.exit(1)

    try:
        migrate_database(args.db, args.skip_backup)
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        logger.error("请使用备份文件恢复数据库")
        sys.exit(1)
