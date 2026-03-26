"""
数据库Schema优化模块

文件名: schema_optimizer.py
路径: backend/core/storage/
功能: 数据库表结构优化、索引管理、约束检查、迁移脚本
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: sqlite3, sqlalchemy

模块内容:
    - SchemaOptimizer: Schema优化器
    - IndexManager: 索引管理器
    - ConstraintChecker: 约束检查器
    - MigrationRunner: 迁移脚本执行器
"""

import hashlib
import json
import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 预定义索引配置（基于项目查询模式）
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
        {
            "name": "ix_data_records_exp_field",
            "columns": ["experiment_id", "field_name"],
            "reason": "实验数据按字段名查询优化",
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
        {
            "name": "ix_experiments_created_desc",
            "columns": ["created_at DESC"],
            "reason": "按创建时间倒序查询实验",
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
        {
            "name": "ix_audit_logs_user_timestamp",
            "columns": ["user_id", "timestamp DESC"],
            "reason": "按用户查询审计日志",
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
        {
            "name": "ix_operation_logs_device_created",
            "columns": ["device_id", "created_at DESC"],
            "reason": "按设备查询操作日志",
        },
    ],
    "device_calibrations": [
        {
            "name": "ix_calibrations_valid_device",
            "columns": ["valid_until", "device_id"],
            "reason": "查询即将过期的校准参数",
        },
        {
            "name": "ix_calibrations_device_valid",
            "columns": ["device_id", "valid_until DESC"],
            "reason": "按设备查询有效校准参数",
        },
    ],
    "device_parameters": [
        {
            "name": "ix_device_params_device_name",
            "columns": ["device_id", "param_name"],
            "reason": "按设备和参数名查询",
        },
    ],
    "devices": [
        {
            "name": "ix_devices_type_status",
            "columns": ["device_type", "status"],
            "reason": "按类型和状态查询设备",
        },
        {
            "name": "ix_devices_status",
            "columns": ["status"],
            "reason": "按状态查询设备",
        },
    ],
}

# 预定义外键约束
PREDEFINED_FOREIGN_KEYS = {
    "data_records": [
        {
            "name": "fk_data_records_experiment",
            "columns": ["experiment_id"],
            "ref_table": "experiments",
            "ref_columns": ["id"],
            "on_delete": "CASCADE",
        },
    ],
    "device_calibrations": [
        {
            "name": "fk_calibrations_device",
            "columns": ["device_id"],
            "ref_table": "devices",
            "ref_columns": ["id"],
            "on_delete": "CASCADE",
        },
    ],
    "device_parameters": [
        {
            "name": "fk_device_params_device",
            "columns": ["device_id"],
            "ref_table": "devices",
            "ref_columns": ["id"],
            "on_delete": "CASCADE",
        },
    ],
    "audit_logs": [
        {
            "name": "fk_audit_logs_user",
            "columns": ["user_id"],
            "ref_table": "users",
            "ref_columns": ["id"],
            "on_delete": "SET NULL",
        },
    ],
}


@dataclass
class IndexInfo:
    """索引信息。

    Attributes:
        name: 索引名称
        table_name: 表名
        columns: 索引列
        unique: 是否唯一索引
        sql: 创建索引的SQL语句
    """

    name: str
    table_name: str
    columns: list[str]
    unique: bool = False
    sql: str = ""


@dataclass
class TableSchema:
    """表结构信息。

    Attributes:
        name: 表名
        columns: 列信息列表
        indexes: 索引信息列表
        foreign_keys: 外键信息列表
        row_count: 行数
    """

    name: str
    columns: list[dict[str, Any]] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)
    foreign_keys: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0


class IndexManager:
    """
    索引管理器。

    管理数据库索引的创建、删除、分析和优化。

    Attributes:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: str) -> None:
        """
        初始化索引管理器。

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        self._lock = Lock()

        logger.info(f"IndexManager initialized for {db_path}")

    def get_all_indexes(self) -> dict[str, list[IndexInfo]]:
        """
        获取所有索引信息。

        Returns:
            表名到索引列表的映射
        """
        indexes = defaultdict(list)

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            # 获取每个表的索引
            for table in tables:
                cursor.execute(f"PRAGMA index_list({table})")
                index_list = cursor.fetchall()

                for idx in index_list:
                    index_name = idx[1]
                    is_unique = bool(idx[2])

                    # 获取索引列
                    cursor.execute(f"PRAGMA index_info({index_name})")
                    columns = [row[2] for row in cursor.fetchall()]

                    indexes[table].append(
                        IndexInfo(
                            name=index_name,
                            table_name=table,
                            columns=columns,
                            unique=is_unique,
                        )
                    )

        return dict(indexes)

    def create_index(
        self,
        table_name: str,
        index_name: str,
        columns: list[str],
        unique: bool = False,
    ) -> bool:
        """
        创建索引。

        Args:
            table_name: 表名
            index_name: 索引名称
            columns: 索引列
            unique: 是否唯一索引

        Returns:
            是否创建成功
        """
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()

                unique_str = "UNIQUE " if unique else ""
                cols_str = ", ".join(columns)
                sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table_name}({cols_str})"

                cursor.execute(sql)
                conn.commit()

            logger.info(f"Index created: {index_name} on {table_name}({cols_str})")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False

    def drop_index(self, index_name: str) -> bool:
        """
        删除索引。

        Args:
            index_name: 索引名称

        Returns:
            是否删除成功
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

    def analyze_index_usage(self, table_name: str) -> dict[str, Any]:
        """
        分析索引使用情况。

        Args:
            table_name: 表名

        Returns:
            索引使用分析结果
        """
        result = {
            "table_name": table_name,
            "indexes": [],
            "recommendations": [],
        }

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取表的索引
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()

            for idx in indexes:
                index_name = idx[1]
                cursor.execute(f"PRAGMA index_info({index_name})")
                columns = [row[2] for row in cursor.fetchall()]

                result["indexes"].append(
                    {
                        "name": index_name,
                        "columns": columns,
                        "unique": bool(idx[2]),
                    }
                )

        return result

    def apply_predefined_indexes(self, dry_run: bool = False) -> dict[str, Any]:
        """
        应用预定义索引。

        Args:
            dry_run: 是否只分析不执行

        Returns:
            应用结果
        """
        result = {
            "created": [],
            "skipped": [],
            "failed": [],
            "dry_run": dry_run,
        }

        # 获取现有索引
        existing_indexes = self.get_all_indexes()
        existing_names = set()
        for table_indexes in existing_indexes.values():
            for idx in table_indexes:
                existing_names.add(idx.name)

        for table_name, indexes in PREDEFINED_INDEXES.items():
            # 检查表是否存在
            if table_name not in existing_indexes:
                logger.warning(f"Table {table_name} does not exist, skipping")
                continue

            for index_config in indexes:
                index_name = index_config["name"]
                columns = index_config["columns"]
                reason = index_config["reason"]

                # 检查索引是否已存在
                if index_name in existing_names:
                    result["skipped"].append(
                        {
                            "index_name": index_name,
                            "table_name": table_name,
                            "reason": "Already exists",
                        }
                    )
                    continue

                # 创建索引
                if dry_run:
                    result["created"].append(
                        {
                            "index_name": index_name,
                            "table_name": table_name,
                            "columns": columns,
                            "reason": reason,
                            "dry_run": True,
                        }
                    )
                else:
                    success = self.create_index(table_name, index_name, columns)
                    if success:
                        result["created"].append(
                            {
                                "index_name": index_name,
                                "table_name": table_name,
                                "columns": columns,
                                "reason": reason,
                            }
                        )
                    else:
                        result["failed"].append(
                            {
                                "index_name": index_name,
                                "table_name": table_name,
                                "columns": columns,
                                "reason": reason,
                            }
                        )

        logger.info(
            f"Index application completed: {len(result['created'])} created, "
            f"{len(result['skipped'])} skipped, {len(result['failed'])} failed"
        )

        return result


class ConstraintChecker:
    """
    约束检查器。

    检查数据库约束的完整性和一致性。

    Attributes:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: str) -> None:
        """
        初始化约束检查器。

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        self._lock = Lock()

        logger.info(f"ConstraintChecker initialized for {db_path}")

    def check_foreign_keys(self) -> dict[str, Any]:
        """
        检查外键约束。

        Returns:
            外键检查结果
        """
        result = {
            "enabled": False,
            "violations": [],
            "foreign_keys": [],
        }

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 检查外键是否启用
            cursor.execute("PRAGMA foreign_keys")
            result["enabled"] = cursor.fetchone()[0] == 1

            # 检查外键违规
            cursor.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()

            for v in violations:
                result["violations"].append(
                    {
                        "table": v[0],
                        "rowid": v[1],
                        "parent": v[2],
                        "fk_index": v[3],
                    }
                )

            # 获取所有外键定义
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"PRAGMA foreign_key_list({table})")
                fks = cursor.fetchall()

                for fk in fks:
                    result["foreign_keys"].append(
                        {
                            "table": table,
                            "id": fk[0],
                            "seq": fk[1],
                            "table_ref": fk[2],
                            "from": fk[3],
                            "to": fk[4],
                            "on_update": fk[5],
                            "on_delete": fk[6],
                            "match": fk[7],
                        }
                    )

        return result

    def check_unique_constraints(self, table_name: str) -> dict[str, Any]:
        """
        检查唯一约束。

        Args:
            table_name: 表名

        Returns:
            唯一约束检查结果
        """
        result = {
            "table_name": table_name,
            "unique_indexes": [],
            "violations": [],
        }

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取唯一索引
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()

            for idx in indexes:
                if idx[2] == 1:  # unique
                    index_name = idx[1]
                    cursor.execute(f"PRAGMA index_info({index_name})")
                    columns = [row[2] for row in cursor.fetchall()]

                    result["unique_indexes"].append(
                        {
                            "name": index_name,
                            "columns": columns,
                        }
                    )

        return result

    def check_not_null_constraints(self, table_name: str) -> dict[str, Any]:
        """
        检查NOT NULL约束。

        Args:
            table_name: 表名

        Returns:
            NOT NULL约束检查结果
        """
        result = {
            "table_name": table_name,
            "not_null_columns": [],
            "violations": [],
        }

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            for col in columns:
                col_name = col[1]
                col_type = col[2]
                not_null = bool(col[3])

                if not_null:
                    result["not_null_columns"].append(
                        {
                            "name": col_name,
                            "type": col_type,
                        }
                    )

                    # 检查是否有NULL值
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL"
                    )
                    null_count = cursor.fetchone()[0]

                    if null_count > 0:
                        result["violations"].append(
                            {
                                "column": col_name,
                                "null_count": null_count,
                            }
                        )

        return result


class SchemaOptimizer:
    """
    Schema优化器。

    分析和优化数据库表结构，提供索引推荐和约束检查。

    Attributes:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: str) -> None:
        """
        初始化Schema优化器。

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        self._index_manager = IndexManager(db_path)
        self._constraint_checker = ConstraintChecker(db_path)
        self._lock = Lock()

        logger.info(f"SchemaOptimizer initialized for {db_path}")

    def get_table_schema(self, table_name: str) -> TableSchema:
        """
        获取表结构信息。

        Args:
            table_name: 表名

        Returns:
            表结构信息
        """
        schema = TableSchema(name=table_name)

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取列信息
            cursor.execute(f"PRAGMA table_info({table_name})")
            for row in cursor.fetchall():
                schema.columns.append(
                    {
                        "cid": row[0],
                        "name": row[1],
                        "type": row[2],
                        "notnull": bool(row[3]),
                        "default": row[4],
                        "primary_key": bool(row[5]),
                    }
                )

            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            schema.row_count = cursor.fetchone()[0]

            # 获取索引
            indexes = self._index_manager.get_all_indexes()
            schema.indexes = indexes.get(table_name, [])

            # 获取外键
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            for row in cursor.fetchall():
                schema.foreign_keys.append(
                    {
                        "id": row[0],
                        "seq": row[1],
                        "table": row[2],
                        "from": row[3],
                        "to": row[4],
                        "on_update": row[5],
                        "on_delete": row[6],
                        "match": row[7],
                    }
                )

        return schema

    def get_all_table_schemas(self) -> dict[str, TableSchema]:
        """
        获取所有表结构信息。

        Returns:
            表名到表结构的映射
        """
        schemas = {}

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            # 获取所有表
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                schemas[table] = self.get_table_schema(table)

        return schemas

    def analyze_schema(self) -> dict[str, Any]:
        """
        分析数据库Schema。

        Returns:
            Schema分析结果
        """
        result = {
            "tables": {},
            "total_tables": 0,
            "total_rows": 0,
            "total_indexes": 0,
            "total_foreign_keys": 0,
            "recommendations": [],
        }

        schemas = self.get_all_table_schemas()

        for table_name, schema in schemas.items():
            result["tables"][table_name] = {
                "columns": len(schema.columns),
                "indexes": len(schema.indexes),
                "foreign_keys": len(schema.foreign_keys),
                "row_count": schema.row_count,
            }

            result["total_tables"] += 1
            result["total_rows"] += schema.row_count
            result["total_indexes"] += len(schema.indexes)
            result["total_foreign_keys"] += len(schema.foreign_keys)

            # 生成优化建议
            # 大表缺少索引
            if schema.row_count > 10000 and len(schema.indexes) < 2:
                result["recommendations"].append(
                    {
                        "table": table_name,
                        "type": "index",
                        "priority": "high",
                        "message": f"大表({schema.row_count}行)索引数量不足，建议添加索引",
                    }
                )

            # 没有主键
            has_pk = any(col["primary_key"] for col in schema.columns)
            if not has_pk:
                result["recommendations"].append(
                    {
                        "table": table_name,
                        "type": "primary_key",
                        "priority": "medium",
                        "message": "表缺少主键，建议添加自增主键",
                    }
                )

        return result

    def optimize_schema(self, dry_run: bool = False) -> dict[str, Any]:
        """
        优化数据库Schema。

        Args:
            dry_run: 是否只分析不执行

        Returns:
            优化结果
        """
        result = {
            "indexes": self._index_manager.apply_predefined_indexes(dry_run),
            "constraints": self._constraint_checker.check_foreign_keys(),
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
        }

        return result

    def get_index_manager(self) -> IndexManager:
        """
        获取索引管理器。

        Returns:
            IndexManager: 索引管理器实例
        """
        return self._index_manager

    def get_constraint_checker(self) -> ConstraintChecker:
        """
        获取约束检查器。

        Returns:
            ConstraintChecker: 约束检查器实例
        """
        return self._constraint_checker


class MigrationRunner:
    """
    数据库迁移脚本执行器。

    管理数据库迁移脚本的版本控制和执行。

    Attributes:
        db_path: 数据库文件路径
        migrations_path: 迁移脚本目录
    """

    def __init__(self, db_path: str, migrations_path: str = "migrations") -> None:
        """
        初始化迁移执行器。

        Args:
            db_path: 数据库文件路径
            migrations_path: 迁移脚本目录
        """
        self._db_path = db_path
        self._migrations_path = Path(migrations_path)
        self._lock = Lock()

        # 确保迁移历史表存在
        self._ensure_migration_table()

        logger.info(
            f"MigrationRunner initialized: db={db_path}, "
            f"migrations={migrations_path}"
        )

    def _ensure_migration_table(self) -> None:
        """确保迁移历史表存在。"""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT,
                    execution_time_ms INTEGER
                )
            """)
            conn.commit()

    def get_applied_migrations(self) -> list[dict[str, Any]]:
        """
        获取已应用的迁移列表。

        Returns:
            已应用的迁移列表
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT version, name, applied_at, checksum, execution_time_ms
                FROM schema_migrations
                ORDER BY applied_at
            """)

            return [
                {
                    "version": row[0],
                    "name": row[1],
                    "applied_at": row[2],
                    "checksum": row[3],
                    "execution_time_ms": row[4],
                }
                for row in cursor.fetchall()
            ]

    def get_pending_migrations(self) -> list[dict[str, Any]]:
        """
        获取待执行的迁移列表。

        Returns:
            待执行的迁移列表
        """
        pending = []

        # 获取已应用的版本
        applied_versions = {m["version"] for m in self.get_applied_migrations()}

        # 扫描迁移目录
        if self._migrations_path.exists():
            for file_path in sorted(self._migrations_path.glob("*.sql")):
                version = file_path.stem

                if version not in applied_versions:
                    content = file_path.read_text(encoding="utf-8")
                    checksum = hashlib.md5(content.encode()).hexdigest()

                    pending.append(
                        {
                            "version": version,
                            "name": file_path.name,
                            "path": str(file_path),
                            "checksum": checksum,
                        }
                    )

        return pending

    def apply_migration(
        self,
        version: str,
        sql: str,
        name: str = "",
        checksum: str = "",
    ) -> dict[str, Any]:
        """
        执行迁移脚本。

        Args:
            version: 迁移版本
            sql: SQL脚本
            name: 迁移名称
            checksum: 校验和

        Returns:
            执行结果
        """
        result = {
            "version": version,
            "success": False,
            "execution_time_ms": 0,
            "error": None,
        }

        start_time = datetime.now()

        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()

                # 执行迁移脚本
                cursor.executescript(sql)

                # 记录迁移历史
                execution_time_ms = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )

                cursor.execute(
                    """
                    INSERT INTO schema_migrations (version, name, checksum, execution_time_ms)
                    VALUES (?, ?, ?, ?)
                    """,
                    (version, name, checksum, execution_time_ms),
                )

                conn.commit()

            result["success"] = True
            result["execution_time_ms"] = execution_time_ms

            logger.info(f"Migration applied: {version} ({execution_time_ms}ms)")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Migration failed: {version} - {e}")

        return result

    def apply_all_pending(self, dry_run: bool = False) -> dict[str, Any]:
        """
        执行所有待执行的迁移。

        Args:
            dry_run: 是否只分析不执行

        Returns:
            执行结果
        """
        result = {
            "applied": [],
            "skipped": [],
            "failed": [],
            "dry_run": dry_run,
        }

        pending = self.get_pending_migrations()

        for migration in pending:
            if dry_run:
                result["skipped"].append(
                    {
                        "version": migration["version"],
                        "name": migration["name"],
                        "reason": "Dry run",
                    }
                )
                continue

            # 读取迁移脚本
            with open(migration["path"], "r", encoding="utf-8") as f:
                sql = f.read()

            # 执行迁移
            migration_result = self.apply_migration(
                version=migration["version"],
                sql=sql,
                name=migration["name"],
                checksum=migration["checksum"],
            )

            if migration_result["success"]:
                result["applied"].append(migration_result)
            else:
                result["failed"].append(migration_result)
                # 遇到错误时停止
                break

        logger.info(
            f"Migration batch completed: {len(result['applied'])} applied, "
            f"{len(result['skipped'])} skipped, {len(result['failed'])} failed"
        )

        return result

    def rollback_migration(self, version: str) -> dict[str, Any]:
        """
        回滚指定迁移（需要迁移脚本包含回滚SQL）。

        Args:
            version: 迁移版本

        Returns:
            回滚结果
        """
        result = {
            "version": version,
            "success": False,
            "error": None,
        }

        # 查找回滚脚本
        rollback_path = self._migrations_path / f"{version}_rollback.sql"

        if not rollback_path.exists():
            result["error"] = f"Rollback script not found: {rollback_path}"
            return result

        try:
            with open(rollback_path, "r", encoding="utf-8") as f:
                sql = f.read()

            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()

                # 执行回滚脚本
                cursor.executescript(sql)

                # 删除迁移记录
                cursor.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (version,),
                )

                conn.commit()

            result["success"] = True
            logger.info(f"Migration rolled back: {version}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Rollback failed: {version} - {e}")

        return result


# ==================== 便捷函数 ====================


def create_schema_optimizer(db_path: str) -> SchemaOptimizer:
    """
    创建Schema优化器的便捷函数。

    Args:
        db_path: 数据库文件路径

    Returns:
        SchemaOptimizer实例
    """
    return SchemaOptimizer(db_path)


def optimize_database_schema(db_path: str, dry_run: bool = False) -> dict[str, Any]:
    """
    优化数据库Schema的便捷函数。

    Args:
        db_path: 数据库文件路径
        dry_run: 是否只分析不执行

    Returns:
        优化结果
    """
    optimizer = SchemaOptimizer(db_path)
    return optimizer.optimize_schema(dry_run)


def apply_database_indexes(db_path: str, dry_run: bool = False) -> dict[str, Any]:
    """
    应用数据库索引的便捷函数。

    Args:
        db_path: 数据库文件路径
        dry_run: 是否只分析不执行

    Returns:
        应用结果
    """
    manager = IndexManager(db_path)
    return manager.apply_predefined_indexes(dry_run)
