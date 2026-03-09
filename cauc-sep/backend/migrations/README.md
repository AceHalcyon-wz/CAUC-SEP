# 数据库迁移文档

## 概述

本文档记录 CAUC-SEP 自旋电子实验平台数据库的所有迁移历史，包括表结构变更、约束添加和索引优化。

## 迁移版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| 002 | 2026-03-07 | 添加字段约束、索引优化和外键级联 |
| 001 | 2026-03-07 | 添加设备校准、操作日志和实验配置表 |

---

## 版本 002: 添加约束和索引优化

### 变更概述

为所有核心表添加CHECK约束、NOT NULL约束、索引优化和外键级联删除规则。

### 变更详情

#### 1. 用户表 (users)

**新增约束**:
- `CHECK (role IN ('admin', 'operator', 'viewer'))` - 角色有效性约束
- `CHECK (LENGTH(username) >= 3)` - 用户名最小长度
- `CHECK (LENGTH(password_hash) >= 32)` - 密码哈希最小长度
- 所有字段添加 `NOT NULL` 约束

**新增索引**:
- `ix_users_username` - 用户名索引
- `ix_users_role` - 角色索引
- `ix_users_role_active` - 复合索引(角色+激活状态)

#### 2. 设备表 (devices)

**新增约束**:
- `CHECK (status IN ('offline', 'online', 'busy', 'error', 'maintenance'))` - 状态有效性
- `CHECK (LENGTH(device_id) >= 1)` - 设备ID非空

**新增索引**:
- `ix_devices_device_id` - 设备ID索引
- `ix_devices_device_type` - 设备类型索引
- `ix_devices_status` - 状态索引
- `ix_devices_type_status` - 复合索引(类型+状态)

**外键级联**:
- `pr_paths` 关联添加 `ON DELETE CASCADE`

#### 3. 实验表 (experiments)

**新增约束**:
- `CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))` - 状态有效性
- `CHECK (LENGTH(exp_name) >= 1)` - 实验名非空

**新增索引**:
- `ix_experiments_exp_name` - 实验名索引
- `ix_experiments_exp_type` - 实验类型索引
- `ix_experiments_user_id` - 用户ID索引
- `ix_experiments_status` - 状态索引
- `ix_experiments_created_at` - 创建时间索引
- `ix_experiments_user_status` - 复合索引(用户+状态)

**外键级联**:
- `user_id` 添加 `ON DELETE SET NULL`
- `data_records` 关联添加 `ON DELETE CASCADE`

#### 4. 数据记录表 (data_records)

**新增索引**:
- `ix_data_records_experiment_id` - 实验ID索引
- `ix_data_records_timestamp` - 时间戳索引
- `ix_data_records_exp_timestamp` - 复合索引(实验+时间)

**外键级联**:
- `experiment_id` 添加 `ON DELETE CASCADE`

#### 5. PR路径表 (pr_paths)

**新增约束**:
- `CHECK (path_number >= 0 AND path_number <= 15)` - 路径编号范围
- `CHECK (velocity > 0)` - 速度正值约束
- `CHECK (accel_time >= 0)` - 加速时间非负
- `CHECK (decel_time >= 0)` - 减速时间非负

**新增索引**:
- `ix_pr_paths_device_id` - 设备ID索引
- `ix_pr_paths_device_path` - 复合索引(设备+路径号)

**外键级联**:
- `device_id` 添加 `ON DELETE CASCADE`

#### 6. 审计日志表 (audit_logs)

**新增约束**:
- `CHECK (operation_category IN ('device', 'experiment', 'system', 'calibration', 'config'))`
- `CHECK (request_method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH'))`
- `CHECK (response_status >= 100 AND response_status < 600 OR response_status IS NULL)`
- `CHECK (duration_ms >= 0 OR duration_ms IS NULL)`

**新增索引**:
- `ix_audit_logs_timestamp` - 时间戳索引
- `ix_audit_logs_user_id` - 用户ID索引
- `ix_audit_logs_device_id` - 设备ID索引
- `ix_audit_logs_operation_type` - 操作类型索引
- `ix_audit_logs_operation_category` - 操作类别索引
- `ix_audit_logs_request_path` - 请求路径索引
- `ix_audit_logs_response_status` - 响应状态索引
- `ix_audit_logs_ip_address` - IP地址索引
- `ix_audit_logs_user_timestamp` - 复合索引
- `ix_audit_logs_device_timestamp` - 复合索引
- `ix_audit_logs_category_timestamp` - 复合索引

**外键级联**:
- `user_id` 添加 `ON DELETE SET NULL`

#### 7. 操作日志表 (operation_logs)

**新增约束**:
- `CHECK (result IN ('success', 'failed', 'pending') OR result IS NULL)`

**新增索引**:
- `ix_operation_logs_user_id` - 用户ID索引
- `ix_operation_logs_device_id` - 设备ID索引
- `ix_operation_logs_operation` - 操作类型索引
- `ix_operation_logs_result` - 结果索引
- `ix_operation_logs_created_at` - 创建时间索引
- `ix_operation_logs_user_created` - 复合索引
- `ix_operation_logs_device_created` - 复合索引

**外键级联**:
- `user_id` 添加 `ON DELETE SET NULL`

#### 8. 设备校准表 (device_calibrations)

**新增约束**:
- `CHECK (LENGTH(device_id) >= 1)` - 设备ID非空
- `CHECK (LENGTH(param_name) >= 1)` - 参数名非空

**新增索引**:
- `ix_calibrations_device_id` - 设备ID索引
- `ix_calibrations_valid_until` - 有效期索引
- `ix_calibrations_device_param` - 复合索引

#### 9. 实验配置表 (experiment_configs)

**新增约束**:
- `CHECK (LENGTH(name) >= 1)` - 配置名非空
- `CHECK (LENGTH(config_json) >= 2)` - 配置数据非空
- `UNIQUE(name)` - 配置名唯一

**新增索引**:
- `ix_configs_name` - 配置名索引

### 执行迁移

```bash
cd c:\Users\15272\Downloads\kimiOKC\cauc-sep\backend

# 方法一: Python脚本 (推荐)
python migrations/add_constraints_indexes.py --db experiments.db

# 方法二: SQL脚本
sqlite3 experiments.db < migrations/sql/002_add_constraints_indexes.sql
```

### 回滚说明

由于SQLite的限制，约束和索引无法直接回滚。如需回滚，请使用迁移前自动创建的备份文件：

```
experiments.db.backup_YYYYMMDD_HHMMSS
```

---

## 版本 001: 添加设备校准、操作日志和实验配置表

### 变更概述

为现有数据库添加三个新表,用于增强设备管理、操作审计和实验配置功能。

### 新增表结构

#### 1. device_calibrations (设备校准参数表)

存储设备的校准参数信息,包括参数名、参数值、校准日期和有效期。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键,自增 |
| device_id | VARCHAR(50) | 设备ID |
| param_name | VARCHAR(100) | 参数名称 |
| param_value | TEXT | 参数值 |
| calibration_date | TIMESTAMP | 校准日期 |
| valid_until | TIMESTAMP | 有效期截止日期 |

**约束**: UNIQUE(device_id, param_name) - 每个设备的每个参数名唯一

**索引**:
- idx_device_calibrations_device_id
- idx_device_calibrations_valid_until

#### 2. operation_logs (操作日志表)

记录用户对设备和系统的操作历史,包括操作类型、参数、结果和错误信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键,自增 |
| user_id | INTEGER | 用户ID (外键) |
| device_id | VARCHAR(50) | 设备ID |
| operation | VARCHAR(100) | 操作类型 |
| parameters | TEXT | 操作参数 (JSON) |
| result | VARCHAR(20) | 操作结果 |
| error_message | TEXT | 错误信息 |
| created_at | TIMESTAMP | 创建时间 |

**外键**: user_id REFERENCES users(id)

**索引**:
- idx_operation_logs_user_id
- idx_operation_logs_device_id
- idx_operation_logs_created_at
- idx_operation_logs_operation

#### 3. experiment_configs (实验配置表)

存储实验的预设配置模板,包括配置名称、描述和JSON格式的配置数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键,自增 |
| name | VARCHAR(100) | 配置名称 |
| description | TEXT | 配置描述 |
| config_json | TEXT | 配置数据 (JSON) |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**索引**:
- idx_experiment_configs_name
- idx_experiment_configs_created_at

### 执行迁移

```bash
cd c:\Users\15272\Downloads\kimiOKC\cauc-sep\backend

# 方法一: Python脚本 (推荐)
python migrations/add_calibration_logs_configs.py --db experiments.db

# 方法二: SQL脚本
sqlite3 experiments.db < migrations/sql/001_add_calibration_logs_configs.sql
```

### 回滚迁移

```bash
python migrations/add_calibration_logs_configs.py --db experiments.db --rollback
```

**警告**: 回滚操作会删除表及数据,请提前备份!

---

## 验证迁移

迁移完成后,脚本会自动验证新表功能。也可以手动验证:

```sql
-- 检查表是否存在
SELECT name FROM sqlite_master
WHERE type='table'
AND name IN ('users', 'devices', 'experiments', 'data_records', 'pr_paths', 
             'audit_logs', 'operation_logs', 'device_calibrations', 'experiment_configs');

-- 查看索引
SELECT m.name AS table_name, il.name AS index_name
FROM sqlite_master m, pragma_index_list(m.name) il
WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
ORDER BY m.name, il.name;

-- 验证约束
INSERT INTO users (username, password_hash, role) VALUES ('ab', 'short', 'invalid');
-- 应该失败: 违反约束
```

---

## 使用示例

### 设备校准参数管理

```python
from core.data_storage import DataStorage
from datetime import datetime, timedelta

storage = DataStorage("experiments.db")

# 创建校准参数
cal_id = storage.create_device_calibration(
    device_id="stepper_01",
    param_name="steps_per_mm",
    param_value="1600",
    calibration_date=datetime.now(),
    valid_until=datetime.now() + timedelta(days=365)
)

# 查询校准参数
cal = storage.get_device_calibration("stepper_01", "steps_per_mm")

# 列出设备的所有校准参数
cals = storage.list_device_calibrations("stepper_01")

# 更新校准参数
storage.update_device_calibration(
    "stepper_01",
    "steps_per_mm",
    param_value="1650"
)
```

### 操作日志管理

```python
# 记录操作日志
log_id = storage.create_operation_log(
    operation="motor_move",
    user_id=1,
    device_id="stepper_01",
    parameters={"position_mm": 10.0, "velocity_mm_s": 5.0},
    result="success"
)

# 查询操作日志
logs = storage.list_operation_logs(limit=100, user_id=1)
```

### 实验配置管理

```python
# 创建实验配置
config_id = storage.create_experiment_config(
    name="默认扫描配置",
    description="标准磁场扫描实验配置",
    config_json={
        "velocity": 10.0,
        "acceleration": 1000.0,
        "field_range": [-1.0, 1.0]
    }
)

# 查询实验配置
config = storage.get_experiment_config(config_id)

# 列出所有配置
configs = storage.list_experiment_configs()

# 更新配置
storage.update_experiment_config(
    config_id,
    description="更新后的配置描述"
)

# 删除配置
storage.delete_experiment_config(config_id)
```

---

## 注意事项

1. **备份数据库**: 执行迁移前请务必备份数据库文件
2. **幂等性**: 迁移脚本支持重复执行,不会重复创建已存在的表
3. **数据完整性**: 新表的外键约束确保数据完整性
4. **性能优化**: 已为常用查询字段创建索引
5. **向后兼容**: 新表不影响现有表结构和功能
6. **SQLite限制**: SQLite不支持ALTER TABLE ADD CONSTRAINT，约束通过重建表实现

---

## 技术栈

- **数据库**: SQLite 3
- **ORM**: SQLAlchemy 2.0
- **Python**: 3.11+
- **迁移工具**: 自定义Python脚本

---

## 相关文件

- 数据模型: `models/__init__.py`
- 数据存储: `core/data_storage.py`
- 迁移脚本: 
  - `migrations/add_calibration_logs_configs.py`
  - `migrations/add_constraints_indexes.py`
- SQL脚本: 
  - `migrations/sql/001_add_calibration_logs_configs.sql`
  - `migrations/sql/002_add_constraints_indexes.sql`

---

## 更新日志

### v2.1 (2026-03-08)
- 更新文档日期和版本信息
- 确认所有迁移脚本与当前项目结构一致

### v2.0 (2026-03-07)
- 为所有核心表添加CHECK约束
- 添加NOT NULL约束和默认值
- 创建30+索引优化查询性能
- 配置外键级联删除规则
- 完善字段文档注释

### v1.0 (2026-03-07)
- 新增 device_calibrations 表
- 新增 operation_logs 表
- 新增 experiment_configs 表
- 实现完整的CRUD操作方法
- 添加数据库索引优化查询性能
