-- ============================================================================
-- CAUC-SEP 数据库索引性能优化脚本
-- 
-- 文件名: 003_optimize_indexes_performance.sql
-- 路径: migrations/sql/
-- 功能: 时序数据索引优化、复合索引创建、查询性能提升
-- 作者: Backend Engineer Agent
-- 创建日期: 2026-03-08
-- 版本: 1.0
-- 
-- 使用方法:
--   sqlite3 experiments.db < migrations/sql/003_optimize_indexes_performance.sql
-- 
-- 注意事项:
--   1. 执行前请备份数据库
--   2. 大表创建索引可能需要较长时间
--   3. 建议在低峰期执行
-- ============================================================================

-- ============================================================================
-- 1. 数据记录表索引优化 (data_records)
-- ============================================================================

-- 1.1 实验数据时间范围查询索引（降序）
-- 用途: 实验数据按时间倒序查询、分页加载
-- 场景: SELECT * FROM data_records WHERE experiment_id = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS ix_data_records_exp_timestamp_desc
ON data_records(experiment_id, timestamp DESC);

-- 1.2 实验数据位置扫描索引
-- 用途: 位置扫描实验数据查询
-- 场景: SELECT * FROM data_records WHERE experiment_id = ? AND position_steps BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS ix_data_records_exp_position
ON data_records(experiment_id, position_steps);

-- 1.3 全局时间范围查询索引（降序）
-- 用途: 跨实验时间范围查询、数据归档
-- 场景: SELECT * FROM data_records WHERE timestamp >= ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS ix_data_records_timestamp_desc
ON data_records(timestamp DESC);

-- 1.4 实验数据复合索引（位置+时间）
-- 用途: 位置扫描实验数据查询优化
-- 场景: SELECT * FROM data_records WHERE experiment_id = ? ORDER BY position_steps, timestamp
CREATE INDEX IF NOT EXISTS ix_data_records_exp_pos_scan
ON data_records(experiment_id, position_steps, timestamp);

-- 1.5 实验数据磁场值查询索引
-- 用途: 磁场扫描数据查询
-- 场景: SELECT * FROM data_records WHERE experiment_id = ? AND field_value BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS ix_data_records_exp_field
ON data_records(experiment_id, field_value);

-- ============================================================================
-- 2. 实验表索引优化 (experiments)
-- ============================================================================

-- 2.1 按状态和时间查询实验
-- 用途: 实验列表按状态筛选
-- 场景: SELECT * FROM experiments WHERE status = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS ix_experiments_status_created
ON experiments(status, created_at DESC);

-- 2.2 按类型和状态查询实验
-- 用途: 按实验类型筛选
-- 场景: SELECT * FROM experiments WHERE exp_type = ? AND status = ?
CREATE INDEX IF NOT EXISTS ix_experiments_type_status
ON experiments(exp_type, status);

-- 2.3 用户实验查询索引
-- 用途: 查询用户的实验列表
-- 场景: SELECT * FROM experiments WHERE user_id = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS ix_experiments_user_created_desc
ON experiments(user_id, created_at DESC);

-- 2.4 运行中实验查询索引
-- 用途: 查询正在运行的实验
-- 场景: SELECT * FROM experiments WHERE status = 'running'
CREATE INDEX IF NOT EXISTS ix_experiments_running
ON experiments(status) WHERE status = 'running';

-- ============================================================================
-- 3. 审计日志表索引优化 (audit_logs)
-- ============================================================================

-- 3.1 审计日志时间范围查询索引（降序）
-- 用途: 审计日志列表、时间范围筛选
-- 场景: SELECT * FROM audit_logs WHERE timestamp >= ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp_desc
ON audit_logs(timestamp DESC);

-- 3.2 按操作类型查询审计日志
-- 用途: 操作类型筛选
-- 场景: SELECT * FROM audit_logs WHERE operation_type = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS ix_audit_logs_type_timestamp
ON audit_logs(operation_type, timestamp DESC);

-- 3.3 按操作类别查询审计日志
-- 用途: 操作类别筛选
-- 场景: SELECT * FROM audit_logs WHERE operation_category = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS ix_audit_logs_category_timestamp
ON audit_logs(operation_category, timestamp DESC);

-- 3.4 用户审计日志查询索引
-- 用途: 用户操作历史
-- 场景: SELECT * FROM audit_logs WHERE user_id = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_timestamp_desc
ON audit_logs(user_id, timestamp DESC);

-- 3.5 设备审计日志查询索引
-- 用途: 设备操作历史
-- 场景: SELECT * FROM audit_logs WHERE device_id = ? ORDER BY timestamp DESC
CREATE INDEX IF NOT EXISTS ix_audit_logs_device_timestamp_desc
ON audit_logs(device_id, timestamp DESC);

-- 3.6 IP地址审计日志查询索引
-- 用途: 按IP地址查询访问记录
-- 场景: SELECT * FROM audit_logs WHERE ip_address = ?
CREATE INDEX IF NOT EXISTS ix_audit_logs_ip
ON audit_logs(ip_address);

-- ============================================================================
-- 4. 操作日志表索引优化 (operation_logs)
-- ============================================================================

-- 4.1 操作日志时间范围查询索引（降序）
-- 用途: 操作日志列表、时间范围筛选
-- 场景: SELECT * FROM operation_logs ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS ix_operation_logs_created_desc
ON operation_logs(created_at DESC);

-- 4.2 按操作类型查询操作日志
-- 用途: 操作类型筛选
-- 场景: SELECT * FROM operation_logs WHERE operation = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS ix_operation_logs_operation_created
ON operation_logs(operation, created_at DESC);

-- 4.3 用户操作日志查询索引
-- 用途: 用户操作历史
-- 场景: SELECT * FROM operation_logs WHERE user_id = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS ix_operation_logs_user_created_desc
ON operation_logs(user_id, created_at DESC);

-- 4.4 设备操作日志查询索引
-- 用途: 设备操作历史
-- 场景: SELECT * FROM operation_logs WHERE device_id = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS ix_operation_logs_device_created_desc
ON operation_logs(device_id, created_at DESC);

-- 4.5 操作结果查询索引
-- 用途: 按结果筛选操作日志
-- 场景: SELECT * FROM operation_logs WHERE result = ?
CREATE INDEX IF NOT EXISTS ix_operation_logs_result
ON operation_logs(result);

-- ============================================================================
-- 5. 设备校准表索引优化 (device_calibrations)
-- ============================================================================

-- 5.1 查询即将过期的校准参数
-- 用途: 校准有效期提醒
-- 场景: SELECT * FROM device_calibrations WHERE valid_until <= ? ORDER BY valid_until
CREATE INDEX IF NOT EXISTS ix_calibrations_valid_device
ON device_calibrations(valid_until, device_id);

-- 5.2 设备校准参数查询索引
-- 用途: 获取设备所有校准参数
-- 场景: SELECT * FROM device_calibrations WHERE device_id = ?
CREATE INDEX IF NOT EXISTS ix_calibrations_device_param
ON device_calibrations(device_id, param_name);

-- ============================================================================
-- 6. 用户表索引优化 (users)
-- ============================================================================

-- 6.1 用户名查询索引（确保存在）
-- 用途: 用户登录验证
-- 场景: SELECT * FROM users WHERE username = ?
CREATE INDEX IF NOT EXISTS ix_users_username
ON users(username);

-- 6.2 用户角色查询索引
-- 用途: 按角色筛选用户
-- 场景: SELECT * FROM users WHERE role = ?
CREATE INDEX IF NOT EXISTS ix_users_role
ON users(role);

-- 6.3 活跃用户查询索引
-- 用途: 活跃用户统计
-- 场景: SELECT * FROM users WHERE is_active = 1 ORDER BY last_login DESC
CREATE INDEX IF NOT EXISTS ix_users_active_login
ON users(is_active, last_login DESC);

-- ============================================================================
-- 7. 设备表索引优化 (devices)
-- ============================================================================

-- 7.1 设备ID查询索引（确保存在）
-- 用途: 设备查询
-- 场景: SELECT * FROM devices WHERE device_id = ?
CREATE INDEX IF NOT EXISTS ix_devices_device_id
ON devices(device_id);

-- 7.2 设备类型和状态复合索引
-- 用途: 按类型和状态筛选设备
-- 场景: SELECT * FROM devices WHERE device_type = ? AND status = ?
CREATE INDEX IF NOT EXISTS ix_devices_type_status
ON devices(device_type, status);

-- 7.3 设备状态查询索引
-- 用途: 按状态筛选设备
-- 场景: SELECT * FROM devices WHERE status = ?
CREATE INDEX IF NOT EXISTS ix_devices_status
ON devices(status);

-- ============================================================================
-- 8. PR路径表索引优化 (pr_paths)
-- ============================================================================

-- 8.1 设备PR路径查询索引（确保存在）
-- 用途: 获取设备的所有PR路径
-- 场景: SELECT * FROM pr_paths WHERE device_id = ? ORDER BY path_number
CREATE INDEX IF NOT EXISTS ix_pr_paths_device_path
ON pr_paths(device_id, path_number);

-- ============================================================================
-- 9. 实验配置表索引优化 (experiment_configs)
-- ============================================================================

-- 9.1 配置名称索引（确保存在）
-- 用途: 按名称查询配置
-- 场景: SELECT * FROM experiment_configs WHERE name = ?
CREATE INDEX IF NOT EXISTS ix_experiment_configs_name
ON experiment_configs(name);

-- 9.2 配置更新时间索引
-- 用途: 按更新时间排序
-- 场景: SELECT * FROM experiment_configs ORDER BY updated_at DESC
CREATE INDEX IF NOT EXISTS ix_experiment_configs_updated
ON experiment_configs(updated_at DESC);

-- ============================================================================
-- 10. 性能优化设置
-- ============================================================================

-- 10.1 执行ANALYZE更新统计信息
-- 建议：在大量数据导入后执行
ANALYZE;

-- ============================================================================
-- 11. 索引验证查询
-- ============================================================================

-- 验证索引创建情况
-- SELECT 
--     m.name AS table_name,
--     il.name AS index_name,
--     ii.name AS column_name
-- FROM sqlite_master m
-- JOIN pragma_index_list(m.name) il
-- JOIN pragma_index_info(il.name) ii
-- WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
-- ORDER BY m.name, il.name, ii.seqno;

-- ============================================================================
-- 12. 索引使用情况分析
-- ============================================================================

-- 查看查询计划（验证索引是否被使用）
-- EXPLAIN QUERY PLAN SELECT * FROM data_records WHERE experiment_id = 1 ORDER BY timestamp DESC;
-- EXPLAIN QUERY PLAN SELECT * FROM experiments WHERE status = 'running' ORDER BY created_at DESC;
-- EXPLAIN QUERY PLAN SELECT * FROM audit_logs WHERE timestamp >= datetime('now', '-7 days') ORDER BY timestamp DESC;
