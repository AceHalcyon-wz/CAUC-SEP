-- ============================================================================
-- 数据库迁移SQL脚本 - 添加字段约束和索引优化
--
-- 文件名: 002_add_constraints_indexes.sql
-- 路径: migrations/sql/
-- 功能: 为现有表添加CHECK约束、索引优化和外键级联
-- 作者: Backend Engineer Agent
-- 创建日期: 2026-03-07
-- 版本: 1.0
--
-- 使用方法:
--     sqlite3 experiments.db < migrations/sql/002_add_constraints_indexes.sql
--
-- 注意:
--     - SQLite不支持ALTER TABLE ADD CONSTRAINT
--     - 此脚本通过重建表的方式添加约束
--     - 执行前请务必备份数据库
-- ============================================================================

-- ============================================================================
-- 说明: SQLite的限制
-- ============================================================================
-- SQLite不支持以下操作:
-- 1. ALTER TABLE ADD CONSTRAINT (CHECK约束)
-- 2. ALTER TABLE ADD FOREIGN KEY ON DELETE CASCADE
-- 3. 直接修改列的NOT NULL属性
--
-- 解决方案: 使用"重建表"模式:
-- 1. 创建新表(带约束)
-- 2. 复制数据
-- 3. 删除旧表
-- 4. 重命名新表
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- 1. 用户表(users) - 添加约束和索引
-- ============================================================================

-- 创建带约束的新用户表
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
);

-- 复制数据
INSERT INTO users_new (id, username, password_hash, role, email, created_at, last_login, is_active)
SELECT id, username, password_hash, 
       CASE WHEN role IN ('admin', 'operator', 'viewer') THEN role ELSE 'operator' END,
       email, created_at, last_login, 
       CASE WHEN is_active IS NULL THEN 1 ELSE is_active END
FROM users;

-- 删除旧表
DROP TABLE users;

-- 重命名新表
ALTER TABLE users_new RENAME TO users;

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
CREATE INDEX IF NOT EXISTS ix_users_role_active ON users(role, is_active);

-- ============================================================================
-- 2. 设备表(devices) - 添加约束和索引
-- ============================================================================

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
);

INSERT INTO devices_new (id, device_id, device_type, device_name, connection_params, status, created_at)
SELECT id, device_id, device_type, device_name, connection_params,
       CASE WHEN status IN ('offline', 'online', 'busy', 'error', 'maintenance') THEN status ELSE 'offline' END,
       created_at
FROM devices;

DROP TABLE devices;
ALTER TABLE devices_new RENAME TO devices;

CREATE INDEX IF NOT EXISTS ix_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS ix_devices_device_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS ix_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS ix_devices_type_status ON devices(device_type, status);

-- ============================================================================
-- 3. 实验表(experiments) - 添加约束和索引
-- ============================================================================

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
);

INSERT INTO experiments_new (id, exp_name, exp_type, user_id, sequence_config, status, created_at, started_at, completed_at, data_file_path, experiment_metadata)
SELECT id, exp_name, exp_type, user_id, sequence_config,
       CASE WHEN status IN ('pending', 'running', 'completed', 'failed', 'cancelled') THEN status ELSE 'pending' END,
       created_at, started_at, completed_at, data_file_path, experiment_metadata
FROM experiments;

DROP TABLE experiments;
ALTER TABLE experiments_new RENAME TO experiments;

CREATE INDEX IF NOT EXISTS ix_experiments_exp_name ON experiments(exp_name);
CREATE INDEX IF NOT EXISTS ix_experiments_exp_type ON experiments(exp_type);
CREATE INDEX IF NOT EXISTS ix_experiments_user_id ON experiments(user_id);
CREATE INDEX IF NOT EXISTS ix_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS ix_experiments_created_at ON experiments(created_at);
CREATE INDEX IF NOT EXISTS ix_experiments_user_status ON experiments(user_id, status);

-- ============================================================================
-- 4. 数据记录表(data_records) - 添加约束和索引
-- ============================================================================

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
);

INSERT INTO data_records_new (id, experiment_id, timestamp, position_steps, position_mm, field_value, current_value, temperature, extra_data)
SELECT id, experiment_id, 
       COALESCE(timestamp, CURRENT_TIMESTAMP),
       position_steps, position_mm, field_value, current_value, temperature, extra_data
FROM data_records;

DROP TABLE data_records;
ALTER TABLE data_records_new RENAME TO data_records;

CREATE INDEX IF NOT EXISTS ix_data_records_experiment_id ON data_records(experiment_id);
CREATE INDEX IF NOT EXISTS ix_data_records_timestamp ON data_records(timestamp);
CREATE INDEX IF NOT EXISTS ix_data_records_exp_timestamp ON data_records(experiment_id, timestamp);

-- ============================================================================
-- 5. PR路径表(pr_paths) - 添加约束和索引
-- ============================================================================

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
);

INSERT INTO pr_paths_new (id, device_id, path_number, mode, position_high, position_low, velocity, accel_time, decel_time, dwell_time, special_param, created_at, updated_at)
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
FROM pr_paths;

DROP TABLE pr_paths;
ALTER TABLE pr_paths_new RENAME TO pr_paths;

CREATE INDEX IF NOT EXISTS ix_pr_paths_device_id ON pr_paths(device_id);
CREATE INDEX IF NOT EXISTS ix_pr_paths_device_path ON pr_paths(device_id, path_number);

-- ============================================================================
-- 6. 审计日志表(audit_logs) - 添加约束和索引
-- ============================================================================

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
);

INSERT INTO audit_logs_new (id, timestamp, user_id, device_id, operation_type, operation_category, request_method, request_path, request_params, response_status, response_message, ip_address, user_agent, duration_ms, extra_data)
SELECT id, COALESCE(timestamp, CURRENT_TIMESTAMP), user_id, device_id, operation_type,
       CASE WHEN operation_category IN ('device', 'experiment', 'system', 'calibration', 'config') THEN operation_category ELSE 'system' END,
       CASE WHEN request_method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH') THEN request_method ELSE 'GET' END,
       request_path, request_params, response_status, response_message, ip_address, user_agent, duration_ms, extra_data
FROM audit_logs;

DROP TABLE audit_logs;
ALTER TABLE audit_logs_new RENAME TO audit_logs;

CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_device_id ON audit_logs(device_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_operation_type ON audit_logs(operation_type);
CREATE INDEX IF NOT EXISTS ix_audit_logs_operation_category ON audit_logs(operation_category);
CREATE INDEX IF NOT EXISTS ix_audit_logs_request_path ON audit_logs(request_path);
CREATE INDEX IF NOT EXISTS ix_audit_logs_response_status ON audit_logs(response_status);
CREATE INDEX IF NOT EXISTS ix_audit_logs_ip_address ON audit_logs(ip_address);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_timestamp ON audit_logs(user_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_logs_device_timestamp ON audit_logs(device_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_logs_category_timestamp ON audit_logs(operation_category, timestamp);

-- ============================================================================
-- 7. 操作日志表(operation_logs) - 添加约束和索引
-- ============================================================================

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
);

INSERT INTO operation_logs_new (id, user_id, device_id, operation, parameters, result, error_message, created_at)
SELECT id, user_id, device_id, operation, parameters,
       CASE WHEN result IN ('success', 'failed', 'pending') THEN result ELSE result END,
       error_message, COALESCE(created_at, CURRENT_TIMESTAMP)
FROM operation_logs;

DROP TABLE operation_logs;
ALTER TABLE operation_logs_new RENAME TO operation_logs;

CREATE INDEX IF NOT EXISTS ix_operation_logs_user_id ON operation_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_operation_logs_device_id ON operation_logs(device_id);
CREATE INDEX IF NOT EXISTS ix_operation_logs_operation ON operation_logs(operation);
CREATE INDEX IF NOT EXISTS ix_operation_logs_result ON operation_logs(result);
CREATE INDEX IF NOT EXISTS ix_operation_logs_created_at ON operation_logs(created_at);
CREATE INDEX IF NOT EXISTS ix_operation_logs_user_created ON operation_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_operation_logs_device_created ON operation_logs(device_id, created_at);

-- ============================================================================
-- 8. 设备校准表(device_calibrations) - 添加约束和索引
-- ============================================================================

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
);

INSERT INTO device_calibrations_new (id, device_id, param_name, param_value, calibration_date, valid_until)
SELECT id, device_id, param_name, param_value, calibration_date, valid_until
FROM device_calibrations;

DROP TABLE device_calibrations;
ALTER TABLE device_calibrations_new RENAME TO device_calibrations;

CREATE INDEX IF NOT EXISTS ix_calibrations_device_id ON device_calibrations(device_id);
CREATE INDEX IF NOT EXISTS ix_calibrations_valid_until ON device_calibrations(valid_until);
CREATE INDEX IF NOT EXISTS ix_calibrations_device_param ON device_calibrations(device_id, param_name);

-- ============================================================================
-- 9. 实验配置表(experiment_configs) - 添加约束和索引
-- ============================================================================

CREATE TABLE IF NOT EXISTS experiment_configs_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    config_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CHECK (LENGTH(name) >= 1),
    CHECK (LENGTH(config_json) >= 2)
);

INSERT INTO experiment_configs_new (id, name, description, config_json, created_at, updated_at)
SELECT id, name, description, config_json, 
       COALESCE(created_at, CURRENT_TIMESTAMP),
       COALESCE(updated_at, CURRENT_TIMESTAMP)
FROM experiment_configs;

DROP TABLE experiment_configs;
ALTER TABLE experiment_configs_new RENAME TO experiment_configs;

CREATE INDEX IF NOT EXISTS ix_configs_name ON experiment_configs(name);

COMMIT;

-- ============================================================================
-- 验证迁移结果
-- ============================================================================

SELECT 'Migration completed. Verifying constraints and indexes...' AS status;

-- 显示所有表的索引
SELECT 
    m.name AS table_name,
    il.name AS index_name
FROM sqlite_master m,
    pragma_index_list(m.name) il
WHERE m.type = 'table'
    AND m.name NOT LIKE 'sqlite_%'
ORDER BY m.name, il.name;

SELECT 'Database migration completed successfully!' AS status;
