-- ============================================================================
-- 数据库迁移SQL脚本 - 添加设备校准、操作日志和实验配置表
--
-- 文件名: 001_add_calibration_logs_configs.sql
-- 路径: migrations/sql/
-- 功能: 为现有数据库添加三个新表
-- 作者: Backend Engineer Agent
-- 创建日期: 2026-03-07
-- 版本: 1.0
--
-- 使用方法:
--     sqlite3 experiments.db < migrations/sql/001_add_calibration_logs_configs.sql
--
-- 注意:
--     - 执行前请备份数据库
--     - 脚本使用 IF NOT EXISTS 避免重复创建
-- ============================================================================

-- ============================================================================
-- 1. 设备校准参数表
-- ============================================================================
-- 功能: 存储设备的校准参数信息
-- 约束: 每个设备的每个参数名唯一
-- ============================================================================

CREATE TABLE IF NOT EXISTS device_calibrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(50) NOT NULL,
    param_name VARCHAR(100) NOT NULL,
    param_value TEXT,
    calibration_date TIMESTAMP,
    valid_until TIMESTAMP,
    UNIQUE(device_id, param_name)
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_device_calibrations_device_id
ON device_calibrations(device_id);

CREATE INDEX IF NOT EXISTS idx_device_calibrations_valid_until
ON device_calibrations(valid_until);

-- ============================================================================
-- 2. 操作日志表
-- ============================================================================
-- 功能: 记录用户对设备和系统的操作历史
-- 关联: user_id 关联 users 表
-- ============================================================================

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    device_id VARCHAR(50),
    operation VARCHAR(100) NOT NULL,
    parameters TEXT,
    result VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_operation_logs_user_id
ON operation_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_operation_logs_device_id
ON operation_logs(device_id);

CREATE INDEX IF NOT EXISTS idx_operation_logs_created_at
ON operation_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_operation_logs_operation
ON operation_logs(operation);

-- ============================================================================
-- 3. 实验配置表
-- ============================================================================
-- 功能: 存储实验的预设配置模板
-- 字段: config_json 存储JSON格式的配置数据
-- ============================================================================

CREATE TABLE IF NOT EXISTS experiment_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    config_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_experiment_configs_name
ON experiment_configs(name);

CREATE INDEX IF NOT EXISTS idx_experiment_configs_created_at
ON experiment_configs(created_at);

-- ============================================================================
-- 验证脚本
-- ============================================================================
-- 检查新表是否创建成功
-- ============================================================================

SELECT 'Migration completed. Checking new tables...' AS status;

SELECT
    name AS table_name,
    'Created' AS status
FROM sqlite_master
WHERE type='table'
AND name IN ('device_calibrations', 'operation_logs', 'experiment_configs')
ORDER BY name;

-- ============================================================================
-- 示例数据插入（可选，用于测试）
-- ============================================================================
-- 取消注释以下语句以插入测试数据
-- ============================================================================

-- INSERT INTO device_calibrations (device_id, param_name, param_value, calibration_date, valid_until)
-- VALUES ('stepper_01', 'steps_per_mm', '1600', datetime('now'), datetime('now', '+1 year'));

-- INSERT INTO operation_logs (operation, result, created_at)
-- VALUES ('database_migration', 'success', datetime('now'));

-- INSERT INTO experiment_configs (name, description, config_json, created_at, updated_at)
-- VALUES ('default_config', '默认实验配置', '{"velocity": 10.0, "acceleration": 1000.0}', datetime('now'), datetime('now'));

-- ============================================================================
-- 迁移完成
-- ============================================================================
SELECT 'Database migration completed successfully!' AS status;
