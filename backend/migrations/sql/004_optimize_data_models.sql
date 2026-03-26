"""
数据库迁移SQL - 数据模型优化

文件名: 004_optimize_data_models.sql
路径: backend/migrations/sql/
功能: 完善数据模型设计、索引优化、性能视图
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0
"""

-- ==================== 1. 数据库表结构优化 ====================

-- 1.1 实验表添加索引
CREATE INDEX IF NOT EXISTS ix_experiments_status_created_desc
ON experiments(status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_experiments_type_status
ON experiments(exp_type, status);

-- 1.2 数据记录表添加复合索引
CREATE INDEX IF NOT EXISTS ix_data_records_exp_timestamp_desc
ON data_records(experiment_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_data_records_exp_position
ON data_records(experiment_id, position_steps);

CREATE INDEX IF NOT EXISTS ix_data_records_timestamp_desc
ON data_records(timestamp DESC);

-- 1.3 设备表添加索引
CREATE INDEX IF NOT EXISTS ix_devices_type_status
ON devices(device_type, status);

-- 1.4 PR路径表添加索引
CREATE INDEX IF NOT EXISTS ix_pr_paths_device_path
ON pr_paths(device_id, path_number);

-- 1.5 设备校准表添加索引
CREATE INDEX IF NOT EXISTS ix_calibrations_valid_device
ON device_calibrations(valid_until, device_id);

-- 1.6 操作日志表添加索引
CREATE INDEX IF NOT EXISTS ix_operation_logs_created_desc
ON operation_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS ix_operation_logs_operation_created
ON operation_logs(operation, created_at DESC);

-- 1.7 操作历史表添加索引
CREATE INDEX IF NOT EXISTS ix_operation_histories_user_created
ON operation_histories(user_id, created_at);

CREATE INDEX IF NOT EXISTS ix_operation_histories_type_created
ON operation_histories(operation_type, created_at);

CREATE INDEX IF NOT EXISTS ix_operation_histories_device_created
ON operation_histories(device_id, created_at);

-- ==================== 2. 数据完整性约束 ====================

-- 2.1 确保实验名称不为空（已在模型中定义）
-- CheckConstraint已定义

-- 2.2 确保设备ID不为空（已在模型中定义）
-- CheckConstraint已定义

-- ==================== 3. 性能优化视图 ====================

-- 3.1 实验统计视图
CREATE VIEW IF NOT EXISTS v_experiment_statistics AS
SELECT 
    e.id AS experiment_id,
    e.exp_name,
    e.status,
    e.created_at,
    e.started_at,
    e.completed_at,
    COUNT(dr.id) AS data_record_count,
    MIN(dr.timestamp) AS first_data_time,
    MAX(dr.timestamp) AS last_data_time
FROM experiments e
LEFT JOIN data_records dr ON e.id = dr.experiment_id
GROUP BY e.id;

-- 3.2 设备状态统计视图
CREATE VIEW IF NOT EXISTS v_device_status_summary AS
SELECT 
    d.id,
    d.device_id,
    d.device_type,
    d.device_name,
    d.status,
    COUNT(pp.id) AS pr_path_count,
    COUNT(dc.id) AS calibration_count
FROM devices d
LEFT JOIN pr_paths pp ON d.device_id = pp.device_id
LEFT JOIN device_calibrations dc ON d.device_id = dc.device_id
GROUP BY d.id;

-- 3.3 最近实验数据视图
CREATE VIEW IF NOT EXISTS v_recent_experiments AS
SELECT 
    id,
    exp_name,
    exp_type,
    status,
    created_at,
    started_at,
    completed_at
FROM experiments
ORDER BY created_at DESC
LIMIT 100;

-- ==================== 4. 数据清理优化 ====================

-- 4.1 创建数据归档日志表
CREATE TABLE IF NOT EXISTS data_archive_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    archive_type TEXT NOT NULL CHECK(archive_type IN ('hdf5', 'json', 'csv')),
    archive_path TEXT NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    archive_size_bytes INTEGER NOT NULL DEFAULT 0,
    archived_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_archive_logs_experiment
ON data_archive_logs(experiment_id);

CREATE INDEX IF NOT EXISTS ix_archive_logs_archived_at
ON data_archive_logs(archived_at DESC);

-- 4.2 创建数据库优化日志表
CREATE TABLE IF NOT EXISTS database_optimization_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    optimization_type TEXT NOT NULL,
    description TEXT,
    duration_ms REAL NOT NULL,
    records_affected INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    optimized_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_optimization_logs_type
ON database_optimization_logs(optimization_type);

CREATE INDEX IF NOT EXISTS ix_optimization_logs_optimized_at
ON database_optimization_logs(optimized_at DESC);

-- ==================== 5. 缓存统计表 ====================

-- 5.1 创建缓存统计表
CREATE TABLE IF NOT EXISTS cache_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_type TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0,
    miss_count INTEGER NOT NULL DEFAULT 0,
    last_hit_at DATETIME,
    last_miss_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_cache_statistics_type
ON cache_statistics(cache_type);

CREATE INDEX IF NOT EXISTS ix_cache_statistics_key
ON cache_statistics(cache_key);

-- ==================== 6. 批量写入统计表 ====================

-- 6.1 创建批量写入统计表
CREATE TABLE IF NOT EXISTS batch_write_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    batch_size INTEGER NOT NULL,
    write_duration_ms REAL NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    written_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_batch_write_statistics_table
ON batch_write_statistics(table_name);

CREATE INDEX IF NOT EXISTS ix_batch_write_statistics_written_at
ON batch_write_statistics(written_at DESC);

-- ==================== 7. 数据库配置表 ====================

-- 7.1 创建数据库配置表
CREATE TABLE IF NOT EXISTS database_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7.2 插入默认配置
INSERT OR IGNORE INTO database_config (config_key, config_value, description)
VALUES 
    ('journal_mode', 'WAL', 'SQLite日志模式'),
    ('synchronous', 'NORMAL', 'SQLite同步模式'),
    ('cache_size_mb', '64', 'SQLite缓存大小（MB）'),
    ('temp_store', 'MEMORY', 'SQLite临时存储位置'),
    ('busy_timeout_ms', '30000', 'SQLite忙等待超时（毫秒）'),
    ('batch_write_size', '1000', '批量写入大小'),
    ('cache_ttl_seconds', '300', '缓存过期时间（秒）'),
    ('hdf5_chunk_size', '10000', 'HDF5分块大小'),
    ('hdf5_compression_level', '6', 'HDF5压缩级别');

-- ==================== 8. 性能监控表 ====================

-- 8.1 创建查询性能监控表
CREATE TABLE IF NOT EXISTS query_performance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL,
    query_sql TEXT NOT NULL,
    table_name TEXT,
    duration_ms REAL NOT NULL,
    rows_affected INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_query_performance_hash
ON query_performance_logs(query_hash);

CREATE INDEX IF NOT EXISTS ix_query_performance_executed_at
ON query_performance_logs(executed_at DESC);

CREATE INDEX IF NOT EXISTS ix_query_performance_table
ON query_performance_logs(table_name);

-- 8.2 创建慢查询日志表
CREATE TABLE IF NOT EXISTS slow_query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_sql TEXT NOT NULL,
    duration_ms REAL NOT NULL,
    threshold_ms REAL NOT NULL,
    executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_slow_query_logs_executed_at
ON slow_query_logs(executed_at DESC);

-- ==================== 9. 数据完整性检查 ====================

-- 9.1 创建数据完整性检查日志表
CREATE TABLE IF NOT EXISTS integrity_check_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type TEXT NOT NULL,
    table_name TEXT,
    check_result TEXT NOT NULL,
    issues_found INTEGER DEFAULT 0,
    issues_detail TEXT,
    checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_integrity_check_logs_type
ON integrity_check_logs(check_type);

CREATE INDEX IF NOT EXISTS ix_integrity_check_logs_checked_at
ON integrity_check_logs(checked_at DESC);
