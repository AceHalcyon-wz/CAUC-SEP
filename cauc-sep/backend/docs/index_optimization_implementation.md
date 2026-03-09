# 数据库索引优化实现说明

## 实现文件

### 1. 核心模块
**文件**: [core/index_optimizer.py](file:///c:/Users/15272/Downloads/kimiOKC/cauc-sep/backend/core/index_optimizer.py)

**主要功能**:
- `QueryPerformanceMonitor`: 查询性能监控器
  - 实时监控数据库查询性能
  - 记录慢查询（可配置阈值，默认100ms）
  - 分析查询模式，识别高频查询
  - 线程安全的性能统计

- `IndexOptimizer`: 索引优化器
  - 分析现有索引结构
  - 分析表统计信息（行数、列信息）
  - 根据查询模式生成索引推荐
  - 创建/删除索引
  - 分析单个查询性能

- `DatabaseIndexMigration`: 数据库索引迁移
  - 预定义索引配置（基于项目查询模式）
  - 支持预演模式（dry-run）
  - 支持回滚操作
  - 自动备份

### 2. 迁移脚本
**文件**: [migrations/optimize_indexes.py](file:///c:/Users/15272/Downloads/kimiOKC/cauc-sep/backend/migrations/optimize_indexes.py)

**使用方法**:
```bash
# 分析索引
python migrations/optimize_indexes.py --db experiments.db --analyze

# 预演迁移（不实际执行）
python migrations/optimize_indexes.py --db experiments.db --migrate --dry-run

# 执行迁移
python migrations/optimize_indexes.py --db experiments.db --migrate

# 验证索引
python migrations/optimize_indexes.py --db experiments.db --verify

# 性能测试
python migrations/optimize_indexes.py --db experiments.db --test
```

### 3. 性能测试
**文件**: [tests/test_query_performance.py](file:///c:/Users/15272/Downloads/kimiOKC/cauc-sep/backend/tests/test_query_performance.py)

**测试覆盖**:
- 索引优化器初始化和基本功能
- 索引创建和删除
- 查询性能分析
- 慢查询检测
- 查询模式分析
- 并发查询监控
- 索引效果对比测试
- 基准性能测试（大数据集）

### 4. 集成到DataStorage
**文件**: [core/data_storage.py](file:///c:/Users/15272/Downloads/kimiOKC/cauc-sep/backend/core/data_storage.py)

**新增方法**:
- `get_performance_statistics()`: 获取查询性能统计
- `get_slow_queries(limit)`: 获取慢查询列表
- `get_query_patterns(limit)`: 获取查询模式分析
- `optimize_indexes(dry_run)`: 优化数据库索引
- `analyze_query_performance(sql)`: 分析单个查询性能
- `clear_performance_history()`: 清空性能监控历史

## 预定义索引配置

基于项目查询模式，预定义了以下索引：

### data_records表
- `ix_data_records_exp_timestamp_desc`: 实验数据按时间倒序查询
- `ix_data_records_exp_position`: 实验数据按位置查询
- `ix_data_records_timestamp_desc`: 全局时间范围查询

### experiments表
- `ix_experiments_status_created`: 按状态和时间查询实验
- `ix_experiments_type_status`: 按类型和状态查询实验

### audit_logs表
- `ix_audit_logs_timestamp_desc`: 审计日志时间范围查询
- `ix_audit_logs_type_timestamp`: 按操作类型查询审计日志

### operation_logs表
- `ix_operation_logs_created_desc`: 操作日志时间范围查询
- `ix_operation_logs_operation_created`: 按操作类型查询操作日志

### device_calibrations表
- `ix_calibrations_valid_device`: 查询即将过期的校准参数

## 性能监控特性

1. **实时监控**: 通过SQLAlchemy事件监听器自动捕获所有查询
2. **慢查询检测**: 可配置阈值，默认100ms
3. **查询模式分析**: 自动识别高频查询和性能瓶颈
4. **线程安全**: 支持并发环境下的性能监控
5. **历史记录**: 保留最近10000条查询记录

## 使用示例

```python
from core.data_storage import DataStorage

# 初始化（自动启用性能监控）
storage = DataStorage("experiments.db")

# 获取性能统计
stats = storage.get_performance_statistics()
print(f"总查询数: {stats['total_queries']}")
print(f"慢查询数: {stats['slow_query_count']}")

# 获取慢查询
slow_queries = storage.get_slow_queries(limit=10)
for query in slow_queries:
    print(f"{query['duration_ms']:.2f}ms - {query['sql'][:100]}")

# 优化索引（预演）
result = storage.optimize_indexes(dry_run=True)
print(f"将创建 {len(result['created_indexes'])} 个索引")

# 执行索引优化
result = storage.optimize_indexes(dry_run=False)

# 分析特定查询性能
analysis = storage.analyze_query_performance(
    "SELECT * FROM data_records WHERE experiment_id = 1 LIMIT 100"
)
print(f"执行时间: {analysis['duration_ms']:.2f}ms")
```

## 测试结果

所有16个测试用例全部通过：
- 索引优化器初始化 ✓
- 获取现有索引 ✓
- 分析表统计信息 ✓
- 分析查询模式 ✓
- 创建索引 ✓
- 删除索引 ✓
- 分析查询性能 ✓
- 数据库索引迁移 ✓
- 迁移预演模式 ✓
- 索引回滚 ✓
- 查询性能监控 ✓
- 慢查询检测 ✓
- 查询模式分析 ✓
- 索引效果对比 ✓
- 并发查询监控 ✓
- 清空性能历史 ✓

## 技术特点

1. **零侵入性**: 通过SQLAlchemy事件监听器实现，无需修改现有查询代码
2. **智能推荐**: 基于查询频率和执行时间自动生成索引推荐
3. **安全迁移**: 支持预演模式和自动备份，确保数据安全
4. **性能优先**: 使用原生SQLite连接进行索引操作，避免ORM开销
5. **完整测试**: 包含单元测试、集成测试和性能基准测试

---

## 版本信息

- **实现版本**: v1.0.0
- **更新日期**: 2026-03-08
- **作者**: Backend Engineer Agent
